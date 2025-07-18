#!/usr/bin/env python3
"""
Category-First Navigation System for PoundWholesale
Implements sitemap-driven category discovery and product extraction
Replaces homepage-based navigation with structured category traversal
"""

import asyncio
import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass
import requests
import sys
import os

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.path_manager import get_log_path, path_manager

# Playwright imports
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:
    raise ImportError("Playwright not available. Install with: pip install playwright && playwright install")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

@dataclass
class CategoryResult:
    """Result of category processing"""
    category_url: str
    product_urls: List[str]
    pages_processed: int
    success: bool
    error_message: Optional[str] = None

@dataclass 
class ProductExtractionResult:
    """Result of product data extraction"""
    url: str
    title: Optional[str]
    price: Optional[str]
    ean: Optional[str]
    success: bool
    error_message: Optional[str] = None
    extraction_method: str = ""
    sku: Optional[str] = None
    identifier_type: str = "none"
    out_of_stock: bool = False
    stock_status: Optional[str] = None

class CategoryNavigator:
    """Category-first navigation system for PoundWholesale"""
    
    # Configuration for PoundWholesale/Magento
    SITEMAP_URL = "https://www.poundwholesale.co.uk/sitemap.xml"
    BASE_URL = "https://www.poundwholesale.co.uk"
    
    # URL patterns for filtering
    CATEGORY_URL_PATTERN = re.compile(r'^https://www\.poundwholesale\.co\.uk/[a-z-]+(/[a-z-]+)*/?$')
    PRODUCT_URL_PATTERN = re.compile(r'^https://www\.poundwholesale\.co\.uk/[a-z0-9-]+/?$')
    
    # Magento selectors for category pages
    CATEGORY_SELECTORS = {
        'product_items': [
            'li.product-item',
            '.product-item',
            '.product-card',
            'div.item'
        ],
        'product_links': [
            'a.product-item-link',
            '.product-item a',
            '.product-card a',
            'a[href*="/"][title]'
        ],
        'pagination_next': [
            'a.action.next',
            '.pages-item-next a',
            'a[aria-label="Next"]',
            'a:contains("Next")',
            '.pagination .next'
        ]
    }
    
    # Magento selectors for product pages  
    PRODUCT_SELECTORS = {
        'title': [
            'h1.page-title',
            'h1.product-title',
            '.page-title-wrapper h1',
            'h1'
        ],
        'price': [
            '.price-box .price',
            '.product-info-price .price',
            'span.price',
            '.price-container .price',
            '.regular-price'
        ],
        'ean_barcode': [
            '.product-attribute-ean',
            '.product-info-sku',
            '.sku',
            '.barcode',
            '.product-details .ean'
        ],
        'stock_status': [
            '.stock.available',
            '.stock.unavailable', 
            '.product-info-stock-sku .stock',
            '.availability',
            '.in-stock',
            '.out-of-stock',
            '.stock-status'
        ]
    }
    
    # Out of stock indicators
    OUT_OF_STOCK_INDICATORS = [
        'text=Out of Stock',
        'text=OUT OF STOCK',
        'text=Not Available',
        'text=Unavailable',
        'text=Sold Out',
        'text=No Stock',
        '.out-of-stock',
        '.unavailable',
        '.stock.unavailable',
        '[class*="out-of-stock"]',
        '[class*="unavailable"]'
    ]
    
    # Product page validation selectors
    PRODUCT_PAGE_INDICATORS = [
        'meta[property="og:type"][content="product"]',
        'body.catalog-product-view',
        '.product-info-main',
        '.product-add-to-cart'
    ]
    
    # Login selectors
    LOGIN_SELECTORS = {
        'email_field': ['input[name="email"]', 'input[type="email"]', '#email', '.email-field'],
        'password_field': ['input[name="password"]', 'input[type="password"]', '#password', '.password-field'],
        'login_button': ['button[type="submit"]', '.login-button', 'input[type="submit"]', '#login-btn'],
        'login_form': ['form[action*="login"]', '.login-form', '#login-form']
    }

    def __init__(self, cdp_port: int = 9222):
        """Initialize navigator with CDP settings"""
        self.cdp_port = cdp_port
        self.cdp_endpoint = f"http://localhost:{cdp_port}"
        
        # Browser state
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Data storage
        self.discovered_categories: Set[str] = set()
        self.discovered_products: Set[str] = set()
        
        # Load configuration defaults from system_config.json
        self.config = self._load_system_config()
        
        # Setup logging
        self._setup_debug_logging()
    
    def _setup_debug_logging(self):
        """Setup debug logging to standardized path"""
        try:
            date_str = datetime.now().strftime('%Y%m%d')
            debug_log_path = get_log_path("debug", f"category_navigation_{date_str}.log")
            
            debug_handler = logging.FileHandler(debug_log_path)
            debug_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            debug_handler.setFormatter(formatter)
            
            log.addHandler(debug_handler)
            log.setLevel(logging.DEBUG)
            log.debug(f"Category navigator debug logging initialized - writing to {debug_log_path}")
            
        except Exception as e:
            log.warning(f"Failed to setup debug logging: {e}")
    
    def _load_system_config(self) -> Dict[str, Any]:
        """Load system configuration from system_config.json"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "system_config.json")
            with open(config_path, 'r', encoding='utf-8') as f:
                system_config = json.load(f)
            
            # Extract relevant configuration values
            config = {
                'max_categories': system_config.get("processing_limits", {}).get("max_categories_per_cycle", 5),
                'max_products_per_category': system_config.get("system", {}).get("max_products_per_category", 3),
                'max_analyzed_products': system_config.get("system", {}).get("max_analyzed_products", 0)
            }
            
            # If unlimited (0), set reasonable defaults for this specific tool
            if config['max_products_per_category'] == 0:
                config['max_products_per_category'] = 50  # Reasonable default for category navigation
            
            log.info(f"Loaded system configuration: {config}")
            return config
            
        except Exception as e:
            log.warning(f"Failed to load system config, using hardcoded defaults: {e}")
            return {
                'max_categories': 5,
                'max_products_per_category': 3,
                'max_analyzed_products': 100
            }
    
    async def connect_browser(self) -> bool:
        """Connect to shared Chrome instance via CDP"""
        try:
            if self.playwright is None:
                self.playwright = await async_playwright().start()
            
            # Connect to shared Chrome via CDP
            self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_endpoint)
            log.info(f"✅ Connected to shared Chrome instance at {self.cdp_endpoint}")
            
            # Use existing context or create new one
            if self.browser.contexts:
                self.context = self.browser.contexts[0]
                log.debug("Using existing browser context")
            else:
                self.context = await self.browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                log.debug("Created new browser context")
            
            # Get or create page
            if self.context.pages:
                self.page = self.context.pages[0]
                log.debug("Using existing page")
            else:
                self.page = await self.context.new_page()
                log.debug("Created new page")
            
            return True
            
        except Exception as e:
            log.error(f"❌ Failed to connect to shared Chrome: {e}")
            return False
    
    def parse_sitemap_categories(self) -> List[str]:
        """Parse sitemap.xml to extract category URLs"""
        try:
            log.info(f"🔍 Parsing sitemap: {self.SITEMAP_URL}")
            
            response = requests.get(self.SITEMAP_URL, timeout=30)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Extract URLs from sitemap
            category_urls = []
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            for url_element in root.findall('.//ns:url', namespace):
                loc_element = url_element.find('ns:loc', namespace)
                if loc_element is not None:
                    url = loc_element.text.strip()
                    
                    # Filter for category URLs (not blog, not single products)
                    if (url.startswith(self.BASE_URL) and 
                        '/blog/' not in url and
                        '/customer/' not in url and
                        '/checkout/' not in url and
                        url != self.BASE_URL + '/' and
                        self.CATEGORY_URL_PATTERN.match(url)):
                        
                        category_urls.append(url)
                        self.discovered_categories.add(url)
            
            log.info(f"✅ Found {len(category_urls)} category URLs in sitemap")
            
            # Save category list for debugging
            category_file = path_manager.get_output_path("debug", "discovered_categories.json")
            os.makedirs(os.path.dirname(category_file), exist_ok=True)
            with open(category_file, 'w') as f:
                json.dump(sorted(category_urls), f, indent=2)
            
            return category_urls
            
        except Exception as e:
            log.error(f"❌ Failed to parse sitemap: {e}")
            return []
    
    async def process_category(self, category_url: str, max_pages: int = 5) -> CategoryResult:
        """Process a single category to extract product URLs"""
        try:
            log.info(f"🔍 Processing category: {category_url}")
            
            product_urls = []
            pages_processed = 0
            current_url = category_url
            
            while pages_processed < max_pages:
                try:
                    # Navigate to category page
                    await self.page.goto(current_url, wait_until='domcontentloaded')
                    await self.page.wait_for_load_state('networkidle', timeout=10000)
                    
                    pages_processed += 1
                    log.debug(f"Processing page {pages_processed}: {current_url}")
                    
                    # Extract product links from current page
                    page_products = await self._extract_products_from_page()
                    product_urls.extend(page_products)
                    
                    # Look for next page
                    next_url = await self._find_next_page()
                    if not next_url:
                        log.debug(f"No more pages found for category {category_url}")
                        break
                    
                    current_url = next_url
                    
                    # Rate limiting
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    log.warning(f"Error processing page {pages_processed} of {category_url}: {e}")
                    break
            
            # Deduplicate and validate product URLs
            unique_products = list(set(product_urls))
            validated_products = [url for url in unique_products if self.PRODUCT_URL_PATTERN.match(url)]
            
            # Debug URL filtering
            if len(unique_products) > len(validated_products):
                log.debug(f"URL filtering: {len(unique_products)} found, {len(validated_products)} validated")
                filtered_out = [url for url in unique_products if not self.PRODUCT_URL_PATTERN.match(url)]
                log.debug(f"Filtered out URLs (first 3): {filtered_out[:3]}")
            
            log.info(f"✅ Category {category_url}: {len(validated_products)} products from {pages_processed} pages")
            
            return CategoryResult(
                category_url=category_url,
                product_urls=validated_products,
                pages_processed=pages_processed,
                success=True
            )
            
        except Exception as e:
            log.error(f"❌ Failed to process category {category_url}: {e}")
            return CategoryResult(
                category_url=category_url,
                product_urls=[],
                pages_processed=0,
                success=False,
                error_message=str(e)
            )
    
    async def _extract_products_from_page(self) -> List[str]:
        """Extract product URLs from current category page"""
        try:
            product_urls = []
            
            # Try different selectors for product links
            for selector in self.CATEGORY_SELECTORS['product_links']:
                try:
                    elements = await self.page.locator(selector).all()
                    
                    for element in elements:
                        try:
                            href = await element.get_attribute('href')
                            if href:
                                # Convert relative URLs to absolute
                                if href.startswith('/'):
                                    href = self.BASE_URL + href
                                
                                # Basic filtering
                                if (href.startswith(self.BASE_URL) and 
                                    '/blog/' not in href and
                                    'javascript:' not in href and
                                    '#' not in href):
                                    product_urls.append(href)
                                    
                        except Exception:
                            continue
                    
                    if product_urls:
                        log.debug(f"Found {len(product_urls)} products using selector: {selector}")
                        break
                        
                except Exception as e:
                    log.debug(f"Selector {selector} failed: {e}")
                    continue
            
            return product_urls
            
        except Exception as e:
            log.warning(f"Failed to extract products from page: {e}")
            return []
    
    async def _find_next_page(self) -> Optional[str]:
        """Find next pagination page URL"""
        try:
            for selector in self.CATEGORY_SELECTORS['pagination_next']:
                try:
                    next_element = self.page.locator(selector).first
                    if await next_element.is_visible():
                        href = await next_element.get_attribute('href')
                        if href:
                            if href.startswith('/'):
                                href = self.BASE_URL + href
                            return href
                except Exception:
                    continue
            
            return None
            
        except Exception as e:
            log.debug(f"Error finding next page: {e}")
            return None
    
    async def extract_product_data(self, product_url: str) -> ProductExtractionResult:
        """Extract data from a single product page"""
        try:
            log.debug(f"🔍 Extracting data from: {product_url}")
            
            # Navigate to product page
            await self.page.goto(product_url, wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Validate this is actually a product page
            if not await self._is_product_page():
                return ProductExtractionResult(
                    url=product_url,
                    title=None,
                    price=None,
                    ean=None,
                    success=False,
                    error_message="Not a valid product page",
                    extraction_method="validation_failed"
                )
            
            # Extract title
            title = await self._extract_with_selectors(self.PRODUCT_SELECTORS['title'])
            
            # Extract price
            price = await self._extract_with_selectors(self.PRODUCT_SELECTORS['price'])
            
            # Check stock status
            out_of_stock, stock_status = await self._check_stock_status()
            
            # Extract EAN/barcode and distinguish from SKU
            raw_identifier = await self._extract_with_selectors(self.PRODUCT_SELECTORS['ean_barcode'])
            
            # Analyze the identifier to determine if it's EAN/barcode or SKU
            ean_code = None
            sku_code = None
            identifier_type = "none"
            
            if raw_identifier:
                # Clean up the raw text
                clean_identifier = raw_identifier.replace("SKU", "").replace("\n", "").strip()
                
                # Check if it looks like an EAN/barcode (typically 8-14 digits)
                import re
                ean_pattern = re.compile(r'\b\d{8,14}\b')
                ean_match = ean_pattern.search(clean_identifier)
                
                if ean_match and len(ean_match.group()) >= 12:
                    # Looks like a proper EAN/barcode
                    ean_code = ean_match.group()
                    identifier_type = "ean"
                    log.debug(f"Found EAN code: {ean_code}")
                else:
                    # Likely a supplier SKU
                    sku_code = clean_identifier
                    identifier_type = "sku"
                    log.debug(f"Found SKU code: {sku_code}")
            
            # Check if extraction was successful
            success = bool(title and title != "Title not found")
            
            return ProductExtractionResult(
                url=product_url,
                title=title,
                price=price,
                ean=ean_code,  # Only actual EAN codes here
                success=success,
                extraction_method="category_navigation",
                sku=sku_code,  # Add SKU field
                identifier_type=identifier_type,  # Track what type we found
                out_of_stock=out_of_stock,
                stock_status=stock_status
            )
            
        except Exception as e:
            log.error(f"❌ Failed to extract data from {product_url}: {e}")
            return ProductExtractionResult(
                url=product_url,
                title=None,
                price=None,
                ean=None,
                success=False,
                error_message=str(e),
                extraction_method="extraction_failed"
            )
    
    async def _is_product_page(self) -> bool:
        """Validate that current page is actually a product page"""
        try:
            for selector in self.PRODUCT_PAGE_INDICATORS:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible():
                        return True
                except Exception:
                    continue
            
            return False
            
        except Exception:
            return False
    
    async def _extract_with_selectors(self, selectors: List[str]) -> Optional[str]:
        """Extract text using list of selectors"""
        try:
            for selector in selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible():
                        text = await element.text_content()
                        if text and text.strip():
                            return text.strip()
                except Exception:
                    continue
            
            return None
            
        except Exception:
            return None
    
    async def _check_stock_status(self) -> Tuple[bool, Optional[str]]:
        """Check if product is out of stock"""
        try:
            # Check for explicit out-of-stock indicators first
            for indicator in self.OUT_OF_STOCK_INDICATORS:
                try:
                    element = self.page.locator(indicator).first
                    if await element.is_visible():
                        text = await element.text_content()
                        log.debug(f"Found out-of-stock indicator: {text}")
                        return True, text.strip() if text else "Out of Stock"
                except Exception:
                    continue
            
            # Check stock status selectors for availability info
            for selector in self.PRODUCT_SELECTORS['stock_status']:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible():
                        text = await element.text_content()
                        if text:
                            text = text.strip().lower()
                            # Check for out-of-stock keywords
                            out_of_stock_keywords = [
                                'out of stock', 'unavailable', 'not available', 
                                'sold out', 'no stock', 'out-of-stock'
                            ]
                            
                            for keyword in out_of_stock_keywords:
                                if keyword in text:
                                    log.debug(f"Found out-of-stock in stock status: {text}")
                                    return True, text
                            
                            # Check for in-stock keywords
                            in_stock_keywords = ['in stock', 'available', 'in-stock']
                            for keyword in in_stock_keywords:
                                if keyword in text:
                                    log.debug(f"Found in-stock status: {text}")
                                    return False, text
                except Exception:
                    continue
            
            # Default to in-stock if no indicators found
            return False, "In Stock (assumed)"
            
        except Exception as e:
            log.debug(f"Error checking stock status: {e}")
            return False, None
    
    async def login(self, email: str, password: str) -> bool:
        """Login to PoundWholesale with provided credentials"""
        try:
            log.info("🔐 Attempting login to PoundWholesale...")
            
            # Navigate to homepage first
            await self.page.goto("https://www.poundwholesale.co.uk/", wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Check if already logged in
            current_url = self.page.url
            page_content = await self.page.content()
            
            if "login" not in current_url.lower() and ("logout" in page_content.lower() or "account" in page_content.lower()):
                log.info("✅ Already logged in to PoundWholesale")
                return True
            
            # Look for login link or form
            login_link_found = False
            login_link_selectors = ['a[href*="login"]', '.login-link', '#login', 'a:has-text("Login")', 'a:has-text("Sign In")']
            
            for selector in login_link_selectors:
                try:
                    login_element = self.page.locator(selector).first
                    if await login_element.is_visible():
                        await login_element.click()
                        await self.page.wait_for_load_state('networkidle')
                        log.info(f"Clicked login link via selector: {selector}")
                        login_link_found = True
                        break
                except Exception as e:
                    log.debug(f"Login link selector '{selector}' failed: {e}")
            
            if not login_link_found:
                log.warning("No login link found, assuming login form is on current page")
            
            # Fill login form
            email_filled = False
            for selector in self.LOGIN_SELECTORS['email_field']:
                try:
                    email_field = self.page.locator(selector).first
                    if await email_field.is_visible():
                        await email_field.fill(email)
                        log.info(f"Email filled via selector: {selector}")
                        email_filled = True
                        break
                except Exception as e:
                    log.debug(f"Email selector '{selector}' failed: {e}")
            
            if not email_filled:
                log.error("❌ Could not find email field")
                return False
            
            password_filled = False
            for selector in self.LOGIN_SELECTORS['password_field']:
                try:
                    password_field = self.page.locator(selector).first
                    if await password_field.is_visible():
                        await password_field.fill(password)
                        log.info(f"Password filled via selector: {selector}")
                        password_filled = True
                        break
                except Exception as e:
                    log.debug(f"Password selector '{selector}' failed: {e}")
            
            if not password_filled:
                log.error("❌ Could not find password field")
                return False
            
            # Submit login form
            login_submitted = False
            for selector in self.LOGIN_SELECTORS['login_button']:
                try:
                    login_button = self.page.locator(selector).first
                    if await login_button.is_visible():
                        await login_button.click()
                        log.info(f"Login button clicked via selector: {selector}")
                        login_submitted = True
                        break
                except Exception as e:
                    log.debug(f"Login button selector '{selector}' failed: {e}")
            
            if not login_submitted:
                log.error("❌ Could not find login button")
                return False
            
            # Wait for login to complete
            try:
                await self.page.wait_for_load_state('networkidle', timeout=15000)
                
                # Check if login was successful
                current_url = self.page.url
                page_content = await self.page.content()
                
                if "login" not in current_url.lower() and ("logout" in page_content.lower() or "account" in page_content.lower()):
                    log.info("✅ Login successful!")
                    return True
                else:
                    log.error("❌ Login appears to have failed")
                    return False
                    
            except Exception as e:
                log.error(f"❌ Login completion check failed: {e}")
                return False
                
        except Exception as e:
            log.error(f"❌ Login process failed: {e}")
            return False
    
    async def run_discovery(self, email: str, password: str, max_categories: Optional[int] = None, max_products_per_category: Optional[int] = None) -> Dict[str, Any]:
        """Run complete category-based product discovery"""
        try:
            # Use configuration values if parameters not provided
            if max_categories is None:
                max_categories = self.config.get('max_categories', 5)
            if max_products_per_category is None:
                max_products_per_category = self.config.get('max_products_per_category', 3)
            
            log.info(f"🚀 Starting category-based product discovery with max_categories={max_categories}, max_products_per_category={max_products_per_category}")
            
            results = {
                "started_at": datetime.now().isoformat(),
                "categories_processed": 0,
                "total_products_found": 0,
                "successful_extractions": 0,
                "failed_extractions": 0,
                "in_stock_products": 0,
                "out_of_stock_products": 0,
                "category_results": [],
                "in_stock_product_results": [],
                "out_of_stock_product_results": []
            }
            
            # Connect to browser
            if not await self.connect_browser():
                results["error"] = "Failed to connect to browser"
                return results
            
            # Login first
            if not await self.login(email, password):
                results["error"] = "Failed to login to PoundWholesale"
                return results
            
            # Parse sitemap for categories
            categories = self.parse_sitemap_categories()
            if not categories:
                results["error"] = "No categories found in sitemap"
                return results
            
            # Process limited number of categories for testing
            for i, category_url in enumerate(categories[:max_categories]):
                try:
                    log.info(f"Processing category {i+1}/{max_categories}: {category_url}")
                    
                    # Process category to get product URLs
                    category_result = await self.process_category(category_url)
                    results["category_results"].append({
                        "url": category_result.category_url,
                        "success": category_result.success,
                        "products_found": len(category_result.product_urls),
                        "pages_processed": category_result.pages_processed,
                        "error": category_result.error_message
                    })
                    
                    if category_result.success:
                        results["categories_processed"] += 1
                        results["total_products_found"] += len(category_result.product_urls)
                        
                        # Extract data from limited number of products per category
                        for j, product_url in enumerate(category_result.product_urls[:max_products_per_category]):
                            try:
                                product_result = await self.extract_product_data(product_url)
                                
                                # Create product data object
                                product_data = {
                                    "url": product_result.url,
                                    "title": product_result.title,
                                    "price": product_result.price,
                                    "ean": product_result.ean,
                                    "sku": product_result.sku,
                                    "identifier_type": product_result.identifier_type,
                                    "out_of_stock": product_result.out_of_stock,
                                    "stock_status": product_result.stock_status,
                                    "success": product_result.success,
                                    "error": product_result.error_message,
                                    "method": product_result.extraction_method,
                                    "amazon_matching_strategy": "ean" if product_result.ean else "title" if product_result.sku else "none"
                                }
                                
                                # Separate in-stock vs out-of-stock products
                                if product_result.out_of_stock:
                                    results["out_of_stock_product_results"].append(product_data)
                                    results["out_of_stock_products"] += 1
                                    log.info(f"📦 OUT OF STOCK: {product_result.title} - {product_result.stock_status}")
                                else:
                                    results["in_stock_product_results"].append(product_data)
                                    results["in_stock_products"] += 1
                                    log.info(f"✅ IN STOCK: {product_result.title}")
                                
                                if product_result.success:
                                    results["successful_extractions"] += 1
                                else:
                                    results["failed_extractions"] += 1
                                
                                # Rate limiting
                                await asyncio.sleep(1)
                                
                            except Exception as e:
                                log.error(f"Error processing product {product_url}: {e}")
                                results["failed_extractions"] += 1
                    
                    # Rate limiting between categories
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    log.error(f"Error processing category {category_url}: {e}")
            
            results["completed_at"] = datetime.now().isoformat()
            
            # Save results
            results_file = path_manager.get_output_path("FBA_ANALYSIS", "extraction_logs", "poundwholesale-co-uk", 
                                                       f"category_discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            os.makedirs(os.path.dirname(results_file), exist_ok=True)
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            log.info(f"✅ Discovery complete: {results['successful_extractions']} successful, {results['failed_extractions']} failed")
            log.info(f"📊 Stock Summary: {results['in_stock_products']} in-stock, {results['out_of_stock_products']} out-of-stock")
            log.info(f"Results saved to: {results_file}")
            
            # Analysis workflow message
            if results['out_of_stock_products'] > 0:
                log.info(f"🔄 WORKFLOW: In-stock products will be processed first for Amazon matching and financial analysis")
                log.info(f"📦 OUT-OF-STOCK QUEUE: {results['out_of_stock_products']} products waiting for separate analysis after in-stock completion")
            
            return results
            
        except Exception as e:
            log.error(f"❌ Discovery failed: {e}")
            results["error"] = str(e)
            return results
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.browser:
                await self.browser.close()
                log.debug("Disconnected from shared Chrome browser")
            
            if self.playwright:
                await self.playwright.stop()
                log.debug("Playwright stopped")
                
        except Exception as e:
            log.warning(f"Cleanup warning: {e}")

# Example usage
async def main():
    """Example usage of CategoryNavigator"""
    navigator = CategoryNavigator()
    
    try:
        # Configuration values will be loaded from system_config.json automatically
        # You can still override them by passing parameters
        results = await navigator.run_discovery(
            email="info@theblacksmithmarket.com",
            password="0Dqixm9c&"
            # max_categories and max_products_per_category will use system_config.json values
            # Or you can override: max_categories=3, max_products_per_category=2
        )
        print(f"Discovery completed: {results['successful_extractions']} successful extractions")
        
    finally:
        await navigator.cleanup()

if __name__ == "__main__":
    asyncio.run(main())