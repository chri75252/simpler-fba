"""
Passive extraction workflow for Amazon FBA products from supplier websites.
MODIFIED: To integrate ConfigurableSupplierScraper, Zero-Token Triage,
enhanced product validation, and updated sales velocity logic.
Uses Chrome with debug port for Amazon data (via AmazonExtractor) and a
configurable web scraper for supplier sites.
Integrates AI client for enhanced extraction capabilities and optimizes data processing.
"""

import os, logging
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = (
        "sk-15Mk5F_Nvf8k06VvEi4_TD2GhL8mQnqR_8I6Z2zHjWT3BlbkFJvKlNwbgLB_HPw1C-SixqIskN03to4PNyXnXedS-pMA"
    )
    logging.warning("OPENAI_API_KEY not supplied – using hard-coded fallback")

import os
import asyncio
import logging
import json
import sys
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set, Union
from collections import defaultdict
import re
import time
import xml.etree.ElementTree as ET
import requests
from urllib.parse import urlparse, parse_qs, urljoin, parse_qsl, urlencode, urlunparse
import difflib # Added for enhanced title similarity
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path # ADDED IMPORT
import aiohttp  # Added for async HTTP requests

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Assuming OpenAI client; ensure it's installed: pip install openai
from openai import OpenAI
# For enhanced HTML parsing
from bs4 import BeautifulSoup

# Import required custom modules
# FIXED: Change relative imports to absolute imports when running as standalone script
import sys
import os
# Add both tools directory and parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from amazon_playwright_extractor import AmazonExtractor # Base class for FixedAmazonExtractor
# MODIFIED: Use ConfigurableSupplierScraper
from configurable_supplier_scraper import ConfigurableSupplierScraper
# Zero-token triage module available but not activated by default
# from zero_token_triage_module import perform_zero_token_triage
# Import FBA Calculator for accurate fee calculations
# from FBA_Financial_calculator import FBACalculator  # TODO: Fix class name or create wrapper
from cache_manager import CacheManager
from tools.linking_map_writer import LinkingMapWriter

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"fba_extraction_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
log = logging.getLogger(__name__)

# ──────────────────────── ①  Enhanced FBA Priority Patterns (Research-Based) ──────────────────────
FBA_FRIENDLY_PATTERNS = {
    "home_kitchen":      ["home","kitchen","dining","storage","decor","organization","household"],     # Priority #1
    "pet_supplies":      ["pet","dog","cat","animal","bird","aquarium","fish"],                  # Priority #2
    "beauty_care":       ["beauty","personal","skincare","grooming","cosmetic","health"],            # Priority #3
    "sports_outdoor":    ["sport","fitness","camping","outdoor","exercise","yoga","garden"],     # Priority #4
    "office_stationery": ["office","stationery","desk","paper","business","school"],           # Priority #5
    "diy_tools":         ["diy","tool","hardware","hand-tool","craft","workshop","repair"],           # Priority #6
    "baby_nursery":      ["baby","infant","nursery","toddler","child-safe","kids"],               # Priority #7
    "toys_games":        ["toy","game","puzzle","educational","learning","play"],              # Priority #8
    "automotive":        ["car","auto","vehicle","motorcycle","bike","cycling"],                # Priority #9
    "kids_books":        ["kids book","children book","coloring book","sticker book","activity book","playbook","educational book","picture book","story book"],  # Priority #10
    "clearance_value":   ["pound","poundline","50p","under","clearance","sale","discount","bargain","cheap","value","deal"],  # Priority #11 (Medium-Low)
    "crafts_hobbies":    ["craft","hobby","sewing","knitting","art","creative","scrapbook","drawing"],  # Priority #12 (Lower)
    "seasonal_items":    ["christmas","halloween","easter","valentine","seasonal","holiday","party"],  # Priority #13 (Lower)
    "miscellaneous":     ["misc","other","general","various","assorted","mixed"]                # Priority #14 (Lower)
}
FBA_AVOID_PATTERNS = {
    "dangerous_goods": ["battery","power","lithium","flammable","hazmat","explosive"],           # CRITICAL AVOID
    "electronics":     ["electronic","tech","computer","phone","gadget","digital","tv"],     # HIGH AVOID
    "clothing":        ["clothing","fashion","apparel","shoe","sock","wear","dress"],             # HIGH AVOID
    "medical":         ["medical","pharma","medicine","healthcare","therapeutic","prescription"],          # HIGH AVOID
    "food":            ["food","beverage","grocery","snack","drink","edible","alcohol"],               # HIGH AVOID
    "large_bulky":     ["appliance","sofa","mattress","wardrobe","furniture","heavy"],          # MEDIUM AVOID
    "high_value":      ["jewelry","jewellery","watch","precious","gold","diamond","expensive"],      # MEDIUM AVOID
    "adult_books":     ["novel","fiction","romance","thriller","biography","autobiography","textbook","academic book","adult book","paperback novel"]  # AVOID adult reading books
}

# Third category for when FBA friendly categories are exhausted
FBA_NEUTRAL_PATTERNS = {
    "collectibles":    ["collectible","vintage","antique","memorabilia"],
    "media_dvd_cd":    ["dvd","cd","music","movie","film","media"]  # Removed general "book" from here since it's now classified above
}

# ──────────────────────── ②  Add OpenAI client initialization (after imports) ────────────

# Battery filtering patterns - products containing these will be excluded
BATTERY_KEYWORDS = [
    "battery", "batteries", "lithium", "alkaline", "rechargeable", 
    "power cell", "coin cell", "button cell", "watch battery", 
    "hearing aid battery", "cordless phone battery", "9v battery",
    "aa battery", "aaa battery", "c battery", "d battery",
    "cr2032", "cr2025", "cr2016", "cr1220", "cr1632", "cr2354",
    "lr44", "lr41", "lr20", "lr14", "lr6", "lr03",
    "ag13", "ag10", "ag4", "ag3", "ag1", "sr626", "sr621",
    "18650", "26650", "14500", "16340", "10440",
    "4lr44", "23a", "27a", "n battery", "aaaa battery"
]

BATTERY_BRAND_CONTEXT = [
    "duracell", "energizer", "panasonic", "rayovac", "eveready",
    "maxell", "renata", "vinnic", "gp", "varta", "sony",
    "toshiba", "philips", "uniross", "extrastar", "infapower",
    "eunicell", "jcb battery", "tesco battery"
]

# Non-FBA friendly product filtering patterns - products containing these will be excluded
NON_FBA_FRIENDLY_KEYWORDS = [
    # Smoking/Drug-related products
    "smoking pipe", "glass pipe", "water pipe", "tobacco pipe", "hookah", "shisha",
    "bong", "vaporizer", "vape", "e-cigarette", "cigarette", "cigar", "rolling paper",
    "grinder", "herb grinder", "smoking accessories", "pipe cleaner", "pipe screen",
    
    # Weapons and dangerous items
    "knife", "blade", "sword", "dagger", "machete", "tactical", "self defense",
    "pepper spray", "stun gun", "taser", "brass knuckles", "nunchucks",
    
    # Adult/inappropriate content
    "adult toy", "sex toy", "erotic", "pornographic", "xxx", "adult entertainment",
    
    # Hazardous materials
    "flammable", "explosive", "toxic", "corrosive", "radioactive", "biohazard",
    "chemical", "pesticide", "insecticide", "poison", "acid",
    
    # Restricted electronics
    "laser pointer", "high power laser", "jamming device", "signal jammer",
    "surveillance", "spy camera", "hidden camera", "wiretap",
    
    # Medical devices (restricted)
    "prescription", "medical device", "surgical", "diagnostic", "therapeutic device",
    "hearing aid", "pacemaker", "insulin pump", "blood glucose",
    
    # Counterfeit indicators
    "replica", "fake", "knockoff", "copy", "imitation", "unauthorized",
    
    # Alcohol and controlled substances
    "alcohol", "wine", "beer", "spirits", "liquor", "alcoholic",
    
    # Live animals and perishables
    "live animal", "pet", "fish", "bird", "reptile", "fresh food", "perishable"
]

NON_FBA_FRIENDLY_BRAND_CONTEXT = [
    # Smoking brands
    "zippo", "clipper", "bic lighter", "dunhill", "peterson pipe", "savinelli",
    "chacom", "stanwell", "missouri meerschaum", "raw papers", "zig zag",
    
    # Weapon brands
    "gerber", "benchmade", "spyderco", "cold steel", "ka-bar", "smith wesson",
    
    # Vaping brands
    "juul", "pax", "volcano", "storz bickel", "davinci", "arizer"
]

# Price criteria for supplier products
MIN_PRICE = float(os.getenv("MIN_PRICE", "0.1"))
MAX_PRICE = float(os.getenv("MAX_PRICE", "20.0"))

# Profitability and Amazon listing criteria
MIN_ROI_PERCENT = float(os.getenv("MIN_ROI_PERCENT", "35.0"))
MIN_PROFIT_PER_UNIT = float(os.getenv("MIN_PROFIT_PER_UNIT", "3.0")) # Added explicit min profit
MIN_RATING = float(os.getenv("MIN_RATING", "4.0"))
MIN_REVIEWS = int(os.getenv("MIN_REVIEWS", "50"))
MAX_SALES_RANK = int(os.getenv("MAX_SALES_RANK", "150000"))

DEFAULT_SUPPLIER_URL = os.getenv("DEFAULT_SUPPLIER_URL", "https://www.clearance-king.co.uk")
DEFAULT_SUPPLIER_NAME = os.getenv("DEFAULT_SUPPLIER", "clearance-king.co.uk")

EXTENSION_DATA_WAIT = int(os.getenv("EXTENSION_DATA_WAIT", "25"))
DEFAULT_NAVIGATION_TIMEOUT = int(os.getenv("NAVIGATION_TIMEOUT", "60000"))
POST_NAVIGATION_STABILIZE_WAIT = int(os.getenv("STABILIZE_WAIT", "10"))

import json

