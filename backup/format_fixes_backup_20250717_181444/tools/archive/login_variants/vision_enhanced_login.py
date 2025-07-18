#!/usr/bin/env python3
"""
Vision-Enhanced Login System - Intelligent Supplier Login Automation
===================================================================

This system uses GPT-4 Vision API and sophisticated pattern recognition
to automatically detect and interact with login forms on any supplier website.

Inspired by Amazon Playwright extraction patterns with:
- Mouse guidance and clicking
- Vision-based element discovery
- Robust error handling and retries
- Multi-tier fallback system

INTEGRATION:
    - Works with Chrome CDP (port 9222) like Amazon script
    - Uses vision API for element discovery
    - Integrates with LangGraph workflow
    - Supports multiple login patterns (buttons, forms, links)
"""

import asyncio
import base64
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import openai
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeoutError

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_SUPPLIER", "")
OPENAI_MODEL_VISION = os.getenv("OPENAI_MODEL_SUPPLIER", "gpt-4o-mini-2024-07-18")

if not OPENAI_API_KEY:
    log.error("🚨 OPENAI_API_KEY not found in environment variables!")
    log.error("Please set OPENAI_API_KEY environment variable")

# Configuration
DEFAULT_NAVIGATION_TIMEOUT = 60000  # 60 seconds
POST_NAVIGATION_STABILIZE_WAIT = 3   # 3 seconds
LOGIN_ATTEMPT_WAIT = 2               # 2 seconds between attempts

