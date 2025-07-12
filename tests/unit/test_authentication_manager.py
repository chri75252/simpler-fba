#!/usr/bin/env python3
"""
Comprehensive Unit Tests for AuthenticationManager
Tests multi-tier authentication logic, circuit breaker patterns, statistics tracking,
and configuration handling for the Amazon FBA Agent System v32.
"""

import pytest
import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from freezegun import freeze_time

# Add tools directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))

from authentication_manager import AuthenticationManager, AuthenticationResult, AuthenticationStats

# Mock LoginResult since we'll be mocking the external login function
class MockLoginResult:
    def __init__(self, success=True, method_used="test_method", error_message="", 
                 login_detected=True, price_access_verified=True, login_duration_seconds=1.5):
        self.success = success
        self.method_used = method_used
        self.error_message = error_message
        self.login_detected = login_detected
        self.price_access_verified = price_access_verified
        self.login_duration_seconds = login_duration_seconds

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

@pytest.fixture
def default_system_config():
    """Fixture providing default system configuration matching system_config.json"""
    return {
        "authentication": {
            "enabled": True,
            "startup_verification": True,
            "consecutive_failure_threshold": 3,
            "primary_periodic_interval": 100,
            "secondary_periodic_interval": 200,
            "max_consecutive_auth_failures": 3,
            "auth_failure_delay_seconds": 30,
            "min_products_between_logins": 10,
            "adaptive_threshold_enabled": False
        },
        "chrome": {
            "debug_port": 9222
        }
    }

@pytest.fixture
def auth_manager(default_system_config):
    """Fixture providing AuthenticationManager with default configuration"""
    return AuthenticationManager(cdp_port=9222, system_config=default_system_config)

@pytest.fixture
def mock_login_result():
    """Fixture providing successful mock login result"""
    return MockLoginResult(
        success=True,
        method_used="test_method",
        error_message="",
        login_detected=True,
        price_access_verified=True,
        login_duration_seconds=1.5
    )

# Test Initialization and Configuration
@pytest.mark.asyncio
async def test_init_defaults_and_config_override():
    """Test AuthenticationManager initialization with default and custom configurations"""
    
    # Test with default config
    default_config = {
        "authentication": {
            "consecutive_failure_threshold": 3,
            "primary_periodic_interval": 100,
            "secondary_periodic_interval": 200,
            "max_consecutive_auth_failures": 3,
            "auth_failure_delay_seconds": 30,
            "min_products_between_logins": 10
        }
    }
    manager = AuthenticationManager(cdp_port=9222, system_config=default_config)
    assert manager.consecutive_failure_threshold == 3
    assert manager.primary_periodic_interval == 100
    assert manager.secondary_periodic_interval == 200
    assert manager.max_consecutive_auth_failures == 3
    assert manager.auth_failure_delay_seconds == 30
    assert manager.min_products_between_logins == 10
    assert manager.stats.session_start_time is not None

    # Test with custom config values
    custom_config = {
        "authentication": {
            "consecutive_failure_threshold": 5,
            "primary_periodic_interval": 50,
            "secondary_periodic_interval": 150,
            "max_consecutive_auth_failures": 2,
            "auth_failure_delay_seconds": 60,
            "min_products_between_logins": 5,
        },
        "chrome": {"debug_port": 9223}
    }
    manager_custom = AuthenticationManager(cdp_port=9223, system_config=custom_config)
    assert manager_custom.consecutive_failure_threshold == 5
    assert manager_custom.primary_periodic_interval == 50
    assert manager_custom.secondary_periodic_interval == 150
    assert manager_custom.max_consecutive_auth_failures == 2
    assert manager_custom.auth_failure_delay_seconds == 60
    assert manager_custom.min_products_between_logins == 5
    assert manager_custom.cdp_port == 9223

    # Test with empty config (should fall back to hardcoded defaults)
    manager_empty = AuthenticationManager(system_config={})
    assert manager_empty.consecutive_failure_threshold == 3
    assert manager_empty.primary_periodic_interval == 100
    assert manager_empty.secondary_periodic_interval == 200

