#!/usr/bin/env python3
"""
Infinite FBA Analysis Runner
Automatically restarts the FBA analysis if it stops for any reason
Designed for overnight/continuous operation
"""
import subprocess
import time
import os
import sys
import logging
from datetime import datetime
import json

# Setup logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"infinite_fba_runner_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

class InfiniteFBARunner:
    def __init__(self):
        self.restart_count = 0
        self.total_runtime = 0
        self.start_time = time.time()
        self.max_restarts_per_hour = 10  # Safety limit
        self.restart_times = []
        
    def clean_old_restart_times(self):
        """Remove restart times older than 1 hour"""
        current_time = time.time()
        self.restart_times = [t for t in self.restart_times if current_time - t < 3600]
    
    def can_restart(self):
        """Check if we can restart (not too many restarts in the last hour)"""
        self.clean_old_restart_times()
        return len(self.restart_times) < self.max_restarts_per_hour
    
    def log_system_status(self):
        """Log current system status"""
        uptime = time.time() - self.start_time
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        
        log.info(f"🔄 INFINITE RUNNER STATUS:")
        log.info(f"  Total Runtime: {hours}h {minutes}m")
        log.info(f"  Restart Count: {self.restart_count}")
        log.info(f"  Restarts in last hour: {len(self.restart_times)}")
        
        # Check output files
        try:
            reports_dir = "OUTPUTS/FBA_ANALYSIS/financial_reports"
            if os.path.exists(reports_dir):
                csv_files = [f for f in os.listdir(reports_dir) if f.endswith('.csv')]
                log.info(f"  CSV Reports Generated: {len(csv_files)}")
                if csv_files:
                    latest_csv = max(csv_files, key=lambda f: os.path.getmtime(os.path.join(reports_dir, f)))
                    log.info(f"  Latest Report: {latest_csv}")
            
            cache_dir = "OUTPUTS/FBA_ANALYSIS/amazon_cache"
            if os.path.exists(cache_dir):
                cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.json')]
                log.info(f"  Amazon Cache Files: {len(cache_files)}")
                
        except Exception as e:
            log.warning(f"Error checking output status: {e}")
    
    def run_fba_analysis(self):
        """Run the FBA analysis process"""
        cmd = [
            sys.executable, 
            "passive_extraction_workflow_latest.py", 
            "--max-products", "0"
        ]
        
        log.info(f"🚀 Starting FBA Analysis (Attempt #{self.restart_count + 1})")
        log.info(f"Command: {' '.join(cmd)}")
        
        try:
            # Run the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    # Log important output
                    if any(keyword in output.lower() for keyword in [
                        'error', 'exception', 'failed', 'unlimited mode', 
                        'processing', 'financial report saved', 'completed'
                    ]):
                        log.info(f"PROCESS: {output.strip()}")
            
            return_code = process.poll()
            log.info(f"Process finished with return code: {return_code}")
            
            return return_code == 0
            
        except Exception as e:
            log.error(f"❌ Error running FBA analysis: {e}")
            return False
    
    def wait_before_restart(self, wait_time=30):
        """Wait before restarting with countdown"""
        log.info(f"⏳ Waiting {wait_time} seconds before restart...")
        for i in range(wait_time, 0, -5):
            log.info(f"  Restarting in {i} seconds...")
            time.sleep(5)
    
    def run_infinite(self):
        """Main infinite loop"""
        log.info("🌟 STARTING INFINITE FBA ANALYSIS RUNNER")
        log.info("This will run continuously until manually stopped")
        log.info("Press Ctrl+C to stop gracefully")
        
        try:
            while True:
                self.log_system_status()
                
                # Check restart limits
                if not self.can_restart():
                    log.error(f"❌ Too many restarts ({len(self.restart_times)}) in the last hour. Waiting...")
                    time.sleep(3600)  # Wait 1 hour
                    continue
                
                # Run the analysis
                success = self.run_fba_analysis()
                
                if success:
                    log.info("✅ FBA Analysis completed successfully!")
                    log.info("🔄 Restarting for continuous operation...")
                else:
                    log.warning("⚠️ FBA Analysis ended with errors. Restarting...")
                    self.restart_times.append(time.time())
                
                self.restart_count += 1
                
                # Wait before restart (shorter wait if successful)
                wait_time = 10 if success else 30
                self.wait_before_restart(wait_time)
                
        except KeyboardInterrupt:
            log.info("🛑 Infinite runner stopped by user (Ctrl+C)")
        except Exception as e:
            log.error(f"❌ Fatal error in infinite runner: {e}")
            log.info("🔄 Attempting to restart in 60 seconds...")
            time.sleep(60)
            # Restart the infinite runner itself
            os.execv(sys.executable, [sys.executable] + sys.argv)

if __name__ == "__main__":
    runner = InfiniteFBARunner()
    runner.run_infinite()
