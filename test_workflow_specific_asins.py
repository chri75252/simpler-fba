#!/usr/bin/env python3
"""
Test script to run the actual system workflow on specific ASINs
This simulates the exact workflow conditions without editing main scripts
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

# Configure logging to match system
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

class WorkflowASINTester:
    """Test specific ASINs using the actual system workflow components"""
    
    def __init__(self):
        self.setup_paths()
        self.load_system_config()
        
    def setup_paths(self):
        """Setup paths exactly as the main workflow does"""
        self.project_root = current_dir
        self.output_root = os.path.join(self.project_root, "OUTPUTS")
        self.amazon_cache_dir = os.path.join(self.output_root, "FBA_ANALYSIS", "amazon_cache")
        
        # Ensure directories exist
        os.makedirs(self.amazon_cache_dir, exist_ok=True)
        
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
    
    async def simulate_workflow_amazon_extraction(self, asin: str, supplier_ean: str = None) -> Dict[str, Any]:
        """
        Simulate exactly how the main workflow calls Amazon extraction
        This replicates the _get_amazon_data method behavior
        """
        log.info(f"\n🔄 SIMULATING WORKFLOW AMAZON EXTRACTION: {asin}")
        
        try:
            # Import exactly as the main workflow does
            from utils.browser_manager import BrowserManager
            from tools.amazon_playwright_extractor import AmazonExtractor
            
            # Initialize browser manager exactly as workflow does (singleton pattern)
            browser_manager = BrowserManager()
            
            # Initialize Amazon extractor exactly as workflow does
            extractor = AmazonExtractor(
                chrome_debug_port=self.system_config.get("chrome", {}).get("debug_port", 9222),
                browser_manager=browser_manager
            )
            
            log.info("🔧 Initialized components exactly as main workflow")
            
            # Check for existing cache exactly as workflow does
            cache_file_patterns = [
                f"amazon_{asin}_{supplier_ean}.json" if supplier_ean else None,
                f"amazon_{asin}_*.json"
            ]
            
            cached_data = None
            for pattern in cache_file_patterns:
                if pattern:
                    cache_file_path = os.path.join(self.amazon_cache_dir, pattern)
                    if '*' in pattern:
                        # Use glob to find matching files
                        import glob
                        matching_files = glob.glob(cache_file_path)
                        if matching_files:
                            cache_file_path = matching_files[0]
                            pattern = os.path.basename(cache_file_path)
                    
                    if os.path.exists(cache_file_path):
                        try:
                            with open(cache_file_path, 'r') as f:
                                cached_data = json.load(f)
                            log.info(f"📋 Found existing cache: {pattern}")
                            break
                        except Exception as e:
                            log.warning(f"⚠️ Cache file corrupted: {e}")
            
            if cached_data:
                log.info("♻️ Using cached data (as workflow would)")
                result = cached_data.copy()
                result["workflow_test_source"] = "cache"
                result["test_timestamp"] = datetime.now().isoformat()
                return result
            
            # Extract fresh data exactly as workflow does
            log.info("🔍 Extracting fresh Amazon data (as workflow would)")
            
            # Get page exactly as workflow browser manager does
            page = await browser_manager.get_page(f"https://www.amazon.co.uk/dp/{asin}")
            
            if not page:
                return {"error": "Failed to get page from browser manager", "asin": asin}
            
            # Extract data using the actual extractor with page provided
            result = await extractor.extract_data(asin, page=page)
            
            # Add workflow test metadata
            result["workflow_test_source"] = "fresh_extraction"
            result["test_timestamp"] = datetime.now().isoformat()
            result["supplier_ean_provided"] = supplier_ean
            
            # Save to cache exactly as workflow does
            cache_filename = f"amazon_{asin}_{supplier_ean or 'test'}.json"
            cache_file_path = os.path.join(self.amazon_cache_dir, cache_filename)
            
            try:
                with open(cache_file_path, 'w') as f:
                    json.dump(result, f, indent=2)
                log.info(f"💾 Saved to cache: {cache_filename}")
            except Exception as e:
                log.warning(f"⚠️ Failed to save cache: {e}")
            
            return result
            
        except Exception as e:
            log.error(f"❌ Workflow simulation failed for {asin}: {e}")
            return {"error": str(e), "asin": asin}
    
    def analyze_result(self, asin: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the extraction result for debugging"""
        analysis = {
            "asin": asin,
            "timestamp": datetime.now().isoformat(),
            "extraction_successful": "error" not in result,
            "has_title": bool(result.get("title")),
            "has_current_price": bool(result.get("current_price")),
            "has_price": bool(result.get("price")),
            "has_original_price": bool(result.get("original_price")),
            "price_fields": {},
            "data_source": result.get("workflow_test_source", "unknown")
        }
        
        # Check all price-related fields
        price_fields = ["current_price", "price", "original_price", "amazon_price"]
        for field in price_fields:
            if field in result:
                analysis["price_fields"][field] = result[field]
        
        # Check for extraction errors
        if "error" in result:
            analysis["error"] = result["error"]
        
        # Check cache vs fresh extraction
        if result.get("workflow_test_source") == "cache":
            analysis["cache_was_incomplete"] = not bool(result.get("current_price"))
        
        return analysis

