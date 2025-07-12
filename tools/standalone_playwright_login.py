#!/usr/bin/env python3
"""
Standalone Playwright Login Script for PoundWholesale
Reliable login without any vision dependency - pure Playwright selectors
Can be used independently or imported by other scripts.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:
    raise ImportError("Playwright not available. Install with: pip install playwright && playwright install")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

@dataclass
class LoginResult:
    """Result of login attempt"""
    success: bool
    method_used: str = "playwright_selectors"
    error_message: str = ""
    login_detected: bool = False
    price_access_verified: bool = False
    login_duration_seconds: float = 0.0

class StandalonePlaywrightLogin:
    """Standalone Playwright login for PoundWholesale"""
    
    def __init__(self, cdp_port: int = 9222):
        """Initialize login handler"""
        self.cdp_port = cdp_port
        self.cdp_endpoint = f"http://localhost:{cdp_port}"
        
        # Browser state
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # Credentials
        self.email = "info@theblacksmithmarket.com"
        self.password = "0Dqixm9c&"
        self.base_url = "https://www.poundwholesale.co.uk"
        self.login_url = f"{self.base_url}/customer/account/login/"
        
        # Price verification selectors
        self.PRICE_SELECTORS = [
            '.price .amount',
            '.price-current',
            '.product-price .amount',
            '.woocommerce-Price-amount',
            '.price',
            '.product-price',
            '.current-price',
            '.sale-price',
            'span[class*="price"]',
            '.price-box .price',
            '.product-info-price .price',
            'span.price',
            '.price-container .price',
            '.regular-price',
            '.price-final_price'
        ]
    
    async def connect_browser(self) -> bool:
        """Connect to shared Chrome instance via CDP"""
        try:
            log.info("🔗 Connecting to shared Chrome instance...")
            
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
    
    async def check_if_already_logged_in(self) -> bool:
        """Check if user is already logged in by testing price visibility"""
        try:
            log.info("🔍 Checking if already logged in...")
            
            # Navigate to a product page that requires login to see prices
            test_product = f"{self.base_url}/sealapack-turkey-roasting-bags-2-pack"
            await self.page.goto(test_product, wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Look for price elements (main indicator)
            for selector in self.PRICE_SELECTORS:
                try:
                    elements = await self.page.locator(selector).all()
                    for element in elements:
                        if await element.is_visible():
                            text = await element.text_content()
                            if text and '£' in text and len(text.strip()) > 1:
                                log.info(f"✅ Found price element: {text} - already logged in")
                                return True
                except Exception:
                    continue
            
            # Look for logout indicators as secondary check
            logout_indicators = [
                'text=Log out',
                'text=Logout', 
                'text=My Account',
                'text=Welcome',
                '.customer-welcome',
                '.customer-name'
            ]
            
            for indicator in logout_indicators:
                try:
                    element = self.page.locator(indicator).first
                    if await element.is_visible():
                        log.info(f"✅ Found login indicator: {indicator}")
                        return True
                except Exception:
                    continue
            
            log.info("❌ No login indicators found - need to log in")
            return False
            
        except Exception as e:
            log.error(f"Error checking login status: {e}")
            return False
    
    async def perform_login(self) -> LoginResult:
        """Perform login using reliable Playwright selectors"""
        start_time = datetime.now()
        
        try:
            log.info("🔐 Starting Playwright login...")
            
            # Navigate to login page
            log.info(f"📍 Navigating to login page: {self.login_url}")
            await self.page.goto(self.login_url, wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Enhanced email field selectors (in order of preference)
            email_selectors = [
                'input[name="email"]',
                'input[type="email"]', 
                '#email',
                '#customer_email',
                '.email-field',
                'input[id*="email"]',
                'input[placeholder*="email" i]',
                'input[autocomplete="email"]'
            ]
            
            email_filled = False
            for selector in email_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible():
                        await element.click()
                        await asyncio.sleep(0.3)
                        # Clear field first
                        await element.fill("")
                        await element.fill(self.email)
                        log.info(f"✅ Filled email using selector: {selector}")
                        email_filled = True
                        break
                except Exception as e:
                    log.debug(f"Email selector '{selector}' failed: {e}")
            
            if not email_filled:
                return LoginResult(
                    success=False,
                    error_message="Could not find or fill email field",
                    login_duration_seconds=(datetime.now() - start_time).total_seconds()
                )
            
            # Enhanced password field selectors (in order of preference)
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]', 
                '#password',
                '#customer_password',
                '.password-field',
                'input[id*="password"]',
                'input[autocomplete="current-password"]'
            ]
            
            password_filled = False
            for selector in password_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible():
                        await element.click()
                        await asyncio.sleep(0.3)
                        # Clear field first
                        await element.fill("")
                        await element.fill(self.password)
                        log.info(f"✅ Filled password using selector: {selector}")
                        password_filled = True
                        break
                except Exception as e:
                    log.debug(f"Password selector '{selector}' failed: {e}")
            
            if not password_filled:
                return LoginResult(
                    success=False,
                    error_message="Could not find or fill password field",
                    login_duration_seconds=(datetime.now() - start_time).total_seconds()
                )
            
            # Enhanced submit button selectors (in order of preference)
            submit_selectors = [
                'button[type="submit"]',
                '.login-button',
                'input[type="submit"]',
                '#login-btn',
                '#customer_login_btn',
                'button:has-text("Sign In")',
                'button:has-text("Log In")',
                'button:has-text("Login")',
                '.btn-login',
                '.submit-button'
            ]
            
            submit_clicked = False
            for selector in submit_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible():
                        await element.click()
                        log.info(f"✅ Clicked submit using selector: {selector}")
                        submit_clicked = True
                        break
                except Exception as e:
                    log.debug(f"Submit selector '{selector}' failed: {e}")
            
            if not submit_clicked:
                return LoginResult(
                    success=False,
                    error_message="Could not find or click submit button",
                    login_duration_seconds=(datetime.now() - start_time).total_seconds()
                )
            
            # Wait for login to process
            log.info("⏳ Waiting for login to complete...")
            await self.page.wait_for_load_state('networkidle', timeout=15000)
            
            # Verify login success
            login_verified = await self.verify_login_success()
            price_access = await self.verify_price_access()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if login_verified and price_access:
                log.info(f"🎉 Playwright login successful! (took {duration:.1f}s)")
                return LoginResult(
                    success=True,
                    login_detected=True,
                    price_access_verified=True,
                    login_duration_seconds=duration
                )
            elif login_verified:
                log.warning("⚠️ Login detected but price access verification failed")
                return LoginResult(
                    success=True,
                    login_detected=True,
                    price_access_verified=False,
                    error_message="Login successful but price access unverified",
                    login_duration_seconds=duration
                )
            else:
                log.error("❌ Login verification failed")
                return LoginResult(
                    success=False,
                    error_message="Login form submitted but verification failed",
                    login_duration_seconds=duration
                )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            log.error(f"❌ Playwright login failed: {e}")
            return LoginResult(
                success=False,
                error_message=str(e),
                login_duration_seconds=duration
            )
    
    async def verify_login_success(self) -> bool:
        """Verify that login was successful"""
        try:
            # Check URL - should not be on login page anymore
            current_url = self.page.url
            if '/customer/account/login' in current_url:
                log.warning("Still on login page - login may have failed")
                return False
            
            # Look for error messages first
            error_indicators = [
                'text=Invalid login',
                'text=Login failed',
                'text=Incorrect email',
                'text=Incorrect password',
                '.error-message',
                '.alert-error',
                '.message-error'
            ]
            
            for indicator in error_indicators:
                try:
                    element = self.page.locator(indicator).first
                    if await element.is_visible():
                        error_text = await element.text_content()
                        log.warning(f"❌ Login error detected: {error_text}")
                        return False
                except Exception:
                    continue
            
            # Look for success indicators
            success_indicators = [
                'text=Log out',
                'text=Logout', 
                'text=My Account',
                'text=Welcome',
                '.customer-welcome',
                '.customer-name',
                'a[href*="logout"]'
            ]
            
            for indicator in success_indicators:
                try:
                    element = self.page.locator(indicator).first
                    if await element.is_visible():
                        log.info(f"✅ Login success confirmed by indicator: {indicator}")
                        return True
                except Exception:
                    continue
            
            log.warning("⚠️ Login status unclear - no clear success indicators")
            return False
            
        except Exception as e:
            log.error(f"Error verifying login: {e}")
            return False
    
    async def verify_price_access(self) -> bool:
        """Verify that logged-in user can see wholesale prices"""
        try:
            log.info("💰 Verifying price access...")
            
            # Navigate to a test product
            test_product = f"{self.base_url}/sealapack-turkey-roasting-bags-2-pack"
            await self.page.goto(test_product, wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Look for price elements
            for selector in self.PRICE_SELECTORS:
                try:
                    elements = await self.page.locator(selector).all()
                    for element in elements:
                        if await element.is_visible():
                            text = await element.text_content()
                            if text and '£' in text and len(text.strip()) > 1:
                                log.info(f"✅ Price access confirmed: {text.strip()}")
                                return True
                except Exception:
                    continue
            
            # Look for "login required" messages
            login_required_indicators = [
                'text=Login to view prices',
                'text=login to view prices',
                'text=Sign in to see prices'
            ]
            
            for indicator in login_required_indicators:
                try:
                    element = self.page.locator(indicator).first
                    if await element.is_visible():
                        log.warning(f"❌ Still seeing login required message: {indicator}")
                        return False
                except Exception:
                    continue
            
            log.warning("⚠️ No clear price elements found - price access unclear")
            return False
            
        except Exception as e:
            log.error(f"Error verifying price access: {e}")
            return False
    
    async def login_workflow(self) -> LoginResult:
        """Complete login workflow - checks if already logged in first"""
        try:
            # Connect to browser
            if not await self.connect_browser():
                return LoginResult(
                    success=False,
                    error_message="Failed to connect to browser"
                )
            
            # Check if already logged in
            if await self.check_if_already_logged_in():
                log.info("✅ Already logged in!")
                price_verified = await self.verify_price_access()
                return LoginResult(
                    success=True,
                    method_used="already_logged_in",
                    login_detected=True,
                    price_access_verified=price_verified
                )
            
            # Perform login
            return await self.perform_login()
            
        except Exception as e:
            log.error(f"❌ Login workflow failed: {e}")
            return LoginResult(
                success=False,
                error_message=str(e)
            )
    
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

# Convenience function for easy import
async def login_to_poundwholesale(cdp_port: int = 9222) -> LoginResult:
    """
    Convenience function to login to PoundWholesale
    
    Args:
        cdp_port: CDP port for Chrome connection (default 9222)
    
    Returns:
        LoginResult with success status and details
    """
    login_handler = StandalonePlaywrightLogin(cdp_port)
    
    try:
        result = await login_handler.login_workflow()
        return result
    finally:
        await login_handler.cleanup()

async def main():
    """Test the standalone login functionality"""
    print("Testing Standalone Playwright Login...")
    
    login_handler = StandalonePlaywrightLogin()
    
    try:
        result = await login_handler.login_workflow()
        
        print(f"\n{'='*60}")
        print(f"STANDALONE PLAYWRIGHT LOGIN RESULTS")
        print(f"{'='*60}")
        
        print(f"Success: {result.success}")
        print(f"Method: {result.method_used}")
        print(f"Login Detected: {result.login_detected}")
        print(f"Price Access: {result.price_access_verified}")
        print(f"Duration: {result.login_duration_seconds:.1f}s")
        
        if result.error_message:
            print(f"Error: {result.error_message}")
        
        if result.success:
            print("✅ Login test PASSED")
        else:
            print("❌ Login test FAILED")
        
    finally:
        await login_handler.cleanup()

if __name__ == "__main__":
    asyncio.run(main())