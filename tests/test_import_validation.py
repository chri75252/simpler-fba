#!/usr/bin/env python3
"""
Import Validation Test - LangGraph Fixes
========================================

Lightweight import-only validation for critical LangGraph components.
This replaces the heavy end-to-end test for production environments.

USAGE:
    python tests/test_import_validation.py
"""

import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class ImportValidator:
    """Validate critical imports are working"""
    
    def __init__(self):
        self.test_results = {}
        self.validation_errors = []
    
    def run_import_validation(self) -> dict:
        """Run lightweight import validation"""
        try:
            log.info("🧪 Running import validation tests")
            
            # Test core imports
            self._test_core_imports()
            
            # Test LangGraph workflow
            self._test_workflow_imports()
            
            # Test tools imports  
            self._test_tools_imports()
            
            # Test browser manager
            self._test_browser_manager_imports()
            
            # Generate validation report
            return self._generate_report()
            
        except Exception as e:
            log.error(f"❌ Import validation failed: {e}")
            self.validation_errors.append(f"General validation error: {str(e)}")
            return self._generate_report()
    
    def _test_core_imports(self) -> None:
        """Test core system imports"""
        try:
            log.info("🔍 Testing core imports...")
            
            # Test pathlib and json
            try:
                from pathlib import Path
                import json
                from datetime import datetime
                self.test_results["core_stdlib"] = True
                log.info("Standard library imports: ✅ PASS")
            except ImportError as e:
                self.test_results["core_stdlib"] = False
                self.validation_errors.append(f"Standard library import failed: {str(e)}")
                log.error(f"Standard library imports: ❌ FAIL - {e}")
            
        except Exception as e:
            log.error(f"❌ Core imports test failed: {e}")
            self.validation_errors.append(f"Core imports error: {str(e)}")
            self.test_results["core_stdlib"] = False
    
    def _test_workflow_imports(self) -> None:
        """Test LangGraph workflow imports"""
        try:
            log.info("🔍 Testing workflow imports...")
            
            # Test LangGraph workflow
            try:
                from langraph_integration.complete_fba_workflow import CompleteFBAWorkflow, CompleteFBAState
                self.test_results["workflow_main"] = True
                log.info("CompleteFBAWorkflow import: ✅ PASS")
            except ImportError as e:
                self.test_results["workflow_main"] = False
                self.validation_errors.append(f"Workflow import failed: {str(e)}")
                log.error(f"CompleteFBAWorkflow import: ❌ FAIL - {e}")
            
            # Test LangGraph core
            try:
                from langgraph.graph import StateGraph, END, START
                from langchain_core.messages import HumanMessage, AIMessage
                self.test_results["langgraph_core"] = True
                log.info("LangGraph core imports: ✅ PASS")
            except ImportError as e:
                self.test_results["langgraph_core"] = False
                self.validation_errors.append(f"LangGraph core import failed: {str(e)}")
                log.error(f"LangGraph core imports: ❌ FAIL - {e}")
            
        except Exception as e:
            log.error(f"❌ Workflow imports test failed: {e}")
            self.validation_errors.append(f"Workflow imports error: {str(e)}")
            self.test_results["workflow_main"] = False
            self.test_results["langgraph_core"] = False
    
    def _test_tools_imports(self) -> None:
        """Test tools imports"""
        try:
            log.info("🔍 Testing tools imports...")
            
            # Test AI category suggester
            try:
                from tools.ai_category_suggester import generate_categories, AICategorySuggester
                self.test_results["ai_category_suggester"] = True
                log.info("AI Category Suggester import: ✅ PASS")
            except ImportError as e:
                self.test_results["ai_category_suggester"] = False
                self.validation_errors.append(f"AI Category Suggester import failed: {str(e)}")
                log.error(f"AI Category Suggester import: ❌ FAIL - {e}")
            
            # Test vision discovery engine
            try:
                from tools.vision_discovery_engine import discover_complete_supplier, VisionDiscoveryEngine
                self.test_results["vision_discovery"] = True
                log.info("Vision Discovery Engine import: ✅ PASS")
            except ImportError as e:
                self.test_results["vision_discovery"] = False
                self.validation_errors.append(f"Vision Discovery Engine import failed: {str(e)}")
                log.error(f"Vision Discovery Engine import: ❌ FAIL - {e}")
            
            # Test supplier script generator
            try:
                from tools.supplier_script_generator import SupplierScriptGenerator
                self.test_results["supplier_script_generator"] = True
                log.info("Supplier Script Generator import: ✅ PASS")
            except ImportError as e:
                self.test_results["supplier_script_generator"] = False
                self.validation_errors.append(f"Supplier Script Generator import failed: {str(e)}")
                log.error(f"Supplier Script Generator import: ❌ FAIL - {e}")
            
            # Test configurable supplier scraper
            try:
                from tools.configurable_supplier_scraper import ConfigurableSupplierScraper
                self.test_results["configurable_scraper"] = True
                log.info("Configurable Supplier Scraper import: ✅ PASS")
            except ImportError as e:
                self.test_results["configurable_scraper"] = False
                self.validation_errors.append(f"Configurable Supplier Scraper import failed: {str(e)}")
                log.error(f"Configurable Supplier Scraper import: ❌ FAIL - {e}")
            
        except Exception as e:
            log.error(f"❌ Tools imports test failed: {e}")
            self.validation_errors.append(f"Tools imports error: {str(e)}")
            self.test_results["ai_category_suggester"] = False
            self.test_results["vision_discovery"] = False
            self.test_results["supplier_script_generator"] = False
            self.test_results["configurable_scraper"] = False
    
    def _test_browser_manager_imports(self) -> None:
        """Test browser manager imports"""
        try:
            log.info("🔍 Testing browser manager imports...")
            
            # Test Selenium browser manager
            try:
                from browser_automation.selenium_browser_manager import SeleniumBrowserManager
                from browser_automation.playwright_to_selenium_migrator import PlaywrightToSeleniumMigrator
                self.test_results["browser_manager"] = True
                log.info("Selenium Browser Manager import: ✅ PASS")
            except ImportError as e:
                self.test_results["browser_manager"] = False
                self.validation_errors.append(f"Browser Manager import failed: {str(e)}")
                log.error(f"Selenium Browser Manager import: ❌ FAIL - {e}")
            
        except Exception as e:
            log.error(f"❌ Browser manager imports test failed: {e}")
            self.validation_errors.append(f"Browser manager imports error: {str(e)}")
            self.test_results["browser_manager"] = False
    
    def _generate_report(self) -> dict:
        """Generate validation report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Critical imports (required for basic functionality)
        critical_imports = [
            "core_stdlib",
            "workflow_main", 
            "ai_category_suggester",
            "vision_discovery",
            "supplier_script_generator",
            "browser_manager"
        ]
        
        critical_passed = sum(1 for key in critical_imports if self.test_results.get(key, False))
        critical_success = (critical_passed / len(critical_imports) * 100) if critical_imports else 0
        
        report = {
            "validation_type": "import_only",
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": success_rate,
            "critical_success_rate": critical_success,
            "overall_status": "PASS" if critical_success >= 90 else "FAIL",
            "test_results": self.test_results,
            "validation_errors": self.validation_errors,
            "summary": {
                "critical_imports_working": critical_success >= 90,
                "optional_imports_working": True,
                "workflow_importable": self.test_results.get("workflow_main", False),
                "tools_importable": all([
                    self.test_results.get("ai_category_suggester", False),
                    self.test_results.get("vision_discovery", False),
                    self.test_results.get("supplier_script_generator", False)
                ])
            }
        }
        
        return report

def main():
    """Main validation execution"""
    validator = ImportValidator()
    
    try:
        report = validator.run_import_validation()
        
        # Print results
        print(f"\n📊 IMPORT VALIDATION REPORT")
        print(f"=" * 50)
        print(f"Overall Status: {report['overall_status']}")
        print(f"Success Rate: {report['success_rate']:.1f}% ({report['passed_tests']}/{report['total_tests']})")
        print(f"Critical Success Rate: {report['critical_success_rate']:.1f}%")
        
        print(f"\n🔧 Import Results:")
        for test_name, result in report['test_results'].items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name}: {status}")
        
        if report['validation_errors']:
            print(f"\n⚠️ Import Errors:")
            for error in report['validation_errors']:
                print(f"  - {error}")
        
        print(f"\n📋 Summary:")
        print(f"  Critical imports working: {'✅ YES' if report['summary']['critical_imports_working'] else '❌ NO'}")
        print(f"  Workflow importable: {'✅ YES' if report['summary']['workflow_importable'] else '❌ NO'}")
        print(f"  Tools importable: {'✅ YES' if report['summary']['tools_importable'] else '❌ NO'}")
        
        if report['overall_status'] == "PASS":
            print(f"\n🎉 IMPORT VALIDATION SUCCESSFUL! All critical imports are working.")
            return 0
        else:
            print(f"\n⚠️ IMPORT VALIDATION FAILED! Some critical imports are missing.")
            return 1
            
    except Exception as e:
        print(f"\n❌ IMPORT VALIDATION FAILED: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)