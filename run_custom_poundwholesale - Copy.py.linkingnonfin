import asyncio
import logging
import sys
import os

# Add project root to Python path to resolve module imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.async_api import async_playwright
from config.system_config_loader import SystemConfigLoader
from tools.standalone_playwright_login import StandalonePlaywrightLogin
from tools.passive_extraction_workflow_latest import PassiveExtractionWorkflow
from tools.supplier_authentication_service import SupplierAuthenticationService
from utils.logger import setup_logger
from utils.browser_manager import BrowserManager

async def main():
    """Main function to run the custom extraction workflow."""
    print("--- Starting Custom Pound Wholesale Extraction Workflow ---")
    
    # Setup logging
    debug_log_file = setup_logger()
    log = logging.getLogger(__name__)
    log.info(f"📋 Debug log file: {debug_log_file}")
    log.debug("Debug logging initialized - full system execution details will be captured")

    config_loader = SystemConfigLoader()
    workflow_config = config_loader.get_workflow_config('poundwholesale_workflow')
    supplier_name = workflow_config.get('supplier_name', 'poundwholesale.co.uk')
    credentials = config_loader.get_credentials(supplier_name)
    chrome_debug_port = config_loader.get_system_config().get('chrome_debug_port', 9222)

    browser_manager = None
    try:
        browser_manager = BrowserManager.get_instance()
        await browser_manager.launch_browser(cdp_port=chrome_debug_port)
        page = await browser_manager.get_page()

        supplier_url = workflow_config.get('supplier_url', f"https://{supplier_name}")
        supplier_config_path = os.path.join("config", "supplier_configs", f"{supplier_name}.json")

        log.info(f"🔐 Initializing authentication service for logout detection...")
        auth_service = SupplierAuthenticationService(browser_manager)

        if not credentials:
            log.error(f"🚨 Credentials for {supplier_name} not found in config. Exiting.")
            return

        log.info(f"✅ Using hardcoded credentials for {supplier_name}")
        
        log.info(f"🌐 Connecting to existing Chrome debug port {chrome_debug_port} for authentication...")

        authenticated = await auth_service.ensure_authenticated_session(page, credentials)
        if not authenticated:
            log.error("Authentication failed. Exiting workflow.")
            return

        # Pass the single browser manager instance to the workflow
        workflow = PassiveExtractionWorkflow(
            config_loader=config_loader,
            workflow_config=workflow_config,
            browser_manager=browser_manager
        )
        await workflow.run()

    except Exception as e:
        log.critical(f"💥 A critical error occurred in the main workflow: {e}", exc_info=True)
    finally:
        if browser_manager:
            # Keep browser persistent - only close pages, not the browser itself
            log.info("🌐 Keeping browser persistent for next run - not closing browser")
            # No browser cleanup to maintain persistence
        print("--- Custom Pound Wholesale Extraction Workflow Finished ---")

if __name__ == "__main__":
    # Ensure the event loop is created and set for the main thread
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user. Shutting down gracefully.")