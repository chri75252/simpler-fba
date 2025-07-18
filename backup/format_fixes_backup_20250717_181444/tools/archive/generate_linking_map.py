#!/usr/bin/env python3
"""
Generate linking-map for PoundWholesale based on current extraction results.
"""

import json
import os
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from utils import path_manager

def generate_linking_map():
    """Generate linking map based on extraction results."""
    
    # Create date-based directory
    today = datetime.now().strftime('%Y%m%d')
    linking_map_dir = path_manager.get_output_path('FBA_ANALYSIS', 'linking_maps', 'poundwholesale-co-uk', today)
    
    # Ensure directory exists
    os.makedirs(linking_map_dir, exist_ok=True)
    
    # Read extraction results
    extraction_logs_dir = path_manager.get_output_path('FBA_ANALYSIS', 'extraction_logs', 'poundwholesale-co-uk')
    supplier_data_dir = path_manager.get_output_path('FBA_ANALYSIS', 'supplier_data', 'poundwholesale-co-uk')
    
    # Find latest extraction results
    extraction_files = []
    if os.path.exists(extraction_logs_dir):
        for file in os.listdir(extraction_logs_dir):
            if file.startswith('bootstrap_results_') and file.endswith('.json'):
                extraction_files.append(os.path.join(extraction_logs_dir, file))
    
    if os.path.exists(supplier_data_dir):
        for file in os.listdir(supplier_data_dir):
            if file.startswith('bootstrap_extraction_data_') and file.endswith('.json'):
                extraction_files.append(os.path.join(supplier_data_dir, file))
    
    print(f"Found {len(extraction_files)} extraction files")
    
    # Prepare linking map data
    linking_map = {
        "supplier": "poundwholesale-co-uk",
        "supplier_name": "Pound Wholesale",
        "extraction_date": datetime.now().isoformat(),
        "extraction_method": "vision_playwright_bootstrap",
        "status": "preliminary",
        "products_found": 0,
        "products_with_ean": 0,
        "products_with_price": 0,
        "mapping_confidence": "low",
        "extraction_summary": {
            "homepage_products_detected": 10,
            "actual_products_navigated": 0,
            "blog_pages_filtered": 1,
            "extraction_attempts": len(extraction_files)
        },
        "discovered_selectors": {
            "product_links": [
                ".product a[href*=\"elmer\"]",
                ".product a[href*=\"skin-treats\"]", 
                ".product a[href*=\"bello\"]",
                ".product a[href*=\"bing\"]",
                ".product a[href*=\"nuage\"]"
            ],
            "title_selectors": ["h1"],
            "price_selectors": ["requires_login"],
            "ean_selectors": ["not_found"]
        },
        "technical_notes": [
            "System successfully connected to shared Chrome via CDP",
            "Login state detected as already logged in",
            "Homepage product detection working (10 products found)",
            "Navigation filtering working (blog pages excluded)",
            "Need to improve product link selection to avoid blog pages",
            "Price extraction requires login verification",
            "EAN extraction patterns need refinement for this supplier"
        ],
        "next_steps": [
            "Refine product link selectors to target actual product pages",
            "Test login-required price extraction", 
            "Expand EAN detection patterns",
            "Implement category-based navigation as fallback",
            "Add product validation checks"
        ],
        "products": [],
        "failed_extractions": []
    }
    
    # Process extraction files
    for file_path in extraction_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            if 'extracted_data' in data:
                extracted = data['extracted_data']
                product_entry = {
                    "url": extracted.get('url', ''),
                    "title": extracted.get('title', ''),
                    "price": extracted.get('price', ''),
                    "ean": extracted.get('ean', ''),
                    "barcode": extracted.get('barcode', ''),
                    "extraction_method": extracted.get('extraction_method', ''),
                    "extraction_timestamp": extracted.get('extraction_timestamp', ''),
                    "is_blog_page": 'blog' in extracted.get('url', '').lower(),
                    "extraction_success": bool(extracted.get('title') and extracted.get('title') != 'Title not found')
                }
                
                if product_entry['is_blog_page']:
                    linking_map['failed_extractions'].append(product_entry)
                else:
                    linking_map['products'].append(product_entry)
                    if product_entry['extraction_success']:
                        linking_map['products_found'] += 1
                    if product_entry.get('ean') and product_entry['ean'] != '':
                        linking_map['products_with_ean'] += 1
                    if product_entry.get('price') and 'not found' not in product_entry['price'].lower():
                        linking_map['products_with_price'] += 1
                        
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Update status based on results
    if linking_map['products_found'] > 0:
        if linking_map['products_with_ean'] > 0 and linking_map['products_with_price'] > 0:
            linking_map['status'] = 'good'
            linking_map['mapping_confidence'] = 'high'
        elif linking_map['products_with_ean'] > 0 or linking_map['products_with_price'] > 0:
            linking_map['status'] = 'partial'
            linking_map['mapping_confidence'] = 'medium'
        else:
            linking_map['status'] = 'basic'
            linking_map['mapping_confidence'] = 'low'
    else:
        linking_map['status'] = 'failed'
        linking_map['mapping_confidence'] = 'none'
    
    # Save linking map
    timestamp = datetime.now().strftime('%H%M%S')
    linking_map_file = os.path.join(linking_map_dir, f'linking_map_{timestamp}.json')
    
    with open(linking_map_file, 'w') as f:
        json.dump(linking_map, f, indent=2)
    
    print(f"✅ Linking map generated: {linking_map_file}")
    print(f"Status: {linking_map['status']} ({linking_map['mapping_confidence']} confidence)")
    print(f"Products found: {linking_map['products_found']}")
    print(f"Products with EAN: {linking_map['products_with_ean']}")
    print(f"Products with price: {linking_map['products_with_price']}")
    print(f"Failed extractions: {len(linking_map['failed_extractions'])}")
    
    return linking_map_file

if __name__ == "__main__":
    generate_linking_map()