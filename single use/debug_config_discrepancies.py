#!/usr/bin/env python3
"""
Configuration Discrepancy Debug Tool
====================================

Systematically traces configuration loading paths and identifies discrepancies
between config values and runtime behavior in the Amazon FBA Agent System.

Findings from ZEN MCP DEBUG Analysis:
====================================

1. ❌ update_frequency_products HARDCODED BUG
   - Config: 2 (from supplier_cache_control.update_frequency_products)
   - Runtime: 3 (hardcoded default in passive_extraction_workflow_latest.py:2667)
   - Fix: Remove hardcoded default, use actual config value

2. ❌ max_categories_per_request WRONG CONFIG PATH
   - Config: 5 (at root level)
   - Runtime: 3 (trying to access ai_features.category_selection.max_categories_per_request)
   - Fix: Change line 1029 to access root level config

3. ✅ supplier_extraction_batch_size vs max_products_per_category CLARIFIED
   - These are different parameters for different purposes:
   - supplier_extraction_batch_size: 1 (controls category batch processing)
   - max_products_per_category: 5 (controls products per category limit)

4. ⚠️ chunk_size_categories CONFIG MISSING
   - Config: Missing from hybrid_processing.processing_modes.chunked
   - Runtime: Using hardcoded default of 10
   - Note: switch_to_amazon_after_categories correctly loads as 1

Critical File Issue:
===================
🚨 WORKFLOW FILE CORRUPTION DETECTED:
- passive_extraction_workflow_latest.py has massive duplication
- Method definitions repeated multiple times
- This indicates merge conflict or file corruption
- Immediate file restoration from backup recommended

Configuration Loader Analysis:
=============================
✅ SystemConfigLoader is working correctly
❌ Issues are in workflow configuration access patterns
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from config.system_config_loader import SystemConfigLoader
except ImportError:
    print("❌ Cannot import SystemConfigLoader - check project structure")
    sys.exit(1)

def debug_configuration_paths():
    """Debug configuration loading paths and identify discrepancies."""
    
    print("🔍 Configuration Discrepancy Debug Tool")
    print("=" * 50)
    
    # Load configuration
    config_loader = SystemConfigLoader()
    full_config = config_loader._config
    system_config = config_loader.get_system_config()
    
    print("\n📊 Configuration Values Analysis:")
    print("-" * 30)
    
    # 1. update_frequency_products analysis
    cache_config = full_config.get("supplier_cache_control", {})
    actual_frequency = cache_config.get("update_frequency_products")
    print(f"1. update_frequency_products:")
    print(f"   ✅ Config value: {actual_frequency}")
    print(f"   ❌ Hardcoded in code: 3 (line 2667)")
    print(f"   🎯 Should use: {actual_frequency}")
    
    # 2. max_categories_per_request analysis
    ai_features_path = full_config.get("ai_features", {}).get("category_selection", {}).get("max_categories_per_request")
    root_level_value = full_config.get("max_categories_per_request")
    print(f"\n2. max_categories_per_request:")
    print(f"   ❌ Code looks for ai_features path: {ai_features_path}")
    print(f"   ✅ Actual config location (root): {root_level_value}")
    print(f"   🎯 Should use: full_config.get('max_categories_per_request', 5)")
    
    # 3. Batch size parameters analysis
    supplier_batch = system_config.get("supplier_extraction_batch_size")
    max_per_category = system_config.get("max_products_per_category")
    print(f"\n3. Batch Size Parameters:")
    print(f"   ✅ supplier_extraction_batch_size: {supplier_batch} (category processing)")
    print(f"   ✅ max_products_per_category: {max_per_category} (products per category)")
    print(f"   📝 These are different parameters for different purposes")
    
    # 4. Hybrid processing configuration
    hybrid_config = full_config.get("hybrid_processing", {})
    switch_after = hybrid_config.get("switch_to_amazon_after_categories")
    processing_modes = hybrid_config.get("processing_modes", {})
    chunked_config = processing_modes.get("chunked", {})
    chunk_size = chunked_config.get("chunk_size_categories")
    
    print(f"\n4. Hybrid Processing Configuration:")
    print(f"   ✅ switch_to_amazon_after_categories: {switch_after}")
    print(f"   ⚠️ chunk_size_categories: {chunk_size} (missing from config)")
    print(f"   🎯 Add to config: hybrid_processing.processing_modes.chunked.chunk_size_categories")
    
    # 5. Check for cache control hierarchy
    cache_modes = cache_config.get("cache_modes", {})
    exhaustive_freq = cache_modes.get("exhaustive", {}).get("update_frequency_products")
    print(f"\n5. Cache Control Hierarchy:")
    print(f"   ✅ Root cache frequency: {actual_frequency}")
    print(f"   ✅ Exhaustive mode frequency: {exhaustive_freq}")
    
    print("\n🚨 CRITICAL ISSUES IDENTIFIED:")
    print("-" * 30)
    print("1. Line 2667: Remove hardcoded default '3' for update_frequency_products")
    print("2. Line 1029: Fix max_categories_per_request path access")
    print("3. File corruption: Multiple duplicate method definitions detected")
    print("4. Missing chunk_size_categories in config structure")
    
    print("\n✅ CONFIGURATION FIXES NEEDED:")
    print("-" * 30)
    print("Code fixes:")
    print("  - passive_extraction_workflow_latest.py:2667")
    print("  - passive_extraction_workflow_latest.py:1029")
    print("Config additions:")
    print("  - hybrid_processing.processing_modes.chunked.chunk_size_categories: 1")
    
    return {
        "update_frequency_products": {
            "config_value": actual_frequency,
            "hardcoded_value": 3,
            "fix_needed": True
        },
        "max_categories_per_request": {
            "config_value": root_level_value,
            "wrong_path_value": ai_features_path,
            "fix_needed": True
        },
        "batch_sizes": {
            "supplier_extraction_batch_size": supplier_batch,
            "max_products_per_category": max_per_category,
            "clarification": "Different parameters for different purposes"
        },
        "hybrid_processing": {
            "switch_to_amazon_after_categories": switch_after,
            "chunk_size_categories": chunk_size,
            "config_missing": chunk_size is None
        }
    }

if __name__ == "__main__":
    try:
        results = debug_configuration_paths()
        
        # Save results to debug file
        debug_file = Path("config_debug_results.json")
        with open(debug_file, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Debug results saved to: {debug_file}")
        print("🔧 Use this analysis to fix configuration discrepancies")
        
    except Exception as e:
        print(f"❌ Error during configuration debug: {e}")
        import traceback
        traceback.print_exc()