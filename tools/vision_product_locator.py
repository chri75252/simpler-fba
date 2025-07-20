#!/usr/bin/env python3
"""
Vision-Assisted Product Locator for PoundWholesale
Combines Playwright + heuristic selectors with GPT-4.1-mini Vision fallback
Uses persistent Chrome CDP session for login maintenance
"""

import asyncio
import json
import logging
import base64
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.path_manager import get_log_path, path_manager

# Playwright imports
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:
    raise ImportError("Playwright not available. Install with: pip install playwright && playwright install")

# OpenAI for Vision API
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

@dataclass
class NavigationResult:
    """Result of navigation attempt"""
    success: bool
    product_url: Optional[str] = None
    method_used: str = ""
    screenshot_path: Optional[str] = None
    error_message: Optional[str] = None
    navigation_dump: List[Dict[str, str]] = None

class PoundWholesaleLocator:
    """Vision-assisted product locator for PoundWholesale with CDP persistence"""
    
    # Heuristic selectors (primary method)
    CATEGORY_SELECTORS = [
        'a[href*="/category/"]',
        '.main-nav a[href*="category"]',
        'nav a[href*="product-category"]',
        '.category-link',
        '.navigation a[href*="category"]',
        'header a[href*="category"]'
    ]
    
    PRODUCT_SELECTORS = [
        'a[href*="/product/"]',
        '.product-card a',
        '.product-item a',
        '.product-title a',
        '.woocommerce-loop-product__link',
        'div.product a[href*="product"]',
        '.product-grid a'
    ]
    
    LOGIN_SELECTORS = {
        'email_field': ['input[name="email"]', 'input[type="email"]', '#email', '.email-field'],
        'password_field': ['input[name="password"]', 'input[type="password"]', '#password', '.password-field'],
        'login_button': ['button[type="submit"]', '.login-button', 'input[type="submit"]', '#login-btn'],
        'login_form': ['form[action*="login"]', '.login-form', '#login-form']
    }
    
    def __init__(self, openai_client: OpenAI, cdp_port: int = 9222):
        """Initialize with OpenAI client and CDP settings"""
        self.openai_client = openai_client
        self.cdp_port = cdp_port
        self.cdp_endpoint = f"http://localhost:{cdp_port}"
        
        # Browser state
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Setup debug logging
        self._setup_debug_logging()
        
    def _setup_debug_logging(self):
        """Setup debug logging to standardized path"""
        try:
            date_str = datetime.now().strftime('%Y%m%d')
            debug_log_path = get_log_path("debug", f"supplier_scraping_debug_{date_str}.log")
            
            debug_handler = logging.FileHandler(debug_log_path)
            debug_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            debug_handler.setFormatter(formatter)
            
            log.addHandler(debug_handler)
            log.setLevel(logging.DEBUG)
            log.debug(f"Vision locator debug logging initialized - writing to {debug_log_path}")
            
        except Exception as e:
            log.warning(f"Failed to setup debug logging: {e}")
    
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
                    # Capture screenshot for debugging
                    screenshot_path = path_manager.get_output_path("debug", "login_failure.png")
                    await self.page.screenshot(path=screenshot_path)
                    log.info(f"Login failure screenshot saved to: {screenshot_path}")
                    return False
                    
            except Exception as e:
                log.error(f"❌ Login completion check failed: {e}")
                return False
                
        except Exception as e:
            log.error(f"❌ Login process failed: {e}")
            return False
    
    async def find_product_via_heuristics(self) -> NavigationResult:
        """Find first product using heuristic selectors (primary method)"""
        try:
            log.info("🔍 Attempting to find product via heuristic selectors...")
            
            # Navigate to homepage if not already there
            if not self.page.url.endswith('.co.uk/') and 'poundwholesale.co.uk' not in self.page.url:
                await self.page.goto("https://www.poundwholesale.co.uk/", wait_until='domcontentloaded')
                await self.page.wait_for_load_state('networkidle')
            
            # Store navigation dump
            navigation_links = await self._extract_navigation_links()
            
            # Try to find and click category link first
            category_clicked = False
            for selector in self.CATEGORY_SELECTORS:
                try:
                    category_element = self.page.locator(selector).first
                    if await category_element.is_visible():
                        href = await category_element.get_attribute('href')
                        await category_element.click()
                        await self.page.wait_for_load_state('networkidle')
                        log.info(f"✅ Clicked category link '{href}' via selector: {selector}")
                        category_clicked = True
                        break
                except Exception as e:
                    log.debug(f"Category selector '{selector}' failed: {e}")
            
            if not category_clicked:
                log.info("No category link found, searching for products on current page")
                
                # Check if current page has products (e.g., homepage with featured products)
                product_links = await self._find_homepage_products()
                if product_links:
                    # Navigate to first product
                    for product_link in product_links[:3]:  # Try first 3
                        try:
                            href = await product_link.get_attribute('href')
                            if href and 'product' in href:
                                await product_link.click()
                                await self.page.wait_for_load_state('networkidle')
                                product_url = self.page.url
                                
                                if '/product/' in product_url or 'product' in product_url:
                                    log.info(f"✅ Found homepage product: {product_url}")
                                    return NavigationResult(
                                        success=True,
                                        product_url=product_url,
                                        method_used="homepage_products",
                                        navigation_dump=navigation_links
                                    )
                        except Exception as e:
                            log.debug(f"Failed to click homepage product: {e}")
                            continue
            
            # Try to find product link
            for selector in self.PRODUCT_SELECTORS:
                try:
                    product_element = self.page.locator(selector).first
                    if await product_element.is_visible():
                        product_url = await product_element.get_attribute('href')
                        if product_url and '/product/' in product_url:
                            # Navigate to product page
                            await product_element.click()
                            await self.page.wait_for_load_state('networkidle')
                            
                            final_url = self.page.url
                            log.info(f"✅ Found product page: {final_url}")
                            
                            return NavigationResult(
                                success=True,
                                product_url=final_url,
                                method_used=f"heuristics_{selector}",
                                navigation_dump=navigation_links
                            )
                except Exception as e:
                    log.debug(f"Product selector '{selector}' failed: {e}")
            
            log.warning("❌ No product found via heuristic selectors")
            return NavigationResult(
                success=False,
                method_used="heuristics",
                error_message="No product links found via selectors",
                navigation_dump=navigation_links
            )
            
        except Exception as e:
            log.error(f"❌ Heuristic product finding failed: {e}")
            return NavigationResult(
                success=False,
                method_used="heuristics",
                error_message=str(e)
            )
    
    async def find_product_via_vision(self) -> NavigationResult:
        """Find first product using GPT-4.1-mini Vision (fallback method)"""
        try:
            log.info("🔍 Attempting to find product via Vision API...")
            
            # Navigate to homepage
            await self.page.goto("https://www.poundwholesale.co.uk/", wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle')
            
            # Capture screenshot
            screenshot_path = path_manager.get_output_path("debug", f"vision_homepage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            await self.page.screenshot(path=screenshot_path, full_page=False)
            
            # Encode screenshot for Vision API
            with open(screenshot_path, 'rb') as img_file:
                screenshot_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Ask Vision API to identify first category or product
            vision_prompt = """
            You are looking at the PoundWholesale homepage. I need you to identify the first clickable element that leads to products.
            
            Look for:
            1. First main category link (like "Home & Garden", "Toys", etc.)
            2. First product card or product link
            3. Any "Shop" or "Products" navigation link
            
            Return ONLY a JSON object with this structure:
            {
                "element_type": "category|product|navigation",
                "element_text": "exact text of the element",
                "coordinates": {"x": 100, "y": 200},
                "confidence": "high|medium|low"
            }
            
            If you cannot identify any suitable element, return:
            {"error": "No suitable product navigation element found"}
            """
            
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",  # Using the specified model
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": vision_prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{screenshot_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=300,
                    temperature=0.1
                )
                
                vision_result = response.choices[0].message.content.strip()
                log.info(f"Vision API response: {vision_result}")
                
                # Parse Vision response - handle markdown formatting
                try:
                    # Remove markdown formatting if present
                    if vision_result.startswith("```json"):
                        vision_result = vision_result.replace("```json", "").replace("```", "").strip()
                    vision_data = json.loads(vision_result)
                    if "error" in vision_data:
                        log.warning(f"Vision API could not find element: {vision_data['error']}")
                        return NavigationResult(
                            success=False,
                            method_used="vision",
                            error_message=vision_data['error'],
                            screenshot_path=str(screenshot_path)
                        )
                    
                    # Click on identified coordinates
                    x, y = vision_data["coordinates"]["x"], vision_data["coordinates"]["y"]
                    await self.page.mouse.click(x, y)
                    await self.page.wait_for_load_state('networkidle')
                    
                    log.info(f"✅ Clicked element '{vision_data['element_text']}' at ({x}, {y})")
                    
                    # If we clicked a category, try to find a product on the category page
                    if vision_data["element_type"] == "category":
                        # Use heuristics to find product on category page
                        for selector in self.PRODUCT_SELECTORS:
                            try:
                                product_element = self.page.locator(selector).first
                                if await product_element.is_visible():
                                    await product_element.click()
                                    await self.page.wait_for_load_state('networkidle')
                                    
                                    final_url = self.page.url
                                    log.info(f"✅ Found product page via Vision + heuristics: {final_url}")
                                    
                                    return NavigationResult(
                                        success=True,
                                        product_url=final_url,
                                        method_used="vision_category_then_heuristics",
                                        screenshot_path=str(screenshot_path)
                                    )
                            except Exception as e:
                                log.debug(f"Product selector '{selector}' failed on category page: {e}")
                    
                    # If direct product click or category didn't lead to product
                    final_url = self.page.url
                    if '/product/' in final_url:
                        return NavigationResult(
                            success=True,
                            product_url=final_url,
                            method_used="vision_direct",
                            screenshot_path=str(screenshot_path)
                        )
                    else:
                        return NavigationResult(
                            success=False,
                            method_used="vision",
                            error_message=f"Vision click led to {final_url}, not a product page",
                            screenshot_path=str(screenshot_path)
                        )
                        
                except json.JSONDecodeError as e:
                    log.error(f"Failed to parse Vision API response as JSON: {e}")
                    return NavigationResult(
                        success=False,
                        method_used="vision",
                        error_message=f"Invalid JSON response from Vision API: {vision_result}",
                        screenshot_path=str(screenshot_path)
                    )
                    
            except Exception as e:
                log.error(f"Vision API call failed: {e}")
                return NavigationResult(
                    success=False,
                    method_used="vision",
                    error_message=f"Vision API error: {str(e)}",
                    screenshot_path=str(screenshot_path)
                )
                
        except Exception as e:
            log.error(f"❌ Vision product finding failed: {e}")
            return NavigationResult(
                success=False,
                method_used="vision",
                error_message=str(e)
            )
    
    async def _find_homepage_products(self) -> List:
        """Find product links on the current page (homepage or category page)"""
        try:
            # Try specific selectors based on inspection - look for actual product links
            selectors = [
                '.product a[href*="elmer"], .product a[href*="skin-treats"], .product a[href*="bello"], .product a[href*="bing"], .product a[href*="nuage"]',  # Product name links
                '.product-item a[href*="elmer"], .product-item a[href*="skin-treats"], .product-item a[href*="bello"], .product-item a[href*="bing"], .product-item a[href*="nuage"]',  # Product item name links
            ]
            
            for selector in selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    if elements:
                        # Filter for actual product links
                        product_links = []
                        for element in elements:
                            href = await element.get_attribute('href')
                            is_visible = await element.is_visible()
                            
                            # Filter for actual product pages - these are the exact patterns we found
                            if (href and is_visible and 
                                href.startswith('https://www.poundwholesale.co.uk/') and
                                'javascript:' not in href and
                                '#' not in href and
                                'account' not in href and
                                'customer' not in href and
                                ('elmer' in href or 'skin-treats' in href or 'bello' in href or 'bing' in href or 'nuage' in href)):
                                product_links.append(element)
                        
                        if product_links:
                            log.info(f"Found {len(product_links)} homepage products with selector: {selector}")
                            return product_links[:5]  # Return first 5
                            
                except Exception as e:
                    log.debug(f"Product selector '{selector}' failed: {e}")
            
            return []
            
        except Exception as e:
            log.error(f"Error finding homepage products: {e}")
            return []

    async def _extract_navigation_links(self) -> List[Dict[str, str]]:
        """Extract all navigation links for analysis"""
        try:
            links = []
            nav_selectors = ['nav a', '.menu a', '.navigation a', 'header a', '.navbar a']
            
            for selector in nav_selectors:
                elements = self.page.locator(selector)
                count = await elements.count()
                
                for i in range(count):
                    try:
                        element = elements.nth(i)
                        if await element.is_visible():
                            text = await element.text_content()
                            href = await element.get_attribute('href')
                            if text and href:
                                links.append({"text": text.strip(), "href": href})
                    except Exception:
                        continue
            
            log.info(f"Extracted {len(links)} navigation links")
            return links
            
        except Exception as e:
            log.warning(f"Failed to extract navigation links: {e}")
            return []
    
    async def save_navigation_dump(self, navigation_links: List[Dict[str, str]], supplier: str = "poundwholesale-co-uk"):
        """Save navigation dump to specified path"""
        try:
            date_str = datetime.now().strftime('%Y%m%d')
            dump_dir = path_manager.get_output_path("FBA_ANALYSIS", "navigation_dumps", supplier)
            dump_dir.mkdir(parents=True, exist_ok=True)
            
            dump_file = dump_dir / f"links_{date_str}.jsonl"
            
            with open(dump_file, 'a', encoding='utf-8') as f:
                for link in navigation_links:
                    f.write(json.dumps(link) + '\n')
            
            log.info(f"Navigation dump saved to: {dump_file}")
            
        except Exception as e:
            log.error(f"Failed to save navigation dump: {e}")
    
    async def find_first_product(self, email: str, password: str) -> NavigationResult:
        """Main method to find first product page using hybrid approach"""
        try:
            log.info("🚀 Starting Vision-Assisted Product Location...")
            
            # Connect to browser
            if not await self.connect_browser():
                return NavigationResult(
                    success=False,
                    method_used="browser_connection",
                    error_message="Failed to connect to shared Chrome via CDP"
                )
            
            # Login
            if not await self.login(email, password):
                return NavigationResult(
                    success=False,
                    method_used="login",
                    error_message="Login failed"
                )
            
            # Try heuristics first (faster, more reliable)
            result = await self.find_product_via_heuristics()
            if result.success:
                log.info(f"✅ Product found via heuristics: {result.product_url}")
                if result.navigation_dump:
                    await self.save_navigation_dump(result.navigation_dump)
                return result
            
            # Fallback to Vision
            log.info("🔄 Heuristics failed, falling back to Vision API...")
            result = await self.find_product_via_vision()
            if result.success:
                log.info(f"✅ Product found via Vision: {result.product_url}")
                return result
            
            # Both methods failed
            log.error("❌ Both heuristics and Vision methods failed")
            return NavigationResult(
                success=False,
                method_used="all_methods",
                error_message="Both heuristics and Vision approaches failed to find product"
            )
            
        except Exception as e:
            log.error(f"❌ Product location process failed: {e}")
            return NavigationResult(
                success=False,
                method_used="process",
                error_message=str(e)
            )
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.browser:
                # Don't close the shared browser, just disconnect
                await self.browser.close()
                log.debug("Disconnected from shared Chrome browser")
            
            if self.playwright:
                await self.playwright.stop()
                log.debug("Playwright stopped")
                
        except Exception as e:
            log.warning(f"Cleanup warning: {e}")

# Example usage function
async def main():
    """Example usage of the Vision Product Locator"""
    from openai import OpenAI
    
    # Initialize OpenAI client
    openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # Initialize locator
    locator = PoundWholesaleLocator(openai_client)
    
    try:
        # Find first product
        result = await locator.find_first_product(
            email="info@theblacksmithmarket.com",
            password="0Dqixm9c&"
        )
        
        if result.success:
            print(f"✅ Success! Product URL: {result.product_url}")
            print(f"Method used: {result.method_used}")
        else:
            print(f"❌ Failed: {result.error_message}")
            print(f"Method attempted: {result.method_used}")
            
    finally:
        await locator.cleanup()

if __name__ == "__main__":
    asyncio.run(main())