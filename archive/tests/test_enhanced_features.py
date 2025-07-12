#!/usr/bin/env python3
"""
Test script for enhanced features of the FBA System Orchestrator
"""
import asyncio
import json
import logging
from pathlib import Path

from main_orchestrator import FBASystemOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

async def test_selective_cache_clearing(orchestrator):
    """Test selective cache clearing functionality"""
    log.info("=== Testing Selective Cache Clearing ===")
    
    # Test selective clearing
    await orchestrator.selective_clear_cache_dirs()
    
    # Verify preserved directories still exist
    for preserve_dir in orchestrator.preserve_dirs:
        if preserve_dir.exists():
            log.info(f"✅ Preserved directory exists as expected: {preserve_dir}")
        else:
            log.error(f"❌ Preserved directory was incorrectly cleared: {preserve_dir}")

async def test_extraction_mode_selection(orchestrator):
    """Test extraction mode selection logic"""
    log.info("\n=== Testing Extraction Mode Selection ===")
    
    # Get current mode
    current_mode = orchestrator.active_extraction_mode
    log.info(f"Current extraction mode: {current_mode}")
    
    # Get mode config
    mode_config = orchestrator.get_extraction_mode_config()
    log.info(f"Mode configuration: {mode_config}")
    
    # Check bypass status
    should_bypass = orchestrator.should_bypass_ai_scraping()
    log.info(f"Should bypass AI scraping: {should_bypass}")
    
    # Get fallback behavior
    fallback = orchestrator.get_fallback_behavior()
    log.info(f"Fallback behavior: {fallback}")

async def test_supplier_processing(orchestrator):
    """Test supplier processing with limited products"""
    log.info("\n=== Testing Supplier Processing (5 products) ===")
    
    try:
        # Process supplier with 5 products limit
        await orchestrator.run(['clearance-king'], max_products=5)
        
        # Check results
        if orchestrator.results:
            log.info(f"✅ Found {len(orchestrator.results)} profitable products")
            for i, result in enumerate(orchestrator.results, 1):
                product = result['supplier_product']
                analysis = result['analysis']
                log.info(f"Product {i}: {product.get('title')} - ROI: {analysis.roi_percent:.1f}%")
        else:
            log.info("No profitable products found in test run")
            
    except Exception as e:
        log.error(f"❌ Error during supplier processing: {e}")
        raise

async def main():
    """Main test execution"""
    try:
        # Load configuration
        config_path = Path('../config/system_config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        log.info("Configuration loaded successfully")
        log.info(f"Test mode: {config['system']['test_mode']}")
        log.info(f"Clear cache: {config['system']['clear_cache']}")
        log.info(f"Selective cache clear: {config['system']['selective_cache_clear']}")
        
        # Initialize orchestrator
        orchestrator = FBASystemOrchestrator(config)
        
        # Run tests
        await test_selective_cache_clearing(orchestrator)
        await test_extraction_mode_selection(orchestrator)
        await test_supplier_processing(orchestrator)
        
        log.info("\n=== All tests completed successfully! ===")
        
    except Exception as e:
        log.error(f"Test execution failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
