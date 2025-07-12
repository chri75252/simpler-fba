# Cache Manager Integration Guide

## Overview

This guide explains how to integrate the enhanced cache management system into the Amazon FBA Agent System. The new cache manager provides intelligent cache clearing, data validation, performance monitoring, and automated maintenance.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install psutil
```

### 2. Update System Configuration

Add the cache configuration to your `system_config.json`:

```json
{
  "cache": {
    "enabled": true,
    "global_settings": {
      "max_total_size_gb": 5.0,
      "default_ttl_hours": 336,
      "backup_retention_days": 7,
      "validation_interval_hours": 6,
      "optimization_interval_hours": 24
    },
    "cache_types": {
      "supplier_cache": {
        "ttl_hours": 336,
        "max_size_mb": 1000,
        "backup_enabled": true,
        "validation_enabled": true,
        "cleanup_strategy": "smart_selective"
      },
      "amazon_cache": {
        "ttl_hours": 336,
        "max_size_mb": 2000,
        "backup_enabled": true,
        "validation_enabled": true,
        "cleanup_strategy": "size_based"
      },
      "ai_category_cache": {
        "ttl_hours": 720,
        "max_size_mb": 100,
        "backup_enabled": false,
        "validation_enabled": true,
        "cleanup_strategy": "selective"
      },
      "linking_map": {
        "ttl_hours": -1,
        "max_size_mb": 500,
        "backup_enabled": true,
        "validation_enabled": true,
        "cleanup_strategy": "archive_old"
      }
    },
    "directories": {
      "supplier_cache": "OUTPUTS/cached_products",
      "amazon_cache": "OUTPUTS/FBA_ANALYSIS/amazon_cache",
      "ai_category_cache": "OUTPUTS/FBA_ANALYSIS/ai_category_cache",
      "linking_map": "OUTPUTS/FBA_ANALYSIS/Linking map"
    }
  }
}
```

### 3. Basic Integration

```python
from tools.cache_manager import CacheManager
import json

# Load configuration
with open('system_config.json', 'r') as f:
    config = json.load(f)

# Initialize cache manager
cache_manager = CacheManager(config)

# Perform health check
health_report = await cache_manager.health_check()
print(f"Cache Status: {health_report['overall_status']}")

# Clear cache intelligently
results = await cache_manager.clear_cache("smart_selective")
```

## 🔧 Integration Points

### 1. Main Application Startup

Add cache manager initialization to your main application:

```python
# main.py or app.py
import asyncio
from tools.cache_manager import CacheManager

class FBAAgentSystem:
    def __init__(self, config):
        self.config = config
        self.cache_manager = CacheManager(config)
    
    async def startup(self):
        """Application startup routine"""
        # Perform cache health check on startup
        health_report = await self.cache_manager.health_check()
        
        if health_report['overall_status'] in ['critical', 'error']:
            print("⚠️ Cache issues detected on startup!")
            for rec in health_report['recommendations']:
                print(f"  • {rec}")
        
        # Schedule periodic maintenance
        asyncio.create_task(self._periodic_cache_maintenance())
    
    async def _periodic_cache_maintenance(self):
        """Run periodic cache maintenance"""
        while True:
            try:
                # Wait 6 hours between maintenance cycles
                await asyncio.sleep(6 * 3600)
                
                # Validate caches
                await self.cache_manager.validate_cache()
                
                # Optimize if needed
                await self.cache_manager.optimize_cache()
                
                # Clear old data
                await self.cache_manager.clear_cache("smart_selective")
                
            except Exception as e:
                print(f"Cache maintenance error: {e}")
    
    async def shutdown(self):
        """Application shutdown routine"""
        await self.cache_manager.cleanup()
