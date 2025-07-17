#!/usr/bin/env python3
"""
Debug script to trace exactly why linking map files are not being generated.
This script runs a minimal version of the workflow with extensive debugging.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.system_config_loader import SystemConfigLoader
from utils.browser_manager import BrowserManager

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"debug_linking_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)

async def main():
    """Debug linking map issue with detailed tracing."""
    log = logging.getLogger(__name__)
    log.info("🔍 DEBUGGING: Starting linking map issue investigation")
    
    # Check if the expected directory structure exists
    expected_dirs = [
        "/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/OUTPUTS",
        "/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/OUTPUTS/FBA_ANALYSIS", 
        "/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/OUTPUTS/FBA_ANALYSIS/linking_maps"
    ]
    
    for dir_path in expected_dirs:
        if os.path.exists(dir_path):
            log.info(f"✅ Directory exists: {dir_path}")
            # List contents
            try:
                contents = os.listdir(dir_path)
                log.info(f"   Contents: {contents}")
            except Exception as e:
                log.error(f"   Failed to list contents: {e}")
        else:
            log.error(f"❌ Directory missing: {dir_path}")
    
    # Check specific linking maps directory
    linking_maps_dir = "/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32/OUTPUTS/FBA_ANALYSIS/linking_maps"
    if os.path.exists(linking_maps_dir):
        contents = os.listdir(linking_maps_dir)
        log.info(f"🔍 linking_maps directory contents: {contents}")
        
        # Check if poundwholesale.co.uk directory exists
        poundwholesale_dir = os.path.join(linking_maps_dir, "poundwholesale.co.uk")
        if os.path.exists(poundwholesale_dir):
            log.info(f"✅ poundwholesale.co.uk directory exists")
            poundwholesale_contents = os.listdir(poundwholesale_dir)
            log.info(f"   Contents: {poundwholesale_contents}")
        else:
            log.error(f"❌ MISSING: poundwholesale.co.uk directory not found at {poundwholesale_dir}")
            log.error("   This confirms the linking map is never being saved!")
    
    # Test directory creation manually
    test_dir = os.path.join(linking_maps_dir, "debug_test_supplier")
    try:
        os.makedirs(test_dir, exist_ok=True)
        log.info(f"✅ Test directory creation successful: {test_dir}")
        
        # Test file creation
        test_file = os.path.join(test_dir, "test_linking_map.json")
        with open(test_file, 'w') as f:
            import json
            json.dump({"test": "data"}, f)
        log.info(f"✅ Test file creation successful: {test_file}")
        
        # Clean up
        os.remove(test_file)
        os.rmdir(test_dir)
        log.info("🧹 Test files cleaned up")
        
    except Exception as e:
        log.error(f"❌ Test directory/file creation failed: {e}")
    
    # Check current working directory and permissions
    current_dir = os.getcwd()
    log.info(f"🔍 Current working directory: {current_dir}")
    
    # Try to initialize workflow components to see what breaks
    try:
        log.info("🔍 Initializing config loader...")
        config_loader = SystemConfigLoader()
        log.info("✅ Config loader initialized")
        
        workflow_config = config_loader.get_workflow_config('poundwholesale_workflow')
        log.info(f"✅ Workflow config loaded: {workflow_config}")
        
        supplier_name = workflow_config.get('supplier_name', 'poundwholesale.co.uk')
        log.info(f"🔍 Supplier name from config: '{supplier_name}'")
        
        # Check if browser manager can be initialized
        log.info("🔍 Initializing browser manager...")
        browser_manager = BrowserManager.get_instance()
        log.info("✅ Browser manager initialized")
        
    except Exception as e:
        log.error(f"❌ Failed to initialize workflow components: {e}", exc_info=True)
    
    log.info("🔍 DEBUGGING: Investigation complete")

if __name__ == "__main__":
    # Fix import for datetime
    from datetime import datetime
    asyncio.run(main())