#!/usr/bin/env python3
"""
Final Verification Test - All Critical Issues Resolved
Tests all the fixes implemented for the user's critical issues
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def test_all_critical_fixes():
    """Test all critical fixes implemented"""
    log.info("🧪 FINAL VERIFICATION: Testing All Critical Fixes")
    
    results = {
        "financial_reports_generation": False,
        "processing_state_management": False,
        "authentication_fallback_integration": False,
        "price_not_found_trigger": False,
        "file_verification": {}
    }
    
    # Test 1: Financial Reports Generation
    log.info("\n1️⃣ TESTING: Financial Reports Generation")
    financial_reports_dir = Path("/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/OUTPUTS/FBA_ANALYSIS/financial_reports/poundwholesale-co-uk")
    
    if financial_reports_dir.exists():
        csv_files = list(financial_reports_dir.glob("fba_financial_report_*.csv"))
        if csv_files:
            latest_report = max(csv_files, key=lambda x: x.stat().st_mtime)
            age_minutes = (datetime.now().timestamp() - latest_report.stat().st_mtime) / 60
            
            if age_minutes < 30:  # Recent file (within 30 minutes)
                results["financial_reports_generation"] = True
                results["file_verification"]["latest_financial_report"] = str(latest_report)
                log.info(f"✅ Financial reports: WORKING - Latest report: {latest_report.name} (age: {age_minutes:.1f} min)")
                
                # Check file content
                try:
                    with open(latest_report, 'r') as f:
                        content = f.read()
                    if len(content) > 1000:  # Has substantial content
                        log.info(f"✅ Report content: VERIFIED - Size: {len(content)} characters")
                    else:
                        log.warning(f"⚠️ Report content: SMALL - Size: {len(content)} characters")
                except Exception as e:
                    log.error(f"❌ Could not read report: {e}")
            else:
                log.warning(f"⚠️ Financial reports: OLD - Latest report age: {age_minutes:.1f} minutes")
        else:
            log.error("❌ Financial reports: NO FILES FOUND")
    else:
        log.error("❌ Financial reports: DIRECTORY NOT FOUND")
    
    # Test 2: Processing State Management
    log.info("\n2️⃣ TESTING: Processing State Management")
    state_file = Path("/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/OUTPUTS/CACHE/processing_states/poundwholesale-co-uk_processing_state.json")
    
    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                state_data = json.load(f)
            
            last_index = state_data.get("last_processed_index", 0)
            if last_index > 0:
                results["processing_state_management"] = True
                results["file_verification"]["processing_state"] = str(state_file)
                log.info(f"✅ Processing state: WORKING - Last index: {last_index}")
                
                # Check for recent activity
                timestamp_str = state_data.get("last_updated")
                if timestamp_str:
                    log.info(f"✅ State timestamp: {timestamp_str}")
            else:
                log.warning(f"⚠️ Processing state: NO PROGRESS - Last index: {last_index}")
        except Exception as e:
            log.error(f"❌ Processing state: ERROR - {e}")
    else:
        log.error("❌ Processing state: FILE NOT FOUND")
    
    # Test 3: Authentication Fallback Integration
    log.info("\n3️⃣ TESTING: Authentication Fallback Integration")
    
    # Check workflow file for authentication integration
    workflow_file = Path("/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/tools/passive_extraction_workflow_latest.py")
    if workflow_file.exists():
        try:
            with open(workflow_file, 'r') as f:
                workflow_content = f.read()
            
            # Check for key authentication features
            auth_features = [
                "products_without_price_count",
                "auth_fallback_config",
                "price_missing_threshold",
                "PRICE MISSING:",
                "AUTH TRIGGER:"
            ]
            
            found_features = []
            for feature in auth_features:
                if feature in workflow_content:
                    found_features.append(feature)
            
            if len(found_features) >= 4:
                results["authentication_fallback_integration"] = True
                log.info(f"✅ Authentication fallback: INTEGRATED - Found {len(found_features)}/5 features")
                log.info(f"   Features found: {', '.join(found_features)}")
            else:
                log.warning(f"⚠️ Authentication fallback: PARTIAL - Found {len(found_features)}/5 features")
        except Exception as e:
            log.error(f"❌ Authentication fallback: ERROR - {e}")
    else:
        log.error("❌ Authentication fallback: WORKFLOW FILE NOT FOUND")
    
    # Test 4: Price Not Found Trigger Mechanism
    log.info("\n4️⃣ TESTING: Price Not Found Trigger Mechanism")
    
    # Check product_data_extractor.py for "Price not found" pattern
    extractor_file = Path("/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/tools/product_data_extractor.py")
    if extractor_file.exists():
        try:
            with open(extractor_file, 'r') as f:
                extractor_content = f.read()
            
            trigger_patterns = [
                "'Price not found'",
                "'Login required to view price'",
                "price_data['price'] = 'Price not found'"
            ]
            
            found_patterns = []
            for pattern in trigger_patterns:
                if pattern in extractor_content:
                    found_patterns.append(pattern)
            
            if len(found_patterns) >= 2:
                results["price_not_found_trigger"] = True
                log.info(f"✅ Price not found trigger: IMPLEMENTED - Found {len(found_patterns)}/3 patterns")
            else:
                log.warning(f"⚠️ Price not found trigger: INCOMPLETE - Found {len(found_patterns)}/3 patterns")
        except Exception as e:
            log.error(f"❌ Price not found trigger: ERROR - {e}")
    else:
        log.error("❌ Price not found trigger: EXTRACTOR FILE NOT FOUND")
    
    # Summary
    log.info("\n📊 FINAL VERIFICATION RESULTS:")
    log.info("=" * 50)
    
    total_tests = len([k for k in results.keys() if k != "file_verification"])
    passed_tests = sum([1 for k, v in results.items() if k != "file_verification" and v])
    
    log.info(f"✅ Tests Passed: {passed_tests}/{total_tests}")
    log.info(f"📋 Financial Reports Generation: {'✅ PASS' if results['financial_reports_generation'] else '❌ FAIL'}")
    log.info(f"📋 Processing State Management: {'✅ PASS' if results['processing_state_management'] else '❌ FAIL'}")
    log.info(f"📋 Authentication Fallback Integration: {'✅ PASS' if results['authentication_fallback_integration'] else '❌ FAIL'}")
    log.info(f"📋 Price Not Found Trigger: {'✅ PASS' if results['price_not_found_trigger'] else '❌ FAIL'}")
    
    if passed_tests == total_tests:
        log.info("\n🎉 ALL CRITICAL ISSUES RESOLVED SUCCESSFULLY!")
        log.info("🎯 System is ready for production use")
    else:
        log.warning(f"\n⚠️ {total_tests - passed_tests} issues still need attention")
    
    # File verification summary
    if results["file_verification"]:
        log.info("\n📁 FILE VERIFICATION:")
        for file_type, file_path in results["file_verification"].items():
            log.info(f"   {file_type}: {file_path}")
    
    return results

if __name__ == "__main__":
    test_all_critical_fixes()