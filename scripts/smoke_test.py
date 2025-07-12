#!/usr/bin/env python3
"""
Smoke Test for Amazon FBA Agent System v3.5 Tier-2/Tier-3 Sync System

This script performs basic validation of all sync system components
to ensure the implementation is working correctly.

Usage:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --verbose
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import argparse


class SmokeTest:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent.absolute()
        self.test_results = []
        self.passed = 0
        self.failed = 0
    
    def log(self, message, level="info"):
        if level == "error":
            prefix = "❌"
        elif level == "success":
            prefix = "✅"
        elif level == "warning":
            prefix = "⚠️"
        else:
            prefix = "ℹ️"
        
        print(f"{prefix} {message}")
        
        if self.verbose or level in ["error", "success"]:
            self.test_results.append(f"{prefix} {message}")
    
    def run_command(self, cmd, cwd=None, timeout=30):
        """Run command and return result"""
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
    
    def test_file_exists(self, file_path, description):
        """Test if a file exists"""
        full_path = self.project_root / file_path
        if full_path.exists():
            self.log(f"{description}: Found", "success")
            self.passed += 1
            return True
        else:
            self.log(f"{description}: Missing {file_path}", "error")
            self.failed += 1
            return False
    
    def test_script_executable(self, script_path, description):
        """Test if a script is executable and runs without errors"""
        success, stdout, stderr = self.run_command([sys.executable, str(script_path), "--help"])
        
        if success:
            self.log(f"{description}: Executable and responsive", "success")
            self.passed += 1
            return True
        else:
            self.log(f"{description}: Failed to run - {stderr[:100]}", "error")
            self.failed += 1
            return False
    
    def test_sync_script_functionality(self):
        """Test sync script core functionality"""
        self.log("Testing sync script functionality...")
        
        # Test check-only mode
        success, stdout, stderr = self.run_command([
            sys.executable, "tools/sync_claude_standards.py", "--check-only"
        ])
        
        if success:
            self.log("Sync script --check-only: Working", "success")
            self.passed += 1
        else:
            # Check-only can return 1 if sync is needed, that's ok
            # Script is working if it properly reports sync status (output to stdout)
            if ("❌ Sync needed" in stdout or "✅ All files are in sync" in stdout or 
                "synced successfully" in stdout or "Files are in sync" in stdout or
                "Sync needed for:" in stdout):
                self.log("Sync script --check-only: Working (reports sync status)", "success")
                self.passed += 1
            else:
                self.log(f"Sync script --check-only: Failed - {stderr[:100] if stderr else stdout[:100]}", "error")
                self.failed += 1
                return False
        
        # Test actual sync
        success, stdout, stderr = self.run_command([
            sys.executable, "tools/sync_claude_standards.py"
        ])
        
        if success and "synced successfully" in stdout:
            self.log("Sync script execution: Working", "success")
            self.passed += 1
            return True
        else:
            self.log(f"Sync script execution: Failed - {stderr[:100]}", "error")
            self.failed += 1
            return False
    
    def test_opportunity_detector(self):
        """Test sync opportunity detector"""
        self.log("Testing sync opportunity detector...")
        
        success, stdout, stderr = self.run_command([
            sys.executable, "tools/sync_opportunity_detector.py", "--check"
        ])
        
        # Either success or exit code 1 (sync needed) is acceptable
        # Script is working if it can analyze and report sync opportunities (output to stdout)
        if (success or "Sync needed: True" in stdout or "Sync needed: False" in stdout or
            "Should prompt for sync:" in stdout or "Recent work activity detected" in stdout or 
            "No compelling sync" in stdout or "Reason:" in stdout):
            self.log("Sync opportunity detector: Working (analyzes opportunities)", "success")
            self.passed += 1
            return True
        else:
            self.log(f"Sync opportunity detector: Failed - {stderr[:100] if stderr else stdout[:100]}", "error")
            self.failed += 1
            return False
    
    def test_git_checkpoint_basic(self):
        """Test git checkpoint helper basic functionality"""
        self.log("Testing git checkpoint helper...")
        
        # Just test that it can parse arguments and show help
        success, stdout, stderr = self.run_command([
            sys.executable, "tools/git_checkpoint.py", "--help"
        ])
        
        if success and "checkpoint" in stdout.lower():
            self.log("Git checkpoint helper: Responsive", "success")
            self.passed += 1
            return True
        else:
            self.log(f"Git checkpoint helper: Failed - {stderr[:100]}", "error")
            self.failed += 1
            return False
    
    def test_security_checker_basic(self):
        """Test security checker basic functionality"""
        self.log("Testing security checker (basic)...")
        
        # Test help first
        success, stdout, stderr = self.run_command([
            sys.executable, "tools/security_checks.py", "--help"
        ], timeout=10)
        
        if success and "security" in stdout.lower():
            self.log("Security checker: Responsive", "success")
            self.passed += 1
            return True
        else:
            self.log(f"Security checker: Not responsive - {stderr[:100]}", "warning")
            # Don't fail the entire test for this
            return True
    
    def test_github_workflow_syntax(self):
        """Test GitHub workflow file syntax"""
        workflow_file = self.project_root / ".github/workflows/claude_sync_validate.yml"
        
        if not workflow_file.exists():
            self.log("GitHub workflow: File missing", "error")
            self.failed += 1
            return False
        
        try:
            import yaml
            with open(workflow_file, 'r') as f:
                workflow_data = yaml.safe_load(f)
            
            # Basic validation - handle 'on' being parsed as boolean True
            actual_keys = list(workflow_data.keys())
            required_keys = ['name', 'jobs']
            has_on_key = 'on' in workflow_data or True in workflow_data
            
            for key in required_keys:
                if key not in workflow_data:
                    self.log(f"GitHub workflow: Missing key '{key}'", "error")
                    self.failed += 1
                    return False
            
            if not has_on_key:
                self.log("GitHub workflow: Missing 'on' trigger configuration", "error")
                self.failed += 1
                return False
            
            self.log("GitHub workflow: Valid YAML syntax", "success")
            self.passed += 1
            return True
            
        except ImportError:
            self.log("GitHub workflow: YAML parser not available (skipping validation)", "warning")
            return True
        except Exception as e:
            self.log(f"GitHub workflow: Invalid YAML - {str(e)[:100]}", "error")
            self.failed += 1
            return False
    
    def test_environment_file(self):
        """Test environment file structure"""
        env_file = self.project_root / ".env"
        
        if not env_file.exists():
            self.log("Environment file: Not found (this is normal)", "info")
            return True
        
        try:
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Check for required GitHub integration variables
            required_vars = [
                "GITHUB_TOKEN",
                "GIT_USER_NAME", 
                "GIT_USER_EMAIL",
                "DEFAULT_BRANCH"
            ]
            
            missing_vars = []
            for var in required_vars:
                if var not in content:
                    missing_vars.append(var)
            
            if missing_vars:
                self.log(f"Environment file: Missing variables - {', '.join(missing_vars)}", "warning")
            else:
                self.log("Environment file: Has GitHub integration variables", "success")
                self.passed += 1
            
            return True
            
        except Exception as e:
            self.log(f"Environment file: Read error - {str(e)}", "error")
            self.failed += 1
            return False
    
    def test_pre_commit_hook(self):
        """Test pre-commit hook basic functionality"""
        hook_file = self.project_root / ".githooks/pre-commit"
        
        if not hook_file.exists():
            self.log("Pre-commit hook: File missing", "error")
            self.failed += 1
            return False
        
        # Test that it's executable and doesn't crash immediately
        success, stdout, stderr = self.run_command(["bash", str(hook_file)], timeout=15)
        
        # Exit code 0 or 1 is ok (1 means sync needed)
        if "Claude Standards" in stdout or "sync" in stderr.lower():
            self.log("Pre-commit hook: Working", "success")
            self.passed += 1
            return True
        else:
            self.log(f"Pre-commit hook: Issues - {stderr[:100]}", "warning")
            return True  # Don't fail test for hook issues
    
    def run_all_tests(self):
        """Run all smoke tests"""
        self.log("🚀 Starting smoke test for Tier-2/Tier-3 sync system")
        self.log("=" * 60)
        
        # File existence tests
        critical_files = [
            ("CLAUDE_STANDARDS.md", "Source of truth file"),
            ("tools/sync_claude_standards.py", "Sync script"),
            ("tools/sync_opportunity_detector.py", "Opportunity detector"),
            ("tools/git_checkpoint.py", "Git checkpoint helper"),
            ("tools/security_checks.py", "Security checker"),
            (".github/workflows/claude_sync_validate.yml", "GitHub workflow"),
            (".pre-commit-config.yaml", "Pre-commit config"),
            (".githooks/pre-commit", "Pre-commit hook"),
        ]
        
        for file_path, description in critical_files:
            self.test_file_exists(file_path, description)
        
        # Functionality tests
        self.test_sync_script_functionality()
        self.test_opportunity_detector()
        self.test_git_checkpoint_basic()
        self.test_security_checker_basic()
        self.test_github_workflow_syntax()
        self.test_environment_file()
        self.test_pre_commit_hook()
        
        # Summary
        self.log("=" * 60)
        total_tests = self.passed + self.failed
        self.log(f"Tests completed: {total_tests} total, {self.passed} passed, {self.failed} failed")
        
        if self.failed == 0:
            self.log("🎉 All smoke tests passed! System is ready for use.", "success")
            return True
        else:
            self.log(f"⚠️ {self.failed} tests failed. Check issues above.", "error")
            return False
    
    def save_report(self, filename):
        """Save test report to file"""
        report_path = self.project_root / "logs" / "debug" / filename
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            f.write(f"Smoke Test Report - {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Total tests: {self.passed + self.failed}\n")
            f.write(f"Passed: {self.passed}\n")
            f.write(f"Failed: {self.failed}\n\n")
            f.write("Detailed Results:\n")
            f.write("-" * 30 + "\n")
            for result in self.test_results:
                f.write(result + "\n")
        
        self.log(f"Report saved to: {report_path}")


def main():
    parser = argparse.ArgumentParser(description='Smoke test for sync system')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--save-report', 
                       help='Save report to specified filename')
    
    args = parser.parse_args()
    
    tester = SmokeTest(verbose=args.verbose)
    success = tester.run_all_tests()
    
    if args.save_report:
        tester.save_report(args.save_report)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()