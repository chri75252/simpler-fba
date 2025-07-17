"""
passive_extraction_workflow_latest.py - Architectural Summary & Script Index
================================================================================

**High-Level Summary:**
This script is the central engine for a multi-stage workflow that identifies profitable products for Amazon FBA. When executed by a targeted runner like `run_custom_poundwholesale.py`, it operates in a deterministic mode, using a predefined list of category URLs to ensure reliable and repeatable scraping runs. The system is architected for resilience and statefulness, allowing it to resume interrupted sessions and handle supplier authentication, making it ideal for the thorough analysis of complex e-commerce websites.

**Key Features & Concepts:**
- **Centralized Configuration:** The workflow is now exclusively controlled by `system_config.json`. The launcher script (`run_custom_poundwholesale.py`) is a simple trigger, and the `PassiveExtractionWorkflow` class itself is responsible for loading and respecting all operational toggles, ensuring a single source of truth.
- **Batched Supplier Scraping:** The system processes supplier categories in configurable chunks (defined by `supplier_extraction_batch_size`). This provides critical memory management and stability, preventing the system from being overwhelmed when scraping suppliers with many categories.
- **Stateful Resume Capability:** The workflow's progress is meticulously tracked using an `EnhancedStateManager`. This component saves the index of the last processed product, allowing the script to be stopped and resumed without losing work—a critical feature for long-running, interruptible scraping tasks.
- **Integrated Authentication & Retry:** The workflow is designed to handle supplier logins. It can detect authentication failures during a run, trigger a re-login attempt via the `SupplierAuthenticationService`, and retry the workflow, making it resilient to session timeouts.
- **Robust Dual-Pronged Product Matching:** The system employs a powerful two-step process to find products on Amazon. It first attempts a high-confidence match using the product's EAN. If that fails, it falls back to a title-based search that uses an advanced similarity scoring algorithm to ensure the match is rational.
- **Comprehensive Financial Analysis:** After a match is validated, the script invokes the `FBA_Financial_calculator` to determine ROI, net profit, and other key financial metrics, ensuring only genuinely profitable products are flagged.
- **Atomic & Batched Data Persistence:** To ensure data integrity against crashes, critical state files (like the linking map and processing state) are saved using an atomic write pattern (write to a temp file, then rename). These saves occur periodically in configurable batches during the main processing loop.

**--(Latent AI Capabilities - Bypassed in this Workflow)--**
*   **(Inactive) AI-Powered Category Selection:** The codebase contains sophisticated logic (`_get_ai_suggested_categories_enhanced`) to use an OpenAI client to intelligently select categories. This is bypassed when using a predefined category list.
*   **(Inactive) Hierarchical Category Processing:** The script has the capability (`_hierarchical_category_selection`) to explore a supplier's site by prioritizing FBA-friendly categories first, then moving to other phases. This is not used in the custom Pound Wholesale run.

**Core Workflow Logic (as executed by `run_custom_poundwholesale.py`):**
1.  **Initialization and Configuration Loading:** The workflow starts, initializing the `EnhancedStateManager`. Its first action is to load `system_config.json` to set all operational parameters (`max_products`, `max_products_per_category`, batch sizes, etc.).
2.  **Predefined Category Loading:** The `use_predefined_categories=True` flag is detected. The workflow bypasses all AI logic and instead calls `_get_predefined_categories` to load a hard-coded list of URLs from a specific config file.
3.  **Batched Supplier Product Scraping & Caching:** Using the predefined category list, `_extract_supplier_products` is called. This method now processes the category URLs in batches (controlled by `supplier_extraction_batch_size`), scraping the products from each batch sequentially before moving to the next.
4.  **Product Filtering and Resume Point Identification:** After all scraping is complete, the collected products are filtered by the configured price range. The script then slices the product list to start processing from the `last_processed_index` provided by the state manager.
5.  **Main Processing Loop (Cycled Analysis):** The script enters its main analysis loop, iterating through the products in configurable cycles (`max_products_per_cycle`).
6.  **Amazon Data Retrieval:** For each supplier product, `_get_amazon_data` is called. This method orchestrates the search on Amazon, executing the EAN-first, title-fallback strategy.
7.  **Data Caching & Linking:** The retrieved Amazon data is cached to disk. A "linking map" entry is created in memory to permanently associate the supplier product with the matched Amazon ASIN.
8.  **Financial Calculation:** The `FBA_Financial_calculator` is run on the combined supplier and Amazon data.
9.  **Profitability Check & State Update:** If the product meets the defined ROI and profit criteria, it's added to a list of profitable results. The product's URL is then marked as processed in the state manager to prevent re-analysis.
10. **Periodic Saves:** At configurable intervals (e.g., every 4 products, per `linking_map_batch_size`), the entire state (including the linking map and processing index) is saved to disk using an atomic write pattern.
11. **Finalization & Dual Reporting:** Once the loop completes, a final save is performed. Two reports are generated: a simple JSON list of profitable products from the current session, and a comprehensive CSV financial report for all cached products for the supplier.

**Class & Function Directory (with Line Numbers):**

- `FixedAmazonExtractor` (Lines: 435-830): A specialized class that extends the base `AmazonExtractor`. It is responsible for all interactions with Amazon.co.uk, including searching and data extraction.
  - `search_by_ean_and_extract_data()` (Lines: 625-795): The primary, high-confidence search method. It searches by EAN, filters out sponsored ads, and uses title similarity scoring to select the best match.
  - `extract_data()` (Lines: 824-848): The main data extraction method for a given ASIN. It reuses existing browser pages to ensure Chrome extensions function correctly.

- `PassiveExtractionWorkflow` (Lines: 851-2650): The main orchestrator class for the entire product sourcing workflow.
  - `__init__()` (Lines: 860-989): Initializes the system, loading configurations, setting up paths, and instantiating the scraper and extractor clients.
  - `run()` (Lines: 1970-2316): The main execution entry point. **It now loads all operational parameters directly from `self.system_config`**, orchestrating the entire process from state loading to final report generation.
  - `_extract_supplier_products()` (Lines: 2318-2435): Manages scraping product data from a list of category URLs. **This method now processes categories in batches controlled by `supplier_extraction_batch_size`**.
  - `_get_amazon_data()` (Lines: 2437-2525): Implements the EAN-first, title-fallback logic for finding a supplier product on Amazon and performs the critical title similarity validation.
  - `_validate_product_match()` (Lines: 2548-2563): A helper method that calculates a confidence score for a potential match based on title similarity.

- **--(Inactive Methods in this Workflow)--**
  - `_get_ai_suggested_categories_enhanced()` (Lines: 1412-1633): **(Bypassed)** The core AI interaction method.
  - `_hierarchical_category_selection()` (Lines: 1809-1968): **(Bypassed)** Manages the high-level strategy for choosing categories.

- `main()` (Lines: 2634-2647): A generic command-line entry point. **(Note: The `run_custom_poundwholesale.py` script serves as the actual, simplified entry point for this specific workflow).**

**Architect's Note:**
The system's architecture is now properly decoupled. The `PassiveExtractionWorkflow` is a self-contained engine driven by its configuration file. The "runner" script (`run_custom_poundwholesale.py`) acts as a simple, clean trigger, which is a much more robust and maintainable design.
"""

