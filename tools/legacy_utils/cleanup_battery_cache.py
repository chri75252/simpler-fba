#!/usr/bin/env python3
"""
Script to clean up battery products from existing cache files.
This will remove all battery products from the cached supplier data.
"""

import os
import json
import re
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Battery filtering patterns - same as in the main workflow
BATTERY_KEYWORDS = [
    "battery", "batteries", "lithium", "alkaline", "rechargeable", 
    "power cell", "coin cell", "button cell", "watch battery", 
    "hearing aid battery", "cordless phone battery", "9v battery",
    "aa battery", "aaa battery", "c battery", "d battery",
    "cr2032", "cr2025", "cr2016", "cr1220", "cr1632", "cr2354",
    "lr44", "lr41", "lr20", "lr14", "lr6", "lr03",
    "ag13", "ag10", "ag4", "ag3", "ag1", "sr626", "sr621",
    "18650", "26650", "14500", "16340", "10440",
    "4lr44", "23a", "27a", "n battery", "aaaa battery"
]

BATTERY_BRAND_CONTEXT = [
    "duracell", "energizer", "panasonic", "rayovac", "eveready",
    "maxell", "renata", "vinnic", "gp", "varta", "sony",
    "toshiba", "philips", "uniross", "extrastar", "infapower",
    "eunicell", "jcb battery", "tesco battery"
]

def is_battery_product(title: str) -> bool:
    """
    Check if a product title indicates it's a battery product that should be filtered out.
    Returns True if the product should be excluded (is a battery product).
    """
    if not title:
        return False
        
    title_lower = title.lower()
    
    # Direct battery keyword check
    for keyword in BATTERY_KEYWORDS:
        if keyword in title_lower:
            return True
    
    # Brand context check - only flag as battery if brand appears with battery context
    for brand in BATTERY_BRAND_CONTEXT:
        if brand in title_lower:
            # Check if there are battery-related terms near the brand
            battery_context_terms = ["battery", "batteries", "cell", "power", "rechargeable", 
                                   "alkaline", "lithium", "volt", "v ", "mah", "amp"]
            for context_term in battery_context_terms:
                if context_term in title_lower:
                    return True
    
    # Voltage pattern check (e.g., "3V", "12V", "1.5V")
    voltage_pattern = r'\b\d+\.?\d*v\b'
    if re.search(voltage_pattern, title_lower) and any(term in title_lower for term in ["battery", "cell", "power"]):
        return True
        
    return False

def cleanup_cache_file(cache_file_path: Path) -> tuple[int, int]:
    """
    Clean up a single cache file, removing battery products.
    Returns (original_count, cleaned_count)
    """
    try:
        with open(cache_file_path, 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        if not isinstance(products, list):
            log.warning(f"Skipping {cache_file_path} - not a list of products")
            return 0, 0
        
        original_count = len(products)
        
        # Filter out battery products
        cleaned_products = []
        battery_products_removed = []
        
        for product in products:
            title = product.get('title', '')
            if is_battery_product(title):
                battery_products_removed.append(title)
                log.debug(f"Removing battery product: {title}")
            else:
                cleaned_products.append(product)
        
        cleaned_count = len(cleaned_products)
        removed_count = original_count - cleaned_count
        
        if removed_count > 0:
            # Create backup of original file
            backup_path = cache_file_path.with_suffix('.bak')
            cache_file_path.rename(backup_path)
            log.info(f"Created backup: {backup_path}")
            
            # Write cleaned products back to original file
            with open(cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned_products, f, indent=2, ensure_ascii=False)
            
            log.info(f"Cleaned {cache_file_path.name}: removed {removed_count} battery products, kept {cleaned_count}")
            
            # Log some examples of removed products
            if battery_products_removed:
                log.info(f"Examples of removed products: {battery_products_removed[:5]}")
        else:
            log.info(f"No battery products found in {cache_file_path.name}")
        
        return original_count, cleaned_count
        
    except Exception as e:
        log.error(f"Error processing {cache_file_path}: {e}")
        return 0, 0

def main():
    """Main function to clean up all cache files."""
    # Define cache directories
    cache_dirs = [
        r"C:\Users\chris\Amazon-FBA-Agent-System\OUTPUTS\FBA_ANALYSIS\cache",
        r"C:\Users\chris\Amazon-FBA-Agent-System\OUTPUTS\FBA_ANALYSIS\supplier_cache"
    ]
    
    total_original = 0
    total_cleaned = 0
    files_processed = 0
    
    for cache_dir in cache_dirs:
        cache_path = Path(cache_dir)
        if not cache_path.exists():
            log.warning(f"Cache directory does not exist: {cache_dir}")
            continue
        
        log.info(f"Processing cache directory: {cache_dir}")
        
        # Find all JSON cache files
        cache_files = list(cache_path.glob("*_products_cache.json"))
        
        if not cache_files:
            log.info(f"No cache files found in {cache_dir}")
            continue
        
        for cache_file in cache_files:
            log.info(f"Processing cache file: {cache_file.name}")
            original, cleaned = cleanup_cache_file(cache_file)
            total_original += original
            total_cleaned += cleaned
            files_processed += 1
    
    removed_total = total_original - total_cleaned
    log.info(f"\nCLEANUP SUMMARY:")
    log.info(f"Files processed: {files_processed}")
    log.info(f"Total products before cleanup: {total_original}")
    log.info(f"Total products after cleanup: {total_cleaned}")
    log.info(f"Total battery products removed: {removed_total}")
    
    if removed_total > 0:
        log.info(f"Battery products successfully filtered from cache files!")
        log.info(f"Backup files created with .bak extension")
    else:
        log.info("No battery products found in cache files")

if __name__ == "__main__":
    main()
