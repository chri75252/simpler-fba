"""
Comprehensive Amazon data extraction using Playwright connected to Chrome with debug port.
Passively extracts all available data from Amazon product pages including extension data.
Integrates AI fallbacks, CAPTCHA/cookie handling, and advanced Keepa/SellerAmp extraction.
Combines detailed original selector logic with new enhancements.
"""

import os
import re
import json
import logging
import asyncio
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from playwright.async_api import async_playwright, Page, Browser, BrowserContext, FrameLocator, TimeoutError as PlaywrightTimeoutError
from openai import OpenAI
import base64

# Import centralized browser manager
try:
    from utils.browser_manager import get_browser_manager, get_page_for_url
except ImportError:
    # Fallback if browser manager not available
    get_browser_manager = None
    get_page_for_url = None

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# OpenAI API Configuration - Load from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_SUPPLIER", "")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_AMAZON_EXTRACTOR", "gpt-4.1-mini-2025-04-14")

if not OPENAI_API_KEY:
    log.error("🚨 OPENAI_API_KEY not found in environment variables!")
    log.error("Please set OPENAI_API_KEY environment variable")
    sys.exit(1)

# Import file manager for standardized paths
try:
    from utils.file_manager import get_file_manager
    fm = get_file_manager()
    OUTPUT_DIR = str(fm.get_directory_path("cache_amazon", False))
except ImportError:
    # Fallback to old path if file manager not available
    OUTPUT_DIR = r"C:\Users\chris\Amazon-FBA-Agent-System\OUTPUTS\AMAZON_SCRAPE"

# Default timeouts and waits
DEFAULT_NAVIGATION_TIMEOUT = 60000  # 60 seconds
POST_NAVIGATION_STABILIZE_WAIT = 5 # 8 seconds
CAPTCHA_MANUAL_SOLVE_WAIT = 20    # 20 seconds
EXTENSION_DATA_WAIT = 7         # Increased to ensure extensions have adequate time to load properly

