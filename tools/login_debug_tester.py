#!/usr/bin/env python3
"""
Login Tester for PoundWholesale
Focus on finding the actual "Sign in" button and "login to view prices" elements
"""

import asyncio
import logging
from datetime import datetime
import sys
import os

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.path_manager import get_log_path

# Playwright imports
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:
    raise ImportError("Playwright not available. Install with: pip install playwright && playwright install")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class LoginTester:
    """Test login process to find correct selectors"""
    
    def __init__(self, cdp_port: int = 9222):
        """Initialize login tester"""
        self.cdp_port = cdp_port
        self.cdp_endpoint = f"http://localhost:{cdp_port}"
        
        # Browser state
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # Setup logging
        self._setup_debug_logging()
    
    def _setup_debug_logging(self):
        """Setup debug logging"""
        try:
            date_str = datetime.now().strftime('%Y%m%d')
            debug_log_path = get_log_path("debug", f"login_tester_{date_str}.log")
            
            debug_handler = logging.FileHandler(debug_log_path)
            debug_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            debug_handler.setFormatter(formatter)
            
            log.addHandler(debug_handler)
            log.setLevel(logging.DEBUG)
            log.debug(f"Login tester debug logging initialized - writing to {debug_log_path}")
            
        except Exception as e:
            log.warning(f"Failed to setup debug logging: {e}")
    
    async def connect_browser(self) -> bool:
        """Connect to shared Chrome instance"""
        try:
            if self.playwright is None:
                self.playwright = await async_playwright().start()
            
            self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_endpoint)
            log.info(f"✅ Connected to shared Chrome instance at {self.cdp_endpoint}")
            
            if self.browser.contexts:
                self.context = self.browser.contexts[0]
                log.debug("Using existing browser context")
            else:
                self.context = await self.browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                log.debug("Created new browser context")
            
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
    
    async def scan_homepage_for_login_elements(self):
        """Scan homepage for all login-related elements"""
        try:
            log.info("🔍 Scanning homepage for login elements...")
            
            # Navigate to homepage
            await self.page.goto("https://www.poundwholesale.co.uk/", wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            log.info(f"📍 Current URL: {self.page.url}")
            log.info(f"📋 Page Title: {await self.page.title()}")
            
            # Look for "Sign in" text elements
            sign_in_selectors = [
                'text=Sign in',
                'text=Sign In',  
                'text=LOGIN',
                'text=Log in',
                'text=Log In',
                'a:has-text("Sign in")',
                'a:has-text("Sign In")',
                'a:has-text("LOGIN")',
                'a:has-text("Log in")',
                'button:has-text("Sign in")',
                'button:has-text("Sign In")',
                '.sign-in',
                '.login',
                '#login',
                '.header-login',
                '.customer-login'
            ]
            
            found_elements = []
            
            for selector in sign_in_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    for i, element in enumerate(elements):
                        if await element.is_visible():
                            text = await element.text_content()
                            href = await element.get_attribute('href')
                            tag_name = await element.evaluate("el => el.tagName")
                            classes = await element.get_attribute('class')
                            
                            element_info = {
                                "selector": selector,
                                "index": i,
                                "text": text.strip() if text else "",
                                "href": href,
                                "tag_name": tag_name,
                                "classes": classes,
                                "visible": True
                            }
                            found_elements.append(element_info)
                            log.info(f"✅ FOUND: {selector} -> '{text}' (href: {href}, tag: {tag_name})")
                            
                except Exception as e:
                    log.debug(f"Selector '{selector}' failed: {e}")
            
            # Look for "login to view prices" elements
            price_login_selectors = [
                'text=Login to view prices',
                'text=login to view prices',
                'text=Sign in to see prices',
                'text=Login for prices',
                '.price-login',
                '.login-price',
                '.price-requires-login'
            ]
            
            for selector in price_login_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    for i, element in enumerate(elements):
                        if await element.is_visible():
                            text = await element.text_content()
                            
                            element_info = {
                                "selector": selector,
                                "index": i,
                                "text": text.strip() if text else "",
                                "type": "price_login"
                            }
                            found_elements.append(element_info)
                            log.info(f"💰 PRICE LOGIN FOUND: {selector} -> '{text}'")
                            
                except Exception as e:
                    log.debug(f"Price selector '{selector}' failed: {e}")
            
            # Also scan all links in header/navigation
            log.info("🔍 Scanning header/navigation links...")
            nav_links = await self.page.locator('header a, nav a, .header a, .navigation a').all()
            
            for i, link in enumerate(nav_links[:20]):  # First 20 links
                try:
                    if await link.is_visible():
                        text = await link.text_content()
                        href = await link.get_attribute('href')
                        
                        if text and any(keyword in text.lower() for keyword in ['sign', 'login', 'account']):
                            log.info(f"🔗 NAV LINK {i}: '{text}' -> {href}")
                            
                except Exception:
                    continue
            
            log.info(f"📊 Total login elements found: {len(found_elements)}")
            return found_elements
            
        except Exception as e:
            log.error(f"❌ Failed to scan homepage: {e}")
            return []
    
    async def test_specific_product_login_requirement(self, product_url: str):
        """Test a specific product page for login requirements"""
        try:
            log.info(f"🔍 Testing product page: {product_url}")
            
            # Navigate to product page
            await self.page.goto(product_url, wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            log.info(f"📍 Product URL: {self.page.url}")
            log.info(f"📋 Product Title: {await self.page.title()}")
            
            # Look for price elements
            price_selectors = [
                '.price',
                '.product-price',
                '.price-box',
                '.price-final',
                '[data-price]',
                '.regular-price',
                '.special-price'
            ]
            
            prices_found = []
            for selector in price_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    for element in elements:
                        if await element.is_visible():
                            text = await element.text_content()
                            if text and text.strip():
                                prices_found.append({
                                    "selector": selector,
                                    "text": text.strip()
                                })
                                log.info(f"💰 PRICE FOUND: {selector} -> '{text.strip()}'")
                except Exception:
                    continue
            
            # Look for login requirements
            login_required_selectors = [
                'text=Login to view prices',
                'text=login to view prices', 
                'text=Sign in to see prices',
                'text=Login for pricing',
                'text=Member prices',
                '.login-for-price',
                '.price-login-required'
            ]
            
            login_requirements = []
            for selector in login_required_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    for element in elements:
                        if await element.is_visible():
                            text = await element.text_content()
                            login_requirements.append({
                                "selector": selector,
                                "text": text.strip() if text else ""
                            })
                            log.info(f"🔐 LOGIN REQUIRED: {selector} -> '{text}'")
                except Exception:
                    continue
            
            return {
                "product_url": product_url,
                "prices_found": prices_found,
                "login_requirements": login_requirements,
                "has_prices": len(prices_found) > 0,
                "requires_login": len(login_requirements) > 0
            }
            
        except Exception as e:
            log.error(f"❌ Failed to test product page: {e}")
            return None
    
    async def run_comprehensive_login_test(self):
        """Run comprehensive login testing"""
        try:
            log.info("🚀 Starting comprehensive login test...")
            
            # Connect to browser
            if not await self.connect_browser():
                return {"error": "Failed to connect to browser"}
            
            # Test homepage login elements
            homepage_elements = await self.scan_homepage_for_login_elements()
            
            # Test specific product pages
            test_products = [
                "https://www.poundwholesale.co.uk/sealapack-turkey-roasting-bags-2-pack",
                "https://www.poundwholesale.co.uk/elpine-oil-filled-radiator-heater-1500w",
                "https://www.poundwholesale.co.uk/kids-black-beanie-hat"
            ]
            
            product_tests = []
            for product_url in test_products:
                result = await self.test_specific_product_login_requirement(product_url)
                if result:
                    product_tests.append(result)
                await asyncio.sleep(2)  # Rate limiting
            
            results = {
                "timestamp": datetime.now().isoformat(),
                "homepage_login_elements": homepage_elements,
                "product_page_tests": product_tests,
                "summary": {
                    "homepage_login_elements_found": len(homepage_elements),
                    "products_tested": len(product_tests),
                    "products_with_prices": len([p for p in product_tests if p.get("has_prices")]),
                    "products_requiring_login": len([p for p in product_tests if p.get("requires_login")])
                }
            }
            
            log.info(f"✅ Login test complete")
            log.info(f"📊 Homepage login elements: {len(homepage_elements)}")
            log.info(f"📊 Products with prices: {results['summary']['products_with_prices']}/{len(product_tests)}")
            log.info(f"📊 Products requiring login: {results['summary']['products_requiring_login']}/{len(product_tests)}")
            
            return results
            
        except Exception as e:
            log.error(f"❌ Login test failed: {e}")
            return {"error": str(e)}
    
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

async def main():
    """Run login testing"""
    tester = LoginTester()
    
    try:
        results = await tester.run_comprehensive_login_test()
        
        print(f"\n{'='*60}")
        print(f"LOGIN TESTING RESULTS")
        print(f"{'='*60}")
        
        if "error" in results:
            print(f"❌ Error: {results['error']}")
        else:
            print(f"Homepage login elements found: {results['summary']['homepage_login_elements_found']}")
            print(f"Products with visible prices: {results['summary']['products_with_prices']}/{results['summary']['products_tested']}")
            print(f"Products requiring login: {results['summary']['products_requiring_login']}/{results['summary']['products_tested']}")
            
            if results['homepage_login_elements']:
                print(f"\n🔗 LOGIN ELEMENTS FOUND:")
                for element in results['homepage_login_elements'][:5]:  # First 5
                    print(f"  - {element['selector']}: '{element['text']}' (href: {element.get('href')})")
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())