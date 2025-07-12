#!/usr/bin/env python3
"""
Flag Notification System for FBA Monitoring
Creates desktop notifications and email alerts when monitoring flags are created.
"""

import os
import json
import time
import smtplib
from pathlib import Path
from datetime import datetime
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import logging

# Try to import Windows toast notifications
try:
    from plyer import notification
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    print("Install 'plyer' for desktop notifications: pip install plyer")

class FlagNotifier:
    def __init__(self, base_dir: str = None, email_config: dict = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.flags_dir = self.base_dir / "MONITORING_FLAGS"
        self.notified_flags = set()
        self.email_config = email_config or {}
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.base_dir / "flag_notifier.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def send_desktop_notification(self, title: str, message: str, urgency: str = "normal"):
        """Send desktop notification"""
        if not NOTIFICATIONS_AVAILABLE:
            return False
            
        try:
            # Map severity to urgency
            timeout_map = {"INFO": 5, "WARNING": 10, "CRITICAL": 15}
            timeout = timeout_map.get(urgency, 10)
            
            notification.notify(
                title=title,
                message=message,
                timeout=timeout,
                app_name="FBA Monitor"
            )
            return True
        except Exception as e:
            self.logger.error(f"Desktop notification failed: {e}")
            return False
            
    def send_email_notification(self, subject: str, body: str, urgency: str = "normal"):
        """Send email notification"""
        if not self.email_config.get('enabled', False):
            return False
            
        try:
            msg = MimeMultipart()
            msg['From'] = self.email_config['from_email']
            msg['To'] = self.email_config['to_email']
            msg['Subject'] = f"[FBA-{urgency}] {subject}"
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            if self.email_config.get('use_tls', True):
                server.starttls()
            if self.email_config.get('username') and self.email_config.get('password'):
                server.login(self.email_config['username'], self.email_config['password'])
                
            server.send_message(msg)
            server.quit()
            return True
            
        except Exception as e:
            self.logger.error(f"Email notification failed: {e}")
            return False
            
    def format_flag_message(self, flag_data: dict) -> tuple:
        """Format flag data into notification title and message"""
        flag_type = flag_data.get('flag_type', 'UNKNOWN')
        severity = flag_data.get('severity', 'INFO')
        summary = flag_data.get('details', {}).get('summary', 'No details available')
        timestamp = flag_data.get('timestamp', '')
        
        title = f"FBA Alert: {flag_type}"
        
        message = f"""
Severity: {severity}
Time: {timestamp}
Issue: {summary}

Action Required: {'YES' if flag_data.get('requires_action', False) else 'NO'}
        """.strip()
        
        return title, message
        
    def check_for_new_flags(self):
        """Check for new flags and send notifications"""
        if not self.flags_dir.exists():
            return
            
        current_flags = set()
        new_flags = []
        
        for flag_file in self.flags_dir.glob("*.json"):
            flag_id = flag_file.stem
            current_flags.add(flag_id)
            
            if flag_id not in self.notified_flags:
                try:
                    with open(flag_file, 'r') as f:
                        flag_data = json.load(f)
                        new_flags.append((flag_id, flag_data))
                except Exception as e:
                    self.logger.error(f"Error reading flag file {flag_file}: {e}")
                    
        # Send notifications for new flags
        for flag_id, flag_data in new_flags:
            severity = flag_data.get('severity', 'INFO')
            title, message = self.format_flag_message(flag_data)
            
            # Send desktop notification
            self.send_desktop_notification(title, message, severity)
            
            # Send email for WARNING and CRITICAL flags
            if severity in ['WARNING', 'CRITICAL']:
                self.send_email_notification(title, message, severity)
                
            self.logger.info(f"Notified about flag: {flag_id} ({severity})")
            
        # Update notified flags
        self.notified_flags.update(flag_id for flag_id, _ in new_flags)
        
        # Clean up notified flags for files that no longer exist
        self.notified_flags &= current_flags
        
        return len(new_flags)
        
    def run_continuous_notification(self, check_interval: int = 60):
        """Run continuous flag monitoring and notification"""
        self.logger.info("Starting FBA flag notification system...")
        
        while True:
            try:
                new_count = self.check_for_new_flags()
                if new_count > 0:
                    self.logger.info(f"Processed {new_count} new flags")
                    
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("Flag notifier stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in notification loop: {e}")
                time.sleep(60)
                
    def create_sample_email_config(self):
        """Create sample email configuration file"""
        sample_config = {
            "enabled": False,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "use_tls": True,
            "from_email": "your-email@gmail.com",
            "to_email": "your-email@gmail.com",
            "username": "your-email@gmail.com",
            "password": "your-app-password"
        }
        
        config_file = self.base_dir / "email_config.json"
        with open(config_file, 'w') as f:
            json.dump(sample_config, f, indent=2)
            
        print(f"Sample email config created: {config_file}")
        print("Edit the file and set 'enabled': true to activate email notifications")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FBA Flag Notification System")
    parser.add_argument("--base-dir", default=".", help="Base directory for FBA system")
    parser.add_argument("--check-once", action="store_true", help="Check once instead of continuous")
    parser.add_argument("--create-email-config", action="store_true", help="Create sample email config")
    parser.add_argument("--email-config", help="Path to email configuration file")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")
    
    args = parser.parse_args()
    
    # Load email config if provided
    email_config = {}
    if args.email_config and Path(args.email_config).exists():
        with open(args.email_config, 'r') as f:
            email_config = json.load(f)
    elif Path(args.base_dir, "email_config.json").exists():
        with open(Path(args.base_dir, "email_config.json"), 'r') as f:
            email_config = json.load(f)
            
    notifier = FlagNotifier(args.base_dir, email_config)
    
    if args.create_email_config:
        notifier.create_sample_email_config()
    elif args.check_once:
        count = notifier.check_for_new_flags()
        print(f"Processed {count} new flags")
    else:
        notifier.run_continuous_notification(args.interval)
