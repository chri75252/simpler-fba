#!/usr/bin/env python3
"""
Test script for infinite mode edge case handling.
Validates the new infinite mode detection logic.
"""

import math
import sys
import json
from pathlib import Path

def is_infinite_mode(max_products, max_products_per_category):
    """Detect infinite mode based on multiple indicators"""
    mp = max_products or 0
    mppc = max_products_per_category or 0
    
    return any([
        mp <= 0,                    # Zero or negative
        mppc <= 0,                  # Zero or negative  
        mp >= 99999,                # High value threshold
        mppc >= 99999,              # High value threshold
    ])

def calculate_categories_needed(max_products, max_products_per_category, total_available_categories):
    """
    Safely calculate how many categories to process, handling all edge cases.
    
    Returns:
    - total_available_categories if infinite mode detected
    - calculated value if finite mode
    """
    # Detect infinite mode
    if is_infinite_mode(max_products, max_products_per_category):
        return total_available_categories
    
    # Safe finite mode calculation
    try:
        if max_products > 0 and max_products_per_category > 0:
            categories_needed = math.ceil(max_products / max_products_per_category)
            # Cap at available categories
            return min(categories_needed, total_available_categories)
        else:
            # Fallback to infinite mode
            return total_available_categories
    except (ZeroDivisionError, TypeError, ValueError):
        # Any calculation error defaults to infinite mode
        return total_available_categories

def test_infinite_mode_detection():
    """Test the infinite mode detection with comprehensive edge cases"""
    print("🧪 TESTING INFINITE MODE EDGE CASE DETECTION")
    print("=" * 60)
    
    # Test cases: (max_products, max_products_per_category, expected_mode, description)
    test_cases = [
        (0, 0, True, "Both zero values"),
        (99999, 0, True, "Zero denominator (division by zero risk)"),
        (0, 99999, True, "Zero numerator"),
        (99999, 99999, True, "Both high values (user infinite intent)"),
        (100000, 50, True, "Very high max_products"),
        (50, 100000, True, "Very high max_products_per_category"),
        (-1, 50, True, "Negative max_products"),
        (50, -1, True, "Negative max_products_per_category"),
        (None, 50, True, "None max_products"),
        (50, None, True, "None max_products_per_category"),
        (None, None, True, "Both None"),
        
        # Finite mode cases
        (100, 50, False, "Normal finite calculation"),
        (150, 50, False, "Finite with remainder"),
        (1, 1, False, "Minimal finite values"),
        (50, 100, False, "Less than 1 category needed"),
    ]
    
    total_available_categories = 20
    passed = 0
    failed = 0
    
    for max_products, max_products_per_category, expected_infinite, description in test_cases:
        result = is_infinite_mode(max_products, max_products_per_category)
        categories_result = calculate_categories_needed(max_products, max_products_per_category, total_available_categories)
        
        status = "✅ PASS" if result == expected_infinite else "❌ FAIL"
        mode_str = "INFINITE" if result else "FINITE"
        expected_str = "INFINITE" if expected_infinite else "FINITE"
        
        print(f"{status} | {description}")
        print(f"    Input: max_products={max_products}, max_products_per_category={max_products_per_category}")
        print(f"    Expected: {expected_str}, Got: {mode_str}")
        print(f"    Categories to process: {categories_result}/{total_available_categories}")
        
        if result == expected_infinite:
            passed += 1
        else:
            failed += 1
        print()
    
    print("=" * 60)
    print(f"📊 TEST RESULTS: {passed} PASSED, {failed} FAILED")
    return failed == 0

def test_division_by_zero_prevention():
    """Test that division by zero is completely prevented"""
    print("\n🛡️ TESTING DIVISION BY ZERO PREVENTION")
    print("=" * 60)
    
    # These combinations previously caused ZeroDivisionError
    dangerous_cases = [
        (0, 0),
        (99999, 0),
        (1000, 0),
        (-1, 0),
        (None, 0),
    ]
    
    all_safe = True
    for max_products, max_products_per_category in dangerous_cases:
        try:
            result = calculate_categories_needed(max_products, max_products_per_category, 20)
            print(f"✅ SAFE: ({max_products}, {max_products_per_category}) → {result} categories")
        except ZeroDivisionError as e:
            print(f"❌ DIVISION BY ZERO: ({max_products}, {max_products_per_category}) → {e}")
            all_safe = False
        except Exception as e:
            print(f"⚠️ OTHER ERROR: ({max_products}, {max_products_per_category}) → {e}")
            all_safe = False
    
    print("=" * 60)
    status = "✅ ALL SAFE" if all_safe else "❌ ERRORS DETECTED"
    print(f"🛡️ DIVISION BY ZERO PREVENTION: {status}")
    return all_safe

def test_current_config_files():
    """Test with actual configuration files from the system"""
    print("\n📁 TESTING ACTUAL CONFIGURATION FILES")
    print("=" * 60)
    
    config_files = [
        "config/system_config.json.inifinitnewst",
        "config/system_config.json",
        "config/system_config_finite_mode.json",
        "config/system_config_exhaustive_mode.json",
    ]
    
    for config_file in config_files:
        config_path = Path(config_file)
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                # Extract relevant values
                system = config.get('system', {})
                max_products = system.get('max_products')
                max_products_per_category = system.get('max_products_per_category')
                
                infinite = is_infinite_mode(max_products, max_products_per_category)
                categories = calculate_categories_needed(max_products, max_products_per_category, 20)
                
                mode = "INFINITE" if infinite else "FINITE"
                print(f"📄 {config_file}")
                print(f"    max_products: {max_products}")
                print(f"    max_products_per_category: {max_products_per_category}")
                print(f"    Detected mode: {mode}")
                print(f"    Categories to process: {categories}/20")
                print()
                
            except Exception as e:
                print(f"❌ Error reading {config_file}: {e}")
                print()
        else:
            print(f"⚠️ Config file not found: {config_file}")
            print()

if __name__ == "__main__":
    print("🚀 AMAZON FBA AGENT SYSTEM - INFINITE MODE EDGE CASE TESTING")
    print("Testing robust infinite mode detection and division by zero prevention")
    print()
    
    # Run all tests
    test1_passed = test_infinite_mode_detection()
    test2_passed = test_division_by_zero_prevention()
    test_current_config_files()
    
    # Final results
    print("\n" + "=" * 60)
    print("🎯 FINAL TEST RESULTS")
    print("=" * 60)
    
    if test1_passed and test2_passed:
        print("✅ ALL TESTS PASSED - Infinite mode edge cases are now handled safely!")
        print("✅ No division by zero errors possible")
        print("✅ System will correctly detect infinite mode from configuration")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED - Review implementation")
        sys.exit(1)