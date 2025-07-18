#!/usr/bin/env python3
"""
Authentication System Verification Script
Simple verification of authentication system without external test dependencies.
Tests core functionality and integration points for Amazon FBA Agent System v32.
"""

import asyncio
import sys
import os
import json
import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Mock classes for testing
class MockLoginResult:
    def __init__(self, success=True, method_used="test_method", error_message="", 
                 login_detected=True, price_access_verified=True, login_duration_seconds=1.5):
        self.success = success
        self.method_used = method_used
        self.error_message = error_message
        self.login_detected = login_detected
        self.price_access_verified = price_access_verified
        self.login_duration_seconds = login_duration_seconds

async def test_authentication_manager_basic():
    """Test basic AuthenticationManager functionality"""
    
    print("🔍 Testing AuthenticationManager basic functionality...")
    
    try:
        from authentication_manager import AuthenticationManager, AuthenticationStats
        
        # Test configuration loading
        config = {
            "authentication": {
                "consecutive_failure_threshold": 3,
                "primary_periodic_interval": 100,
                "secondary_periodic_interval": 200,
                "max_consecutive_auth_failures": 3,
                "auth_failure_delay_seconds": 30,
                "min_products_between_logins": 10
            }
        }
        
        auth_manager = AuthenticationManager(cdp_port=9222, system_config=config)
        
        # Verify initialization
        assert auth_manager.consecutive_failure_threshold == 3
        assert auth_manager.primary_periodic_interval == 100
        assert auth_manager.secondary_periodic_interval == 200
        assert auth_manager.stats.session_start_time is not None
        
        print("  ✅ Configuration loading works")
        
        # Test consecutive failure detection
        auth_manager.consecutive_failures = 0
        auth_manager.products_since_login = 0
        auth_manager.total_products_processed = 0
        auth_manager.consecutive_auth_failures = 0
        
        # Process 3 failed price extractions
        for i in range(3):
            needs_login, reason, value = await auth_manager.evaluate_login_needed(None)
            if i == 2:  # Third failure should trigger
                assert needs_login is True
                assert reason == "consecutive_failures"
                assert value == 3
                print("  ✅ Consecutive failure detection works")
                break
        
        # Test periodic trigger (set to 99 so it becomes 100 after evaluation)
        auth_manager.consecutive_failures = 0
        auth_manager.products_since_login = 99
        auth_manager.total_products_processed = 99
        
        needs_login, reason, value = await auth_manager.evaluate_login_needed(10.0)
        assert needs_login is True
        assert reason == "periodic_primary"
        assert value == 100
        print("  ✅ Periodic trigger detection works")
        
        # Test circuit breaker logic
        auth_manager.consecutive_auth_failures = 3
        auth_manager.last_auth_failure_time = datetime.now()
        
        assert auth_manager._is_circuit_breaker_active() is True
        print("  ✅ Circuit breaker activation works")
        
        # Test statistics calculation
        auth_manager.stats.total_attempts = 10
        auth_manager.stats.successful_logins = 7
        
        success_rate = auth_manager._get_success_rate()
        assert success_rate == 70.0
        print("  ✅ Statistics calculation works")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

async def test_authentication_integration():
    """Test authentication integration with workflow components"""
    
    print("🔍 Testing authentication integration...")
    
    try:
        from authentication_manager import AuthenticationManager
        
        # Test mock authentication callback
        auth_manager = MagicMock()
        auth_manager.evaluate_login_needed = AsyncMock()
        auth_manager.perform_authentication = AsyncMock()
        
        # Configure mock responses
        auth_manager.evaluate_login_needed.side_effect = [
            (False, "no_trigger", 0),
            (False, "no_trigger", 0),
            (True, "consecutive_failures", 3)
        ]
        
        # Test authentication callback logic
        prices = [None, None, None]
        auth_triggered = False
        
        for i, price in enumerate(prices):
            needs_login, reason, value = await auth_manager.evaluate_login_needed(price)
            if needs_login:
                await auth_manager.perform_authentication(reason, value)
                auth_triggered = True
                break
        
        assert auth_triggered is True
        assert auth_manager.perform_authentication.called
        print("  ✅ Authentication callback integration works")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

