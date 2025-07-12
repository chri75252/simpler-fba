"""
Passive extraction workflow for Amazon FBA products from supplier websites.
MODIFIED: To integrate ConfigurableSupplierScraper, Zero-Token Triage,
enhanced product validation, and updated sales velocity logic.
Uses Chrome with debug port for Amazon data (via AmazonExtractor) and a
configurable web scraper for supplier sites.
Integrates AI client for enhanced extraction capabilities and optimizes data processing.
"""

import os
import asyncio
import logging
import json
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import re
import time
import xml.etree.ElementTree as ET
import requests
from urllib.parse import urlparse, parse_qs, urljoin
import difflib # Added for enhanced title similarity

# Assuming OpenAI client; ensure it's installed: pip install openai
from openai import OpenAI
# For enhanced HTML parsing
from bs4 import BeautifulSoup

# Import required custom modules
# FIXED: Change relative imports to absolute imports when running as standalone script
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from amazon_playwright_extractor import AmazonExtractor # Base class for FixedAmazonExtractor
# MODIFIED: Use ConfigurableSupplierScraper
from configurable_supplier_scraper import ConfigurableSupplierScraper
# MODIFIED: Import triage module - COMMENTED OUT PER REQUIREMENTS
# from zero_token_triage_module import perform_zero_token_triage

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

# ──────────────────────── ①  Add priority patterns (top of file) ──────────────────────
FBA_FRIENDLY_PATTERNS = {
    "home_kitchen":      ["home","kitchen","dining","storage","decor","organization"],  # P#1
    "pet_supplies":      ["pet","dog","cat","animal","bird","aquarium"],               # P#2
    "beauty_care":       ["beauty","personal","skincare","grooming","cosmetic"],       # P#3
    "sports_outdoor":    ["sport","fitness","camping","outdoor","exercise","yoga"],    # P#4
    "office_stationery": ["office","stationery","desk","paper","business"],            # P#5
    "diy_tools":         ["diy","tool","hardware","hand-tool","craft","workshop"],      # P#6
    "baby_nursery":      ["baby","infant","nursery","toddler","child-safe"],            # P#7
}
FBA_AVOID_PATTERNS = {
    "dangerous_goods": ["battery","power","lithium","flammable","hazmat"],
    "electronics":     ["electronic","tech","computer","phone","gadget","digital"],
    "clothing":        ["clothing","fashion","apparel","shoe","sock","wear"],
    "medical":         ["medical","pharma","medicine","healthcare","therapeutic"],
    "food":            ["food","beverage","grocery","snack","drink","edible"],
    "large_bulky":     ["appliance","sofa","mattress","wardrobe","furniture"],
    "high_value":      ["jewelry","jewellery","watch","precious","gold","diamond"],
}

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

# Initial constants and paths
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "C:\\Users\\chris\\Amazon-FBA-Agent-System\\OUTPUTS\\FBA_ANALYSIS")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Global constant for persistent linking map in dedicated directory
LINKING_MAP_DIR = r"C:\Users\chris\Amazon-FBA-Agent-System\OUTPUTS\FBA_ANALYSIS\Linking map"
os.makedirs(LINKING_MAP_DIR, exist_ok=True)
LINKING_MAP_PATH = os.path.join(LINKING_MAP_DIR, "linking_map.json")

