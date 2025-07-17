#!/usr/bin/env python3
"""
PREP-AGENT - Multi-Toggle Analysis Backup and Validation System
Amazon FBA Agent System v32

PURPOSE: Create numbered backups and validate environment before toggle experiments
LOCATION: Amazon-FBA-Agent-System-v32-prep worktree
"""

import os
import sys
import json
import shutil
import requests
from datetime import datetime
from pathlib import Path

class PrepAgent:
    def __init__(self, project_root="/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32"):
        self.project_root = Path(project_root)
        self.backup_targets = [
            "OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json",
            "OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json", 
            "OUTPUTS/FBA_ANALYSIS/linking_maps/poundwholesale.co.uk/linking_map.json"
        ]
        self.log_entries = []
        
    def log(self, message, level="INFO"):
        """Log messages with timestamps"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.log_entries.append(log_entry)
        print(log_entry)
        
    def create_numbered_backup(self, file_path):
        """Create numbered backup (.bak1, .bak2, etc.) without deleting existing"""
        if not file_path.exists():
            self.log(f"⚠️  Source file does not exist: {file_path}", "WARNING")
            return False
            
        # Find next backup number
        backup_num = 1
        while True:
            backup_path = Path(f"{file_path}.bak{backup_num}")
            if not backup_path.exists():
                break
            backup_num += 1
            
        try:
            shutil.copy2(file_path, backup_path)
            file_size = backup_path.stat().st_size
            self.log(f"✅ Created backup: {backup_path.name} ({file_size} bytes)")
            return True
        except Exception as e:
            self.log(f"❌ Failed to create backup for {file_path}: {e}", "ERROR")
            return False
            
    def validate_chrome_debug_port(self):
        """Test Chrome debug port 9222 accessibility"""
        try:
            response = requests.get("http://localhost:9222/json/version", timeout=5)
            if response.status_code == 200:
                version_info = response.json()
                browser = version_info.get("Browser", "Unknown")
                self.log(f"✅ Chrome debug port accessible: {browser}")
                return True
            else:
                self.log(f"❌ Chrome debug port returned status {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ Chrome debug port not accessible: {e}", "ERROR")
            return False
            
    def validate_mandatory_outputs_exist(self):
        """Check that all mandatory output files exist before backup"""
        missing_files = []
        
        for target in self.backup_targets:
            file_path = self.project_root / target
            if not file_path.exists():
                missing_files.append(str(file_path))
                
        if missing_files:
            self.log(f"❌ Missing mandatory files: {missing_files}", "ERROR")
            return False
        else:
            self.log("✅ All mandatory output files exist")
            return True
            
    def backup_all_targets(self):
        """Create numbered backups for all target files"""
        self.log("🔄 Creating numbered backups for all target files...")
        
        backup_success = True
        for target in self.backup_targets:
            file_path = self.project_root / target
            if not self.create_numbered_backup(file_path):
                backup_success = False
                
        return backup_success
        
    def verify_project_structure(self):
        """Verify essential project files and directories exist"""
        essential_paths = [
            "config/system_config.json",
            "config/system-config-toggle-v2.md",
            "run_custom_poundwholesale.py",
            "OUTPUTS",
            "logs/debug"
        ]
        
        missing_paths = []
        for path in essential_paths:
            full_path = self.project_root / path
            if not full_path.exists():
                missing_paths.append(path)
                
        if missing_paths:
            self.log(f"❌ Missing essential paths: {missing_paths}", "ERROR")
            return False
        else:
            self.log("✅ Project structure validated")
            return True
            
    def check_worktrees(self):
        """Verify git worktrees exist and are accessible"""
        worktree_paths = [
            "/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32-prep",
            "/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32-test", 
            "/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32-debug"
        ]
        
        missing_worktrees = []
        for path in worktree_paths:
            if not Path(path).exists():
                missing_worktrees.append(path)
                
        if missing_worktrees:
            self.log(f"❌ Missing worktrees: {missing_worktrees}", "ERROR")
            return False
        else:
            self.log("✅ All worktrees accessible")
            return True
            
    def generate_prep_report(self):
        """Generate comprehensive preparation report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.project_root / f"logs/debug/prep_agent_report_{timestamp}.log"
        
        # Ensure logs directory exists
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            f.write("PREP-AGENT EXECUTION REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Project Root: {self.project_root}\n")
            f.write("\nEXECUTION LOG:\n")
            f.write("-" * 30 + "\n")
            for entry in self.log_entries:
                f.write(entry + "\n")
                
        self.log(f"📄 Prep report saved: {report_path}")
        return report_path
        
    def run_full_preparation(self):
        """Execute complete preparation workflow"""
        self.log("🚀 PREP-AGENT: Starting full preparation workflow")
        
        # Step 1: Verify project structure
        if not self.verify_project_structure():
            self.log("❌ PREP-AGENT: Project structure validation failed", "ERROR")
            return False
            
        # Step 2: Check worktrees
        if not self.check_worktrees():
            self.log("❌ PREP-AGENT: Worktree validation failed", "ERROR")
            return False
            
        # Step 3: Validate Chrome debug port
        if not self.validate_chrome_debug_port():
            self.log("❌ PREP-AGENT: Chrome debug port validation failed", "ERROR")
            return False
            
        # Step 4: Check mandatory outputs exist
        if not self.validate_mandatory_outputs_exist():
            self.log("❌ PREP-AGENT: Mandatory output validation failed", "ERROR")
            return False
            
        # Step 5: Create numbered backups
        if not self.backup_all_targets():
            self.log("❌ PREP-AGENT: Backup creation failed", "ERROR")
            return False
            
        # Step 6: Generate report
        report_path = self.generate_prep_report()
        
        self.log("✅ PREP-AGENT: Full preparation completed successfully")
        self.log("🔄 HANDOFF: Ready for exec-agent execution")
        
        return True

def main():
    """Main execution function"""
    prep_agent = PrepAgent()
    
    try:
        success = prep_agent.run_full_preparation()
        sys.exit(0 if success else 1)
    except Exception as e:
        prep_agent.log(f"❌ PREP-AGENT: Fatal error: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()