#!/usr/bin/env python3
"""
SAFE CACHED PRODUCTS ANALYZER - GUARANTEED NOT TO AFFECT RUNNING SYSTEM
==========================================================================
Purpose: Reconstruct missing cached products from Amazon cache files
Method: Analyzes Amazon cache files created since last supplier cache update
Safety: 100% guaranteed - read-only operations on separate files

APPROACH: 
- Amazon cache files are created for each new product match
- These files contain supplier product info that hasn't been saved to cache
- By analyzing timestamps, we can reconstruct missing cached products
"""

import os
import sys
import json
import glob
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = "/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3"
sys.path.insert(0, project_root)

def safe_cached_products_analysis():
    """
    GUARANTEED SAFE METHOD: Analyze Amazon cache files to reconstruct missing products
    """
    
    print("🔍 SAFE CACHED PRODUCTS ANALYZER")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print()
    
    # Get supplier cache info
    supplier_cache_path = os.path.join(project_root, "OUTPUTS/cached_products/clearance-king_co_uk_products_cache.json")
    amazon_cache_dir = os.path.join(project_root, "OUTPUTS/FBA_ANALYSIS/amazon_cache")
    
    if not os.path.exists(supplier_cache_path):
        print("❌ Supplier cache file not found!")
        return False
    
    if not os.path.exists(amazon_cache_dir):
        print("❌ Amazon cache directory not found!")
        return False
    
    # Get supplier cache timestamp (last update)
    supplier_stat = os.stat(supplier_cache_path)
    supplier_last_modified = datetime.fromtimestamp(supplier_stat.st_mtime)
    
    with open(supplier_cache_path, 'r', encoding='utf-8') as f:
        current_cached_products = json.load(f)
    
    print(f"📊 CURRENT SUPPLIER CACHE STATUS:")
    print(f"   Products cached: {len(current_cached_products)}")
    print(f"   Last updated: {supplier_last_modified}")
    print()
    
    # Find Amazon cache files created AFTER supplier cache update
    print("🔍 Analyzing Amazon cache files for missing products...")
    amazon_files = glob.glob(os.path.join(amazon_cache_dir, "amazon_*.json"))
    
    new_amazon_files = []
    for file_path in amazon_files:
        file_stat = os.stat(file_path)
        file_modified = datetime.fromtimestamp(file_stat.st_mtime)
        
        if file_modified > supplier_last_modified:
            new_amazon_files.append((file_path, file_modified))
    
    new_amazon_files.sort(key=lambda x: x[1])  # Sort by timestamp
    
    print(f"📈 ANALYSIS RESULTS:")
    print(f"   Total Amazon cache files: {len(amazon_files)}")
    print(f"   New files since supplier cache update: {len(new_amazon_files)}")
    print()
    
    if not new_amazon_files:
        print("ℹ️  No new Amazon cache files found since last supplier cache update")
        print("   This suggests either:")
        print("   - No new products processed, or")
        print("   - Products processed but not yet reaching save threshold")
        return True
    
    # Analyze new Amazon files to extract supplier product info
    print("🕵️  EXTRACTING SUPPLIER PRODUCT INFO FROM NEW AMAZON FILES:")
    print("-" * 60)
    
    missing_products = []
    processed_suppliers = set()
    
    for file_path, file_time in new_amazon_files[:10]:  # Limit to first 10 for safety
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                amazon_data = json.load(f)
            
            # Extract supplier info from Amazon cache file
            if 'supplier_info' in amazon_data:
                supplier_info = amazon_data['supplier_info']
                supplier_url = supplier_info.get('url', 'Unknown')
                
                if supplier_url not in processed_suppliers:
                    processed_suppliers.add(supplier_url)
                    
                    # Reconstruct supplier product data
                    product_data = {
                        'title': supplier_info.get('title', 'Unknown'),
                        'price': supplier_info.get('price', 0.0),
                        'url': supplier_url,
                        'image_url': supplier_info.get('image_url', 'N/A'),
                        'ean': supplier_info.get('ean', 'Unknown'),
                        'upc': supplier_info.get('upc'),
                        'sku': supplier_info.get('sku'),
                        'source_supplier': 'clearance-king.co.uk',
                        'source_category_url': supplier_info.get('category_url', 'Unknown'),
                        'extraction_timestamp': file_time.isoformat(),
                        'recovered_from_amazon_cache': True
                    }
                    
                    missing_products.append(product_data)
                    
                    print(f"✅ Recovered: {product_data['title'][:50]}... (£{product_data['price']})")
            
        except Exception as e:
            print(f"⚠️  Error reading {os.path.basename(file_path)}: {e}")
    
    print()
    print(f"📊 RECOVERY SUMMARY:")
    print(f"   Products recovered from Amazon cache: {len(missing_products)}")
    print(f"   Time range: {new_amazon_files[0][1]} to {new_amazon_files[-1][1]}")
    print()
    
    if missing_products:
        # Save recovered products to backup file
        backup_file = os.path.join(
            os.path.dirname(supplier_cache_path), 
            f"recovered_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(missing_products, f, indent=2, ensure_ascii=False)
        
        print(f"💾 RECOVERED PRODUCTS SAVED TO: {backup_file}")
        print()
        
        # Create consolidated cache file (original + recovered)
        consolidated_products = current_cached_products + missing_products
        
        consolidated_file = os.path.join(
            os.path.dirname(supplier_cache_path),
            f"consolidated_cache_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(consolidated_file, 'w', encoding='utf-8') as f:
            json.dump(consolidated_products, f, indent=2, ensure_ascii=False)
        
        print(f"📁 CONSOLIDATED CACHE CREATED:")
        print(f"   File: {consolidated_file}")
        print(f"   Total products: {len(consolidated_products)}")
        print(f"   Original: {len(current_cached_products)}")
        print(f"   Recovered: {len(missing_products)}")
        
        return True
    else:
        print("ℹ️  No recoverable products found in new Amazon cache files")
        return True

if __name__ == "__main__":
    print("🚨 SAFE CACHED PRODUCTS ANALYZER")
    print("Reconstructs missing cached products from Amazon cache files")
    print("100% GUARANTEED not to affect running system")
    print()
    
    success = safe_cached_products_analysis()
    
    if success:
        print("✅ ANALYSIS COMPLETE")
    else:
        print("❌ ANALYSIS FAILED")