```

### 2. Supplier Data Processing Integration

```python
# supplier_processor.py
class SupplierProcessor:
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
    
    async def process_supplier_data(self, supplier_url):
        """Process supplier data with cache management"""
        
        # Before processing, check cache health
        metrics = await self.cache_manager.get_cache_metrics()
        supplier_metrics = metrics.get('supplier_cache')
        
        if supplier_metrics and supplier_metrics.size_mb > 800:  # 80% of 1000MB limit
            print("🧹 Supplier cache getting large, cleaning up...")
            await self.cache_manager.clear_cache("smart_selective", ["supplier_cache"])
        
        # Your existing supplier processing logic here...
        
        # After processing, validate cache integrity
        validation_results = await self.cache_manager.validate_cache(["supplier_cache"])
        supplier_validation = validation_results.get('supplier_cache', [])
        
        corrupted_files = [r for r in supplier_validation if not r.is_valid]
        if corrupted_files:
            print(f"⚠️ Found {len(corrupted_files)} corrupted cache files")
            # Handle corruption (backup, repair, etc.)
```

### 3. Amazon Data Processing Integration

```python
# amazon_processor.py
class AmazonProcessor:
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
    
    async def process_amazon_data(self, asin_list):
        """Process Amazon data with intelligent caching"""
        
        # Check if we need to clear old Amazon cache (336-hour TTL)
        cache_info = await self.cache_manager._get_cache_info(
            Path("OUTPUTS/FBA_ANALYSIS/amazon_cache"),
            {"ttl_hours": 336, "max_size_mb": 2000}
        )

        if cache_info['age_hours'] > 336:
            print("🔄 Amazon cache expired, clearing old data...")
            await self.cache_manager.clear_cache("size_based", ["amazon_cache"])
        
        # Your existing Amazon processing logic here...
```

### 4. Error Handling Integration

```python
# error_handler.py
class ErrorHandler:
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
    
    async def handle_cache_corruption(self, error):
        """Handle cache corruption errors"""
        print(f"🔧 Handling cache corruption: {error}")
        
        # Create backup before attempting repair
        backup_results = await self.cache_manager.create_backup()
        
        # Validate all caches to identify corruption
        validation_results = await self.cache_manager.validate_cache()
        
        for cache_type, results in validation_results.items():
            corrupted_files = [r for r in results if not r.is_valid]
            
            if corrupted_files:
                print(f"🔧 Repairing {len(corrupted_files)} corrupted files in {cache_type}")
                
                for result in corrupted_files:
                    # Remove corrupted file
                    try:
                        result.file_path.unlink()
                        print(f"  ✅ Removed corrupted file: {result.file_path.name}")
                    except Exception as e:
                        print(f"  ❌ Failed to remove {result.file_path.name}: {e}")
```

### 5. CLI Integration

```python
# cli.py
import click
from tools.cache_manager import CacheManager

@click.group()
def cache():
    """Cache management commands"""
    pass

@cache.command()
@click.option('--strategy', default='smart_selective', help='Clearing strategy')
@click.option('--cache-type', multiple=True, help='Specific cache types to clear')
def clear(strategy, cache_type):
    """Clear cache using specified strategy"""
    
    async def _clear():
        with open('system_config.json', 'r') as f:
            config = json.load(f)
        
        cache_manager = CacheManager(config)
        
        try:
            cache_types = list(cache_type) if cache_type else None
            results = await cache_manager.clear_cache(strategy, cache_types)
            
            for cache_type, result in results.items():
                if result.files_removed > 0:
                    freed_mb = result.bytes_freed / (1024 * 1024)
                    click.echo(f"✅ {cache_type}: Removed {result.files_removed} items, freed {freed_mb:.1f} MB")
                else:
                    click.echo(f"✨ {cache_type}: No cleaning needed")
        
        finally:
            await cache_manager.cleanup()
    
    asyncio.run(_clear())

@cache.command()
def health():
    """Check cache health"""
    
    async def _health():
        with open('system_config.json', 'r') as f:
            config = json.load(f)
        
        cache_manager = CacheManager(config)
        
        try:
            health_report = await cache_manager.health_check()
            
            status_colors = {
                'healthy': 'green',
                'warning': 'yellow',
                'degraded': 'yellow',
                'critical': 'red',
                'error': 'red'
            }
            
            color = status_colors.get(health_report['overall_status'], 'white')
            click.echo(click.style(f"Overall Status: {health_report['overall_status'].upper()}", fg=color))
            
            for cache_type, status in health_report['cache_status'].items():
                cache_color = status_colors.get(status['status'], 'white')
                click.echo(f"  {cache_type}: ", nl=False)
                click.echo(click.style(status['status'], fg=cache_color))
                
                for issue in status['issues']:
                    click.echo(f"    ⚠️  {issue}")
            
            if health_report['recommendations']:
                click.echo("\n💡 Recommendations:")
                for rec in health_report['recommendations']:
                    click.echo(f"  • {rec}")
        
        finally:
            await cache_manager.cleanup()
    
    asyncio.run(_health())

