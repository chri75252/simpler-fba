import asyncio
import logging
import json
import os
from datetime import datetime
from tools.passive_extraction_workflow_latest import PassiveExtractionWorkflow
from tools.supplier_authentication_service import SupplierAuthenticationService

def setup_logging():
    """Setup comprehensive logging with debug file output"""
    try:
        # Create logs directory structure if it doesn't exist
        os.makedirs("logs/debug", exist_ok=True)
        
        # Generate timestamp for log filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_log_file = f"logs/debug/run_custom_poundwholesale_{timestamp}.log"
        
        # Clear any existing handlers to prevent conflicts
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # Configure root logger
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                # Console handler (INFO level)
                logging.StreamHandler(),
                # Debug file handler (DEBUG level)
                logging.FileHandler(debug_log_file, mode='w', encoding='utf-8')
            ],
            force=True  # Force reconfiguration
        )
        
        # Verify file was created
        with open(debug_log_file, 'a') as f:
            f.write(f"=== DEBUG LOG INITIALIZED: {timestamp} ===\n")
        
        print(f"✅ Debug logging initialized: {debug_log_file}")
        return debug_log_file
        
    except Exception as e:
        print(f"❌ Failed to setup logging: {e}")
        # Fallback to basic console logging
        logging.basicConfig(level=logging.INFO)
        return None

# Setup logging and get the debug log file path
debug_log_path = setup_logging()
log = logging.getLogger(__name__)

def load_config():
    """Load system configuration from config/system_config.json"""
    try:
        with open("config/system_config.json", 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        log.error("config/system_config.json not found. Please ensure the file exists.")
        return {}
    except json.JSONDecodeError:
        log.error("Error decoding config/system_config.json. Please ensure it is valid JSON.")
        return {}

async def main():
    """
    Simplified launcher for Pound Wholesale extraction workflow.
    Configuration and parameter logic handled entirely by the workflow.
    """
    log.info("--- Starting Custom Pound Wholesale Extraction Workflow ---")
    log.info(f"📋 Debug log file: {debug_log_path}")
    log.debug("Debug logging initialized - full system execution details will be captured")

    # Initialize authentication service for logout detection and login retry
    supplier_name = "poundwholesale.co.uk"
    supplier_url = "https://www.poundwholesale.co.uk/"
    
    log.info("🔐 Initializing authentication service for logout detection...")
    auth_service = SupplierAuthenticationService(
        supplier_name=supplier_name,
        supplier_url=supplier_url,
        config_path="config/supplier_configs/poundwholesale.co.uk.json"
    )
    
    # Check initial authentication state
    try:
        is_authenticated = await auth_service.check_authentication_status()
        if is_authenticated:
            log.info("✅ Authentication verified - ready to proceed")
        else:
            log.warning("⚠️ Not authenticated - will attempt login if needed during extraction")
    except Exception as e:
        log.warning(f"Authentication check failed: {e} - proceeding anyway")

    # Initialize workflow - configuration handled entirely within workflow
    workflow = PassiveExtractionWorkflow(ai_client=None)
    
    # Pass authentication service to workflow for logout detection
    workflow.auth_service = auth_service

    # Execute the main run method - workflow handles all parameter loading
    try:
        await workflow.run(
            supplier_name=supplier_name,
            supplier_url=supplier_url,
            use_predefined_categories=True
        )
    except Exception as e:
        log.error(f"Workflow execution failed: {e}")
        
        # Check if failure was due to authentication issues
        if "login" in str(e).lower() or "auth" in str(e).lower() or "session" in str(e).lower():
            log.warning("🔄 Possible authentication issue detected - attempting re-authentication...")
            try:
                login_success = await auth_service.authenticate()
                if login_success:
                    log.info("✅ Re-authentication successful - retrying workflow...")
                    await workflow.run(
                        supplier_name=supplier_name,
                        supplier_url=supplier_url,
                        use_predefined_categories=True
                    )
                else:
                    log.error("❌ Re-authentication failed - workflow cannot continue")
                    raise e
            except Exception as retry_error:
                log.error(f"Retry attempt failed: {retry_error}")
                raise e
        else:
            raise e

    log.info("--- Custom Pound Wholesale Extraction Workflow Finished ---")
    log.info(f"📋 Complete debug log available at: {debug_log_path}")
    log.debug("System execution completed - check debug log for detailed analysis")

if __name__ == "__main__":
    asyncio.run(main())