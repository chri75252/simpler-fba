#!/usr/bin/env python3

import json
import os
from datetime import datetime

print("🔍 FINDING MISSING SUPPLIER PRODUCTS")
print("=" * 60)
print(f"Timestamp: {datetime.now()}")
print("Extracting supplier EANs from linking map and comparing with cached products...")

# Paths
linking_map_path = "/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json"
cached_products_path = "/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/OUTPUTS/cached_products/clearance-king_co_uk_products_cache.json"

# Load linking map and extract supplier EANs
print("\n📊 LOADING LINKING MAP...")
with open(linking_map_path, 'r', encoding='utf-8') as f:
    linking_map = json.load(f)

linking_map_eans = set()
for entry in linking_map:
    supplier_id = entry.get('supplier_product_identifier', '')
    if supplier_id.startswith('EAN_'):
        ean = supplier_id.replace('EAN_', '')
        linking_map_eans.add(ean)

print(f"   Supplier EANs in linking map: {len(linking_map_eans)}")

# Load cached products and extract supplier EANs
print("\n📦 LOADING CACHED PRODUCTS...")
with open(cached_products_path, 'r', encoding='utf-8') as f:
    cached_products = json.load(f)

cached_eans = set()
for product in cached_products:
    ean = product.get('ean')
    if ean:
        cached_eans.add(ean)

print(f"   Supplier EANs in cache: {len(cached_eans)}")

# Find missing EANs
missing_eans = linking_map_eans - cached_eans
extra_eans = cached_eans - linking_map_eans

print(f"\n🔍 ANALYSIS RESULTS:")
print(f"   EANs in linking map: {len(linking_map_eans)}")
print(f"   EANs in cached products: {len(cached_eans)}")
print(f"   Missing from cache: {len(missing_eans)}")
print(f"   Extra in cache (not in linking map): {len(extra_eans)}")

if missing_eans:
    print(f"\n⚠️  MISSING SUPPLIER EANs FROM CACHE:")
    for i, ean in enumerate(sorted(missing_eans), 1):
        print(f"   {i:3d}. {ean}")
        
    # Find these EANs in linking map to get more details
    print(f"\n📋 MISSING PRODUCTS DETAILS:")
    missing_products = []
    for entry in linking_map:
        supplier_id = entry.get('supplier_product_identifier', '')
        if supplier_id.startswith('EAN_'):
            ean = supplier_id.replace('EAN_', '')
            if ean in missing_eans:
                missing_products.append({
                    'ean': ean,
                    'title': entry.get('supplier_title_snippet', ''),
                    'amazon_asin': entry.get('chosen_amazon_asin', ''),
                    'match_method': entry.get('match_method', '')
                })
    
    # Save missing products
    output_file = f"/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/OUTPUTS/cached_products/missing_supplier_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(missing_products, f, indent=2, ensure_ascii=False)
    
    print(f"   💾 Missing products saved to: {output_file}")
    
    for product in missing_products[:10]:  # Show first 10
        print(f"   EAN: {product['ean']} | {product['title'][:50]}...")

if extra_eans:
    print(f"\n➕ EXTRA EANs IN CACHE (not in linking map): {len(extra_eans)}")
    for i, ean in enumerate(sorted(list(extra_eans)[:10]), 1):  # Show first 10
        print(f"   {i:3d}. {ean}")

print(f"\n✅ ANALYSIS COMPLETE")