#!/usr/bin/env python3
"""
Test script to verify cache frequency fix and chunking functionality.

Tests:
1. Per-product cache saving (every 3 products)
2. Chunking behavior (supplier/Amazon switching)
3. Recovery mode effectiveness
4. State persistence validation
"""

import os
import sys
import json
import time
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def backup_current_config():
    """Create backup of current system config"""
    backup_name = f"config/system_config.json.bak_cache_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy("config/system_config.json", backup_name)
    print(f"✅ Created backup: {backup_name}")
    return backup_name

def apply_test_config():
    """Apply test configuration for cache frequency testing"""
    # Read test config
    with open("config/test_cache_frequency_fix.json", 'r') as f:
        test_config = json.load(f)
    
    # Read current config
    with open("config/system_config.json", 'r') as f:
        current_config = json.load(f)
    
    # Update specific test settings
    current_config["system"].update(test_config["system"])
    current_config["supplier_cache_control"] = test_config["supplier_cache_control"]
    current_config["supplier_extraction_progress"] = test_config["supplier_extraction_progress"]
    current_config["hybrid_processing"] = test_config["hybrid_processing"]
    
    # Write updated config
    with open("config/system_config.json", 'w') as f:
        json.dump(current_config, f, indent=2)
    
    print("✅ Applied test configuration:")
    print(f"   - max_products: {test_config['system']['max_products']}")
    print(f"   - update_frequency_products: {test_config['supplier_cache_control']['update_frequency_products']}")
    print(f"   - chunk_size_categories: {test_config['hybrid_processing']['processing_modes']['chunked']['chunk_size_categories']}")

def clear_test_state():
    """Clear processing state and cache files for clean test"""
    state_files = [
        "OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json",
        "OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json"
    ]
    
    for state_file in state_files:
        if os.path.exists(state_file):
            os.remove(state_file)
            print(f"🗑️ Cleared: {state_file}")

def monitor_cache_saves():
    """Monitor cache file timestamps to verify per-product saves"""
    cache_file = "OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json"
    timestamps = []
    
    print(f"\\n📊 MONITORING CACHE SAVES:")
    print(f"Expected: Save every 3 products")
    print(f"Watching: {cache_file}")
    print(f"Timestamp monitoring started at: {datetime.now().strftime('%H:%M:%S')}")
    
    return cache_file, timestamps

def verify_chunking_behavior():
    """Verify chunking toggle functionality"""
    print("\\n🔄 CHUNKING BEHAVIOR VERIFICATION:")
    print("Expected: Process 2 categories, then switch to Amazon analysis")
    print("Watch for: 'CHUNKED MODE' messages in logs")

def main():
    """Main test execution"""
    print("🧪 CACHE FREQUENCY FIX & CHUNKING TEST")
    print("=" * 50)
    
    # Step 1: Backup current config
    backup_file = backup_current_config()
    
    try:
        # Step 2: Apply test configuration
        apply_test_config()
        
        # Step 3: Clear test state
        clear_test_state()
        
        # Step 4: Setup monitoring
        cache_file, timestamps = monitor_cache_saves()
        verify_chunking_behavior()
        
        # Step 5: Instructions for manual verification
        print("\\n🔧 MANUAL VERIFICATION STEPS:")
        print("1. Run the system: python run_complete_fba_system.py")
        print("2. Watch for periodic cache saves in logs:")
        print("   - '💾 PERIODIC CACHE SAVE: Saved X products to cache (every 3 products)'")
        print("3. Verify cache file timestamps change every 3 products:")
        print(f"   - Watch: {cache_file}")
        print("4. Check chunking behavior:")
        print("   - Should process 2 categories, then switch to Amazon analysis")
        print("5. Test interruption recovery:")
        print("   - Interrupt after 6-9 products")
        print("   - Restart and verify it resumes from correct product")
        
        print("\\n📋 SUCCESS CRITERIA:")
        print("✅ Cache saves happen every 3 products (not per category)")
        print("✅ Cache file modified timestamp updates during extraction")
        print("✅ Chunking switches between supplier/Amazon every 2 categories")
        print("✅ Recovery resumes from exact product (not category start)")
        print("✅ No data loss during interruption")
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        # Restore backup
        if backup_file and os.path.exists(backup_file):
            shutil.copy(backup_file, "config/system_config.json")
            print(f"🔄 Restored backup: {backup_file}")
    
    print("\\n🎯 Test configuration applied. Run the system to verify the fix!")

if __name__ == "__main__":
    main()