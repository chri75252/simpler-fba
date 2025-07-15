#!/usr/bin/env python3
"""
TOGGLE-AGENT - Configuration Management and Experiment Design System
Amazon FBA Agent System v32

PURPOSE: Apply toggle experiments and manage configuration changes
LOCATION: Amazon-FBA-Agent-System-v32-test worktree
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
import copy

class ToggleAgent:
    def __init__(self, project_root="/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32"):
        self.project_root = Path(project_root)
        self.config_path = self.project_root / "config/system_config.json"
        self.toggle_plan_path = self.project_root / "toggle_test_plan.md"
        self.log_entries = []
        self.experiments = self._define_experiments()
        self.current_experiment = 0
        
    def log(self, message, level="INFO"):
        """Log messages with timestamps"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.log_entries.append(log_entry)
        print(log_entry)
        
    def _define_experiments(self):
        """Define all toggle experiments"""
        return {
            1: {
                "name": "Processing & System Limits",
                "description": "Core throughput and batch sizing",
                "toggles": {
                    "processing_limits.max_products_per_category": {"from": 3, "to": 5},
                    "processing_limits.max_price_gbp": {"from": 20.0, "to": 25.0},
                    "system.max_products_per_cycle": {"from": 2, "to": 3}
                },
                "expected_effects": [
                    "Increased product extraction per category",
                    "Higher price range coverage", 
                    "Larger Amazon analysis batches"
                ]
            },
            2: {
                "name": "Cache Control & Hybrid Processing",
                "description": "Cache behavior and processing mode",
                "toggles": {
                    "supplier_cache_control.update_frequency_products": {"from": 1, "to": 3},
                    "hybrid_processing.chunked.chunk_size_categories": {"from": 1, "to": 2},
                    "hybrid_processing.chunked.enabled": {"from": True, "to": False}
                },
                "expected_effects": [
                    "Reduced cache update frequency",
                    "Larger category chunks",
                    "Switch to sequential processing mode"
                ]
            },
            3: {
                "name": "Batch Synchronization & Financial Reporting",
                "description": "Unified batch management",
                "toggles": {
                    "batch_synchronization.enabled": {"from": False, "to": True},
                    "batch_synchronization.target_batch_size": {"from": 3, "to": 2},
                    "system.financial_report_batch_size": {"from": 2, "to": 1}
                },
                "expected_effects": [
                    "Synchronized batch sizes across system",
                    "More frequent financial report generation",
                    "Aligned processing cycles"
                ]
            },
            4: {
                "name": "Advanced Progress Tracking",
                "description": "Progress persistence and recovery",
                "toggles": {
                    "supplier_extraction_progress.recovery_mode": {"from": "subcategory_resume", "to": "product_resume"},
                    "supplier_extraction_progress.progress_display.update_frequency_products": {"from": 1, "to": 2},
                    "supplier_extraction_progress.state_persistence.batch_save_frequency": {"from": 1, "to": 3}
                },
                "expected_effects": [
                    "Finer-grained recovery granularity",
                    "Less frequent progress updates",
                    "Reduced state save frequency"
                ]
            },
            5: {
                "name": "System Capacity & Analysis Limits",
                "description": "Maximum system throughput",
                "toggles": {
                    "system.max_products": {"from": 12, "to": 18},
                    "system.max_analyzed_products": {"from": 6, "to": 10},
                    "system.linking_map_batch_size": {"from": 2, "to": 3}
                },
                "expected_effects": [
                    "Higher total product processing",
                    "More products sent for Amazon analysis",
                    "Less frequent linking map saves"
                ]
            },
            6: {
                "name": "Performance Matching Thresholds",
                "description": "Amazon matching quality vs speed",
                "toggles": {
                    "performance.matching_thresholds.title_similarity": {"from": 0.25, "to": 0.4},
                    "performance.matching_thresholds.confidence_medium": {"from": 0.45, "to": 0.6},
                    "performance.matching_thresholds.high_title_similarity": {"from": 0.75, "to": 0.85}
                },
                "expected_effects": [
                    "Stricter matching criteria",
                    "Higher confidence requirements",
                    "Potentially fewer but higher quality matches"
                ]
            },
            7: {
                "name": "Authentication & Circuit Breaker",
                "description": "System reliability and authentication behavior",
                "toggles": {
                    "authentication.primary_periodic_interval": {"from": 100, "to": 150},
                    "authentication.circuit_breaker.failure_threshold": {"from": 3, "to": 2},
                    "authentication.max_consecutive_auth_failures": {"from": 3, "to": 5}
                },
                "expected_effects": [
                    "Less frequent authentication checks",
                    "Earlier circuit breaker activation", 
                    "Higher auth failure tolerance"
                ]
            }
        }
        
    def load_current_config(self):
        """Load current system configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            self.log(f"✅ Loaded config from: {self.config_path}")
            return config
        except Exception as e:
            self.log(f"❌ Failed to load config: {e}", "ERROR")
            return None
            
    def save_config(self, config, backup_original=True):
        """Save configuration with optional backup"""
        try:
            if backup_original and self.config_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.config_path.with_suffix(f".{timestamp}.bak")
                config_content = self.config_path.read_text()
                backup_path.write_text(config_content)
                self.log(f"📄 Config backed up to: {backup_path.name}")
                
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            self.log(f"✅ Config saved to: {self.config_path}")
            return True
        except Exception as e:
            self.log(f"❌ Failed to save config: {e}", "ERROR")
            return False
            
    def get_nested_value(self, config, key_path):
        """Get value from nested config using dot notation"""
        keys = key_path.split('.')
        value = config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return None
            
    def set_nested_value(self, config, key_path, value):
        """Set value in nested config using dot notation"""
        keys = key_path.split('.')
        current = config
        
        # Navigate to parent of target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
            
        # Set the target value
        current[keys[-1]] = value
        
    def apply_experiment(self, experiment_id):
        """Apply a specific experiment's toggle changes"""
        if experiment_id not in self.experiments:
            self.log(f"❌ Invalid experiment ID: {experiment_id}", "ERROR")
            return False
            
        experiment = self.experiments[experiment_id]
        self.log(f"🧪 Applying Experiment {experiment_id}: {experiment['name']}")
        
        # Load current config
        config = self.load_current_config()
        if not config:
            return False
            
        # Store original values for verification
        original_values = {}
        
        # Apply each toggle change
        for toggle_path, change in experiment['toggles'].items():
            original_value = self.get_nested_value(config, toggle_path)
            expected_from = change['from']
            new_value = change['to']
            
            # Verify current value matches expected "from" value
            if original_value != expected_from:
                self.log(f"⚠️  {toggle_path}: Current value {original_value} != expected {expected_from}", "WARNING")
                
            original_values[toggle_path] = original_value
            self.set_nested_value(config, toggle_path, new_value)
            
            self.log(f"🔄 {toggle_path}: {original_value} → {new_value}")
            
        # Save updated config
        if not self.save_config(config):
            return False
            
        # Verify changes were applied correctly
        verification_config = self.load_current_config()
        verification_success = True
        
        for toggle_path, change in experiment['toggles'].items():
            current_value = self.get_nested_value(verification_config, toggle_path)
            expected_value = change['to']
            
            if current_value == expected_value:
                self.log(f"✅ Verified: {toggle_path} = {current_value}")
            else:
                self.log(f"❌ Verification failed: {toggle_path} = {current_value}, expected {expected_value}", "ERROR")
                verification_success = False
                
        if verification_success:
            # Commit changes to git
            self.commit_experiment_changes(experiment_id, experiment)
            self.log(f"✅ Experiment {experiment_id} applied successfully")
        else:
            self.log(f"❌ Experiment {experiment_id} verification failed", "ERROR")
            
        return verification_success
        
    def commit_experiment_changes(self, experiment_id, experiment):
        """Commit toggle changes to git with descriptive message"""
        try:
            # Add config file
            subprocess.run(['git', 'add', str(self.config_path)], cwd=self.project_root, check=True)
            
            # Create commit message
            commit_msg = f"Experiment {experiment_id}: {experiment['name']}\n\n"
            commit_msg += "Toggle changes:\n"
            for toggle_path, change in experiment['toggles'].items():
                commit_msg += f"- {toggle_path}: {change['from']} → {change['to']}\n"
            commit_msg += f"\nExpected effects: {', '.join(experiment['expected_effects'])}"
            
            # Commit changes
            subprocess.run(['git', 'commit', '-m', commit_msg], cwd=self.project_root, check=True)
            self.log(f"📝 Git commit created for Experiment {experiment_id}")
            
        except subprocess.CalledProcessError as e:
            self.log(f"⚠️  Git commit failed: {e}", "WARNING")
            
    def update_toggle_plan_log(self, experiment_id, success, notes=""):
        """Update the toggle test plan with experiment results"""
        if not self.toggle_plan_path.exists():
            self.log("⚠️  Toggle plan file not found", "WARNING")
            return
            
        try:
            content = self.toggle_plan_path.read_text()
            
            # Find the experiment log table
            lines = content.split('\n')
            table_start = -1
            for i, line in enumerate(lines):
                if '| Exp # | Date |' in line:
                    table_start = i + 2  # Skip header and separator
                    break
                    
            if table_start == -1:
                self.log("⚠️  Could not find experiment log table", "WARNING")
                return
                
            # Find the row for this experiment
            experiment_row = -1
            for i in range(table_start, len(lines)):
                if lines[i].startswith(f"| {experiment_id}"):
                    experiment_row = i
                    break
                    
            if experiment_row == -1:
                self.log(f"⚠️  Could not find row for experiment {experiment_id}", "WARNING")
                return
                
            # Update the row
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            result = "SUCCESS" if success else "FAILED"
            experiment = self.experiments[experiment_id]
            
            toggle_summary = ", ".join([f"{k.split('.')[-1]}:{v['from']}→{v['to']}" 
                                      for k, v in experiment['toggles'].items()])
            
            updated_row = f"| {experiment_id}     | {timestamp} | {toggle_summary} | {result} | {notes} | | |"
            lines[experiment_row] = updated_row
            
            # Write back to file
            self.toggle_plan_path.write_text('\n'.join(lines))
            self.log(f"📄 Updated toggle plan with Experiment {experiment_id} results")
            
        except Exception as e:
            self.log(f"❌ Failed to update toggle plan: {e}", "ERROR")
            
    def list_available_experiments(self):
        """List all available experiments"""
        self.log("🧪 Available Toggle Experiments:")
        for exp_id, experiment in self.experiments.items():
            self.log(f"   {exp_id}. {experiment['name']}: {experiment['description']}")
            
    def generate_toggle_report(self, experiment_id, success):
        """Generate detailed toggle application report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.project_root / f"logs/debug/toggle_agent_exp{experiment_id}_report_{timestamp}.log"
        
        # Ensure log directory exists
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        experiment = self.experiments[experiment_id]
        
        with open(report_path, 'w') as f:
            f.write("TOGGLE-AGENT EXPERIMENT REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Experiment ID: {experiment_id}\n")
            f.write(f"Experiment Name: {experiment['name']}\n")
            f.write(f"Description: {experiment['description']}\n")
            f.write(f"Success: {success}\n")
            f.write(f"Timestamp: {timestamp}\n\n")
            
            f.write("TOGGLE CHANGES APPLIED:\n")
            f.write("-" * 30 + "\n")
            for toggle_path, change in experiment['toggles'].items():
                f.write(f"{toggle_path}:\n")
                f.write(f"  FROM: {change['from']}\n")
                f.write(f"  TO:   {change['to']}\n\n")
                
            f.write("EXPECTED EFFECTS:\n")
            f.write("-" * 30 + "\n")
            for effect in experiment['expected_effects']:
                f.write(f"- {effect}\n")
                
            f.write("\nTOGGLE-AGENT LOG:\n")
            f.write("-" * 30 + "\n")
            for entry in self.log_entries:
                f.write(entry + "\n")
                
        self.log(f"📄 Toggle report saved: {report_path}")
        return report_path
        
    def run_experiment(self, experiment_id):
        """Execute a complete experiment workflow"""
        self.log(f"🚀 TOGGLE-AGENT: Starting Experiment {experiment_id}")
        
        if experiment_id not in self.experiments:
            self.log(f"❌ Invalid experiment ID: {experiment_id}", "ERROR")
            return False
            
        # Apply the experiment
        success = self.apply_experiment(experiment_id)
        
        # Update toggle plan
        self.update_toggle_plan_log(experiment_id, success)
        
        # Generate report
        report_path = self.generate_toggle_report(experiment_id, success)
        
        if success:
            self.log(f"✅ TOGGLE-AGENT: Experiment {experiment_id} completed successfully")
            self.log("🔄 HANDOFF: Ready for prep-agent → exec-agent → verify-agent cycle")
        else:
            self.log(f"❌ TOGGLE-AGENT: Experiment {experiment_id} failed")
            
        return success

def main():
    """Main execution function"""
    if len(sys.argv) < 2:
        print("Usage: python toggle_agent.py <experiment_id>")
        print("       python toggle_agent.py list")
        sys.exit(1)
        
    toggle_agent = ToggleAgent()
    
    try:
        if sys.argv[1] == "list":
            toggle_agent.list_available_experiments()
            sys.exit(0)
        else:
            experiment_id = int(sys.argv[1])
            success = toggle_agent.run_experiment(experiment_id)
            sys.exit(0 if success else 1)
    except Exception as e:
        toggle_agent.log(f"❌ TOGGLE-AGENT: Fatal error: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()