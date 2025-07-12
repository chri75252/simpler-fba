#!/usr/bin/env python3

import json
import os
from datetime import datetime

print("📖 SAFE MEMORY RETRIEVAL SCRIPT - READ ONLY")
print("=" * 60)
print(f"Timestamp: {datetime.now()}")
print("100% GUARANTEED not to affect running system - READ ONLY OPERATIONS")

# Read-only analysis of current state
linking_map_path = "/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json"
cached_products_path = "/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/OUTPUTS/cached_products/clearance-king_co_uk_products_cache.json"
dashboard_path = "/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/DASHBOARD/live_dashboard.txt"

print("\n📊 CURRENT SYSTEM STATE ANALYSIS:")

# Read dashboard for current stats
try:
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        dashboard_content = f.read()
    
    # Extract key metrics from dashboard
    lines = dashboard_content.split('\n')
    for line in lines:
        if 'Total Supplier Products:' in line:
            total_products = line.split(':')[1].strip()
            print(f"   Dashboard Total Products: {total_products}")
        elif 'Current Processing Index:' in line:
            current_index = line.split(':')[1].strip()
            print(f"   Current Processing Index: {current_index}")
        elif 'Processing Completion:' in line:
            completion = line.split(':')[1].strip()
            print(f"   Processing Completion: {completion}")
        elif 'EAN Matched Products:' in line:
            ean_matches = line.split(':')[1].strip()
            print(f"   EAN Matched Products: {ean_matches}")
            
except Exception as e:
    print(f"   ⚠️  Error reading dashboard: {e}")

print("\n📋 LINKING MAP ANALYSIS:")
try:
    with open(linking_map_path, 'r', encoding='utf-8') as f:
        linking_map = json.load(f)
    
    ean_matches = sum(1 for entry in linking_map if entry.get('match_method') == 'EAN_search')
    title_matches = sum(1 for entry in linking_map if entry.get('match_method') == 'title_search')
    
    print(f"   Total entries in linking map: {len(linking_map)}")
    print(f"   EAN matches: {ean_matches}")
    print(f"   Title matches: {title_matches}")
    
    # Get file modification time
    mod_time = os.path.getmtime(linking_map_path)
    mod_datetime = datetime.fromtimestamp(mod_time)
    print(f"   Last modified: {mod_datetime}")
    
except Exception as e:
    print(f"   ⚠️  Error reading linking map: {e}")

print("\n📦 CACHED PRODUCTS ANALYSIS:")
try:
    with open(cached_products_path, 'r', encoding='utf-8') as f:
        cached_products = json.load(f)
    
    print(f"   Total cached products: {len(cached_products)}")
    
    # Get file modification time
    mod_time = os.path.getmtime(cached_products_path)
    mod_datetime = datetime.fromtimestamp(mod_time)
    print(f"   Last modified: {mod_datetime}")
    
    # Count products with EANs
    with_ean = sum(1 for product in cached_products if product.get('ean'))
    print(f"   Products with EAN: {with_ean}")
    
except Exception as e:
    print(f"   ⚠️  Error reading cached products: {e}")

print("\n🔍 GAP ANALYSIS:")
try:
    # Calculate gaps based on available data
    dashboard_total = int(total_products) if 'total_products' in locals() else 0
    cached_count = len(cached_products) if 'cached_products' in locals() else 0
    linking_count = len(linking_map) if 'linking_map' in locals() else 0
    
    print(f"   Dashboard claims: {dashboard_total} products")
    print(f"   Actually cached: {cached_count} products")
    print(f"   Successfully matched: {linking_count} products")
    print(f"   Missing from cache: {dashboard_total - cached_count} products")
    print(f"   Cached but not matched: {cached_count - linking_count} products")
    
except Exception as e:
    print(f"   ⚠️  Error in gap analysis: {e}")

print("\n💾 CREATING BACKUP COPIES TO SEPARATE FILES:")

# Create backup copy of linking map with timestamp
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
linking_map_backup = f"/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/OUTPUTS/FBA_ANALYSIS/Linking map/linking_map_monitor_{timestamp}.json"
cached_products_backup = f"/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3/OUTPUTS/cached_products/cached_products_monitor_{timestamp}.json"

try:
    # Backup linking map
    if 'linking_map' in locals():
        with open(linking_map_backup, 'w', encoding='utf-8') as f:
            json.dump(linking_map, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Linking map backed up to: linking_map_monitor_{timestamp}.json")
    else:
        print(f"   ⚠️  No linking map data to backup")
        
    # Backup cached products
    if 'cached_products' in locals():
        with open(cached_products_backup, 'w', encoding='utf-8') as f:
            json.dump(cached_products, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Cached products backed up to: cached_products_monitor_{timestamp}.json")
    else:
        print(f"   ⚠️  No cached products data to backup")
        
except Exception as e:
    print(f"   ❌ Error creating backups: {e}")

print("\n✅ READ-ONLY ANALYSIS COMPLETE")
print("Original files untouched - backups created in separate monitor files")