#!/usr/bin/env python3
"""
Comprehensive System Monitor for Amazon FBA Agent System
Generates detailed monitoring report with all metrics and errors in single file
"""

import json
import os
import glob
import csv
from datetime import datetime
from collections import defaultdict, Counter
import re

class ComprehensiveSystemMonitor:
    def __init__(self, base_path):
        self.base_path = base_path
        self.outputs_path = os.path.join(base_path, "OUTPUTS", "FBA_ANALYSIS")
        self.report_data = {
            'summary': {},
            'ai_categories': {},
            'processing_metrics': {},
            'amazon_matching': {},
            'keepa_extraction': {},
            'financial_analysis': {},
            'errors_and_warnings': {},
            'file_analysis': {}
        }
        
    def generate_comprehensive_report(self):
        """Generate complete monitoring report"""
        print("🔍 Analyzing system performance...")
        
        # Core analysis functions
        self._analyze_processing_state()
        self._analyze_ai_categories()
        self._analyze_amazon_cache()
        self._analyze_financial_reports()
        self._analyze_api_logs()
        self._analyze_errors_and_patterns()
        self._generate_summary()
        
        # Write comprehensive report
        report_path = self._write_comprehensive_report()
        print(f"📊 Comprehensive report generated: {report_path}")
        return report_path
    
    def _analyze_processing_state(self):
        """Analyze processing state and progress"""
        state_file = os.path.join(self.outputs_path, "clearance-king_co_uk_processing_state.json")
        
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            self.report_data['processing_metrics'] = {
                'last_processed_index': state.get('last_processed_index', 0),
                'total_products_in_cache': self._count_supplier_cache_products(),
                'processing_completion_rate': self._calculate_completion_rate(state),
                'ai_decision_history_count': len(state.get('ai_decision_history', [])),
                'categories_scraped_count': len(state.get('categories_scraped', [])),
                'products_processed_count': len(state.get('products_processed', [])),
                'failed_categories_count': len(state.get('failed_categories', []))
            }
    
    def _analyze_ai_categories(self):
        """Analyze AI category suggestions and performance"""
        ai_cache_file = os.path.join(self.outputs_path, "ai_category_cache", "clearance-king_co_uk_ai_category_cache.json")
        
        ai_data = {}
        if os.path.exists(ai_cache_file):
            with open(ai_cache_file, 'r') as f:
                ai_cache = json.load(f)
            
            # Count categories by type
            categories_analysis = {
                'total_ai_calls': len(ai_cache.get('sessions', [])),
                'total_categories_suggested': 0,
                'top_categories': [],
                'secondary_categories': [],
                'skipped_categories': [],
                'category_performance': {}
            }
            
            for session_id, session_data in ai_cache.items():
                if isinstance(session_data, dict) and 'categories_suggested' in session_data:
                    cats = session_data['categories_suggested']
                    categories_analysis['total_categories_suggested'] += len(cats.get('top_3_urls', []))
                    categories_analysis['total_categories_suggested'] += len(cats.get('secondary_urls', []))
                    categories_analysis['top_categories'].extend(cats.get('top_3_urls', []))
                    categories_analysis['secondary_categories'].extend(cats.get('secondary_urls', []))
                    categories_analysis['skipped_categories'].extend(cats.get('skip_urls', []))
        
        self.report_data['ai_categories'] = categories_analysis
    
    def _analyze_amazon_cache(self):
        """Analyze Amazon product matching and data extraction"""
        amazon_cache_dir = os.path.join(self.outputs_path, "amazon_cache")
        
        cache_files = glob.glob(os.path.join(amazon_cache_dir, "amazon_*.json"))
        
        matching_stats = {
            'total_amazon_cache_files': len(cache_files),
            'ean_based_matches': 0,
            'title_based_matches': 0,
            'successful_extractions': 0,
            'prime_eligible_count': 0,
            'fba_eligible_count': 0,
            'products_with_ratings': 0,
            'products_with_sales_rank': 0,
            'extraction_errors': []
        }
        
        for cache_file in cache_files:
            try:
                with open(cache_file, 'r') as f:
                    product_data = json.load(f)
                
                # Analyze extraction quality
                if 'title' in product_data:
                    matching_stats['successful_extractions'] += 1
                
                if product_data.get('prime_eligible'):
                    matching_stats['prime_eligible_count'] += 1
                
                if product_data.get('fulfilled_by_amazon'):
                    matching_stats['fba_eligible_count'] += 1
                
                if product_data.get('rating'):
                    matching_stats['products_with_ratings'] += 1
                
                if product_data.get('sales_rank'):
                    matching_stats['products_with_sales_rank'] += 1
                
                # Determine match type from filename
                if '_title_' in os.path.basename(cache_file):
                    matching_stats['title_based_matches'] += 1
                else:
                    matching_stats['ean_based_matches'] += 1
                    
            except Exception as e:
                matching_stats['extraction_errors'].append({
                    'file': os.path.basename(cache_file),
                    'error': str(e)
                })
        
        self.report_data['amazon_matching'] = matching_stats
    
    def _analyze_keepa_extraction(self):
        """Analyze Keepa data extraction quality"""
        amazon_cache_dir = os.path.join(self.outputs_path, "amazon_cache")
        cache_files = glob.glob(os.path.join(amazon_cache_dir, "amazon_*.json"))
        
        keepa_stats = {
            'total_files_with_keepa': 0,
            'successful_keepa_extractions': 0,
            'keepa_fee_extractions': 0,
            'keepa_rank_extractions': 0,
            'keepa_disabled_count': 0,
            'keepa_errors': []
        }
        
        for cache_file in cache_files:
            try:
                with open(cache_file, 'r') as f:
                    product_data = json.load(f)
                
                keepa_data = product_data.get('keepa', {})
                if keepa_data:
                    keepa_stats['total_files_with_keepa'] += 1
                    
                    if keepa_data.get('status') == 'Extraction process completed':
                        keepa_stats['successful_keepa_extractions'] += 1
                    
                    if 'product_details_tab_data' in keepa_data:
                        keepa_stats['keepa_fee_extractions'] += 1
                    
                    if 'sales_rank_details_table' in keepa_data:
                        keepa_stats['keepa_rank_extractions'] += 1
                    
                    if 'disabled' in keepa_data.get('status', '').lower():
                        keepa_stats['keepa_disabled_count'] += 1
                        
            except Exception as e:
                keepa_stats['keepa_errors'].append({
                    'file': os.path.basename(cache_file),
                    'error': str(e)
                })
        
        self.report_data['keepa_extraction'] = keepa_stats
    
    def _analyze_financial_reports(self):
        """Analyze financial calculation accuracy and errors"""
        financial_reports = glob.glob(os.path.join(self.outputs_path, "**", "fba_financial_report_*.csv"), recursive=True)
        
        financial_stats = {
            'total_financial_reports': len(financial_reports),
            'latest_report_products': 0,
            'profitable_products': 0,
            'unprofitable_products': 0,
            'roi_distribution': {'high': 0, 'medium': 0, 'low': 0, 'negative': 0},
            'calculation_errors': [],
            'missing_data_errors': []
        }
        
        if financial_reports:
            # Analyze latest report
            latest_report = max(financial_reports, key=os.path.getmtime)
            
            try:
                with open(latest_report, 'r') as f:
                    csv_reader = csv.DictReader(f)
                    rows = list(csv_reader)
                    
                financial_stats['latest_report_products'] = len(rows)
                
                for row in rows:
                    try:
                        roi = float(row.get('ROI', 0))
                        
                        if roi > 0:
                            financial_stats['profitable_products'] += 1
                        else:
                            financial_stats['unprofitable_products'] += 1
                        
                        # ROI distribution
                        if roi >= 50:
                            financial_stats['roi_distribution']['high'] += 1
                        elif roi >= 20:
                            financial_stats['roi_distribution']['medium'] += 1
                        elif roi > 0:
                            financial_stats['roi_distribution']['low'] += 1
                        else:
                            financial_stats['roi_distribution']['negative'] += 1
                            
                    except (ValueError, TypeError) as e:
                        financial_stats['calculation_errors'].append({
                            'row': row.get('ASIN', 'Unknown'),
                            'error': str(e)
                        })
                        
            except Exception as e:
                financial_stats['calculation_errors'].append({
                    'file': os.path.basename(latest_report),
                    'error': str(e)
                })
        
        self.report_data['financial_analysis'] = financial_stats
    
    def _analyze_api_logs(self):
        """Analyze OpenAI API usage and errors"""
        # Use standardized path management
        from utils.path_manager import path_manager
        api_logs_dir = path_manager.get_log_path("api_calls", "", create_dirs=False)
        api_files = glob.glob(os.path.join(api_logs_dir, "openai_api_calls_*.jsonl"))
        
        api_stats = {
            'total_api_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_tokens_used': 0,
            'api_errors': []
        }
        
        for api_file in api_files:
            try:
                with open(api_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            api_call = json.loads(line)
                            api_stats['total_api_calls'] += 1
                            
                            if 'usage' in api_call:
                                api_stats['successful_calls'] += 1
                                api_stats['total_tokens_used'] += api_call['usage'].get('total_tokens', 0)
                            else:
                                api_stats['failed_calls'] += 1
                                
            except Exception as e:
                api_stats['api_errors'].append({
                    'file': os.path.basename(api_file),
                    'error': str(e)
                })
        
        self.report_data['ai_categories']['api_usage'] = api_stats
    
    def _analyze_errors_and_patterns(self):
        """Analyze error patterns and system warnings"""
        # This would analyze log files for error patterns
        # For now, collecting errors from other analysis
        
        all_errors = []
        
        # Collect errors from all sections
        for section, data in self.report_data.items():
            if isinstance(data, dict):
                for key, value in data.items():
                    if 'error' in key.lower() and isinstance(value, list):
                        all_errors.extend(value)
        
        error_analysis = {
            'total_errors': len(all_errors),
            'error_types': Counter([error.get('error', 'Unknown').split(':')[0] for error in all_errors if isinstance(error, dict)]),
            'critical_errors': [error for error in all_errors if 'critical' in str(error).lower()],
            'warning_patterns': []
        }
        
        self.report_data['errors_and_warnings'] = error_analysis
    
    def _generate_summary(self):
        """Generate executive summary"""
        processing = self.report_data.get('processing_metrics', {})
        amazon = self.report_data.get('amazon_matching', {})
        financial = self.report_data.get('financial_analysis', {})
        
        summary = {
            'report_timestamp': datetime.now().isoformat(),
            'system_status': 'RUNNING' if processing.get('last_processed_index', 0) > 0 else 'STOPPED',
            'overall_progress_percent': processing.get('processing_completion_rate', 0),
            'products_processed': processing.get('last_processed_index', 0),
            'amazon_match_rate': round((amazon.get('successful_extractions', 0) / max(amazon.get('total_amazon_cache_files', 1), 1)) * 100, 2),
            'profitability_rate': round((financial.get('profitable_products', 0) / max(financial.get('latest_report_products', 1), 1)) * 100, 2),
            'ai_categories_suggested': self.report_data.get('ai_categories', {}).get('total_categories_suggested', 0),
            'keepa_success_rate': round((self.report_data.get('keepa_extraction', {}).get('successful_keepa_extractions', 0) / max(amazon.get('total_amazon_cache_files', 1), 1)) * 100, 2),
            'total_errors': self.report_data.get('errors_and_warnings', {}).get('total_errors', 0)
        }
        
        self.report_data['summary'] = summary
    
    def _count_supplier_cache_products(self):
        """Count products in supplier cache"""
        cache_files = glob.glob(os.path.join(self.base_path, "OUTPUTS", "cached_products", "*_products_cache.json"))
        total_products = 0
        
        for cache_file in cache_files:
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                    if isinstance(cache_data, list):
                        total_products += len(cache_data)
                    elif isinstance(cache_data, dict) and 'products' in cache_data:
                        total_products += len(cache_data['products'])
            except:
                pass
        
        return total_products
    
    def _calculate_completion_rate(self, state):
        """Calculate processing completion percentage"""
        current_index = state.get('last_processed_index', 0)
        total_products = self._count_supplier_cache_products()
        
        if total_products > 0:
            return round((current_index / total_products) * 100, 2)
        return 0
    
    def _write_comprehensive_report(self):
        """Write comprehensive monitoring report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(self.outputs_path, f"COMPREHENSIVE_SYSTEM_MONITOR_{timestamp}.md")
        
        with open(report_path, 'w') as f:
            f.write("# 📊 COMPREHENSIVE SYSTEM MONITORING REPORT\n\n")
            f.write(f"**Generated**: {self.report_data['summary']['report_timestamp']}\n\n")
            
            # Executive Summary
            f.write("## 🎯 EXECUTIVE SUMMARY\n\n")
            summary = self.report_data['summary']
            f.write(f"- **System Status**: {summary['system_status']}\n")
            f.write(f"- **Overall Progress**: {summary['overall_progress_percent']}%\n")
            f.write(f"- **Products Processed**: {summary['products_processed']}\n")
            f.write(f"- **Amazon Match Rate**: {summary['amazon_match_rate']}%\n")
            f.write(f"- **Profitability Rate**: {summary['profitability_rate']}%\n")
            f.write(f"- **AI Categories Suggested**: {summary['ai_categories_suggested']}\n")
            f.write(f"- **Keepa Success Rate**: {summary['keepa_success_rate']}%\n")
            f.write(f"- **Total Errors**: {summary['total_errors']}\n\n")
            
            # Processing Metrics
            f.write("## ⚙️ PROCESSING METRICS\n\n")
            processing = self.report_data['processing_metrics']
            for key, value in processing.items():
                f.write(f"- **{key.replace('_', ' ').title()}**: {value}\n")
            f.write("\n")
            
            # AI Categories Analysis
            f.write("## 🤖 AI CATEGORIES ANALYSIS\n\n")
            ai_cats = self.report_data['ai_categories']
            for key, value in ai_cats.items():
                if isinstance(value, list) and value:
                    f.write(f"### {key.replace('_', ' ').title()}\n")
                    for item in value[:10]:  # Limit to first 10 items
                        f.write(f"- {item}\n")
                    f.write("\n")
                elif not isinstance(value, list):
                    f.write(f"- **{key.replace('_', ' ').title()}**: {value}\n")
            f.write("\n")
            
            # Amazon Matching Analysis
            f.write("## 🔍 AMAZON MATCHING ANALYSIS\n\n")
            amazon = self.report_data['amazon_matching']
            for key, value in amazon.items():
                if key != 'extraction_errors':
                    f.write(f"- **{key.replace('_', ' ').title()}**: {value}\n")
            f.write("\n")
            
            # Keepa Extraction Analysis
            f.write("## 📈 KEEPA DATA EXTRACTION\n\n")
            keepa = self.report_data['keepa_extraction']
            for key, value in keepa.items():
                if key != 'keepa_errors':
                    f.write(f"- **{key.replace('_', ' ').title()}**: {value}\n")
            f.write("\n")
            
            # Financial Analysis
            f.write("## 💰 FINANCIAL ANALYSIS\n\n")
            financial = self.report_data['financial_analysis']
            for key, value in financial.items():
                if key == 'roi_distribution':
                    f.write(f"### ROI Distribution\n")
                    for roi_type, count in value.items():
                        f.write(f"- **{roi_type.title()}**: {count}\n")
                elif not isinstance(value, list):
                    f.write(f"- **{key.replace('_', ' ').title()}**: {value}\n")
            f.write("\n")
            
            # Errors and Warnings
            f.write("## ⚠️ ERRORS AND WARNINGS\n\n")
            errors = self.report_data['errors_and_warnings']
            f.write(f"- **Total Errors**: {errors.get('total_errors', 0)}\n")
            
            if errors.get('error_types'):
                f.write(f"### Error Types\n")
                for error_type, count in errors['error_types'].most_common():
                    f.write(f"- **{error_type}**: {count} occurrences\n")
            
            # Individual Error Sections
            for section_name, section_data in self.report_data.items():
                if isinstance(section_data, dict):
                    for key, value in section_data.items():
                        if 'error' in key.lower() and isinstance(value, list) and value:
                            f.write(f"### {section_name.title()} - {key.replace('_', ' ').title()}\n")
                            for error in value[:20]:  # Limit to first 20 errors
                                if isinstance(error, dict):
                                    f.write(f"- **{error.get('file', 'Unknown')}**: {error.get('error', 'Unknown error')}\n")
                                else:
                                    f.write(f"- {error}\n")
                            f.write("\n")
        
        return report_path

def main():
    """Main execution function"""
    base_path = "/mnt/c/Users/chris/Cloud-Drive_christianhaddad8@gmail.com/Cloud-Drive/Full/claude code/Amazon-FBA-Agent-System-v3"
    
    monitor = ComprehensiveSystemMonitor(base_path)
    report_path = monitor.generate_comprehensive_report()
    
    print(f"✅ Comprehensive monitoring report generated: {report_path}")

if __name__ == "__main__":
    main()