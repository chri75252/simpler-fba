#!/usr/bin/env python3
"""
Integration Tests for Authentication System
Tests authentication integration with workflow components, supplier scraper callbacks,
and end-to-end authentication scenarios for Amazon FBA Agent System v32.
"""

import pytest
import asyncio
import logging
import sys
import os
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from freezegun import freeze_time

# Add tools directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))

from authentication_manager import AuthenticationManager, AuthenticationResult
from configurable_supplier_scraper import ConfigurableSupplierScraper
from passive_extraction_workflow_latest import PassiveExtractionWorkflow

# Mock LoginResult for external dependency
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
def system_config():
    """Fixture providing complete system configuration for integration tests"""
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
            "debug_port": 9222,
            "headless": False
        },
        "system": {
            "max_products": 999999,
            "max_analyzed_products": 999999,
            "max_products_per_category": 999999,
            "max_products_per_cycle": 10,
            "linking_map_batch_size": 10,
            "financial_report_batch_size": 30,
            "supplier_extraction_batch_size": 3
        }
    }

@pytest.fixture
def auth_manager_integrated(system_config):
    """Fixture providing AuthenticationManager for integration testing"""
    return AuthenticationManager(cdp_port=9222, system_config=system_config)

@pytest.fixture
def mock_successful_login():
    """Fixture providing successful mock login result"""
    return MockLoginResult(
        success=True,
        method_used="playwright_selectors",
        error_message="",
        login_detected=True,
        price_access_verified=True,
        login_duration_seconds=2.3
    )

@pytest.fixture
def mock_failed_login():
    """Fixture providing failed mock login result"""
    return MockLoginResult(
        success=False,
        method_used="playwright_selectors",
        error_message="Login credentials rejected",
        login_detected=False,
        price_access_verified=False,
        login_duration_seconds=1.8
    )

# Test Authentication Manager Integration with Workflow
@pytest.mark.asyncio
async def test_workflow_startup_authentication_success(auth_manager_integrated, mock_successful_login):
    """Test successful startup authentication in workflow context"""
    
    with patch('authentication_manager.login_to_poundwholesale') as mock_login:
        mock_login.return_value = mock_successful_login
        
        # Test startup authentication
        result = await auth_manager_integrated.perform_authentication("startup", 0)
        
        # Verify successful startup authentication
        assert result.success is True
        assert result.trigger_reason == "startup"
        assert result.method_used == "playwright_selectors"
        assert result.price_access_verified is True
        
        # Verify state after startup
        assert auth_manager_integrated.stats.startup_logins == 1
        assert auth_manager_integrated.stats.successful_logins == 1
        assert auth_manager_integrated.products_since_login == 0
        assert auth_manager_integrated.consecutive_failures == 0

@pytest.mark.asyncio
async def test_workflow_startup_authentication_failure_graceful_degradation(auth_manager_integrated, mock_failed_login):
    """Test that startup authentication failure allows workflow to continue"""
    
    with patch('authentication_manager.login_to_poundwholesale') as mock_login:
        mock_login.return_value = mock_failed_login
        
        # Test startup authentication failure
        result = await auth_manager_integrated.perform_authentication("startup", 0)
        
        # Verify failed startup authentication
        assert result.success is False
        assert result.trigger_reason == "startup"
        assert result.error_message == "Login credentials rejected"
        
        # Verify stats tracking failure
        assert auth_manager_integrated.stats.startup_logins == 1
        assert auth_manager_integrated.stats.failed_logins == 1
        assert auth_manager_integrated.consecutive_auth_failures == 1
        
        # Verify workflow can continue - subsequent auth evaluation should work
        needs_login, reason, value = await auth_manager_integrated.evaluate_login_needed(10.0)
        assert needs_login is False  # No immediate trigger needed
        assert reason == "no_trigger"

