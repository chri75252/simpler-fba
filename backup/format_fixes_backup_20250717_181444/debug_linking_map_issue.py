#!/usr/bin/env python3
"""
Debug script to trace linking map save operations
This will help identify why linking maps and financial reports aren't being generated
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up enhanced logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'debug_linking_map_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

def check_method_signatures():
    """Check method signatures in the workflow file"""
    log.info("🔍 Checking method signatures in passive_extraction_workflow_latest.py")
    
    workflow_file = project_root / "tools" / "passive_extraction_workflow_latest.py"
    
    if not workflow_file.exists():
        log.error(f"❌ Workflow file not found: {workflow_file}")
        return
    
    with open(workflow_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find _save_final_report method signatures
    import re
    save_final_report_matches = re.findall(r'def _save_final_report\([^)]*\):', content)
    log.info(f"Found _save_final_report signatures: {save_final_report_matches}")
    
    # Find calls to _save_final_report
    save_final_report_calls = re.findall(r'self\._save_final_report\([^)]*\)', content)
    log.info(f"Found _save_final_report calls: {save_final_report_calls}")
    
    # Check for parameter mismatches
    for call in save_final_report_calls:
        param_count = call.count(',') + 1
        log.info(f"Call '{call}' has {param_count} parameters")

def check_import_paths():
    """Check if all required imports are available"""
    log.info("🔍 Checking import paths and dependencies")
    
    try:
        from tools.passive_extraction_workflow_latest import PassiveExtractionWorkflow
        log.info("✅ PassiveExtractionWorkflow import successful")
    except ImportError as e:
        log.error(f"❌ Failed to import PassiveExtractionWorkflow: {e}")
        return False
    
    try:
        from utils.path_manager import get_linking_map_path
        log.info("✅ get_linking_map_path import successful")
    except ImportError as e:
        log.error(f"❌ Failed to import get_linking_map_path: {e}")
        return False
    
    return True

def test_path_manager():
    """Test path manager functionality"""
    log.info("🔍 Testing path manager functionality")
    
    try:
        from utils.path_manager import get_linking_map_path
        
        # Test with sample supplier name
        test_supplier = "test_supplier"
        linking_map_path = get_linking_map_path(test_supplier)
        
        log.info(f"✅ Linking map path for '{test_supplier}': {linking_map_path}")
        log.info(f"✅ Path type: {type(linking_map_path)}")
        log.info(f"✅ Path exists: {linking_map_path.exists()}")
        log.info(f"✅ Parent directory exists: {linking_map_path.parent.exists()}")
        
        return True
        
    except Exception as e:
        log.error(f"❌ Path manager test failed: {e}", exc_info=True)
        return False

def check_output_directories():
    """Check if output directories exist and are writable"""
    log.info("🔍 Checking output directories")
    
    # Check main output directories
    output_dirs = [
        project_root / "OUTPUTS",
        project_root / "OUTPUTS" / "linking_maps",
        project_root / "OUTPUTS" / "supplier_cache",
        project_root / "OUTPUTS" / "amazon_cache"
    ]
    
    for output_dir in output_dirs:
        log.info(f"Checking directory: {output_dir}")
        
        if output_dir.exists():
            log.info(f"✅ Directory exists: {output_dir}")
            
            # Test write permissions
            test_file = output_dir / "test_write.tmp"
            try:
                test_file.write_text("test")
                test_file.unlink()
                log.info(f"✅ Directory writable: {output_dir}")
            except Exception as e:
                log.error(f"❌ Directory not writable: {output_dir} - {e}")
        else:
            log.warning(f"⚠️ Directory does not exist: {output_dir}")
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                log.info(f"✅ Created directory: {output_dir}")
            except Exception as e:
                log.error(f"❌ Failed to create directory: {output_dir} - {e}")

def analyze_workflow_execution():
    """Analyze the workflow execution path"""
    log.info("🔍 Analyzing workflow execution path")
    
    workflow_file = project_root / "tools" / "passive_extraction_workflow_latest.py"
    
    if not workflow_file.exists():
        log.error(f"❌ Workflow file not found: {workflow_file}")
        return
    
    with open(workflow_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the _process_chunk_with_main_workflow_logic method
    method_start = None
    for i, line in enumerate(lines):
        if "def _process_chunk_with_main_workflow_logic" in line:
            method_start = i + 1
            break
    
    if method_start is None:
        log.error("❌ Could not find _process_chunk_with_main_workflow_logic method")
        return
    
    log.info(f"✅ Found _process_chunk_with_main_workflow_logic at line {method_start}")
    
    # Check lines around 6399 and 6404
    target_lines = [6399, 6404]
    for line_num in target_lines:
        if line_num <= len(lines):
            line_content = lines[line_num - 1].strip()
            log.info(f"Line {line_num}: {line_content}")
        else:
            log.error(f"❌ Line {line_num} does not exist in file (total lines: {len(lines)})")

def main():
    """Main debug function"""
    log.info("🚀 Starting comprehensive linking map debug analysis")
    log.info(f"Project root: {project_root}")
    
    # Step 1: Check method signatures
    check_method_signatures()
    
    # Step 2: Check imports
    if not check_import_paths():
        log.error("❌ Import check failed - cannot continue")
        return
    
    # Step 3: Test path manager
    if not test_path_manager():
        log.error("❌ Path manager test failed")
    
    # Step 4: Check output directories
    check_output_directories()
    
    # Step 5: Analyze workflow execution
    analyze_workflow_execution()
    
    log.info("🏁 Debug analysis completed")

if __name__ == "__main__":
    main()