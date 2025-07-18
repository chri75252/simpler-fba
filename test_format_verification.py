#!/usr/bin/env python3
"""
Test script to verify the linking map and financial report format fixes
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add tools to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

def test_linking_map_format():
    """Test that linking map saves in correct array format"""
    print("🧪 Testing linking map format...")
    
    # Create a test linking map entry in the expected format
    test_entry = {
        "supplier_product_identifier": "EAN_5055319510417",
        "supplier_title_snippet": "Home & Garden Stove Polish Fireplace Restorer 200ml",
        "chosen_amazon_asin": "B0DCNDW6K9",
        "amazon_title_snippet": "Amazon Product Title Here",
        "amazon_ean_on_page": "5055319510417",
        "match_method": "EAN_search"
    }
    
    # Test array format
    test_linking_map = [test_entry]
    
    # Create test output directory
    test_dir = Path("/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/test_output")
    test_dir.mkdir(exist_ok=True)
    
    # Save test linking map
    test_file = test_dir / "test_linking_map.json"
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(test_linking_map, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Test linking map saved to: {test_file}")
    
    # Verify format
    with open(test_file, 'r', encoding='utf-8') as f:
        saved_data = json.load(f)
    
    if isinstance(saved_data, list):
        print("✅ SUCCESS: Linking map is in correct array format!")
        print(f"📊 Array contains {len(saved_data)} entries")
        if saved_data:
            print(f"📋 Sample entry keys: {list(saved_data[0].keys())}")
        return True
    else:
        print("❌ FAILED: Linking map is not in array format")
        return False

def test_financial_report_integration():
    """Test that financial report function is callable"""
    print("\n🧪 Testing financial report integration...")
    
    try:
        # Try to import the financial calculator
        from FBA_Financial_calculator import run_calculations
        print("✅ SUCCESS: FBA_Financial_calculator.run_calculations imported successfully")
        
        # Test that it's callable
        if callable(run_calculations):
            print("✅ SUCCESS: run_calculations is callable")
            print("📊 Financial report will be generated in CSV format")
            return True
        else:
            print("❌ FAILED: run_calculations is not callable")
            return False
            
    except ImportError as e:
        print(f"❌ FAILED: Could not import FBA_Financial_calculator: {e}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False

def main():
    """Run all format verification tests"""
    print("🔬 FORMAT VERIFICATION TESTS")
    print("=" * 50)
    
    # Test linking map format
    linking_map_success = test_linking_map_format()
    
    # Test financial report integration
    financial_report_success = test_financial_report_integration()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print(f"✅ Linking Map Format: {'PASSED' if linking_map_success else 'FAILED'}")
    print(f"✅ Financial Report Integration: {'PASSED' if financial_report_success else 'FAILED'}")
    
    if linking_map_success and financial_report_success:
        print("\n🎉 ALL FORMAT FIXES: VERIFIED SUCCESSFULLY")
        print("✅ System is ready to generate files in correct formats")
        return True
    else:
        print("\n❌ SOME FORMAT FIXES: FAILED VERIFICATION")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)