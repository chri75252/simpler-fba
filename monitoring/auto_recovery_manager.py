#!/usr/bin/env python3
"""
AutoRecoveryManager - Intelligent error recovery and monitoring system
Part of Amazon FBA Agent System v3.2 - Phase 6 Implementation
Provides automated recovery from common failures and intelligent retry logic.
"""

import asyncio
import logging
import time
import psutil
import gc
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import traceback
import functools

# Import our file manager
try:
    from utils.file_manager import get_file_manager
    fm = get_file_manager()
except ImportError:
    fm = None


class RecoveryAction(Enum):
    """Types of recovery actions"""
    RETRY = "retry"
    SKIP = "skip"
    RESTART_COMPONENT = "restart_component"
    CLEAR_CACHE = "clear_cache"
    WAIT_AND_RETRY = "wait_and_retry"
    ESCALATE = "escalate"


@dataclass
class RecoveryAttempt:
    """Single recovery attempt record"""
    timestamp: datetime
    error_type: str
    error_message: str
    action_taken: RecoveryAction
    success: bool
    retry_count: int
    recovery_time_seconds: float


@dataclass
class ComponentHealth:
    """Health status of a system component"""
    name: str
    status: str = "healthy"  # healthy, degraded, failed
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    failure_count: int = 0
    recovery_attempts: List[RecoveryAttempt] = field(default_factory=list)


