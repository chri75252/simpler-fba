#!/usr/bin/env python3
"""
Unified Multi-Agent Monitoring Dashboard
Real-time monitoring dashboard for Amazon FBA multi-agent workflow
"""

import os
import time
import re
import glob
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict, deque
import threading
import signal
import sys

class UnifiedMonitorDashboard:
    def __init__(self):
        self.base_dir = Path.cwd()
        self.running = True
        
        # Agent configurations
        self.agents = {
            'exec-agent': {
                'pattern': 'logs/debug/run_custom_poundwholesale_*.log',
                'alt_pattern': '../AFBAS32-test/logs/debug/run_custom_poundwholesale_*.log',
                'color': '🚀',
                'focus': 'Main execution workflow'
            },
            'verify-agent': {
                'pattern': 'logs/debug/verify_*.log',
                'color': '✅',
                'focus': 'Verification processes'
            },
            'debug-agent': {
                'pattern': '../AFBAS32-debug/logs/debug/debug_*.log',
                'color': '🔧',
                'focus': 'Debug analysis'
            },
            'toggle-agent': {
                'pattern': 'logs/debug/toggle_*.log',
                'color': '⚙️',
                'focus': 'Toggle testing'
            }
        }
        
        # Monitoring state
        self.last_positions = {}
        self.metrics = defaultdict(lambda: defaultdict(int))
        self.recent_events = deque(maxlen=20)
        self.file_counts = defaultdict(int)
        self.last_summary = time.time()
        
        # Patterns for analysis
        self.critical_patterns = {
            'CRITICAL_ERROR': r'ERROR|error|Error|CRITICAL|critical',
            'AUTH_ISSUE': r'authentication failed|login failed|auth error',
            'BROWSER_ISSUE': r'browser disconnect|connection lost|session ended',
            'SUCCESS': r'SUCCESS|success|Successfully|✅',
            'PROGRESS': r'Processing category|Found \d+ products|Product \d+ of \d+',
            'FILE_OPS': r'Generated file|Created:|Saved to|backup'
        }
        
        self.setup_signal_handlers()

    def setup_signal_handlers(self):
        """Setup graceful shutdown"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.running = False
        print(f"\n🛑 Received signal {signum}, shutting down...")

    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def find_latest_log_file(self, pattern, alt_pattern=None):
        """Find the most recent log file"""
        try:
            files = glob.glob(str(self.base_dir / pattern))
            
            # Try alternative pattern if no files found
            if not files and alt_pattern:
                files = glob.glob(str(self.base_dir / alt_pattern))
            
            if files:
                return max(files, key=os.path.getmtime)
            return None
        except:
            return None

    def read_new_lines(self, file_path, last_position=0):
        """Read new lines from file"""
        try:
            if not Path(file_path).exists():
                return [], last_position
            
            current_size = Path(file_path).stat().st_size
            if current_size <= last_position:
                return [], last_position
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_position)
                new_lines = f.readlines()
                new_position = f.tell()
            
            return new_lines, new_position
        except:
            return [], last_position

    def analyze_line(self, line, agent_name):
        """Analyze a log line and update metrics"""
        line = line.strip()
        if not line:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Check patterns
        for pattern_name, regex in self.critical_patterns.items():
            if re.search(regex, line, re.IGNORECASE):
                self.metrics[agent_name][pattern_name] += 1
                
                # Add to recent events
                priority = "🚨" if pattern_name in ['CRITICAL_ERROR', 'AUTH_ISSUE', 'BROWSER_ISSUE'] else "📊"
                event = f"{priority} [{timestamp}] {agent_name}: {pattern_name}"
                self.recent_events.append(event)
                break

    def monitor_files(self):
        """Monitor file system changes"""
        # Check key directories
        paths_to_monitor = [
            ('OUTPUTS', self.base_dir / 'OUTPUTS'),
            ('logs', self.base_dir / 'logs'),
            ('config', self.base_dir / 'config'),
            ('backups', self.base_dir / '**/*.bak*')
        ]
        
        for name, path in paths_to_monitor:
            if name == 'backups':
                files = glob.glob(str(path), recursive=True)
                current_count = len(files)
            elif path.exists():
                files = list(path.rglob("*")) if path.is_dir() else [path]
                current_count = len([f for f in files if f.is_file()])
            else:
                current_count = 0
            
            if name in self.file_counts and current_count > self.file_counts[name]:
                diff = current_count - self.file_counts[name]
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.recent_events.append(f"📁 [{timestamp}] {name}: +{diff} files (total: {current_count})")
            
            self.file_counts[name] = current_count

    def get_processing_status(self):
        """Get current processing status from state files"""
        status = {}
        state_pattern = str(self.base_dir / "OUTPUTS/CACHE/processing_states/*.json")
        state_files = glob.glob(state_pattern)
        
        for state_file in state_files:
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                
                supplier = Path(state_file).stem.replace('_processing_state', '')
                status[supplier] = {
                    'progress': f"{state.get('last_processed_index', 0)}/{state.get('total_products', 0)}",
                    'current_category': state.get('current_category_index', 0)
                }
            except:
                continue
        
        return status

    def display_dashboard(self):
        """Display the unified monitoring dashboard"""
        self.clear_screen()
        
        print("🚀 AMAZON FBA MULTI-AGENT MONITORING DASHBOARD")
        print("=" * 80)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 📍 {self.base_dir}")
        print("=" * 80)
        
        # Agent Status Section
        print("\n📊 AGENT STATUS:")
        print("-" * 40)
        for agent_name, config in self.agents.items():
            latest_file = self.find_latest_log_file(config['pattern'], config.get('alt_pattern'))
            status = "🟢 Active" if latest_file and Path(latest_file).exists() else "🔴 No logs"
            
            file_name = Path(latest_file).name if latest_file else "None"
            print(f"{config['color']} {agent_name:<15} {status:<10} | {file_name}")
        
        # Metrics Section
        print("\n📈 METRICS SUMMARY:")
        print("-" * 40)
        for agent_name, agent_metrics in self.metrics.items():
            if agent_metrics:
                print(f"{agent_name}:")
                for metric, count in agent_metrics.items():
                    print(f"  {metric:<15}: {count:>3}")
        
        # File System Status
        print("\n📁 FILE SYSTEM STATUS:")
        print("-" * 40)
        for name, count in self.file_counts.items():
            print(f"{name:<10}: {count:>5} files")
        
        # Processing Status
        processing_status = self.get_processing_status()
        if processing_status:
            print("\n🔄 PROCESSING STATUS:")
            print("-" * 40)
            for supplier, status in processing_status.items():
                print(f"{supplier:<20}: {status['progress']:<10} | Category: {status['current_category']}")
        
        # Recent Events
        print("\n📰 RECENT EVENTS (Last 20):")
        print("-" * 40)
        if self.recent_events:
            for event in list(self.recent_events)[-10:]:  # Show last 10
                print(f"  {event}")
        else:
            print("  No recent events")
        
        # Live Monitoring Indicator
        print("\n" + "=" * 80)
        print("🔴 LIVE MONITORING | Press Ctrl+C to stop | Updates every 2 seconds")
        print("=" * 80)

    def monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Monitor each agent
                for agent_name, config in self.agents.items():
                    latest_file = self.find_latest_log_file(config['pattern'], config.get('alt_pattern'))
                    
                    if latest_file:
                        file_key = f"{agent_name}_{latest_file}"
                        last_pos = self.last_positions.get(file_key, 0)
                        new_lines, new_pos = self.read_new_lines(latest_file, last_pos)
                        
                        if new_lines:
                            for line in new_lines:
                                self.analyze_line(line, agent_name)
                            
                            self.last_positions[file_key] = new_pos
                
                # Monitor file system
                self.monitor_files()
                
                # Update display every 2 seconds
                self.display_dashboard()
                
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                time.sleep(5)

    def run(self):
        """Start the monitoring dashboard"""
        print("🚀 Starting Amazon FBA Multi-Agent Monitoring Dashboard...")
        print("📊 Initializing monitoring systems...")
        time.sleep(2)
        
        try:
            self.monitor_loop()
        except KeyboardInterrupt:
            print("\n👋 Dashboard stopped by user")
        except Exception as e:
            print(f"❌ Dashboard error: {e}")
        finally:
            self.running = False
            print("\n🏁 Dashboard shutdown complete")

if __name__ == "__main__":
    dashboard = UnifiedMonitorDashboard()
    dashboard.run()