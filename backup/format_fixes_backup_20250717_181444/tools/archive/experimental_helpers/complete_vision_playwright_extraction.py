#!/usr/bin/env python3
"""
Complete Vision + Playwright Extraction Script
Re-runs the complete workflow to extract ALL required metrics:
- title, price, EAN/barcode, out of stock status, product URL

Includes refined Playwright login snippet that works without vision dependency.
"""

import asyncio
import json
import logging
import os
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Add project paths
sys.path.insert(0, os.path.dirname(__file__))
from utils.path_manager import get_log_path, path_manager

# Playwright imports
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:
    raise ImportError("Playwright not available. Install with: pip install playwright && playwright install")

# OpenAI for Vision API (if needed)
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

@dataclass
class ExtractionResult:
    """Complete extraction result with all required metrics"""
    success: bool
    product_url: str = ""
    title: str = ""
    price: str = ""
    ean_barcode: str = ""
    stock_status: str = ""
    extraction_method: str = ""
    error_message: str = ""
    login_method: str = ""
    extraction_timestamp: str = ""

class CompleteVisionPlaywrightExtractor:
    """Complete extractor with vision + playwright capabilities"""
    
    def __init__(self):
        """Initialize the complete extractor"""
        self.cdp_port = 9222
        self.cdp_endpoint = f"http://localhost:{self.cdp_port}"
        
        # Browser state
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # OpenAI client (load if needed)
        try:
            self.openai_client = OpenAI()
        except Exception as e:
            log.warning(f"OpenAI client not available: {e}")
            self.openai_client = None
        
        # Credentials
        self.email = "info@theblacksmithmarket.com"
        self.password = "0Dqixm9c&"
        self.base_url = "https://www.poundwholesale.co.uk"
        self.login_url = f"{self.base_url}/customer/account/login/"
        
        # Setup logging
        self._setup_debug_logging()
        
        # Product selectors (refined from previous analysis)
        self.TITLE_SELECTORS = [
            'h1.product-title',
            'h1.entry-title', 
            '.product-title',
            'h1.product-name',
            '.product-name',
            'h1',
            '.page-title'
        ]
        
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
        
        self.STOCK_SELECTORS = [
            '.stock-status',
            '.availability',
            '.in-stock',
            '.out-of-stock',
            '.stock-indicator',
            '.product-availability',
            '.inventory-status',
            'span[class*="stock"]',
            '.stock-level'
        ]
        
        self.EAN_PATTERNS = [
            r'EAN[:\s]*([0-9]{8,14})',
            r'Barcode[:\s]*([0-9]{8,14})',
            r'UPC[:\s]*([0-9]{8,14})',
            r'GTIN[:\s]*([0-9]{8,14})',
            r'Product Code[:\s]*([0-9]{8,14})',
            r'SKU[:\s]*([A-Z0-9]{8,})',
            r'Item Code[:\s]*([0-9]{8,14})'
        ]
    
    def _setup_debug_logging(self):
        """Setup debug logging"""
        try:
            date_str = datetime.now().strftime('%Y%m%d')
            debug_log_path = get_log_path("debug", f"complete_extraction_{date_str}.log")
            
            debug_handler = logging.FileHandler(debug_log_path)
            debug_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            debug_handler.setFormatter(formatter)
            
            log.addHandler(debug_handler)
            log.setLevel(logging.DEBUG)
            log.debug(f"Complete extraction debug logging initialized - writing to {debug_log_path}")
            
        except Exception as e:
            log.warning(f"Failed to setup debug logging: {e}")
    
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
            
            # Look for price elements first (main indicator)
            for selector in self.PRICE_SELECTORS:
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
    
    async def playwright_login_without_vision(self) -> str:
        """Refined Playwright login that works without vision dependency"""
        try:
            log.info("🔐 Starting Playwright login (no vision dependency)...")
            
            # Navigate to login page
            log.info(f"📍 Navigating to login page: {self.login_url}")
            await self.page.goto(self.login_url, wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Enhanced email field selectors
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
                        await asyncio.sleep(0.5)
                        # Clear field first
                        await element.fill("")
                        await element.fill(self.email)
                        log.info(f"✅ Filled email using selector: {selector}")
                        email_filled = True
                        break
                except Exception as e:
                    log.debug(f"Email selector '{selector}' failed: {e}")
            
            # Enhanced password field selectors
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
                        await asyncio.sleep(0.5)
                        # Clear field first
                        await element.fill("")
                        await element.fill(self.password)
                        log.info(f"✅ Filled password using selector: {selector}")
                        password_filled = True
                        break
                except Exception as e:
                    log.debug(f"Password selector '{selector}' failed: {e}")
            
            # Enhanced submit button selectors
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
            
            if email_filled and password_filled:
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
                
                if submit_clicked:
                    # Wait for login to process
                    log.info("⏳ Waiting for login to complete...")
                    await self.page.wait_for_load_state('networkidle', timeout=15000)
                    
                    # Verify login success
                    if await self.verify_login_success():
                        log.info("🎉 Playwright login successful!")
                        return "playwright_login_success"
                    else:
                        log.warning("⚠️ Login form submitted but verification failed")
                        return "login_verification_failed"
                else:
                    log.error("❌ Could not find or click submit button")
                    return "submit_button_not_found"
            else:
                missing = []
                if not email_filled:
                    missing.append("email")
                if not password_filled:
                    missing.append("password")
                log.error(f"❌ Could not fill required fields: {', '.join(missing)}")
                return f"field_fill_failed_{','.join(missing)}"
            
        except Exception as e:
            log.error(f"❌ Playwright login failed: {e}")
            return f"login_exception_{str(e)}"
    
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
            
            # Final check: try to access a price-protected page
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
            
            log.warning("⚠️ Login status unclear - no clear success indicators")
            return False
            
        except Exception as e:
            log.error(f"Error verifying login: {e}")
            return False
    
    async def extract_all_product_metrics(self, product_url: str) -> ExtractionResult:
        """Extract ALL required metrics from a product page"""
        try:
            log.info(f"🔍 Extracting ALL metrics from: {product_url}")
            
            # Navigate to product page
            await self.page.goto(product_url, wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Get page content for text analysis
            html_content = await self.page.content()
            
            # Initialize result
            result = ExtractionResult(
                success=False,
                product_url=product_url,
                extraction_timestamp=datetime.now().isoformat(),
                extraction_method="complete_playwright_extraction"
            )
            
            # Extract Title
            result.title = await self._extract_title()
            log.info(f"✅ Title: {result.title}")
            
            # Extract Price
            result.price = await self._extract_price()
            log.info(f"💰 Price: {result.price}")
            
            # Extract EAN/Barcode
            result.ean_barcode = await self._extract_ean_barcode(html_content)
            log.info(f"🏷️ EAN/Barcode: {result.ean_barcode}")
            
            # Extract Stock Status
            result.stock_status = await self._extract_stock_status(html_content)
            log.info(f"📦 Stock: {result.stock_status}")
            
            # Determine success
            metrics_found = sum([
                bool(result.title),
                bool(result.price) and 'not found' not in result.price.lower(),
                bool(result.ean_barcode),
                bool(result.stock_status)
            ])
            
            result.success = metrics_found >= 2  # At least 2 out of 4 metrics
            
            if result.success:
                log.info(f"✅ Product extraction successful ({metrics_found}/4 metrics found)")
            else:
                log.warning(f"⚠️ Product extraction partial ({metrics_found}/4 metrics found)")
            
            return result
            
        except Exception as e:
            log.error(f"❌ Product extraction failed: {e}")
            return ExtractionResult(
                success=False,
                product_url=product_url,
                error_message=str(e),
                extraction_timestamp=datetime.now().isoformat()
            )
    
    async def _extract_title(self) -> str:
        """Extract product title"""
        for selector in self.TITLE_SELECTORS:
            try:
                element = self.page.locator(selector).first
                if await element.is_visible():
                    title = await element.text_content()
                    if title and len(title.strip()) > 10:
                        # Validate title (avoid navigation elements)
                        if not any(nav_word in title.lower() for nav_word in ['home', 'login', 'cart', 'menu']):
                            return title.strip()
            except Exception:
                continue
        return ""
    
    async def _extract_price(self) -> str:
        """Extract product price"""
        for selector in self.PRICE_SELECTORS:
            try:
                element = self.page.locator(selector).first
                if await element.is_visible():
                    price_text = await element.text_content()
                    if price_text and any(char in price_text for char in ['£', '$', '€']) and any(char.isdigit() for char in price_text):
                        return price_text.strip()
            except Exception:
                continue
        
        # Check for login required messages
        page_text = await self.page.text_content('body')
        if page_text:
            login_indicators = ['login to view', 'sign in to see', 'member price', 'wholesale price']
            if any(indicator in page_text.lower() for indicator in login_indicators):
                return 'Login required to view price'
        
        return 'Price not found'
    
    async def _extract_ean_barcode(self, html_content: str) -> str:
        """Extract EAN/barcode using multiple strategies"""
        # Strategy 1: Look in page text first
        page_text = await self.page.text_content('body')
        if page_text:
            for pattern in self.EAN_PATTERNS:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    ean_code = match.group(1)
                    if len(ean_code) >= 8:
                        return ean_code
        
        # Strategy 2: Look in HTML source
        for pattern in self.EAN_PATTERNS:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                ean_code = match.group(1)
                if len(ean_code) >= 8:
                    return ean_code
        
        # Strategy 3: Look in meta tags
        try:
            meta_elements = await self.page.locator('meta').all()
            for meta in meta_elements:
                content = await meta.get_attribute('content') or ""
                name = await meta.get_attribute('name') or ""
                property_attr = await meta.get_attribute('property') or ""
                
                # Check meta content for EAN patterns
                for pattern in self.EAN_PATTERNS:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        ean_code = match.group(1)
                        if len(ean_code) >= 8:
                            return ean_code
                
                # Check meta name/property for EAN indicators
                if any(ean_term in (name + property_attr).lower() for ean_term in ['ean', 'gtin', 'upc', 'barcode']):
                    if content and content.isdigit() and len(content) >= 8:
                        return content
        except Exception:
            pass
        
        return ""
    
    async def _extract_stock_status(self, html_content: str) -> str:
        """Extract stock status"""
        # Try stock selectors first
        for selector in self.STOCK_SELECTORS:
            try:
                element = self.page.locator(selector).first
                if await element.is_visible():
                    stock_text = await element.text_content()
                    if stock_text:
                        stock_lower = stock_text.lower()
                        if any(term in stock_lower for term in ['out of stock', 'unavailable', 'sold out']):
                            return 'Out of Stock'
                        elif any(term in stock_lower for term in ['in stock', 'available', 'in-stock']):
                            return 'In Stock'
                        else:
                            return stock_text.strip()
            except Exception:
                continue
        
        # Check page text for stock indicators
        page_text = await self.page.text_content('body')
        if page_text:
            page_lower = page_text.lower()
            if any(term in page_lower for term in ['out of stock', 'unavailable', 'sold out']):
                return 'Out of Stock'
            elif any(term in page_lower for term in ['in stock', 'available']):
                return 'In Stock'
        
        return 'UNKNOWN'
    
    async def save_extraction_results(self, results: List[ExtractionResult]) -> str:
        """Save extraction results to output directory"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = path_manager.get_output_path("FBA_ANALYSIS", "linking_maps", "poundwholesale-co-uk", 
                                        datetime.now().strftime('%Y%m%d'), 
                                        f"complete_extraction_results_{timestamp}.json")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Convert results to dict format
            results_data = {
                'extraction_session': {
                    'timestamp': datetime.now().isoformat(),
                    'total_products_attempted': len(results),
                    'successful_extractions': sum(1 for r in results if r.success),
                    'extraction_method': 'complete_vision_playwright_workflow'
                },
                'products': []
            }
            
            for result in results:
                product_data = {
                    'url': result.product_url,
                    'title': result.title,
                    'price': result.price,
                    'ean_barcode': result.ean_barcode,
                    'stock_status': result.stock_status,
                    'success': result.success,
                    'extraction_method': result.extraction_method,
                    'login_method': result.login_method,
                    'timestamp': result.extraction_timestamp
                }
                
                if result.error_message:
                    product_data['error_message'] = result.error_message
                
                results_data['products'].append(product_data)
            
            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
            
            log.info(f"💾 Results saved to: {output_path}")
            return output_path
            
        except Exception as e:
            log.error(f"❌ Failed to save results: {e}")
            return ""
    
    async def run_complete_extraction_workflow(self) -> List[ExtractionResult]:
        """Run the complete extraction workflow"""
        results = []
        
        try:
            log.info("🚀 Starting complete Vision + Playwright extraction workflow...")
            
            # Step 1: Connect to browser
            if not await self.connect_browser():
                log.error("❌ Failed to connect to browser")
                return results
            
            # Step 2: Check login status
            login_method = ""
            if await self.check_if_already_logged_in():
                log.info("✅ Already logged in")
                login_method = "already_logged_in"
            else:
                # Step 3: Perform login
                log.info("🔐 Performing login...")
                login_method = await self.playwright_login_without_vision()
                
                if "success" not in login_method:
                    log.error(f"❌ Login failed: {login_method}")
                    return results
                
                log.info("✅ Login successful")
            
            # Step 4: Extract from test products
            test_products = [
                f"{self.base_url}/sealapack-turkey-roasting-bags-2-pack",
                f"{self.base_url}/elpine-oil-filled-radiator-heater-1500w",
                f"{self.base_url}/kids-black-beanie-hat"
            ]
            
            log.info(f"📦 Starting extraction from {len(test_products)} products...")
            
            for i, product_url in enumerate(test_products, 1):
                log.info(f"🔍 Extracting product {i}/{len(test_products)}: {product_url}")
                result = await self.extract_all_product_metrics(product_url)
                result.login_method = login_method
                results.append(result)
                
                # Brief pause between extractions
                await asyncio.sleep(1)
            
            # Step 5: Save results
            output_path = await self.save_extraction_results(results)
            
            return results
            
        except Exception as e:
            log.error(f"❌ Complete extraction workflow failed: {e}")
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

async def main():
    """Main execution function"""
    extractor = CompleteVisionPlaywrightExtractor()
    
    try:
        results = await extractor.run_complete_extraction_workflow()
        
        print(f"\n{'='*80}")
        print(f"COMPLETE VISION + PLAYWRIGHT EXTRACTION RESULTS")
        print(f"{'='*80}")
        
        successful = sum(1 for r in results if r.success)
        print(f"Total Products: {len(results)}")
        print(f"Successful Extractions: {successful}")
        print(f"Success Rate: {(successful/len(results)*100):.1f}%" if results else "0%")
        
        for i, result in enumerate(results, 1):
            print(f"\nProduct {i}: {result.product_url}")
            print(f"  Success: {result.success}")
            print(f"  Title: {result.title}")
            print(f"  Price: {result.price}")
            print(f"  EAN/Barcode: {result.ean_barcode}")
            print(f"  Stock Status: {result.stock_status}")
            print(f"  Login Method: {result.login_method}")
            
            if result.error_message:
                print(f"  Error: {result.error_message}")
        
    finally:
        await extractor.cleanup()

if __name__ == "__main__":
    asyncio.run(main())