# Other directories
SUPPLIER_CACHE_DIR = os.path.join(OUTPUT_DIR, "supplier_cache")
AMAZON_CACHE_DIR = os.path.join(OUTPUT_DIR, "amazon_cache")
AI_CATEGORY_CACHE_DIR = os.path.join(OUTPUT_DIR, "ai_category_cache")
os.makedirs(SUPPLIER_CACHE_DIR, exist_ok=True)
os.makedirs(AMAZON_CACHE_DIR, exist_ok=True)
os.makedirs(AI_CATEGORY_CACHE_DIR, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-1SaPo0zJ5L5iww9DRzXvsYe1YZKc2-9b6ajA2PfBXOT3BlbkFJZG72hYLIvwHl6jBxRuZANQoREAEDxx2Xos-xG7Ho0A")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

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
    def __init__(self, chrome_debug_port: int = 9222, ai_client: Optional[OpenAI] = None, max_cache_age_hours: int = 168, min_price: float = 0.1):
        self.min_price = min_price
        self.used_ai_client = ai_client
        self.enable_quick_triage = False  # Default to False, can be enabled via CLI flag
        self.last_processed_index = 0  # Initialize index tracker for resume feature
        if not self.used_ai_client and OPENAI_API_KEY:
            try:
                self.used_ai_client = OpenAI(api_key=OPENAI_API_KEY)
                log.info(f"OpenAI client initialized with model {OPENAI_MODEL_NAME}")
            except Exception as e:
                log.error(f"Failed to initialize OpenAI client: {e}")
                self.used_ai_client = None

        self.extractor = FixedAmazonExtractor(
            chrome_debug_port=chrome_debug_port,
            ai_client=self.used_ai_client
        )
        # MODIFIED: Use ConfigurableSupplierScraper
        self.web_scraper = ConfigurableSupplierScraper(
            ai_client=self.used_ai_client,
            openai_model_name=OPENAI_MODEL_NAME
        )
        self.supplier_cache_dir = SUPPLIER_CACHE_DIR
        self.amazon_cache_dir = AMAZON_CACHE_DIR
        self.max_cache_age_seconds = max_cache_age_hours * 3600
        
        # Load existing linking map if available
        self.linking_map = self._load_linking_map()
        log.info(f"Loaded linking map with {len(self.linking_map)} entries")
        self.results_summary = {
            "total_supplier_products": 0,
            "products_analyzed_ean": 0,
            "products_analyzed_title": 0,
            "products_passed_triage": 0, # New counter
            "products_rejected_by_triage": 0, # New counter
            "products_previously_visited": 0, # Track resumed products
            "profitable_products": 0,
            "errors": 0,
            "start_time": datetime.now().isoformat()
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
        if self.state_path and self.state_path.exists():
            try:
                history = json.loads(self.state_path.read_text())
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
            temp_path = f"{self.state_path}.tmp"
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(hist, f, indent=2, ensure_ascii=False)
                os.replace(temp_path, self.state_path)
                log.debug(f"History saved with {len(hist.get('categories_scraped', []))} categories, {len(hist.get('pages_visited', []))} pages")
            except Exception as e:
                log.error(f"Failed to save history: {e}")
                if os.path.exists(temp_path):
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

    # ──────────────────────── ②  Enhanced AI method ──────────────────────────
    async def _get_ai_suggested_categories_enhanced(
        self,
        supplier_url: str,
        supplier_name: str,
        discovered_categories: list[dict],
        previous_categories: list[str] | None = None,
        processed_products: list[str] | None = None,
    ) -> dict:
        """FBA-aware AI selection with UK business intelligence & memory."""
        prev_cats = previous_categories or []
        friendly = [c for c in discovered_categories if self._classify_url(c["url"]) == "friendly" and c["url"] not in prev_cats][:100]
        formatted = "\n".join(f'- {c["name"]}: {c["url"]}' for c in friendly)
        prompt = f"""
AMAZON FBA UK CATEGORY ANALYSIS FOR: {supplier_name}

You are an expert Amazon FBA consultant (UK marketplace).

DISCOVERED CATEGORIES:
{formatted}

PREVIOUSLY PROCESSED CATEGORIES: {prev_cats or "None"}
PREVIOUSLY PROCESSED PRODUCTS: {processed_products or "None"}

(Use priority list & avoid list exactly as described; output JSON only.)
"""
        # ---------- AI CALL ----------
        raw = await asyncio.to_thread(
            self.used_ai_client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=600,
        )

        # ---------- STRICT VALIDATION ----------
        try:
            ai = json.loads(raw.choices[0].message.content.strip())
            required = {"top_3_urls", "secondary_urls", "skip_urls"}
            if not required.issubset(ai):
                raise KeyError(f"AI JSON missing keys: {required - set(ai)}")
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

    # ──────────────────────── ④  Hierarchical selector ───────────────────────
    async def _hierarchical_category_selection(self, supplier_url, supplier_name):
        hist = self._load_history()
        
        # Use the new discover_categories method that returns dict format
        discovered_categories = await self.web_scraper.discover_categories(supplier_url)
        
        if not discovered_categories:
            log.warning(f"No categories discovered for {supplier_url}, using fallback")
            # Fallback to basic homepage categories
            basic_cats = await self.web_scraper.get_homepage_categories(supplier_url)
            discovered_categories = [{"name": url.split('/')[-1] or "category", "url": url} for url in basic_cats[:10]]
        
        ai = await self._get_ai_suggested_categories_enhanced(
            supplier_url, supplier_name, discovered_categories,
            previous_categories=hist["categories_scraped"],
            processed_products=hist["products_processed"],
        )
        
        # Record AI decision in history
        self._record_ai_decision(hist, ai)
        
        # Update history with new categories
        hist["categories_scraped"] += ai["top_3_urls"]
        self._save_history(hist)
        
        pages = []
        for url in ai["top_3_urls"]:
            # Get subpages for each selected category
            subpages = await self.web_scraper.discover_subpages(url)
            pages.extend(subpages[:2])  # First 2 sub-pages per category
        
        # If no pages found, return the original URLs
        if not pages:
            pages = ai["top_3_urls"]
            
        log.info(f"Hierarchical selection returned {len(pages)} pages to scrape")
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

    async def run(self, supplier_url: str = DEFAULT_SUPPLIER_URL,
                  supplier_name: str = DEFAULT_SUPPLIER_NAME,
                  max_products_to_process: int = 50,
                  cache_supplier_data: bool = True,
                  force_config_reload: bool = False,
                  debug_smoke: bool = False,
                  resume_from_last: bool = True) -> List[Dict[str, Any]]:
        profitable_results: List[Dict[str, Any]] = []
        session_id = f"{supplier_name.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        log.info(f"Starting passive extraction workflow for supplier: {supplier_name} ({supplier_url})")
        log.info(f"Session ID: {session_id}")
        log.info(f"PRICE CRITERIA: Min Supplier Cost £{self.min_price}, Max Supplier Cost £{MAX_PRICE}")

        # State file to track last processed product index and categories
        from pathlib import Path
        state_file_path = Path(OUTPUT_DIR) / f"{supplier_name.replace('.', '_')}_processing_state.json"
        self.state_path = state_file_path  # Set for use in helper methods
        self.last_processed_index = 0

        # Load previous state if resume is enabled
        if resume_from_last and state_file_path.exists():
            try:
                state_data = json.loads(state_file_path.read_text())
                self.last_processed_index = state_data.get("last_processed_index", 0)
                log.info(f"Resuming from index {self.last_processed_index} (previous run state found)")
            except Exception as e:
                log.warning(f"Failed to load previous state, starting from beginning: {e}")

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
            supplier_products = await self._extract_supplier_products(supplier_url, supplier_name)
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
            supplier_products = await self._extract_supplier_products(supplier_url, supplier_name)
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
            
        log.info(f"Processing up to {max_products_to_process} products starting from index {self.last_processed_index}.")
        products_to_analyze = price_filtered_products[self.last_processed_index:self.last_processed_index + max_products_to_process]

        for i, product_data in enumerate(products_to_analyze):
            # Update last_processed_index for next run (absolute index in price_filtered_products)
            current_absolute_index = self.last_processed_index + i
            state_data = {"last_processed_index": current_absolute_index + 1}  # +1 for next product
            try:
                with open(state_file_path, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f)
            except Exception as e:
                log.warning(f"Failed to save processing state: {e}")
            
            log.info(f"--- Processing supplier product {i+1}/{len(products_to_analyze)}: '{product_data.get('title')}' (EAN: {product_data.get('ean', 'N/A')}) ---")
            
            # Check if this product has already been processed in previous runs (using linking map)
            supplier_ean = product_data.get("ean")
            supplier_url = product_data.get("url")
            if supplier_ean or supplier_url:
                # Create identifier for lookup in linking map
                supplier_identifier = f"EAN_{supplier_ean}" if supplier_ean else f"URL_{supplier_url}"
                
                # Find the existing entry for more detailed feedback
                existing_entry = next((link for link in self.linking_map 
                                     if link.get("supplier_product_identifier") == supplier_identifier), None)
                
                if existing_entry:
                    # Extract details for enhanced message
                    supplier_title = existing_entry.get("supplier_title_snippet", "Unknown product")
                    amazon_asin = existing_entry.get("chosen_amazon_asin", "No ASIN found")
                    amazon_title = existing_entry.get("amazon_title_snippet", "No Amazon match")
                    match_method = existing_entry.get("match_method", "Unknown method")
                    
                    # Create an informative previously visited message
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
                
                # Try to get from cache first using EAN (or ASIN derived from EAN)
                # This part needs careful thought: EAN search might return different ASINs over time.
                # Caching by ASIN is more reliable if EAN -> ASIN mapping is stable.
                # For now, we search by EAN, get an ASIN, then cache by that ASIN.
                
                amazon_product_data_from_ean_search = await self.extractor.search_by_ean_and_extract_data(supplier_ean, product_data["title"])
                
                if amazon_product_data_from_ean_search and "error" not in amazon_product_data_from_ean_search and (amazon_product_data_from_ean_search.get("asin") or amazon_product_data_from_ean_search.get("asin_from_details")):
                    asin_to_check = (amazon_product_data_from_ean_search.get("asin") or 
                                     amazon_product_data_from_ean_search.get("asin_from_details"))
                    log.info(f"EAN search successful for '{supplier_ean}' - found ASIN: {asin_to_check}")
                    
                    # Check cache first
                    cached_amazon_data = await self._get_cached_amazon_data_by_asin(asin_to_check) # type: ignore
                    if cached_amazon_data:
                        amazon_product_data = cached_amazon_data
                        log.info(f"Using cached Amazon data for ASIN: {asin_to_check} (from EAN search)")
                    else:
                        # Use the fresh EAN search data and cache it
                        amazon_product_data = amazon_product_data_from_ean_search
                        
                        # Apply quick triage if enabled
                        if self.enable_quick_triage and product_data.get("price"):
                            if self._passes_quick_triage(product_data.get("price"), amazon_product_data):
                                await self._cache_amazon_data(asin_to_check, amazon_product_data, product_data, "EAN_search") # type: ignore
                                log.info(f"Cached fresh Amazon data from EAN search for ASIN: {asin_to_check}")
                            else:
                                log.info(f"Skipping cache for ASIN {asin_to_check} - failed quick triage check")
                        else:
                            await self._cache_amazon_data(asin_to_check, amazon_product_data, product_data, "EAN_search") # type: ignore
                            log.info(f"Cached fresh Amazon data from EAN search for ASIN: {asin_to_check}")
                elif amazon_product_data_from_ean_search and "error" in amazon_product_data_from_ean_search:
                    log.warning(f"EAN search for '{supplier_ean}' failed or returned error: {amazon_product_data_from_ean_search.get('error')}")
                    amazon_product_data = None  # Explicitly set to None
                else:
                    log.debug(f"EAN search for '{supplier_ean}' did not yield a usable ASIN.")
                    amazon_product_data = None  # Explicitly set to None

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

                amazon_product_data = await self._get_cached_amazon_data_by_asin(asin_to_check)
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

            # --- COMMENTED OUT: Zero-Token Triage Step (per requirements) ---
            # log.info(f"Performing Zero-Token Triage for ASIN: {asin_to_check}")
            # # Landed cost is the supplier product price
            # triage_result = await perform_zero_token_triage(asin_to_check, product_data['price'])
            # combined_data_for_triage_log = { # For logging/saving if rejected
            #     "supplier_product_info": product_data,
            #     "amazon_product_info_initial_asin": asin_to_check, # Log the ASIN identified pre-deep-scrape
            #     "triage_result": triage_result,
            #     "analysis_timestamp": datetime.now().isoformat(),
            #     "session_id": session_id
            # }

            # if triage_result.get("verdict") == "REJECT":
            #     log.info(f"ASIN {asin_to_check} REJECTED by triage: {triage_result.get('reasons')}")
            #     self.results_summary["products_rejected_by_triage"] += 1
            #     # Optionally save rejected product details
            #     # rejected_filename = f"triage_rejected_{session_id}_{asin_to_check}.json"
            #     # with open(os.path.join(OUTPUT_DIR, rejected_filename), "w", encoding="utf-8") as f_rej:
            #     #    json.dump(combined_data_for_triage_log, f_rej, indent=2, ensure_ascii=False)
            #     continue # Skip to the next supplier product
            
            # self.results_summary["products_passed_triage"] += 1
            # log.info(f"ASIN {asin_to_check} PASSED triage or triage skipped/failed. Proceeding with detailed extraction if not already done.")
            # --- END TRIAGE INTEGRATION (COMMENTED OUT) ---
            
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
                log.warning(f"Low quality match ({match_validation['match_quality']}) between supplier product '{product_data.get('title')}' and Amazon product '{amazon_product_data.get('title')}'. Skipping.")
                log.debug(f"Match reasons: {match_validation.get('reasons', [])}")
        
        # D2: Stage-guard audit - Log triage stage completion
        log.info(f"STAGE-COMPLETE: triage_stage - {self.results_summary['products_passed_triage']} passed, {self.results_summary['products_rejected_by_triage']} rejected")
        if self.results_summary['products_passed_triage'] == 0 and len(products_to_analyze) > 0:
            log.warning(f"STAGE-GUARD WARNING: Triage stage rejected all {len(products_to_analyze)} products. Check SellerAmp connectivity or criteria.")
            
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
                        f"{self.results_summary['products_analyzed_ean'] + self.results_summary['products_analyzed_title']} newly analyzed, "
                        f"{self.results_summary['profitable_products']} profitable products found")
            else:
                log.info(f"📋 Session Summary: {self.results_summary['products_analyzed_ean'] + self.results_summary['products_analyzed_title']} products analyzed, "
                        f"{self.results_summary['profitable_products']} profitable products found")
                        
        except Exception as e: 
            log.error(f"Error saving summary: {e}")
        
        # Save to persistent linking map for Fix 2.6 (removed session-specific saving)
        if self.linking_map:
            self._save_linking_map()
            log.info(f"Persistent linking map updated with {len(self.linking_map)} entries")
        
        return profitable_results

    async def _get_cached_amazon_data_by_asin(self, asin: str) -> Optional[Dict[str, Any]]:
        """Helper to get cached Amazon data by ASIN."""
        if not asin: 
            return None # Added check for None ASIN
        asin_cache_file = os.path.join(self.amazon_cache_dir, f"amazon_{asin}.json")
        if os.path.exists(asin_cache_file):
            cache_age = time.time() - os.path.getmtime(asin_cache_file)
            if cache_age < self.max_cache_age_seconds:
                try:
                    with open(asin_cache_file, 'r', encoding='utf-8') as f:
                        amazon_product_data = json.load(f)
                    log.info(f"Loaded Amazon data for ASIN {asin} from cache ({cache_age/3600:.1f} hours old)")
                    return amazon_product_data
                except Exception as e:
                    log.error(f"Error loading Amazon cache for ASIN {asin}: {e}")
        return None

    async def _cache_amazon_data(self, chosen_asin: str, amazon_product_data: Dict[str, Any], supplier_product_info: Dict[str, Any], match_method_used: str):
        """Helper to cache Amazon data with enhanced linking map generation for Fix 2.6."""
        if not chosen_asin: 
            return  # Added check for None ASIN
        if "error" not in amazon_product_data and amazon_product_data.get("title"):
            # Filename Logic with supplier EAN integration
            supplier_ean = supplier_product_info.get("ean")
            if supplier_ean:
                filename = f"amazon_{chosen_asin}_{supplier_ean}.json"
            else:
                filename = f"amazon_{chosen_asin}.json"
            
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
                self.linking_map.append(link_record)
                log.info(f"Added to linking map: {supplier_identifier_for_map} -> {chosen_asin}")
                
            except Exception as e:
                log.error(f"Error caching Amazon data for ASIN {chosen_asin}: {e}")

    async def _extract_supplier_products(self, supplier_base_url: str, supplier_name: str) -> List[Dict[str, Any]]:
        extracted_products: List[Dict[str, Any]] = []
        
        # Set up state tracking path
        from pathlib import Path
        self.state_path = Path(OUTPUT_DIR) / f"{supplier_name.replace('.', '_')}_processing_state.json"
        
        # MODIFIED: Get supplier configuration from ConfigurableSupplierScraper
        supplier_config = self.web_scraper._get_selectors_for_domain(supplier_base_url) # type: ignore
        
        # Check if AI category progression is enabled
        use_ai_progression = supplier_config.get("use_ai_category_progression", True)
        use_two_step = supplier_config.get("two_step_extraction", True)
        
        log.info(f"Extracting products from {supplier_name} using {'two-step' if use_two_step else 'single-step'} process.")
        
        # ──────────────────────── ⑤  Integrate hierarchical selection ────────────────────────
        if use_ai_progression:
            log.info("AI category progression enabled - using hierarchical category selection")
            try:
                category_urls_to_process = await self._hierarchical_category_selection(supplier_base_url, supplier_name)
                if not category_urls_to_process:
                    log.warning("No AI-suggested categories available, falling back to default paths")
                    category_paths = supplier_config.get("category_paths", ["/"])
                    category_urls_to_process = [supplier_base_url.rstrip('/') + path for path in category_paths]
                else:
                    log.info(f"Processing {len(category_urls_to_process)} AI-suggested categories")
            except Exception as e:
                log.error(f"Hierarchical category selection failed: {e}")
                # Fallback to traditional approach
                category_paths = supplier_config.get("category_paths", ["/"])
                category_urls_to_process = [supplier_base_url.rstrip('/') + path for path in category_paths]
                log.info(f"Using fallback category paths: {category_paths}")
        else:
            # Traditional category path approach
            category_paths = supplier_config.get("category_paths", ["/"])
            category_urls_to_process = [supplier_base_url.rstrip('/') + path for path in category_paths]
            log.info(f"Using traditional category paths: {category_paths}")

        for category_url in category_urls_to_process:
            log.info(f"Scraping supplier category: {category_url}")
            
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
                    
                    # Simplified approach: if a pattern exists, construct it. Otherwise, complex loop needed.
                    # This is a placeholder for more robust orchestrator-level supplier pagination.
                    # The ConfigurableSupplierScraper's get_next_page_url is designed to take soup.
                    # For now, we'll assume a simple pattern if current_page_num > 1 or break.
                    if current_page_num > 1: # Only try to get next page if not the first page
                        # This part is tricky without the soup of the *previous* page.
                        # The ConfigurableSupplierScraper's get_next_page_url is designed for this.
                        # For now, we'll assume that if a simple pattern exists, we can form it.
                        # A more robust implementation would fetch page N, parse it, get URL for N+1.
                        # This loop structure is simplified.
                        temp_parsed_url = urlparse(category_url)
                        if f"p={current_page_num-1}" in temp_parsed_url.query or f"page={current_page_num-1}" in temp_parsed_url.query : # example
                             page_url_to_fetch = category_url.replace(f"p={current_page_num-1}", f"p={current_page_num}").replace(f"page={current_page_num-1}", f"page={current_page_num}")
                        elif current_page_num >1 : # if no pattern was easily replaceable, and not page 1, break from this simplified pagination
                             log.info(f"Simplified pagination: stopping at page {current_page_num-1} for {category_url} as direct next URL construction is complex here.")
                             break


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

                # Process elements from the current page
                if use_two_step:
                    basic_products = []
                    for p_soup in product_elements_soup:
                        try:
                            # Pass page_url_to_fetch as context_url
                            title = await self.web_scraper.extract_title(p_soup, str(p_soup), page_url_to_fetch)
                            product_page_url = await self.web_scraper.extract_url(p_soup, str(p_soup), page_url_to_fetch, supplier_base_url)
                            if title and product_page_url:
                                basic_products.append({"title": title, "url": product_page_url, "category_url_source": page_url_to_fetch})
                        except Exception as e:
                            log.error(f"Error extracting basic product info: {e}")
                    
                    batch_size = 5
                    for i in range(0, len(basic_products), batch_size):
                        batch = basic_products[i:i+batch_size]
                        # Pass category_url_source for context if needed by _get_product_details
                        batch_tasks = [self._get_product_details(p["url"], p["title"], supplier_name, p["category_url_source"]) for p in batch]
                        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                        for result in batch_results:
                            if isinstance(result, Exception): 
                                log.error(f"Error processing product details: {result}")
                            elif result: 
                                extracted_products.append(result)
                        log.info(f"Processed batch of {len(batch)} detailed products from page {current_page_num}, total extracted so far: {len(extracted_products)}")
                else: # Single-step
                    batch_size = 5
                    for i in range(0, len(product_elements_soup), batch_size):
                        batch = product_elements_soup[i:i+batch_size]
                        batch_tasks = [self._process_product_element(p_soup, str(p_soup), page_url_to_fetch, supplier_base_url, supplier_name) for p_soup in batch]
                        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                        for result in batch_results:
                            if isinstance(result, Exception): log.error(f"Error processing supplier product element: {result}")
                            elif result: extracted_products.append(result)
                        log.info(f"Processed batch of {len(batch)} products from supplier page {current_page_num}, total extracted so far: {len(extracted_products)}")
                
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
                return {
                    "title": title,
                    "price": price,
                    "url": product_page_url,
                    "image_url": image_url or "N/A",
                    "ean": ean, 
                    "source_supplier": supplier_name,
                    "source_category_url": context_url, # Was category_url
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
            
            # FIXED: Use ConfigurableSupplierScraper's proven extract_identifier method instead of duplicate logic
            # This method has tolerant regex and comprehensive selector support that works with "Barcode502..." patterns
            # Correct signature: extract_identifier(element_soup, element_html, context_url) -> Optional[str]
            ean = await self.web_scraper.extract_identifier(soup, product_html, product_url)
            upc = None  # extract_identifier returns primary identifier only
            sku = None  # Could be enhanced to extract these separately if needed
            
            log.info(f"Identifier extraction for {product_url}: EAN={ean}, UPC={upc}, SKU={sku}")

            # TODO: Extract other details like description, brand, etc., using self.web_scraper
            # and selectors defined in the supplier's JSON config (e.g., "description_selector", "brand_selector")

            return {
                "title": title, # Title from listing page is usually sufficient
                "price": price, # Price from detail page might be more accurate
                "url": product_url,
                "image_url": image_url or "N/A",
                "ean": ean,
                "upc": upc,
                "sku": sku,
                "source_supplier": supplier_name,
                "source_category_url": category_url_source, # URL of the category page where it was found
                "extraction_timestamp": datetime.now().isoformat()
                # Add other details as extracted
            }
            
        except Exception as e:
            log.error(f"Error getting product details for {product_url}: {e}")
            return None
            
    # REMOVED: _extract_product_identifiers_from_detail_page() method
    # This method contained duplicate logic with strict regex that failed on "Barcode502..." patterns.
    # Replaced with calls to ConfigurableSupplierScraper.extract_identifier() which has proven tolerant regex.
        
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
        metrics = {
            "supplier_cost_price": 0.0, "amazon_selling_price": 0.0,
            "estimated_amazon_fees": 0.0, "estimated_profit_per_unit": 0.0,
            "roi_percent_calculated": 0.0, "vat_on_purchase_estimated": 0.0,
            "vat_on_sale_estimated": 0.0, "costs_breakdown": {}, "revenue_breakdown": {},
            "estimated_monthly_sales": 0 # Initialize
        }
        try:
            supplier_price = combined_data["supplier_product_info"].get("price", 0.0)
            amazon_price = combined_data["amazon_product_info"].get("current_price", 0.0)
            if not isinstance(supplier_price, (int, float)) or not isinstance(amazon_price, (int, float)) or supplier_price <= 0 or amazon_price <= 0:
                log.warning("Cannot calculate ROI: Invalid or missing supplier or Amazon price.")
                return metrics

            metrics["supplier_cost_price"] = supplier_price
            metrics["amazon_selling_price"] = amazon_price
            metrics["costs_breakdown"]["supplier_price_incl_vat"] = supplier_price
            vat_rate = 0.20 # Assume 20% VAT
            cost_ex_vat = supplier_price / (1 + vat_rate)
            metrics["vat_on_purchase_estimated"] = round(supplier_price - cost_ex_vat, 2)
            metrics["costs_breakdown"]["supplier_price_ex_vat"] = round(cost_ex_vat, 2)
            metrics["costs_breakdown"]["supplier_vat"] = metrics["vat_on_purchase_estimated"]
            
            amazon_price_ex_vat = amazon_price / (1 + vat_rate)
            metrics["vat_on_sale_estimated"] = round(amazon_price - amazon_price_ex_vat, 2)
            metrics["revenue_breakdown"]["amazon_price_incl_vat"] = amazon_price
            metrics["revenue_breakdown"]["amazon_price_ex_vat"] = round(amazon_price_ex_vat, 2)
            metrics["revenue_breakdown"]["amazon_vat"] = metrics["vat_on_sale_estimated"]

            referral_fee_percentage = 0.15 # Example, this can be category-dependent
            amazon_referral_fee = round(amazon_price_ex_vat * referral_fee_percentage, 2)
            metrics["costs_breakdown"]["amazon_referral_fee"] = amazon_referral_fee
            
            fba_fee = 0.0
            # Prioritize FBA fee from Keepa if available
            if combined_data["amazon_product_info"].get("keepa") and \
               combined_data["amazon_product_info"]["keepa"].get("product_details_tab_data"):
                keepa_details = combined_data["amazon_product_info"]["keepa"]["product_details_tab_data"]
                for key_k, val_k in keepa_details.items():
                    if "FBA Pick&Pack Fee" in key_k and isinstance(val_k, (int, float)): # Check type
                        fba_fee = float(val_k)
                        log.info(f"Using FBA fee from Keepa data: £{fba_fee:.2f}")
                        break
            if fba_fee == 0.0: # Fallback to estimation if not found in Keepa
                fba_fee = self._estimate_fba_fee(combined_data["amazon_product_info"])
                log.info(f"Using estimated FBA fee: £{fba_fee:.2f}")
            
            metrics["costs_breakdown"]["fba_fee"] = round(fba_fee, 2)
            total_amazon_fees = amazon_referral_fee + fba_fee
            metrics["estimated_amazon_fees"] = round(total_amazon_fees, 2)
            
            profit = amazon_price_ex_vat - cost_ex_vat - total_amazon_fees
            metrics["estimated_profit_per_unit"] = round(profit, 2)
            if cost_ex_vat > 0: metrics["roi_percent_calculated"] = round((profit / cost_ex_vat) * 100, 2)
            else: metrics["roi_percent_calculated"] = 0.0
            
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
            
            log.debug(f"Financials for '{combined_data['amazon_product_info'].get('title')}': Cost (exVAT): {cost_ex_vat:.2f}, Sell (exVAT): {amazon_price_ex_vat:.2f}, Fees: {total_amazon_fees:.2f}, Profit: {profit:.2f}, ROI: {metrics['roi_percent_calculated']}%")
        except Exception as e: log.error(f"Error calculating ROI & profit: {e}", exc_info=True)
        return metrics

    def _estimate_fba_fee(self, amazon_product_data: Dict[str, Any]) -> float:
        # This estimation logic can be quite complex and depends on Amazon's fee structure.
        # The version from amazon_playwright_extractor.py is more detailed.
        # For now, using a simplified version or the one from the plan.
        # Plan's version:
        default_fba_fee = 3.50; weight_grams = None; dimensions_str = None
        
        # Try to get weight and dimensions from various sources in amazon_product_data
        # (e.g., 'weight_from_details', 'dimensions_from_details', Keepa data if parsed)
        # This logic is simplified here for brevity, refer to amazon_playwright_extractor for more detail.
        
        weight_str = amazon_product_data.get("weight_from_details", "")
        if isinstance(weight_str, str): # Ensure it's a string
            weight_match = re.search(r"([\d,.]+)\s*(kg|g|oz|pounds|lbs)", weight_str, re.IGNORECASE)
            if weight_match:
                weight_val = float(weight_match.group(1).replace(',', '.'))
                unit = weight_match.group(2).lower()
                if 'kg' in unit: weight_grams = weight_val * 1000
                elif 'g' in unit: weight_grams = weight_val
                # ... other unit conversions ...
        
        dimensions_str = amazon_product_data.get("dimensions_from_details", "")
        # ... (similar parsing for dimensions to determine size_tier) ...
        size_tier = "standard_parcel_medium" # Default/Example

        fee_map = {"small_envelope": 1.90, "standard_parcel_small": 2.70, 
                   "standard_parcel_medium": 3.80, "standard_parcel_large": 4.90, 
                   "standard_parcel_xlarge": 6.50}
        base_fee = fee_map.get(size_tier, default_fba_fee)
        # ... add weight fee component and category multiplier ...
        
        return round(max(base_fee, 1.50), 2) # Ensure a minimum fee

    # --- MODIFIED: _validate_product_match (as per plan) ---
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

        if validation["match_quality"] == "medium" and self.used_ai_client:
            log.info(f"Match quality is medium ({validation['confidence_score']:.2f}) for ASIN {amazon_product.get('asin')}. Attempting AI validation.")
            try:
                prompt = (
                    f"Assess if the following two products are likely the same. Respond with only 'MATCH', 'MISMATCH', or 'UNCERTAIN'.\n\n"
                    f"Supplier Product:\nTitle: {supplier_title}\nBrand: {supplier_product.get('brand', 'N/A')}\nEAN: {supplier_ean or 'N/A'}\nPrice: {supplier_product.get('price', 'N/A')}\nDescription: {str(supplier_product.get('description', 'N/A'))[:200]}...\n\n"
                    f"Amazon Product:\nTitle: {amazon_title}\nBrand: {amazon_product.get('brand', 'N/A')}\nASIN: {amazon_product.get('asin', 'N/A')}\nEAN on Page: {amazon_ean_on_page or 'N/A'}\nPrice: {amazon_product.get('current_price', 'N/A')}\nDescription: {str(amazon_product.get('description', 'N/A'))[:200]}...\nFeatures: {str(amazon_product.get('features', []))[:200]}..."
                )
                
                # Ensure ai_client is not None before calling create
                if self.used_ai_client:
                    chat_completion = await asyncio.to_thread(
                        self.used_ai_client.chat.completions.create, # type: ignore
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
    # --- END MODIFIED _validate_product_match ---

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

    def _load_linking_map(self) -> List[Dict[str, Any]]:
        """Load linking map from persistent file or initialize empty map if not exists."""
        if os.path.exists(LINKING_MAP_PATH):
            try:
                with open(LINKING_MAP_PATH, 'r', encoding='utf-8') as f:
                    linking_map = json.load(f)
                log.info(f"Loaded linking map from {LINKING_MAP_PATH} with {len(linking_map)} entries")
                return linking_map
            except (json.JSONDecodeError, UnicodeDecodeError, Exception) as e:
                log.error(f"Error loading linking map: {e} - Creating new map")
                return []
        else:
            log.info(f"No existing linking map found at {LINKING_MAP_PATH} - Creating new map")
            return []

    def _save_linking_map(self):
        """Save linking map to persistent file using atomic write pattern."""
        if not self.linking_map:
            log.info("Empty linking map - nothing to save.")
            return
            
        # Use atomic write pattern to prevent data corruption
        temp_path = f"{LINKING_MAP_PATH}.tmp"
        try:
            # First write to temporary file
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.linking_map, f, indent=2, ensure_ascii=False)
                
            # Then atomically replace the original file
            os.replace(temp_path, LINKING_MAP_PATH)
            log.info(f"Successfully saved linking map with {len(self.linking_map)} entries to {LINKING_MAP_PATH}")
        except Exception as e:
            log.error(f"Error saving linking map: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

async def run_workflow_main():
    log.info("Initializing Passive Extraction Workflow...")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Amazon FBA Passive Extraction Workflow')
    parser.add_argument('--max-products', type=int, default=10, help='Maximum number of products to process (default: 10)')
    parser.add_argument('--supplier-url', default=DEFAULT_SUPPLIER_URL, help=f'Supplier website URL (default: {DEFAULT_SUPPLIER_URL})')
    parser.add_argument('--supplier-name', '--supplier', default=DEFAULT_SUPPLIER_NAME, help=f'Supplier name (default: {DEFAULT_SUPPLIER_NAME})')
    parser.add_argument('--min-price', type=float, default=0.1, help='Minimum supplier product price in GBP (default: 0.1)')
    parser.add_argument('--force-config-reload', action='store_true', help='Force reload supplier configuration and clear cache')
    parser.add_argument('--debug-smoke', action='store_true', help='Inject debug product for end-to-end testing')
    parser.add_argument('--enable-quick-triage', action='store_true', help='Enable quick ROI/net-profit gate before financial calculations')
    
    args = parser.parse_args()
    
    max_products = args.max_products
    supplier_url = args.supplier_url
    supplier_name = args.supplier_name
    min_price = args.min_price
    force_config_reload = args.force_config_reload
    debug_smoke = args.debug_smoke
    enable_quick_triage = args.enable_quick_triage

    ai_client = None
    if OPENAI_API_KEY:
        try:
            ai_client = OpenAI(api_key=OPENAI_API_KEY)
            log.info(f"OpenAI client initialized with model {OPENAI_MODEL_NAME}")
        except Exception as e: 
            log.error(f"Failed to initialize OpenAI client: {e}")
    
    workflow_instance = PassiveExtractionWorkflow(chrome_debug_port=9222, ai_client=ai_client, max_cache_age_hours=168, min_price=min_price)
    workflow_instance.enable_quick_triage = enable_quick_triage
    
    try:
        log_message = f"Running workflow for {supplier_name} with max {max_products} products. Price range £{min_price}-£{MAX_PRICE}."
        if enable_quick_triage:
            log_message += " Quick triage enabled."
        log.info(log_message)
        if force_config_reload:
            log.info("Force config reload enabled - supplier cache cleared")
        if debug_smoke:
            log.info("Debug smoke test enabled - will inject test product")
        results = await workflow_instance.run(
            supplier_url=supplier_url, supplier_name=supplier_name,
            max_products_to_process=max_products, cache_supplier_data=True,
            force_config_reload=force_config_reload, debug_smoke=debug_smoke,
            resume_from_last=True
        )
        if results: 
            log.info(f"Workflow completed. Found {len(results)} potentially profitable products.")
        else: 
            log.info("Workflow completed. No profitable products found.")
    except Exception as e:
        log.critical(f"Unhandled exception in main workflow execution: {e}", exc_info=True)
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
    print("="*80)
    print(f"Amazon FBA Passive Extraction Workflow")
    print(f"Version: 1.0.3 - {datetime.now().strftime('%Y-%m-%d')}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print(f"Using FixedAmazonExtractor for improved extension compatibility.")
    print(f"Profitability Criteria: Min ROI {MIN_ROI_PERCENT}%, Min Profit £{MIN_PROFIT_PER_UNIT}")
    print("="*80)
    asyncio.run(run_workflow_main())

