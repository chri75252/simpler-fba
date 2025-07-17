#!/usr/bin/env python3

import json
import os
import time
from datetime import datetime
from pathlib import Path

class IncrementalBackupMonitor:
    def __init__(self):
        self.base_dir = "/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3"
        
        # Source files to monitor
        self.linking_map_path = f"{self.base_dir}/OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json"
        self.cached_products_path = f"{self.base_dir}/OUTPUTS/cached_products/clearance-king_co_uk_products_cache.json"
        
        # Incremental backup files (will grow with new entries)
        self.incremental_linking_path = f"{self.base_dir}/OUTPUTS/FBA_ANALYSIS/Linking map/linking_map_incremental_backup.json"
        self.incremental_cache_path = f"{self.base_dir}/OUTPUTS/cached_products/cached_products_incremental_backup.json"
        
        # Track what we've already backed up
        self.known_linking_entries = set()
        self.known_cache_entries = set()
        
        # Load existing backup data if files exist
        self._load_existing_backups()
        
        print("🔄 INCREMENTAL BACKUP MONITOR STARTED")
        print("=" * 60)
        print(f"Source: {os.path.basename(self.linking_map_path)}")
        print(f"Backup: {os.path.basename(self.incremental_linking_path)}")
        print(f"Source: {os.path.basename(self.cached_products_path)}")
        print(f"Backup: {os.path.basename(self.incremental_cache_path)}")
        print(f"Known linking entries: {len(self.known_linking_entries)}")
        print(f"Known cache entries: {len(self.known_cache_entries)}")
        
    def _load_existing_backups(self):
        """Load existing backup files to know what we already have"""
        
        # Load existing linking map backup
        if os.path.exists(self.incremental_linking_path):
            try:
                with open(self.incremental_linking_path, 'r', encoding='utf-8') as f:
                    existing_linking = json.load(f)
                
                for entry in existing_linking:
                    # Create unique identifier for each entry
                    identifier = f"{entry.get('supplier_product_identifier', '')}_{entry.get('chosen_amazon_asin', '')}"
                    self.known_linking_entries.add(identifier)
                    
                print(f"📚 Loaded {len(existing_linking)} existing linking entries")
            except Exception as e:
                print(f"⚠️  Error loading existing linking backup: {e}")
        
        # Load existing cache backup
        if os.path.exists(self.incremental_cache_path):
            try:
                with open(self.incremental_cache_path, 'r', encoding='utf-8') as f:
                    existing_cache = json.load(f)
                
                for entry in existing_cache:
                    # Create unique identifier for each product
                    identifier = f"{entry.get('ean', '')}_{entry.get('url', '')}"
                    self.known_cache_entries.add(identifier)
                    
                print(f"📦 Loaded {len(existing_cache)} existing cache entries")
            except Exception as e:
                print(f"⚠️  Error loading existing cache backup: {e}")
    
    def _get_new_linking_entries(self):
        """Get new linking map entries that we haven't backed up yet"""
        try:
            with open(self.linking_map_path, 'r', encoding='utf-8') as f:
                current_linking = json.load(f)
            
            new_entries = []
            for entry in current_linking:
                identifier = f"{entry.get('supplier_product_identifier', '')}_{entry.get('chosen_amazon_asin', '')}"
                if identifier not in self.known_linking_entries:
                    new_entries.append(entry)
                    self.known_linking_entries.add(identifier)
            
            return new_entries
            
        except Exception as e:
            print(f"❌ Error reading linking map: {e}")
            return []
    
    def _get_new_cache_entries(self):
        """Get new cache entries that we haven't backed up yet"""
        try:
            with open(self.cached_products_path, 'r', encoding='utf-8') as f:
                current_cache = json.load(f)
            
            new_entries = []
            for entry in current_cache:
                identifier = f"{entry.get('ean', '')}_{entry.get('url', '')}"
                if identifier not in self.known_cache_entries:
                    new_entries.append(entry)
                    self.known_cache_entries.add(identifier)
            
            return new_entries
            
        except Exception as e:
            print(f"❌ Error reading cached products: {e}")
            return []
    
    def _append_to_backup(self, new_entries, backup_path, file_type):
        """Append new entries to incremental backup file"""
        if not new_entries:
            return
        
        try:
            # Load existing backup or create empty list
            existing_backup = []
            if os.path.exists(backup_path):
                with open(backup_path, 'r', encoding='utf-8') as f:
                    existing_backup = json.load(f)
            
            # Add new entries
            existing_backup.extend(new_entries)
            
            # Write back to file
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(existing_backup, f, indent=2, ensure_ascii=False)
            
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"✅ [{timestamp}] Added {len(new_entries)} new {file_type} entries (Total: {len(existing_backup)})")
            
        except Exception as e:
            print(f"❌ Error updating {file_type} backup: {e}")
    
    def monitor_and_update(self):
        """Main monitoring loop"""
        check_count = 0
        
        while True:
            check_count += 1
            current_time = datetime.now().strftime('%H:%M:%S')
            
            # Check for new linking map entries
            new_linking = self._get_new_linking_entries()
            if new_linking:
                self._append_to_backup(new_linking, self.incremental_linking_path, "linking map")
            
            # Check for new cache entries
            new_cache = self._get_new_cache_entries()
            if new_cache:
                self._append_to_backup(new_cache, self.incremental_cache_path, "cached products")
            
            # Show periodic status
            if check_count % 60 == 0:  # Every 5 minutes
                print(f"\n📊 [{current_time}] Status check #{check_count//60}")
                print(f"   Total linking entries tracked: {len(self.known_linking_entries)}")
                print(f"   Total cache entries tracked: {len(self.known_cache_entries)}")
                
                # Show current file sizes
                try:
                    if os.path.exists(self.incremental_linking_path):
                        with open(self.incremental_linking_path, 'r') as f:
                            backup_linking = json.load(f)
                        print(f"   Incremental linking backup size: {len(backup_linking)} entries")
                    
                    if os.path.exists(self.incremental_cache_path):
                        with open(self.incremental_cache_path, 'r') as f:
                            backup_cache = json.load(f)
                        print(f"   Incremental cache backup size: {len(backup_cache)} entries")
                        
                except Exception as e:
                    print(f"   Error checking backup sizes: {e}")
            
            # Sleep for 5 seconds between checks
            time.sleep(5)

if __name__ == "__main__":
    monitor = IncrementalBackupMonitor()
    try:
        monitor.monitor_and_update()
    except KeyboardInterrupt:
        print("\n\n🛑 Incremental backup monitor stopped by user")
        print(f"📊 Final tracking counts:")
        print(f"   Linking entries: {len(monitor.known_linking_entries)}")
        print(f"   Cache entries: {len(monitor.known_cache_entries)}")
    except Exception as e:
        print(f"\n❌ Monitor error: {e}")