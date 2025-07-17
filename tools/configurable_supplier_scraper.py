"""
ConfigurableSupplierScraper class for the passive extraction workflow.
Provides methods for extracting data from supplier websites with externalized selector configuration.
Uses Playwright for robust browser automation with anti-bot evasion and JavaScript support.
Maintains backward compatibility with the orchestrator while using improved Playwright-based approach.
"""

import os
import logging
import argparse
import re
import asyncio
import time
import json
import random # For jitter in retries
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin
import aiohttp

# Playwright imports with graceful fallback
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = BrowserContext = Page = None

# Import centralized browser manager
try:
    from utils.browser_manager import get_browser_manager, get_page_for_url
    BROWSER_MANAGER_AVAILABLE = True
except ImportError:
    # Fallback if browser manager not available
    get_browser_manager = None
    get_page_for_url = None
    BROWSER_MANAGER_AVAILABLE = False

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import config loader for supplier selector configuration
import sys
# Add both parent directory and config directory to path for standalone execution
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'config'))

try:
    from config.supplier_config_loader import load_supplier_selectors, get_domain_from_url
except ImportError:
    try:
        # Alternative path when run from tools directory
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'config'))
        from supplier_config_loader import load_supplier_selectors, get_domain_from_url
    except ImportError:
        # Final fallback - define minimal functions
        def load_supplier_selectors(domain: str):
            """Fallback function to load selectors"""
            return {}
        def get_domain_from_url(url: str):
            """Fallback function to get domain from URL"""
            from urllib.parse import urlparse
            return urlparse(url).netloc.replace("www.", "")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Constants
OPENAI_MODEL_NAME_DEFAULT = "gpt-4.1-mini-2025-04-14"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
REQUEST_TIMEOUT = 30  # seconds


