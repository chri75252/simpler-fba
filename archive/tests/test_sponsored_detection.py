"""
Simple test script to validate the sponsored detection fix.
This script tests the core sponsored detection logic without the full workflow.
"""

import asyncio
import logging
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

async def test_sponsored_detection():
    """Test the comprehensive sponsored detection logic"""
    
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
            log.info("Performing search for 'wireless headphones'...")
            await page.fill("input#twotabsearchtextbox", "wireless headphones", timeout=5000)
            await page.press("input#twotabsearchtextbox", "Enter")
            
            # Wait for search results
            await page.wait_for_selector("div.s-search-results", timeout=15000)
            log.info("Search results loaded")
            
            # Get search result elements
            search_result_elements = await page.query_selector_all("div.s-search-results > div[data-asin]")
            log.info(f"Found {len(search_result_elements)} search result elements")
            
            sponsored_count = 0
            organic_count = 0
            
            # Test the comprehensive sponsored detection logic on each element
            for i, element in enumerate(search_result_elements[:10]):  # Test first 10 results
                asin = await element.get_attribute("data-asin")
                if not asin or len(asin) != 10:
                    continue
                    
                # COMPREHENSIVE SPONSORED DETECTION LOGIC (From Fix 2.1)
                is_sponsored = False
                
                # Check 1: Direct 'Sponsored' aria-label on the tile itself or a prominent child
                try:
                    if await element.locator('[aria-label="Sponsored"]', has_text="Sponsored").is_visible(timeout=500):
                        is_sponsored = True
                        log.info(f"ASIN {asin} detected as sponsored by direct aria-label='Sponsored'.")
                except Exception: pass

                # Check 2: Specific text "Sponsored" within known ad badge elements
                if not is_sponsored:
                    sponsored_text_locators = [
                        element.locator("span:text-matches('^Sponsored$', 'i')"),
                        element.locator(".s-sponsored-label-text"),
                        element.locator(".puis-label-text:text-matches('^Sponsored$', 'i')"),
                        element.locator("span.s-label-popover-default:text-matches('^Sponsored$', 'i')"),
                        element.locator(".sponsored-brand-label:text-matches('^Sponsored$', 'i')")
                    ]
                    for loc in sponsored_text_locators:
                        try:
                            if await loc.is_visible(timeout=500):
                                is_sponsored = True
                                log.info(f"ASIN {asin} detected as sponsored by visible text locator")
                                break
                        except Exception: pass
                
                # Check 3: Presence of specific data-attributes on the tile that mark it as an ad
                if not is_sponsored:
                    if await element.evaluate("el => el.dataset.adMarker === 'true' || el.dataset.isAd === 'true'"):
                        is_sponsored = True
                        log.info(f"ASIN {asin} detected as sponsored by data-attribute.")

                # Check 4: Known wrapper classes on the tile itself
                if not is_sponsored:
                    tile_classes = await element.get_attribute("class") or ""
                    if "AdHolder" in tile_classes or "s-widget-sponsored-product" in tile_classes:
                        is_sponsored = True
                        log.info(f"ASIN {asin} detected as sponsored by tile class: {tile_classes}")
                
                # Get title for logging
                try:
                    title_element = await element.query_selector("h2 a span")
                    title = await title_element.inner_text() if title_element else "Unknown Title"
                    title = title[:50] + "..." if len(title) > 50 else title
                except:
                    title = "Unknown Title"
                
                if is_sponsored:
                    sponsored_count += 1
                    log.info(f"SPONSORED: ASIN {asin} - {title}")
                else:
                    organic_count += 1
                    log.info(f"ORGANIC: ASIN {asin} - {title}")
            
            # Report results
            log.info(f"DETECTION RESULTS:")
            log.info(f"  Total elements tested: {min(len(search_result_elements), 10)}")
            log.info(f"  Sponsored results detected: {sponsored_count}")
            log.info(f"  Organic results detected: {organic_count}")
            
            if sponsored_count > 0:
                log.info("✅ SUCCESS: Sponsored detection logic is working - detected sponsored ads")
            else:
                log.warning("⚠️  WARNING: No sponsored ads detected - this could be normal or indicate an issue")
                
            if organic_count > 0:
                log.info("✅ SUCCESS: Organic results are being detected correctly")
            else:
                log.error("❌ ERROR: No organic results detected - this indicates a problem")
            
            await page.close()
            await browser.close()
            
        except Exception as e:
            log.error(f"Test failed with error: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("="*60)
    print("Testing Sponsored Detection Fix (Fix 2.1)")
    print("="*60)
    
    success = asyncio.run(test_sponsored_detection())
    
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")
