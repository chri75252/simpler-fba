#!/usr/bin/env python3
"""
Acceptance Gate Test - Full System Validation
============================================

Validates all acceptance criteria for the delta-fix implementation:
1. .supplier_ready flag present  
2. Cache reports total_products ≥ 5
3. Linking-map folder contains ≥ 1 file with at least one matching_result
4. Category JSON exists and has ≥ 5 categories
5. logs/debug/login_*.ok found

USAGE:
    python tests/test_acceptance_gate.py --supplier-url "https://www.poundwholesale.co.uk/" --supplier-email "email" --supplier-password "pass" --headed
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class AcceptanceGateValidator:
    """Validate all acceptance gate criteria"""
    
    def __init__(self):
        self.test_results = {}
        self.validation_errors = []
        
    async def run_acceptance_gate_test(self, supplier_url: str, credentials: Dict[str, str], max_products: int = 15) -> Dict[str, Any]:
        """Run complete acceptance gate validation"""
        try:
            log.info("🚦 Starting Acceptance Gate Test")
            log.info(f"🎯 Target: {supplier_url} with max {max_products} products")
            
            # Step 1: Run the workflow to generate data
            await self._run_workflow_for_test_data(supplier_url, credentials, max_products)
            
            # Step 2: Validate all acceptance criteria
            await self._validate_acceptance_criteria(supplier_url)
            
            # Generate final report
            return self._generate_acceptance_report()
            
        except Exception as e:
            log.error(f"❌ Acceptance gate test failed: {e}")
            self.validation_errors.append(f"General test error: {str(e)}")
            return self._generate_acceptance_report()
    
    async def _run_workflow_for_test_data(self, supplier_url: str, credentials: Dict[str, str], max_products: int) -> None:
        """Run the LangGraph workflow to generate test data"""
        try:
            log.info("🏃 Running workflow to generate test data...")
            
            # Set required environment variables
            if not os.getenv("OPENAI_API_KEY"):
                log.error("❌ OPENAI_API_KEY environment variable is required")
                self.validation_errors.append("OPENAI_API_KEY missing")
                return
            
            from langraph_integration.complete_fba_workflow import CompleteFBAWorkflow
            
            workflow = CompleteFBAWorkflow()
            
            # Run workflow with supplier-first discovery mode
            result = await workflow.run_workflow(
                asin="SUPPLIER_DISCOVERY",
                supplier_url=supplier_url,
                supplier_credentials=credentials
            )
            
            workflow_success = result.get("status") in ["completed_successfully", "completed_with_warnings"]
            self.test_results["workflow_execution"] = workflow_success
            
            if workflow_success:
                log.info("✅ Workflow execution completed successfully")
            else:
                log.error(f"❌ Workflow execution failed: {result.get('status')}")
                self.validation_errors.append(f"Workflow failed: {result.get('error', 'Unknown error')}")
            
        except Exception as e:
            log.error(f"❌ Workflow execution failed: {e}")
            self.validation_errors.append(f"Workflow execution error: {str(e)}")
            self.test_results["workflow_execution"] = False
    
    async def _validate_acceptance_criteria(self, supplier_url: str) -> None:
        """Validate all 5 acceptance gate criteria"""
        try:
            from urllib.parse import urlparse
            
            # Extract supplier domain
            domain = urlparse(supplier_url).netloc.replace("www.", "").replace(".", "-")
            log.info(f"🔍 Validating criteria for domain: {domain}")
            
            # Criteria 1: .supplier_ready present
            self._validate_supplier_ready_flag(domain)
            
            # Criteria 2: Cache reports total_products ≥ 5
            self._validate_cache_products(domain)
            
            # Criteria 3: Linking-map folder contains ≥ 1 file with matching_result
            self._validate_linking_maps(domain)
            
            # Criteria 4: Category JSON exists and has ≥ 5 categories
            self._validate_category_json(domain)
            
            # Criteria 5: logs/debug/login_*.ok found
            self._validate_login_flag(domain)
            
        except Exception as e:
            log.error(f"❌ Acceptance criteria validation failed: {e}")
            self.validation_errors.append(f"Criteria validation error: {str(e)}")
    
    def _validate_supplier_ready_flag(self, domain: str) -> None:
        """Validate .supplier_ready flag is present"""
        try:
            log.info("🔍 Checking .supplier_ready flag...")
            
            ready_file = Path(f"suppliers/{domain}/.supplier_ready")
            ready_exists = ready_file.exists()
            
            self.test_results["supplier_ready_flag"] = ready_exists
            
            if ready_exists:
                # Check file content
                try:
                    ready_data = json.loads(ready_file.read_text())
                    log.info(f"✅ .supplier_ready flag found: {ready_data.get('created_at', 'No timestamp')}")
                except:
                    log.info("✅ .supplier_ready flag found (non-JSON format)")
            else:
                log.error(f"❌ .supplier_ready flag missing: {ready_file}")
                self.validation_errors.append(f"Missing .supplier_ready flag: {ready_file}")
                
        except Exception as e:
            log.error(f"❌ Supplier ready flag validation failed: {e}")
            self.validation_errors.append(f"Supplier ready flag error: {str(e)}")
            self.test_results["supplier_ready_flag"] = False
    
    def _validate_cache_products(self, domain: str) -> None:
        """Validate cache file has total_products ≥ 5"""
        try:
            log.info("🔍 Checking cache file product count...")
            
            cache_file = Path(f"OUTPUTS/cached_products/{domain}_products_cache.json")
            
            if not cache_file.exists():
                log.error(f"❌ Cache file missing: {cache_file}")
                self.validation_errors.append(f"Missing cache file: {cache_file}")
                self.test_results["cache_products"] = False
                return
            
            try:
                cache_data = json.loads(cache_file.read_text())
                total_products = cache_data.get("total_products", 0)
                
                cache_valid = total_products >= 5
                self.test_results["cache_products"] = cache_valid
                
                if cache_valid:
                    log.info(f"✅ Cache validation passed: {total_products} products (≥ 5 required)")
                else:
                    log.error(f"❌ Insufficient products in cache: {total_products} < 5 required")
                    self.validation_errors.append(f"Insufficient products: {total_products} < 5 in {cache_file}")
                    
            except Exception as e:
                log.error(f"❌ Failed to parse cache file: {e}")
                self.validation_errors.append(f"Invalid cache file format: {cache_file}")
                self.test_results["cache_products"] = False
                
        except Exception as e:
            log.error(f"❌ Cache products validation failed: {e}")
            self.validation_errors.append(f"Cache products error: {str(e)}")
            self.test_results["cache_products"] = False
    
    def _validate_linking_maps(self, domain: str) -> None:
        """Validate linking-map folder has ≥ 1 file with matching_result"""
        try:
            log.info("🔍 Checking linking map files...")
            
            linking_map_dir = Path(f"OUTPUTS/FBA_ANALYSIS/linking_maps/{domain}")
            
            if not linking_map_dir.exists():
                log.error(f"❌ Linking map directory missing: {linking_map_dir}")
                self.validation_errors.append(f"Missing linking map directory: {linking_map_dir}")
                self.test_results["linking_maps"] = False
                return
            
            # Find all JSON files in subdirectories
            linking_map_files = list(linking_map_dir.glob("**/*.json"))
            
            if not linking_map_files:
                log.error(f"❌ No linking map files found in: {linking_map_dir}")
                self.validation_errors.append(f"No linking map files in: {linking_map_dir}")
                self.test_results["linking_maps"] = False
                return
            
            # Check for valid matching_result in at least one file
            valid_maps = 0
            for map_file in linking_map_files:
                try:
                    with open(map_file, 'r') as f:
                        map_data = json.load(f)
                    
                    matching_result = map_data.get("matching_result", {})
                    if isinstance(matching_result, dict) and len(matching_result) >= 1:
                        valid_maps += 1
                        log.info(f"✅ Valid linking map found: {map_file.name}")
                    
                except Exception as e:
                    log.warning(f"⚠️ Failed to parse linking map {map_file}: {e}")
            
            maps_valid = valid_maps >= 1
            self.test_results["linking_maps"] = maps_valid
            
            if maps_valid:
                log.info(f"✅ Linking map validation passed: {valid_maps} valid maps found")
            else:
                log.error(f"❌ No valid linking maps found (need ≥ 1)")
                self.validation_errors.append(f"No valid linking maps with matching_result in {linking_map_dir}")
                
        except Exception as e:
            log.error(f"❌ Linking maps validation failed: {e}")
            self.validation_errors.append(f"Linking maps error: {str(e)}")
            self.test_results["linking_maps"] = False
    
    def _validate_category_json(self, domain: str) -> None:
        """Validate category JSON exists and has ≥ 5 categories"""
        try:
            log.info("🔍 Checking AI category JSON...")
            
            categories_file = Path(f"OUTPUTS/ai_suggested_categories/{domain}.json")
            
            if not categories_file.exists():
                log.error(f"❌ Category JSON missing: {categories_file}")
                self.validation_errors.append(f"Missing category JSON: {categories_file}")
                self.test_results["category_json"] = False
                return
            
            try:
                with open(categories_file, 'r') as f:
                    categories_data = json.load(f)
                
                total_categories = categories_data.get("total_categories", 0)
                categories_valid = total_categories >= 5
                
                self.test_results["category_json"] = categories_valid
                
                if categories_valid:
                    log.info(f"✅ Category JSON validation passed: {total_categories} categories (≥ 5 required)")
                else:
                    log.error(f"❌ Insufficient categories: {total_categories} < 5 required")
                    self.validation_errors.append(f"Insufficient categories: {total_categories} < 5 in {categories_file}")
                    
            except Exception as e:
                log.error(f"❌ Failed to parse category JSON: {e}")
                self.validation_errors.append(f"Invalid category JSON format: {categories_file}")
                self.test_results["category_json"] = False
                
        except Exception as e:
            log.error(f"❌ Category JSON validation failed: {e}")
            self.validation_errors.append(f"Category JSON error: {str(e)}")
            self.test_results["category_json"] = False
    
    def _validate_login_flag(self, domain: str) -> None:
        """Validate logs/debug/login_*.ok found"""
        try:
            log.info("🔍 Checking login debug flag...")
            
            debug_dir = Path("logs/debug")
            
            if not debug_dir.exists():
                log.error(f"❌ Debug log directory missing: {debug_dir}")
                self.validation_errors.append(f"Missing debug directory: {debug_dir}")
                self.test_results["login_flag"] = False
                return
            
            # Look for login flag files
            login_flag_pattern = f"login_{domain}.ok"
            login_flag_files = list(debug_dir.glob("login_*.ok"))
            specific_flag_file = debug_dir / login_flag_pattern
            
            flag_found = specific_flag_file.exists() or len(login_flag_files) > 0
            self.test_results["login_flag"] = flag_found
            
            if flag_found:
                if specific_flag_file.exists():
                    log.info(f"✅ Login flag found: {specific_flag_file}")
                    # Check file content
                    try:
                        flag_data = json.loads(specific_flag_file.read_text())
                        log.info(f"Login timestamp: {flag_data.get('timestamp', 'No timestamp')}")
                    except:
                        log.info("Login flag found (non-JSON format)")
                else:
                    log.info(f"✅ Login flags found: {[f.name for f in login_flag_files]}")
            else:
                log.error(f"❌ No login flag files found in: {debug_dir}")
                self.validation_errors.append(f"No login flag files found in {debug_dir}")
                
        except Exception as e:
            log.error(f"❌ Login flag validation failed: {e}")
            self.validation_errors.append(f"Login flag error: {str(e)}")
            self.test_results["login_flag"] = False
    
    def _generate_acceptance_report(self) -> Dict[str, Any]:
        """Generate acceptance gate report"""
        # All 5 criteria must pass
        criteria = [
            "supplier_ready_flag",
            "cache_products", 
            "linking_maps",
            "category_json",
            "login_flag"
        ]
        
        passed_criteria = sum(1 for criterion in criteria if self.test_results.get(criterion, False))
        all_passed = passed_criteria == len(criteria)
        
        report = {
            "acceptance_gate_timestamp": datetime.now().isoformat(),
            "total_criteria": len(criteria),
            "passed_criteria": passed_criteria,
            "acceptance_status": "PASS" if all_passed else "FAIL",
            "criteria_results": {criterion: self.test_results.get(criterion, False) for criterion in criteria},
            "validation_errors": self.validation_errors,
            "summary": {
                "all_criteria_met": all_passed,
                "workflow_executed": self.test_results.get("workflow_execution", False),
                "ready_for_production": all_passed and len(self.validation_errors) == 0
            }
        }
        
        return report

async def main():
    """Main acceptance gate test execution"""
    parser = argparse.ArgumentParser(description='Run acceptance gate test')
    parser.add_argument('--supplier-url', required=True, help='Supplier website URL')
    parser.add_argument('--supplier-email', help='Supplier login email')
    parser.add_argument('--supplier-password', help='Supplier login password')
    parser.add_argument('--headed', action='store_true', help='Run browsers in headed mode')
    parser.add_argument('--max-products', type=int, default=15, help='Maximum products to extract')
    
    args = parser.parse_args()
    
    # Prepare credentials
    credentials = {}
    if args.supplier_email and args.supplier_password:
        credentials = {
            "email": args.supplier_email,
            "password": args.supplier_password
        }
    
    # Run acceptance gate test
    validator = AcceptanceGateValidator()
    
    try:
        report = await validator.run_acceptance_gate_test(
            supplier_url=args.supplier_url,
            credentials=credentials,
            max_products=args.max_products
        )
        
        # Print results
        print(f"\n🚦 ACCEPTANCE GATE REPORT")
        print(f"=" * 60)
        print(f"Status: {report['acceptance_status']}")
        print(f"Criteria Passed: {report['passed_criteria']}/{report['total_criteria']}")
        print(f"Timestamp: {report['acceptance_gate_timestamp']}")
        
        print(f"\n📋 Criteria Results:")
        for criterion, result in report['criteria_results'].items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {criterion}: {status}")
        
        if report['validation_errors']:
            print(f"\n⚠️ Validation Errors:")
            for error in report['validation_errors']:
                print(f"  - {error}")
        
        print(f"\n📊 Summary:")
        print(f"  All criteria met: {'✅ YES' if report['summary']['all_criteria_met'] else '❌ NO'}")
        print(f"  Workflow executed: {'✅ YES' if report['summary']['workflow_executed'] else '❌ NO'}")
        print(f"  Ready for production: {'✅ YES' if report['summary']['ready_for_production'] else '❌ NO'}")
        
        # Save report
        report_file = f"acceptance_gate_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Report saved to: {report_file}")
        
        if report['acceptance_status'] == "PASS":
            print(f"\n🎉 ACCEPTANCE GATE PASSED! System is ready for production.")
            return 0
        else:
            print(f"\n❌ ACCEPTANCE GATE FAILED! System needs attention before production.")
            return 1
            
    except Exception as e:
        print(f"\n❌ ACCEPTANCE GATE TEST FAILED: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)