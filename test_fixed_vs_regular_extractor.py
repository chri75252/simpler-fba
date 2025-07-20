#!/usr/bin/env python3
"""
Test FixedAmazonExtractor vs regular AmazonExtractor to identify differences
This will show why newly extracted products in workflow still have null prices
"""

import asyncio
import logging
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any

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

class ExtractorComparison:
    """Compare FixedAmazonExtractor vs regular AmazonExtractor"""
    
    def __init__(self):
        self.setup_paths()
        self.load_system_config()
        
    def setup_paths(self):
        """Setup paths exactly as the main workflow does"""
        self.project_root = current_dir
        
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
    
    async def test_regular_amazon_extractor(self, asin: str, ean: str) -> Dict[str, Any]:
        """Test regular AmazonExtractor (as used in standalone tests)"""
        log.info(f"\n🔧 TESTING REGULAR AMAZON EXTRACTOR: {asin}")
        
        try:
            from utils.browser_manager import BrowserManager
            from tools.amazon_playwright_extractor import AmazonExtractor
            
            # Initialize exactly as standalone tests do
            browser_manager = BrowserManager()
            chrome_debug_port = self.system_config.get("chrome", {}).get("debug_port", 9222)
            await browser_manager.launch_browser(chrome_debug_port, headless=False)
            
            extractor = AmazonExtractor(
                chrome_debug_port=chrome_debug_port,
                browser_manager=browser_manager
            )
            
            # Get page and extract data exactly as standalone tests
            page = await browser_manager.get_page(f"https://www.amazon.co.uk/dp/{asin}")
            result = await extractor.extract_data(asin, page=page)
            
            # Add test metadata
            result["test_source"] = "regular_extractor"
            result["test_timestamp"] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            log.error(f"❌ Regular extractor failed for {asin}: {e}")
            return {"error": str(e), "asin": asin, "test_source": "regular_extractor"}
    
    async def test_fixed_amazon_extractor(self, asin: str, ean: str, product_title: str) -> Dict[str, Any]:
        """Test FixedAmazonExtractor (as used in workflow)"""
        log.info(f"\n🔧 TESTING FIXED AMAZON EXTRACTOR: {asin}")
        
        try:
            # Import FixedAmazonExtractor from workflow
            from tools.passive_extraction_workflow_latest import FixedAmazonExtractor
            
            # Initialize exactly as workflow does
            chrome_debug_port = self.system_config.get("chrome", {}).get("debug_port", 9222)
            extractor = FixedAmazonExtractor(chrome_debug_port=chrome_debug_port)
            
            # Connect to browser
            await extractor.connect()
            
            # Extract data using EAN search as workflow does
            result = await extractor.search_by_ean_and_extract_data(ean, product_title)
            
            # Add test metadata
            result["test_source"] = "fixed_extractor"
            result["test_timestamp"] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            log.error(f"❌ Fixed extractor failed for {asin}: {e}")
            return {"error": str(e), "asin": asin, "test_source": "fixed_extractor"}
    
    def analyze_extraction_comparison(self, asin: str, regular_result: Dict[str, Any], fixed_result: Dict[str, Any]) -> Dict[str, Any]:
        """Compare the two extraction results"""
        analysis = {
            "asin": asin,
            "timestamp": datetime.now().isoformat(),
            "regular_extractor": {
                "success": "error" not in regular_result,
                "has_price": bool(regular_result.get("current_price")),
                "price_value": regular_result.get("current_price"),
                "total_fields": len(regular_result.keys()),
                "all_price_fields": {}
            },
            "fixed_extractor": {
                "success": "error" not in fixed_result,
                "has_price": bool(fixed_result.get("current_price")),
                "price_value": fixed_result.get("current_price"),
                "total_fields": len(fixed_result.keys()),
                "all_price_fields": {}
            }
        }
        
        # Collect price fields from both
        price_fields = ["current_price", "price", "original_price", "amazon_price"]
        for field in price_fields:
            if field in regular_result:
                analysis["regular_extractor"]["all_price_fields"][field] = regular_result[field]
            if field in fixed_result:
                analysis["fixed_extractor"]["all_price_fields"][field] = fixed_result[field]
        
        # Add errors if any
        if "error" in regular_result:
            analysis["regular_extractor"]["error"] = regular_result["error"]
        if "error" in fixed_result:
            analysis["fixed_extractor"]["error"] = fixed_result["error"]
        
        return analysis

