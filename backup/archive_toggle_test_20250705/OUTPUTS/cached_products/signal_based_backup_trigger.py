#!/usr/bin/env python3

import os
import signal
import time
import psutil
from datetime import datetime

class SignalBasedBackupTrigger:
    def __init__(self):
        self.process_name = "python"
        self.script_name = "passive_extraction_workflow_latest.py"
        
    def find_target_process(self):
        """Find the running FBA process"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == self.process_name:
                    cmdline = ' '.join(proc.info['cmdline'])
                    if self.script_name in cmdline:
                        return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None
    
    def send_backup_signal(self, pid):
        """Send SIGUSR1 signal to trigger backup"""
        try:
            os.kill(pid, signal.SIGUSR1)
            return True
        except Exception as e:
            print(f"❌ Error sending signal: {e}")
            return False
    
    def run_periodic_backup(self, interval_minutes=10):
        """Run periodic backup triggering"""
        print("🔄 SIGNAL-BASED BACKUP TRIGGER")
        print("=" * 50)
        print(f"Looking for process: {self.script_name}")
        print(f"Backup interval: {interval_minutes} minutes")
        print("This will send SIGUSR1 signals to trigger saves")
        
        while True:
            pid = self.find_target_process()
            
            if pid:
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"\n📡 [{timestamp}] Found target process PID: {pid}")
                
                if self.send_backup_signal(pid):
                    print(f"✅ [{timestamp}] Backup signal sent successfully")
                else:
                    print(f"❌ [{timestamp}] Failed to send backup signal")
            else:
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"⚠️  [{timestamp}] Target process not found")
            
            # Wait for the specified interval
            print(f"💤 Waiting {interval_minutes} minutes until next backup trigger...")
            time.sleep(interval_minutes * 60)

if __name__ == "__main__":
    trigger = SignalBasedBackupTrigger()
    
    print("Choose backup frequency:")
    print("1. Every 5 minutes (aggressive)")
    print("2. Every 10 minutes (balanced)")  
    print("3. Every 15 minutes (conservative)")
    
    try:
        choice = input("Enter choice (1-3): ").strip()
        
        if choice == "1":
            interval = 5
        elif choice == "2":
            interval = 10
        elif choice == "3":
            interval = 15
        else:
            print("Invalid choice, using 10 minutes")
            interval = 10
            
        trigger.run_periodic_backup(interval)
        
    except KeyboardInterrupt:
        print("\n🛑 Backup trigger stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")