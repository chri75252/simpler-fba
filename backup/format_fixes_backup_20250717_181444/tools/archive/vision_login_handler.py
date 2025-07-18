#!/usr/bin/env python3
"""
Vision-Assisted Login Handler for PoundWholesale
Uses GPT-4.1-mini Vision to identify and interact with login forms
Handles wholesale account authentication for price extraction
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
from utils import path_manager

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
class LoginResult:
    """Result of login attempt"""
    success: bool
    method_used: str = ""
    screenshot_path: Optional[str] = None
    error_message: Optional[str] = None
    login_detected: bool = False
    price_access_verified: bool = False

class VisionLoginHandler:
    """Vision-assisted login handler for wholesale accounts"""
    
    def __init__(self, openai_client: OpenAI, cdp_port: int = 9222):
        """Initialize Vision login handler"""
        self.openai_client = openai_client
        self.cdp_port = cdp_port
        self.cdp_endpoint = f"http://localhost:{cdp_port}"
        
        # Browser state
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # Login credentials from config
        self.email = "info@theblacksmithmarket.com"
        self.password = "0Dqixm9c&"
        self.login_url = "https://www.poundwholesale.co.uk/customer/account/login/"
        
        # Setup logging
        self._setup_debug_logging()
    
    def _setup_debug_logging(self):
        """Setup debug logging"""
        try:
            date_str = datetime.now().strftime('%Y%m%d')
            debug_log_path = path_manager.get_log_path("debug", f"vision_login_{date_str}.log")
            
            debug_handler = logging.FileHandler(debug_log_path)
            debug_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            debug_handler.setFormatter(formatter)
            
            log.addHandler(debug_handler)
            log.setLevel(logging.DEBUG)
            log.debug(f"Vision login debug logging initialized - writing to {debug_log_path}")
            
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
    
    async def check_if_already_logged_in(self) -> bool:
        """Check if user is already logged in"""
        try:
            log.info("🔍 Checking if already logged in...")
            
            # Navigate to a product page that requires login to see prices
            test_product = "https://www.poundwholesale.co.uk/sealapack-turkey-roasting-bags-2-pack"
            await self.page.goto(test_product, wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Look for logout indicators
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
            
            # Look for price elements (if logged in, prices should be visible)
            price_selectors = [
                '.price-box .price',
                '.product-info-price .price',
                'span.price',
                '.price-container .price'
            ]
            
            for selector in price_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    for element in elements:
                        if await element.is_visible():
                            text = await element.text_content()
                            if text and '£' in text and len(text.strip()) > 1:
                                log.info(f"✅ Found price element: {text} - likely logged in")
                                return True
                except Exception:
                    continue
            
            log.info("❌ No login indicators found - need to log in")
            return False
            
        except Exception as e:
            log.error(f"Error checking login status: {e}")
            return False
    
    async def vision_assisted_login(self) -> LoginResult:
        """Use Vision API to identify and fill login form"""
        try:
            log.info("🚀 Starting Vision-assisted login process...")
            
            # Navigate to login page
            log.info(f"📍 Navigating to login page: {self.login_url}")
            await self.page.goto(self.login_url, wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Take screenshot for Vision API
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot_path = path_manager.get_output_path("FBA_ANALYSIS", "navigation_dumps", "poundwholesale-co-uk", f"login_page_{timestamp}.png")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            
            await self.page.screenshot(path=screenshot_path, full_page=True)
            log.info(f"📸 Screenshot saved: {screenshot_path}")
            
            # Encode screenshot for Vision API
            with open(screenshot_path, "rb") as image_file:
                screenshot_base64 = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Vision API call to identify login elements
            log.info("🔍 Calling Vision API to identify login form elements...")
            
            vision_prompt = """
You are helping to automate login to a wholesale website. 

Please analyze this login page screenshot and identify the login form elements.

Look for:
1. Email/username input field
2. Password input field  
3. Login/Submit button

For each element found, provide the pixel coordinates where I should click to interact with it.

Respond in this exact JSON format:
{
    "email_field": {"x": 123, "y": 456, "found": true},
    "password_field": {"x": 234, "y": 567, "found": true}, 
    "login_button": {"x": 345, "y": 678, "found": true}
}

