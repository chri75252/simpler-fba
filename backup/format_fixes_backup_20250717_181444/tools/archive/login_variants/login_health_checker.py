#!/usr/bin/env python3
"""
Login Health Checker for PoundWholesale
Verifies that login provides access to wholesale prices on actual product pages
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
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

class LoginHealthChecker:
    """Verify login provides wholesale price access"""
    
    # Test product URLs for health check (from our successful extractions)
    TEST_PRODUCT_URLS = [
        "https://www.poundwholesale.co.uk/just-stationery-assorted-colour-numbered-raffle-tickets-1-500",
        "https://www.poundwholesale.co.uk/151-self-adhesive-white-plastic-hooks-12-pack",
        "https://www.poundwholesale.co.uk/farley-mill-boys-beanie-hat-gloves-set-3pc-assorted-colours"
    ]
    
    # Price selectors to test
    PRICE_SELECTORS = [
        '.price-box .price',
        '.product-info-price .price', 
        'span.price',
        '.price-container .price',
        '.regular-price',
        '.price-final_price',
        '.price-including-tax',
        '.price-excluding-tax',
        '[data-price-amount]',
        '.product-price .price'
    ]
    
    # Login indicators
    LOGIN_INDICATORS = [
        'a[href*="logout"]',
        '.customer-welcome',
        '.logged-in',
        'span:contains("Welcome")',
        '.header-links .customer-name'
    ]
    
    # Price access denied indicators
    PRICE_DENIED_INDICATORS = [
        'text=Login to see price',
        'text=Price available upon request', 
        'text=Contact for pricing',
        'text=Member price only',
        'text=Login required',
        '.price-login-required'
    ]
    
    def __init__(self, cdp_port: int = 9222):
        """Initialize health checker"""
        self.cdp_port = cdp_port
        self.cdp_endpoint = f"http://localhost:{cdp_port}"
        
        # Browser state
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Setup logging
        self._setup_debug_logging()
    
    def _setup_debug_logging(self):
        """Setup debug logging"""
        try:
            date_str = datetime.now().strftime('%Y%m%d')
            debug_log_path = get_log_path("debug", f"login_health_check_{date_str}.log")
            
            debug_handler = logging.FileHandler(debug_log_path)
            debug_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            debug_handler.setFormatter(formatter)
            
            log.addHandler(debug_handler)
            log.setLevel(logging.DEBUG)
            log.debug(f"Login health check logging initialized - writing to {debug_log_path}")
            
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
    
    async def check_login_status(self) -> Dict[str, Any]:
        """Check if user is logged in"""
        try:
            log.info("🔍 Checking login status...")
            
            # Navigate to homepage
            await self.page.goto("https://www.poundwholesale.co.uk/", wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Check for login indicators
            login_detected = False
            login_method = ""
            
            for selector in self.LOGIN_INDICATORS:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible():
                        login_detected = True
                        login_method = selector
                        log.info(f"✅ Login detected via selector: {selector}")
                        break
                except Exception:
                    continue
            
            # Get page content for additional checks
            page_content = await self.page.content()
            
            # Check URL
            current_url = self.page.url
            
            result = {
                "login_detected": login_detected,
                "login_method": login_method,
                "current_url": current_url,
                "has_logout_link": "logout" in page_content.lower(),
                "has_welcome_text": "welcome" in page_content.lower(),
                "page_title": await self.page.title()
            }
            
            if login_detected:
                log.info("✅ User appears to be logged in")
            else:
                log.warning("⚠️ No clear login indicators found")
            
            return result
            
        except Exception as e:
            log.error(f"❌ Failed to check login status: {e}")
            return {"error": str(e)}
    
    async def check_price_access(self, product_url: str) -> Dict[str, Any]:
        """Check price access on a specific product page"""
        try:
            log.info(f"🔍 Checking price access on: {product_url}")
            
            # Navigate to product page
            await self.page.goto(product_url, wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            result = {
                "product_url": product_url,
                "page_title": await self.page.title(),
                "price_found": False,
                "price_text": None,
                "price_selector_used": None,
                "price_denied": False,
                "price_denied_message": None,
                "all_text_elements": []
            }
            
            # Check for price denial indicators first
            for indicator in self.PRICE_DENIED_INDICATORS:
                try:
                    element = self.page.locator(indicator).first
                    if await element.is_visible():
                        text = await element.text_content()
                        result["price_denied"] = True
                        result["price_denied_message"] = text.strip()
                        log.warning(f"⚠️ Price access denied: {text.strip()}")
                        return result
                except Exception:
                    continue
            
            # Try to find price using various selectors
            for selector in self.PRICE_SELECTORS:
                try:
                    elements = await self.page.locator(selector).all()
                    for element in elements:
                        if await element.is_visible():
                            text = await element.text_content()
                            if text and text.strip():
                                # Check if it looks like a price
                                clean_text = text.strip()
                                if any(char in clean_text for char in ['£', '$', '€', '.', ',']) and any(char.isdigit() for char in clean_text):
                                    result["price_found"] = True
                                    result["price_text"] = clean_text
                                    result["price_selector_used"] = selector
                                    log.info(f"✅ Price found: {clean_text} (using {selector})")
                                    return result
                except Exception as e:
                    log.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # If no price found, collect all visible text for analysis
            try:
                all_elements = await self.page.locator('*:visible').all()
                texts = []
                for element in all_elements[:50]:  # Limit to first 50 elements
                    try:
                        text = await element.text_content()
                        if text and text.strip() and len(text.strip()) > 2:
                            texts.append(text.strip())
                    except Exception:
                        continue
                result["all_text_elements"] = texts[:20]  # First 20 text elements
            except Exception:
                pass
            
            log.warning(f"⚠️ No price found on {product_url}")
            return result
            
        except Exception as e:
            log.error(f"❌ Failed to check price access for {product_url}: {e}")
            return {
                "product_url": product_url,
                "error": str(e),
                "price_found": False
            }
    
    async def run_full_health_check(self) -> Dict[str, Any]:
        """Run complete login and price access health check"""
        try:
            log.info("🚀 Starting login health check...")
            
            health_check_result = {
                "timestamp": datetime.now().isoformat(),
                "browser_connection": False,
                "login_status": {},
                "price_access_tests": [],
                "overall_status": "unknown",
                "recommendations": []
            }
            
            # Connect to browser
            if not await self.connect_browser():
                health_check_result["overall_status"] = "failed"
                health_check_result["recommendations"].append("Cannot connect to shared Chrome browser")
                return health_check_result
            
            health_check_result["browser_connection"] = True
            
            # Check login status
            login_status = await self.check_login_status()
            health_check_result["login_status"] = login_status
            
            if "error" in login_status:
                health_check_result["overall_status"] = "failed"
                health_check_result["recommendations"].append("Failed to check login status")
                return health_check_result
            
            # Test price access on multiple products
            price_tests_passed = 0
            for product_url in self.TEST_PRODUCT_URLS:
                price_result = await self.check_price_access(product_url)
                health_check_result["price_access_tests"].append(price_result)
                
                if price_result.get("price_found"):
                    price_tests_passed += 1
                
                # Rate limiting
                await asyncio.sleep(2)
            
            # Determine overall status
            if login_status.get("login_detected") and price_tests_passed > 0:
                health_check_result["overall_status"] = "healthy"
                health_check_result["recommendations"].append("Login and price access working correctly")
            elif login_status.get("login_detected"):
                health_check_result["overall_status"] = "partial"
                health_check_result["recommendations"].extend([
                    "Login detected but no wholesale prices visible",
                    "User may need higher permission level for wholesale pricing",
                    "Check if account has wholesale access enabled"
                ])
            else:
                health_check_result["overall_status"] = "failed"
                health_check_result["recommendations"].extend([
                    "No login detected",
                    "Need to login with wholesale account credentials",
                    "Verify login process is working correctly"
                ])
            
            # Save results
            results_file = path_manager.get_output_path("debug", f"login_health_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            os.makedirs(os.path.dirname(results_file), exist_ok=True)
            with open(results_file, 'w') as f:
                json.dump(health_check_result, f, indent=2)
            
            log.info(f"✅ Health check complete. Status: {health_check_result['overall_status']}")
            log.info(f"Results saved to: {results_file}")
            
            return health_check_result
            
        except Exception as e:
            log.error(f"❌ Health check failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "error",
                "error": str(e)
            }
    
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
    """Run login health check"""
    checker = LoginHealthChecker()
    
    try:
        results = await checker.run_full_health_check()
        print(f"\n{'='*50}")
        print(f"LOGIN HEALTH CHECK RESULTS")
        print(f"{'='*50}")
        print(f"Overall Status: {results.get('overall_status', 'unknown')}")
        print(f"Login Detected: {results.get('login_status', {}).get('login_detected', False)}")
        print(f"Price Tests Passed: {sum(1 for test in results.get('price_access_tests', []) if test.get('price_found'))}/{len(results.get('price_access_tests', []))}")
        print(f"\nRecommendations:")
        for rec in results.get('recommendations', []):
            print(f"  - {rec}")
        
    finally:
        await checker.cleanup()

if __name__ == "__main__":
    asyncio.run(main())