#!/usr/bin/env python3
"""
Amazon FBA Agent System - Comprehensive File-Based Monitoring System
Detects unusual conditions, errors, and data quality issues by reading ONLY from actual output files.
Implements alert aggregation, progress tracking, and detailed reporting with severity escalation.
Creates structured flag files for human review and AI assistant investigation.
"""

import os
import json
import time
import psutil
import logging
import csv
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, Counter

class FBAMonitoringSystem:
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.flags_dir = self.base_dir / "MONITORING_FLAGS"
        self.flags_dir.mkdir(exist_ok=True)

        # Monitoring configuration
        self.check_interval = 300  # 5 minutes

        # Output directories - READ FROM ACTUAL FILES ONLY
        self.outputs_dir = self.base_dir / "OUTPUTS" / "FBA_ANALYSIS"
        self.amazon_cache_dir = self.outputs_dir / "amazon_cache"
        self.financial_reports_dir = self.outputs_dir / "financial_reports"
        self.ai_cache_dir = self.outputs_dir / "ai_category_cache"
        self.supplier_cache_dir = self.base_dir / "OUTPUTS" / "cached_products"
        self.linking_map_dir = self.outputs_dir / "Linking map"

        # Alert aggregation tracking
        self.alert_instances = defaultdict(list)
        self.severity_thresholds = {
            "WARNING_TO_CRITICAL": 10,
            "CRITICAL_TO_URGENT": 20
        }

        # State tracking from actual files
        self.last_check_time = datetime.now()
        self.known_processes = set()
        self.file_modification_cache = {}

        # Setup logging with UTF-8 encoding
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.base_dir / "monitoring_system.log", encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def create_aggregated_flag(self, flag_type: str, severity: str, instance_data: Dict[str, Any],
                              source_file_path: str = None, extracted_data: Dict[str, Any] = None):
        """Create or update aggregated flag with comprehensive file-based data"""

        # Create instance entry with actual file data
        instance = {
            "detection_timestamp": datetime.now().isoformat(),
            "source_file_path": source_file_path,
            "file_modification_time": self._get_file_modification_time(source_file_path) if source_file_path else None,
            "extracted_data": extracted_data or {},
            "specific_issue": instance_data.get("specific_issue", ""),
            "resolution_suggestions": instance_data.get("resolution_suggestions", []),
            "impact_assessment": instance_data.get("impact_assessment", ""),
            "data_quality_metrics": instance_data.get("data_quality_metrics", {})
        }

        # Add to aggregation tracking
        self.alert_instances[flag_type].append(instance)

        # Calculate aggregation metrics
        instances = self.alert_instances[flag_type]
        total_instances = len(instances)

        # Determine severity escalation
        escalated_severity = self._calculate_severity_escalation(severity, total_instances)

        # Calculate timespan
        timestamps = [inst["detection_timestamp"] for inst in instances]
        timespan = f"{min(timestamps)} to {max(timestamps)}" if len(timestamps) > 1 else timestamps[0]

        # Create aggregated flag file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        flag_file = self.flags_dir / f"{flag_type}_{escalated_severity}_{timestamp}.json"

        # Check for existing flag file to append to
        existing_flag_file = self._find_existing_flag_file(flag_type)
        if existing_flag_file and total_instances <= 100:  # Append to existing if under limit
            flag_file = existing_flag_file

        flag_data = {
            "timestamp": datetime.now().isoformat(),
            "flag_type": flag_type,
            "severity": escalated_severity,
            "severity_escalated": escalated_severity != severity,
            "requires_action": escalated_severity in ["CRITICAL", "WARNING", "URGENT"],
            "alert_summary": {
                "total_instances": total_instances,
                "severity_escalated": escalated_severity != severity,
                "original_severity": severity,
                "timespan": timespan,
                "data_sources_checked": self._get_data_sources_checked(),
                "monitoring_cycles": self._calculate_monitoring_cycles(instances)
            },
            "instances": instances[-50:] if total_instances > 50 else instances,  # Keep last 50 instances
            "progress_tracking": self._get_comprehensive_progress_tracking(),
            "data_quality_summary": self._calculate_data_quality_summary()
        }

        # Atomic file write with backup
        self._atomic_flag_write(flag_file, flag_data)

        self.logger.warning(f"AGGREGATED FLAG: {flag_type} ({escalated_severity}) - {total_instances} instances - {timespan}")

        return flag_file

    def _get_file_modification_time(self, file_path: str) -> Optional[str]:
        """Get file modification time as ISO string"""
        if not file_path or not Path(file_path).exists():
            return None
        try:
            mtime = Path(file_path).stat().st_mtime
            return datetime.fromtimestamp(mtime).isoformat()
        except Exception:
            return None

    def _calculate_severity_escalation(self, original_severity: str, instance_count: int) -> str:
        """Calculate severity escalation based on instance count"""
        if instance_count >= self.severity_thresholds["CRITICAL_TO_URGENT"]:
            return "URGENT"
        elif instance_count >= self.severity_thresholds["WARNING_TO_CRITICAL"] and original_severity == "WARNING":
            return "CRITICAL"
        return original_severity

    def _find_existing_flag_file(self, flag_type: str) -> Optional[Path]:
        """Find existing flag file for the same type"""
        pattern = f"{flag_type}_*_*.json"
        existing_files = list(self.flags_dir.glob(pattern))
        if existing_files:
            # Return most recent file
            return max(existing_files, key=lambda x: x.stat().st_mtime)
        return None

    def _get_data_sources_checked(self) -> List[str]:
        """Get list of data sources that were checked"""
        sources = []
        if self.amazon_cache_dir.exists():
            sources.append("amazon_cache")
        if self.ai_cache_dir.exists():
            sources.append("ai_cache")
        if self.financial_reports_dir.exists():
            sources.append("csv_reports")
        if self.supplier_cache_dir.exists():
            sources.append("supplier_cache")
        if self.linking_map_dir.exists():
            sources.append("linking_map")
        return sources

    def _calculate_monitoring_cycles(self, instances: List[Dict]) -> int:
        """Calculate number of monitoring cycles based on instance timestamps"""
        if not instances:
            return 0

        timestamps = [datetime.fromisoformat(inst["detection_timestamp"]) for inst in instances]
        timestamps.sort()

        cycles = 1
        last_time = timestamps[0]

        for timestamp in timestamps[1:]:
            if (timestamp - last_time).total_seconds() > self.check_interval:
                cycles += 1
            last_time = timestamp

        return cycles

    def _atomic_flag_write(self, flag_file: Path, flag_data: Dict):
        """Atomic file write with backup"""
        # Create backup if file exists
        if flag_file.exists():
            backup_file = flag_file.with_suffix(f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            shutil.copy2(flag_file, backup_file)

        # Write to temporary file first
        temp_file = flag_file.with_suffix('.tmp')
        try:
            with open(temp_file, 'w') as f:
                json.dump(flag_data, f, indent=2)

            # Atomic move
            temp_file.replace(flag_file)

        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise e

    def _get_comprehensive_progress_tracking(self) -> Dict[str, Any]:
        """Get comprehensive progress tracking from actual output files"""
        progress = {
            "products_progress": self._get_products_progress(),
            "financial_analysis_progress": self._get_financial_analysis_progress(),
            "ai_category_progress": self._get_ai_category_progress(),
            "data_quality_metrics": self._get_data_quality_metrics(),
            "system_health": self._get_system_health_metrics()
        }
        return progress

    def _get_products_progress(self) -> Dict[str, Any]:
        """Get products progress from supplier cache, Amazon cache, and processing state"""
        progress = {}

        try:
            # Total products in supplier cache
            supplier_cache_files = list(self.supplier_cache_dir.glob("*_products_cache.json"))
            total_supplier_products = 0

            for cache_file in supplier_cache_files:
                with open(cache_file, 'r') as f:
                    supplier_data = json.load(f)
                    total_supplier_products += len(supplier_data)

            progress["total_supplier_products"] = total_supplier_products

            # Products with Amazon data
            amazon_cache_files = list(self.amazon_cache_dir.glob("amazon_*.json"))
            progress["products_with_amazon_data"] = len(amazon_cache_files)

            # Products with complete Keepa data
            complete_keepa_count = 0
            for amazon_file in amazon_cache_files:
                try:
                    with open(amazon_file, 'r') as f:
                        amazon_data = json.load(f)
                        keepa_data = amazon_data.get('keepa', {}).get('product_details_tab_data', {})
                        if keepa_data and isinstance(keepa_data, dict) and keepa_data:
                            complete_keepa_count += 1
                except Exception:
                    continue

            progress["products_with_complete_keepa"] = complete_keepa_count

            # Current processing index from state files
            state_files = list(self.outputs_dir.glob("*_processing_state.json"))
            current_processing_index = 0

            for state_file in state_files:
                try:
                    with open(state_file, 'r') as f:
                        state_data = json.load(f)
                        current_processing_index = max(current_processing_index,
                                                     state_data.get('last_processed_index', 0))
                except Exception:
                    continue

            progress["current_processing_index"] = current_processing_index

            # Calculate processing rate
            if total_supplier_products > 0:
                progress["processing_completion_rate"] = (current_processing_index / total_supplier_products) * 100
                progress["amazon_cache_coverage"] = (len(amazon_cache_files) / total_supplier_products) * 100
                progress["keepa_success_rate"] = (complete_keepa_count / len(amazon_cache_files)) * 100 if amazon_cache_files else 0

        except Exception as e:
            progress["error"] = f"Error calculating products progress: {str(e)}"

        return progress

    def _get_financial_analysis_progress(self) -> Dict[str, Any]:
        """Get financial analysis progress from CSV files and FBA summaries"""
        progress = {}

        try:
            # CSV reports generated
            csv_files = list(self.financial_reports_dir.glob("fba_financial_report_*.csv"))
            progress["csv_reports_generated"] = len(csv_files)

            if csv_files:
                # Get most recent CSV
                latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
                progress["latest_csv_file"] = str(latest_csv)
                progress["latest_csv_modification_time"] = self._get_file_modification_time(str(latest_csv))

                # Count products in latest CSV
                try:
                    with open(latest_csv, 'r', newline='') as f:
                        reader = csv.reader(f)
                        rows = list(reader)
                        if len(rows) > 1:  # Has header + data
                            progress["products_in_latest_csv"] = len(rows) - 1

                            # Check data completeness
                            header = rows[0]
                            required_columns = ['EAN', 'ASIN', 'supplier_cost', 'amazon_price', 'profit_margin']
                            complete_records = 0

                            for row in rows[1:]:
                                if len(row) >= len(header):
                                    row_dict = dict(zip(header, row))
                                    if all(row_dict.get(col, '').strip() not in ['', 'N/A', '0.00']
                                          for col in required_columns if col in row_dict):
                                        complete_records += 1

                            progress["complete_financial_records"] = complete_records
                            progress["financial_data_completeness_rate"] = (complete_records / (len(rows) - 1)) * 100

                except Exception as e:
                    progress["csv_analysis_error"] = str(e)

            # FBA summary files
            fba_summary_files = list(self.outputs_dir.glob("fba_summary_*.json"))
            progress["fba_summary_files"] = len(fba_summary_files)

            if fba_summary_files:
                latest_summary = max(fba_summary_files, key=lambda x: x.stat().st_mtime)
                try:
                    with open(latest_summary, 'r') as f:
                        summary_data = json.load(f)
                        progress["latest_fba_summary"] = {
                            "file": str(latest_summary),
                            "modification_time": self._get_file_modification_time(str(latest_summary)),
                            "session_data": summary_data
                        }
                except Exception as e:
                    progress["fba_summary_error"] = str(e)

        except Exception as e:
            progress["error"] = f"Error calculating financial progress: {str(e)}"

        return progress

    def _get_ai_category_progress(self) -> Dict[str, Any]:
        """Get AI category progress from AI cache files"""
        progress = {}

        try:
            ai_cache_files = list(self.ai_cache_dir.glob("*_ai_category_cache.json"))
            progress["ai_cache_files"] = len(ai_cache_files)

            total_categories_suggested = 0
            categories_validated_productive = 0
            categories_scraped = 0
            all_suggested_urls = []
            latest_suggestion_timestamp = None

            for cache_file in ai_cache_files:
                try:
                    with open(cache_file, 'r') as f:
                        ai_data = json.load(f)

                        for entry in ai_data:
                            # Count suggested URLs
                            suggested_urls = entry.get('suggested_urls', [])
                            total_categories_suggested += len(suggested_urls)
                            all_suggested_urls.extend(suggested_urls)

                            # Check validation results
                            validation_results = entry.get('validation_results', {})
                            if validation_results.get('productive', False):
                                categories_validated_productive += 1

                            # Check if scraped
                            if entry.get('scraped_products_count', 0) > 0:
                                categories_scraped += 1

                            # Track latest timestamp
                            timestamp = entry.get('timestamp', '')
                            if timestamp and (not latest_suggestion_timestamp or timestamp > latest_suggestion_timestamp):
                                latest_suggestion_timestamp = timestamp

                except Exception as e:
                    progress[f"error_reading_{cache_file.name}"] = str(e)

            progress["total_categories_suggested"] = total_categories_suggested
            progress["categories_validated_productive"] = categories_validated_productive
            progress["categories_scraped"] = categories_scraped
            progress["latest_suggestion_timestamp"] = latest_suggestion_timestamp

            # Check for duplicates
            url_counts = Counter(all_suggested_urls)
            duplicate_urls = [url for url, count in url_counts.items() if count > 1]
            progress["duplicate_ai_suggestions"] = len(duplicate_urls)
            progress["duplicate_urls"] = duplicate_urls[:10]  # First 10 duplicates

            # Calculate efficiency rates
            if total_categories_suggested > 0:
                progress["ai_productivity_rate"] = (categories_validated_productive / total_categories_suggested) * 100
                progress["ai_scraping_success_rate"] = (categories_scraped / total_categories_suggested) * 100

        except Exception as e:
            progress["error"] = f"Error calculating AI progress: {str(e)}"

        return progress

    def _get_data_quality_metrics(self) -> Dict[str, Any]:
        """Calculate data quality metrics from actual files"""
        metrics = {}

        try:
            # Amazon cache data quality
            amazon_files = list(self.amazon_cache_dir.glob("amazon_*.json"))
            if amazon_files:
                keepa_success = 0
                keepa_timeout = 0
                missing_ean = 0
                missing_fees = 0

                for amazon_file in amazon_files[-100:]:  # Check last 100 files
                    try:
                        with open(amazon_file, 'r') as f:
                            data = json.load(f)

                        keepa_status = data.get('keepa', {}).get('status', '')
                        keepa_data = data.get('keepa', {}).get('product_details_tab_data', {})

                        if 'timeout' in keepa_status.lower():
                            keepa_timeout += 1
                        elif keepa_data and isinstance(keepa_data, dict):
                            keepa_success += 1

                            # Check for EAN
                            if not any('ean' in str(v).lower() for v in keepa_data.values()):
                                missing_ean += 1

                            # Check for fees
                            has_fba_fee = any('fba' in str(v).lower() for v in keepa_data.values())
                            has_referral_fee = any('referral' in str(v).lower() for v in keepa_data.values())
                            if not (has_fba_fee and has_referral_fee):
                                missing_fees += 1

                    except Exception:
                        continue

                total_checked = len(amazon_files[-100:])
                metrics["amazon_cache_quality"] = {
                    "files_checked": total_checked,
                    "keepa_success_rate": (keepa_success / total_checked) * 100 if total_checked > 0 else 0,
                    "keepa_timeout_rate": (keepa_timeout / total_checked) * 100 if total_checked > 0 else 0,
                    "missing_ean_rate": (missing_ean / keepa_success) * 100 if keepa_success > 0 else 0,
                    "missing_fees_rate": (missing_fees / keepa_success) * 100 if keepa_success > 0 else 0
                }

            # Linking map efficiency
            linking_map_file = self.linking_map_dir / "linking_map.json"
            if linking_map_file.exists():
                try:
                    with open(linking_map_file, 'r') as f:
                        linking_data = json.load(f)

                    total_links = len(linking_data)
                    successful_links = sum(1 for entry in linking_data.values()
                                         if entry.get('amazon_url') and entry.get('amazon_url') != 'Not found')

                    metrics["linking_map_efficiency"] = {
                        "total_links": total_links,
                        "successful_links": successful_links,
                        "success_rate": (successful_links / total_links) * 100 if total_links > 0 else 0
                    }
                except Exception as e:
                    metrics["linking_map_error"] = str(e)

        except Exception as e:
            metrics["error"] = f"Error calculating data quality: {str(e)}"

        return metrics

    def _get_system_health_metrics(self) -> Dict[str, Any]:
        """Get system health metrics"""
        health = {}

        try:
            # Disk space
            disk_usage = psutil.disk_usage(str(self.base_dir))
            health["disk_space"] = {
                "free_gb": disk_usage.free / (1024**3),
                "used_gb": disk_usage.used / (1024**3),
                "total_gb": disk_usage.total / (1024**3),
                "usage_percentage": (disk_usage.used / disk_usage.total) * 100
            }

            # Process status
            fba_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status', 'memory_info']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'passive_extraction_workflow' in cmdline or 'fba' in cmdline.lower():
                        fba_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'status': proc.info['status'],
                            'memory_mb': proc.info['memory_info'].rss / (1024*1024) if proc.info['memory_info'] else 0
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            health["fba_processes"] = fba_processes
            health["process_count"] = len(fba_processes)

            # File system health
            health["file_system"] = {
                "amazon_cache_files": len(list(self.amazon_cache_dir.glob("*.json"))) if self.amazon_cache_dir.exists() else 0,
                "csv_reports": len(list(self.financial_reports_dir.glob("*.csv"))) if self.financial_reports_dir.exists() else 0,
                "ai_cache_files": len(list(self.ai_cache_dir.glob("*.json"))) if self.ai_cache_dir.exists() else 0,
                "supplier_cache_files": len(list(self.supplier_cache_dir.glob("*.json"))) if self.supplier_cache_dir.exists() else 0
            }

        except Exception as e:
            health["error"] = f"Error getting system health: {str(e)}"

        return health

    def _calculate_data_quality_summary(self) -> Dict[str, Any]:
        """Calculate overall data quality summary"""
        summary = {}

        try:
            progress = self._get_comprehensive_progress_tracking()

            # Overall quality score
            quality_factors = []

            # Keepa success rate
            products_progress = progress.get("products_progress", {})
            keepa_rate = products_progress.get("keepa_success_rate", 0)
            quality_factors.append(keepa_rate)

            # Financial data completeness
            financial_progress = progress.get("financial_analysis_progress", {})
            financial_rate = financial_progress.get("financial_data_completeness_rate", 0)
            quality_factors.append(financial_rate)

            # AI productivity
            ai_progress = progress.get("ai_category_progress", {})
            ai_rate = ai_progress.get("ai_productivity_rate", 0)
            quality_factors.append(ai_rate)

            # Calculate overall score
            if quality_factors:
                summary["overall_quality_score"] = sum(quality_factors) / len(quality_factors)
                summary["quality_grade"] = self._get_quality_grade(summary["overall_quality_score"])

            summary["component_scores"] = {
                "keepa_extraction": keepa_rate,
                "financial_analysis": financial_rate,
                "ai_suggestions": ai_rate
            }

        except Exception as e:
            summary["error"] = f"Error calculating quality summary: {str(e)}"

        return summary

    def _get_quality_grade(self, score: float) -> str:
        """Convert quality score to grade"""
        if score >= 90:
            return "EXCELLENT"
        elif score >= 75:
            return "GOOD"
        elif score >= 60:
            return "FAIR"
        elif score >= 40:
            return "POOR"
        else:
            return "CRITICAL"
        
    def check_system_processes(self):
        """Check if FBA system processes are running"""
        fba_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status', 'memory_info', 'create_time']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'passive_extraction_workflow' in cmdline or 'fba' in cmdline.lower():
                    fba_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': cmdline,
                        'status': proc.info['status'],
                        'memory_mb': proc.info['memory_info'].rss / (1024*1024) if proc.info['memory_info'] else 0,
                        'running_since': datetime.fromtimestamp(proc.info['create_time']).isoformat() if proc.info['create_time'] else None
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        current_pids = {p['pid'] for p in fba_processes}

        # Check for stopped processes
        if self.known_processes and not current_pids:
            self.create_aggregated_flag(
                "SYSTEM_STOPPED",
                "CRITICAL",
                {
                    "specific_issue": "All FBA system processes have stopped unexpectedly",
                    "resolution_suggestions": [
                        "Check system logs for crash reasons",
                        "Verify system resources (memory, disk space)",
                        "Restart FBA processing system",
                        "Check for Python/Chrome process conflicts",
                        "Verify network connectivity"
                    ],
                    "impact_assessment": "No product processing or analysis is occurring",
                    "data_quality_metrics": {
                        "last_known_process_count": len(self.known_processes),
                        "current_process_count": len(current_pids),
                        "process_stop_time": datetime.now().isoformat()
                    }
                },
                source_file_path=None,
                extracted_data={
                    "last_known_processes": list(self.known_processes),
                    "current_processes": fba_processes,
                    "system_uptime_hours": (datetime.now() - self.last_check_time).total_seconds() / 3600
                }
            )

        # Check for new processes
        new_processes = current_pids - self.known_processes
        if new_processes:
            new_process_details = [p for p in fba_processes if p['pid'] in new_processes]

            self.create_aggregated_flag(
                "NEW_PROCESS_STARTED",
                "INFO",
                {
                    "specific_issue": f"New FBA processes detected: {len(new_processes)} processes",
                    "resolution_suggestions": [
                        "Monitor new processes for stability",
                        "Check if multiple instances are intended",
                        "Verify process resource usage",
                        "Ensure no process conflicts"
                    ],
                    "impact_assessment": "New processing capacity available",
                    "data_quality_metrics": {
                        "new_process_count": len(new_processes),
                        "total_process_count": len(current_pids),
                        "total_memory_mb": sum(p['memory_mb'] for p in fba_processes)
                    }
                },
                source_file_path=None,
                extracted_data={
                    "new_processes": new_process_details,
                    "all_current_processes": fba_processes
                }
            )

        self.known_processes = current_pids
        return fba_processes
        
    def check_ai_suggestions(self):
        """Check for redundant or problematic AI suggestions from actual AI cache files"""
        ai_cache_files = list(self.ai_cache_dir.glob("*_ai_category_cache.json"))

        if not ai_cache_files:
            return

        for cache_file in ai_cache_files:
            try:
                with open(cache_file, 'r') as f:
                    ai_data = json.load(f)

                all_suggestions = []
                entry_details = []

                for i, entry in enumerate(ai_data):
                    suggested_urls = entry.get('suggested_urls', [])
                    all_suggestions.extend(suggested_urls)

                    entry_details.append({
                        "entry_index": i,
                        "timestamp": entry.get('timestamp', ''),
                        "suggested_urls": suggested_urls,
                        "scraped_products_count": entry.get('scraped_products_count', 0),
                        "validation_results": entry.get('validation_results', {}),
                        "suggestion_count": len(suggested_urls)
                    })

                # Check for redundant suggestions
                url_counts = Counter(all_suggestions)
                duplicate_urls = [url for url, count in url_counts.items() if count > 1]

                if duplicate_urls:
                    # Find specific entries with duplicates
                    duplicate_entries = []
                    for entry_detail in entry_details:
                        entry_duplicates = [url for url in entry_detail["suggested_urls"] if url in duplicate_urls]
                        if entry_duplicates:
                            duplicate_entries.append({
                                "entry_index": entry_detail["entry_index"],
                                "timestamp": entry_detail["timestamp"],
                                "duplicate_urls": entry_duplicates
                            })

                    self.create_aggregated_flag(
                        "REDUNDANT_AI_SUGGESTIONS",
                        "WARNING",
                        {
                            "specific_issue": f"Found {len(duplicate_urls)} duplicate AI category suggestions",
                            "resolution_suggestions": [
                                "Clear AI category cache to reset suggestions",
                                "Check AI memory system for duplicate prevention",
                                "Verify category validation logic",
                                "Review AI suggestion algorithm"
                            ],
                            "impact_assessment": "Wasted processing time on already-explored categories",
                            "data_quality_metrics": {
                                "total_suggestions": len(all_suggestions),
                                "unique_suggestions": len(set(all_suggestions)),
                                "duplicate_count": len(duplicate_urls),
                                "duplication_rate": (len(duplicate_urls) / len(all_suggestions)) * 100 if all_suggestions else 0
                            }
                        },
                        source_file_path=str(cache_file),
                        extracted_data={
                            "cache_file_name": cache_file.name,
                            "total_entries": len(ai_data),
                            "duplicate_urls": duplicate_urls[:10],  # First 10 duplicates
                            "duplicate_entries": duplicate_entries,
                            "suggestion_timeline": [{"index": e["entry_index"], "timestamp": e["timestamp"], "count": e["suggestion_count"]} for e in entry_details]
                        }
                    )

                # Check for excessive suggestions (possible infinite loop)
                if len(all_suggestions) > 20:
                    recent_entries = entry_details[-5:] if len(entry_details) > 5 else entry_details
                    recent_suggestion_rate = sum(e["suggestion_count"] for e in recent_entries) / len(recent_entries) if recent_entries else 0

                    self.create_aggregated_flag(
                        "EXCESSIVE_AI_SUGGESTIONS",
                        "WARNING",
                        {
                            "specific_issue": f"AI has made {len(all_suggestions)} suggestions - possible infinite loop",
                            "resolution_suggestions": [
                                "Check AI stopping criteria",
                                "Verify category exhaustion logic",
                                "Review AI suggestion limits",
                                "Check for category validation failures"
                            ],
                            "impact_assessment": "System may be stuck in infinite suggestion loop",
                            "data_quality_metrics": {
                                "total_suggestions": len(all_suggestions),
                                "entries_count": len(ai_data),
                                "average_suggestions_per_entry": len(all_suggestions) / len(ai_data) if ai_data else 0,
                                "recent_suggestion_rate": recent_suggestion_rate,
                                "suggestion_growth_trend": self._calculate_suggestion_growth_trend(entry_details)
                            }
                        },
                        source_file_path=str(cache_file),
                        extracted_data={
                            "cache_file_name": cache_file.name,
                            "total_entries": len(ai_data),
                            "total_suggestions": len(all_suggestions),
                            "recent_entries": recent_entries,
                            "suggestion_timeline": [{"index": e["entry_index"], "timestamp": e["timestamp"], "count": e["suggestion_count"]} for e in entry_details[-10:]]
                        }
                    )

                # Check for AI suggestions without productive results
                unproductive_entries = [e for e in entry_details if e["scraped_products_count"] == 0 and e["suggestion_count"] > 0]
                if len(unproductive_entries) > 5:
                    self.create_aggregated_flag(
                        "UNPRODUCTIVE_AI_SUGGESTIONS",
                        "INFO",
                        {
                            "specific_issue": f"Found {len(unproductive_entries)} AI suggestions with no scraped products",
                            "resolution_suggestions": [
                                "Review category validation criteria",
                                "Check URL accessibility",
                                "Verify scraping selectors",
                                "Adjust AI suggestion filters"
                            ],
                            "impact_assessment": "AI suggesting categories that yield no products",
                            "data_quality_metrics": {
                                "unproductive_entries": len(unproductive_entries),
                                "total_entries": len(entry_details),
                                "unproductive_rate": (len(unproductive_entries) / len(entry_details)) * 100 if entry_details else 0
                            }
                        },
                        source_file_path=str(cache_file),
                        extracted_data={
                            "cache_file_name": cache_file.name,
                            "unproductive_entries": unproductive_entries[:5],  # First 5
                            "total_entries": len(ai_data)
                        }
                    )

            except Exception as e:
                self.create_aggregated_flag(
                    "AI_CACHE_ERROR",
                    "WARNING",
                    {
                        "specific_issue": f"Error reading AI cache file: {str(e)}",
                        "resolution_suggestions": [
                            "Check file permissions",
                            "Verify JSON file format",
                            "Check disk space",
                            "Restart AI suggestion system"
                        ],
                        "impact_assessment": "Cannot analyze AI suggestion quality",
                        "data_quality_metrics": {
                            "file_size_bytes": cache_file.stat().st_size if cache_file.exists() else 0,
                            "error_type": type(e).__name__
                        }
                    },
                    source_file_path=str(cache_file),
                    extracted_data={
                        "file_name": cache_file.name,
                        "error_message": str(e),
                        "file_exists": cache_file.exists()
                    }
                )

    def _calculate_suggestion_growth_trend(self, entry_details: List[Dict]) -> str:
        """Calculate if AI suggestions are growing, stable, or declining"""
        if len(entry_details) < 3:
            return "insufficient_data"

        recent_counts = [e["suggestion_count"] for e in entry_details[-3:]]

        if recent_counts[-1] > recent_counts[0]:
            return "increasing"
        elif recent_counts[-1] < recent_counts[0]:
            return "decreasing"
        else:
            return "stable"
                
    def check_keepa_data_quality(self):
        """Check for missing or incomplete Keepa data from actual Amazon cache files"""
        amazon_files = list(self.amazon_cache_dir.glob("amazon_*.json"))

        if not amazon_files:
            return

        # Check recent files for patterns
        recent_files = amazon_files[-50:] if len(amazon_files) > 50 else amazon_files

        for amazon_file in recent_files:
            # Only check Keepa data for matched products (EAN or title-based matches)
            # Skip unmatched products as they don't need Keepa data extraction
            filename = amazon_file.name
            # Pattern analysis:
            # EAN-matched: amazon_B003XLBV3S_5060226063390.json (3 parts)
            # Title-matched: amazon_B0F7FJVMC6_title_9b243ec0.json (4 parts with 'title')
            # Unmatched: amazon_B07JR7TM2N.json (2 parts)
            filename_parts = filename.replace('.json', '').split('_')
            is_matched_product = (len(filename_parts) >= 3)  # EAN or title matches have 3+ parts

            if not is_matched_product:
                continue  # Skip unmatched products - they don't need Keepa data

            try:
                with open(amazon_file, 'r') as f:
                    data = json.load(f)

                keepa_status = data.get('keepa', {}).get('status', '')
                keepa_data = data.get('keepa', {}).get('product_details_tab_data', {})

                # Extract product details for detailed reporting
                asin = data.get('asin', 'Unknown')
                ean = None
                supplier_product_name = data.get('supplier_product_name', 'Unknown')

                # Try to extract EAN from various sources
                if keepa_data:
                    for key, value in keepa_data.items():
                        if 'ean' in str(key).lower() or (isinstance(value, str) and len(value) == 13 and value.isdigit()):
                            ean = value
                            break

                # Check for timeout issues
                if 'timeout' in keepa_status.lower():
                    self.create_aggregated_flag(
                        "KEEPA_TIMEOUT_SPIKE",
                        "WARNING",
                        {
                            "specific_issue": f"Keepa extraction timeout: {keepa_status}",
                            "resolution_suggestions": [
                                "Check Keepa login status",
                                "Verify Chrome browser connection",
                                "Clear browser cache and cookies",
                                "Restart Chrome with debug port"
                            ],
                            "impact_assessment": "Product will have incomplete financial data",
                            "data_quality_metrics": {
                                "timeout_duration": self._extract_timeout_duration(keepa_status),
                                "retry_attempts": data.get('keepa', {}).get('retry_attempts', 0)
                            }
                        },
                        source_file_path=str(amazon_file),
                        extracted_data={
                            "asin": asin,
                            "ean": ean,
                            "keepa_status": keepa_status,
                            "supplier_product_name": supplier_product_name,
                            "has_keepa_data": bool(keepa_data)
                        }
                    )

                # Check for missing Keepa data
                elif not keepa_data or not isinstance(keepa_data, dict):
                    self.create_aggregated_flag(
                        "MISSING_KEEPA_DATA",
                        "WARNING",
                        {
                            "specific_issue": "No Keepa product details data extracted",
                            "resolution_suggestions": [
                                "Verify Keepa subscription is active",
                                "Check product exists on Amazon",
                                "Verify ASIN is correct",
                                "Check Keepa website accessibility"
                            ],
                            "impact_assessment": "Cannot calculate FBA fees and profitability",
                            "data_quality_metrics": {
                                "keepa_data_size": len(str(keepa_data)) if keepa_data else 0,
                                "keepa_data_type": type(keepa_data).__name__
                            }
                        },
                        source_file_path=str(amazon_file),
                        extracted_data={
                            "asin": asin,
                            "ean": ean,
                            "keepa_status": keepa_status,
                            "supplier_product_name": supplier_product_name,
                            "keepa_data_present": bool(keepa_data)
                        }
                    )

                # Check for incomplete fee data
                elif keepa_data:
                    # Check for fee data in KEYS (not values) since fee names are the keys
                    has_fba_fee = any('fba' in str(k).lower() or 'pick' in str(k).lower() for k in keepa_data.keys())
                    has_referral_fee = any('referral' in str(k).lower() for k in keepa_data.keys())

                    if not (has_fba_fee and has_referral_fee):
                        missing_fees = []
                        if not has_fba_fee:
                            missing_fees.append("FBA Pick&Pack Fee")
                        if not has_referral_fee:
                            missing_fees.append("Referral Fee")

                        self.create_aggregated_flag(
                            "INCOMPLETE_KEEPA_DATA",
                            "WARNING",
                            {
                                "specific_issue": f"Missing critical fee data: {', '.join(missing_fees)}",
                                "resolution_suggestions": [
                                    "Verify product is eligible for FBA",
                                    "Check Keepa data extraction selectors",
                                    "Verify product category has fee data",
                                    "Check if product is restricted"
                                ],
                                "impact_assessment": "Cannot calculate accurate profit margins",
                                "data_quality_metrics": {
                                    "has_fba_fee": has_fba_fee,
                                    "has_referral_fee": has_referral_fee,
                                    "total_keepa_fields": len(keepa_data),
                                    "missing_fee_types": missing_fees
                                }
                            },
                            source_file_path=str(amazon_file),
                            extracted_data={
                                "asin": asin,
                                "ean": ean,
                                "keepa_status": keepa_status,
                                "supplier_product_name": supplier_product_name,
                                "keepa_data_fields": list(keepa_data.keys())[:10],  # First 10 fields
                                "missing_fees": missing_fees
                            }
                        )

            except Exception as e:
                self.create_aggregated_flag(
                    "AMAZON_CACHE_READ_ERROR",
                    "WARNING",
                    {
                        "specific_issue": f"Error reading Amazon cache file: {str(e)}",
                        "resolution_suggestions": [
                            "Check file permissions",
                            "Verify JSON file format",
                            "Check disk space",
                            "Restart monitoring system"
                        ],
                        "impact_assessment": "Cannot analyze product data quality",
                        "data_quality_metrics": {
                            "file_size_bytes": amazon_file.stat().st_size if amazon_file.exists() else 0,
                            "error_type": type(e).__name__
                        }
                    },
                    source_file_path=str(amazon_file),
                    extracted_data={
                        "file_name": amazon_file.name,
                        "error_message": str(e),
                        "file_exists": amazon_file.exists()
                    }
                )

    def _extract_timeout_duration(self, status_message: str) -> Optional[int]:
        """Extract timeout duration from status message"""
        import re
        match = re.search(r'(\d+)\s*s', status_message)
        return int(match.group(1)) if match else None

    def check_csv_data_quality(self):
        """Check financial CSV files for missing or invalid data from actual CSV files"""
        csv_files = list(self.financial_reports_dir.glob("fba_financial_report_*.csv"))

        if not csv_files:
            return

        # Check most recent CSV
        latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)

        try:
            with open(latest_csv, 'r', newline='') as f:
                reader = csv.reader(f)
                rows = list(reader)

            if len(rows) < 2:  # Header + at least 1 data row
                self.create_aggregated_flag(
                    "EMPTY_CSV_REPORT",
                    "CRITICAL",
                    {
                        "specific_issue": "Financial CSV report is empty or has no data rows",
                        "resolution_suggestions": [
                            "Check FBA calculator execution",
                            "Verify Amazon cache data availability",
                            "Check processing state and product count",
                            "Restart financial analysis process"
                        ],
                        "impact_assessment": "No financial analysis data available for decision making",
                        "data_quality_metrics": {
                            "line_count": len(rows),
                            "expected_minimum_rows": 2,
                            "file_size_bytes": latest_csv.stat().st_size
                        }
                    },
                    source_file_path=str(latest_csv),
                    extracted_data={
                        "csv_file_name": latest_csv.name,
                        "line_count": len(rows),
                        "file_modification_time": self._get_file_modification_time(str(latest_csv))
                    }
                )
                return

            header = rows[0]
            data_rows = rows[1:]

            # Check for missing critical columns
            required_columns = ['EAN', 'ASIN', 'supplier_cost', 'amazon_price', 'profit_margin', 'fba_fees', 'referral_fees']
            missing_columns = [col for col in required_columns if col not in header]

            if missing_columns:
                self.create_aggregated_flag(
                    "CSV_MISSING_COLUMNS",
                    "CRITICAL",
                    {
                        "specific_issue": f"CSV missing required columns: {', '.join(missing_columns)}",
                        "resolution_suggestions": [
                            "Check FBA calculator column mapping",
                            "Verify Keepa data extraction completeness",
                            "Update CSV generation logic",
                            "Check Amazon cache data structure"
                        ],
                        "impact_assessment": "Cannot perform complete financial analysis",
                        "data_quality_metrics": {
                            "missing_columns_count": len(missing_columns),
                            "total_columns": len(header),
                            "missing_columns_percentage": (len(missing_columns) / len(required_columns)) * 100
                        }
                    },
                    source_file_path=str(latest_csv),
                    extracted_data={
                        "csv_file_name": latest_csv.name,
                        "missing_columns": missing_columns,
                        "available_columns": header,
                        "required_columns": required_columns
                    }
                )

            # Analyze data completeness row by row
            empty_rows_details = []
            incomplete_rows = 0

            for row_idx, row in enumerate(data_rows[:20], 1):  # Check first 20 data rows
                if len(row) < len(header):
                    row.extend([''] * (len(header) - len(row)))  # Pad short rows

                row_dict = dict(zip(header, row))
                empty_count = sum(1 for value in row if not value.strip() or value.strip() in ['', 'N/A', '0.00', 'None'])

                if empty_count > len(row) * 0.5:  # More than 50% empty
                    incomplete_rows += 1
                    empty_fields = [header[i] for i, value in enumerate(row) if not value.strip() or value.strip() in ['', 'N/A', '0.00', 'None']]

                    empty_rows_details.append({
                        "row_number": row_idx,
                        "empty_fields": empty_fields[:5],  # First 5 empty fields
                        "empty_count": empty_count,
                        "total_fields": len(row),
                        "ean": row_dict.get('EAN', 'Unknown'),
                        "asin": row_dict.get('ASIN', 'Unknown')
                    })

            if incomplete_rows > 5:
                self.create_aggregated_flag(
                    "CSV_EXCESSIVE_EMPTY_DATA",
                    "WARNING",
                    {
                        "specific_issue": f"CSV has {incomplete_rows} rows with excessive empty values out of {len(data_rows[:20])} checked",
                        "resolution_suggestions": [
                            "Check Amazon cache data completeness",
                            "Verify Keepa extraction success rate",
                            "Review product linking accuracy",
                            "Check supplier data quality"
                        ],
                        "impact_assessment": "Financial analysis may be inaccurate due to missing data",
                        "data_quality_metrics": {
                            "incomplete_rows": incomplete_rows,
                            "total_rows_checked": len(data_rows[:20]),
                            "incomplete_percentage": (incomplete_rows / len(data_rows[:20])) * 100,
                            "total_data_rows": len(data_rows)
                        }
                    },
                    source_file_path=str(latest_csv),
                    extracted_data={
                        "csv_file_name": latest_csv.name,
                        "incomplete_rows_details": empty_rows_details[:5],  # First 5 problematic rows
                        "total_rows": len(data_rows),
                        "sample_analysis_count": min(20, len(data_rows))
                    }
                )

        except Exception as e:
            self.create_aggregated_flag(
                "CSV_READ_ERROR",
                "WARNING",
                {
                    "specific_issue": f"Error reading CSV file: {str(e)}",
                    "resolution_suggestions": [
                        "Check file permissions",
                        "Verify CSV file format",
                        "Check disk space",
                        "Restart CSV generation process"
                    ],
                    "impact_assessment": "Cannot analyze financial data quality",
                    "data_quality_metrics": {
                        "file_size_bytes": latest_csv.stat().st_size if latest_csv.exists() else 0,
                        "error_type": type(e).__name__
                    }
                },
                source_file_path=str(latest_csv),
                extracted_data={
                    "csv_file_name": latest_csv.name,
                    "error_message": str(e),
                    "file_exists": latest_csv.exists()
                }
            )

    def check_processing_progress(self):
        """Check if processing is making progress or stuck from actual state files"""
        state_files = list(self.outputs_dir.glob("*_processing_state.json"))

        if not state_files:
            return

        for state_file in state_files:
            try:
                with open(state_file, 'r') as f:
                    state_data = json.load(f)

                current_index = state_data.get('last_processed_index', 0)
                file_mod_time = datetime.fromtimestamp(state_file.stat().st_mtime)

                # Get supplier cache info for context
                supplier_name = state_file.stem.replace('_processing_state', '')
                supplier_cache_file = self.supplier_cache_dir / f"{supplier_name}_products_cache.json"
                total_products = 0

                if supplier_cache_file.exists():
                    try:
                        with open(supplier_cache_file, 'r') as f:
                            supplier_data = json.load(f)
                            total_products = len(supplier_data)
                    except Exception:
                        pass

                # Check if stuck on same product for too long
                cache_key = f"last_index_{supplier_name}"
                last_known_index = self.file_modification_cache.get(cache_key, {})

                if (last_known_index.get('index') == current_index and
                    last_known_index.get('timestamp')):

                    last_time = datetime.fromisoformat(last_known_index['timestamp'])
                    time_diff = datetime.now() - last_time

                    if time_diff.total_seconds() > 1800:  # 30 minutes
                        progress_percentage = (current_index / total_products) * 100 if total_products > 0 else 0

                        self.create_aggregated_flag(
                            "PROCESSING_STUCK",
                            "CRITICAL",
                            {
                                "specific_issue": f"Processing stuck on index {current_index} for {time_diff}",
                                "resolution_suggestions": [
                                    "Check if FBA process is still running",
                                    "Verify Chrome browser connection",
                                    "Check for system resource issues",
                                    "Restart processing from current index",
                                    "Check for network connectivity issues"
                                ],
                                "impact_assessment": "No progress being made on product analysis",
                                "data_quality_metrics": {
                                    "stuck_duration_minutes": time_diff.total_seconds() / 60,
                                    "stuck_index": current_index,
                                    "total_products": total_products,
                                    "progress_percentage": progress_percentage,
                                    "estimated_remaining_hours": ((total_products - current_index) * 3) / 60 if total_products > current_index else 0
                                }
                            },
                            source_file_path=str(state_file),
                            extracted_data={
                                "supplier_name": supplier_name,
                                "stuck_index": current_index,
                                "total_products": total_products,
                                "file_modification_time": self._get_file_modification_time(str(state_file)),
                                "stuck_since": last_known_index['timestamp'],
                                "progress_percentage": progress_percentage
                            }
                        )
                else:
                    # Update cache with current state
                    self.file_modification_cache[cache_key] = {
                        'index': current_index,
                        'timestamp': datetime.now().isoformat()
                    }

            except Exception as e:
                self.create_aggregated_flag(
                    "STATE_FILE_ERROR",
                    "WARNING",
                    {
                        "specific_issue": f"Error reading processing state file: {str(e)}",
                        "resolution_suggestions": [
                            "Check file permissions",
                            "Verify JSON file format",
                            "Check disk space",
                            "Restart processing system"
                        ],
                        "impact_assessment": "Cannot monitor processing progress",
                        "data_quality_metrics": {
                            "file_size_bytes": state_file.stat().st_size if state_file.exists() else 0,
                            "error_type": type(e).__name__
                        }
                    },
                    source_file_path=str(state_file),
                    extracted_data={
                        "state_file_name": state_file.name,
                        "error_message": str(e),
                        "file_exists": state_file.exists()
                    }
                )

    def check_disk_space(self):
        """Check available disk space"""
        disk_usage = psutil.disk_usage(str(self.base_dir))
        free_gb = disk_usage.free / (1024**3)
        used_gb = disk_usage.used / (1024**3)
        total_gb = disk_usage.total / (1024**3)
        usage_percentage = (disk_usage.used / disk_usage.total) * 100

        if free_gb < 1:  # Less than 1GB free
            self.create_aggregated_flag(
                "LOW_DISK_SPACE",
                "CRITICAL",
                {
                    "specific_issue": f"Critical disk space shortage: {free_gb:.2f}GB remaining",
                    "resolution_suggestions": [
                        "Clear Amazon cache files older than 7 days",
                        "Remove old CSV reports and FBA summaries",
                        "Clear browser cache and temporary files",
                        "Move large files to external storage",
                        "Add additional disk space"
                    ],
                    "impact_assessment": "System may crash or fail to save data",
                    "data_quality_metrics": {
                        "free_space_gb": free_gb,
                        "used_space_gb": used_gb,
                        "total_space_gb": total_gb,
                        "usage_percentage": usage_percentage,
                        "critical_threshold_gb": 1.0
                    }
                },
                source_file_path=None,
                extracted_data={
                    "disk_path": str(self.base_dir),
                    "free_space_gb": free_gb,
                    "usage_percentage": usage_percentage,
                    "recommendation": "Immediate action required - clear cache files"
                }
            )
        elif free_gb < 5:  # Less than 5GB free
            self.create_aggregated_flag(
                "DISK_SPACE_WARNING",
                "WARNING",
                {
                    "specific_issue": f"Low disk space warning: {free_gb:.2f}GB remaining",
                    "resolution_suggestions": [
                        "Monitor disk usage closely",
                        "Plan cache cleanup schedule",
                        "Consider archiving old reports",
                        "Prepare additional storage"
                    ],
                    "impact_assessment": "May run out of space during long processing runs",
                    "data_quality_metrics": {
                        "free_space_gb": free_gb,
                        "used_space_gb": used_gb,
                        "total_space_gb": total_gb,
                        "usage_percentage": usage_percentage,
                        "warning_threshold_gb": 5.0
                    }
                },
                source_file_path=None,
                extracted_data={
                    "disk_path": str(self.base_dir),
                    "free_space_gb": free_gb,
                    "usage_percentage": usage_percentage,
                    "recommendation": "Monitor and plan cleanup"
                }
            )



    def run_monitoring_cycle(self):
        """Run one complete file-based monitoring cycle"""
        self.logger.info("Starting comprehensive file-based monitoring cycle...")

        try:
            # File-based monitoring checks - READ FROM ACTUAL FILES ONLY
            self.check_system_processes()
            self.check_ai_suggestions()
            self.check_keepa_data_quality()
            self.check_csv_data_quality()
            self.check_processing_progress()
            self.check_disk_space()

            # Generate comprehensive progress report
            progress_report = self._get_comprehensive_progress_tracking()
            self.logger.info(f"Progress Summary - Products: {progress_report.get('products_progress', {}).get('processing_completion_rate', 0):.1f}% complete")

            self.last_check_time = datetime.now()
            self.logger.info("File-based monitoring cycle completed successfully")

        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {e}")
            self.create_aggregated_flag(
                "MONITORING_ERROR",
                "WARNING",
                {
                    "specific_issue": f"Error in monitoring system: {str(e)}",
                    "resolution_suggestions": [
                        "Check monitoring system permissions",
                        "Verify file system accessibility",
                        "Restart monitoring system",
                        "Check system resources"
                    ],
                    "impact_assessment": "Monitoring system may miss critical issues",
                    "data_quality_metrics": {
                        "error_type": type(e).__name__,
                        "monitoring_uptime_hours": (datetime.now() - self.last_check_time).total_seconds() / 3600
                    }
                },
                source_file_path=None,
                extracted_data={
                    "error_message": str(e),
                    "monitoring_cycle_timestamp": datetime.now().isoformat()
                }
            )

    def run_continuous_monitoring(self):
        """Run continuous monitoring loop"""
        self.logger.info("Starting continuous FBA monitoring system...")

        while True:
            try:
                self.run_monitoring_cycle()
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                self.logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

    def get_active_flags(self) -> List[Dict]:
        """Get all active monitoring flags"""
        flags = []
        for flag_file in self.flags_dir.glob("*.json"):
            try:
                with open(flag_file, 'r') as f:
                    flag_data = json.load(f)
                    flag_data['file_path'] = str(flag_file)
                    flags.append(flag_data)
            except Exception as e:
                self.logger.error(f"Error reading flag file {flag_file}: {e}")

        # Sort by timestamp, newest first
        flags.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return flags

    def clear_flags(self, flag_types: List[str] = None):
        """Clear monitoring flags"""
        cleared_count = 0
        for flag_file in self.flags_dir.glob("*.json"):
            if flag_types:
                # Only clear specific flag types
                flag_type = flag_file.stem.split('_')[0]
                if flag_type not in flag_types:
                    continue

            flag_file.unlink()
            cleared_count += 1

        self.logger.info(f"Cleared {cleared_count} monitoring flags")
        return cleared_count

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FBA Monitoring System")
    parser.add_argument("--base-dir", default=".", help="Base directory for FBA system")
    parser.add_argument("--check-once", action="store_true", help="Run single check instead of continuous")
    parser.add_argument("--clear-flags", nargs="*", help="Clear flags (optionally specify types)")
    parser.add_argument("--show-flags", action="store_true", help="Show active flags")

    args = parser.parse_args()

    monitor = FBAMonitoringSystem(args.base_dir)

    if args.clear_flags is not None:
        monitor.clear_flags(args.clear_flags if args.clear_flags else None)
    elif args.show_flags:
        flags = monitor.get_active_flags()
        print(f"\n=== ACTIVE MONITORING FLAGS ({len(flags)}) ===")
        for flag in flags:
            flag_type = flag.get('flag_type', 'UNKNOWN')
            severity = flag.get('severity', 'INFO')
            timestamp = flag.get('timestamp', '')

            # Show aggregated summary
            alert_summary = flag.get('alert_summary', {})
            total_instances = alert_summary.get('total_instances', 1)
            timespan = alert_summary.get('timespan', timestamp)
            escalated = alert_summary.get('severity_escalated', False)

            print(f"\n{flag_type} ({severity}) - {total_instances} instances")
            if escalated:
                print(f"  ⚠️  SEVERITY ESCALATED from {alert_summary.get('original_severity', 'UNKNOWN')}")
            print(f"  📅 Timespan: {timespan}")

            # Show latest instance details
            instances = flag.get('instances', [])
            if instances:
                latest = instances[-1]
                print(f"  🔍 Latest Issue: {latest.get('specific_issue', 'No details')}")
                if latest.get('source_file_path'):
                    print(f"  📁 Source: {Path(latest['source_file_path']).name}")

            # Show progress tracking summary
            progress = flag.get('progress_tracking', {})
            if progress:
                products_progress = progress.get('products_progress', {})
                if products_progress.get('processing_completion_rate'):
                    print(f"  📊 Processing: {products_progress['processing_completion_rate']:.1f}% complete")

            # Show data quality summary
            quality_summary = flag.get('data_quality_summary', {})
            if quality_summary.get('overall_quality_score'):
                score = quality_summary['overall_quality_score']
                grade = quality_summary.get('quality_grade', 'UNKNOWN')
                print(f"  🎯 Data Quality: {score:.1f}% ({grade})")
    elif args.check_once:
        monitor.run_monitoring_cycle()
    else:
        monitor.run_continuous_monitoring()
