#!/usr/bin/env python3
"""
KPITracker - Key Performance Indicator tracking and analysis
Part of Amazon FBA Agent System v3.2 - Phase 6 Implementation
Tracks system performance metrics and business intelligence KPIs.
"""

import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics

# Import our file manager
try:
    from utils.file_manager import get_file_manager
    fm = get_file_manager()
except ImportError:
    fm = None


@dataclass
class ProductProcessingMetrics:
    """Metrics for product processing performance"""
    products_processed: int = 0
    products_successful: int = 0
    products_failed: int = 0
    products_skipped: int = 0
    avg_processing_time_seconds: float = 0.0
    total_processing_time_seconds: float = 0.0
    amazon_matches_found: int = 0
    profitable_products_found: int = 0


@dataclass
class BusinessIntelligenceMetrics:
    """Business intelligence and profitability metrics"""
    total_revenue_potential: float = 0.0
    avg_roi_percent: float = 0.0
    avg_profit_per_product: float = 0.0
    high_roi_products: int = 0  # ROI > 50%
    medium_roi_products: int = 0  # ROI 20-50%
    low_roi_products: int = 0  # ROI < 20%
    top_categories: List[str] = field(default_factory=list)
    avg_supplier_price: float = 0.0
    avg_amazon_price: float = 0.0


@dataclass
class SystemPerformanceMetrics:
    """System and technical performance metrics"""
    session_start_time: datetime = field(default_factory=datetime.now)
    session_duration_minutes: float = 0.0
    api_calls_made: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    errors_encountered: int = 0
    recoveries_successful: int = 0


