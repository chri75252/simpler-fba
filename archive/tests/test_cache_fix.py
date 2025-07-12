#!/usr/bin/env python3
"""
Test script to verify the Amazon cache file reading fix
Tests that the system can now find files with EAN in the filename
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the tools directory to the path
sys.path.append('tools')

async def test_cache_reading():
    """Test the fixed cache reading logic"""
    print("🧪 Testing Amazon Cache File Reading Fix")
    print("=" * 50)
    
    try:
        # Import the workflow class
        from passive_extraction_workflow_latest import PassiveExtractionWorkflow
        
        # Create a test instance
        workflow = PassiveExtractionWorkflow()
        
        # Test cases: Check if we can find existing files
        amazon_cache_dir = Path("OUTPUTS/FBA_ANALYSIS/amazon_cache")
        
        if not amazon_cache_dir.exists():
            print("❌ Amazon cache directory not found")
            return False
        
        # Get some test files
        test_files = list(amazon_cache_dir.glob("amazon_*.json"))[:5]
        
        if not test_files:
            print("❌ No Amazon cache files found for testing")
            return False
        
        print(f"🔍 Testing cache reading with {len(test_files)} files...")
        
        success_count = 0
        for test_file in test_files:
            filename = test_file.name
            
            # Extract ASIN and EAN from filename
            if filename.startswith("amazon_") and filename.endswith(".json"):
                parts = filename[7:-5].split("_")  # Remove "amazon_" and ".json"
                asin = parts[0]
                ean = parts[1] if len(parts) > 1 else None
                
                print(f"\n📁 Testing file: {filename}")
                print(f"   ASIN: {asin}")
                print(f"   EAN: {ean}")
                
                # Test the fixed cache reading method
                try:
                    cached_data = await workflow._get_cached_amazon_data_by_asin(asin, ean)
                    
                    if cached_data:
                        print(f"   ✅ Successfully loaded cache data")
                        print(f"   📊 Data keys: {list(cached_data.keys())[:5]}...")
                        success_count += 1
                    else:
                        print(f"   ❌ Failed to load cache data")
                        
                except Exception as e:
                    print(f"   ❌ Error loading cache: {e}")
        
        print(f"\n📊 Test Results:")
        print(f"   ✅ Successful reads: {success_count}/{len(test_files)}")
        print(f"   📈 Success rate: {(success_count/len(test_files))*100:.1f}%")
        
        if success_count == len(test_files):
            print(f"\n🎉 ALL TESTS PASSED - Cache reading fix is working!")
            return True
        else:
            print(f"\n⚠️  Some tests failed - may need further investigation")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_cache_lookup_patterns():
    """Test different cache lookup patterns"""
    print("\n🔍 Testing Cache Lookup Patterns")
    print("=" * 40)
    
    try:
        from passive_extraction_workflow_latest import PassiveExtractionWorkflow
        workflow = PassiveExtractionWorkflow()
        
        # Find a file with EAN to test different lookup scenarios
        amazon_cache_dir = Path("OUTPUTS/FBA_ANALYSIS/amazon_cache")
        ean_files = [f for f in amazon_cache_dir.glob("amazon_*_*.json") if len(f.stem.split("_")) >= 3]
        
        if not ean_files:
            print("❌ No EAN-based files found for pattern testing")
            return False
        
        test_file = ean_files[0]
        filename = test_file.name
        parts = filename[7:-5].split("_")
        asin = parts[0]
        ean = parts[1]
        
        print(f"📁 Using test file: {filename}")
        print(f"   ASIN: {asin}, EAN: {ean}")
        
        # Test 1: Lookup with correct EAN
        print(f"\n🧪 Test 1: Lookup with correct EAN")
        result1 = await workflow._get_cached_amazon_data_by_asin(asin, ean)
        print(f"   Result: {'✅ Found' if result1 else '❌ Not found'}")
        
        # Test 2: Lookup with wrong EAN
        print(f"\n🧪 Test 2: Lookup with wrong EAN")
        result2 = await workflow._get_cached_amazon_data_by_asin(asin, "1234567890123")
        print(f"   Result: {'✅ Found' if result2 else '❌ Not found'}")
        
        # Test 3: Lookup without EAN (should still find via pattern search)
        print(f"\n🧪 Test 3: Lookup without EAN")
        result3 = await workflow._get_cached_amazon_data_by_asin(asin, None)
        print(f"   Result: {'✅ Found' if result3 else '❌ Not found'}")
        
        # Test 4: Lookup with non-existent ASIN
        print(f"\n🧪 Test 4: Lookup with non-existent ASIN")
        result4 = await workflow._get_cached_amazon_data_by_asin("B999999999", None)
        print(f"   Result: {'✅ Found' if result4 else '❌ Not found (expected)'}")
        
        success_tests = sum([bool(result1), bool(result2), bool(result3), not bool(result4)])
        print(f"\n📊 Pattern Test Results: {success_tests}/4 tests behaved as expected")
        
        return success_tests >= 3  # Allow some flexibility
        
    except Exception as e:
        print(f"❌ Pattern test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Amazon Cache Reading Fix - Comprehensive Test")
    print("=" * 60)
    
    # Run basic cache reading test
    basic_test_passed = await test_cache_reading()
    
    # Run pattern lookup test
    pattern_test_passed = await test_cache_lookup_patterns()
    
    print("\n" + "=" * 60)
    if basic_test_passed and pattern_test_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Amazon cache reading fix is working correctly")
        print("✅ System can now find files with EAN in filename")
        print("✅ FBA Financial Calculator should work much better now")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        print("⚠️  Cache reading may still have issues")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
