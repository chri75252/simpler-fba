#!/usr/bin/env python3
"""
Git Checkpoint Helper - Automated Git operations for Tier-2/Tier-3 sync system

This script creates checkpoints by:
1. Creating a new branch off the stable branch (june-15)
2. Committing current changes with descriptive messages
3. Pushing to GitHub repository for backup and collaboration

Usage:
    python tools/git_checkpoint.py --message "feature-description"
    python tools/git_checkpoint.py --auto-sync  # Called by TodoWrite
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import json

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


class GitCheckpointManager:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.absolute()
        self.default_branch = os.getenv("DEFAULT_BRANCH", "june-15")
        self.git_user_name = os.getenv("GIT_USER_NAME", "FBA-Bot")
        self.git_user_email = os.getenv("GIT_USER_EMAIL", "chri75252@gmail.com")
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repo_url = os.getenv("GITHUB_REPO_URL", "https://github.com/chri75252/fba-tool-claude.git")
        
        # Validate environment
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
    
    def run_git_command(self, cmd: list, check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run git command with proper error handling"""
        try:
            result = subprocess.run(
                cmd, 
                cwd=self.project_root,
                check=check,
                capture_output=capture_output,
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            print(f"❌ Git command failed: {' '.join(cmd)}")
            print(f"Error: {e.stderr}")
            raise
    
    def setup_git_config(self):
        """Configure Git user for automated commits"""
        try:
            self.run_git_command(["git", "config", "user.name", self.git_user_name])
            self.run_git_command(["git", "config", "user.email", self.git_user_email])
            print(f"✅ Git configured for {self.git_user_name} <{self.git_user_email}>")
        except Exception as e:
            print(f"⚠️ Failed to configure Git user: {e}")
    
    def get_current_branch(self) -> str:
        """Get current Git branch"""
        result = self.run_git_command(["git", "branch", "--show-current"])
        return result.stdout.strip()
    
    def get_short_sha(self) -> str:
        """Get short SHA of current HEAD"""
        result = self.run_git_command(["git", "rev-parse", "--short", "HEAD"])
        return result.stdout.strip()
    
    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes"""
        result = self.run_git_command(["git", "status", "--porcelain"])
        return bool(result.stdout.strip())
    
    def generate_checkpoint_branch_name(self, message: str) -> str:
        """Generate unique checkpoint branch name"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        short_sha = self.get_short_sha()
        
        # Clean message for branch name
        clean_message = "".join(c for c in message if c.isalnum() or c in "-_").lower()
        clean_message = clean_message[:20]  # Limit length
        
        return f"checkpoint/{timestamp}-{clean_message}-{short_sha}"
    
    def stash_changes(self) -> bool:
        """Stash current changes, return True if stash was created"""
        if not self.has_uncommitted_changes():
            return False
        
        try:
            self.run_git_command(["git", "stash", "push", "-u", "-m", "Auto-stash before checkpoint"])
            print("📦 Stashed uncommitted changes")
            return True
        except Exception as e:
            print(f"❌ Failed to stash changes: {e}")
            raise
    
    def pop_stash(self):
        """Pop the most recent stash"""
        try:
            self.run_git_command(["git", "stash", "pop"])
            print("📤 Restored stashed changes")
        except Exception as e:
            print(f"⚠️ Failed to restore stash: {e}")
    
    def ensure_on_stable_branch(self):
        """Ensure we're on the stable branch and up to date"""
        current_branch = self.get_current_branch()
        
        if current_branch != self.default_branch:
            print(f"🔄 Switching from {current_branch} to {self.default_branch}")
            self.run_git_command(["git", "checkout", self.default_branch])
        
        # Pull latest changes
        print(f"📥 Pulling latest changes from origin/{self.default_branch}")
        try:
            self.run_git_command(["git", "pull", "origin", self.default_branch])
        except Exception as e:
            print(f"⚠️ Failed to pull latest changes: {e}")
            print("Continuing with local state...")
    
    def create_checkpoint_branch(self, branch_name: str):
        """Create and checkout checkpoint branch"""
        print(f"🌿 Creating checkpoint branch: {branch_name}")
        self.run_git_command(["git", "checkout", "-b", branch_name])
    
    def commit_changes(self, message: str):
        """Add all changes and commit with message"""
        # Add all changes
        self.run_git_command(["git", "add", "."])
        
        # Create commit message with metadata
        commit_msg = f"chore: {message}\n\n"
        commit_msg += f"Automated checkpoint created via git_checkpoint.py\n"
        commit_msg += f"Timestamp: {datetime.now().isoformat()}\n"
        commit_msg += f"Base branch: {self.default_branch}\n"
        
        print(f"💾 Committing changes: {message}")
        self.run_git_command(["git", "commit", "-m", commit_msg])
    
    def push_to_remote(self, branch_name: str):
        """Push checkpoint branch to remote"""
        # Configure remote URL with token for authentication
        auth_url = self.repo_url.replace("https://", f"https://{self.github_token}@")
        
        print(f"📤 Pushing {branch_name} to remote...")
        try:
            self.run_git_command(["git", "push", "-u", "origin", branch_name])
            print(f"✅ Successfully pushed {branch_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to push: {e}")
            return False
    
    def create_checkpoint(self, message: str, auto_sync: bool = False) -> Tuple[bool, str]:
        """
        Main checkpoint creation workflow
        
        Args:
            message: Description for the checkpoint
            auto_sync: If True, called from TodoWrite auto-sync
            
        Returns:
            (success: bool, branch_name: str)
        """
        try:
            print(f"🚀 Creating checkpoint: {message}")
            
            # Setup Git configuration
            self.setup_git_config()
            
            # Check if we have changes to commit
            if not self.has_uncommitted_changes():
                if auto_sync:
                    print("ℹ️ No uncommitted changes for auto-sync checkpoint")
                    return True, ""
                else:
                    print("⚠️ No uncommitted changes to checkpoint")
                    return False, ""
            
            # Generate branch name
            branch_name = self.generate_checkpoint_branch_name(message)
            
            # Stash any uncommitted changes
            stashed = self.stash_changes()
            
            try:
                # Ensure we're on stable branch and up to date
                self.ensure_on_stable_branch()
                
                # Create checkpoint branch
                self.create_checkpoint_branch(branch_name)
                
                # Restore stashed changes
                if stashed:
                    self.pop_stash()
                
                # Commit changes
                self.commit_changes(message)
                
                # Push to remote
                success = self.push_to_remote(branch_name)
                
                if success:
                    print(f"✅ Checkpoint created successfully!")
                    print(f"📍 Branch: {branch_name}")
                    print(f"🔗 View at: {self.repo_url}/tree/{branch_name}")
                    
                    # Log checkpoint creation
                    self.log_checkpoint(branch_name, message, auto_sync)
                    
                    return True, branch_name
                else:
                    return False, branch_name
                    
            except Exception as e:
                # If something went wrong after stashing, try to restore
                if stashed:
                    try:
                        self.pop_stash()
                    except:
                        print("⚠️ Failed to restore stash after error")
                raise
                
        except Exception as e:
            print(f"❌ Checkpoint creation failed: {e}")
            return False, ""
    
    def log_checkpoint(self, branch_name: str, message: str, auto_sync: bool):
        """Log checkpoint creation for debugging and audit"""
        log_dir = self.project_root / "logs" / "debug"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"git_checkpoints_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "branch_name": branch_name,
            "message": message,
            "auto_sync": auto_sync,
            "base_branch": self.default_branch,
            "repository": self.repo_url
        }
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"⚠️ Failed to log checkpoint: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Git Checkpoint Helper')
    parser.add_argument('--message', '-m', 
                       help='Checkpoint description message')
    parser.add_argument('--auto-sync', action='store_true',
                       help='Auto-sync mode (called by TodoWrite)')
    
    args = parser.parse_args()
    
    # Determine message
    if args.auto_sync:
        message = "Auto-sync checkpoint from TodoWrite"
    elif args.message:
        message = args.message
    else:
        message = input("Enter checkpoint description: ").strip()
        if not message:
            print("❌ Checkpoint message is required")
            sys.exit(1)
    
    try:
        manager = GitCheckpointManager()
        success, branch_name = manager.create_checkpoint(message, args.auto_sync)
        
        if success and branch_name:
            print(f"\n🎉 Checkpoint complete!")
            if not args.auto_sync:
                print(f"Next steps:")
                print(f"  • Review changes at: {manager.repo_url}/tree/{branch_name}")
                print(f"  • Create PR if ready to merge")
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()