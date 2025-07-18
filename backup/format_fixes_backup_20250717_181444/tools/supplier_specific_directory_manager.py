#!/usr/bin/env python3
"""
Supplier-Specific Directory Manager
===================================

This module provides centralized directory management for supplier-specific output organization.
Ensures consistent directory structure across all components of the Amazon FBA Agent System.

DIRECTORY STRUCTURE:
    OUTPUTS/
    ├── FBA_ANALYSIS/
    │   ├── financial_reports/
    │   │   └── {supplier_id}/
    │   ├── fba_summary/
    │   │   └── {supplier_id}/
    │   ├── ai_category_cache/
    │   │   └── {supplier_id}_ai_category_cache.json
    │   ├── amazon_cache/           # Shared across suppliers
    │   └── workflow_results/
    │       └── {supplier_id}/
    ├── cached_products/
    │   └── {supplier_id}/
    ├── CACHE/
    │   └── processing_states/
    │       └── {supplier_id}/
    └── DASHBOARD/
        └── {supplier_id}/
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class SupplierDirectoryManager:
    """Centralized manager for supplier-specific directory organization"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.outputs_dir = self.base_dir / "OUTPUTS"
        self.config_dir = self.base_dir / "config"
        
        # Create base directories
        self._ensure_base_directories()
    
    def _ensure_base_directories(self):
        """Create all base directories"""
        base_dirs = [
            self.outputs_dir / "FBA_ANALYSIS" / "financial_reports",
            self.outputs_dir / "FBA_ANALYSIS" / "fba_summary", 
            self.outputs_dir / "FBA_ANALYSIS" / "ai_category_cache",
            self.outputs_dir / "FBA_ANALYSIS" / "amazon_cache",
            self.outputs_dir / "FBA_ANALYSIS" / "workflow_results",
            self.outputs_dir / "cached_products",
            self.outputs_dir / "CACHE" / "processing_states",
            self.outputs_dir / "DASHBOARD"
        ]
        
        for dir_path in base_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_supplier_id_from_url(self, supplier_url: str) -> str:
        """Extract supplier ID from URL using consistent naming convention"""
        try:
            # Parse domain from URL
            domain = urlparse(supplier_url).netloc
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            # Convert to supplier_id format (replace dots with hyphens)
            supplier_id = domain.replace('.', '-')
            return supplier_id
        except Exception as e:
            log.error(f"Failed to extract supplier ID from URL {supplier_url}: {e}")
            return "unknown-supplier"
    
    def get_supplier_id_from_config(self, supplier_url: str) -> Optional[str]:
        """Get supplier ID from configuration files"""
        try:
            supplier_configs_dir = self.config_dir / "supplier_configs"
            
            # Look for config file matching the URL
            for config_file in supplier_configs_dir.glob("*.json"):
                try:
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                        if config.get("base_url") == supplier_url or config.get("supplier_name") == supplier_url:
                            return config.get("supplier_id")
                except (json.JSONDecodeError, KeyError) as e:
                    log.warning(f"Invalid config file {config_file}: {e}")
                    continue
            
            return None
        except Exception as e:
            log.error(f"Failed to get supplier ID from config: {e}")
            return None
    
    def get_supplier_id(self, supplier_url: str) -> str:
        """Get supplier ID with fallback to URL-based generation"""
        # First try to get from config
        supplier_id = self.get_supplier_id_from_config(supplier_url)
        if supplier_id:
            return supplier_id
        
        # Fallback to URL-based generation
        return self.get_supplier_id_from_url(supplier_url)
    
    def get_supplier_directories(self, supplier_url: str) -> Dict[str, Path]:
        """Get all supplier-specific directories"""
        supplier_id = self.get_supplier_id(supplier_url)
        
        directories = {
            "financial_reports": self.outputs_dir / "FBA_ANALYSIS" / "financial_reports" / supplier_id,
            "fba_summary": self.outputs_dir / "FBA_ANALYSIS" / "fba_summary" / supplier_id,
            "cached_products": self.outputs_dir / "cached_products" / supplier_id,
            "processing_states": self.outputs_dir / "CACHE" / "processing_states" / supplier_id,
            "workflow_results": self.outputs_dir / "FBA_ANALYSIS" / "workflow_results" / supplier_id,
            "dashboard": self.outputs_dir / "DASHBOARD" / supplier_id,
            
            # Shared directories (no supplier isolation)
            "amazon_cache": self.outputs_dir / "FBA_ANALYSIS" / "amazon_cache",
            "ai_category_cache": self.outputs_dir / "FBA_ANALYSIS" / "ai_category_cache"
        }
        
        # Create supplier-specific directories
        for key, path in directories.items():
            if key not in ["amazon_cache", "ai_category_cache"]:  # Don't create subdirs for shared resources
                path.mkdir(parents=True, exist_ok=True)
        
        return directories
    
    def get_file_paths(self, supplier_url: str, timestamp: Optional[str] = None) -> Dict[str, Path]:
        """Get complete file paths for supplier outputs"""
        supplier_id = self.get_supplier_id(supplier_url)
        directories = self.get_supplier_directories(supplier_url)
        timestamp = timestamp or self._get_timestamp()
        
        file_paths = {
            # Financial reports
            "financial_report": directories["financial_reports"] / f"fba_financial_report_{timestamp}.csv",
            
            # FBA summaries  
            "fba_summary": directories["fba_summary"] / f"fba_summary_{supplier_id}_{timestamp}.json",
            
            # Cache files
            "products_cache": directories["cached_products"] / f"{supplier_id}_products_cache.json",
            "processing_state": directories["processing_states"] / f"{supplier_id}_session_state.json",
            
            # AI category cache (shared directory, supplier-specific filename)
            "ai_category_cache": directories["ai_category_cache"] / f"{supplier_id}_ai_category_cache.json",
            
            # Workflow results
            "workflow_result": directories["workflow_results"] / f"workflow_{timestamp}.json",
            "workflow_summary": directories["workflow_results"] / f"workflow_{timestamp}_summary.txt"
        }
        
        return file_paths
    
    def _get_timestamp(self) -> str:
        """Generate timestamp for file naming"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def migrate_existing_files(self, supplier_url: str) -> Dict[str, int]:
        """Migrate existing files to supplier-specific directories"""
        supplier_id = self.get_supplier_id(supplier_url)
        directories = self.get_supplier_directories(supplier_url)
        migration_stats = {
            "financial_reports": 0,
            "fba_summaries": 0,
            "processing_states": 0,
            "cached_products": 0
        }
        
        try:
            # Migrate financial reports
            fba_analysis_dir = self.outputs_dir / "FBA_ANALYSIS"
            for file_path in fba_analysis_dir.glob("fba_financial_report_*.csv"):
                if supplier_id in file_path.name or "clearance-king" in file_path.name.lower():
                    new_path = directories["financial_reports"] / file_path.name
                    file_path.rename(new_path)
                    migration_stats["financial_reports"] += 1
                    log.info(f"Migrated financial report: {file_path.name}")
            
            # Migrate FBA summaries
            for file_path in fba_analysis_dir.glob("fba_summary_*.json"):
                if supplier_id in file_path.name or "clearance-king" in file_path.name.lower():
                    new_path = directories["fba_summary"] / file_path.name
                    file_path.rename(new_path)
                    migration_stats["fba_summaries"] += 1
                    log.info(f"Migrated FBA summary: {file_path.name}")
            
            # Migrate processing states from wrong location
            for file_path in fba_analysis_dir.glob("*_processing_state.json"):
                if supplier_id in file_path.name or "clearance-king" in file_path.name.lower():
                    # Rename to new naming convention
                    new_name = f"{supplier_id}_session_state.json"
                    new_path = directories["processing_states"] / new_name
                    file_path.rename(new_path)
                    migration_stats["processing_states"] += 1
                    log.info(f"Migrated processing state: {file_path.name} -> {new_name}")
            
            # Migrate cached products
            cached_products_dir = self.outputs_dir / "cached_products"
            for file_path in cached_products_dir.glob("*_products_cache.json"):
                if supplier_id in file_path.name or "clearance-king" in file_path.name.lower():
                    new_name = f"{supplier_id}_products_cache.json"
                    new_path = directories["cached_products"] / new_name
                    file_path.rename(new_path)
                    migration_stats["cached_products"] += 1
                    log.info(f"Migrated cached products: {file_path.name} -> {new_name}")
            
        except Exception as e:
            log.error(f"Migration failed for {supplier_id}: {e}")
        
        return migration_stats
    
    def validate_directory_structure(self, supplier_url: str) -> Dict[str, bool]:
        """Validate that all required directories exist"""
        directories = self.get_supplier_directories(supplier_url)
        validation_results = {}
        
        for key, path in directories.items():
            validation_results[key] = path.exists()
            if not path.exists():
                log.warning(f"Missing directory: {path}")
        
        return validation_results

def get_directory_manager() -> SupplierDirectoryManager:
    """Get singleton instance of directory manager"""
    if not hasattr(get_directory_manager, '_instance'):
        get_directory_manager._instance = SupplierDirectoryManager()
    return get_directory_manager._instance

# Convenience functions for backward compatibility
def get_supplier_financial_reports_dir(supplier_url: str) -> Path:
    """Get financial reports directory for supplier"""
    return get_directory_manager().get_supplier_directories(supplier_url)["financial_reports"]

def get_supplier_cache_dir(supplier_url: str) -> Path:
    """Get cached products directory for supplier"""
    return get_directory_manager().get_supplier_directories(supplier_url)["cached_products"]

def get_supplier_processing_state_path(supplier_url: str) -> Path:
    """Get processing state file path for supplier"""
    return get_directory_manager().get_file_paths(supplier_url)["processing_state"]

if __name__ == "__main__":
    # Test the directory manager
    manager = SupplierDirectoryManager()
    
    test_url = "https://www.poundwholesale.co.uk/"
    print(f"Testing with URL: {test_url}")
    
    supplier_id = manager.get_supplier_id(test_url)
    print(f"Supplier ID: {supplier_id}")
    
    directories = manager.get_supplier_directories(test_url)
    print(f"Directories created:")
    for key, path in directories.items():
        print(f"  {key}: {path}")
    
    file_paths = manager.get_file_paths(test_url)
    print(f"File paths:")
    for key, path in file_paths.items():
        print(f"  {key}: {path}")
    
    validation = manager.validate_directory_structure(test_url)
    print(f"Directory validation: {validation}")