# Initial constants and paths
# Get the base directory path dynamically
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.join(BASE_DIR, "OUTPUTS", "FBA_ANALYSIS"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load cache directories from config/system_config.json
def _load_cache_directories():
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "system_config.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        cache_dirs = config.get("cache", {}).get("directories", {})
        return cache_dirs
    except Exception as e:
        log.warning(f"Failed to load cache directories from config: {e}")
        return {}

cache_directories = _load_cache_directories()

# Global constant for persistent linking map in dedicated directory
LINKING_MAP_DIR = os.path.join(OUTPUT_DIR, "Linking map")
os.makedirs(LINKING_MAP_DIR, exist_ok=True)
LINKING_MAP_PATH = os.path.join(LINKING_MAP_DIR, "linking_map.json")

# Other directories
SUPPLIER_CACHE_DIR = os.path.join(BASE_DIR, "OUTPUTS", "cached_products")
AMAZON_CACHE_DIR = os.path.join(OUTPUT_DIR, "amazon_cache")
AI_CATEGORY_CACHE_DIR = os.path.join(OUTPUT_DIR, "ai_category_cache")

os.makedirs(SUPPLIER_CACHE_DIR, exist_ok=True)
os.makedirs(AMAZON_CACHE_DIR, exist_ok=True)
os.makedirs(AI_CATEGORY_CACHE_DIR, exist_ok=True)

# Load OpenAI configuration from system config
def _load_openai_config():
    """Load OpenAI configuration from system_config.json"""
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "system_config.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        openai_config = config.get("integrations", {}).get("openai", {})
        return {
            "api_key": openai_config.get("api_key", ""),
            "model": openai_config.get("model", "gpt-4o-mini"),
            "enabled": openai_config.get("enabled", False)
        }
    except Exception as e:
        log.warning(f"Failed to load OpenAI config from system_config.json: {e}")
        return {
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "enabled": True
        }

# Load OpenAI configuration
_openai_config = _load_openai_config()

# Load API key and model from environment variables or config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or _openai_config.get("api_key", "")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_PRIMARY", "gpt-4o-mini-2024-07-18")
OPENAI_ENABLED = bool(OPENAI_API_KEY) and _openai_config.get("enabled", True)

if not OPENAI_API_KEY:
    log.error("🚨 OPENAI_API_KEY not found in environment variables or config!")
    log.error("Please set OPENAI_API_KEY environment variable or update config/system_config.json")
    sys.exit(1)
# REMOVED: SUPPLIER_CONFIGS dictionary, as this is now handled by ConfigurableSupplierScraper and supplier_config_loader.py

# Battery product detection constants
BATTERY_KEYWORDS = ("battery", "batteries", "cell", "cr20", "lr41", "lithium", "alkaline")

def is_battery_title(title: str) -> bool:
    """Check if a product title indicates it's a battery product."""
    if not title:
        return False
    return any(k in title.lower() for k in BATTERY_KEYWORDS)

class FixedAmazonExtractor(AmazonExtractor):
    """
    Extension of AmazonExtractor.
    Includes EAN search capabilities and attempts EAN extraction from product pages.
    It reuses browser pages and avoids unnecessary page creation/closure for extension stability.
    """

    def __init__(self, chrome_debug_port: int, ai_client: Optional[OpenAI] = None):
        super().__init__(chrome_debug_port, ai_client)
        # self.ai_client is already set by parent constructor if ai_client is passed.

    async def connect(self) -> Browser: # type: ignore
        # This method can be simplified if the base class handles connection adequately
        # or kept if specific logic for FixedAmazonExtractor is needed during connection.
        # For now, assuming base class connection logic is sufficient or this override is intended.
        log.info(f"Connecting to Chrome browser on debug port {self.chrome_debug_port} (FixedAmazonExtractor)")
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.connect_over_cdp(f"http://localhost:{self.chrome_debug_port}")
            log.info(f"Successfully connected to Chrome on port {self.chrome_debug_port} (FixedAmazonExtractor)")

            all_pages = self.browser.contexts[0].pages if self.browser.contexts and len(self.browser.contexts) > 0 else []
            if all_pages:
                log.info(f"Found {len(all_pages)} existing pages (FixedAmazonExtractor)")
                test_page = all_pages[0]
                log.info(f"Using existing page: {test_page.url} (FixedAmazonExtractor)")
                await test_page.bring_to_front()
            else:
                log.info("No existing pages found. Creating new page (FixedAmazonExtractor)")
                page = await self.browser.new_page()
                await page.goto("about:blank", timeout=10000)
                # The base AmazonExtractor is designed to keep pages open.
                # If a new page is created here just for a check, it might be closed or managed differently.
                # The original base class logic handles page creation/reuse within extract_data.
            return self.browser
        except Exception as e:
            log.error(f"Failed to connect to Chrome on port {self.chrome_debug_port} (FixedAmazonExtractor): {e}")
            log.error("Ensure Chrome is running with --remote-debugging-port=9222 and a dedicated --user-data-dir for persistence.")
            raise

    def _overlap_score(self, title_a: str, title_b: str) -> float:
        """Calculate word overlap score between two titles"""
        a = set(re.sub(r'[^\w\s]', ' ', title_a.lower()).split())
        b = set(re.sub(r'[^\w\s]', ' ', title_b.lower()).split())
        return len(a & b) / max(1, len(a))

    async def search_by_title_using_search_bar(self, title: str) -> Dict[str, Any]:
        """Search Amazon by title using search bar interaction (not URL building)"""
        if not self.browser or not self.browser.is_connected():
            await self.connect()

        log.info(f"Searching Amazon by title using search bar: '{title}'")
        
        # Get or create a page to work with
        all_pages = self.browser.contexts[0].pages if self.browser.contexts and len(self.browser.contexts) > 0 else []
        if all_pages:
            page = all_pages[0]
            await page.bring_to_front()
        else:
            page = await self.browser.new_page()
        
        try:
            # Navigate to Amazon UK and search by typing title into search bar
            log.info(f"Navigating to Amazon UK to search for title: {title}")
            await page.goto("https://www.amazon.co.uk", timeout=60000)
            
            # Type title into search box and press Enter
            await page.fill("input#twotabsearchtextbox", title, timeout=5000)
            await page.press("input#twotabsearchtextbox", "Enter")
            
            # Wait for search results
            await page.wait_for_selector("div.s-search-results", timeout=15000)
            
            # Parse search results - extract first few results with improved element selection
            potential_asins_info = []
            
            # Try multiple selectors for search result elements
            search_result_elements = []
            search_selectors = [
                "div.s-search-results > div[data-asin]",
                "div[data-component-type='s-search-result']",
                "div[data-asin]:not([data-asin=''])",
                "[cel_widget_id*='MAIN-SEARCH_RESULTS'] div[data-asin]"
            ]
            
            for selector in search_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        search_result_elements = elements
                        log.info(f"Title search found {len(elements)} elements using selector: {selector}")
                        break
                except Exception as e:
                    log.debug(f"Title search selector '{selector}' failed: {e}")
                    continue
            
            for element in search_result_elements[:10]:  # More results for title search
                asin = await element.get_attribute("data-asin")
                if asin and len(asin) == 10:  # Valid ASIN format
                    # Use improved title extraction
                    result_title = await self._extract_title_from_element(element, asin)
                    
                    potential_asins_info.append({
                        "asin": asin,
                        "title": result_title
                    })
            
            # Create search_results_data in expected format
            if potential_asins_info:
                search_results_data = {
                    "results": potential_asins_info,
                    "search_method": "title_search_bar_interaction"
                }
                log.info(f"Title search found {len(potential_asins_info)} results for '{title}'")
            else:
                search_results_data = {"error": f"No valid ASINs found for title '{title}'"}
                log.warning(f"No valid ASINs found for title '{title}'")
                
        except Exception as search_error:
            log.error(f"Error during title search for '{title}': {search_error}")
            search_results_data = {"error": f"Search error for title '{title}': {str(search_error)}"}
            
        return search_results_data

    async def _extract_title_from_element(self, element, asin: str) -> str:
        """Extract title from search result element using multiple fallback selectors"""
        title_selectors = [
            "h2 a span.a-text-normal",
            "h2 a span",
            ".s-title-instructions-style span.a-text-normal",
            "span.a-size-medium.a-color-base.a-text-normal",
            "h2 span.a-size-base-plus",
            "h2 a",
            "h2",
            "[data-cy='title-recipe-title']",
            ".s-line-clamp-2 span",
            ".s-line-clamp-3 span",
            ".s-line-clamp-4 span",
            ".s-size-mini .s-link-style a span",
            ".s-size-mini .s-link-style span",
            "span[data-a-text-type='title']",
            "a.a-link-normal > span.a-text-normal",
            "a span[aria-label]",
            "a[href*='/dp/'] span",
            ".a-link-normal span"
        ]
        
        for selector in title_selectors:
            try:
                title_element = await element.query_selector(selector)
                if title_element:
                    title_text = await title_element.inner_text()
                    if title_text and title_text.strip() and title_text.strip() != "":
                        log.debug(f"ASIN {asin} title extracted using selector '{selector}': {title_text.strip()[:50]}...")
                        return title_text.strip()
            except Exception as e:
                log.debug(f"Selector '{selector}' failed for ASIN {asin}: {e}")
                continue
        
        # Fallback level 1: Try any element with "title" in class or data attributes
        try:
            title_containing_selectors = [
                "[class*='title']",
                "[data-cy*='title']",
                "[data-a-target*='title']",
                ".a-size-base-plus",
                ".a-size-medium"
            ]
            
            for fallback_selector in title_containing_selectors:
                fallback_element = await element.query_selector(fallback_selector)
                if fallback_element:
                    fallback_text = await fallback_element.inner_text()
                    if fallback_text and fallback_text.strip():
                        log.debug(f"ASIN {asin} title extracted using fallback selector '{fallback_selector}': {fallback_text.strip()[:50]}...")
                        return fallback_text.strip()
        except Exception as e:
            log.debug(f"Fallback title extraction with selectors failed for ASIN {asin}: {e}")
        
        # Fallback level 2: Try to get any text content from h2 or other common title containers
        try:
            fallback_element = await element.query_selector("h2, .a-text-normal, .a-link-normal")
            if fallback_element:
                fallback_text = await fallback_element.inner_text()
                if fallback_text and fallback_text.strip():
                    log.debug(f"ASIN {asin} title extracted using last-resort fallback: {fallback_text.strip()[:50]}...")
                    return fallback_text.strip()
        except Exception as e:
            log.debug(f"Last-resort fallback title extraction failed for ASIN {asin}: {e}")
        
        log.warning(f"Could not extract title for ASIN {asin} using any selector")
        return "Unknown Title"

    async def search_by_ean_and_extract_data(self, ean: str, supplier_product_title: str) -> Dict[str, Any]:
        """
        Search Amazon by EAN and extract data for the best match.
        Uses AI for disambiguation if multiple results are found.
        Uses robust search result selection and sponsored ad detection.
        """
        if not self.browser or not self.browser.is_connected():
            await self.connect()

        log.info(f"Searching Amazon by EAN: {ean} for supplier product: '{supplier_product_title}' (FixedAmazonExtractor)")
        
        # Get or create a page to work with
        all_pages = self.browser.contexts[0].pages if self.browser.contexts and len(self.browser.contexts) > 0 else []
        if all_pages:
            page = all_pages[0]
            await page.bring_to_front()
        else:
            page = await self.browser.new_page()
        
        try:
            # Navigate to Amazon UK and search by typing EAN into search bar
            log.info(f"Navigating to Amazon UK to search for EAN: {ean}")
            await page.goto("https://www.amazon.co.uk", timeout=60000)
            
            # Type EAN into search box and press Enter
            await page.fill("input#twotabsearchtextbox", ean, timeout=5000)
            await page.press("input#twotabsearchtextbox", "Enter")
            
            # Wait for search results with enhanced multiple selector approach - REQUIREMENT 1
            log.info(f"Waiting for search results page to load for EAN {ean}...")
            search_result_containers_found = False
            container_selectors = [
                "div.s-search-results", 
                "div[data-component-type='s-search-results']", 
                "[data-cy='search-result-list']",
                "div.s-result-list",
                "div.s-main-slot"
            ]
            
            # Wait for any of the container selectors with a longer timeout
            for container_selector in container_selectors:
                try:
                    await page.wait_for_selector(container_selector, timeout=20000)
                    log.info(f"Found search results container with selector: {container_selector}")
                    search_result_containers_found = True
                    break
                except Exception as container_error:
                    log.debug(f"Container selector '{container_selector}' not found: {container_error}")
            
            if not search_result_containers_found:
                # Check for a direct product page (Amazon sometimes redirects to product page for exact EAN match)
                try:
                    direct_product_selectors = ["div#dp-container", "div#ppd", "div#centerCol"]
                    for direct_selector in direct_product_selectors:
                        if await page.query_selector(direct_selector):
                            log.info(f"EAN search redirected to a direct product page (selector: {direct_selector})")
                            # Extract ASIN from URL
                            current_url = page.url
                            asin_match = re.search(r"/dp/([A-Z0-9]{10})", current_url)
                            if asin_match:
                                direct_asin = asin_match.group(1)
                                log.info(f"Found direct product match for EAN {ean}: ASIN {direct_asin}")
                                # Return the data directly
                                return await super().extract_data(direct_asin)
                            break
                except Exception as direct_page_error:
                    log.debug(f"Error checking for direct product page: {direct_page_error}")
                
                log.warning(f"No search results containers found for EAN {ean}")
                return {"error": f"No search results found for EAN {ean}"}
            
            # Add a brief stabilization wait to ensure all elements are loaded
            await asyncio.sleep(2)
                        
            # REQUIREMENT 2: Search Result Element (Tile) Selection with improved selectors 
            organic_results = []
            search_result_elements = []
            
            # Enhanced list of selectors for finding individual product tiles
            search_selectors = [
                # Try to exclude obvious ad containers at the selection stage
                "div[data-asin]:not([data-asin='']):not(.AdHolder):not([class*='s-widget-sponsored-product'])",
                "div.s-result-item[data-asin]:not([data-asin=''])",
                "div[data-component-type='s-search-result'][data-asin]:not([data-asin=''])",
                "div.s-search-results > div[data-asin]",
                "div[data-cel-widget*='search_result_'][data-asin]:not([data-asin=''])",
                "[cel_widget_id*='MAIN-SEARCH_RESULTS'] div[data-asin]",
                "div[data-uuid][data-asin]:not([data-asin=''])"
            ]
            
            for selector in search_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        search_result_elements = elements
                        log.info(f"Found {len(elements)} search result elements using selector: {selector}")
                        break
                except Exception as e:
                    log.debug(f"Search selector '{selector}' failed: {e}")
                    continue
            
            if not search_result_elements:
                log.warning(f"No search result elements found for EAN {ean}")
                return {"error": "no_elements_found"}
            else:
                log.info(f"Processing {len(search_result_elements)} search result elements for EAN {ean}")
                
                # Look at more elements (up to 15) to find organic results
                for i, element in enumerate(search_result_elements[:15]):
                    asin = await element.get_attribute("data-asin")
                    if not asin or len(asin) != 10:  # Skip if no valid ASIN
                        log.debug(f"Element {i+1}: Invalid or missing ASIN: {asin}")
                        continue
                        
                    log.debug(f"Processing element {i+1}: ASIN {asin}")
                    
                    # --- REQUIREMENT 4: Enhanced sponsored detection logic (Iteration 3) ---
                    is_sponsored = False
                    sponsor_detection_reason = ""
                    
                    # Add debug logging for first few elements
                    if i < 3:
                        try:
                            element_html_debug = await element.evaluate("element => element.outerHTML")
                            log.debug(f"ASIN {asin} HTML structure sample: {element_html_debug[:600]}...")
                        except Exception as html_error:
                            log.debug(f"Could not get HTML for element debug: {html_error}")
                    
                    # Check 1: Explicit "Sponsored" text directly visible within the element
                    try:
                        sponsored_badge_locator = element.locator("span:visible", has_text=re.compile(r"^\s*Sponsored\s*$", re.IGNORECASE))
                        if await sponsored_badge_locator.count() > 0: 
                            is_sponsored = True
                            sponsor_detection_reason = "visible 'Sponsored' text badge"
                    except Exception as e_badge:
                        log.debug(f"Error checking sponsored badge for ASIN {asin}: {e_badge}")

                    # Check 2: Aria-label on the element or a significant child
                    if not is_sponsored:
                        try:
                            if await element.locator('[aria-label="Sponsored"]:visible').count() > 0:
                                is_sponsored = True
                                sponsor_detection_reason = "aria-label='Sponsored'"
                        except Exception as e_aria:
                            log.debug(f"Error checking aria-label for ASIN {asin}: {e_aria}")
                    
                    # Check 3: Data attributes on the element itself (tile)
                    if not is_sponsored:
                        try:
                            is_sponsored = await element.evaluate("""el => {
                                if (el.getAttribute('data-component-type') === 'sp-sponsored-result') return true;
                                if (el.getAttribute('data-ad-marker') === 'true') return true;
                                if (el.querySelector('[data-component-type="sp-sponsored-result"]')) return true;
                                if (el.querySelector('[data-cel-widget*="advertising"]')) return true;
                                if (el.querySelector('[data-ad-id]')) return true;
                                return false;
                            }""")
                            if is_sponsored:
                                sponsor_detection_reason = "data attributes indicating sponsored content"
                        except Exception as e_data_attr:
                            log.debug(f"Error checking data-attributes for ASIN {asin}: {e_data_attr}")

                    # Check 4: Presence of known ad-specific classes on the main element (tile)
                    if not is_sponsored:
                        try:
                            element_classes = await element.get_attribute("class") or ""
                            known_ad_classes = [
                                "AdHolder", 
                                "s-widget-sponsored-product", 
                                "sponsored-results-padding",
                                "s-result-item-sponsored-popup",
                                "puis-sponsored-container-component",
                                "ad-feedback"
                            ] 
                            for ad_class in known_ad_classes:
                                if ad_class in element_classes:
                                    is_sponsored = True
                                    sponsor_detection_reason = f"ad-specific class: '{ad_class}'"
                                    break
                        except Exception as e_class:
                            log.debug(f"Error checking tile classes for ASIN {asin}: {e_class}")

                    # Check 5: Text content contains typical ad indicators
                    if not is_sponsored:
                        try:
                            ad_indicators_locator = element.locator("text=/sponsored|advertisement|ad for/i")
                            if await ad_indicators_locator.count() > 0:
                                is_sponsored = True
                                sponsor_detection_reason = "text containing ad indicators"
                        except Exception as e_text:
                            log.debug(f"Error checking text for ad indicators for ASIN {asin}: {e_text}")

                    if is_sponsored:
                        log.info(f"Skipping sponsored result: ASIN {asin} (detected by {sponsor_detection_reason})")
                        continue
                    
                    # Process organic result with improved title extraction from helper method
                    title = await self._extract_title_from_element(element, asin)
                    
                    organic_results.append({
                        "asin": asin,
                        "title": title
                    })
                    log.info(f"Found organic result: ASIN {asin} - {title[:60]}...")
                    
                    # Break after finding a reasonable number of organic results to improve performance
                    if len(organic_results) >= 5:
                        log.info(f"Found {len(organic_results)} organic results, stopping search to improve performance.")
                        break
            
                # Check if we have any organic results
                if not organic_results:
                    log.warning(f"EAN {ean} returned no organic results - skipping")
                    search_results_data = {"error": "no_organic_results"}
                else:
                    # Apply word overlap scoring for multiple results
                    if len(organic_results) == 1:
                        chosen_result = organic_results[0]
                        log.info(f"Single organic result found for EAN {ean}: ASIN {chosen_result['asin']}")
                    else:
                        log.info(f"Multiple organic results ({len(organic_results)}) found for EAN {ean}. Applying word overlap scoring.")

                        # Score each result against supplier title
                        scored_results = []
                        for result in organic_results:
                            score = self._overlap_score(supplier_product_title, result['title'])
                            scored_results.append((result, score))
                            log.info(f"ASIN {result['asin']}: {score:.2f} overlap score with '{result['title'][:50]}...'")
                        
                        # Find results that meet the 0.25 threshold
                        good_matches = [(result, score) for result, score in scored_results if score >= 0.25]
                        
                        if good_matches:
                            # Pick the highest scoring result
                            chosen_result, best_score = max(good_matches, key=lambda x: x[1])
                            log.info(f"Multiple matches - chose ASIN {chosen_result['asin']} ({best_score:.2f} word-overlap)")
                        else:
                            # Edge case fallback: use top organic result with low confidence
                            chosen_result = organic_results[0]
                            chosen_result['match_confidence'] = 'low'
                            log.warning(f"No result met 0.25 threshold. Using top organic result ASIN {chosen_result['asin']} with low confidence.")
                    
                    search_results_data = {
                        "results": [chosen_result],  # Single chosen result
                        "search_method": "ean_search_bar_with_verification"
                    }
                    log.info(f"EAN search selected ASIN {chosen_result['asin']} for {ean}")
                
        except Exception as search_error:
            log.error(f"Error during EAN search for {ean}: {search_error}")
            search_results_data = {"error": f"Search error for EAN {ean}: {str(search_error)}"}

        if "error" in search_results_data or not search_results_data.get("results"):
            log.warning(f"No Amazon results or error for EAN '{ean}'. Details: {search_results_data.get('error', 'No results list')}")
            return {"error": f"No results for EAN {ean} or search error"}

        potential_asins_info = search_results_data["results"]
        chosen_asin_data = None

        if len(potential_asins_info) == 1:
            chosen_asin_data = potential_asins_info[0]
            log.info(f"Single ASIN {chosen_asin_data.get('asin')} found for EAN {ean}.")
        elif len(potential_asins_info) > 1:
            log.info(f"Multiple ASINs ({len(potential_asins_info)}) found for EAN {ean}. Prioritizing by title similarity to '{supplier_product_title}'.")
            # The results from search_by_title are already sorted by similarity to the query (EAN in this case).
            # We might want to re-score against the supplier_product_title if EAN search yields multiple items.
            # For now, let's assume the top result from EAN search is most relevant, or use AI if available.
            
            # Simple approach: take the first result from EAN search if no AI.
            chosen_asin_data = potential_asins_info[0] 
            log.info(f"Taking first result from EAN search: ASIN {chosen_asin_data.get('asin')}")

            if self.ai_client:
                log.info(f"Attempting AI disambiguation for EAN {ean} against supplier title '{supplier_product_title}'.")
                prompt = (
                    f"The EAN '{ean}' (from supplier product '{supplier_product_title}') "
                    f"returned multiple products on Amazon. Which of the following Amazon products is the most likely match to the supplier product title?\n"
                )
                for i, item in enumerate(potential_asins_info[:3]): # Limit to top 3 for AI prompt
                    prompt += f"{i+1}. ASIN: {item.get('asin')}, Title: {item.get('title')}\n"
                prompt += "Respond with the ASIN of the best match, or 'NONE' if no good match."
                
                try:
                    # Ensure ai_client is not None before calling create
                    if self.ai_client:
                        chat_completion = await asyncio.to_thread(
                            self.ai_client.chat.completions.create, # type: ignore
                            messages=[{"role": "user", "content": prompt}],
                            model=OPENAI_MODEL_NAME,
                        )
                        ai_response = chat_completion.choices[0].message.content.strip() # type: ignore
                        log.info(f"AI response for EAN {ean} disambiguation: {ai_response}")
                        
                        # Find the item that matches the AI's chosen ASIN
                        matched_item_by_ai = next((item for item in potential_asins_info if item.get('asin') == ai_response), None)
                        if matched_item_by_ai:
                            chosen_asin_data = matched_item_by_ai
                            log.info(f"AI selected ASIN {chosen_asin_data.get('asin')} for EAN {ean}.")
                        elif ai_response != "NONE":
                             log.warning(f"AI suggested ASIN {ai_response} not in search results. Using first result.")
                        else: # AI responded "NONE"
                            log.warning(f"AI could not confidently match EAN {ean}. Using first result.")
                    else:
                        log.warning("AI client not available for EAN disambiguation. Using first result.")
                except Exception as ai_err:
                    log.error(f"AI disambiguation failed for EAN {ean}: {ai_err}")
        
        if not chosen_asin_data or not chosen_asin_data.get("asin"):
            log.warning(f"No suitable ASIN found for EAN {ean} after search and disambiguation.")
            return {"error": f"No suitable ASIN for EAN {ean}"}

        chosen_asin = chosen_asin_data.get("asin")
        log.info(f"Proceeding with ASIN: {chosen_asin} for EAN: {ean}")
        
        # Extract detailed data for the chosen ASIN using the base class method
        product_data = await super().extract_data(chosen_asin) # type: ignore

        # The base AmazonExtractor's extract_data method should now attempt to get 'ean_on_page'
        # No need for redundant EAN extraction here if the base class handles it.
        if "error" not in product_data and product_data.get("title"):
            log.info(f"Successfully extracted data for ASIN {chosen_asin} (EAN on page: {product_data.get('ean_on_page', 'N/A')})")
        
        # Wait for extensions to stabilize if needed (already in base extract_data)
        # await asyncio.sleep(EXTENSION_DATA_WAIT) # This wait is in the base class's extract_data
        return product_data


    async def extract_data(self, asin: str) -> Dict[str, Any]:
        """
        Extract data for an Amazon product by ASIN.
        This implementation reuses existing pages to ensure extensions work properly.
        The base class method is called, which should handle EAN extraction.
        """
        # This method primarily relies on the superclass's extract_data.
        # The FixedAmazonExtractor's role is more about specialized search (like by EAN)
        # and ensuring the correct browser context is used.
        if not self.browser or not self.browser.is_connected():
            await self.connect() # Ensure connection

        # Call the parent's extract_data method
        result = await super().extract_data(asin) # type: ignore

        # The base class's extract_data should now be responsible for finding 'ean_on_page'.
        # Any additional EAN logic specific to FixedAmazonExtractor could go here if needed,
        # but it's better if the base class is comprehensive.
        
        # The stabilization wait is also part of the base class's extract_data
        # log.info(f"Waiting {EXTENSION_DATA_WAIT}s for extensions to stabilize (FixedAmazonExtractor.extract_data)...")
        # await asyncio.sleep(EXTENSION_DATA_WAIT) # This is in the base class
        return result


class PassiveExtractionWorkflow:
    def __init__(self, chrome_debug_port: int = 9222, ai_client: Optional[OpenAI] = None, max_cache_age_hours: int = 336, min_price: float = 0.1, headless: bool = True, linking_map_batch_size: int = 40, financial_report_batch_size: int = 50, force_ai_scraping: bool = False, selective_cache_clear: bool = False):
        from pathlib import Path
        self.state_path = Path(OUTPUT_DIR) / f"passive_extraction_state_{datetime.now().strftime('%Y%m%d')}.json"
        self.chrome_debug_port = chrome_debug_port
        self.ai_client = ai_client
        self.max_cache_age_hours = max_cache_age_hours
        self.min_price = min_price
        self.headless = headless
        self.log = logging.getLogger(__name__)
        self.amazon_extractor = None
        self.supplier_scraper = None
        self.linking_map_writer = LinkingMapWriter()  # New array-format writer
        self.enable_quick_triage = False  # Default to False, can be enabled via CLI flag
        self.last_processed_index = 0  # Initialize index tracker for resume feature
        self._processed_count = 0  # CRITICAL FIX: Track processed products for periodic saves
        self.linking_map_batch_size = linking_map_batch_size  # Configurable batch size for linking map saves
        self._linking_map_buffer = []  # Buffer for batch saving in new array format
        self.financial_report_batch_size = financial_report_batch_size  # Configurable batch size for financial reports
        self.force_ai_scraping = force_ai_scraping  # Force AI category selection
        self.selective_cache_clear = selective_cache_clear  # Use selective cache clearing
        # OLD: self.linking_map = self._load_linking_map() - removed in favor of array format buffer
        self.history = self._load_history()
        
        # PHASE 4 FIX: Product cache periodic save support
        self._current_extracted_products = []  # Track current extraction products
        self._current_supplier_name = None     # Track current supplier for cache path
        self._current_supplier_cache_path = None  # Track current supplier cache file path
        
        # REMOVED: Fallback OpenAI client initialization using module-level OPENAI_API_KEY.
        # The ai_client should be passed in by the caller (e.g., MainOrchestrator)
        # after loading the configuration, to ensure the correct API key is used.
        # if not self.ai_client and OPENAI_API_KEY:
        #     try:
        #         self.ai_client = OpenAI(api_key=OPENAI_API_KEY)
        #         log.info(f"OpenAI client initialized with model {OPENAI_MODEL_NAME}")
        #     except Exception as e:
        #         log.error(f"Failed to initialize OpenAI client: {e}")
        #         self.ai_client = None

        if self.ai_client:
            log.info(f"PassiveExtractionWorkflow initialized WITH an AI client.")
        else:
            log.info(f"PassiveExtractionWorkflow initialized WITHOUT an AI client. AI-dependent features will be skipped or use fallbacks.")

        self.extractor = FixedAmazonExtractor(
            chrome_debug_port=chrome_debug_port,
            ai_client=self.ai_client # Pass the ai_client (which could be None)
        )
        # MODIFIED: Use ConfigurableSupplierScraper
        self.web_scraper = ConfigurableSupplierScraper(
            ai_client=self.ai_client, # Pass the ai_client (which could be None)
            openai_model_name=OPENAI_MODEL_NAME, # OPENAI_MODEL_NAME is module-level, generally less critical than API key
            headless=self.headless
        )
        # Initialize FBA Calculator - Commented out
        # self.fba_calculator = FBACalculator()
        self.supplier_cache_dir = SUPPLIER_CACHE_DIR
        self.amazon_cache_dir = AMAZON_CACHE_DIR
        self.max_cache_age_seconds = max_cache_age_hours * 3600
        
        # Initialize linking map buffer (no longer loading old format)
        # Old linking map files will be ignored in favor of new array format in run output directories
        log.info(f"✅ Linking map buffer initialized - using new array format in run output directories")
        self.results_summary = {
            "total_supplier_products": 0,
            "products_analyzed_ean": 0,
            "products_analyzed_title": 0,
            "products_passed_triage": 0, # New counter
            "products_rejected_by_triage": 0, # New counter
            "products_previously_visited": 0, # Track resumed products
            "profitable_products": 0,
            "errors": 0,
            "products_processed_total": 0,
            "products_processed_per_category": {},
            "start_time": datetime.now().isoformat(),
        }
        
        # Set up state tracking
        self.state_path = None  # Will be set per supplier

    def _classify_url(self, url: str) -> str:
        """return 'friendly' | 'avoid' | 'neutral' based on patterns (priority order)."""
        path = url.lower()
        for kws in FBA_FRIENDLY_PATTERNS.values():
            if any(k in path for k in kws):
                return "friendly"
        for kws in FBA_AVOID_PATTERNS.values():
            if any(k in path for k in kws):
                return "avoid"
        return "neutral"

    # ──────────────────────── ③  Enhanced State tracking helpers ──────────────────────
    def _load_history(self):
        """Load comprehensive scraping history to prevent duplicate processing"""
        if self.state_path and Path(self.state_path).exists(): # MODIFIED HERE
            try:
                history = json.loads(Path(self.state_path).read_text()) # AND HERE for consistency
                # Ensure all required keys exist with backward compatibility
                default_history = {
                    "categories_scraped": [],
                    "products_processed": [],
                    "pages_visited": [],
                    "subpages_scraped": [],
                    "ai_suggested_categories": [],
                    "failed_categories": [],
                    "last_scrape_timestamp": None,
                    "scrape_sessions": [],
                    "category_performance": {},
                    "url_hash_cache": {},
                    "ai_decision_history": []  # New field for AI decisions
                }
                # Merge with defaults to handle missing keys
                for key, default_value in default_history.items():
                    if key not in history:
                        history[key] = default_value
                return history
            except (json.JSONDecodeError, Exception) as e:
                log.warning(f"Failed to load history, creating new: {e}")
                return self._get_default_history()
        return self._get_default_history()

    def _load_ai_memory(self, supplier_name: str) -> Dict[str, Any]:
        """
        🧠 Load AI memory from AI cache file to prevent re-suggesting same categories.

        Args:
            supplier_name: Name of the supplier

        Returns:
            Dictionary containing AI memory data
        """
        try:
            ai_cache_file = os.path.join(AI_CATEGORY_CACHE_DIR, f"{supplier_name.replace('.', '_')}_ai_category_cache.json")

            if os.path.exists(ai_cache_file):
                with open(ai_cache_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content or content == "{}":  # File is empty or just empty JSON
                        log.info(f"🧠 AI cache file is empty for {supplier_name} - starting fresh")
                        # Don't raise error - return empty memory but let the system continue
                        return {
                            "previously_suggested_urls": [],
                            "total_products_processed": 0,
                            "ai_history": [],
                            "total_ai_calls": 0,
                            "price_phase": "low"
                        }
                    ai_cache_data = json.loads(content)

                # Extract all previously suggested URLs from AI history
                previously_suggested_urls = set()
                total_products_processed = 0

                ai_history = ai_cache_data.get("ai_suggestion_history", [])
                for entry in ai_history:
                    ai_suggestions = entry.get("ai_suggestions", {})

                    # Collect all suggested URLs
                    top_urls = ai_suggestions.get("top_3_urls", [])
                    secondary_urls = ai_suggestions.get("secondary_urls", [])

                    previously_suggested_urls.update(top_urls)
                    previously_suggested_urls.update(secondary_urls)

                    # Track products processed
                    session_context = entry.get("session_context", {})
                    total_products_processed += session_context.get("total_products_processed", 0)

                log.info(f"🧠 AI Memory loaded: {len(previously_suggested_urls)} previously suggested URLs, {total_products_processed} products processed")
                log.debug(f"🧠 Previously suggested URLs: {list(previously_suggested_urls)}")

                return {
                    "previously_suggested_urls": list(previously_suggested_urls),
                    "total_products_processed": total_products_processed,
                    "ai_history": ai_history,
                    "total_ai_calls": ai_cache_data.get("total_ai_calls", 0),
                    "price_phase": ai_cache_data.get("price_phase", "low")  # Default to Phase 1
                }
            else:
                log.info(f"🧠 No AI cache file found for {supplier_name} - starting fresh")

        except Exception as e:
            log.error(f"Error loading AI memory for {supplier_name}: {e}")

        # Return default empty memory
        return {
            "previously_suggested_urls": [],
            "total_products_processed": 0,
            "ai_history": [],
            "total_ai_calls": 0,
            "price_phase": "low"  # Default to Phase 1
        }

    def _get_default_history(self):
        """Get default history structure"""
        return {
            "categories_scraped": [],
            "products_processed": [],
            "pages_visited": [],
            "subpages_scraped": [],
            "ai_suggested_categories": [],
            "failed_categories": [],
            "last_scrape_timestamp": None,
            "scrape_sessions": [],
            "category_performance": {},
            "url_hash_cache": {},
            "ai_decision_history": []  # New field for AI decisions
        }

    def _save_history(self, hist: dict):
        """Save comprehensive scraping history with atomic write"""
        if self.state_path:
            # Add current timestamp
            hist["last_scrape_timestamp"] = datetime.now().isoformat()
            
            # Use atomic write to prevent corruption
            # Ensure self.state_path is a Path object for .with_suffix and os.replace
            state_path_obj = Path(self.state_path)
            temp_path = state_path_obj.with_suffix(".tmp")
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(hist, f, indent=2, ensure_ascii=False)
                os.replace(temp_path, state_path_obj) # Use Path object here too
                log.debug(f"History saved with {len(hist.get('categories_scraped', []))} categories, {len(hist.get('pages_visited', []))} pages")
            except Exception as e:
                log.error(f"Failed to save history: {e}")
                if os.path.exists(temp_path): # os.path.exists is fine for string or Path
                    try:
                        os.remove(temp_path)
                    except:
                        pass

    def _record_ai_decision(self, hist: dict, ai_response: dict):
        """Record AI decision for future reference and learning"""
        hist.setdefault("ai_decision_history", []).append({
            "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
            "categories_suggested": ai_response["top_3_urls"],
            "skip_urls": ai_response["skip_urls"],
            "reasoning": ai_response.get("detailed_reasoning", {}),
            "progression_strategy": ai_response.get("progression_strategy", "unknown")
        })
        self._save_history(hist)

    def _is_url_previously_scraped(self, url: str, hist: dict) -> bool:
        """Check if URL has been previously scraped using multiple tracking methods"""
        if not url:
            return False
            
        # Direct URL check
        if url in hist.get("categories_scraped", []):
            return True
        if url in hist.get("pages_visited", []):
            return True
        if url in hist.get("subpages_scraped", []):
            return True
            
        # URL hash check for similar URLs (handles pagination, query params)
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        if url_hash in hist.get("url_hash_cache", {}):
            cached_url = hist["url_hash_cache"][url_hash]
            log.debug(f"URL hash match found: {url} matches previously scraped {cached_url}")
            return True
            
        # Normalize URL and check (remove trailing slashes, query params for base comparison)
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        
        for scraped_url in hist.get("categories_scraped", []) + hist.get("pages_visited", []):
            scraped_parsed = urlparse(scraped_url)
            scraped_base = f"{scraped_parsed.scheme}://{scraped_parsed.netloc}{scraped_parsed.path.rstrip('/')}"
            if base_url == scraped_base:
                log.debug(f"Base URL match: {url} matches {scraped_url}")
                return True
                
        return False

    def _add_url_to_history(self, url: str, hist: dict, url_type: str = "page"):
        """Add URL to appropriate history list and hash cache"""
        if not url:
            return
            
        # Add to appropriate list
        if url_type == "category":
            if url not in hist.get("categories_scraped", []):
                hist.setdefault("categories_scraped", []).append(url)
        elif url_type == "subpage":
            if url not in hist.get("subpages_scraped", []):
                hist.setdefault("subpages_scraped", []).append(url)
        else:  # default to pages_visited
            if url not in hist.get("pages_visited", []):
                hist.setdefault("pages_visited", []).append(url)
        
        # Add to hash cache
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        hist.setdefault("url_hash_cache", {})[url_hash] = url
        
        log.debug(f"Added {url_type} URL to history: {url}")

    def _record_category_performance(self, category_url: str, products_found: int, hist: dict):
        """Record performance metrics for categories to improve future AI suggestions"""
        hist.setdefault("category_performance", {})[category_url] = {
            "products_found": products_found,
            "last_scraped": datetime.now().isoformat(),
            "performance_score": min(products_found / 10.0, 1.0)  # Normalize to 0-1 scale
        }

    def _get_category_performance_summary(self, hist: dict) -> str:
        """Get summary of category performance for AI context"""
        performance = hist.get("category_performance", {})
        if not performance:
            return "No previous category performance data available."
        
        summary_lines = ["Previous category performance:"]
        sorted_categories = sorted(performance.items(), key=lambda x: x[1]["performance_score"], reverse=True)
        
        for url, metrics in sorted_categories[:5]:  # Top 5 performing categories
            summary_lines.append(f"- {url}: {metrics['products_found']} products (score: {metrics['performance_score']:.2f})")
        
        if len(sorted_categories) > 5:
            summary_lines.append(f"... and {len(sorted_categories) - 5} more categories")
            
        return "\n".join(summary_lines)

    # ──────────────────────── PHASE 3: SUBCATEGORY DEDUPLICATION ──────────────────────────
    def _detect_parent_child_urls(self, urls: List[str]) -> Dict[str, List[str]]:
        """
        Detect parent-child URL relationships to prevent double processing.
        Returns dict where keys are parent URLs and values are lists of child URLs.
        
        Example:
        Input: ['/health-beauty.html', '/health-beauty/cosmetics.html', '/gifts-toys.html']
        Output: {'/health-beauty.html': ['/health-beauty/cosmetics.html'], '/gifts-toys.html': []}
        """
        from urllib.parse import urlparse
        
        parent_child_map = {}
        processed_urls = set()
        
        # Sort URLs by path depth (shorter paths first)
        sorted_urls = sorted(urls, key=lambda url: urlparse(url).path.count('/'))
        
        for url in sorted_urls:
            if url in processed_urls:
                continue
                
            parsed_url = urlparse(url)
            url_path = parsed_url.path.rstrip('/')
            
            # Find potential child URLs
            child_urls = []
            for other_url in sorted_urls:
                if other_url == url or other_url in processed_urls:
                    continue
                    
                other_parsed = urlparse(other_url)
                other_path = other_parsed.path.rstrip('/')
                
                # Check if other_url is a child of current url
                # Child URL should start with parent path + '/'
                if other_path.startswith(url_path + '/') and other_path != url_path:
                    # Additional validation: ensure it's direct child, not grandchild
                    remaining_path = other_path[len(url_path + '/'):]
                    if '/' not in remaining_path or remaining_path.count('/') <= 1:
                        child_urls.append(other_url)
                        processed_urls.add(other_url)
            
            parent_child_map[url] = child_urls
            processed_urls.add(url)
            
        log.info(f"Parent-child URL analysis: {len(parent_child_map)} parent categories, "
                f"{sum(len(children) for children in parent_child_map.values())} child categories")
        
        return parent_child_map

    async def _filter_urls_by_subcategory_deduplication(self, category_urls: List[str]) -> List[str]:
        """
        Apply subcategory deduplication logic: only include subcategories if parent category has <2 products.
        
        This prevents double processing of URLs like:
        - /health-beauty.html AND /health-beauty/cosmetics.html
        - /gifts-toys.html AND /gifts-toys/toys-games.html
        """
        if not category_urls:
            return category_urls
            
        # Detect parent-child relationships
        parent_child_map = self._detect_parent_child_urls(category_urls)
        
        # Validate each parent category for product count
        filtered_urls = []
        validation_cache = {}  # Cache validation results to avoid duplicate checks
        
        for parent_url, child_urls in parent_child_map.items():
            # Check parent category product count (use cache if available)
            if parent_url not in validation_cache:
                validation_result = await self._validate_category_productivity(parent_url)
                validation_cache[parent_url] = validation_result
            else:
                validation_result = validation_cache[parent_url]
            
            parent_product_count = validation_result.get("product_count", 0)
            
            # CORE LOGIC: Apply subcategory deduplication rule
            if parent_product_count >= 2:
                # Parent has sufficient products - skip subcategories, use pagination only
                filtered_urls.append(parent_url)
                log.info(f"✅ PARENT CATEGORY SUFFICIENT: {parent_url} ({parent_product_count} products) "
                        f"- SKIPPING {len(child_urls)} subcategories: {child_urls}")
            else:
                # Parent has <2 products - include subcategories for more products
                filtered_urls.append(parent_url)
                filtered_urls.extend(child_urls)
                log.info(f"⚠️  PARENT CATEGORY INSUFFICIENT: {parent_url} ({parent_product_count} products) "
                        f"- INCLUDING {len(child_urls)} subcategories: {child_urls}")
        
        log.info(f"SUBCATEGORY DEDUPLICATION: Reduced {len(category_urls)} URLs to {len(filtered_urls)} "
                f"(eliminated {len(category_urls) - len(filtered_urls)} redundant subcategories)")
        
        return filtered_urls

    # ──────────────────────── ②  Enhanced AI method ──────────────────────────
    async def _get_ai_suggested_categories_enhanced(
        self,
        supplier_url: str,
        supplier_name: str,
        discovered_categories: list[dict],
        previous_categories: list[str] | None = None,
        processed_products: int | None = None,
    ) -> dict:
        """🧠 FBA-aware AI selection with UK business intelligence & enhanced memory."""
        prev_cats = previous_categories or []

        # 🧠 ENHANCED: Filter out previously suggested categories more thoroughly
        available_categories = []
        for c in discovered_categories:
            if (self._classify_url(c["url"]) == "friendly" and
                c["url"] not in prev_cats and
                not any(prev_url in c["url"] or c["url"] in prev_url for prev_url in prev_cats)):
                available_categories.append(c)

        # Limit to reasonable number for AI processing
        friendly = available_categories[:100]
        formatted = "\n".join(f'- {c["name"]}: {c["url"]}' for c in friendly)

        # 🧠 ENHANCED: Include comprehensive memory context with failure tracking
        memory_context = ""
        if prev_cats:
            memory_context = f"\n\n🧠 IMPORTANT - PREVIOUSLY SUGGESTED CATEGORIES (DO NOT REPEAT):\n"
            for i, prev_cat in enumerate(prev_cats[-10:], 1):  # Show last 10 to avoid token limit
                memory_context += f"{i}. {prev_cat}\n"
            memory_context += "\n⚠️ You MUST suggest DIFFERENT categories that have NOT been suggested before!"

        # Add failure tracking from AI memory
        ai_memory = self._load_ai_memory(supplier_name)
        failed_urls = []
        failed_errors = {}

        # Extract failed URLs from AI history
        for entry in ai_memory.get("ai_history", []):
            if isinstance(entry, dict) and "ai_suggestions" in entry:
                suggestions = entry["ai_suggestions"]
                if "failed_urls" in suggestions:
                    failed_urls.extend(suggestions["failed_urls"])
                if "failed_url_errors" in suggestions:
                    failed_errors.update(suggestions["failed_url_errors"])

        # Add failure context to prompt
        if failed_urls:
            memory_context += f"\n\n❌ FAILED CATEGORIES (DO NOT SUGGEST THESE):\n"
            for i, failed_url in enumerate(set(failed_urls[-15:]), 1):  # Show last 15 failures
                error_msg = failed_errors.get(failed_url, "Unknown error")
                memory_context += f"{i}. {failed_url} (Error: {error_msg})\n"
            memory_context += "\n⚠️ These URLs failed validation - DO NOT suggest them again!"
        prompt = f"""
AMAZON FBA UK CATEGORY ANALYSIS FOR: {supplier_name}

You are an expert Amazon FBA consultant specializing in UK marketplace product sourcing and category analysis.

DISCOVERED CATEGORIES FROM WEBSITE HOMEPAGE:
{formatted}

{memory_context}

PREVIOUSLY PROCESSED CATEGORIES: {prev_cats or "None"}
PREVIOUSLY PROCESSED PRODUCTS: {processed_products or "None"}

🚨 CRITICAL INSTRUCTIONS - READ CAREFULLY:
1. **YOU MUST ONLY SELECT URLs FROM THE "DISCOVERED CATEGORIES" LIST ABOVE**
2. **DO NOT INVENT OR CREATE NEW URLs - ONLY USE THE PROVIDED ONES**
3. **DO NOT SUGGEST URLs THAT ARE NOT IN THE DISCOVERED CATEGORIES LIST**
4. ONLY select URLs that appear to be PRODUCT LISTING PAGES, not search forms or filters
5. Avoid URLs containing: "search", "advanced", "filter", "sort", "login", "account"
6. Prioritize URLs with clear category names that suggest product listings
7. Avoid URLs that look like individual product pages (containing specific product names)

URL SELECTION RULES:
- **ONLY SELECT FROM THE DISCOVERED CATEGORIES LIST ABOVE**
- **DO NOT CREATE NEW URLs OR MODIFY EXISTING ONES**
- GOOD patterns from the list: URLs ending in category names like "/household.html", "/baby-kids.html"
- BAD patterns from the list: URLs containing "search", "advanced", "filter", "catalogsearch"

Based on your FBA expertise, select categories from the DISCOVERED CATEGORIES list that are most likely to contain profitable, scrapeable products for Amazon FBA UK.

⚠️ **IMPORTANT: ALL URLs in your response MUST come from the DISCOVERED CATEGORIES list above. Do not invent new URLs.**

Return a JSON object with EXACTLY these keys:
{{
    "top_3_urls": [list of 3 best PRODUCT LISTING category URLs],
    "secondary_urls": [list of 3-5 backup category URLs],
    "skip_urls": [list of category URLs to avoid - include search/filter pages],
    "detailed_reasoning": {{"category_name": "detailed reason for selection/skipping including URL pattern analysis"}},
    "progression_strategy": "description of your category selection strategy focusing on product listing identification",
    "url_pattern_confidence": {{"high_confidence": ["urls you're very confident contain products"], "medium_confidence": ["urls that might contain products"], "low_confidence": ["urls unlikely to contain products"]}}
}}

PRIORITIZE CATEGORIES LIKELY TO CONTAIN:
HIGH PRIORITY:
- Home & Kitchen products (high profit margins, consistent demand)
- Pet Supplies (growing market, good margins)
- Beauty & Personal Care (repeat purchases, brand loyalty)
- Sports & Outdoors (seasonal opportunities)
- Office & Stationery (business demand)
- DIY & Tools (practical demand)
- Baby & Nursery products (premium pricing potential)
- Toys & Games (consistent demand)
- Kids Books (coloring books, sticker books, activity books, picture books)

MEDIUM PRIORITY:
- Clearance/Value categories (pound lines, 50p & under, clearance, sale, discount)
- Crafts & Hobbies (creative supplies, art materials)
- Seasonal items (Christmas, Halloween, party supplies)
- Automotive accessories (small car accessories)

AVOID CATEGORIES WITH:
- Electronics (high competition, warranty issues)
- Clothing/Fashion (size/fit issues, returns)
- Medical/Pharmaceutical (regulatory restrictions)
- Food/Beverages (expiry dates, regulations)
- Large/bulky items (shipping costs, storage issues)
- High-value jewelry (authentication, insurance)
- Dangerous goods (batteries, flammables, restricted)
- Adult Books (novels, fiction, textbooks, academic books - AVOID these)
- Search/filter pages (no actual products)

IMPORTANT BOOK DISTINCTION:
- INCLUDE: Kids books, coloring books, sticker books, activity books, picture books
- EXCLUDE: Adult novels, fiction, textbooks, academic books, biographies

REASONING REQUIREMENTS:
For each selected URL, explain:
1. Why the URL pattern suggests it contains product listings
2. What type of products you expect to find
3. Why those products are suitable for FBA
4. Estimated profit potential (High/Medium/Low)

Return ONLY valid JSON, no additional text."""
        # ---------- AI CALL ----------
        # 🔧 FIXED: Use regular model since search-enabled model doesn't support json_object format
        model_to_use = "gpt-4o-mini"  # Regular model that supports json_object

        # Log API call details for debugging
        log.info(f"🤖 OpenAI API Call - Model: {model_to_use}, Max Tokens: 1200")
        log.info(f"🤖 Prompt Length: {len(prompt)} characters")
        log.debug(f"🤖 Full Prompt: {prompt[:500]}..." if len(prompt) > 500 else f"🤖 Full Prompt: {prompt}")

        raw = await asyncio.to_thread(
            self.ai_client.chat.completions.create,
            model=model_to_use,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=1200,  # Increased for better reasoning
        )

        # Log token usage
        if hasattr(raw, 'usage') and raw.usage:
            log.info(f"🤖 Token Usage - Input: {raw.usage.prompt_tokens}, Output: {raw.usage.completion_tokens}, Total: {raw.usage.total_tokens}")

        # Save detailed API call log
        self._save_api_call_log(prompt, raw, model_to_use, "category_suggestion")

        # ---------- STRICT VALIDATION ----------
        try:
            ai = json.loads(raw.choices[0].message.content.strip())
            # Fix: Add missing keys with default values instead of failing
            required = {"top_3_urls", "secondary_urls", "skip_urls"}
            if not required.issubset(ai):
                self.log.warning(f"AI JSON missing keys: {required - set(ai)} - adding defaults")
                # Add missing keys with defaults
                if "top_3_urls" not in ai:
                    ai["top_3_urls"] = [c["url"] for c in discovered_categories
                                      if self._classify_url(c["url"]) == "friendly"
                                      and c["url"] not in (previous_categories or [])][:3]
                if "secondary_urls" not in ai:
                    ai["secondary_urls"] = []
                if "skip_urls" not in ai:
                    ai["skip_urls"] = []
            
            # Ensure lists are actually lists
            for key in ["top_3_urls", "secondary_urls", "skip_urls"]:
                if not isinstance(ai[key], list):
                    self.log.warning(f"AI JSON '{key}' is not a list - fixing")
                    ai[key] = [ai[key]] if ai[key] else []
                    
        except Exception as e:
            self.log.error("AI JSON invalid → %s – falling back to heuristic list", e)
            friendly_urls = [c["url"] for c in discovered_categories
                             if self._classify_url(c["url"]) == "friendly"
                             and c["url"] not in (previous_categories or [])][:3]
            ai = {"top_3_urls": friendly_urls,
                  "secondary_urls": [],
                  "skip_urls": [],
                  "detailed_reasoning": {"fallback": "heuristic-friendly"},
                  "progression_strategy": "simple-first-3"}

        # hard filter avoid patterns
        ai["top_3_urls"] = [u for u in ai["top_3_urls"] if self._classify_url(u) != "avoid"]
        ai["skip_urls"]  = list(set(ai.get("skip_urls",[]) + [u for u in ai["top_3_urls"] if self._classify_url(u)=="avoid"]))
        return ai

    async def _validate_category_productivity(self, url: str) -> dict:
        """Check if category URL actually contains products (Solution 3)"""
        try:
            log.info(f"Validating category productivity for: {url}")

            # Quick scrape to count products on first page
            session = await self.web_scraper._get_session()
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    return {
                        "url": url,
                        "product_count": 0,
                        "is_productive": False,
                        "error": f"HTTP {response.status}"
                    }

                html_content = await response.text()

            # Use the same product detection logic as the scraper
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # Try configured selectors first
            product_elements = []
            try:
                supplier_config = self.web_scraper.get_supplier_config(url)
                if supplier_config and supplier_config.get("selectors", {}).get("product_container"):
                    product_selector = supplier_config["selectors"]["product_container"]
                    product_elements = soup.select(product_selector)
            except Exception as e:
                log.debug(f"Failed to use configured selectors for {url}: {e}")

            # Fallback to generic selectors if no configured ones work
            if not product_elements:
                generic_selectors = [
                    'div.product',
                    '.product-item',
                    '.product-container',
                    '[class*="product"]',
                    '.item'
                ]
                for selector in generic_selectors:
                    product_elements = soup.select(selector)
                    if product_elements:
                        break

            product_count = len(product_elements)
            is_productive = product_count >= 2  # Minimum 2 products required

            log.info(f"Category validation: {url} -> {product_count} products (productive: {is_productive})")

            return {
                "url": url,
                "product_count": product_count,
                "is_productive": is_productive,
                "validation_method": "product_count_check"
            }

        except Exception as e:
            log.warning(f"Category productivity validation failed for {url}: {e}")
            return {
                "url": url,
                "product_count": 0,
                "is_productive": False,
                "error": str(e)
            }

    def _optimize_category_urls(self, urls: list, price_range: str = "low") -> list:
        """Add optimization parameters to category URLs for better product retrieval"""
        optimized_urls = []

        for url in urls:
            # Base parameters for better product retrieval (generic, no price filtering)
            base_params = "product_list_limit=64&product_list_order=price&product_list_dir=asc"

            # Add parameters to URL
            if '?' in url:
                optimized_url = f"{url}&{base_params}"
            else:
                optimized_url = f"{url}?{base_params}"

            optimized_urls.append(optimized_url)
            log.info(f"Optimized URL (no price filtering): {url} -> {optimized_url}")

        return optimized_urls

    def _save_api_call_log(self, prompt: str, response, model: str, call_type: str):
        """Save detailed OpenAI API call logs for debugging and token tracking"""
        try:
            from pathlib import Path

            # Create API logs directory using proper path management (claude.md standards)
            from utils.path_manager import get_api_log_path
            log_file = get_api_log_path("openai")  # This creates the proper path

            # Create log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "call_type": call_type,
                "model": model,
                "prompt_length": len(prompt),
                "prompt": prompt,
                "response_content": response.choices[0].message.content if response.choices else "No response",
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if hasattr(response, 'usage') and response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if hasattr(response, 'usage') and response.usage else 0,
                    "total_tokens": response.usage.total_tokens if hasattr(response, 'usage') and response.usage else 0
                }
            }

            # Save to daily log file (already created by get_api_log_path)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

            log.info(f"💾 API call logged to {log_file}")

        except Exception as e:
            log.warning(f"Failed to save API call log: {e}")

    def _determine_price_phase(self, ai_memory: dict) -> str:
        """Determine current price phase based on AI memory"""
        # Check if Phase 2 has been initiated
        if ai_memory.get("price_phase") == "medium":
            return "medium"

        # Default to Phase 1 (low price range)
        return "low"

    def _store_phase_2_continuation_point(self, category_url: str, page_num: int, products_scraped: int):
        """Store pagination state for Phase 2 continuation"""
        try:
            from utils.path_manager import get_phase_continuation_path

            # Create continuation points file using path_manager (claude.md standards)
            continuation_file = get_phase_continuation_path()
            continuation_file.parent.mkdir(parents=True, exist_ok=True)

            # Load existing continuation points
            continuation_data = {}
            if continuation_file.exists():
                try:
                    with open(continuation_file, 'r', encoding='utf-8') as f:
                        continuation_data = json.load(f)
                except Exception as e:
                    log.warning(f"Could not load continuation points: {e}")

            # Store continuation point for this category
            base_url = category_url.split('?')[0]  # Remove any existing parameters
            continuation_data[base_url] = {
                "last_page": page_num,
                "products_scraped": products_scraped,
                "timestamp": datetime.now().isoformat(),
                "phase_1_complete": True
            }

            # Save updated continuation points
            with open(continuation_file, 'w', encoding='utf-8') as f:
                json.dump(continuation_data, f, indent=2, ensure_ascii=False)

            log.info(f"📍 Stored Phase 2 continuation point for {base_url}: page {page_num}, {products_scraped} products")

        except Exception as e:
            log.error(f"Failed to store Phase 2 continuation point: {e}")

    def _reset_ai_memory_for_phase_2(self, supplier_name: str, current_memory: dict):
        """Reset AI memory for Phase 2 while preserving Phase 1 history"""
        try:
            from pathlib import Path

            cache_file_path = Path(AI_CATEGORY_CACHE_DIR) / f"{supplier_name.replace('.', '_')}_ai_category_cache.json"

            if cache_file_path.exists():
                with open(cache_file_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                # Add Phase 2 marker to cache
                phase_2_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "phase_transition": "Phase 1 (£0-£10) complete, starting Phase 2 (£10-£20)",
                    "phase_1_summary": {
                        "total_categories_processed": len(current_memory.get("previously_suggested_urls", [])),
                        "total_products_processed": current_memory.get("total_products_processed", 0)
                    }
                }

                cache_data["ai_suggestion_history"].append(phase_2_entry)
                cache_data["last_updated"] = datetime.now().isoformat()
                cache_data["price_phase"] = "medium"  # Mark as Phase 2

                # Reset category suggestions for Phase 2 but keep history
                cache_data["phase_2_started"] = datetime.now().isoformat()

                with open(cache_file_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, indent=2, ensure_ascii=False)

                log.info(f"🔄 Phase 2 transition recorded in AI cache: {cache_file_path}")

        except Exception as e:
            log.error(f"Failed to reset AI memory for Phase 2: {e}")

    # COMMENTED OUT: Perplexity API integration for future use
    # async def _get_category_suggestions_with_perplexity(self, supplier_url: str) -> dict:
    #     """Use Perplexity API for enhanced category research"""
    #     try:
    #         import httpx
    #
    #         perplexity_api_key = "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"
    #
    #         prompt = f"""
    #         Research the website {supplier_url} and identify the best product categories
    #         for Amazon FBA sourcing. Focus on categories with:
    #         - Small, lightweight products
    #         - Good profit margins
    #         - Consistent demand
    #         - Low competition
    #
    #         Avoid categories with electronics, clothing, food, or dangerous goods.
    #         Return specific category URLs if possible.
    #         """
    #
    #         async with httpx.AsyncClient() as client:
    #             response = await client.post(
    #                 "https://api.perplexity.ai/chat/completions",
    #                 headers={
    #                     "Authorization": f"Bearer {perplexity_api_key}",
    #                     "Content-Type": "application/json"
    #                 },
    #                 json={
    #                     "model": "sonar-small-online",  # Lightweight, cost-effective
    #                     "messages": [{"role": "user", "content": prompt}],
    #                     "max_tokens": 500,
    #                     "temperature": 0.1
    #                 }
    #             )
    #
    #             if response.status_code == 200:
    #                 result = response.json()
    #                 return {"perplexity_research": result["choices"][0]["message"]["content"]}
    #             else:
    #                 log.warning(f"Perplexity API error: {response.status_code}")
    #                 return {"error": "Perplexity API failed"}
    #
    #     except Exception as e:
    #         log.warning(f"Perplexity integration failed: {e}")
    #         return {"error": str(e)}

    def _classify_category_type(self, url: str, name: str = "") -> str:
        """Classify category as friendly, avoid, or neutral for FBA"""
        url_lower = url.lower()
        name_lower = name.lower()
        combined_text = f"{url_lower} {name_lower}"

        # Check FBA friendly patterns
        for category_type, keywords in FBA_FRIENDLY_PATTERNS.items():
            if any(keyword in combined_text for keyword in keywords):
                return "friendly"

        # Check FBA avoid patterns
        for category_type, keywords in FBA_AVOID_PATTERNS.items():
            if any(keyword in combined_text for keyword in keywords):
                return "avoid"

        # Check neutral patterns
        for category_type, keywords in FBA_NEUTRAL_PATTERNS.items():
            if any(keyword in combined_text for keyword in keywords):
                return "neutral"

        return "unknown"

    def _save_products_to_cache(self, products: list, cache_file_path: str):
        """Save products to cache file for FBA calculator"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(cache_file_path), exist_ok=True)

            # Load existing cache if it exists
            existing_products = []
            if os.path.exists(cache_file_path):
                try:
                    with open(cache_file_path, 'r', encoding='utf-8') as f:
                        existing_products = json.load(f)
                except Exception as e:
                    log.warning(f"Could not load existing cache: {e}")

            # Merge with new products (avoid duplicates by URL)
            existing_urls = {p.get('url', '') for p in existing_products}
            new_products = [p for p in products if p.get('url', '') not in existing_urls]

            all_products = existing_products + new_products

            # Save to cache
            with open(cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(all_products, f, indent=2, ensure_ascii=False)

            log.info(f"Saved {len(all_products)} products to cache ({len(new_products)} new)")

        except Exception as e:
            log.error(f"Error saving products to cache: {e}")

    def _check_category_exhaustion_status(self, discovered_categories: list, processed_categories: list) -> dict:
        """Check how many categories of each type remain to be processed"""
        friendly_total = 0
        friendly_processed = 0
        neutral_total = 0
        neutral_processed = 0

        for category in discovered_categories:
            category_type = self._classify_category_type(category["url"], category.get("name", ""))
            if category_type == "friendly":
                friendly_total += 1
                if category["url"] in processed_categories:
                    friendly_processed += 1
            elif category_type == "neutral":
                neutral_total += 1
                if category["url"] in processed_categories:
                    neutral_processed += 1

        friendly_remaining = friendly_total - friendly_processed
        neutral_remaining = neutral_total - neutral_processed

        return {
            "friendly_total": friendly_total,
            "friendly_processed": friendly_processed,
            "friendly_remaining": friendly_remaining,
            "neutral_total": neutral_total,
            "neutral_processed": neutral_processed,
            "neutral_remaining": neutral_remaining,
            "should_continue": friendly_remaining > 0 or neutral_remaining > 0,
            "phase": "friendly" if friendly_remaining > 0 else ("neutral" if neutral_remaining > 0 else "complete")
        }

    # ──────────────────────── ④  Hierarchical selector ───────────────────────
    async def _hierarchical_category_selection(self, supplier_url, supplier_name):
        hist = self._load_history()

        # 🧠 FIXED: Load AI memory from AI cache file, not processing state
        ai_memory = self._load_ai_memory(supplier_name)

        # Use the new discover_categories method that returns dict format
        discovered_categories = await self.web_scraper.discover_categories(supplier_url)

        if not discovered_categories:
            log.warning(f"No categories discovered for {supplier_url}, using fallback")
            # Fallback to basic homepage categories
            basic_cats = await self.web_scraper.get_homepage_categories(supplier_url)
            discovered_categories = [{"name": url.split('/')[-1] or "category", "url": url} for url in basic_cats[:10]]

        # PHASE 3: SUBCATEGORY DEDUPLICATION - Apply before AI processing
        log.info(f"PHASE 3: Applying subcategory deduplication to {len(discovered_categories)} discovered categories")
        category_urls_only = [cat["url"] for cat in discovered_categories]
        filtered_category_urls = await self._filter_urls_by_subcategory_deduplication(category_urls_only)
        
        # Rebuild discovered_categories with filtered URLs
        filtered_discovered_categories = []
        for cat in discovered_categories:
            if cat["url"] in filtered_category_urls:
                filtered_discovered_categories.append(cat)
        
        # Update discovered_categories with filtered results
        original_count = len(discovered_categories)
        discovered_categories = filtered_discovered_categories
        eliminated_count = original_count - len(discovered_categories)
        
        log.info(f"PHASE 3 RESULT: Eliminated {eliminated_count} redundant subcategories, "
                f"proceeding with {len(discovered_categories)} optimized categories")

        # Check category exhaustion status using AI memory instead of processing state
        exhaustion_status = self._check_category_exhaustion_status(discovered_categories, ai_memory["previously_suggested_urls"])
        log.info(f"Category exhaustion status: {exhaustion_status}")

        # Determine current price phase based on AI memory
        current_price_phase = self._determine_price_phase(ai_memory)
        log.info(f"Current price phase: {current_price_phase}")

        if not exhaustion_status["should_continue"] and current_price_phase == "low":
            log.info("All categories processed in Phase 1 (£0-£10). Moving to Phase 2 (£10-£20)...")
            # Reset AI memory for Phase 2 but keep track of Phase 1 completion
            self._reset_ai_memory_for_phase_2(supplier_name, ai_memory)
            current_price_phase = "medium"
        elif not exhaustion_status["should_continue"] and current_price_phase == "medium":
            log.info("All FBA-friendly and neutral categories have been processed in both phases. Scraping complete.")
            return []

        # 🧠 FIXED: Pass AI memory instead of processing state history
        ai_suggestions = await self._get_ai_suggested_categories_enhanced(
            supplier_url, supplier_name, discovered_categories,
            previous_categories=ai_memory["previously_suggested_urls"],
            processed_products=ai_memory["total_products_processed"],
        )
        
        # Validate category productivity (Solution 3)
        log.info("Validating AI-suggested categories for product content...")
        validated_urls = []
        validation_results = []

        for url in ai_suggestions["top_3_urls"]:
            validation_result = await self._validate_category_productivity(url)
            validation_results.append(validation_result)

            if validation_result["is_productive"]:
                validated_urls.append(url)
                log.info(f"✅ Category validated: {url} ({validation_result['product_count']} products)")
            else:
                log.warning(f"❌ Category rejected: {url} ({validation_result['product_count']} products - below minimum of 2)")
                # Add to skip_urls in AI suggestions
                if url not in ai_suggestions.get("skip_urls", []):
                    ai_suggestions.setdefault("skip_urls", []).append(url)

        # Update AI suggestions with validated URLs
        ai_suggestions["top_3_urls"] = validated_urls
        ai_suggestions["validation_results"] = validation_results

        # If no validated URLs, try secondary URLs
        if not validated_urls and ai_suggestions.get("secondary_urls"):
            log.warning("No productive primary URLs found. Validating secondary URLs...")
            for url in ai_suggestions["secondary_urls"][:3]:  # Try up to 3 secondary URLs
                validation_result = await self._validate_category_productivity(url)
                if validation_result["is_productive"]:
                    validated_urls.append(url)
                    log.info(f"✅ Secondary category validated: {url}")
                    if len(validated_urls) >= 3:  # Limit to 3 URLs
                        break
            ai_suggestions["top_3_urls"] = validated_urls

        # Record AI decision in history
        self._record_ai_decision(hist, ai_suggestions)

        # Update history with validated categories only
        hist["categories_scraped"] += validated_urls
        self._save_history(hist)

        # Apply URL optimization to validated URLs FIRST
        if validated_urls:
            log.info("Applying URL optimization parameters...")
            optimized_urls = self._optimize_category_urls(validated_urls, price_range=current_price_phase)
            log.info(f"Optimized {len(validated_urls)} URLs with product display parameters for {current_price_phase} price phase")

            # Update AI suggestions with optimized URLs and failure tracking
            ai_suggestions["optimized_urls"] = optimized_urls
            ai_suggestions["failed_urls"] = [r["url"] for r in validation_results if not r["is_productive"]]
            ai_suggestions["failed_url_errors"] = {r["url"]: r.get("error", "Unknown") for r in validation_results if not r["is_productive"]}

            # 🔧 FIX: Replace top_3_urls with optimized URLs for caching
            ai_suggestions["top_3_urls"] = optimized_urls[:3]  # Keep only top 3 optimized URLs
            ai_suggestions["original_urls"] = validated_urls  # Store original URLs for reference
        else:
            log.warning("No validated URLs to optimize. Using fallback categories.")
            optimized_urls = []
            # Fallback to known working categories
            fallback_categories = [
                f"{supplier_url.rstrip('/')}/pound-lines.html",
                f"{supplier_url.rstrip('/')}/household.html",
                f"{supplier_url.rstrip('/')}/health-beauty.html"
            ]
            # Validate fallback categories
            fallback_validated = []
            for url in fallback_categories:
                validation_result = await self._validate_category_productivity(url)
                if validation_result["is_productive"]:
                    fallback_validated.append(url)

            if fallback_validated:
                optimized_urls = self._optimize_category_urls(fallback_validated, price_range="low")
                log.info(f"Using {len(optimized_urls)} validated fallback categories")
                # Update AI suggestions with fallback optimized URLs
                ai_suggestions["top_3_urls"] = optimized_urls[:3]
                ai_suggestions["optimized_urls"] = optimized_urls
                ai_suggestions["original_urls"] = fallback_validated
            else:
                log.error("No productive categories found. Cannot proceed with scraping.")
                return []

        # 🧠 FIXED: Save AI category suggestions to cache AFTER URL optimization
        try:
            Path(AI_CATEGORY_CACHE_DIR).mkdir(parents=True, exist_ok=True)
            cache_file_path = Path(AI_CATEGORY_CACHE_DIR) / f"{supplier_name.replace('.', '_')}_ai_category_cache.json"

            # Load existing cache data
            existing_cache = {}
            if cache_file_path.exists():
                try:
                    with open(cache_file_path, 'r', encoding='utf-8') as f:
                        existing_cache = json.load(f)
                except Exception as e:
                    log.warning(f"Could not load existing AI cache: {e}")

            # Create new entry for this AI suggestion session (now with optimized URLs)
            new_entry = {
                "timestamp": datetime.now().isoformat(),
                "session_context": {
                    "categories_discovered": len(discovered_categories),
                    "total_products_processed": ai_memory["total_products_processed"] if isinstance(ai_memory["total_products_processed"], int) else 0,
                    "previous_categories_count": len(ai_memory["previously_suggested_urls"]) if ai_memory["previously_suggested_urls"] else 0
                },
                "ai_suggestions": ai_suggestions,  # Now contains optimized URLs
                "validation_summary": {
                    "total_suggested": len(ai_suggestions.get("top_3_urls", [])),
                    "productive_categories": len(validated_urls),
                    "rejected_categories": len([r for r in validation_results if not r["is_productive"]])
                }
            }

            # Initialize or update cache structure
            if not existing_cache:
                cache_data = {
                    "supplier": supplier_name,
                    "url": supplier_url,
                    "created": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "total_ai_calls": 1,
                    "ai_suggestion_history": [new_entry]
                }
            else:
                # Append to existing history
                cache_data = existing_cache
                cache_data["last_updated"] = datetime.now().isoformat()
                cache_data["total_ai_calls"] = cache_data.get("total_ai_calls", 0) + 1

                # Ensure ai_suggestion_history exists
                if "ai_suggestion_history" not in cache_data:
                    cache_data["ai_suggestion_history"] = []

                cache_data["ai_suggestion_history"].append(new_entry)

            # Save updated cache
            with open(cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            log.info(f"🧠 Appended AI suggestion #{cache_data['total_ai_calls']} to cache with optimized URLs: {cache_file_path}")
            log.info(f"🧠 Total AI history entries: {len(cache_data['ai_suggestion_history'])}")

        except Exception as e:
            log.error(f"Failed to save AI category suggestions: {e}")

        pages = []

        # Process optimized URLs directly (no subpage discovery for now to keep it simple)
        pages = optimized_urls

        log.info(f"Hierarchical selection returned {len(pages)} optimized pages to scrape")
        log.info(f"URLs to scrape: {pages}")
        return pages

    async def _fetch_sitemap_urls(self, base_url: str) -> List[str]:
        """Fetch URLs from sitemap.xml or sitemap references in robots.txt"""
        sitemap_urls = []
        
        try:
            # Try direct sitemap.xml first
            sitemap_url = f"{base_url.rstrip('/')}/sitemap.xml"
            response = requests.get(sitemap_url, timeout=10)
            if response.status_code == 200:
                sitemap_urls.extend(self._parse_sitemap_xml(response.text))
                log.info(f"Found {len(sitemap_urls)} URLs in sitemap.xml")
                return sitemap_urls[:200]  # Limit to 200 URLs
        except Exception as e:
            log.debug(f"Direct sitemap.xml fetch failed: {e}")
        
        try:
            # Try robots.txt for sitemap references
            robots_url = f"{base_url.rstrip('/')}/robots.txt"
            response = requests.get(robots_url, timeout=10)
            if response.status_code == 200:
                for line in response.text.split('\n'):
                    if line.lower().startswith('sitemap:'):
                        sitemap_ref_url = line.split(':', 1)[1].strip()
                        try:
                            sitemap_response = requests.get(sitemap_ref_url, timeout=10)
                            if sitemap_response.status_code == 200:
                                sitemap_urls.extend(self._parse_sitemap_xml(sitemap_response.text))
                                if len(sitemap_urls) >= 200:
                                    break
                        except Exception as e:
                            log.debug(f"Failed to fetch sitemap from robots.txt reference {sitemap_ref_url}: {e}")
        except Exception as e:
            log.debug(f"Failed to fetch robots.txt: {e}")
        
        return sitemap_urls[:200]

    def _parse_sitemap_xml(self, xml_content: str) -> List[str]:
        """Parse sitemap XML and extract <loc> URLs"""
        urls = []
        try:
            # Handle XML namespaces
            xml_content = xml_content.replace('xmlns=', 'xmlnamespace=')
            root = ET.fromstring(xml_content)
            
            # Find all <loc> elements regardless of namespace
            for elem in root.iter():
                if elem.tag.endswith('loc') and elem.text:
                    urls.append(elem.text.strip())
                    
        except Exception as e:
            log.debug(f"XML parsing failed, trying regex fallback: {e}")
            # Fallback: regex extraction
            loc_pattern = re.compile(r'<loc>(.*?)</loc>', re.IGNORECASE)
            matches = loc_pattern.findall(xml_content)
            urls.extend(matches)
        
        return urls

    async def run(
        self,
        supplier_url: str = DEFAULT_SUPPLIER_URL,
        supplier_name: str = DEFAULT_SUPPLIER_NAME,
        max_products_to_process: int = 50,
        max_products_per_category: int = 0,
        max_analyzed_products: int = 0,
        cache_supplier_data: bool = True,
        force_config_reload: bool = False,
        debug_smoke: bool = False,
        resume_from_last: bool = True,
    ) -> List[Dict[str, Any]]:
        # Set current supplier name for linking map writer
        self._current_supplier_name = supplier_name
        
        profitable_results: List[Dict[str, Any]] = []
        processed_by_category: Dict[str, int] = defaultdict(int)
        total_processed = 0
        session_id = f"{supplier_name.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        log.info(f"Starting passive extraction workflow for supplier: {supplier_name} ({supplier_url})")
        log.info(f"Session ID: {session_id}")
        log.info(f"PRICE CRITERIA: Min Supplier Cost £{self.min_price}, Max Supplier Cost £{MAX_PRICE}")

        # Handle cache clearing if configured
        if hasattr(self, 'config') and self.config:
            clear_cache_setting = self.config.get("system", {}).get("clear_cache", False)
            if clear_cache_setting:
                log.warning("PassiveExtractionWorkflow: clear_cache=True, performing cache clear (Amazon cache preserved)")
                try:
                    # Simple cache clearing - delete supplier cache files directly
                    from pathlib import Path

                    cache_dirs = [
                        Path('OUTPUTS/cached_products'),
                        # Path('OUTPUTS/FBA_ANALYSIS/amazon_cache'),  # PRESERVED: Amazon cache disabled from clearing
                    ]

                    files_removed = 0
                    for cache_dir in cache_dirs:
                        if cache_dir.exists():
                            for cache_file in cache_dir.glob('*.json'):
                                try:
                                    cache_file.unlink()
                                    files_removed += 1
                                    log.info(f"Removed cache file: {cache_file}")
                                except Exception as e:
                                    log.warning(f"Could not remove {cache_file}: {e}")

                    log.info(f"Cache clearing completed. Removed {files_removed} files.")
                    force_config_reload = True  # Force fresh scraping

                except Exception as e:
                    log.error(f"Error during cache clearing: {e}")
                    # Continue anyway

            # CRITICAL FIX 2: Clear failed Keepa extractions if configured
            clear_failed_extractions_setting = self.config.get("system", {}).get("clear_failed_extractions", False)
            if clear_failed_extractions_setting:
                await self._clear_failed_keepa_extractions()

        # Enhanced state management using comprehensive state tracking
        try:
            from utils.enhanced_state_manager import EnhancedStateManager
        except ImportError:
            import sys
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            try:
                from utils.enhanced_state_manager import EnhancedStateManager
            except ImportError as e:
                log.error(f"Failed to import EnhancedStateManager even after path fix: {e}")
                log.error(f"Current sys.path: {sys.path}")
                log.error(f"Parent dir: {parent_dir}")
                log.error(f"File location: {os.path.abspath(__file__)}")
                raise
        self.state_manager = EnhancedStateManager(supplier_name)
        self.last_processed_index = 0

        # Load previous state if resume is enabled
        if resume_from_last:
            if self.state_manager.load_state():
                self.last_processed_index = self.state_manager.get_resume_index()
                log.info(f"Resuming from index {self.last_processed_index} - {self.state_manager.get_state_summary()}")
            else:
                log.info("Starting fresh analysis - no previous state found")

        supplier_cache_file = os.path.join(self.supplier_cache_dir, f"{supplier_name.replace('.', '_')}_products_cache.json")
        supplier_products = []
        
        # D3: Clear supplier cache if force_config_reload is True
        if force_config_reload and os.path.exists(supplier_cache_file):
            try:
                os.remove(supplier_cache_file)
                log.info(f"Cleared supplier cache: {supplier_cache_file}")
            except Exception as e:
                log.warning(f"Failed to clear supplier cache: {e}")
        
        if cache_supplier_data and os.path.exists(supplier_cache_file):
            cache_age = time.time() - os.path.getmtime(supplier_cache_file)
            if cache_age < self.max_cache_age_seconds:
                try:
                    with open(supplier_cache_file, 'r', encoding='utf-8') as f: supplier_products = json.load(f)
                    log.info(f"Loaded {len(supplier_products)} products from supplier cache ({cache_age/3600:.1f} hours old)")
                except Exception as e: log.error(f"Error loading supplier cache: {e}")
            else: log.info(f"Supplier cache too old ({cache_age/3600:.1f} hours). Fetching new data.")

        if not supplier_products:
            log.info(f"Extracting products from {supplier_name}...")
            supplier_products = await self._extract_supplier_products(
                supplier_url,
                supplier_name,
                max_products_per_category,
            )
            if cache_supplier_data and supplier_products:
                try:
                    with open(supplier_cache_file, 'w', encoding='utf-8') as f: 
                        json.dump(supplier_products, f, indent=2, ensure_ascii=False)
                    log.info(f"Cached {len(supplier_products)} supplier products")
                except Exception as e: 
                    log.error(f"Error caching supplier products: {e}")

        if not supplier_products:
            log.warning(f"No products extracted from {supplier_name}. Workflow cannot continue.")
            return []

        # D2: Stage-guard audit - Log stage completion
        log.info(f"STAGE-COMPLETE: supplier_scrape - {len(supplier_products)} records")
        if len(supplier_products) == 0:
            log.error(f"STAGE-GUARD ERROR: Supplier scrape returned 0 records unexpectedly for {supplier_name}")
            return []

        self.results_summary["total_supplier_products"] = len(supplier_products)
        log.info(f"Successfully got {len(supplier_products)} products from {supplier_name}")

        valid_supplier_products = [
            p for p in supplier_products
            if p.get("title") and isinstance(p.get("price"), (float, int)) and p.get("price", 0) > 0 and p.get("url")
        ]
        price_filtered_products = [
            p for p in valid_supplier_products
            if self.min_price <= p.get("price", 0) <= MAX_PRICE
        ]
        log.info(f"Found {len(valid_supplier_products)} valid supplier products, {len(price_filtered_products)} within price range [£{self.min_price}-£{MAX_PRICE}]")
        
        # D2: Stage-guard audit - Check price filtering stage
        log.info(f"STAGE-COMPLETE: price_filtering - {len(price_filtered_products)} records")
        if len(price_filtered_products) == 0 and len(valid_supplier_products) > 0:
            log.warning(f"STAGE-GUARD WARNING: Price filtering removed all {len(valid_supplier_products)} products. Consider adjusting price range [£{self.min_price}-£{MAX_PRICE}]")
        
        # Check if all cached products have been processed and need to fetch fresh data
        if resume_from_last and self.last_processed_index >= len(price_filtered_products):
            log.info("All cached products have been processed in previous runs. Fetching fresh supplier data...")
            # Force refresh supplier cache by fetching fresh data
            supplier_products = await self._extract_supplier_products(
                supplier_url,
                supplier_name,
                max_products_per_category,
            )
            if cache_supplier_data and supplier_products:
                try:
                    with open(supplier_cache_file, 'w', encoding='utf-8') as f: 
                        json.dump(supplier_products, f, indent=2, ensure_ascii=False)
                    log.info(f"Refreshed supplier cache with {len(supplier_products)} products")
                except Exception as e: 
                    log.error(f"Error caching refreshed supplier products: {e}")
            
            # Reset filtering with new data
            valid_supplier_products = [
                p for p in supplier_products
                if p.get("title") and isinstance(p.get("price"), (float, int)) and p.get("price", 0) > 0 and p.get("url")
            ]
            price_filtered_products = [
                p for p in valid_supplier_products
                if self.min_price <= p.get("price", 0) <= MAX_PRICE
            ]
            self.last_processed_index = 0  # Reset index since we have new data
            log.info(f"Refreshed data contains {len(price_filtered_products)} products in price range")
            
        # UNLIMITED AMAZON ANALYSIS: Process all products with smart rate limiting
        if max_products_to_process <= 0:
            log.info(f"UNLIMITED MODE: Processing ALL {len(price_filtered_products)} products starting from index {self.last_processed_index} with smart rate limiting.")
            products_to_analyze = price_filtered_products[self.last_processed_index:]
        else:
            log.info(f"LIMITED MODE: Processing up to {max_products_to_process} products starting from index {self.last_processed_index}.")
            products_to_analyze = price_filtered_products[self.last_processed_index:self.last_processed_index + max_products_to_process]

        # Initialize enhanced state management for this processing session
        import hashlib
        config_hash = hashlib.md5(str(getattr(self, 'config', {})).encode()).hexdigest()[:8]
        runtime_settings = {
            "max_products": max_products_to_process,
            "price_range": f"£{self.min_price}-£{MAX_PRICE}",
            "cache_enabled": cache_supplier_data,
            "resume_enabled": resume_from_last,
            "force_ai_scraping": getattr(self, 'force_ai_scraping', False),
            "ai_category_progression": getattr(self, 'force_ai_category_progression', False)
        }
        self.state_manager.start_processing(config_hash, runtime_settings)
        
        # Smart rate limiting configuration
        RATE_LIMIT_DELAY = 3.0  # 3 seconds between Amazon analyses
        BATCH_DELAY = 15.0      # 15 seconds every 25 products
        BATCH_SIZE = 25         # Process in batches of 25

        limit_reached = False
        for i, product_data in enumerate(products_to_analyze):
            # Update last_processed_index for next run (absolute index in price_filtered_products)
            current_absolute_index = self.last_processed_index + i

            category_key = product_data.get("source_category_url", "unknown")
            if max_analyzed_products > 0 and total_processed >= max_analyzed_products:
                log.info(
                    f"Reached max_analyzed_products={max_analyzed_products}. Halting further analysis."
                )
                limit_reached = True

                
                break

            processed_by_category[category_key] += 1
            total_processed += 1

            # Smart rate limiting: delay between each product
            if i > 0:  # Don't delay before the first product
                log.debug(f"Rate limiting: waiting {RATE_LIMIT_DELAY}s before processing product {i+1}")
                await asyncio.sleep(RATE_LIMIT_DELAY)

            # Batch delay: longer pause every BATCH_SIZE products
            if i > 0 and i % BATCH_SIZE == 0:
                log.info(f"Batch delay: processed {i} products, waiting {BATCH_DELAY}s before continuing...")
                await asyncio.sleep(BATCH_DELAY)
            # Update enhanced state with progress and performance metrics
            self.state_manager.update_processing_index(current_absolute_index + 1, len(products_to_analyze))
            
            # Enhanced progress logging with percentage (Fix #4)
            progress_percent = ((i + 1) / len(products_to_analyze)) * 100
            log.info(f"--- Processing supplier product {i+1}/{len(products_to_analyze)} ({progress_percent:.1f}%): '{product_data.get('title')}' (EAN: {product_data.get('ean', 'N/A')}) ---")
            
            # Check if this product has already been processed in previous runs (using linking map)
            supplier_ean = product_data.get("ean")
            supplier_url = product_data.get("url")
            if supplier_ean or supplier_url:
                # Create identifier for lookup in linking map
                supplier_identifier = f"EAN_{supplier_ean}" if supplier_ean else f"URL_{supplier_url}"

                # Find existing entry in buffer for detailed feedback (simple deduplication)
                existing_entry = next((link for link in self._linking_map_buffer
                                     if link.get("supplier_product_identifier") == supplier_identifier), None)

                if existing_entry:
                    # Extract details for enhanced message
                    supplier_title = existing_entry.get("supplier_title_snippet", "Unknown product")
                    amazon_asin = existing_entry.get("chosen_amazon_asin", "No ASIN found")
                    amazon_title = existing_entry.get("amazon_title_snippet", "No Amazon match")
                    match_method = existing_entry.get("match_method", "Unknown method")

                    # UNLIMITED MODE: Process previously visited products for comprehensive analysis
                    if max_products_to_process <= 0:
                        log.info(f"🔄 UNLIMITED MODE: Re-processing previously visited product: {supplier_title}")
                        log.info(f"  Product ID: {supplier_identifier}")
                        if amazon_asin != "No ASIN found":
                            log.info(f"  Previous Amazon match: {amazon_asin} - {amazon_title}")
                            log.info(f"  Match method: {match_method}")
                        log.info(f"  Proceeding with fresh analysis...")
                        # Track previously visited products but continue processing
                        self.results_summary["products_previously_visited"] += 1
                        # Continue to process this product instead of skipping
                    else:
                        # LIMITED MODE: Skip previously visited products
                        log.info(f"✓ Previously visited product: {supplier_title}")
                        log.info(f"  Product ID: {supplier_identifier}")
                        if amazon_asin != "No ASIN found":
                            log.info(f"  Previous Amazon match: {amazon_asin} - {amazon_title}")
                            log.info(f"  Match method: {match_method}")
                        else:
                            log.info(f"  Previous result: No Amazon match found")
                        log.info(f"  Skipping to next product...")

                        # Track previously visited products
                        self.results_summary["products_previously_visited"] += 1
                        continue
            
            amazon_product_data = None
            asin_to_check = None # Initialize asin_to_check
            supplier_ean = product_data.get("ean")

            if supplier_ean:
                log.info(f"Attempting Amazon search using EAN: {supplier_ean}")
                self.results_summary["products_analyzed_ean"] += 1
                
                amazon_product_data_from_ean_search = await self.extractor.search_by_ean_and_extract_data(supplier_ean, product_data["title"])
                
                potential_asin = None
                if amazon_product_data_from_ean_search: # Ensure the result dict exists
                    potential_asin = (amazon_product_data_from_ean_search.get("asin") or 
                                      amazon_product_data_from_ean_search.get("asin_from_details") or
                                      amazon_product_data_from_ean_search.get("asin_extracted_from_page") or
                                      amazon_product_data_from_ean_search.get("asin_queried"))

                if potential_asin:
                    asin_to_check = potential_asin
                    log.info(f"EAN search for '{supplier_ean}' identified ASIN: {asin_to_check}")

                    # Log a warning if there was an error during full data extraction for this ASIN, but proceed with the ASIN
                    if "error" in amazon_product_data_from_ean_search and amazon_product_data_from_ean_search["error"]:
                        log.warning(f"Partial data for ASIN {asin_to_check} (from EAN {supplier_ean}). Error during full extraction: {amazon_product_data_from_ean_search['error']}. Proceeding with available data.")
                    
                    cached_amazon_data = await self._get_cached_amazon_data_by_asin(asin_to_check, supplier_ean)
                    if cached_amazon_data:
                        amazon_product_data = cached_amazon_data
                        log.info(f"Using cached Amazon data for ASIN: {asin_to_check} (identified via EAN {supplier_ean})")
                    else:
                        amazon_product_data = amazon_product_data_from_ean_search # Use the (potentially partial) data
                        # Quick triage and caching logic (remains the same)
                        if self.enable_quick_triage and product_data.get("price"):
                            if self._passes_quick_triage(product_data.get("price"), amazon_product_data):
                                await self._cache_amazon_data(asin_to_check, amazon_product_data, product_data, "EAN_search_partial_ok")
                                log.info(f"Cached (potentially partial) Amazon data from EAN search for ASIN: {asin_to_check}")
                            else:
                                log.info(f"Skipping cache for ASIN {asin_to_check} - failed quick triage check")
                        else:
                            await self._cache_amazon_data(asin_to_check, amazon_product_data, product_data, "EAN_search_partial_ok")
                            log.info(f"Cached (potentially partial) Amazon data from EAN search for ASIN: {asin_to_check}")
                
                # This 'elif' handles cases where EAN search truly failed to identify any ASIN or had a critical error preventing ASIN identification.
                elif amazon_product_data_from_ean_search and "error" in amazon_product_data_from_ean_search: 
                    log.warning(f"EAN search for '{supplier_ean}' failed to identify an ASIN. Error: {amazon_product_data_from_ean_search.get('error')}")
                    amazon_product_data = None
                else:
                    log.debug(f"EAN search for '{supplier_ean}' did not yield an ASIN or any usable data.")
                    amazon_product_data = None

            if not amazon_product_data: # Fallback to title search if EAN search fails or no EAN
                if supplier_ean: log.info(f"EAN search failed for '{product_data.get('title')}'. Falling back to title search.")
                else: log.info(f"No EAN for '{product_data.get('title')}'. Using title search.")
                
                self.results_summary["products_analyzed_title"] += 1
                amazon_search_results = await self.extractor.search_by_title_using_search_bar(product_data["title"])
                if "error" in amazon_search_results or not amazon_search_results.get("results"):
                    log.warning(f"No Amazon results for title '{product_data['title']}'. Skipping. Details: {amazon_search_results.get('error', 'No results list')}")
                    continue
                
                top_amazon_result = amazon_search_results["results"][0] # search_by_title now returns sorted results
                asin_to_check = top_amazon_result.get("asin")
                if not asin_to_check:
                    log.warning(f"Could not determine ASIN from title search for '{product_data['title']}'. Skipping.")
                    continue

                amazon_product_data = await self._get_cached_amazon_data_by_asin(asin_to_check, supplier_ean)
                if not amazon_product_data:
                    log.info(f"Extracting detailed Amazon data for ASIN: {asin_to_check} (from title search)")
                    amazon_product_data = await self.extractor.extract_data(asin_to_check)
                    
                    # Apply quick triage if enabled
                    if self.enable_quick_triage and product_data.get("price"):
                        if self._passes_quick_triage(product_data.get("price"), amazon_product_data):
                            await self._cache_amazon_data(asin_to_check, amazon_product_data, product_data, "title_search")
                            log.info(f"Cached Amazon data from title search for ASIN: {asin_to_check}")
                        else:
                            log.info(f"Skipping cache for ASIN {asin_to_check} - failed quick triage check")
                    else:
                        await self._cache_amazon_data(asin_to_check, amazon_product_data, product_data, "title_search")
            
            if not amazon_product_data or "error" in amazon_product_data or not amazon_product_data.get("title") or not asin_to_check:
                log.warning(f"Failed to get valid Amazon data for supplier product '{product_data['title']}'. Skipping.")
                self.results_summary["errors"] += 1
                continue
            
            # SKIP TRIAGE: All products proceed to detailed extraction
            log.info(f"Skipping triage for ASIN {asin_to_check} - proceeding directly to detailed extraction")
            triage_result = {"verdict": "ACCEPT", "metrics": {}}  # Create dummy triage result for compatibility

            # Re-fetch amazon_product_data if it was from a cache and triage passed,
            # or if EAN search provided it directly without needing separate extract_data call.
            # The amazon_product_data should be the full detailed data at this point.
            if not amazon_product_data.get("keepa"): # Indicator that it might be shallow data or needs refresh
                log.info(f"Re-extracting/confirming detailed Amazon data for ASIN: {asin_to_check} post-triage.")
                amazon_product_data = await self.extractor.extract_data(asin_to_check)
                
                # Apply quick triage if enabled
                if self.enable_quick_triage and product_data.get("price"):
                    if self._passes_quick_triage(product_data.get("price"), amazon_product_data):
                        await self._cache_amazon_data(asin_to_check, amazon_product_data, product_data, "post_triage_refresh")
                        log.info(f"Cached Amazon data from post-triage refresh for ASIN: {asin_to_check}")
                    else:
                        log.info(f"Skipping cache for ASIN {asin_to_check} - failed quick triage check")
                else:
                    await self._cache_amazon_data(asin_to_check, amazon_product_data, product_data, "post_triage_refresh")


            if not amazon_product_data or "error" in amazon_product_data or not amazon_product_data.get("title"):
                log.warning(f"Failed to get valid Amazon data for ASIN '{asin_to_check}' post-triage. Skipping.")
                self.results_summary["errors"] += 1
                continue

            log.info(f"Successfully got Amazon data for '{amazon_product_data.get('title', 'N/A')}' (ASIN: {asin_to_check}, EAN on page: {amazon_product_data.get('ean_on_page', 'N/A')})")

            combined_data = {
                "supplier_product_info": product_data,
                "amazon_product_info": amazon_product_data, # This is now the detailed data
                "analysis_timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "triage_metrics_if_run": triage_result.get("metrics") # Add triage metrics
            }
            financial_metrics = self._calculate_roi_and_profit(combined_data)
            combined_data.update(financial_metrics)

            match_validation = await self._validate_product_match(product_data, amazon_product_data) # MODIFIED: Now async
            combined_data["match_validation"] = match_validation
            
            if match_validation["match_quality"] in ["high", "medium"]:
                if self._is_product_meeting_criteria(combined_data):
                    log.info(f"*** Profitable Product Found ***: '{amazon_product_data.get('title')}' (ASIN: {asin_to_check}) from supplier '{product_data.get('title')}'")
                    log.info(f"ROI: {combined_data.get('roi_percent_calculated')}%, Profit: £{combined_data.get('estimated_profit_per_unit')}")
                    log.info(f"Match Quality: {match_validation['match_quality']} ({match_validation['confidence_score']:.1%})") # MODIFIED: use confidence_score
                    profitable_results.append(combined_data)
                    self.results_summary["profitable_products"] += 1
                else:
                    log.info(f"Product does not meet criteria. ROI: {combined_data.get('roi_percent_calculated')}%, Profit: £{combined_data.get('estimated_profit_per_unit')}")
            else:
                log.warning(
                    f"Low quality match ({match_validation['match_quality']}) between supplier product '{product_data.get('title')}' and Amazon product '{amazon_product_data.get('title')}'. Skipping."
                )
                log.debug(f"Match reasons: {match_validation.get('reasons', [])}")

        self.results_summary["products_processed_total"] += total_processed
        for cat, count in processed_by_category.items():
            self.results_summary.setdefault("products_processed_per_category", {}).setdefault(cat, 0)
            self.results_summary["products_processed_per_category"][cat] += count

        if limit_reached:
            log.info("Product processing limit reached. Ending workflow early.")
            return profitable_results

        
        # D2: Stage-guard audit - Log triage stage completion
        log.info(f"STAGE-COMPLETE: triage_stage - {self.results_summary['products_passed_triage']} passed, {self.results_summary['products_rejected_by_triage']} rejected (Triage Setting: {'ENABLED' if self.enable_quick_triage else 'DISABLED'})")
        if self.enable_quick_triage and self.results_summary['products_passed_triage'] == 0 and self.results_summary['products_rejected_by_triage'] > 0 and self.results_summary['products_rejected_by_triage'] == len(products_to_analyze):
            log.warning(f"STAGE-GUARD WARNING: Triage was ENABLED and rejected all {len(products_to_analyze)} products processed in this batch. Check SellerAmp connectivity or criteria.")
        elif not self.enable_quick_triage and len(products_to_analyze) > 0 and len(profitable_results) == 0 :
             log.info(f"Triage was DISABLED. All {len(products_to_analyze)} products processed in this batch proceeded to full analysis. No profitable products found post-analysis in this batch.")
            
        # D2: Stage-guard audit - Log deep extraction stage completion
        total_deep_extractions = self.results_summary['products_passed_triage'] - self.results_summary['errors']
        log.info(f"STAGE-COMPLETE: deep_extraction - {total_deep_extractions} successful extractions, {self.results_summary['errors']} errors")
        if total_deep_extractions == 0 and self.results_summary['products_passed_triage'] > 0:
            log.error(f"STAGE-GUARD ERROR: Deep extraction failed for all {self.results_summary['products_passed_triage']} products that passed triage. Check Chrome CDP connection.")
        
        # D2: Stage-guard audit - Log final results stage
        log.info(f"STAGE-COMPLETE: profitable_filtering - {len(profitable_results)} profitable products found")
        
        if profitable_results:
            output_filename = f"fba_profitable_finds_{session_id}.json"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            try:
                with open(output_path, "w", encoding="utf-8") as f: 
                    json.dump(profitable_results, f, indent=2, ensure_ascii=False)
                log.info(f"Found {len(profitable_results)} profitable products. Results saved to {output_path}")
            except Exception as e: 
                log.error(f"Error saving results: {e}")
        else:
            log.info("No profitable products found meeting all criteria in this run.")

        self.results_summary["end_time"] = datetime.now().isoformat()
        summary_filename = f"fba_summary_{session_id}.json"
        summary_path = os.path.join(OUTPUT_DIR, summary_filename)
        try:
            with open(summary_path, "w", encoding="utf-8") as f: 
                json.dump(self.results_summary, f, indent=2, ensure_ascii=False)
            log.info(f"Workflow summary saved to {summary_path}")
            
            # Log final session summary with previously visited info
            if self.results_summary["products_previously_visited"] > 0:
                log.info(f"📋 Session Summary: {self.results_summary['products_previously_visited']} products previously visited (resumed), "
                        f"{self.results_summary['products_analyzed_ean'] + self.results_summary['products_analyzed_title'] - self.results_summary['products_previously_visited']} newly analyzed, "
                        f"{self.results_summary['profitable_products']} profitable products found")
            else:
                log.info(f"📋 Session Summary: {self.results_summary['products_analyzed_ean'] + self.results_summary['products_analyzed_title']} products analyzed, "
                        f"{self.results_summary['profitable_products']} profitable products found")
                        
        except Exception as e: 
            log.error(f"Error saving summary: {e}")
        
        # Save linking map buffer using new array format writer
        if self._linking_map_buffer:
            try:
                # Use LinkingMapWriter to save in proper array format to run output directory
                linking_map_path = await self._save_linking_map_batch()
                log.info(f"✅ Linking map saved with {len(self._linking_map_buffer)} entries to {linking_map_path}")
            except Exception as e:
                log.error(f"❌ Failed to save linking map: {e}")
        else:
            log.info("📋 No linking map entries to save")
        
        # Run integrated FBA Financial Calculator to generate detailed CSV report
        # Assign instance/global directories to local vars before the try block for clarity
        current_supplier_cache_dir = self.supplier_cache_dir
        current_amazon_cache_dir = AMAZON_CACHE_DIR # Global in this file
        current_output_dir = OUTPUT_DIR # Global in this file

        try:
            log.info("Running FBA_Financial_calculator run_calculations...")
            from FBA_Financial_calculator import run_calculations # Import locally
            
            # Use the local variables for paths
            supplier_cache_file_path = os.path.join(current_supplier_cache_dir, f"{supplier_name.replace('.', '_')}_products_cache.json")
            financial_reports_output_path = os.path.join(current_output_dir, "financial_reports")
            os.makedirs(financial_reports_output_path, exist_ok=True)
            
            financial_results = run_calculations(
                supplier_cache_path=supplier_cache_file_path,
                output_dir=financial_reports_output_path,
                amazon_scrape_dir=current_amazon_cache_dir
            )
            log.info(f"FBA financial report generated at: {financial_results['statistics']['output_file']}")
        except Exception as e:
            log.error(f"Error running FBA_Financial_calculator: {e}")

        # ──────────────────────── 🔄 CONTINUOUS LOOP LOGIC ────────────────────────
        # Check if we should trigger a new AI category cycle after processing products
        products_analyzed_this_session = len(products_to_analyze) - self.results_summary.get("products_previously_visited", 0)

        # Determine if we should continue with new AI categories
        should_continue_with_ai = self._should_trigger_new_ai_cycle(
            products_analyzed_this_session=products_analyzed_this_session,
            max_products_limit=max_products_to_process,
            current_categories_exhausted=True  # Always consider exhausted after processing batch
        )

        # REMOVED: AI category generation moved to post-scrape section
        if False:  # Disabled: AI category generation within main loop
            log.info(f"🔄 AI CATEGORY CYCLE DISABLED - Moved to post-scrape section")

            try:
                # REMOVED: Get fresh AI category suggestions with proper memory
                new_category_urls = []  # await self._hierarchical_category_selection(supplier_url, supplier_name)

                if new_category_urls:
                    log.info(f"🎯 NEW AI CYCLE: Found {len(new_category_urls)} new categories to process")

                    # Scrape new categories and get fresh products
                    log.info("🔄 Scraping new AI-suggested categories...")
                    fresh_supplier_products = []

                    for category_url in new_category_urls:
                        log.info(f"🔍 Scraping new category: {category_url}")
                        category_products = await self._scrape_single_category(category_url, supplier_name)
                        if category_products:
                            fresh_supplier_products.extend(category_products)
                            log.info(f"✅ Found {len(category_products)} products in {category_url}")

                    if fresh_supplier_products:
                        log.info(f"🎯 NEW AI CYCLE: Scraped {len(fresh_supplier_products)} fresh products from new categories")

                        # Update supplier cache with new products
                        if cache_supplier_data:
                            try:
                                # Load existing products from cache
                                supplier_cache_file = os.path.join(SUPPLIER_CACHE_DIR, f"{supplier_name.replace('.', '_')}_products_cache.json")
                                existing_products = []
                                if os.path.exists(supplier_cache_file):
                                    with open(supplier_cache_file, 'r', encoding='utf-8') as f:
                                        existing_products = json.load(f)

                                # Merge with new products to avoid duplicates
                                all_products = existing_products + fresh_supplier_products

                                # Remove duplicates based on URL
                                seen_urls = set()
                                unique_products = []
                                for product in all_products:
                                    if product.get("url") not in seen_urls:
                                        unique_products.append(product)
                                        seen_urls.add(product.get("url"))

                                with open(supplier_cache_file, 'w', encoding='utf-8') as f:
                                    json.dump(unique_products, f, indent=2, ensure_ascii=False)
                                log.info(f"🔄 Updated supplier cache with {len(unique_products)} total products ({len(fresh_supplier_products)} new)")
                            except Exception as e:
                                log.error(f"Error updating supplier cache with new products: {e}")

                        # Reset processing index to continue with new products
                        self.last_processed_index = len(products_to_analyze)  # Start after previously processed products

                        # Filter new products by price range
                        valid_fresh_products = [
                            p for p in fresh_supplier_products
                            if p.get("title") and isinstance(p.get("price"), (float, int)) and p.get("price", 0) > 0 and p.get("url")
                        ]
                        price_filtered_fresh_products = [
                            p for p in valid_fresh_products
                            if self.min_price <= p.get("price", 0) <= MAX_PRICE
                        ]

                        if price_filtered_fresh_products:
                            log.info(f"🎯 NEW AI CYCLE: {len(price_filtered_fresh_products)} new products meet price criteria [£{self.min_price}-£{MAX_PRICE}]")

                            # 🎯 DYNAMIC PARAMETER SWITCHING: Switch to unlimited mode after first AI cycle
                            # If this is the first AI cycle (small batch), switch to unlimited mode
                            if max_products_to_process > 0 and max_products_to_process <= 10:
                                log.info("🔄 DYNAMIC SWITCHING: First AI cycle complete with small batch testing")
                                log.info("🔄 SWITCHING TO UNLIMITED MODE: max_products=0 for continuous operation")
                                new_max_products = 0  # Switch to unlimited mode
                            else:
                                new_max_products = max_products_to_process  # Keep current setting

                            # Recursively call run() with new products to continue the cycle
                            log.info(f"🔄 RECURSIVE CALL: Starting new cycle with max_products={new_max_products} (was {max_products_to_process})")
                            additional_results = await self.run(
                                supplier_url=supplier_url,
                                supplier_name=supplier_name,
                                max_products_to_process=new_max_products,
                                max_products_per_category=max_products_per_category,
                                max_analyzed_products=max_analyzed_products,
                                cache_supplier_data=cache_supplier_data,
                                force_config_reload=False,  # Don't clear cache again
                                debug_smoke=debug_smoke,
                                resume_from_last=True,
                            )

                            # Merge results from recursive call
                            if additional_results:
                                profitable_results.extend(additional_results)
                                log.info(f"🎯 CYCLE COMPLETE: Added {len(additional_results)} profitable products from new AI cycle")
                        else:
                            log.info("🔄 NEW AI CYCLE: No products from new categories meet price criteria")
                    else:
                        log.info("🔄 NEW AI CYCLE: No products found in new AI-suggested categories")
                else:
                    log.info("🔄 NEW AI CYCLE: No new categories suggested by AI - cycle complete")
            except Exception as e:
                log.error(f"Error during new AI category cycle: {e}")
        else:
            if not should_continue_with_ai:
                log.info("🔄 No new AI cycle needed - workflow complete")
            elif not hasattr(self, 'ai_client') or not self.ai_client:
                log.info("🔄 No AI client available for new cycle")

        # Complete enhanced state management tracking
        self.state_manager.complete_processing()
        final_state = self.state_manager.get_state_summary()
        log.info(f"✅ Enhanced state tracking completed: {final_state}")

        # POST-SCRAPE AI CATEGORY GENERATION (Fix #4)
        # Move all AI category generation calls to after full supplier scrape completion
        if (getattr(self, 'force_ai_scraping', False) or 
            (hasattr(self, 'force_ai_category_progression') and self.force_ai_category_progression)):
            log.info("🧠 Starting post-scrape AI category generation...")
            try:
                from tools.ai_category_suggester import generate_categories
                
                # Collect URL discovery data from processing
                url_discovery_output = {
                    "navigation_urls": [],
                    "category_urls": [],
                    "total_products_processed": len(supplier_products),
                    "workflow_session_id": session_id
                }
                
                # Generate AI categories with full product data
                ai_cache_path = await generate_categories(
                    supplier_name, 
                    supplier_products, 
                    url_discovery_output=url_discovery_output
                )
                log.info(f"✅ Post-scrape AI category generation completed: {ai_cache_path}")
                
                # Update results summary with AI generation info
                self.results_summary["ai_category_generation"] = {
                    "completed": True,
                    "cache_path": str(ai_cache_path),
                    "products_analyzed": len(supplier_products),
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                log.error(f"❌ Post-scrape AI category generation failed: {e}")
                self.results_summary["ai_category_generation"] = {
                    "completed": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        else:
            log.info("🧠 Post-scrape AI category generation skipped (not enabled)")

        return profitable_results

    def _should_trigger_new_ai_cycle(self, products_analyzed_this_session: int, max_products_limit: int,
                                   current_categories_exhausted: bool = False) -> bool:
        """
        Determine if we should trigger a new AI category selection cycle.

        Args:
            products_analyzed_this_session: Number of products analyzed in current session
            max_products_limit: Maximum products limit (0 = unlimited)
            current_categories_exhausted: Whether current AI-suggested categories are exhausted

        Returns:
            bool: True if new AI cycle should be triggered
        """
        # 🔧 FIXED: Always trigger AI cycle when categories are exhausted, regardless of products analyzed
        if current_categories_exhausted:
            log.info(f"🔄 CATEGORIES EXHAUSTED: Triggering new AI cycle (products analyzed: {products_analyzed_this_session})")
            return True

        # For unlimited mode (max_products_limit = 0), trigger new cycle every N products (configurable)
        if max_products_limit <= 0:
            cycle_interval = self.financial_report_batch_size  # Use same interval as financial reports
            if products_analyzed_this_session > 0 and products_analyzed_this_session % cycle_interval == 0:
                log.info(f"🔄 UNLIMITED MODE: Triggering new AI cycle after {products_analyzed_this_session} products (interval: {cycle_interval})")
                return True

        # Check if we've reached a reasonable threshold for new suggestions
        if products_analyzed_this_session >= 20:  # Trigger after analyzing 20+ products
            log.info(f"🔄 THRESHOLD REACHED: Triggering new AI cycle after {products_analyzed_this_session} products")
            return True

        # 🔧 FIXED: For small batches (like testing), trigger after any processing
        if products_analyzed_this_session >= 1 and max_products_limit <= 10:
            log.info(f"🔄 SMALL BATCH MODE: Triggering new AI cycle after {products_analyzed_this_session} products (limit: {max_products_limit})")
            return True

        return False

    async def _scrape_single_category(self, category_url: str, supplier_name: str) -> List[Dict[str, Any]]:
        """
        Scrape products from a single category URL.

        Args:
            category_url: URL of the category to scrape
            supplier_name: Name of the supplier

        Returns:
            List of product dictionaries
        """
        try:
            log.info(f"🔍 Scraping category: {category_url}")

            # Get page content
            html_content = await self.web_scraper.get_page_content(category_url)
            if not html_content:
                log.warning(f"Failed to get content from {category_url}")
                return []

            # Extract product elements
            product_elements_soup = self.web_scraper.extract_product_elements(html_content, category_url)
            if not product_elements_soup:
                log.warning(f"No product elements found on {category_url}")
                return []

            log.info(f"Found {len(product_elements_soup)} product elements in {category_url}")

            # Process products in batches
            extracted_products = []
            batch_size = 5

            for i in range(0, len(product_elements_soup), batch_size):
                batch = product_elements_soup[i:i+batch_size]
                batch_tasks = [
                    self._process_product_element(
                        p_soup, str(p_soup), category_url,
                        urlparse(category_url).scheme + "://" + urlparse(category_url).netloc,
                        supplier_name
                    ) for p_soup in batch
                ]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        log.error(f"Error processing product element: {result}")
                    elif result:
                        extracted_products.append(result)

                log.debug(f"Processed batch of {len(batch)} products from {category_url}")

            log.info(f"✅ Extracted {len(extracted_products)} products from {category_url}")
            return extracted_products

        except Exception as e:
            log.error(f"Error scraping category {category_url}: {e}")
            return []

    async def _get_cached_amazon_data_by_asin(self, asin: str, supplier_ean: str = None) -> Optional[Dict[str, Any]]:
        """Helper to get cached Amazon data by ASIN, with support for EAN-based filenames."""
        if not asin:
            return None # Added check for None ASIN

        # FIXED: Try multiple filename patterns to find cached data
        # Priority order: 1) ASIN_EAN format, 2) ASIN-only format, 3) Pattern search
        cache_files_to_try = []

        # 1. If we have supplier EAN, try ASIN_EAN format first
        if supplier_ean:
            cache_files_to_try.append(f"amazon_{asin}_{supplier_ean}.json")

        # 2. Try ASIN-only format (legacy and fallback)
        cache_files_to_try.append(f"amazon_{asin}.json")

        # 3. Search for any file starting with amazon_{asin}_ (in case EAN differs)
        try:
            import glob
            pattern_files = glob.glob(os.path.join(self.amazon_cache_dir, f"amazon_{asin}_*.json"))
            for pattern_file in pattern_files:
                filename = os.path.basename(pattern_file)
                if filename not in cache_files_to_try:
                    cache_files_to_try.append(filename)
        except Exception:
            pass  # Fallback if glob fails

        # Try each potential cache file
        for cache_filename in cache_files_to_try:
            asin_cache_file = os.path.join(self.amazon_cache_dir, cache_filename)
            if os.path.exists(asin_cache_file):
                cache_age = time.time() - os.path.getmtime(asin_cache_file)
                if cache_age < self.max_cache_age_seconds:
                    try:
                        with open(asin_cache_file, 'r', encoding='utf-8') as f:
                            amazon_product_data = json.load(f)
                        log.info(f"Loaded Amazon data for ASIN {asin} from cache file {cache_filename} ({cache_age/3600:.1f} hours old)")
                        return amazon_product_data
                    except Exception as e:
                        log.error(f"Error loading Amazon cache for ASIN {asin} from {cache_filename}: {e}")
                        continue  # Try next file
                else:
                    log.debug(f"Cache file {cache_filename} too old ({cache_age/3600:.1f} hours), skipping")

        log.debug(f"No valid cache found for ASIN {asin} (tried {len(cache_files_to_try)} files)")
        return None

    async def _clear_failed_keepa_extractions(self):
        """
        CRITICAL FIX 2: Clear Amazon cache files with failed Keepa extractions.
        This addresses the issue where files with failed Keepa data accumulate in cache.
        """
        if not os.path.exists(self.amazon_cache_dir):
            log.info("Amazon cache directory does not exist, skipping failed extraction clearing")
            return

        log.info("Clearing Amazon cache files with failed Keepa extractions...")

        cleared_count = 0
        total_checked = 0

        for cache_file in os.listdir(self.amazon_cache_dir):
            if not cache_file.endswith('.json') or not cache_file.startswith('amazon_'):
                continue

            cache_file_path = os.path.join(self.amazon_cache_dir, cache_file)
            total_checked += 1

            try:
                with open(cache_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Check for failed Keepa extractions
                keepa_data = data.get("keepa", {})
                keepa_status = keepa_data.get("status", "").lower()

                # Identify failed extractions by status indicators
                failed_indicators = [
                    "timeout", "failed", "error", "not detected",
                    "iframe not found", "no data extracted", "extraction process failed"
                ]

                is_failed_extraction = any(indicator in keepa_status for indicator in failed_indicators)

                # Also check if product_details_tab_data is missing or empty
                product_details = keepa_data.get("product_details_tab_data", {})
                has_no_product_details = not product_details or len(product_details) == 0

                # Clear if failed status OR no product details (indicating incomplete extraction)
                if is_failed_extraction or has_no_product_details:
                    os.remove(cache_file_path)
                    cleared_count += 1
                    log.info(f"Cleared failed Keepa extraction: {cache_file} (status: {keepa_status})")

            except Exception as e:
                log.warning(f"Error checking {cache_file} for failed extractions: {e}")
                # Optionally remove corrupted files
                try:
                    os.remove(cache_file_path)
                    cleared_count += 1
                    log.info(f"Cleared corrupted cache file: {cache_file}")
                except Exception as remove_error:
                    log.error(f"Failed to remove corrupted file {cache_file}: {remove_error}")

        log.info(f"Failed Keepa extraction clearing completed: {cleared_count} files removed out of {total_checked} checked")

    async def _cache_amazon_data(self, chosen_asin: str, amazon_product_data: Dict[str, Any], supplier_product_info: Dict[str, Any], match_method_used: str):
        """Helper to cache Amazon data with enhanced linking map generation for Fix 2.6."""
        if not chosen_asin: 
            return  # Added check for None ASIN
        if "error" not in amazon_product_data and amazon_product_data.get("title"):
            # Enhanced Filename Logic - ALWAYS include supplier context for traceability
            supplier_ean = supplier_product_info.get("ean")
            if supplier_ean:
                # Primary case: Use supplier EAN when available
                filename = f"amazon_{chosen_asin}_{supplier_ean}.json"
            else:
                # Fallback: Use supplier context for traceability even without EAN
                import hashlib
                supplier_title = supplier_product_info.get("title", "")
                supplier_url = supplier_product_info.get("url", "")

                if supplier_title:
                    # Use title hash for traceability
                    title_hash = hashlib.md5(supplier_title.encode('utf-8')).hexdigest()[:8]
                    filename = f"amazon_{chosen_asin}_title_{title_hash}.json"
                    log.info(f"Using title-based filename for ASIN {chosen_asin}: {filename} (title: {supplier_title[:50]}...)")
                elif supplier_url:
                    # Use URL hash as last resort
                    url_hash = hashlib.md5(supplier_url.encode('utf-8')).hexdigest()[:8]
                    filename = f"amazon_{chosen_asin}_url_{url_hash}.json"
                    log.info(f"Using URL-based filename for ASIN {chosen_asin}: {filename}")
                else:
                    # Ultimate fallback with timestamp for uniqueness
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"amazon_{chosen_asin}_unknown_{timestamp}.json"
                    log.warning(f"No supplier context available for ASIN {chosen_asin}, using timestamp-based filename: {filename}")
            
            cache_file_path = os.path.join(self.amazon_cache_dir, filename)
            
            try:
                with open(cache_file_path, 'w', encoding='utf-8') as f:
                    json.dump(amazon_product_data, f, indent=2, ensure_ascii=False)
                log.info(f"Cached Amazon data for ASIN {chosen_asin} as {filename}")
                
                # Update Linking Map
                supplier_url = supplier_product_info.get("url", "")
                supplier_title = supplier_product_info.get("title", "")

                supplier_identifier_for_map = f"EAN_{supplier_ean}" if supplier_ean else f"URL_{supplier_url}"

                amazon_title_snippet = (amazon_product_data.get("title", "")[:60] + "...") if amazon_product_data.get("title") else "N/A"
                supplier_title_snippet = (supplier_title[:60] + "...") if supplier_title else "N/A"

                link_record = {
                    "supplier_product_identifier": supplier_identifier_for_map,
                    "supplier_title_snippet": supplier_title_snippet,
                    "chosen_amazon_asin": chosen_asin,
                    "amazon_title_snippet": amazon_title_snippet,
                    "amazon_ean_on_page": amazon_product_data.get("ean_on_page"),
                    "match_method": match_method_used
                }
                # Add to buffer for batch saving in new array format
                self._linking_map_buffer.append(link_record)
                log.info(f"Added to linking map buffer: {supplier_identifier_for_map} -> {chosen_asin}")
                
                # CRITICAL FIX: Periodic saves every N products to prevent data loss (configurable)
                self._processed_count += 1
                if self._processed_count % self.linking_map_batch_size == 0:
                    log.info(f"🔄 PERIODIC SAVE triggered at product #{self._processed_count} (batch size: {self.linking_map_batch_size})")
                    try:
                        await self._save_linking_map_batch()
                    except Exception as e:
                        log.error(f"Error in periodic linking map save: {e}")
                    self._save_product_cache()
                    log.info(f"✅ PERIODIC SAVE completed - {len(self._linking_map_buffer)} linking entries saved")
                
            except Exception as e:
                log.error(f"Error caching Amazon data for ASIN {chosen_asin}: {e}")

    def _is_battery_product(self, title: str) -> bool:
        """
        Check if a product title indicates it's a battery product that should be filtered out.
        Returns True if the product should be excluded (is a battery product).
        """
        if not title:
            return False
            
        title_lower = title.lower()
        
        # Direct battery keyword check
        for keyword in BATTERY_KEYWORDS:
            if keyword in title_lower:
                log.debug(f"Product '{title}' identified as battery product (keyword: {keyword})")
                return True
        
        # Brand context check - only flag as battery if brand appears with battery context
        for brand in BATTERY_BRAND_CONTEXT:
            if brand in title_lower:
                # Check if there are battery-related terms near the brand
                battery_context_terms = ["battery", "batteries", "cell", "power", "rechargeable", 
                                       "alkaline", "lithium", "volt", "v ", "mah", "amp"]
                for context_term in battery_context_terms:
                    if context_term in title_lower:
                        log.debug(f"Product '{title}' identified as battery product (brand: {brand}, context: {context_term})")
                        return True
        
        # Voltage pattern check (e.g., "3V", "12V", "1.5V")
        voltage_pattern = r'\b\d+\.?\d*v\b'
        if re.search(voltage_pattern, title_lower) and any(term in title_lower for term in ["battery", "cell", "power"]):
            log.debug(f"Product '{title}' identified as battery product (voltage pattern)")
            return True
            
        return False

    async def _extract_supplier_products(
        self,
        supplier_base_url: str,
        supplier_name: str,
        max_products_per_category: int = 0,
    ) -> List[Dict[str, Any]]:
        extracted_products: List[Dict[str, Any]] = []
        
        # PHASE 4 FIX: Initialize product cache tracking for periodic saves
        # Note: _current_supplier_name already set at start of run method
        self._current_supplier_cache_path = os.path.join(
            self.supplier_cache_dir, 
            f"{supplier_name.replace('.', '_')}_products_cache.json"
        )
        self._current_extracted_products = extracted_products  # Reference to current list
        
        # Set up state tracking path
        from pathlib import Path
        self.state_path = os.path.join(OUTPUT_DIR, f"{supplier_name.replace('.', '_')}_processing_state.json")
        
        # MODIFIED: Get supplier configuration from ConfigurableSupplierScraper
        supplier_config = self.web_scraper._get_selectors_for_domain(supplier_base_url) # type: ignore
        
        # DISABLED: Check if AI category progression is enabled (Fix #4)
        # AI category progression moved to post-scrape phase
        use_ai_progression = False  # Disabled mid-scrape AI calls
        
        log.info("AI category progression disabled during scraping (moved to post-scrape phase)")
            
        use_two_step = supplier_config.get("two_step_extraction", True)
        
        log.info(f"Extracting products from {supplier_name} using {'two-step' if use_two_step else 'single-step'} process.")
        
        # ──────────────────────── ⑤  Use traditional category paths only ────────────────────────
        # Traditional category path approach (no mid-scrape AI calls)
        category_paths = supplier_config.get("category_paths", ["/"])
        category_urls_to_process = [supplier_base_url.rstrip('/') + path for path in category_paths]
        log.info(f"Using traditional category paths for supplier scraping: {category_paths}")
        log.info("📝 AI category generation will run after complete supplier scrape (Fix #4)")

        for category_url in category_urls_to_process:
            log.info(f"Scraping supplier category: {category_url}")
            products_in_category = 0
            
            # MODIFIED: Pagination for supplier category pages
            current_page_num = 1
            max_supplier_pages = supplier_config.get("max_category_pages_to_scrape", 5) # Configurable max pages
            
            while current_page_num <= max_supplier_pages:
                page_url_to_fetch = category_url
                if current_page_num > 1 and hasattr(self.web_scraper, 'get_next_page_url'): # Ensure method exists
                    # For subsequent pages, get_next_page_url would need the previous page's soup.
                    # This requires fetching page 1 first, then using its soup for page 2 URL, etc.
                    # The current structure fetches HTML then extracts elements.
                    # Let's adjust to fetch, then get next page URL from soup if page_num > 1.
                    
                    # Fixed pagination logic for clearance-king.co.uk
                    if current_page_num > 1:
                        # For clearance-king, page 2+ follows pattern: ?p=2&product_list_dir=asc&product_list_limit=64&product_list_order=price
                        temp_parsed_url = urlparse(category_url)
                        query_params = dict(parse_qsl(temp_parsed_url.query))
                        
                        # Update or add pagination parameter
                        query_params['p'] = str(current_page_num)
                        
                        # Ensure required parameters are present
                        if 'product_list_limit' not in query_params:
                            query_params['product_list_limit'] = '64'
                        if 'product_list_order' not in query_params:
                            query_params['product_list_order'] = 'price'
                        if 'product_list_dir' not in query_params:
                            query_params['product_list_dir'] = 'asc'
                        
                        # Reconstruct URL with pagination
                        new_query = urlencode(query_params, doseq=True)
                        page_url_to_fetch = urlunparse((
                            temp_parsed_url.scheme,
                            temp_parsed_url.netloc, 
                            temp_parsed_url.path,
                            temp_parsed_url.params,
                            new_query,
                            temp_parsed_url.fragment
                        ))
                        log.info(f"Constructed page {current_page_num} URL: {page_url_to_fetch}")


                log.info(f"Fetching supplier category page {current_page_num}: {page_url_to_fetch}")
                html_content = await self.web_scraper.get_page_content(page_url_to_fetch)
                if not html_content:
                    log.warning(f"Failed to get content from {page_url_to_fetch} (Page {current_page_num}). Skipping remaining pages for this category.")
                    break 
                
                # The scraper uses the URL to determine domain and load correct selectors
                product_elements_soup = self.web_scraper.extract_product_elements(html_content, page_url_to_fetch)
                if not product_elements_soup:
                    log.warning(f"No product elements found on {page_url_to_fetch} (Page {current_page_num}).")
                    if current_page_num == 1: # If no products on first page, probably no more.
                        break
                    else: # If products on previous pages but not this one, assume end of pagination
                        log.info(f"Assuming end of pagination for {category_url} at page {current_page_num}.")
                        break

                log.info(f"Found {len(product_elements_soup)} product elements in category {category_url}, page {current_page_num}")

                # Check for price-based stopping logic (Phase 1: £0-£10)
                should_stop_scraping = False
                if len(extracted_products) > 0:
                    # Check last few products for price range
                    recent_products = extracted_products[-min(10, len(extracted_products)):]
                    prices = [p.get("price", 0) for p in recent_products if p.get("price")]

                    if prices:
                        # Check if we've reached the £10 threshold (Phase 1 completion)
                        prices_above_10 = [p for p in prices if p > 10.0]
                        if len(prices_above_10) >= 5:  # If 5+ recent products are above £10
                            avg_recent_price = sum(prices) / len(prices)
                            log.info(f"Phase 1 (£0-£10) threshold reached: {len(prices_above_10)}/10 recent products above £10.00 (avg: £{avg_recent_price:.2f})")
                            log.info(f"Stopping current category to move to next category in Phase 1.")
                            should_stop_scraping = True

                            # Store pagination state for Phase 2 continuation
                            self._store_phase_2_continuation_point(category_url, current_page_num, len(extracted_products))

                # Process elements from the current page
                if use_two_step:
                    basic_products = []
                    for p_soup in product_elements_soup:
                        try:
                            # Pass page_url_to_fetch as context_url
                            title = await self.web_scraper.extract_title(p_soup, str(p_soup), page_url_to_fetch)
                            
                            # Early battery filter
                            if is_battery_title(title):
                                log.debug("⚡ Battery item skipped early → %s", title[:60])
                                continue
                                
                            product_page_url = await self.web_scraper.extract_url(p_soup, str(p_soup), page_url_to_fetch, supplier_base_url)
                            if title and product_page_url:
                                basic_products.append({"title": title, "url": product_page_url, "category_url_source": page_url_to_fetch})
                        except Exception as e:
                            log.error(f"Error extracting basic product info: {e}")
                    
                    batch_size = 5
                    for i in range(0, len(basic_products), batch_size):
                        if max_products_per_category > 0 and products_in_category >= max_products_per_category:
                            should_stop_scraping = True
                            break
                        batch = basic_products[i:i+batch_size]
                        if max_products_per_category > 0:
                            remaining = max_products_per_category - products_in_category
                            if remaining <= 0:
                                should_stop_scraping = True
                                break
                            batch = batch[:remaining]
                        # Pass category_url_source for context if needed by _get_product_details
                        batch_tasks = [self._get_product_details(p["url"], p["title"], supplier_name, p["category_url_source"]) for p in batch]
                        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                        for result in batch_results:
                            if isinstance(result, Exception):
                                log.error(f"Error processing product details: {result}")
                            elif result:
                                extracted_products.append(result)
                                products_in_category += 1
                                if max_products_per_category > 0 and products_in_category >= max_products_per_category:
                                    log.info(
                                        f"Reached max_products_per_category={max_products_per_category} for {category_url}. Stopping category scrape."
                                    )
                                    should_stop_scraping = True
                                    break
                        log.info(
                            f"Processed batch of {len(batch)} detailed products from page {current_page_num}, total extracted so far: {len(extracted_products)}"
                        )
                        if should_stop_scraping:
                            break
                else: # Single-step
                    batch_size = 5
                    for i in range(0, len(product_elements_soup), batch_size):
                        if max_products_per_category > 0 and products_in_category >= max_products_per_category:
                            should_stop_scraping = True
                            break
                        batch = product_elements_soup[i:i+batch_size]
                        if max_products_per_category > 0:
                            remaining = max_products_per_category - products_in_category
                            if remaining <= 0:
                                should_stop_scraping = True
                                break
                            batch = batch[:remaining]
                        batch_tasks = [self._process_product_element(p_soup, str(p_soup), page_url_to_fetch, supplier_base_url, supplier_name) for p_soup in batch]
                        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                        for result in batch_results:
                            if isinstance(result, Exception):
                                log.error(f"Error processing supplier product element: {result}")
                            elif result:
                                extracted_products.append(result)
                                products_in_category += 1
                                if max_products_per_category > 0 and products_in_category >= max_products_per_category:
                                    log.info(
                                        f"Reached max_products_per_category={max_products_per_category} for {category_url}. Stopping category scrape."
                                    )
                                    should_stop_scraping = True
                                    break
                        log.info(
                            f"Processed batch of {len(batch)} products from supplier page {current_page_num}, total extracted so far: {len(extracted_products)}"
                        )
                        if should_stop_scraping:
                            break

                # Run FBA Financial Calculator every N products (configurable)
                if len(extracted_products) % self.financial_report_batch_size == 0 and len(extracted_products) > 0:
                    log.info(f"Reached {len(extracted_products)} products. Running FBA Financial Calculator (batch size: {self.financial_report_batch_size})...")
                    try:
                        from FBA_Financial_calculator import run_calculations
                        supplier_cache_file_path = os.path.join(current_supplier_cache_dir, f"{supplier_name.replace('.', '_')}_products_cache.json")
                        financial_reports_output_path = os.path.join(current_output_dir, "financial_reports")
                        os.makedirs(financial_reports_output_path, exist_ok=True)

                        # Save current products to cache before running calculator
                        self._save_products_to_cache(extracted_products, supplier_cache_file_path)

                        financial_results = run_calculations(
                            supplier_cache_path=supplier_cache_file_path,
                            output_dir=financial_reports_output_path,
                            amazon_scrape_dir=current_amazon_cache_dir
                        )
                        log.info(f"FBA Financial Calculator completed for {len(extracted_products)} products. Report: {financial_results.get('statistics', {}).get('output_file', 'N/A')}")
                    except Exception as e:
                        log.error(f"Error running FBA Financial Calculator at {len(extracted_products)} products: {e}")

                # Check if we should stop due to price threshold
                if should_stop_scraping:
                    log.info(f"Stopping pagination for {category_url} due to price threshold.")
                    break

                # Attempt to get next page URL using the scraper's method
                # This requires the current page's soup.
                current_page_soup_for_pagination = BeautifulSoup(html_content, 'html.parser')
                next_page_url_from_scraper = self.web_scraper.get_next_page_url(page_url_to_fetch, current_page_soup_for_pagination, current_page_num)

                if next_page_url_from_scraper:
                    category_url = next_page_url_from_scraper # Update category_url for the next iteration
                    current_page_num += 1
                else:
                    log.info(f"No next page found by scraper for {page_url_to_fetch}. Ending pagination for this category path.")
                    break # No more pages for this category path
            
        # Final battery filter check before returning products
        initial_count = len(extracted_products)
        extracted_products = [p for p in extracted_products if not is_battery_title(p.get('title', ''))]
        filtered_count = initial_count - len(extracted_products)
        if filtered_count > 0:
            log.info(f"Filtered out {filtered_count} battery products from {supplier_name}")
            
        return extracted_products

    async def _process_product_element(self, p_soup: BeautifulSoup, element_html: str, context_url: str, supplier_base_url: str, supplier_name: str):
        """
        Process a single product element from a listing page (single-step extraction).
        Relies on ConfigurableSupplierScraper for data extraction.
        """
        try:
            # ConfigurableSupplierScraper methods take context_url to load appropriate selectors
            title = await self.web_scraper.extract_title(p_soup, element_html, context_url)
            price = await self.web_scraper.extract_price(p_soup, element_html, context_url)
            product_page_url = await self.web_scraper.extract_url(p_soup, element_html, context_url, supplier_base_url)
            image_url = await self.web_scraper.extract_image(p_soup, element_html, context_url, supplier_base_url)
            
            ean = None # EAN extraction is typically better on the product detail page
            # If ConfigurableSupplierScraper is enhanced to get EAN from listing elements, it would be called here.
            # For now, EAN is primarily handled in _get_product_details for two-step.

            if title and price is not None and price > 0 and product_page_url:
                # Battery filtering - exclude battery products
                if self._is_battery_product(title):
                    log.debug(f"Excluding battery product: {title}")
                    return None
                    
                return {
                    "title": title,
                    "price": price,
                    "url": product_page_url,
                    "image_url": image_url,  # Use proper null instead of "N/A"
                    "ean": ean,
                    "upc": None,  # Add UPC field with null fallback
                    "sku": None,  # Add SKU field with null fallback
                    "source_supplier": supplier_name,
                    "source_category_url": context_url,
                    "extraction_timestamp": datetime.now().isoformat()
                }
            return None
        except Exception as e:
            log.error(f"Error processing supplier product element from {context_url}: {e}")
            return None

    async def _get_product_details(self, product_url: str, title: str, supplier_name: str, category_url_source: str) -> Optional[Dict[str, Any]]:
        """
        Second step: Extract detailed product information by visiting the product page.
        Relies on ConfigurableSupplierScraper.
        """
        try:
            log.info(f"Getting detailed info for product: {title} from {product_url}")
            product_html = await self.web_scraper.get_page_content(product_url)
            if not product_html:
                log.warning(f"Failed to get content from {product_url}. Skipping.")
                return None
            
            soup = BeautifulSoup(product_html, 'html.parser')
            
            # ConfigurableSupplierScraper methods will use product_url to load correct selectors
            # Price might be more accurately extracted from the product page
            price = await self.web_scraper.extract_price(soup, product_html, product_url)
            image_url = await self.web_scraper.extract_image(soup, product_html, product_url, urlparse(product_url).scheme + "://" + urlparse(product_url).netloc) # type: ignore
            # CRITICAL FIX: Extract EAN/Barcode first, only fall back to SKU if EAN not available
            # Priority: EAN/Barcode -> UPC -> SKU (as fallback)
            ean = None
            upc = None
            sku = None
            
            # First try to extract EAN/Barcode using the specific method
            try:
                ean = self.web_scraper.extract_ean(soup, product_url)
                if ean:
                    log.info(f"✅ EAN extracted successfully: {ean}")
            except Exception as e:
                log.warning(f"EAN extraction failed: {e}")
            
            # If no EAN found, try the generic identifier method as fallback
            if not ean:
                identifier = await self.web_scraper.extract_identifier(soup, product_html, product_url)
                if identifier:
                    # Check if identifier looks like an EAN (8-14 digits)
                    cleaned_id = re.sub(r'[^0-9]', '', identifier)
                    if cleaned_id and len(cleaned_id) in [8, 12, 13, 14]:
                        ean = cleaned_id
                        log.info(f"✅ EAN extracted from identifier: {ean}")
                    else:
                        # Store as SKU if not EAN format
                        sku = identifier
                        log.info(f"⚠️ SKU extracted (no EAN found): {sku}")
            
            log.info(f"Final extraction for {product_url}: EAN={ean}, UPC={upc}, SKU={sku}")

            # Battery filtering - exclude battery products
            if self._is_battery_product(title):
                log.debug(f"Excluding battery product from detailed extraction: {title}")
                return None

            # TODO: Extract other details like description, brand, etc., using self.web_scraper
            # and selectors defined in the supplier's JSON config (e.g., "description_selector", "brand_selector")

            return {
                "title": title,  # Title from listing page is usually sufficient
                "price": price,  # Price from detail page might be more accurate
                "url": product_url,
                "image_url": image_url,  # Use proper null instead of "N/A"
                "ean": ean or "",  # Leave blank if no valid EAN found - DO NOT populate with SKU
                "upc": upc or "",
                "sku": sku or "",  # SKU separate from EAN
                "out_of_stock_badge": "",  # Will be populated by out of stock detection
                "source_supplier": supplier_name,
                "source_category_url": category_url_source,  # URL of the category page where it was found
                "extraction_timestamp": datetime.now().isoformat()
                # Add other details as extracted
            }
            
        except Exception as e:
            log.error(f"Error getting product details for {product_url}: {e}")
            return None
            
    def _extract_additional_details(self, soup: BeautifulSoup, html_content: str, product_url: str) -> Dict[str, Any]:
        """
        MODIFIED: To use ConfigurableSupplierScraper for extracting additional details.
        """
        additional_details = {}
        config = self.web_scraper._get_selectors_for_domain(product_url) # type: ignore

        desc_selectors = config.get("description_selector_product_page", config.get("description_selector"))
        if desc_selectors:
            desc_val = self.web_scraper._extract_with_selector(soup, desc_selectors if isinstance(desc_selectors, list) else [desc_selectors]) # type: ignore
            if desc_val: additional_details["description"] = desc_val.strip()
        
        brand_selectors = config.get("brand_selector_product_page", config.get("brand_selector"))
        if brand_selectors:
            brand_val = self.web_scraper._extract_with_selector(soup, brand_selectors if isinstance(brand_selectors, list) else [brand_selectors]) # type: ignore
            if brand_val: additional_details["brand"] = brand_val.strip()

        # Add more selectors from config as needed (e.g., model, dimensions, weight)
        # model_selectors = config.get("model_selector_product_page")
        # if model_selectors: ...
        return additional_details
            
    def _parse_price(self, price_text: str) -> Optional[float]:
        # This method is now primarily in ConfigurableSupplierScraper.
        # Keeping a version here for direct use if needed, or could call scraper's version.
        # For consistency, it's better if the scraper handles its own parsing.
        # However, the orchestrator might parse prices from Amazon data too.
        # The one in ConfigurableSupplierScraper is more advanced.
        if not price_text: return None
        try:
            cleaned_text = re.sub(r'(?:[£$€]|(?:[Ss]ale)|(?:[Ff]rom)|(?:[Nn]ow:?))\s*', '', price_text).strip()
            match = re.search(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)', cleaned_text)
            if match:
                price_str = match.group(1)
                if ',' in price_str and '.' not in price_str: price_str = price_str.replace(',', '.')
                elif ',' in price_str and '.' in price_str:
                    if price_str.rfind(',') > price_str.rfind('.'): price_str = price_str.replace('.', '').replace(',', '.')
                    else: price_str = price_str.replace(',', '')
                return float(price_str)
            return None
        except Exception: return None
            
    def _ensure_absolute_url(self, url: str, base_url: str) -> str:
        # This utility is also in ConfigurableSupplierScraper.
        # Could be a shared utility or rely on scraper's version.
        if url.startswith('//'): return 'https:' + url
        elif url.startswith('/'):
            parsed_base = urlparse(base_url)
            return f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
        elif not url.startswith(('http://', 'https://', 'data:')):
            return urljoin(base_url, url) # urljoin is more robust for relative paths
        return url

    def _calculate_roi_and_profit(self, combined_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate ROI and profit. FBACalculator usage is commented out."""
        metrics = {
            "supplier_cost_price": 0.0, "amazon_selling_price": 0.0,
            "estimated_amazon_fees": 0.0, "estimated_profit_per_unit": 0.0,
            "roi_percent_calculated": 0.0, "vat_on_purchase_estimated": 0.0,
            "vat_on_sale_estimated": 0.0, "costs_breakdown": {}, "revenue_breakdown": {},
            "estimated_monthly_sales": 0, # Initialize
            # "fba_calculator_result": {} # Commented out: Store FBA calculator results
        }
        try:
            supplier_price = combined_data["supplier_product_info"].get("price", 0.0)
            amazon_price = combined_data["amazon_product_info"].get("current_price", 0.0)
            if not isinstance(supplier_price, (int, float)) or not isinstance(amazon_price, (int, float)) or supplier_price <= 0 or amazon_price <= 0:
                log.warning("Cannot calculate ROI: Invalid or missing supplier or Amazon price.")
                return metrics

            metrics["supplier_cost_price"] = supplier_price
            metrics["amazon_selling_price"] = amazon_price
            
            # Prepare product data for FBA calculator - Original section commented out
            # amazon_info = combined_data["amazon_product_info"]
            # weight = self._extract_weight_pounds(amazon_info)
            # dimensions = self._extract_dimensions_inches(amazon_info)
            # category = self._determine_product_category(amazon_info)
            # fba_product_data = {
            #     'weight': weight,
            #     'dimensions': dimensions,
            #     'category': category,
            #     'price': amazon_price,
            #     'is_media': self._is_media_product(amazon_info),
            #     'monthly_units': 100  # Default estimate, will be updated later
            # }
            
            # Calculate FBA fees using the calculator - Original section commented out
            # fba_result = self.fba_calculator.calculate_fees(fba_product_data)
            # if fba_result.get('error'):
            #     log.warning(f"FBA calculator error: {fba_result['error']}. Falling back to estimation.")
            #     # Fallback to old estimation method
            #     fba_fee = self._estimate_fba_fee(amazon_info)
            #     referral_fee = amazon_price * 0.15  # Default 15%
            #     total_fees = fba_fee + referral_fee
            # else:
            #     # Use FBA calculator results
            #     fba_fee = fba_result['fulfillment_fee']
            #     referral_fee = fba_result['referral_fee']
            #     total_fees = fba_result['total_fees']
            #     metrics["fba_calculator_result"] = fba_result
            #     log.info(f"FBA Calculator - Size tier: {fba_result['size_tier']}, Total fees: £{total_fees:.2f}")

            # Placeholder for fees - assuming Keepa or other source will provide them
            # TODO: Integrate fee data from Keepa/SellerAmp directly from combined_data["amazon_product_info"]
            amazon_product_info = combined_data.get("amazon_product_info", {})
            keepa_data = amazon_product_info.get("keepa", {})
            
            referral_fee_text = keepa_data.get("Referral Fee based on current Buy Box price", "0")
            fba_pick_pack_fee_text = keepa_data.get("FBA Pick&Pack Fee", "0")
            
            try:
                referral_fee = float(str(referral_fee_text).replace("£", "").replace("€", "").replace("$", "").strip())
            except ValueError:
                referral_fee = amazon_price * 0.15 # Fallback if parsing fails
            try:
                fba_fee = float(str(fba_pick_pack_fee_text).replace("£", "").replace("€", "").replace("$", "").strip())
            except ValueError:
                fba_fee = 3.50 # Fallback if parsing fails

            total_fees = referral_fee + fba_fee
            log.info(f"Using fees from Keepa (or fallback): Referral Fee £{referral_fee:.2f}, FBA Fee £{fba_fee:.2f}, Total £{total_fees:.2f}")
            
            # VAT calculations
            vat_rate = 0.20 # UK VAT rate
            cost_ex_vat = supplier_price / (1 + vat_rate)
            metrics["vat_on_purchase_estimated"] = round(supplier_price - cost_ex_vat, 2)
            metrics["costs_breakdown"]["supplier_price_ex_vat"] = round(cost_ex_vat, 2)
            metrics["costs_breakdown"]["supplier_vat"] = metrics["vat_on_purchase_estimated"]
            
            amazon_price_ex_vat = amazon_price / (1 + vat_rate)
            metrics["vat_on_sale_estimated"] = round(amazon_price - amazon_price_ex_vat, 2)
            metrics["revenue_breakdown"]["amazon_price_incl_vat"] = amazon_price
            metrics["revenue_breakdown"]["amazon_price_ex_vat"] = round(amazon_price_ex_vat, 2)
            metrics["revenue_breakdown"]["amazon_vat"] = metrics["vat_on_sale_estimated"]
            
            # Update costs breakdown
            metrics["costs_breakdown"]["amazon_referral_fee"] = round(referral_fee, 2)
            metrics["costs_breakdown"]["fba_fee"] = round(fba_fee, 2)
            metrics["estimated_amazon_fees"] = round(total_fees, 2)
            
            # Calculate profit and ROI
            profit = amazon_price_ex_vat - cost_ex_vat - total_fees
            metrics["estimated_profit_per_unit"] = round(profit, 2)
            if cost_ex_vat > 0:
                metrics["roi_percent_calculated"] = round((profit / cost_ex_vat) * 100, 2)
            else:
                metrics["roi_percent_calculated"] = 0.0
            
            # --- MODIFIED: Sales Velocity Logic ---
            estimated_monthly_sales = 0
            # 1. Try SellerAmp text data for sales
            selleramp_info = combined_data["amazon_product_info"].get("selleramp", {})
            if selleramp_info.get("estimated_monthly_sales_from_text"):
                try:
                    selleramp_sales_text = str(selleramp_info["estimated_monthly_sales_from_text"])
                    match_sales = re.search(r'(\d+)', selleramp_sales_text)
                    if match_sales:
                        estimated_monthly_sales = int(match_sales.group(1))
                        log.info(f"Using SellerAmp text for estimated monthly sales: {estimated_monthly_sales}")
                except (ValueError, TypeError) as e:
                    log.warning(f"Could not parse SellerAmp sales text '{selleramp_info['estimated_monthly_sales_from_text']}': {e}")

            # 2. Fallback to AI Vision for SellerAmp sales
            if not estimated_monthly_sales and selleramp_info.get("estimated_monthly_sales_ai_vision"):
                try:
                    ai_vision_sales_text = str(selleramp_info["estimated_monthly_sales_ai_vision"])
                    match_sales_ai = re.search(r'(\d+)', ai_vision_sales_text)
                    if match_sales_ai:
                        estimated_monthly_sales = int(match_sales_ai.group(1))
                        log.info(f"Using AI Vision for SellerAmp estimated monthly sales: {estimated_monthly_sales}")
                except (ValueError, TypeError) as e:
                    log.warning(f"Could not parse AI Vision SellerAmp sales text '{ai_vision_sales_text}': {e}")
            
            # 3. Fallback to BSR-based estimation
            if not estimated_monthly_sales and combined_data["amazon_product_info"].get("sales_rank"):
                sales_rank = combined_data["amazon_product_info"]["sales_rank"]
                if isinstance(sales_rank, int) and sales_rank > 0: # Ensure valid rank
                    category = combined_data["amazon_product_info"].get("category", "")
                    estimated_monthly_sales = self._estimate_sales_from_bsr(sales_rank, category)
                    log.info(f"Using BSR-based estimated monthly sales: {estimated_monthly_sales}")
            
            if estimated_monthly_sales > 0:
                metrics["estimated_monthly_sales"] = estimated_monthly_sales
                metrics["estimated_monthly_profit"] = round(metrics["estimated_profit_per_unit"] * estimated_monthly_sales, 2)
            # --- END MODIFIED Sales Velocity Logic ---
            
            log.debug(f"Financials for '{combined_data['amazon_product_info'].get('title')}': Cost (exVAT): {cost_ex_vat:.2f}, Sell (exVAT): {amazon_price_ex_vat:.2f}, Fees: {total_fees:.2f}, Profit: {profit:.2f}, ROI: {metrics['roi_percent_calculated']}%")
        except Exception as e: log.error(f"Error calculating ROI & profit: {e}", exc_info=True)
        return metrics

    def _extract_weight_pounds(self, amazon_data: Dict[str, Any]) -> float:
        """Extract product weight in pounds from Amazon data."""
        default_weight = 1.0  # Default weight if not found
        
        # Try weight from details
        weight_str = amazon_data.get("weight_from_details", "")
        if weight_str and isinstance(weight_str, str):
            weight_match = re.search(r"([\d,.]+)\s*(kg|g|oz|pounds|lbs|lb)", weight_str, re.IGNORECASE)
            if weight_match:
                weight_val = float(weight_match.group(1).replace(',', '.'))
                unit = weight_match.group(2).lower()
                if 'kg' in unit:
                    return weight_val * 2.20462  # kg to pounds
                elif 'g' in unit:
                    return weight_val * 0.00220462  # g to pounds
                elif 'oz' in unit:
                    return weight_val * 0.0625  # oz to pounds
                elif 'lb' in unit or 'pound' in unit:
                    return weight_val
        
        # Try Keepa data
        if amazon_data.get("keepa") and amazon_data["keepa"].get("product_details_tab_data"):
            keepa_details = amazon_data["keepa"]["product_details_tab_data"]
            for key, val in keepa_details.items():
                if "weight" in key.lower() and isinstance(val, (int, float, str)):
                    try:
                        # Parse weight from Keepa
                        weight_str = str(val)
                        weight_match = re.search(r"([\d,.]+)", weight_str)
                        if weight_match:
                            return float(weight_match.group(1).replace(',', '.'))
                    except:
                        pass
        
        return default_weight

    def _extract_dimensions_inches(self, amazon_data: Dict[str, Any]) -> Tuple[float, float, float]:
        """Extract product dimensions in inches from Amazon data."""
        default_dimensions = (10.0, 8.0, 6.0)  # Default dimensions if not found
        
        # Try dimensions from details
        dimensions_str = amazon_data.get("dimensions_from_details", "")
        if dimensions_str and isinstance(dimensions_str, str):
            # Look for pattern like "10 x 8 x 6 inches" or "25 x 20 x 15 cm"
            dim_match = re.search(r"([\d,.]+)\s*x\s*([\d,.]+)\s*x\s*([\d,.]+)\s*(inches|inch|in|cm|centimeters|centimetres)?", dimensions_str, re.IGNORECASE)
            if dim_match:
                length = float(dim_match.group(1).replace(',', '.'))
                width = float(dim_match.group(2).replace(',', '.'))
                height = float(dim_match.group(3).replace(',', '.'))
                unit = dim_match.group(4).lower() if dim_match.group(4) else "inches"
                
                if 'cm' in unit or 'centimeter' in unit or 'centimetre' in unit:
                    # Convert cm to inches
                    length = length * 0.393701
                    width = width * 0.393701
                    height = height * 0.393701
                
                return (length, width, height)
        
        # Try Keepa data
        if amazon_data.get("keepa") and amazon_data["keepa"].get("product_details_tab_data"):
            keepa_details = amazon_data["keepa"]["product_details_tab_data"]
            for key, val in keepa_details.items():
                if "dimension" in key.lower() and isinstance(val, str):
                    # Try to parse dimensions from Keepa
                    dim_match = re.search(r"([\d,.]+)\s*x\s*([\d,.]+)\s*x\s*([\d,.]+)", val)
                    if dim_match:
                        return (
                            float(dim_match.group(1).replace(',', '.')),
                            float(dim_match.group(2).replace(',', '.')),
                            float(dim_match.group(3).replace(',', '.'))
                        )
        
        return default_dimensions

    def _determine_product_category(self, amazon_data: Dict[str, Any]) -> str:
        """Determine product category for FBA fee calculation."""
        # Try to extract category from Amazon data
        category = amazon_data.get("category", "").lower()
        
        # Map Amazon categories to FBA calculator categories
        category_mapping = {
            'electronics': 'electronics',
            'computers': 'computers',
            'video games': 'video_games',
            'books': 'books',
            'music': 'music',
            'dvd': 'dvd',
            'toys': 'toys',
            'games': 'games',
            'home': 'home',
            'kitchen': 'kitchen',
            'sports': 'sports',
            'outdoors': 'outdoors',
            'tools': 'tools',
            'grocery': 'grocery',
            'health': 'health',
            'beauty': 'beauty',
            'clothing': 'clothing',
            'shoes': 'shoes',
            'jewelry': 'jewelry',
            'watches': 'watches'
        }
        
        # Check if any category keyword matches
        for keyword, fba_category in category_mapping.items():
            if keyword in category:
                return fba_category
        
        return 'default'  # Default category

    def _is_media_product(self, amazon_data: Dict[str, Any]) -> bool:
        """Determine if product is a media item (books, music, DVD, etc.)."""
        category = amazon_data.get("category", "").lower()
        title = amazon_data.get("title", "").lower()
        
        media_keywords = ['book', 'music', 'dvd', 'blu-ray', 'cd', 'vinyl', 'audiobook', 'ebook']
        
        return any(keyword in category or keyword in title for keyword in media_keywords)

    def _estimate_fba_fee(self, amazon_product_data: Dict[str, Any]) -> float:
        """Legacy FBA fee estimation method - kept as fallback."""
        default_fba_fee = 3.50
        
        # This is the simplified version - the FBA calculator provides more accurate fees
        weight = self._extract_weight_pounds(amazon_product_data)
        dimensions = self._extract_dimensions_inches(amazon_product_data)
        
        # Simple size-based estimation
        volume = dimensions[0] * dimensions[1] * dimensions[2]
        if volume < 100 and weight < 1:
            return 2.50  # Small item
        elif volume < 500 and weight < 5:
            return 3.50  # Medium item
        elif volume < 1000 and weight < 20:
            return 5.00  # Large item
        else:
            return 8.00  # Oversize item

    def _normalize_title_for_similarity(self, title: str) -> str:
        if not title: return ""
        title_lower = title.lower()
        # Remove common words and punctuation
        common_words = ["the", "a", "an", "and", "or", "for", "with", "in", "of", "at", "by", "from", "to", "pack", "of", "new", "set"]
        title_no_punc = re.sub(r'[^\w\s]', ' ', title_lower) # Replace non-alphanumeric with space
        words = title_no_punc.split()
        # Filter out common words and very short words (e.g., single characters if not numbers)
        normalized_words = [word for word in words if word not in common_words and (len(word) > 1 or word.isdigit())]
        return " ".join(normalized_words)

    async def _validate_product_match(self, supplier_product: Dict[str, Any], amazon_product: Dict[str, Any]) -> Dict[str, Any]:
        validation: Dict[str, Any] = { # Added type hint
            "match_quality": "low", # Default to low
            "confidence_score": 0.0, # Use a numeric score
            "reasons": [],
            "checks_performed": []
        }

        supplier_title = supplier_product.get("title", "")
        amazon_title = amazon_product.get("title", "")
        supplier_ean = supplier_product.get("ean")
        amazon_ean_on_page = amazon_product.get("ean_on_page") # EAN found on Amazon page by AmazonExtractor
        
        supplier_brand = str(supplier_product.get("brand", "")).lower().strip() # Ensure string and normalize
        amazon_brand = str(amazon_product.get("brand", "")).lower().strip() # Ensure string and normalize

        max_score = 1.0 
        current_score = 0.0

        # Check 1: EAN/UPC Match (Highest Confidence)
        amazon_gtin_for_match = amazon_ean_on_page # or amazon_product.get("upc") if available
        
        if supplier_ean and amazon_gtin_for_match:
            validation["checks_performed"].append("EAN/GTIN")
            if str(supplier_ean) == str(amazon_gtin_for_match):
                current_score += 0.6 
                validation["reasons"].append(f"EAN exact match: {supplier_ean}")
            else:
                validation["reasons"].append(f"EAN mismatch: Supplier EAN {supplier_ean}, Amazon EAN {amazon_gtin_for_match}")
                current_score -= 0.2 
        elif supplier_ean:
             validation["checks_performed"].append("EAN/GTIN")
             validation["reasons"].append(f"Supplier EAN {supplier_ean} present, but no comparable EAN/GTIN found on Amazon product page.")

        # Check 2: Brand Match
        if supplier_brand and amazon_brand: # Both must exist
            validation["checks_performed"].append("Brand")
            brand_similarity = difflib.SequenceMatcher(None, supplier_brand, amazon_brand).ratio()
            if brand_similarity >= 0.85: 
                current_score += 0.25 
                validation["reasons"].append(f"Brand match (Similarity: {brand_similarity:.2f}): '{supplier_brand}' vs '{amazon_brand}'")
            else:
                validation["reasons"].append(f"Brand mismatch or low similarity (Similarity: {brand_similarity:.2f}): Supplier '{supplier_brand}', Amazon '{amazon_brand}'")
        elif supplier_brand or amazon_brand: 
            validation["checks_performed"].append("Brand")
            validation["reasons"].append(f"Brand information incomplete: Supplier '{supplier_brand}', Amazon '{amazon_brand}'")

        # Check 3: Title Similarity
        if supplier_title and amazon_title:
            validation["checks_performed"].append("Title")
            norm_supplier_title = self._normalize_title_for_similarity(supplier_title)
            norm_amazon_title = self._normalize_title_for_similarity(amazon_title)
            
            title_similarity = difflib.SequenceMatcher(None, norm_supplier_title, norm_amazon_title).ratio()
            validation["title_similarity_score"] = round(title_similarity, 3)

            if title_similarity >= 0.75: 
                current_score += 0.15 
                validation["reasons"].append(f"High title similarity ({title_similarity:.2%})")
            elif title_similarity >= 0.5: 
                current_score += 0.05
                validation["reasons"].append(f"Medium title similarity ({title_similarity:.2%})")
            else: 
                validation["reasons"].append(f"Low title similarity ({title_similarity:.2%})")
                current_score -= 0.1

        validation["confidence_score"] = max(0, min(current_score, max_score)) 

        if validation["confidence_score"] >= 0.75: 
            validation["match_quality"] = "high"
        elif validation["confidence_score"] >= 0.45: 
            validation["match_quality"] = "medium"
        else:
            validation["match_quality"] = "low"

        if validation["match_quality"] == "medium" and self.ai_client:
            log.info(f"Match quality is medium ({validation['confidence_score']:.2f}) for ASIN {amazon_product.get('asin')}. Attempting AI validation.")
            try:
                prompt = (
                    f"Assess if the following two products are likely the same. Respond with only 'MATCH', 'MISMATCH', or 'UNCERTAIN'.\n\n"
                    f"Supplier Product:\nTitle: {supplier_title}\nBrand: {supplier_product.get('brand', 'N/A')}\nEAN: {supplier_ean or 'N/A'}\nPrice: {supplier_product.get('price', 'N/A')}\nDescription: {str(supplier_product.get('description', 'N/A'))[:200]}...\n\n"
                    f"Amazon Product:\nTitle: {amazon_title}\nBrand: {amazon_product.get('brand', 'N/A')}\nASIN: {amazon_product.get('asin', 'N/A')}\nEAN on Page: {amazon_ean_on_page or 'N/A'}\nPrice: {amazon_product.get('current_price', 'N/A')}\nDescription: {str(amazon_product.get('description', 'N/A'))[:200]}...\nFeatures: {str(amazon_product.get('features', []))[:200]}..."
                )
                
                # Ensure ai_client is not None before calling create
                if self.ai_client:
                    chat_completion = await asyncio.to_thread(
                        self.ai_client.chat.completions.create, # type: ignore
                        model=OPENAI_MODEL_NAME, 
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1,
                        max_tokens=10
                    )
                    ai_decision = chat_completion.choices[0].message.content.strip().upper() # type: ignore
                    validation["ai_validation_decision"] = ai_decision
                    validation["reasons"].append(f"AI Validation: {ai_decision}")

                    if ai_decision == "MATCH" and validation["match_quality"] == "medium":
                        validation["match_quality"] = "high" 
                        validation["confidence_score"] = max(validation["confidence_score"], 0.80) 
                    elif ai_decision == "MISMATCH":
                        validation["match_quality"] = "low" 
                        validation["confidence_score"] = min(validation["confidence_score"], 0.20) 
                else:
                    validation["reasons"].append("AI validation skipped: AI client not available.")
            except Exception as ai_err:
                log.error(f"AI validation step failed: {ai_err}")
                validation["reasons"].append(f"AI validation error: {str(ai_err)[:100]}") # Truncate long errors
        
        validation["confidence_score"] = max(0, min(validation["confidence_score"], 1.0))
        return validation

    def _estimate_sales_from_bsr(self, rank: int, category: str = "") -> int:
        if not isinstance(rank, int) or rank < 1: return 0 # Added type check
        category_lower = category.lower() if category else "" # Ensure lowercase
        cat_multipliers = {
            ("books", "kindle", "ebook"): 0.5, ("electronics", "computers", "technology"): 1.2,
            ("toys", "games"): 1.5, ("grocery", "food", "consumable"): 2.0,
            ("beauty", "health"): 1.8, ("home", "kitchen", "garden"): 1.3
        }
        multiplier = 1.0
        for terms, mult in cat_multipliers.items():
            if any(term in category_lower for term in terms): multiplier = mult; break
        
        if rank < 100: return int(3000 * multiplier)
        elif rank < 500: return int(1000 * multiplier)
        elif rank < 1000: return int(500 * multiplier)
        elif rank < 5000: return int(100 * multiplier)
        elif rank < 10000: return int(50 * multiplier)
        elif rank < 50000: return int(20 * multiplier)
        elif rank < 100000: return int(10 * multiplier)
        else: return int(5 * multiplier)

    def _is_product_meeting_criteria(self, combined_data: Dict[str, Any]) -> bool:
        try:
            if combined_data.get("roi_percent_calculated", 0.0) < MIN_ROI_PERCENT:
                log.debug(f"Criteria Fail (ROI): {combined_data.get('roi_percent_calculated')}% < {MIN_ROI_PERCENT}%")
                return False
            # MODIFIED: Use MIN_PROFIT_PER_UNIT
            if combined_data.get("estimated_profit_per_unit", 0.0) < MIN_PROFIT_PER_UNIT:
                log.debug(f"Criteria Fail (Profit): £{combined_data.get('estimated_profit_per_unit')} < £{MIN_PROFIT_PER_UNIT}")
                return False
            
            rating = combined_data["amazon_product_info"].get("rating", 0.0)
            if not isinstance(rating, (int, float)): rating = 0.0 # Ensure numeric
            if combined_data["amazon_product_info"].get("rating_ai_fallback"):
                try: rating = float(combined_data["amazon_product_info"]["rating_ai_fallback"])
                except (ValueError, TypeError): pass
            if rating < MIN_RATING:
                log.debug(f"Criteria Fail (Rating): {rating} < {MIN_RATING}")
                return False
            
            review_count = combined_data["amazon_product_info"].get("review_count", 0)
            if not isinstance(review_count, int): review_count = 0 # Ensure int
            if combined_data["amazon_product_info"].get("review_count_ai_fallback"):
                try: review_count = int(re.sub(r'[^\d]', '', str(combined_data["amazon_product_info"]["review_count_ai_fallback"])))
                except (ValueError, TypeError): pass
            if review_count < MIN_REVIEWS:
                log.debug(f"Criteria Fail (Reviews): {review_count} < {MIN_REVIEWS}")
                return False

            sales_rank = combined_data["amazon_product_info"].get("sales_rank", float('inf'))
            if not isinstance(sales_rank, int): sales_rank = float('inf') # Ensure numeric or inf
            if sales_rank == 0 or sales_rank > MAX_SALES_RANK: 
                log.debug(f"Criteria Fail (Sales Rank): {sales_rank} > {MAX_SALES_RANK} or 0")
                return False
            
            in_stock = combined_data["amazon_product_info"].get("in_stock", False)
            if not in_stock:
                availability_ai = combined_data["amazon_product_info"].get("availability_ai_fallback")
                if availability_ai and isinstance(availability_ai, str) and any(s in availability_ai.lower() for s in ["in stock", "add to cart"]):
                    in_stock = True
                else:
                    log.debug("Criteria Fail (Stock): Not in stock or availability unknown")
                    return False
            
            if combined_data["amazon_product_info"].get("sold_by_amazon", False):
                log.debug("Criteria Fail: Product is sold directly by Amazon")
                return False
            if not combined_data["amazon_product_info"].get("main_image"):
                log.debug("Criteria Fail: No product image available")
                return False
            
            log.info(f"Product '{combined_data['amazon_product_info'].get('title')}' meets all criteria.")
            return True
        except Exception as e:
            log.error(f"Error checking product criteria: {e}", exc_info=True)
            return False

    def _passes_quick_triage(self, supplier_price: float, amazon: dict) -> bool:
        """Quick pre-filter that checks if a product meets basic ROI and net profit criteria.
        
        This filter runs before the heavy financial calculations but after the full Amazon scrape
        so that Keepa fees are available.
        
        Args:
            supplier_price (float): The price of the product from the supplier
            amazon (dict): The Amazon product data with Keepa info
            
        Returns:
            bool: True if the product meets the criteria, False otherwise
        """
        # Check for battery products first
        title = amazon.get("title", "")
        if is_battery_title(title):
            log.debug("⚡ Battery product filtered in triage → %s", title[:60])
            return False
            
        fee = (amazon.get("keepa", {}).get("Referral Fee based on current Buy Box price", 0) 
               + amazon.get("keepa", {}).get("FBA Pick&Pack Fee", 0))
        buy_box = amazon.get("current_price") or 0
        if buy_box == 0:
            return True  # skip if price unknown
        net = buy_box - fee - supplier_price
        roi = net / supplier_price * 100 if supplier_price > 0 else 0
        return net >= 3 and roi >= 35

    async def _save_linking_map_batch(self) -> Path:
        """
        Save linking map buffer using LinkingMapWriter in proper array format.
        Clears buffer after successful save.
        
        Returns:
            Path to saved linking map file
        """
        if not self._linking_map_buffer:
            log.debug("No linking map entries in buffer to save")
            return None
            
        try:
            # Get current supplier name for proper run output directory
            supplier_name = getattr(self, '_current_supplier_name', 'unknown-supplier')
            
            # Use LinkingMapWriter to save in array format
            linking_map_path = self.linking_map_writer.write_linking_map(
                supplier_name=supplier_name,
                linking_results=self._linking_map_buffer
            )
            
            log.info(f"🔗 Saved {len(self._linking_map_buffer)} linking entries to {linking_map_path}")
            
            # Clear buffer after successful save
            self._linking_map_buffer.clear()
            
            return linking_map_path
            
        except Exception as e:
            log.error(f"Failed to save linking map batch: {e}")
            raise

    # OLD: _save_linking_map method removed in favor of _save_linking_map_batch using LinkingMapWriter

    def _save_product_cache(self):
        """
        PHASE 4 FIX: Product cache periodic save implementation.
        Saves current extracted products to prevent data loss during long-running processes.
        """
        try:
            if not self._current_extracted_products or not self._current_supplier_cache_path:
                log.debug("No current products or cache path available for periodic save")
                return
                
            # Use the existing _save_products_to_cache method for consistency
            self._save_products_to_cache(
                self._current_extracted_products, 
                self._current_supplier_cache_path
            )
            
            log.info(f"🔄 PRODUCT CACHE periodic save: {len(self._current_extracted_products)} products saved to {os.path.basename(self._current_supplier_cache_path)}")
            
        except Exception as e:
            log.error(f"Error in _save_product_cache periodic save: {e}")

