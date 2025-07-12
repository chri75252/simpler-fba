#!/usr/bin/env python3
"""
Sync Opportunity Detector - Tier-2 Smart Prompting for Claude Standards Sync

This module detects when CLAUDE_STANDARDS.md should be synced to claude.md based on:
1. High-priority TodoWrite tasks completed
2. Session checkpoints (compact/summary)
3. Major workflow file changes
4. Test suite completion

Usage:
    python tools/sync_opportunity_detector.py --check
    python tools/sync_opportunity_detector.py --prompt-user
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import hashlib


class SyncOpportunityDetector:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.absolute()
        self.claude_standards_path = self.project_root / "CLAUDE_STANDARDS.md"
        self.claude_md_path = self.project_root / "claude.md"
        self.sync_script_path = self.project_root / "tools" / "sync_claude_standards.py"
        self.checkpoint_script_path = self.project_root / "tools" / "git_checkpoint.py"
        
        # Files that trigger sync opportunities when modified
        self.trigger_files = [
            "CLAUDE_STANDARDS.md",
            "tools/*.py",
            "config/*.json",
            "utils/*.py",
            "tests/*.py"
        ]
        
        # Session state file for tracking opportunities
        self.state_file = self.project_root / "logs" / "debug" / "sync_state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
    
    def get_file_hash(self, file_path: Path) -> Optional[str]:
        """Get MD5 hash of file content"""
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception:
            return None
    
    def load_sync_state(self) -> Dict:
        """Load previous sync state"""
        if not self.state_file.exists():
            return {
                "last_sync_check": None,
                "claude_standards_hash": None,
                "claude_md_hash": None,
                "last_prompt": None,
                "deferred_until": None,
                "session_checkpoints": []
            }
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def save_sync_state(self, state: Dict):
        """Save sync state to file"""
        state["last_sync_check"] = datetime.now().isoformat()
        
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save sync state: {e}")
    
    def is_claude_md_out_of_sync(self) -> Tuple[bool, str]:
        """Check if claude.md is out of sync with CLAUDE_STANDARDS.md"""
        standards_hash = self.get_file_hash(self.claude_standards_path)
        claude_hash = self.get_file_hash(self.claude_md_path)
        
        if not standards_hash:
            return False, "CLAUDE_STANDARDS.md not found"
        
        if not claude_hash:
            return True, "claude.md not found"
        
        # Get last known hashes from state
        state = self.load_sync_state()
        last_standards_hash = state.get("claude_standards_hash")
        
        # If CLAUDE_STANDARDS.md changed since last check, sync is needed
        if last_standards_hash and last_standards_hash != standards_hash:
            return True, "CLAUDE_STANDARDS.md has been modified"
        
        # Run sync script in check mode to verify
        try:
            result = subprocess.run([
                sys.executable, str(self.sync_script_path), "--check-only"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode != 0:
                return True, "Sync script reports files are out of sync"
            
            return False, "Files are in sync"
            
        except Exception as e:
            return True, f"Failed to check sync status: {e}"
    
    def has_recent_git_activity(self, hours: int = 2) -> bool:
        """Check if there's been recent Git activity indicating work completion"""
        try:
            # Check for recent commits
            since_time = datetime.now() - timedelta(hours=hours)
            since_str = since_time.strftime("%Y-%m-%d %H:%M:%S")
            
            result = subprocess.run([
                "git", "log", "--oneline", f"--since={since_str}"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.stdout.strip():
                return True
            
            # Check for staged/modified files
            result = subprocess.run([
                "git", "status", "--porcelain"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            return bool(result.stdout.strip())
            
        except Exception:
            return False
    
    def detect_session_checkpoint(self) -> bool:
        """Detect if we're at a natural session checkpoint"""
        # Check for recent test runs (pytest logs)
        test_logs = list(self.project_root.glob("logs/tests/pytest_run_*.log"))
        if test_logs:
            latest_test = max(test_logs, key=lambda x: x.stat().st_mtime)
            test_age = datetime.now() - datetime.fromtimestamp(latest_test.stat().st_mtime)
            if test_age < timedelta(minutes=30):
                return True
        
        # Check for recent application runs
        app_logs = list(self.project_root.glob("logs/application/*.log"))
        if app_logs:
            latest_app = max(app_logs, key=lambda x: x.stat().st_mtime)
            app_age = datetime.now() - datetime.fromtimestamp(latest_app.stat().st_mtime)
            if app_age < timedelta(minutes=10):
                return True
        
        return False
    
    def should_prompt_for_sync(self) -> Tuple[bool, str, Dict]:
        """
        Determine if user should be prompted for sync
        
        Returns:
            (should_prompt: bool, reason: str, context: dict)
        """
        # Check if files are out of sync
        out_of_sync, sync_reason = self.is_claude_md_out_of_sync()
        if not out_of_sync:
            return False, "Files are already in sync", {}
        
        # Load state to check deferral
        state = self.load_sync_state()
        
        # Check if user deferred recently
        if state.get("deferred_until"):
            defer_until = datetime.fromisoformat(state["deferred_until"])
            if datetime.now() < defer_until:
                return False, f"User deferred until {defer_until}", {}
        
        # Check if we prompted too recently (avoid spam)
        if state.get("last_prompt"):
            last_prompt = datetime.fromisoformat(state["last_prompt"])
            if datetime.now() - last_prompt < timedelta(minutes=30):
                return False, "Prompted too recently", {}
        
        # Determine sync opportunity context
        context = {
            "sync_reason": sync_reason,
            "has_git_activity": self.has_recent_git_activity(),
            "at_checkpoint": self.detect_session_checkpoint(),
            "urgency": "low"
        }
        
        # Determine urgency and whether to prompt
        if context["at_checkpoint"] and context["has_git_activity"]:
            context["urgency"] = "high"
            return True, "Natural checkpoint with recent activity detected", context
        
        elif context["has_git_activity"]:
            context["urgency"] = "medium"
            return True, "Recent work activity detected", context
        
        elif "CLAUDE_STANDARDS.md has been modified" in sync_reason:
            context["urgency"] = "medium"
            return True, "Source standards file has been updated", context
        
        return False, "No compelling sync opportunity detected", context
    
    def prompt_user_for_sync(self) -> str:
        """
        Interactive prompt for sync decision
        
        Returns:
            'sync', 'defer', or 'skip'
        """
        should_prompt, reason, context = self.should_prompt_for_sync()
        
        if not should_prompt:
            print(f"ℹ️ {reason}")
            return 'skip'
        
        print("\n" + "="*60)
        print("🔄 SYNC OPPORTUNITY DETECTED")
        print("="*60)
        print(f"📋 Reason: {reason}")
        print(f"📄 Details: {context.get('sync_reason', 'Unknown')}")
        
        if context.get('urgency') == 'high':
            print("⚡ Urgency: HIGH - Recommended to sync now")
        elif context.get('urgency') == 'medium':
            print("🔶 Urgency: MEDIUM - Good time to sync")
        else:
            print("🔵 Urgency: LOW - Optional sync")
        
        print("\nOptions:")
        print("  (S)ync now - Run sync and create checkpoint")
        print("  (D)efer 1 hour - Ask again later")
        print("  (N)ot now - Skip this opportunity")
        
        while True:
            choice = input("\nYour choice [S/d/n]: ").strip().lower()
            
            if choice in ['', 's', 'sync']:
                return 'sync'
            elif choice in ['d', 'defer']:
                return 'defer'
            elif choice in ['n', 'no', 'not', 'skip']:
                return 'skip'
            else:
                print("Please choose S, D, or N")
    
    def execute_sync(self, create_checkpoint: bool = True) -> bool:
        """Execute the sync operation"""
        try:
            print("🔄 Running sync script...")
            
            # Run sync script
            result = subprocess.run([
                sys.executable, str(self.sync_script_path)
            ], cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Sync failed: {result.stderr}")
                return False
            
            print("✅ Sync completed successfully")
            
            # Create checkpoint if requested
            if create_checkpoint:
                print("📍 Creating checkpoint...")
                checkpoint_result = subprocess.run([
                    sys.executable, str(self.checkpoint_script_path), 
                    "--message", "Sync checkpoint - claude.md updated"
                ], cwd=self.project_root, capture_output=True, text=True)
                
                if checkpoint_result.returncode == 0:
                    print("✅ Checkpoint created")
                else:
                    print(f"⚠️ Checkpoint failed: {checkpoint_result.stderr}")
            
            # Update state
            state = self.load_sync_state()
            state["claude_standards_hash"] = self.get_file_hash(self.claude_standards_path)
            state["claude_md_hash"] = self.get_file_hash(self.claude_md_path)
            state["last_sync"] = datetime.now().isoformat()
            state["deferred_until"] = None  # Clear any deferral
            self.save_sync_state(state)
            
            return True
            
        except Exception as e:
            print(f"❌ Sync execution failed: {e}")
            return False
    
    def defer_sync(self, hours: int = 1):
        """Defer sync prompt for specified hours"""
        state = self.load_sync_state()
        defer_until = datetime.now() + timedelta(hours=hours)
        state["deferred_until"] = defer_until.isoformat()
        state["last_prompt"] = datetime.now().isoformat()
        self.save_sync_state(state)
        
        print(f"⏰ Sync deferred until {defer_until.strftime('%H:%M')}")
    
    def update_prompt_state(self):
        """Update state to record that we prompted"""
        state = self.load_sync_state()
        state["last_prompt"] = datetime.now().isoformat()
        self.save_sync_state(state)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Sync Opportunity Detector')
    parser.add_argument('--check', action='store_true',
                       help='Check if sync is needed (exit code 0=no, 1=yes)')
    parser.add_argument('--prompt-user', action='store_true',
                       help='Interactively prompt user for sync decision')
    parser.add_argument('--force-sync', action='store_true',
                       help='Force sync without prompting')
    
    args = parser.parse_args()
    
    detector = SyncOpportunityDetector()
    
    if args.check:
        should_prompt, reason, context = detector.should_prompt_for_sync()
        print(f"Sync needed: {should_prompt}")
        if should_prompt:
            print(f"Reason: {reason}")
        sys.exit(1 if should_prompt else 0)
    
    elif args.force_sync:
        success = detector.execute_sync()
        sys.exit(0 if success else 1)
    
    elif args.prompt_user:
        choice = detector.prompt_user_for_sync()
        
        if choice == 'sync':
            success = detector.execute_sync()
            sys.exit(0 if success else 1)
        elif choice == 'defer':
            detector.defer_sync()
            sys.exit(0)
        else:
            detector.update_prompt_state()
            print("⏭️ Sync skipped")
            sys.exit(0)
    
    else:
        # Default: check and report
        should_prompt, reason, context = detector.should_prompt_for_sync()
        print(f"Should prompt for sync: {should_prompt}")
        print(f"Reason: {reason}")
        if context:
            print(f"Context: {json.dumps(context, indent=2)}")


if __name__ == "__main__":
    main()