# Test Trigger Logic
@pytest.mark.asyncio
@pytest.mark.parametrize("scenario,prices,expected_trigger,expected_value", [
    ("no_trigger", [10.0, 12.0, 15.0], "no_trigger", 0),
    ("consecutive_failures_3", [None, None, None], "consecutive_failures", 3),
    ("consecutive_failures_mixed", [10.0, None, None, None], "consecutive_failures", 3),
    ("consecutive_failures_reset", [None, None, 10.0, None, None], "no_trigger", 0),
    ("primary_periodic_exact", [1.0] * 100, "periodic_primary", 100),
    ("primary_periodic_over", [1.0] * 101, "periodic_primary", 101),
])
async def test_evaluate_login_needed_triggers(auth_manager, scenario, prices, expected_trigger, expected_value):
    """Test various scenarios for evaluate_login_needed to ensure correct triggers"""
    
    # Reset manager state for each test case
    auth_manager.consecutive_failures = 0
    auth_manager.products_since_login = 0
    auth_manager.total_products_processed = 0
    auth_manager.consecutive_auth_failures = 0  # Ensure circuit breaker is off

    actual_trigger = "no_trigger"
    actual_value = 0

    for i, price in enumerate(prices):
        needs_login, trigger_reason, trigger_value = await auth_manager.evaluate_login_needed(price)
        if needs_login:
            actual_trigger = trigger_reason
            actual_value = trigger_value
            break

    assert actual_trigger == expected_trigger, f"Scenario {scenario}: Expected {expected_trigger}, got {actual_trigger}"
    if expected_trigger != "no_trigger":
        assert actual_value == expected_value, f"Scenario {scenario}: Expected value {expected_value}, got {actual_value}"

@pytest.mark.asyncio
async def test_evaluate_login_needed_consecutive_failures_reset(auth_manager):
    """Test that consecutive failure counter resets on successful price extraction"""
    
    # Simulate 2 failures
    await auth_manager.evaluate_login_needed(None)
    await auth_manager.evaluate_login_needed(0)
    assert auth_manager.consecutive_failures == 2
    
    # Successful price should reset counter
    needs_login, reason, value = await auth_manager.evaluate_login_needed(10.0)
    assert not needs_login
    assert auth_manager.consecutive_failures == 0

@pytest.mark.asyncio
async def test_evaluate_login_needed_secondary_periodic_trigger(auth_manager):
    """Test secondary periodic trigger at 200 products"""
    
    # Process exactly 200 products to trigger secondary periodic
    for i in range(200):
        needs_login, reason, value = await auth_manager.evaluate_login_needed(10.0)
        if i == 199:  # 200th product (0-indexed)
            assert needs_login
            assert reason == "periodic_secondary"
            assert value == 200
        elif i >= auth_manager.primary_periodic_interval - 1:  # Should trigger primary first
            if needs_login and reason == "periodic_primary":
                # Reset after primary trigger
                auth_manager.products_since_login = 0
                auth_manager.consecutive_failures = 0

@pytest.mark.asyncio
async def test_evaluate_login_needed_min_products_between_logins_skip(auth_manager):
    """Test that periodic triggers are skipped if min_products_between_logins is not met"""
    
    auth_manager.min_products_between_logins = 5
    auth_manager.primary_periodic_interval = 3
    auth_manager.products_since_login = 0
    auth_manager.total_products_processed = 0

    # Process 3 products - should hit primary interval but be skipped
    for i in range(3):
        needs_login, reason, value = await auth_manager.evaluate_login_needed(10.0)
        if i == 2:  # 3rd product
            assert not needs_login
            assert reason == "recent_login_skip"
            assert value == 3

    # Process 2 more products to reach min_products_between_logins
    for i in range(2):
        needs_login, reason, value = await auth_manager.evaluate_login_needed(10.0)
    
    # Now should trigger
    assert needs_login
    assert reason == "periodic_primary"
    assert value == 5

