"""
Supplier Guard System - .supplier_ready file management and archival
===================================================================

Implements:
- Skip regeneration if .supplier_ready exists and mtime ≤ 7 days
- On --force-regenerate, move to .bak_{UTC_ts}/ before recreating
- Proper validation of supplier readiness state
- Archive and backup management
"""

import os
import shutil
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import json

# Add parent directory to Python path for utils import
import sys
import os
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from utils.path_manager import path_manager

logger = logging.getLogger(__name__)


class SupplierGuard:
    """Manages supplier readiness state and archival"""
    
    def __init__(self):
        self.max_ready_age_days = 7
        logger.info("🛡️ Supplier Guard initialized")
    
    def check_supplier_ready(self, supplier_name: str) -> Tuple[bool, Optional[str]]:
        """
        Check if supplier is ready (has recent .supplier_ready file)
        
        Args:
            supplier_name: Supplier domain identifier
            
        Returns:
            Tuple of (is_ready, reason_message)
        """
        try:
            # Get supplier directory
            supplier_dir = Path("suppliers") / supplier_name
            ready_file = supplier_dir / ".supplier_ready"
            
            if not ready_file.exists():
                return False, f"No .supplier_ready file found in {supplier_dir}"
            
            # Check file age
            mtime = datetime.fromtimestamp(ready_file.stat().st_mtime, tz=timezone.utc)
            age = datetime.now(timezone.utc) - mtime
            max_age = timedelta(days=self.max_ready_age_days)
            
            if age > max_age:
                age_days = age.days
                return False, f".supplier_ready file is {age_days} days old (max {self.max_ready_age_days} days)"
            
            # Try to read and validate content
            try:
                with open(ready_file, 'r', encoding='utf-8') as f:
                    ready_data = json.load(f)
                
                # Basic validation
                if not isinstance(ready_data, dict):
                    return False, ".supplier_ready file contains invalid JSON structure"
                
                if not ready_data.get('supplier_name'):
                    return False, ".supplier_ready file missing supplier_name field"
                
                if ready_data.get('supplier_name') != supplier_name:
                    return False, f".supplier_ready supplier_name mismatch: {ready_data.get('supplier_name')} != {supplier_name}"
                
                logger.info(f"✅ Supplier {supplier_name} is ready (file age: {age.days} days)")
                return True, f"Supplier ready (created: {mtime.isoformat()})"
                
            except json.JSONDecodeError as e:
                return False, f".supplier_ready file contains invalid JSON: {e}"
            except Exception as e:
                return False, f"Error reading .supplier_ready file: {e}"
                
        except Exception as e:
            logger.error(f"Error checking supplier readiness: {e}")
            return False, f"Error checking supplier readiness: {e}"
    
    def archive_supplier_on_force_regenerate(
        self, 
        supplier_name: str, 
        force_regenerate: bool = False
    ) -> Optional[Path]:
        """
        Archive supplier directory when force regeneration is requested
        
        Args:
            supplier_name: Supplier domain identifier
            force_regenerate: Whether to force regeneration
            
        Returns:
            Path to backup directory if archived, None if not needed
        """
        if not force_regenerate:
            return None
        
        try:
            supplier_dir = Path("suppliers") / supplier_name
            
            if not supplier_dir.exists():
                logger.info(f"Supplier directory {supplier_dir} does not exist, no archival needed")
                return None
            
            # Create backup directory with UTC timestamp
            utc_ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%SUTC")
            backup_name = f"{supplier_name}.bak_{utc_ts}"
            backup_dir = supplier_dir.parent / backup_name
            
            # Move supplier directory to backup location
            shutil.move(str(supplier_dir), str(backup_dir))
            
            logger.info(f"📦 Archived supplier {supplier_name} to {backup_dir}")
            
            # Create new empty supplier directory
            supplier_dir.mkdir(parents=True, exist_ok=True)
            
            return backup_dir
            
        except Exception as e:
            logger.error(f"Failed to archive supplier {supplier_name}: {e}")
            raise
    
    def create_supplier_ready_file_intelligent(
        self,
        supplier_name: str,
        ready_data: Dict[str, Any]
    ) -> Path:
        """
        Create intelligent .supplier_ready file in new "report card" format
        
        Args:
            supplier_name: Supplier domain identifier
            ready_data: Complete ready file data in new format
            
        Returns:
            Path to created .supplier_ready file
        """
        try:
            # Get supplier directory
            supplier_dir = Path("suppliers") / supplier_name
            supplier_dir.mkdir(parents=True, exist_ok=True)
            
            ready_file = supplier_dir / ".supplier_ready"
            
            # Save ready file directly (data already formatted)
            with open(ready_file, 'w', encoding='utf-8') as f:
                json.dump(ready_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Created intelligent .supplier_ready file for {supplier_name}: {ready_file}")
            return ready_file
            
        except Exception as e:
            logger.error(f"Failed to create intelligent .supplier_ready file for {supplier_name}: {e}")
            raise

    def create_supplier_ready_file(
        self, 
        supplier_name: str, 
        supplier_data: Dict[str, Any]
    ) -> Path:
        """
        Create .supplier_ready file with supplier completion data (legacy format)
        
        Args:
            supplier_name: Supplier domain identifier
            supplier_data: Supplier metadata and completion status
            
        Returns:
            Path to created .supplier_ready file
        """
        try:
            # Get supplier directory
            supplier_dir = Path("suppliers") / supplier_name
            supplier_dir.mkdir(parents=True, exist_ok=True)
            
            ready_file = supplier_dir / ".supplier_ready"
            
            # Create comprehensive ready file data
            ready_data = {
                "supplier_name": supplier_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "system_version": "3.5.0",
                "completion_status": {
                    "products_extracted": supplier_data.get('total_products', 0),
                    "categories_processed": supplier_data.get('categories_discovered', 0),
                    "linking_map_generated": supplier_data.get('linking_map_created', False),
                    "ai_categories_generated": supplier_data.get('ai_categories_created', False)
                },
                "file_locations": {
                    "cached_products": supplier_data.get('cached_products_path'),
                    "ai_category_cache": supplier_data.get('ai_category_cache_path'), 
                    "linking_map": supplier_data.get('linking_map_path'),
                    "run_output_dir": supplier_data.get('run_output_dir')
                },
                "processing_summary": {
                    "extraction_started": supplier_data.get('extraction_started'),
                    "extraction_completed": supplier_data.get('extraction_completed'),
                    "total_processing_time": supplier_data.get('total_processing_time'),
                    "success_rate": supplier_data.get('success_rate', 1.0)
                },
                "validation": {
                    "guard_version": "1.0",
                    "max_age_days": self.max_ready_age_days,
                    "checksum": self._calculate_checksum(supplier_data)
                }
            }
            
            # Save ready file
            with open(ready_file, 'w', encoding='utf-8') as f:
                json.dump(ready_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Created .supplier_ready file for {supplier_name}: {ready_file}")
            return ready_file
            
        except Exception as e:
            logger.error(f"Failed to create .supplier_ready file for {supplier_name}: {e}")
            raise
    
    def _calculate_checksum(self, supplier_data: Dict[str, Any]) -> str:
        """Calculate simple checksum for supplier data validation"""
        try:
            # Create checksum from key fields
            checksum_data = {
                "total_products": supplier_data.get('total_products', 0),
                "categories_discovered": supplier_data.get('categories_discovered', 0),
                "timestamp": datetime.now(timezone.utc).strftime("%Y%m%d")
            }
            checksum_string = json.dumps(checksum_data, sort_keys=True)
            return str(hash(checksum_string))
        except:
            return "unknown"
    
    def validate_supplier_ready_file(self, supplier_name: str) -> Dict[str, Any]:
        """
        Validate and return contents of .supplier_ready file
        
        Args:
            supplier_name: Supplier domain identifier
            
        Returns:
            Dictionary with validation results and file contents
        """
        try:
            supplier_dir = Path("suppliers") / supplier_name
            ready_file = supplier_dir / ".supplier_ready"
            
            if not ready_file.exists():
                return {
                    "valid": False,
                    "error": "File does not exist",
                    "path": str(ready_file)
                }
            
            # Read file contents
            with open(ready_file, 'r', encoding='utf-8') as f:
                ready_data = json.load(f)
            
            # File age check
            mtime = datetime.fromtimestamp(ready_file.stat().st_mtime, tz=timezone.utc)
            age = datetime.now(timezone.utc) - mtime
            is_fresh = age <= timedelta(days=self.max_ready_age_days)
            
            # Validation checks
            validation_results = {
                "valid": True,
                "path": str(ready_file),
                "age_days": age.days,
                "is_fresh": is_fresh,
                "created_at": ready_data.get('created_at'),
                "supplier_name_match": ready_data.get('supplier_name') == supplier_name,
                "completion_status": ready_data.get('completion_status', {}),
                "file_locations": ready_data.get('file_locations', {}),
                "data": ready_data
            }
            
            # Check for critical issues
            if not validation_results["supplier_name_match"]:
                validation_results["valid"] = False
                validation_results["error"] = "Supplier name mismatch"
            elif not is_fresh:
                validation_results["valid"] = False
                validation_results["error"] = f"File too old ({age.days} days)"
            
            return validation_results
            
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "error": f"Invalid JSON: {e}",
                "path": str(ready_file)
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {e}",
                "path": str(ready_file) if 'ready_file' in locals() else "unknown"
            }
    
    def cleanup_old_backups(self, supplier_name: str, keep_count: int = 5) -> int:
        """
        Clean up old backup directories, keeping only the most recent ones
        
        Args:
            supplier_name: Supplier domain identifier
            keep_count: Number of recent backups to keep
            
        Returns:
            Number of backups removed
        """
        try:
            suppliers_dir = Path("suppliers")
            if not suppliers_dir.exists():
                return 0
            
            # Find backup directories for this supplier
            backup_pattern = f"{supplier_name}.bak_*"
            backup_dirs = list(suppliers_dir.glob(backup_pattern))
            
            if len(backup_dirs) <= keep_count:
                return 0
            
            # Sort by modification time (newest first)
            backup_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            
            # Remove old backups
            removed_count = 0
            for old_backup in backup_dirs[keep_count:]:
                try:
                    shutil.rmtree(old_backup)
                    removed_count += 1
                    logger.info(f"🗑️ Removed old backup: {old_backup}")
                except Exception as e:
                    logger.warning(f"Failed to remove backup {old_backup}: {e}")
            
            logger.info(f"🧹 Cleaned up {removed_count} old backups for {supplier_name}")
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup backups for {supplier_name}: {e}")
            return 0
    
    def get_supplier_status_summary(self, supplier_name: str) -> Dict[str, Any]:
        """
        Get comprehensive status summary for supplier
        
        Args:
            supplier_name: Supplier domain identifier
            
        Returns:
            Dictionary with complete supplier status
        """
        try:
            # Check readiness
            is_ready, ready_message = self.check_supplier_ready(supplier_name)
            
            # Validate ready file
            validation_results = self.validate_supplier_ready_file(supplier_name)
            
            # Count backups
            suppliers_dir = Path("suppliers")
            backup_count = len(list(suppliers_dir.glob(f"{supplier_name}.bak_*"))) if suppliers_dir.exists() else 0
            
            # Check for current supplier directory
            supplier_dir = Path("suppliers") / supplier_name
            has_current_dir = supplier_dir.exists()
            
            return {
                "supplier_name": supplier_name,
                "is_ready": is_ready,
                "ready_message": ready_message,
                "has_current_directory": has_current_dir,
                "backup_count": backup_count,
                "validation": validation_results,
                "guard_recommendations": self._get_recommendations(is_ready, validation_results, backup_count)
            }
            
        except Exception as e:
            logger.error(f"Failed to get status summary for {supplier_name}: {e}")
            return {
                "supplier_name": supplier_name,
                "is_ready": False,
                "ready_message": f"Error getting status: {e}",
                "error": str(e)
            }
    
    def _get_recommendations(
        self, 
        is_ready: bool, 
        validation_results: Dict[str, Any], 
        backup_count: int
    ) -> List[str]:
        """Generate recommendations based on supplier status"""
        recommendations = []
        
        if not is_ready:
            recommendations.append("Run full supplier processing to create .supplier_ready file")
        
        if validation_results.get("age_days", 0) > 3:
            recommendations.append("Consider refreshing supplier data (file is getting old)")
        
        if backup_count > 10:
            recommendations.append(f"Clean up old backups ({backup_count} found)")
        
        if not validation_results.get("valid", False):
            recommendations.append("Fix .supplier_ready file validation issues")
        
        if not recommendations:
            recommendations.append("Supplier is ready and healthy")
        
        return recommendations


# Global instance
_supplier_guard: Optional[SupplierGuard] = None


def get_supplier_guard() -> SupplierGuard:
    """Get or create global supplier guard instance"""
    global _supplier_guard
    if _supplier_guard is None:
        _supplier_guard = SupplierGuard()
    return _supplier_guard


# Convenience functions
def check_supplier_ready(supplier_name: str) -> Tuple[bool, Optional[str]]:
    """Check if supplier is ready for processing"""
    guard = get_supplier_guard()
    return guard.check_supplier_ready(supplier_name)


def archive_supplier_on_force_regenerate(supplier_name: str, force_regenerate: bool = False) -> Optional[Path]:
    """Archive supplier directory on force regeneration"""
    guard = get_supplier_guard()
    return guard.archive_supplier_on_force_regenerate(supplier_name, force_regenerate)


def create_supplier_ready_file(supplier_name: str, supplier_data: Dict[str, Any]) -> Path:
    """Create .supplier_ready file for completed supplier"""
    guard = get_supplier_guard()
    return guard.create_supplier_ready_file(supplier_name, supplier_data)


def get_supplier_status_summary(supplier_name: str) -> Dict[str, Any]:
    """Get comprehensive supplier status summary"""
    guard = get_supplier_guard()
    return guard.get_supplier_status_summary(supplier_name)


if __name__ == "__main__":
    # Test supplier guard functionality
    logging.basicConfig(level=logging.INFO)
    
    test_supplier = "test-supplier.com"
    
    # Test status checking
    print("Testing supplier guard...")
    
    # Check non-existent supplier
    is_ready, message = check_supplier_ready(test_supplier)
    print(f"Non-existent supplier ready: {is_ready} - {message}")
    
    # Create test ready file
    test_data = {
        "total_products": 50,
        "categories_discovered": 8,
        "linking_map_created": True,
        "ai_categories_created": True,
        "cached_products_path": "/test/path/cached_products.json",
        "extraction_started": datetime.now(timezone.utc).isoformat(),
        "extraction_completed": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        ready_file = create_supplier_ready_file(test_supplier, test_data)
        print(f"Created ready file: {ready_file}")
        
        # Check status again
        is_ready, message = check_supplier_ready(test_supplier)
        print(f"After creation ready: {is_ready} - {message}")
        
        # Get full status
        status = get_supplier_status_summary(test_supplier)
        print(f"Status summary: {json.dumps(status, indent=2)}")
        
        # Test archival
        backup_dir = archive_supplier_on_force_regenerate(test_supplier, force_regenerate=True)
        print(f"Archived to: {backup_dir}")
        
        print("✅ All supplier guard tests passed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")