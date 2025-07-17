#!/usr/bin/env python3
"""
VERIFY-AGENT - Output Validation and Difference Analysis System
Amazon FBA Agent System v32

PURPOSE: Validate all mandatory outputs and analyze changes vs previous run
LOCATION: Amazon-FBA-Agent-System-v32-test worktree
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
import glob

class VerifyAgent:
    def __init__(self, project_root="/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32"):
        self.project_root = Path(project_root)
        self.mandatory_outputs = [
            "OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json",
            "OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json",
            "OUTPUTS/FBA_ANALYSIS/linking_maps/poundwholesale.co.uk/linking_map.json"
        ]
        self.dynamic_outputs = {
            "amazon_cache": "OUTPUTS/FBA_ANALYSIS/amazon_cache/amazon_*.json",
            "financial_reports": "OUTPUTS/FBA_ANALYSIS/financial_reports/**/*.csv"
        }
        self.log_entries = []
        self.validation_results = {}
        
    def log(self, message, level="INFO"):
        """Log messages with timestamps"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.log_entries.append(log_entry)
        print(log_entry)
        
    def validate_mandatory_outputs(self, baseline_timestamp=None):
        """Validate all 6 mandatory outputs exist with proper timestamps"""
        self.log("🔍 VERIFY-AGENT: Validating mandatory outputs")
        
        missing_outputs = []
        stale_outputs = []
        
        # Check static mandatory outputs
        for output_path in self.mandatory_outputs:
            full_path = self.project_root / output_path
            
            if not full_path.exists():
                missing_outputs.append(str(output_path))
                self.log(f"❌ Missing: {output_path}", "ERROR")
            else:
                # Check timestamp if baseline provided
                if baseline_timestamp:
                    file_mtime = datetime.fromtimestamp(full_path.stat().st_mtime)
                    if file_mtime < baseline_timestamp:
                        stale_outputs.append(str(output_path))
                        self.log(f"⚠️  Stale: {output_path} (modified: {file_mtime})", "WARNING")
                    else:
                        self.log(f"✅ Fresh: {output_path} (modified: {file_mtime})")
                else:
                    self.log(f"✅ Exists: {output_path}")
                    
        # Check dynamic outputs (at least 1 new file required)
        for output_type, pattern in self.dynamic_outputs.items():
            full_pattern = str(self.project_root / pattern)
            matching_files = glob.glob(full_pattern)
            
            if not matching_files:
                missing_outputs.append(f"{output_type} (pattern: {pattern})")
                self.log(f"❌ No files found for {output_type}: {pattern}", "ERROR")
            else:
                new_files = []
                if baseline_timestamp:
                    for file_path in matching_files:
                        file_mtime = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
                        if file_mtime >= baseline_timestamp:
                            new_files.append(file_path)
                            
                    if new_files:
                        self.log(f"✅ {output_type}: {len(new_files)} new files since baseline")
                        for file_path in new_files[:3]:  # Show first 3
                            self.log(f"   📄 {Path(file_path).name}")
                    else:
                        stale_outputs.append(f"{output_type} (no new files)")
                        self.log(f"⚠️  {output_type}: No new files since baseline", "WARNING")
                else:
                    self.log(f"✅ {output_type}: {len(matching_files)} files found")
                    
        # Store validation results
        self.validation_results['missing_outputs'] = missing_outputs
        self.validation_results['stale_outputs'] = stale_outputs
        
        if missing_outputs:
            self.log(f"❌ VALIDATION FAILED: {len(missing_outputs)} missing outputs", "ERROR")
            return False
        elif stale_outputs:
            self.log(f"⚠️  VALIDATION WARNING: {len(stale_outputs)} stale outputs", "WARNING")
            return True  # Warning but not failure
        else:
            self.log("✅ VALIDATION SUCCESS: All mandatory outputs present and fresh")
            return True
            
    def find_latest_execution_log(self):
        """Find the most recent execution log"""
        log_pattern = str(self.project_root / "logs/debug/run_custom_poundwholesale_*.log")
        log_files = glob.glob(log_pattern)
        
        if not log_files:
            self.log("❌ No execution logs found", "ERROR")
            return None
            
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
        latest_log = Path(log_files[0])
        
        self.log(f"📄 Latest execution log: {latest_log.name}")
        return latest_log
        
    def validate_execution_log(self, log_path):
        """Validate execution log for zero errors/critical issues"""
        if not log_path or not log_path.exists():
            self.log("❌ Execution log not found", "ERROR")
            return False
            
        try:
            with open(log_path, 'r') as f:
                content = f.read()
                
            # Count error types - only count actual log level errors, not words in messages
            lines = content.split('\n')
            error_count = 0
            critical_count = 0
            
            for line in lines:
                # Only count lines with proper log level formatting (e.g., "- ERROR -", "- CRITICAL -")
                if ' - ERROR - ' in line or line.strip().endswith('- ERROR'):
                    error_count += 1
                elif ' - CRITICAL - ' in line or line.strip().endswith('- CRITICAL'):
                    critical_count += 1
                    
            self.log(f"📊 Execution log analysis: {error_count} errors, {critical_count} critical")
            
            if error_count == 0 and critical_count == 0:
                self.log("✅ Zero errors/critical issues in execution log")
                return True
            else:
                self.log("❌ Errors or critical issues found in execution log", "ERROR")
                # Show first few errors for debugging
                error_lines = [line for line in lines if 'ERROR' in line.upper() or 'CRITICAL' in line.upper()]
                for error_line in error_lines[:3]:
                    self.log(f"   🚨 {error_line.strip()}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Failed to validate execution log: {e}", "ERROR")
            return False
            
    def analyze_file_differences(self):
        """Analyze differences between current files and .bak1 versions"""
        self.log("🔍 Analyzing file differences vs .bak1 versions")
        
        diff_results = {}
        
        for output_path in self.mandatory_outputs:
            current_file = self.project_root / output_path
            backup_file = Path(f"{current_file}.bak1")
            
            if not current_file.exists():
                self.log(f"❌ Current file missing: {output_path}", "ERROR")
                continue
                
            if not backup_file.exists():
                self.log(f"⚠️  No .bak1 version for: {output_path}", "WARNING")
                diff_results[output_path] = "NO_BACKUP"
                continue
                
            try:
                # Get file sizes
                current_size = current_file.stat().st_size
                backup_size = backup_file.stat().st_size
                size_diff = current_size - backup_size
                
                # Run diff command
                result = subprocess.run(
                    ['diff', str(current_file), str(backup_file)], 
                    capture_output=True, 
                    text=True
                )
                
                if result.returncode == 0:
                    diff_results[output_path] = "IDENTICAL"
                    self.log(f"🔹 {Path(output_path).name}: IDENTICAL to .bak1")
                else:
                    diff_lines = len(result.stdout.split('\n')) - 1
                    diff_results[output_path] = f"CHANGED ({diff_lines} diff lines, {size_diff:+d} bytes)"
                    self.log(f"🔸 {Path(output_path).name}: {diff_lines} differences, size {size_diff:+d} bytes")
                    
                    # Save diff to file for detailed analysis
                    diff_file = self.project_root / f"{output_path}.changes.txt"
                    diff_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(diff_file, 'w') as f:
                        f.write(f"DIFF ANALYSIS: {output_path}\n")
                        f.write(f"Current: {current_size} bytes\n")
                        f.write(f"Backup:  {backup_size} bytes\n")
                        f.write(f"Diff:    {size_diff:+d} bytes\n\n")
                        f.write(result.stdout)
                        
                    self.log(f"   📄 Detailed diff saved: {diff_file.name}")
                    
            except Exception as e:
                self.log(f"❌ Failed to diff {output_path}: {e}", "ERROR")
                diff_results[output_path] = f"ERROR: {e}"
                
        self.validation_results['file_differences'] = diff_results
        return diff_results
        
    def generate_verification_report(self):
        """Generate comprehensive verification report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.project_root / f"logs/debug/verify_agent_report_{timestamp}.log"
        
        # Ensure log directory exists
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            f.write("VERIFY-AGENT VALIDATION REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Project Root: {self.project_root}\n\n")
            
            # Validation Results Summary
            f.write("VALIDATION SUMMARY:\n")
            f.write("-" * 30 + "\n")
            missing = self.validation_results.get('missing_outputs', [])
            stale = self.validation_results.get('stale_outputs', [])
            
            f.write(f"Missing Outputs: {len(missing)}\n")
            f.write(f"Stale Outputs: {len(stale)}\n")
            
            if missing:
                f.write("\nMISSING OUTPUTS:\n")
                for item in missing:
                    f.write(f"  - {item}\n")
                    
            if stale:
                f.write("\nSTALE OUTPUTS:\n")
                for item in stale:
                    f.write(f"  - {item}\n")
                    
            # File Differences Summary
            diffs = self.validation_results.get('file_differences', {})
            if diffs:
                f.write("\nFILE DIFFERENCES vs .bak1:\n")
                f.write("-" * 30 + "\n")
                for file_path, diff_status in diffs.items():
                    f.write(f"{Path(file_path).name}: {diff_status}\n")
                    
            # Full Log
            f.write("\nVERIFY-AGENT LOG:\n")
            f.write("-" * 30 + "\n")
            for entry in self.log_entries:
                f.write(entry + "\n")
                
        self.log(f"📄 Verification report saved: {report_path}")
        return report_path
        
    def run_full_verification(self, baseline_timestamp=None):
        """Execute complete verification workflow"""
        self.log("🚀 VERIFY-AGENT: Starting full verification workflow")
        
        # Step 1: Validate mandatory outputs
        outputs_valid = self.validate_mandatory_outputs(baseline_timestamp)
        
        # Step 2: Find and validate latest execution log
        latest_log = self.find_latest_execution_log()
        log_valid = self.validate_execution_log(latest_log)
        
        # Step 3: Analyze file differences
        diff_results = self.analyze_file_differences()
        
        # Step 4: Generate verification report
        report_path = self.generate_verification_report()
        
        # Determine overall success
        overall_success = outputs_valid and log_valid
        
        if overall_success:
            self.log("✅ VERIFY-AGENT: All validations passed")
            self.log("🔄 HANDOFF: Ready for toggle-agent or next experiment")
        else:
            self.log("❌ VERIFY-AGENT: Validation failures detected")
            self.log("🔄 HANDOFF: Requires debug-agent intervention")
            
        return overall_success, report_path, diff_results

def main():
    """Main execution function"""
    verify_agent = VerifyAgent()
    
    try:
        # Use current time as baseline if no specific timestamp provided
        baseline_timestamp = datetime.now() - timedelta(minutes=30)  # Files newer than 30 min ago
        
        success, report_path, diff_results = verify_agent.run_full_verification(baseline_timestamp)
        sys.exit(0 if success else 1)
    except Exception as e:
        verify_agent.log(f"❌ VERIFY-AGENT: Fatal error: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    from datetime import timedelta
    main()