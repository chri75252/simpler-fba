#!/usr/bin/env python3
"""
System Setup Automation for Amazon FBA Agent System v3.2
Automated configuration, dependency validation, and environment setup.
Part of Phase 6 Implementation - System Setup Automation.
"""

import os
import sys
import json
import subprocess
import platform
import psutil
import time
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import shutil

# Import our file manager
try:
    from utils.file_manager import get_file_manager
    fm = get_file_manager()
except ImportError:
    print("⚠️  File manager not available - some features may be limited")
    fm = None


class SystemSetup:
    """Automated system setup and validation for Amazon FBA Agent System"""
    
    def __init__(self):
        self.system_info = {
            'platform': platform.system(),
            'architecture': platform.architecture()[0],
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_gb': round(psutil.virtual_memory().total / (1024**3), 1)
        }
        self.setup_results = {
            'chrome_setup': False,
            'dependencies': False,
            'environment': False,
            'directories': False,
            'permissions': False
        }
        
    def run_full_setup(self) -> bool:
        """Run complete system setup and validation"""
        print("🚀 Amazon FBA Agent System - Automated Setup")
        print("=" * 60)
        self.print_system_info()
        
        success = True
        
        # 1. Validate Environment Variables
        print("\n📋 Step 1: Environment Variables")
        if not self.validate_environment_variables():
            success = False
            
        # 2. Check Dependencies  
        print("\n📦 Step 2: Python Dependencies")
        if not self.check_dependencies():
            success = False
            
        # 3. Setup Chrome Debug Port
        print("\n🌐 Step 3: Chrome Configuration")
        if not self.setup_chrome_debug():
            success = False
            
        # 4. Create Directory Structure
        print("\n📁 Step 4: Directory Structure")
        if not self.setup_directories():
            success = False
            
        # 5. Test System Components
        print("\n🧪 Step 5: Component Testing")
        if not self.test_system_components():
            success = False
            
        # 6. Generate Configuration Report
        print("\n📊 Step 6: Configuration Report")
        self.generate_setup_report()
        
        print("\n" + "=" * 60)
        if success:
            print("✅ System setup completed successfully!")
            print("🎯 Ready for Amazon FBA Agent System operation")
        else:
            print("❌ System setup completed with issues")
            print("📝 Check the setup report for details")
            
        return success
    
    def print_system_info(self):
        """Print system information"""
        print(f"Platform: {self.system_info['platform']} ({self.system_info['architecture']})")
        print(f"Python: {self.system_info['python_version']}")
        print(f"CPU Cores: {self.system_info['cpu_count']}")
        print(f"Memory: {self.system_info['memory_gb']} GB")
        
    def validate_environment_variables(self) -> bool:
        """Validate required environment variables"""
        required_vars = {
            'OPENAI_API_KEY': 'OpenAI API key for AI category suggestions',
        }
        
        optional_vars = {
            'KEEPA_API_KEY': 'Keepa API key for enhanced Amazon data',
            'FIRECRAWL_API_KEY': 'Firecrawl API key for web scraping',
            'HYPERBROWSER_API_KEY': 'HyperBrowser API key for browser automation'
        }
        
        success = True
        
        # Check required variables
        for var, description in required_vars.items():
            value = os.getenv(var)
            if value:
                # Mask the key for security
                masked = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
                print(f"  ✅ {var}: {masked} ({description})")
            else:
                print(f"  ❌ {var}: Missing - {description}")
                success = False
                
        # Check optional variables
        print("\n  Optional API Keys:")
        for var, description in optional_vars.items():
            value = os.getenv(var)
            if value:
                masked = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
                print(f"  ✅ {var}: {masked} ({description})")
            else:
                print(f"  ⚪ {var}: Not set - {description}")
                
        # Check .env file
        env_file = Path('.env')
        if env_file.exists():
            print(f"  ✅ .env file: Found at {env_file.absolute()}")
        else:
            print(f"  ⚠️  .env file: Not found - create one for secure API key storage")
            
        self.setup_results['environment'] = success
        return success
    
    def check_dependencies(self) -> bool:
        """Check Python dependencies"""
        required_packages = [
            ('aiohttp', 'aiohttp'), 
            ('playwright', 'playwright'), 
            ('openai', 'openai'), 
            ('beautifulsoup4', 'bs4'),  # Package name vs import name
            ('psutil', 'psutil'), 
            ('requests', 'requests'), 
            ('pandas', 'pandas')
        ]
        
        success = True
        missing_packages = []
        
        for package_name, import_name in required_packages:
            try:
                __import__(import_name.replace('-', '_'))
                print(f"  ✅ {package_name}: Installed")
            except ImportError:
                print(f"  ❌ {package_name}: Missing")
                missing_packages.append(package_name)
                success = False
                
        if missing_packages:
            print(f"\n  📥 To install missing packages:")
            print(f"     pip install {' '.join(missing_packages)}")
            
        # Check virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print(f"  ✅ Virtual environment: Active ({sys.prefix})")
        else:
            print(f"  ⚠️  Virtual environment: Not detected (recommended for isolation)")
            
        self.setup_results['dependencies'] = success
        return success
    
    def setup_chrome_debug(self) -> bool:
        """Setup Chrome debug port configuration"""
        debug_port = 9222
        
        # Check if Chrome is running with debug port
        chrome_running = self.is_chrome_debug_running(debug_port)
        
        if chrome_running:
            print(f"  ✅ Chrome debug port {debug_port}: Running")
            success = True
        else:
            print(f"  ⚠️  Chrome debug port {debug_port}: Not running")
            print(f"     Start Chrome with: chrome.exe --remote-debugging-port={debug_port}")
            
            # Create helper script
            self.create_chrome_launcher(debug_port)
            success = False
            
        self.setup_results['chrome_setup'] = success
        return success
    
    def is_chrome_debug_running(self, port: int) -> bool:
        """Check if Chrome debug port is accessible"""
        try:
            response = requests.get(f'http://localhost:{port}/json', timeout=2)
            return response.status_code == 200
        except:
            return False
            
    def create_chrome_launcher(self, port: int):
        """Create Chrome launcher scripts"""
        # Windows batch file
        if self.system_info['platform'] == 'Windows':
            launcher_content = f'''@echo off
echo Starting Chrome with remote debugging on port {port}...
start chrome.exe --remote-debugging-port={port} --user-data-dir="C:\\ChromeDebugProfile"
echo Chrome started with debug port {port}
pause
'''
            launcher_path = Path('launch_chrome_debug.bat')
            with open(launcher_path, 'w') as f:
                f.write(launcher_content)
            print(f"  📝 Created Chrome launcher: {launcher_path.absolute()}")
            
        # Linux/Mac shell script
        else:
            launcher_content = f'''#!/bin/bash
echo "Starting Chrome with remote debugging on port {port}..."
google-chrome --remote-debugging-port={port} --user-data-dir="$HOME/ChromeDebugProfile" &
echo "Chrome started with debug port {port}"
'''
            launcher_path = Path('launch_chrome_debug.sh')
            with open(launcher_path, 'w') as f:
                f.write(launcher_content)
            launcher_path.chmod(0o755)  # Make executable
            print(f"  📝 Created Chrome launcher: {launcher_path.absolute()}")
    
    def setup_directories(self) -> bool:
        """Setup required directory structure"""
        success = True
        
        if fm:
            try:
                # Create dated directories for today
                created_dirs = fm.create_dated_directories()
                print(f"  ✅ Created {len(created_dirs)} directories using StandardizedFileManager")
                
                # Test directory creation
                test_path = fm.get_full_path("setup_test", "logs_system", "", "complete", "txt")
                test_path.parent.mkdir(parents=True, exist_ok=True)
                with open(test_path, 'w') as f:
                    f.write(f"System setup test - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  ✅ Directory structure test: {test_path}")
                
            except Exception as e:
                print(f"  ❌ Directory setup error: {e}")
                success = False
        else:
            # Fallback directory creation
            dirs_to_create = [
                "OUTPUTS/LOGS/system",
                "OUTPUTS/LOGS/errors", 
                "OUTPUTS/CACHE/amazon_data",
                "OUTPUTS/CACHE/supplier_data",
                "OUTPUTS/ANALYSIS/DAILY"
            ]
            
            for dir_path in dirs_to_create:
                try:
                    Path(dir_path).mkdir(parents=True, exist_ok=True)
                    print(f"  ✅ Created: {dir_path}")
                except Exception as e:
                    print(f"  ❌ Failed to create {dir_path}: {e}")
                    success = False
                    
        self.setup_results['directories'] = success
        return success
    
    def test_system_components(self) -> bool:
        """Test key system components"""
        success = True
        
        # Test file manager
        if fm:
            try:
                test_filename = fm.generate_filename("system_test", "setup", "complete", "json")
                print(f"  ✅ File manager: Working (test file: {test_filename})")
            except Exception as e:
                print(f"  ❌ File manager: Error - {e}")
                success = False
        else:
            print(f"  ⚠️  File manager: Not available")
            
        # Test OpenAI connection
        try:
            import openai
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                client = openai.OpenAI(api_key=api_key)
                # Simple test call
                response = client.models.list()
                print(f"  ✅ OpenAI API: Connected ({len(response.data)} models available)")
            else:
                print(f"  ❌ OpenAI API: No API key")
                success = False
        except Exception as e:
            print(f"  ❌ OpenAI API: Error - {e}")
            success = False
            
        # Test Chrome debug connection
        if self.is_chrome_debug_running(9222):
            print(f"  ✅ Chrome debug: Connected")
        else:
            print(f"  ❌ Chrome debug: Not accessible")
            success = False
            
        return success
    
    def generate_setup_report(self):
        """Generate system setup report"""
        report = {
            'setup_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'system_info': self.system_info,
            'setup_results': self.setup_results,
            'environment_variables': {
                'OPENAI_API_KEY': bool(os.getenv('OPENAI_API_KEY')),
                'KEEPA_API_KEY': bool(os.getenv('KEEPA_API_KEY')),
            },
            'next_steps': []
        }
        
        # Add recommendations
        if not self.setup_results['chrome_setup']:
            report['next_steps'].append("Start Chrome with debug port using the generated launcher script")
            
        if not self.setup_results['dependencies']:
            report['next_steps'].append("Install missing Python dependencies")
            
        if not self.setup_results['environment']:
            report['next_steps'].append("Set required environment variables in .env file")
            
        # Save report
        try:
            if fm:
                report_path = fm.get_full_path("system_setup_report", "logs_system", "", "complete", "json")
            else:
                report_path = Path("system_setup_report.json")
                
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"  📋 Setup report saved: {report_path}")
            
        except Exception as e:
            print(f"  ❌ Failed to save setup report: {e}")


def main():
    """Main setup function"""
    try:
        setup = SystemSetup()
        success = setup.run_full_setup()
        
        if success:
            print("\n🎉 System is ready for Amazon FBA Agent operation!")
            print("\n🚀 Quick start:")
            print("   python tools/passive_extraction_workflow_latest.py --max-products 3")
        else:
            print("\n⚠️  Setup completed with issues. Please resolve them before running the system.")
            
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())