#!/usr/bin/env python3
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
    print(f"\n📊 SUMMARY - {datetime.now().strftime('%H:%M:%S')}")
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
        print("\n👋 Metrics monitor stopped")
        break
    except Exception as e:
        print(f"❌ Metrics monitor error: {e}")
        time.sleep(5)
