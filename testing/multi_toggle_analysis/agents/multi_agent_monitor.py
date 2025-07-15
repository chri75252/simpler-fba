#!/usr/bin/env python3
"""
Intelligent Multi-Agent FBA Workflow Monitor
Real-time monitoring for Amazon FBA multi-agent testing workflow
"""

import os
import time
import re
import glob
from datetime import datetime
from pathlib import Path
import json
import threading
from collections import defaultdict, deque
import signal
import sys

class AgentMonitor:
    def __init__(self):
        self.base_dir = Path.cwd()
        self.agents = {
            'exec-agent': '../AFBAS32-test/logs/debug/run_custom_poundwholesale_*.log',
            'verify-agent': 'logs/debug/verify_*.log',
            'debug-agent': '../AFBAS32-debug/logs/debug/debug_*.log',
            'toggle-agent': 'logs/debug/toggle_*.log'
        }
        
        # Current monitoring state
        self.current_agent = 'exec-agent'
        self.agent_files = {}
        self.last_positions = {}
        self.metrics = defaultdict(dict)
        self.running = True
        self.last_summary = time.time()
        
        # Filter patterns
        self.critical_patterns = {
            'ERROR': r'ERROR|error|Error',
            'WARNING': r'WARNING|warning|Warning', 
            'SUCCESS': r'SUCCESS|success|Success|successfully|Successfully',
            'PROCESSING': r'Processing category|Found \d+ products',
            'ATTRIBUTE_ERROR': r'AttributeError',
            'BROWSER_SESSION': r'browser session|Browser session',
            'AUTH_FAILURE': r'authentication failed|login failed|auth error',
            'BROWSER_DISCONNECT': r'browser disconnect|connection lost|session ended',
            'FILE_ERROR': r'file creation error|failed to create|permission denied'
        }
        
        # Progress tracking patterns
        self.progress_patterns = {
            'products_processed': r'Product \d+ of \d+|Processed (\d+) products',
            'categories_done': r'Category \d+ of \d+|Completed category: (.+)',
            'files_generated': r'Generated file: (.+)|Created: (.+\.(?:json|csv|log))',
            'backup_created': r'Created backup: (.+\.bak\d+)',
            'toggle_changed': r'Toggle (.+) changed to (.+)'
        }
        
        self.setup_signal_handlers()
        self.print_startup_info()

    def setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False

    def print_startup_info(self):
        """Print monitoring startup information"""
        print("🚀 Amazon FBA Multi-Agent Monitoring System Started")
        print("=" * 60)
        print(f"📍 Base Directory: {self.base_dir}")
        print(f"🎯 Starting with: {self.current_agent}")
        print("📊 Monitoring Scope:")
        for agent, pattern in self.agents.items():
            print(f"   {agent}: {pattern}")
        print("\n🔍 Critical Patterns:")
        for name, pattern in self.critical_patterns.items():
            print(f"   {name}: Active")
        print("\n▶️  Starting monitoring... (Ctrl+C to stop)")
        print("=" * 60)

    def find_latest_log_file(self, pattern):
        """Find the most recent log file matching pattern"""
        try:
            # Handle relative paths
            if pattern.startswith('../'):
                search_path = self.base_dir / pattern
            else:
                search_path = self.base_dir / pattern
            
            files = glob.glob(str(search_path))
            if not files:
                return None
            
            # Get the most recent file
            latest_file = max(files, key=os.path.getmtime)
            return Path(latest_file)
        except Exception as e:
            print(f"❌ Error finding log file for {pattern}: {e}")
            return None

    def get_file_size(self, file_path):
        """Get current file size"""
        try:
            return file_path.stat().st_size if file_path.exists() else 0
        except:
            return 0

    def read_new_lines(self, file_path, last_position=0):
        """Read new lines from file since last position"""
        try:
            if not file_path.exists():
                return [], last_position
            
            current_size = self.get_file_size(file_path)
            if current_size <= last_position:
                return [], last_position
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_position)
                new_lines = f.readlines()
                new_position = f.tell()
            
            return new_lines, new_position
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            return [], last_position

    def analyze_line(self, line, agent_name):
        """Analyze a log line for patterns and metrics"""
        line = line.strip()
        if not line:
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Check critical patterns
        for pattern_name, regex in self.critical_patterns.items():
            if re.search(regex, line, re.IGNORECASE):
                priority = "🚨" if pattern_name in ['AUTH_FAILURE', 'BROWSER_DISCONNECT', 'FILE_ERROR'] else "⚠️"
                print(f"{priority} [{timestamp}] {agent_name} | {pattern_name}: {line}")
                
                # Update metrics
                if 'critical_alerts' not in self.metrics[agent_name]:
                    self.metrics[agent_name]['critical_alerts'] = 0
                self.metrics[agent_name]['critical_alerts'] += 1
        
        # Check progress patterns
        for pattern_name, regex in self.progress_patterns.items():
            match = re.search(regex, line, re.IGNORECASE)
            if match:
                print(f"📈 [{timestamp}] {agent_name} | {pattern_name}: {line}")
                
                # Update specific metrics
                if pattern_name == 'products_processed' and match.group(1):
                    self.metrics[agent_name]['products_processed'] = int(match.group(1))
                elif pattern_name == 'files_generated':
                    if 'files_generated' not in self.metrics[agent_name]:
                        self.metrics[agent_name]['files_generated'] = 0
                    self.metrics[agent_name]['files_generated'] += 1
                elif pattern_name == 'backup_created':
                    if 'backups_created' not in self.metrics[agent_name]:
                        self.metrics[agent_name]['backups_created'] = 0
                    self.metrics[agent_name]['backups_created'] += 1

    def check_agent_completion(self, agent_name, lines):
        """Check if current agent has completed its work"""
        completion_patterns = {
            'exec-agent': [r'Workflow completed', r'Processing finished', r'All categories processed'],
            'verify-agent': [r'Verification complete', r'All verifications passed'],
            'debug-agent': [r'Debug analysis complete', r'Debug session ended'],
            'toggle-agent': [r'Toggle testing complete', r'All toggles tested']
        }
        
        if agent_name not in completion_patterns:
            return False
        
        # Check recent lines for completion patterns
        recent_lines = ' '.join(lines[-10:]) if lines else ''
        for pattern in completion_patterns[agent_name]:
            if re.search(pattern, recent_lines, re.IGNORECASE):
                return True
        
        return False

    def switch_to_next_agent(self):
        """Switch to the next agent in sequence"""
        agent_sequence = list(self.agents.keys())
        current_index = agent_sequence.index(self.current_agent)
        
        if current_index < len(agent_sequence) - 1:
            next_agent = agent_sequence[current_index + 1]
            print(f"\n🔄 Auto-switching from {self.current_agent} to {next_agent}")
            self.current_agent = next_agent
            return True
        
        print(f"\n✅ All agents completed. Monitoring cycle finished.")
        return False

    def print_progress_summary(self):
        """Print progress summary every 2 minutes"""
        print("\n" + "=" * 50)
        print(f"📊 PROGRESS SUMMARY - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 50)
        
        for agent, metrics in self.metrics.items():
            if metrics:
                print(f"\n{agent.upper()}:")
                for metric, value in metrics.items():
                    print(f"  📈 {metric}: {value}")
        
        # Show current file being monitored
        current_file = self.agent_files.get(self.current_agent)
        if current_file:
            file_size = self.get_file_size(current_file)
            print(f"\n🎯 Currently monitoring: {self.current_agent}")
            print(f"📁 File: {current_file}")
            print(f"📊 File size: {file_size:,} bytes")
        
        print("=" * 50)

    def monitor_file_system(self):
        """Monitor for new backup files and toggle changes"""
        backup_pattern = self.base_dir / "**/*.bak*"
        toggle_files = [
            self.base_dir / "config/system_config.json",
            self.base_dir / "run_custom_poundwholesale.py"
        ]
        
        # Check for new backups
        backup_files = glob.glob(str(backup_pattern), recursive=True)
        current_backup_count = len(backup_files)
        
        if hasattr(self, '_last_backup_count') and current_backup_count > self._last_backup_count:
            new_backups = current_backup_count - self._last_backup_count
            print(f"💾 Detected {new_backups} new backup file(s)")
        
        self._last_backup_count = current_backup_count
        
        # Check toggle files for recent modifications
        for toggle_file in toggle_files:
            if toggle_file.exists():
                mtime = toggle_file.stat().st_mtime
                if hasattr(self, f'_last_mtime_{toggle_file.name}'):
                    last_mtime = getattr(self, f'_last_mtime_{toggle_file.name}')
                    if mtime > last_mtime:
                        print(f"⚙️  Toggle file modified: {toggle_file.name}")
                
                setattr(self, f'_last_mtime_{toggle_file.name}', mtime)

    def run(self):
        """Main monitoring loop"""
        try:
            while self.running:
                # Update current agent file
                current_pattern = self.agents[self.current_agent]
                current_file = self.find_latest_log_file(current_pattern)
                
                if current_file and current_file != self.agent_files.get(self.current_agent):
                    print(f"📁 New log file detected for {self.current_agent}: {current_file}")
                    self.agent_files[self.current_agent] = current_file
                    self.last_positions[self.current_agent] = 0
                
                # Monitor current agent
                if current_file and current_file.exists():
                    last_pos = self.last_positions.get(self.current_agent, 0)
                    new_lines, new_pos = self.read_new_lines(current_file, last_pos)
                    
                    if new_lines:
                        for line in new_lines:
                            self.analyze_line(line, self.current_agent)
                        
                        self.last_positions[self.current_agent] = new_pos
                        
                        # Check for agent completion
                        if self.check_agent_completion(self.current_agent, new_lines):
                            if not self.switch_to_next_agent():
                                break
                
                # Monitor file system changes
                self.monitor_file_system()
                
                # Print summary every 2 minutes
                if time.time() - self.last_summary > 120:
                    self.print_progress_summary()
                    self.last_summary = time.time()
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.5)
                
        except Exception as e:
            print(f"❌ Monitoring error: {e}")
        finally:
            print("\n🛑 Monitoring stopped")
            self.print_final_summary()

    def print_final_summary(self):
        """Print final summary when monitoring ends"""
        print("\n" + "=" * 60)
        print("📋 FINAL MONITORING SUMMARY")
        print("=" * 60)
        
        total_alerts = sum(metrics.get('critical_alerts', 0) for metrics in self.metrics.values())
        total_files = sum(metrics.get('files_generated', 0) for metrics in self.metrics.values())
        total_backups = sum(metrics.get('backups_created', 0) for metrics in self.metrics.values())
        
        print(f"🚨 Total Critical Alerts: {total_alerts}")
        print(f"📁 Total Files Generated: {total_files}")
        print(f"💾 Total Backups Created: {total_backups}")
        
        for agent, metrics in self.metrics.items():
            if metrics:
                print(f"\n{agent.upper()} Metrics:")
                for metric, value in metrics.items():
                    print(f"  {metric}: {value}")
        
        print("=" * 60)


def main():
    """Main entry point"""
    print("🔧 Initializing Amazon FBA Multi-Agent Monitor...")
    
    monitor = AgentMonitor()
    
    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\n👋 Monitoring interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
    finally:
        print("🏁 Monitor shutdown complete")


if __name__ == "__main__":
    main()