class VisionEnhancedLogin:
    """Vision-powered login automation system"""
    
    def __init__(self, supplier_url: str, chrome_debug_port: int = 9222):
        self.supplier_url = supplier_url
        self.chrome_debug_port = chrome_debug_port
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        # Initialize OpenAI client
        self.ai_client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        
        # Login detection patterns
        self.login_indicators = [
            # Sign In buttons/links
            "a:has-text('Sign In')",
            "button:has-text('Sign In')",
            "a:has-text('Login')", 
            "button:has-text('Login')",
            "a:has-text('Log In')",
            "button:has-text('Log In')",
            
            # Account/User links
            "a:has-text('Account')",
            "a:has-text('My Account')",
            "a[href*='login']",
            "a[href*='signin']",
            "a[href*='account']",
            
            # Common login selectors
            ".login-link",
            ".signin-link",
            "#login-button",
            "#signin-button",
            ".account-link"
        ]
        
        # Logout detection (indicates already logged in)
        self.logout_indicators = [
            "a:has-text('Logout')",
            "a:has-text('Log Out')", 
            "a:has-text('Sign Out')",
            "a[href*='logout']",
            ".logout-link"
        ]
        
        log.info(f"🔐 Vision Enhanced Login initialized for {supplier_url}")
    
    async def connect(self) -> bool:
        """Connect to Chrome debug instance - inspired by Amazon script"""
        try:
            log.info(f"Connecting to Chrome browser on debug port {self.chrome_debug_port}")
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.connect_over_cdp(f"http://localhost:{self.chrome_debug_port}")
            log.info(f"Successfully connected to Chrome on port {self.chrome_debug_port}")
            
            # Use existing pages instead of creating new ones (like Amazon script)
            all_pages = self.browser.contexts[0].pages if self.browser.contexts and len(self.browser.contexts) > 0 else []
            
            if all_pages:
                log.info(f"Found {len(all_pages)} existing pages")
                self.page = all_pages[0]
                log.info(f"Using existing page: {self.page.url}")
                await self.page.bring_to_front()
            else:
                log.info("No existing pages found. Creating new page")
                self.page = await self.browser.new_page()
                
            return True
            
        except Exception as e:
            log.error(f"Failed to connect to Chrome on port {self.chrome_debug_port}: {e}")
            log.error("Ensure Chrome is running with --remote-debugging-port=9222")
            return False
    
    async def check_login_status(self) -> bool:
        """Check if already logged in by looking for logout indicators"""
        try:
            if not self.page:
                return False
                
            log.info("🔍 Checking login status...")
            
            # Look for logout indicators (means we're logged in)
            for selector in self.logout_indicators:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        log.info(f"✅ Already logged in (found logout element: {selector})")
                        return True
                except Exception:
                    continue
            
            log.info("❌ Not logged in - no logout indicators found")
            return False
            
        except Exception as e:
            log.warning(f"Error checking login status: {e}")
            return False
    
    async def navigate_to_supplier(self) -> bool:
        """Navigate to supplier website with retries (like Amazon script)"""
        try:
            if not self.page:
                log.error("No page available for navigation")
                return False
            
            log.info(f"🌐 Navigating to {self.supplier_url}")
            
            # Multi-attempt navigation like Amazon script
            navigation_successful = False
            for attempt in range(3):
                try:
                    await self.page.goto(self.supplier_url, wait_until="domcontentloaded", timeout=DEFAULT_NAVIGATION_TIMEOUT)
                    navigation_successful = True
                    break
                except Exception as e:
                    log.warning(f"Navigation attempt {attempt+1} for {self.supplier_url} failed: {e}")
                    if attempt < 2:
                        await asyncio.sleep(5 + attempt * 5)
            
            if not navigation_successful:
                log.error(f"Navigation failed for {self.supplier_url} after multiple attempts")
                return False
            
            # Stabilization wait like Amazon script
            log.info(f"Page loaded. Waiting {POST_NAVIGATION_STABILIZE_WAIT}s for stabilization...")
            await asyncio.sleep(POST_NAVIGATION_STABILIZE_WAIT)
            
            return True
            
        except Exception as e:
            log.error(f"Failed to navigate to supplier: {e}")
            return False
    
    async def find_login_entry_points(self) -> List[Dict[str, Any]]:
        """Find all possible login entry points using vision and heuristics"""
        try:
            log.info("🔍 Searching for login entry points...")
            
            entry_points = []
            
            # 1. Heuristic search for common login patterns
            for selector in self.login_indicators:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for i, element in enumerate(elements):
                        if element:
                            text = await element.text_content()
                            href = await element.get_attribute('href') if await element.get_attribute('href') else ''
                            
                            entry_points.append({
                                'type': 'heuristic',
                                'selector': selector,
                                'index': i,
                                'text': text.strip() if text else '',
                                'href': href,
                                'element': element
                            })
                            
                            log.info(f"Found login entry point: {selector} - '{text.strip() if text else 'No text'}' - {href}")
                except Exception:
                    continue
            
            # 2. Vision-based discovery if we have AI client
            if self.ai_client and len(entry_points) == 0:
                log.info("🔍 No heuristic matches - trying vision-based discovery...")
                vision_entry_points = await self._vision_discover_login_elements()
                entry_points.extend(vision_entry_points)
            
            log.info(f"Found {len(entry_points)} total login entry points")
            return entry_points
            
        except Exception as e:
            log.error(f"Error finding login entry points: {e}")
            return []
    
    async def _vision_discover_login_elements(self) -> List[Dict[str, Any]]:
        """Use GPT-4 Vision to discover login elements"""
        try:
            if not self.ai_client:
                return []
            
            log.info("📸 Taking screenshot for vision analysis...")
            
            # Take screenshot
            screenshot_data = await self.page.screenshot(full_page=True)
            screenshot_b64 = base64.b64encode(screenshot_data).decode()
            
            # Vision prompt for login detection
            prompt = """
            Analyze this webpage screenshot and identify ALL possible ways to access a login form.
            Look for:
            1. "Sign In", "Login", "Log In" buttons or links (top-right corner is common)
            2. "Account", "My Account" links that lead to login
            3. Any small login form already visible on the page
            4. Price display areas that might show login prompts instead of prices
            
            Return a JSON array with this format:
            [
                {
                    "type": "vision",
                    "description": "Sign In button in top-right corner",
                    "location": "top-right",
                    "text_visible": "Sign In",
                    "likely_selector": "button:has-text('Sign In')",
                    "confidence": 0.9
                }
            ]
            
            Focus on the most obvious login entry points. Return empty array if none found.
            """
            
            response = await asyncio.to_thread(
                self.ai_client.chat.completions.create,
                model=OPENAI_MODEL_VISION,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            vision_response = response.choices[0].message.content
            log.info(f"Vision response: {vision_response}")
            
            # Parse JSON response
            try:
                vision_entry_points = json.loads(vision_response)
                if isinstance(vision_entry_points, list):
                    log.info(f"Vision discovered {len(vision_entry_points)} login entry points")
                    return vision_entry_points
            except json.JSONDecodeError:
                log.warning("Could not parse vision response as JSON")
            
            return []
            
        except Exception as e:
            log.error(f"Vision discovery failed: {e}")
            return []
    
    async def attempt_login_via_entry_point(self, entry_point: Dict[str, Any], email: str, password: str) -> bool:
        """Attempt login through a specific entry point"""
        try:
            log.info(f"🚀 Attempting login via: {entry_point.get('description', entry_point.get('selector', 'unknown'))}")
            
            # Click the entry point if it's a heuristic match
            if entry_point['type'] == 'heuristic' and 'element' in entry_point:
                element = entry_point['element']
                
                # Get element position for mouse guidance (like Amazon script)
                box = await element.bounding_box()
                if box:
                    # Move mouse to element and click (inspired by Amazon script)
                    await self.page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                    await asyncio.sleep(0.5)
                    await element.click()
                    log.info(f"Clicked login element: {entry_point['selector']}")
                else:
                    await element.click()
                    log.info(f"Clicked login element (no box): {entry_point['selector']}")
                
                await asyncio.sleep(LOGIN_ATTEMPT_WAIT)
            
            # Vision-based entry points - try to find and click based on description
            elif entry_point['type'] == 'vision':
                likely_selector = entry_point.get('likely_selector', '')
                if likely_selector:
                    try:
                        vision_element = await self.page.query_selector(likely_selector)
                        if vision_element:
                            await vision_element.click()
                            log.info(f"Clicked vision-discovered element: {likely_selector}")
                            await asyncio.sleep(LOGIN_ATTEMPT_WAIT)
                    except Exception as e:
                        log.warning(f"Could not click vision element: {e}")
                        return False
            
            # Now look for login form fields
            return await self._fill_login_form(email, password)
            
        except Exception as e:
            log.error(f"Login attempt via entry point failed: {e}")
            return False
    
    async def _fill_login_form(self, email: str, password: str) -> bool:
        """Find and fill login form fields"""
        try:
            log.info("🔍 Looking for login form fields...")
            
            # Common email/username field selectors
            email_selectors = [
                "input[type='email']",
                "input[name*='email']",
                "input[name*='username']",
                "input[name*='user']",
                "input[id*='email']",
                "input[id*='username']",
                "input[id*='user']",
                "input[placeholder*='email']",
                "input[placeholder*='Email']",
                "#email",
                "#username",
                "#user"
            ]
            
            # Common password field selectors
            password_selectors = [
                "input[type='password']",
                "input[name*='password']",
                "input[name*='pass']",
                "input[id*='password']",
                "input[id*='pass']",
                "#password",
                "#pass"
            ]
            
            # Submit button selectors
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Login')",
                "button:has-text('Sign In')",
                "button:has-text('Log In')",
                ".login-button",
                ".signin-button",
                "#login-submit",
                "#signin-submit"
            ]
            
            # Find and fill email field
            email_filled = False
            for selector in email_selectors:
                try:
                    email_field = await self.page.query_selector(selector)
                    if email_field and await email_field.is_visible():
                        await email_field.fill(email)
                        log.info(f"✅ Filled email field: {selector}")
                        email_filled = True
                        break
                except Exception:
                    continue
            
            if not email_filled:
                log.error("❌ Could not find email field")
                return False
            
            # Find and fill password field
            password_filled = False
            for selector in password_selectors:
                try:
                    password_field = await self.page.query_selector(selector)
                    if password_field and await password_field.is_visible():
                        await password_field.fill(password)
                        log.info(f"✅ Filled password field: {selector}")
                        password_filled = True
                        break
                except Exception:
                    continue
            
            if not password_filled:
                log.error("❌ Could not find password field")
                return False
            
            # Submit the form
            submitted = False
            for selector in submit_selectors:
                try:
                    submit_button = await self.page.query_selector(selector)
                    if submit_button and await submit_button.is_visible():
                        await submit_button.click()
                        log.info(f"✅ Clicked submit button: {selector}")
                        submitted = True
                        break
                except Exception:
                    continue
            
            if not submitted:
                # Try pressing Enter on password field as fallback
                try:
                    for selector in password_selectors:
                        password_field = await self.page.query_selector(selector)
                        if password_field:
                            await password_field.press('Enter')
                            log.info("✅ Pressed Enter on password field")
                            submitted = True
                            break
                except Exception:
                    pass
            
            if not submitted:
                log.error("❌ Could not submit login form")
                return False
            
            # Wait for navigation/response
            await asyncio.sleep(5)
            
            # Check if login was successful
            return await self.check_login_status()
            
        except Exception as e:
            log.error(f"Error filling login form: {e}")
            return False
    
    async def perform_full_login(self, email: str, password: str) -> bool:
        """Perform complete login workflow with multiple fallbacks"""
        try:
            log.info("🚀 Starting full login workflow...")
            
            # 1. Connect to browser
            if not await self.connect():
                log.error("❌ Could not connect to browser")
                return False
            
            # 2. Navigate to supplier
            if not await self.navigate_to_supplier():
                log.error("❌ Could not navigate to supplier")
                return False
            
            # 3. Check if already logged in
            if await self.check_login_status():
                log.info("✅ Already logged in!")
                return True
            
            # 4. Find all login entry points
            entry_points = await self.find_login_entry_points()
            
            if not entry_points:
                log.error("❌ No login entry points found")
                return False
            
            # 5. Try each entry point until one works
            for i, entry_point in enumerate(entry_points):
                log.info(f"🔄 Trying entry point {i+1}/{len(entry_points)}")
                
                success = await self.attempt_login_via_entry_point(entry_point, email, password)
                
                if success:
                    log.info("🎉 LOGIN SUCCESSFUL!")
                    return True
                else:
                    log.warning(f"Entry point {i+1} failed, trying next...")
                    # Navigate back to start for next attempt
                    await self.navigate_to_supplier()
            
            log.error("❌ All login attempts failed")
            return False
            
        except Exception as e:
            log.error(f"Full login workflow failed: {e}")
            return False

# Standalone function for integration with other scripts
async def vision_enhanced_login(supplier_url: str, email: str, password: str, page: Optional[Page] = None) -> bool:
    """
    Standalone vision-enhanced login function
    
    Args:
        supplier_url: Supplier website URL
        email: Login email
        password: Login password  
        page: Optional existing Playwright page
        
    Returns:
        bool: True if login successful
    """
    try:
        login_system = VisionEnhancedLogin(supplier_url)
        
        if page:
            login_system.page = page
            # Check if already logged in
            if await login_system.check_login_status():
                return True
        
        return await login_system.perform_full_login(email, password)
        
    except Exception as e:
        log.error(f"Standalone vision login failed: {e}")
        return False

if __name__ == "__main__":
    # Test the vision login system
    async def test_vision_login():
        supplier_url = "https://www.poundwholesale.co.uk/"
        email = input("Enter email: ").strip()
        password = input("Enter password: ").strip()
        
        if email and password:
            login_system = VisionEnhancedLogin(supplier_url)
            success = await login_system.perform_full_login(email, password)
            
            if success:
                log.info("✅ Vision login test completed successfully")
            else:
                log.error("❌ Vision login test failed")
        else:
            log.error("Email and password required for testing")
    
    asyncio.run(test_vision_login())