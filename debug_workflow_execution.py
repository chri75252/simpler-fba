#!/usr/bin/env python3
"""
Debug script to isolate PassiveExtractionWorkflow execution issue
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set OPENAI_API_KEY
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "sk-15Mk5F_Nvf8k06VvEi4_TD2GhL8mQnqR_8I6Z2zHjWT3BlbkFJvKlNwbgLB_HPw1C-SixqIskN03to4PNyXnXedS-pMA"

# Configure basic logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

async def test_workflow_execution():
    """Test PassiveExtractionWorkflow execution"""
    try:
        logger.info("🔍 Starting workflow execution test...")
        
        # Test import
        logger.info("📦 Testing import...")
        from tools.passive_extraction_workflow_latest import PassiveExtractionWorkflow
        logger.info("✅ Import successful")
        
        # Test instantiation
        logger.info("🏗️ Testing instantiation...")
        workflow = PassiveExtractionWorkflow()
        logger.info("✅ Instantiation successful")
        
        # Test run method call with minimal parameters
        logger.info("🚀 Testing run method...")
        
        # Configure browser mode
        os.environ["BROWSER_HEADED"] = "false"
        
        extraction_results = await workflow.run(
            supplier_name="www-poundwholesale-co-uk",
            supplier_url="https://www.poundwholesale.co.uk/",
            max_products_to_process=1,  # Minimal test
            max_products_per_category=1,
            max_analyzed_products=1,
            cache_supplier_data=True,
            force_config_reload=False,
            debug_smoke=True,  # Enable debug mode
            resume_from_last=False  # Start fresh
        )
        
        logger.info(f"✅ Run method completed! Results: {type(extraction_results)}, Length: {len(extraction_results) if extraction_results else 'None'}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    print("="*80)
    print("PassiveExtractionWorkflow Debug Test")
    print("="*80)
    
    success = asyncio.run(test_workflow_execution())
    
    if success:
        print("✅ Workflow execution test PASSED")
        sys.exit(0)
    else:
        print("❌ Workflow execution test FAILED")
        sys.exit(1)