@cache.command()
def metrics():
    """Show cache metrics"""
    
    async def _metrics():
        with open('system_config.json', 'r') as f:
            config = json.load(f)
        
        cache_manager = CacheManager(config)
        
        try:
            metrics = await cache_manager.get_cache_metrics()
            
            total_size_mb = 0
            total_files = 0
            
            for cache_type, cache_metrics in metrics.items():
                size_mb = cache_metrics.size_mb
                file_count = cache_metrics.file_count
                
                total_size_mb += size_mb
                total_files += file_count
                
                click.echo(f"📁 {cache_type}:")
                click.echo(f"   Files: {file_count}")
                click.echo(f"   Size: {size_mb:.1f} MB")
                
                if cache_metrics.hit_rate > 0:
                    click.echo(f"   Hit Rate: {cache_metrics.hit_rate:.1%}")
            
            click.echo(f"\n📊 Total: {total_files} files, {total_size_mb:.1f} MB")
        
        finally:
            await cache_manager.cleanup()
    
    asyncio.run(_metrics())

if __name__ == '__main__':
    cache()
```

## 🔄 Migration from Old Cache System

### Step 1: Backup Existing Cache

```bash
# Create backup of existing cache
mkdir -p OUTPUTS/cache_backup_$(date +%Y%m%d)
cp -r OUTPUTS/cached_products OUTPUTS/cache_backup_$(date +%Y%m%d)/
cp -r "OUTPUTS/FBA_ANALYSIS/Linking map" OUTPUTS/cache_backup_$(date +%Y%m%d)/
```

### Step 2: Update Existing Code

Replace manual cache clearing with cache manager calls:

```python
# OLD CODE:
def clear_cache_files():
    cache_dir = Path("OUTPUTS/cached_products")
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

# NEW CODE:
async def clear_cache_intelligently():
    results = await cache_manager.clear_cache("smart_selective", ["supplier_cache"])
    return results
```

### Step 3: Add Health Monitoring

```python
# Add to your existing monitoring/logging system
async def log_cache_health():
    health_report = await cache_manager.health_check()
    
    # Log to your existing logging system
    logger.info(f"Cache health: {health_report['overall_status']}")
    
    if health_report['overall_status'] != 'healthy':
        logger.warning(f"Cache issues detected: {health_report['recommendations']}")
```

## 📊 Monitoring and Alerting

### Health Check Integration

```python
# monitoring.py
async def cache_health_monitor():
    """Monitor cache health and send alerts"""
    
    health_report = await cache_manager.health_check()
    
    if health_report['overall_status'] == 'critical':
        # Send critical alert
        await send_alert(
            level="CRITICAL",
            message=f"Cache system critical: {health_report['recommendations']}"
        )
    
    elif health_report['overall_status'] in ['warning', 'degraded']:
        # Send warning alert
        await send_alert(
            level="WARNING", 
            message=f"Cache system needs attention: {health_report['recommendations']}"
        )
    
    # Log metrics for monitoring dashboard
    metrics = await cache_manager.get_cache_metrics()
    for cache_type, cache_metrics in metrics.items():
        await log_metric(f"cache.{cache_type}.size_mb", cache_metrics.size_mb)
        await log_metric(f"cache.{cache_type}.file_count", cache_metrics.file_count)
        await log_metric(f"cache.{cache_type}.hit_rate", cache_metrics.hit_rate)
```

## 🧪 Testing

### Unit Tests

```python
# test_cache_manager.py
import pytest
from tools.cache_manager import CacheManager