class AutoRecoveryManager:
    """
    Intelligent error recovery and monitoring system
    
    Features:
    - Automatic retry with exponential backoff
    - Component health monitoring
    - Memory management
    - Failure pattern detection
    - Recovery strategy optimization
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.log = logging.getLogger(__name__)
        
        # Component health tracking
        self.component_health: Dict[str, ComponentHealth] = {}
        
        # Recovery statistics
        self.recovery_stats = {
            'total_failures': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'components_restarted': 0,
            'cache_clears': 0
        }
        
        # Memory management settings
        self.memory_threshold_percent = 80
        self.cleanup_interval_minutes = 30
        self.last_cleanup = datetime.now()
        
        # Error patterns for intelligent recovery
        self.error_patterns = {
            'ConnectionError': RecoveryAction.WAIT_AND_RETRY,
            'TimeoutError': RecoveryAction.RETRY,
            'MemoryError': RecoveryAction.CLEAR_CACHE,
            'JSONDecodeError': RecoveryAction.SKIP,
            'PlaywrightTimeoutError': RecoveryAction.RESTART_COMPONENT,
            'HTTPError': RecoveryAction.WAIT_AND_RETRY,
            'OpenAIError': RecoveryAction.WAIT_AND_RETRY
        }
        
    def monitor_component(self, component_name: str):
        """Decorator to monitor component health"""
        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._execute_with_monitoring(component_name, func, args, kwargs)
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self._execute_with_monitoring_sync(component_name, func, args, kwargs)
            
            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        return decorator
    
    async def _execute_with_monitoring(self, component_name: str, func: Callable, args: tuple, kwargs: dict):
        """Execute function with full monitoring and recovery"""
        if component_name not in self.component_health:
            self.component_health[component_name] = ComponentHealth(component_name)
        
        component = self.component_health[component_name]
        
        for attempt in range(self.max_retries + 1):
            try:
                # Memory check before execution
                await self._check_memory_usage()
                
                # Execute the function
                start_time = time.time()
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Success - update component health
                component.status = "healthy"
                component.last_success = datetime.now()
                component.failure_count = 0
                
                self.log.info(f"✅ {component_name}: Success in {execution_time:.2f}s")
                return result
                
            except Exception as e:
                # Record failure
                component.last_failure = datetime.now()
                component.failure_count += 1
                self.recovery_stats['total_failures'] += 1
                
                error_type = type(e).__name__
                error_message = str(e)
                
                self.log.warning(f"❌ {component_name}: {error_type} - {error_message} (attempt {attempt + 1}/{self.max_retries + 1})")
                
                # Determine recovery action
                recovery_action = self._determine_recovery_action(error_type, attempt)
                
                if attempt < self.max_retries:
                    recovery_success = await self._execute_recovery_action(
                        component_name, recovery_action, error_type, error_message, attempt
                    )
                    
                    if recovery_success:
                        self.recovery_stats['successful_recoveries'] += 1
                        # Record successful recovery attempt
                        recovery_attempt = RecoveryAttempt(
                            timestamp=datetime.now(),
                            error_type=error_type,
                            error_message=error_message,
                            action_taken=recovery_action,
                            success=True,
                            retry_count=attempt + 1,
                            recovery_time_seconds=0
                        )
                        component.recovery_attempts.append(recovery_attempt)
                        continue  # Retry the operation
                    else:
                        self.recovery_stats['failed_recoveries'] += 1
                
                # Final failure after all retries
                component.status = "failed"
                recovery_attempt = RecoveryAttempt(
                    timestamp=datetime.now(),
                    error_type=error_type,
                    error_message=error_message,
                    action_taken=RecoveryAction.ESCALATE,
                    success=False,
                    retry_count=attempt + 1,
                    recovery_time_seconds=0
                )
                component.recovery_attempts.append(recovery_attempt)
                
                self.log.error(f"💥 {component_name}: All recovery attempts failed. Final error: {e}")
                raise e
    
    def _execute_with_monitoring_sync(self, component_name: str, func: Callable, args: tuple, kwargs: dict):
        """Synchronous version of monitoring execution"""
        # For sync functions, we'll use a simpler monitoring approach
        if component_name not in self.component_health:
            self.component_health[component_name] = ComponentHealth(component_name)
        
        component = self.component_health[component_name]
        
        try:
            result = func(*args, **kwargs)
            component.status = "healthy"
            component.last_success = datetime.now()
            component.failure_count = 0
            return result
        except Exception as e:
            component.last_failure = datetime.now()
            component.failure_count += 1
            component.status = "failed"
            self.log.error(f"💥 {component_name}: {type(e).__name__} - {str(e)}")
            raise
    
    def _determine_recovery_action(self, error_type: str, attempt: int) -> RecoveryAction:
        """Determine the best recovery action based on error type and attempt count"""
        # Check predefined patterns
        if error_type in self.error_patterns:
            action = self.error_patterns[error_type]
        else:
            # Default strategy based on attempt number
            if attempt == 0:
                action = RecoveryAction.RETRY
            elif attempt == 1:
                action = RecoveryAction.WAIT_AND_RETRY
            else:
                action = RecoveryAction.CLEAR_CACHE
        
        return action
    
    async def _execute_recovery_action(self, component_name: str, action: RecoveryAction, 
                                     error_type: str, error_message: str, attempt: int) -> bool:
        """Execute the determined recovery action"""
        self.log.info(f"🔧 {component_name}: Executing recovery action: {action.value}")
        
        try:
            if action == RecoveryAction.RETRY:
                # Simple retry with short delay
                await asyncio.sleep(0.5)
                return True
                
            elif action == RecoveryAction.WAIT_AND_RETRY:
                # Exponential backoff
                delay = self.base_delay * (2 ** attempt)
                self.log.info(f"⏳ {component_name}: Waiting {delay:.1f}s before retry")
                await asyncio.sleep(delay)
                return True
                
            elif action == RecoveryAction.CLEAR_CACHE:
                # Memory cleanup and garbage collection
                self.log.info(f"🧹 {component_name}: Clearing cache and running garbage collection")
                gc.collect()
                self.recovery_stats['cache_clears'] += 1
                await asyncio.sleep(1)
                return True
                
            elif action == RecoveryAction.RESTART_COMPONENT:
                # Component-specific restart logic
                self.log.info(f"🔄 {component_name}: Attempting component restart")
                # This would be component-specific logic
                self.recovery_stats['components_restarted'] += 1
                await asyncio.sleep(2)
                return True
                
            elif action == RecoveryAction.SKIP:
                # Skip this operation and continue
                self.log.info(f"⏭️  {component_name}: Skipping failed operation")
                return False  # Don't retry, but don't fail the entire process
                
            else:
                return False
                
        except Exception as e:
            self.log.error(f"❌ Recovery action {action.value} failed: {e}")
            return False
    
    async def _check_memory_usage(self):
        """Check memory usage and trigger cleanup if needed"""
        memory_percent = psutil.virtual_memory().percent
        
        if memory_percent > self.memory_threshold_percent:
            self.log.warning(f"🐏 High memory usage: {memory_percent:.1f}% > {self.memory_threshold_percent}%")
            await self._perform_memory_cleanup()
    
    async def _perform_memory_cleanup(self):
        """Perform memory cleanup operations"""
        self.log.info("🧹 Performing memory cleanup...")
        
        # Garbage collection
        collected = gc.collect()
        self.log.info(f"   Collected {collected} objects")
        
        # Update last cleanup time
        self.last_cleanup = datetime.now()
        
        # Wait a moment for cleanup to take effect
        await asyncio.sleep(1)
        
        new_memory_percent = psutil.virtual_memory().percent
        self.log.info(f"   Memory usage after cleanup: {new_memory_percent:.1f}%")
    
    def get_component_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'recovery_stats': self.recovery_stats.copy(),
            'system_health': {
                'memory_usage_percent': psutil.virtual_memory().percent,
                'cpu_usage_percent': psutil.cpu_percent(),
                'last_cleanup': self.last_cleanup.isoformat()
            },
            'components': {}
        }
        
        for name, component in self.component_health.items():
            component_report = {
                'status': component.status,
                'failure_count': component.failure_count,
                'last_success': component.last_success.isoformat() if component.last_success else None,
                'last_failure': component.last_failure.isoformat() if component.last_failure else None,
                'recent_recoveries': len([r for r in component.recovery_attempts 
                                        if r.timestamp > datetime.now() - timedelta(hours=1)])
            }
            report['components'][name] = component_report
        
        return report
    
    def save_health_report(self):
        """Save health report to file"""
        try:
            report = self.get_component_health_report()
            
            if fm:
                report_path = fm.get_full_path("health_report", "logs_performance", "", "active", "json")
            else:
                report_path = Path("health_report.json")
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.log.info(f"📊 Health report saved: {report_path}")
            
        except Exception as e:
            self.log.error(f"❌ Failed to save health report: {e}")
    
    def get_recovery_recommendations(self) -> List[str]:
        """Generate recommendations based on current system state"""
        recommendations = []
        
        # Check overall failure rate
        total_attempts = self.recovery_stats['successful_recoveries'] + self.recovery_stats['failed_recoveries']
        if total_attempts > 0:
            success_rate = self.recovery_stats['successful_recoveries'] / total_attempts
            if success_rate < 0.7:
                recommendations.append("Consider reviewing error patterns - recovery success rate is low")
        
        # Check memory usage
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > 85:
            recommendations.append("High memory usage detected - consider increasing cleanup frequency")
        
        # Check component health
        failed_components = [name for name, comp in self.component_health.items() if comp.status == "failed"]
        if failed_components:
            recommendations.append(f"Failed components need attention: {', '.join(failed_components)}")
        
        # Check frequent failures
        frequent_failures = [name for name, comp in self.component_health.items() if comp.failure_count > 5]
        if frequent_failures:
            recommendations.append(f"Components with frequent failures: {', '.join(frequent_failures)}")
        
        return recommendations


# Convenience function for global recovery manager
_global_recovery_manager = None

def get_recovery_manager() -> AutoRecoveryManager:
    """Get global recovery manager instance"""
    global _global_recovery_manager
    if _global_recovery_manager is None:
        _global_recovery_manager = AutoRecoveryManager()
    return _global_recovery_manager


# Convenience decorator
def auto_recover(component_name: str):
    """Convenience decorator for auto-recovery"""
    recovery_manager = get_recovery_manager()
    return recovery_manager.monitor_component(component_name)


if __name__ == "__main__":
    # Test the recovery manager
    async def test_recovery_manager():
        manager = AutoRecoveryManager()
        
        @manager.monitor_component("test_component")
        async def test_function(should_fail: bool = False):
            if should_fail:
                raise ConnectionError("Test connection error")
            return "success"
        
        # Test successful operation
        result = await test_function(False)
        print(f"Success: {result}")
        
        # Test failure and recovery
        try:
            await test_function(True)
        except Exception as e:
            print(f"Final failure: {e}")
        
        # Print health report
        report = manager.get_component_health_report()
        print(f"Health report: {json.dumps(report, indent=2)}")
    
    asyncio.run(test_recovery_manager())