async def run_workflow_main():
    """
    Main entry point for the passive extraction workflow.
    Orchestrates cache clearing, workflow execution, and cleanup.
    """
    results = [] # Initialize results variable
    workflow_instance = None
    ai_client = None
    log.info("Initializing Passive Extraction Workflow...")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Amazon FBA Passive Extraction Workflow')
    parser.add_argument('--max-products', type=int, default=0, help='Maximum number of products to process (default: 0 = unlimited with rate limiting)')
    parser.add_argument('--supplier-url', default=DEFAULT_SUPPLIER_URL, help=f'Supplier website URL (default: {DEFAULT_SUPPLIER_URL})')
    parser.add_argument('--supplier-name', '--supplier', default=DEFAULT_SUPPLIER_NAME, help=f'Supplier name (default: {DEFAULT_SUPPLIER_NAME})')
    parser.add_argument('--min-price', type=float, default=0.1, help='Minimum supplier product price in GBP (default: 0.1)')
    parser.add_argument('--force-config-reload', action='store_true', help='Force reload supplier configuration and clear cache')
    parser.add_argument('--debug-smoke', action='store_true', help='Inject debug product for end-to-end testing')
    parser.add_argument('--enable-quick-triage', action='store_true', help='Enable quick ROI/net-profit gate before financial calculations')
    parser.add_argument('--headless', type=lambda x: x.lower() in ['true', '1'], default=True, help='Run browser in headless mode (default: true)')
    
    args = parser.parse_args()
    
    max_products = args.max_products
    supplier_url = args.supplier_url
    supplier_name = args.supplier_name
    min_price = args.min_price
    force_config_reload = args.force_config_reload
    debug_smoke = args.debug_smoke
    enable_quick_triage = args.enable_quick_triage
    headless = args.headless

    # Load system configuration for cache settings
    # Use same robust path resolution as _load_openai_config
    script_dir = os.path.dirname(os.path.abspath(__file__))
    possible_config_paths = [
        os.path.join(script_dir, "config", "system_config.json"),
        os.path.join(os.path.dirname(script_dir), "config", "system_config.json"),
        os.path.join(os.path.dirname(os.path.dirname(script_dir)), "config", "system_config.json"),
        os.path.join(os.getcwd(), "config", "system_config.json")
    ]

    config_path = None
    for path in possible_config_paths:
        if os.path.exists(path):
            config_path = path
            break

    if not config_path:
        log.warning(f"system_config.json not found in any of: {possible_config_paths}")
        config_path = possible_config_paths[1]  # Use parent directory as fallback for tools location
    max_products_per_category_cfg = 0
    max_analyzed_products_cfg = 0
    max_products_per_cycle_cfg = 0
    linking_map_batch_size = 40  # Default fallback
    financial_report_batch_size = 50  # Default fallback
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            system_config = json.load(f)
        log.info(f"Loaded system config from {config_path}")
        max_products_per_category_cfg = system_config.get("system", {}).get("max_products_per_category", 0)
        max_analyzed_products_cfg = system_config.get("system", {}).get("max_analyzed_products", 0)
        max_products_per_cycle_cfg = system_config.get("system", {}).get("max_products_per_cycle", 0)
        linking_map_batch_size = system_config.get("system", {}).get("linking_map_batch_size", 40)
        financial_report_batch_size = system_config.get("system", {}).get("financial_report_batch_size", 50)
        force_ai_scraping = system_config.get("system", {}).get("force_ai_scraping", False)
        selective_cache_clear = system_config.get("system", {}).get("selective_cache_clear", False)
        log.info(f"Batch sizes configured: linking_map={linking_map_batch_size}, financial_report={financial_report_batch_size}")
        log.info(f"Config flags: force_ai_scraping={force_ai_scraping}, selective_cache_clear={selective_cache_clear}")
        if max_products == 0:
            max_products = max_products_per_cycle_cfg

    except Exception as e:
        log.warning(f"Failed to load system config from {config_path}: {e}")
        system_config = {}

    # Initialize CacheManager and clear caches if configured
    cache_cleared = False
    supplier_cache_cleared = False
    
    # Get cache configuration settings - simplified approach
    clear_cache_setting = system_config.get("system", {}).get("clear_cache", False)
    force_ai_suggestion_config = system_config.get("system", {}).get("force_ai_category_suggestion", False)

    # Simple cache clearing logic: only clear if explicitly requested
    cache_cleared = False
    supplier_cache_cleared = False

    if clear_cache_setting:
        log.info("System config: clear_cache=True, performing cache clear")
        try:
            # Simple cache clearing - delete supplier cache files directly
            from pathlib import Path

            cache_dirs = [
                Path('OUTPUTS/cached_products'),
                # Path('OUTPUTS/FBA_ANALYSIS/amazon_cache'),  # PRESERVED: Amazon cache disabled from clearing (consistent with line 2087)
            ]

            files_removed = 0
            for cache_dir in cache_dirs:
                if cache_dir.exists():
                    for cache_file in cache_dir.glob('*.json'):
                        try:
                            cache_file.unlink()
                            files_removed += 1
                            log.info(f"Removed cache file: {cache_file}")
                        except Exception as e:
                            log.warning(f"Could not remove {cache_file}: {e}")

            log.info(f"Cache clearing completed. Removed {files_removed} files.")
            cache_cleared = True
            supplier_cache_cleared = True
            force_config_reload = True

        except Exception as e:
            log.error(f"Error during cache clearing: {e}")

    # CRITICAL FIX 2: Clear failed Keepa extractions if configured
    clear_failed_extractions_setting = system_config.get("system", {}).get("clear_failed_extractions", False)
    if clear_failed_extractions_setting:
        log.info("System config: clear_failed_extractions=True, clearing failed Keepa extractions")
        try:
            # Create a temporary workflow instance to access the method
            temp_workflow = PassiveExtractionWorkflow(chrome_debug_port=9222, ai_client=ai_client, max_cache_age_hours=336, min_price=min_price, headless=headless, linking_map_batch_size=linking_map_batch_size, financial_report_batch_size=financial_report_batch_size, force_ai_scraping=force_ai_scraping, selective_cache_clear=selective_cache_clear)
            await temp_workflow._clear_failed_keepa_extractions()
        except Exception as e:
            log.error(f"Error clearing failed Keepa extractions: {e}")
            # Continue anyway
            supplier_cache_cleared = False

    if OPENAI_API_KEY:
        try:
            ai_client = OpenAI(api_key=OPENAI_API_KEY)
            log.info(f"OpenAI client initialized with model {OPENAI_MODEL_NAME}")
        except Exception as e: 
            log.error(f"Failed to initialize OpenAI client: {e}")
    
    workflow_instance = PassiveExtractionWorkflow(chrome_debug_port=9222, ai_client=ai_client, max_cache_age_hours=336, min_price=min_price, headless=headless, linking_map_batch_size=linking_map_batch_size, financial_report_batch_size=financial_report_batch_size, force_ai_scraping=force_ai_scraping, selective_cache_clear=selective_cache_clear)
    workflow_instance.enable_quick_triage = enable_quick_triage
    
    # Force AI category progression if supplier cache was cleared OR if force_ai_scraping is enabled
    if (supplier_cache_cleared or force_ai_scraping) and ai_client:
        log.info("Forcing AI category progression due to supplier cache clearing or explicit config setting.")
        workflow_instance.force_ai_category_progression = True
    else:
        workflow_instance.force_ai_category_progression = False
    
    try:
        log_message = f"Running workflow for {supplier_name} with max {max_products} products. Price range £{min_price}-£{MAX_PRICE}."
        if enable_quick_triage:
            log_message += " Quick triage enabled."
        log.info(log_message)
        if force_config_reload:
            log.info("Force config reload enabled - supplier cache cleared")
        if debug_smoke:
            log.info("Debug smoke test enabled - will inject test product")
        
        # Assign the output of workflow_instance.run() to the results variable
        results = await workflow_instance.run(
            supplier_url=supplier_url,
            supplier_name=supplier_name,
            max_products_to_process=max_products,
            max_products_per_category=max_products_per_category_cfg,
            max_analyzed_products=max_analyzed_products_cfg,
            cache_supplier_data=True,
            force_config_reload=force_config_reload,
            debug_smoke=debug_smoke,
            resume_from_last=True,
        )
        
        if results: 
            log.info(f"Workflow completed. Found {len(results)} potentially profitable products.")
        else: 
            log.info("Workflow completed. No profitable products found.")

        # REMOVED the two redundant and problematic blocks that called FBA_Financial_calculator.run_calculations
        # The call to FBA_Financial_calculator.run_calculations is correctly handled
        # at the end of the PassiveExtractionWorkflow.run() method.

        return results # Return the actual results from the workflow instance

    except Exception as e:
        log.critical(f"Unhandled exception in main workflow execution: {e}", exc_info=True)
        return results # Return current results (likely empty) on critical failure
    finally:
        try:
            if hasattr(workflow_instance, 'extractor') and workflow_instance.extractor and \
               hasattr(workflow_instance.extractor, 'browser') and workflow_instance.extractor.browser and \
               workflow_instance.extractor.browser.is_connected(): # type: ignore
                # Keeping connection open is by design for FixedAmazonExtractor
                log.info("Amazon extractor browser connection intended to be kept open.")
                # await workflow_instance.extractor.close() # Uncomment to explicitly close
        except Exception as e:
            log.error(f"Error during extractor cleanup check: {e}")
        try:
            if hasattr(workflow_instance, 'web_scraper') and workflow_instance.web_scraper:
                await workflow_instance.web_scraper.close_session()
                log.info("Web scraper session closed.")
        except Exception as e:
            log.error(f"Error closing web scraper: {e}")
        log.info("Main workflow execution finished.")

if __name__ == "__main__":
    # Global OPENAI_KEY guard
    if not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = (
            "sk-15Mk5F_Nvf8k06VvEi4_TD2GhL8mQnqR_8I6Z2zHjWT3BlbkFJvKlNwbgLB_HPw1C-SixqIskN03to4PNyXnXedS-pMA"
        )
        logging.warning("OPENAI_API_KEY missing – using fallback test key")
    
    print("="*80)
    print(f"Amazon FBA Passive Extraction Workflow")
    print(f"Version: 1.0.3 - {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print(f"Using FixedAmazonExtractor for improved extension compatibility.")
    print(f"Profitability Criteria: Min ROI {MIN_ROI_PERCENT}%, Min Profit £{MIN_PROFIT_PER_UNIT}")
    print("="*80)
    asyncio.run(run_workflow_main())