async def test_workflow_asins():
    """Test specific problematic ASINs using workflow simulation"""
    
    # ASINs that showed null prices in the linking map
    test_cases = [
        {"asin": "B0C6FM877Z", "supplier_ean": "8696601070188", "description": "Valentte Reed Diffuser"},
        {"asin": "B0BSFN7BK9", "supplier_ean": "5053249278674", "description": "SOL Air Freshener"},
        {"asin": "B07H9Q8K9D", "supplier_ean": None, "description": "Additional test ASIN"},
    ]
    
    tester = WorkflowASINTester()
    results = []
    
    log.info("🧪 TESTING WORKFLOW-SPECIFIC AMAZON EXTRACTION")
    log.info("=" * 70)
    
    for i, test_case in enumerate(test_cases, 1):
        asin = test_case["asin"]
        supplier_ean = test_case["supplier_ean"]
        description = test_case["description"]
        
        log.info(f"\n📋 Test {i}/{len(test_cases)}: {description}")
        log.info(f"   ASIN: {asin}")
        log.info(f"   Supplier EAN: {supplier_ean or 'None'}")
        
        try:
            # Run workflow simulation
            result = await tester.simulate_workflow_amazon_extraction(asin, supplier_ean)
            
            # Analyze result
            analysis = tester.analyze_result(asin, result)
            
            # Store combined result
            combined_result = {
                "test_case": test_case,
                "extraction_result": result,
                "analysis": analysis
            }
            results.append(combined_result)
            
            # Log summary
            status = "✅ SUCCESS" if analysis["has_current_price"] else "❌ NO PRICE"
            price = result.get("current_price", "N/A")
            source = analysis["data_source"]
            
            log.info(f"   Result: {status} - £{price} (from {source})")
            
            if not analysis["has_current_price"] and analysis["extraction_successful"]:
                log.warning(f"   ⚠️ Extraction succeeded but no price found!")
                log.warning(f"   Available fields: {list(result.keys())}")
                
        except Exception as e:
            log.error(f"   ❌ Test failed: {e}")
            results.append({
                "test_case": test_case,
                "extraction_result": {"error": str(e)},
                "analysis": {"error": str(e)}
            })
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"workflow_asin_test_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Generate summary report
    log.info(f"\n📊 WORKFLOW TEST SUMMARY")
    log.info(f"Tested {len(test_cases)} ASINs using workflow simulation")
    log.info(f"Detailed results saved to: {results_file}")
    
    successful_extractions = sum(1 for r in results if r["analysis"].get("has_current_price"))
    failed_extractions = len(test_cases) - successful_extractions
    
    log.info(f"Successful price extractions: {successful_extractions}/{len(test_cases)}")
    log.info(f"Failed price extractions: {failed_extractions}/{len(test_cases)}")
    
    # Detailed analysis
    for result in results:
        test_case = result["test_case"]
        analysis = result["analysis"]
        
        asin = test_case["asin"]
        status = "✅" if analysis.get("has_current_price") else "❌"
        price = result["extraction_result"].get("current_price", "N/A")
        source = analysis.get("data_source", "unknown")
        
        log.info(f"  {asin}: {status} £{price} (from {source})")
        
        if not analysis.get("has_current_price") and analysis.get("extraction_successful"):
            log.info(f"    🔍 Debugging: {analysis.get('data_source')} extraction succeeded but no price")
    
    # Compare with standalone test results
    log.info(f"\n🔍 COMPARISON WITH STANDALONE TESTS:")
    log.info(f"Standalone tests: Both ASINs extracted prices successfully")
    log.info(f"Workflow tests: {successful_extractions}/{len(test_cases)} successful")
    
    if failed_extractions > 0:
        log.info(f"🎯 CONCLUSION: Workflow environment causes price extraction failures")
        log.info(f"   The issue is in the workflow context, not the extraction script")
    else:
        log.info(f"✅ CONCLUSION: Workflow extraction works - investigate timing/state issues")

if __name__ == "__main__":
    asyncio.run(test_workflow_asins())