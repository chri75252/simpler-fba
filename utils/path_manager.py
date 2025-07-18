"""
Path Manager - Centralized file path management for Amazon FBA Agent System v3.5

This module provides standardized path resolution following the CLAUDE_STANDARDS.md file organization standards.
All scripts MUST use these functions instead of hardcoded paths.
"""

import os
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Union, Optional


class PathManager:
    """Centralized path management following CLAUDE_STANDARDS.md standards"""
    
    def __init__(self):
        # Determine project root (where CLAUDE_STANDARDS.md is located)
        current_file = Path(__file__).resolve()
        self.project_root = current_file.parent.parent
        
        # Verify we found the correct root by checking for CLAUDE_STANDARDS.md
        claude_standards_path = self.project_root / "CLAUDE_STANDARDS.md"
        if not claude_standards_path.exists():
            # Fallback to claude.md for backwards compatibility
            claude_md_path = self.project_root / "claude.md"
            if not claude_md_path.exists():
                raise FileNotFoundError(
                    f"Could not locate CLAUDE_STANDARDS.md or claude.md at {self.project_root}. "
                    f"Please ensure PathManager is imported from the correct location."
                )
    
    def get_log_path(self, category: str, filename: str, create_dirs: bool = True) -> Path:
        """
        Get standardized log file path
        
        Args:
            category: Log category (application, api_calls, tests, monitoring, security, debug)
            filename: Log filename (should include date and extension)
            create_dirs: Whether to create missing directories
            
        Returns:
            Path object for the log file
            
        Example:
            log_path = path_manager.get_log_path("application", "passive_extraction_20250615.log")
        """
        valid_categories = ["application", "api_calls", "tests", "monitoring", "security", "debug"]
        if category not in valid_categories:
            raise ValueError(f"Invalid log category '{category}'. Must be one of: {valid_categories}")
        
        log_dir = self.project_root / "logs" / category
        if create_dirs:
            log_dir.mkdir(parents=True, exist_ok=True)
            
        return log_dir / filename
    
    def get_output_path(self, *path_parts: str, create_dirs: bool = True) -> Path:
        """
        Get standardized output file path under OUTPUTS/
        
        Args:
            *path_parts: Path components under OUTPUTS/ directory
            create_dirs: Whether to create missing directories
            
        Returns:
            Path object for the output file
            
        Example:
            output_path = path_manager.get_output_path("FBA_ANALYSIS", "financial_reports", "report_20250615.csv")
        """
        output_path = self.project_root / "OUTPUTS"
        for part in path_parts:
            output_path = output_path / part
            
        if create_dirs:
            # Smart directory creation: if the last component has an extension, 
            # it's likely a filename, so only create the parent directory
            if len(path_parts) > 0 and '.' in str(path_parts[-1]):
                # Last component appears to be a filename, create parent directories only
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                # Create the full directory path when requested
                output_path.mkdir(parents=True, exist_ok=True)
            
        return output_path
    
    def get_docs_path(self, filename: str, subdir: Optional[str] = None, create_dirs: bool = True) -> Path:
        """
        Get standardized documentation file path
        
        Args:
            filename: Documentation filename
            subdir: Optional subdirectory under docs/ (architecture, user_guides, development, reports)
            create_dirs: Whether to create missing directories
            
        Returns:
            Path object for the documentation file
            
        Example:
            docs_path = path_manager.get_docs_path("API_REFERENCE.md")
            report_path = path_manager.get_docs_path("security_audit.md", "reports")
        """
        docs_dir = self.project_root / "docs"
        if subdir:
            docs_dir = docs_dir / subdir
            
        if create_dirs:
            docs_dir.mkdir(parents=True, exist_ok=True)
            
        return docs_dir / filename
    
    def get_cache_path(self, *path_parts: str, create_dirs: bool = True) -> Path:
        """
        Get standardized cache file path under OUTPUTS/CACHE/
        
        Args:
            *path_parts: Path components under CACHE/ directory
            create_dirs: Whether to create missing directories
            
        Returns:
            Path object for the cache file
            
        Example:
            cache_path = path_manager.get_cache_path("processing_states", "clearance_king_state.json")
        """
        return self.get_output_path("CACHE", *path_parts, create_dirs=create_dirs)
    
    def get_config_path(self, filename: str) -> Path:
        """
        Get configuration file path
        
        Args:
            filename: Configuration filename
            
        Returns:
            Path object for the config file
            
        Example:
            config_path = path_manager.get_config_path("system_config.json")
        """
        return self.project_root / "config" / filename
    
    def get_test_path(self, *path_parts: str, create_dirs: bool = True) -> Path:
        """
        Get test-related file path
        
        Args:
            *path_parts: Path components under tests/ directory
            create_dirs: Whether to create missing directories
            
        Returns:
            Path object for the test file
            
        Example:
            test_path = path_manager.get_test_path("fixtures", "sample_data.json")
        """
        test_path = self.project_root / "tests"
        for part in path_parts:
            test_path = test_path / part
            
        if create_dirs and len(path_parts) > 1:
            test_path.parent.mkdir(parents=True, exist_ok=True)
            
        return test_path