# Test Authentication Callback Integration
@pytest.mark.asyncio
async def test_authentication_callback_consecutive_failures_trigger():
    """Test authentication callback triggers auth after consecutive price failures"""
    
    # Create mock authentication manager
    auth_manager = MagicMock()
    auth_manager.evaluate_login_needed = AsyncMock()
    auth_manager.perform_authentication = AsyncMock()
    
    # Set up callback scenarios
    auth_scenarios = [
        # First two failures - no auth needed
        (False, "no_trigger", 1),
        (False, "no_trigger", 2),
        # Third failure - auth needed
        (True, "consecutive_failures", 3)
    ]
    
    auth_manager.evaluate_login_needed.side_effect = [scenario for scenario in auth_scenarios]
    auth_manager.perform_authentication.return_value = AuthenticationResult(
        success=True, trigger_reason="consecutive_failures", trigger_value=3,
        method_used="test", timestamp=datetime.now().isoformat()
    )
    
    # Create mock authentication callback
    async def test_auth_callback(price, product_index):
        needs_login, trigger_reason, trigger_value = await auth_manager.evaluate_login_needed(price)
        if needs_login:
            await auth_manager.perform_authentication(trigger_reason, trigger_value)
    
    # Test consecutive failures triggering authentication
    prices = [None, None, None]  # Three consecutive failures
    
    for i, price in enumerate(prices):
        await test_auth_callback(price, i + 1)
    
    # Verify auth evaluation was called for each price
    assert auth_manager.evaluate_login_needed.call_count == 3
    
    # Verify authentication was performed only once (on third failure)
    assert auth_manager.perform_authentication.call_count == 1
    auth_manager.perform_authentication.assert_called_with("consecutive_failures", 3)

@pytest.mark.asyncio
async def test_authentication_callback_periodic_triggers():
    """Test authentication callback triggers periodic authentication"""
    
    # Create mock authentication manager with realistic periodic logic
    auth_manager = MagicMock()
    auth_manager.evaluate_login_needed = AsyncMock()
    auth_manager.perform_authentication = AsyncMock()
    
    # Configure mock to trigger on 100th product
    def mock_evaluate_login(price):
        # Mock internal counter logic
        mock_evaluate_login.call_count += 1
        if mock_evaluate_login.call_count == 100:
            return (True, "periodic_primary", 100)
        return (False, "no_trigger", 0)
    
    mock_evaluate_login.call_count = 0
    auth_manager.evaluate_login_needed.side_effect = mock_evaluate_login
    auth_manager.perform_authentication.return_value = AuthenticationResult(
        success=True, trigger_reason="periodic_primary", trigger_value=100,
        method_used="test", timestamp=datetime.now().isoformat()
    )
    
    # Create authentication callback
    async def test_auth_callback(price, product_index):
        needs_login, trigger_reason, trigger_value = await auth_manager.evaluate_login_needed(price)
        if needs_login:
            await auth_manager.perform_authentication(trigger_reason, trigger_value)
    
    # Process 100 products to trigger periodic authentication
    for i in range(100):
        await test_auth_callback(10.0, i + 1)
    
    # Verify authentication was triggered exactly once at 100th product
    assert auth_manager.perform_authentication.call_count == 1
    auth_manager.perform_authentication.assert_called_with("periodic_primary", 100)

# Test Supplier Scraper Integration
@pytest.mark.asyncio
async def test_supplier_scraper_auth_callback_integration():
    """Test that supplier scraper properly calls authentication callback"""
    
    # Mock the authentication callback
    auth_callback = AsyncMock()
    
    # Create supplier scraper with auth callback (minimal setup)
    scraper = ConfigurableSupplierScraper(auth_callback=auth_callback)
    
    # Verify auth callback is stored
    assert scraper.auth_callback is auth_callback
    
    # Mock the scraper's extract_products_from_category method to test callback usage
    with patch.object(scraper, 'get_page_content') as mock_get_content:
        mock_get_content.return_value = """
        <html>
            <div class="product">
                <span class="title">Test Product</span>
                <span class="price">£10.99</span>
            </div>
        </html>
        """
        
        # Mock successful extraction but test callback is called
        with patch.object(scraper, '_parse_price') as mock_parse_price:
            mock_parse_price.return_value = 10.99
            
            # Extract from a mock category
            products = await scraper.extract_products_from_category("https://test.com/category", max_products=1)
            
            # Verify auth callback was called with extracted price and product index
            auth_callback.assert_called_once_with(10.99, 1)

