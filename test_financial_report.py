#!/usr/bin/env python3
"""
Test to manually create a financial report file.
"""

import json
import os
from pathlib import Path
from datetime import datetime

# Create test financial data
test_financial_data = [
    {
        "supplier_product": "Home & Garden Stove Polish Fireplace Restorer 200ml",
        "supplier_price": 0.79,
        "amazon_asin": "B0DCNDW6K9",
        "amazon_price": 4.99,
        "profit_margin": 3.20,
        "is_profitable": True,
        "roi_percentage": 305.1
    },
    {
        "supplier_product": "Home & Garden Multi-Purpose White Vinegar Cleaning Spray 500ml", 
        "supplier_price": 0.84,
        "amazon_asin": "B0BRHD3K23",
        "amazon_price": 6.99,
        "profit_margin": 4.15,
        "is_profitable": True,
        "roi_percentage": 394.0
    }
]

# Create the output path
output_dir = Path("/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/OUTPUTS/FBA_ANALYSIS/financial_reports/poundwholesale-co-uk")
output_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
report_file = output_dir / f"fba_financial_report_{timestamp}.json"

print(f"🧪 MANUAL TEST: Creating financial report file")
print(f"📂 Target file: {report_file}")
print(f"📋 Test data: {len(test_financial_data)} profitable products")

try:
    # Save the test data
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            "report_timestamp": timestamp,
            "supplier": "poundwholesale.co.uk",
            "total_profitable_products": len(test_financial_data),
            "profitable_products": test_financial_data
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Successfully created financial report file!")
    print(f"📊 File size: {report_file.stat().st_size} bytes")
    
    # Verify content
    with open(report_file, 'r', encoding='utf-8') as f:
        saved_data = json.load(f)
    
    print(f"✅ Verified saved content: {saved_data['total_profitable_products']} profitable products")
    print(f"📈 Report details:")
    for i, product in enumerate(saved_data['profitable_products'], 1):
        print(f"   {i}. {product['supplier_product']} - Profit: £{product['profit_margin']}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()