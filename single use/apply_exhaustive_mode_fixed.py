#!/usr/bin/env python3
"""
Apply Exhaustive Mode Configuration - Process EVERY product under £20 from ALL categories
"""

import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path

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
            "cache_enabled": config["supplier_cache_control"]["enabled"] == True,
            "product_resume": config["supplier_extraction_progress"]["recovery_mode"] == "product_resume"
        }
        
        print("\\n🔍 CONFIGURATION VALIDATION:")
        all_passed = True
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check}: {passed}")
            if not passed:
                all_passed = False
        
        return all_passed
            
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

def display_exhaustive_settings():
    """Display key exhaustive mode settings"""
    try:
        with open("config/system_config.json", 'r') as f:
            config = json.load(f)
        
        print("\\n🚀 EXHAUSTIVE MODE CONFIGURATION:")
        print("=" * 50)
        
        print("\\n📊 LIMITS REMOVED:")
        print(f"  • Max products: {config['system']['max_products']:,}")
        print(f"  • Max per category: {config['system']['max_products_per_category']:,}")
        print(f"  • Only filter: £{config['processing_limits']['min_price_gbp']:.2f} - £{config['processing_limits']['max_price_gbp']:.2f}")
        
        print("\\n💾 DATA PROTECTION:")
        print(f"  • Cache saves: Every {config['supplier_cache_control']['update_frequency_products']} products")
        print(f"  • Recovery mode: {config['supplier_extraction_progress']['recovery_mode']}")
        
        print("\\n🎯 EXPECTED RESULTS:")
        print("  • Categories: ALL 276 categories")
        print("  • Products: 15,000 - 100,000+ products")
        print("  • Runtime: 24-72 hours")
        print("  • Max data loss: 10 products")
        
    except Exception as e:
        print(f"❌ Could not display settings: {e}")

def main():
    """Main execution for exhaustive mode setup"""
    print("🚀 EXHAUSTIVE MODE SETUP")
    print("=" * 40)
    
    # Apply configuration
    backup_file = backup_current_config()
    
    if not apply_exhaustive_config():
        return 1
    
    if not validate_exhaustive_config():
        return 1
    
    display_exhaustive_settings()
    
    print("\\n✅ EXHAUSTIVE MODE READY!")
    print("\\nStart with: python run_custom_poundwholesale.py")
    
    return 0

if __name__ == "__main__":
    exit(main())