# Global instance for easy access
path_manager = PathManager()


# Convenience functions for common operations
def get_log_path(category: str, filename: str = None, component_name: str = None) -> Path:
    """
    Convenience function to get log path with automatic filename generation
    
    Args:
        category: Log category 
        filename: Specific filename, or None to auto-generate
        component_name: Component name for auto-generation
        
    Returns:
        Path object for log file
    """
    if filename is None:
        if component_name is None:
            raise ValueError("Either filename or component_name must be provided")
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{component_name}_{date_str}.log"
    
    return path_manager.get_log_path(category, filename)


def get_api_log_path(api_name: str, format_type: str = "jsonl") -> Path:
    """
    Convenience function for API log paths
    
    Args:
        api_name: Name of the API (openai, keepa, amazon)
        format_type: File format (jsonl, log)
        
    Returns:
        Path object for API log file
    """
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{api_name}_api_calls_{date_str}.{format_type}"
    return path_manager.get_log_path("api_calls", filename)


def get_processing_state_path(supplier_name: str) -> Path:
    """
    Convenience function for processing state files
    
    Args:
        supplier_name: Name of the supplier
        
    Returns:
        Path object for state file
    """
    safe_name = supplier_name.replace(".", "_").replace("/", "_")
    filename = f"{safe_name}_processing_state.json"
    return path_manager.get_cache_path("processing_states", filename)


def get_phase_continuation_path() -> Path:
    """
    Convenience function for phase 2 continuation points file
    
    Returns:
        Path object for phase continuation file
    """
    return path_manager.get_cache_path("processing_states", "phase_2_continuation_points.json")


