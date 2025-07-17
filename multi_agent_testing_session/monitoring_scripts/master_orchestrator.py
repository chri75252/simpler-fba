#!/usr/bin/env python3
"""
MASTER ORCHESTRATOR - Multi-Toggle Analysis Pipeline Controller
Amazon FBA Agent System v32

PURPOSE: Orchestrate complete multi-agent pipeline for toggle experiments
LOCATION: Main project directory
"""

import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

class MasterOrchestrator:
    def __init__(self, project_root="/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32"):
        self.project_root = Path(project_root)
        self.worktrees = {
            "prep": "/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32-prep",
            "test": "/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32-test",
            "debug": "/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32-debug"
        }
        self.log_entries = []
        self.experiments_completed = 0
        self.max_experiments = 7
        
    def log(self, message, level="INFO"):
        """Log messages with timestamps"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [ORCHESTRATOR] [{level}] {message}"
        self.log_entries.append(log_entry)
        print(log_entry)
        
    def run_agent(self, agent_name, worktree_path, script_name, args=None):
        """Execute an agent in its designated worktree"""
        if args is None:
            args = []
            
        try:
            self.log(f"🤖 Starting {agent_name}")
            
            # Change to worktree directory
            original_cwd = os.getcwd()
            os.chdir(worktree_path)
            
            # Execute agent script
            cmd = ["python", script_name] + args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30 min timeout
            
            # Restore original directory
            os.chdir(original_cwd)
            
            if result.returncode == 0:
                self.log(f"✅ {agent_name} completed successfully")
                return True, result.stdout
            else:
                self.log(f"❌ {agent_name} failed with exit code {result.returncode}", "ERROR")
                self.log(f"   Error output: {result.stderr}", "ERROR")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            self.log(f"⏰ {agent_name} timed out after 30 minutes", "ERROR")
            return False, "Timeout"
        except Exception as e:
            self.log(f"❌ {agent_name} execution failed: {e}", "ERROR")
            return False, str(e)
            
    def run_prep_agent(self):
        """Execute prep-agent for backup and validation"""
        return self.run_agent("prep-agent", self.worktrees["prep"], "prep_agent.py")
        
    def run_exec_agent(self):
        """Execute exec-agent for script execution"""
        return self.run_agent("exec-agent", self.worktrees["test"], "exec_agent.py")
        
    def run_verify_agent(self):
        """Execute verify-agent for output validation"""
        return self.run_agent("verify-agent", self.worktrees["test"], "verify_agent.py")
        
    def run_toggle_agent(self, experiment_id):
        """Execute toggle-agent for configuration changes"""
        return self.run_agent("toggle-agent", self.worktrees["test"], "toggle_agent.py", [str(experiment_id)])
        
    def run_debug_agent(self):
        """Execute debug-agent for error resolution (placeholder)"""
        self.log("🔧 DEBUG-AGENT: Manual intervention required")
        self.log("   Please review logs and fix any issues before continuing")
        return False, "Manual intervention required"
        
    def execute_single_experiment(self, experiment_id):
        """Execute complete pipeline for one experiment"""
        self.log(f"🧪 ====== EXPERIMENT {experiment_id} PIPELINE ======")
        
        # Step 1: Apply toggle configuration
        self.log(f"🔄 Step 1: Applying Experiment {experiment_id} configuration")
        success, output = self.run_toggle_agent(experiment_id)
        if not success:
            self.log(f"❌ Toggle configuration failed for Experiment {experiment_id}", "ERROR")
            return False
            
        # Step 2: Prepare environment and create backups
        self.log("🔄 Step 2: Preparing environment and creating backups")
        success, output = self.run_prep_agent()
        if not success:
            self.log("❌ Environment preparation failed", "ERROR")
            return False
            
        # Step 3: Execute main script
        self.log("🔄 Step 3: Executing main script")
        success, output = self.run_exec_agent()
        if not success:
            self.log("❌ Script execution failed", "ERROR")
            return self.handle_execution_failure()
            
        # Step 4: Verify outputs and analyze changes
        self.log("🔄 Step 4: Verifying outputs and analyzing changes")
        success, output = self.run_verify_agent()
        if not success:
            self.log("❌ Output verification failed", "ERROR")
            return self.handle_verification_failure()
            
        self.log(f"✅ Experiment {experiment_id} completed successfully")
        self.experiments_completed += 1
        return True
        
    def handle_execution_failure(self):
        """Handle script execution failures"""
        self.log("🔧 Execution failure detected - debug intervention required")
        
        # For now, return failure. In a full implementation, this would:
        # 1. Run debug-agent to analyze logs
        # 2. Apply fixes automatically if possible
        # 3. Retry execution
        # 4. Escalate to manual intervention if needed
        
        return False
        
    def handle_verification_failure(self):
        """Handle output verification failures"""
        self.log("🔧 Verification failure detected - debug intervention required")
        
        # For now, return failure. In a full implementation, this would:
        # 1. Analyze specific verification failures
        # 2. Check for partial success scenarios
        # 3. Determine if retry is warranted
        # 4. Run debug-agent if needed
        
        return False
        
    def generate_final_report(self):
        """Generate comprehensive final report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.project_root / f"FINAL_TOGGLE_ANALYSIS_REPORT_{timestamp}.md"
        
        with open(report_path, 'w') as f:
            f.write("# FINAL TOGGLE ANALYSIS REPORT\n")
            f.write("## Amazon FBA Agent System v32 - Multi-Toggle Experiment Results\n\n")
            f.write(f"**Generated**: {timestamp}\n")
            f.write(f"**Total Experiments Planned**: {self.max_experiments}\n")
            f.write(f"**Experiments Completed**: {self.experiments_completed}\n")
            f.write(f"**Success Rate**: {(self.experiments_completed/self.max_experiments)*100:.1f}%\n\n")
            
            f.write("## Executive Summary\n\n")
            if self.experiments_completed == self.max_experiments:
                f.write("✅ **SUCCESS**: All toggle experiments completed successfully.\n\n")
                f.write("The system has been comprehensively tested across all critical toggle combinations. ")
                f.write("Behavioral mapping is complete and the system is ready for production optimization.\n\n")
            else:
                f.write(f"⚠️ **PARTIAL SUCCESS**: {self.experiments_completed}/{self.max_experiments} experiments completed.\n\n")
                f.write("Some experiments encountered issues and require additional investigation.\n\n")
                
            f.write("## Detailed Results\n\n")
            f.write("See individual experiment reports in `logs/debug/` for detailed analysis:\n")
            f.write("- Toggle configuration changes\n")
            f.write("- File difference analysis\n")
            f.write("- Performance impact assessment\n")
            f.write("- Behavioral change documentation\n\n")
            
            f.write("## Next Steps\n\n")
            if self.experiments_completed == self.max_experiments:
                f.write("1. **Performance Analysis**: Review all experiment reports for optimal settings\n")
                f.write("2. **Production Configuration**: Apply best-performing toggle combinations\n")
                f.write("3. **Monitoring Setup**: Implement monitoring for identified performance indicators\n")
                f.write("4. **Documentation Update**: Update system documentation with findings\n\n")
            else:
                f.write("1. **Debug Incomplete Experiments**: Address failures in remaining experiments\n")
                f.write("2. **Retry Failed Experiments**: Re-run experiments that encountered issues\n")
                f.write("3. **Investigate Root Causes**: Analyze common failure patterns\n")
                f.write("4. **System Stability**: Ensure system stability before production use\n\n")
                
            f.write("## Master Orchestrator Log\n\n")
            f.write("```\n")
            for entry in self.log_entries:
                f.write(entry + "\n")
            f.write("```\n")
            
        self.log(f"📄 Final report generated: {report_path}")
        return report_path
        
    def run_complete_analysis(self, start_experiment=1, end_experiment=None):
        """Execute complete multi-toggle analysis pipeline"""
        if end_experiment is None:
            end_experiment = self.max_experiments
            
        self.log("🚀 MASTER ORCHESTRATOR: Starting complete multi-toggle analysis")
        self.log(f"   Target experiments: {start_experiment} to {end_experiment}")
        self.log(f"   Total experiments: {end_experiment - start_experiment + 1}")
        
        # Validate worktrees exist
        for name, path in self.worktrees.items():
            if not Path(path).exists():
                self.log(f"❌ Missing worktree: {name} at {path}", "ERROR")
                return False
                
        # Execute experiments sequentially
        for experiment_id in range(start_experiment, end_experiment + 1):
            self.log(f"\n🎯 Starting Experiment {experiment_id} of {end_experiment}")
            
            success = self.execute_single_experiment(experiment_id)
            
            if not success:
                self.log(f"❌ Experiment {experiment_id} failed - stopping pipeline", "ERROR")
                break
                
            # Brief pause between experiments
            if experiment_id < end_experiment:
                self.log("⏸️  Brief pause before next experiment...")
                time.sleep(5)
                
        # Generate final report
        final_report = self.generate_final_report()
        
        if self.experiments_completed == (end_experiment - start_experiment + 1):
            self.log("🎉 SUCCESS: Multi-toggle analysis completed successfully!")
            self.log(f"📊 All {self.experiments_completed} experiments executed and validated")
        else:
            self.log(f"⚠️  PARTIAL SUCCESS: {self.experiments_completed} of {end_experiment - start_experiment + 1} experiments completed")
            
        self.log(f"📄 Final report: {final_report}")
        return self.experiments_completed == (end_experiment - start_experiment + 1)

def main():
    """Main execution function"""
    orchestrator = MasterOrchestrator()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "single" and len(sys.argv) > 2:
            # Run single experiment
            experiment_id = int(sys.argv[2])
            success = orchestrator.execute_single_experiment(experiment_id)
            sys.exit(0 if success else 1)
        elif sys.argv[1] == "range" and len(sys.argv) > 3:
            # Run range of experiments
            start = int(sys.argv[2])
            end = int(sys.argv[3])
            success = orchestrator.run_complete_analysis(start, end)
            sys.exit(0 if success else 1)
    
    # Default: run all experiments
    try:
        success = orchestrator.run_complete_analysis()
        sys.exit(0 if success else 1)
    except Exception as e:
        orchestrator.log(f"❌ ORCHESTRATOR: Fatal error: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()