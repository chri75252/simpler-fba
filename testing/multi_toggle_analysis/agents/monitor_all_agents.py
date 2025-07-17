#!/usr/bin/env python3
"""
Comprehensive Multi-Agent Log Monitor
Monitors ALL agent logs with pattern matching for complete visibility
"""

import glob
import time
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import threading

class MultiAgentMonitor:
    def __init__(self):
        self.base_dir = Path.cwd()
        self.running = True
        
        # Define agent patterns to monitor ALL logs
        self.agent_patterns = {
            'EXEC-AGENT': 'logs/debug/run_custom_poundwholesale_*.log',
            'VERIFY-AGENT': 'logs/debug/verify_agent_*.log',
            'TOGGLE-AGENT': 'logs/debug/toggle_agent_*.log',
            'EXEC-REPORTS': 'logs/debug/exec_agent_report_*.log',
            'PREP-AGENT': 'logs/debug/prep_agent_*.log',
            'DEBUG-AGENT': ['logs/debug/debug_*.log', '../AFBAS32-debug/logs/debug/debug_*.log']
        }
        
        # Track file positions
        self.file_positions = {}
        self.last_activity = defaultdict(str)
        
    def get_all_matching_files(self, patterns):
        """Get all files matching the patterns"""
        if isinstance(patterns, str):
            patterns = [patterns]
        
        all_files = []
        for pattern in patterns:
            files = glob.glob(str(self.base_dir / pattern))
            all_files.extend(files)
        
        return sorted(all_files, key=lambda x: Path(x).stat().st_mtime, reverse=True)
    
    def read_new_lines(self, file_path, last_position=0):
        """Read new lines from file since last position"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return [], last_position
            
            current_size = file_path.stat().st_size
            if current_size <= last_position:
                return [], last_position
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_position)
                new_lines = f.readlines()
                new_position = f.tell()
            
            return new_lines, new_position
        except Exception as e:
            return [], last_position
    
    def format_line(self, line, agent_name, file_name):
        """Format a log line for display"""
        line = line.strip()
        if not line:
            return None
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color coding based on content
        if re.search(r'ERROR|error|Error|CRITICAL|Exception|Traceback', line):
            prefix = "🚨"
        elif re.search(r'SUCCESS|success|Successfully|✅|completed', line):
            prefix = "✅"
        elif re.search(r'WARNING|warning|Warning', line):
            prefix = "⚠️"
        elif re.search(r'Processing|Found \d+|Product \d+', line):
            prefix = "📊"
        elif re.search(r'authentication|login|Login|auth', line):
            prefix = "🔐"
        elif re.search(r'browser|Browser|playwright|chrome', line):
            prefix = "🌐"
        elif re.search(r'Generated file|Created:|Saved to|backup', line):
            prefix = "📁"
        elif re.search(r'Toggle|Experiment|Config', line):
            prefix = "⚙️"
        else:
            prefix = "📝"
        
        # Truncate very long lines
        if len(line) > 120:
            line = line[:117] + "..."
        
        return f"{prefix} [{timestamp}] {agent_name}: {line}"
    
    def monitor_agent_files(self, agent_name, patterns):
        """Monitor all files for a specific agent"""
        all_files = self.get_all_matching_files(patterns)
        
        for file_path in all_files:
            file_key = f"{agent_name}_{file_path}"
            last_pos = self.file_positions.get(file_key, 0)
            
            # For new monitoring, start from current end of file
            if file_key not in self.file_positions:
                try:
                    self.file_positions[file_key] = Path(file_path).stat().st_size
                    continue
                except:
                    continue
            
            new_lines, new_pos = self.read_new_lines(file_path, last_pos)
            
            if new_lines:
                file_name = Path(file_path).name
                for line in new_lines:
                    formatted = self.format_line(line, agent_name, file_name)
                    if formatted:
                        print(formatted)
                        self.last_activity[agent_name] = formatted
                
                self.file_positions[file_key] = new_pos
    
    def show_startup_info(self):
        """Show startup information"""
        print("🚀 COMPREHENSIVE MULTI-AGENT MONITOR")
        print("=" * 70)
        print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📍 Directory: {self.base_dir}")
        print("\n🔍 Monitoring ALL logs for these agents:")
        
        for agent_name, patterns in self.agent_patterns.items():
            if isinstance(patterns, list):
                pattern_str = ", ".join(patterns)
            else:
                pattern_str = patterns
            
            files = self.get_all_matching_files(patterns)
            file_count = len(files)
            
            print(f"  {agent_name:<15}: {file_count:>2} files | {pattern_str}")
        
        print("\n📊 Legend:")
        print("  🚨 Errors/Critical  ✅ Success  ⚠️ Warnings  📊 Progress")
        print("  🔐 Authentication   🌐 Browser  📁 Files     ⚙️ Toggles")
        print("\n🔴 LIVE MONITORING - Press Ctrl+C to stop")
        print("=" * 70)
    
    def show_periodic_summary(self):
        """Show periodic summary of last activity"""
        print(f"\n📋 ACTIVITY SUMMARY - {datetime.now().strftime('%H:%M:%S')}")
        print("-" * 50)
        
        for agent_name in self.agent_patterns.keys():
            last_msg = self.last_activity.get(agent_name, "No recent activity")
            # Remove timestamp and emoji for cleaner summary
            clean_msg = re.sub(r'[🚨✅⚠️📊🔐🌐📁⚙️📝] \[\d{2}:\d{2}:\d{2}\] \w+-?\w*: ', '', last_msg)
            if len(clean_msg) > 80:
                clean_msg = clean_msg[:77] + "..."
            print(f"  {agent_name:<15}: {clean_msg}")
        
        print("-" * 50)
    
    def run(self):
        """Main monitoring loop"""
        self.show_startup_info()
        
        summary_counter = 0
        
        try:
            while self.running:
                # Monitor each agent
                for agent_name, patterns in self.agent_patterns.items():
                    self.monitor_agent_files(agent_name, patterns)
                
                # Show summary every 30 iterations (about 1 minute)
                summary_counter += 1
                if summary_counter >= 30:
                    self.show_periodic_summary()
                    summary_counter = 0
                
                time.sleep(2)
                
        except KeyboardInterrupt:
            print(f"\n👋 Monitoring stopped at {datetime.now().strftime('%H:%M:%S')}")
            print("📋 Final activity summary:")
            self.show_periodic_summary()

if __name__ == "__main__":
    monitor = MultiAgentMonitor()
    monitor.run()