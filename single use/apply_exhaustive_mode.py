#!/usr/bin/env python3
"""
Apply Exhaustive Mode Configuration - Process EVERY product under £20 from ALL categories

This script applies the exhaustive mode configuration that:
- Removes ALL artificial limits except £20 price filter
- Processes ALL 276 categories completely
- Extracts EVERY product from EVERY subcategory
- Provides maximum data protection with frequent saves
- Enables live analysis during extraction
"""

import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def backup_current_config():
    """Create timestamped backup of current configuration"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"config/system_config_backup_exhaustive_{timestamp}.json"
    
    if os.path.exists("config/system_config.json"):
        shutil.copy("config/system_config.json", backup_name)
        print(f"✅ Backup created: {backup_name}")
        return backup_name
    else:
        print("⚠️ No existing config found")
        return None

def apply_exhaustive_config():
    """Apply exhaustive mode configuration"""
    try:
        # Read exhaustive mode config
        with open("config/system_config_exhaustive_mode.json", 'r') as f:
            exhaustive_config = json.load(f)
        
        # Write as main config
        with open("config/system_config.json", 'w') as f:
            json.dump(exhaustive_config, f, indent=2)
        
        print("✅ Exhaustive mode configuration applied successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to apply exhaustive config: {e}")
        return False

def validate_exhaustive_config():
    """Validate that exhaustive configuration is correctly applied"""
    try:
        with open("config/system_config.json", 'r') as f:
            config = json.load(f)
        
        # Check key exhaustive settings
        checks = {
            "max_products": config["system"]["max_products"] >= 999999999,
            "max_products_per_category": config["system"]["max_products_per_category"] >= 999999999,
            "max_price_gbp": config["processing_limits"]["max_price_gbp"] == 20.00,
            "min_price_gbp": config["processing_limits"]["min_price_gbp"] == 0.01,
            "cache_enabled": config["supplier_cache_control"]["enabled"] == True,
            "progress_tracking": config["supplier_extraction_progress"]["enabled"] == True,
            "product_resume": config["supplier_extraction_progress"]["recovery_mode"] == "product_resume",
            "chunked_processing": config["hybrid_processing"]["enabled"] == True
        }
        
        print("\\n🔍 CONFIGURATION VALIDATION:")
        all_passed = True
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check}: {passed}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\\n🎯 ALL VALIDATION CHECKS PASSED!")
            return True
        else:
            print("\\n⚠️ Some validation checks failed!")
            return False
            
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

def clear_previous_state():
    """Clear previous processing state for clean exhaustive run"""
    state_files = [
        "OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json",
        "OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json"
    ]
    
    cleared_files = []
    for state_file in state_files:
        if os.path.exists(state_file):
            # Create backup before clearing
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"{state_file}.backup_{timestamp}"
            shutil.copy(state_file, backup_file)
            os.remove(state_file)
            cleared_files.append(state_file)
            print(f"🗑️ Cleared: {state_file} (backup: {backup_file})")
    
    if not cleared_files:
        print("📝 No previous state files found - ready for clean start")
    
    return len(cleared_files)

def display_exhaustive_settings():
    """Display key exhaustive mode settings"""
    try:
        with open("config/system_config.json", 'r') as f:
            config = json.load(f)
        
        print("\\n🚀 EXHAUSTIVE MODE CONFIGURATION SUMMARY:")
        print("=" * 60)
        
        print("\\n📊 PROCESSING LIMITS:")
        print(f"  • Max products: {config['system']['max_products']:,}")
        print(f"  • Max products per category: {config['system']['max_products_per_category']:,}")
        print(f"  • Price range: £{config['processing_limits']['min_price_gbp']:.2f} - £{config['processing_limits']['max_price_gbp']:.2f}")
        print(f"  • Products per cycle: {config['system']['max_products_per_cycle']}")
        
        print("\\n💾 DATA PROTECTION:")
        print(f"  • Cache save frequency: Every {config['supplier_cache_control']['update_frequency_products']} products")
        print(f"  • State save frequency: Every {config['supplier_extraction_progress']['state_persistence']['batch_save_frequency']} products")
        print(f"  • Recovery mode: {config['supplier_extraction_progress']['recovery_mode']}")
        print(f"  • Force cache on interruption: {config['supplier_cache_control']['force_update_on_interruption']}")
        
        print("\\n🔄 PROCESSING STRATEGY:")
        print(f"  • Hybrid processing: {config['hybrid_processing']['enabled']}")
        print(f"  • Chunk size: {config['hybrid_processing']['processing_modes']['chunked']['chunk_size_categories']} categories")
        print(f"  • Switch to Amazon after: {config['hybrid_processing']['switch_to_amazon_after_categories']} categories")
        print(f"  • Batch size: {config['system']['supplier_extraction_batch_size']} categories simultaneously")
        
        print("\\n⚡ PERFORMANCE SETTINGS:")
        print(f"  • Max concurrent requests: {config['performance']['max_concurrent_requests']}")
        print(f"  • Request timeout: {config['performance']['request_timeout_seconds']}s")
        print(f"  • Memory threshold: {config['hybrid_processing']['memory_management']['max_memory_threshold_mb']} MB")
        print(f"  • Cache size limit: {config['cache']['max_size_mb']} MB")
        
        print("\\n🎯 EXPECTED RESULTS:")
        print("  • Categories to process: ALL 276 categories")
        print("  • Estimated products: 15,000 - 100,000+ products")
        print("  • Estimated runtime: 24-72 hours")
        print("  • Max data loss if interrupted: 10 products")
        print("  • Financial reports: Every ~2,500 products")
        
    except Exception as e:
        print(f"❌ Could not display settings: {e}")

def provide_monitoring_commands():
    """Provide monitoring commands for exhaustive run"""
    print("\\n📊 MONITORING COMMANDS FOR EXHAUSTIVE RUN:")
    print("=" * 60)
    
    print("\\n🔍 REAL-TIME MONITORING:")
    print("# Watch extraction progress")
    print("tail -f logs/debug/run_custom_poundwholesale_*.log | grep -E \\"(PERIODIC CACHE SAVE|REAL-TIME.*total|Financial report)\\"")
    
    print("\\n# Monitor current statistics")
    print("watch -n 300 'echo \\"Products: $(cat OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json 2>/dev/null | jq \\".products | length\\" 2>/dev/null || echo 0)\\"; echo \\"Reports: $(ls OUTPUTS/FBA_ANALYSIS/financial_reports/ 2>/dev/null | wc -l)\\"; echo \\"Categories: $(cat OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json 2>/dev/null | jq .supplier_extraction_progress.current_category_index 2>/dev/null || echo 0)/276\\"'")
    
    print("\\n📈 PROGRESS ANALYSIS:")
    print("# Current processing state")
    print("cat OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json | jq .supplier_extraction_progress")
    
    print("\\n# Latest financial analysis")
    print("ls -ltr OUTPUTS/FBA_ANALYSIS/financial_reports/ | tail -3")
    
    print("\\n# Cache file size and product count")
    print("ls -lh OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json")
    print("cat OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json | jq '.products | length'")
    
    print("\\n🚨 INTERRUPTION RECOVERY:")
    print("# If interrupted, simply restart with:")
    print("python run_custom_poundwholesale.py")
    print("# System will automatically resume from last processed product")

def main():
    """Main execution for exhaustive mode setup"""
    print("🚀 EXHAUSTIVE MODE SETUP - Process EVERY Product Under £20")
    print("=" * 70)
    
    # Step 1: Backup current configuration
    backup_file = backup_current_config()
    
    try:
        # Step 2: Apply exhaustive configuration
        if not apply_exhaustive_config():
            print("❌ Failed to apply exhaustive configuration")
            return 1
        
        # Step 3: Validate configuration
        if not validate_exhaustive_config():
            print("⚠️ Configuration validation failed - please check settings")
            return 1
        
        # Step 4: Clear previous state
        cleared_count = clear_previous_state()
        
        # Step 5: Display settings summary
        display_exhaustive_settings()
        
        # Step 6: Provide monitoring guidance
        provide_monitoring_commands()
        
        print("\\n✅ EXHAUSTIVE MODE SETUP COMPLETE!")
        print("\\n🎯 NEXT STEPS:")
        print("1. Review the configuration summary above")
        print("2. Start exhaustive processing: python run_custom_poundwholesale.py")
        print("3. Monitor progress using the provided commands")
        print("4. System will process ALL 276 categories under £20 price limit")
        print("5. Recovery: If interrupted, restart with same command - auto-resumes")
        
        if backup_file:
            print(f"\\n🔄 To restore original config: cp {backup_file} config/system_config.json")
        
        return 0
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        # Restore backup if available
        if backup_file and os.path.exists(backup_file):
            shutil.copy(backup_file, "config/system_config.json")
            print(f"🔄 Restored original configuration from {backup_file}")
        return 1

if __name__ == "__main__":
    exit(main())