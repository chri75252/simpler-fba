#!/usr/bin/env python3
"""
Quick runner script for comprehensive monitoring
Usage: python monitoring/run_monitoring.py
"""

import sys
import os

# Add the base directory to Python path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

from monitoring.comprehensive_system_monitor import ComprehensiveSystemMonitor

def main():
    base_path = "/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3"
    
    print("🔍 Starting comprehensive system monitoring...")
    monitor = ComprehensiveSystemMonitor(base_path)
    report_path = monitor.generate_comprehensive_report()
    
    print(f"\n✅ COMPREHENSIVE MONITORING COMPLETE")
    print(f"📊 Report location: {report_path}")
    print(f"🔗 View with: cat '{report_path}'")

if __name__ == "__main__":
    main()