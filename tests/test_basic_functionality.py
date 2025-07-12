"""
Basic functionality tests for Amazon FBA Agent System v3.5
Tests core imports and basic functionality without external dependencies.
"""
import os
import sys
import json
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools"))
sys.path.insert(0, str(project_root / "utils"))


class TestBasicImports:
    """Test that all core modules can be imported."""
    
    def test_environment_variables_loaded(self):
        """Test that environment variables are properly loaded."""
        from dotenv import load_dotenv
        load_dotenv()
        
        # Check if at least one environment variable is set
        openai_key = os.getenv("OPENAI_API_KEY")
        assert openai_key is not None, "OPENAI_API_KEY should be set in environment"
        assert len(openai_key) > 10, "OPENAI_API_KEY should be a valid length"
        # Accept both real keys (sk-) and test keys for flexible testing
        assert openai_key.startswith(("sk-", "test-")), "OPENAI_API_KEY should be valid format"
    
    def test_path_manager_import(self):
        """Test that path manager can be imported and used."""
        try:
            from utils.path_manager import get_api_log_path, get_processing_state_path
            
            # Test basic functionality
            log_path = get_api_log_path("test")
            assert "logs/api_calls" in str(log_path), "Log path should contain logs/api_calls"
            
            state_path = get_processing_state_path("test-supplier")
            assert "processing_states" in str(state_path), "State path should contain processing_states"
            
        except ImportError as e:
            pytest.fail(f"Failed to import path manager: {e}")
    
    def test_enhanced_state_manager_import(self):
        """Test that enhanced state manager can be imported."""
        try:
            from utils.enhanced_state_manager import EnhancedStateManager
            
            # Test basic initialization
            state_manager = EnhancedStateManager("test-supplier")
            assert state_manager.supplier_name == "test-supplier"
            
        except ImportError as e:
            pytest.fail(f"Failed to import enhanced state manager: {e}")
    
    @pytest.mark.slow
    def test_main_workflow_import(self):
        """Test that main workflow can be imported (may be slow due to dependencies)."""
        try:
            import tools.passive_extraction_workflow_latest
            # Just test that it imports without error
            assert hasattr(tools.passive_extraction_workflow_latest, 'OPENAI_API_KEY')
            
        except ImportError as e:
            pytest.fail(f"Failed to import main workflow: {e}")
    
    def test_required_directories_exist(self):
        """Test that required directories exist."""
        project_root = Path(__file__).parent.parent
        
        required_dirs = [
            "logs/api_calls",
            "logs/application", 
            "OUTPUTS/CACHE/processing_states",
            "OUTPUTS/FBA_ANALYSIS",
            "tools",
            "utils",
            "config"
        ]
        
        for dir_path in required_dirs:
            full_path = project_root / dir_path
            assert full_path.exists(), f"Required directory {dir_path} should exist"


class TestConfiguration:
    """Test configuration loading and validation."""
    
    def test_system_config_exists(self):
        """Test that system config file exists and is valid JSON."""
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config" / "system_config.json"
        
        assert config_path.exists(), "system_config.json should exist"
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        assert "system" in config, "Config should have 'system' section"
        assert "version" in config["system"], "Config should have version"
        assert config["system"]["version"] == "3.5.0", "Version should be 3.5.0"
    
    def test_env_file_exists(self):
        """Test that .env file exists."""
        project_root = Path(__file__).parent.parent
        env_path = project_root / ".env"
        
        assert env_path.exists(), ".env file should exist"
        
        # Check that it contains required keys
        with open(env_path, 'r') as f:
            content = f.read()
        
        assert "OPENAI_API_KEY=" in content, ".env should contain OPENAI_API_KEY"
        assert "OPENAI_MODEL_PRIMARY=" in content, ".env should contain OPENAI_MODEL_PRIMARY"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])