# Test Authentication Performance
@pytest.mark.asyncio
async def test_perform_authentication_success(auth_manager, mock_login_result):
    """Test successful authentication verifying stats update and counter resets"""
    
    with patch('authentication_manager.login_to_poundwholesale') as mock_login:
        mock_login.return_value = mock_login_result
        
        # Simulate some prior state
        auth_manager.consecutive_failures = 2
        auth_manager.products_since_login = 50
        auth_manager.consecutive_auth_failures = 1
        auth_manager.stats.total_attempts = 5
        auth_manager.stats.failed_logins = 1

        result = await auth_manager.perform_authentication("startup", 0)

        # Verify call
        mock_login.assert_called_once_with(auth_manager.cdp_port)
        
        # Verify result
        assert result.success is True
        assert result.trigger_reason == "startup"
        assert result.method_used == "test_method"
        
        # Verify stats update
        assert auth_manager.stats.total_attempts == 6
        assert auth_manager.stats.successful_logins == 1
        assert auth_manager.stats.failed_logins == 1  # Should not increment
        assert auth_manager.stats.startup_logins == 1
        
        # Verify counter resets
        assert auth_manager.products_since_login == 0
        assert auth_manager.consecutive_failures == 0
        assert auth_manager.consecutive_auth_failures == 0
        assert auth_manager.stats.last_login_time is not None
        assert result.duration_seconds > 0

@pytest.mark.asyncio
async def test_perform_authentication_failure(auth_manager):
    """Test failed authentication verifying stats update and consecutive auth failures"""
    
    mock_login_result = MockLoginResult(
        success=False,
        error_message="Login failed due to bad credentials",
        login_detected=False,
        price_access_verified=False
    )
    
    with patch('authentication_manager.login_to_poundwholesale') as mock_login:
        mock_login.return_value = mock_login_result
        
        # Simulate some prior state
        auth_manager.consecutive_failures = 0
        auth_manager.products_since_login = 10
        auth_manager.consecutive_auth_failures = 0
        auth_manager.stats.total_attempts = 0
        auth_manager.stats.failed_logins = 0

        result = await auth_manager.perform_authentication("consecutive_failures", 3)

        # Verify result
        assert result.success is False
        assert result.error_message == "Login failed due to bad credentials"
        
        # Verify stats update
        assert auth_manager.stats.total_attempts == 1
        assert auth_manager.stats.successful_logins == 0
        assert auth_manager.stats.failed_logins == 1
        assert auth_manager.stats.consecutive_failure_triggers == 1
        assert auth_manager.consecutive_auth_failures == 1
        assert auth_manager.last_auth_failure_time is not None

@pytest.mark.asyncio
async def test_perform_authentication_exception(auth_manager):
    """Test exception during authentication verifying stats update and error handling"""
    
    with patch('authentication_manager.login_to_poundwholesale') as mock_login:
        mock_login.side_effect = Exception("Playwright error during login")
        
        result = await auth_manager.perform_authentication("periodic_primary", 100)

        # Verify exception handling
        assert result.success is False
        assert "Playwright error during login" in result.error_message
        assert auth_manager.stats.total_attempts == 1
        assert auth_manager.stats.failed_logins == 1
        assert auth_manager.stats.periodic_primary_triggers == 1
        assert auth_manager.consecutive_auth_failures == 1