class ConfigurableSupplierScraper:
    """
    Configurable web scraper for extracting data from supplier websites.
    Uses Playwright for robust browser automation with anti-bot evasion.
    Prioritizes selector-based extraction, with AI-powered fallbacks.
    Features include full JavaScript support, dynamic content handling, and flexible selectors.
    """

    def __init__(self, ai_client: Optional[Any] = None, openai_model_name: str = None, 
                 headless: bool = False, use_shared_chrome: bool = True, 
                 auth_callback: Optional[callable] = None, browser_manager=None):
        """
        Initialize the configurable supplier scraper with Playwright.

        Args:
            ai_client: An initialized OpenAI client (or compatible)
            openai_model_name: The model name to use for AI operations (None = load from system_config.json)
            headless: Whether to run browser in headless mode (default: False for debugging)
            use_shared_chrome: Whether to connect to shared Chrome instance via CDP (default: True)
            auth_callback: Optional callback function for authentication evaluation (price, product_index) -> None
        """
        # Load system configuration first
        self.system_config = self._load_system_config()
        
        # Browser management - prefer passed BrowserManager first, then check availability
        self.browser_manager = browser_manager
        self.use_browser_manager = (browser_manager is not None) or (BROWSER_MANAGER_AVAILABLE and use_shared_chrome)
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
        # Progress tracking callback
        self.progress_callback = None
        
        # Authentication callback for multi-tier authentication integration
        self.auth_callback = auth_callback
        
        self.headless = headless
        self.use_shared_chrome = use_shared_chrome
        self.cdp_endpoint = "http://localhost:9222"
        
        # PHASE 1: Add session management for aiohttp
        self._session = None
        
        if self.use_browser_manager:
            log.info("🔧 ConfigurableSupplierScraper will use centralized BrowserManager")
        else:
            log.info("⚠️ Using legacy browser management (BrowserManager not available or disabled)")
        
        # AI client for fallback extraction with dynamic config loading
        self.ai_client = ai_client
        self.openai_model = openai_model_name or self._get_ai_model_from_config()
        self.extraction_targets = self._get_extraction_targets_from_config()
        self.discovery_assistance = self._get_discovery_assistance_from_config()
        self.last_request_time = 0
        self.rate_limit_delay = 1.0  # Default 1 second between requests

        # Cache for loaded selector configurations
        self.loaded_selector_configs: Dict[str, Dict[str, Any]] = {}
        self.supplier_config = {}
        
        # Setup debug logging to logs/debug/ directory
        self._setup_debug_logging()
        
        log.info(f"[CONFIG] Initialized with AI model: {self.openai_model}")
        log.info(f"[TARGET] Extraction targets loaded: {list(self.extraction_targets.keys())}")
        log.info(f"[ASSIST] Discovery assistance enabled: {self.discovery_assistance.get('enabled', False)}")

    def _setup_debug_logging(self):
        """Setup debug logging to logs/debug/supplier_scraping_debug_YYYYMMDD.log"""
        # DISABLED: This was overriding the main script's logging configuration
        # The main script (run_custom_poundwholesale.py) already sets up proper logging
        return
        
        # try:
        #     # Import path manager for standardized logging
        #     import sys
        #     import os
        #     parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        #     if parent_dir not in sys.path:
        #         sys.path.insert(0, parent_dir)
        #     try:
        #         from utils.path_manager import get_log_path
        #     except ImportError:
        #         # Fallback path setup
        #         log.warning("Could not import path_manager, using fallback logging")
        #         return
            
        #     # Create debug log file with current date and time for separate runs
        #     from datetime import datetime
        #     date_time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        #     debug_log_path = get_log_path("debug", f"supplier_scraping_debug_{date_time_str}.log")
            
        #     # Add file handler to logger
        #     debug_handler = logging.FileHandler(debug_log_path)
        #     debug_handler.setLevel(logging.DEBUG)
        #     formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        #     debug_handler.setFormatter(formatter)
            
        #     # Add handler to both module logger and class logger
        #     log.addHandler(debug_handler)
        #     log.setLevel(logging.DEBUG)
            
        #     log.debug(f"Debug logging initialized - writing to {debug_log_path}")
        #     log.debug(f"Headless mode: {self.headless}")
            
        # except Exception as e:
        #     log.warning(f"Failed to setup debug logging: {e}")
    
    def _load_system_config(self) -> Dict[str, Any]:
        """Load system configuration from system_config.json"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "system_config.json")
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                log.info(f"✅ Loaded system configuration from {config_path}")
                return config
        except Exception as e:
            log.error(f"❌ Failed to load system configuration: {e}")
            return {}
    
    def _get_ai_model_from_config(self) -> str:
        """Get AI model name from system configuration"""
        ai_config = self.system_config.get("ai_selector_extraction", {})
        model = ai_config.get("ai_model", OPENAI_MODEL_NAME_DEFAULT)
        log.debug(f"AI model from config: {model}")
        return model
    
    def _get_extraction_targets_from_config(self) -> Dict[str, List[str]]:
        """Get extraction targets from system configuration"""
        ai_config = self.system_config.get("ai_selector_extraction", {})
        targets = ai_config.get("extraction_targets", {})
        log.debug(f"Extraction targets from config: {targets}")
        return targets
    
    def _get_discovery_assistance_from_config(self) -> Dict[str, Any]:
        """Get discovery assistance configuration"""
        discovery_config = self.system_config.get("discovery_assistance", {})
        log.debug(f"Discovery assistance from config: {discovery_config}")
        return discovery_config

    async def _ensure_browser(self) -> Browser:
        """
        Get or create a Playwright browser instance with anti-bot configuration.
        Uses BrowserManager if available, otherwise falls back to legacy methods.

        Returns:
            Browser: The Playwright browser instance
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not available. Install with: pip install playwright && playwright install")
            
        if self.browser is None or not self.browser.is_connected():
            # Try BrowserManager first if available
            if self.use_browser_manager:
                try:
                    # Use passed browser_manager first, then fallback to get_browser_manager()
                    if self.browser_manager:
                        self.browser = await self.browser_manager.get_browser()
                        log.info("✅ Connected to Chrome via passed BrowserManager")
                    else:
                        browser_manager = await get_browser_manager()
                        self.browser = await browser_manager.connect()
                        log.info("✅ Connected to Chrome via BrowserManager")
                    return self.browser
                except Exception as e:
                    log.warning(f"BrowserManager connection failed, falling back to legacy: {e}")
                    self.use_browser_manager = False
            
            # Legacy browser connection
            if self.playwright is None:
                self.playwright = await async_playwright().start()
                
            # Try to connect to shared Chrome instance via CDP if enabled
            if self.use_shared_chrome:
                try:
                    self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_endpoint)
                    log.info(f"Connected to shared Chrome instance at {self.cdp_endpoint}")
                except Exception as e:
                    log.warning(f"Failed to connect to shared Chrome at {self.cdp_endpoint}: {e}")
                    log.info("Falling back to standalone browser launch...")
                    self.browser = None
            
            # Fallback to standalone browser launch if CDP connection failed or disabled
            if self.browser is None:
                self.browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-first-run',
                        '--disable-dev-shm-usage',
                        '--disable-extensions-except-for-extension-validation',
                        '--disable-web-security' if not self.headless else '',  # Only for development
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
                log.info(f"Launched {'headless' if self.headless else 'headed'} Playwright browser")
            
        return self.browser

    async def _get_context(self) -> BrowserContext:
        """
        Get or create a browser context with realistic settings.

        Returns:
            BrowserContext: The browser context for scraping
        """
        if self.context is None:
            browser = await self._ensure_browser()
            self.context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
                timezone_id='America/New_York',
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Cache-Control': 'max-age=0',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            log.debug("Created new browser context with realistic settings")
        return self.context

    async def _get_session(self):
        """
        Get or create an aiohttp session for URL validation and lightweight HTTP requests.
        
        Returns:
            aiohttp.ClientSession: Session instance for HTTP requests
        """
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                headers={'User-Agent': USER_AGENT}
            )
            log.debug("Created new aiohttp session for HTTP requests")
        return self._session

    async def get_page_content(self, url: str, retry_count: int = 3) -> Optional[str]:
        """
        Get the HTML content of a page using Playwright with rate limiting and retries.
        Includes anti-bot evasion and JavaScript support.
        """
        # Rate limiting
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last_request)

        self.last_request_time = time.time()

        for attempt in range(retry_count):
            page = None
            try:
                log.info(f"Fetching page content from: {url} (attempt {attempt + 1}/{retry_count})")
                
                # Use BrowserManager for page creation if available
                if self.use_browser_manager:
                    try:
                        if self.browser_manager:
                            page = await self.browser_manager.get_page()
                            log.info(f"🔧 Using passed BrowserManager page for {url}")
                        elif get_page_for_url:
                            page = await get_page_for_url(url, reuse_existing=True)
                            log.info(f"🔧 Using BrowserManager page for {url}")
                        else:
                            page = None
                    except Exception as e:
                        log.warning(f"BrowserManager page creation failed, using legacy: {e}")
                        self.use_browser_manager = False
                        page = None
                
                # Legacy page creation if BrowserManager not available or failed
                if not self.use_browser_manager or page is None:
                    # Get browser context and create new page
                    context = await self._get_context()
                    page = await context.new_page()
                
                # Add random delay to mimic human behavior
                if attempt > 0:
                    human_delay = random.uniform(1.0, 3.0)
                    await asyncio.sleep(human_delay)
                
                # Navigate to page with timeout (skip if BrowserManager already navigated)
                response = None
                if self.use_browser_manager and page.url == url:
                    # BrowserManager already navigated to the URL
                    log.info(f"🔧 BrowserManager already navigated to {url}")
                    response = page  # Mock response for compatibility
                else:
                    # Need to navigate manually
                    try:
                        response = await page.goto(
                            url,
                            timeout=REQUEST_TIMEOUT * 1000,  # Playwright uses milliseconds
                            wait_until='domcontentloaded'  # Wait for DOM to be ready
                        )
                    except Exception as nav_error:
                        log.warning(f"Navigation failed for {url}: {nav_error}")
                        response = None
                    
                if response is None:
                    log.warning(f"No response received for {url} (attempt {attempt + 1})")
                    continue
                    
                # Check for rate limiting or blocks (skip if using BrowserManager)
                if hasattr(response, 'status'):
                    if response.status == 429:
                        retry_after = 5  # Default wait time
                        log.warning(f"Rate limited (429) for {url}. Waiting {retry_after}s before retry.")
                        await asyncio.sleep(retry_after)
                        continue
                    elif response.status >= 400:
                        log.warning(f"HTTP {response.status} for {url} (attempt {attempt + 1})")
                        if response.status in [403, 503]:  # Possible bot detection
                            wait_time = (2 ** attempt) + random.uniform(2.0, 5.0)
                            log.info(f"Possible bot detection, waiting {wait_time:.2f}s before retry...")
                            await asyncio.sleep(wait_time)
                            continue
                else:
                    # BrowserManager case - assume successful navigation
                    log.info(f"🔧 BrowserManager navigation assumed successful for {url}")
                    
                    try:
                        # Wait for page to be fully loaded (handles dynamic content)
                        await page.wait_for_load_state('networkidle', timeout=10000)
                        
                        # Get page content
                        html_content = await page.content()
                        
                        # Validate content
                        if not html_content or len(html_content) < 500:
                            log.warning(f"Suspiciously small response size ({len(html_content)} bytes) for {url}.")
                            if "<html" not in html_content.lower() or "<body" not in html_content.lower():
                                log.warning(f"Response from {url} doesn't appear to be valid HTML. Retrying if attempts left.")
                                if attempt < retry_count - 1:
                                    await asyncio.sleep(2 * (attempt + 1))
                                continue
                        
                        log.info(f"Successfully fetched content from {url} (Size: {len(html_content)} bytes)")
                        return html_content
                        
                    except Exception as nav_error:
                        log.error(f"Navigation error for {url} (attempt {attempt + 1}): {nav_error}")
                        # Don't immediately retry on navigation errors, let the outer retry logic handle it
                        raise nav_error

            except Exception as e:
                log.error(f"Error fetching {url} (attempt {attempt + 1}): {e}")
                
            finally:
                # Only close page if NOT using BrowserManager (BrowserManager handles page lifecycle)
                if page and not self.use_browser_manager:
                    try:
                        await page.close()
                    except Exception as close_error:
                        log.warning(f"Error closing page: {close_error}")

            if attempt < retry_count - 1:
                wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                log.info(f"Retrying {url} in {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)

        log.error(f"Failed to fetch {url} after {retry_count} attempts.")
        return None

    async def fetch_html(self, url: str) -> Optional[str]:
        """Alias for get_page_content for compatibility."""
        return await self.get_page_content(url)
    
    def set_progress_callback(self, callback_func):
        """Set progress tracking callback for workflow integration"""
        self.progress_callback = callback_func

    async def scrape_products_from_url(self, url: str, max_products: int = 50, product_accumulator: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Enhanced method to scrape products with pagination and individual product page visits.
        
        Args:
            url: Category URL to scrape
            max_products: Maximum products to extract
            product_accumulator: Optional list to append products to in real-time for progress tracking
        """
        log.info(f"Starting enhanced scraping from {url}")
        
        # Step 1: Set page limiter to 60 products per page
        await self._set_page_limiter(url)
        
        # Step 2: Collect all product URLs from all paginated pages
        all_product_urls = await self._collect_all_product_urls(url, max_products)
        
        if not all_product_urls:
            log.warning(f"No product URLs found across all pages for {url}")
            return []
        
        log.info(f"Found {len(all_product_urls)} total product URLs across all pages")
        
        # Step 3: Visit individual product pages to extract detailed data
        products = []  # Local list for return value
        # Use product_accumulator for real-time updates if provided
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        
        for i, product_url in enumerate(all_product_urls[:max_products]):
            try:
                log.info(f"Visiting product page {i+1}/{len(all_product_urls[:max_products])}: {product_url}")
                
                # Get individual product page content
                product_html = await self.get_page_content(product_url)
                if not product_html:
                    log.warning(f"Failed to fetch product page: {product_url}")
                    continue
                
                # Extract detailed product data from individual product page
                soup = BeautifulSoup(product_html, 'html.parser')
                
                # Extract core product data from individual product page
                title = self._extract_text_by_selector(soup, ["h1.page-title .base", "[data-ui-id='page-title-wrapper']"])
                # CRITICAL FIX: Use configurable price extraction instead of hardcoded selectors
                price = await self.extract_price(soup, product_html, product_url)
                ean = self._extract_text_by_selector(soup, [".value.attribute-code-product_barcode"])
                sku = self._extract_text_by_selector(soup, [".value.attribute-code-sku", "[itemprop='sku']"])
                availability = self._extract_text_by_selector(soup, [".stock.available", ".stock.unavailable"])
                
                # Get image from product page or fallback to placeholder
                image_url = self._extract_image_by_selector(soup, ["img.product-image-photo", ".product-image img"])
                
                # Create product data
                product = {
                    'title': title,
                    'price': price,
                    'url': product_url,
                    'ean': ean,
                    'sku': sku,
                    'availability': availability,
                    'image_url': image_url,
                    'source_url': url,
                    'scraped_at': datetime.now().isoformat()
                }
                
                # Authentication evaluation for multi-tier authentication system
                if self.auth_callback:
                    try:
                        # Call authentication callback with price and product index
                        await self.auth_callback(price, i+1)
                    except Exception as auth_error:
                        log.warning(f"🔐 Authentication callback error for product {i+1}: {auth_error}")
                
                # Only include products with valid data and apply price filtering
                if title and price:
                    # Apply price filtering if max_price is configured
                    try:
                        price_float = float(price)
                        max_price = getattr(self, 'max_price', 20.0)  # Default from system config
                        if hasattr(self, 'system_config') and self.system_config:
                            max_price = self.system_config.get('processing_limits', {}).get('max_price_gbp', 20.0)
                        
                        if price_float <= max_price:
                            products.append(product)  # Always add to local return list
                            
                            # 🚨 DEFINITIVE FIX: Add to shared accumulator for real-time progress tracking
                            if product_accumulator is not None:
                                product_accumulator.append(product)
                                log.info(f"🔄 REAL-TIME: Added product {i+1} to shared accumulator (total: {len(product_accumulator)})")
                            
                            log.info(f"✅ Extracted product {i+1}: {title} - £{price} (EAN: {ean or 'N/A'})")
                        else:
                            log.info(f"🛑 PRICE FILTER: Excluding '{title}' - £{price} > £{max_price} limit")
                    except (ValueError, TypeError):
                        # Keep products with invalid/missing prices for now
                        products.append(product)
                        if product_accumulator is not None:
                            product_accumulator.append(product)
                        log.warning(f"⚠️ Invalid price for '{title}': {price}")
                    
                    # Call progress callback AFTER successful product extraction
                    if self.progress_callback:
                        self.progress_callback('supplier_extraction', i+1, len(all_product_urls[:max_products]), product_url, product)
                        
                else:
                    log.warning(f"⚠️ Skipping product {i+1} - missing title or price")
                    # Additional warning for authentication system
                    if not price:
                        log.debug(f"🔍 Price extraction failed for product {i+1} - authentication system will evaluate")
                    
            except Exception as e:
                log.error(f"Error extracting product {i+1}: {e}")
                continue
        
        log.info(f"Successfully extracted {len(products)} products from {url}")
        return products

    async def _set_page_limiter(self, url: str) -> bool:
        """
        Sets the products per page limiter to the configured value (e.g., 60).
        Uses the current browser page managed by BrowserManager.
        """
        log.info(f"Setting page limiter for {url}")
        
        try:
            # Get current page from BrowserManager
            if self.use_browser_manager:
                if self.browser_manager:
                    page = await self.browser_manager.get_page()
                elif get_page_for_url:
                    page = await get_page_for_url(url, reuse_existing=True)
                else:
                    log.warning("BrowserManager not available for page limiter setup")
                    return False
            else:
                log.warning("BrowserManager not available for page limiter setup")
                return False
            
            # Get page limiter configuration
            domain = urlparse(url).netloc
            selectors_config = self._get_selectors_for_domain(domain)
            page_limiter_config = selectors_config.get("page_limiter", {})
            limiter_selector = page_limiter_config.get("selector")
            limiter_value = page_limiter_config.get("value", "60")
            
            if not limiter_selector:
                log.info(f"No page limiter configuration found for {domain}")
                return False
            
            # Wait for and click the page limiter
            await page.wait_for_selector(limiter_selector, state='visible', timeout=10000)
            await page.click(limiter_selector, timeout=5000)
            
            # Wait for page to reload with new limit
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            log.info(f"Successfully set page limiter to {limiter_value} for {url}")
            return True
            
        except Exception as e:
            log.warning(f"Failed to set page limiter for {url}: {e}")
            return False

    async def _collect_all_product_urls(self, url: str, max_products: int) -> List[str]:
        """
        Collects all product URLs from paginated category pages.
        Navigates through pages using ?p=N URL pattern.
        """
        log.info(f"Collecting product URLs from paginated pages starting at: {url}")
        all_product_urls = set()
        current_page = 1
        
        while len(all_product_urls) < max_products:
            # Construct page URL
            if current_page == 1:
                page_url = url
            else:
                separator = "&" if "?" in url else "?"
                page_url = f"{url}{separator}p={current_page}"
            
            log.info(f"Processing page {current_page}: {page_url}")
            
            # Fetch page content
            html_content = await self.get_page_content(page_url)
            if not html_content:
                log.warning(f"Failed to fetch page {current_page}")
                break
            
            # Extract product elements from current page
            product_elements = self.extract_product_elements(html_content, page_url)
            if not product_elements:
                log.info(f"No products found on page {current_page}, stopping pagination")
                break
            
            # Extract URLs from product elements
            base_url = f"{urlparse(page_url).scheme}://{urlparse(page_url).netloc}"
            page_urls = []
            
            for element in product_elements:
                element_html = str(element)
                product_url = await self.extract_url(element, element_html, page_url, base_url)
                if product_url and product_url not in all_product_urls:
                    all_product_urls.add(product_url)
                    page_urls.append(product_url)
                    
                    if len(all_product_urls) >= max_products:
                        break
            
            log.info(f"Found {len(page_urls)} new product URLs on page {current_page}")
            
            # Stop if no new products found or max reached
            if not page_urls or len(all_product_urls) >= max_products:
                break
                
            current_page += 1
            
            # Reasonable pagination limit to prevent infinite loops
            if current_page > 50:
                log.warning("Reached pagination limit of 50 pages")
                break
        
        log.info(f"Collected {len(all_product_urls)} total product URLs across {current_page} pages")
        return list(all_product_urls)[:max_products]

    def _extract_text_by_selector(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
        """Extract text using a list of CSS selectors."""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    return element.get_text(strip=True)
            except Exception as e:
                log.debug(f"Selector '{selector}' failed: {e}")
        return None

    def _extract_price_by_selector(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[float]:
        """Extract price using a list of CSS selectors."""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    # Try to get price from data attribute first
                    price_value = element.get('content') or element.get('data-price-amount')
                    if price_value:
                        return float(price_value)
                    
                    # Fall back to text content
                    text = element.get_text(strip=True)
                    if text:
                        # Extract number from text like "£12.99" or "12.99"
                        import re
                        price_match = re.search(r'[\d,]+\.?\d*', text.replace(',', ''))
                        if price_match:
                            return float(price_match.group())
            except Exception as e:
                log.debug(f"Price selector '{selector}' failed: {e}")
        return None

    def _extract_image_by_selector(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
        """Extract image URL using a list of CSS selectors."""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    # Try different image URL attributes
                    for attr in ['src', 'data-src', 'data-lazy']:
                        img_url = element.get(attr)
                        if img_url:
                            return img_url
            except Exception as e:
                log.debug(f"Image selector '{selector}' failed: {e}")
        return None

    async def _retry_with_vision_selectors(self, element: BeautifulSoup, element_html: str, url: str, base_url: str, product_index: int, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Retry product extraction with vision-based selector discovery if initial extraction fails.
        
        Args:
            element: BeautifulSoup element for the product
            element_html: HTML content of the element
            url: Source URL
            base_url: Base URL for relative links
            product_index: Index of product being processed
            max_retries: Maximum retry attempts
            
        Returns:
            Product dict if successful, None if all retries failed
        """
        try:
            domain = urlparse(url).netloc
            log.info(f"Retrying product {product_index} extraction with vision selectors for {domain}")
            
            for retry in range(max_retries):
                try:
                    log.info(f"Vision retry {retry + 1}/{max_retries} for product {product_index}")
                    
                    # Try to navigate to the product page for better extraction
                    product_url = await self.extract_url(element, element_html, url, base_url)
                    
                    if product_url and self.page:
                        log.info(f"Navigating to product page: {product_url}")
                        await self.page.goto(product_url, wait_until='domcontentloaded')
                        await self.page.wait_for_load_state('networkidle', timeout=5000)
                        
                        # Use vision discovery to find better selectors
                        from tools.vision_discovery_engine import VisionDiscoveryEngine
                        
                        vision_engine = VisionDiscoveryEngine(self.page)
                        product_config = await vision_engine.discover_product_selectors()
                        
                        if product_config and product_config.get('success'):
                            log.info(f"Vision discovery successful for product {product_index}")
                            
                            # Update selectors configuration
                            self._update_selectors_config(domain, product_config)
                            
                            # Retry extraction with new selectors
                            page_content = await self.page.content()
                            page_soup = BeautifulSoup(page_content, 'html.parser')
                            
                            # Extract from the full page now
                            title = await self.extract_title(page_soup, page_content, product_url)
                            price = await self.extract_price(page_soup, page_content, product_url)
                            image_url = await self.extract_image(page_soup, page_content, product_url, base_url)
                            identifier = await self.extract_identifier(page_soup, page_content, product_url)
                            
                            if title and price:
                                product = {
                                    'title': title,
                                    'price': price,
                                    'url': product_url,
                                    'image_url': image_url,
                                    'identifier': identifier,
                                    'source_url': url,
                                    'scraped_at': datetime.now().isoformat(),
                                    'extraction_method': 'vision_retry'
                                }
                                log.info(f"✅ Vision retry successful for product {product_index}: {title}")
                                return product
                            else:
                                log.warning(f"Vision retry {retry + 1} for product {product_index} still missing title or price")
                    else:
                        log.warning(f"No product URL or page available for vision retry {retry + 1}")
                        
                except Exception as e:
                    log.error(f"Vision retry {retry + 1} failed for product {product_index}: {e}")
                    
                # Small delay between retries
                await asyncio.sleep(1)
            
            log.warning(f"All vision retries failed for product {product_index}")
            return None
            
        except Exception as e:
            log.error(f"Vision selector retry failed for product {product_index}: {e}")
            return None
    
    def _update_selectors_config(self, domain: str, product_config: Dict[str, Any]) -> None:
        """Update the cached selectors configuration with vision-discovered selectors"""
        try:
            if domain not in self.loaded_selector_configs:
                self.loaded_selector_configs[domain] = {}
            
            # Merge vision-discovered selectors with existing config
            if 'field_mappings' not in self.loaded_selector_configs[domain]:
                self.loaded_selector_configs[domain]['field_mappings'] = {}
            
            field_mappings = self.loaded_selector_configs[domain]['field_mappings']
            
            # Update with vision-discovered selectors
            if product_config.get('title_selector'):
                field_mappings['title'] = [product_config['title_selector']] + field_mappings.get('title', [])
            
            if product_config.get('price_selector'):
                field_mappings['price'] = [product_config['price_selector']] + field_mappings.get('price', [])
                
            if product_config.get('url_selector'):
                field_mappings['url'] = [product_config['url_selector']] + field_mappings.get('url', [])
                
            if product_config.get('image_selector'):
                field_mappings['image'] = [product_config['image_selector']] + field_mappings.get('image', [])
            
            # Save updated config to file
            try:
                config_dir = os.path.join(os.path.dirname(__file__), '..', 'config', 'supplier_configs')
                os.makedirs(config_dir, exist_ok=True)
                
                config_file = os.path.join(config_dir, f"{domain}.json")
                with open(config_file, 'w') as f:
                    json.dump(self.loaded_selector_configs[domain], f, indent=2)
                
                log.info(f"Updated selectors configuration saved for {domain}")
                
            except Exception as e:
                log.warning(f"Failed to save updated selectors for {domain}: {e}")
                
        except Exception as e:
            log.error(f"Failed to update selectors config for {domain}: {e}")

    def _get_selectors_for_domain(self, domain_or_url: str) -> Dict[str, Any]:
        """Get selectors for a specific domain with supplier package priority."""
        try:
            # Ensure we are working with a clean domain name
            domain = get_domain_from_url(domain_or_url)
            if not domain:
                log.warning(f"Could not extract a valid domain from: {domain_or_url}")
                return {}

            # Check cache first
            if domain in self.loaded_selector_configs:
                # log.debug(f"Using cached selectors for domain {domain}")
                return self.loaded_selector_configs[domain]

            # PRIORITY 1: Check for generated supplier package
            supplier_id = domain.replace('.', '-').replace('www-', '')
            base_dir = os.path.dirname(os.path.dirname(__file__))
            supplier_ready_path = os.path.join(base_dir, "suppliers", supplier_id, ".supplier_ready")
            supplier_config_path = os.path.join(base_dir, "suppliers", supplier_id, "config", "product_selectors.json")
            
            if os.path.exists(supplier_ready_path) and os.path.exists(supplier_config_path):
                try:
                    # Validate supplier package readiness
                    with open(supplier_ready_path, 'r', encoding='utf-8') as f:
                        ready_data = json.load(f)
                    
                    validation_status = ready_data.get("validation_status", {})
                    if validation_status.get("products_validated", False):
                        # Load validated supplier package selectors
                        with open(supplier_config_path, 'r', encoding='utf-8') as f:
                            supplier_selectors = json.load(f)
                        
                        log.info(f"✅ Loaded VALIDATED supplier package selectors for {domain} from {supplier_config_path}")
                        self.loaded_selector_configs[domain] = supplier_selectors
                        return supplier_selectors
                    else:
                        log.warning(f"⚠️ Supplier package for {domain} exists but not validated: {validation_status}")
                except Exception as e:
                    log.error(f"❌ Error loading supplier package for {domain}: {e}")
            
            # PRIORITY 2: Fallback to config/supplier_configs/ (legacy)
            config = load_supplier_selectors(domain) # Use the utility function
            
            if config:
                log.info(f"📁 Loaded selectors for domain {domain} from legacy config/supplier_configs/")
                self.loaded_selector_configs[domain] = config # Cache it
                # Store full configuration for navigation settings
                self.supplier_config = config
                return config
            else:
                # PRIORITY 3: Direct filesystem fallback
                clean_domain_fs = domain.replace('www.', '')
                
                possible_paths = [
                    os.path.join("config", "supplier_configs", f"{domain}.json"), 
                    os.path.join("config", "supplier_configs", f"{clean_domain_fs}.json"),
                    os.path.join("..", "config", "supplier_configs", f"{domain}.json"),  
                    os.path.join("..", "config", "supplier_configs", f"{clean_domain_fs}.json"),
                    os.path.join(os.path.dirname(__file__), "..", "config", "supplier_configs", f"{domain}.json"),
                    os.path.join(os.path.dirname(__file__), "..", "config", "supplier_configs", f"{clean_domain_fs}.json")
                ]
                
                for config_path in possible_paths:
                    if os.path.exists(config_path):
                        with open(config_path, 'r') as f:
                            loaded_config = json.load(f)
                            log.info(f"📂 Loaded selectors for domain {domain} via fallback path: {config_path}")
                            self.loaded_selector_configs[domain] = loaded_config # Cache it
                            # Store full configuration for navigation settings
                            self.supplier_config = loaded_config
                            return loaded_config
            
            log.warning(f"❌ No selector configuration found for domain {domain} in supplier packages or config files")
            self.loaded_selector_configs[domain] = {} # Cache empty result to avoid re-attempts
            return {}
        except Exception as e:
            log.error(f"Error loading selectors for domain derived from {domain_or_url}: {e}")
            # Try to cache an empty dict for the original input to prevent repeated errors if domain extraction failed
            if domain: # if domain was successfully extracted
                 self.loaded_selector_configs[domain] = {}
            return {}

    def extract_product_elements(self, html_content: str, context_url: str) -> List[BeautifulSoup]:
        """Extract product elements from HTML using BeautifulSoup and site-specific selectors."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            selectors = self._get_selectors_for_domain(urlparse(context_url).netloc)
            
            # Get product item selector from field_mappings
            product_item_selector = selectors.get("field_mappings", {}).get("product_item", [])
            if not product_item_selector:
                return []
                
            # Try each selector in the list
            for selector in product_item_selector:
                elements = soup.select(selector)
                if elements:
                    return elements
                    
            return []
        except Exception as e:
            log.error(f"Error extracting product elements: {e}")
            return []

    def _extract_with_selector(self, element_soup: BeautifulSoup, selector_configs: List[Union[str, Dict[str, Any]]], default_value: Optional[str] = None) -> Optional[str]:
        """
        Enhanced selector extraction with flexible configuration support.
        
        Args:
            element_soup: BeautifulSoup element to search within
            selector_configs: List of selector configurations. Each can be:
                - str: Simple CSS selector for text extraction
                - dict: Configuration with:
                    - "selector": CSS selector (required)
                    - "attribute": HTML attribute to extract (optional)
                    - "processing_regex": Regex pattern to process value (optional)
                    - "regex_group": Regex group to return (optional, default 1)
            default_value: Value to return if no extraction succeeds
            
        Returns:
            Extracted value or default_value if nothing found
        """
        if not isinstance(selector_configs, list):
            selector_configs = [selector_configs]
        
        for config in selector_configs:
            try:
                # Handle string selector (backward compatibility)
                if isinstance(config, str):
                    target = element_soup.select_one(config)
                    if target:
                        text_content = target.get_text(separator=" ", strip=True)
                        if text_content:
                            return text_content
                            
                # Handle dictionary configuration
                elif isinstance(config, dict):
                    selector = config.get('selector')
                    if not selector:
                        log.warning("Selector configuration missing 'selector' key")
                        continue
                        
                    target = element_soup.select_one(selector)
                    if not target:
                        continue
                        
                    # Extract based on attribute or text
                    attribute = config.get('attribute')
                    if attribute:
                        value = target.get(attribute)
                    else:
                        value = target.get_text(separator=" ", strip=True)
                        
                    if not value:
                        continue
                        
                    # Apply regex processing if specified
                    processing_regex = config.get('processing_regex')
                    if processing_regex:
                        regex_group = config.get('regex_group', 1)
                        match = re.search(processing_regex, str(value))
                        if match:
                            try:
                                if regex_group == 0:
                                    return match.group(0)
                                else:
                                    return match.group(regex_group)
                            except IndexError:
                                log.warning(f"Regex group {regex_group} not found in match")
                                continue
                    else:
                        return str(value).strip()
                        
            except Exception as e:
                log.debug(f"Error with selector config '{config}': {e}")
                continue
                
        return default_value

    async def _ai_extract_field_from_html_element(self, element_html: str, field_description: str, context_url: str) -> Optional[str]:
        """
        Call AI model to extract a specific field from a product HTML element.
        """
        if not self.ai_client:
            log.warning(f"AI client not available. Cannot extract '{field_description}' from HTML element for {context_url}.")
            return None

        try:
            max_html_len = 4000 # Reduced to be safer with token limits and typical product snippets
            truncated_html = element_html[:max_html_len]
            if len(element_html) > max_html_len:
                truncated_html += "... [truncated]"

            prompt = (
                f"You are an expert web data extractor. From the following HTML snippet of a product item on the webpage {context_url}, "
                f"extract the '{field_description}'. Provide only the extracted value with no explanation or commentary. "
                f"If not found or not applicable, respond with 'Not found'.\n\n"
                f"HTML Snippet:\n{truncated_html}"
            )

            # Check if the model supports temperature parameter
            api_params = {
                "model": self.openai_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150
            }
            
            # Only add temperature for models that support it
            if "search-preview" not in self.openai_model.lower():
                api_params["temperature"] = 0.0
            
            response = await asyncio.to_thread(
                self.ai_client.chat.completions.create,
                **api_params
            )
            extracted_value = response.choices[0].message.content.strip()

            if extracted_value.lower() in ["not found", "none", "n/a", "", "null", "not applicable"]:
                log.info(f"AI indicated '{field_description}' not found in HTML for {context_url}.")
                return None

            log.info(f"AI extracted '{field_description}' for {context_url}: '{extracted_value[:60].replace(chr(10), ' ')}...'")
            return extracted_value

        except Exception as e:
            log.error(f"AI HTML element extraction for '{field_description}' on {context_url} failed: {e}", exc_info=True)
            return None

    async def _ai_discover_selectors(self, html_content: str, context_url: str) -> Dict[str, Any]:
        """
        Use AI to discover CSS selectors for product elements on a new supplier website.
        """
        if not self.ai_client:
            log.warning(f"AI client not available. Cannot discover selectors for {context_url}.")
            return {}

        try:
            # Truncate HTML for AI analysis (keep reasonable size)
            max_html_len = 8000
            truncated_html = html_content[:max_html_len]
            if len(html_content) > max_html_len:
                truncated_html += "... [truncated]"

            prompt = f"""You are an expert CSS selector discovery tool. Analyze this HTML from {context_url} and identify CSS selectors for e-commerce product elements.

WEBSITE URL: {context_url}

Return ONLY a JSON object with these exact keys (no additional text):
{{
  "product_item": ["selector1", "selector2"],
  "title": ["selector1", "selector2"], 
  "price": ["selector1", "selector2"],
  "price_login_required": ["selector1", "selector2"],
  "url": ["selector1", "selector2"],
  "image": ["selector1", "selector2"],
  "ean": ["selector1", "selector2"],
  "barcode": ["selector1", "selector2"],
  "product_code": ["selector1", "selector2"],
  "sku": ["selector1", "selector2"]
}}

CRITICAL REQUIREMENTS FOR POUNDWHOLESALE.CO.UK:
1. PRICES: 
   - CONFIRMED WORKING: meta[property="product:price:amount"] (contains actual price like "0.59")
   - LOGIN REQUIRED: a.btn.customer-login-link.login-btn (contains "Log in to view prices")
2. EAN/BARCODE: 
   - CONFIRMED PATTERN: Search HTML content for 13-digit barcodes like 5060563215438
   - Look in script tags, meta tags, and hidden data attributes
3. PRODUCT CODES: Any alphanumeric identifiers, model numbers, SKUs

PROVEN WORKING SELECTORS (USE THESE):
- Price: meta[property="product:price:amount"]
- Currency: meta[property="product:price:currency"]  
- Login Required: a.btn.customer-login-link.login-btn
- EAN Pattern: Search raw HTML for /[0-9]{13}/ or /[0-9]{12}/ patterns

IMPORTANT RULES:
1. ALWAYS include the confirmed working selectors above
2. For EAN: Focus on finding ANY numeric identifiers 8-14 digits long
3. For price: Include BOTH meta tag selectors AND login message selectors
4. Look in script tags, meta tags, and structured data for EAN codes
5. Provide the proven selectors plus additional fallback options

HTML CONTENT:
{truncated_html}"""

            # Check if the model supports temperature parameter
            api_params = {
                "model": self.openai_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800
            }
            
            # Only add temperature for models that support it
            if "search-preview" not in self.openai_model.lower():
                api_params["temperature"] = 0.1
            
            response = await asyncio.to_thread(
                self.ai_client.chat.completions.create,
                **api_params
            )
            
            ai_response = response.choices[0].message.content.strip()
            log.info(f"AI selector discovery response for {context_url}: {ai_response[:200]}...")
            
            # Try to parse JSON response (handle markdown code blocks)
            try:
                import json
                import re
                
                # Extract JSON from markdown code blocks if present
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1)
                else:
                    json_content = ai_response
                
                selectors = json.loads(json_content)
                log.info(f"Successfully discovered selectors for {context_url}: {selectors}")
                return selectors
            except json.JSONDecodeError as e:
                log.error(f"Failed to parse AI selector response as JSON for {context_url}: {e}")
                log.error(f"Raw AI response: {ai_response}")
                return {}

        except Exception as e:
            log.error(f"AI selector discovery failed for {context_url}: {e}", exc_info=True)
            return {}

    async def auto_configure_supplier(self, supplier_url: str, save_config: bool = True) -> Dict[str, Any]:
        """
        Automatically configure a new supplier by discovering selectors with AI.
        """
        try:
            log.info(f"Auto-configuring supplier for {supplier_url}")
            
            # Get homepage content
            html_content = await self.get_page_content(supplier_url)
            if not html_content:
                log.error(f"Failed to fetch content from {supplier_url}")
                return {}

            # Use AI to discover selectors
            discovered_selectors = await self._ai_discover_selectors(html_content, supplier_url)
            if not discovered_selectors:
                log.error(f"Failed to discover selectors for {supplier_url}")
                return {}

            # Create configuration structure
            domain = get_domain_from_url(supplier_url)
            config = {
                "supplier_id": domain.replace('.', '-'),
                "supplier_name": domain.title(),
                "base_url": supplier_url,
                "field_mappings": discovered_selectors,
                "pagination": {
                    "pattern": "?page={page_num}",
                    "next_button_selector": ["a.next", ".pagination .next a", "a[rel='next']"]
                },
                "auto_discovered": True,
                "discovery_timestamp": datetime.now().isoformat(),
                "success": True
            }

            # Save configuration if requested
            if save_config:
                try:
                    # Import save function with fallback
                    try:
                        from config.supplier_config_loader import save_supplier_selectors
                    except ImportError:
                        import sys
                        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'config'))
                        from supplier_config_loader import save_supplier_selectors
                    
                    success = save_supplier_selectors(domain, config)
                    if success:
                        log.info(f"Saved auto-discovered configuration for {domain}")
                    else:
                        log.warning(f"Failed to save configuration for {domain}")
                except Exception as e:
                    log.error(f"Error saving configuration for {domain}: {e}")

            return config

        except Exception as e:
            log.error(f"Auto-configuration failed for {supplier_url}: {e}", exc_info=True)
            return {}

    def _prepare_selector_configs(self, raw_configs: List[Union[str, Dict[str, Any]]], default_attribute: Optional[str] = None) -> List[Union[str, Dict[str, Any]]]:
        """Helper to process raw selector configs, adding default attributes if needed."""
        processed_configs = []
        if not isinstance(raw_configs, list): # Ensure it's a list
            raw_configs = [raw_configs]

        for config in raw_configs:
            if isinstance(config, str):
                if default_attribute:
                    processed_configs.append({"selector": config, "attribute": default_attribute})
                else:
                    processed_configs.append(config) # Assumes text extraction
            elif isinstance(config, dict) and "selector" in config:
                if default_attribute and "attribute" not in config:
                    processed_configs.append({**config, "attribute": default_attribute})
                else:
                    processed_configs.append(config)
            # else: log an error or skip invalid config? For now, skip.
        return processed_configs


    async def extract_title(self, element: BeautifulSoup, element_html: str, context_url: str) -> Optional[str]:
        """Extract product title using configured selectors."""
        try:
            selectors = self._get_selectors_for_domain(urlparse(context_url).netloc)
            title_selectors = selectors.get("field_mappings", {}).get("title", [])
            
            for selector in title_selectors:
                title_element = element.select_one(selector)
                if title_element and title_element.text.strip():
                    return title_element.text.strip()
                    
            return None
        except Exception as e:
            log.error(f"Error extracting title: {e}")
            return None

    async def extract_price(self, element: BeautifulSoup, element_html: str, context_url: str) -> Optional[float]:
        """Extract product price using configured selectors."""
        try:
            selectors = self._get_selectors_for_domain(urlparse(context_url).netloc)
            price_selectors = selectors.get("field_mappings", {}).get("price", [])
            
            for selector in price_selectors:
                price_element = element.select_one(selector)
                if price_element:
                    price_text = price_element.text.strip()
                    parsed_price = self._parse_price(price_text)
                    if parsed_price is not None:
                        return parsed_price
            return None
        except Exception as e:
            log.error(f"Error extracting price: {e}")
            return None

    async def extract_url(self, element: BeautifulSoup, element_html: str, context_url: str, base_url: str) -> Optional[str]:
        """Extract product URL using configured selectors."""
        try:
            selectors = self._get_selectors_for_domain(urlparse(context_url).netloc)
            url_selectors = selectors.get("field_mappings", {}).get("url", [])
            
            for selector in url_selectors:
                url_element = element.select_one(selector)
                if url_element:
                    href = url_element.get('href')
                    if href:
                        return self._ensure_absolute_url(href, base_url)
            return None
        except Exception as e:
            log.error(f"Error extracting URL: {e}")
            return None

    def _ensure_absolute_url(self, url: str, base_url: str) -> str:
        if not url or not isinstance(url, str): return url

        url = url.strip()
        if not url: return url

        if url.startswith(('data:', 'javascript:', 'mailto:', 'tel:')): return url
        if url.startswith('//'): return 'https:' + url # Protocol-relative
        if url.startswith(('http://', 'https://')): return url # Already absolute

        try:
            parsed_base = urlparse(base_url)
            # Ensure base_url has a scheme for urljoin to work correctly
            base_url_for_join = base_url
            if not parsed_base.scheme:
                # If base_url is like "domain.com/path", prepend https://
                if not base_url.startswith("//") and "." in base_url.split("/")[0]:
                     base_url_for_join = "https://" + base_url
                # If base_url is like "//domain.com/path", prepend https:
                elif base_url.startswith("//"):
                     base_url_for_join = "https:" + base_url
                # Else, it might be a local file path or malformed, urljoin might handle or fail

            return urljoin(base_url_for_join, url)

        except Exception as e:
            log.warning(f"Error in urljoin for URL '{url}' with base '{base_url}': {e}. Falling back to basic join.")
            # Basic fallback if urljoin fails
            if url.startswith('/'):
                try:
                    scheme, netloc, _, _, _, _ = urlparse(base_url)
                    if scheme and netloc:
                        return f"{scheme}://{netloc}{url}"
                except: pass
            return url # Return original url if all else fails

    async def extract_image(self, element: BeautifulSoup, element_html: str, context_url: str, base_url: str) -> Optional[str]:
        """Extract product image using configured selectors."""
        try:
            selectors = self._get_selectors_for_domain(urlparse(context_url).netloc)
            image_selectors = selectors.get("field_mappings", {}).get("image", [])
            
            for selector in image_selectors:
                img_element = element.select_one(selector)
                if img_element:
                    # Try common image attributes
                    for attr in ['src', 'data-src', 'data-original']:
                        img_src = img_element.get(attr)
                        if img_src:
                            return self._ensure_absolute_url(img_src, base_url)
            return None
        except Exception as e:
            log.error(f"Error extracting image: {e}")
            return None

    async def extract_identifier(self, element_soup: BeautifulSoup, element_html: str, context_url: str) -> Optional[str]:
        config = self._get_selectors_for_domain(context_url)

        if "clearance-king.co.uk" in context_url.lower(): # Specific handling for Clearance King
            page_text_content = element_soup.get_text(" ", strip=True)
            ck_barcode_match = re.search(r'Barcode\s*\*\*\s*(\d{8,14})\s*\*\*', page_text_content)
            if ck_barcode_match:
                barcode_val = ck_barcode_match.group(1)
                if len(barcode_val) in [8, 12, 13, 14]:
                    log.info(f"Found Clearance King specific barcode pattern: '{barcode_val}' from {context_url}")
                    return barcode_val
            ck_text_match = re.search(r'(?:EAN|Barcode|UPC|GTIN)[\s:]*(\d{8,14})(?:\b|$)', page_text_content, re.IGNORECASE)
            if ck_text_match:
                barcode_val = ck_text_match.group(1)
                if len(barcode_val) in [8, 12, 13, 14]:
                    log.info(f"Found Clearance King text barcode: '{barcode_val}' from {context_url}")
                    return barcode_val

        identifier_keys = [
            "identifier_selectors_product_page", "ean_selector_product_page",
            "barcode_selector_product_page", "upc_selector_product_page",
            "gtin_selector_product_page", "sku_selector_product_page",
            "mpn_selector_product_page", "product_code_selector_product_page"
        ]
        all_identifier_configs: List[Union[str, Dict[str, Any]]] = []
        for key in identifier_keys:
            configs = config.get(key, [])
            if isinstance(configs, (str, dict)): configs = [configs] # Ensure list
            all_identifier_configs.extend(configs)

        # Add generic fallback selectors
        generic_selectors = [
            "[itemprop='gtin13']", "[itemprop='gtin12']", "[itemprop='gtin8']", "[itemprop='gtin']",
            "[itemprop='ean']", "[itemprop='upc']", "[itemprop='productID']", "[itemprop='sku']", "[itemprop='mpn']",
            "dd.ean", "span.ean", ".product-ean", "div[class*='ean']",
            "dd.upc", "span.upc", ".product-upc", "div[class*='upc']",
            "dd.sku", "span.sku", ".product-sku", "div[class*='sku']",
            "dd.mpn", "span.mpn", ".product-mpn", "div[class*='mpn']",
            "div[class*='barcode']", "span[class*='barcode']",
            {"selector": "dt:contains('EAN') + dd", "processing_regex": r"(\S+)"}, # Key-value pairs
            {"selector": "dt:contains('UPC') + dd", "processing_regex": r"(\S+)"},
            {"selector": "dt:contains('SKU') + dd", "processing_regex": r"(\S+)"},
            {"selector": "dt:contains('MPN') + dd", "processing_regex": r"(\S+)"},
            {"selector": "dt:contains('Barcode') + dd", "processing_regex": r"(\S+)"},
            {"selector": "dt:contains('Product Code') + dd", "processing_regex": r"(\S+)"},
        ]
        all_identifier_configs.extend(generic_selectors)
        
        if all_identifier_configs:
            extracted_code_str = self._extract_with_selector(element_soup, all_identifier_configs)
            if extracted_code_str:
                # Attempt to clean for numeric barcodes first
                cleaned_numeric = re.sub(r'[^0-9]', '', extracted_code_str)
                if cleaned_numeric and len(cleaned_numeric) in [8, 12, 13, 14]: # Standard EAN/UPC lengths
                    log.info(f"Valid numeric identifier (EAN/UPC format) '{cleaned_numeric}' extracted using selectors from {context_url}.")
                    return cleaned_numeric

                # If not a standard numeric barcode, consider it as SKU/MPN/Product Code or other identifier
                # Basic cleaning for alphanumeric codes: remove common prefixes/suffixes but preserve structure
                cleaned_alphanumeric = re.sub(r'^(?:SKU|MPN|Code|ID|Item No\.?|Product Code|P/N|Part No\.?)[\s:]*', '', extracted_code_str, flags=re.IGNORECASE).strip()
                
                # Avoid overly aggressive compaction for alphanumeric, allow some internal hyphens/spaces if meaningful
                # Example: ABC-123 or XYZ 456 should be preserved if not clearly a barcode attempt
                
                # If it's purely numeric after this cleaning, but not a valid barcode length, it's likely an internal ID, not an EAN/UPC.
                # We should be cautious about returning this if an EAN/UPC was expected.
                # However, if the selector was for SKU/MPN, this might be valid.
                # For now, if it becomes purely numeric and not barcode length, we won't treat it as a primary EAN for Amazon.
                # It can still be stored as 'identifier' for the supplier product.
                is_potentially_internal_numeric_id = False
                temp_compacted_for_check = re.sub(r'[\s:-]+', '', cleaned_alphanumeric)
                if temp_compacted_for_check.isdigit() and len(temp_compacted_for_check) not in [8, 12, 13, 14]:
                    is_potentially_internal_numeric_id = True
                    # log.debug(f"Identifier '{cleaned_alphanumeric}' from {context_url} is numeric but not standard EAN/UPC length.")

                # Return if it seems like a valid alphanumeric SKU/MPN (not just a short, non-barcode number)
                if cleaned_alphanumeric and 3 < len(cleaned_alphanumeric) < 50 and not is_potentially_internal_numeric_id:
                    if len(cleaned_alphanumeric.split()) < 4 and cleaned_alphanumeric.lower() not in ['n/a', 'none', 'unknown', 'not available']:
                        log.info(f"Potential alphanumeric identifier (SKU/MPN) '{cleaned_alphanumeric}' (from '{extracted_code_str}') extracted from {context_url}.")
                        return cleaned_alphanumeric
                elif cleaned_alphanumeric and is_potentially_internal_numeric_id:
                    # If it was an internal numeric ID, and that's what we got, return it. Passive workflow can decide if it tries it as EAN.
                    log.info(f"Potential internal numeric ID '{cleaned_alphanumeric}' (from '{extracted_code_str}') extracted from {context_url}.")
                    return cleaned_alphanumeric
                # else: log.debug(f"Discarding '{cleaned_alphanumeric}' from '{extracted_code_str}' as it doesn't meet SKU/MPN criteria or is a non-barcode numeric string.")
        
        log.warning(f"Failed to extract EAN/Barcode/Identifier with selectors from {context_url}. Attempting AI fallback.")
        ai_identifier_str = await self._ai_extract_field_from_html_element(
            element_html,
            "product's EAN (e.g., 13-digit), UPC (e.g., 12-digit), GTIN, SKU, MPN, or other primary Product Code. Provide only the identifier value.",
            context_url
        )
        
        if ai_identifier_str:
            cleaned_ai_identifier = re.sub(r'^(?:SKU|MPN|Code|ID|Item No\.?|Product Code)[\s:]*', '', ai_identifier_str, flags=re.IGNORECASE).strip()
            cleaned_ai_identifier_compact = re.sub(r'[\s:-]+', '', cleaned_ai_identifier)

            if cleaned_ai_identifier_compact.isdigit() and len(cleaned_ai_identifier_compact) in [8, 12, 13, 14]:
                log.info(f"AI extracted valid numeric identifier '{cleaned_ai_identifier_compact}' from {context_url}.")
                return cleaned_ai_identifier_compact
            elif 3 < len(cleaned_ai_identifier_compact) < 50 and cleaned_ai_identifier_compact.lower() not in ['n/a', 'none', 'unknown', 'not available']:
                 log.info(f"AI extracted potential alphanumeric identifier '{cleaned_ai_identifier_compact}' (from '{ai_identifier_str}') from {context_url}.")
                 return cleaned_ai_identifier_compact # Return the more readable version if it's alphanumeric
            else:
                log.info(f"AI extraction for identifier from {context_url} ('{ai_identifier_str}') did not yield a usable or standard format code.")
        
        return None

    def get_next_page_url(self, current_url: str, current_page_soup: BeautifulSoup, current_page_num: int = 1) -> Optional[str]:
        selectors_config = self._get_selectors_for_domain(current_url)
        pagination_config = selectors_config.get("pagination", {})

        # Method 1: Specific next button selector from config
        next_button_config_raw = pagination_config.get("next_button_selector")
        if next_button_config_raw:
            next_button_configs = self._prepare_selector_configs(
                next_button_config_raw if isinstance(next_button_config_raw, list) else [next_button_config_raw],
                default_attribute="href"
            )
            next_url_path = self._extract_with_selector(current_page_soup, next_button_configs)
            if next_url_path:
                abs_url = self._ensure_absolute_url(next_url_path, current_url)
                if abs_url and abs_url != current_url and urlparse(abs_url).netloc == urlparse(current_url).netloc:
                    log.info(f"Found next page URL via specific config selector: {abs_url}")
                    return abs_url

        # Method 2: Pattern-based pagination from config
        pattern_str = pagination_config.get("pattern")
        if pattern_str and "{page_num}" in pattern_str:
            next_page_url_from_pattern = self._apply_pagination_pattern(current_url, pattern_str, current_page_num + 1)
            if next_page_url_from_pattern and next_page_url_from_pattern != current_url:
                log.info(f"Found next page URL via pattern string: {next_page_url_from_pattern}")
                return next_page_url_from_pattern
        
        # Method 3: List of patterns from config
        patterns_list = pagination_config.get("patterns", []) # Expects a list of pattern strings
        if isinstance(patterns_list, list):
            for pat_str in patterns_list:
                if isinstance(pat_str, str) and "{page_num}" in pat_str:
                    next_page_url_from_list = self._apply_pagination_pattern(current_url, pat_str, current_page_num + 1)
                    if next_page_url_from_list and next_page_url_from_list != current_url:
                        log.info(f"Found next page URL via patterns list item: {next_page_url_from_list}")
                        return next_page_url_from_list

        # Method 4: Common generic next button selectors
        generic_next_button_selectors = [
            {"selector": "a[rel='next']", "attribute": "href"},
            {"selector": ".next a", "attribute": "href"},
            {"selector": "a.next", "attribute": "href"},
            {"selector": ".pagination .next a", "attribute": "href"},
            {"selector": "li.next a", "attribute": "href"},
            {"selector": ".pager .next a", "attribute": "href"},
            {"selector": "a[aria-label*='Next']", "attribute": "href"}, # For accessibility-labeled links
            {"selector": "a.page-link-next", "attribute": "href"},
            {"selector": "link[rel='next']", "attribute": "href"} # Check <link> tags in <head>
        ]
        next_url_path_generic = self._extract_with_selector(current_page_soup, generic_next_button_selectors)
        if next_url_path_generic:
            abs_url = self._ensure_absolute_url(next_url_path_generic, current_url)
            if abs_url and abs_url != current_url and urlparse(abs_url).netloc == urlparse(current_url).netloc:
                log.info(f"Found next page URL via generic selector: {abs_url}")
                return abs_url

        # Method 5: Infer pagination from URL structure (last resort)
        inferred_next_page = self._infer_next_page_url(current_url, current_page_num)
        if inferred_next_page and inferred_next_page != current_url:
            log.info(f"Inferred next page URL: {inferred_next_page}")
            return inferred_next_page

        log.info(f"Could not determine next page URL for {current_url} (current page: {current_page_num})")
        return None

    def _apply_pagination_pattern(self, current_url: str, pattern: str, next_page_num: int) -> Optional[str]:
        try:
            if "{page_num}" not in pattern: return None

            if pattern.startswith(("http://", "https://")): # Absolute URL pattern
                return pattern.replace("{page_num}", str(next_page_num))

            parsed_current = urlparse(current_url)
            
            # Query parameter pattern (e.g., "?page={page_num}" or "page={page_num}" or "&page={page_num}")
            if pattern.startswith("?") or (pattern.count("=") == 1 and "{page_num}" in pattern.split("=")[1]) or pattern.startswith("&"):
                param_name_val = pattern.lstrip("?&").split("=")[0] # e.g. "page" from "page={page_num}"
                
                query_dict = {}
                if parsed_current.query:
                    for p_item in parsed_current.query.split("&"):
                        if "=" in p_item: k,v = p_item.split("=",1); query_dict[k] = v
                        elif p_item: query_dict[p_item] = "" # Handle params without values if any

                query_dict[param_name_val] = str(next_page_num)
                new_query_string = "&".join(f"{k}={v}" for k,v in query_dict.items() if v is not None) # Filter out None values if any param was removed
                return parsed_current._replace(query=new_query_string).geturl()

            # Path-based patterns
            # Using urljoin is generally safer for relative path manipulations
            base_for_join = current_url
            # If current_url looks like a file, and pattern is not absolute, join from parent dir
            if not current_url.endswith('/') and '.' in parsed_current.path.split('/')[-1] and not pattern.startswith('/'):
                 base_for_join = current_url.rsplit('/', 1)[0] + '/'
            
            # If pattern is root-relative (starts with / but not //)
            if pattern.startswith('/') and not pattern.startswith('//'):
                 return f"{parsed_current.scheme}://{parsed_current.netloc}{pattern.replace('{page_num}', str(next_page_num))}"

            return urljoin(base_for_join, pattern.replace("{page_num}", str(next_page_num)))

        except Exception as e:
            log.warning(f"Error applying pagination pattern '{pattern}' to '{current_url}': {e}", exc_info=True)
        return None

    def _infer_next_page_url(self, current_url: str, current_page_num: int) -> Optional[str]:
        parsed_url = urlparse(current_url)
        path_segments = [seg for seg in parsed_url.path.split('/') if seg]
        query_params = {}
        if parsed_url.query:
            for item in parsed_url.query.split('&'):
                if '=' in item: key,val = item.split('=',1); query_params[key] = val

        next_page_str = str(current_page_num + 1)

        # Check query parameters
        for key, val in query_params.items():
            if val == str(current_page_num) and key.lower() in ["page", "p", "pg", "pagenum", "page_number", "startindex", "offset"]:
                query_params[key] = next_page_str
                new_query = "&".join(f"{k}={v}" for k,v in query_params.items())
                return parsed_url._replace(query=new_query).geturl()

        # Check path segments
        for i, segment in enumerate(path_segments):
            if segment == str(current_page_num):
                new_segments = path_segments[:]
                new_segments[i] = next_page_str
                new_path = "/" + "/".join(new_segments)
                if parsed_url.path.endswith('/'): new_path += '/'
                return parsed_url._replace(path=new_path).geturl()
            # Try common prefixes like /page/2 or /p-2
            for prefix in ["page", "p", "pg"]:
                if segment.lower().startswith(prefix) and segment.lower().replace(prefix, "").strip("-/") == str(current_page_num):
                    new_segments = path_segments[:]
                    new_segments[i] = prefix + next_page_str # Reconstruct with prefix
                    new_path = "/" + "/".join(new_segments)
                    if parsed_url.path.endswith('/'): new_path += '/'
                    return parsed_url._replace(path=new_path).geturl()
        
        # If current_page_num is 1, try appending common patterns
        if current_page_num == 1:
            base_path = parsed_url.path.rstrip('/')
            common_appends = [
                f"{base_path}/page/{next_page_str}",
                f"{base_path}/p/{next_page_str}",
            ]
            common_query_appends = [
                f"page={next_page_str}",
                f"p={next_page_str}"
            ]
            for append_path_try in common_appends:
                # Basic check: don't append if base_path already looks like a product detail page
                if not any(kw in base_path.lower() for kw in ['.html', '.htm', 'product/', 'item/']):
                    new_url_try = parsed_url._replace(path=append_path_try, query="").geturl()
                    # Here, one might add a check if this URL is valid before returning
                    # For now, we assume it might be.
                    # return new_url_try # This can be too aggressive.
            
            for query_append_try in common_query_appends:
                new_query_str = f"{parsed_url.query}&{query_append_try}" if parsed_url.query else query_append_try
                # return parsed_url._replace(query=new_query_str).geturl() # Also can be too aggressive.

        return None

    def _parse_price(self, price_text: str) -> Optional[float]:
        if not price_text or not isinstance(price_text, str): return None
        
        cleaned_text = price_text
        # Remove common prefixes/suffixes and currency symbols
        prefixes = r'^(?:sale price|on sale|special|now only|price from|approx\.|our price|your price|was|rrp|msrp|ex\s*vat|inc\s*vat|total)[\s:CHF.-]*'
        suffixes = r'[\s:CHF.-]*(?:only|each|per item|ex\s*vat|inc\s*vat|total)$'
        currency_symbols = r'[£$€¥₹]|(?:GBP|USD|EUR|CAD|AUD|JPY|INR|SEK|PLN|CHF)\s*'
        
        cleaned_text = re.sub(prefixes, '', cleaned_text, flags=re.IGNORECASE).strip()
        cleaned_text = re.sub(suffixes, '', cleaned_text, flags=re.IGNORECASE).strip()
        cleaned_text = re.sub(currency_symbols, '', cleaned_text, flags=re.IGNORECASE).strip()

        # Regex to find numbers with optional decimal and thousands separators
        # Handles: 1,234.56 | 1.234,56 | 1234.56 | 1234,56 | 1 234.56 | 1 234,56 | 1'234.56
        # It will take the first valid-looking number sequence.
        match = re.search(r'(\d{1,3}(?:[.,\s\']\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)', cleaned_text)
        
        if match:
            price_str = match.group(1)
            price_str = price_str.replace(' ', '').replace("'", "") # Remove spaces and apostrophes if used as thousand separators
            
            if ',' in price_str and '.' in price_str:
                if price_str.rfind(',') > price_str.rfind('.'): # Comma is decimal: "1.234,56"
                    price_str = price_str.replace('.', '').replace(',', '.')
                else: # Dot is decimal: "1,234.56"
                    price_str = price_str.replace(',', '')
            elif ',' in price_str: # Only comma present
                # If last comma is followed by 1 or 2 digits, assume it's decimal (e.g., "1234,56")
                # Otherwise, assume it's a thousands separator (e.g., "1,234")
                if re.match(r'^\d+,\d{1,2}$', price_str.split()[-1]):
                     price_str = price_str.replace(',', '.')
                else: # Assume it's thousands separator
                     price_str = price_str.replace(',', '')
            
            try:
                price_float = float(price_str)
                # Basic sanity check for price range (e.g., not excessively large or small)
                if 0.001 < price_float < 5000000: # Adjusted upper limit
                    return round(price_float, 2)
                else:
                    log.debug(f"Parsed price {price_float} from '{price_text}' is out of typical range.")
            except ValueError:
                log.debug(f"ValueError converting final price string '{price_str}' to float from '{price_text}'.")
        
        log.warning(f"Could not parse valid price from: '{price_text}' (cleaned: '{cleaned_text}')")
        return None

    async def get_homepage_categories(self, base_url: str) -> List[str]:
        try:
            # Check if predefined categories are configured
            if hasattr(self, 'supplier_config') and self.supplier_config:
                nav_config = self.supplier_config.get('navigation_configuration', {})
                if nav_config.get('use_predefined_categories') and nav_config.get('predefined_categories'):
                    log.info(f"Using predefined categories for {base_url}")
                    predefined_categories = nav_config['predefined_categories']
                    category_urls = [cat['url'] for cat in predefined_categories]
                    log.info(f"Found {len(category_urls)} predefined category URLs:")
                    for i, cat in enumerate(predefined_categories):
                        log.info(f"  {i+1}. {cat['name']}: {cat['url']}")
                    return category_urls
            
            log.info(f"Extracting homepage categories from {base_url}")
            html_content = await self.get_page_content(base_url)
            if not html_content: return []

            soup = BeautifulSoup(html_content, 'html.parser')
            category_urls = set()

            # Comprehensive selectors for navigation elements
            # Prioritize the most effective selectors first
            nav_selectors = [
                '.navigation ul li a',  # Primary navigation - most effective for clearance-king
                '.navigation .level0 a',  # Magento-style navigation
                '.nav-sections .level0 a',  # Alternative Magento navigation
                'nav ul li a',  # Generic navigation
                '.navigation a[href]', '.nav a[href]', '.menu a[href]',
                '.main-menu a[href]', '.primary-menu a[href]', 'header a[href]',
                '.header a[href]', '.category-menu a[href]', '.categories a[href]',
                '#mainNav a[href]', '#main-navigation a[href]', 'ul.navbar-nav a[href]',
                'div.sitemap a[href]', 'footer nav a[href]' # Include sitemap/footer links
            ]

            for selector in nav_selectors:
                try:
                    links = soup.select(selector)
                    for link in links:
                        href = link.get('href')
                        if href:
                            absolute_url = self._ensure_absolute_url(href, base_url)
                            if self._looks_like_category_url(absolute_url, base_url):
                                category_urls.add(absolute_url)
                except Exception as e:
                    log.debug(f"Error with navigation selector '{selector}' on {base_url}: {e}")

            unique_urls = list(category_urls)
            log.info(f"Found {len(unique_urls)} unique potential category URLs from homepage of {base_url}")
            return unique_urls[:75] # Limit to a reasonable number, e.g., 75
        except Exception as e:
            log.error(f"Error extracting homepage categories from {base_url}: {e}", exc_info=True)
            return []

    def _looks_like_category_url(self, url: str, base_url: str) -> bool:
        if not url or not isinstance(url, str): return False

        url_lower = url.lower()
        parsed_url = urlparse(url)
        parsed_base_url = urlparse(base_url)

        # 1. Domain check
        if parsed_url.netloc != parsed_base_url.netloc and not parsed_url.netloc.endswith('.' + parsed_base_url.netloc):
            return False

        # 2. Exclude common file extensions and specific non-category paths
        excluded_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.css', '.js', '.xml', '.txt', '.doc', '.docx', '.xls', '.xlsx', '.svg', '.webp', '.mp4', '.mov']
        if any(url_lower.endswith(ext) for ext in excluded_extensions): return False

        non_category_keywords = [
            '/cart', '/basket', '/checkout', '/payment', '/account', '/login', '/register',
            '/contact', '/about', '/help', '/support', '/faq', '/terms', '/privacy', '/policy',
            '/search', '/wishlist', '/compare', '/blog', '/news', '/article', '/review',
            'mailto:', 'tel:', 'javascript:', '#', 'add_to_cart', 'my_account',
            'customer_service', 'track_order', 'order_status', 'returns_policy', 'shipping_info',
            'sitemap', 'rss_feed', 'brand_list', 'all_brands', 'gift_card', 'voucher_codes',
            'event=', 'attachment_id=', 'replytocom=', 'author/', 'tag/', 'feed/'
        ]
        # Check full URL for non-category keywords
        if any(keyword in url_lower for keyword in non_category_keywords): return False
        # Avoid fragment-only URLs or URLs that are just the base_url again
        if (parsed_url.path in ['', '/'] and not parsed_url.query and parsed_url.fragment) or url == base_url:
            return False


        # 3. Positive category indicators in path or query
        category_keywords = [
            'category', 'categories', 'cat', 'collection', 'dept', 'department', 'section',
            'products', 'items', 'group', 'range', 'shop', 'browse', 'listing', 'gallery',
            'view', 'filter', 'sort', 'type', 'style', 'gender', 'sale', 'offers', 'deals',
            'brand/', 'manufacturer/', 'c/', 'p/', 'pg/', 'page/', 'shopby', 'product-list', 'product_list',
            # Add specific clearance-king category patterns
            'clearance', 'pound', '50p', 'baby', 'kids', 'gifts', 'toys', 'health', 'beauty',
            'household', 'pets', 'smoking', 'stationery', 'crafts', 'mailing', 'supplies',
            'pallet', 'books', 'electrical', 'clothing', 'fashion', 'garden', 'outdoor'
        ]
        path_and_query = (parsed_url.path + '?' + parsed_url.query).lower()
        if any(keyword in path_and_query for keyword in category_keywords): return True

        # 4. Structural checks: Path depth, common patterns
        path_segments = [seg for seg in parsed_url.path.split('/') if seg]
        # Allow slightly deeper paths if they don't end in a file extension
        if 1 <= len(path_segments) <= 5:
            last_segment = path_segments[-1]
            # Avoid paths ending with numbers that look like product IDs if too long, unless it's a common page pattern
            if not (last_segment.isdigit() and len(last_segment) > 6 and not any(p_ind in last_segment for p_ind in ["page","p"])):
                if re.match(r'^[a-z0-9][a-z0-9\-_]*[a-z0-9]$', last_segment, re.IGNORECASE) and len(last_segment) > 1:
                    return True
        
        # 5. Check for common pagination parameters
        if parsed_url.query and any(page_param in parsed_url.query.lower() for page_param in ['page=', 'p=', 'pg=', 'startindex=', 'pagenumber=']):
            return True

        return False

    async def discover_categories(self, base_url: str) -> List[Dict[str, str]]:
        try:
            # Load supplier configuration first to check for predefined categories
            domain = get_domain_from_url(base_url)
            if domain:
                self._get_selectors_for_domain(domain)
            
            category_urls = await self.get_homepage_categories(base_url)
            categories = []
            processed_urls = set()

            for url in category_urls:
                if url in processed_urls: continue
                processed_urls.add(url)

                path = urlparse(url).path.strip('/')
                name_parts = [part for part in path.split('/') if part and not part.isdigit()] # Exclude purely numeric parts
                
                name = ' '.join(name_parts[-2:]) if len(name_parts) >=2 else (name_parts[-1] if name_parts else 'Category')
                name = name.replace('-', ' ').replace('_', ' ').title()
                name = re.sub(r'\s+', ' ', name).strip() # Consolidate whitespace

                if not name or name.lower() == "category" or len(name) < 3: # Try to get a better name from link text
                    # This would require fetching the homepage again or passing soup, skipping for now
                    pass
                if len(name) > 60: name = name[:57] + "..."

                categories.append({"name": name if name else "Unknown Category", "url": url})
            
            log.info(f"Discovered {len(categories)} categories for {base_url}")
            return categories
        except Exception as e:
            log.error(f"Error discovering categories from {base_url}: {e}", exc_info=True)
            return []

    async def discover_subpages(self, category_url: str, max_depth: int = 1, current_depth: int = 0) -> List[str]:
        """
        Discover subpages (subcategories or pagination) for a given category URL, with depth control.
        """
        if current_depth >= max_depth:
            log.info(f"Max depth {max_depth} reached for subpage discovery from {category_url}.")
            return [category_url]

        try:
            log.info(f"Subpage discovery (depth {current_depth+1}) for: {category_url}")
            html_content = await self.get_page_content(category_url)
            if not html_content:
                log.warning(f"Failed to fetch content for {category_url} at depth {current_depth+1}.")
                return [category_url]

            soup = BeautifulSoup(html_content, 'html.parser')
            discovered_urls = {category_url} # Use set for uniqueness
            base_domain = urlparse(category_url).netloc

            # Selectors for subcategories, pagination, and sometimes "view all" type links
            link_selectors = [
                "nav[aria-label*='sub-categories'] a[href]", "ul.subcategory-list a[href]",
                ".pagination a[href]", "ul.pager a[href]", "div.page-numbers a[href]",
                "a[rel='next']", "a.next-page", "a.load-more", "a.view-all-products",
                "aside nav a[href]", ".sidebar-menu a[href]", ".filter-options a[href]" # Broader sidebar/filter links
            ]

            for selector in link_selectors:
                try:
                    links = soup.select(selector)
                    for link in links:
                        href = link.get('href')
                        if href:
                            absolute_url = self._ensure_absolute_url(href, category_url)
                            # Validate: same domain, looks like category/pagination, not an excluded type
                            if urlparse(absolute_url).netloc == base_domain and \
                               self._looks_like_category_url(absolute_url, category_url) and \
                               absolute_url not in discovered_urls: # Avoid re-adding and re-processing
                                discovered_urls.add(absolute_url)
                                log.debug(f"Discovered potential subpage: {absolute_url} via '{selector}' from {category_url}")
                except Exception as e:
                    log.debug(f"Error with selector '{selector}' for subpage discovery on {category_url}: {e}")
            
            # Recursively discover for newly found, valid subcategory-like URLs
            # Pagination links are usually not recursed into unless they are also category links
            final_urls_list = list(discovered_urls)
            # for new_url in list(discovered_urls): # Iterate over a copy
            #     if new_url != category_url and self._looks_like_category_url(new_url, category_url) and not any(pg_kw in new_url for pg_kw in ["page=", "/page/", "?p="]): # Avoid recursing too deep on pagination
            #         final_urls_list.extend(await self.discover_subpages(new_url, max_depth, current_depth + 1))


            unique_final_urls = sorted(list(set(final_urls_list))) # Ensure uniqueness and sort
            log.info(f"Total unique subpages/pagination links found from {category_url} (depth {current_depth+1}): {len(unique_final_urls)}")
            return unique_final_urls[:50] # Limit results per call

        except Exception as e:
            log.error(f"Error discovering subpages for {category_url} at depth {current_depth+1}: {e}", exc_info=True)
            return [category_url] # Return original if error

    async def validate_url_exists(self, url: str) -> bool:
        """
        Quick HEAD request to check if URL exists and returns 200.

        Args:
            url: The URL to validate

        Returns:
            bool: True if URL exists and returns 200, False otherwise
        """
        try:
            session = await self._get_session()
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                return response.status == 200
        except Exception as e:
            log.debug(f"URL validation failed for {url}: {e}")
            return False

    async def filter_valid_urls(self, urls: List[str]) -> List[str]:
        """
        Filter a list of URLs to only include those that exist.

        Args:
            urls: List of URLs to validate

        Returns:
            List[str]: Only URLs that return 200 status
        """
        valid_urls = []
        for url in urls:
            if await self.validate_url_exists(url):
                valid_urls.append(url)
                log.debug(f"URL validated: {url}")
            else:
                log.warning(f"URL validation failed (404 or error): {url}")

        log.info(f"URL validation: {len(valid_urls)}/{len(urls)} URLs are valid")
        return valid_urls

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session for URL validation."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers={'User-Agent': USER_AGENT})
            log.debug("Created new aiohttp session.")
        return self._session

    async def close_session(self):
        """
        Close the Playwright browser and context gracefully.
        """
        if self.context:
            try:
                await self.context.close()
                log.debug("Browser context closed.")
            except Exception as e:
                log.warning(f"Error closing browser context: {e}")
            self.context = None
            
        if self.browser:
            try:
                await self.browser.close()
                log.info("Playwright browser closed.")
                log.debug("Browser isolation maintained: Dedicated instance for supplier scraping closed to ensure clean context and anti-bot detection separation from Amazon debug port 9222")
            except Exception as e:
                log.warning(f"Error closing browser: {e}")
            self.browser = None
            
        if self.playwright:
            try:
                await self.playwright.stop()
                log.debug("Playwright stopped.")
            except Exception as e:
                log.warning(f"Error stopping Playwright: {e}")
            self.playwright = None
            
        # PHASE 1: Close aiohttp session
        if self._session and not self._session.closed:
            try:
                await self._session.close()
                log.debug("Aiohttp session closed.")
            except Exception as e:
                log.warning(f"Error closing aiohttp session: {e}")
            self._session = None

    async def cleanup(self):
        """Alias for close_session for compatibility."""
        await self.close_session()

    def extract_ean(self, product_page_soup, context_url: str = None):
        """Extract EAN from the product page using multiple methods including HTML pattern search."""
        
        # FIRST: Try HTML pattern search for 8-14 digit codes (MOST RELIABLE)
        html_content = str(product_page_soup)
        ean_patterns = [
            r'Product Barcode/ASIN/EAN:\s*([0-9]{8,14})',  # Poundwholesale specific pattern
            r'barcode[^>]*[>:]?\s*([0-9]{8,14})',
            r'ean[^>]*[>:]?\s*([0-9]{8,14})',
            r'gtin[^>]*[>:]?\s*([0-9]{8,14})',
            r'upc[^>]*[>:]?\s*([0-9]{8,14})',
            r'"([0-9]{13})"',  # 13-digit codes in quotes
            r'"([0-9]{12})"',  # 12-digit codes in quotes
            r'>([0-9]{13})<',  # 13-digit codes between tags
            r'>([0-9]{12})<'   # 12-digit codes between tags
        ]
        
        for pattern in ean_patterns:
            matches = re.finditer(pattern, html_content, re.IGNORECASE)
            for match in matches:
                code = match.group(1).strip()
                if len(code) >= 8 and code.isdigit():
                    log.info(f"🎯 EAN found via pattern search: {code}")
                    return code
        
        # SECOND: Try CSS selectors
        selectors = [] # Default to empty list
        if context_url:
            domain = urlparse(context_url).netloc # Parse domain from product page URL
            selectors_config = self._get_selectors_for_domain(domain)
            selectors = selectors_config.get('field_mappings', {}).get('ean', [])
        
        # Enhanced selectors for Poundwholesale specifically
        if not selectors or 'poundwholesale' in (context_url or ''):
            selectors = [
                # Meta tags (most reliable)
                "meta[name='product:ean']",
                "meta[property='product:ean']", 
                "meta[name='product:gtin']",
                "meta[property='product:gtin']",
                # Script and data attributes
                "script[type='application/ld+json']",
                "[data-barcode]",
                "[data-ean]", 
                "[data-gtin]",
                # Clearance King specific
                "div.product-info-main div.ck-product-code-b-code span.ck-b-code-value b",
                "div.product-info-main div.ck-product-code-b-code span.ck-b-code-value",
                "table.additional-attributes-table td[data-th='EAN']",
                "div.product.attribute.sku div.value[itemprop='sku']",
                "div.product.attribute.gtin div.value[itemprop='gtin13']"
            ]
        for selector in selectors:
            if selector:  # Skip empty selectors
                element = product_page_soup.select_one(selector)
                if element:
                    return element.get_text(strip=True)
        return None

    def extract_barcode(self, product_page_soup, context_url: str = None):
        """Extract barcode from the product page using multiple selectors."""
        selectors = [] # Default to empty list
        if context_url:
            domain = urlparse(context_url).netloc # Parse domain from product page URL
            selectors_config = self._get_selectors_for_domain(domain)
            selectors = selectors_config.get('field_mappings', {}).get('barcode', [])
        
        # Fallback to generic selectors if no domain-specific ones are found or context_url is None
        if not selectors:
            selectors = [
                "table.additional-attributes-table td[data-th='Barcode']"
                # Add more generic barcode selectors if needed
            ]
        for selector in selectors:
            if selector:  # Skip empty selectors
                element = product_page_soup.select_one(selector)
                if element:
                    return element.get_text(strip=True)
        return None

    def extract_availability(self, product_page_soup, context_url: str = None):
        """Extract availability status from the product page using multiple selectors."""
        selectors = [] # Default to empty list
        if context_url:
            domain = urlparse(context_url).netloc # Parse domain from product page URL
            selectors_config = self._get_selectors_for_domain(domain)
            selectors = selectors_config.get('field_mappings', {}).get('availability', [])
        
        # Fallback to generic selectors if no domain-specific ones are found or context_url is None
        if not selectors:
            selectors = [
                "meta[property='product:availability']",
                ".stock span",
                ".availability",
                ".product-availability"
            ]
        
        for selector in selectors:
            if selector:  # Skip empty selectors
                element = product_page_soup.select_one(selector)
                if element:
                    # Check if it's a meta tag
                    if selector.startswith("meta"):
                        return element.get('content', '').strip()
                    else:
                        return element.get_text(strip=True)
        return None

    def extract_out_of_stock_status(self, product_page_soup, context_url: str = None):
        """Extract out-of-stock status from the product page using multiple selectors."""
        selectors = [] # Default to empty list
        if context_url:
            domain = urlparse(context_url).netloc # Parse domain from product page URL
            selectors_config = self._get_selectors_for_domain(domain)
            selectors = selectors_config.get('field_mappings', {}).get('out_of_stock', [])
        
        # Fallback to generic selectors if no domain-specific ones are found or context_url is None
        if not selectors:
            selectors = [
                ".stock.unavailable",
                ".out-of-stock",
                "meta[property='product:availability'][content*='out of stock']",
                "meta[property='product:availability'][content*='OutOfStock']"
            ]
        
        for selector in selectors:
            if selector:  # Skip empty selectors
                # Handle special selectors with attribute conditions
                if '[content*=' in selector:
                    elements = product_page_soup.select(selector)
                    if elements:
                        return True
                else:
                    element = product_page_soup.select_one(selector)
                    if element:
                        return True
        
        # Also check availability text for out-of-stock indicators
        availability = self.extract_availability(product_page_soup, context_url)
        if availability:
            availability_lower = availability.lower()
            out_of_stock_indicators = ['out of stock', 'unavailable', 'sold out', 'outofstock']
            for indicator in out_of_stock_indicators:
                if indicator in availability_lower:
                    return True
        
        return False

    async def extract_availability_category(self, element: BeautifulSoup, element_html: str, context_url: str) -> Optional[str]:
        """Extract availability status from category page product element."""
        # Look for availability indicators within the product element
        availability_selectors = [
            ".stock", ".availability", ".in-stock", ".out-of-stock",
            "[data-availability]", ".product-availability"
        ]
        
        for selector in availability_selectors:
            availability_element = element.select_one(selector)
            if availability_element:
                return availability_element.get_text(strip=True)
        
        return None

    async def extract_out_of_stock_category(self, element: BeautifulSoup, element_html: str, context_url: str) -> bool:
        """Extract out-of-stock status from category page product element."""
        # Look for out-of-stock indicators within the product element
        out_of_stock_selectors = [
            ".out-of-stock", ".stock.unavailable", ".sold-out",
            ".stock-alert", "[data-stock='out']"
        ]
        
        for selector in out_of_stock_selectors:
            if element.select_one(selector):
                return True
        
        # Check availability text
        availability = await self.extract_availability_category(element, element_html, context_url)
        if availability:
            availability_lower = availability.lower()
            out_of_stock_indicators = ['out of stock', 'unavailable', 'sold out', 'outofstock']
            for indicator in out_of_stock_indicators:
                if indicator in availability_lower:
                    return True
        
        return False


async def test_new_suppliers(headless: bool = False, use_shared_chrome: bool = True):
    """Test AI selector discovery on new supplier websites."""
    outputs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "OUTPUTS", "supplier_data")
    os.makedirs(outputs_dir, exist_ok=True)

    # Initialize AI client with environment key
    ai_client = None
    openai_api_key = os.getenv("OPENAI_API_KEY_SUPPLIER") or os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        try:
            from openai import OpenAI
            ai_client = OpenAI(api_key=openai_api_key)
            log.info("OpenAI client initialized for new supplier testing.")
        except Exception as e:
            log.error(f"Error initializing OpenAI client for testing: {e}")
            return
    else:
        log.error("OpenAI API key not available. Cannot test AI selector discovery.")
        return

    scraper = ConfigurableSupplierScraper(
        ai_client=ai_client, 
        openai_model_name=os.getenv("OPENAI_MODEL_SUPPLIER", "gpt-4.1-mini-2025-04-14"),
        headless=headless,
        use_shared_chrome=use_shared_chrome
    )
    
    # Test URLs
    test_suppliers = [
        {
            "url": "https://www.poundwholesale.co.uk/",
            "name": "Pound Wholesale",
            "category_test_url": "https://www.poundwholesale.co.uk/"  # Use homepage (20 products available)
        },
        {
            "url": "https://www.cutpricewholesaler.com/",
            "name": "Cut Price Wholesaler", 
            "category_test_url": "https://www.cutpricewholesaler.com/toys-games"  # Example category
        }
    ]

    results = {}
    
    for supplier in test_suppliers:
        log.info(f"\n{'='*80}")
        log.info(f"TESTING: {supplier['name']} - {supplier['url']}")
        log.info(f"{'='*80}")
        
        try:
            # Step 1: Auto-discover selectors from homepage
            log.info(f"🔍 Auto-discovering selectors for {supplier['name']}...")
            config = await scraper.auto_configure_supplier(supplier['url'], save_config=True)
            
            if not config:
                log.error(f"❌ Failed to auto-configure {supplier['name']}")
                results[supplier['name']] = {"status": "failed", "error": "auto-configuration failed"}
                continue
                
            log.info(f"✅ Successfully discovered selectors for {supplier['name']}")
            log.info(f"📋 Config: {json.dumps(config['field_mappings'], indent=2)}")
            
            # Step 2: Test selector discovery on a category page if available
            if supplier.get('category_test_url'):
                log.info(f"🧪 Testing on category page: {supplier['category_test_url']}")
                
                html_content = await scraper.get_page_content(supplier['category_test_url'])
                if html_content:
                    product_elements = scraper.extract_product_elements(html_content, supplier['category_test_url'])
                    log.info(f"📦 Found {len(product_elements)} product elements on category page")
                    
                    if product_elements:
                        # Test extraction on first few products
                        for i, element in enumerate(product_elements[:3]):
                            log.info(f"\n--- Testing Product {i+1} ---")
                            element_html = str(element)
                            
                            title = await scraper.extract_title(element, element_html, supplier['category_test_url'])
                            price = await scraper.extract_price(element, element_html, supplier['category_test_url'])
                            url = await scraper.extract_url(element, element_html, supplier['category_test_url'], supplier['url'])
                            image = await scraper.extract_image(element, element_html, supplier['category_test_url'], supplier['url'])
                            
                            log.info(f"  Title: {title}")
                            log.info(f"  Price: {price}")
                            log.info(f"  URL: {url}")
                            log.info(f"  Image: {image}")
                            
                            if i == 0:  # Save detailed result for first product
                                results[supplier['name']] = {
                                    "status": "success",
                                    "config": config,
                                    "test_extraction": {
                                        "title": title,
                                        "price": price,
                                        "url": url,
                                        "image": image
                                    }
                                }
                    else:
                        log.warning(f"⚠️ No product elements found on {supplier['category_test_url']}")
                        results[supplier['name']] = {
                            "status": "partial_success",
                            "config": config,
                            "warning": "no products found on category page"
                        }
            else:
                results[supplier['name']] = {
                    "status": "config_only",
                    "config": config
                }
            
        except Exception as e:
            log.error(f"❌ Error testing {supplier['name']}: {e}", exc_info=True)
            results[supplier['name']] = {"status": "error", "error": str(e)}
        
        # Brief pause between suppliers
        await asyncio.sleep(2)
    
    # Save test results
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(outputs_dir, f"new_suppliers_test_{timestamp_str}.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    log.info(f"\n📄 Test results saved to: {results_file}")
    
    # Summary
    log.info(f"\n{'='*80}")
    log.info("SUMMARY:")
    for supplier_name, result in results.items():
        status = result.get('status', 'unknown')
        log.info(f"  {supplier_name}: {status}")
    log.info(f"{'='*80}")
    
    await scraper.close_session()
    return results

async def test_scraper(headless: bool = False):
    """Test the scraper on a sample URL and save results to OUTPUTS directory."""
    outputs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "OUTPUTS", "supplier_data")
    os.makedirs(outputs_dir, exist_ok=True)

    ai_client = None
    openai_api_key = os.getenv("OPENAI_API_KEY_SUPPLIER") or os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        try:
            from openai import OpenAI
            ai_client = OpenAI(api_key=openai_api_key)
            log.info("OpenAI client initialized for testing.")
        except Exception as e:
            log.error(f"Error initializing OpenAI client for testing: {e}")
    else:
        log.warning("OPENAI_API_KEY not set. AI fallbacks will not be tested.")

    scraper = ConfigurableSupplierScraper(ai_client=ai_client, headless=headless)
    # Example test URL (replace with a more suitable one if needed)
    test_url = "https://www.clearance-king.co.uk/pound-lines.html" # A category page
    base_url = "https://www.clearance-king.co.uk"

    # --- Test Category Discovery ---
    log.info(f"\n--- Testing Category Discovery from {base_url} ---")
    categories = await scraper.discover_categories(base_url)
    if categories:
        log.info(f"Discovered {len(categories)} categories:")
        for i, cat in enumerate(categories[:5]): # Log first 5
            log.info(f"  {i+1}. Name: {cat['name']}, URL: {cat['url']}")
        # --- Test Subpage Discovery for the first category ---
        if categories:
            first_category_url = categories[0]['url']
            log.info(f"\n--- Testing Subpage Discovery for {first_category_url} (max_depth=1) ---")
            subpages = await scraper.discover_subpages(first_category_url, max_depth=1)
            if subpages:
                log.info(f"Discovered {len(subpages)} subpages/pagination links for {first_category_url}:")
                for i, sp_url in enumerate(subpages[:5]): # Log first 5
                    log.info(f"  {i+1}. {sp_url}")
    else:
        log.warning(f"No categories discovered from {base_url}")


    log.info(f"\n--- Testing Product Extraction from {test_url} ---")
    html = await scraper.get_page_content(test_url)
    if html:
        log.info(f"Successfully fetched page content from {test_url} ({len(html)} bytes)")
        product_elements = scraper.extract_product_elements(html, test_url)
        log.info(f"Found {len(product_elements)} product elements on {test_url}")

        products_data = []
        if product_elements:
            for i, p_soup in enumerate(product_elements[:3]): # Test first 3 products
                p_html = str(p_soup)
                log.info(f"\n--- Extracting data for Product {i+1} ---")
                title = await scraper.extract_title(p_soup, p_html, test_url)
                price = await scraper.extract_price(p_soup, p_html, test_url)
                product_page_url = await scraper.extract_url(p_soup, p_html, test_url, base_url)
                image = await scraper.extract_image(p_soup, p_html, test_url, base_url)
                
                # CRITICAL FIX: Extract EAN properly, leave blank if not found
                ean = ""
                sku = ""
                if product_page_url:
                    log.info(f"Fetching detail page for EAN: {product_page_url}")
                    detail_page_html = await scraper.get_page_content(product_page_url)
                    if detail_page_html:
                        detail_soup = BeautifulSoup(detail_page_html, 'html.parser')
                        # Try EAN extraction first
                        extracted_ean = scraper.extract_ean(detail_soup, product_page_url)
                        if extracted_ean:
                            # Validate if it's actually an EAN (8-14 digits)
                            cleaned_ean = re.sub(r'[^0-9]', '', extracted_ean)
                            if cleaned_ean and len(cleaned_ean) in [8, 12, 13, 14]:
                                ean = cleaned_ean
                                log.info(f"✅ Valid EAN extracted: {ean}")
                            else:
                                sku = extracted_ean  # Store as SKU if not EAN format
                                log.info(f"⚠️ SKU extracted (not EAN format): {sku}")
                        else:
                            # Try fallback identifier extraction
                            identifier = await scraper.extract_identifier(detail_soup, str(detail_soup), product_page_url)
                            if identifier:
                                cleaned_id = re.sub(r'[^0-9]', '', identifier)
                                if cleaned_id and len(cleaned_id) in [8, 12, 13, 14]:
                                    ean = cleaned_id
                                    log.info(f"✅ EAN from identifier: {ean}")
                                else:
                                    sku = identifier
                                    log.info(f"⚠️ SKU from identifier: {sku}")
                    else:
                        log.warning(f"Failed to fetch detail page {product_page_url} for EAN extraction.")
                
                product_data = {
                    "id": i + 1, "title": title, "price": price, "url": product_page_url,
                    "image": image, "ean": ean, "sku": sku, "out_of_stock_badge": "", 
                    "source_url": test_url, "timestamp": datetime.now().isoformat()
                }
                products_data.append(product_data)
                log.info(f"Product {i+1} Data: {json.dumps(product_data, indent=2)}")
                if i < 2 : await asyncio.sleep(1) # Brief pause

            # Save to JSON
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(outputs_dir, f"scraper_test_output_{timestamp_str}.json")
            output_content = {
                "source_category_url": test_url, "extraction_time": datetime.now().isoformat(),
                "total_products_processed": len(products_data), "products": products_data
            }
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_content, f, indent=2, ensure_ascii=False)
            log.info(f"\nSaved {len(products_data)} products' data to: {output_file}")

            # Test pagination from the category page
            log.info(f"\n--- Testing Pagination from {test_url} ---")
            category_page_soup = BeautifulSoup(html, 'html.parser')
            next_page_url = scraper.get_next_page_url(test_url, category_page_soup, 1)
            log.info(f"Next page URL from {test_url}: {next_page_url}")
            if next_page_url:
                next_page_html = await scraper.get_page_content(next_page_url)
                if next_page_html:
                    log.info(f"Successfully fetched next page ({next_page_url}) content ({len(next_page_html)} bytes)")
                    next_page_soup = BeautifulSoup(next_page_html, 'html.parser')
                    next_next_page_url = scraper.get_next_page_url(next_page_url, next_page_soup, 2)
                    log.info(f"Next-next page URL from {next_page_url}: {next_next_page_url}")

    else:
        log.error(f"Failed to fetch initial page content from {test_url}")

    await scraper.close_session()
    log.info("Scraper test finished.")

async def run_validation_test(supplier_url: str, config_file: str, overrides: dict, headless: bool = False):
    """Run validation test on specific supplier URL with overrides."""
    print(f"="*80)
    print(f"LIVE SELECTOR-EXTRACTION VALIDATION")
    print(f"Supplier URL: {supplier_url}")
    print(f"Config File: {config_file}")
    print(f"Overrides: {json.dumps(overrides, indent=2)}")
    print(f"="*80)
    
    # Create outputs directory
    outputs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "OUTPUTS", "supplier_data")
    os.makedirs(outputs_dir, exist_ok=True)
    
    # Initialize AI client
    ai_client = None
    openai_api_key = os.getenv("OPENAI_API_KEY_SUPPLIER") or os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        try:
            from openai import OpenAI
            ai_client = OpenAI(api_key=openai_api_key)
            log.info("✅ OpenAI client initialized for validation testing.")
        except Exception as e:
            log.error(f"❌ Error initializing OpenAI client: {e}")
            return False
    
    # Initialize scraper with headless setting
    scraper = ConfigurableSupplierScraper(
        ai_client=ai_client, 
        openai_model_name=os.getenv("OPENAI_MODEL_SUPPLIER", "gpt-4.1-mini-2025-04-14"),
        headless=headless
    )
    
    try:
        # Apply clear_cache if requested
        if overrides.get("clear_cache", False):
            log.info("🗑️  Clearing cache as requested...")
        
        # Test supplier configuration or auto-discovery
        domain = get_domain_from_url(supplier_url)
        log.info(f"🔍 Testing domain: {domain}")
        
        # Try to auto-configure the supplier
        config_result = await scraper.auto_configure_supplier(supplier_url)
        
        if config_result.get("success", False):
            log.info(f"✅ Auto-configuration successful for {domain}")
            
            # Test product extraction with limits
            max_products = overrides.get("max_products", 40)
            max_categories = overrides.get("max_categories", 8)
            
            log.info(f"📊 Testing with limits: {max_products} products, {max_categories} categories")
            
            # Get category URLs or use base URL
            test_urls = [supplier_url]  # Start with base URL
            
            products_extracted = 0
            categories_processed = 0
            
            for test_url in test_urls:
                if categories_processed >= max_categories:
                    break
                    
                log.info(f"\n🔍 Testing URL: {test_url}")
                html = await scraper.get_page_content(test_url)
                
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    product_elements = scraper.extract_product_elements(html, test_url)
                    
                    log.info(f"📦 Found {len(product_elements)} product elements")
                    
                    # Extract data from products (limited by max_products)
                    for i, p_soup in enumerate(product_elements):
                        if products_extracted >= max_products:
                            break
                            
                        p_html = str(p_soup)
                        log.info(f"\n--- Product {products_extracted + 1} ---")
                        
                        title = await scraper.extract_title(p_soup, p_html, test_url)
                        price = await scraper.extract_price(p_soup, p_html, test_url)
                        product_url = await scraper.extract_url(p_soup, p_html, test_url, supplier_url)
                        image = await scraper.extract_image(p_soup, p_html, test_url, supplier_url)
                        
                        # Try to extract price from detail page (for sites requiring login)
                        detail_price = None
                        ean = None
                        if product_url:
                            detail_html = await scraper.get_page_content(product_url)
                            if detail_html:
                                detail_soup = BeautifulSoup(detail_html, 'html.parser')
                                
                                # Extract price from meta tags
                                price_meta = detail_soup.select_one('meta[property="product:price:amount"]')
                                if price_meta and price_meta.get('content'):
                                    try:
                                        detail_price = float(price_meta.get('content'))
                                        log.info(f"  💰 Meta Price Found: £{detail_price}")
                                    except:
                                        pass
                                
                                # Check for login required message
                                login_btn = detail_soup.select_one('a.btn.customer-login-link.login-btn')
                                if login_btn:
                                    log.info(f"  🔒 Login Required: {login_btn.get_text(strip=True)}")
                                
                                # Extract EAN using enhanced method
                                ean = scraper.extract_ean(detail_soup, product_url)
                        
                        # Use detail page price if found, otherwise listing price
                        final_price = detail_price if detail_price is not None else price
                        
                        log.info(f"  Title: {title}")
                        log.info(f"  Price: {final_price}")
                        log.info(f"  URL: {product_url}")
                        log.info(f"  EAN: {ean or 'Not found'}")
                        
                        products_extracted += 1
                        
                        if i < min(3, len(product_elements) - 1):
                            await asyncio.sleep(0.5)  # Brief pause
                
                categories_processed += 1
            
            log.info(f"\n✅ VALIDATION COMPLETE")
            log.info(f"   Products extracted: {products_extracted}")
            log.info(f"   Categories processed: {categories_processed}")
            
            return True
            
        else:
            log.error(f"❌ Auto-configuration failed for {domain}")
            return False
            
    except Exception as e:
        log.error(f"❌ Validation test failed: {e}")
        return False
    finally:
        await scraper.cleanup()


if __name__ == "__main__":
    import sys
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='ConfigurableSupplierScraper Validation Tool')
    parser.add_argument('--url', type=str, help='Supplier URL to test')
    parser.add_argument('--config', type=str, help='Config file path')
    parser.add_argument('--override', type=str, help='JSON string with override parameters')
    parser.add_argument('--new-suppliers', action='store_true', help='Test new supplier websites')
    parser.add_argument('--headless', action='store_true', default=False, 
                       help='Run browser in headless mode (default: False for debugging)')
    parser.add_argument('--use-shared-chrome', action='store_true', default=True,
                       help='Connect to shared Chrome instance on port 9222 (default: True)')
    
    args = parser.parse_args()
    
    print("="*80)
    print("ConfigurableSupplierScraper Test Run")
    print("="*80)
    
    # Check for validation mode (--url, --config, --override)
    if args.url and args.config and args.override:
        try:
            overrides = json.loads(args.override)
            print(f"🚀 Running validation test mode... (headless: {args.headless})")
            
            # Pass headless parameter to validation test
            success = asyncio.run(run_validation_test(args.url, args.config, overrides, args.headless))
            if success:
                print("✅ Validation test completed successfully")
            else:
                print("❌ Validation test failed")
                sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in --override parameter: {e}")
            sys.exit(1)
    # Check for new suppliers mode
    elif args.new_suppliers:
        print(f"Testing new supplier websites with AI selector discovery... (headless: {args.headless}, shared-chrome: {args.use_shared_chrome})")
        asyncio.run(test_new_suppliers(headless=args.headless, use_shared_chrome=args.use_shared_chrome))
    else:
        print(f"Running standard test on Clearance King... (headless: {args.headless})")
        print("Usage examples:")
        print("  --new-suppliers                    # Test Pound Wholesale and Cut Price Wholesaler")
        print("  --url <URL> --config <CONFIG> --override <JSON>  # Validation mode")
        print("  --headless                         # Run in headless mode")
        asyncio.run(test_scraper(headless=args.headless))