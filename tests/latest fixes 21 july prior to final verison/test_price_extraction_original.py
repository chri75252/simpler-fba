#!/usr/bin/env python3
"""
Test script for Amazon price extraction WITHOUT new selector
Tests why the original selectors fail on variation pages
"""

import asyncio
import logging
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Add project directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'tools'))

from playwright.async_api import async_playwright, Browser, Page
from tools.amazon_playwright_extractor import AmazonExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

class OriginalTestExtractor(AmazonExtractor):
    """Test version using ONLY original selectors - NO new selector"""
    
    async def _extract_price(self, page: Page, data: Dict[str, Any], get_html_content_func) -> None:
        log.info("🧪 ORIGINAL PRICE EXTRACTION - No enhanced selectors")
        try:
            # ORIGINAL SELECTORS ONLY - Exactly as in current system
            price_selectors = [
                # Primary Buy Box Price (original selectors)
                "#corePrice_feature_div .a-offscreen", 
                "span.priceToPay .a-offscreen", 
                ".a-price[data-a-size='xl'] .a-offscreen", 
                ".a-price[data-a-size='core'] .a-offscreen", 
                "#price_inside_buybox",
                "div#apex_desktop_usedAccordionRow .a-color-price",
                "div#corePriceDisplay_desktop_feature_div span.a-price.a-text-price span.a-offscreen",
                "div#corePrice_feature_div span.a-price span.a-offscreen",
                "div#centerCol #priceblock_ourprice",
                "div#centerCol #priceblock_dealprice",
                "div#centerCol #priceblock_saleprice",
                "div#centerCol span.apexPriceToPay span.a-offscreen",
                "#priceblock_ourprice", 
                "#priceblock_dealprice", 
                ".offer-price", 
                "#price", 
                "span.apexPriceToPay .a-offscreen", 
                ".priceToPay .a-price .a-offscreen", 
                "span#priceblock_saleprice",
                "span#subscriptionPrice",
                "span.reinventPricePriceToPayMargin.a-size-base span.a-offscreen"
            ]
            
            price_found = False
            log.info(f"🔍 Testing {len(price_selectors)} ORIGINAL selectors...")
            
            for i, selector in enumerate(price_selectors, 1):
                try:
                    log.info(f"🔍 Testing selector {i}/{len(price_selectors)}: {selector}")
                    price_elem = await page.query_selector(selector)
                    
                    if price_elem:
                        price_text = await price_elem.text_content()
                        log.info(f"✅ FOUND ELEMENT: '{price_text}' via {selector}")
                        
                        if price_text:
                            parsed_price = self._parse_price(price_text)
                            log.info(f"🔢 PARSED PRICE: {parsed_price} from '{price_text}'")
                            
                            if parsed_price > 0:
                                data["current_price"] = parsed_price
                                data["price_selector_used"] = selector
                                data["price_selector_index"] = i
                                log.info(f"✅ SUCCESS: Price £{parsed_price} via selector #{i}: {selector}")
                                price_found = True
                                break
                            else:
                                log.warning(f"⚠️ ZERO PRICE: Parsed to {parsed_price} from '{price_text}'")
                        else:
                            log.warning(f"⚠️ EMPTY TEXT: Element found but no text content")
                    else:
                        log.debug(f"❌ NO MATCH: {selector}")
                        
                except Exception as e:
                    log.error(f"❌ SELECTOR ERROR: {selector} - {e}")
                    continue
            
            if not price_found:
                log.error("❌ NO PRICE FOUND: All ORIGINAL selectors failed")
                data["price_extraction_status"] = "failed_original_selectors"
                
                # Additional debugging - check what elements ARE available
                log.info("🔍 DEBUGGING: Looking for ANY price-related elements...")
                debug_selectors = [
                    ".a-price",
                    "span[class*='price']",
                    "*[class*='Price']",
                    "span.a-price.aok-align-center.reinventPricePriceToPayMargin.priceToPay"  # The working selector
                ]
                
                for debug_sel in debug_selectors:
                    try:
                        debug_elems = await page.query_selector_all(debug_sel)
                        if debug_elems:
                            log.info(f"🔍 FOUND {len(debug_elems)} elements for: {debug_sel}")
                            for j, elem in enumerate(debug_elems[:3]):  # Show first 3
                                try:
                                    text = await elem.text_content()
                                    classes = await elem.get_attribute("class")
                                    log.info(f"   Element {j+1}: text='{text}' class='{classes}'")
                                except:
                                    pass
                    except Exception as e:
                        log.error(f"Debug selector error: {e}")
                        
            else:
                data["price_extraction_status"] = "success_original_selectors"
                
        except Exception as e:
            log.error(f"❌ PRICE EXTRACTION ERROR: {e}")
            data["price_extraction_error"] = str(e)

