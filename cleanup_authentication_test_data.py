#!/usr/bin/env python3
"""
Authentication Test Cleanup Script
Clears processing state files, cached supplier folder files, and linking maps
as requested after comprehensive authentication system testing.
"""

import os
import shutil
import json
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def backup_before_cleanup():
    """Create backup of current state before cleanup"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f"backup_pre_auth_cleanup_{timestamp}"
    
    print(f"📦 Creating backup: {backup_dir}")
    
    backup_paths = [
        ("OUTPUTS/CACHE/processing_states/", f"{backup_dir}/processing_states/"),
        ("OUTPUTS/cached_products/", f"{backup_dir}/cached_products/"),
        ("OUTPUTS/FBA_ANALYSIS/linking_maps/", f"{backup_dir}/linking_maps/"),
        ("OUTPUTS/FBA_ANALYSIS/ai_category_cache/", f"{backup_dir}/ai_category_cache/"),
        ("OUTPUTS/FBA_ANALYSIS/amazon_cache/", f"{backup_dir}/amazon_cache/")
    ]
    
    os.makedirs(backup_dir, exist_ok=True)
    
    for source, dest in backup_paths:
        if os.path.exists(source):
            try:
                shutil.copytree(source, dest, dirs_exist_ok=True)
                print(f"  ✅ Backed up {source} -> {dest}")
            except Exception as e:
                print(f"  ⚠️ Could not backup {source}: {e}")
        else:
            print(f"  📄 {source} does not exist - skipping")
    
    return backup_dir

def cleanup_processing_states():
    """Clear all processing state files"""
    
    print("🧹 Cleaning up processing state files...")
    
    processing_states_dir = "OUTPUTS/CACHE/processing_states/"
    
    if os.path.exists(processing_states_dir):
        try:
            files_removed = 0
            for file in os.listdir(processing_states_dir):
                if file.endswith('.json'):
                    file_path = os.path.join(processing_states_dir, file)
                    os.remove(file_path)
                    files_removed += 1
                    print(f"  🗑️ Removed processing state: {file}")
            
            print(f"  ✅ Removed {files_removed} processing state files")
            
        except Exception as e:
            print(f"  ❌ Error cleaning processing states: {e}")
    else:
        print("  📄 Processing states directory does not exist")

def cleanup_cached_supplier_files():
    """Clear cached supplier folder files"""
    
    print("🧹 Cleaning up cached supplier files...")
    
    cached_products_dir = "OUTPUTS/cached_products/"
    
    if os.path.exists(cached_products_dir):
        try:
            files_removed = 0
            for file in os.listdir(cached_products_dir):
                if file.endswith('.json'):
                    file_path = os.path.join(cached_products_dir, file)
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    files_removed += 1
                    print(f"  🗑️ Removed cached supplier file: {file} ({file_size} bytes)")
            
            print(f"  ✅ Removed {files_removed} cached supplier files")
            
        except Exception as e:
            print(f"  ❌ Error cleaning cached supplier files: {e}")
    else:
        print("  📄 Cached products directory does not exist")

def cleanup_linking_maps():
    """Clear linking map files"""
    
    print("🧹 Cleaning up linking maps...")
    
    linking_maps_dir = "OUTPUTS/FBA_ANALYSIS/linking_maps/"
    
    if os.path.exists(linking_maps_dir):
        try:
            directories_removed = 0
            files_removed = 0
            
            for supplier_dir in os.listdir(linking_maps_dir):
                supplier_path = os.path.join(linking_maps_dir, supplier_dir)
                
                if os.path.isdir(supplier_path):
                    # Remove all files in supplier directory
                    for file in os.listdir(supplier_path):
                        if file.endswith('.json'):
                            file_path = os.path.join(supplier_path, file)
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            files_removed += 1
                            print(f"  🗑️ Removed linking map: {supplier_dir}/{file} ({file_size} bytes)")
                    
                    # Remove empty supplier directory
                    try:
                        os.rmdir(supplier_path)
                        directories_removed += 1
                        print(f"  🗑️ Removed empty supplier directory: {supplier_dir}")
                    except OSError:
                        # Directory not empty
                        pass
            
            print(f"  ✅ Removed {files_removed} linking map files and {directories_removed} directories")
            
        except Exception as e:
            print(f"  ❌ Error cleaning linking maps: {e}")
    else:
        print("  📄 Linking maps directory does not exist")

def cleanup_optional_cache_files():
    """Clear optional cache files that may affect testing"""
    
    print("🧹 Cleaning up optional cache files...")
    
    optional_cleanup_paths = [
        "OUTPUTS/FBA_ANALYSIS/ai_category_cache/",
        "OUTPUTS/FBA_ANALYSIS/amazon_cache/",
        "OUTPUTS/FBA_ANALYSIS/financial_reports/"
    ]
    
    total_files_removed = 0
    
    for cache_dir in optional_cleanup_paths:
        if os.path.exists(cache_dir):
            try:
                files_in_dir = 0
                for file in os.listdir(cache_dir):
                    if file.endswith(('.json', '.csv')):
                        file_path = os.path.join(cache_dir, file)
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        files_in_dir += 1
                        total_files_removed += 1
                        print(f"  🗑️ Removed cache file: {os.path.basename(cache_dir)}/{file} ({file_size} bytes)")
                
                if files_in_dir == 0:
                    print(f"  📄 No files to remove in {cache_dir}")
                    
            except Exception as e:
                print(f"  ⚠️ Error cleaning {cache_dir}: {e}")
        else:
            print(f"  📄 {cache_dir} does not exist")
    
    print(f"  ✅ Removed {total_files_removed} optional cache files")

def verify_cleanup():
    """Verify that cleanup was successful"""
    
    print("🔍 Verifying cleanup completion...")
    
    verification_paths = [
        ("OUTPUTS/CACHE/processing_states/", "processing state files"),
        ("OUTPUTS/cached_products/", "cached supplier files"),
        ("OUTPUTS/FBA_ANALYSIS/linking_maps/", "linking map files"),
        ("OUTPUTS/FBA_ANALYSIS/ai_category_cache/", "AI category cache files"),
        ("OUTPUTS/FBA_ANALYSIS/amazon_cache/", "Amazon cache files"),
        ("OUTPUTS/FBA_ANALYSIS/financial_reports/", "financial report files")
    ]
    
    all_clean = True
    
    for path, description in verification_paths:
        if os.path.exists(path):
            files = [f for f in os.listdir(path) if f.endswith(('.json', '.csv'))]
            if files:
                print(f"  ⚠️ {description}: {len(files)} files remaining")
                for file in files[:3]:  # Show first 3 files
                    print(f"    - {file}")
                if len(files) > 3:
                    print(f"    ... and {len(files) - 3} more")
                all_clean = False
            else:
                print(f"  ✅ {description}: cleaned")
        else:
            print(f"  ✅ {description}: directory doesn't exist")
    
    return all_clean

def main():
    """Main cleanup function"""
    
    print("🧹 Amazon FBA Agent System v32 - Authentication Test Data Cleanup")
    print("=" * 70)
    print("🎯 Clearing processing state, cached supplier files, and linking maps")
    print("📋 As requested after comprehensive authentication system testing")
    print()
    
    try:
        # Create backup before cleanup
        backup_dir = backup_before_cleanup()
        print()
        
        # Perform cleanup operations
        cleanup_processing_states()
        print()
        
        cleanup_cached_supplier_files()
        print()
        
        cleanup_linking_maps()
        print()
        
        cleanup_optional_cache_files()
        print()
        
        # Verify cleanup
        all_clean = verify_cleanup()
        print()
        
        # Summary
        print("=" * 70)
        print("🧹 CLEANUP SUMMARY")
        print("=" * 70)
        print(f"📦 Backup created: {backup_dir}")
        
        if all_clean:
            print("✅ ALL CLEANUP OPERATIONS COMPLETED SUCCESSFULLY")
            print("   📝 Processing state files cleared")
            print("   📁 Cached supplier folder files cleared")
            print("   🔗 Linking map files cleared")
            print("   🗃️ Optional cache files cleared")
            print()
            print("🎉 SYSTEM READY FOR FRESH AUTHENTICATION TESTING")
            print("   The authentication system is now in a clean state.")
            print("   All previous test data has been cleared and backed up.")
        else:
            print("⚠️  CLEANUP PARTIALLY COMPLETED")
            print("   Some files may still remain - see verification output above")
        
        return all_clean
        
    except Exception as e:
        print(f"💥 Unexpected error during cleanup: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)