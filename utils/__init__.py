"""
Utils Package - Amazon FBA Agent System v3.5

This package contains utility modules for path management, state management,
and file organization following the claude.md standards.
"""

from .path_manager import (
    PathManager, 
    path_manager,
    get_log_path,
    get_api_log_path,
    get_processing_state_path,
    ensure_directories_exist
)

from .enhanced_state_manager import EnhancedStateManager

__version__ = "3.5.0"
__all__ = [
    "PathManager",
    "path_manager", 
    "get_log_path",
    "get_api_log_path",
    "get_processing_state_path",
    "ensure_directories_exist",
    "EnhancedStateManager"
]