import os, logging
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = (
        "sk-s2-Q4jjFLfsmK1su4XzrXFdsYbTsZH4SWSES8efNDBT3BlbkFJGYMdHui-NLIdqGTgob3syatBmf40zqu9v8VPG6adUA"
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
from FBA_Financial_calculator import run_calculations
from cache_manager import CacheManager
# Removed LinkingMapWriter - using internal linking map methods
# Import enhanced state manager
# The utils directory is at the parent level (project root), not in tools/
try:
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    from utils.enhanced_state_manager import EnhancedStateManager
except ImportError:
    from enhanced_state_manager import EnhancedStateManager

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
from utils.browser_manager import BrowserManager
from config.system_config_loader import SystemConfigLoader

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

# ──────────────────────── BACKUP UTILITY FUNCTIONS ──────────────────────
def create_backup_with_experiment_number(file_path: str, experiment_number: int) -> str:
    """Create backup with .bakN suffix for experiment tracking"""
    if not os.path.exists(file_path):
        return None
    
    backup_path = f"{file_path}.bak{experiment_number}"
    shutil.copy2(file_path, backup_path)
    return backup_path

def backup_experiment_files(experiment_number: int, output_root: str = "OUTPUTS") -> Dict[str, str]:
    """Backup all files that need .bakN suffix (EXCEPT Amazon cache)"""
    backup_results = {}
    
    # System config
    config_path = "config/system_config.json"
    if os.path.exists(config_path):
        backup_results["system_config"] = create_backup_with_experiment_number(config_path, experiment_number)
    
    # Processing state
    state_path = os.path.join(output_root, "CACHE/processing_states/poundwholesale_co_uk_processing_state.json")
    if os.path.exists(state_path):
        backup_results["processing_state"] = create_backup_with_experiment_number(state_path, experiment_number)
    
    # Linking map
    linking_path = os.path.join(output_root, "FBA_ANALYSIS/linking_maps/poundwholesale.co.uk/linking_map.json")
    if os.path.exists(linking_path):
        backup_results["linking_map"] = create_backup_with_experiment_number(linking_path, experiment_number)
    
    # Supplier product cache
    supplier_cache_path = os.path.join(output_root, "cached_products/poundwholesale-co-uk_products_cache.json")
    if os.path.exists(supplier_cache_path):
        backup_results["supplier_cache"] = create_backup_with_experiment_number(supplier_cache_path, experiment_number)
    
    return backup_results

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

DEFAULT_SUPPLIER_URL = os.getenv("DEFAULT_SUPPLIER_URL", None)
DEFAULT_SUPPLIER_NAME = os.getenv("DEFAULT_SUPPLIER", None)

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
LINKING_MAP_DIR = os.path.join(OUTPUT_DIR, "linking_maps")
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

    async def search_by_title_using_search_bar(self, title: str, page: Optional[Page] = None) -> Dict[str, Any]:
        """Search Amazon by title using search bar interaction (not URL building)"""
        if not self.browser or not self.browser.is_connected():
            await self.connect()

        log.info(f"Searching Amazon by title using search bar: '{title}'")
        
        # Get page from parameter or use BrowserManager
        if page is None:
            from utils.browser_manager import get_page_for_url
            log.info("No page provided to search_by_title, getting one from BrowserManager.")
            page = await get_page_for_url("https://www.amazon.co.uk", reuse_existing=True)
        
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

    async def search_by_ean_and_extract_data(self, ean: str, supplier_product_title: str, page: Optional[Page] = None) -> Dict[str, Any]:
        """
        Search Amazon by EAN and extract data for the best match.
        Uses AI for disambiguation if multiple results are found.
        Uses robust search result selection and sponsored ad detection.
        """
        if not self.browser or not self.browser.is_connected():
            await self.connect()

        log.info(f"Searching Amazon by EAN: {ean} for supplier product: '{supplier_product_title}' (FixedAmazonExtractor)")
        
        # Get page from parameter or use BrowserManager
        if page is None:
            from utils.browser_manager import get_page_for_url
            log.info("No page provided to search_by_ean, getting one from BrowserManager.")
            page = await get_page_for_url("https://www.amazon.co.uk", reuse_existing=True)
        
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
                "[data-cy='search-result-list]",
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
                        sponsored_badge_locator = element.locator("span:visible", has_text=re.compile(r"^\\s*Sponsored\\s*$", re.IGNORECASE))
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
                    # FIX 1: EAN search should use exact EAN matching, NOT title scoring
                    # When EAN search returns results, use the first organic result (highest relevance)
                    if len(organic_results) == 1:
                        chosen_result = organic_results[0]
                        log.info(f"Single organic result found for EAN {ean}: ASIN {chosen_result['asin']}")
                    else:
                        # Multiple EAN search results - use first organic result (most relevant by Amazon's ranking)
                        chosen_result = organic_results[0]
                        log.info(f"Multiple organic results ({len(organic_results)}) found for EAN {ean}. Using first organic result (most relevant): ASIN {chosen_result['asin']}")
                        log.info(f"FIXED: No title scoring on EAN search results - using Amazon's search relevance ranking")
                    
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
            # FIX 1: EAN search → title match fallback
            log.info(f"Falling back to title search for supplier product: '{supplier_product_title}'")
            title_search_results = await self.search_by_title_using_search_bar(supplier_product_title, page=page)
            if title_search_results and "error" not in title_search_results and title_search_results.get("results"):
                log.info(f"Title search successful for '{supplier_product_title}' after EAN '{ean}' failed")
                # Return the best result from title search
                return title_search_results["results"][0] if title_search_results["results"] else {"error": f"No results for EAN {ean} or title search"}
            else:
                log.warning(f"Both EAN '{ean}' and title '{supplier_product_title}' searches failed")
                return {"error": f"No results for EAN {ean} or title search"}

        potential_asins_info = search_results_data["results"]
        chosen_asin_data = None

        if len(potential_asins_info) == 1:
            chosen_asin_data = potential_asins_info[0]
            log.info(f"Single ASIN {chosen_asin_data.get('asin')} found for EAN {ean}.")
        elif len(potential_asins_info) > 1:
            # FIX 1: EAN search → stop title scoring when search initiated by EAN
            # Trust Amazon's search relevance ranking for EAN searches
            chosen_asin_data = potential_asins_info[0]
            log.info(f"Multiple ASINs ({len(potential_asins_info)}) found for EAN {ean}. Using Amazon's first result: ASIN {chosen_asin_data.get('asin')}")
            log.info(f"FIXED: No title scoring on EAN search results - using Amazon's search relevance ranking")

            # EAN search complete - skip AI disambiguation to trust Amazon's ranking
            # AI disambiguation removed to prevent title scoring on EAN results
            if False:  # Disabled AI disambiguation for EAN searches
                log.info(f"AI disambiguation disabled for EAN {ean} - trusting Amazon's ranking")
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

        # The base AmazonExtractor's extract_data method should now attempt to get 'ean_on_page'.
        # No need for redundant EAN extraction here if the base class handles it.
        if "error" not in product_data and product_data.get("title"):
            log.info(f"Successfully extracted data for ASIN {chosen_asin} (EAN on page: {product_data.get('ean_on_page', 'N/A')})")
        
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
    def __init__(self, config_loader: SystemConfigLoader, workflow_config: dict, browser_manager: BrowserManager):
        self.config_loader = config_loader
        self.workflow_config = workflow_config
        self.browser_manager = browser_manager
        self.log = logging.getLogger(self.__class__.__name__)
        
        # Core components initialized here
        self.supplier_name = self.workflow_config.get('supplier_name')
        self.system_config = self.config_loader.get_system_config()
        
        self.output_dir = self._initialize_output_directory()
        self.supplier_cache_dir = os.path.join(self.output_dir, 'cached_products')
        self.amazon_cache_dir = os.path.join(self.output_dir, 'FBA_ANALYSIS', 'amazon_cache')
        os.makedirs(self.supplier_cache_dir, exist_ok=True)
        os.makedirs(self.amazon_cache_dir, exist_ok=True)
        self.state_manager = EnhancedStateManager(self.supplier_name)
        
        # Pass the single browser_manager instance to the tools
        self.amazon_extractor = self._initialize_amazon_extractor()
        self.supplier_scraper = self._initialize_supplier_scraper()
        
        # CRITICAL FIX: Set extractor alias to amazon_extractor to prevent AttributeError
        self.extractor = self.amazon_extractor
        
        # Initialize linking map as a dictionary (EAN -> ASIN mapping)
        self.linking_map = {}
        self.log.debug(f"🔍 DEBUG: linking_map initialized as type: {type(self.linking_map)}")
        # self.performance_tracker = PerformanceTracker()  # Removed - not defined

        # Workflow state attributes
        self.consecutive_amazon_price_misses = 0
        self.products_for_fba_analysis = []
        self.last_processed_index = 0
        
        # CRITICAL FIX: Initialize results_summary to prevent AttributeError
        self.results_summary = {
            "total_supplier_products": 0,
            "profitable_products": 0,
            "products_analyzed_ean": 0,
            "products_analyzed_title": 0,
            "errors": 0
        }

        self.log.info(f"✅ Output directory set to: {self.output_dir}")
        
        # CRITICAL FIX: Validate initialization to prevent AttributeError
        self._validate_initialization()

    def _initialize_output_directory(self):
        """Creates and returns the absolute path to the output directory."""
        output_dir = self.system_config.get("output_root", "OUTPUTS")
        os.makedirs(output_dir, exist_ok=True)
        return os.path.abspath(output_dir)

    def _initialize_amazon_extractor(self):
        """Initializes the Amazon extractor with the shared browser manager."""
        chrome_debug_port = self.system_config.get('chrome_debug_port', 9222)
        # CRITICAL FIX: Use FixedAmazonExtractor which has search_by_ean_and_extract_data method
        return FixedAmazonExtractor(
            chrome_debug_port=chrome_debug_port,
            ai_client=None  # AI features disabled
        )

    def _initialize_supplier_scraper(self):
        """Initializes the supplier scraper with the shared browser manager."""
        return ConfigurableSupplierScraper(
            ai_client=None,  # AI features disabled
            headless=False,  # Keep browser visible for debugging
            use_shared_chrome=True,  # Use existing Chrome instance
            auth_callback=None,  # No authentication callback needed
            browser_manager=self.browser_manager
        )

    def _validate_initialization(self):
        """Validates that all critical attributes are properly initialized."""
        required_attributes = {
            'results_summary': dict,
            'extractor': object,
            'amazon_extractor': object,
            'supplier_scraper': object,
            'system_config': dict,
            'output_dir': str,
            'supplier_cache_dir': str,
            'state_manager': object
        }
        
        for attr_name, expected_type in required_attributes.items():
            if not hasattr(self, attr_name):
                raise AttributeError(f"Critical attribute '{attr_name}' not initialized in PassiveExtractionWorkflow")
            
            attr_value = getattr(self, attr_name)
            if attr_value is None:
                raise AttributeError(f"Critical attribute '{attr_name}' is None in PassiveExtractionWorkflow")
            
            if not isinstance(attr_value, expected_type):
                raise AttributeError(f"Critical attribute '{attr_name}' has wrong type. Expected {expected_type}, got {type(attr_value)}")
        
        self.log.info("✅ Initialization validation passed - all critical attributes verified")

    async def run(self):
        """Main execution loop for the workflow."""
        profitable_results: List[Dict[str, Any]] = []
        session_id = f"{self.supplier_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.log.info(f"--- Starting Passive Extraction Workflow for: {self.supplier_name} ---")
        self.log.info(f"Session ID: {session_id}")

        # FIXED: Load configuration values directly from system_config (no hardcoded fallbacks)
        # This ensures all toggle experiments work correctly
        
        # CRITICAL FIX: The SystemConfigLoader.get_system_config() returns the "system" section directly
        # So we don't need to access ["system"] again - it's already the system section
        max_products_to_process = self.system_config.get("max_products", 10)
        max_products_per_category = self.system_config.get("max_products_per_category", 5)
        max_analyzed_products = self.system_config.get("max_analyzed_products", 5)
        max_products_per_cycle = self.system_config.get("max_products_per_cycle", 5)
        supplier_extraction_batch_size = self.system_config.get("supplier_extraction_batch_size", 3)
        
        # Get the full config for accessing root level values
        full_config = self.config_loader._config
        max_categories_per_request = full_config.get("max_categories_per_request", 5)
        
        # CRITICAL FIX: Initialize max_price from config to prevent AttributeError
        self.max_price = full_config.get("processing_limits", {}).get("max_price_gbp", 20.0)
        
        # Apply batch synchronization if enabled
        batch_sync_config = full_config.get("batch_synchronization", {})
        if batch_sync_config.get("enabled", False):
            max_products_per_cycle, supplier_extraction_batch_size = self._apply_batch_synchronization(
                max_products_per_cycle, supplier_extraction_batch_size, batch_sync_config
            )
        
        self.log.info(f"📊 CONFIGURATION VALUES:")
        self.log.info(f"   max_products_to_process: {max_products_to_process}")
        self.log.info(f"   max_products_per_category: {max_products_per_category}")
        self.log.info(f"   max_analyzed_products: {max_analyzed_products}")
        self.log.info(f"   max_products_per_cycle: {max_products_per_cycle}")
        self.log.info(f"   supplier_extraction_batch_size: {supplier_extraction_batch_size}")
        self.log.info(f"   max_categories_per_request: {max_categories_per_request}")

        # Load state and linking map
        self.state_manager.load_state()
        self.last_processed_index = self.state_manager.get_resume_index()
        self.consecutive_amazon_price_misses = self.state_manager.state_data.get('consecutive_amazon_price_misses', 0)
        self.log.info(f"📋 Loaded existing processing state for {self.supplier_name}")
        self.log.info(f"🔄 Resuming from index {self.last_processed_index}")

        # Hard reset logic: General cache validation without category dependency
        supplier_cache_file = os.path.join(self.supplier_cache_dir, f"{self.supplier_name.replace('.', '-')}_products_cache.json")
        if not os.path.exists(supplier_cache_file) or os.path.getsize(supplier_cache_file) == 0:
            if self.last_processed_index > 0:
                self.log.warning("🔥 State file shows progress, but supplier cache is empty. Wiping state to restart.")
                self.state_manager.hard_reset()
                self.last_processed_index = 0
            else:
                self.log.info("✅ No previous progress found, starting fresh.")
        
        # Load the linking map for the current supplier
        self.linking_map = self._load_linking_map(self.supplier_name)
        self.log.debug(f"🔍 DEBUG: linking_map loaded as type: {type(self.linking_map)}, length: {len(self.linking_map)}")

        try:
            # Note: Supplier configuration is loaded automatically by ConfigurableSupplierScraper
            # Load the linking map for the current supplier
            self.linking_map = self._load_linking_map(self.supplier_name)

            # --- CUSTOM CATEGORY LOGIC ---
            if self.workflow_config.get('use_predefined_categories'):
                self.log.info("CUSTOM MODE: Using predefined category list.")
                category_urls_to_scrape = await self._get_predefined_categories(self.supplier_name)
                if not category_urls_to_scrape:
                    self.log.error("CUSTOM MODE FAILED: No URLs found in predefined list. Aborting.")
                    return []
                max_categories_to_process = self.workflow_config.get('max_categories_to_process', 0)
                if max_categories_to_process > 0:
                    self.log.info(f"Limiting to {max_categories_to_process} categories as per configuration.")
                    category_urls_to_scrape = category_urls_to_scrape[:max_categories_to_process]
            else:
                # Original AI-based category selection
                self.log.info("STANDARD MODE: Using AI-based hierarchical category selection.")
                category_urls_to_scrape = await self._hierarchical_category_selection(self.workflow_config.get('supplier_url'), self.supplier_name)
                if not category_urls_to_scrape:
                    self.log.warning("No categories selected for scraping. Workflow cannot continue.")
                    return []

            # Check hybrid processing configuration (from full config, not system section)
            hybrid_config = full_config.get("hybrid_processing", {})
            if hybrid_config.get("enabled", False):
                self.log.info("🔄 HYBRID PROCESSING MODE: Enabled")
                return await self._run_hybrid_processing_mode(
                    self.workflow_config.get('supplier_url'), self.supplier_name, category_urls_to_scrape, 
                    max_products_per_category, max_products_to_process, 
                    max_analyzed_products, max_products_per_cycle, supplier_extraction_batch_size
                )
            
            supplier_products = await self._extract_supplier_products(
                self.workflow_config.get('supplier_url'), self.supplier_name, category_urls_to_scrape, max_products_per_category, max_products_to_process, supplier_extraction_batch_size
            )

            if not supplier_products:
                self.log.warning(f"No products extracted from {self.supplier_name}. Workflow cannot continue.")
                return []

            self.results_summary["total_supplier_products"] = len(supplier_products)
            self.log.info(f"Successfully got {len(supplier_products)} products from {self.supplier_name}")
            
            # Save supplier products to cache immediately after extraction
            supplier_cache_file = os.path.join(self.supplier_cache_dir, f"{self.supplier_name.replace('.', '-')}_products_cache.json")
            self._save_products_to_cache(supplier_products, supplier_cache_file)

            # Filter products based on price and validity
            valid_supplier_products = [
                p for p in supplier_products
                if p.get("title") and isinstance(p.get("price"), (float, int)) and p.get("price", 0) > 0 and p.get("url")
            ]
            price_filtered_products = [
                p for p in valid_supplier_products
                if MIN_PRICE <= p.get("price", 0) <= MAX_PRICE
            ]
            self.log.info(f"Found {len(valid_supplier_products)} valid supplier products, {len(price_filtered_products)} within price range [£{MIN_PRICE}-£{MAX_PRICE}]")
            
            # Check if all cached products have been processed
            if self.last_processed_index >= len(price_filtered_products):
                self.log.info(f"📋 All cached products have been processed in previous runs (index {self.last_processed_index} >= total {len(price_filtered_products)}). Continuing with fresh data...")
                self.last_processed_index = 0
            
            # Apply max_products_to_process limit starting from resume index
            if max_products_to_process <= 0:
                # Unlimited mode - process all remaining products
                products_to_analyze = price_filtered_products[self.last_processed_index:]
                self.log.info(f"🔄 UNLIMITED MODE: Processing ALL {len(products_to_analyze)} remaining products starting from index {self.last_processed_index}")
            else:
                # Limited mode - process up to max_products_to_process starting from resume index
                end_index = min(self.last_processed_index + max_products_to_process, len(price_filtered_products))
                products_to_analyze = price_filtered_products[self.last_processed_index:end_index]
                self.log.info(f"🔄 LIMITED MODE: Processing {len(products_to_analyze)} products (from index {self.last_processed_index} to {end_index-1})")
            
            # Update processing state with total products to analyze
            self.state_manager.update_processing_index(self.last_processed_index, len(price_filtered_products))

            # Batch processing logic - group products by max_products_per_cycle
            batch_size = max_products_per_cycle
            total_batches = (len(products_to_analyze) + batch_size - 1) // batch_size
            self.log.info(f"🚀 BATCH PROCESSING: {len(products_to_analyze)} products in {total_batches} batches of {batch_size}")

            # Process products in batches
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(products_to_analyze))
                batch_products = products_to_analyze[start_idx:end_idx]
                
                self.log.info(f"🔄 Processing batch {batch_num + 1}/{total_batches} ({len(batch_products)} products)")
                
                # Process each product in the current batch
                for i, product_data in enumerate(batch_products):
                    # Calculate the absolute index in the full product list (considering resume index)
                    current_index = self.last_processed_index + start_idx + i + 1
                    self.log.info(f"--- Processing supplier product {current_index}/{len(price_filtered_products)}: '{product_data.get('title')}' ---")
                    
                    # Update processing index for resumability (CRITICAL FIX)
                    self.log.info(f"🔍 DEBUG: Updating processing index to {current_index}/{len(price_filtered_products)}")
                    self.state_manager.update_processing_index(current_index, len(price_filtered_products))
                    # Verify the update worked
                    current_state = self.state_manager.get_state_summary()
                    self.log.info(f"🔍 DEBUG: State after update - last_processed_index: {current_state.get('progress', 'unknown')}")
                    
                    # Check if product has been previously processed
                    if self.state_manager.is_product_processed(product_data.get("url")):
                        self.log.info(f"Product already processed: {product_data.get('url')}. Skipping.")
                        continue

                    # Extract Amazon data
                    self.log.info(f"🔍 DEBUG: About to extract Amazon data for product: '{product_data.get('title')}'")
                    self.log.info(f"🔍 DEBUG: Product EAN/barcode: {product_data.get('ean')} / {product_data.get('barcode')}")
                    
                    amazon_data = await self._get_amazon_data(product_data)
                    
                    self.log.info(f"🔍 DEBUG: Amazon data extraction result: {type(amazon_data)}")
                    if amazon_data:
                        self.log.info(f"🔍 DEBUG: Amazon data keys: {list(amazon_data.keys()) if isinstance(amazon_data, dict) else 'not a dict'}")
                        if isinstance(amazon_data, dict) and "error" not in amazon_data:
                            self.log.info(f"🔍 DEBUG: Amazon ASIN extracted: {amazon_data.get('asin')}")
                        
                    if not amazon_data or "error" in amazon_data:
                        self.log.warning(f"Could not retrieve valid Amazon data for '{product_data.get('title')}'. Skipping.")
                        self.log.warning(f"🔍 DEBUG: Amazon data failure: {amazon_data}")
                        self.state_manager.mark_product_processed(product_data.get("url"), "failed_amazon_extraction")
                        continue

                    # Save the Amazon data with the correct filename
                    supplier_ean = product_data.get("ean") or product_data.get("barcode")
                    # Ensure we don't get None values
                    if supplier_ean == "None" or supplier_ean is None:
                        supplier_ean = None
                    
                    # Use supplier product title when EAN is not available
                    if not supplier_ean:
                        # Sanitize supplier product title for filename
                        supplier_title = product_data.get("title", "NO_TITLE")
                        # Remove/replace characters that aren't safe for filenames
                        import re
                        filename_identifier = re.sub(r'[<>:"/\\|?*]', '_', supplier_title)
                        filename_identifier = re.sub(r'\s+', '_', filename_identifier)  # Replace spaces with underscores
                        filename_identifier = filename_identifier[:50]  # Limit length to prevent long filenames
                        self.log.info(f"🔧 Using supplier title for Amazon cache filename: '{supplier_title}' -> '{filename_identifier}'")
                    else:
                        filename_identifier = supplier_ean
                    
                    asin = amazon_data.get("asin", "NO_ASIN")
                    amazon_cache_path = os.path.join(self.amazon_cache_dir, f"amazon_{asin}_{filename_identifier}.json")
                    with open(amazon_cache_path, 'w', encoding='utf-8') as f:
                        json.dump(amazon_data, f, indent=2, ensure_ascii=False)
                    self.log.info(f"Saved Amazon data to {amazon_cache_path}")

                    # Add EAN→ASIN mapping to linking map (CRITICAL FIX: Track actual search method)
                    self.log.info(f"🔍 DEBUG: supplier_ean='{supplier_ean}', asin='{asin}', product_ean='{product_data.get('ean')}'")
                    self.log.info(f"🔍 DEBUG: Checking linking conditions - supplier_ean valid: {bool(supplier_ean)}, asin valid: {bool(asin and asin != 'NO_ASIN')}")
                    
                    # Get actual search method used (fixed logic)
                    actual_search_method = amazon_data.get("_search_method_used", "unknown")
                    
                    # Create linking entry with accurate method and confidence
                    self.log.info(f"🔍 DEBUG: Linking map entry conditions check:")
                    self.log.info(f"   supplier_ean: '{supplier_ean}' (valid: {bool(supplier_ean)})")
                    self.log.info(f"   product_title: '{product_data.get('title')}' (valid: {bool(product_data.get('title'))})")
                    self.log.info(f"   asin: '{asin}' (valid: {bool(asin and asin != 'NO_ASIN')})")
                    self.log.info(f"   overall condition: {bool((supplier_ean or product_data.get('title')) and asin and asin != 'NO_ASIN')}")
                    
                    if (supplier_ean or product_data.get("title")) and asin and asin != "NO_ASIN":
                        # Determine confidence based on actual search success, not just supplier data availability
                        if actual_search_method == "EAN":
                            confidence = "high"  # EAN search actually worked
                        elif actual_search_method == "title":
                            confidence = "medium"  # Title search worked
                        else:
                            confidence = "low"  # Unknown method
                            
                        linking_entry = {
                            "supplier_ean": supplier_ean,
                            "amazon_asin": asin,
                            "supplier_title": product_data.get("title"),
                            "amazon_title": amazon_data.get("title"),
                            "supplier_price": product_data.get("price"),
                            "amazon_price": amazon_data.get("current_price"),
                            "match_method": actual_search_method,  # Use actual method, not assumption
                            "confidence": confidence,
                            "created_at": datetime.now().isoformat(),
                            "supplier_url": product_data.get("url")
                        }
                        # CRITICAL FIX: Use dictionary assignment, not append
                        self.linking_map[supplier_ean or product_data.get("url")] = linking_entry
                        self.log.info(f"✅ Added linking map entry: {actual_search_method.upper()} search {supplier_ean or 'NO_EAN'} → ASIN {asin}")
                        self.log.info(f"🔍 DEBUG: Current linking_map size: {len(self.linking_map)} entries")
                        self.log.info(f"🔍 DEBUG: Linking entry created: {linking_entry}")
                    else:
                        self.log.error(f"❌ CRITICAL: Could not create linking map entry - condition failed!")
                        self.log.error(f"   supplier_ean: '{supplier_ean}' (bool: {bool(supplier_ean)})")
                        self.log.error(f"   product_title: '{product_data.get('title')}' (bool: {bool(product_data.get('title'))})")
                        self.log.error(f"   asin: '{asin}' (bool: {bool(asin and asin != 'NO_ASIN')})")
                        self.log.error(f"   This means NO linking map entries will be created and saved!")

                    # Perform financial analysis for individual product
                    try:
                        # Import financial calculation functions directly to avoid full cache dependency
                        from FBA_Financial_calculator import financials as calc_financials
                        
                        # Extract supplier price with validation from the linking map entry
                        supplier_price_inc_vat = linking_entry.get("supplier_price", 0)
                        if isinstance(supplier_price_inc_vat, str):
                            # Clean price string and convert to float
                            import re
                            price_clean = re.sub(r'[^0-9.]', '', supplier_price_inc_vat)
                            supplier_price_inc_vat = float(price_clean) if price_clean else 0
                        elif supplier_price_inc_vat is None:
                            supplier_price_inc_vat = 0
                            
                        # Calculate financial metrics for this specific product
                        financials = calc_financials(product_data, amazon_data, supplier_price_inc_vat)
                        
                        if not financials:
                            self.log.warning(f"Financial calculation returned empty for '{product_data.get('title')}'")
                            financials = {}
                            
                    except Exception as e:
                        self.log.error(f"Financial calculation failed for '{product_data.get('title')}': {e}")
                        self.state_manager.mark_product_processed(product_data.get("url"), "failed_financial_calculation")
                        # Continue with empty financials rather than failing completely
                        financials = {}

                    # Combine all data
                    combined_data = {**product_data, "amazon_data": amazon_data, "financials": financials}
                                
                    # Check for profitability
                    if financials.get("ROI", 0) > MIN_ROI_PERCENT and financials.get("NetProfit", 0) > MIN_PROFIT_PER_UNIT:
                        self.log.info(f"✅ Profitable product found: '{product_data.get('title')}' (ROI: {financials.get('ROI'):.2f}%, Profit: £{financials.get('NetProfit'):.2f})")
                        profitable_results.append(combined_data)
                        self.results_summary["profitable_products"] += 1
                        self.state_manager.mark_product_processed(product_data.get("url"), "profitable")
                    else:
                        self.log.info(f"Product not profitable: '{product_data.get('title')}' (ROI: {financials.get('ROI', 0):.2f}%, Profit: £{financials.get('NetProfit', 0):.2f})")
                        self.state_manager.mark_product_processed(product_data.get("url"), "not_profitable")

                    # Save state periodically using configurable batch sizes
                    overall_product_index = start_idx + i + 1
                    linking_map_batch = self.system_config.get("system", {}).get("linking_map_batch_size", 3)
                    
                    if overall_product_index % linking_map_batch == 0:
                        self.state_manager.save_state()
                        self._save_linking_map(self.supplier_name)
                        self.log.info(f"📊 Periodic save at product {overall_product_index} (linking_map_batch_size: {linking_map_batch})")

            # Final save and completion
            self.log.info("🔍 DEBUG: Starting final save and completion phase...")
            try:
                self.log.info("🔍 DEBUG: Calling state_manager.complete_processing()...")
                self.state_manager.complete_processing()
                self.log.info("✅ State manager processing completed")
                
                self.log.info(f"🔍 DEBUG: Calling _save_linking_map with supplier_name='{self.supplier_name}'...")
                self._save_linking_map(self.supplier_name)
                self.log.info("✅ Linking map save completed")
                
                self.log.info(f"🔍 DEBUG: Calling _save_final_report with {len(profitable_results)} profitable results...")
                self._save_final_report(profitable_results, self.supplier_name)
                self.log.info("✅ Final report save completed")
                
            except Exception as final_save_error:
                self.log.error(f"❌ CRITICAL: Error during final save phase: {final_save_error}", exc_info=True)
                self.log.error("This explains why linking map and financial reports are not being saved!")
            
            
            
            self.log.info(f"📊 Processing state file saved: {self.state_manager.state_file_path}")
            self.log.info(f"📊 Final state summary: {self.state_manager.get_state_summary()}")
            self.log.info("--- Passive Extraction Workflow Finished ---")
            self.log.info(f"Summary: {self.results_summary}")
            return profitable_results

        except Exception as e:
            self.log.error(f"Unexpected error occurred during workflow execution: {e}", exc_info=True)
            return []


    def _save_converted_linking_map(self, supplier_name: str, linking_map: Dict[str, str]) -> None:
        """Write converted linking map back to disk using path_manager."""
        from utils.path_manager import get_linking_map_path

        linking_map_path = get_linking_map_path(supplier_name)
        temp_path = f"{linking_map_path}.tmp"

        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(linking_map, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, linking_map_path)
            self.log.info(f"✅ Saved converted linking map to {linking_map_path}")
        except Exception as e:
            self.log.error(f"Error saving converted linking map: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

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

    async def _get_predefined_categories(self, supplier_name: str) -> list:
        """Load predefined category URLs from a custom JSON file."""
        log.info(f"Attempting to load predefined categories for {supplier_name}")
        try:
            # Robust path construction using pathlib
            config_path = Path(__file__).parent.parent / "config" / f"{supplier_name.replace('.co.uk', '')}_categories.json"
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    category_urls = data.get("category_urls", [])
                    log.info(f"✅ Successfully loaded {len(category_urls)} predefined category URLs from {config_path}")
                    return category_urls
            else:
                log.warning(f"⚠️ Predefined category file not found at {config_path}")
                return []
        except FileNotFoundError:
            log.error(f"❌ Configuration file not found: {config_path}")
            return []
        except json.JSONDecodeError as e:
            log.error(f"❌ Invalid JSON in configuration file: {e}")
            return []
        except Exception as e:
            log.error(f"❌ Unexpected error loading predefined categories: {e}")
            return []

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
        # DEPRECATED: Replaced by EnhancedStateManager to prevent state conflicts
        # self._save_history(hist)

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
            if (
                self._classify_url(c["url"]) == "friendly" and
                c["url"] not in prev_cats and
                not any(prev_url in c["url"] or c["url"] in prev_url for prev_url in prev_cats)
            ):
                available_categories.append(c)

        # Limit to reasonable number for AI processing
        category_limit = self.system_config.get("ai_features", {}).get("category_selection", {}).get("max_categories_per_request", 3)
        friendly = available_categories[:category_limit]
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
    "detailed_reasoning": {{\"category_name\": \"detailed reason for selection/skipping including URL pattern analysis\"}},
    "progression_strategy": "description of your category selection strategy focusing on product listing identification",
    "url_pattern_confidence": {{\"high_confidence\": [\"urls you're very confident contain products\"], \"medium_confidence\": [\"urls that might contain products\"], \"low_confidence\": [\"urls unlikely to contain products\"]}}
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
        model_to_use = "gpt-4.1-mini-2025-04-14"  # Use gpt-4.1-mini for consistency

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
        """DEPRECATED: URL optimization is now handled by supplier-specific extraction scripts"""
        optimized_urls = []

        for url in urls:
            # Base parameters for better product retrieval (generic, no price filtering)
            # ❌ COMMENTED OUT - hardcoded for different website, not compatible with poundwholesale.co.uk
            # base_params = "product_list_limit=64&product_list_order=price&product_list_dir=asc"

            # Add parameters to URL
            # ❌ COMMENTED OUT - using raw URLs for poundwholesale.co.uk compatibility
            # if '?' in url:
            #     optimized_url = f"{url}&{base_params}"
            # else:
            #     optimized_url = f"{url}?{base_params}"

            # ✅ USE RAW URL for poundwholesale.co.uk
            optimized_url = url
            optimized_urls.append(optimized_url)
            log.info(f"Using raw URL (poundwholesale.co.uk): {url}")

        return optimized_urls

    def _save_api_call_log(self, prompt: str, response, model: str, call_type: str):
        """Save detailed OpenAI API call logs for debugging and token tracking"""
        try:
            from pathlib import Path

            # Create API logs directory using proper path management (claude.md standards)
            from utils.path_manager import get_api_log_path, get_linking_map_path
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
                    "phase_transition": f"Phase 1 (£{self.min_price}-£{self.price_midpoint}) complete, starting Phase 2 (£{self.price_midpoint}-£{MAX_PRICE})",
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
        """Save products to cache file with progress feedback"""
        try:
            # Get cache control configuration
            cache_config = self.system_config.get("supplier_cache_control", {})
            
            # Progress feedback for cache operations
            if cache_config.get("enabled", True):
                self.log.info(f"💾 CACHE SAVE: Starting save of {len(products)} products to cache...")
            
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

            # FIX 3: Supplier cache deduplication - Enhanced EAN-based deduplication
            existing_urls = {p.get('url', '') for p in existing_products}
            existing_eans = {p.get('ean', '') for p in existing_products if p.get('ean') and p.get('ean') != 'None'}
            
            # Filter out products with duplicate URLs or EANs
            new_products = []
            ean_duplicates_skipped = 0
            url_duplicates_skipped = 0
            
            for p in products:
                product_url = p.get('url', '')
                product_ean = p.get('ean', '')
                
                # Skip if URL already exists
                if product_url and product_url in existing_urls:
                    url_duplicates_skipped += 1
                    continue
                
                # FIX 3: Skip if EAN already exists and is not empty/None
                if product_ean and product_ean != 'None' and product_ean in existing_eans:
                    ean_duplicates_skipped += 1
                    self.log.debug(f"Skipping duplicate EAN: {product_ean}")
                    continue
                
                new_products.append(p)
                
                # Add to tracking sets to prevent duplicates within current batch
                if product_url:
                    existing_urls.add(product_url)
                if product_ean and product_ean != 'None':
                    existing_eans.add(product_ean)

            all_products = existing_products + new_products

            # Save to cache
            with open(cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(all_products, f, indent=2, ensure_ascii=False)

            # Enhanced progress feedback with deduplication statistics
            if cache_config.get("enabled", True):
                self.log.info(f"✅ CACHE SAVE: Successfully saved {len(all_products)} products ({len(new_products)} new) to {os.path.basename(cache_file_path)}")
                if ean_duplicates_skipped > 0 or url_duplicates_skipped > 0:
                    self.log.info(f"🔄 DEDUPLICATION: Skipped {ean_duplicates_skipped} EAN duplicates and {url_duplicates_skipped} URL duplicates")
            else:
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
        # DEPRECATED: Replaced by EnhancedStateManager to prevent state conflicts
        # hist = self._load_history()
        hist = {"categories_scraped": [], "ai_suggested_categories": []}  # Minimal hist for legacy compatibility

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
            log.info(f"All categories processed in Phase 1 (£{self.min_price}-£{self.price_midpoint}). Moving to Phase 2 (£{self.price_midpoint}-£{MAX_PRICE})...")
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
        # DEPRECATED: Replaced by EnhancedStateManager to prevent state conflicts

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
                cache_data.setdefault("ai_suggestion_history", []).append(new_entry)
                cache_data["total_ai_calls"] = cache_data.get("total_ai_calls", 0) + 1
                cache_data["last_updated"] = datetime.now().isoformat()

            # Save updated cache data
            with open(cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            log.info(f"🧠 Saved AI category suggestions to cache: {cache_file_path}")

        except Exception as e:
            log.error(f"Error saving AI category suggestions to cache: {e}")

        return optimized_urls

    async def _extract_supplier_products(self, supplier_url: str, supplier_name: str, category_urls: List[str], max_products_per_category: int, max_products_to_process: int = None, supplier_extraction_batch_size: int = 3) -> List[Dict[str, Any]]:
        """Extract products from a list of category URLs with overall product limit enforcement."""
        
        # 🔄 SUPPLIER CACHE FRESHNESS CHECK
        # If we have cached products and processing state indicates progress, skip supplier scraping
        cached_products_path = os.path.join(self.supplier_cache_dir, f"{supplier_name.replace('.', '-')}_products_cache.json")
        
        if os.path.exists(cached_products_path) and hasattr(self, 'state_manager') and self.state_manager:
            try:
                # Check if we have processing state indicating previous progress
                if hasattr(self.state_manager, 'state_data') and self.state_manager.state_data:
                    last_index = self.state_manager.state_data.get('last_processed_index', 0)
                    processing_status = self.state_manager.state_data.get('processing_status', 'not_started')
                    
                    # Check cache file age (fresh within 24 hours)
                    import time
                    cache_age_hours = (time.time() - os.path.getmtime(cached_products_path)) / 3600
                    cache_is_fresh = cache_age_hours < 24
                    
                    if last_index > 0 and cache_is_fresh:
                        self.log.info(f"🔄 SKIPPING SUPPLIER SCRAPING: Found fresh cached products (age: {cache_age_hours:.1f}h) with processing progress (index: {last_index})")
                        self.log.info(f"📋 Loading products from cache: {cached_products_path}")
                        
                        # Load cached products instead of scraping
                        import json
                        with open(cached_products_path, 'r', encoding='utf-8') as f:
                            cached_products = json.load(f)
                        self.log.info(f"✅ Loaded {len(cached_products)} cached products from {cached_products_path}")
                        return cached_products
                    elif not cache_is_fresh:
                        self.log.info(f"🔄 CACHE STALE: Cache age {cache_age_hours:.1f}h > 24h threshold, proceeding with fresh scraping")
                        # Reset processing index since we're re-scraping (product list may have changed)
                        if hasattr(self, 'last_processed_index'):
                            self.last_processed_index = 0
                            self.log.info(f"⚠️ Reset processing index to 0 due to stale cache")
                    else:
                        self.log.info(f"🔄 NO PROCESSING PROGRESS: index={last_index}, proceeding with scraping")
                        
            except Exception as e:
                self.log.warning(f"⚠️ Error checking supplier cache freshness: {e}, proceeding with scraping")
        
        # Proceed with normal supplier scraping with batching
        # supplier_extraction_batch_size is now passed as a parameter
        self.log.info(f"🕷️ PERFORMING SUPPLIER SCRAPING from {len(category_urls)} categories")
        self.log.info(f"📦 Using supplier extraction batch size: {supplier_extraction_batch_size}")
        
        # Process categories in batches for better memory management
        all_products = []
        # Store as instance variable for progress callback access
        self._current_all_products = all_products
        category_batches = [category_urls[i:i + supplier_extraction_batch_size] for i in range(0, len(category_urls), supplier_extraction_batch_size)]
        
        # Get progress tracking configuration
        progress_config = self.system_config.get("supplier_extraction_progress", {})
        cache_config = self.system_config.get("supplier_cache_control", {})
        
        # Initialize extraction progress tracking
        if progress_config.get("enabled", True):
            self.log.info(f"📊 PROGRESS TRACKING: Extracting from {len(category_urls)} categories in {len(category_batches)} batches")
        
        for batch_num, category_batch in enumerate(category_batches, 1):
            # Check if we've reached the overall product limit before starting a new batch
            if max_products_to_process and len(all_products) >= max_products_to_process:
                self.log.info(f"🛑 STOPPING: Reached max_products_to_process limit of {max_products_to_process} products before batch {batch_num}")
                break
                
            self.log.info(f"📦 Processing category batch {batch_num}/{len(category_batches)} ({len(category_batch)} categories)")
            
            for subcategory_index, category_url in enumerate(category_batch, 1):
                # Update detailed progress tracking
                if progress_config.get("enabled", True) and hasattr(self, 'state_manager'):
                    category_index = (batch_num - 1) * supplier_extraction_batch_size + subcategory_index
                    self.state_manager.update_supplier_extraction_progress(
                        category_index=category_index,
                        total_categories=len(category_urls),
                        subcategory_index=subcategory_index,
                        total_subcategories=len(category_batch),
                        batch_number=batch_num,
                        total_batches=len(category_batches),
                        category_url=category_url,
                        extraction_phase="categories"
                    )
                    
                    if progress_config.get("progress_display", {}).get("show_subcategory_progress", True):
                        self.log.info(f"🔄 EXTRACTION PROGRESS: Processing subcategory {subcategory_index}/{len(category_batch)} in batch {batch_num} (Category {category_index}/{len(category_urls)})")
                
                # Setup progress callback for individual product tracking
                if hasattr(self.supplier_scraper, 'set_progress_callback'):
                    self.supplier_scraper.set_progress_callback(self._create_product_progress_callback(category_url, progress_config))
                # Check if we've reached the overall product limit
                if max_products_to_process and len(all_products) >= max_products_to_process:
                    self.log.info(f"🛑 STOPPING: Reached max_products_to_process limit of {max_products_to_process} products")
                    break
                    
                self.log.info(f"Scraping category: {category_url}")
                # 🚨 DEFINITIVE FIX: Pass all_products as product_accumulator for real-time updates
                products = await self.supplier_scraper.scrape_products_from_url(
                    category_url,
                    max_products_per_category,
                    product_accumulator=all_products  # Share the list for real-time cache saves
                )
                
                # 🚨 REMOVED: Price filtering and product extension now handled in progress callback
                # Products are added to all_products immediately when found via progress_callback
                # This ensures per-product cache saves work correctly with live data
                self.log.info(f"📊 Category completed: {len(products)} raw products extracted, {len(all_products)} total products accumulated")
                
                # 🚨 REMOVED: Category-based cache saving logic (now handled per-product in progress callback)
                # This was causing the update_frequency_products to only save after complete categories
                # instead of respecting the per-product frequency configuration
                
                # Check again after adding products from this category
                if max_products_to_process and len(all_products) >= max_products_to_process:
                    # Trim to exact limit if we exceeded it
                    all_products = all_products[:max_products_to_process]
                    self.log.info(f"🛑 TRIMMED: Limited to exactly {max_products_to_process} products")
                    break
            
            # Batch completion logging
            self.log.info(f"✅ Completed batch {batch_num}: {len(all_products)} total products extracted so far")
                
        return all_products

    def _create_product_progress_callback(self, category_url: str, progress_config: Dict[str, Any]):
        """Create a progress callback for individual product extraction with proper caching"""
        # Initialize a simple counter if it doesn't exist
        if not hasattr(self, '_supplier_product_counter'):
            self._supplier_product_counter = 0
            
        def progress_callback(operation_type: str, product_index: int, total_products: int, product_url: str, product_data: dict = None):
            if operation_type == 'supplier_extraction':
                # Increment global product counter
                self._supplier_product_counter += 1
                
                # 🚨 DEFINITIVE FIX: Products are now added by scraper directly to shared list
                # Progress callback only needs to track progress and trigger cache saves
                if product_data and hasattr(self, '_current_all_products'):
                    self.log.info(f"📊 PROGRESS: Product {self._supplier_product_counter} processed (total in cache: {len(self._current_all_products)})")
                
                # Simple index-based logging (matching Amazon analysis style)
                if progress_config.get("progress_display", {}).get("show_product_progress", True):
                    self.log.info(f"🔄 SUPPLIER EXTRACTION: Processing product {self._supplier_product_counter}")
                
                # 🚨 NEW: Per-product cache saving logic (now works because list is populated)
                cache_config = self.system_config.get("supplier_cache_control", {})
                update_frequency = cache_config.get("update_frequency_products", 2)  # Use config value
                
                # Debug logging for cache save logic
                self.log.info(f"🔍 CACHE CHECK: Product {self._supplier_product_counter}, frequency={update_frequency}, enabled={cache_config.get('enabled', True)}")
                self.log.info(f"🔍 CACHE CHECK: List length={len(getattr(self, '_current_all_products', []))}, modulo={self._supplier_product_counter % update_frequency}")
                
                if (cache_config.get("enabled", True) and 
                    hasattr(self, '_current_all_products') and
                    len(self._current_all_products) > 0 and
                    self._supplier_product_counter % update_frequency == 0):
                    
                    # Import path_manager for proper path handling
                    from utils.path_manager import path_manager
                    
                    # Build cache path using path_manager
                    cache_filename = f"{self.supplier_name.replace('.', '-')}_products_cache.json"
                    cache_file_path = path_manager.get_output_path("cached_products", cache_filename)
                    
                    # Save current products to cache
                    self._save_products_to_cache(self._current_all_products, cache_file_path)
                    self.log.info(f"💾 PERIODIC CACHE SAVE: Saved {len(self._current_all_products)} products to cache (every {update_frequency} products)")
                    
                # Update state for interruption recovery
                if hasattr(self, 'state_manager'):
                    progress = self.state_manager.state_data["supplier_extraction_progress"]
                    progress["products_extracted_total"] = self._supplier_product_counter
                    progress["current_product_url"] = product_url
                    progress["extraction_phase"] = "products"
                    self.state_manager.save_state()
                    
        return progress_callback

    def _check_amazon_cache_by_asin(self, asin: str, supplier_ean: str = None) -> Optional[Dict[str, Any]]:
        """Check for existing Amazon cache data by ASIN with multiple filename patterns."""
        import glob
        import time
        
        # FIX 2: Amazon cache reuse logic - Enhanced ASIN/EAN matching
        amazon_cache_dir = self.amazon_cache_dir
        
        # First: Check for exact EAN match
        if supplier_ean:
            exact_pattern = f"amazon_{asin}_{supplier_ean}.json"
            exact_file = os.path.join(amazon_cache_dir, exact_pattern)
            if os.path.exists(exact_file):
                try:
                    with open(exact_file, 'r', encoding='utf-8') as f:
                        self.log.info(f"📋 Found exact EAN match in cache: {exact_pattern}")
                        return json.load(f)
                except Exception as e:
                    self.log.error(f"Error loading exact EAN match cache: {e}")
        
        # Second: Check for ASIN with different EAN - copy to new filename
        cache_patterns = [
            f"amazon_{asin}_*.json",  # ASIN with any suffix
            f"amazon_{asin}.json"     # ASIN only
        ]
        
        for pattern in cache_patterns:
            cache_path_pattern = os.path.join(amazon_cache_dir, pattern)
            matching_files = sorted(glob.glob(cache_path_pattern), key=os.path.getmtime, reverse=True)

            for cache_file in matching_files:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                except Exception as e:
                    self.log.error(f"Error loading cached Amazon data from {cache_file}: {e}")
                    continue

                # Gather all EAN values present in the cache file
                eans_in_cache = set()
                if cached_data.get("ean"):
                    eans_in_cache.add(str(cached_data.get("ean")))
                if cached_data.get("ean_on_page"):
                    eans_in_cache.add(str(cached_data.get("ean_on_page")))
                for ean in cached_data.get("eans_on_page", []):
                    eans_in_cache.add(str(ean))

                if supplier_ean and supplier_ean not in eans_in_cache:
                    self.log.info(
                        f"Skipping cache file {os.path.basename(cache_file)} due to EAN mismatch"
                    )
                    continue

                # Copy existing cache to new EAN-specific filename if needed
                if supplier_ean:
                    new_filename = f"amazon_{asin}_{supplier_ean}.json"
                    new_filepath = os.path.join(amazon_cache_dir, new_filename)

                    if not os.path.exists(new_filepath):
                        try:
                            with open(new_filepath, 'w', encoding='utf-8') as f:
                                json.dump(cached_data, f, indent=2, ensure_ascii=False)
                            self.log.info(
                                f"📋 Copied existing cache to EAN-specific file: {new_filename}"
                            )
                        except Exception as copy_error:
                            self.log.error(f"Error copying cache to EAN-specific file: {copy_error}")

                self.log.info(f"📋 Found ASIN match in cache: {os.path.basename(cache_file)}")
                return cached_data
        
        return None

    async def _get_amazon_data(self, product_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle Amazon search logic (EAN first, then title)."""
        supplier_ean = product_data.get("ean")
        amazon_product_data = None
        actual_search_method = None  # Track which method actually worked
        
        if supplier_ean:
            self.log.info(f"Attempting Amazon search using EAN: {supplier_ean}")
            self.results_summary["products_analyzed_ean"] += 1
            
            # FIX 2: Enhanced Amazon cache reuse logic - Check cache before scraping
            # First try to find cached data by EAN before performing any searches
            cached_data = None
            found_asin = None
            
            # Check if we have cached data for this EAN
            amazon_cache_dir = os.path.join(self.output_dir, "FBA_ANALYSIS", "amazon_cache")
            if os.path.exists(amazon_cache_dir):
                for cache_file in os.listdir(amazon_cache_dir):
                    if cache_file.endswith(".json"):
                        # Check if supplier EAN matches filename
                        if supplier_ean in cache_file:
                            try:
                                with open(os.path.join(amazon_cache_dir, cache_file), 'r', encoding='utf-8') as f:
                                    cached_data = json.load(f)
                                    found_asin = cached_data.get("asin") or cached_data.get("asin_extracted_from_page")
                                    self.log.info(f"📋 Found cached Amazon data for EAN {supplier_ean} in file: {cache_file}")
                                    break
                            except Exception as e:
                                self.log.debug(f"Error reading cache file {cache_file}: {e}")
                        
                        # Check for ASIN matches that might need EAN-specific copying
                        elif cache_file.startswith("amazon_") and cache_file.endswith(".json"):
                            try:
                                # Extract ASIN from filename
                                asin_match = re.search(r'amazon_([A-Z0-9]{10})', cache_file)
                                if asin_match:
                                    cache_asin = asin_match.group(1)
                                    with open(os.path.join(amazon_cache_dir, cache_file), 'r', encoding='utf-8') as f:
                                        cache_data = json.load(f)
                                        cache_ean = cache_data.get("ean") or cache_data.get("ean_on_page")
                                        
                                        # Apply EAN validation like the patched _check_amazon_cache_by_asin function
                                        if cache_asin and cache_ean:
                                            # Gather all EAN values present in the cache file
                                            eans_in_cache = set()
                                            if cache_data.get("ean"):
                                                eans_in_cache.add(str(cache_data.get("ean")))
                                            if cache_data.get("ean_on_page"):
                                                eans_in_cache.add(str(cache_data.get("ean_on_page")))
                                            for ean in cache_data.get("eans_on_page", []):
                                                eans_in_cache.add(str(ean))

                                            # Skip if supplier EAN not found in cache EANs
                                            if supplier_ean not in eans_in_cache:
                                                self.log.info(f"Skipping cache file {cache_file} due to EAN mismatch: {supplier_ean} not in {eans_in_cache}")
                                                continue

                                            # EAN matches - use this cache
                                            cached_data = cache_data
                                            found_asin = cache_asin
                                            self.log.info(f"📋 Found matching EAN {supplier_ean} in cache file: {cache_file}")
                                            break
                            except Exception as e:
                                self.log.debug(f"Error checking cache file {cache_file} for ASIN reuse: {e}")
            
            if cached_data:
                amazon_product_data = cached_data
                actual_search_method = "EAN_cached"
                self.log.info(f"📋 Using cached Amazon data for EAN {supplier_ean}")
            else:
                # No cache found - perform EAN search
                amazon_product_data = await self.extractor.search_by_ean_and_extract_data(supplier_ean, product_data["title"])
            
            if amazon_product_data and "error" not in amazon_product_data:
                # EAN search succeeded (or we used cached data)
                found_asin = amazon_product_data.get("asin") or amazon_product_data.get("asin_extracted_from_page")
                
                if found_asin and actual_search_method != "EAN_cached":
                    # For fresh EAN search results, check if we need to copy to EAN-specific cache file
                    actual_search_method = "EAN"  # EAN search succeeded
                elif not found_asin:
                    actual_search_method = "EAN"  # EAN search succeeded but no ASIN found
                
                # FIX 1: EAN search successful - skip title search completely
                self.log.info(f"✅ EAN search successful for {supplier_ean}. Using EAN result without title fallback.")
                
                # Add search method info and return immediately to prevent title search
                amazon_product_data["_search_method_used"] = actual_search_method
                return amazon_product_data
            else:
                amazon_product_data = None # Reset if EAN search failed
                self.log.info(f"❌ EAN search failed for {supplier_ean}. Will fall back to title search.")
                
        if not amazon_product_data:
            if supplier_ean: self.log.info("EAN search failed. Falling back to title search.")
            else: self.log.info("No EAN. Using title search.")
            self.results_summary["products_analyzed_title"] += 1
            amazon_search_results = await self.extractor.search_by_title_using_search_bar(product_data["title"])
            if not amazon_search_results or "error" in amazon_search_results or not amazon_search_results.get("results"):
                self.log.warning(f"No Amazon results for title '{product_data['title']}'. Skipping.")
                return None
                
            # CRITICAL FIX: Use configurable confidence threshold to prevent irrational matches
            best_result = None
            best_confidence = 0.0
            
            # Use configurable confidence threshold instead of hardcoded value
            matching_thresholds = self.system_config.get("performance", {}).get("matching_thresholds", {})
            confidence_threshold = matching_thresholds.get("medium_title_similarity", 0.5)  # More conservative than old 0.4
            
            self.log.info(f"🔍 PRODUCT VALIDATION: Evaluating {len(amazon_search_results['results'])} Amazon results for '{product_data['title']}'")
            
            for i, result in enumerate(amazon_search_results["results"][:5]):  # Check top 5 results
                # Use existing _validate_product_match method (now fixed)
                amazon_product_data = {"title": result.get("title", "")}
                validation = self._validate_product_match(product_data, amazon_product_data)
                
                confidence = validation.get("confidence", 0.0)
                match_quality = validation.get("match_quality", "low")
                overlap_score = validation.get("title_overlap_score", 0.0)
                
                self.log.info(f"📊 Result {i+1}: ASIN {result.get('asin')} - Confidence: {confidence:.3f} ({match_quality}) - Overlap: {overlap_score:.3f} - '{result.get('title', 'No title')[:60]}...'")
                
                if confidence > best_confidence and confidence >= confidence_threshold:
                    best_confidence = confidence
                    best_result = result
            
            if not best_result:
                self.log.warning(f"🚨 NO CONFIDENT MATCH: All Amazon results below {confidence_threshold:.1%} confidence threshold for '{product_data['title']}'. Skipping to prevent irrational matches.")
                return None
            
            self.log.info(f"✅ BEST MATCH: ASIN {best_result.get('asin')} with {best_confidence:.1%} confidence")
            asin = best_result.get("asin")
            if not asin:
                self.log.warning(f"Could not determine ASIN for '{product_data['title']}'. Skipping.")
                return None
            
            # ENHANCEMENT: Check Amazon cache before scraping
            amazon_product_data = self._check_amazon_cache_by_asin(asin, supplier_ean)
            
            if amazon_product_data:
                # Cache hit - use cached data
                actual_search_method = "title_cached"
                self.log.info(f"📋 Using cached Amazon data for ASIN {asin}")
            else:
                # Cache miss - perform fresh extraction
                amazon_product_data = await self.extractor.extract_data(asin)
                if amazon_product_data and "error" not in amazon_product_data:
                    actual_search_method = "title"  # Title search succeeded
                
        if not amazon_product_data or "error" in amazon_product_data:
            self.log.warning(f"Failed to get valid Amazon data for '{product_data['title']}'. Skipping.")
            self.results_summary["errors"] += 1
            return None
            
        # Add search method info to the returned data for accurate linking map creation
        amazon_product_data["_search_method_used"] = actual_search_method
        return amazon_product_data



    def _combine_data(self, supplier_data: Dict[str, Any], amazon_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Combine supplier and Amazon data and calculate financial metrics."""
        combined = {
            "supplier_product_info": supplier_data,
            "amazon_product_info": amazon_data,
            "analysis_timestamp": datetime.now().isoformat(),
            "session_id": session_id
        }
        # Financial calculation is now handled within the main run loop before this function is called
        # This function is primarily for combining data and adding match validation
        match_validation = self._validate_product_match(supplier_data, amazon_data)
        combined["match_validation"] = match_validation
        return combined

    def _overlap_score(self, title_a: str, title_b: str) -> float:
        """Calculate word overlap score between two titles"""
        a = set(re.sub(r'[^\w\s]', ' ', title_a.lower()).split())
        b = set(re.sub(r'[^\w\s]', ' ', title_b.lower()).split())
        return len(a & b) / max(1, len(a))
    
    def _sanitize_filename(self, title: str) -> str:
        """Sanitize product title for use in filename"""
        if not title:
            return "unknown_title"
        # Remove or replace problematic characters
        sanitized = re.sub(r'[^\w\s-]', '', title)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized[:50]  # Limit length to 50 chars

    def _validate_product_match(self, supplier_product: Dict[str, Any], amazon_product: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the match between supplier and Amazon products using configurable thresholds."""
        # CRITICAL FIX: Use configurable matching thresholds instead of hardcoded values
        matching_thresholds = self.system_config.get("performance", {}).get("matching_thresholds", {})
        
        # Get configurable thresholds with fallback to more conservative defaults
        title_similarity_threshold = matching_thresholds.get("title_similarity", 0.25)
        medium_title_similarity = matching_thresholds.get("medium_title_similarity", 0.5) 
        high_title_similarity = matching_thresholds.get("high_title_similarity", 0.75)
        
        title_overlap_score = self._overlap_score(supplier_product.get("title", ""), amazon_product.get("title", ""))

        match_quality = "low"
        confidence = 0.0
        
        # Use configurable thresholds - much more strict than previous hardcoded values
        if title_overlap_score >= high_title_similarity:
            match_quality = "high"
            confidence = 0.9
        elif title_overlap_score >= medium_title_similarity:
            match_quality = "medium"
            confidence = 0.6
        elif title_overlap_score >= title_similarity_threshold:
            match_quality = "low"
            confidence = 0.3
        else:
            match_quality = "very_low"
            confidence = 0.1

        self.log.debug(f"🔍 MATCH VALIDATION: '{supplier_product.get('title', 'Unknown')}' vs '{amazon_product.get('title', 'Unknown')}' = {title_overlap_score:.2f} ({match_quality}, {confidence:.1%})")
        
        return {"match_quality": match_quality, "confidence": confidence, "title_overlap_score": title_overlap_score}

    def _is_product_meeting_criteria(self, combined_data: Dict[str, Any]) -> bool:
        """Check if a product meets all defined business criteria."""
        # This function is now largely redundant as profitability checks are done in the main loop.
        # However, it can be used for other criteria like sales rank, reviews, etc.
        amazon_data = combined_data.get("amazon_product_info", {})
        financials = combined_data.get("financials", {})
        # Check profitability (already done, but for completeness)
        is_profitable = financials.get("ROI", 0) > MIN_ROI_PERCENT and financials.get("NetProfit", 0) > MIN_PROFIT_PER_UNIT
        # Check Amazon listing quality
        meets_rating = amazon_data.get("rating", 0) >= MIN_RATING
        meets_reviews = amazon_data.get("reviews", 0) >= MIN_REVIEWS
        meets_sales_rank = amazon_data.get("sales_rank", MAX_SALES_RANK + 1) <= MAX_SALES_RANK
        # Check for battery products (using the helper function)
        is_battery = is_battery_title(amazon_data.get("title", "")) or is_battery_title(combined_data["supplier_product_info"].get("title", ""))
        # Check for other non-FBA friendly keywords
        is_non_fba_friendly = any(k in amazon_data.get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS) or \
                              any(k in combined_data["supplier_product_info"].get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS)
        # All criteria must be met
        return is_profitable and meets_rating and meets_reviews and meets_sales_rank and not is_battery and not is_non_fba_friendly

    def _apply_batch_synchronization(self, max_products_per_cycle: int, 
                                   supplier_extraction_batch_size: int,
                                   batch_sync_config: Dict[str, Any]) -> Tuple[int, int]:
        """
        Apply batch synchronization to align all batch sizes consistently.
        Returns updated max_products_per_cycle and supplier_extraction_batch_size.
        """
        target_batch_size = batch_sync_config.get("target_batch_size", 3)
        synchronize_all = batch_sync_config.get("synchronize_all_batch_sizes", False)
        validation_config = batch_sync_config.get("validation", {})
        
        self.log.info(f"🔄 BATCH SYNCHRONIZATION: Enabled")
        self.log.info(f"   target_batch_size: {target_batch_size}")
        self.log.info(f"   synchronize_all_batch_sizes: {synchronize_all}")
        
        original_values = {
            "max_products_per_cycle": max_products_per_cycle,
            "supplier_extraction_batch_size": supplier_extraction_batch_size,
            "linking_map_batch_size": self.system_config.get("system", {}).get("linking_map_batch_size", 3),
            "financial_report_batch_size": self.system_config.get("system", {}).get("financial_report_batch_size", 3)
        }
        
        # Check for mismatched sizes and warn if configured
        if validation_config.get("warn_on_mismatched_sizes", True):
            unique_sizes = set(original_values.values())
            if len(unique_sizes) > 1:
                self.log.warning(f"⚠️ BATCH SYNC WARNING: Mismatched batch sizes detected: {original_values}")
                self.log.warning(f"   Unique sizes found: {sorted(unique_sizes)}")
        
        if synchronize_all:
            # Synchronize all batch sizes to target
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            # Also update system config values in memory for consistency
            if "system" in self.system_config:
                self.system_config["system"]["max_products_per_cycle"] = target_batch_size
                self.system_config["system"]["supplier_extraction_batch_size"] = target_batch_size
                self.system_config["system"]["linking_map_batch_size"] = target_batch_size
                self.system_config["system"]["financial_report_batch_size"] = target_batch_size
            
            self.log.info(f"✅ BATCH SYNC: All batch sizes synchronized to {target_batch_size}")
            self.log.info(f"   Updated values: max_products_per_cycle={new_max_products_per_cycle}, supplier_extraction_batch_size={new_supplier_extraction_batch_size}")
            
        else:
            # Only synchronize the two main processing batch sizes
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            self.log.info(f"✅ BATCH SYNC: Main processing batch sizes synchronized to {target_batch_size}")
            self.log.info(f"   Updated values: max_products_per_cycle={new_max_products_per_cycle}, supplier_extraction_batch_size={new_supplier_extraction_batch_size}")
        
        return new_max_products_per_cycle, new_supplier_extraction_batch_size




    def _get_cached_products_path(self, category_url: str):
        """Helper to get the path for a category's product cache file."""
        category_filename = f"{self.supplier_name}_{category_url.split('/')[-1]}_products.json"
        cache_dir = os.path.join(self.output_dir, 'CACHE', 'supplier_cache')
        return os.path.join(cache_dir, category_filename)


    def _combine_data(self, supplier_data: Dict[str, Any], amazon_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Combine supplier and Amazon data and calculate financial metrics."""
        combined = {
            "supplier_product_info": supplier_data,
            "amazon_product_info": amazon_data,
            "analysis_timestamp": datetime.now().isoformat(),
            "session_id": session_id
        }
        # Financial calculation is now handled within the main run loop before this function is called
        # This function is primarily for combining data and adding match validation
        match_validation = self._validate_product_match(supplier_data, amazon_data)
        combined["match_validation"] = match_validation
        return combined

    def _overlap_score(self, title_a: str, title_b: str) -> float:
        """Calculate word overlap score between two titles"""
        a = set(re.sub(r'[^\w\s]', ' ', title_a.lower()).split())
        b = set(re.sub(r'[^\w\s]', ' ', title_b.lower()).split())
        return len(a & b) / max(1, len(a))
    
    def _sanitize_filename(self, title: str) -> str:
        """Sanitize product title for use in filename"""
        if not title:
            return "unknown_title"
        # Remove or replace problematic characters
        sanitized = re.sub(r'[^\w\s-]', '', title)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized[:50]  # Limit length to 50 chars

    def _validate_product_match(self, supplier_product: Dict[str, Any], amazon_product: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the match between supplier and Amazon products using configurable thresholds."""
        # CRITICAL FIX: Use configurable matching thresholds instead of hardcoded values
        matching_thresholds = self.system_config.get("performance", {}).get("matching_thresholds", {})
        
        # Get configurable thresholds with fallback to more conservative defaults
        title_similarity_threshold = matching_thresholds.get("title_similarity", 0.25)
        medium_title_similarity = matching_thresholds.get("medium_title_similarity", 0.5) 
        high_title_similarity = matching_thresholds.get("high_title_similarity", 0.75)
        
        title_overlap_score = self._overlap_score(supplier_product.get("title", ""), amazon_product.get("title", ""))

        match_quality = "low"
        confidence = 0.0
        
        # Use configurable thresholds - much more strict than previous hardcoded values
        if title_overlap_score >= high_title_similarity:
            match_quality = "high"
            confidence = 0.9
        elif title_overlap_score >= medium_title_similarity:
            match_quality = "medium"
            confidence = 0.6
        elif title_overlap_score >= title_similarity_threshold:
            match_quality = "low"
            confidence = 0.3
        else:
            match_quality = "very_low"
            confidence = 0.1

        self.log.debug(f"🔍 MATCH VALIDATION: '{supplier_product.get('title', 'Unknown')}' vs '{amazon_product.get('title', 'Unknown')}' = {title_overlap_score:.2f} ({match_quality}, {confidence:.1%})")
        
        return {"match_quality": match_quality, "confidence": confidence, "title_overlap_score": title_overlap_score}

    def _is_product_meeting_criteria(self, combined_data: Dict[str, Any]) -> bool:
        """Check if a product meets all defined business criteria."""
        # This function is now largely redundant as profitability checks are done in the main loop.
        # However, it can be used for other criteria like sales rank, reviews, etc.
        amazon_data = combined_data.get("amazon_product_info", {})
        financials = combined_data.get("financials", {})
        # Check profitability (already done, but for completeness)
        is_profitable = financials.get("ROI", 0) > MIN_ROI_PERCENT and financials.get("NetProfit", 0) > MIN_PROFIT_PER_UNIT
        # Check Amazon listing quality
        meets_rating = amazon_data.get("rating", 0) >= MIN_RATING
        meets_reviews = amazon_data.get("reviews", 0) >= MIN_REVIEWS
        meets_sales_rank = amazon_data.get("sales_rank", MAX_SALES_RANK + 1) <= MAX_SALES_RANK
        # Check for battery products (using the helper function)
        is_battery = is_battery_title(amazon_data.get("title", "")) or is_battery_title(combined_data["supplier_product_info"].get("title", ""))
        # Check for other non-FBA friendly keywords
        is_non_fba_friendly = any(k in amazon_data.get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS) or \
                              any(k in combined_data["supplier_product_info"].get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS)
        # All criteria must be met
        return is_profitable and meets_rating and meets_reviews and meets_sales_rank and not is_battery and not is_non_fba_friendly

    def _apply_batch_synchronization(self, max_products_per_cycle: int, 
                                   supplier_extraction_batch_size: int,
                                   batch_sync_config: Dict[str, Any]) -> Tuple[int, int]:
        """
        Apply batch synchronization to align all batch sizes consistently.
        Returns updated max_products_per_cycle and supplier_extraction_batch_size.
        """
        target_batch_size = batch_sync_config.get("target_batch_size", 3)
        synchronize_all = batch_sync_config.get("synchronize_all_batch_sizes", False)
        validation_config = batch_sync_config.get("validation", {})
        
        self.log.info(f"🔄 BATCH SYNCHRONIZATION: Enabled")
        self.log.info(f"   target_batch_size: {target_batch_size}")
        self.log.info(f"   synchronize_all_batch_sizes: {synchronize_all}")
        
        original_values = {
            "max_products_per_cycle": max_products_per_cycle,
            "supplier_extraction_batch_size": supplier_extraction_batch_size,
            "linking_map_batch_size": self.system_config.get("system", {}).get("linking_map_batch_size", 3),
            "financial_report_batch_size": self.system_config.get("system", {}).get("financial_report_batch_size", 3)
        }
        
        # Check for mismatched sizes and warn if configured
        if validation_config.get("warn_on_mismatched_sizes", True):
            unique_sizes = set(original_values.values())
            if len(unique_sizes) > 1:
                self.log.warning(f"⚠️ BATCH SYNC WARNING: Mismatched batch sizes detected: {original_values}")
                self.log.warning(f"   Unique sizes found: {sorted(unique_sizes)}")
        
        if synchronize_all:
            # Synchronize all batch sizes to target
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            # Also update system config values in memory for consistency
            if "system" in self.system_config:
                self.system_config["system"]["max_products_per_cycle"] = target_batch_size
                self.system_config["system"]["supplier_extraction_batch_size"] = target_batch_size
                self.system_config["system"]["linking_map_batch_size"] = target_batch_size
                self.system_config["system"]["financial_report_batch_size"] = target_batch_size
            
            self.log.info(f"✅ BATCH SYNC: All batch sizes synchronized to {target_batch_size}")
            self.log.info(f"   Updated values: max_products_per_cycle={new_max_products_per_cycle}, supplier_extraction_batch_size={new_supplier_extraction_batch_size}")
            
        else:
            # Only synchronize the two main processing batch sizes
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            self.log.info(f"✅ BATCH SYNC: Main processing batch sizes synchronized to {target_batch_size}")
            self.log.info(f"   Updated values: max_products_per_cycle={new_max_products_per_cycle}, supplier_extraction_batch_size={new_supplier_extraction_batch_size}")
        
        return new_max_products_per_cycle, new_supplier_extraction_batch_size




    def _get_cached_products_path(self, category_url: str):
        """Helper to get the path for a category's product cache file."""
        category_filename = f"{self.supplier_name}_{category_url.split('/')[-1]}_products.json"
        cache_dir = os.path.join(self.output_dir, 'CACHE', 'supplier_cache')
        return os.path.join(cache_dir, category_filename)


    def _combine_data(self, supplier_data: Dict[str, Any], amazon_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Combine supplier and Amazon data and calculate financial metrics."""
        combined = {
            "supplier_product_info": supplier_data,
            "amazon_product_info": amazon_data,
            "analysis_timestamp": datetime.now().isoformat(),
            "session_id": session_id
        }
        # Financial calculation is now handled within the main run loop before this function is called
        # This function is primarily for combining data and adding match validation
        match_validation = self._validate_product_match(supplier_data, amazon_data)
        combined["match_validation"] = match_validation
        return combined

    def _overlap_score(self, title_a: str, title_b: str) -> float:
        """Calculate word overlap score between two titles"""
        a = set(re.sub(r'[^\w\s]', ' ', title_a.lower()).split())
        b = set(re.sub(r'[^\w\s]', ' ', title_b.lower()).split())
        return len(a & b) / max(1, len(a))
    
    def _sanitize_filename(self, title: str) -> str:
        """Sanitize product title for use in filename"""
        if not title:
            return "unknown_title"
        # Remove or replace problematic characters
        sanitized = re.sub(r'[^\w\s-]', '', title)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized[:50]  # Limit length to 50 chars

    def _validate_product_match(self, supplier_product: Dict[str, Any], amazon_product: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the match between supplier and Amazon products using configurable thresholds."""
        # CRITICAL FIX: Use configurable matching thresholds instead of hardcoded values
        matching_thresholds = self.system_config.get("performance", {}).get("matching_thresholds", {})
        
        # Get configurable thresholds with fallback to more conservative defaults
        title_similarity_threshold = matching_thresholds.get("title_similarity", 0.25)
        medium_title_similarity = matching_thresholds.get("medium_title_similarity", 0.5) 
        high_title_similarity = matching_thresholds.get("high_title_similarity", 0.75)
        
        title_overlap_score = self._overlap_score(supplier_product.get("title", ""), amazon_product.get("title", ""))

        match_quality = "low"
        confidence = 0.0
        
        # Use configurable thresholds - much more strict than previous hardcoded values
        if title_overlap_score >= high_title_similarity:
            match_quality = "high"
            confidence = 0.9
        elif title_overlap_score >= medium_title_similarity:
            match_quality = "medium"
            confidence = 0.6
        elif title_overlap_score >= title_similarity_threshold:
            match_quality = "low"
            confidence = 0.3
        else:
            match_quality = "very_low"
            confidence = 0.1

        self.log.debug(f"🔍 MATCH VALIDATION: '{supplier_product.get('title', 'Unknown')}' vs '{amazon_product.get('title', 'Unknown')}' = {title_overlap_score:.2f} ({match_quality}, {confidence:.1%})")
        
        return {"match_quality": match_quality, "confidence": confidence, "title_overlap_score": title_overlap_score}

    def _is_product_meeting_criteria(self, combined_data: Dict[str, Any]) -> bool:
        """Check if a product meets all defined business criteria."""
        # This function is now largely redundant as profitability checks are done in the main loop.
        # However, it can be used for other criteria like sales rank, reviews, etc.
        amazon_data = combined_data.get("amazon_product_info", {})
        financials = combined_data.get("financials", {})
        # Check profitability (already done, but for completeness)
        is_profitable = financials.get("ROI", 0) > MIN_ROI_PERCENT and financials.get("NetProfit", 0) > MIN_PROFIT_PER_UNIT
        # Check Amazon listing quality
        meets_rating = amazon_data.get("rating", 0) >= MIN_RATING
        meets_reviews = amazon_data.get("reviews", 0) >= MIN_REVIEWS
        meets_sales_rank = amazon_data.get("sales_rank", MAX_SALES_RANK + 1) <= MAX_SALES_RANK
        # Check for battery products (using the helper function)
        is_battery = is_battery_title(amazon_data.get("title", "")) or is_battery_title(combined_data["supplier_product_info"].get("title", ""))
        # Check for other non-FBA friendly keywords
        is_non_fba_friendly = any(k in amazon_data.get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS) or \
                              any(k in combined_data["supplier_product_info"].get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS)
        # All criteria must be met
        return is_profitable and meets_rating and meets_reviews and meets_sales_rank and not is_battery and not is_non_fba_friendly

    def _apply_batch_synchronization(self, max_products_per_cycle: int, 
                                   supplier_extraction_batch_size: int,
                                   batch_sync_config: Dict[str, Any]) -> Tuple[int, int]:
        """
        Apply batch synchronization to align all batch sizes consistently.
        Returns updated max_products_per_cycle and supplier_extraction_batch_size.
        """
        target_batch_size = batch_sync_config.get("target_batch_size", 3)
        synchronize_all = batch_sync_config.get("synchronize_all_batch_sizes", False)
        validation_config = batch_sync_config.get("validation", {})
        
        self.log.info(f"🔄 BATCH SYNCHRONIZATION: Enabled")
        self.log.info(f"   target_batch_size: {target_batch_size}")
        self.log.info(f"   synchronize_all_batch_sizes: {synchronize_all}")
        
        original_values = {
            "max_products_per_cycle": max_products_per_cycle,
            "supplier_extraction_batch_size": supplier_extraction_batch_size,
            "linking_map_batch_size": self.system_config.get("system", {}).get("linking_map_batch_size", 3),
            "financial_report_batch_size": self.system_config.get("system", {}).get("financial_report_batch_size", 3)
        }
        
        # Check for mismatched sizes and warn if configured
        if validation_config.get("warn_on_mismatched_sizes", True):
            unique_sizes = set(original_values.values())
            if len(unique_sizes) > 1:
                self.log.warning(f"⚠️ BATCH SYNC WARNING: Mismatched batch sizes detected: {original_values}")
                self.log.warning(f"   Unique sizes found: {sorted(unique_sizes)}")
        
        if synchronize_all:
            # Synchronize all batch sizes to target
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            # Also update system config values in memory for consistency
            if "system" in self.system_config:
                self.system_config["system"]["max_products_per_cycle"] = target_batch_size
                self.system_config["system"]["supplier_extraction_batch_size"] = target_batch_size
                self.system_config["system"]["linking_map_batch_size"] = target_batch_size
                self.system_config["system"]["financial_report_batch_size"] = target_batch_size
            
            self.log.info(f"✅ BATCH SYNC: All batch sizes synchronized to {target_batch_size}")
            self.log.info(f"   Updated values: max_products_per_cycle={new_max_products_per_cycle}, supplier_extraction_batch_size={new_supplier_extraction_batch_size}")
            
        else:
            # Only synchronize the two main processing batch sizes
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            self.log.info(f"✅ BATCH SYNC: Main processing batch sizes synchronized to {target_batch_size}")
            self.log.info(f"   Updated values: max_products_per_cycle={new_max_products_per_cycle}, supplier_extraction_batch_size={new_supplier_extraction_batch_size}")
        
        return new_max_products_per_cycle, new_supplier_extraction_batch_size


    def _get_cached_products_path(self, category_url: str):
        """Helper to get the path for a category's product cache file."""
        category_filename = f"{self.supplier_name}_{category_url.split('/')[-1]}_products.json"
        cache_dir = os.path.join(self.output_dir, 'CACHE', 'supplier_cache')
        return os.path.join(cache_dir, category_filename)


    def _combine_data(self, supplier_data: Dict[str, Any], amazon_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Combine supplier and Amazon data and calculate financial metrics."""
        combined = {
            "supplier_product_info": supplier_data,
            "amazon_product_info": amazon_data,
            "analysis_timestamp": datetime.now().isoformat(),
            "session_id": session_id
        }
        # Financial calculation is now handled within the main run loop before this function is called
        # This function is primarily for combining data and adding match validation
        match_validation = self._validate_product_match(supplier_data, amazon_data)
        combined["match_validation"] = match_validation
        return combined

    def _overlap_score(self, title_a: str, title_b: str) -> float:
        """Calculate word overlap score between two titles"""
        a = set(re.sub(r'[^\w\s]', ' ', title_a.lower()).split())
        b = set(re.sub(r'[^\w\s]', ' ', title_b.lower()).split())
        return len(a & b) / max(1, len(a))
    
    def _sanitize_filename(self, title: str) -> str:
        """Sanitize product title for use in filename"""
        if not title:
            return "unknown_title"
        # Remove or replace problematic characters
        sanitized = re.sub(r'[^\w\s-]', '', title)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized[:50]  # Limit length to 50 chars

    def _validate_product_match(self, supplier_product: Dict[str, Any], amazon_product: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the match between supplier and Amazon products using configurable thresholds."""
        # CRITICAL FIX: Use configurable matching thresholds instead of hardcoded values
        matching_thresholds = self.system_config.get("performance", {}).get("matching_thresholds", {})
        
        # Get configurable thresholds with fallback to more conservative defaults
        title_similarity_threshold = matching_thresholds.get("title_similarity", 0.25)
        medium_title_similarity = matching_thresholds.get("medium_title_similarity", 0.5) 
        high_title_similarity = matching_thresholds.get("high_title_similarity", 0.75)
        
        title_overlap_score = self._overlap_score(supplier_product.get("title", ""), amazon_product.get("title", ""))

        match_quality = "low"
        confidence = 0.0
        
        # Use configurable thresholds - much more strict than previous hardcoded values
        if title_overlap_score >= high_title_similarity:
            match_quality = "high"
            confidence = 0.9
        elif title_overlap_score >= medium_title_similarity:
            match_quality = "medium"
            confidence = 0.6
        elif title_overlap_score >= title_similarity_threshold:
            match_quality = "low"
            confidence = 0.3
        else:
            match_quality = "very_low"
            confidence = 0.1

        self.log.debug(f"🔍 MATCH VALIDATION: '{supplier_product.get('title', 'Unknown')}' vs '{amazon_product.get('title', 'Unknown')}' = {title_overlap_score:.2f} ({match_quality}, {confidence:.1%})")
        
        return {"match_quality": match_quality, "confidence": confidence, "title_overlap_score": title_overlap_score}

    def _is_product_meeting_criteria(self, combined_data: Dict[str, Any]) -> bool:
        """Check if a product meets all defined business criteria."""
        # This function is now largely redundant as profitability checks are done in the main loop.
        # However, it can be used for other criteria like sales rank, reviews, etc.
        amazon_data = combined_data.get("amazon_product_info", {})
        financials = combined_data.get("financials", {})
        # Check profitability (already done, but for completeness)
        is_profitable = financials.get("ROI", 0) > MIN_ROI_PERCENT and financials.get("NetProfit", 0) > MIN_PROFIT_PER_UNIT
        # Check Amazon listing quality
        meets_rating = amazon_data.get("rating", 0) >= MIN_RATING
        meets_reviews = amazon_data.get("reviews", 0) >= MIN_REVIEWS
        meets_sales_rank = amazon_data.get("sales_rank", MAX_SALES_RANK + 1) <= MAX_SALES_RANK
        # Check for battery products (using the helper function)
        is_battery = is_battery_title(amazon_data.get("title", "")) or is_battery_title(combined_data["supplier_product_info"].get("title", ""))
        # Check for other non-FBA friendly keywords
        is_non_fba_friendly = any(k in amazon_data.get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS) or \
                              any(k in combined_data["supplier_product_info"].get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS)
        # All criteria must be met
        return is_profitable and meets_rating and meets_reviews and meets_sales_rank and not is_battery and not is_non_fba_friendly

    def _apply_batch_synchronization(self, max_products_per_cycle: int, 
                                   supplier_extraction_batch_size: int,
                                   batch_sync_config: Dict[str, Any]) -> Tuple[int, int]:
        """
        Apply batch synchronization to align all batch sizes consistently.
        Returns updated max_products_per_cycle and supplier_extraction_batch_size.
        """
        target_batch_size = batch_sync_config.get("target_batch_size", 3)
        synchronize_all = batch_sync_config.get("synchronize_all_batch_sizes", False)
        validation_config = batch_sync_config.get("validation", {})
        
        self.log.info(f"🔄 BATCH SYNCHRONIZATION: Enabled")
        self.log.info(f"   target_batch_size: {target_batch_size}")
        self.log.info(f"   synchronize_all_batch_sizes: {synchronize_all}")
        
        original_values = {
            "max_products_per_cycle": max_products_per_cycle,
            "supplier_extraction_batch_size": supplier_extraction_batch_size,
            "linking_map_batch_size": self.system_config.get("system", {}).get("linking_map_batch_size", 3),
            "financial_report_batch_size": self.system_config.get("system", {}).get("financial_report_batch_size", 3)
        }
        
        # Check for mismatched sizes and warn if configured
        if validation_config.get("warn_on_mismatched_sizes", True):
            unique_sizes = set(original_values.values())
            if len(unique_sizes) > 1:
                self.log.warning(f"⚠️ BATCH SYNC WARNING: Mismatched batch sizes detected: {original_values}")
                self.log.warning(f"   Unique sizes found: {sorted(unique_sizes)}")
        
        if synchronize_all:
            # Synchronize all batch sizes to target
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            # Also update system config values in memory for consistency
            if "system" in self.system_config:
                self.system_config["system"]["max_products_per_cycle"] = target_batch_size
                self.system_config["system"]["supplier_extraction_batch_size"] = target_batch_size
                self.system_config["system"]["linking_map_batch_size"] = target_batch_size
                self.system_config["system"]["financial_report_batch_size"] = target_batch_size
            
            self.log.info(f"✅ BATCH SYNC: All batch sizes synchronized to {target_batch_size}")
            self.log.info(f"   Updated values: max_products_per_cycle={new_max_products_per_cycle}, supplier_extraction_batch_size={new_supplier_extraction_batch_size}")
            
        else:
            # Only synchronize the two main processing batch sizes
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            self.log.info(f"✅ BATCH SYNC: Main processing batch sizes synchronized to {target_batch_size}")
            self.log.info(f"   Updated values: max_products_per_cycle={new_max_products_per_cycle}, supplier_extraction_batch_size={new_supplier_extraction_batch_size}")
        
        return new_max_products_per_cycle, new_supplier_extraction_batch_size



    def _get_cached_products_path(self, category_url: str):
        """Helper to get the path for a category's product cache file."""
        category_filename = f"{self.supplier_name}_{category_url.split('/')[-1]}_products.json"
        cache_dir = os.path.join(self.output_dir, 'CACHE', 'supplier_cache')
        return os.path.join(cache_dir, category_filename)



    def _combine_data(self, supplier_data: Dict[str, Any], amazon_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Combine supplier and Amazon data and calculate financial metrics."""
        combined = {
            "supplier_product_info": supplier_data,
            "amazon_product_info": amazon_data,
            "analysis_timestamp": datetime.now().isoformat(),
            "session_id": session_id
        }
        # Financial calculation is now handled within the main run loop before this function is called
        # This function is primarily for combining data and adding match validation
        match_validation = self._validate_product_match(supplier_data, amazon_data)
        combined["match_validation"] = match_validation
        return combined

    def _overlap_score(self, title_a: str, title_b: str) -> float:
        """Calculate word overlap score between two titles"""
        a = set(re.sub(r'[^\w\s]', ' ', title_a.lower()).split())
        b = set(re.sub(r'[^\w\s]', ' ', title_b.lower()).split())
        return len(a & b) / max(1, len(a))
    
    def _sanitize_filename(self, title: str) -> str:
        """Sanitize product title for use in filename"""
        if not title:
            return "unknown_title"
        # Remove or replace problematic characters
        sanitized = re.sub(r'[^\w\s-]', '', title)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized[:50]  # Limit length to 50 chars

    def _validate_product_match(self, supplier_product: Dict[str, Any], amazon_product: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the match between supplier and Amazon products using configurable thresholds."""
        # CRITICAL FIX: Use configurable matching thresholds instead of hardcoded values
        matching_thresholds = self.system_config.get("performance", {}).get("matching_thresholds", {})
        
        # Get configurable thresholds with fallback to more conservative defaults
        title_similarity_threshold = matching_thresholds.get("title_similarity", 0.25)
        medium_title_similarity = matching_thresholds.get("medium_title_similarity", 0.5) 
        high_title_similarity = matching_thresholds.get("high_title_similarity", 0.75)
        
        title_overlap_score = self._overlap_score(supplier_product.get("title", ""), amazon_product.get("title", ""))

        match_quality = "low"
        confidence = 0.0
        
        # Use configurable thresholds - much more strict than previous hardcoded values
        if title_overlap_score >= high_title_similarity:
            match_quality = "high"
            confidence = 0.9
        elif title_overlap_score >= medium_title_similarity:
            match_quality = "medium"
            confidence = 0.6
        elif title_overlap_score >= title_similarity_threshold:
            match_quality = "low"
            confidence = 0.3
        else:
            match_quality = "very_low"
            confidence = 0.1

        self.log.debug(f"🔍 MATCH VALIDATION: '{supplier_product.get('title', 'Unknown')}' vs '{amazon_product.get('title', 'Unknown')}' = {title_overlap_score:.2f} ({match_quality}, {confidence:.1%})")
        
        return {"match_quality": match_quality, "confidence": confidence, "title_overlap_score": title_overlap_score}

    def _is_product_meeting_criteria(self, combined_data: Dict[str, Any]) -> bool:
        """Check if a product meets all defined business criteria."""
        # This function is now largely redundant as profitability checks are done in the main loop.
        # However, it can be used for other criteria like sales rank, reviews, etc.
        amazon_data = combined_data.get("amazon_product_info", {})
        financials = combined_data.get("financials", {})
        # Check profitability (already done, but for completeness)
        is_profitable = financials.get("ROI", 0) > MIN_ROI_PERCENT and financials.get("NetProfit", 0) > MIN_PROFIT_PER_UNIT
        # Check Amazon listing quality
        meets_rating = amazon_data.get("rating", 0) >= MIN_RATING
        meets_reviews = amazon_data.get("reviews", 0) >= MIN_REVIEWS
        meets_sales_rank = amazon_data.get("sales_rank", MAX_SALES_RANK + 1) <= MAX_SALES_RANK
        # Check for battery products (using the helper function)
        is_battery = is_battery_title(amazon_data.get("title", "")) or is_battery_title(combined_data["supplier_product_info"].get("title", ""))
        # Check for other non-FBA friendly keywords
        is_non_fba_friendly = any(k in amazon_data.get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS) or \
                              any(k in combined_data["supplier_product_info"].get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS)
        # All criteria must be met
        return is_profitable and meets_rating and meets_reviews and meets_sales_rank and not is_battery and not is_non_fba_friendly

    def _apply_batch_synchronization(self, max_products_per_cycle: int, 
                                   supplier_extraction_batch_size: int,
                                   batch_sync_config: Dict[str, Any]) -> Tuple[int, int]:
        """
        Apply batch synchronization to align all batch sizes consistently.
        Returns updated max_products_per_cycle and supplier_extraction_batch_size.
        """
        target_batch_size = batch_sync_config.get("target_batch_size", 3)
        synchronize_all = batch_sync_config.get("synchronize_all_batch_sizes", False)
        validation_config = batch_sync_config.get("validation", {})
        
        self.log.info(f"🔄 BATCH SYNCHRONIZATION: Enabled")
        self.log.info(f"   target_batch_size: {target_batch_size}")
        self.log.info(f"   synchronize_all_batch_sizes: {synchronize_all}")
        
        original_values = {
            "max_products_per_cycle": max_products_per_cycle,
            "supplier_extraction_batch_size": supplier_extraction_batch_size,
            "linking_map_batch_size": self.system_config.get("system", {}).get("linking_map_batch_size", 3),
            "financial_report_batch_size": self.system_config.get("system", {}).get("financial_report_batch_size", 3)
        }
        
        # Check for mismatched sizes and warn if configured
        if validation_config.get("warn_on_mismatched_sizes", True):
            unique_sizes = set(original_values.values())
            if len(unique_sizes) > 1:
                self.log.warning(f"⚠️ BATCH SYNC WARNING: Mismatched batch sizes detected: {original_values}")
                self.log.warning(f"   Unique sizes found: {sorted(unique_sizes)}")
        
        if synchronize_all:
            # Synchronize all batch sizes to target
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            # Also update system config values in memory for consistency
            if "system" in self.system_config:
                self.system_config["system"]["max_products_per_cycle"] = target_batch_size
                self.system_config["system"]["supplier_extraction_batch_size"] = target_batch_size
                self.system_config["system"]["linking_map_batch_size"] = target_batch_size
                self.system_config["system"]["financial_report_batch_size"] = target_batch_size
            

        
        return new_max_products_per_cycle, new_supplier_extraction_batch_size



    def _get_cached_products_path(self, category_url: str):
        """Helper to get the path for a category's product cache file."""
        category_filename = f"{self.supplier_name}_{category_url.split('/')[-1]}_products.json"
        cache_dir = os.path.join(self.output_dir, 'CACHE', 'supplier_cache')
        return os.path.join(cache_dir, category_filename)


    def _combine_data(self, supplier_data: Dict[str, Any], amazon_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Combine supplier and Amazon data and calculate financial metrics."""
        combined = {
            "supplier_product_info": supplier_data,
            "amazon_product_info": amazon_data,
            "analysis_timestamp": datetime.now().isoformat(),
            "session_id": session_id
        }
        # Financial calculation is now handled within the main run loop before this function is called
        # This function is primarily for combining data and adding match validation
        match_validation = self._validate_product_match(supplier_data, amazon_data)
        combined["match_validation"] = match_validation
        return combined

    def _overlap_score(self, title_a: str, title_b: str) -> float:
        """Calculate word overlap score between two titles"""
        a = set(re.sub(r'[^\w\s]', ' ', title_a.lower()).split())
        b = set(re.sub(r'[^\w\s]', ' ', title_b.lower()).split())
        return len(a & b) / max(1, len(a))
    
    def _sanitize_filename(self, title: str) -> str:
        """Sanitize product title for use in filename"""
        if not title:
            return "unknown_title"
        # Remove or replace problematic characters
        sanitized = re.sub(r'[^\w\s-]', '', title)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized[:50]  # Limit length to 50 chars

    def _validate_product_match(self, supplier_product: Dict[str, Any], amazon_product: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the match between supplier and Amazon products using configurable thresholds."""
        # CRITICAL FIX: Use configurable matching thresholds instead of hardcoded values
        matching_thresholds = self.system_config.get("performance", {}).get("matching_thresholds", {})
        
        # Get configurable thresholds with fallback to more conservative defaults
        title_similarity_threshold = matching_thresholds.get("title_similarity", 0.25)
        medium_title_similarity = matching_thresholds.get("medium_title_similarity", 0.5) 
        high_title_similarity = matching_thresholds.get("high_title_similarity", 0.75)
        
        title_overlap_score = self._overlap_score(supplier_product.get("title", ""), amazon_product.get("title", ""))

        match_quality = "low"
        confidence = 0.0
        
        # Use configurable thresholds - much more strict than previous hardcoded values
        if title_overlap_score >= high_title_similarity:
            match_quality = "high"
            confidence = 0.9
        elif title_overlap_score >= medium_title_similarity:
            match_quality = "medium"
            confidence = 0.6
        elif title_overlap_score >= title_similarity_threshold:
            match_quality = "low"
            confidence = 0.3
        else:
            match_quality = "very_low"
            confidence = 0.1

        self.log.debug(f"🔍 MATCH VALIDATION: '{supplier_product.get('title', 'Unknown')}' vs '{amazon_product.get('title', 'Unknown')}' = {title_overlap_score:.2f} ({match_quality}, {confidence:.1%})")
        
        return {"match_quality": match_quality, "confidence": confidence, "title_overlap_score": title_overlap_score}

    def _is_product_meeting_criteria(self, combined_data: Dict[str, Any]) -> bool:
        """Check if a product meets all defined business criteria."""
        # This function is now largely redundant as profitability checks are done in the main loop.
        # However, it can be used for other criteria like sales rank, reviews, etc.
        amazon_data = combined_data.get("amazon_product_info", {})
        financials = combined_data.get("financials", {})
        # Check profitability (already done, but for completeness)
        is_profitable = financials.get("ROI", 0) > MIN_ROI_PERCENT and financials.get("NetProfit", 0) > MIN_PROFIT_PER_UNIT
        # Check Amazon listing quality
        meets_rating = amazon_data.get("rating", 0) >= MIN_RATING
        meets_reviews = amazon_data.get("reviews", 0) >= MIN_REVIEWS
        meets_sales_rank = amazon_data.get("sales_rank", MAX_SALES_RANK + 1) <= MAX_SALES_RANK
        # Check for battery products (using the helper function)
        is_battery = is_battery_title(amazon_data.get("title", "")) or is_battery_title(combined_data["supplier_product_info"].get("title", ""))
        # Check for other non-FBA friendly keywords
        is_non_fba_friendly = any(k in amazon_data.get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS) or \
                              any(k in combined_data["supplier_product_info"].get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS)
        # All criteria must be met
        return is_profitable and meets_rating and meets_reviews and meets_sales_rank and not is_battery and not is_non_fba_friendly

    def _apply_batch_synchronization(self, max_products_per_cycle: int, 
                                   supplier_extraction_batch_size: int,
                                   batch_sync_config: Dict[str, Any]) -> Tuple[int, int]:
        """
        Apply batch synchronization to align all batch sizes consistently.
        Returns updated max_products_per_cycle and supplier_extraction_batch_size.
        """
        target_batch_size = batch_sync_config.get("target_batch_size", 3)
        synchronize_all = batch_sync_config.get("synchronize_all_batch_sizes", False)
        validation_config = batch_sync_config.get("validation", {})
        
        self.log.info(f"🔄 BATCH SYNCHRONIZATION: Enabled")
        self.log.info(f"   target_batch_size: {target_batch_size}")
        self.log.info(f"   synchronize_all_batch_sizes: {synchronize_all}")
        
        original_values = {
            "max_products_per_cycle": max_products_per_cycle,
            "supplier_extraction_batch_size": supplier_extraction_batch_size,
            "linking_map_batch_size": self.system_config.get("system", {}).get("linking_map_batch_size", 3),
            "financial_report_batch_size": self.system_config.get("system", {}).get("financial_report_batch_size", 3)
        }
        
        # Check for mismatched sizes and warn if configured
        if validation_config.get("warn_on_mismatched_sizes", True):
            unique_sizes = set(original_values.values())
            if len(unique_sizes) > 1:
                self.log.warning(f"⚠️ BATCH SYNC WARNING: Mismatched batch sizes detected: {original_values}")
                self.log.warning(f"   Unique sizes found: {sorted(unique_sizes)}")
        
        if synchronize_all:
            # Synchronize all batch sizes to target
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            # Also update system config values in memory for consistency
            if "system" in self.system_config:
                self.system_config["system"]["max_products_per_cycle"] = target_batch_size
                self.system_config["system"]["supplier_extraction_batch_size"] = target_batch_size
                self.system_config["system"]["linking_map_batch_size"] = target_batch_size
                self.system_config["system"]["financial_report_batch_size"] = target_batch_size
            
            self.log.info(f"✅ BATCH SYNC: All batch sizes synchronized to {target_batch_size}")
            self.log.info(f"   Updated values: max_products_per_cycle={new_max_products_per_cycle}, supplier_extraction_batch_size={new_supplier_extraction_batch_size}")
            
        else:
            # Only synchronize the two main processing batch sizes
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            self.log.info(f"✅ BATCH SYNC: Main processing batch sizes synchronized to {target_batch_size}")
            self.log.info(f"   Updated values: max_products_per_cycle={new_max_products_per_cycle}, supplier_extraction_batch_size={new_supplier_extraction_batch_size}")
        
        return new_max_products_per_cycle, new_supplier_extraction_batch_size




    def _get_cached_products_path(self, category_url: str):
        """Helper to get the path for a category's product cache file."""
        category_filename = f"{self.supplier_name}_{category_url.split('/')[-1]}_products.json"
        cache_dir = os.path.join(self.output_dir, 'CACHE', 'supplier_cache')
        return os.path.join(cache_dir, category_filename)


    def _combine_data(self, supplier_data: Dict[str, Any], amazon_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Combine supplier and Amazon data and calculate financial metrics."""
        combined = {
            "supplier_product_info": supplier_data,
            "amazon_product_info": amazon_data,
            "analysis_timestamp": datetime.now().isoformat(),
            "session_id": session_id
        }
        # Financial calculation is now handled within the main run loop before this function is called
        # This function is primarily for combining data and adding match validation
        match_validation = self._validate_product_match(supplier_data, amazon_data)
        combined["match_validation"] = match_validation
        return combined

    def _overlap_score(self, title_a: str, title_b: str) -> float:
        """Calculate word overlap score between two titles"""
        a = set(re.sub(r'[^\w\s]', ' ', title_a.lower()).split())
        b = set(re.sub(r'[^\w\s]', ' ', title_b.lower()).split())
        return len(a & b) / max(1, len(a))
    
    def _sanitize_filename(self, title: str) -> str:
        """Sanitize product title for use in filename"""
        if not title:
            return "unknown_title"
        # Remove or replace problematic characters
        sanitized = re.sub(r'[^\w\s-]', '', title)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized[:50]  # Limit length to 50 chars

    def _validate_product_match(self, supplier_product: Dict[str, Any], amazon_product: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the match between supplier and Amazon products using configurable thresholds."""
        # CRITICAL FIX: Use configurable matching thresholds instead of hardcoded values
        matching_thresholds = self.system_config.get("performance", {}).get("matching_thresholds", {})
        
        # Get configurable thresholds with fallback to more conservative defaults
        title_similarity_threshold = matching_thresholds.get("title_similarity", 0.25)
        medium_title_similarity = matching_thresholds.get("medium_title_similarity", 0.5) 
        high_title_similarity = matching_thresholds.get("high_title_similarity", 0.75)
        
        title_overlap_score = self._overlap_score(supplier_product.get("title", ""), amazon_product.get("title", ""))

        match_quality = "low"
        confidence = 0.0
        
        # Use configurable thresholds - much more strict than previous hardcoded values
        if title_overlap_score >= high_title_similarity:
            match_quality = "high"
            confidence = 0.9
        elif title_overlap_score >= medium_title_similarity:
            match_quality = "medium"
            confidence = 0.6
        elif title_overlap_score >= title_similarity_threshold:
            match_quality = "low"
            confidence = 0.3
        else:
            match_quality = "very_low"
            confidence = 0.1

        self.log.debug(f"🔍 MATCH VALIDATION: '{supplier_product.get('title', 'Unknown')}' vs '{amazon_product.get('title', 'Unknown')}' = {title_overlap_score:.2f} ({match_quality}, {confidence:.1%})")
        
        return {"match_quality": match_quality, "confidence": confidence, "title_overlap_score": title_overlap_score}

    def _is_product_meeting_criteria(self, combined_data: Dict[str, Any]) -> bool:
        """Check if a product meets all defined business criteria."""
        # This function is now largely redundant as profitability checks are done in the main loop.
        # However, it can be used for other criteria like sales rank, reviews, etc.
        amazon_data = combined_data.get("amazon_product_info", {})
        financials = combined_data.get("financials", {})
        # Check profitability (already done, but for completeness)
        is_profitable = financials.get("ROI", 0) > MIN_ROI_PERCENT and financials.get("NetProfit", 0) > MIN_PROFIT_PER_UNIT
        # Check Amazon listing quality
        meets_rating = amazon_data.get("rating", 0) >= MIN_RATING
        meets_reviews = amazon_data.get("reviews", 0) >= MIN_REVIEWS
        meets_sales_rank = amazon_data.get("sales_rank", MAX_SALES_RANK + 1) <= MAX_SALES_RANK
        # Check for battery products (using the helper function)
        is_battery = is_battery_title(amazon_data.get("title", "")) or is_battery_title(combined_data["supplier_product_info"].get("title", ""))
        # Check for other non-FBA friendly keywords
        is_non_fba_friendly = any(k in amazon_data.get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS) or \
                              any(k in combined_data["supplier_product_info"].get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS)
        # All criteria must be met
        return is_profitable and meets_rating and meets_reviews and meets_sales_rank and not is_battery and not is_non_fba_friendly

    def _apply_batch_synchronization(self, max_products_per_cycle: int, 
                                   supplier_extraction_batch_size: int,
                                   batch_sync_config: Dict[str, Any]) -> Tuple[int, int]:
        """
        Apply batch synchronization to align all batch sizes consistently.
        Returns updated max_products_per_cycle and supplier_extraction_batch_size.
        """
        target_batch_size = batch_sync_config.get("target_batch_size", 3)
        synchronize_all = batch_sync_config.get("synchronize_all_batch_sizes", False)
        validation_config = batch_sync_config.get("validation", {})

        
        self.log.info(f"🔄 BATCH SYNCHRONIZATION: Enabled")
        self.log.info(f"   target_batch_size: {target_batch_size}")
        self.log.info(f"   synchronize_all_batch_sizes: {synchronize_all}")
        
        original_values = {
            "max_products_per_cycle": max_products_per_cycle,
            "supplier_extraction_batch_size": supplier_extraction_batch_size,
            "linking_map_batch_size": self.system_config.get("system", {}).get("linking_map_batch_size", 3),
            "financial_report_batch_size": self.system_config.get("system", {}).get("financial_report_batch_size", 3)
        }
        
        # Check for mismatched sizes and warn if configured
        if validation_config.get("warn_on_mismatched_sizes", True):
            unique_sizes = set(original_values.values())
            if len(unique_sizes) > 1:
                self.log.warning(f"⚠️ BATCH SYNC WARNING: Mismatched batch sizes detected: {original_values}")
                self.log.warning(f"   Unique sizes found: {sorted(unique_sizes)}")
        
        if synchronize_all:
            # Synchronize all batch sizes to target
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            # Also update system config values in memory for consistency
            if "system" in self.system_config:
                self.system_config["system"]["max_products_per_cycle"] = target_batch_size
                self.system_config["system"]["supplier_extraction_batch_size"] = target_batch_size
                self.system_config["system"]["linking_map_batch_size"] = target_batch_size
                self.system_config["system"]["financial_report_batch_size"] = target_batch_size
            
            self.log.info(f"✅ BATCH SYNC: All batch sizes synchronized to {target_batch_size}")
            self.log.info(f"   Updated values: max_products_per_cycle={new_max_products_per_cycle}, supplier_extraction_batch_size={new_supplier_extraction_batch_size}")
            
        else:
            # Only synchronize the two main processing batch sizes
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            self.log.info(f"✅ BATCH SYNC: Main processing batch sizes synchronized to {target_batch_size}")
            self.log.info(f"   Updated values: max_products_per_cycle={new_max_products_per_cycle}, supplier_extraction_batch_size={new_supplier_extraction_batch_size}")
        
        return new_max_products_per_cycle, new_supplier_extraction_batch_size



    def _get_cached_products_path(self, category_url: str):
        """Helper to get the path for a category's product cache file."""
        category_filename = f"{self.supplier_name}_{category_url.split('/')[-1]}_products.json"
        cache_dir = os.path.join(self.output_dir, 'CACHE', 'supplier_cache')
        return os.path.join(cache_dir, category_filename)



    def _combine_data(self, supplier_data: Dict[str, Any], amazon_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Combine supplier and Amazon data and calculate financial metrics."""
        combined = {
            "supplier_product_info": supplier_data,
            "amazon_product_info": amazon_data,
            "analysis_timestamp": datetime.now().isoformat(),
            "session_id": session_id
        }
        # Financial calculation is now handled within the main run loop before this function is called
        # This function is primarily for combining data and adding match validation
        match_validation = self._validate_product_match(supplier_data, amazon_data)
        combined["match_validation"] = match_validation
        return combined

    def _overlap_score(self, title_a: str, title_b: str) -> float:
        """Calculate word overlap score between two titles"""
        a = set(re.sub(r'[^\w\s]', ' ', title_a.lower()).split())
        b = set(re.sub(r'[^\w\s]', ' ', title_b.lower()).split())
        return len(a & b) / max(1, len(a))
    
    def _sanitize_filename(self, title: str) -> str:
        """Sanitize product title for use in filename"""
        if not title:
            return "unknown_title"
        # Remove or replace problematic characters
        sanitized = re.sub(r'[^\w\s-]', '', title)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized[:50]  # Limit length to 50 chars

    def _validate_product_match(self, supplier_product: Dict[str, Any], amazon_product: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the match between supplier and Amazon products using configurable thresholds."""
        # CRITICAL FIX: Use configurable matching thresholds instead of hardcoded values
        matching_thresholds = self.system_config.get("performance", {}).get("matching_thresholds", {})
        
        # Get configurable thresholds with fallback to more conservative defaults
        title_similarity_threshold = matching_thresholds.get("title_similarity", 0.25)
        medium_title_similarity = matching_thresholds.get("medium_title_similarity", 0.5) 
        high_title_similarity = matching_thresholds.get("high_title_similarity", 0.75)
        
        title_overlap_score = self._overlap_score(supplier_product.get("title", ""), amazon_product.get("title", ""))

        match_quality = "low"
        confidence = 0.0
        
        # Use configurable thresholds - much more strict than previous hardcoded values
        if title_overlap_score >= high_title_similarity:
            match_quality = "high"
            confidence = 0.9
        elif title_overlap_score >= medium_title_similarity:
            match_quality = "medium"
            confidence = 0.6
        elif title_overlap_score >= title_similarity_threshold:
            match_quality = "low"
            confidence = 0.3
        else:
            match_quality = "very_low"
            confidence = 0.1

        self.log.debug(f"🔍 MATCH VALIDATION: '{supplier_product.get('title', 'Unknown')}' vs '{amazon_product.get('title', 'Unknown')}' = {title_overlap_score:.2f} ({match_quality}, {confidence:.1%})")
        
        return {"match_quality": match_quality, "confidence": confidence, "title_overlap_score": title_overlap_score}

    def _is_product_meeting_criteria(self, combined_data: Dict[str, Any]) -> bool:
        """Check if a product meets all defined business criteria."""
        # This function is now largely redundant as profitability checks are done in the main loop.
        # However, it can be used for other criteria like sales rank, reviews, etc.
        amazon_data = combined_data.get("amazon_product_info", {})
        financials = combined_data.get("financials", {})
        # Check profitability (already done, but for completeness)
        is_profitable = financials.get("ROI", 0) > MIN_ROI_PERCENT and financials.get("NetProfit", 0) > MIN_PROFIT_PER_UNIT
        # Check Amazon listing quality
        meets_rating = amazon_data.get("rating", 0) >= MIN_RATING
        meets_reviews = amazon_data.get("reviews", 0) >= MIN_REVIEWS
        meets_sales_rank = amazon_data.get("sales_rank", MAX_SALES_RANK + 1) <= MAX_SALES_RANK
        # Check for battery products (using the helper function)
        is_battery = is_battery_title(amazon_data.get("title", "")) or is_battery_title(combined_data["supplier_product_info"].get("title", ""))
        # Check for other non-FBA friendly keywords
        is_non_fba_friendly = any(k in amazon_data.get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS) or \
                              any(k in combined_data["supplier_product_info"].get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS)
        # All criteria must be met
        return is_profitable and meets_rating and meets_reviews and meets_sales_rank and not is_battery and not is_non_fba_friendly

    def _apply_batch_synchronization(self, max_products_per_cycle: int, 
                                   supplier_extraction_batch_size: int,
                                   batch_sync_config: Dict[str, Any]) -> Tuple[int, int]:
        """
        Apply batch synchronization to align all batch sizes consistently.
        Returns updated max_products_per_cycle and supplier_extraction_batch_size.
        """
        target_batch_size = batch_sync_config.get("target_batch_size", 3)
        synchronize_all = batch_sync_config.get("synchronize_all_batch_sizes", False)
        validation_config = batch_sync_config.get("validation", {})
        
        self.log.info(f"🔄 BATCH SYNCHRONIZATION: Enabled")
        self.log.info(f"   target_batch_size: {target_batch_size}")
        self.log.info(f"   synchronize_all_batch_sizes: {synchronize_all}")
        
        original_values = {
            "max_products_per_cycle": max_products_per_cycle,
            "supplier_extraction_batch_size": supplier_extraction_batch_size,
            "linking_map_batch_size": self.system_config.get("system", {}).get("linking_map_batch_size", 3),
            "financial_report_batch_size": self.system_config.get("system", {}).get("financial_report_batch_size", 3)
        }
        
        # Check for mismatched sizes and warn if configured
        if validation_config.get("warn_on_mismatched_sizes", True):
            unique_sizes = set(original_values.values())
            if len(unique_sizes) > 1:
                self.log.warning(f"⚠️ BATCH SYNC WARNING: Mismatched batch sizes detected: {original_values}")
                self.log.warning(f"   Unique sizes found: {sorted(unique_sizes)}")
        
        if synchronize_all:
            # Synchronize all batch sizes to target
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            # Also update system config values in memory for consistency
            if "system" in self.system_config:
                self.system_config["system"]["max_products_per_cycle"] = target_batch_size
                self.system_config["system"]["supplier_extraction_batch_size"] = target_batch_size
                self.system_config["system"]["linking_map_batch_size"] = target_batch_size
                self.system_config["system"]["financial_report_batch_size"] = target_batch_size
            
            self.log.info(f"✅ BATCH SYNC: All batch sizes synchronized to {target_batch_size}")
            self.log.info(f"   Updated values: max_products_per_cycle={new_max_products_per_cycle}, supplier_extraction_batch_size={new_supplier_extraction_batch_size}")
            
        else:
            # Only synchronize the two main processing batch sizes
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            self.log.info(f"✅ BATCH SYNC: Main processing batch sizes synchronized to {target_batch_size}")
            self.log.info(f"   Updated values: max_products_per_cycle={new_max_products_per_cycle}, supplier_extraction_batch_size={new_supplier_extraction_batch_size}")
        
        return new_max_products_per_cycle, new_supplier_extraction_batch_size



    def _get_cached_products_path(self, category_url: str):
        """Helper to get the path for a category's product cache file."""
        category_filename = f"{self.supplier_name}_{category_url.split('/')[-1]}_products.json"
        cache_dir = os.path.join(self.output_dir, 'CACHE', 'supplier_cache')
        return os.path.join(cache_dir, category_filename)

    def _save_final_report(self, profitable_products: list):
        """Save the final report of profitable products to a JSON file."""
        if not profitable_products:
            self.log.info("No profitable products found in this run.")
            return
        from utils.path_manager import path_manager
        output_filename = f"fba_profitable_finds_{self.supplier_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_path = path_manager.get_output_path("FBA_ANALYSIS", "profitable_reports", output_filename)
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(profitable_products, f, indent=2, ensure_ascii=False)
            self.log.info(f"Found {len(profitable_products)} profitable products. Results saved to {output_path}")
        except Exception as e:
            self.log.error(f"Error saving final report: {e}")

    def _combine_data(self, supplier_data: Dict[str, Any], amazon_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Combine supplier and Amazon data and calculate financial metrics."""
        combined = {
            "supplier_product_info": supplier_data,
            "amazon_product_info": amazon_data,
            "analysis_timestamp": datetime.now().isoformat(),
            "session_id": session_id
        }
        # Financial calculation is now handled within the main run loop before this function is called
        # This function is primarily for combining data and adding match validation
        match_validation = self._validate_product_match(supplier_data, amazon_data)
        combined["match_validation"] = match_validation
        return combined

    def _overlap_score(self, title_a: str, title_b: str) -> float:
        """Calculate word overlap score between two titles"""
        a = set(re.sub(r'[^\w\s]', ' ', title_a.lower()).split())
        b = set(re.sub(r'[^\w\s]', ' ', title_b.lower()).split())
        return len(a & b) / max(1, len(a))
    
    def _sanitize_filename(self, title: str) -> str:
        """Sanitize product title for use in filename"""
        if not title:
            return "unknown_title"
        # Remove or replace problematic characters
        sanitized = re.sub(r'[^\w\s-]', '', title)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized[:50]  # Limit length to 50 chars

    def _validate_product_match(self, supplier_product: Dict[str, Any], amazon_product: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the match between supplier and Amazon products using configurable thresholds."""
        # CRITICAL FIX: Use configurable matching thresholds instead of hardcoded values
        matching_thresholds = self.system_config.get("performance", {}).get("matching_thresholds", {})
        
        # Get configurable thresholds with fallback to more conservative defaults
        title_similarity_threshold = matching_thresholds.get("title_similarity", 0.25)
        medium_title_similarity = matching_thresholds.get("medium_title_similarity", 0.5) 
        high_title_similarity = matching_thresholds.get("high_title_similarity", 0.75)
        
        title_overlap_score = self._overlap_score(supplier_product.get("title", ""), amazon_product.get("title", ""))

        match_quality = "low"
        confidence = 0.0
        
        # Use configurable thresholds - much more strict than previous hardcoded values
        if title_overlap_score >= high_title_similarity:
            match_quality = "high"
            confidence = 0.9
        elif title_overlap_score >= medium_title_similarity:
            match_quality = "medium"
            confidence = 0.6
        elif title_overlap_score >= title_similarity_threshold:
            match_quality = "low"
            confidence = 0.3
        else:
            match_quality = "very_low"
            confidence = 0.1

        self.log.debug(f"🔍 MATCH VALIDATION: '{supplier_product.get('title', 'Unknown')}' vs '{amazon_product.get('title', 'Unknown')}' = {title_overlap_score:.2f} ({match_quality}, {confidence:.1%})")
        
        return {"match_quality": match_quality, "confidence": confidence, "title_overlap_score": title_overlap_score}

    def _is_product_meeting_criteria(self, combined_data: Dict[str, Any]) -> bool:
        """Check if a product meets all defined business criteria."""
        # This function is now largely redundant as profitability checks are done in the main loop.
        # However, it can be used for other criteria like sales rank, reviews, etc.
        amazon_data = combined_data.get("amazon_product_info", {})
        financials = combined_data.get("financials", {})
        # Check profitability (already done, but for completeness)
        is_profitable = financials.get("ROI", 0) > MIN_ROI_PERCENT and financials.get("NetProfit", 0) > MIN_PROFIT_PER_UNIT
        # Check Amazon listing quality
        meets_rating = amazon_data.get("rating", 0) >= MIN_RATING
        meets_reviews = amazon_data.get("reviews", 0) >= MIN_REVIEWS
        meets_sales_rank = amazon_data.get("sales_rank", MAX_SALES_RANK + 1) <= MAX_SALES_RANK
        # Check for battery products (using the helper function)
        is_battery = is_battery_title(amazon_data.get("title", "")) or is_battery_title(combined_data["supplier_product_info"].get("title", ""))
        # Check for other non-FBA friendly keywords
        is_non_fba_friendly = any(k in amazon_data.get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS) or \
                              any(k in combined_data["supplier_product_info"].get("title", "").lower() for k in NON_FBA_FRIENDLY_KEYWORDS)
        # All criteria must be met
        return is_profitable and meets_rating and meets_reviews and meets_sales_rank and not is_battery and not is_non_fba_friendly

    def _apply_batch_synchronization(self, max_products_per_cycle: int, 
                                   supplier_extraction_batch_size: int,
                                   batch_sync_config: Dict[str, Any]) -> Tuple[int, int]:
        """
        Apply batch synchronization to align all batch sizes consistently.
        Returns updated max_products_per_cycle and supplier_extraction_batch_size.
        """
        target_batch_size = batch_sync_config.get("target_batch_size", 3)
        synchronize_all = batch_sync_config.get("synchronize_all_batch_sizes", False)
        validation_config = batch_sync_config.get("validation", {})
        
        self.log.info(f"🔄 BATCH SYNCHRONIZATION: Enabled")
        self.log.info(f"   target_batch_size: {target_batch_size}")
        self.log.info(f"   synchronize_all_batch_sizes: {synchronize_all}")
        
        original_values = {
            "max_products_per_cycle": max_products_per_cycle,
            "supplier_extraction_batch_size": supplier_extraction_batch_size,
            "linking_map_batch_size": self.system_config.get("system", {}).get("linking_map_batch_size", 3),
            "financial_report_batch_size": self.system_config.get("system", {}).get("financial_report_batch_size", 3)
        }
        
        # Check for mismatched sizes and warn if configured
        if validation_config.get("warn_on_mismatched_sizes", True):
            unique_sizes = set(original_values.values())
            if len(unique_sizes) > 1:
                self.log.warning(f"⚠️ BATCH SYNC WARNING: Mismatched batch sizes detected: {original_values}")
                self.log.warning(f"   Unique sizes found: {sorted(unique_sizes)}")
        
        if synchronize_all:
            # Synchronize all batch sizes to target
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            # Also update system config values in memory for consistency
            if "system" in self.system_config:
                self.system_config["system"]["max_products_per_cycle"] = target_batch_size
                self.system_config["system"]["supplier_extraction_batch_size"] = target_batch_size
                self.system_config["system"]["linking_map_batch_size"] = target_batch_size
                self.system_config["system"]["financial_report_batch_size"] = target_batch_size
            
            self.log.info(f"✅ BATCH SYNC: All batch sizes synchronized to {target_batch_size}")
            self.log.info(f"   Updated values: max_products_per_cycle={new_max_products_per_cycle}, supplier_extraction_batch_size={new_supplier_extraction_batch_size}")
            
        else:
            # Only synchronize the two main processing batch sizes
            new_max_products_per_cycle = target_batch_size
            new_supplier_extraction_batch_size = target_batch_size
            
            self.log.info(f"✅ BATCH SYNC: Main processing batch sizes synchronized to {target_batch_size}")
            self.log.info(f"   Updated values: max_products_per_cycle={new_max_products_per_cycle}, supplier_extraction_batch_size={new_supplier_extraction_batch_size}")
        
        return new_max_products_per_cycle, new_supplier_extraction_batch_size

    async def _run_hybrid_processing_mode(self, supplier_url: str, supplier_name: str, 
                                         category_urls_to_scrape: List[str], 
                                         max_products_per_category: int, max_products_to_process: int,
                                         max_analyzed_products: int, max_products_per_cycle: int, 
                                         supplier_extraction_batch_size: int) -> List[Dict[str, Any]]:
        """
        Hybrid processing mode that allows switching between supplier extraction and Amazon analysis.
        Supports chunked, sequential, and balanced processing modes.
        """
        profitable_results: List[Dict[str, Any]] = []
        full_config = self.config_loader._config
        hybrid_config = full_config.get("hybrid_processing", {})
        processing_modes = hybrid_config.get("processing_modes", {})
        switch_after_categories = hybrid_config.get("switch_to_amazon_after_categories", 10)
        
        self.log.info(f"🔄 HYBRID PROCESSING: Mode configuration loaded")
        self.log.info(f"   switch_to_amazon_after_categories: {switch_after_categories}")
        
        if processing_modes.get("chunked", {}).get("enabled", False):
            # Chunked mode: Alternate between supplier extraction and Amazon analysis
            chunk_size = processing_modes.get("chunked", {}).get("chunk_size_categories", 10)
            self.log.info(f"🔄 HYBRID MODE: Chunked processing (chunk size: {chunk_size} categories)")
            
            # Process categories in chunks
            for chunk_start in range(0, len(category_urls_to_scrape), chunk_size):
                chunk_end = min(chunk_start + chunk_size, len(category_urls_to_scrape))
                chunk_categories = category_urls_to_scrape[chunk_start:chunk_end]
                
                self.log.info(f"🔄 Processing chunk {chunk_start//chunk_size + 1}: categories {chunk_start+1}-{chunk_end}")
                
                # Extract from this chunk of categories
                chunk_products = await self._extract_supplier_products(
                    supplier_url, supplier_name, chunk_categories, 
                    max_products_per_category, max_products_to_process, supplier_extraction_batch_size
                )
                
                if chunk_products:
                    # Immediately analyze these products
                    # Use the same detailed processing logic as main workflow
                    chunk_results = await self._process_chunk_with_main_workflow_logic(
                        chunk_products, max_products_per_cycle
                    )
                    profitable_results.extend(chunk_results)
                    
                    # Check memory management
                    memory_config = hybrid_config.get("memory_management", {})
                    if memory_config.get("clear_cache_between_phases", False):
                        self.log.info("🧹 Clearing cache between processing phases")
                        # Add cache clearing logic here if needed
                
        elif processing_modes.get("balanced", {}).get("enabled", False):
            # Balanced mode: Extract in batches, analyze each batch
            self.log.info(f"🔄 HYBRID MODE: Balanced processing")
            
            # Extract all products first
            all_products = await self._extract_supplier_products(
                supplier_url, supplier_name, category_urls_to_scrape, 
                max_products_per_category, max_products_to_process
            )
            
            if all_products:
                # Process in analysis batches if enabled
                if processing_modes.get("balanced", {}).get("analysis_after_extraction_batch", True):
                    batch_size = max_products_per_cycle
                    for batch_start in range(0, len(all_products), batch_size):
                        batch_end = min(batch_start + batch_size, len(all_products))
                        batch_products = all_products[batch_start:batch_end]
                        
                        self.log.info(f"🔄 Analyzing batch {batch_start//batch_size + 1}: products {batch_start+1}-{batch_end}")
                        # Use the same detailed processing logic as main workflow
                        batch_results = await self._process_chunk_with_main_workflow_logic(
                            batch_products, max_products_per_cycle
                        )
                        profitable_results.extend(batch_results)
                else:
                    # Analyze all products at once
                    # Use the same detailed processing logic as main workflow
                    profitable_results = await self._process_chunk_with_main_workflow_logic(
                        all_products, max_products_per_cycle
                    )
        else:
            # Sequential mode (default): Complete supplier extraction, then Amazon analysis
            self.log.info(f"🔄 HYBRID MODE: Sequential processing (extract all, then analyze all)")
            
            # Standard sequential processing - extract all first
            all_products = await self._extract_supplier_products(
                supplier_url, supplier_name, category_urls_to_scrape, 
                max_products_per_category, max_products_to_process
            )
            
            if all_products:
                profitable_results = await self._analyze_products_batch(
                    all_products, supplier_name, max_products_per_cycle
                )
        
        # Final save operations for hybrid mode
        try:
            self.state_manager.complete_processing()
            self._save_linking_map(self.supplier_name)
            self._save_final_report(profitable_results, self.supplier_name)
            self.log.info(f"📊 Processing state file saved: {self.state_manager.state_file_path}")
            self.log.info(f"📊 Final state summary: {self.state_manager.get_state_summary()}")
            self.log.info("--- Hybrid Processing Mode Finished ---")
            self.log.info(f"Summary: {self.results_summary}")
        except Exception as save_error:
            self.log.error(f"❌ CRITICAL: Error during final save operations: {save_error}", exc_info=True)


        return profitable_results

    async def _analyze_products_batch(self, products: List[Dict[str, Any]], 
                                    supplier_name: str, max_products_per_cycle: int) -> List[Dict[str, Any]]:
        """Analyze a batch of supplier products for Amazon matching and profitability."""
        profitable_results = []
        
        # Filter and prepare products for analysis
        valid_products = [
            p for p in products
            if p.get("title") and isinstance(p.get("price"), (float, int)) and p.get("price", 0) > 0 and p.get("url")
        ]
        
        price_filtered_products = [
            p for p in valid_products
            if MIN_PRICE <= p.get("price", 0) <= MAX_PRICE
        ]
        
        self.log.info(f"🔍 Analyzing {len(price_filtered_products)} products in batch mode")
        
        # Process products in cycles
        batch_size = max_products_per_cycle
        total_batches = (len(price_filtered_products) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(price_filtered_products))
            batch_products = price_filtered_products[start_idx:end_idx]
            
            self.log.info(f"🔄 Processing analysis batch {batch_num + 1}/{total_batches} ({len(batch_products)} products)")
            
            for i, product_data in enumerate(batch_products):
                current_index = start_idx + i + 1
                self.log.info(f"🔍 Analyzing product {current_index}: '{product_data.get('title')}'")
                
                # Check if already processed
                if self.state_manager.is_product_processed(product_data.get("url")):
                    self.log.info(f"Product already processed: {product_data.get('url')}. Skipping.")
                    continue
                
                # Amazon data extraction and analysis
                amazon_data = await self._get_amazon_data(product_data)
                if not amazon_data or "error" in amazon_data:
                    self.log.warning(f"Could not retrieve Amazon data for '{product_data.get('title')}'")
                    self.state_manager.mark_product_processed(product_data.get("url"), "failed_amazon_extraction")
                    continue
                
                # Save Amazon cache and create linking map
                supplier_ean = product_data.get("ean") or product_data.get("barcode")
                asin = amazon_data.get("asin", "NO_ASIN")
                
                # Save Amazon data
                filename_identifier = supplier_ean if supplier_ean else re.sub(r'[<>:"/\\|?*\s]+', '_', product_data.get("title", "NO_TITLE")[:50])
                amazon_cache_path = os.path.join(self.amazon_cache_dir, f"amazon_{asin}_{filename_identifier}.json")
                with open(amazon_cache_path, 'w', encoding='utf-8') as f:
                    json.dump(amazon_data, f, indent=2, ensure_ascii=False)
                
                # Financial analysis
                try:
                    from FBA_Financial_calculator import financials as calc_financials
                    supplier_price = float(product_data.get("price", 0))
                    supplier_price_inc_vat = supplier_price
                    current_price = amazon_data.get("current_price", 0)

                    if supplier_price > 0 and current_price > 0:
                        financials = calc_financials(product_data, amazon_data, supplier_price_inc_vat)
                        
                        # Check profitability
                        if financials.get("ROI", 0) > MIN_ROI_PERCENT and financials.get("NetProfit", 0) > MIN_PROFIT_PER_UNIT:
                            self.log.info(f"✅ PROFITABLE: ROI {financials['ROI']:.1f}%, Profit £{financials['NetProfit']:.2f}")
                            
                            combined_data = self._combine_supplier_amazon_data(product_data, amazon_data, "hybrid_batch")
                            combined_data["financials"] = financials
                            profitable_results.append(combined_data)
                            
                            self.state_manager.update_success_metrics(True, True, financials.get("NetProfit", 0))
                            self.state_manager.mark_product_processed(product_data.get("url"), "completed_profitable")
                        else:
                            self.log.info(f"Not profitable: ROI {financials.get('ROI', 0):.1f}%, Profit £{financials.get('NetProfit', 0):.2f}")
                            self.state_manager.update_success_metrics(True, False)
                            self.state_manager.mark_product_processed(product_data.get("url"), "completed_not_profitable")
                            
                except Exception as e:
                    self.log.error(f"Financial calculation failed: {e}")
                    self.state_manager.mark_product_processed(product_data.get("url"), "failed_financial_calculation")
        
        return profitable_results

    def _get_cached_products_path(self, category_url: str):
        """Helper to get the path for a category's product cache file."""
        category_filename = f"{self.supplier_name}_{category_url.split('/')[-1]}_products.json"
        cache_dir = os.path.join(self.output_dir, 'CACHE', 'supplier_cache')
        return os.path.join(cache_dir, category_filename)

    def _load_linking_map(self, supplier_name: str) -> Dict[str, str]:
        """Load linking map from supplier-specific JSON file"""
        linking_map_path = get_linking_map_path(supplier_name)
        
        if os.path.exists(linking_map_path):
            try:
                with open(linking_map_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                
                # Handle both formats: new dict format and legacy list format
                if isinstance(raw_data, dict):
                    # New simple format: {"EAN": "ASIN", "EAN2": "ASIN2"}
                    linking_map = raw_data
                    self.log.info(f"✅ Loaded linking map (dict format) from {linking_map_path} with {len(linking_map)} entries")
                elif isinstance(raw_data, list):
                    # Legacy detailed format: [{"supplier_ean": "123", "amazon_asin": "ABC", ...}]
                    linking_map = {}
                    for entry in raw_data:
                        if isinstance(entry, dict) and "supplier_ean" in entry and "amazon_asin" in entry:
                            linking_map[entry["supplier_ean"]] = entry["amazon_asin"]
                    self.log.info(f"✅ Converted linking map from list format to dict format from {linking_map_path} with {len(linking_map)} entries")
                    
                    # Save the converted format back to file for future use
                    self._save_converted_linking_map(supplier_name, linking_map)
                else:
                    self.log.error(f"Unexpected linking map format: {type(raw_data)} - Creating new map")
                    return {}
                    
                return linking_map
            except (json.JSONDecodeError, UnicodeDecodeError, Exception) as e:
                self.log.error(f"Error loading linking map: {e} - Creating new map")
                return {}
        else:
            self.log.info(f"✅ No existing linking map found at {linking_map_path} - Creating new map")
            return {}

    def _save_linking_map(self, supplier_name: str):
        """Save linking map to supplier-specific JSON file using atomic write pattern"""
        self.log.info(f"🔍 DEBUG: _save_linking_map called with {len(self.linking_map)} entries for supplier {supplier_name}")
        if not self.linking_map:
            self.log.info("Empty linking map - nothing to save.")
            return
            
        linking_map_path = get_linking_map_path(supplier_name)
        
        # Use atomic write pattern to prevent corruption
        temp_path = f"{linking_map_path}.tmp"
        try:
            # First write to temporary file
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.linking_map, f, indent=2, ensure_ascii=False)
                
            # Then atomically replace the original file
            os.replace(temp_path, linking_map_path)
            self.log.info(f"✅ Successfully saved linking map with {len(self.linking_map)} entries to {linking_map_path}")
        except Exception as e:
            self.log.error(f"Error saving linking map: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    async def _run_financial_analysis(self, combined_data: dict) -> dict:
        """Run financial analysis on combined supplier and Amazon data"""
        try:
            # Import financial calculation functions directly to avoid full cache dependency (matches line 1253)
            from FBA_Financial_calculator import financials as calc_financials
            
            # Extract supplier price with validation (matches your Fix 1.4 pattern)
            supplier_price_inc_vat = combined_data.get("price", 0)
            amazon_price = combined_data.get("current_price", 0)
            
            # Ensure we have valid prices
            if supplier_price_inc_vat <= 0 or amazon_price <= 0:
                self.log.warning(f"Invalid prices: supplier={supplier_price_inc_vat}, amazon={amazon_price}")
                return {"is_profitable": False, "error": "Invalid prices"}
            
            # Calculate financial metrics (matches your Fix 1.1 pattern)
            financials = calc_financials(combined_data, combined_data, supplier_price_inc_vat)
            
            # Check minimum profitability thresholds
            MIN_ROI_PERCENT = 15  # Minimum 15% ROI
            MIN_PROFIT_PER_UNIT = 2  # Minimum £2 profit per unit
            
            roi = financials.get("ROI", 0)
            net_profit = financials.get("NetProfit", 0)
            
            is_profitable = roi > MIN_ROI_PERCENT and net_profit > MIN_PROFIT_PER_UNIT
            
            # Prepare result
            result = {
                "is_profitable": is_profitable,
                "financials": financials,
                "roi": roi,
                "net_profit": net_profit,
                "supplier_price": supplier_price,
                "amazon_price": amazon_price
            }
            
            if is_profitable:
                self.log.info(f"✅ PROFITABLE: ROI {roi:.1f}%, Profit £{net_profit:.2f}")
            else:
                self.log.info(f"Not profitable: ROI {roi:.1f}%, Profit £{net_profit:.2f}")
                
            return result
            
        except Exception as e:
            self.log.error(f"Financial analysis failed: {e}")
            return {"is_profitable": False, "error": str(e)}

    async def _process_chunk_with_main_workflow_logic(self, products: List[Dict[str, Any]], max_products_per_cycle: int) -> List[Dict[str, Any]]:
        """Process products using the same detailed logic as main workflow (not simplified batch processing)"""
        profitable_results = []
        
        # Filter and prepare products for analysis (same as main workflow)
        valid_products = [
            p for p in products
            if p.get("title") and isinstance(p.get("price"), (float, int)) and p.get("price", 0) > 0 and p.get("url")
        ]
        
        price_filtered_products = [
            p for p in valid_products
            if MIN_PRICE <= p.get("price", 0) <= MAX_PRICE
        ]
        
        self.log.info(f"🔍 Processing {len(price_filtered_products)} products with main workflow logic")
        
        # Use the same logic as the main workflow
        batch_size = max_products_per_cycle
        total_batches = (len(price_filtered_products) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(price_filtered_products))
            batch_products = price_filtered_products[start_idx:end_idx]
            
            # Process each product in the current batch using main workflow logic
            for i, product_data in enumerate(batch_products):
                current_index = start_idx + i + 1
                self.log.info(f"--- Processing supplier product {current_index}/{len(price_filtered_products)}: '{product_data.get('title')}' ---")
                
                # Check if product has been previously processed
                if self.state_manager.is_product_processed(product_data.get("url")):
                    self.log.info(f"Product already processed: {product_data.get('url')}. Skipping.")
                    continue

                # Extract Amazon data using the same logic as main workflow
                amazon_data = await self._get_amazon_data(product_data)
                
                if amazon_data:
                    # Create linking map entry
                    supplier_ean = product_data.get("ean")
                    amazon_asin = amazon_data.get("asin") or amazon_data.get("asin_extracted_from_page")
                    
                    if supplier_ean and amazon_asin:
                        # DEBUG: Check linking_map type before assignment
                        self.log.debug(f"🔍 DEBUG: linking_map type: {type(self.linking_map)}, value: {self.linking_map}")
                        self.linking_map[supplier_ean] = amazon_asin
                    
                    # Combine supplier and Amazon data
                    combined_data = {**product_data, **amazon_data}
                    
                    # Run financial analysis
                    financial_result = await self._run_financial_analysis(combined_data)
                    
                    if financial_result and financial_result.get("is_profitable"):
                        profitable_results.append(financial_result)
                        self.log.info(f"✅ Profitable product found: {product_data.get('title')}")
                        self.state_manager.mark_product_processed(product_data.get("url"), "completed_profitable")
                    elif financial_result and financial_result.get("error"):
                        self.log.info(f"❌ Financial analysis failed: {financial_result.get('error')}")
                        self.state_manager.mark_product_processed(product_data.get("url"), "failed_financial_calculation")
                    else:
                        self.log.info(f"❌ Not profitable product: {product_data.get('title')}")
                        self.state_manager.mark_product_processed(product_data.get("url"), "completed_not_profitable")
                
                # Save state periodically
                if current_index % 5 == 0:
                    self.state_manager.save_state()
                    self._save_linking_map(self.supplier_name)
        
        return profitable_results