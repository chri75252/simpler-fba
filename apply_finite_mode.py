#!/usr/bin/env python3
"""
Apply Finite Mode Configuration Script
=====================================

This script applies the finite mode configuration to enable processing of ALL products
from ALL categories without artificial limits, while maintaining recovery capabilities.

Usage:
    python apply_finite_mode.py [--backup] [--verify]

Options:
    --backup    Create backup of current config before applying changes
    --verify    Verify configuration after applying changes
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

def backup_current_config():
    """Create backup of current system_config.json"""
    current_config = Path("config/system_config.json")
    if current_config.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = Path(f"config/system_config_backup_{timestamp}.json")
        shutil.copy2(current_config, backup_path)
        print(f"✅ Backed up current config to: {backup_path}")
        return backup_path
    return None

def apply_finite_mode_config():
    """Apply finite mode configuration"""
    finite_config_path = Path("config/system_config_finite_mode.json")
    current_config_path = Path("config/system_config.json")
    
    if not finite_config_path.exists():
        print(f"❌ ERROR: Finite mode config not found: {finite_config_path}")
        return False
    
    try:
        # Load finite mode config
        with open(finite_config_path, 'r', encoding='utf-8') as f:
            finite_config = json.load(f)
        
        # Apply finite mode config
        with open(current_config_path, 'w', encoding='utf-8') as f:
            json.dump(finite_config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Applied finite mode configuration to: {current_config_path}")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Failed to apply finite mode config: {e}")
        return False

def verify_configuration():
    """Verify finite mode configuration is applied correctly"""
    config_path = Path("config/system_config.json")
    
    if not config_path.exists():
        print(f"❌ ERROR: Configuration file not found: {config_path}")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Check key finite mode settings
        system_config = config.get("system", {})
        processing_limits = config.get("processing_limits", {})
        
        checks = [
            ("system.max_products", system_config.get("max_products"), 100000),
            ("system.max_analyzed_products", system_config.get("max_analyzed_products"), 100000),
            ("system.max_products_per_category", system_config.get("max_products_per_category"), 10000),
            ("processing_limits.max_products_per_category", processing_limits.get("max_products_per_category"), 10000),
            ("processing_limits.max_price_gbp", processing_limits.get("max_price_gbp"), 10000.00),
            ("processing_limits.min_price_gbp", processing_limits.get("min_price_gbp"), 0.01),
        ]
        
        print("🔍 VERIFICATION RESULTS:")
        all_passed = True
        
        for setting_name, actual_value, expected_value in checks:
            if actual_value == expected_value:
                print(f"   ✅ {setting_name}: {actual_value}")
            else:
                print(f"   ❌ {setting_name}: {actual_value} (expected: {expected_value})")
                all_passed = False
        
        # Check recovery mode settings
        recovery_config = config.get("supplier_extraction_progress", {})
        recovery_mode = recovery_config.get("recovery_mode")
        recovery_enabled = recovery_config.get("enabled")
        
        print(f"   {'✅' if recovery_enabled else '❌'} supplier_extraction_progress.enabled: {recovery_enabled}")
        print(f"   {'✅' if recovery_mode == 'product_resume' else '❌'} supplier_extraction_progress.recovery_mode: {recovery_mode}")
        
        if all_passed and recovery_enabled and recovery_mode == "product_resume":
            print("✅ FINITE MODE CONFIGURATION VERIFIED SUCCESSFULLY")
            return True
        else:
            print("❌ FINITE MODE CONFIGURATION VERIFICATION FAILED")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: Failed to verify configuration: {e}")
        return False

def show_expected_impact():
    """Show the expected impact of finite mode configuration"""
    print("\n🚀 EXPECTED IMPACT OF FINITE MODE CONFIGURATION:")
    print("=" * 60)
    print("BEFORE (Current Configuration):")
    print("  • Max products processed: 16")
    print("  • Max products per category: 4")
    print("  • Price range: £1.00 - £20.00")
    print("  • Categories processed: ~4 out of 276")
    print("  • Total processing capacity: ~0.1% of available products")
    print()
    print("AFTER (Finite Mode Configuration):")
    print("  • Max products processed: 100,000")
    print("  • Max products per category: 10,000")
    print("  • Price range: £0.01 - £10,000.00")
    print("  • Categories processed: ALL 276 categories")
    print("  • Total processing capacity: 100% of available products")
    print()
    print("🔄 RECOVERY FEATURES:")
    print("  • Product-level recovery enabled")
    print("  • Progress tracking across all categories")
    print("  • Automatic state persistence every 5 products")
    print("  • Chunked processing for efficiency")
    print()
    print("⚡ PERFORMANCE OPTIMIZATIONS:")
    print("  • Batch size increased to 25 products")
    print("  • Category processing increased to 5 simultaneous")
    print("  • Enhanced cache management")
    print("  • Memory management for long-running processes")

def main():
    """Main execution function"""
    print("🚀 FINITE MODE CONFIGURATION SCRIPT")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("config").exists():
        print("❌ ERROR: Must be run from the project root directory")
        sys.exit(1)
    
    # Parse command line arguments
    create_backup = "--backup" in sys.argv
    verify_config = "--verify" in sys.argv
    
    # Show expected impact
    show_expected_impact()
    
    # Create backup if requested
    if create_backup:
        backup_current_config()
    
    # Apply finite mode configuration
    if apply_finite_mode_config():
        print("✅ Finite mode configuration applied successfully!")
    else:
        print("❌ Failed to apply finite mode configuration")
        sys.exit(1)
    
    # Verify configuration if requested
    if verify_config:
        print("\n🔍 VERIFYING CONFIGURATION...")
        if verify_configuration():
            print("✅ Configuration verification passed!")
        else:
            print("❌ Configuration verification failed!")
            sys.exit(1)
    
    print("\n🎯 NEXT STEPS:")
    print("1. Run the system with: python run_complete_fba_system.py")
    print("2. Monitor progress in the logs")
    print("3. Check processing state files for recovery information")
    print("4. Expect processing time of several hours for complete analysis")
    print()
    print("📊 MONITORING COMMANDS:")
    print("  • Check progress: tail -f fba_extraction_*.log")
    print("  • View state: cat OUTPUTS/processing_states/*_processing_state.json")
    print("  • Monitor results: ls -la OUTPUTS/FBA_ANALYSIS/")

if __name__ == "__main__":
    main()