def get_run_output_dir(supplier: str) -> Path:
    """
    Get run-based output directory for a supplier with comprehensive error handling
    
    Creates a timestamped run directory: OUTPUTS/{supplier}/{run_ts}_run/
    where run_ts is a UTC timestamp in YYYYMMDD_HHMMSS format.
    
    Args:
        supplier: Supplier domain string (e.g., "clearance-king.co.uk")
        
    Returns:
        Path object for run-specific output directory
        
    Raises:
        ValueError: If supplier string is empty or invalid
        OSError: If directory creation fails
        
    Example:
        >>> run_dir = get_run_output_dir("clearance-king.co.uk")
        >>> # Returns: OUTPUTS/clearance-king-co-uk/20250628_143022_run/
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Input validation
        if not supplier or not isinstance(supplier, str):
            raise ValueError(f"Supplier must be a non-empty string, got: {type(supplier).__name__}")
        
        if not supplier.strip():
            raise ValueError("Supplier string cannot be empty or whitespace only")
        
        # Sanitize supplier name for filesystem compatibility
        # Remove common URL prefixes and replace problematic characters
        safe_name = (supplier.strip()
                    .replace("https://", "")
                    .replace("http://", "")
                    .replace("www.", "")
                    .replace(".", "-")
                    .replace("/", "-")
                    .replace("\\", "-")
                    .replace(":", "-")
                    .replace("?", "-")
                    .replace("&", "-")
                    .replace("=", "-")
                    .replace("#", "-"))
        
        # Remove any remaining invalid characters and consecutive dashes
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in "-_")
        safe_name = "-".join(filter(None, safe_name.split("-")))  # Remove consecutive dashes
        
        if not safe_name:
            raise ValueError(f"Supplier name '{supplier}' results in empty safe name after sanitization")
        
        # Generate UTC timestamp in YYYYMMDD_HHMMSS format
        try:
            utc_now = datetime.now(timezone.utc)
            run_ts = utc_now.strftime("%Y%m%d_%H%M%S")
        except Exception as e:
            logger.error(f"Failed to generate UTC timestamp: {e}")
            raise OSError(f"Timestamp generation failed: {e}") from e
        
        # Construct run directory name
        run_dir_name = f"{run_ts}_run"
        
        logger.info(f"Creating run output directory for supplier '{supplier}' -> '{safe_name}/{run_dir_name}'")
        
        # Create the directory path using path_manager
        try:
            run_output_path = path_manager.get_output_path(safe_name, run_dir_name, create_dirs=True)
        except Exception as e:
            logger.error(f"Failed to create run output directory for supplier '{supplier}': {e}")
            raise OSError(f"Directory creation failed for '{safe_name}/{run_dir_name}': {e}") from e
        
        # Verify directory was created successfully
        if not run_output_path.exists():
            raise OSError(f"Directory creation appeared to succeed but path does not exist: {run_output_path}")
        
        if not run_output_path.is_dir():
            raise OSError(f"Path exists but is not a directory: {run_output_path}")
        
        logger.debug(f"Successfully created run output directory: {run_output_path}")
        
        return run_output_path
        
    except ValueError:
        # Re-raise ValueError with original message
        raise
    except OSError:
        # Re-raise OSError with original message
        raise
    except Exception as e:
        # Catch any unexpected errors and wrap them
        logger.error(f"Unexpected error in get_run_output_dir for supplier '{supplier}': {e}")
        raise OSError(f"Unexpected error creating run output directory: {e}") from e


def get_linking_map_path(supplier_name: str = None, run_output_dir: Path = None) -> Path:
    """
    Convenience function for linking map files
    
    Args:
        supplier_name: Optional supplier name for specific linking map
        run_output_dir: Optional run-specific output directory
        
    Returns:
        Path object for linking map file
    """
    if run_output_dir:
        linking_maps_dir = run_output_dir / "linking_maps"
        linking_maps_dir.mkdir(exist_ok=True)
        return linking_maps_dir / "linking_map.json"
    elif supplier_name:
        # Use subdirectory structure for linking maps (matching working pre-minor-fix format)
        return path_manager.get_output_path("FBA_ANALYSIS", "linking_maps", supplier_name, "linking_map.json")
    else:
        filename = "linking_map.json"
    return path_manager.get_output_path("FBA_ANALYSIS", "linking_maps", filename)


def ensure_directories_exist():
    """
    Ensure all standard directories exist
    Should be called during application startup
    """
    # Create all standard log directories
    for category in ["application", "api_calls", "tests", "monitoring", "security", "debug"]:
        path_manager.get_log_path(category, "dummy", create_dirs=True)
    
    # Create standard output directories
    for subdir in ["FBA_ANALYSIS", "CACHE", "REPORTS", "BACKUPS"]:
        path_manager.get_output_path(subdir, "dummy", create_dirs=True)
    
    # Create docs subdirectories
    for subdir in ["architecture", "user_guides", "development", "reports"]:
        path_manager.get_docs_path("dummy", subdir, create_dirs=True)
    
    print("✅ All standard directories created/verified")


def ensure_output_subdirs():
    """
    Ensure OUTPUTS subdirectories exist for tests and workflow operations
    Creates the specific directories that tests expect to find
    """
    # Create FBA_ANALYSIS subdirectories required by tests
    subdirs = [
        ("FBA_ANALYSIS", "Linking map"),         # For linking map logic tests
        ("FBA_ANALYSIS", "financial_reports"),   # For enhanced CSV output tests  
        ("FBA_ANALYSIS", "amazon_cache"),        # For Amazon cache data tests
        ("FBA_ANALYSIS", "linking_maps"),        # Alternative linking map location
        ("CACHE", "processing_states"),          # For processing state management
        ("CACHE", "products"),                   # For product cache
        ("CACHE", "analysis"),                   # For analysis cache
    ]
    
    for subdir_parts in subdirs:
        # Create the full path using path_manager
        full_path = path_manager.get_output_path(*subdir_parts)
        # Ensure the directory exists (get_output_path creates parent dirs)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Also create a .gitkeep file to ensure directories persist
        gitkeep_file = full_path.parent / ".gitkeep"
        if not gitkeep_file.exists():
            gitkeep_file.touch()
    
    print("✅ OUTPUTS subdirectories created/verified")


# Example usage and testing
if __name__ == "__main__":
    # Test path generation
    print("Testing PathManager...")
    
    # Test log paths
    log_path = get_log_path("application", component_name="passive_extraction")
    print(f"Application log: {log_path}")
    
    # Test API log paths
    api_log = get_api_log_path("openai")
    print(f"API log: {api_log}")
    
    # Test output paths
    output_path = path_manager.get_output_path("FBA_ANALYSIS", "financial_reports", "test_report.csv")
    print(f"Output path: {output_path}")
    
    # Test state file path
    state_path = get_processing_state_path("clearance-king.co.uk")
    print(f"State path: {state_path}")
    
    # Test enhanced run output directory function
    try:
        run_output_dir = get_run_output_dir("clearance-king.co.uk")
        print(f"Run output directory: {run_output_dir}")
        
        # Test with edge cases
        print("Testing edge cases...")
        edge_case_dir = get_run_output_dir("https://www.supplier-site.com/path?param=value")
        print(f"Edge case directory: {edge_case_dir}")
        
    except Exception as e:
        print(f"❌ Error testing run output directory: {e}")
    
    # Ensure directories exist
    ensure_directories_exist()
    
    # Test output subdirectories helper
    ensure_output_subdirs()
    
    print("✅ PathManager test completed successfully")