#!/usr/bin/env python3
"""
StandardizedFileManager - Centralized file management with standardized naming and paths.
Part of Amazon FBA Agent System v3.2 - Phase 6 Implementation
"""

import os
import datetime
import re
from typing import Optional, Tuple, Dict, Any
from pathlib import Path


class StandardizedFileManager:
    """
    Manages standardized file naming convention and directory structure.
    
    Naming Convention: {type}_{supplier}_{date}_{time}_{status}.{ext}
    Example: financial_report_clearance-king_20250606_143527_complete.csv
    """
    
    def __init__(self, base_dir: str = None):
        """Initialize with base directory (defaults to OUTPUTS)"""
        if base_dir is None:
            # Get current script directory and find OUTPUTS
            current_dir = Path(__file__).parent.parent
            self.base_dir = current_dir / "OUTPUTS"
        else:
            self.base_dir = Path(base_dir)
        
        # Ensure base directory exists
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Define standardized subdirectories
        self.directories = {
            'analysis_daily': 'ANALYSIS/DAILY',
            'analysis_weekly': 'ANALYSIS/WEEKLY', 
            'analysis_monthly': 'ANALYSIS/MONTHLY',
            'cache_amazon': 'CACHE/amazon_data',
            'cache_supplier': 'CACHE/supplier_data',
            'cache_ai': 'CACHE/ai_suggestions',
            'logs_system': 'LOGS/system',
            'logs_errors': 'LOGS/errors',
            'logs_performance': 'LOGS/performance',
            'exports_csv': 'EXPORTS/csv',
            'exports_excel': 'EXPORTS/excel',
            'exports_api': 'EXPORTS/api'
        }
    
    def generate_filename(self, file_type: str, supplier: str = "", 
                         status: str = "complete", extension: str = "json") -> str:
        """
        Generate standardized filename with current timestamp.
        
        Args:
            file_type: Type of file (e.g., 'financial_report', 'amazon_cache', 'ai_suggestions')
            supplier: Supplier name (sanitized)
            status: File status ('complete', 'partial', 'processing', 'error')
            extension: File extension without dot
        
        Returns:
            Standardized filename
        """
        # Get current timestamp
        now = datetime.datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        
        # Sanitize supplier name
        supplier_clean = self._sanitize_name(supplier) if supplier else "system"
        file_type_clean = self._sanitize_name(file_type)
        
        # Build filename
        if supplier_clean and supplier_clean != "system":
            filename = f"{file_type_clean}_{supplier_clean}_{date_str}_{time_str}_{status}.{extension}"
        else:
            filename = f"{file_type_clean}_{date_str}_{time_str}_{status}.{extension}"
        
        return filename
    
    def get_directory_path(self, directory_type: str, create_dated_subdir: bool = True) -> Path:
        """
        Get full path to a standardized directory.
        
        Args:
            directory_type: Key from self.directories
            create_dated_subdir: Whether to create date-based subdirectory
        
        Returns:
            Full path to directory
        """
        if directory_type not in self.directories:
            raise ValueError(f"Unknown directory type: {directory_type}")
        
        base_path = self.base_dir / self.directories[directory_type]
        
        # Add date-based subdirectory for analysis and logs
        if create_dated_subdir and directory_type.startswith(('analysis_daily', 'logs_')):
            if directory_type.startswith('analysis_daily'):
                dated_path = base_path / datetime.datetime.now().strftime("%Y-%m-%d")
                if 'financial' in directory_type or 'report' in directory_type:
                    dated_path = dated_path / "financial_reports"
                elif 'product' in directory_type or 'match' in directory_type:
                    dated_path = dated_path / "product_matches"
                elif 'summary' in directory_type:
                    dated_path = dated_path / "summary_reports"
            else:
                dated_path = base_path
        else:
            dated_path = base_path
        
        # Create directory if it doesn't exist
        dated_path.mkdir(parents=True, exist_ok=True)
        
        return dated_path
    
    def get_full_path(self, file_type: str, directory_type: str, 
                     supplier: str = "", status: str = "complete", 
                     extension: str = "json") -> Path:
        """
        Get full path for a standardized file.
        
        Returns:
            Complete Path object for the file
        """
        filename = self.generate_filename(file_type, supplier, status, extension)
        directory = self.get_directory_path(directory_type)
        return directory / filename
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize name for use in filenames"""
        if not name:
            return ""
        
        # Convert to lowercase and replace common separators
        sanitized = name.lower()
        sanitized = re.sub(r'[^\w\-_]', '-', sanitized)
        sanitized = re.sub(r'-+', '-', sanitized)  # Multiple dashes to single
        sanitized = sanitized.strip('-_')  # Remove leading/trailing separators
        
        return sanitized
    
    def create_dated_directories(self, date_str: str = None) -> Dict[str, Path]:
        """
        Create all dated directories for a specific date.
        
        Args:
            date_str: Date string (YYYY-MM-DD format), defaults to today
        
        Returns:
            Dictionary mapping directory types to paths
        """
        if date_str is None:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Validate date format
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")
        
        created_dirs = {}
        
        # Create daily analysis directories
        daily_base = self.base_dir / "ANALYSIS" / "DAILY" / date_str
        subdirs = ["financial_reports", "product_matches", "summary_reports"]
        
        for subdir in subdirs:
            dir_path = daily_base / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            created_dirs[f"daily_{subdir}"] = dir_path
        
        # Create weekly and monthly if needed
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        
        weekly_path = self.base_dir / "ANALYSIS" / "WEEKLY" / date_obj.strftime("%Y-W%U")
        weekly_path.mkdir(parents=True, exist_ok=True)
        created_dirs["weekly"] = weekly_path
        
        monthly_path = self.base_dir / "ANALYSIS" / "MONTHLY" / date_obj.strftime("%Y-%m")
        monthly_path.mkdir(parents=True, exist_ok=True)
        created_dirs["monthly"] = monthly_path
        
        return created_dirs
    
    def parse_filename(self, filename: str) -> Dict[str, str]:
        """
        Parse standardized filename to extract components.
        
        Returns:
            Dictionary with parsed components
        """
        # Remove extension
        name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
        extension = filename.rsplit('.', 1)[1] if '.' in filename else ""
        
        # Split by underscores
        parts = name_without_ext.split('_')
        
        if len(parts) >= 4:
            return {
                'file_type': parts[0],
                'supplier': parts[1] if len(parts) > 4 else "",
                'date': parts[-3],
                'time': parts[-2], 
                'status': parts[-1],
                'extension': extension
            }
        else:
            # Fallback for non-standard filenames
            return {
                'file_type': parts[0] if parts else "",
                'supplier': "",
                'date': "",
                'time': "",
                'status': "unknown",
                'extension': extension
            }
    
    def migrate_existing_file(self, old_path: str, file_type: str, 
                            directory_type: str, supplier: str = "") -> Optional[Path]:
        """
        Migrate an existing file to the new standardized structure.
        
        Args:
            old_path: Path to existing file
            file_type: Type classification for new filename
            directory_type: Target directory type
            supplier: Supplier name if applicable
        
        Returns:
            New path if successful, None if failed
        """
        old_file = Path(old_path)
        if not old_file.exists():
            return None
        
        # Determine extension
        extension = old_file.suffix.lstrip('.')
        if not extension:
            extension = "json"  # Default
        
        # Generate new path
        new_path = self.get_full_path(file_type, directory_type, supplier, "migrated", extension)
        
        try:
            # Copy file to new location
            import shutil
            shutil.copy2(old_file, new_path)
            return new_path
        except Exception as e:
            print(f"Failed to migrate {old_path}: {e}")
            return None


# Convenience functions for common operations
def get_file_manager() -> StandardizedFileManager:
    """Get a StandardizedFileManager instance"""
    return StandardizedFileManager()

def generate_financial_report_path(supplier: str = "") -> Path:
    """Generate path for financial report"""
    fm = get_file_manager()
    return fm.get_full_path("financial_report", "analysis_daily", supplier, "complete", "csv")

def generate_amazon_cache_path(asin: str, supplier: str = "") -> Path:
    """Generate path for Amazon cache file"""
    fm = get_file_manager()
    file_type = f"amazon_cache_{asin}" if asin else "amazon_cache"
    return fm.get_full_path(file_type, "cache_amazon", supplier, "complete", "json")

def generate_ai_suggestions_path(supplier: str) -> Path:
    """Generate path for AI suggestions cache"""
    fm = get_file_manager()
    return fm.get_full_path("ai_suggestions", "cache_ai", supplier, "complete", "json")

def generate_supplier_cache_path(supplier: str) -> Path:
    """Generate path for supplier cache"""
    fm = get_file_manager()
    return fm.get_full_path("supplier_cache", "cache_supplier", supplier, "complete", "json")

def generate_log_path(log_type: str = "system") -> Path:
    """Generate path for log files"""
    fm = get_file_manager()
    if log_type not in ["system", "errors", "performance"]:
        log_type = "system"
    return fm.get_full_path("fba_extraction", f"logs_{log_type}", "", "active", "log")


if __name__ == "__main__":
    # Test the file manager
    fm = StandardizedFileManager()
    
    print("Testing StandardizedFileManager...")
    
    # Test filename generation
    filename = fm.generate_filename("financial_report", "clearance-king", "complete", "csv")
    print(f"Generated filename: {filename}")
    
    # Test path generation
    path = fm.get_full_path("amazon_cache", "cache_amazon", "clearance-king", "complete", "json")
    print(f"Generated path: {path}")
    
    # Test directory creation
    dirs = fm.create_dated_directories()
    print(f"Created directories: {list(dirs.keys())}")
    
    print("File manager test completed successfully!")