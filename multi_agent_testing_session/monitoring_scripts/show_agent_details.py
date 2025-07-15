#!/usr/bin/env python3
"""
Detailed Agent Activity Viewer
Shows comprehensive details of what each agent is doing
"""

import glob
import json
from pathlib import Path
from datetime import datetime

def show_exec_agent_details():
    """Show detailed execution agent activity"""
    print("🚀 EXEC-AGENT DETAILED ACTIVITY:")
    print("=" * 50)
    
    # Get latest exec agent log
    exec_logs = glob.glob("logs/debug/run_custom_poundwholesale_*.log")
    if exec_logs:
        latest_log = max(exec_logs, key=lambda x: Path(x).stat().st_mtime)
        print(f"📄 Latest log: {Path(latest_log).name}")
        
        # Show key activities from the log
        with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        print("\n📊 Key Activities Found:")
        key_activities = []
        for line in lines:
            if any(keyword in line for keyword in [
                'Processing category', 'Found', 'Product', 'SUCCESS', 
                'ERROR', 'Login', 'authentication', 'Generated file'
            ]):
                key_activities.append(line.strip())
        
        # Show last 10 key activities
        for activity in key_activities[-10:]:
            if 'ERROR' in activity:
                print(f"  🚨 {activity}")
            elif 'SUCCESS' in activity:
                print(f"  ✅ {activity}")
            elif 'Processing' in activity or 'Product' in activity:
                print(f"  📊 {activity}")
            else:
                print(f"  📝 {activity}")
    
    print()

def show_verify_agent_details():
    """Show detailed verification agent activity"""
    print("✅ VERIFY-AGENT DETAILED ACTIVITY:")
    print("=" * 50)
    
    verify_logs = glob.glob("logs/debug/verify_agent_*.log")
    if verify_logs:
        latest_log = max(verify_logs, key=lambda x: Path(x).stat().st_mtime)
        print(f"📄 Latest log: {Path(latest_log).name}")
        
        with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        print("\n🔍 Verification Summary:")
        lines = content.split('\n')
        for line in lines:
            if line.strip():
                if 'IDENTICAL' in line:
                    print(f"  🔹 {line.strip()}")
                elif 'differences' in line:
                    print(f"  🔸 {line.strip()}")
                elif 'Detailed diff saved' in line:
                    print(f"  📄 {line.strip()}")
                elif any(word in line for word in ['ERROR', 'WARNING', 'INFO']):
                    print(f"  📝 {line.strip()}")
    
    print()

def show_toggle_agent_details():
    """Show detailed toggle agent activity"""
    print("⚙️ TOGGLE-AGENT DETAILED ACTIVITY:")
    print("=" * 50)
    
    toggle_logs = glob.glob("logs/debug/toggle_agent_*.log")
    if toggle_logs:
        latest_log = max(toggle_logs, key=lambda x: Path(x).stat().st_mtime)
        print(f"📄 Latest log: {Path(latest_log).name}")
        
        with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        print("\n⚙️ Toggle Changes Applied:")
        lines = content.split('\n')
        for line in lines:
            if line.strip():
                if 'Verified:' in line:
                    print(f"  ✅ {line.strip()}")
                elif 'Experiment' in line and ('applied' in line or 'results' in line):
                    print(f"  🎯 {line.strip()}")
                elif 'Git commit' in line:
                    print(f"  📝 {line.strip()}")
                elif any(word in line for word in ['ERROR', 'WARNING', 'INFO']):
                    print(f"  📄 {line.strip()}")
    
    print()

def show_exec_reports_details():
    """Show detailed exec reports activity"""
    print("📊 EXEC-REPORTS DETAILED ACTIVITY:")
    print("=" * 50)
    
    report_logs = glob.glob("logs/debug/exec_agent_report_*.log")
    if report_logs:
        latest_log = max(report_logs, key=lambda x: Path(x).stat().st_mtime)
        print(f"📄 Latest log: {Path(latest_log).name}")
        
        with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        print("\n📈 Execution Analysis:")
        lines = content.split('\n')
        for line in lines:
            if line.strip():
                if 'completed successfully' in line:
                    print(f"  ✅ {line.strip()}")
                elif 'errors' in line or 'critical' in line:
                    print(f"  📊 {line.strip()}")
                elif 'Errors detected' in line:
                    print(f"  🚨 {line.strip()}")
                elif any(word in line for word in ['WARNING', 'INFO', 'ERROR']):
                    print(f"  📝 {line.strip()}")
    
    print()

def show_file_system_status():
    """Show file system status"""
    print("📁 FILE SYSTEM STATUS:")
    print("=" * 50)
    
    # Check key directories
    paths = {
        'OUTPUTS': Path('OUTPUTS'),
        'Cache': Path('OUTPUTS/CACHE'),
        'Reports': Path('OUTPUTS/FBA_ANALYSIS'),
        'Logs': Path('logs/debug'),
        'Config': Path('config')
    }
    
    for name, path in paths.items():
        if path.exists():
            if path.is_dir():
                file_count = len(list(path.rglob("*")))
                print(f"  📂 {name:<10}: {file_count:>4} files")
            else:
                print(f"  📄 {name:<10}: File")
        else:
            print(f"  ❌ {name:<10}: Not found")
    
    # Show recent file activity
    print("\n📈 Recent File Activity:")
    recent_files = []
    for path in Path('OUTPUTS').rglob("*"):
        if path.is_file():
            try:
                mtime = path.stat().st_mtime
                recent_files.append((mtime, path))
            except:
                continue
    
    # Show 5 most recent files
    recent_files.sort(reverse=True)
    for mtime, path in recent_files[:5]:
        file_time = datetime.fromtimestamp(mtime).strftime("%H:%M:%S")
        print(f"  📄 {file_time}: {path}")
    
    print()

def show_processing_status():
    """Show current processing status"""
    print("🔄 PROCESSING STATUS:")
    print("=" * 50)
    
    # Check processing state files
    state_files = glob.glob("OUTPUTS/CACHE/processing_states/*.json")
    
    for state_file in state_files:
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            supplier = Path(state_file).stem.replace('_processing_state', '')
            progress = f"{state.get('last_processed_index', 0)}/{state.get('total_products', 0)}"
            category = state.get('current_category_index', 0)
            
            print(f"  📊 {supplier}: {progress} products, category {category}")
        except:
            continue
    
    # Check linking maps
    link_files = glob.glob("OUTPUTS/FBA_ANALYSIS/linking_maps/**/linking_map.json", recursive=True)
    
    print("\n🔗 Linking Maps:")
    for link_file in link_files:
        try:
            with open(link_file, 'r') as f:
                data = json.load(f)
            
            supplier = Path(link_file).parent.name
            count = len(data) if isinstance(data, list) else 0
            
            print(f"  🔗 {supplier}: {count} product links")
        except:
            continue
    
    print()

def main():
    print("🎯 AMAZON FBA MULTI-AGENT DETAILED ACTIVITY REPORT")
    print("=" * 70)
    print(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    show_exec_agent_details()
    show_verify_agent_details()
    show_toggle_agent_details()
    show_exec_reports_details()
    show_file_system_status()
    show_processing_status()
    
    print("🔄 For live monitoring, run: python monitor_all_agents.py")
    print("📊 For specific agent logs, use: tail -f logs/debug/[agent]_*.log")

if __name__ == "__main__":
    main()