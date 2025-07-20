#!/usr/bin/env python3
"""
Test script for Amazon price extraction with new selector
Tests specific ASINs that are failing to extract prices
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

class TestAmazonExtractor(AmazonExtractor):
    """Test version of Amazon extractor with enhanced price selectors"""
    
    async def _extract_price(self, page: Page, data: Dict[str, Any], get_html_content_func) -> None:
        log.info("🧪 TEST PRICE EXTRACTION - Enhanced selectors")
        try:
            # ENHANCED PRICE SELECTORS - New selector added at top
            price_selectors = [
                # 🆕 NEW SELECTOR - Added at top priority
                "span.a-price.aok-align-center.reinventPricePriceToPayMargin.priceToPay",
                "span.a-price.aok-align-center.reinventPricePriceToPayMargin.priceToPay .a-offscreen",
                
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
            log.info(f"🔍 Testing {len(price_selectors)} price selectors...")
            
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
                log.error("❌ NO PRICE FOUND: All selectors failed")
                data["price_extraction_status"] = "failed"
            else:
                data["price_extraction_status"] = "success"
                
        except Exception as e:
            log.error(f"❌ PRICE EXTRACTION ERROR: {e}")
            data["price_extraction_error"] = str(e)

async def test_asin_price_extraction(asin: str) -> Dict[str, Any]:
    """Test price extraction for a specific ASIN"""
    log.info(f"\n🧪 TESTING ASIN: {asin}")
    
    async with async_playwright() as p:
        # Connect to existing Chrome instance
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            log.info("✅ Connected to Chrome via CDP")
        except Exception as e:
            log.error(f"❌ Failed to connect to Chrome: {e}")
            return {"error": "Browser connection failed"}
        
        try:
            # Create test extractor
            extractor = TestAmazonExtractor(chrome_debug_port=9222)
            extractor.browser = browser
            
            # Extract data
            result = await extractor.extract_data(asin)
            
            log.info(f"📊 EXTRACTION RESULT for {asin}:")
            log.info(f"   Title: {result.get('title', 'N/A')}")
            log.info(f"   Price: £{result.get('current_price', 'N/A')}")
            log.info(f"   Status: {result.get('price_extraction_status', 'unknown')}")
            log.info(f"   Selector: {result.get('price_selector_used', 'none')}")
            log.info(f"   Selector Index: {result.get('price_selector_index', 'none')}")
            
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
    """Test multiple ASINs with enhanced price extraction"""
    # Test ASINs from the linking map with null prices
    test_asins = [
        "B0C6FM877Z",  # Valentte Reed Diffuser
        "B0BSFN7BK9",  # SOL Air Freshener
        "B07H9Q8K9D",  # Another test ASIN
    ]
    
    results = []
    
    for asin in test_asins:
        try:
            result = await test_asin_price_extraction(asin)
            results.append(result)
            
            # Add delay between tests
            await asyncio.sleep(2)
            
        except Exception as e:
            log.error(f"❌ Failed to test {asin}: {e}")
            results.append({"asin": asin, "error": str(e)})
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"test_price_extraction_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    log.info(f"\n📊 TEST SUMMARY:")
    log.info(f"Tested {len(test_asins)} ASINs")
    log.info(f"Results saved to: {results_file}")
    
    successful_extractions = sum(1 for r in results if r.get('current_price'))
    log.info(f"Successful price extractions: {successful_extractions}/{len(test_asins)}")
    
    for result in results:
        asin = result.get('asin', result.get('asin_queried', 'Unknown'))
        price = result.get('current_price')
        status = "✅ SUCCESS" if price else "❌ FAILED"
        log.info(f"  {asin}: {status} - £{price if price else 'N/A'}")

if __name__ == "__main__":
    asyncio.run(main())