If any element is not found, set "found": false and omit x,y coordinates.
Only return the JSON, no other text.
"""
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
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
            )
            
            vision_result = response.choices[0].message.content.strip()
            log.info(f"Vision API response: {vision_result}")
            
            # Parse Vision response
            try:
                # Remove markdown formatting if present
                if vision_result.startswith("```json"):
                    vision_result = vision_result.replace("```json", "").replace("```", "").strip()
                vision_data = json.loads(vision_result)
                
                # Fill in the login form using Vision coordinates
                if vision_data.get("email_field", {}).get("found"):
                    email_coords = vision_data["email_field"]
                    log.info(f"✅ Clicking email field at ({email_coords['x']}, {email_coords['y']})")
                    await self.page.mouse.click(email_coords['x'], email_coords['y'])
                    await asyncio.sleep(0.5)
                    
                    # Clear field and type email
                    await self.page.keyboard.press('Control+a')
                    await self.page.keyboard.type(self.email)
                    log.info(f"📧 Entered email: {self.email}")
                    
                if vision_data.get("password_field", {}).get("found"):
                    password_coords = vision_data["password_field"]
                    log.info(f"✅ Clicking password field at ({password_coords['x']}, {password_coords['y']})")
                    await self.page.mouse.click(password_coords['x'], password_coords['y'])
                    await asyncio.sleep(0.5)
                    
                    # Clear field and type password
                    await self.page.keyboard.press('Control+a')
                    await self.page.keyboard.type(self.password)
                    log.info("🔐 Entered password")
                    
                if vision_data.get("login_button", {}).get("found"):
                    login_coords = vision_data["login_button"]
                    log.info(f"✅ Clicking login button at ({login_coords['x']}, {login_coords['y']})")
                    await self.page.mouse.click(login_coords['x'], login_coords['y'])
                    
                    # Wait for login to process
                    await self.page.wait_for_load_state('networkidle', timeout=15000)
                    log.info("⏳ Waiting for login to complete...")
                    
                    # Verify login success
                    login_success = await self.verify_login_success()
                    
                    if login_success:
                        log.info("🎉 Vision-assisted login successful!")
                        
                        # Take screenshot of successful login
                        success_screenshot = path_manager.get_output_path("FBA_ANALYSIS", "navigation_dumps", "poundwholesale-co-uk", f"login_success_{timestamp}.png")
                        await self.page.screenshot(path=success_screenshot, full_page=True)
                        
                        return LoginResult(
                            success=True,
                            method_used="vision_assisted",
                            screenshot_path=success_screenshot,
                            login_detected=True,
                            price_access_verified=await self.verify_price_access()
                        )
                    else:
                        return LoginResult(
                            success=False,
                            method_used="vision_assisted",
                            screenshot_path=screenshot_path,
                            error_message="Login form filled but verification failed",
                            login_detected=False
                        )
                else:
                    return LoginResult(
                        success=False,
                        method_used="vision_assisted",
                        screenshot_path=screenshot_path,
                        error_message="Vision API could not identify all required login elements"
                    )
                    
            except json.JSONDecodeError as e:
                log.error(f"Failed to parse Vision API response as JSON: {e}")
                return LoginResult(
                    success=False,
                    method_used="vision_assisted",
                    screenshot_path=screenshot_path,
                    error_message=f"Invalid JSON response from Vision API: {vision_result}"
                )
                
        except Exception as e:
            log.error(f"❌ Vision-assisted login failed: {e}")
            return LoginResult(
                success=False,
                method_used="vision_assisted",
                error_message=str(e)
            )
    
    async def fallback_selector_login(self) -> LoginResult:
        """Fallback login using traditional selectors"""
        try:
            log.info("🔄 Attempting fallback selector-based login...")
            
            # Navigate to login page
            await self.page.goto(self.login_url, wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Email field selectors
            email_selectors = [
                'input[name="email"]',
                'input[type="email"]', 
                '#email',
                '.email-field',
                'input[id*="email"]',
                'input[placeholder*="email" i]'
            ]
            
            email_filled = False
            for selector in email_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible():
                        await element.click()
                        await element.fill(self.email)
                        log.info(f"✅ Filled email using selector: {selector}")
                        email_filled = True
                        break
                except Exception as e:
                    log.debug(f"Email selector '{selector}' failed: {e}")
            
            # Password field selectors
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]', 
                '#password',
                '.password-field',
                'input[id*="password"]'
            ]
            
            password_filled = False
            for selector in password_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible():
                        await element.click()
                        await element.fill(self.password)
                        log.info(f"✅ Filled password using selector: {selector}")
                        password_filled = True
                        break
                except Exception as e:
                    log.debug(f"Password selector '{selector}' failed: {e}")
            
            # Submit button selectors
            submit_selectors = [
                'button[type="submit"]',
                '.login-button',
                'input[type="submit"]',
                '#login-btn',
                'button:has-text("Sign In")',
                'button:has-text("Log In")',
                'button:has-text("Login")'
            ]
            
            if email_filled and password_filled:
                for selector in submit_selectors:
                    try:
                        element = self.page.locator(selector).first
                        if await element.is_visible():
                            await element.click()
                            log.info(f"✅ Clicked submit using selector: {selector}")
                            
                            # Wait for login to process
                            await self.page.wait_for_load_state('networkidle', timeout=15000)
                            
                            # Verify login success
                            login_success = await self.verify_login_success()
                            
                            if login_success:
                                log.info("🎉 Fallback selector login successful!")
                                return LoginResult(
                                    success=True,
                                    method_used="fallback_selectors",
                                    login_detected=True,
                                    price_access_verified=await self.verify_price_access()
                                )
                            break
                    except Exception as e:
                        log.debug(f"Submit selector '{selector}' failed: {e}")
            
            return LoginResult(
                success=False,
                method_used="fallback_selectors",
                error_message="Could not fill form or login failed"
            )
            
        except Exception as e:
            log.error(f"❌ Fallback selector login failed: {e}")
            return LoginResult(
                success=False,
                method_used="fallback_selectors",
                error_message=str(e)
            )
    
    async def verify_login_success(self) -> bool:
        """Verify that login was successful"""
        try:
            # Check URL - should not be on login page anymore
            current_url = self.page.url
            if '/customer/account/login' in current_url:
                log.warning("Still on login page - login may have failed")
                return False
            
            # Look for logout/account indicators
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
            
            # Check for error messages
            error_indicators = [
                'text=Invalid login',
                'text=Login failed',
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
            
            log.info("⚠️ Login status unclear - no clear success or error indicators")
            return False
            
        except Exception as e:
            log.error(f"Error verifying login: {e}")
            return False
    
    async def verify_price_access(self) -> bool:
        """Verify that logged-in user can see wholesale prices"""
        try:
            log.info("💰 Verifying price access...")
            
            # Navigate to a test product
            test_product = "https://www.poundwholesale.co.uk/sealapack-turkey-roasting-bags-2-pack"
            await self.page.goto(test_product, wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Look for price elements
            price_selectors = [
                '.price-box .price',
                '.product-info-price .price',
                'span.price',
                '.price-container .price',
                '.regular-price',
                '.price-final_price'
            ]
            
            for selector in price_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    for element in elements:
                        if await element.is_visible():
                            text = await element.text_content()
                            if text and '£' in text and len(text.strip()) > 1:
                                log.info(f"✅ Found price: {text.strip()} - wholesale access confirmed")
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
    
    async def perform_login(self) -> LoginResult:
        """Main login orchestrator - tries Vision first, then fallback"""
        try:
            log.info("🚀 Starting comprehensive login process...")
            
            # Connect to browser
            if not await self.connect_browser():
                return LoginResult(
                    success=False,
                    error_message="Failed to connect to browser"
                )
            
            # Check if already logged in
            if await self.check_if_already_logged_in():
                log.info("✅ Already logged in!")
                return LoginResult(
                    success=True,
                    method_used="already_logged_in",
                    login_detected=True,
                    price_access_verified=await self.verify_price_access()
                )
            
            # Try Vision-assisted login first
            log.info("🎯 Attempting Vision-assisted login...")
            vision_result = await self.vision_assisted_login()
            
            if vision_result.success:
                return vision_result
            
            # Fallback to selector-based login
            log.info("🔄 Vision login failed, trying fallback selectors...")
            fallback_result = await self.fallback_selector_login()
            
            return fallback_result
            
        except Exception as e:
            log.error(f"❌ Login process failed: {e}")
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

async def main():
    """Test the Vision login handler"""
    # Load OpenAI client
    openai_client = OpenAI()
    
    handler = VisionLoginHandler(openai_client)
    
    try:
        result = await handler.perform_login()
        
        print(f"\n{'='*60}")
        print(f"VISION LOGIN RESULTS")
        print(f"{'='*60}")
        
        print(f"Success: {result.success}")
        print(f"Method: {result.method_used}")
        print(f"Login Detected: {result.login_detected}")
        print(f"Price Access: {result.price_access_verified}")
        
        if result.screenshot_path:
            print(f"Screenshot: {result.screenshot_path}")
        
        if result.error_message:
            print(f"Error: {result.error_message}")
        
    finally:
        await handler.cleanup()

if __name__ == "__main__":
    asyncio.run(main())