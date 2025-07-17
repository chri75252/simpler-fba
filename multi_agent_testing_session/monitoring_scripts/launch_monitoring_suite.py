#!/usr/bin/env python3
"""
Launch comprehensive monitoring suite for Amazon FBA multi-agent workflow
Creates multiple specialized monitoring terminals
"""

import subprocess
import time
import os
import sys
from pathlib import Path

def create_exec_monitor():
    """Create execution monitoring script"""
    script_content = '''#!/usr/bin/env python3
import time
import glob
import re
from pathlib import Path
from datetime import datetime

print("🚀 EXEC-AGENT MONITOR STARTED")
print("=" * 50)
print("📍 Monitoring: ../AFBAS32-test/logs/debug/run_custom_poundwholesale_*.log")
print("🎯 Focus: Main workflow execution, product processing, authentication")
print("=" * 50)

base_dir = Path.cwd()
last_position = 0
metrics = {"products": 0, "categories": 0, "errors": 0, "successes": 0}

while True:
    try:
        # Find latest log file
        pattern = str(base_dir / "../AFBAS32-test/logs/debug/run_custom_poundwholesale_*.log")
        files = glob.glob(pattern)
        
        if not files:
            pattern = str(base_dir / "logs/debug/run_custom_poundwholesale_*.log")
            files = glob.glob(pattern)
        
        if files:
            latest_file = max(files, key=os.path.getmtime)
            
            if Path(latest_file).exists():
                current_size = Path(latest_file).stat().st_size
                
                if current_size > last_position:
                    with open(latest_file, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(last_position)
                        new_lines = f.readlines()
                        last_position = f.tell()
                    
                    for line in new_lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        
                        # Critical patterns
                        if re.search(r'ERROR|error|Error', line):
                            metrics["errors"] += 1
                            print(f"🚨 [{timestamp}] ERROR: {line}")
                        elif re.search(r'SUCCESS|success|Successfully|✅', line):
                            metrics["successes"] += 1
                            print(f"✅ [{timestamp}] SUCCESS: {line}")
                        elif re.search(r'Processing category|Found \\d+ products', line):
                            print(f"📊 [{timestamp}] PROGRESS: {line}")
                        elif re.search(r'Product \\d+ of \\d+|--- Processing supplier product', line):
                            if 'Processing supplier product' in line:
                                metrics["products"] += 1
                            print(f"🔄 [{timestamp}] PRODUCT: {line}")
                        elif re.search(r'authentication|login|Login', line):
                            print(f"🔐 [{timestamp}] AUTH: {line}")
                        elif re.search(r'browser|Browser|playwright', line):
                            print(f"🌐 [{timestamp}] BROWSER: {line}")
                        elif re.search(r'WARNING|warning|Warning', line):
                            print(f"⚠️  [{timestamp}] WARNING: {line}")
                        
                        # Show every 10th line for context
                        if metrics["products"] % 10 == 0 and metrics["products"] > 0:
                            print(f"📈 [{timestamp}] METRICS: Products: {metrics['products']}, Errors: {metrics['errors']}, Successes: {metrics['successes']}")
        
        time.sleep(1)
    except KeyboardInterrupt:
        print("\\n👋 Exec monitor stopped")
        break
    except Exception as e:
        print(f"❌ Monitor error: {e}")
        time.sleep(5)
'''
    
    with open("exec_monitor.py", "w") as f:
        f.write(script_content)
    
    return "exec_monitor.py"

def create_file_monitor():
    """Create file system monitoring script"""
    script_content = '''#!/usr/bin/env python3
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
        print("\\n👋 File monitor stopped")
        break
    except Exception as e:
        print(f"❌ File monitor error: {e}")
        time.sleep(5)
'''
    
    with open("file_monitor.py", "w") as f:
        f.write(script_content)
    
    return "file_monitor.py"