# Test Circuit Breaker Logic
@pytest.mark.asyncio
async def test_circuit_breaker_activation(auth_manager):
    """Test circuit breaker activation after max_consecutive_auth_failures"""
    
    mock_failure = MockLoginResult(success=False, error_message="Auth failed")
    
    with patch('authentication_manager.login_to_poundwholesale') as mock_login:
        mock_login.return_value = mock_failure
        
        auth_manager.max_consecutive_auth_failures = 3

        # Simulate 3 consecutive authentication failures
        for i in range(3):
            result = await auth_manager.perform_authentication("test_failure", i+1)
            assert result.success is False
            assert auth_manager.consecutive_auth_failures == i + 1
            
            # Circuit breaker should activate only after 3rd failure
            expected_active = (i == 2)
            assert auth_manager._is_circuit_breaker_active() == expected_active

        # After activation, evaluate_login_needed should return circuit_breaker_active
        needs_login, reason, value = await auth_manager.evaluate_login_needed(10.0)
        assert needs_login is False
        assert reason == "circuit_breaker_active"
        assert value == 3

@pytest.mark.asyncio
async def test_circuit_breaker_recovery():
    """Test circuit breaker recovery after cooldown period"""
    
    config = {
        "authentication": {
            "max_consecutive_auth_failures": 3,
            "auth_failure_delay_seconds": 5  # Short delay for testing
        }
    }
    auth_manager = AuthenticationManager(system_config=config)
    
    mock_failure = MockLoginResult(success=False, error_message="Auth failed")
    
    with patch('authentication_manager.login_to_poundwholesale') as mock_login:
        mock_login.return_value = mock_failure
        
        with freeze_time("2023-01-01 10:00:00") as frozen_time:
            # Activate circuit breaker
            for i in range(3):
                await auth_manager.perform_authentication("failure_test", i+1)
                frozen_time.tick(timedelta(seconds=1))

            assert auth_manager._is_circuit_breaker_active() is True
            assert auth_manager.consecutive_auth_failures == 3

            # Still active within cooldown
            frozen_time.tick(timedelta(seconds=4))  # Total 4 seconds since last failure
            needs_login, reason, value = await auth_manager.evaluate_login_needed(10.0)
            assert needs_login is False
            assert reason == "circuit_breaker_active"

            # After cooldown period
            frozen_time.tick(timedelta(seconds=2))  # Total 6 seconds (> 5s delay)
            needs_login, reason, value = await auth_manager.evaluate_login_needed(10.0)
            assert needs_login is False  # No trigger because price is successful
            assert reason == "no_trigger"
            
            # Circuit breaker should be reset
            assert auth_manager._is_circuit_breaker_active() is False
            assert auth_manager.consecutive_auth_failures == 0

# Test Statistics Tracking
@pytest.mark.asyncio
async def test_get_comprehensive_stats_accuracy(auth_manager):
    """Verify comprehensive statistics are accurately tracked and reported"""
    
    mock_success = MockLoginResult(success=True)
    mock_failure = MockLoginResult(success=False, error_message="fail")
    
    # Mock alternating success/failure sequence
    login_sequence = [mock_success, mock_failure, mock_success, mock_failure, mock_success]
    
    with patch('authentication_manager.login_to_poundwholesale') as mock_login:
        mock_login.side_effect = login_sequence
        
        with freeze_time("2023-01-01 10:00:00") as frozen_time:
            # Execute authentication sequence
            await auth_manager.perform_authentication("startup", 0)
            frozen_time.tick(timedelta(seconds=5))
            
            # Trigger consecutive failures auth
            for _ in range(3):
                await auth_manager.evaluate_login_needed(None)
            await auth_manager.perform_authentication("consecutive_failures", 3)
            frozen_time.tick(timedelta(seconds=10))
            
            # Trigger primary periodic auth
            for _ in range(100):
                await auth_manager.evaluate_login_needed(10.0)
            await auth_manager.perform_authentication("periodic_primary", 100)
            frozen_time.tick(timedelta(seconds=15))
            
            # Trigger secondary periodic auth
            for _ in range(200):
                await auth_manager.evaluate_login_needed(10.0)
            await auth_manager.perform_authentication("periodic_secondary", 200)
            frozen_time.tick(timedelta(seconds=20))
            
            # Manual trigger
            await auth_manager.perform_authentication("manual_trigger", 0)

        stats = auth_manager.get_comprehensive_stats()

        # Verify authentication stats
        assert stats["authentication_stats"]["total_attempts"] == 5
        assert stats["authentication_stats"]["successful_logins"] == 3
        assert stats["authentication_stats"]["failed_logins"] == 2
        assert stats["authentication_stats"]["success_rate_percent"] == 60.0

        # Verify trigger breakdown
        assert stats["trigger_breakdown"]["startup_triggers"] == 1
        assert stats["trigger_breakdown"]["consecutive_failure_triggers"] == 1
        assert stats["trigger_breakdown"]["periodic_primary_triggers"] == 1
        assert stats["trigger_breakdown"]["periodic_secondary_triggers"] == 1

        # Verify circuit breaker status
        assert stats["circuit_breaker"]["active"] is False
        assert stats["circuit_breaker"]["consecutive_failures"] == 0