@pytest.fixture
def cache_manager():
    config = {
        "cache": {
            "directories": {
                "test_cache": "test_outputs/cache"
            },
            "cache_types": {
                "test_cache": {
                    "ttl_hours": 336,
                    "max_size_mb": 100
                }
            }
        }
    }
    return CacheManager(config)

@pytest.mark.asyncio
async def test_health_check(cache_manager):
    health_report = await cache_manager.health_check()
    assert 'overall_status' in health_report
    assert 'cache_status' in health_report

@pytest.mark.asyncio
async def test_cache_clearing(cache_manager):
    results = await cache_manager.clear_cache("smart_selective")
    assert isinstance(results, dict)
```

### Integration Tests

```python
# test_integration.py
@pytest.mark.asyncio
async def test_full_workflow():
    """Test complete cache management workflow"""
    
    # Initialize
    cache_manager = CacheManager(test_config)
    
    # Health check
    health = await cache_manager.health_check()
    assert health['overall_status'] in ['healthy', 'warning']
    
    # Validation
    validation = await cache_manager.validate_cache()
    assert isinstance(validation, dict)
    
    # Clearing
    clearing = await cache_manager.clear_cache("smart_selective")
    assert isinstance(clearing, dict)
    
    # Cleanup
    await cache_manager.cleanup()
```

## 🚀 Performance Optimization

### Async Operations

The cache manager is designed for async operations. Always use `await`:

```python
# ✅ CORRECT
health_report = await cache_manager.health_check()
results = await cache_manager.clear_cache("smart_selective")

# ❌ INCORRECT
health_report = cache_manager.health_check()  # This returns a coroutine!
```

### Batch Operations

Process multiple cache types efficiently:

```python
# Clear multiple cache types in one call
results = await cache_manager.clear_cache(
    strategy="smart_selective",
    cache_types=["supplier_cache", "amazon_cache"]
)

# Validate multiple cache types
validation_results = await cache_manager.validate_cache(
    cache_types=["supplier_cache", "linking_map"]
)
```

### Resource Management

Always cleanup resources:

```python
try:
    # Your cache operations
    await cache_manager.clear_cache("smart_selective")
finally:
    # Always cleanup
    await cache_manager.cleanup()
```

## 🔧 Troubleshooting

### Common Issues

1. **Permission Errors**
   ```python
   # Ensure proper file permissions
   import os
   os.chmod("OUTPUTS/cached_products", 0o755)
   ```

2. **Disk Space Issues**
   ```python
   # Check disk space before operations
   health_report = await cache_manager.health_check()
   if health_report['system_resources']['disk_usage_percent'] > 90:
       await cache_manager.clear_cache("size_based")
   ```

3. **Corrupted Cache Files**
   ```python
   # Validate and repair
   validation_results = await cache_manager.validate_cache()
   for cache_type, results in validation_results.items():
       corrupted = [r for r in results if not r.is_valid]
       if corrupted:
           # Create backup first
           await cache_manager.create_backup([cache_type])
           # Then remove corrupted files
           for result in corrupted:
               result.file_path.unlink()
   ```

## 📈 Best Practices

1. **Regular Health Checks**: Run health checks on startup and periodically
2. **Intelligent Clearing**: Use smart_selective strategy for most cases
3. **Monitor Metrics**: Track cache size and hit rates
4. **Backup Critical Data**: Enable backups for important caches like linking_map
5. **Validate Regularly**: Run validation to catch corruption early
6. **Resource Monitoring**: Watch disk space and system resources
7. **Error Handling**: Always handle cache operations gracefully
8. **Async Operations**: Use proper async/await patterns
9. **Configuration Management**: Keep cache settings in configuration files
10. **Testing**: Test cache operations in your CI/CD pipeline

## 🎯 Next Steps

1. **Deploy**: Integrate the cache manager into your system
2. **Monitor**: Set up monitoring and alerting
3. **Optimize**: Tune cache settings based on usage patterns
4. **Extend**: Add custom cache strategies if needed
5. **Scale**: Consider distributed caching for larger deployments

For questions or issues, refer to the cache manager source code or create an issue in the project repository.
