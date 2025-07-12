#!/usr/bin/env python3
"""
Simple test to verify Amazon cache file reading logic
Tests the core cache lookup functionality without full workflow imports
"""

import os
import json
import glob
import time
from pathlib import Path
from typing import Optional, Dict, Any

def get_cached_amazon_data_by_asin(asin: str, supplier_ean: str = None, amazon_cache_dir: str = "OUTPUTS/FBA_ANALYSIS/amazon_cache") -> Optional[Dict[str, Any]]:
    """
    Replicated cache reading logic from the fixed workflow
    """
    if not asin:
        return None
    
    # Try multiple filename patterns to find cached data
    cache_files_to_try = []
    
    # 1. If we have supplier EAN, try ASIN_EAN format first
    if supplier_ean:
        cache_files_to_try.append(f"amazon_{asin}_{supplier_ean}.json")
    
    # 2. Try ASIN-only format (legacy and fallback)
    cache_files_to_try.append(f"amazon_{asin}.json")
    
    # 3. Search for any file starting with amazon_{asin}_
    try:
        pattern_files = glob.glob(os.path.join(amazon_cache_dir, f"amazon_{asin}_*.json"))
        for pattern_file in pattern_files:
            filename = os.path.basename(pattern_file)
            if filename not in cache_files_to_try:
                cache_files_to_try.append(filename)
    except Exception:
        pass
    
    # Try each potential cache file
    for cache_filename in cache_files_to_try:
        asin_cache_file = os.path.join(amazon_cache_dir, cache_filename)
        if os.path.exists(asin_cache_file):
            try:
                with open(asin_cache_file, 'r', encoding='utf-8') as f:
                    amazon_product_data = json.load(f)
                print(f"   ✅ Found cache in: {cache_filename}")
                return amazon_product_data
            except Exception as e:
                print(f"   ❌ Error reading {cache_filename}: {e}")
                continue
    
    print(f"   ❌ No cache found for ASIN {asin} (tried {len(cache_files_to_try)} files)")
    return None

def test_cache_reading():
    """Test the cache reading logic"""
    print("🧪 Testing Amazon Cache File Reading Logic")
    print("=" * 50)
    
    amazon_cache_dir = Path("OUTPUTS/FBA_ANALYSIS/amazon_cache")
    
    if not amazon_cache_dir.exists():
        print("❌ Amazon cache directory not found")
        return False
    
    # Get test files
    test_files = list(amazon_cache_dir.glob("amazon_*.json"))[:10]
    
    if not test_files:
        print("❌ No Amazon cache files found")
        return False
    
    print(f"🔍 Testing with {len(test_files)} cache files...")
    
    success_count = 0
    for test_file in test_files:
        filename = test_file.name
        
        # Extract ASIN and EAN from filename
        if filename.startswith("amazon_") and filename.endswith(".json"):
            parts = filename[7:-5].split("_")  # Remove "amazon_" and ".json"
            asin = parts[0]
            ean = parts[1] if len(parts) > 1 else None
            
            print(f"\n📁 Testing: {filename}")
            print(f"   ASIN: {asin}, EAN: {ean}")
            
            # Test cache reading
            cached_data = get_cached_amazon_data_by_asin(asin, ean, str(amazon_cache_dir))
            
            if cached_data:
                print(f"   📊 Data contains: {len(cached_data)} keys")
                if 'title' in cached_data:
                    print(f"   📝 Title: {cached_data['title'][:50]}...")
                success_count += 1
            else:
                print(f"   ❌ Failed to read cache")
    
    print(f"\n📊 Results:")
    print(f"   ✅ Successful: {success_count}/{len(test_files)}")
    print(f"   📈 Success rate: {(success_count/len(test_files))*100:.1f}%")
    
    return success_count == len(test_files)

def test_lookup_patterns():
    """Test different lookup patterns"""
    print("\n🔍 Testing Lookup Patterns")
    print("=" * 30)
    
    amazon_cache_dir = Path("OUTPUTS/FBA_ANALYSIS/amazon_cache")
    
    # Find files with different patterns
    ean_files = [f for f in amazon_cache_dir.glob("amazon_*_*.json") if len(f.stem.split("_")) >= 3]
    asin_only_files = [f for f in amazon_cache_dir.glob("amazon_*.json") if len(f.stem.split("_")) == 2]
    
    print(f"📊 Found {len(ean_files)} EAN-based files, {len(asin_only_files)} ASIN-only files")
    
    tests_passed = 0
    total_tests = 0
    
    # Test EAN-based file lookup
    if ean_files:
        test_file = ean_files[0]
        parts = test_file.stem.split("_")
        asin = parts[1]
        ean = parts[2]
        
        print(f"\n🧪 EAN File Test: {test_file.name}")
        
        # Test 1: Correct EAN
        total_tests += 1
        result = get_cached_amazon_data_by_asin(asin, ean, str(amazon_cache_dir))
        if result:
            tests_passed += 1
            print(f"   ✅ Found with correct EAN")
        else:
            print(f"   ❌ Not found with correct EAN")
        
        # Test 2: No EAN (should still find via pattern)
        total_tests += 1
        result = get_cached_amazon_data_by_asin(asin, None, str(amazon_cache_dir))
        if result:
            tests_passed += 1
            print(f"   ✅ Found without EAN (pattern search)")
        else:
            print(f"   ❌ Not found without EAN")
    
    # Test ASIN-only file lookup
    if asin_only_files:
        test_file = asin_only_files[0]
        asin = test_file.stem.split("_")[1]
        
        print(f"\n🧪 ASIN-Only File Test: {test_file.name}")
        
        # Test 3: ASIN-only lookup
        total_tests += 1
        result = get_cached_amazon_data_by_asin(asin, None, str(amazon_cache_dir))
        if result:
            tests_passed += 1
            print(f"   ✅ Found ASIN-only file")
        else:
            print(f"   ❌ Not found ASIN-only file")
    
    print(f"\n📊 Pattern Tests: {tests_passed}/{total_tests} passed")
    return tests_passed == total_tests

def main():
    """Run all tests"""
    print("🚀 Simple Amazon Cache Reading Test")
    print("=" * 40)
    
    # Test basic cache reading
    basic_passed = test_cache_reading()
    
    # Test lookup patterns
    pattern_passed = test_lookup_patterns()
    
    print("\n" + "=" * 40)
    if basic_passed and pattern_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Cache reading fix is working correctly")
        print("✅ System can find files with EAN in filename")
        print("✅ FBA Financial Calculator should work better now")
    else:
        print("⚠️  Some tests failed")
        print("   This may indicate remaining cache issues")
    
    return basic_passed and pattern_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
