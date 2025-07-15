#!/usr/bin/env python3
"""
EXEC-AGENT - Script Execution and Monitoring System
Amazon FBA Agent System v32

PURPOSE: Execute run_custom_poundwholesale.py with proper logging and monitoring
LOCATION: Amazon-FBA-Agent-System-v32-test worktree
"""

import os
import sys
import subprocess
import time
import psutil
from datetime import datetime
from pathlib import Path

class ExecAgent:
    def __init__(self, project_root="/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32"):
        self.project_root = Path(project_root)
        self.script_name = "run_custom_poundwholesale.py"
        self.log_entries = []
        self.execution_start_time = None
        self.execution_end_time = None
        self.process = None
        
    def log(self, message, level="INFO"):
        """Log messages with timestamps"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.log_entries.append(log_entry)
        print(log_entry)
        
    def validate_script_exists(self):
        """Verify the target script exists"""
        script_path = self.project_root / self.script_name
        if script_path.exists():
            self.log(f"✅ Target script found: {script_path}")
            return True
        else:
            self.log(f"❌ Target script not found: {script_path}", "ERROR")
            return False
            
    def setup_execution_environment(self):
        """Prepare environment for script execution"""
        # Ensure we're in the correct directory
        os.chdir(self.project_root)
        self.log(f"🔄 Changed working directory to: {self.project_root}")
        
        # Check Python environment
        python_version = sys.version.split()[0]
        self.log(f"🐍 Python version: {python_version}")
        
        # Check available memory
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        self.log(f"💾 Available memory: {available_gb:.1f} GB")
        
        return True
        
    def execute_script(self):
        """Execute the target script with monitoring"""
        self.log("🚀 EXEC-AGENT: Starting script execution")
        self.execution_start_time = datetime.now()
        
        # Generate unique log filename
        timestamp = self.execution_start_time.strftime("%Y%m%d_%H%M%S")
        log_filename = f"run_custom_poundwholesale_{timestamp}.log"
        log_path = self.project_root / "logs" / "debug" / log_filename
        
        # Ensure log directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Execute script with output redirection and timeout
            cmd = ["python", self.script_name]
            self.log(f"📄 Execution log: {log_path}")
            self.log(f"⚡ Executing command: {' '.join(cmd)}")
            
            # Start process with timeout
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                cwd=self.project_root
            )
            
            self.log(f"🔄 Process started with PID: {self.process.pid}")
            
            # Wait for completion with timeout (10 minutes max)
            try:
                stdout, stderr = self.process.communicate(timeout=600)
                self.execution_end_time = datetime.now()
                
                # Write complete log
                with open(log_path, 'w') as log_file:
                    log_file.write(f"EXEC-AGENT EXECUTION LOG\n")
                    log_file.write(f"Script: {self.script_name}\n")
                    log_file.write(f"Start Time: {self.execution_start_time}\n")
                    log_file.write(f"End Time: {self.execution_end_time}\n")
                    log_file.write(f"Working Directory: {self.project_root}\n")
                    log_file.write(f"Exit Code: {self.process.returncode}\n")
                    log_file.write("=" * 50 + "\n\n")
                    log_file.write("STDOUT:\n")
                    log_file.write(stdout)
                    log_file.write("\n\nSTDERR:\n")
                    log_file.write(stderr)
                    
                # Check for errors in output
                if stderr and any(keyword in stderr.upper() for keyword in ['ERROR', 'CRITICAL', 'EXCEPTION']):
                    self.log(f"🚨 Errors detected in stderr: {stderr[:200]}...", "WARNING")
                    
            except subprocess.TimeoutExpired:
                self.log("⏰ Script execution timed out after 10 minutes", "ERROR")
                self.process.kill()
                self.execution_end_time = datetime.now()
                return False, log_path
                
        except Exception as e:
            self.log(f"❌ Script execution failed: {e}", "ERROR")
            self.execution_end_time = datetime.now()
            return False, log_path
            
        # Analyze execution results
        duration = self.execution_end_time - self.execution_start_time
        exit_code = self.process.returncode
        
        if exit_code == 0:
            self.log(f"✅ Script completed successfully in {duration}")
        else:
            self.log(f"❌ Script failed with exit code {exit_code} after {duration}", "ERROR")
            
        return exit_code == 0, log_path
        
    def analyze_execution_log(self, log_path):
        """Analyze the execution log for errors and patterns"""
        if not log_path.exists():
            self.log(f"❌ Log file not found: {log_path}", "ERROR")
            return False
            
        error_count = 0
        critical_count = 0
        warning_count = 0
        
        try:
            with open(log_path, 'r') as f:
                content = f.read()
                
            # Count error types - only count actual log level errors, not words in messages
            lines = content.split('\n')
            for line in lines:
                # Only count lines with proper log level formatting (e.g., "- ERROR -", "- CRITICAL -")
                if ' - ERROR - ' in line or line.strip().endswith('- ERROR'):
                    error_count += 1
                elif ' - CRITICAL - ' in line or line.strip().endswith('- CRITICAL'):
                    critical_count += 1
                elif ' - WARNING - ' in line or line.strip().endswith('- WARNING'):
                    warning_count += 1
                    
            self.log(f"📊 Log analysis: {error_count} errors, {critical_count} critical, {warning_count} warnings")
            
            # Check for zero errors (success criteria)
            if error_count == 0 and critical_count == 0:
                self.log("✅ Zero errors/critical issues found in execution log")
                return True
            else:
                self.log("❌ Errors or critical issues found in execution log", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Failed to analyze log: {e}", "ERROR")
            return False
            
    def generate_exec_report(self, log_path, success):
        """Generate execution summary report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.project_root / f"logs/debug/exec_agent_report_{timestamp}.log"
        
        duration = "Unknown"
        if self.execution_start_time and self.execution_end_time:
            duration = str(self.execution_end_time - self.execution_start_time)
            
        with open(report_path, 'w') as f:
            f.write("EXEC-AGENT EXECUTION REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Script: {self.script_name}\n")
            f.write(f"Success: {success}\n")
            f.write(f"Duration: {duration}\n")
            f.write(f"Execution Log: {log_path}\n")
            f.write(f"Process PID: {self.process.pid if self.process else 'N/A'}\n")
            f.write("\nEXEC-AGENT LOG:\n")
            f.write("-" * 30 + "\n")
            for entry in self.log_entries:
                f.write(entry + "\n")
                
        self.log(f"📄 Exec report saved: {report_path}")
        return report_path
        
    def run_full_execution(self):
        """Execute complete execution workflow"""
        self.log("🚀 EXEC-AGENT: Starting full execution workflow")
        
        # Step 1: Validate script exists
        if not self.validate_script_exists():
            return False, None
            
        # Step 2: Setup execution environment
        if not self.setup_execution_environment():
            return False, None
            
        # Step 3: Execute script
        success, log_path = self.execute_script()
        
        # Step 4: Analyze execution log
        if success:
            log_analysis_success = self.analyze_execution_log(log_path)
            success = success and log_analysis_success
            
        # Step 5: Generate report
        report_path = self.generate_exec_report(log_path, success)
        
        if success:
            self.log("✅ EXEC-AGENT: Execution completed successfully")
            self.log("🔄 HANDOFF: Ready for verify-agent validation")
        else:
            self.log("❌ EXEC-AGENT: Execution failed")
            self.log("🔄 HANDOFF: Requires debug-agent intervention")
            
        return success, log_path

def main():
    """Main execution function"""
    exec_agent = ExecAgent()
    
    try:
        success, log_path = exec_agent.run_full_execution()
        sys.exit(0 if success else 1)
    except Exception as e:
        exec_agent.log(f"❌ EXEC-AGENT: Fatal error: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()