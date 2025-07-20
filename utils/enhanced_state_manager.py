"""
Enhanced State Manager - Comprehensive state management for Amazon FBA Agent System v3.5

This module provides superior state management capabilities based on analysis of the deprecated 
script's more comprehensive approach, following claude.md standards.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import hashlib
import logging
try:
    from .path_manager import get_processing_state_path, path_manager
except ImportError:
    try:
        from utils.path_manager import get_processing_state_path, path_manager
    except ImportError:
        # For standalone testing
        import sys
        sys.path.append('.')
        from utils.path_manager import get_processing_state_path, path_manager

log = logging.getLogger(__name__)


class EnhancedStateManager:
    """Enhanced state management with comprehensive tracking and recovery capabilities"""
    
    SCHEMA_VERSION = "1.0"
    
    def __init__(self, supplier_name: str):
        self.supplier_name = supplier_name
        self.state_file_path = get_processing_state_path(supplier_name)
        self.state_data = self._initialize_state()
        
    def _initialize_state(self) -> Dict[str, Any]:
        """Initialize state structure with all required fields"""
        return {
            "schema_version": self.SCHEMA_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "supplier_name": self.supplier_name,
            "last_processed_index": 0,
            "total_products": 0,
            "processing_status": "initialized",  # initialized, in_progress, completed, error, paused
            "category_performance": {},
            "error_log": [],
            "successful_products": 0,
            "profitable_products": 0,
            "total_profit_found": 0.0,
            "processing_statistics": {
                "start_time": None,
                "end_time": None,
                "total_runtime_seconds": 0,
                "average_time_per_product": 0,
                "products_per_hour": 0
            },
            "metadata": {
                "version": "3.5",
                "config_hash": "",
                "runtime_settings": {},
                "system_info": {}
            },
            "processed_products": {},  # URL -> status mapping for product-level tracking
            "supplier_extraction_progress": {
                "current_category_index": 0,
                "total_categories": 0,
                "current_subcategory_index": 0,
                "total_subcategories_in_batch": 0,
                "current_product_index_in_category": 0,
                "total_products_in_current_category": 0,
                "current_category_url": "",
                "current_batch_number": 0,
                "total_batches": 0,
                "extraction_phase": "not_started",  # not_started, categories, products, completed
                "last_completed_category": "",
                "categories_completed": [],
                "products_extracted_total": 0
            }
        }
    
    def load_state(self) -> bool:
        """
        Load existing state from file, with backward compatibility
        Returns True if state was loaded, False if starting fresh
        """
        if not self.state_file_path.exists():
            log.info(f"No existing state file found for {self.supplier_name}, starting fresh")
            return False
        
        try:
            with open(self.state_file_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            # Handle backward compatibility with simple state format
            if isinstance(loaded_data, dict) and "schema_version" not in loaded_data:
                log.info("Converting legacy state format to enhanced format")
                self._migrate_legacy_state(loaded_data)
            else:
                # Merge loaded data with initialized structure to handle missing fields
                self._merge_state_data(loaded_data)
            
            log.info(f"Loaded state for {self.supplier_name} - resuming from index {self.state_data['last_processed_index']}")
            return True
            
        except Exception as e:
            log.warning(f"Failed to load state file: {e}, starting fresh")
            return False
    
    def _migrate_legacy_state(self, legacy_data: Dict[str, Any]):
        """Migrate legacy state format to enhanced format"""
        self.state_data["last_processed_index"] = legacy_data.get("last_processed_index", 0)
        self.state_data["processing_status"] = "migrated_from_legacy"
        log.info("Successfully migrated legacy state format")
    
    def _merge_state_data(self, loaded_data: Dict[str, Any]):
        """Merge loaded data with initialized structure"""
        def deep_merge(base: Dict, overlay: Dict) -> Dict:
            result = base.copy()
            for key, value in overlay.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        self.state_data = deep_merge(self.state_data, loaded_data)
        self.state_data["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    def save_state(self, force: bool = False):
        """
        Save state to file with atomic write operation
        Args:
            force: Force save even if no changes detected
        """
        try:
            # Update timestamp
            self.state_data["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            # Ensure directory exists
            self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Atomic write using temporary file
            temp_path = self.state_file_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.state_data, f, indent=2, ensure_ascii=False)
            
            # Atomic replace
            os.replace(temp_path, self.state_file_path)
            
        except Exception as e:
            log.error(f"Failed to save state: {e}")
            # Cleanup temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
    
    def update_processing_index(self, index: int, total_products: int = None):
        """Update the current processing index"""
        self.state_data["last_processed_index"] = index
        if total_products is not None:
            self.state_data["total_products"] = total_products
        self.state_data["processing_status"] = "in_progress"
        self.save_state()
    
    def add_category_performance(self, category_url: str, products_found: int, 
                               profitable_products: int = 0, avg_roi: float = 0.0):
        """Add or update category performance metrics"""
        self.state_data["category_performance"][category_url] = {
            "products_found": products_found,
            "profitable_products": profitable_products,
            "avg_roi_percent": avg_roi,
            "last_processed": datetime.now(timezone.utc).isoformat()
        }
        self.save_state()
    
    def log_error(self, error_type: str, error_message: str, product_index: int = None, 
                  context: Dict[str, Any] = None):
        """Log an error with context"""
        error_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "product_index": product_index,
            "context": context or {}
        }
        self.state_data["error_log"].append(error_entry)
        
        # Keep only last 100 errors to prevent file bloat
        if len(self.state_data["error_log"]) > 100:
            self.state_data["error_log"] = self.state_data["error_log"][-100:]
        
        self.save_state()
    
    def update_success_metrics(self, successful: bool, profitable: bool = False, 
                             profit_amount: float = 0.0):
        """Update success and profitability metrics"""
        if successful:
            self.state_data["successful_products"] += 1
        if profitable:
            self.state_data["profitable_products"] += 1
            self.state_data["total_profit_found"] += profit_amount
        self.save_state()
    
    def start_processing(self, config_hash: str = "", runtime_settings: Dict[str, Any] = None):
        """Mark processing as started with metadata"""
        self.state_data["processing_status"] = "in_progress"
        self.state_data["processing_statistics"]["start_time"] = datetime.now(timezone.utc).isoformat()
        self.state_data["metadata"]["config_hash"] = config_hash
        self.state_data["metadata"]["runtime_settings"] = runtime_settings or {}
        self.save_state()
    
    def complete_processing(self):
        """Mark processing as completed and calculate final statistics"""
        self.state_data["processing_status"] = "completed"
        end_time = datetime.now(timezone.utc)
        self.state_data["processing_statistics"]["end_time"] = end_time.isoformat()
        
        # Calculate runtime statistics
        if self.state_data["processing_statistics"]["start_time"]:
            start_time = datetime.fromisoformat(self.state_data["processing_statistics"]["start_time"].replace('Z', '+00:00'))
            runtime_seconds = (end_time - start_time).total_seconds()
            self.state_data["processing_statistics"]["total_runtime_seconds"] = runtime_seconds
            
            if self.state_data["successful_products"] > 0:
                self.state_data["processing_statistics"]["average_time_per_product"] = runtime_seconds / self.state_data["successful_products"]
                self.state_data["processing_statistics"]["products_per_hour"] = (self.state_data["successful_products"] * 3600) / runtime_seconds
        
        self.save_state()
    
    def mark_error_state(self, error_message: str):
        """Mark processing as failed due to error"""
        self.state_data["processing_status"] = "error"
        self.log_error("system_error", error_message)
    
    def get_category_performance_summary(self) -> str:
        """Generate category performance summary for AI re-ordering (like deprecated script)"""
        if not self.state_data["category_performance"]:
            return "CATEGORY PERFORMANCE: No previous performance data available."
        
        summary_lines = ["CATEGORY PERFORMANCE SUMMARY:"]
        sorted_categories = sorted(
            self.state_data["category_performance"].items(),
            key=lambda x: x[1].get('products_found', 0),
            reverse=True
        )[:5]
        
        for url, metrics in sorted_categories:
            products_found = metrics.get('products_found', 0)
            profitable_count = metrics.get('profitable_products', 0)
            avg_roi = metrics.get('avg_roi_percent', 0)
            summary_lines.append(
                f"- {url.split('/')[-1]}: {products_found} products, "
                f"{profitable_count} profitable, {avg_roi:.1f}% avg ROI"
            )
        
        return "\n".join(summary_lines)
    
    def should_resume(self) -> bool:
        """Check if processing should be resumed"""
        return (self.state_data["processing_status"] in ["in_progress", "paused"] and 
                self.state_data["last_processed_index"] > 0)
    
    def update_supplier_extraction_progress(self, category_index: int, total_categories: int,
                                          subcategory_index: int, total_subcategories: int,
                                          batch_number: int, total_batches: int,
                                          category_url: str, extraction_phase: str = "categories"):
        """Update detailed supplier extraction progress"""
        progress = self.state_data["supplier_extraction_progress"]
        progress.update({
            "current_category_index": category_index,
            "total_categories": total_categories,
            "current_subcategory_index": subcategory_index,
            "total_subcategories_in_batch": total_subcategories,
            "current_batch_number": batch_number,
            "total_batches": total_batches,
            "current_category_url": category_url,
            "extraction_phase": extraction_phase,
            "last_updated": datetime.now(timezone.utc).isoformat()
        })
        self.save_state()
    
    def update_product_extraction_progress(self, product_index: int, total_products_in_category: int,
                                         product_url: str = "", products_extracted_total: int = None):
        """Update product-level extraction progress within current category"""
        progress = self.state_data["supplier_extraction_progress"]
        progress.update({
            "current_product_index_in_category": product_index,
            "total_products_in_current_category": total_products_in_category,
            "extraction_phase": "products",
            "last_updated": datetime.now(timezone.utc).isoformat()
        })
        
        if products_extracted_total is not None:
            progress["products_extracted_total"] = products_extracted_total
            
        self.save_state()
    
    def hard_reset(self):
        """🚨 CRITICAL FIX: Hard reset state manager - wipe all state and restart fresh"""
        log.info("🔄 HARD RESET: Wiping all state data and starting fresh")
        
        # Delete existing state file
        if os.path.exists(self.state_file_path):
            try:
                os.remove(self.state_file_path)
                log.info(f"✅ Deleted existing state file: {self.state_file_path}")
            except Exception as e:
                log.warning(f"⚠️ Could not delete state file: {e}")
        
        # Reinitialize state data to fresh state
        self.state_data = self._initialize_state()
        
        # Save fresh state
        self.save_state()
        log.info("✅ Hard reset completed - fresh state initialized")
    
    def complete_category_extraction(self, category_url: str, products_found: int):
        """Mark a category as completed during extraction"""
        progress = self.state_data["supplier_extraction_progress"]
        progress["last_completed_category"] = category_url
        progress["categories_completed"].append({
            "url": category_url,
            "products_found": products_found,
            "completed_at": datetime.now(timezone.utc).isoformat()
        })
        
        # Also update category performance for historical tracking
        self.add_category_performance(category_url, products_found)
        self.save_state()
    
    def get_extraction_resume_point(self) -> Dict[str, Any]:
        """Get detailed resume point for supplier extraction"""
        progress = self.state_data["supplier_extraction_progress"]
        return {
            "should_resume_extraction": progress.get("extraction_phase") in ["categories", "products"],
            "last_category_index": progress.get("current_category_index", 0),
            "last_subcategory_index": progress.get("current_subcategory_index", 0),
            "last_batch_number": progress.get("current_batch_number", 0),
            "completed_categories": progress.get("categories_completed", []),
            "extraction_phase": progress.get("extraction_phase", "not_started")
        }
    
    def get_resume_index(self) -> int:
        """Get the index to resume from"""
        return self.state_data["last_processed_index"]
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of current state for logging"""
        return {
            "supplier": self.supplier_name,
            "status": self.state_data["processing_status"],
            "progress": f"{self.state_data['last_processed_index']}/{self.state_data['total_products']}",
            "successful": self.state_data["successful_products"],
            "profitable": self.state_data["profitable_products"],
            "total_profit": self.state_data["total_profit_found"],
            "categories_processed": len(self.state_data["category_performance"]),
            "errors": len(self.state_data["error_log"])
        }
    
    def is_product_processed(self, url: str) -> bool:
        """Check if a product URL has been previously processed"""
        if not url:
            return False
        return url in self.state_data.get("processed_products", {})
    
    def is_all_products_failed(self) -> bool:
        """Check if all processed products have failed status"""
        processed_products = self.state_data.get("processed_products", {})
        if not processed_products:
            return False
        
        # Check if all products have failed status
        failed_statuses = ["failed_financial_calculation", "failed_amazon_extraction", "failed_supplier_extraction"]
        
        # CRITICAL FIX: Consider success statuses - these are NOT failures!
        success_statuses = ["completed_profitable", "completed_not_profitable", "completed"]
        
        all_failed = all(
            product_data.get("status", "") in failed_statuses 
            for product_data in processed_products.values()
        )
        
        # ADDITIONAL CHECK: If any products have success status, then NOT all failed
        any_successful = any(
            product_data.get("status", "") in success_statuses
            for product_data in processed_products.values()
        )
        
        return all_failed and len(processed_products) > 0 and not any_successful
    
    def auto_reset_failed_state(self) -> bool:
        """Automatically reset state if all products failed and no successful processing occurred"""
        if self.is_all_products_failed() and self.state_data.get("successful_products", 0) == 0:
            log.warning(f"🔄 AUTO-RESET: All {len(self.state_data.get('processed_products', {}))} products failed processing - resetting state for fresh run")
            # Reset critical state fields
            self.state_data["processing_status"] = "initialized"
            self.state_data["last_processed_index"] = 0
            self.state_data["processed_products"] = {}
            self.state_data["error_log"] = []
            self.state_data["processing_statistics"]["start_time"] = None
            self.state_data["processing_statistics"]["end_time"] = None
            self.save_state()
            return True
        return False
    
    def mark_product_processed(self, url: str, status: str) -> None:
        """Mark a product URL as processed with the given status"""
        if not url:
            return
        if "processed_products" not in self.state_data:
            self.state_data["processed_products"] = {}
        
        self.state_data["processed_products"][url] = {
            "status": status,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        # Auto-save after marking product as processed
        self.save_state()


def migrate_legacy_state_files():
    """Migrate any legacy state files to new format"""
    log.info("Checking for legacy state files to migrate...")
    
    # Find legacy state files in old locations
    legacy_patterns = [
        "OUTPUTS/*_processing_state.json",
        "tools/OUTPUTS/*_processing_state.json", 
        "*_processing_state.json"
    ]
    
    migrated_count = 0
    for pattern in legacy_patterns:
        for legacy_file in Path(".").glob(pattern):
            try:
                # Extract supplier name from filename
                supplier_name = legacy_file.stem.replace("_processing_state", "")
                
                # Create enhanced state manager
                state_manager = EnhancedStateManager(supplier_name)
                
                # Load and migrate legacy data
                with open(legacy_file, 'r') as f:
                    legacy_data = json.load(f)
                
                state_manager._migrate_legacy_state(legacy_data)
                state_manager.save_state()
                
                # Archive the old file
                archive_dir = Path("archive/migrated_states")
                archive_dir.mkdir(parents=True, exist_ok=True)
                archive_file = archive_dir / legacy_file.name
                legacy_file.rename(archive_file)
                
                log.info(f"Migrated {legacy_file} → {state_manager.state_file_path}")
                migrated_count += 1
                
            except Exception as e:
                log.error(f"Failed to migrate {legacy_file}: {e}")
    
    log.info(f"Migration complete: {migrated_count} files migrated")


if __name__ == "__main__":
    # Test the enhanced state manager
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Test basic functionality
    state_manager = EnhancedStateManager("test-supplier")
    state_manager.start_processing("test_hash", {"test_mode": True})
    state_manager.update_processing_index(10, 100)
    state_manager.add_category_performance("/test-category", 25, 5, 45.2)
    state_manager.log_error("test_error", "This is a test error", 5)
    state_manager.update_success_metrics(True, True, 15.50)
    
    print("State Summary:", state_manager.get_state_summary())
    print("Category Performance:", state_manager.get_category_performance_summary())
    
    state_manager.complete_processing()
    print("✅ Enhanced state manager test completed")