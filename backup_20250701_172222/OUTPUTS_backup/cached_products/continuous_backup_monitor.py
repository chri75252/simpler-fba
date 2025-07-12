#!/usr/bin/env python3

import json
import os
import time
import shutil
from datetime import datetime
from pathlib import Path

class ContinuousBackupMonitor:
    def __init__(self):
        self.base_dir = "/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3"
        
        # Files to monitor
        self.linking_map_path = f"{self.base_dir}/OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json"
        self.cached_products_path = f"{self.base_dir}/OUTPUTS/cached_products/clearance-king_co_uk_products_cache.json"
        
        # Backup directories
        self.linking_backup_dir = f"{self.base_dir}/OUTPUTS/FBA_ANALYSIS/Linking map/backups"
        self.cache_backup_dir = f"{self.base_dir}/OUTPUTS/cached_products/backups"
        
        # Create backup directories
        os.makedirs(self.linking_backup_dir, exist_ok=True)
        os.makedirs(self.cache_backup_dir, exist_ok=True)
        
        # Track last modification times
        self.last_linking_mod = 0
        self.last_cache_mod = 0
        
        print("🔄 CONTINUOUS BACKUP MONITOR STARTED")
        print("=" * 60)
        print(f"Monitoring: {os.path.basename(self.linking_map_path)}")
        print(f"Monitoring: {os.path.basename(self.cached_products_path)}")
        print(f"Backup dirs created: backups/")
        
    def get_file_mod_time(self, filepath):
        """Get file modification time safely"""
        try:
            return os.path.getmtime(filepath)
        except:
            return 0
    
    def create_backup(self, source_path, backup_dir, file_type):
        """Create timestamped backup of file"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{file_type}_backup_{timestamp}.json"
            backup_path = os.path.join(backup_dir, backup_name)
            
            # Use shutil.copy2 to preserve metadata
            shutil.copy2(source_path, backup_path)
            
            # Also read and validate the JSON
            with open(source_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            count = len(data) if isinstance(data, list) else "unknown"
            print(f"✅ {file_type.upper()} backup created: {backup_name} ({count} entries)")
            
            return True
            
        except Exception as e:
            print(f"❌ Error backing up {file_type}: {e}")
            return False
    
    def monitor_files(self):
        """Main monitoring loop"""
        check_count = 0
        
        while True:
            check_count += 1
            current_time = datetime.now().strftime('%H:%M:%S')
            
            # Check linking map
            current_linking_mod = self.get_file_mod_time(self.linking_map_path)
            if current_linking_mod > self.last_linking_mod:
                print(f"\n🔍 [{current_time}] Linking map updated!")
                if self.create_backup(self.linking_map_path, self.linking_backup_dir, "linking_map"):
                    self.last_linking_mod = current_linking_mod
            
            # Check cached products
            current_cache_mod = self.get_file_mod_time(self.cached_products_path)
            if current_cache_mod > self.last_cache_mod:
                print(f"\n🔍 [{current_time}] Cached products updated!")
                if self.create_backup(self.cached_products_path, self.cache_backup_dir, "cached_products"):
                    self.last_cache_mod = current_cache_mod
            
            # Show periodic status
            if check_count % 60 == 0:  # Every 5 minutes (60 * 5 seconds)
                print(f"\n📊 [{current_time}] Status check #{check_count//60}")
                
                # Show current file sizes
                try:
                    with open(self.linking_map_path, 'r') as f:
                        linking_data = json.load(f)
                    print(f"   Linking map entries: {len(linking_data)}")
                except:
                    print(f"   Linking map: Unable to read")
                
                try:
                    with open(self.cached_products_path, 'r') as f:
                        cache_data = json.load(f)
                    print(f"   Cached products: {len(cache_data)}")
                except:
                    print(f"   Cached products: Unable to read")
            
            # Sleep for 5 seconds between checks
            time.sleep(5)

if __name__ == "__main__":
    monitor = ContinuousBackupMonitor()
    try:
        monitor.monitor_files()
    except KeyboardInterrupt:
        print("\n\n🛑 Monitor stopped by user")
    except Exception as e:
        print(f"\n❌ Monitor error: {e}")