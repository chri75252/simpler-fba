"""
Passive extraction workflow for Amazon FBA products from supplier websites.
Uses Chrome with debug port for Amazon data and a configurable web scraper for supplier sites.
Integrates AI client for enhanced extraction capabilities.
"""

import os
import asyncio
import logging
import json
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
import re
import time
import requests
from urllib.parse import urlparse, parse_qs, urljoin
import difflib

from openai import OpenAI
from bs4 import BeautifulSoup

# Ensure paths are set up correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))

# Import required modules from tools directory
from amazon_playwright_extractor import AmazonExtractor
from configurable_supplier_scraper import ConfigurableSupplierScraper

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

# Priority patterns for product classification
FBA_FRIENDLY_PATTERNS = {
    "home_kitchen":      ["home","kitchen","dining","storage","decor","organization"],
    "pet_supplies":      ["pet","dog","cat","animal","bird","aquarium"],
    "beauty_care":       ["beauty","personal","skincare","grooming","cosmetic"],
    "sports_outdoor":    ["sport","fitness","camping","outdoor","exercise","yoga"],
    "office_stationery": ["office","stationery","desk","paper","business"],
    "diy_tools":         ["diy","tool","hardware","hand-tool","craft","workshop"],
    "baby_nursery":      ["baby","infant","nursery","toddler","child-safe"],
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
MIN_PROFIT_PER_UNIT = float(os.getenv("MIN_PROFIT_PER_UNIT", "3.0"))
MIN_RATING = float(os.getenv("MIN_RATING", "4.0"))
MIN_REVIEWS = int(os.getenv("MIN_REVIEWS", "50"))
MAX_SALES_RANK = int(os.getenv("MAX_SALES_RANK", "150000"))

DEFAULT_SUPPLIER_URL = os.getenv("DEFAULT_SUPPLIER_URL", "https://www.clearance-king.co.uk")
DEFAULT_SUPPLIER_NAME = os.getenv("DEFAULT_SUPPLIER", "clearance-king.co.uk")

# Initial constants and paths
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "C:\\Users\\chris\\Amazon-FBA-Agent-System\\Amazon-FBA-Agent-System-v3\\OUTPUTS\\FBA_ANALYSIS")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Global constant for persistent linking map
LINKING_MAP_DIR = os.path.join(OUTPUT_DIR, "Linking map")
os.makedirs(LINKING_MAP_DIR, exist_ok=True)
LINKING_MAP_PATH = os.path.join(LINKING_MAP_DIR, "linking_map.json")

