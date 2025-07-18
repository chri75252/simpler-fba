# In /tools/temp_integrated_workflow_runner.py

import asyncio
import logging
import os
import sys
from pathlib import Path

# --- Setup Project Paths ---
# This ensures all custom modules can be imported correctly
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools"))
sys.path.insert(0, str(project_root / "utils"))

# --- Import Required System Components ---
from tools.passive_extraction_workflow_latest import PassiveExtractionWorkflow
from tools.vision_login_handler import VisionLoginHandler
from openai import OpenAI

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("TempWorkflowRunner")

# --- Main Test Function ---
async def run_integrated_test():
    """
    This function orchestrates a temporary, integrated test run.
    It handles login and workflow execution in the correct sequence.
    """
    log.info("🚀 STARTING TEMPORARY INTEGRATED WORKFLOW TEST 🚀")
    
    # --- 1. Initialize Components ---
    log.info("Initializing components...")
    # Use a hardcoded API key or ensure the environment variable is set
    api_key = os.getenv("OPENAI_API_KEY", "YOUR_FALLBACK_API_KEY_HERE")
    if "FALLBACK" in api_key:
        log.warning("Using a fallback OpenAI API key.")
        
    ai_client = OpenAI(api_key=api_key)
    
    # Instantiate the main workflow. We will manually control its browser.
    workflow = PassiveExtractionWorkflow(ai_client=ai_client)
    
    # Instantiate the login handler
    login_handler = VisionLoginHandler(openai_client=ai_client, cdp_port=9222)

    try:
        # --- 2. Connect to the Browser (ONCE) ---
        log.info("Connecting to the shared browser instance...")
        # The login handler will connect and get the page object
        if not await login_handler.connect_browser():
            log.error("Failed to connect to browser. Aborting test.")
            return

        # The workflow will reuse this same browser connection
        workflow.extractor = login_handler.browser
        
        # --- 3. Perform Login (The "Quick Hack" Integration) ---
        log.info("Attempting to log in using the integrated handler...")
        login_result = await login_handler.perform_login()
        
        if not login_result.success:
            log.error(f"Login failed: {login_result.error_message}. Aborting workflow.")
            return
            
        log.info(f"✅ Login successful using method: {login_result.method_used}")
        
        # --- 4. Run the Main Workflow with the Authenticated Session ---
        log.info("Handing off authenticated session to the main PassiveExtractionWorkflow...")
        
        # The workflow will now run on the page that is already logged in
        # It will use the configuration from system_config.json as usual
        await workflow.run(
            supplier_url="https://www.poundwholesale.co.uk/",
            supplier_name="poundwholesale-co-uk",
            # Use the same test parameters as before
            max_products_to_process=15,
            max_analyzed_products=6,
            force_config_reload=True # Force a fresh scrape, ignoring the old cache
        )
        
        log.info("✅ Main workflow execution finished.")

    except Exception as e:
        log.critical(f"An unexpected error occurred during the test run: {e}", exc_info=True)
    finally:
        # --- 5. Cleanup ---
        log.info("Cleaning up resources...")
        if login_handler and login_handler.browser and login_handler.browser.is_connected():
            # We only need to close the connection from one handler, as it's a shared browser
            await login_handler.cleanup()
        log.info("🏁 TEST RUN COMPLETE 🏁")


# --- Entry Point ---
if __name__ == "__main__":
    # Ensure Chrome is running with the debug port open before running this script
    # Example: chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"
    asyncio.run(run_integrated_test())