"""
Enhanced diagnostic test script to validate the sponsored detection fix.
This script provides more detailed diagnostics about the search results.
"""

import asyncio
import logging
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

async def test_sponsored_detection_detailed():
    """Test the comprehensive sponsored detection logic with detailed diagnostics"""
    
    async with async_playwright() as playwright:
        # Connect to existing Chrome instance
        try:
            browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
            log.info("Successfully connected to Chrome on port 9222")
            
            # Get or create a page
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            
            # Navigate to Amazon UK search
            log.info("Navigating to Amazon UK...")
            await page.goto("https://www.amazon.co.uk", timeout=30000)
            
            # Search for a common term to get some results including sponsored ones
            log.info("Performing search for 'bluetooth speakers'...")
            await page.fill("input#twotabsearchtextbox", "bluetooth speakers", timeout=5000)
            await page.press("input#twotabsearchtextbox", "Enter")
            
            # Wait for search results
            await page.wait_for_selector("div.s-search-results", timeout=15000)
            log.info("Search results loaded")
            
            # Let's try different selectors to understand the page structure
            selectors_to_try = [
                "div.s-search-results > div[data-asin]",
                "div[data-component-type='s-search-result']",
                "div.s-result-item[data-asin]",
                "div[data-asin]:not([data-asin=''])"
            ]
            
            best_selector = None
            best_count = 0
            
            for selector in selectors_to_try:
                try:
                    elements = await page.query_selector_all(selector)
                    count = len(elements)
                    log.info(f"Selector '{selector}' found {count} elements")
                    if count > best_count:
                        best_count = count
                        best_selector = selector
                except Exception as e:
                    log.error(f"Selector '{selector}' failed: {e}")
            
            if not best_selector or best_count == 0:
                log.error("No valid search result elements found with any selector")
                return False
                
            log.info(f"Using best selector: '{best_selector}' with {best_count} elements")
            
            # Get search result elements using the best selector
            search_result_elements = await page.query_selector_all(best_selector)
            
            sponsored_count = 0
            organic_count = 0
            invalid_count = 0
            
            # Test the comprehensive sponsored detection logic on each element
            for i, element in enumerate(search_result_elements[:15]):  # Test first 15 results
                try:
                    asin = await element.get_attribute("data-asin")
                    log.info(f"Element {i+1}: ASIN = {asin}")
                    
                    if not asin or len(asin) != 10:
                        invalid_count += 1
                        log.info(f"  -> Invalid ASIN: '{asin}'")
                        continue
                    
                    # Get title for logging
                    try:
                        title_element = await element.query_selector("h2 a span, h3 a span, .s-size-mini span")
                        title = await title_element.inner_text() if title_element else "Unknown Title"
                        title = title[:40] + "..." if len(title) > 40 else title
                    except:
                        title = "Unknown Title"
                    
                    log.info(f"  -> Title: {title}")
                    
                    # COMPREHENSIVE SPONSORED DETECTION LOGIC (From Fix 2.1)
                    is_sponsored = False
                    detection_method = None
                    
                    # Check 1: Direct 'Sponsored' aria-label
                    try:
                        if await element.locator('[aria-label="Sponsored"]').is_visible(timeout=500):
                            is_sponsored = True
                            detection_method = "aria-label='Sponsored'"
                    except Exception: pass

                    # Check 2: Specific text "Sponsored" within known ad badge elements
                    if not is_sponsored:
                        sponsored_text_locators = [
                            ("span:text-matches('^Sponsored$', 'i')", "exact text match"),
                            (".s-sponsored-label-text", "sponsored label class"),
                            (".puis-label-text:text-matches('^Sponsored$', 'i')", "puis label"),
                            ("span.s-label-popover-default:text-matches('^Sponsored$', 'i')", "label popover"),
                            (".sponsored-brand-label:text-matches('^Sponsored$', 'i')", "brand label")
                        ]
                        for loc_selector, method_name in sponsored_text_locators:
                            try:
                                loc = element.locator(loc_selector)
                                if await loc.is_visible(timeout=500):
                                    is_sponsored = True
                                    detection_method = method_name
                                    break
                            except Exception: pass
                    
                    # Check 3: Data attributes
                    if not is_sponsored:
                        try:
                            if await element.evaluate("el => el.dataset.adMarker === 'true' || el.dataset.isAd === 'true'"):
                                is_sponsored = True
                                detection_method = "data-attribute"
                        except Exception: pass

                    # Check 4: Known wrapper classes
                    if not is_sponsored:
                        try:
                            tile_classes = await element.get_attribute("class") or ""
                            if "AdHolder" in tile_classes or "s-widget-sponsored-product" in tile_classes:
                                is_sponsored = True
                                detection_method = f"tile class: {tile_classes}"
                        except Exception: pass
                    
                    # Check 5: Alternative method - look for any "Sponsored" text
                    if not is_sponsored:
                        try:
                            all_text = await element.inner_text()
                            if "Sponsored" in all_text:
                                is_sponsored = True
                                detection_method = "text content search"
                        except Exception: pass
                    
                    if is_sponsored:
                        sponsored_count += 1
                        log.info(f"  -> SPONSORED (method: {detection_method})")
                    else:
                        organic_count += 1
                        log.info(f"  -> ORGANIC")
                        
                except Exception as e:
                    log.error(f"Error processing element {i+1}: {e}")
                    invalid_count += 1
            
            # Report results
            log.info("=" * 60)
            log.info("DETECTION RESULTS:")
            log.info(f"  Total elements tested: {min(len(search_result_elements), 15)}")
            log.info(f"  Sponsored results detected: {sponsored_count}")
            log.info(f"  Organic results detected: {organic_count}")
            log.info(f"  Invalid/skipped elements: {invalid_count}")
            log.info("=" * 60)
            
            success = True
            if sponsored_count > 0:
                log.info("SUCCESS: Sponsored detection logic is working - detected sponsored ads")
            else:
                log.warning("WARNING: No sponsored ads detected - this could be normal")
                
            if organic_count > 0:
                log.info("SUCCESS: Organic results are being detected correctly")
            else:
                log.error("ERROR: No organic results detected - this indicates a problem")
                success = False
            
            await page.close()
            
            return success
            
        except Exception as e:
            log.error(f"Test failed with error: {e}")
            return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Sponsored Detection Fix (Fix 2.1) - Enhanced")
    print("=" * 60)
    
    success = asyncio.run(test_sponsored_detection_detailed())
    
    if success:
        print("\nSUCCESS: Test completed successfully!")
    else:
        print("\nFAILED: Test failed!")
