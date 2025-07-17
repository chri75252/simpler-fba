#!/usr/bin/env python3
import time
import os
import glob
from pathlib import Path
from datetime import datetime

print("📁 FILE SYSTEM MONITOR STARTED")
print("=" * 50)
print("🎯 Monitoring: File creation, backups, outputs, toggles")
print("📍 Paths: OUTPUTS/, logs/, config/, *.bak*")
print("=" * 50)

base_dir = Path.cwd()
last_counts = {}
last_mtimes = {}

def check_directory(path, name):
    """Check directory for changes"""
    if not path.exists():
        return
    
    files = list(path.rglob("*")) if path.is_dir() else [path]
    current_count = len([f for f in files if f.is_file()])
    
    if name in last_counts and current_count > last_counts[name]:
        new_files = current_count - last_counts[name]
        print(f"📄 [{datetime.now().strftime('%H:%M:%S')}] NEW FILES in {name}: +{new_files} (total: {current_count})")
    
    last_counts[name] = current_count

def check_backups():
    """Check for backup files"""
    backup_pattern = str(base_dir / "**/*.bak*")
    backup_files = glob.glob(backup_pattern, recursive=True)
    
    if "backups" in last_counts and len(backup_files) > last_counts["backups"]:
        new_backups = len(backup_files) - last_counts["backups"]
        print(f"💾 [{datetime.now().strftime('%H:%M:%S')}] NEW BACKUPS: +{new_backups}")
        
        # Show recent backups
        recent_backups = sorted(backup_files, key=os.path.getmtime)[-new_backups:]
        for backup in recent_backups:
            print(f"   📦 {Path(backup).name}")
    
    last_counts["backups"] = len(backup_files)

def check_config_changes():
    """Check configuration file changes"""
    config_files = [
        base_dir / "config/system_config.json",
        base_dir / "run_custom_poundwholesale.py",
        base_dir / "config/system-config-toggle-v2.md"
    ]
    
    for config_file in config_files:
        if config_file.exists():
            mtime = config_file.stat().st_mtime
            file_key = str(config_file)
            
            if file_key in last_mtimes and mtime > last_mtimes[file_key]:
                print(f"⚙️  [{datetime.now().strftime('%H:%M:%S')}] CONFIG CHANGED: {config_file.name}")
            
            last_mtimes[file_key] = mtime

while True:
    try:
        # Monitor key directories
        check_directory(base_dir / "OUTPUTS", "OUTPUTS")
        check_directory(base_dir / "logs/debug", "logs/debug")
        check_directory(base_dir / "config", "config")
        
        # Monitor backups
        check_backups()
        
        # Monitor config changes
        check_config_changes()
        
        time.sleep(2)
    except KeyboardInterrupt:
        print("\n👋 File monitor stopped")
        break
    except Exception as e:
        print(f"❌ File monitor error: {e}")
        time.sleep(5)