async def test_original_selectors(asin: str) -> Dict[str, Any]:
    """Test ORIGINAL selectors only for a specific ASIN"""
    log.info(f"\n🧪 TESTING ORIGINAL SELECTORS ONLY: {asin}")
    
    async with async_playwright() as p:
        # Connect to existing Chrome instance
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            log.info("✅ Connected to Chrome via CDP")
        except Exception as e:
            log.error(f"❌ Failed to connect to Chrome: {e}")
            return {"error": "Browser connection failed"}
        
        try:
            # Create test extractor with ORIGINAL selectors only
            extractor = OriginalTestExtractor(chrome_debug_port=9222)
            extractor.browser = browser
            
            # Extract data
            result = await extractor.extract_data(asin)
            
            log.info(f"📊 ORIGINAL EXTRACTION RESULT for {asin}:")
            log.info(f"   Title: {result.get('title', 'N/A')}")
            log.info(f"   Price: £{result.get('current_price', 'N/A')}")
            log.info(f"   Status: {result.get('price_extraction_status', 'unknown')}")
            log.info(f"   Selector: {result.get('price_selector_used', 'none')}")
            
            return result
            
        except Exception as e:
            log.error(f"❌ Extraction failed for {asin}: {e}")
            return {"error": str(e), "asin": asin}
        finally:
            try:
                await browser.close()
            except:
                pass

async def main():
    """Test original selectors to understand why they fail"""
    # Test the same ASINs that failed with original selectors
    test_asins = [
        "B0C6FM877Z",  # Valentte Reed Diffuser - NEW selector worked 
        "B0BSFN7BK9",  # SOL Air Freshener - NEW selector worked
    ]
    
    results = []
    
    log.info("🧪 TESTING WHY ORIGINAL SELECTORS FAIL")
    log.info("=" * 60)
    
    for asin in test_asins:
        try:
            result = await test_original_selectors(asin)
            results.append(result)
            
            # Add delay between tests
            await asyncio.sleep(2)
            
        except Exception as e:
            log.error(f"❌ Failed to test {asin}: {e}")
            results.append({"asin": asin, "error": str(e)})
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"test_original_selectors_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    log.info(f"\n📊 ORIGINAL SELECTORS TEST SUMMARY:")
    log.info(f"Tested {len(test_asins)} ASINs with ORIGINAL selectors")
    log.info(f"Results saved to: {results_file}")
    
    successful_extractions = sum(1 for r in results if r.get('current_price'))
    failed_extractions = len(test_asins) - successful_extractions
    
    log.info(f"Successful extractions: {successful_extractions}/{len(test_asins)}")
    log.info(f"Failed extractions: {failed_extractions}/{len(test_asins)}")
    
    for result in results:
        asin = result.get('asin', result.get('asin_queried', 'Unknown'))
        price = result.get('current_price')
        status = "✅ SUCCESS" if price else "❌ FAILED"
        log.info(f"  {asin}: {status} - £{price if price else 'N/A'}")
    
    if failed_extractions > 0:
        log.info("\n🔍 CONCLUSION: Original selectors FAIL on these variation pages")
        log.info("✅ SOLUTION: The new selector is needed for variation pages")
    else:
        log.info("\n⚠️ UNEXPECTED: Original selectors worked - investigate further")

if __name__ == "__main__":
    asyncio.run(main())