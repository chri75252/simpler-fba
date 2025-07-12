#!/usr/bin/env python3
"""
Quick flag checker for FBA Monitoring System
Provides a summary of current monitoring flags for easy review.
"""

import json
from pathlib import Path
from datetime import datetime
import argparse

def format_timestamp(timestamp_str):
    """Format timestamp for display"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp_str

def get_flag_summary(base_dir="."):
    """Get summary of all monitoring flags"""
    flags_dir = Path(base_dir) / "MONITORING_FLAGS"
    
    if not flags_dir.exists():
        return "No monitoring flags directory found."
    
    flag_files = list(flags_dir.glob("*.json"))
    
    if not flag_files:
        return "✅ No monitoring flags found - system appears healthy!"
    
    flags_by_severity = {"CRITICAL": [], "WARNING": [], "INFO": []}
    
    for flag_file in flag_files:
        try:
            with open(flag_file, 'r') as f:
                flag_data = json.load(f)
                severity = flag_data.get('severity', 'INFO')
                flags_by_severity[severity].append(flag_data)
        except Exception as e:
            print(f"Error reading {flag_file}: {e}")
    
    # Build summary
    summary = []
    summary.append("🚨 FBA MONITORING FLAGS SUMMARY")
    summary.append("=" * 50)
    
    total_flags = sum(len(flags) for flags in flags_by_severity.values())
    summary.append(f"Total Flags: {total_flags}")
    summary.append("")
    
    # Show flags by severity
    for severity in ["CRITICAL", "WARNING", "INFO"]:
        flags = flags_by_severity[severity]
        if not flags:
            continue
            
        icon = {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "🔵"}[severity]
        summary.append(f"{icon} {severity} FLAGS ({len(flags)}):")
        summary.append("-" * 30)
        
        for flag in sorted(flags, key=lambda x: x.get('timestamp', ''), reverse=True):
            flag_type = flag.get('flag_type', 'UNKNOWN')
            timestamp = format_timestamp(flag.get('timestamp', ''))
            summary_text = flag.get('details', {}).get('summary', 'No summary')
            
            summary.append(f"  • {flag_type}")
            summary.append(f"    Time: {timestamp}")
            summary.append(f"    Issue: {summary_text}")
            
            # Add specific details for important flags
            if severity == "CRITICAL":
                details = flag.get('details', {})
                if 'recommendation' in details:
                    summary.append(f"    Action: {details['recommendation']}")
            
            summary.append("")
    
    return "\n".join(summary)

def main():
    parser = argparse.ArgumentParser(description="Check FBA monitoring flags")
    parser.add_argument("--base-dir", default=".", help="Base directory for FBA system")
    parser.add_argument("--critical-only", action="store_true", help="Show only critical flags")
    
    args = parser.parse_args()
    
    print(get_flag_summary(args.base_dir))
    
    if args.critical_only:
        flags_dir = Path(args.base_dir) / "MONITORING_FLAGS"
        critical_count = 0
        
        for flag_file in flags_dir.glob("*.json"):
            try:
                with open(flag_file, 'r') as f:
                    flag_data = json.load(f)
                    if flag_data.get('severity') == 'CRITICAL':
                        critical_count += 1
            except:
                pass
        
        if critical_count > 0:
            print(f"\n⚠️  {critical_count} CRITICAL flags require immediate attention!")
            exit(1)
        else:
            print("\n✅ No critical flags found.")
            exit(0)

if __name__ == "__main__":
    main()
