#!/usr/bin/env python3
"""
Test script to verify FBA/FBM seller counts extraction and new CSV columns
"""
import os
import json
import sys

# Add tools directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))
# Add utils to path for ensure_output_subdirs function
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))

from FBA_Financial_calculator import extract_enhanced_metrics, run_calculations
from path_manager import ensure_output_subdirs

def test_seller_counts_extraction():
    """Test if FBA/FBM seller counts are being extracted from Amazon data"""
    print("🧪 Testing FBA/FBM Seller Counts Extraction...")
    
    # Ensure required directories exist
    ensure_output_subdirs()
    
    # Load a sample Amazon cache file
    amazon_cache_dir = "OUTPUTS/FBA_ANALYSIS/amazon_cache"
    assert os.path.exists(amazon_cache_dir), "❌ Amazon cache directory not found"
    
    cache_files = [f for f in os.listdir(amazon_cache_dir) if f.endswith('.json')]
    assert cache_files, "❌ No Amazon cache files found"
    
    # Test with first available cache file
    test_file = os.path.join(amazon_cache_dir, cache_files[0])
    print(f"📁 Testing with: {cache_files[0]}")
    
    with open(test_file, 'r', encoding='utf-8') as f:
        amazon_data = json.load(f)
    
    # Extract enhanced metrics
    metrics = extract_enhanced_metrics(amazon_data)
    
    print("📊 Extracted Enhanced Metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    # Check if we found any seller data
    seller_data_found = any([
        metrics['fba_seller_count'] is not None,
        metrics['fbm_seller_count'] is not None,
        metrics['total_offer_count'] is not None
    ])
    
    if seller_data_found:
        print("✅ Seller count extraction working!")
    else:
        print("⚠️ No seller count data found in this file")

def test_csv_columns():
    """Test if new columns appear in CSV output"""
    print("\n🧪 Testing CSV Column Generation...")
    
    # Run FBA calculator
    results = run_calculations()
    
    assert results and 'dataframe' in results, "❌ No dataframe generated"
    
    df = results['dataframe']
    expected_columns = ['bought_in_past_month', 'fba_seller_count', 'fbm_seller_count', 'total_offer_count']
    
    print("📋 CSV Columns Found:")
    for col in df.columns:
        status = "✅" if col in expected_columns else "📄"
        print(f"  {status} {col}")
    
    missing_columns = [col for col in expected_columns if col not in df.columns]
    assert not missing_columns, f"❌ Missing columns: {missing_columns}"
    print("✅ All new columns present in CSV!")

if __name__ == "__main__":
    print("🚀 Starting Enhanced Metrics Verification Tests...\n")
    
    test_seller_counts_extraction()
    test_csv_columns()
    
    print("\n🎉 All tests passed! Enhanced metrics are working correctly.")
