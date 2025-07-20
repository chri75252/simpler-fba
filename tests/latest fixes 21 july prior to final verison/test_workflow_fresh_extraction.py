#!/usr/bin/env python3
"""
Test workflow with forced fresh extraction (ignore cache)
This will prove if the issue is cached data vs fresh extraction
"""

import asyncio
import logging
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add project directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'tools'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Global browser manager instance
global_browser_manager = None

class FreshExtractionTester:
    """Test workflow with fresh extraction only (ignore cache)"""
    
    def __init__(self):
        self.setup_paths()
        self.load_system_config()
        
    def setup_paths(self):
        """Setup paths exactly as the main workflow does"""
        self.project_root = current_dir
        self.output_root = os.path.join(self.project_root, "OUTPUTS")
        self.amazon_cache_dir = os.path.join(self.output_root, "FBA_ANALYSIS", "amazon_cache")
        
    def load_system_config(self):
        """Load system config exactly as main workflow does"""
        config_path = os.path.join(self.project_root, "config", "system_config.json")
        try:
            with open(config_path, 'r') as f:
                self.system_config = json.load(f)
            log.info(f"✅ Loaded system config from {config_path}")
        except Exception as e:
            log.error(f"❌ Failed to load system config: {e}")
            self.system_config = {}
    
    async def get_persistent_browser_manager(self):
        """Get or create persistent browser manager"""
        global global_browser_manager
        
        if global_browser_manager is None:
            from utils.browser_manager import BrowserManager
            global_browser_manager = BrowserManager()
            
            # Launch browser with system config
            chrome_debug_port = self.system_config.get("chrome", {}).get("debug_port", 9222)
            await global_browser_manager.launch_browser(chrome_debug_port, headless=False)
            log.info("🔧 Created and launched persistent browser manager")
        else:
            log.info("♻️ Using existing persistent browser manager")
        
        return global_browser_manager
    
    async def force_fresh_extraction(self, asin: str, supplier_ean: str = None) -> Dict[str, Any]:
        """
        Force fresh extraction, completely ignoring any cached data
        This simulates what happens when cache is invalid/missing
        """
        log.info(f"\n🚀 FORCING FRESH EXTRACTION: {asin}")
        
        try:
            # Get persistent browser manager
            browser_manager = await self.get_persistent_browser_manager()
            
            # Import Amazon extractor
            from tools.amazon_playwright_extractor import AmazonExtractor
            
            # Initialize Amazon extractor with browser manager
            extractor = AmazonExtractor(
                chrome_debug_port=self.system_config.get("chrome", {}).get("debug_port", 9222),
                browser_manager=browser_manager
            )
            
            log.info("🔧 Initialized extractor with persistent browser manager")
            
            # Get page exactly as workflow does
            page = await browser_manager.get_page(f"https://www.amazon.co.uk/dp/{asin}")
            
            if not page:
                return {"error": "Failed to get page from browser manager", "asin": asin}
            
            log.info(f"📄 Got page for ASIN {asin}")
            
            # Force fresh extraction (ignore any cache)
            log.info("🔍 Extracting fresh Amazon data (CACHE IGNORED)")
            result = await extractor.extract_data(asin, page=page)
            
            # Add test metadata
            result["forced_fresh_extraction"] = True
            result["test_timestamp"] = datetime.now().isoformat()
            result["supplier_ean_provided"] = supplier_ean
            
            # Do NOT save to cache to avoid contaminating future tests
            log.info("💾 Skipping cache save (test mode)")
            
            return result
            
        except Exception as e:
            log.error(f"❌ Fresh extraction failed for {asin}: {e}")
            return {"error": str(e), "asin": asin}
    
    def analyze_fresh_result(self, asin: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze fresh extraction result"""
        analysis = {
            "asin": asin,
            "timestamp": datetime.now().isoformat(),
            "extraction_successful": "error" not in result,
            "has_title": bool(result.get("title")),
            "has_current_price": bool(result.get("current_price")),
            "price_value": result.get("current_price"),
            "all_price_fields": {},
            "total_fields_extracted": len(result.keys()),
            "test_type": "forced_fresh_extraction"
        }
        
        # Collect all price-related fields
        price_fields = ["current_price", "price", "original_price", "amazon_price"]
        for field in price_fields:
            if field in result:
                analysis["all_price_fields"][field] = result[field]
        
        # Check for extraction errors
        if "error" in result:
            analysis["error"] = result["error"]
        
        return analysis

async def test_fresh_vs_cache():
    """Test fresh extraction vs cached data to prove the issue"""
    
    # Test ASINs that are failing in workflow due to cache
    test_cases = [
        {"asin": "B0C6FM877Z", "supplier_ean": "8696601070188", "description": "Valentte Reed Diffuser"},
        {"asin": "B0BSFN7BK9", "supplier_ean": "5053249278674", "description": "SOL Air Freshener"},
    ]
    
    tester = FreshExtractionTester()
    results = []
    
    log.info("🧪 TESTING FRESH EXTRACTION VS CACHED DATA")
    log.info("This will prove if the issue is incomplete cached data")
    log.info("=" * 70)
    
    for i, test_case in enumerate(test_cases, 1):
        asin = test_case["asin"]
        supplier_ean = test_case["supplier_ean"]
        description = test_case["description"]
        
        log.info(f"\n📋 Test {i}/{len(test_cases)}: {description}")
        log.info(f"   ASIN: {asin}")
        log.info(f"   Supplier EAN: {supplier_ean or 'None'}")
        
        try:
            # Check what's in current cache
            cache_file = f"amazon_{asin}_{supplier_ean}.json"
            cache_path = os.path.join(tester.amazon_cache_dir, cache_file)
            
            cached_data = None
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r') as f:
                        cached_data = json.load(f)
                    log.info(f"📋 Current cache has fields: {list(cached_data.keys())}")
                    log.info(f"📋 Cache has price: {'current_price' in cached_data}")
                except Exception as e:
                    log.warning(f"⚠️ Cache read error: {e}")
            else:
                log.info("📋 No existing cache found")
            
            # Force fresh extraction
            fresh_result = await tester.force_fresh_extraction(asin, supplier_ean)
            
            # Analyze result
            analysis = tester.analyze_fresh_result(asin, fresh_result)
            
            # Store results
            test_result = {
                "test_case": test_case,
                "cached_data": cached_data,
                "fresh_extraction": fresh_result,
                "analysis": analysis
            }
            results.append(test_result)
            
            # Log comparison
            cache_price = cached_data.get("current_price") if cached_data else None
            fresh_price = fresh_result.get("current_price")
            
            log.info(f"   📊 COMPARISON:")
            log.info(f"      Cache price: £{cache_price or 'N/A'}")
            log.info(f"      Fresh price: £{fresh_price or 'N/A'}")
            
            if not cache_price and fresh_price:
                log.info(f"   🎯 CONFIRMED: Cache missing price, fresh extraction has price!")
            elif cache_price and fresh_price:
                log.info(f"   ✅ Both have price data")
            elif not fresh_price:
                log.info(f"   ❌ Fresh extraction also failed - different issue")
            
        except Exception as e:
            log.error(f"   ❌ Test failed: {e}")
            results.append({
                "test_case": test_case,
                "error": str(e)
            })
        
        # Small delay between tests
        await asyncio.sleep(2)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"fresh_vs_cache_test_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Generate final analysis
    log.info(f"\n📊 FRESH EXTRACTION TEST SUMMARY")
    log.info(f"Results saved to: {results_file}")
    
    cache_vs_fresh_analysis = []
    
    for result in results:
        if "error" not in result:
            test_case = result["test_case"]
            cached_data = result["cached_data"]
            fresh_result = result["fresh_extraction"]
            
            asin = test_case["asin"]
            cache_price = cached_data.get("current_price") if cached_data else None
            fresh_price = fresh_result.get("current_price")
            
            analysis_item = {
                "asin": asin,
                "cache_has_price": bool(cache_price),
                "fresh_has_price": bool(fresh_price),
                "cache_price": cache_price,
                "fresh_price": fresh_price
            }
            cache_vs_fresh_analysis.append(analysis_item)
            
            status = "🎯 CACHE ISSUE" if not cache_price and fresh_price else "✅ OK" if cache_price and fresh_price else "❌ EXTRACTION ISSUE"
            log.info(f"  {asin}: {status}")
            log.info(f"    Cache: £{cache_price or 'N/A'}")
            log.info(f"    Fresh: £{fresh_price or 'N/A'}")
    
    # Final conclusion
    cache_issues = sum(1 for item in cache_vs_fresh_analysis 
                      if not item["cache_has_price"] and item["fresh_has_price"])
    
    if cache_issues > 0:
        log.info(f"\n🎯 CONCLUSION: CACHE DATA IS THE PROBLEM!")
        log.info(f"   {cache_issues} ASINs have incomplete cache but valid fresh extraction")
        log.info(f"   The workflow uses cached data with missing price fields")
        log.info(f"   Solution: Fix cache validation or force refresh for incomplete cache")
    else:
        log.info(f"\n⚠️ INCONCLUSIVE: Need further investigation")

if __name__ == "__main__":
    asyncio.run(test_fresh_vs_cache())