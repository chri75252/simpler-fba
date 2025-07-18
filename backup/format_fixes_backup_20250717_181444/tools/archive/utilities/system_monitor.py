"""
System monitoring and health check module
"""
import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
from pathlib import Path

# Try to import psutil, provide fallback if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available. System metrics will be limited.")

log = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    active_tasks: int
    error_count: int
    products_processed: int
    avg_processing_time: float

class SystemMonitor:
    """
    Monitor system health and performance.
    """
    
    def __init__(self, log_dir: str = "logs/monitoring"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.metrics: List[SystemMetrics] = []
        self.error_log: List[Dict[str, Any]] = []
        self.task_timings: List[float] = []
        self.products_processed = 0
        self.monitoring = False
        
    async def start_monitoring(self, interval: int = 60):
        """Start continuous monitoring."""
        self.monitoring = True
        while self.monitoring:
            metrics = await self.collect_metrics()
            self.metrics.append(metrics)
            await self.save_metrics(metrics)
            await asyncio.sleep(interval)
    
    def stop_monitoring(self):
        """Stop monitoring."""
        self.monitoring = False
    
    async def collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        # Default values for when psutil is not available
        cpu_percent = 0.0
        memory_percent = 0.0
        disk_usage_percent = 0.0
        
        if PSUTIL_AVAILABLE:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                disk_usage_percent = psutil.disk_usage('/').percent
            except Exception as e:
                log.warning(f"Error collecting system metrics: {e}")
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_usage_percent=disk_usage_percent,
            active_tasks=len(asyncio.all_tasks()),
            error_count=len(self.error_log),
            products_processed=self.products_processed,
            avg_processing_time=sum(self.task_timings) / len(self.task_timings) if self.task_timings else 0
        )
    
    async def save_metrics(self, metrics: SystemMetrics):
        """Save metrics to file."""
        filename = self.log_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.jsonl"
        try:
            # Use regular file I/O since aiofiles might not be available
            with open(filename, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(metrics), default=str) + '\n')
        except Exception as e:
            log.error(f"Failed to save metrics: {e}")
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log error with context."""
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }
        self.error_log.append(error_entry)
        log.error(f"Error logged: {error_entry}")
    
    def record_task_timing(self, duration: float):
        """Record task processing time."""
        self.task_timings.append(duration)
        # Keep only last 1000 timings
        if len(self.task_timings) > 1000:
            self.task_timings = self.task_timings[-1000:]
    
    def increment_products_processed(self):
        """Increment processed products counter."""
        self.products_processed += 1
    
    async def generate_health_report(self) -> Dict[str, Any]:
        """Generate system health report."""
        if not self.metrics:
            return {'status': 'no_data'}
            
        recent_metrics = self.metrics[-10:]  # Last 10 measurements
        
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        
        health_status = 'healthy'
        warnings = []
        
        if avg_cpu > 80:
            warnings.append('High CPU usage')
            health_status = 'warning'
        if avg_memory > 85:
            warnings.append('High memory usage')
            health_status = 'warning'
        if self.error_log and len(self.error_log) > 10:
            warnings.append(f'High error rate: {len(self.error_log)} errors')
            health_status = 'critical' if len(self.error_log) > 50 else 'warning'
            
        return {
            'status': health_status,
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'avg_cpu_percent': round(avg_cpu, 2),
                'avg_memory_percent': round(avg_memory, 2),
                'total_products_processed': self.products_processed,
                'avg_processing_time_seconds': round(sum(self.task_timings) / len(self.task_timings), 2) if self.task_timings else 0,
                'error_count': len(self.error_log)
            },
            'warnings': warnings,
            'recent_errors': self.error_log[-5:] if self.error_log else []
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.metrics:
            return {'status': 'no_data'}
            
        recent_metrics = self.metrics[-100:]  # Last 100 measurements
        
        return {
            'total_products_processed': self.products_processed,
            'total_errors': len(self.error_log),
            'avg_processing_time': round(sum(self.task_timings) / len(self.task_timings), 2) if self.task_timings else 0,
            'min_processing_time': round(min(self.task_timings), 2) if self.task_timings else 0,
            'max_processing_time': round(max(self.task_timings), 2) if self.task_timings else 0,
            'system_metrics': {
                'avg_cpu': round(sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics), 2),
                'avg_memory': round(sum(m.memory_percent for m in recent_metrics) / len(recent_metrics), 2),
                'avg_active_tasks': round(sum(m.active_tasks for m in recent_metrics) / len(recent_metrics), 2)
            },
            'monitoring_period': {
                'start': recent_metrics[0].timestamp.isoformat() if recent_metrics else None,
                'end': recent_metrics[-1].timestamp.isoformat() if recent_metrics else None,
                'duration_hours': round((recent_metrics[-1].timestamp - recent_metrics[0].timestamp).total_seconds() / 3600, 2) if len(recent_metrics) > 1 else 0
            }
        }