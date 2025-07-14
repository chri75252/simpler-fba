#!/usr/bin/env python3
"""
Emergency Frequent Backup Script
Creates timestamped backups every 5 minutes for critical files
Run alongside the main system for extra safety
"""

import os
import json
import shutil
import time
from datetime import datetime
from pathlib import Path

class EmergencyFrequentBackup:
    def __init__(self):
        # Get the project root (3 levels up from this script)
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent.parent
        
        # Critical files to backup
        self.files_to_backup = {
            "supplier_cache": self.script_dir / "clearance-king_co_uk_products_cache.json",
            "linking_map": self.project_root / "OUTPUTS" / "FBA_ANALYSIS" / "Linking map" / "linking_map.json",
            "processing_state": self.project_root / "OUTPUTS" / "FBA_ANALYSIS" / "clearance-king_co_uk_processing_state.json",
            "ai_cache": self.project_root / "OUTPUTS" / "FBA_ANALYSIS" / "ai_category_cache" / "clearance-king_co_uk_ai_category_cache.json"
        }
        
        # Backup directory
        self.backup_dir = self.script_dir / "emergency_backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        print(f"🚨 Emergency Frequent Backup Monitor Started")
        print(f"📂 Backup Directory: {self.backup_dir}")
        print(f"⏰ Backup Interval: Every 5 minutes")
        print(f"📁 Files Monitored: {len(self.files_to_backup)}")
        
    def create_backup(self):
        """Create timestamped backup of all critical files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_created = False
        
        for file_type, file_path in self.files_to_backup.items():
            if file_path.exists():
                try:
                    # Create backup filename with timestamp
                    backup_filename = f"{file_type}_{timestamp}.json"
                    backup_path = self.backup_dir / backup_filename
                    
                    # Copy the file
                    shutil.copy2(file_path, backup_path)
                    
                    # Get file info
                    file_size = backup_path.stat().st_size
                    print(f"✅ Backed up {file_type}: {backup_filename} ({file_size:,} bytes)")
                    backup_created = True
                    
                except Exception as e:
                    print(f"❌ Failed to backup {file_type}: {e}")
            else:
                print(f"⚠️ File not found: {file_type} at {file_path}")
        
        if backup_created:
            print(f"🔄 Backup completed at {timestamp}")
        
        return backup_created
    
    def cleanup_old_backups(self, keep_hours=12):
        """Remove backups older than specified hours"""
        try:
            cutoff_time = time.time() - (keep_hours * 3600)
            removed_count = 0
            
            for backup_file in self.backup_dir.glob("*.json"):
                if backup_file.stat().st_mtime < cutoff_time:
                    backup_file.unlink()
                    removed_count += 1
            
            if removed_count > 0:
                print(f"🧹 Cleaned up {removed_count} old backups (older than {keep_hours}h)")
                
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
    
    def run(self):
        """Main backup loop - runs every 5 minutes"""
        backup_count = 0
        
        try:
            while True:
                # Create backup
                if self.create_backup():
                    backup_count += 1
                
                # Clean up old backups every 10th iteration
                if backup_count % 10 == 0:
                    self.cleanup_old_backups()
                
                # Wait 5 minutes
                print(f"💤 Sleeping for 5 minutes... (Backup #{backup_count})")
                time.sleep(300)  # 5 minutes
                
        except KeyboardInterrupt:
            print(f"\n🛑 Emergency backup stopped by user. Created {backup_count} backups.")
        except Exception as e:
            print(f"❌ Emergency backup crashed: {e}")

if __name__ == "__main__":
    backup_monitor = EmergencyFrequentBackup()
    backup_monitor.run()