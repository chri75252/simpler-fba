#!/usr/bin/env python3
"""
Simple test to manually create a linking map file and verify save functionality.
"""

import json
import os
from pathlib import Path

# Define test data
test_linking_map = {
    "5055319510417": "B0DCNDW6K9",
    "5055319510769": "B0BRHD3K23", 
    "test_ean_123": "test_asin_456"
}

# Create the output path
output_dir = Path("/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/OUTPUTS/FBA_ANALYSIS/linking_maps/poundwholesale_co_uk")
output_dir.mkdir(parents=True, exist_ok=True)

linking_map_file = output_dir / "linking_map.json"

print(f"🧪 MANUAL TEST: Creating linking map file")
print(f"📂 Target file: {linking_map_file}")
print(f"📋 Test data: {test_linking_map}")

try:
    # Save the test data
    with open(linking_map_file, 'w', encoding='utf-8') as f:
        json.dump(test_linking_map, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Successfully created linking map file!")
    print(f"📊 File size: {linking_map_file.stat().st_size} bytes")
    
    # Verify content
    with open(linking_map_file, 'r', encoding='utf-8') as f:
        saved_data = json.load(f)
    
    print(f"✅ Verified saved content: {saved_data}")
    
    if saved_data == test_linking_map:
        print("✅ Content matches perfectly!")
    else:
        print("❌ Content mismatch!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()