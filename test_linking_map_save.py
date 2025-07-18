#!/usr/bin/env python3
"""
Test script to verify linking map save operations work correctly.
This will manually create linking map entries and test the save functionality.
"""

import sys
import os
import json
from pathlib import Path

# Add the project directory to Python path
sys.path.insert(0, '/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32')

# Import required modules
from tools.passive_extraction_workflow_latest import PassiveExtractionWorkflow
from utils.path_manager import get_linking_map_path

def test_linking_map_save():
    """Test that linking map save operations work correctly."""
    print("🧪 TESTING: Linking map save functionality")
    
    # Create a workflow instance
    workflow = PassiveExtractionWorkflow()
    
    # Manually add test entries to linking map
    test_entries = {
        "5055319510417": "B0DCNDW6K9",  # Known working combination from logs
        "5055319510769": "B0BRHD3K23",  # Another test entry
        "test_ean_123": "test_asin_456"  # Additional test entry
    }
    
    print(f"📋 Adding {len(test_entries)} test entries to linking map")
    workflow.linking_map = test_entries
    
    # Test the save operation
    supplier_name = "poundwholesale.co.uk"
    
    print(f"💾 Testing _save_linking_map for supplier: {supplier_name}")
    print(f"🔍 Linking map content: {workflow.linking_map}")
    
    try:
        # Call the save method
        workflow._save_linking_map(supplier_name)
        print("✅ Save operation completed without errors")
        
        # Verify the file was created
        linking_map_path = get_linking_map_path(supplier_name)
        print(f"📂 Expected file path: {linking_map_path}")
        
        if linking_map_path.exists():
            print("✅ Linking map file was created successfully!")
            
            # Read and verify content
            with open(linking_map_path, 'r') as f:
                saved_content = json.load(f)
            
            print(f"📖 Saved content: {saved_content}")
            
            # Verify all entries were saved
            for ean, asin in test_entries.items():
                if ean in saved_content and saved_content[ean] == asin:
                    print(f"✅ Entry verified: {ean} -> {asin}")
                else:
                    print(f"❌ Entry missing or incorrect: {ean} -> {asin}")
            
            print(f"📊 File size: {linking_map_path.stat().st_size} bytes")
            print(f"📅 File modified: {linking_map_path.stat().st_mtime}")
            
        else:
            print(f"❌ Linking map file was NOT created at: {linking_map_path}")
            
    except Exception as e:
        print(f"❌ Error during save operation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_linking_map_save()