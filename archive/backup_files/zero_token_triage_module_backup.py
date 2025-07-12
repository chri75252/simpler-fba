"""
Zero Token Triage Module (Patched, File 1-style waits/pages/extension logic)
- Uses: Existing browser, reuses pages for SellerAmp extension loading
- Waits: 10s for navigation, 25s for extension data
- Extracts SellerAmp metrics from Amazon product detail page (UK)
"""

import re
import os
import sys
import asyncio
import logging
import datetime
import json
from typing import Dict, Any, Optional, Tuple
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as AsyncPlaywrightTimeoutError, Error as PlaywrightError

# --- WAITS (File 1 logic) ---
POST_NAVIGATION_STABILIZE_WAIT = 10  # seconds
EXTENSION_DATA_WAIT = 25  # seconds

TRIAGE_OUTPUT_DIR = os.path.join("C:\\Users\\chris\\Amazon-FBA-Agent-System\\OUTPUTS", "triage_results")
TRIAGE_DEBUG_DIR = os.path.join(TRIAGE_OUTPUT_DIR, "debug")
os.makedirs(TRIAGE_OUTPUT_DIR, exist_ok=True)
os.makedirs(TRIAGE_DEBUG_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- Parsing helpers ---
def _parse_triage_float(text: str) -> float:
    if not text: return 0.0
    match = re.search(r"[-+]?\d*\.\d+|\d+", text.replace(",", "").replace("£", "").replace("$", "").replace("€", "").replace("%",""))
    return float(match.group(0)) if match else 0.0

def _parse_triage_int(text: str) -> int:
    if not text: return 0
    match = re.search(r"\d+", text.replace(",", ""))
    return int(match.group(0)) if match else 0

def _parse_rating_from_text(text: str) -> float:
    if not text:
        return 0.0
    match = re.search(r"([0-5]\.\d+|[0-5])", text)
    return float(match.group(1)) if match else 0.0

def _parse_bsr_from_text(text: str) -> int:
    if not text:
        return 0
    match = re.search(r"#?(\d[\d,]*)", text)
    return int(match.group(1).replace(",", "")) if match else 0

async def _safe_extract_text_from_page(page: Page, selector_key: str, selectors: Dict, default_value: str = "") -> str:
    selector_string = selectors.get(selector_key, "")
    if not selector_string: return default_value
    selectors_to_try = [s.strip() for s in selector_string.split(',')]
    for sel in selectors_to_try:
        try:
            element = page.locator(sel).first
            text_content = await element.text_content(timeout=3500)
            if text_content is not None:
                log.debug(f"Triage: Found text for '{selector_key}' using selector '{sel}': {text_content.strip()[:50]}")
                return text_content.strip()
        except PlaywrightError as e:
            log.debug(f"Triage: Selector '{sel}' for '{selector_key}' failed or timed out: {type(e).__name__}")
        except Exception as e:
            log.error(f"Triage: Unexpected error with selector '{sel}' for '{selector_key}': {e}")
    log.warning(f"Triage: Could not extract text for '{selector_key}' using selectors: {selector_string}")
    return default_value

async def _get_connected_browser_page(playwright_instance, chrome_debug_port: int) -> Tuple[Optional[Browser], Optional[Page]]:
    browser = None
    try:
        browser = await playwright_instance.chromium.connect_over_cdp(f"http://localhost:{chrome_debug_port}")
        log.info(f"Successfully connected to Chrome on debug port {chrome_debug_port} for triage.")
        all_pages = browser.contexts[0].pages if browser.contexts and len(browser.contexts) > 0 else []
        if all_pages:
            log.info(f"Found {len(all_pages)} existing pages")
            test_page = all_pages[0]
            log.info(f"Using existing page: {test_page.url}")
            await test_page.bring_to_front()
            return browser, test_page
        else:
            log.info("No existing pages found. Creating new page")
            page = await browser.contexts[0].new_page()
            await page.goto("about:blank", timeout=10000)
            await page.close()
            return browser, None
    except Exception as e:
        log.error(f"Failed to connect to Chrome or get page for triage on port {chrome_debug_port}: {e}")
        if browser:
            await browser.close()
        return None, None

async def perform_zero_token_triage(
    asin: str,
    landed_cost: float,
    chrome_debug_port: int = 9222,
    shared_browser_page: Optional[Page] = None
) -> Dict[str, Any]:
    log.info(f"TRIAGE STARTING for ASIN: {asin} with landed cost: {landed_cost}")
    output = {
        "asin": asin,
        "verdict": "ERROR",
        "reasons": ["Triage not fully performed"],
        "metrics": {}
    }
    playwright = None
    browser_conn_internal = None
    page_internal = None
    try:
        if shared_browser_page:
            page = shared_browser_page
            log.info("Triage using shared browser page.")
        else:
            playwright = await async_playwright().start()
            browser_conn_internal, page_internal = await _get_connected_browser_page(playwright, chrome_debug_port)
            if not page_internal:
                output["reasons"] = ["Failed to get browser page for triage"]
                if playwright: await playwright.stop()
                return output
            page = page_internal

        await page.goto(f"https://www.amazon.co.uk/dp/{asin}", wait_until="domcontentloaded", timeout=45000)
        log.info(f"Triage: Navigated to ASIN {asin}")
        log.info(f"Triage: Waiting {POST_NAVIGATION_STABILIZE_WAIT}s for navigation stabilization.")
        await asyncio.sleep(POST_NAVIGATION_STABILIZE_WAIT)

        log.info(f"Triage: Waiting up to {EXTENSION_DATA_WAIT}s for SellerAmp panel and data.")
        
        # R3: Longer wait & polling loop for SellerAmp
        timeout = 45
        poll = 1
        elapsed = 0
        selleramp_detected = False
        
        while elapsed < timeout:
            # Check for SellerAmp panel
            panel_element = await page.query_selector("div#quick-info-body")
            if panel_element:
                log.info(f"SellerAmp panel detected after {elapsed}s")
                selleramp_detected = True
                break
            
            # Also check alternative selectors
            alt_panel = await page.query_selector("div.qi-wrapper, div.qi-container, div.qi-row")
            if alt_panel:
                log.info(f"SellerAmp alternative panel detected after {elapsed}s")
                selleramp_detected = True
                break
                
            await asyncio.sleep(poll)
            elapsed += poll
            log.debug(f"SellerAmp polling: {elapsed}s elapsed, still waiting...")
        
        if not selleramp_detected:
            log.warning(f"SellerAmp panel not detected after {timeout}s timeout")
        
        # R3: Take screenshot and page content to debug directory
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        try:
            screenshot_path = os.path.join(TRIAGE_DEBUG_DIR, f"selleramp_screenshot_{asin}_{timestamp}.png")
            await page.screenshot(path=screenshot_path)
            log.info(f"Debug screenshot saved: {screenshot_path}")
            
            page_content = await page.content()
            content_path = os.path.join(TRIAGE_DEBUG_DIR, f"selleramp_content_{asin}_{timestamp}.html")
            with open(content_path, 'w', encoding='utf-8') as f:
                f.write(page_content)
            log.info(f"Debug page content saved: {content_path}")
        except Exception as e:
            log.warning(f"Failed to save debug files: {e}")

        await asyncio.sleep(2)  # Small extra wait after panel detected

        # --- Updated SellerAmp Selectors to match specific HTML elements ---
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
        AMAZON_PAGE_SELECTORS = {
            "rating": "#acrPopover[title*='out of 5 stars'] .a-icon-alt",
            "reviews": "#acrCustomerReviewText"
        }

        # Extract static SellerAmp data fields first
        sa_fulfilment_fee_txt = await _safe_extract_text_from_page(page, "fulfilment_fee", SELLERAMP_SELECTORS)
        sa_referral_fee_txt = await _safe_extract_text_from_page(page, "referral_fee", SELLERAMP_SELECTORS)
        sa_estimated_sales_txt = await _safe_extract_text_from_page(page, "estimated_sales", SELLERAMP_SELECTORS)
        sa_bsr_txt = await _safe_extract_text_from_page(page, "bsr", SELLERAMP_SELECTORS)
        sa_max_cost_txt = await _safe_extract_text_from_page(page, "max_cost", SELLERAMP_SELECTORS)
        
        # Implement input workflow for dynamic calculations
        dynamic_roi_txt = ""
        dynamic_profit_txt = ""
        input_cost_used = 0.0
        
        try:
            # Find the qi_cost input field
            qi_cost_input = None
            for sel in SELLERAMP_SELECTORS["qi_cost_input"].split(','):
                sel = sel.strip()
                try:
                    input_element = page.locator(sel).first
                    if await input_element.is_visible(timeout=2000):
                        qi_cost_input = input_element
                        log.info(f"Triage: Found qi_cost input field using selector: {sel}")
                        break
                except Exception:
                    continue
            
            if qi_cost_input:
                # Input the landed cost to trigger calculations
                test_cost = str(landed_cost) if landed_cost > 0 else "5.00"
                log.info(f"Triage: Inputting cost value: {test_cost}")
                
                # Clear and fill the input field
                await qi_cost_input.clear()
                await qi_cost_input.fill(test_cost)
                
                # Trigger calculation by pressing Enter
                await qi_cost_input.press("Enter")
                
                # Wait for calculations to complete
                await asyncio.sleep(3)  # 3 second wait for calculations
                log.info("Triage: Waiting for SellerAmp calculations to complete...")
                
                # Now extract the dynamic calculated values
                dynamic_roi_txt = await _safe_extract_text_from_page(page, "roi", SELLERAMP_SELECTORS)
                dynamic_profit_txt = await _safe_extract_text_from_page(page, "profit", SELLERAMP_SELECTORS)
                input_cost_used = float(test_cost)
                
                if dynamic_roi_txt:
                    log.info(f"Triage: Dynamic ROI extracted: {dynamic_roi_txt}")
                if dynamic_profit_txt:
                    log.info(f"Triage: Dynamic profit extracted: {dynamic_profit_txt}")
            else:
                log.warning("Triage: qi_cost input field not found - using static values only")
                # Fallback to static extraction if input field not found
                dynamic_roi_txt = await _safe_extract_text_from_page(page, "roi", SELLERAMP_SELECTORS)
                dynamic_profit_txt = await _safe_extract_text_from_page(page, "profit", SELLERAMP_SELECTORS)
                
        except Exception as e:
            log.error(f"Triage: Error during input workflow: {e}")
            # Fallback to static extraction
            dynamic_roi_txt = await _safe_extract_text_from_page(page, "roi", SELLERAMP_SELECTORS)
            dynamic_profit_txt = await _safe_extract_text_from_page(page, "profit", SELLERAMP_SELECTORS)
        
        # Extract Amazon page data
        amazon_rating_txt = await _safe_extract_text_from_page(page, "rating", AMAZON_PAGE_SELECTORS)
        amazon_reviews_txt = await _safe_extract_text_from_page(page, "reviews", AMAZON_PAGE_SELECTORS)

        # Parse all extracted values
        fulfilment_fee = _parse_triage_float(sa_fulfilment_fee_txt)
        referral_fee = _parse_triage_float(sa_referral_fee_txt)
        roi_percent = _parse_triage_float(dynamic_roi_txt)
        net_profit = _parse_triage_float(dynamic_profit_txt)
        bsr = _parse_triage_int(sa_bsr_txt)
        est_sales = _parse_triage_int(sa_estimated_sales_txt)
        max_workable_cost = _parse_triage_float(sa_max_cost_txt)
        rating = _parse_rating_from_text(amazon_rating_txt)
        review_count = _parse_triage_int(amazon_reviews_txt)
        
        metrics = {
            "triage_fulfilment_fee_ext": fulfilment_fee,
            "triage_referral_fee_ext": referral_fee,
            "triage_roi_percent_ext": roi_percent,
            "triage_net_profit_ext": net_profit,
            "triage_bsr_ext": bsr,
            "triage_est_sales_ext": est_sales,
            "triage_max_workable_cost_ext": max_workable_cost,
            "amazon_rating_page": rating,
            "amazon_review_count_page": review_count,
            "input_cost_used": input_cost_used
        }
        output["metrics"] = metrics
        log.info(f"Triage Metrics for {asin}: {metrics}")
        reasons = []
        # Add your threshold logic here
        if roi_percent < 25.0 and landed_cost > 0:
            reasons.append(f"Low ROI from Extension: {roi_percent}% < 25.0%")
        if net_profit < 2.0 and landed_cost > 0:
            reasons.append(f"Low Net Profit from Extension: £{net_profit} < £2.0")
        if bsr > 150000 and bsr > 0:
            reasons.append(f"High BSR: {bsr} > 150000")
        if rating < 3.5 and rating > 0:
            reasons.append(f"Low Rating: {rating} < 3.5")
        if review_count < 30 and review_count > 0:
            reasons.append(f"Low Review Count: {review_count} < 30")
        if reasons:
            output["verdict"] = "REJECT"
            output["reasons"] = reasons
            log.info(f"ASIN {asin} REJECTED in triage: {', '.join(reasons)}")
        else:
            output["verdict"] = "CANDIDATE"
            output["reasons"] = ["Passed triage checks"]
            log.info(f"ASIN {asin} PASSED triage")
    except AsyncPlaywrightTimeoutError:
        log.warning(f"Timeout during triage for ASIN {asin}")
        output["reasons"] = ["Timeout during triage page interaction"]
    except Exception as e:
        log.error(f"Error during triage for ASIN {asin}: {e}", exc_info=True)
        output["reasons"] = [f"General Error in Triage: {str(e)}"]
    finally:
        if page_internal and not page_internal.is_closed():
            await page_internal.close()
            log.info("Triage: Closed internally created page.")
        if browser_conn_internal and browser_conn_internal.is_connected():
            await browser_conn_internal.close()
            log.info("Triage: Closed internal browser connection.")
        if playwright:
            await playwright.stop()
            log.info("Triage: Playwright instance stopped.")
    try:
        output_filename = os.path.join(TRIAGE_OUTPUT_DIR, f"triage_{asin}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        log.info(f"Triage result for {asin} saved to {output_filename}")
    except Exception as e_save:
        log.error(f"Failed to save triage result for {asin}: {e_save}")
    return output

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python zero_token_triage_module.py <ASIN> <landed_cost>")
        sys.exit(1)
    asin = sys.argv[1]
    try:
        landed_cost = float(sys.argv[2])
    except ValueError:
        print("Invalid landed_cost. Please enter a valid number.")
        sys.exit(1)
    asyncio.run(perform_zero_token_triage(asin, landed_cost))
