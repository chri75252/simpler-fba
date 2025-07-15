#!/usr/bin/env python3
import time
import glob
import re
from pathlib import Path
from datetime import datetime

print("🚨 ERROR & CRITICAL EVENT MONITOR STARTED")
print("=" * 50)
print("🎯 Focus: Errors, exceptions, authentication failures, browser issues")
print("⚠️  Critical patterns: AttributeError, browser disconnect, auth failures")
print("=" * 50)

base_dir = Path.cwd()
last_positions = {}
error_count = 0

critical_patterns = {
    'AUTHENTICATION_FAILURE': r'authentication failed|login failed|auth error',
    'BROWSER_DISCONNECT': r'browser disconnect|connection lost|session ended',
    'ATTRIBUTE_ERROR': r'AttributeError',
    'FILE_ERROR': r'file creation error|failed to create|permission denied',
    'NETWORK_ERROR': r'network error|connection timeout|dns resolution',
    'EXCEPTION': r'Exception:|Error:|Traceback'
}

def monitor_log_file(file_path, file_key):
    """Monitor a single log file for errors"""
    global error_count
    
    if not Path(file_path).exists():
        return
    
    current_size = Path(file_path).stat().st_size
    last_pos = last_positions.get(file_key, 0)
    
    if current_size <= last_pos:
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(last_pos)
            new_lines = f.readlines()
            last_positions[file_key] = f.tell()
        
        for line in new_lines:
            line = line.strip()
            if not line:
                continue
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Check critical patterns
            for pattern_name, regex in critical_patterns.items():
                if re.search(regex, line, re.IGNORECASE):
                    error_count += 1
                    print(f"🚨 [{timestamp}] {pattern_name}: {line}")
                    
                    # For critical errors, also show context
                    if pattern_name in ['AUTHENTICATION_FAILURE', 'BROWSER_DISCONNECT']:
                        print(f"   📁 File: {Path(file_path).name}")
            
            # Show general errors
            if re.search(r'ERROR|error|Error', line) and not any(re.search(pattern, line, re.IGNORECASE) for pattern in critical_patterns.values()):
                print(f"❌ [{timestamp}] ERROR: {line[:100]}...")
    
    except Exception as e:
        print(f"❌ Monitor error for {file_path}: {e}")

while True:
    try:
        # Monitor all log directories
        log_patterns = [
            "logs/debug/*.log",
            "../AFBAS32-test/logs/debug/*.log",
            "../AFBAS32-debug/logs/debug/*.log"
        ]
        
        for pattern in log_patterns:
            files = glob.glob(str(base_dir / pattern))
            for file_path in files:
                monitor_log_file(file_path, file_path)
        
        # Show error count every 20 iterations
        if error_count > 0 and error_count % 5 == 0:
            print(f"📊 [{datetime.now().strftime('%H:%M:%S')}] Total critical events detected: {error_count}")
        
        time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Error monitor stopped")
        break
    except Exception as e:
        print(f"❌ Error monitor error: {e}")
        time.sleep(5)
