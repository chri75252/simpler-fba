#!/usr/bin/env python3
"""
Demo script for the Enhanced Cache Manager

This script demonstrates the key features of the new cache management system:
- Health checks
- Cache validation
- Smart selective clearing
- Performance monitoring
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the tools directory to the path
sys.path.append(str(Path(__file__).parent))

from cache_manager import CacheManager, CacheMetrics

async def demo_cache_manager():
    """Demonstrate the enhanced cache manager capabilities"""
    
    print("🚀 Enhanced Cache Manager Demo")
    print("=" * 50)
    
    # Configuration for the demo
    config = {
        "cache": {
            "enabled": True,
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
                    "backup_enabled": True,
                    "validation_enabled": True,
                    "cleanup_strategy": "smart_selective"
                },
                "amazon_cache": {
                    "ttl_hours": 336,
                    "max_size_mb": 2000,
                    "backup_enabled": True,
                    "validation_enabled": True,
                    "cleanup_strategy": "size_based"
                },
                "ai_category_cache": {
                    "ttl_hours": 720,
                    "max_size_mb": 100,
                    "backup_enabled": False,
                    "validation_enabled": True,
                    "cleanup_strategy": "selective"
                },
                "linking_map": {
                    "ttl_hours": -1,
                    "max_size_mb": 500,
                    "backup_enabled": True,
                    "validation_enabled": True,
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
    
    # Initialize cache manager
    cache_manager = CacheManager(config)
    
    try:
        # 1. System Health Check
        print("\n📊 1. CACHE HEALTH CHECK")
        print("-" * 30)
        
        health_report = await cache_manager.health_check()
        
        # Display overall status with emoji
        status_emoji = {
            'healthy': '✅',
            'warning': '⚠️',
            'degraded': '🔶',
            'critical': '🔴',
            'error': '❌'
        }
        
        print(f"Overall Status: {status_emoji.get(health_report['overall_status'], '❓')} {health_report['overall_status'].upper()}")
        
        # Display cache-specific status
        for cache_type, status in health_report['cache_status'].items():
            cache_emoji = status_emoji.get(status['status'], '❓')
            print(f"  {cache_emoji} {cache_type}: {status['status']}")
            
            if status['issues']:
                for issue in status['issues']:
                    print(f"    ⚠️  {issue}")
        
        # Display recommendations
        if health_report['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in health_report['recommendations']:
                print(f"  • {rec}")
        
        # Display system resources
        resources = health_report['system_resources']
        print(f"\n🖥️  System Resources:")
        print(f"  • CPU: {resources['cpu_percent']:.1f}%")
        print(f"  • Memory: {resources['memory_percent']:.1f}%")
        print(f"  • Disk: {resources['disk_usage_percent']:.1f}%")
        
        # 2. Cache Metrics
        print("\n📈 2. CACHE METRICS")
        print("-" * 30)
        
        metrics = await cache_manager.get_cache_metrics()
        total_size_mb = 0
        total_files = 0
        
        for cache_type, cache_metrics in metrics.items():
            size_mb = cache_metrics.size_mb
            file_count = cache_metrics.file_count
            
            total_size_mb += size_mb
            total_files += file_count
            
            # Format size with appropriate units
            if size_mb < 1:
                size_str = f"{size_mb * 1024:.1f} KB"
            elif size_mb < 1024:
                size_str = f"{size_mb:.1f} MB"
            else:
                size_str = f"{size_mb / 1024:.1f} GB"
            
            print(f"  📁 {cache_type}:")
            print(f"     Files: {file_count}")
            print(f"     Size: {size_str}")
            
            if cache_metrics.hit_rate > 0:
                print(f"     Hit Rate: {cache_metrics.hit_rate:.1%}")
        
        print(f"\n📊 Total: {total_files} files, {total_size_mb:.1f} MB")
        
        # 3. Cache Validation
        print("\n🔍 3. CACHE VALIDATION")
        print("-" * 30)
        
        validation_results = await cache_manager.validate_cache()
        
        for cache_type, results in validation_results.items():
            if not results:
                print(f"  📁 {cache_type}: No files to validate")
                continue
                
            valid_count = sum(1 for r in results if r.is_valid)
            total_count = len(results)
            
            if valid_count == total_count:
                print(f"  ✅ {cache_type}: All {total_count} files valid")
            else:
                invalid_count = total_count - valid_count
                print(f"  ⚠️  {cache_type}: {valid_count}/{total_count} files valid ({invalid_count} corrupted)")
                
                # Show details of invalid files
                for result in results:
                    if not result.is_valid:
                        print(f"    ❌ {result.file_path.name}: {', '.join(result.errors)}")
        
        # 4. Smart Cache Clearing Demo
        print("\n🧹 4. SMART CACHE CLEARING")
        print("-" * 30)
        
        print("Testing smart selective clearing strategy...")
        clearing_results = await cache_manager.clear_cache("smart_selective")
        
        total_removed = 0
        total_freed = 0
        
        for cache_type, result in clearing_results.items():
            if result.files_removed > 0 or result.bytes_freed > 0:
                freed_mb = result.bytes_freed / (1024 * 1024)
                print(f"  🗑️  {cache_type}: Removed {result.files_removed} items, freed {freed_mb:.1f} MB")
                total_removed += result.files_removed
                total_freed += result.bytes_freed
            else:
                print(f"  ✨ {cache_type}: No cleaning needed")
            
            if result.errors:
                for error in result.errors:
                    print(f"    ❌ Error: {error}")
        
        if total_removed > 0:
            total_freed_mb = total_freed / (1024 * 1024)
            print(f"\n📊 Total cleaned: {total_removed} items, {total_freed_mb:.1f} MB freed")
        else:
            print(f"\n✨ All caches are already optimized!")
        
        # 5. Cache Optimization
        print("\n⚡ 5. CACHE OPTIMIZATION")
        print("-" * 30)
        
        optimization_results = await cache_manager.optimize_cache()
        
        if optimization_results['compression_savings'] > 0:
            savings_mb = optimization_results['compression_savings'] / (1024 * 1024)
            print(f"  📦 Compression savings: {savings_mb:.1f} MB")
        else:
            print(f"  ✨ No files needed compression")
        
        if optimization_results['errors']:
            for error in optimization_results['errors']:
                print(f"  ❌ Optimization error: {error}")
        
        # 6. Backup Creation
        print("\n💾 6. BACKUP CREATION")
        print("-" * 30)
        
        backup_results = await cache_manager.create_backup()
        
        for cache_type, success in backup_results.items():
            if success:
                print(f"  ✅ {cache_type}: Backup created successfully")
            else:
                print(f"  ❌ {cache_type}: Backup failed")
        
        print("\n🎉 Demo completed successfully!")
        print("\nKey Benefits Demonstrated:")
        print("  • Comprehensive health monitoring")
        print("  • Intelligent cache clearing strategies")
        print("  • Data validation and corruption detection")
        print("  • Performance optimization")
        print("  • Automated backup management")
        print("  • Real-time metrics and reporting")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await cache_manager.cleanup()

def create_sample_cache_files():
    """Create some sample cache files for demonstration"""
    
    # Create sample supplier cache
    supplier_cache_dir = Path("OUTPUTS/cached_products")
    supplier_cache_dir.mkdir(parents=True, exist_ok=True)
    
    sample_supplier_data = [
        {
            "title": "Sample Product 1",
            "price": "€29.99",
            "url": "https://example.com/product1",
            "ean": "1234567890123"
        },
        {
            "title": "Sample Product 2", 
            "price": "€45.50",
            "url": "https://example.com/product2",
            "ean": "2345678901234"
        }
    ]
    
    with open(supplier_cache_dir / "sample_products_cache.json", 'w') as f:
        json.dump(sample_supplier_data, f, indent=2)
    
    # Create sample linking map
    linking_map_dir = Path("OUTPUTS/FBA_ANALYSIS/Linking map")
    linking_map_dir.mkdir(parents=True, exist_ok=True)
    
    sample_linking_data = [
        {
            "supplier_product_identifier": "EAN_1234567890123",
            "chosen_amazon_asin": "B08EXAMPLE1",
            "confidence_score": 0.95
        }
    ]
    
    with open(linking_map_dir / "linking_map.json", 'w') as f:
        json.dump(sample_linking_data, f, indent=2)
    
    print("📁 Sample cache files created for demonstration")

if __name__ == "__main__":
    print("Setting up demo environment...")
    create_sample_cache_files()
    print()
    
    # Run the demo
    asyncio.run(demo_cache_manager())
