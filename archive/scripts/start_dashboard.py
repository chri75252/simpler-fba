#!/usr/bin/env python3
"""
Quick start script for FBA Dashboard Monitor
Run this to start continuous dashboard monitoring
"""

import subprocess
import sys
from pathlib import Path

def main():
    dashboard_script = Path(__file__).parent / "dashboard_monitor.py"
    
    print("🚀 Starting FBA Dashboard Monitor...")
    print("📊 Dashboard will update every 30 seconds")
    print("📂 Check DASHBOARD/live_dashboard.txt for live metrics")
    print("📁 Detailed metrics in DASHBOARD/metrics/")
    print("\nPress Ctrl+C to stop")
    
    try:
        subprocess.run([sys.executable, str(dashboard_script)], check=True)
    except KeyboardInterrupt:
        print("\n✅ Dashboard monitoring stopped")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()