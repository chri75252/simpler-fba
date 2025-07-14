#!/usr/bin/env python3
"""
Script to clean up supplier cache by removing products that have already been processed
(i.e., products that exist in the linking map).
"""

import json
import os
import sys
from pathlib import Path

# Add the tools directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_linking_map():
    """Load the linking map to see which products have been processed."""
    # Go up one directory from tools to find OUTPUTS
    linking_map_path = Path("../OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json")
    if linking_map_path.exists():
        with open(linking_map_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def get_processed_identifiers(linking_map):
    """Extract all processed product identifiers from the linking map."""
    processed_identifiers = set()
    for entry in linking_map:
        identifier = entry.get("supplier_product_identifier", "")
        if identifier:
            processed_identifiers.add(identifier)
    return processed_identifiers

def clean_supplier_cache(cache_file_path, processed_identifiers):
    """Remove processed products from supplier cache."""
    if not os.path.exists(cache_file_path):
        print(f"Cache file not found: {cache_file_path}")
        return
    
    # Load current cache
    with open(cache_file_path, 'r', encoding='utf-8') as f:
        cached_products = json.load(f)
    
    print(f"Original cache contains {len(cached_products)} products")
    
    # Filter out processed products
    cleaned_products = []
    removed_count = 0
    
    for product in cached_products:
        # Create identifier for this product (same logic as in workflow)
        supplier_ean = product.get("ean")
        supplier_url = product.get("url")
        
        if supplier_ean:
            product_identifier = f"EAN_{supplier_ean}"
        elif supplier_url:
            product_identifier = f"URL_{supplier_url}"
        else:
            # Keep products without identifiers
            cleaned_products.append(product)
            continue
        
        if product_identifier in processed_identifiers:
            print(f"Removing processed product: {product.get('title', 'Unknown')} ({product_identifier})")
            removed_count += 1
        else:
            cleaned_products.append(product)
    
    print(f"Removed {removed_count} processed products")
    print(f"Cleaned cache contains {len(cleaned_products)} products")
    
    # Create backup of original cache
    backup_path = cache_file_path + ".backup"
    os.rename(cache_file_path, backup_path)
    print(f"Original cache backed up to: {backup_path}")
    
    # Save cleaned cache
    with open(cache_file_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_products, f, indent=2, ensure_ascii=False)
    
    print(f"Cleaned cache saved to: {cache_file_path}")

def main():
    print("=== Supplier Cache Cleanup Tool ===")
    print("This tool removes products from supplier cache that have already been processed.")
    print()
    
    # Load linking map
    print("Loading linking map...")
    linking_map = load_linking_map()
    print(f"Found {len(linking_map)} processed products in linking map")
    
    if not linking_map:
        print("No processed products found in linking map. Nothing to clean.")
        return
    
    # Get processed identifiers
    processed_identifiers = get_processed_identifiers(linking_map)
    print(f"Extracted {len(processed_identifiers)} unique processed identifiers")
    
    # Find and clean supplier cache files
    supplier_cache_dir = Path("../OUTPUTS/FBA_ANALYSIS/supplier_cache")
    if not supplier_cache_dir.exists():
        print(f"Supplier cache directory not found: {supplier_cache_dir}")
        return
    
    cache_files = list(supplier_cache_dir.glob("*_products_cache.json"))
    if not cache_files:
        print("No supplier cache files found")
        return
    
    print(f"Found {len(cache_files)} cache files to process:")
    for cache_file in cache_files:
        print(f"  - {cache_file.name}")
    
    print()
    
    # Process each cache file
    for cache_file in cache_files:
        print(f"Processing: {cache_file.name}")
        clean_supplier_cache(str(cache_file), processed_identifiers)
        print()
    
    print("Cache cleanup completed!")

if __name__ == "__main__":
    main()