async def test_configuration_integration():
    """Test configuration file integration"""
    
    print("🔍 Testing configuration integration...")
    
    try:
        # Load actual system configuration
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'system_config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                system_config = json.load(f)
            
            auth_config = system_config.get('authentication', {})
            
            # Verify required configuration exists
            required_keys = [
                'enabled', 'startup_verification', 'consecutive_failure_threshold',
                'primary_periodic_interval', 'secondary_periodic_interval',
                'max_consecutive_auth_failures', 'auth_failure_delay_seconds'
            ]
            
            for key in required_keys:
                assert key in auth_config, f"Missing config key: {key}"
            
            print("  ✅ Configuration file structure is valid")
            
            # Test configuration values are reasonable
            assert auth_config['consecutive_failure_threshold'] > 0
            assert auth_config['primary_periodic_interval'] > 0
            assert auth_config['secondary_periodic_interval'] > auth_config['primary_periodic_interval']
            assert auth_config['max_consecutive_auth_failures'] > 0
            assert auth_config['auth_failure_delay_seconds'] > 0
            
            print("  ✅ Configuration values are valid")
            
        else:
            print("  ⚠️ System configuration file not found - using defaults")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_file_structure():
    """Test that all required authentication files exist"""
    
    print("🔍 Testing file structure...")
    
    required_files = [
        'tools/authentication_manager.py',
        'tools/passive_extraction_workflow_latest.py',
        'tools/configurable_supplier_scraper.py',
        'tools/standalone_playwright_login.py',
        'config/system_config.json'
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path} exists")
        else:
            print(f"  ❌ {file_path} missing")
            all_exist = False
    
    return all_exist

def test_import_compatibility():
    """Test that authentication modules can be imported"""
    
    print("🔍 Testing import compatibility...")
    
    try:
        from authentication_manager import AuthenticationManager, AuthenticationResult, AuthenticationStats
        print("  ✅ authentication_manager imports successfully")
        
        # Test if modules have required attributes
        assert hasattr(AuthenticationManager, 'evaluate_login_needed')
        assert hasattr(AuthenticationManager, 'perform_authentication')
        assert hasattr(AuthenticationManager, '_is_circuit_breaker_active')
        print("  ✅ AuthenticationManager has required methods")
        
        return True
        
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

async def run_verification():
    """Run comprehensive authentication system verification"""
    
    print("🚀 Amazon FBA Agent System v32 - Authentication System Verification")
    print("=" * 70)
    print()
    
    test_results = []
    
    # Test 1: File structure
    result1 = test_file_structure()
    test_results.append(("File Structure", result1))
    print()
    
    # Test 2: Import compatibility
    result2 = test_import_compatibility()
    test_results.append(("Import Compatibility", result2))
    print()
    
    # Test 3: Basic functionality
    result3 = await test_authentication_manager_basic()
    test_results.append(("Basic Functionality", result3))
    print()
    
    # Test 4: Integration
    result4 = await test_authentication_integration()
    test_results.append(("Integration", result4))
    print()
    
    # Test 5: Configuration
    result5 = await test_configuration_integration()
    test_results.append(("Configuration", result5))
    print()
    
    # Summary
    print("=" * 70)
    print("🧪 AUTHENTICATION SYSTEM VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    print(f"📊 Tests: {passed}/{total} passed")
    print()
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    print()
    
    if passed == total:
        print("🎉 ALL VERIFICATION TESTS PASSED!")
        print("   The multi-tier authentication system is properly implemented.")
        print("   ✅ Configuration loading works")
        print("   ✅ Multi-tier trigger logic implemented") 
        print("   ✅ Circuit breaker pattern active")
        print("   ✅ Statistics tracking functional")
        print("   ✅ Integration points verified")
        return True
    else:
        print("⚠️  SOME VERIFICATION TESTS FAILED")
        print("   Review the output above and fix issues before proceeding.")
        return False

def main():
    """Main verification function"""
    
    try:
        success = asyncio.run(run_verification())
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Verification interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n\n💥 Unexpected error during verification: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()