async def test_extractor_comparison():
    """Compare FixedAmazonExtractor vs regular AmazonExtractor"""
    
    # Test cases that showed null prices in workflow
    test_cases = [
        {
            "asin": "B0C6FM877Z", 
            "ean": "8696601070188", 
            "title": "Valentte Reed Diffuser - White Neroli & Lemon Scent | Essential Oil Aroma for Home | 100 ml",
            "description": "Valentte Reed Diffuser"
        },
        {
            "asin": "B0BSFN7BK9", 
            "ean": "5053249278674", 
            "title": "SOL 12pk Gel Air Fresheners - Pacific Surf & Fresh Berries Scents, Odour Eliminator Room Fresheners, Bathroom Air Fresheners, Toilet Deodorisers, Long-Lasting Room Fragrance for Home & Office",
            "description": "SOL Air Freshener"
        }
    ]
    
    tester = ExtractorComparison()
    results = []
    
    log.info("🧪 TESTING FIXED vs REGULAR AMAZON EXTRACTOR")
    log.info("This will show if FixedAmazonExtractor returns incomplete data")
    log.info("=" * 70)
    
    for i, test_case in enumerate(test_cases, 1):
        asin = test_case["asin"]
        ean = test_case["ean"]
        title = test_case["title"]
        description = test_case["description"]
        
        log.info(f"\n📋 Test {i}/{len(test_cases)}: {description}")
        log.info(f"   ASIN: {asin}")
        log.info(f"   EAN: {ean}")
        
        try:
            # Test regular extractor (as used in standalone tests)
            regular_result = await tester.test_regular_amazon_extractor(asin, ean)
            
            # Test fixed extractor (as used in workflow) 
            fixed_result = await tester.test_fixed_amazon_extractor(asin, ean, title)
            
            # Analyze comparison
            analysis = tester.analyze_extraction_comparison(asin, regular_result, fixed_result)
            
            # Store results
            test_result = {
                "test_case": test_case,
                "regular_extractor_result": regular_result,
                "fixed_extractor_result": fixed_result,
                "comparison_analysis": analysis
            }
            results.append(test_result)
            
            # Log comparison
            regular_price = regular_result.get("current_price")
            fixed_price = fixed_result.get("current_price")
            
            log.info(f"   📊 COMPARISON:")
            log.info(f"      Regular extractor: £{regular_price or 'N/A'}")
            log.info(f"      Fixed extractor: £{fixed_price or 'N/A'}")
            
            if regular_price and not fixed_price:
                log.warning(f"   🚨 WORKFLOW ISSUE: Regular extractor has price, Fixed extractor missing price!")
            elif not regular_price and fixed_price:
                log.info(f"   ⚠️ UNEXPECTED: Fixed extractor has price, Regular extractor missing price")
            elif regular_price and fixed_price:
                log.info(f"   ✅ Both extractors have price data")
            else:
                log.warning(f"   ❌ Both extractors failed to get price")
            
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
    results_file = f"extractor_comparison_test_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Generate final analysis
    log.info(f"\n📊 EXTRACTOR COMPARISON SUMMARY")
    log.info(f"Results saved to: {results_file}")
    
    workflow_issues = 0
    for result in results:
        if "error" not in result:
            analysis = result["comparison_analysis"]
            regular_has_price = analysis["regular_extractor"]["has_price"]
            fixed_has_price = analysis["fixed_extractor"]["has_price"]
            asin = analysis["asin"]
            
            if regular_has_price and not fixed_has_price:
                workflow_issues += 1
                log.info(f"  🚨 {asin}: WORKFLOW ISSUE - Regular extractor works, Fixed extractor fails")
            elif regular_has_price and fixed_has_price:
                log.info(f"  ✅ {asin}: Both extractors work")
            elif not regular_has_price and not fixed_has_price:
                log.info(f"  ❌ {asin}: Both extractors fail")
            else:
                log.info(f"  ⚠️ {asin}: Unexpected result pattern")
    
    # Final conclusion
    if workflow_issues > 0:
        log.info(f"\n🎯 CONCLUSION: FIXEDAMAZONEXTRACTOR IS THE PROBLEM!")
        log.info(f"   {workflow_issues} ASINs work with regular extractor but fail with workflow's FixedAmazonExtractor")
        log.info(f"   The workflow uses FixedAmazonExtractor which has different behavior")
        log.info(f"   Solution: Fix FixedAmazonExtractor or use regular AmazonExtractor in workflow")
    else:
        log.info(f"\n⚠️ INCONCLUSIVE: Both extractors behave similarly - investigate further")

if __name__ == "__main__":
    asyncio.run(test_extractor_comparison())