class KPITracker:
    """
    Comprehensive KPI tracking system for Amazon FBA Agent System
    
    Features:
    - Real-time performance tracking
    - Business intelligence metrics
    - Progress monitoring with ETA calculations
    - Historical trend analysis
    - Performance optimization insights
    """
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"session_{int(time.time())}"
        self.session_start = datetime.now()
        self.log = logging.getLogger(__name__)
        
        # Initialize metric containers
        self.processing_metrics = ProductProcessingMetrics()
        self.business_metrics = BusinessIntelligenceMetrics()
        self.system_metrics = SystemPerformanceMetrics()
        
        # Real-time tracking data
        self.processing_times = deque(maxlen=100)  # Last 100 processing times
        self.roi_values = []
        self.profit_values = []
        self.category_counts = defaultdict(int)
        
        # Progress tracking
        self.start_time = time.time()
        self.last_progress_time = time.time()
        self.target_products = 0
        
        # Historical data
        self.hourly_metrics = defaultdict(dict)
        
    def start_session(self, target_products: int = 0):
        """Start a new tracking session"""
        self.target_products = target_products
        self.session_start = datetime.now()
        self.start_time = time.time()
        
        self.log.info(f"📊 KPI Tracking started for session: {self.session_id}")
        if target_products > 0:
            self.log.info(f"🎯 Target: {target_products} products")
    
    def record_product_processing_start(self) -> float:
        """Record start of product processing and return timestamp"""
        return time.time()
    
    def record_product_processing_complete(self, start_time: float, success: bool = True, 
                                         amazon_match_found: bool = False,
                                         roi_percent: float = None,
                                         profit_amount: float = None,
                                         supplier_price: float = None,
                                         amazon_price: float = None,
                                         category: str = None):
        """Record completion of product processing with metrics"""
        processing_time = time.time() - start_time
        self.processing_times.append(processing_time)
        
        # Update processing metrics
        self.processing_metrics.products_processed += 1
        self.processing_metrics.total_processing_time_seconds += processing_time
        
        if success:
            self.processing_metrics.products_successful += 1
        else:
            self.processing_metrics.products_failed += 1
            
        if amazon_match_found:
            self.processing_metrics.amazon_matches_found += 1
            
        # Update average processing time
        if self.processing_metrics.products_processed > 0:
            self.processing_metrics.avg_processing_time_seconds = (
                self.processing_metrics.total_processing_time_seconds / 
                self.processing_metrics.products_processed
            )
        
        # Business intelligence metrics
        if roi_percent is not None:
            self.roi_values.append(roi_percent)
            if roi_percent > 50:
                self.business_metrics.high_roi_products += 1
                self.processing_metrics.profitable_products_found += 1
            elif roi_percent >= 20:
                self.business_metrics.medium_roi_products += 1
                self.processing_metrics.profitable_products_found += 1
            else:
                self.business_metrics.low_roi_products += 1
                
        if profit_amount is not None:
            self.profit_values.append(profit_amount)
            self.business_metrics.total_revenue_potential += profit_amount
            
        if supplier_price is not None and amazon_price is not None:
            # Update price tracking (simplified)
            pass
            
        if category:
            self.category_counts[category] += 1
            
        # Update averages
        if self.roi_values:
            self.business_metrics.avg_roi_percent = statistics.mean(self.roi_values)
        if self.profit_values:
            self.business_metrics.avg_profit_per_product = statistics.mean(self.profit_values)
            
        # Update top categories
        if self.category_counts:
            sorted_categories = sorted(self.category_counts.items(), key=lambda x: x[1], reverse=True)
            self.business_metrics.top_categories = [cat for cat, count in sorted_categories[:5]]
    
    def record_product_skipped(self, reason: str = ""):
        """Record when a product is skipped"""
        self.processing_metrics.products_skipped += 1
        self.log.debug(f"📋 Product skipped: {reason}")
    
    def record_api_call(self, api_name: str, success: bool = True):
        """Record API call for tracking"""
        self.system_metrics.api_calls_made += 1
        if not success:
            self.system_metrics.errors_encountered += 1
    
    def record_cache_hit(self):
        """Record cache hit"""
        self.system_metrics.cache_hits += 1
    
    def record_cache_miss(self):
        """Record cache miss"""  
        self.system_metrics.cache_misses += 1
    
    def get_current_progress(self) -> Dict[str, Any]:
        """Get current progress and performance metrics"""
        current_time = time.time()
        elapsed_seconds = current_time - self.start_time
        elapsed_minutes = elapsed_seconds / 60
        
        # Calculate processing rate
        if elapsed_minutes > 0:
            products_per_hour = (self.processing_metrics.products_processed / elapsed_minutes) * 60
        else:
            products_per_hour = 0
            
        # Calculate ETA
        eta_minutes = 0
        if self.target_products > 0 and products_per_hour > 0:
            remaining_products = self.target_products - self.processing_metrics.products_processed
            eta_minutes = (remaining_products / products_per_hour) * 60
        
        # Calculate success rate
        total_attempts = (self.processing_metrics.products_successful + 
                         self.processing_metrics.products_failed)
        success_rate = (self.processing_metrics.products_successful / total_attempts * 100 
                       if total_attempts > 0 else 0)
        
        # Cache hit rate
        total_cache_requests = self.system_metrics.cache_hits + self.system_metrics.cache_misses
        cache_hit_rate = (self.system_metrics.cache_hits / total_cache_requests * 100 
                         if total_cache_requests > 0 else 0)
        
        progress = {
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'elapsed_minutes': round(elapsed_minutes, 1),
            'products_processed': self.processing_metrics.products_processed,
            'target_products': self.target_products,
            'progress_percent': (self.processing_metrics.products_processed / self.target_products * 100 
                               if self.target_products > 0 else 0),
            'processing_rate': {
                'products_per_hour': round(products_per_hour, 1),
                'avg_seconds_per_product': round(self.processing_metrics.avg_processing_time_seconds, 2),
                'eta_minutes': round(eta_minutes, 1) if eta_minutes > 0 else None
            },
            'success_metrics': {
                'success_rate_percent': round(success_rate, 1),
                'amazon_matches_found': self.processing_metrics.amazon_matches_found,
                'profitable_products': self.processing_metrics.profitable_products_found,
                'products_skipped': self.processing_metrics.products_skipped
            },
            'business_intelligence': {
                'avg_roi_percent': round(self.business_metrics.avg_roi_percent, 1),
                'total_profit_potential': round(self.business_metrics.total_revenue_potential, 2),
                'high_roi_products': self.business_metrics.high_roi_products,
                'top_categories': self.business_metrics.top_categories[:3]
            },
            'system_performance': {
                'api_calls_made': self.system_metrics.api_calls_made,
                'cache_hit_rate_percent': round(cache_hit_rate, 1),
                'errors_encountered': self.system_metrics.errors_encountered
            }
        }
        
        return progress
    
    def print_progress_update(self):
        """Print formatted progress update"""
        progress = self.get_current_progress()
        
        print(f"\n📊 === PROGRESS UPDATE ({datetime.now().strftime('%H:%M:%S')}) ===")
        print(f"🎯 Products: {progress['products_processed']}/{progress['target_products']} "
              f"({progress['progress_percent']:.1f}%)")
        print(f"⏱️  Rate: {progress['processing_rate']['products_per_hour']:.1f}/hour "
              f"({progress['processing_rate']['avg_seconds_per_product']:.1f}s each)")
        
        if progress['processing_rate']['eta_minutes']:
            eta_hours = progress['processing_rate']['eta_minutes'] / 60
            if eta_hours > 1:
                print(f"🕐 ETA: {eta_hours:.1f} hours")
            else:
                print(f"🕐 ETA: {progress['processing_rate']['eta_minutes']:.0f} minutes")
        
        print(f"✅ Success: {progress['success_metrics']['success_rate_percent']:.1f}% "
              f"| 💰 Profitable: {progress['success_metrics']['profitable_products']} "
              f"| 📦 Amazon Matches: {progress['success_metrics']['amazon_matches_found']}")
        
        if progress['business_intelligence']['avg_roi_percent'] > 0:
            print(f"📈 Avg ROI: {progress['business_intelligence']['avg_roi_percent']:.1f}% "
                  f"| 💷 Total Profit Potential: £{progress['business_intelligence']['total_profit_potential']:.2f}")
        
        print(f"🔧 API Calls: {progress['system_performance']['api_calls_made']} "
              f"| 💾 Cache Hit Rate: {progress['system_performance']['cache_hit_rate_percent']:.1f}%")
        
        if progress['business_intelligence']['top_categories']:
            print(f"🏷️  Top Categories: {', '.join(progress['business_intelligence']['top_categories'])}")
    
    def save_progress_checkpoint(self):
        """Save current progress to file"""
        try:
            progress = self.get_current_progress()
            
            if fm:
                checkpoint_path = fm.get_full_path("progress_checkpoint", "logs_performance", 
                                                 "", "active", "json")
            else:
                checkpoint_path = Path(f"progress_checkpoint_{self.session_id}.json")
            
            with open(checkpoint_path, 'w') as f:
                json.dump(progress, f, indent=2)
            
            self.log.debug(f"💾 Progress checkpoint saved: {checkpoint_path}")
            
        except Exception as e:
            self.log.error(f"❌ Failed to save progress checkpoint: {e}")
    
    def generate_session_report(self) -> Dict[str, Any]:
        """Generate comprehensive session report"""
        session_duration = (datetime.now() - self.session_start).total_seconds() / 60
        
        report = {
            'session_summary': {
                'session_id': self.session_id,
                'start_time': self.session_start.isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration_minutes': round(session_duration, 1),
                'target_products': self.target_products,
                'products_processed': self.processing_metrics.products_processed
            },
            'processing_performance': {
                'total_processing_time_seconds': round(self.processing_metrics.total_processing_time_seconds, 1),
                'avg_processing_time_seconds': round(self.processing_metrics.avg_processing_time_seconds, 2),
                'products_per_hour': round((self.processing_metrics.products_processed / session_duration) * 60, 1) if session_duration > 0 else 0,
                'success_rate_percent': round((self.processing_metrics.products_successful / 
                                             max(1, self.processing_metrics.products_processed)) * 100, 1)
            },
            'business_intelligence': {
                'profitable_products_found': self.processing_metrics.profitable_products_found,
                'total_revenue_potential': round(self.business_metrics.total_revenue_potential, 2),
                'avg_roi_percent': round(self.business_metrics.avg_roi_percent, 1),
                'roi_distribution': {
                    'high_roi_products': self.business_metrics.high_roi_products,
                    'medium_roi_products': self.business_metrics.medium_roi_products,
                    'low_roi_products': self.business_metrics.low_roi_products
                },
                'top_categories': self.business_metrics.top_categories
            },
            'system_metrics': {
                'api_calls_made': self.system_metrics.api_calls_made,
                'cache_hits': self.system_metrics.cache_hits,
                'cache_misses': self.system_metrics.cache_misses,
                'cache_hit_rate_percent': round((self.system_metrics.cache_hits / 
                                               max(1, self.system_metrics.cache_hits + self.system_metrics.cache_misses)) * 100, 1),
                'errors_encountered': self.system_metrics.errors_encountered
            }
        }
        
        return report
    
    def save_session_report(self):
        """Save final session report"""
        try:
            report = self.generate_session_report()
            
            if fm:
                report_path = fm.get_full_path("session_report", "analysis_daily", 
                                             "", "complete", "json")
            else:
                report_path = Path(f"session_report_{self.session_id}.json")
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.log.info(f"📋 Session report saved: {report_path}")
            
        except Exception as e:
            self.log.error(f"❌ Failed to save session report: {e}")
    
    def get_performance_insights(self) -> List[str]:
        """Generate performance insights and recommendations"""
        insights = []
        
        # Processing rate analysis
        if self.processing_metrics.products_processed > 10:
            avg_time = self.processing_metrics.avg_processing_time_seconds
            if avg_time > 30:
                insights.append("⚠️  Processing time is high - consider optimizing scraping or caching")
            elif avg_time < 10:
                insights.append("✅ Processing time is excellent - system is well optimized")
        
        # Success rate analysis
        total_attempts = self.processing_metrics.products_successful + self.processing_metrics.products_failed
        if total_attempts > 0:
            success_rate = self.processing_metrics.products_successful / total_attempts
            if success_rate < 0.7:
                insights.append("⚠️  Success rate is low - check error patterns and recovery strategies")
            elif success_rate > 0.9:
                insights.append("✅ Excellent success rate - system is stable")
        
        # Business intelligence insights
        if self.business_metrics.profitable_products_found > 0:
            profitability_rate = (self.business_metrics.profitable_products_found / 
                                max(1, self.processing_metrics.products_processed))
            if profitability_rate > 0.1:
                insights.append("💰 High profitability rate - good supplier selection")
            
        # Cache performance
        total_cache_requests = self.system_metrics.cache_hits + self.system_metrics.cache_misses
        if total_cache_requests > 0:
            cache_rate = self.system_metrics.cache_hits / total_cache_requests
            if cache_rate < 0.5:
                insights.append("💾 Low cache hit rate - consider cache optimization")
            elif cache_rate > 0.8:
                insights.append("✅ Excellent cache performance")
        
        return insights