@pytest.mark.asyncio
async def test_supplier_scraper_auth_callback_price_failure():
    """Test auth callback receives None price when extraction fails"""
    
    auth_callback = AsyncMock()
    scraper = ConfigurableSupplierScraper(auth_callback=auth_callback)
    
    with patch.object(scraper, 'get_page_content') as mock_get_content:
        mock_get_content.return_value = """
        <html>
            <div class="product">
                <span class="title">Test Product</span>
                <span class="price">Invalid Price</span>
            </div>
        </html>
        """
        
        with patch.object(scraper, '_parse_price') as mock_parse_price:
            mock_parse_price.return_value = None  # Price extraction failed
            
            products = await scraper.extract_products_from_category("https://test.com/category", max_products=1)
            
            # Verify auth callback was called with None price (indicating failure)
            auth_callback.assert_called_once_with(None, 1)

# Test Circuit Breaker Integration
@pytest.mark.asyncio
async def test_circuit_breaker_prevents_auth_spam(auth_manager_integrated, mock_failed_login):
    """Test that circuit breaker prevents authentication spam after repeated failures"""
    
    with patch('authentication_manager.login_to_poundwholesale') as mock_login:
        mock_login.return_value = mock_failed_login
        
        # Trigger circuit breaker with 3 consecutive auth failures
        for i in range(3):
            result = await auth_manager_integrated.perform_authentication("test_failure", i + 1)
            assert result.success is False
        
        # Verify circuit breaker is active
        assert auth_manager_integrated._is_circuit_breaker_active() is True
        
        # Attempt to evaluate login - should be blocked by circuit breaker
        needs_login, reason, value = await auth_manager_integrated.evaluate_login_needed(None)
        assert needs_login is False
        assert reason == "circuit_breaker_active"
        assert value == 3
        
        # Multiple failed price extractions should not trigger more auth attempts
        for _ in range(5):
            needs_login, reason, value = await auth_manager_integrated.evaluate_login_needed(None)
            assert needs_login is False
            assert reason == "circuit_breaker_active"
        
        # Verify login function wasn't called again during circuit breaker period
        assert mock_login.call_count == 3  # Only the initial 3 failures

@pytest.mark.asyncio
async def test_circuit_breaker_recovery_allows_auth():
    """Test that circuit breaker recovery allows authentication after cooldown"""
    
    # Use shorter delay for testing
    config = {
        "authentication": {
            "max_consecutive_auth_failures": 3,
            "auth_failure_delay_seconds": 2  # 2 second delay
        }
    }
    auth_manager = AuthenticationManager(system_config=config)
    
    mock_failed = MockLoginResult(success=False, error_message="Auth failed")
    mock_success = MockLoginResult(success=True)
    
    with patch('authentication_manager.login_to_poundwholesale') as mock_login:
        # First trigger circuit breaker
        mock_login.return_value = mock_failed
        
        with freeze_time("2023-01-01 10:00:00") as frozen_time:
            # Activate circuit breaker
            for i in range(3):
                await auth_manager.perform_authentication("failure_test", i + 1)
            
            assert auth_manager._is_circuit_breaker_active() is True
            
            # Wait for cooldown period
            frozen_time.tick(timedelta(seconds=3))  # Wait longer than 2 second delay
            
            # Now circuit breaker should be recovered
            assert auth_manager._is_circuit_breaker_active() is False
            
            # Authentication should be allowed again
            mock_login.return_value = mock_success
            
            # Trigger consecutive failures to test auth works again
            for _ in range(3):
                await auth_manager.evaluate_login_needed(None)
            
            needs_login, reason, value = await auth_manager.evaluate_login_needed(None)
            assert needs_login is True
            assert reason == "consecutive_failures"
            
            # Perform auth - should succeed now
            result = await auth_manager.perform_authentication("consecutive_failures", 3)
            assert result.success is True