@pytest.mark.asyncio
async def test_log_session_summary(auth_manager, caplog):
    """Test log_session_summary outputs correct information to logs"""
    
    caplog.set_level(logging.INFO)
    
    mock_success = MockLoginResult(success=True)
    mock_failure = MockLoginResult(success=False, error_message="fail")
    
    with patch('authentication_manager.login_to_poundwholesale') as mock_login:
        mock_login.side_effect = [mock_success, mock_failure]
        
        with freeze_time("2023-01-01 10:00:00") as frozen_time:
            await auth_manager.perform_authentication("startup", 0)
            frozen_time.tick(timedelta(seconds=10))
            
            # Process some products and trigger failure
            await auth_manager.evaluate_login_needed(10.0)
            for _ in range(3):
                await auth_manager.evaluate_login_needed(None)
            await auth_manager.perform_authentication("consecutive_failures", 3)

    auth_manager.log_session_summary()

    # Verify log content
    assert "AUTHENTICATION SESSION SUMMARY" in caplog.text
    assert "Session Duration:" in caplog.text
    assert "Products Processed:" in caplog.text
    assert "Authentication Attempts: 2" in caplog.text
    assert "Successful Logins: 1" in caplog.text
    assert "Failed Logins: 1" in caplog.text
    assert "Success Rate: 50.0%" in caplog.text
    assert "TRIGGER BREAKDOWN:" in caplog.text
    assert "Startup: 1" in caplog.text
    assert "Consecutive Failures: 1" in caplog.text

# Test Edge Cases and Boundary Conditions
@pytest.mark.asyncio
async def test_edge_case_zero_price_consecutive_failures(auth_manager):
    """Test that zero prices count as failures for consecutive failure detection"""
    
    # Test None values
    for _ in range(3):
        needs_login, reason, value = await auth_manager.evaluate_login_needed(None)
    assert needs_login
    assert reason == "consecutive_failures"
    
    # Reset and test zero values
    auth_manager.consecutive_failures = 0
    for _ in range(3):
        needs_login, reason, value = await auth_manager.evaluate_login_needed(0.0)
    assert needs_login
    assert reason == "consecutive_failures"

@pytest.mark.asyncio
async def test_edge_case_exact_periodic_boundaries(auth_manager):
    """Test exact boundary conditions for periodic triggers"""
    
    # Test exactly at primary periodic boundary
    for i in range(100):
        needs_login, reason, value = await auth_manager.evaluate_login_needed(10.0)
        if i == 99:  # 100th product
            assert needs_login
            assert reason == "periodic_primary"
            assert value == 100

@pytest.mark.asyncio 
async def test_success_rate_calculation_edge_cases(auth_manager):
    """Test success rate calculation with edge cases"""
    
    # Test with zero attempts
    assert auth_manager._get_success_rate() == 0.0
    
    # Test with only failures
    auth_manager.stats.total_attempts = 3
    auth_manager.stats.successful_logins = 0
    assert auth_manager._get_success_rate() == 0.0
    
    # Test with only successes
    auth_manager.stats.successful_logins = 3
    assert auth_manager._get_success_rate() == 100.0

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])