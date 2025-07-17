#!/usr/bin/env python3
"""
Simple Real-Time Monitor for Amazon FBA Agents
Shows live log output with filtering and highlighting
"""

import time
import glob
import re
from pathlib import Path
from datetime import datetime

def find_latest_logs():
    """Find the most recent log files for each agent"""
    base_dir = Path.cwd()
    
    patterns = {
        'exec-agent': 'logs/debug/run_custom_poundwholesale_*.log',
        'verify-agent': 'logs/debug/verify_*.log', 
        'toggle-agent': 'logs/debug/toggle_*.log',
        'debug-agent': '../AFBAS32-debug/logs/debug/debug_*.log'
    }
    
    latest_files = {}
    
    for agent, pattern in patterns.items():
        files = glob.glob(str(base_dir / pattern))
        if files:
            latest_files[agent] = max(files, key=lambda x: Path(x).stat().st_mtime)
        else:
            latest_files[agent] = None
    
    return latest_files

def monitor_logs():
    """Monitor log files and show filtered output"""
    print("🚀 Amazon FBA Multi-Agent Monitor")
    print("=" * 60)
    print("🔍 Looking for active log files...")
    
    latest_files = find_latest_logs()
    
    print("\n📁 Found log files:")
    for agent, file_path in latest_files.items():
        if file_path:
            file_name = Path(file_path).name
            file_time = datetime.fromtimestamp(Path(file_path).stat().st_mtime).strftime("%H:%M:%S")
            print(f"  ✅ {agent}: {file_name} (modified: {file_time})")
        else:
            print(f"  ❌ {agent}: No log file found")
    
    # Choose the most active log to monitor
    active_files = {k: v for k, v in latest_files.items() if v and Path(v).exists()}
    
    if not active_files:
        print("\n❌ No active log files found!")
        return
    
    # Get the most recently modified file
    most_recent = max(active_files.items(), key=lambda x: Path(x[1]).stat().st_mtime)
    monitor_file = most_recent[1]
    monitor_agent = most_recent[0]
    
    print(f"\n🎯 Monitoring: {monitor_agent}")
    print(f"📄 File: {Path(monitor_file).name}")
    print("=" * 60)
    print("📊 Live output (showing ERROR, SUCCESS, PROGRESS, AUTH, BROWSER):")
    print("⌨️  Press Ctrl+C to stop")
    print("-" * 60)
    
    # Monitor the file
    last_position = Path(monitor_file).stat().st_size  # Start from end
    
    try:
        while True:
            if not Path(monitor_file).exists():
                print(f"❌ File {monitor_file} no longer exists")
                break
            
            current_size = Path(monitor_file).stat().st_size
            
            if current_size > last_position:
                with open(monitor_file, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_position)
                    new_lines = f.readlines()
                    last_position = f.tell()
                
                for line in new_lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    
                    # Filter and highlight important lines
                    if re.search(r'ERROR|error|Error|CRITICAL', line, re.IGNORECASE):
                        print(f"🚨 [{timestamp}] ERROR: {line}")
                    elif re.search(r'SUCCESS|success|Successfully|✅', line, re.IGNORECASE):
                        print(f"✅ [{timestamp}] SUCCESS: {line}")
                    elif re.search(r'Processing category|Found \d+ products|Product \d+ of \d+', line, re.IGNORECASE):
                        print(f"📊 [{timestamp}] PROGRESS: {line}")
                    elif re.search(r'authentication|login|Login|auth', line, re.IGNORECASE):
                        print(f"🔐 [{timestamp}] AUTH: {line}")
                    elif re.search(r'browser|Browser|playwright|chrome', line, re.IGNORECASE):
                        print(f"🌐 [{timestamp}] BROWSER: {line}")
                    elif re.search(r'WARNING|warning|Warning', line, re.IGNORECASE):
                        print(f"⚠️  [{timestamp}] WARNING: {line}")
                    elif re.search(r'Generated file|Created:|Saved to|backup', line, re.IGNORECASE):
                        print(f"📁 [{timestamp}] FILE: {line}")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n👋 Stopped monitoring {monitor_agent}")

if __name__ == "__main__":
    monitor_logs()