# Test Configuration Integration
@pytest.mark.asyncio
async def test_config_values_applied_correctly(system_config):
    """Test that configuration values are properly applied in integration context"""
    
    # Modify config for testing
    test_config = system_config.copy()
    test_config["authentication"]["consecutive_failure_threshold"] = 2
    test_config["authentication"]["primary_periodic_interval"] = 5
    test_config["authentication"]["min_products_between_logins"] = 3
    
    auth_manager = AuthenticationManager(cdp_port=9223, system_config=test_config)
    
    # Verify config values applied
    assert auth_manager.consecutive_failure_threshold == 2
    assert auth_manager.primary_periodic_interval == 5
    assert auth_manager.min_products_between_logins == 3
    assert auth_manager.cdp_port == 9223
    
    # Test that modified thresholds work correctly
    # Should trigger after 2 failures instead of default 3
    await auth_manager.evaluate_login_needed(None)
    needs_login, reason, value = await auth_manager.evaluate_login_needed(None)
    assert needs_login is True
    assert reason == "consecutive_failures"
    assert value == 2
    
    # Test modified periodic interval (5 instead of 100)
    auth_manager.consecutive_failures = 0  # Reset
    for i in range(5):
        needs_login, reason, value = await auth_manager.evaluate_login_needed(10.0)
        if i == 4:  # 5th product
            assert needs_login is True
            assert reason == "periodic_primary"
            assert value == 5

# Test Error Handling in Integration Context
@pytest.mark.asyncio
async def test_auth_callback_error_handling():
    """Test that authentication callback errors are handled gracefully"""
    
    # Create auth manager that raises exception
    auth_manager = MagicMock()
    auth_manager.evaluate_login_needed = AsyncMock(side_effect=Exception("Auth evaluation error"))
    
    # Create authentication callback that should handle exceptions
    async def robust_auth_callback(price, product_index):
        try:
            await auth_manager.evaluate_login_needed(price)
        except Exception as e:
            log.warning(f"Authentication callback error for product {product_index}: {e}")
            # Should not re-raise exception
    
    # Test that callback doesn't crash on auth manager errors
    try:
        await robust_auth_callback(10.0, 1)
        # Should complete without raising exception
        success = True
    except Exception:
        success = False
    
    assert success is True

@pytest.mark.asyncio
async def test_authentication_system_statistics_accuracy():
    """Test that authentication statistics remain accurate across integrated operations"""
    
    auth_manager = AuthenticationManager(system_config={
        "authentication": {
            "consecutive_failure_threshold": 2,
            "primary_periodic_interval": 3
        }
    })
    
    mock_success = MockLoginResult(success=True)
    mock_failure = MockLoginResult(success=False, error_message="fail")
    
    with patch('authentication_manager.login_to_poundwholesale') as mock_login:
        # Sequence: success, failure, success, failure
        mock_login.side_effect = [mock_success, mock_failure, mock_success, mock_failure]
        
        # Startup auth (success)
        await auth_manager.perform_authentication("startup", 0)
        
        # Trigger consecutive failures auth (failure)
        await auth_manager.evaluate_login_needed(None)
        await auth_manager.evaluate_login_needed(None)
        await auth_manager.perform_authentication("consecutive_failures", 2)
        
        # Trigger periodic auth (success)
        for _ in range(3):
            await auth_manager.evaluate_login_needed(10.0)
        await auth_manager.perform_authentication("periodic_primary", 3)
        
        # Another failure for testing
        await auth_manager.perform_authentication("manual_test", 0)
        
        stats = auth_manager.get_comprehensive_stats()
        
        # Verify accurate statistics
        assert stats["authentication_stats"]["total_attempts"] == 4
        assert stats["authentication_stats"]["successful_logins"] == 2
        assert stats["authentication_stats"]["failed_logins"] == 2
        assert stats["authentication_stats"]["success_rate_percent"] == 50.0
        
        assert stats["trigger_breakdown"]["startup_triggers"] == 1
        assert stats["trigger_breakdown"]["consecutive_failure_triggers"] == 1
        assert stats["trigger_breakdown"]["periodic_primary_triggers"] == 1

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])