# Global KPI tracker instance
_global_kpi_tracker = None

def get_kpi_tracker(session_id: str = None) -> KPITracker:
    """Get global KPI tracker instance"""
    global _global_kpi_tracker
    if _global_kpi_tracker is None:
        _global_kpi_tracker = KPITracker(session_id)
    return _global_kpi_tracker


if __name__ == "__main__":
    # Test the KPI tracker
    import random
    
    tracker = KPITracker("test_session")
    tracker.start_session(target_products=10)
    
    print("Testing KPI Tracker...")
    
    # Simulate processing some products
    for i in range(5):
        start_time = tracker.record_product_processing_start()
        
        # Simulate processing time
        import time
        time.sleep(0.1)
        
        # Simulate results
        success = random.choice([True, True, True, False])  # 75% success rate
        roi = random.uniform(10, 80) if success else None
        profit = random.uniform(2, 15) if success else None
        
        tracker.record_product_processing_complete(
            start_time, success, True, roi, profit, category="test_category"
        )
        
        if i % 2 == 0:
            tracker.print_progress_update()
    
    # Generate final report
    report = tracker.generate_session_report()
    print(f"\nFinal Report: {json.dumps(report, indent=2)}")
    
    # Performance insights
    insights = tracker.get_performance_insights()
    print(f"\nInsights: {insights}")