# Other directories
SUPPLIER_CACHE_DIR = os.path.join(OUTPUT_DIR, "..", "cached_products")
AMAZON_CACHE_DIR = os.path.join(OUTPUT_DIR, "amazon_cache")
AI_CATEGORY_CACHE_DIR = os.path.join(OUTPUT_DIR, "ai_category_cache")
os.makedirs(SUPPLIER_CACHE_DIR, exist_ok=True)
os.makedirs(AMAZON_CACHE_DIR, exist_ok=True)
os.makedirs(AI_CATEGORY_CACHE_DIR, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Battery product detection constants
BATTERY_KEYWORDS = ("battery", "batteries", "cell", "cr20", "lr41", "lithium", "alkaline")

def is_battery_title(title: str) -> bool:
    """Check if a product title indicates it's a battery product."""
    if not title:
        return False
    return any(k in title.lower() for k in BATTERY_KEYWORDS)


class FixedAmazonExtractor(AmazonExtractor):
    """
    Extension of AmazonExtractor with EAN search capabilities and page reuse.
    """
    def __init__(self, chrome_debug_port: int, ai_client: Optional[OpenAI] = None):
        super().__init__(chrome_debug_port, ai_client)

    async def connect(self) -> Browser:
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
            return self.browser
        except Exception as e:
            log.error(f"Failed to connect to Chrome on port {self.chrome_debug_port} (FixedAmazonExtractor): {e}")
            raise

    async def search_by_ean_and_extract_data(self, ean: str, supplier_product_title: str) -> Dict[str, Any]:
        """Search Amazon by EAN and extract product data."""
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
            log.info(f"Navigating to Amazon UK to search for EAN: {ean}")
            await page.goto(f"https://www.amazon.co.uk/s?k={ean}", timeout=60000)
            
            await page.wait_for_selector("div.s-search-results", timeout=15000)
            
            search_result_elements = []
            search_selectors = [
                "div.s-search-results div[data-asin]:not([data-asin='']):not(.AdHolder):not([class*='s-widget-sponsored-product'])"
            ]
            
            for selector in search_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        search_result_elements = elements
                        log.info(f"Found {len(elements)} search result elements using selector: {selector}")
                        break
                except Exception as e:
                    log.debug(f"Selector '{selector}' failed: {e}")
                    continue
            
            log.info(f"Processing {len(search_result_elements)} search result elements for EAN {ean}")
            
            organic_results = []
            for element in search_result_elements:
                try:
                    # Get ASIN
                    asin = await element.get_attribute("data-asin")
                    if not asin:
                        continue
                    
                    # Try to get title
                    title_element = await element.query_selector("h2 a span")
                    title = await title_element.inner_text() if title_element else "Unknown Title"
                    
                    # Other metadata when available
                    rating_element = await element.query_selector("span[aria-label*='out of 5 stars']")
                    rating = await rating_element.get_attribute("aria-label") if rating_element else None
                    
                    price_element = await element.query_selector("span.a-price span.a-offscreen")
                    price = await price_element.inner_text() if price_element else None
                    
                    log.info(f"Found organic result: ASIN {asin} - {rating}...")
                    
                    organic_results.append({
                        "asin": asin,
                        "title": title,
                        "rating": rating,
                        "price": price,
                        "source": "ean_search"
                    })
                except Exception as e:
                    log.debug(f"Error extracting search result: {e}")
            
            if len(organic_results) == 1:
                only_asin = organic_results[0]["asin"]
                log.info(f"Single organic result found for EAN {ean}: ASIN {only_asin}")
                log.info(f"EAN search selected ASIN {only_asin} for {ean}")
                
                # Extract Amazon data for the identified ASIN
                amazon_data = await self.extract_data(only_asin)
                return amazon_data
            elif len(organic_results) > 1:
                log.info(f"Found {len(organic_results)} potential matches for EAN {ean}")
                
                # Select best match (first result as fallback)
                log.info(f"EAN search selected ASIN {organic_results[0]['asin']} for {ean}")
                amazon_data = await self.extract_data(organic_results[0]['asin'])
                return amazon_data
            else:
                log.warning(f"No organic search results found for EAN: {ean}")
                return {"error": f"No Amazon products found for EAN {ean}"}
                
        except Exception as e:
            log.error(f"Error during Amazon EAN search for {ean}: {e}")
            return {"error": f"Error during Amazon EAN search: {str(e)}"}


class PassiveExtractionWorkflow:
    def __init__(self, chrome_debug_port: int = 9222, ai_client: Optional[OpenAI] = None, max_cache_age_hours: int = 168, min_price: float = 0.1):
        """Initialize the passive extraction workflow."""
        self.chrome_debug_port = chrome_debug_port
        self.ai_client = ai_client
        self.max_cache_age_hours = max_cache_age_hours
        self.min_price = min_price
        
        # Initialize extractor classes
        self.extractor = FixedAmazonExtractor(
            chrome_debug_port=chrome_debug_port,
            ai_client=self.ai_client
        )
        self.scraper = ConfigurableSupplierScraper(
            ai_client=self.ai_client,
            openai_model_name=OPENAI_MODEL_NAME
        )
        
        # Paths
        self.supplier_cache_dir = SUPPLIER_CACHE_DIR
        self.amazon_cache_dir = AMAZON_CACHE_DIR
        self.max_cache_age_seconds = max_cache_age_hours * 3600
        
        # State tracking
        self.linking_map = self._load_linking_map()
        self.last_processed_index = 0
        self.force_ai_category_suggestion = False
        self.max_pages_per_category = None
        
        # Results tracking 
        self.results_summary = {
            "total_supplier_products": 0,
            "products_analyzed_ean": 0,
            "products_analyzed_title": 0,
            "products_passed_triage": 0,
            "products_rejected_by_triage": 0,
            "products_previously_visited": 0,
            "profitable_products": 0,
            "errors": 0,
            "start_time": datetime.now().isoformat()
        }
        
        if self.ai_client:
            log.info(f"PassiveExtractionWorkflow initialized WITH an AI client.")
        else:
            log.info(f"PassiveExtractionWorkflow initialized WITHOUT an AI client. AI-dependent features will be skipped.")

    async def _scrape_supplier_category_url_with_pagination(self, category_url: str, category_name: str, base_url: str, all_supplier_products_for_domain: List[Dict[str, Any]], processed_products_in_run: Set[str]):
        """Scrape a single category URL, handling pagination if configured."""
        total_products_extracted_for_category = 0
        current_category_url = category_url
        current_page_num = 1
        processed_pages_for_this_category = 0

        while current_category_url and (self.max_pages_per_category is None or processed_pages_for_this_category < self.max_pages_per_category):
            log.info(f"Fetching supplier category page {current_page_num} for {category_name}: {current_category_url}")
            page_html = await self.scraper.get_page_content(current_category_url)
            if not page_html:
                log.error(f"Failed to fetch HTML for category page: {current_category_url}")
                break

            page_soup = BeautifulSoup(page_html, 'html.parser')
            product_elements = self.scraper.extract_product_elements(page_html, current_category_url)

            if not product_elements:
                log.warning(f"No product elements found on {current_category_url} (Page {current_page_num}).")
            else:
                log.info(f"Found {len(product_elements)} product elements on {current_category_url} (Page {current_page_num}).")
                extracted_count_on_page = await self._process_product_elements_on_page(
                    product_elements, current_category_url, base_url, all_supplier_products_for_domain, processed_products_in_run
                )
                total_products_extracted_for_category += extracted_count_on_page

            processed_pages_for_this_category += 1
            current_page_num += 1

            # Get next page URL from scraper
            next_page_url = self.scraper.get_next_page_url(current_category_url, page_soup, current_page_num - 1)

            if next_page_url and next_page_url != current_category_url:
                # Validate that the next_page_url is for the same domain to prevent straying off-site
                parsed_next_url = urlparse(next_page_url)
                parsed_base_url = urlparse(base_url)
                if parsed_next_url.netloc == parsed_base_url.netloc:
                    log.info(f"Next page found by scraper: {next_page_url}")
                    current_category_url = next_page_url
                else:
                    log.warning(f"Scraper returned next page URL for a different domain ({parsed_next_url.netloc} vs {parsed_base_url.netloc}): {next_page_url}. Stopping pagination for this category.")
                    break
            else:
                if next_page_url == current_category_url:
                    log.info(f"Scraper returned same URL for next page: {next_page_url}. Stopping pagination for this category.")
                else:
                    log.info(f"No further next page URL found by scraper for {category_name} from {current_category_url}. Reached end of category or pagination limit.")
                break # Exit pagination loop for this category

        log.info(f"Finished scraping category '{category_name}'. Extracted {total_products_extracted_for_category} products from {processed_pages_for_this_category} pages.")

    async def _process_product_elements_on_page(self, product_elements: List[Any], category_url: str, base_url: str, all_supplier_products_for_domain: List[Dict[str, Any]], processed_products_in_run: Set[str]) -> int:
        """Process product elements found on a single category page."""
        # Implementation placeholder
        return 0

    async def run(self, supplier_url: str = DEFAULT_SUPPLIER_URL,
                  supplier_name: str = DEFAULT_SUPPLIER_NAME,
                  max_products_to_process: int = 50,
                  cache_supplier_data: bool = True,
                  force_config_reload: bool = False,
                  debug_smoke: bool = False,
                  resume_from_last: bool = True) -> List[Dict[str, Any]]:
        """Main execution method for the workflow."""
        profitable_results: List[Dict[str, Any]] = []
        
        # Implementation placeholder
        
        # Fee logging enhancement for Keepa data
        # The following code would typically be in this method after Amazon data is extracted:
        """
        referral_fee_gbp = keepa_details.get("product_details_tab_data", {}).get("Referral Fee based on current Buy Box price", 0.0)
        fba_fee_gbp = keepa_details.get("product_details_tab_data", {}).get("FBA Pick&Pack Fee", 0.0)
        
        if not isinstance(referral_fee_gbp, (float, int)) or referral_fee_gbp == 0.0:
            log.warning(f"Referral Fee from Keepa is missing or zero for ASIN {amazon_data['asin']}. Raw Keepa product_details_tab_data keys: {list(keepa_details.get('product_details_tab_data', {}).keys())}")
            referral_fee_gbp = 0.0 # Ensure it's a float
        if not isinstance(fba_fee_gbp, (float, int)) or fba_fee_gbp == 0.0:
            log.warning(f"FBA Fee from Keepa is missing or zero for ASIN {amazon_data['asin']}. Raw Keepa product_details_tab_data keys: {list(keepa_details.get('product_details_tab_data', {}).keys())}")
            fba_fee_gbp = 0.0 # Ensure it's a float

        total_fees_gbp = referral_fee_gbp + fba_fee_gbp
        log.info(f"Using fees from Keepa (or fallback): Referral Fee £{referral_fee_gbp:.2f}, FBA Fee £{fba_fee_gbp:.2f}, Total £{total_fees_gbp:.2f}")
        """
        
        return profitable_results
    
    def _load_linking_map(self) -> Dict[str, Any]:
        """Load linking map from persistent file or initialize empty map if not exists."""
        if os.path.exists(LINKING_MAP_PATH):
            try:
                with open(LINKING_MAP_PATH, 'r', encoding='utf-8') as f:
                    linking_map = json.load(f)
                log.info(f"Loaded linking map from {LINKING_MAP_PATH} with {len(linking_map)} entries")
                return linking_map
            except Exception as e:
                log.error(f"Error loading linking map: {e} - Creating new map")
                return {}
        else:
            log.info(f"No existing linking map found at {LINKING_MAP_PATH} - Creating new map")
            return {}

    def _save_linking_map(self):
        """Save linking map to persistent file."""
        if not self.linking_map:
            return
        
        try:
            with open(LINKING_MAP_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.linking_map, f, indent=2, ensure_ascii=False)
            log.info(f"Successfully saved linking map with {len(self.linking_map)} entries to {LINKING_MAP_PATH}")
        except Exception as e:
            log.error(f"Error saving linking map: {e}")


async def run_workflow_main():
    """
    Main entry point for the passive extraction workflow.
    Orchestrates cache clearing, workflow execution, and cleanup.
    """
    results = []  # Initialize results variable
    workflow_instance = None
    ai_client = None
    log.info("Initializing Passive Extraction Workflow...")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Amazon FBA Passive Extraction Workflow')
    parser.add_argument('--max-products', type=int, default=10, help='Maximum number of products to process (default: 10)')
    parser.add_argument('--supplier-url', default=DEFAULT_SUPPLIER_URL, help=f'Supplier website URL (default: {DEFAULT_SUPPLIER_URL})')
    parser.add_argument('--supplier-name', '--supplier', default=DEFAULT_SUPPLIER_NAME, help=f'Supplier name (default: {DEFAULT_SUPPLIER_NAME})')
    parser.add_argument('--min-price', type=float, default=0.1, help='Minimum supplier product price in GBP (default: 0.1)')
    parser.add_argument('--force-config-reload', action='store_true', help='Force reload supplier configuration and clear cache')
    parser.add_argument('--debug-smoke', action='store_true', help='Inject debug product for end-to-end testing')
    
    args = parser.parse_args()
    
    max_products = args.max_products
    supplier_url = args.supplier_url
    supplier_name = args.supplier_name
    min_price = args.min_price
    force_config_reload = args.force_config_reload
    debug_smoke = args.debug_smoke

    # Initialize OpenAI client if API key is available
    if OPENAI_API_KEY:
        try:
            ai_client = OpenAI(api_key=OPENAI_API_KEY)
            log.info(f"OpenAI client initialized with model {OPENAI_MODEL_NAME}")
        except Exception as e: 
            log.error(f"Failed to initialize OpenAI client: {e}")
    
    try:
        # Initialize workflow
        workflow_instance = PassiveExtractionWorkflow(chrome_debug_port=9222, ai_client=ai_client, min_price=min_price)
        
        # Run workflow
        results = await workflow_instance.run(
            supplier_url=supplier_url,
            supplier_name=supplier_name,
            max_products_to_process=max_products,
            force_config_reload=force_config_reload,
            debug_smoke=debug_smoke
        )
        
        return results
    
    except Exception as e:
        log.error(f"Error in workflow execution: {e}", exc_info=True)
        return []
    
    finally:
        # Clean up resources
        if workflow_instance and hasattr(workflow_instance, 'extractor'):
            log.info("Amazon extractor browser connection intended to be kept open.")
        
        if workflow_instance and hasattr(workflow_instance, 'scraper'):
            await workflow_instance.scraper.close_session()
            log.info("Web scraper session closed.")
        
        log.info("Main workflow execution finished.")


if __name__ == "__main__":
    asyncio.run(run_workflow_main()) 