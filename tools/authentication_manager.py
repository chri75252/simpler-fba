#!/usr/bin/env python3
"""
Multi-Tier Authentication Manager for Amazon FBA Agent System v32
Provides comprehensive authentication management with multiple trigger strategies:
- Startup verification
- Consecutive price failure detection (reactive)
- Periodic maintenance (proactive - 100 products)
- Extended session management (ultra long runs - 200 products)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import time

# Configure logging
log = logging.getLogger(__name__)

@dataclass
class AuthenticationResult:
    """Result of authentication attempt with comprehensive details"""
    success: bool
    trigger_reason: str = ""
    trigger_value: int = 0
    method_used: str = ""
    error_message: str = ""
    login_detected: bool = False
    price_access_verified: bool = False
    duration_seconds: float = 0.0
    timestamp: str = ""

@dataclass
class AuthenticationStats:
    """Authentication statistics for monitoring and optimization"""
    total_attempts: int = 0
    successful_logins: int = 0
    failed_logins: int = 0
    startup_logins: int = 0
    consecutive_failure_triggers: int = 0
    periodic_primary_triggers: int = 0
    periodic_secondary_triggers: int = 0
    total_duration_seconds: float = 0.0
    last_login_time: Optional[datetime] = None
    session_start_time: Optional[datetime] = None

class AuthenticationManager:
    """
    Multi-tier authentication manager with intelligent trigger logic.
    Provides comprehensive authentication management for long-running supplier scraping operations.
    """
    
    def __init__(self, cdp_port: int = 9222, system_config: Optional[Dict[str, Any]] = None):
        """
        Initialize authentication manager with configurable parameters.
        
        Args:
            cdp_port: Chrome debug port for browser connection
            system_config: System configuration dictionary for auth settings
        """
        self.cdp_port = cdp_port
        self.system_config = system_config or {}
        
        # Load authentication configuration
        auth_config = self.system_config.get("authentication", {})
        
        # Configurable thresholds with defaults
        self.consecutive_failure_threshold = auth_config.get("consecutive_failure_threshold", 3)
        self.primary_periodic_interval = auth_config.get("primary_periodic_interval", 100)
        self.secondary_periodic_interval = auth_config.get("secondary_periodic_interval", 200)
        
        # State tracking
        self.consecutive_failures = 0
        self.products_since_login = 0
        self.total_products_processed = 0
        
        # Circuit breaker settings
        self.max_consecutive_auth_failures = auth_config.get("max_consecutive_auth_failures", 3)
        self.auth_failure_delay_seconds = auth_config.get("auth_failure_delay_seconds", 30)
        self.consecutive_auth_failures = 0
        self.last_auth_failure_time = None
        
        # Statistics tracking
        self.stats = AuthenticationStats(session_start_time=datetime.now())
        
        # Smart trigger logic settings
        self.min_products_between_logins = auth_config.get("min_products_between_logins", 10)
        self.adaptive_threshold_enabled = auth_config.get("adaptive_threshold_enabled", False)
        
        log.info(f"🔐 AuthenticationManager initialized")
        log.info(f"   Consecutive failure threshold: {self.consecutive_failure_threshold}")
        log.info(f"   Primary periodic interval: {self.primary_periodic_interval}")
        log.info(f"   Secondary periodic interval: {self.secondary_periodic_interval}")
        log.info(f"   CDP port: {self.cdp_port}")

    async def evaluate_login_needed(self, price_extracted: Optional[float] = None) -> Tuple[bool, str, int]:
        """
        Multi-tier evaluation of whether authentication is needed.
        
        Args:
            price_extracted: Price value extracted (None or 0 indicates failure)
            
        Returns:
            Tuple of (needs_login, trigger_reason, trigger_value)
        """
        # Update counters
        self.products_since_login += 1
        self.total_products_processed += 1
        
        # Circuit breaker check
        if self._is_circuit_breaker_active():
            return False, "circuit_breaker_active", self.consecutive_auth_failures
        
        # Tier 2: Consecutive failure detection (reactive)
        if price_extracted is None or price_extracted == 0:
            self.consecutive_failures += 1
            log.debug(f"🔍 Price extraction failure {self.consecutive_failures}/{self.consecutive_failure_threshold}")
            
            if self.consecutive_failures >= self.consecutive_failure_threshold:
                log.warning(f"🚨 Consecutive failure threshold reached: {self.consecutive_failures}")
                return True, "consecutive_failures", self.consecutive_failures
        else:
            # Reset consecutive failures on successful extraction
            if self.consecutive_failures > 0:
                log.debug(f"✅ Price extraction successful - resetting consecutive failure counter (was {self.consecutive_failures})")
                self.consecutive_failures = 0
        
        # Smart trigger logic - prevent redundant logins
        if self.products_since_login < self.min_products_between_logins:
            log.debug(f"🔒 Skipping periodic check - too soon since last login ({self.products_since_login} < {self.min_products_between_logins})")
            return False, "recent_login_skip", self.products_since_login
        
        # Tier 3: Primary periodic fallback (every 100 products)
        if self.products_since_login >= self.primary_periodic_interval:
            log.info(f"📅 Primary periodic trigger reached: {self.products_since_login} products since last login")
            return True, "periodic_primary", self.products_since_login
        
        # Tier 4: Secondary periodic fallback (every 200 products as backup)
        if self.total_products_processed % self.secondary_periodic_interval == 0:
            log.info(f"📅 Secondary periodic trigger reached: {self.total_products_processed} total products processed")
            return True, "periodic_secondary", self.total_products_processed
        
        return False, "no_trigger", 0

    async def perform_authentication(self, trigger_reason: str, trigger_value: int) -> AuthenticationResult:
        """
        Execute authentication with comprehensive logging and statistics.
        
        Args:
            trigger_reason: Reason for authentication attempt
            trigger_value: Value that triggered authentication
            
        Returns:
            AuthenticationResult with comprehensive details
        """
        start_time = time.time()
        self.stats.total_attempts += 1
        
        # Update trigger statistics
        if trigger_reason == "startup":
            self.stats.startup_logins += 1
        elif trigger_reason == "consecutive_failures":
            self.stats.consecutive_failure_triggers += 1
        elif trigger_reason == "periodic_primary":
            self.stats.periodic_primary_triggers += 1
        elif trigger_reason == "periodic_secondary":
            self.stats.periodic_secondary_triggers += 1
        
        log.info(f"🔐 AUTHENTICATION TRIGGER: {trigger_reason} (value: {trigger_value})")
        log.info(f"📊 Current stats: Total products: {self.total_products_processed}, Since last login: {self.products_since_login}")
        log.info(f"📈 Auth attempts: {self.stats.total_attempts} (Success rate: {self._get_success_rate():.1f}%)")
        
        try:
            # Import and execute login
            from tools.standalone_playwright_login import login_to_poundwholesale
            
            login_result = await login_to_poundwholesale(self.cdp_port)
            duration = time.time() - start_time
            
            # Create comprehensive result
            result = AuthenticationResult(
                success=login_result.success,
                trigger_reason=trigger_reason,
                trigger_value=trigger_value,
                method_used=login_result.method_used,
                error_message=login_result.error_message,
                login_detected=login_result.login_detected,
                price_access_verified=login_result.price_access_verified,
                duration_seconds=duration,
                timestamp=datetime.now().isoformat()
            )
            
            # Update statistics and state
            self.stats.total_duration_seconds += duration
            
            if result.success:
                self.stats.successful_logins += 1
                self.stats.last_login_time = datetime.now()
                self.products_since_login = 0  # Reset counter
                self.consecutive_failures = 0  # Reset failures
                self.consecutive_auth_failures = 0  # Reset auth failures
                
                log.info(f"✅ Authentication successful! Method: {result.method_used}")
                log.info(f"💰 Price access verified: {result.price_access_verified}")
                log.info(f"🕒 Authentication duration: {duration:.2f}s")
                log.info(f"📈 Success rate: {self._get_success_rate():.1f}% ({self.stats.successful_logins}/{self.stats.total_attempts})")
                
            else:
                self.stats.failed_logins += 1
                self.consecutive_auth_failures += 1
                self.last_auth_failure_time = datetime.now()
                
                log.error(f"❌ Authentication failed: {result.error_message}")
                log.error(f"🔥 Consecutive auth failures: {self.consecutive_auth_failures}/{self.max_consecutive_auth_failures}")
                
                # Check if circuit breaker should activate
                if self.consecutive_auth_failures >= self.max_consecutive_auth_failures:
                    log.error(f"🚨 Circuit breaker activated - too many consecutive auth failures")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.stats.failed_logins += 1
            self.consecutive_auth_failures += 1
            self.last_auth_failure_time = datetime.now()
            
            log.error(f"❌ Authentication exception: {e}")
            
            return AuthenticationResult(
                success=False,
                trigger_reason=trigger_reason,
                trigger_value=trigger_value,
                error_message=str(e),
                duration_seconds=duration,
                timestamp=datetime.now().isoformat()
            )

    def _is_circuit_breaker_active(self) -> bool:
        """Check if circuit breaker is currently active due to consecutive auth failures"""
        if self.consecutive_auth_failures < self.max_consecutive_auth_failures:
            return False
            
        if self.last_auth_failure_time is None:
            return False
            
        # Check if enough time has passed since last failure
        time_since_failure = datetime.now() - self.last_auth_failure_time
        delay_threshold = timedelta(seconds=self.auth_failure_delay_seconds)
        
        if time_since_failure > delay_threshold:
            log.info(f"🔄 Circuit breaker cooldown period elapsed - re-enabling authentication")
            self.consecutive_auth_failures = 0  # Reset counter
            return False
            
        log.debug(f"🔒 Circuit breaker active - {delay_threshold - time_since_failure} remaining")
        return True

    def _get_success_rate(self) -> float:
        """Calculate authentication success rate percentage"""
        if self.stats.total_attempts == 0:
            return 0.0
        return (self.stats.successful_logins / self.stats.total_attempts) * 100

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive authentication statistics for monitoring"""
        session_duration = datetime.now() - self.stats.session_start_time if self.stats.session_start_time else timedelta(0)
        
        return {
            "session_duration_hours": session_duration.total_seconds() / 3600,
            "total_products_processed": self.total_products_processed,
            "products_since_last_login": self.products_since_login,
            "consecutive_failures": self.consecutive_failures,
            "authentication_stats": {
                "total_attempts": self.stats.total_attempts,
                "successful_logins": self.stats.successful_logins,
                "failed_logins": self.stats.failed_logins,
                "success_rate_percent": self._get_success_rate(),
                "average_duration_seconds": self.stats.total_duration_seconds / max(1, self.stats.total_attempts),
                "last_login_time": self.stats.last_login_time.isoformat() if self.stats.last_login_time else None
            },
            "trigger_breakdown": {
                "startup_triggers": self.stats.startup_logins,
                "consecutive_failure_triggers": self.stats.consecutive_failure_triggers,
                "periodic_primary_triggers": self.stats.periodic_primary_triggers,
                "periodic_secondary_triggers": self.stats.periodic_secondary_triggers
            },
            "circuit_breaker": {
                "active": self._is_circuit_breaker_active(),
                "consecutive_failures": self.consecutive_auth_failures,
                "max_allowed": self.max_consecutive_auth_failures
            }
        }

    def log_session_summary(self):
        """Log comprehensive session summary for analysis"""
        stats = self.get_comprehensive_stats()
        
        log.info("=" * 60)
        log.info("🔐 AUTHENTICATION SESSION SUMMARY")
        log.info("=" * 60)
        log.info(f"⏱️  Session Duration: {stats['session_duration_hours']:.2f} hours")
        log.info(f"📦 Products Processed: {stats['total_products_processed']}")
        log.info(f"🔐 Authentication Attempts: {stats['authentication_stats']['total_attempts']}")
        log.info(f"✅ Successful Logins: {stats['authentication_stats']['successful_logins']}")
        log.info(f"❌ Failed Logins: {stats['authentication_stats']['failed_logins']}")
        log.info(f"📈 Success Rate: {stats['authentication_stats']['success_rate_percent']:.1f}%")
        log.info(f"⚡ Average Auth Duration: {stats['authentication_stats']['average_duration_seconds']:.2f}s")
        log.info("")
        log.info("🎯 TRIGGER BREAKDOWN:")
        log.info(f"   Startup: {stats['trigger_breakdown']['startup_triggers']}")
        log.info(f"   Consecutive Failures: {stats['trigger_breakdown']['consecutive_failure_triggers']}")
        log.info(f"   Periodic (100): {stats['trigger_breakdown']['periodic_primary_triggers']}")
        log.info(f"   Periodic (200): {stats['trigger_breakdown']['periodic_secondary_triggers']}")
        log.info("=" * 60)

# Convenience function for easy integration
async def create_authentication_manager(cdp_port: int = 9222, system_config: Optional[Dict[str, Any]] = None) -> AuthenticationManager:
    """
    Factory function to create and initialize authentication manager.
    
    Args:
        cdp_port: Chrome debug port
        system_config: System configuration dictionary
        
    Returns:
        Configured AuthenticationManager instance
    """
    return AuthenticationManager(cdp_port=cdp_port, system_config=system_config)