class AmazonExtractor:
    def __init__(self, chrome_debug_port: int = 9222, ai_client: Optional[OpenAI] = None, browser_manager=None):
        self.chrome_debug_port = chrome_debug_port
        self.browser: Optional[Browser] = None
        self.browser_manager = browser_manager
        self.use_browser_manager = browser_manager is not None or get_browser_manager is not None
        
        # DISABLE AI features for now - force ai_client to None
        self.ai_client = None
        log.info("AI features disabled in amazon_playwright_extractor - using only traditional selectors.")
        
        self.openai_model = OPENAI_MODEL_NAME
        
        self.output_dir = OUTPUT_DIR 
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            log.info(f"Output directory set to: {os.path.abspath(self.output_dir)}")
        except OSError as e:
            log.error(f"Could not create output directory '{self.output_dir}': {e}. Files will be saved in the current directory.")
            self.output_dir = "." 
        
        if self.use_browser_manager:
            log.info("🔧 AmazonExtractor will use centralized BrowserManager")
        else:
            log.warning("⚠️ BrowserManager not available, using legacy browser connection")
    
    async def connect(self) -> Browser:
        """Connect to browser using BrowserManager if available, otherwise fallback to legacy method."""
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
        
        # Legacy connection method
        log.info(f"Connecting to Chrome browser on debug port {self.chrome_debug_port}")
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.connect_over_cdp(f"http://localhost:{self.chrome_debug_port}")
            log.info(f"Successfully connected to Chrome on port {self.chrome_debug_port}")
            
            # Use existing pages instead of creating a new one
            # This helps ensure extensions like SellerAmp are properly loaded
            all_pages = self.browser.contexts[0].pages if self.browser.contexts and len(self.browser.contexts) > 0 else []
            
            if all_pages:
                log.info(f"Found {len(all_pages)} existing pages")
                # Use an existing page instead of creating a new one
                test_page = all_pages[0]
                log.info(f"Using existing page: {test_page.url}")
                await test_page.bring_to_front()
            else:
                # Only create a new page if none exist
                log.info("No existing pages found. Creating new page")
                page = await self.browser.new_page()
                await page.goto("about:blank", timeout=10000)
                await page.close()
                
            return self.browser
        except Exception as e:
            log.error(f"Failed to connect to Chrome on port {self.chrome_debug_port}: {e}")
            log.error("Ensure Chrome is running with --remote-debugging-port=9222 and a dedicated --user-data-dir for persistence.")
            raise

    async def _handle_cookie_consent(self, page: Page) -> bool:
        log.info("Checking for cookie consent pop-up...")
        amazon_cookie_button_selector = "input#sp-cc-accept"
        try:
            cookie_button = page.locator(amazon_cookie_button_selector)
            if await cookie_button.is_visible(timeout=3000):
                log.info(f"Amazon cookie button '{amazon_cookie_button_selector}' found. Attempting to click.")
                await cookie_button.click(timeout=5000, force=True) 
                await page.wait_for_timeout(1500) 
                if not await cookie_button.is_visible(timeout=1000):
                    log.info("Amazon cookie consent button clicked and dismissed.")
                    return True
                else:
                    log.warning("Clicked Amazon cookie button, but it might still be visible or a new one appeared.")
            # else: # Removed else log for brevity as it's often not found initially
                # log.info(f"Amazon cookie button '{amazon_cookie_button_selector}' not initially visible.")
        except Exception as e:
            log.warning(f"Error with Amazon specific cookie button '{amazon_cookie_button_selector}': {e}")

        generic_cookie_selectors = [
            "button#onetrust-accept-btn-handler", "button[data-action='accept']", 
            "button[title='Accept Cookies']", "button[aria-label*='Accept']",
            "//button[contains(translate(normalize-space(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all')]",
            "//button[contains(translate(normalize-space(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
            "//button[contains(translate(normalize-space(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]",
            "//button[contains(translate(normalize-space(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'got it')]"
        ]
        for selector in generic_cookie_selectors:
            try:
                button = page.locator(selector).first
                if await button.is_visible(timeout=1500): 
                    log.info(f"Generic cookie consent button found: {selector}. Clicking.")
                    await button.click(timeout=3000, force=True)
                    await page.wait_for_timeout(1000) 
                    log.info(f"Clicked generic cookie button '{selector}'. Assuming dismissed.")
                    return True 
            except Exception: pass 
        log.info("Finished checking for cookie consent pop-ups. If one was present and not handled, it might interfere.")
        return False

    async def _handle_captcha(self, page: Page, asin: str) -> bool:
        log.info("Checking for CAPTCHA...")
        captcha_form_selector = "form[action*='/errors/validateCaptcha']"
        captcha_image_selector = "form[action*='/errors/validateCaptcha'] img"
        captcha_input_selector = "input#captchacharacters"
        captcha_submit_button_selectors = [
            "form[action*='/errors/validateCaptcha'] button[type='submit']",
            "//button[contains(text(), 'Continue shopping')]"
        ]
        try:
            await page.wait_for_selector(captcha_form_selector, timeout=3000) 
            log.info("CAPTCHA page detected.")
        except PlaywrightTimeoutError:
            log.info("No CAPTCHA page detected by form selector.")
            return True 

        if self.ai_client:
            try:
                captcha_image_element = await page.query_selector(captcha_image_selector)
                if captcha_image_element:
                    await captcha_image_element.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500)
                    captcha_image_filename = f"captcha_{asin}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    captcha_image_path = os.path.join(self.output_dir, captcha_image_filename)
                    await captcha_image_element.screenshot(path=captcha_image_path)
                    log.info(f"CAPTCHA image saved to {captcha_image_path}")
                    captcha_text_ai = await self._ai_extract_field_from_image(
                        image_path=captcha_image_path,
                        field_description="the characters in this CAPTCHA image. Respond with only the characters, no other text."
                    )
                    if os.path.exists(captcha_image_path): os.remove(captcha_image_path)

                    if captcha_text_ai and 4 <= len(captcha_text_ai) < 10: 
                        log.info(f"AI returned CAPTCHA text: '{captcha_text_ai}'. Attempting to submit.")
                        await page.fill(captcha_input_selector, captcha_text_ai)
                        submit_clicked = False
                        for btn_selector in captcha_submit_button_selectors:
                            try:
                                submit_button = page.locator(btn_selector).first
                                if await submit_button.is_enabled(timeout=1000):
                                    await submit_button.click(timeout=5000)
                                    submit_clicked = True; break
                            except Exception: pass
                        
                        if submit_clicked:
                            await page.wait_for_selector(captcha_form_selector, state="hidden", timeout=15000)
                            log.info("CAPTCHA likely solved by AI and submitted successfully.")
                            return True
                        else: log.warning("AI CAPTCHA submitted, but form still visible or error finding submit button.")
                    else: log.warning(f"AI did not return usable CAPTCHA text (got: '{captcha_text_ai}').")
            except Exception as e: log.error(f"Error during AI CAPTCHA solving attempt: {e}")
        
        log.info(f"AI CAPTCHA attempt failed or skipped. Please solve CAPTCHA manually. Waiting {CAPTCHA_MANUAL_SOLVE_WAIT}s...")
        await asyncio.sleep(CAPTCHA_MANUAL_SOLVE_WAIT)
        try:
            await page.wait_for_selector(captcha_form_selector, state="hidden", timeout=5000)
            log.info("CAPTCHA seems to have been resolved manually (form is hidden).")
            return True
        except PlaywrightTimeoutError:
            log.error("CAPTCHA still present after manual wait. Extraction for this ASIN may fail.")
            return False

    async def extract_data(self, asin: str, page: Optional[Page] = None) -> Dict[str, Any]:
        result = {"asin_queried": asin, "timestamp": datetime.now().isoformat()}
        amazon_url = f"https://www.amazon.co.uk/dp/{asin}"

        # Validate ASIN format (Bxxxxxxxxx or 10-char ISBN)
        if not asin or not (
            re.match(r"^B[0-9A-Z]{9}$", asin) or 
            re.match(r"^[0-9X]{10}$", asin) or  # ISBN-10 can end in X
            re.match(r"^[A-Z0-9]{10}$", asin) # General 10-char alphanumeric as a fallback
        ):
            log.error(f"ASIN '{asin}' provided to extract_data is not a valid format (Bxxxxxxxxx or 10-char alphanumeric/ISBN). URL: {amazon_url}")
            result["error"] = f"Invalid ASIN format: {asin}"; return result
        
        try:
            if not self.browser or not self.browser.is_connected(): await self.connect()
            if not self.browser: result["error"] = "Browser connection failed."; return result
            
            # Use provided page or get one from BrowserManager
            if page is None:
                log.warning(f"No page object provided to extract_data for ASIN {asin}. Getting a new one from BrowserManager.")
                if self.use_browser_manager and get_page_for_url:
                    page = await get_page_for_url(amazon_url, reuse_existing=True)
                else:
                    # Legacy page creation logic
                    all_pages = self.browser.contexts[0].pages if self.browser.contexts and len(self.browser.contexts) > 0 else []
                    if all_pages:
                        page = all_pages[0]
                        log.info(f"Reusing existing page: {page.url}")
                        await page.bring_to_front()
                    else:
                        page = await self.browser.new_page()
                        log.info("Created new page as none existed")
            else:
                log.info(f"Reusing provided page object for ASIN {asin}.")
            
            # CRITICAL: Only navigate if the page's current URL is not the target URL
            if page.url != amazon_url:
                navigation_successful = False
                for attempt in range(3):
                    try:
                        await page.goto(amazon_url, wait_until="domcontentloaded", timeout=DEFAULT_NAVIGATION_TIMEOUT)
                        navigation_successful = True; break
                    except Exception as e:
                        log.warning(f"Navigation attempt {attempt+1} for {amazon_url} failed: {e}")
                        if attempt < 2: await asyncio.sleep(5 + attempt * 5)
            else:
                log.info(f"Page already on target URL {amazon_url}, skipping navigation")
                navigation_successful = True 
            if not navigation_successful:
                log.error(f"Navigation failed for {amazon_url} after multiple attempts.")
                if self.ai_client: result['ai_navigation_diagnostic'] = await self._ai_diagnose_navigation_failure(amazon_url, "Multiple navigation attempts failed.", page)
                result["error"] = f"Navigation failed to {amazon_url}"; return result

            await self._handle_cookie_consent(page)
            await asyncio.sleep(1) 
            if not await self._handle_captcha(page, asin): 
                result["error"] = "CAPTCHA not resolved."; return result
            await self._handle_cookie_consent(page) 

            log.info(f"Page should be ready. Waiting {POST_NAVIGATION_STABILIZE_WAIT}s for stabilization...")
            await asyncio.sleep(POST_NAVIGATION_STABILIZE_WAIT)
            
            log.info(f"Waiting an additional {EXTENSION_DATA_WAIT}s for extensions (Keepa, SellerAmp)...")
            await asyncio.sleep(EXTENSION_DATA_WAIT)

            if os.getenv("DEBUG_SCREENSHOTS", "").lower() in ("true", "1", "yes"):
                debug_filename = f"debug_asin_{asin}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=os.path.join(self.output_dir, debug_filename), full_page=True)
                log.info(f"Debug screenshot saved to {os.path.join(self.output_dir, debug_filename)}")
        
            log.info(f"Extracting all product data for ASIN: {asin}")
            data = await self._extract_all_data(page, asin) 
            data["asin_extracted_from_page"] = data.get("asin_from_details", data.get("asin")) # Prioritize ASIN from details
            data["asin_queried"] = asin # Keep the originally queried ASIN for reference
            
            # Standardize the asin field name
            if "asin" not in data:
                data["asin"] = (
                    data.get("asin_from_details")
                    or re.search(r"/dp/([A-Z0-9]{10})", page.url).group(1) if re.search(r"/dp/([A-Z0-9]{10})", page.url) else asin
                )
            
            return data
            
        except Exception as e:
            log.error(f"Error extracting data for ASIN {asin}: {e}", exc_info=True)
            result["error"] = str(e)
            page_url_for_diag = amazon_url
            if page and page.url and page.url != "about:blank": # Ensure page.url is valid
                page_url_for_diag = page.url
            if self.ai_client: 
                 result['ai_extraction_diagnostic'] = await self._ai_diagnose_extraction_failure(asin, str(e), page_url_for_diag)
            return result
        finally:
            # Do not close the page - this is essential for keeping extensions like SellerAmp working
            # When we close and reopen pages, extensions don't load properly
            pass
    
    async def _extract_all_data(self, page: Page, asin: str) -> Dict[str, Any]:
        """
        Extract all data from the Amazon product page including extensions.
        Restores detailed selector logic from original script, with AI fallbacks.
        """
        data: Dict[str, Any] = {}
        data["asin_from_details"] = asin  # Store the queried ASIN
        html_content: Optional[str] = None 
        current_page_url = page.url 

        async def get_html_content_func(): 
            nonlocal html_content
            if html_content is None: html_content = await page.content()
            return html_content
        
        # 1. Basic Product Information (Re-integrating and expanding detailed original logic)
        log.info("Extracting basic product information (Title, Price, Images, Amazon Details)...")
        
        # Product title (More selectors from typical Amazon structure)
        try:
            title_selectors = ["#productTitle", "#title", "h1#title", "span#productTitle", ".product-title-word-break"]
            for selector in title_selectors:
                title_elem = await page.query_selector(selector)
                if title_elem:
                    title_text = (await title_elem.text_content() or "").strip()
                    if title_text: data["title"] = title_text; log.info(f"Title found: '{title_text}' via {selector}"); break
            if not data.get("title") and self.ai_client:
                log.warning("Title not found by selectors. AI fallback.")
                data["title"] = await self._ai_extract_field_from_html(await get_html_content_func(), "product title", current_page_url)
        except Exception as e: log.warning(f"Error extracting title: {e}")
        
        await self._extract_price(page, data, get_html_content_func) 
        await self._extract_images(page, data, get_html_content_func) 
        await self._extract_product_details_amazon(page, data, get_html_content_func)

        # 2. Sales Rank Information (Re-integrating and expanding detailed original logic)
        log.info("Extracting sales rank information...")
        try:
            rank_extracted = False
            rank_selectors = [
                "#SalesRank", 
                "tr:has(th:has-text('Best Sellers Rank'))", 
                "li:has(span.a-text-bold:text-matches('Best Sellers Rank', 'i'))", 
                "#productDetails_detailBullets_sections1 tr:has-text('Best Sellers Rank')",
                "#detail-bullets_feature_div li:has-text('Best Sellers Rank')",
                "#detailBullets_feature_div ul li span.a-list-item:has-text('Best Sellers Rank')",
                "ul#detailBullets_list > li:has-text('Best Sellers Rank')",
                "span.a-list-item:has(span.a-text-bold:text-matches('Best Sellers Rank', 'i'))",
                "#productDetails_detailBullets_sections1 th:has-text('Best Sellers Rank')",
                "xpath=//li[.//span[contains(normalize-space(.), 'Best Sellers Rank')]]",
                "xpath=//*[contains(text(),'Best Sellers Rank')]/following-sibling::td",
                "xpath=//*[contains(text(),'Best Sellers Rank')]/ancestor::li"
            ] 
            for selector in rank_selectors:
                rank_container_elem = await page.query_selector(selector)
                if rank_container_elem:
                    rank_text_content = await rank_container_elem.text_content()
                    if not rank_text_content and selector.startswith("//*"): # For XPath that might select the key, get parent's text
                        parent_elem = await rank_container_elem.query_selector("xpath=..")
                        if parent_elem: rank_text_content = await parent_elem.text_content()

                    if rank_text_content:
                        primary_rank_match = re.search(r"#([\d,]+)\s+in\s+([^(]+(?:\([^)]+\))?)", rank_text_content)
                        if primary_rank_match:
                            data["sales_rank"] = self._parse_number(primary_rank_match.group(1))
                            category_text = primary_rank_match.group(2).strip()
                            data["category"] = re.sub(r"\s*\(See Top\s*\d+\s*in.*?\)\s*$", "", category_text, flags=re.IGNORECASE).strip()
                            rank_extracted = True; log.info(f"Sales Rank (primary): #{data['sales_rank']} in {data['category']} (via selector: {selector})")
                            additional_ranks_text = rank_text_content[primary_rank_match.end():] 
                            additional_ranks_matches = re.finditer(r"#([\d,]+)\s+in\s+([^(]+(?:\([^)]+\))?)", additional_ranks_text)
                            data["additional_ranks"] = [{"rank": self._parse_number(m.group(1)), "category": re.sub(r"\s*\(See Top\s*\d+\s*in.*?\)\s*$", "", m.group(2).strip(), flags=re.IGNORECASE).strip()} for m in additional_ranks_matches]
                            if data["additional_ranks"]: log.info(f"Found {len(data['additional_ranks'])} additional ranks.")
                            break 
            if not rank_extracted and self.ai_client:
                log.warning("Sales rank not found by selectors. AI fallback.")
                data["sales_rank_ai_fallback"] = await self._ai_extract_field_from_html(await get_html_content_func(), "Best Sellers Rank information (primary rank and category, plus any sub-category ranks as a list or structured text)", current_page_url)
        except Exception as e: log.warning(f"Error extracting sales rank: {e}")

        # 3. Ratings and Reviews (Re-integrating and expanding detailed original logic)
        log.info("Extracting ratings and reviews...")
        try:
            rating_selectors = [
                "#acrPopover[title*='out of 5 stars']", 
                "span#acrPopover span.a-icon-alt",      
                "i[class*='a-icon-star'] span.a-icon-alt",
                "span.reviewCountTextLinkedHistogram[title*='out of 5 stars']" # Another one for ratings
            ]
            for selector in rating_selectors:
                rating_elem = await page.query_selector(selector)
                if rating_elem:
                    rating_text = await rating_elem.get_attribute("title") or await rating_elem.text_content()
                    if rating_text:
                        rating_match = re.search(r"([\d.]+)\s*(?:out\s*of\s*5)?", rating_text) 
                        if rating_match: data["rating"] = float(rating_match.group(1)); log.info(f"Rating: {data['rating']} via {selector}"); break
            
            review_count_selectors = [
                "#acrCustomerReviewText", 
                "#reviewsMedley .a-size-base:has-text('ratings')", 
                "span#acrCustomerReviewText.a-size-base",
                "a.a-link-normal:has(span.totalReviewCount)" # Link containing total review count
            ]
            for selector in review_count_selectors:
                review_count_elem = await page.query_selector(selector)
                if review_count_elem:
                    review_text = await review_count_elem.text_content()
                    if review_text:
                        count_match = re.search(r"([\d,]+)", review_text) 
                        if count_match: data["review_count"] = self._parse_number(count_match.group(1)); log.info(f"Review count: {data['review_count']} via {selector}"); break
            
            if (not data.get("rating") or not data.get("review_count")) and self.ai_client:
                 log.warning("Rating/review count not fully extracted. AI fallback.")
                 html_c = await get_html_content_func()
                 if not data.get("rating"): data["rating_ai_fallback"] = await self._ai_extract_field_from_html(html_c, "customer rating value (e.g., 4.5)", current_page_url)
                 if not data.get("review_count"): data["review_count_ai_fallback"] = await self._ai_extract_field_from_html(html_c, "number of customer reviews", current_page_url)
        except Exception as e: log.warning(f"Error extracting ratings/reviews: {e}")

        # 4. Stock information (Re-integrating and expanding detailed original logic)
        log.info("Extracting stock information...")
        try:
            availability_selectors = [
                "#availability span.a-size-medium.a-color-success", 
                "#availability span.a-color-price",                 
                "#availability span.a-color-error",                 
                "#availability",                                     
                "#outOfStock",                                       
                "div#desktop_qualifiedBuyBox :text-matches('In stock|Only \\d+ left|Usually dispatched', 'i')",
                "#exports_desktop_qualifiedBuybox_tlc_feature_div :text-matches('In stock|Only \\d+ left', 'i')" # Another buybox variant
            ]
            availability_text = None
            for selector in availability_selectors:
                availability_elem = await page.query_selector(selector)
                if availability_elem:
                    current_text = (await availability_elem.text_content() or "").strip()
                    if current_text: availability_text = current_text; log.info(f"Availability text: '{availability_text}' via {selector}"); break
            
            if availability_text:
                data["availability_text"] = availability_text
                data["in_stock"] = any(s in availability_text.lower() for s in ["in stock", "add to cart", "only", "left", "usually dispatched"]) and \
                                   "currently unavailable" not in availability_text.lower() and \
                                   "out of stock" not in availability_text.lower()
            elif self.ai_client:
                log.warning("Stock info not found by selector. AI fallback.")
                data["availability_ai_fallback"] = await self._ai_extract_field_from_html(await get_html_content_func(), "product availability or stock status (e.g., 'In stock', 'Only 5 left', 'Out of stock')", current_page_url)
                if data.get("availability_ai_fallback") and "in stock" in data["availability_ai_fallback"].lower(): data["in_stock"] = True
        except Exception as e: log.warning(f"Error extracting stock info: {e}")

        # 5. Features/Bullets (Re-integrating and expanding detailed original logic)
        log.info("Extracting features/bullets...")
        try:
            feature_bullets_elems = await page.query_selector_all(
                "#feature-bullets ul li span.a-list-item, #featurebullets_feature_div ul li span.a-list-item, #feature-bullets li, #featurebullets_feature_div li"
            )
            if feature_bullets_elems:
                features = []
                for bullet in feature_bullets_elems:
                    list_item_span = await bullet.query_selector("span.a-list-item") 
                    text_to_use = await (list_item_span or bullet).text_content()
                    cleaned_text = (text_to_use or "").strip()
                    if cleaned_text: features.append(cleaned_text)
                if features: data["features"] = list(dict.fromkeys(features)); log.info(f"Found {len(data['features'])} features.")
            
            if not data.get("features") and self.ai_client:
                log.warning("Features/bullets not found by selector. AI fallback.")
                data["features_ai_fallback"] = await self._ai_extract_field_from_html(await get_html_content_func(), "product feature bullet points as a list of strings", current_page_url)
        except Exception as e: log.warning(f"Error extracting features: {e}")

        # 6. Product Description (Re-integrating and expanding detailed original logic)
        log.info("Extracting product description...")
        try:
            desc_selectors = [
                "#productDescription", "#productDescription_feature_div #productDescription", 
                "#aplus_feature_div",  "#dpx-aplus-product-description_feature_div", 
                "#centerCol div#descriptionAndDetails", "div#aplus",
                "div#bookDescription_feature_div", "div#detailBullets_productDescription"
            ]
            for selector in desc_selectors:
                description_elem = await page.query_selector(selector)
                if description_elem:
                    raw_html_desc = await description_elem.inner_html()
                    if raw_html_desc:
                        desc_text_cleaned = re.sub(r'<style.*?</style>', '', raw_html_desc, flags=re.DOTALL | re.IGNORECASE)
                        desc_text_cleaned = re.sub(r'<script.*?</script>', '', desc_text_cleaned, flags=re.DOTALL | re.IGNORECASE)
                        desc_text_cleaned = re.sub(r'<[^>]+>', ' ', desc_text_cleaned) 
                        description_text = ' '.join(desc_text_cleaned.split()).strip() 
                        if len(description_text) > 50: 
                            data["description"] = description_text; log.info(f"Description found using selector: {selector}"); break
            if not data.get("description") and self.ai_client:
                log.warning("Description not found by selectors. AI fallback.")
                data["description_ai_fallback"] = await self._ai_extract_field_from_html(await get_html_content_func(), "detailed product description text", current_page_url)
        except Exception as e: log.warning(f"Error extracting description: {e}")

        # 7. Product Specifications Table (Re-integrating and expanding detailed original logic)
        log.info("Extracting product specifications table...")
        try:
            spec_table_selectors = [
                "#productDetails_techSpec_section_1", 
                "table.a-keyvalue.prodDetTable",      
                "div#prodDetails table.prodDetTable",  
                "div#detailBullets_productDetailsTable",
                "table#productDetails_detailBullets_sections1" # Sometimes BSR is in a table also used for specs
            ]
            specs = {}
            for selector in spec_table_selectors:
                spec_table_elem = await page.query_selector(selector)
                if spec_table_elem:
                    rows = await spec_table_elem.query_selector_all("tr")
                    for row in rows:
                        key_elem = await row.query_selector("th"); value_elem = await row.query_selector("td")
                        if key_elem and value_elem:
                            key = (await key_elem.text_content() or "").strip(); value = (await value_elem.text_content() or "").strip()
                            if key and value and "Best Sellers Rank" not in key: # Avoid re-parsing BSR here
                                specs[key] = ' '.join(value.split()) 
                    if specs: log.info(f"Specifications table parsed using selector: {selector}"); break 
            if specs: data["specifications_table"] = specs
            elif self.ai_client:
                log.warning("Specifications table not found/parsed by selectors. AI fallback.")
                data["specifications_ai_fallback"] = await self._ai_extract_field_from_html(await get_html_content_func(), "product technical specifications table as key-value pairs or JSON", current_page_url)
        except Exception as e: log.warning(f"Error extracting specifications: {e}")

        # 8. SellerAmp and Keepa Data
        log.info("Extracting SellerAmp data (if present)...")
        data["selleramp"] = await self._extract_selleramp_data(page, get_html_content_func, asin) 
        
        log.info("Extracting Keepa data (if present)...")
        data["keepa"] = await self._extract_keepa_data(page, get_html_content_func, asin) 
        
        # --- Consolidated Keepa Fallback Logic ---
        keepa_product_tab_data = data.get("keepa", {}).get("product_details_tab_data", {})
        keepa_sales_rank_table = data.get("keepa", {}).get("sales_rank_details_table", {})

        # Fallback for EAN from Keepa - collect ALL EANs found
        if keepa_product_tab_data:
            log.info(f"ASIN {asin}: Attempting to extract EANs from Keepa product_details_tab_data.")
            keepa_ean_keys = ["Product Codes - EAN", "EAN", "ean"] # Case-insensitive search might be better
            for key_text in keepa_product_tab_data: # Iterate through actual keys in Keepa data
                if any(k_ean.lower() in key_text.lower() for k_ean in keepa_ean_keys):
                    potential_ean_str = str(keepa_product_tab_data[key_text])
                    cleaned_digits = re.sub(r'\D', '', potential_ean_str)
                    if len(cleaned_digits) == 13:
                        if "eans_on_page" not in data:
                            data["eans_on_page"] = []
                        if cleaned_digits not in data["eans_on_page"]:
                            data["eans_on_page"].append(cleaned_digits)
                            data["ean_on_page_source"] = "Keepa_Product_Details"
                            log.info(f"ASIN {asin}: EAN '{cleaned_digits}' found in Keepa details via key '{key_text}'.")
                        # Keep first EAN for backward compatibility
                        if not data.get("ean_on_page"):
                            data["ean_on_page"] = cleaned_digits
                            data["ean_on_page_source"] = "Keepa_Product_Details"
                        break 
            if not data.get("ean_on_page"):
                 log.warning(f"ASIN {asin}: Could not find EAN in Keepa product_details_tab_data.")

        # Fallback for BSR from Keepa
        if (not data.get("sales_rank") or data.get("sales_rank") == 0 or data.get("sales_rank") == float('inf')) and data.get("keepa"):
            log.info(f"ASIN {asin}: BSR not found or invalid from page. Attempting fallback from Keepa.")
            bsr_found_in_keepa = False
            if keepa_sales_rank_table.get("main_cat_current_rank"):
                data["sales_rank"] = keepa_sales_rank_table["main_cat_current_rank"]
                data["category"] = keepa_sales_rank_table.get("main_cat_name", "").split(" drops / month")[0].strip()
                data["sales_rank_source"] = "Keepa_SalesRankDetailsTable"
                log.info(f"ASIN {asin}: BSR {data['sales_rank']} in '{data['category']}' from Keepa SalesRankDetailsTable.")
                bsr_found_in_keepa = True
            
            if not bsr_found_in_keepa and keepa_product_tab_data:
                # Look for BSR in Keepa's main product details AG Grid data
                # Common keys: "Sales Rank: Current", "Sales Rank - Current" (often includes category too)
                # This requires careful parsing of the value string from Keepa
                keepa_bsr_keys = ["Sales Rank: Current", "Sales Rank - Current", "Current Sales Rank"]
                for key_text in keepa_product_tab_data:
                     if any(k_bsr.lower() in key_text.lower() for k_bsr in keepa_bsr_keys):
                        bsr_string = str(keepa_product_tab_data[key_text])
                        # Example parsing: "#12,345 in Books"
                        match = re.search(r"#([\d,]+)\s+in\s+([^(]+)", bsr_string)
                        if match:
                            data["sales_rank"] = self._parse_number(match.group(1))
                            data["category"] = match.group(2).strip().split(" (See")[0].strip() # Clean category
                            data["sales_rank_source"] = "Keepa_Product_Details_Tab"
                            log.info(f"ASIN {asin}: BSR {data['sales_rank']} in '{data['category']}' from Keepa Product Details Tab via key '{key_text}'.")
                            bsr_found_in_keepa = True
                            break
            if not bsr_found_in_keepa:
                log.warning(f"ASIN {asin}: Could not find BSR in any Keepa data source.")

        # Fallback for Price from Keepa (This is Fix 2.5, ensure it's placed here if not already)
        if (not data.get("current_price") or data.get("current_price") == 0.0) and keepa_product_tab_data:
            log.info(f"ASIN {asin}: Current price missing/zero. Attempting fallback from Keepa Product Details.")
            price_keys_to_check = ["Buy Box - Current", "Amazon - Current", "New - Current"]
            found_keepa_price = None
            for key_text in price_keys_to_check:
                if key_text in keepa_product_tab_data:
                    price_val_str = str(keepa_product_tab_data[key_text])
                    parsed_k_price = self._parse_price(price_val_str)
                    if parsed_k_price and parsed_k_price > 0:
                        found_keepa_price = parsed_k_price
                        log.info(f"ASIN {asin}: Found price in Keepa details ('{key_text}'): {found_keepa_price}")
                        break
            if found_keepa_price:
                data["current_price"] = found_keepa_price
                data["current_price_source"] = "Keepa_Product_Details_Fallback"
                log.info(f"ASIN {asin}: Using price from Keepa fallback: {data['current_price']}")
            else:
                log.warning(f"ASIN {asin}: Could not find a suitable current price in Keepa Product Details for fallback.")
        # --- End Consolidated Keepa Fallback Logic ---
            
        # 9. Price estimations (from original script)
        if data.get("sales_rank") and isinstance(data["sales_rank"], int) and data["sales_rank"] > 0:
            data["estimated_monthly_sales_from_bsr"] = self._estimate_sales_from_bsr(data["sales_rank"], data.get("category", ""))
            
        return data

    async def _extract_price(self, page: Page, data: Dict[str, Any], get_html_content_func) -> None:
        # ... (Price extraction logic as in amazon_playwright_extractor_fully_merged.py, with corrected regex for sold_badge)
        log.info("Extracting price details...")
        try:
            price_selectors = [
                # Primary Buy Box Price
                "#corePrice_feature_div .a-offscreen", 
                "span.priceToPay .a-offscreen", 
                ".a-price[data-a-size='xl'] .a-offscreen", 
                ".a-price[data-a-size='core'] .a-offscreen", 
                "#price_inside_buybox",
                "div#apex_desktop_usedAccordionRow .a-color-price", # Used price, but good to check
                "div#corePriceDisplay_desktop_feature_div span.a-price.a-text-price span.a-offscreen", # Variation
                "div#corePrice_feature_div span.a-price span.a-offscreen", # Another variation
                "div#centerCol #priceblock_ourprice", # More specific to buybox
                "div#centerCol #priceblock_dealprice", # Deals in buybox
                "div#centerCol #priceblock_saleprice", # Sale price in buybox
                "div#centerCol span.apexPriceToPay span.a-offscreen", # Apex price in buybox
                # General Selectors
                "#priceblock_ourprice", 
                "#priceblock_dealprice", 
                ".offer-price", 
                "#price", 
                "span.apexPriceToPay .a-offscreen", 
                ".priceToPay .a-price .a-offscreen", 
                "span#priceblock_saleprice",
                # Selector for subscription price, if that's the only one available
                "span#subscriptionPrice",
                "span.reinventPricePriceToPayMargin.a-size-base span.a-offscreen" # Common for books
            ]
            price_found = False
            for selector in price_selectors:
                price_elem = await page.query_selector(selector)
                if price_elem:
                    price_text = await price_elem.text_content()
                    if price_text:
                        parsed_price = self._parse_price(price_text)
                        if parsed_price > 0: data["current_price"] = parsed_price; log.info(f"Current price: {parsed_price} via {selector}"); price_found = True; break 
            
            original_price_selectors = ["#corePrice_feature_div span[data-a-strike='true'] span.a-offscreen", "td.comparison_baseitem_column span.a-text-strike", ".basisPrice span.a-text-price span.a-offscreen", "#listPrice .a-text-strike", "span.a-price.a-text-price[data-a-strike='true'] span.a-offscreen", "#priceblock_ourprice_lbl + .a-text-strike"]
            for selector in original_price_selectors:
                orig_price_elem = await page.query_selector(selector)
                if orig_price_elem:
                    orig_price_text = await orig_price_elem.text_content()
                    if orig_price_text:
                        parsed_orig_price = self._parse_price(orig_price_text)
                        if parsed_orig_price > 0 and parsed_orig_price > data.get("current_price", 0): data["original_price"] = parsed_orig_price; log.info(f"Original price: {parsed_orig_price} via {selector}"); break
            
            # Corrected approach for "bought in past month"
            sold_badge_container_selectors = ["span#socialSwiperInsideContainer", "div#socialProofingAsinFaceout_feature_div", "div[data-csa-c-type='widget']"]
            for container_selector in sold_badge_container_selectors:
                container = await page.query_selector(container_selector)
                if container:
                    all_text_in_container = await container.text_content()
                    if all_text_in_container and "bought in past month" in all_text_in_container.lower():
                        match_obj = re.search(r"([\d,]+)\+?\s*(?:bought in past month|sold)", all_text_in_container, re.IGNORECASE) # Renamed 'match'
                        if match_obj: 
                            data["amazon_monthly_sales_badge"] = self._parse_number(match_obj.group(1))
                            log.info(f"Amazon sales badge found: {data['amazon_monthly_sales_badge']} in container {container_selector}")
                            break 
                    if data.get("amazon_monthly_sales_badge"): break

            if not price_found and self.ai_client:
                log.warning("Current price not found by selectors. AI fallback.")
                ai_price_str = await self._ai_extract_field_from_html(await get_html_content_func(), "current product price (numerical value)", page.url)
                if ai_price_str: data["current_price_ai_fallback"] = self._parse_price(ai_price_str)
        except Exception as e: log.warning(f"Error extracting price details: {e}")

    async def _extract_images(self, page: Page, data: Dict[str, Any], get_html_content_func) -> None:
        # ... (Image extraction logic as in amazon_playwright_extractor_fully_merged.py)
        log.info("Extracting image URLs...")
        image_urls = {"main_image": None, "thumbnails": [], "high_res_gallery": []}
        try:
            main_image_selectors = ["#landingImage", "#imgTagWrapperId img", "#imgBlkFront", "#ivLargeImage img", "div.imgTagWrapper img"]
            for selector in main_image_selectors:
                img_elem = await page.query_selector(selector)
                if img_elem:
                    src = await img_elem.get_attribute("src"); data_old_hires = await img_elem.get_attribute("data-old-hires"); data_hires = await img_elem.get_attribute("data-hires")
                    final_src = data_hires or data_old_hires or src
                    if final_src and not final_src.startswith("data:image"): image_urls["main_image"] = final_src.split(" ")[0]; log.info(f"Main image: {image_urls['main_image']} via {selector}"); break
            
            thumb_container = await page.query_selector("#altImages")
            if thumb_container: 
                thumb_elems = await thumb_container.query_selector_all("li.item img")
                for thumb in thumb_elems:
                    src = await thumb.get_attribute("src")
                    if src and not src.startswith("data:image") and "Sprite" not in src and "grey-pixel" not in src:
                        larger_thumb = re.sub(r'\._[A-Z0-9_]+_\.jpg', '._SL1500_.jpg', src)
                        if larger_thumb == src: larger_thumb = re.sub(r'\.SS\d+_|\.US\d+_', '._SL1500_', src) 
                        image_urls["thumbnails"].append(larger_thumb)
                if image_urls["thumbnails"]: log.info(f"Found {len(image_urls['thumbnails'])} thumbnails.")

            try: 
                gallery_data_js = await page.evaluate(r"""() => { /* ... JS from original ... */ }""") 
                if gallery_data_js and isinstance(gallery_data_js, list):
                    image_urls["high_res_gallery"] = list(set(url for url in gallery_data_js if url and isinstance(url, str)))
                    if image_urls["high_res_gallery"]: log.info(f"Found {len(image_urls['high_res_gallery'])} high-res images from JS.")
            except Exception as e_js: log.warning(f"Error evaluating JS for images: {e_js}")

            if not image_urls["main_image"] and image_urls["high_res_gallery"]: image_urls["main_image"] = image_urls["high_res_gallery"][0]
            elif not image_urls["main_image"] and image_urls["thumbnails"]: image_urls["main_image"] = image_urls["thumbnails"][0]
            data.update(image_urls)

            if not data.get("main_image") and self.ai_client:
                log.warning("Main image not found. AI fallback.")
                ai_img_url = await self._ai_extract_field_from_html(await get_html_content_func(), "URL of the main product image", page.url)
                if ai_img_url and ai_img_url.startswith("http"): data["main_image_ai_html_fallback"] = ai_img_url
        except Exception as e: log.warning(f"Error extracting images: {e}")

    async def _extract_product_details_amazon(self, page: Page, data: Dict[str, Any], get_html_content_func) -> None:
        # ... (Amazon product details extraction logic as in amazon_playwright_extractor_fully_merged.py)
        log.info("Extracting Amazon product details section...")
        details = {}
        try:
            detail_table_rows = await page.query_selector_all("#productDetails_detailBullets_sections1 tr")
            for row in detail_table_rows:
                th_elem = await row.query_selector("th.prodDetSectionEntry"); td_elem = await row.query_selector("td.prodDetAttrValue")
                if th_elem and td_elem:
                    key = (await th_elem.text_content() or "").strip(); value = (await td_elem.text_content() or "").strip()
                    if key and value: details[key] = ' '.join(value.split()) 
            if not details or "ASIN" not in details:
                detail_list_items = await page.query_selector_all("#detailBullets_feature_div > ul > li > span.a-list-item")
                for item_span in detail_list_items:
                    item_text_full = (await item_span.text_content() or "").strip()
                    key_elem_in_li = await item_span.query_selector("span.a-text-bold")
                    if key_elem_in_li:
                        key_text = (await key_elem_in_li.text_content() or "").strip().rstrip(':').strip()
                        value_text = item_text_full.split(key_text, 1)[-1].strip().lstrip(':').strip() if key_text in item_text_full else item_text_full
                        value_text = ' '.join(value_text.split())
                        if key_text and value_text:
                            if "Best Sellers Rank" in key_text: 
                                bsr_values = [{"rank": self._parse_number(m.group(1)), "category": m.group(2).strip().split(" (See Top")[0].strip()} for m in re.finditer(r"#([\d,]+)\s+in\s+([^(]+(?:\([^)]+\))?)", value_text)]
                                if bsr_values: details[key_text] = bsr_values
                            else: details[key_text] = value_text
            if not details or "ASIN" not in details:
                detail_wrapper_items = await page.query_selector_all("#detailBulletsWrapper_feature_div li") 
                for item in detail_wrapper_items:
                    item_text = await item.text_content()
                    if item_text and ":" in item_text:
                        key, value = item_text.split(":", 1); key = key.strip(); value = value.strip()
                        if key and value: details[key] = ' '.join(value.split())
            if details: 
                data["amazon_product_details_section"] = details
                for k, v_val in details.items():
                    k_lower = k.lower()
                    if "ASIN" in k and not data.get("asin_from_details"): data["asin_from_details"] = v_val 
                    elif "Package Dimensions" in k: data["dimensions_from_details"] = v_val
                    elif "Item Weight" in k: data["weight_from_details"] = v_val
                    elif "Date First Available" in k: data["date_first_available_from_details"] = v_val
                    elif "Manufacturer" in k: data["manufacturer_from_details"] = v_val
                    # Extract EAN/UPC information - collect ALL EANs/UPCs found
                    elif ("ean" in k_lower or "european article number" in k_lower or "international article number" in k_lower):
                        cleaned_digits = re.sub(r'\D', '', str(v_val))
                        if len(cleaned_digits) == 13:
                            if "eans_on_page" not in data:
                                data["eans_on_page"] = []
                            if cleaned_digits not in data["eans_on_page"]:
                                data["eans_on_page"].append(cleaned_digits)
                                log.info(f"EAN '{cleaned_digits}' found in Amazon details section via key '{k}'.")
                            # Keep first EAN for backward compatibility
                            if not data.get("ean_on_page"):
                                data["ean_on_page"] = cleaned_digits
                    elif ("upc" in k_lower or "universal product code" in k_lower):
                        cleaned_digits = re.sub(r'\D', '', str(v_val))
                        if len(cleaned_digits) == 12:
                            if "upcs_on_page" not in data:
                                data["upcs_on_page"] = []
                            if cleaned_digits not in data["upcs_on_page"]:
                                data["upcs_on_page"].append(cleaned_digits)
                                log.info(f"UPC '{cleaned_digits}' found in Amazon details section via key '{k}'.")
                            # Keep first UPC for backward compatibility
                            if not data.get("upc_on_page"):
                                data["upc_on_page"] = cleaned_digits
            # Post-loop check for EAN/UPC in details dictionary - collect ALL matches
            if details:
                # One more detailed scan through all values for EANs/UPCs
                for k, v_val in details.items():
                    if isinstance(v_val, str):
                        # Look for potential 13-digit EANs
                        ean_matches = re.findall(r'\b\d{13}\b', v_val)
                        for ean_match in ean_matches:
                            if "eans_on_page" not in data:
                                data["eans_on_page"] = []
                            if ean_match not in data["eans_on_page"]:
                                data["eans_on_page"].append(ean_match)
                                log.info(f"EAN {ean_match} extracted via pattern matching in '{k}'")
                            # Keep first EAN for backward compatibility
                            if not data.get("ean_on_page"):
                                data["ean_on_page"] = ean_match
                            
                        # Look for potential 12-digit UPCs
                        upc_matches = re.findall(r'\b\d{12}\b', v_val)
                        for upc_match in upc_matches:
                            if "upcs_on_page" not in data:
                                data["upcs_on_page"] = []
                            if upc_match not in data["upcs_on_page"]:
                                data["upcs_on_page"].append(upc_match)
                                log.info(f"UPC {upc_match} extracted via pattern matching in '{k}'")
                            # Keep first UPC for backward compatibility
                            if not data.get("upc_on_page"):
                                data["upc_on_page"] = upc_match
                            
            elif self.ai_client:
                log.warning("Amazon product details section not found/parsed. AI fallback.")
                data["amazon_product_details_ai_fallback"] = await self._ai_extract_field_from_html(await get_html_content_func(), "product details like ASIN, dimensions, weight, manufacturer as JSON", page.url)
                
                # Try to extract EAN/UPC from AI response - collect ALL matches
                if isinstance(data.get("amazon_product_details_ai_fallback"), str):
                    ai_text = data["amazon_product_details_ai_fallback"]
                    ean_matches = re.findall(r'\b\d{13}\b', ai_text)
                    for ean_match in ean_matches:
                        if "eans_on_page" not in data:
                            data["eans_on_page"] = []
                        if ean_match not in data["eans_on_page"]:
                            data["eans_on_page"].append(ean_match)
                            log.info(f"EAN {ean_match} extracted via pattern matching in AI fallback")
                        # Keep first EAN for backward compatibility
                        if not data.get("ean_on_page"):
                            data["ean_on_page"] = ean_match
        except Exception as e: log.warning(f"Error extracting Amazon product details section: {e}")
        try:
            prime_elem = await page.query_selector("#primeDetails_feature_div img[alt*='Prime'], #priceBadging_feature_div img[alt*='Prime'], i.a-icon-prime, #mir-layout-DELIVERY_BLOCK span.a-text-bold:has-text('Prime')")
            data["prime_eligible"] = prime_elem is not None
            fba_elem = await page.query_selector("#merchant-info:has-text('Fulfilled by Amazon'), #tabular-buybox-container :text-matches('Fulfilled by Amazon', 'i'), #availability span:has-text('Fulfilled by Amazon')")
            data["fulfilled_by_amazon"] = fba_elem is not None
            seller_elem = await page.query_selector("#merchant-info, #sellerProfileTriggerId") 
            if seller_elem: 
                seller_info_text = (await seller_elem.text_content() or "").strip()
                if seller_info_text:
                    data["seller_info_text"] = seller_info_text
                    data["sold_by_amazon"] = "amazon" in seller_info_text.lower() and ("dispatched from and sold by amazon" in seller_info_text.lower() or "sold by amazon" in seller_info_text.lower())
        except Exception as e: log.warning(f"Error extracting prime/fba/seller info: {e}")

    async def _extract_selleramp_data(self, page: Page, get_html_content_func, asin: str) -> Dict[str, Any]:
        log.info("SellerAmp data extraction is currently disabled as per requirements (Fix 2.3).")
        return {"status": "SellerAmp extraction disabled"}
        
        while elapsed_time < max_wait_time and not selleramp_detected:
            try:
                # Check multiple SellerAmp panel indicators
                panel_selectors = [
                    "div#quick-info-body",
                    "div.qi-wrapper", 
                    "div.qi-container",
                    "div.qi-row",
                    "span#saslookup-fulfilment_fee",
                    "input#qi_cost"
                ]
                
                for selector in panel_selectors:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        log.info(f"SellerAmp detected via selector '{selector}' after {elapsed_time}s")
                        selleramp_detected = True
                        break
                
                if not selleramp_detected:
                    await asyncio.sleep(poll_interval)
                    elapsed_time += poll_interval
                    if elapsed_time % 10 == 0:  # Log every 10 seconds
                        log.info(f"Still waiting for SellerAmp... {elapsed_time}s elapsed")
                        
            except Exception as e:
                log.debug(f"Error during SellerAmp detection polling: {e}")
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval
        
        if not selleramp_detected:
            log.warning(f"SellerAmp extension not detected after {max_wait_time}s timeout")
            selleramp_data["status"] = "SellerAmp extension not detected - timeout"
            return selleramp_data
        
        # Additional wait for extension to fully initialize data
        log.info("SellerAmp detected - waiting 5s for data initialization...")
        await asyncio.sleep(5)
        
        # Updated SellerAmp selectors to match specific HTML elements from user requirements
        SELLERAMP_SELECTORS = {
            "fulfilment_fee": "span#saslookup-fulfilment_fee, #saslookup-fulfilment_fee",
            "referral_fee": "span#saslookup-referral_fee, #saslookup-referral_fee", 
            "estimated_sales": "span.estimated_sales_per_mo, .estimated_sales_per_mo",
            "roi": "span#qi-roi, #qi-roi, div.qi-roi-pnl span, .qi-roi-pnl span",
            "profit": "span#qi-profit, #qi-profit, div.qi-profit-pnl span, .qi-profit-pnl span",
            "bsr": "span#qi-bsr, #qi-bsr, div.qi-bsr-pnl span, .qi-bsr-pnl span",
            "max_cost": "span#qi-max-cost, #qi-max-cost, div.qi-max-cost-pnl span, .qi-max-cost-pnl span",
            "qi_cost_input": "input#qi_cost, #qi_cost"
        }
        
        # Try to extract specific SellerAmp data fields
        async def safe_extract_selleramp_text(selector_key: str) -> str:
            selector_string = SELLERAMP_SELECTORS.get(selector_key, "")
            if not selector_string: return ""
            selectors_to_try = [s.strip() for s in selector_string.split(',')]
            for sel in selectors_to_try:
                try:
                    element = page.locator(sel).first
                    text_content = await element.text_content(timeout=3000)
                    if text_content is not None:
                        log.debug(f"Found SellerAmp text for '{selector_key}' using selector '{sel}': {text_content.strip()[:50]}")
                        return text_content.strip()
                except Exception as e:
                    log.debug(f"SellerAmp selector '{sel}' for '{selector_key}' failed: {type(e).__name__}")
            return ""
        
        # Extract static SellerAmp data fields first
        fulfilment_fee_text = await safe_extract_selleramp_text("fulfilment_fee")
        referral_fee_text = await safe_extract_selleramp_text("referral_fee")
        estimated_sales_text = await safe_extract_selleramp_text("estimated_sales")
        bsr_text = await safe_extract_selleramp_text("bsr")
        max_cost_text = await safe_extract_selleramp_text("max_cost")
        
        # Parse static extracted values
        if fulfilment_fee_text:
            selleramp_data["fulfilment_fee"] = self._parse_price(fulfilment_fee_text)
            log.info(f"SellerAmp fulfilment fee extracted: {selleramp_data['fulfilment_fee']}")
        if referral_fee_text:
            selleramp_data["referral_fee"] = self._parse_price(referral_fee_text)
            log.info(f"SellerAmp referral fee extracted: {selleramp_data['referral_fee']}")
        if estimated_sales_text:
            selleramp_data["estimated_monthly_sales"] = self._parse_number(estimated_sales_text)
            log.info(f"SellerAmp estimated sales extracted: {selleramp_data['estimated_monthly_sales']}")
        if bsr_text:
            selleramp_data["bsr_from_extension"] = self._parse_number(bsr_text)
        if max_cost_text:
            selleramp_data["max_workable_cost"] = self._parse_price(max_cost_text)
        
        # Enhanced input workflow for dynamic calculations with better error handling
        qi_cost_input = None
        input_workflow_success = False
        
        try:
            # Enhanced input field detection with multiple strategies
            log.info("Searching for qi_cost input field...")
            
            for sel in SELLERAMP_SELECTORS["qi_cost_input"].split(','):
                sel = sel.strip()
                try:
                    input_element = page.locator(sel).first
                    # Check both visibility and enabled state
                    if await input_element.is_visible(timeout=3000) and await input_element.is_enabled(timeout=1000):
                        qi_cost_input = input_element
                        log.info(f"Found qi_cost input field using selector: {sel}")
                        break
                except Exception as e:
                    log.debug(f"Selector '{sel}' failed: {e}")
                    continue
            
            if qi_cost_input:
                # Enhanced input workflow with better calculation triggering
                test_cost = "5.00"  # Use a reasonable test value
                log.info(f"Starting input workflow with test cost: {test_cost}")
                
                # Step 1: Clear the input field thoroughly
                await qi_cost_input.click()  # Focus the field first
                await qi_cost_input.fill("")  # Clear with empty string
                await page.wait_for_timeout(500)  # Brief pause
                
                # Step 2: Input the value with typing simulation
                await qi_cost_input.type(test_cost, delay=100)  # Type with delay for extension to register
                log.info(f"Typed cost value: {test_cost}")
                
                # Step 3: Multiple trigger strategies to ensure calculation
                trigger_strategies = [
                    {"action": "press", "key": "Enter", "wait": 2},
                    {"action": "press", "key": "Tab", "wait": 2}, 
                    {"action": "blur", "wait": 3}  # Trigger blur event
                ]
                
                for strategy in trigger_strategies:
                    try:
                        if strategy["action"] == "press":
                            await qi_cost_input.press(strategy["key"])
                            log.info(f"Pressed {strategy['key']} to trigger calculation")
                        elif strategy["action"] == "blur":
                            await qi_cost_input.blur()
                            log.info("Triggered blur event to ensure calculation")
                        
                        await asyncio.sleep(strategy["wait"])
                        
                        # Check if calculations have started by looking for change in ROI/profit fields
                        roi_text = await safe_extract_selleramp_text("roi")
                        profit_text = await safe_extract_selleramp_text("profit")
                        
                        if roi_text or profit_text:
                            log.info(f"Calculations detected after {strategy['action']} trigger")
                            input_workflow_success = True
                            break
                            
                    except Exception as e:
                        log.warning(f"Trigger strategy {strategy['action']} failed: {e}")
                        continue
                
                # Final wait for calculations to stabilize
                if input_workflow_success:
                    log.info("Waiting additional 3s for calculations to stabilize...")
                    await asyncio.sleep(3)
                    
                    # Extract the final calculated values
                    roi_text = await safe_extract_selleramp_text("roi")
                    profit_text = await safe_extract_selleramp_text("profit")
                    
                    if roi_text:
                        selleramp_data["roi_percent"] = self._parse_price(roi_text)
                        log.info(f"SellerAmp ROI extracted: {selleramp_data['roi_percent']}%")
                    if profit_text:
                        selleramp_data["profit_estimate"] = self._parse_price(profit_text)
                        log.info(f"SellerAmp profit extracted: {selleramp_data['profit_estimate']}")
                    
                    selleramp_data["input_cost_used"] = float(test_cost)
                    selleramp_data["status"] = "Static and dynamic values extracted successfully"
                else:
                    log.warning("Input workflow completed but calculations not detected")
                    selleramp_data["status"] = "Input attempted but calculations not detected"
            else:
                log.warning("qi_cost input field not found - only static values extracted")
                selleramp_data["status"] = "Static values extracted, input field not found"
                
        except Exception as e:
            log.error(f"Error during SellerAmp input workflow: {e}")
            selleramp_data["input_workflow_error"] = str(e)
            selleramp_data["status"] = "Input workflow failed with error"
        
        # Legacy fallback approach for sales text
        panel_selectors = ["div#sas-panel-quick-info", "div[id*='selleramp-container']", "div[class*='sas-app-host']", "div[id*='sas-root']"]
        quick_info_panel = None
        for sel in panel_selectors:
            panel_candidate = page.locator(sel).first
            if await panel_candidate.is_visible(timeout=1500): quick_info_panel = panel_candidate; log.info(f"SellerAmp panel detected with selector: {sel}"); break
        
        if quick_info_panel:
            try:
                sales_text_found = False
                possible_sales_texts = await quick_info_panel.locator("div, span").all_text_contents() 
                for text_content in possible_sales_texts:
                    if text_content:
                        match_bought = re.search(r"(\d+\+?)\s*bought in past month", text_content, re.IGNORECASE)
                        match_est_sales = re.search(r"Est\. Sales:\s*(\d+\+?)", text_content, re.IGNORECASE)
                        if match_bought: 
                            selleramp_data["monthly_sales_indicator_text"] = match_bought.group(0).strip() 
                            selleramp_data["estimated_monthly_sales_from_text"] = match_bought.group(1).replace('+', '')
                            sales_text_found = True 
                            break
                        elif match_est_sales: 
                            selleramp_data["monthly_sales_indicator_text"] = match_est_sales.group(0).strip()
                            selleramp_data["estimated_monthly_sales_from_text"] = match_est_sales.group(1).replace('+', '')
                            sales_text_found = True
                            break
                if sales_text_found: 
                    selleramp_data["status"] = "Sales indicator extracted via text selector"
                    log.info(f"SellerAmp sales indicator found: {selleramp_data['monthly_sales_indicator_text']}")
                    return selleramp_data
                else: 
                    log.info("SellerAmp sales text not found by specific selectors in detected panel.")
                    
                    # No sales text found - implement AI Vision fallback
                    if self.ai_client: 
                        log.info("Attempting AI vision fallback for SellerAmp sales velocity")
                        await quick_info_panel.scroll_into_view_if_needed()
                        await page.wait_for_timeout(500)
                        selleramp_filename = f"selleramp_panel_{asin}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        screenshot_path = os.path.join(self.output_dir, selleramp_filename)
                        await quick_info_panel.screenshot(path=screenshot_path) 
                        log.info(f"SellerAmp panel screenshot for AI vision: {screenshot_path}")
                        
                        ai_extracted_sales = await self._ai_extract_field_from_image(
                            screenshot_path, 
                            "the 'Estimated Monthly Sales' value or 'units bought in past month' numeric value from this SellerAmp panel. Provide only the numerical part or range (e.g., '100+' or '50')."
                        )
                        
                        if os.path.exists(screenshot_path): os.remove(screenshot_path)
                        
                        if ai_extracted_sales:
                            # Store the AI-extracted sales value with a clear key name
                            selleramp_data["estimated_monthly_sales_ai_vision"] = ai_extracted_sales
                            selleramp_data["status"] = "Sales velocity extracted via AI Vision from panel"
                            log.info(f"AI Vision successfully extracted SellerAmp sales velocity: {ai_extracted_sales}")
                        else: 
                            selleramp_data["status"] = "AI vision attempted on panel, but no sales data extracted"
                            log.warning("AI Vision could not extract SellerAmp sales velocity from panel screenshot")
            except Exception as e_sas: 
                log.error(f"Error processing detected SellerAmp panel: {e_sas}")
                selleramp_data["error"] = str(e_sas)
                selleramp_data["status"] = "Error during SellerAmp panel processing"
        else: 
            log.warning("SellerAmp panel not detected by any known selectors.")
            selleramp_data["status"] = "SellerAmp panel not detected."
            
        return selleramp_data

    async def _get_keepa_frame_locator(self, page: Page) -> Optional[FrameLocator]:
        # (Content from amazon_playwright_extractor_final_corrected.py)
        keepa_iframe_selectors = ["iframe[id*='keepaGraph']", "iframe#keepaExtension", "iframe[id*='keepa']", "iframe[src*='keepa.com']"]
        for selector in keepa_iframe_selectors:
            try:
                await page.wait_for_selector(selector, timeout=3000, state="attached")
                frame_loc = page.frame_locator(selector).first
                await frame_loc.locator("body div#box, body div#keepaContainer").first.is_visible(timeout=5000) 
                log.info(f"Keepa iframe found: {selector}")
                return frame_loc
            except Exception as e: log.debug(f"Keepa iframe check failed for selector {selector}: {e}")
        log.warning("Responsive Keepa iframe not located after checking all selectors."); return None

    async def _parse_keepa_ag_grid_product_details(self, keepa_frame: FrameLocator) -> Dict[str, Any]: # Removed table_container_selector, it's fixed
        details = {}
        grid_root_selector = "div#MoreTab1 div#grid-product-detail" 
        log.info(f"Parsing Keepa AG Grid for Product Details from: {grid_root_selector}")
        try:
            grid_root = keepa_frame.locator(grid_root_selector)
            # Wait for the specific content div of "Product Details" sub-tab
            await keepa_frame.locator("div#MoreTab1").wait_for(state="visible", timeout=5000)
            await grid_root.wait_for(state="visible", timeout=5000) # Then wait for the grid itself
            
            # Optimized timeout approach: 12-second primary + 5-second fallback
            try:
                # Primary attempt: 12-second timeout for first row detection
                log.info("Primary attempt: Waiting 12 seconds for AG Grid rows to load...")
                await grid_root.locator("div[role='row']").first.wait_for(state="visible", timeout=12000)
                
                # Minimal stabilization wait based on backup analysis
                await asyncio.sleep(1)  # Reduced from 2 seconds to 1 second
                
                # Process any available rows (no strict >1 requirement)
                rows = await grid_root.locator("div[role='row']").all()
                if len(rows) > 0:
                    log.info(f"✅ Primary attempt successful: {len(rows)} rows found")
                else:
                    raise PlaywrightTimeoutError("No rows found in primary attempt")
                    
            except PlaywrightTimeoutError:
                log.warning("Primary attempt failed, trying 5-second fallback...")
                try:
                    # Fallback attempt: 5-second additional timeout
                    await grid_root.locator("div[role='row']").first.wait_for(state="visible", timeout=5000)
                    await asyncio.sleep(1)  # Consistent 1-second stabilization
                    
                    rows = await grid_root.locator("div[role='row']").all()
                    if len(rows) > 0:
                        log.info(f"✅ Fallback attempt successful: {len(rows)} rows found")
                    else:
                        log.error("Fallback attempt found no rows - proceeding with empty result")
                        return details
                        
                except PlaywrightTimeoutError:
                    log.error("Both primary (12s) and fallback (5s) attempts failed - proceeding with empty result")
                    return details
            
            # Get final row count
            rows = await grid_root.locator("div[role='row']").all()
            log.info(f"Processing {len(rows)} rows in Keepa Product Details AG Grid.")
            
            # Enhanced row processing with better error handling
            successful_extractions = 0
            for row_index, row_loc in enumerate(rows):
                try:
                    key_cell = row_loc.locator("div[role='gridcell'][col-id='productKey']").first
                    value_cell = row_loc.locator("div[role='gridcell'][col-id='productValue']").first
                    
                    # Increased individual cell timeout and add visibility check
                    if await key_cell.is_visible(timeout=2000) and await value_cell.is_visible(timeout=2000):
                        key = (await key_cell.text_content() or "").strip()
                        value_text_content = (await value_cell.text_content() or "").strip()
                        value_text_content = ' '.join(value_text_content.split()) 
                        
                        if key and value_text_content and key.lower() != '\xa0':
                            value = value_text_content.strip()
                            try:
                                # Enhanced value parsing with better error handling
                                if "Reviews - Rating" in key: 
                                    match = re.search(r"([\d.]+)", value_text_content)
                                    value = float(match.group(1)) if match else value_text_content
                                elif any(k_word in key for k_word in ["Review Count", "Bought in past month", "Total Offer Count", "Number of Items", "Package - Quantity", "Item - Model (g)", "Package - Weight (g)", "FBA Seller Count", "FBM Seller Count", "Seller Count"]):
                                    match = re.search(r"([\d,]+)\\+?", value_text_content)
                                    value = self._parse_number(match.group(1)) if match else value_text_content
                                elif "Package - Dimension" in key: 
                                    value = value_text_content.split('\\n')[0].strip() 
                                elif "FBA Pick&Pack Fee" in key or "Referral Fee based on current Buy Box price" in key:
                                    log.info(f"Found potential fee key '{key}' with raw value: '{value_text_content}' in Keepa AG Grid.")
                                    match = re.search(r"[£$€]?\\s*([\\d.]+)", value_text_content)
                                    if match:
                                        value = self._parse_price(match.group(1))
                                    else:
                                        # Alternative pattern without currency symbol
                                        match = re.search(r"([\d.]+)", value_text_content)
                                        value = self._parse_price(match.group(1)) if match else value_text_content
                            except Exception as e:
                                log.warning(f"Error parsing value for key '{key}': {e}. Using raw text.")
                            
                            details[key] = value
                            successful_extractions += 1
                            
                except Exception as e:
                    log.warning(f"Error processing row {row_index}: {e}")
                    continue
            
            if details: 
                log.info(f"✅ Successfully parsed {successful_extractions} items from Keepa Product Details AG Grid.")
            else: 
                log.warning("❌ No data parsed from Keepa Product Details AG Grid via selectors.")
                
        except PlaywrightTimeoutError: 
            log.warning(f"⚠️ Timeout waiting for Keepa Product Details AG Grid root or its container: {grid_root_selector}")
        except Exception as e: 
            log.error(f"❌ Error parsing Keepa Product Details AG Grid: {e}", exc_info=True)
        return details

    async def _extract_keepa_data(self, page: Page, get_html_content_func, asin: str) -> Dict[str, Any]:
        # filepath: c:\Users\chris\Amazon-FBA-Agent-System\tools\amazon_playwright_extractor.py
        # (Content from amazon_playwright_extractor_final_corrected.py, with refined tab interaction)
        keepa_data = {"status": "Not detected or no data extracted"}
        log.info("Attempting to extract Keepa data...")
        keepa_frame = await self._get_keepa_frame_locator(page)
        if not keepa_frame: keepa_data["status"] = "Keepa iframe not found."; return keepa_data

        try: 
            bought_month_locator = keepa_frame.locator("div#priceHistory span:text-matches('Bought in past month:\\s*([\\d\\+]+)', 'i')").first
            if await bought_month_locator.is_visible(timeout=3000):
                text_content = await bought_month_locator.text_content()
                match_obj = re.search(r"Bought in past month:\s*([\d\+]+)", text_content or "", re.IGNORECASE) # Renamed 'match'
                if match_obj: keepa_data["bought_in_past_month_price_history"] = match_obj.group(1).strip(); log.info(f"Keepa 'Bought in past month' (Price History): {match_obj.group(1).strip()}")
        except Exception as e: log.warning(f"Could not extract Keepa 'Bought in past month' from Price History text: {e}")

        try: 
            sales_rank_table = keepa_frame.locator("div#priceHistory table#salesRankDetails")
            if await sales_rank_table.is_visible(timeout=3000):
                srd = {}
                rows = await sales_rank_table.locator("tbody tr").all()
                if len(rows) > 2: 
                    cells = await rows[2].locator("td").all_text_contents()
                    if len(cells) >= 5: srd["main_cat_current_rank"] = self._parse_number(cells[0]); srd["main_cat_name"] = cells[4].split('\n')[0].strip()
                if len(rows) > 3: 
                    cells = await rows[3].locator("td").all_text_contents()
                    if len(cells) >= 5: srd["sub_cat_current_rank"] = self._parse_number(cells[0]); srd["sub_cat_name"] = cells[4].split('\n')[0].strip()
                if srd: keepa_data["sales_rank_details_table"] = srd; log.info(f"Keepa Sales Rank Details Table parsed.")
        except Exception as e: log.warning(f"Could not parse Keepa Sales Rank Details Table: {e}")

        # Skip Keepa Graph AI Analysis as per requirements (Fix 2.4)
        log.info("Keepa Graph AI Analysis is currently disabled as per requirements (Fix 2.4).")
        keepa_data["ai_graph_analysis_status"] = "Keepa Graph AI Analysis disabled"

        try: 
            main_data_tab_selector = "li#tabMore"; product_details_sub_tab_selector = "li.tabSubItem[data-box='#MoreTab1']"
            data_tab_button = keepa_frame.locator(main_data_tab_selector)
            product_details_content_selector = "div#MoreTab1" 

            if await data_tab_button.is_visible(timeout=5000):
                data_tab_active = "active" in (await data_tab_button.get_attribute("class") or "")
                log.info(f"Keepa Data tab found. Currently active: {data_tab_active}")
                if not data_tab_active: 
                    log.info("Clicking Keepa 'Data' tab...")
                    await data_tab_button.click(timeout=3000)
                    # Add a brief wait after clicking to let the tab activation settle
                    await asyncio.sleep(2)
                    # INITIAL WAIT for the Product-Details wrapper to appear with enhanced retry logic
                    max_initial_attempts = 2
                    initial_timeout = 12000  # Reduced from 30000ms to 12000ms for faster processing
                    
                    for attempt in range(max_initial_attempts):
                        try:
                            log.info(f"Attempt {attempt + 1}/{max_initial_attempts}: Waiting {initial_timeout}ms for Product-Details wrapper...")
                            await keepa_frame.locator(product_details_content_selector).wait_for(
                                state="visible", timeout=initial_timeout
                            )
                            log.info(f"✅ Product-Details wrapper appeared on attempt {attempt + 1}")
                            break
                        except PlaywrightTimeoutError:
                            if attempt < max_initial_attempts - 1:
                                log.warning(f"Product-Details wrapper timeout on attempt {attempt + 1}, retrying...")
                                await asyncio.sleep(5)  # Wait before retry
                            else:
                                log.error(f"Product-Details wrapper did not appear after {max_initial_attempts} attempts – aborting.")
                                keepa_data["status"] = "Product details tab timeout (initial)"
                                return keepa_data

                    # CONDITIONAL EXTENSION ─ check if the grid container inside the tab is ready with enhanced logic
                    grid_container_selector = f"{product_details_content_selector} div#grid-container-product-detail"
                    if not await keepa_frame.locator(grid_container_selector).is_visible(timeout=2000):  # Increased from 1000ms
                        log.warning(
                            "Product-Details tab visible, but inner grid still not ready – "
                            "extending wait with retry logic."
                        )
                        
                        # Enhanced retry logic for grid container
                        max_grid_attempts = 3
                        grid_timeout = 15000  # Increased from 10000ms to 15000ms
                        
                        for attempt in range(max_grid_attempts):
                            try:
                                log.info(f"Grid attempt {attempt + 1}/{max_grid_attempts}: Waiting {grid_timeout}ms for grid container...")
                                await keepa_frame.locator(grid_container_selector).wait_for(
                                    state="visible", timeout=grid_timeout
                                )
                                log.info(f"✅ Grid became visible after attempt {attempt + 1} – continuing.")
                                break
                            except PlaywrightTimeoutError:
                                if attempt < max_grid_attempts - 1:
                                    log.warning(f"Grid timeout on attempt {attempt + 1}, retrying...")
                                    await asyncio.sleep(3)  # Wait before retry
                                else:
                                    log.error(
                                        f"Grid still not visible after {max_grid_attempts} attempts – giving up on Keepa details."
                                    )
                                    keepa_data["status"] = "Product details tab timeout (extended)"
                                    return keepa_data
            
                sub_tab_button = keepa_frame.locator(product_details_sub_tab_selector)
                if await sub_tab_button.is_visible(timeout=5000): 
                    sub_tab_active = "active" in (await sub_tab_button.get_attribute("class") or "")
                    if not sub_tab_active: 
                        log.info("Clicking Keepa 'Product Details' sub-tab...")
                        await sub_tab_button.click(timeout=3000)
                        # Wait for the grid container to become visible
                        await keepa_frame.locator(f"{product_details_content_selector} div#grid-container-product-detail").wait_for(state="visible", timeout=5000)
                        # No additional wait needed here as data starts loading when Data tab is clicked
                    
                    parsed_details = await self._parse_keepa_ag_grid_product_details(keepa_frame) # Removed table_container_selector
                    if parsed_details: keepa_data["product_details_tab_data"] = parsed_details
                    elif self.ai_client: 
                        log.warning("Parsing Keepa Product Details AG Grid failed via selectors, trying AI vision.")
                        table_container_loc = keepa_frame.locator("div#MoreTab1 div#grid-container-product-detail") 
                        if await table_container_loc.is_visible(timeout=3000): 
                            keepa_table_filename = f"keepa_prod_details_tbl_{asin}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                            screenshot_path = os.path.join(self.output_dir, keepa_table_filename)
                            await table_container_loc.screenshot(path=screenshot_path)
                            log.info(f"Keepa Product Details table screenshot saved to {screenshot_path} for AI analysis.") 
                            ai_table_data = await self._ai_extract_field_from_image(screenshot_path, "all key-value pairs from this Product Details table. Format as JSON.")
                            if os.path.exists(screenshot_path): os.remove(screenshot_path)
                            if ai_table_data: keepa_data["product_details_tab_ai_vision"] = ai_table_data
                        else: log.warning("Keepa Product Details table container not visible for AI screenshot.")
                else: log.warning("Keepa 'Product Details' sub-tab not found or not visible.")
            else: log.warning("Keepa main 'Data' tab not found or not visible.")
        except PlaywrightTimeoutError as pte: log.error(f"Timeout error processing Keepa 'Product Details' tab: {pte}")
        except Exception as e: log.error(f"Error processing Keepa 'Product Details' tab: {e}", exc_info=True)
        
        keepa_data["status"] = "Extraction process completed" 
        if not any(k not in ["status"] for k in keepa_data): 
            keepa_data["status"] = "No specific Keepa data points extracted beyond initial checks."

        return keepa_data

    async def _ai_extract_field_from_html(self, html_content: str, field_description: str, page_url: str) -> Optional[str]:
        # (Content from amazon_playwright_extractor_final_corrected.py)
        if not self.ai_client: return None
        try:
            max_html_chars = 24000 
            if len(html_content) > max_html_chars:
                log.warning(f"HTML content for AI extraction truncated to {max_html_chars} chars.")
                html_content = html_content[:max_html_chars]
            prompt = (f"You are an expert web data extractor. From the following HTML content of the webpage {page_url}, extract the '{field_description}'. Provide only the extracted value. If the information is not found, respond with 'Not found'.\n\nHTML Content (possibly truncated):\n{html_content}")
            response = await asyncio.to_thread( self.ai_client.chat.completions.create, model=self.openai_model, messages=[{"role": "user", "content": prompt}], temperature=0.0 )
            extracted_value = response.choices[0].message.content.strip()
            return None if extracted_value.lower() == "not found" else extracted_value
        except Exception as e: log.error(f"AI HTML extraction for '{field_description}' failed: {e}"); return None

    async def _ai_extract_field_from_image(self, image_path: str, field_description: str) -> Optional[str]:
        # (Content from amazon_playwright_extractor_final_corrected.py)
        if not self.ai_client: return None
        if not os.path.exists(image_path): log.error(f"Image file not found: {image_path}"); return None
        try:
            with open(image_path, "rb") as image_file: base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            log.info(f"AI vision extraction for: '{field_description}' from {image_path} using {self.openai_model}")
            response = await asyncio.to_thread( self.ai_client.chat.completions.create, model=self.openai_model, messages=[{"role": "user", "content": [{"type": "text", "text": f"From image, {field_description}"}, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}]}], max_tokens=400, temperature=0.1 )
            extracted_value = response.choices[0].message.content.strip()
            if extracted_value.lower() in ["not found", "none", ""]: return None
            if "captcha" in field_description.lower():
                 original_value_for_log = extracted_value
                 extracted_value = re.sub(r'[^a-zA-Z0-9]', '', extracted_value) 
                 if not (4 <= len(extracted_value) < 10):
                     log.warning(f"AI vision for CAPTCHA returned suspicious: '{original_value_for_log}' -> Filtered: '{extracted_value}'.")
                     return None
            log.info(f"AI vision successful for '{field_description}': '{extracted_value[:100]}...'")
            return extracted_value
        except Exception as e: log.error(f"AI vision extraction for '{field_description}' failed: {e}"); return f"[AI vision error: {e}]"

    async def _ai_diagnose_extraction_failure(self, asin: str, error_message: str, page_url: str) -> str:
        # (Content from amazon_playwright_extractor_final_corrected.py)
        if not self.ai_client: return "AI client for diagnostics unavailable."
        try:
            prompt = f"Data extraction for Amazon ASIN {asin} (URL: {page_url}) failed. Error: '{error_message}'. Likely reasons and solutions?"
            response = await asyncio.to_thread(self.ai_client.chat.completions.create, model=self.openai_model, messages=[{"role": "user", "content": prompt}])
            return response.choices[0].message.content.strip()
        except Exception as e: return f"[AI diagnostic error: {e}]"

    async def _ai_diagnose_navigation_failure(self, url: str, error_message: str, page: Optional[Page]) -> str:
        # (Content from amazon_playwright_extractor_final_corrected.py)
        if not self.ai_client: return "AI client for diagnostics unavailable."
        context_info = f"Navigation to URL '{url}' failed. Error: {error_message}."
        if page:
            try:
                nav_fail_filename = f"nav_fail_{url.split('/')[-1] if '/' in url else 'unknown_page'}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                ss_path = os.path.join(self.output_dir, nav_fail_filename)
                await page.screenshot(path=ss_path, full_page=True)
                context_info += f" Screenshot saved to '{ss_path}'."
            except Exception as e_ss: log.warning(f"Could not take screenshot for nav failure: {e_ss}")
        try:
            prompt = f"{context_info} Common reasons and troubleshooting steps?"
            response = await asyncio.to_thread(self.ai_client.chat.completions.create, model=self.openai_model, messages=[{"role": "user", "content": prompt}])
            return response.choices[0].message.content.strip()
        except Exception as e: return f"[AI diagnostic error: {e}]"

    def _parse_price(self, price_text: str) -> float:
        # (Content from amazon_playwright_extractor_final_corrected.py)
        if not price_text: return 0.0
        match = re.search(r'[£$€]?\s*([\d,.]+)', price_text)
        if match:
            try:
                price_str = match.group(1)
                if ',' in price_str and '.' in price_str: 
                    if price_str.rfind(',') > price_str.rfind('.'): price_str = price_str.replace('.', '').replace(',', '.')
                    else: price_str = price_str.replace(',', '')
                elif ',' in price_str: 
                    if len(price_str.split(',')[-1]) == 2 and price_str.count(',') == 1 : price_str = price_str.replace(',', '.')
                    else: price_str = price_str.replace(',', '')
                return float(price_str)
            except ValueError: pass
        cleaned_price = re.sub(r'[^\d.]', '', price_text.replace(',', '.')) 
        if cleaned_price.count('.') > 1: cleaned_price = cleaned_price.replace('.', '', cleaned_price.count('.') -1) 
        if cleaned_price:
            try: return float(cleaned_price)
            except ValueError: return 0.0
        return 0.0
            
    def _parse_number(self, text: str) -> int:
        # (Content from amazon_playwright_extractor_final_corrected.py)
        if not text: return 0
        cleaned_text = re.sub(r'[^\d]', '', text)
        return int(cleaned_text) if cleaned_text else 0
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        ENHANCED TITLE MATCHING - Fixes 90% failure rate with multi-layered scoring.
        
        Improvements over basic Jaccard similarity:
        1. Removes common stop words that add noise
        2. Prioritizes brand and model words with higher weights
        3. Handles package size variations intelligently
        4. Uses token-based scoring with position awareness
        5. Implements deterministic fallback rules
        """
        if not title1 or not title2:
            return 0.0
            
        # Enhanced preprocessing with stop word removal
        def preprocess_title(title):
            title = title.lower().strip()
            # Remove common fluff words that cause false negatives
            stop_words = {
                'new', 'sale', 'offer', 'deal', 'hot', 'best', 'top', 'premium', 
                'quality', 'great', 'amazing', 'perfect', 'ultimate', 'professional',
                'classic', 'original', 'genuine', 'authentic', 'official', 'branded',
                'the', 'and', 'or', 'with', 'for', 'in', 'on', 'at', 'by', 'from'
            }
            words = [w for w in title.split() if w not in stop_words and len(w) > 2]
            return words
        
        words1 = preprocess_title(title1)
        words2 = preprocess_title(title2)
        
        if not words1 or not words2:
            return 0.0
        
        # Multi-layer scoring approach
        total_score = 0.0
        max_possible_score = 0.0
        
        # Layer 1: Brand matching (highest weight)
        brand_indicators = {'apple', 'samsung', 'sony', 'nike', 'adidas', 'lego', 'disney', 'microsoft'}
        brand_words1 = set(w for w in words1 if w in brand_indicators)
        brand_words2 = set(w for w in words2 if w in brand_indicators)
        if brand_words1 and brand_words2:
            brand_match = len(brand_words1.intersection(brand_words2)) / max(len(brand_words1), len(brand_words2))
            total_score += brand_match * 0.4  # 40% weight for brand matching
        max_possible_score += 0.4
        
        # Layer 2: Model/Product number matching (high weight)
        model_pattern = r'\b[A-Z0-9]+\b'
        models1 = set(re.findall(model_pattern, ' '.join(words1).upper()))
        models2 = set(re.findall(model_pattern, ' '.join(words2).upper()))
        if models1 and models2:
            model_match = len(models1.intersection(models2)) / max(len(models1), len(models2))
            total_score += model_match * 0.3  # 30% weight for model matching
        max_possible_score += 0.3
        
        # Layer 3: Package size matching (medium weight)
        def extract_package_info(words):
            package_indicators = []
            for i, word in enumerate(words):
                if word in ['pack', 'set', 'box', 'bundle', 'kit', 'pieces', 'pcs']:
                    # Look for numbers before the package indicator
                    if i > 0 and words[i-1].isdigit():
                        package_indicators.append(f"{words[i-1]}_{word}")
                    elif i < len(words)-1 and words[i+1].isdigit():
                        package_indicators.append(f"{words[i+1]}_{word}")
            return set(package_indicators)
        
        package1 = extract_package_info(words1)
        package2 = extract_package_info(words2)
        if package1 and package2:
            package_match = len(package1.intersection(package2)) / max(len(package1), len(package2))
            total_score += package_match * 0.2  # 20% weight for package matching
        elif not package1 and not package2:
            # Both have no package info - this is actually a good match
            total_score += 0.2
        max_possible_score += 0.2
        
        # Layer 4: Core word matching with TF-IDF concept (remaining weight)
        words1_set = set(words1)
        words2_set = set(words2)
        intersection = len(words1_set.intersection(words2_set))
        union = len(words1_set.union(words2_set))
        
        if union > 0:
            jaccard_score = intersection / union
            total_score += jaccard_score * 0.1  # 10% weight for general word matching
        max_possible_score += 0.1
        
        # Normalize score
        final_score = total_score / max_possible_score if max_possible_score > 0 else 0.0
        
        # Deterministic fallback rule for high-confidence matches
        if intersection >= 3 and final_score >= 0.7:
            final_score = min(0.95, final_score + 0.15)  # Boost high-quality matches
        
        return round(final_score, 3)

    def _estimate_sales_from_bsr(self, rank: int, category: str = "") -> int:
        # (Content from amazon_playwright_extractor_final_corrected.py)
        category = category.lower() if category else ""
        multiplier = 1.0
        if any(term in category for term in ["books", "kindle", "ebook"]): multiplier = 0.5
        elif any(term in category for term in ["electronics", "computers", "technology"]): multiplier = 1.2
        elif any(term in category for term in ["toys", "games"]): multiplier = 1.5
        elif any(term in category for term in ["grocery", "food", "consumable"]): multiplier = 2.0
        if rank < 1: return 0 # Added check for invalid rank
        if rank < 500: return int(1000 * multiplier) 
        elif rank < 1000: return int(500 * multiplier)
        elif rank < 5000: return int(100 * multiplier)
        elif rank < 10000: return int(50 * multiplier)
        elif rank < 50000: return int(20 * multiplier)
        elif rank < 100000: return int(10 * multiplier)
        else: return int(5 * multiplier)

    async def search_by_title(self, title: str, exact_match: bool = False) -> Dict[str, Any]:
        result: Dict[str, Any] = {"query_title": title, "timestamp": datetime.now().isoformat(), "results": []}
        page: Optional[Page] = None
        try:
            if not self.browser or not self.browser.is_connected(): await self.connect()
            if not self.browser: result["error"] = "Browser not connected"; return result
            page = await self.browser.new_page()
            search_query = '+'.join(title.split()); search_url = f"https://www.amazon.co.uk/s?k={search_query}"
            log.info(f"Searching Amazon: {search_url}")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=DEFAULT_NAVIGATION_TIMEOUT)
            await page.wait_for_selector("[data-component-type='s-search-result']", timeout=15000)
            search_result_elements = await page.query_selector_all("[data-component-type='s-search-result']")
            log.info(f"Found {len(search_result_elements)} search results for '{title}'")
            
            # Collect results with similarity scoring
            results_with_scores = []
            
            for res_elem in search_result_elements[:5]: 
                item_data: Dict[str, Any] = {"asin": await res_elem.get_attribute("data-asin")}
                title_el = await res_elem.query_selector("h2 a.a-link-normal span.a-text-normal")
                if title_el: item_data["title"] = (await title_el.text_content() or "").strip()
                price_el = await res_elem.query_selector(".a-price .a-offscreen")
                if price_el: item_data["price"] = self._parse_price(await price_el.text_content() or "")
                img_el = await res_elem.query_selector("img.s-image")
                if img_el: item_data["image_url"] = await img_el.get_attribute("src")
                rating_el = await res_elem.query_selector(".a-icon-star-small") 
                if rating_el:
                    rating_text_aria = await rating_el.get_attribute("aria-label")
                    rating_text_span = await rating_el.query_selector("span.a-icon-alt") 
                    rating_text_content = rating_text_aria or (await rating_text_span.text_content() if rating_text_span else None)

                    if rating_text_content:
                        rating_match = re.search(r"([\d.]+)\s*out of", rating_text_content)
                        if rating_match: item_data["rating"] = float(rating_match.group(1))
                reviews_el = await res_elem.query_selector("span.a-size-base[dir='auto'], a.a-link-normal span.a-size-base") 
                if reviews_el:
                    reviews_text = await reviews_el.text_content()
                    if reviews_text: item_data["review_count"] = self._parse_number(reviews_text)
                
                if item_data.get("asin") and item_data.get("title"):
                    # Calculate similarity score and add to results with score
                    similarity_score = self._calculate_title_similarity(title, item_data["title"])
                    item_data["title_similarity_score"] = round(similarity_score, 3)  # Add score to item data
                    results_with_scores.append((item_data, similarity_score))
                    
                    # ENHANCED THRESHOLD - Optimized for new multi-layer algorithm
                    # 0.75+ = High confidence with new algorithm (vs 0.85 with old basic algorithm)
                    if exact_match and similarity_score >= 0.75:
                        result["exact_match_found"] = True
                        result["exact_match_item"] = item_data
                        log.info(f"HIGH CONFIDENCE MATCH: {similarity_score:.3f} - '{item_data.get('title', '')[:50]}...'")
                        break
            
            # Sort results by their similarity score (highest first)
            results_with_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Add sorted results to the final result
            result["results"] = [item_data for item_data, _ in results_with_scores]
            
            # Log the similarity-based sorting
            if len(result["results"]) > 0:
                log.info(f"Search results sorted by title similarity. Top result: '{result['results'][0].get('title', '')}' with score {result['results'][0].get('title_similarity_score', 0)}")
            
            return result
        except Exception as e: 
            log.error(f"Error during Amazon search for '{title}': {e}", exc_info=True)
            result["error"] = str(e)
            return result
        finally:
            if page: await page.close()

    async def close(self):
        if self.browser and self.browser.is_connected():
            log.info("Closing browser connection.")
            try: await self.browser.close()
            except Exception as e: log.error(f"Error closing browser: {e}")
        self.browser = None
