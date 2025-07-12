#!/usr/bin/env python3
"""
Amazon FBA Agent System - Real-Time Dashboard Monitoring System
Provides live metrics dashboard with separate files for each metric type.
Updates dynamically as the system runs - no more spam logs!
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict, Counter
import re

class FBADashboardMonitor:
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        
        # Create dashboard directory structure
        self.dashboard_dir = self.base_dir / "DASHBOARD"
        self.metrics_dir = self.dashboard_dir / "metrics"
        self.dashboard_dir.mkdir(exist_ok=True)
        self.metrics_dir.mkdir(exist_ok=True)
        
        # Dashboard files
        self.dashboard_file = self.dashboard_dir / "live_dashboard.txt"
        self.metrics_summary = self.dashboard_dir / "metrics_summary.json"
        
        # Output directories
        self.outputs_dir = self.base_dir / "OUTPUTS" / "FBA_ANALYSIS"
        self.amazon_cache_dir = self.outputs_dir / "amazon_cache"
        self.ai_cache_dir = self.outputs_dir / "ai_category_cache" 
        self.supplier_cache_dir = self.base_dir / "OUTPUTS" / "cached_products"
        self.linking_map_dir = self.outputs_dir / "Linking map"
        self.financial_reports_dir = self.outputs_dir / "financial_reports"
        
        # Metrics tracking
        self.metrics = {}
        self.last_update = None
        self.update_interval = 30  # Update every 30 seconds
        
        # Threading for continuous monitoring
        self.monitoring_thread = None
        self.stop_monitoring = False
        
    def start_monitoring(self):
        """Start continuous dashboard monitoring in background thread"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            print("Dashboard monitoring already running")
            return
            
        self.stop_monitoring = False
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        print(f"📊 Dashboard monitoring started - Check {self.dashboard_file}")
        
    def stop_monitoring_loop(self):
        """Stop continuous monitoring"""
        self.stop_monitoring = True
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        print("📊 Dashboard monitoring stopped")
        
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while not self.stop_monitoring:
            try:
                self.update_dashboard()
                time.sleep(self.update_interval)
            except Exception as e:
                print(f"Dashboard monitoring error: {e}")
                time.sleep(self.update_interval)
                
    def update_dashboard(self):
        """Update all dashboard metrics and files"""
        try:
            # Collect all metrics
            self.metrics = self._collect_all_metrics()
            
            # Update dashboard display
            self._update_dashboard_display()
            
            # Update individual metric files
            self._update_metric_files()
            
            # Save metrics summary
            self._save_metrics_summary()
            
            self.last_update = datetime.now()
            
        except Exception as e:
            print(f"Error updating dashboard: {e}")
            
    def _collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all system metrics"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "categories": self._get_category_metrics(),
            "products": self._get_product_metrics(),
            "amazon_data": self._get_amazon_metrics(),
            "keepa_data": self._get_keepa_metrics(),
            "financial": self._get_financial_metrics(),
            "processing": self._get_processing_metrics(),
            "ai_system": self._get_ai_metrics(),
        }
        return metrics
        
    def _get_category_metrics(self) -> Dict[str, Any]:
        """Get category-related metrics"""
        metrics = {
            "total_categories_discovered": 0,
            "categories_analyzed": 0,
            "categories_with_products": 0,
            "ai_suggested_categories": 0,
            "productive_categories": 0,
            "category_urls": []
        }
        
        try:
            # AI suggested categories
            ai_cache_files = list(self.ai_cache_dir.glob("*_ai_category_cache.json"))
            for cache_file in ai_cache_files:
                with open(cache_file, 'r') as f:
                    ai_data = json.load(f)
                    for entry in ai_data.get("ai_suggestion_history", []):
                        suggestions = entry.get("ai_suggestions", {})
                        top_urls = suggestions.get("top_3_urls", [])
                        secondary_urls = suggestions.get("secondary_urls", [])
                        
                        metrics["ai_suggested_categories"] += len(top_urls) + len(secondary_urls)
                        metrics["category_urls"].extend(top_urls + secondary_urls)
                        
                        # Check validation results
                        validation_results = suggestions.get("validation_results", [])
                        for result in validation_results:
                            if result.get("is_productive", False):
                                metrics["productive_categories"] += 1
                                
            metrics["total_categories_discovered"] = len(set(metrics["category_urls"]))
            
        except Exception as e:
            metrics["error"] = str(e)
            
        return metrics
        
    def _get_product_metrics(self) -> Dict[str, Any]:
        """Get product-related metrics"""
        metrics = {
            "total_supplier_products": 0,
            "products_analyzed": 0,
            "products_with_ean_match": 0,
            "products_with_title_match": 0,
            "products_unmatched": 0,
            "current_processing_index": 0,
            "processing_completion_percentage": 0.0
        }
        
        try:
            # Supplier products
            supplier_cache_files = list(self.supplier_cache_dir.glob("*_products_cache.json"))
            for cache_file in supplier_cache_files:
                with open(cache_file, 'r') as f:
                    supplier_data = json.load(f)
                    metrics["total_supplier_products"] += len(supplier_data)
                    
            # Processing state
            state_files = list(self.outputs_dir.glob("*_processing_state.json"))
            for state_file in state_files:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                    current_index = state_data.get('last_processed_index', 0)
                    metrics["current_processing_index"] = max(metrics["current_processing_index"], current_index)
                    
            # Calculate completion percentage
            if metrics["total_supplier_products"] > 0:
                metrics["processing_completion_percentage"] = (
                    metrics["current_processing_index"] / metrics["total_supplier_products"] * 100
                )
                
        except Exception as e:
            metrics["error"] = str(e)
            
        return metrics
        
    def _get_amazon_metrics(self) -> Dict[str, Any]:
        """Get Amazon cache metrics"""
        metrics = {
            "total_amazon_files": 0,
            "ean_matched_products": 0,
            "title_matched_products": 0,
            "unmatched_products": 0,
            "products_with_amazon_data": 0,
        }
        
        try:
            amazon_files = list(self.amazon_cache_dir.glob("amazon_*.json"))
            metrics["total_amazon_files"] = len(amazon_files)
            
            for amazon_file in amazon_files:
                filename = amazon_file.name
                filename_parts = filename.replace('.json', '').split('_')
                
                # Analyze filename pattern to categorize matches
                if len(filename_parts) == 2:  # amazon_ASIN.json (unmatched)
                    metrics["unmatched_products"] += 1
                elif len(filename_parts) == 3:  # amazon_ASIN_EAN.json (EAN matched)
                    metrics["ean_matched_products"] += 1
                elif len(filename_parts) >= 4 and 'title' in filename_parts:  # title matched
                    metrics["title_matched_products"] += 1
                else:
                    metrics["products_with_amazon_data"] += 1
                    
        except Exception as e:
            metrics["error"] = str(e)
            
        return metrics
        
    def _get_keepa_metrics(self) -> Dict[str, Any]:
        """Get Keepa extraction metrics"""
        metrics = {
            "products_with_keepa_data": 0,
            "keepa_extraction_success": 0,
            "keepa_timeouts": 0,
            "keepa_missing_data": 0,
            "incomplete_fee_data": 0,
            "products_with_complete_fees": 0
        }
        
        try:
            amazon_files = list(self.amazon_cache_dir.glob("amazon_*.json"))
            
            for amazon_file in amazon_files:
                # Only check matched products (skip unmatched ones)
                filename = amazon_file.name
                filename_parts = filename.replace('.json', '').split('_')
                is_matched = len(filename_parts) >= 3
                
                if not is_matched:
                    continue  # Skip unmatched products
                    
                with open(amazon_file, 'r') as f:
                    data = json.load(f)
                    
                keepa_status = data.get('keepa', {}).get('status', '')
                keepa_data = data.get('keepa', {}).get('product_details_tab_data', {})
                
                if 'timeout' in keepa_status.lower():
                    metrics["keepa_timeouts"] += 1
                elif keepa_data and isinstance(keepa_data, dict):
                    metrics["keepa_extraction_success"] += 1
                    
                    # Check for fee completeness
                    has_fba_fee = any('fba' in str(k).lower() or 'pick' in str(k).lower() for k in keepa_data.keys())
                    has_referral_fee = any('referral' in str(k).lower() for k in keepa_data.keys())
                    
                    if has_fba_fee and has_referral_fee:
                        metrics["products_with_complete_fees"] += 1
                    else:
                        metrics["incomplete_fee_data"] += 1
                else:
                    metrics["keepa_missing_data"] += 1
                    
            metrics["products_with_keepa_data"] = metrics["keepa_extraction_success"]
            
        except Exception as e:
            metrics["error"] = str(e)
            
        return metrics
        
    def _get_financial_metrics(self) -> Dict[str, Any]:
        """Get financial analysis metrics"""
        metrics = {
            "csv_reports_generated": 0,
            "products_in_latest_csv": 0,
            "complete_financial_records": 0,
            "latest_csv_timestamp": None,
            "financial_data_completeness_rate": 0.0
        }
        
        try:
            csv_files = list(self.financial_reports_dir.glob("fba_financial_report_*.csv"))
            metrics["csv_reports_generated"] = len(csv_files)
            
            if csv_files:
                latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
                metrics["latest_csv_timestamp"] = datetime.fromtimestamp(latest_csv.stat().st_mtime).isoformat()
                
                # Analyze latest CSV
                import csv
                with open(latest_csv, 'r', newline='') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    
                if len(rows) > 1:
                    metrics["products_in_latest_csv"] = len(rows) - 1
                    
                    # Check completeness
                    header = rows[0]
                    required_columns = ['EAN', 'ASIN', 'supplier_cost', 'amazon_price', 'profit_margin']
                    complete_records = 0
                    
                    for row in rows[1:]:
                        if len(row) >= len(header):
                            row_dict = dict(zip(header, row))
                            if all(row_dict.get(col, '').strip() not in ['', 'N/A', '0.00'] 
                                  for col in required_columns if col in row_dict):
                                complete_records += 1
                                
                    metrics["complete_financial_records"] = complete_records
                    if metrics["products_in_latest_csv"] > 0:
                        metrics["financial_data_completeness_rate"] = (
                            complete_records / metrics["products_in_latest_csv"] * 100
                        )
                        
        except Exception as e:
            metrics["error"] = str(e)
            
        return metrics
        
    def _get_processing_metrics(self) -> Dict[str, Any]:
        """Get processing progress metrics"""
        metrics = {
            "active_processing": False,
            "estimated_time_remaining_minutes": 0,
            "processing_rate_products_per_minute": 0.0,
            "last_activity_timestamp": None
        }
        
        try:
            # Check for recent file modifications
            recent_threshold = datetime.now() - timedelta(minutes=10)
            
            # Check Amazon cache for recent activity
            amazon_files = list(self.amazon_cache_dir.glob("amazon_*.json"))
            if amazon_files:
                latest_file = max(amazon_files, key=lambda x: x.stat().st_mtime)
                last_mod_time = datetime.fromtimestamp(latest_file.stat().st_mtime)
                metrics["last_activity_timestamp"] = last_mod_time.isoformat()
                metrics["active_processing"] = last_mod_time > recent_threshold
                
                # Calculate processing rate (rough estimate)
                files_in_last_hour = sum(1 for f in amazon_files 
                                       if datetime.fromtimestamp(f.stat().st_mtime) > 
                                       datetime.now() - timedelta(hours=1))
                metrics["processing_rate_products_per_minute"] = files_in_last_hour / 60.0
                
                # Estimate remaining time
                if metrics["processing_rate_products_per_minute"] > 0:
                    product_metrics = self._get_product_metrics()
                    remaining_products = (product_metrics["total_supplier_products"] - 
                                        product_metrics["current_processing_index"])
                    metrics["estimated_time_remaining_minutes"] = (
                        remaining_products / metrics["processing_rate_products_per_minute"]
                    )
                    
        except Exception as e:
            metrics["error"] = str(e)
            
        return metrics
        
    def _get_ai_metrics(self) -> Dict[str, Any]:
        """Get AI system metrics"""
        metrics = {
            "total_ai_calls": 0,
            "successful_ai_calls": 0,
            "ai_success_rate": 0.0,
            "latest_ai_suggestion_timestamp": None,
            "ai_fallback_usage": 0
        }
        
        try:
            ai_cache_files = list(self.ai_cache_dir.glob("*_ai_category_cache.json"))
            
            for cache_file in ai_cache_files:
                with open(cache_file, 'r') as f:
                    ai_data = json.load(f)
                    
                metrics["total_ai_calls"] = ai_data.get("total_ai_calls", 0)
                
                for entry in ai_data.get("ai_suggestion_history", []):
                    timestamp = entry.get("timestamp", "")
                    if timestamp and (not metrics["latest_ai_suggestion_timestamp"] or 
                                    timestamp > metrics["latest_ai_suggestion_timestamp"]):
                        metrics["latest_ai_suggestion_timestamp"] = timestamp
                        
                    # Count successful suggestions
                    suggestions = entry.get("ai_suggestions", {})
                    if suggestions.get("top_3_urls"):
                        metrics["successful_ai_calls"] += 1
                        
            if metrics["total_ai_calls"] > 0:
                metrics["ai_success_rate"] = (metrics["successful_ai_calls"] / 
                                            metrics["total_ai_calls"] * 100)
                
        except Exception as e:
            metrics["error"] = str(e)
            
        return metrics
        
    def _update_dashboard_display(self):
        """Update the main dashboard display file"""
        try:
            dashboard_content = f"""
🚀 AMAZON FBA AGENT SYSTEM - LIVE DASHBOARD
{'='*60}
Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 SYSTEM OVERVIEW
{'='*30}
Active Processing: {'🟢 YES' if self.metrics['processing']['active_processing'] else '🔴 NO'}
Processing Rate: {self.metrics['processing']['processing_rate_products_per_minute']:.1f} products/min
Est. Time Remaining: {self.metrics['processing']['estimated_time_remaining_minutes']:.0f} minutes

📁 CATEGORIES
{'='*30}
Total Categories Discovered: {self.metrics['categories']['total_categories_discovered']}
AI Suggested Categories: {self.metrics['categories']['ai_suggested_categories']}
Productive Categories: {self.metrics['categories']['productive_categories']}

📦 PRODUCTS
{'='*30}
Total Supplier Products: {self.metrics['products']['total_supplier_products']}
Current Processing Index: {self.metrics['products']['current_processing_index']}
Processing Completion: {self.metrics['products']['processing_completion_percentage']:.1f}%

🛒 AMAZON DATA
{'='*30}
Total Amazon Files: {self.metrics['amazon_data']['total_amazon_files']}
EAN Matched Products: {self.metrics['amazon_data']['ean_matched_products']}
Title Matched Products: {self.metrics['amazon_data']['title_matched_products']}
Unmatched Products: {self.metrics['amazon_data']['unmatched_products']}

📈 KEEPA EXTRACTION
{'='*30}
Successful Keepa Extractions: {self.metrics['keepa_data']['keepa_extraction_success']}
Keepa Timeouts: {self.metrics['keepa_data']['keepa_timeouts']}
Missing Keepa Data: {self.metrics['keepa_data']['keepa_missing_data']}
Complete Fee Data: {self.metrics['keepa_data']['products_with_complete_fees']}
Incomplete Fee Data: {self.metrics['keepa_data']['incomplete_fee_data']}

💰 FINANCIAL ANALYSIS
{'='*30}
CSV Reports Generated: {self.metrics['financial']['csv_reports_generated']}
Products in Latest CSV: {self.metrics['financial']['products_in_latest_csv']}
Complete Financial Records: {self.metrics['financial']['complete_financial_records']}
Data Completeness Rate: {self.metrics['financial']['financial_data_completeness_rate']:.1f}%

🤖 AI SYSTEM
{'='*30}
Total AI Calls: {self.metrics['ai_system']['total_ai_calls']}
Successful AI Calls: {self.metrics['ai_system']['successful_ai_calls']}
AI Success Rate: {self.metrics['ai_system']['ai_success_rate']:.1f}%

{'='*60}
📂 Detailed metrics available in: {self.metrics_dir}
🔄 Auto-refresh every {self.update_interval} seconds
"""
            
            with open(self.dashboard_file, 'w', encoding='utf-8') as f:
                f.write(dashboard_content)
                
        except Exception as e:
            print(f"Error updating dashboard display: {e}")
            
    def _update_metric_files(self):
        """Update individual metric files with detailed data"""
        try:
            # Categories file
            self._write_metric_file("categories.txt", self._format_categories_detail())
            
            # Products file  
            self._write_metric_file("products.txt", self._format_products_detail())
            
            # Amazon data file
            self._write_metric_file("amazon_data.txt", self._format_amazon_detail())
            
            # Keepa data file
            self._write_metric_file("keepa_data.txt", self._format_keepa_detail())
            
            # Financial file
            self._write_metric_file("financial.txt", self._format_financial_detail())
            
        except Exception as e:
            print(f"Error updating metric files: {e}")
            
    def _write_metric_file(self, filename: str, content: str):
        """Write content to a metric file"""
        filepath = self.metrics_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
    def _format_categories_detail(self) -> str:
        """Format detailed categories information"""
        content = f"""📁 CATEGORIES DETAILED REPORT
{'='*50}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
- Total Categories Discovered: {self.metrics['categories']['total_categories_discovered']}
- AI Suggested: {self.metrics['categories']['ai_suggested_categories']}  
- Productive: {self.metrics['categories']['productive_categories']}

CATEGORY URLS:
"""
        
        try:
            # Get unique category URLs
            unique_urls = list(set(self.metrics['categories']['category_urls']))
            for i, url in enumerate(unique_urls, 1):
                content += f"{i:3d}. {url}\n"
                
        except Exception as e:
            content += f"Error getting category details: {e}\n"
            
        return content
        
    def _format_products_detail(self) -> str:
        """Format detailed products information"""
        content = f"""📦 PRODUCTS DETAILED REPORT
{'='*50}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
- Total Supplier Products: {self.metrics['products']['total_supplier_products']}
- Current Processing Index: {self.metrics['products']['current_processing_index']}
- Completion: {self.metrics['products']['processing_completion_percentage']:.1f}%

RECENT PROCESSING ACTIVITY:
"""
        
        try:
            # Get recent Amazon files to show processing activity
            amazon_files = list(self.amazon_cache_dir.glob("amazon_*.json"))
            recent_files = sorted(amazon_files, key=lambda x: x.stat().st_mtime, reverse=True)[:10]
            
            for f in recent_files:
                mod_time = datetime.fromtimestamp(f.stat().st_mtime)
                content += f"- {f.name} ({mod_time.strftime('%H:%M:%S')})\n"
                
        except Exception as e:
            content += f"Error getting product details: {e}\n"
            
        return content
        
    def _format_amazon_detail(self) -> str:
        """Format detailed Amazon data information"""
        content = f"""🛒 AMAZON DATA DETAILED REPORT
{'='*50}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
- Total Amazon Files: {self.metrics['amazon_data']['total_amazon_files']}
- EAN Matched: {self.metrics['amazon_data']['ean_matched_products']}
- Title Matched: {self.metrics['amazon_data']['title_matched_products']}
- Unmatched: {self.metrics['amazon_data']['unmatched_products']}

RECENT EAN MATCHED PRODUCTS:
"""
        
        try:
            amazon_files = list(self.amazon_cache_dir.glob("amazon_*.json"))
            ean_matched = [f for f in amazon_files if len(f.name.replace('.json', '').split('_')) == 3]
            recent_ean = sorted(ean_matched, key=lambda x: x.stat().st_mtime, reverse=True)[:20]
            
            for f in recent_ean:
                parts = f.name.replace('.json', '').split('_')
                if len(parts) == 3:
                    asin, ean = parts[1], parts[2]
                    mod_time = datetime.fromtimestamp(f.stat().st_mtime)
                    content += f"- ASIN: {asin}, EAN: {ean} ({mod_time.strftime('%H:%M:%S')})\n"
                    
        except Exception as e:
            content += f"Error getting Amazon details: {e}\n"
            
        return content
        
    def _format_keepa_detail(self) -> str:
        """Format detailed Keepa information"""
        content = f"""📈 KEEPA DATA DETAILED REPORT
{'='*50}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
- Successful Extractions: {self.metrics['keepa_data']['keepa_extraction_success']}
- Timeouts: {self.metrics['keepa_data']['keepa_timeouts']}
- Missing Data: {self.metrics['keepa_data']['keepa_missing_data']}
- Complete Fee Data: {self.metrics['keepa_data']['products_with_complete_fees']}

PRODUCTS WITH COMPLETE KEEPA DATA:
"""
        
        try:
            amazon_files = list(self.amazon_cache_dir.glob("amazon_*.json"))
            successful_keepa = []
            
            for f in amazon_files:
                # Only check matched products
                filename_parts = f.name.replace('.json', '').split('_')
                if len(filename_parts) < 3:
                    continue
                    
                try:
                    with open(f, 'r') as file:
                        data = json.load(file)
                        keepa_data = data.get('keepa', {}).get('product_details_tab_data', {})
                        if keepa_data and isinstance(keepa_data, dict):
                            has_fba = any('fba' in str(k).lower() for k in keepa_data.keys())
                            has_referral = any('referral' in str(k).lower() for k in keepa_data.keys())
                            if has_fba and has_referral:
                                successful_keepa.append((f, data.get('asin', 'Unknown')))
                except:
                    continue
                    
            # Show most recent successful extractions
            recent_success = sorted(successful_keepa, key=lambda x: x[0].stat().st_mtime, reverse=True)[:15]
            for file_obj, asin in recent_success:
                mod_time = datetime.fromtimestamp(file_obj.stat().st_mtime)
                content += f"- ASIN: {asin} ({mod_time.strftime('%H:%M:%S')})\n"
                
        except Exception as e:
            content += f"Error getting Keepa details: {e}\n"
            
        return content
        
    def _format_financial_detail(self) -> str:
        """Format detailed financial information"""
        content = f"""💰 FINANCIAL ANALYSIS DETAILED REPORT
{'='*50}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
- CSV Reports: {self.metrics['financial']['csv_reports_generated']}
- Products in Latest CSV: {self.metrics['financial']['products_in_latest_csv']}
- Complete Records: {self.metrics['financial']['complete_financial_records']}
- Completeness Rate: {self.metrics['financial']['financial_data_completeness_rate']:.1f}%

"""
        
        try:
            csv_files = list(self.financial_reports_dir.glob("fba_financial_report_*.csv"))
            if csv_files:
                content += "RECENT CSV REPORTS:\n"
                recent_csvs = sorted(csv_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
                
                for csv_file in recent_csvs:
                    mod_time = datetime.fromtimestamp(csv_file.stat().st_mtime)
                    size_mb = csv_file.stat().st_size / (1024 * 1024)
                    content += f"- {csv_file.name} ({mod_time.strftime('%Y-%m-%d %H:%M:%S')}, {size_mb:.1f}MB)\n"
            else:
                content += "No CSV reports found.\n"
                
        except Exception as e:
            content += f"Error getting financial details: {e}\n"
            
        return content
        
    def _save_metrics_summary(self):
        """Save metrics summary as JSON for other tools"""
        try:
            with open(self.metrics_summary, 'w') as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            print(f"Error saving metrics summary: {e}")
            
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics (for external access)"""
        return self.metrics.copy() if self.metrics else {}


def main():
    """Main function for running dashboard monitor"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FBA Dashboard Monitor")
    parser.add_argument("--base-dir", default=".", help="Base directory for FBA system")
    parser.add_argument("--update-once", action="store_true", help="Run single update instead of continuous")
    parser.add_argument("--interval", type=int, default=30, help="Update interval in seconds")
    
    args = parser.parse_args()
    
    monitor = FBADashboardMonitor(args.base_dir)
    monitor.update_interval = args.interval
    
    if args.update_once:
        print("📊 Running single dashboard update...")
        monitor.update_dashboard()
        print(f"✅ Dashboard updated - Check {monitor.dashboard_file}")
    else:
        print("📊 Starting continuous dashboard monitoring...")
        print(f"📂 Dashboard location: {monitor.dashboard_file}")
        print(f"📁 Metrics details: {monitor.metrics_dir}")
        print("Press Ctrl+C to stop")
        
        try:
            monitor.start_monitoring()
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n📊 Stopping dashboard monitoring...")
            monitor.stop_monitoring_loop()
            print("✅ Dashboard monitoring stopped")


if __name__ == "__main__":
    main()