def create_metrics_monitor():
    """Create metrics and progress monitoring script"""
    script_content = '''#!/usr/bin/env python3
import json
import time
from pathlib import Path
from datetime import datetime
import glob

print("📊 METRICS & PROGRESS MONITOR STARTED")
print("=" * 50)
print("🎯 Tracking: Processing state, linking maps, financial reports")
print("📈 Metrics: Progress, performance, success rates")
print("=" * 50)

base_dir = Path.cwd()
last_metrics = {}

def check_processing_state():
    """Check processing state files"""
    state_pattern = str(base_dir / "OUTPUTS/CACHE/processing_states/*.json")
    state_files = glob.glob(state_pattern)
    
    for state_file in state_files:
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            supplier = Path(state_file).stem.replace('_processing_state', '')
            current_progress = f"{state.get('last_processed_index', 0)}/{state.get('total_products', 0)}"
            
            if supplier not in last_metrics or last_metrics[supplier] != current_progress:
                print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] {supplier.upper()}: {current_progress} products")
                last_metrics[supplier] = current_progress
        
        except Exception as e:
            continue

def check_linking_maps():
    """Check linking map updates"""
    map_pattern = str(base_dir / "OUTPUTS/FBA_ANALYSIS/linking_maps/**/linking_map.json")
    map_files = glob.glob(map_pattern, recursive=True)
    
    for map_file in map_files:
        try:
            with open(map_file, 'r') as f:
                data = json.load(f)
            
            supplier = Path(map_file).parent.name
            count = len(data) if isinstance(data, list) else 0
            
            map_key = f"{supplier}_links"
            if map_key not in last_metrics or last_metrics[map_key] != count:
                print(f"🔗 [{datetime.now().strftime('%H:%M:%S')}] {supplier.upper()}: {count} product links")
                last_metrics[map_key] = count
        
        except Exception as e:
            continue

def check_financial_reports():
    """Check financial report updates"""
    report_pattern = str(base_dir / "OUTPUTS/FBA_ANALYSIS/financial_reports/*.csv")
    report_files = glob.glob(report_pattern)
    
    report_count = len(report_files)
    if "reports" not in last_metrics or last_metrics["reports"] != report_count:
        print(f"💰 [{datetime.now().strftime('%H:%M:%S')}] FINANCIAL REPORTS: {report_count} files")
        last_metrics["reports"] = report_count
        
        if report_files:
            latest_report = max(report_files, key=lambda x: Path(x).stat().st_mtime)
            print(f"   📋 Latest: {Path(latest_report).name}")

def show_summary():
    """Show periodic summary"""
    print(f"\\n📊 SUMMARY - {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 30)
    for key, value in last_metrics.items():
        print(f"   {key}: {value}")
    print("-" * 30)

summary_timer = 0
while True:
    try:
        check_processing_state()
        check_linking_maps()
        check_financial_reports()
        
        summary_timer += 1
        if summary_timer >= 30:  # Show summary every minute (30 * 2s)
            show_summary()
            summary_timer = 0
        
        time.sleep(2)
    except KeyboardInterrupt:
        print("\\n👋 Metrics monitor stopped")
        break
    except Exception as e:
        print(f"❌ Metrics monitor error: {e}")
        time.sleep(5)
'''
    
    with open("metrics_monitor.py", "w") as f:
        f.write(script_content)
    
    return "metrics_monitor.py"

def create_error_monitor():
    """Create error and critical event monitoring script"""
    script_content = '''#!/usr/bin/env python3
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
        print("\\n👋 Error monitor stopped")
        break
    except Exception as e:
        print(f"❌ Error monitor error: {e}")
        time.sleep(5)
'''
    
    with open("error_monitor.py", "w") as f:
        f.write(script_content)
    
    return "error_monitor.py"

def launch_monitors():
    """Launch all monitoring terminals"""
    print("🚀 LAUNCHING AMAZON FBA MULTI-AGENT MONITORING SUITE")
    print("=" * 60)
    
    # Create monitoring scripts
    monitors = [
        ("Execution Monitor", create_exec_monitor()),
        ("File System Monitor", create_file_monitor()),
        ("Metrics Monitor", create_metrics_monitor()),
        ("Error Monitor", create_error_monitor())
    ]
    
    # Launch each monitor in a new terminal
    processes = []
    
    for name, script_file in monitors:
        print(f"📺 Launching {name}...")
        
        # Try different terminal commands based on system
        terminal_commands = [
            f'gnome-terminal --title="{name}" -- python3 {script_file}',
            f'xterm -title "{name}" -e python3 {script_file} &',
            f'konsole --title "{name}" -e python3 {script_file} &',
            f'terminator --title="{name}" -e "python3 {script_file}" &'
        ]
        
        launched = False
        for cmd in terminal_commands:
            try:
                process = subprocess.Popen(cmd, shell=True)
                processes.append((name, process))
                print(f"   ✅ {name} launched successfully")
                launched = True
                break
            except Exception:
                continue
        
        if not launched:
            print(f"   ⚠️  Could not launch {name} in new terminal, running in background...")
            process = subprocess.Popen([sys.executable, script_file])
            processes.append((name, process))
        
        time.sleep(1)
    
    print(f"\n🎯 ALL MONITORS LAUNCHED!")
    print("=" * 60)
    print("📊 You now have comprehensive monitoring:")
    print("   🚀 Execution Monitor - Main workflow progress")
    print("   📁 File System Monitor - File creation & backups")
    print("   📈 Metrics Monitor - Progress & performance")
    print("   🚨 Error Monitor - Critical events & errors")
    print("\n🔥 START YOUR MULTI-AGENT TESTING NOW!")
    print("=" * 60)
    
    return processes

if __name__ == "__main__":
    try:
        processes = launch_monitors()
        
        # Keep main script running
        print("\n⌨️  Press Ctrl+C to stop all monitors...")
        while True:
            time.sleep(60)
            print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] All monitors running...")
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping all monitors...")
        for name, process in processes:
            try:
                process.terminate()
                print(f"   ✅ Stopped {name}")
            except:
                pass
        print("👋 All monitors stopped")