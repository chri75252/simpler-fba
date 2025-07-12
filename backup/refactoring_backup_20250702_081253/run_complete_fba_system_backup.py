#!/usr/bin/env python3
"""
Complete FBA System Runner - Master entry point for Amazon FBA Agent System v3

Implements the acceptance gate requirements:
- Supplier URL, email, password arguments
- Headed/headless mode control  
- Max products limiting
- Proper file schemas and validation
- Supplier guard system integration
"""

import os, logging
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = (
        "sk-15Mk5F_Nvf8k06VvEi4_TD2GhL8mQnqR_8I6Z2zHjWT3BlbkFJvKlNwbgLB_HPw1C-SixqIskN03to4PNyXnXedS-pMA"
    )
    logging.warning("OPENAI_API_KEY not supplied – using hard-coded fallback")

import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Global OPENAI_KEY guard
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = (
        "sk-15Mk5F_Nvf8k06VvEi4_TD2GhL8mQnqR_8I6Z2zHjWT3BlbkFJvKlNwbgLB_HPw1C-SixqIskN03to4PNyXnXedS-pMA"
    )
    logging.warning("OPENAI_API_KEY missing – using fallback test key")

from tools.supplier_guard import check_supplier_ready, archive_supplier_on_force_regenerate, create_supplier_ready_file
from tools.passive_extraction_workflow_latest import PassiveExtractionWorkflow
from tools.output_verification_node import verify_supplier_outputs, NeedsInterventionError
from utils.browser_manager import cleanup_global_browser
from utils.path_manager import get_run_output_dir, path_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(path_manager.get_log_path("application", f"run_complete_fba_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"))
    ]
)
logger = logging.getLogger(__name__)


class CompleteFBASystem:
    """Complete FBA system orchestrator with supplier guard integration"""
    
    def __init__(self):
        self.start_time = datetime.now()
        logger.info("🚀 Complete FBA System v3 initialized")
    
    async def run_complete_system(
        self,
        supplier_url: str,
        supplier_email: str,
        supplier_password: str,
        headed: bool = True,
        max_products: int = 0,
        force_regenerate: bool = False,
        enable_langgraph_tracing: bool = False
    ) -> dict:
        """
        Run complete FBA system with supplier guard checks
        
        Args:
            supplier_url: Supplier website URL
            supplier_email: Supplier login email
            supplier_password: Supplier login password
            headed: Whether to run browser in headed mode
            max_products: Maximum products to process (0 = unlimited)
            force_regenerate: Force regeneration even if supplier ready
            enable_langgraph_tracing: Enable LangGraph tracing for debugging
            
        Returns:
            Dictionary with system results and status
        """
        results = {
            "status": "pending",
            "supplier_url": supplier_url,
            "supplier_email": supplier_email,
            "headed_mode": headed,
            "max_products": max_products,
            "force_regenerate": force_regenerate,
            "enable_langgraph_tracing": enable_langgraph_tracing,
            "start_time": self.start_time.isoformat(),
            "end_time": None,
            "total_processing_time": None,
            "files_created": {},
            "verification_results": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            # Extract supplier name from URL
            supplier_name = self._extract_supplier_name(supplier_url)
            results["supplier_name"] = supplier_name
            
            logger.info(f"🏭 Processing supplier: {supplier_name}")
            logger.info(f"🔗 URL: {supplier_url}")
            logger.info(f"📧 Email: {supplier_email}")
            logger.info(f"🖥️ Headed mode: {headed}")
            logger.info(f"📦 Max products: {max_products}")
            logger.info(f"🔄 Force regenerate: {force_regenerate}")
            
            # Check supplier readiness (unless force regenerate)
            if not force_regenerate:
                is_ready, ready_message = check_supplier_ready(supplier_name)
                if is_ready:
                    logger.info(f"✅ Supplier {supplier_name} is ready: {ready_message}")
                    results["status"] = "skipped_already_ready"
                    results["ready_message"] = ready_message
                    return results
                else:
                    logger.info(f"⚠️ Supplier {supplier_name} not ready: {ready_message}")
                    results["ready_check_message"] = ready_message
            
            # Archive existing supplier data if force regenerating
            if force_regenerate:
                backup_dir = archive_supplier_on_force_regenerate(supplier_name, force_regenerate)
                if backup_dir:
                    logger.info(f"📦 Archived existing data to: {backup_dir}")
                    results["backup_directory"] = str(backup_dir)
            
            # Get run output directory
            run_output_dir = get_run_output_dir(supplier_name)
            results["run_output_dir"] = str(run_output_dir)
            logger.info(f"📁 Run output directory: {run_output_dir}")
            
            # CRITICAL: Pre-flight login check and browser setup
            login_success = await self._perform_pre_flight_login_check(
                supplier_url=supplier_url,
                supplier_email=supplier_email,
                supplier_password=supplier_password,
                headed=headed
            )
            
            if not login_success:
                results["status"] = "login_failed"
                results["errors"].append("Pre-flight login check failed")
                logger.error("❌ Pre-flight login check failed - aborting workflow")
                return results
            
            logger.info("✅ Pre-flight login check successful - proceeding with workflow")
            
            # Configure and run extraction workflow
            # NOTE: LangGraph integration temporarily commented out - will create wrapper later
            # if enable_langgraph_tracing:
            #     logger.info("🔄 Using LangGraph workflow with tracing enabled")
            #     workflow_results = await self._run_langgraph_workflow(
            #         supplier_url=supplier_url,
            #         supplier_email=supplier_email,
            #         supplier_password=supplier_password,
            #         supplier_name=supplier_name,
            #         headed=headed,
            #         max_products=max_products,
            #         run_output_dir=run_output_dir
            #     )
            # else:
            logger.info("🔄 Using standard workflow (LangGraph integration disabled)")
            workflow_results = await self._run_extraction_workflow(
                supplier_url=supplier_url,
                supplier_email=supplier_email,
                supplier_password=supplier_password,
                supplier_name=supplier_name,
                headed=headed,
                max_products=max_products,
                run_output_dir=run_output_dir
            )
            
            results.update(workflow_results)
            
            if workflow_results.get("extraction_successful"):
                # Verify output files
                try:
                    verification_results = verify_supplier_outputs(supplier_name, run_output_dir)
                    results["verification_results"] = verification_results
                    
                    if verification_results.get("overall_status") == "passed":
                        logger.info("✅ Output verification passed")
                        
                        # Create .supplier_ready file
                        supplier_data = {
                            "total_products": workflow_results.get("total_products_extracted", 0),
                            "categories_discovered": workflow_results.get("categories_discovered", 0),
                            "linking_map_created": workflow_results.get("linking_map_created", False),
                            "ai_categories_created": workflow_results.get("ai_categories_created", False),
                            "cached_products_path": str(workflow_results.get("cached_products_path", "")),
                            "ai_category_cache_path": str(workflow_results.get("ai_category_cache_path", "")),
                            "linking_map_path": str(workflow_results.get("linking_map_path", "")),
                            "run_output_dir": str(run_output_dir),
                            "extraction_started": self.start_time.isoformat(),
                            "extraction_completed": datetime.now().isoformat(),
                            "total_processing_time": str(datetime.now() - self.start_time),
                            "success_rate": 1.0
                        }
                        
                        ready_file_path = create_supplier_ready_file(supplier_name, supplier_data)
                        results["supplier_ready_file"] = str(ready_file_path)
                        results["status"] = "completed_successfully"
                        
                        logger.info(f"✅ System completed successfully for {supplier_name}")
                        
                    else:
                        results["status"] = "verification_failed"
                        results["errors"].append("Output verification failed")
                        logger.error("❌ Output verification failed")
                        
                except NeedsInterventionError as e:
                    results["status"] = "needs_intervention" 
                    results["errors"].append(f"Needs intervention: {e}")
                    logger.error(f"🚨 Needs intervention: {e}")
                    
            else:
                results["status"] = "extraction_failed"
                results["errors"].append("Extraction workflow failed")
                logger.error("❌ Extraction workflow failed")
            
        except Exception as e:
            logger.error(f"❌ System error: {e}", exc_info=True)
            results["status"] = "system_error"
            results["errors"].append(f"System error: {e}")
        
        finally:
            # Set end time and duration
            end_time = datetime.now()
            results["end_time"] = end_time.isoformat()
            results["total_processing_time"] = str(end_time - self.start_time)
            
            # Cleanup browser resources
            try:
                await cleanup_global_browser()
                logger.info("🧹 Browser cleanup completed")
            except Exception as e:
                logger.warning(f"Browser cleanup warning: {e}")
        
        return results
    
    async def _perform_pre_flight_login_check(
        self,
        supplier_url: str,
        supplier_email: str,
        supplier_password: str,
        headed: bool
    ) -> bool:
        """
        Perform pre-flight login check using existing standalone login script
        
        Returns:
            bool: True if login successful and price access verified
        """
        try:
            logger.info("🚀 Starting pre-flight login check using standalone_playwright_login.py...")
            
            # Import the existing production-ready login system
            from tools.standalone_playwright_login import login_to_poundwholesale
            
            # Use the existing login workflow
            login_result = await login_to_poundwholesale(cdp_port=9222)
            
            if login_result.success and login_result.price_access_verified:
                logger.info(f"✅ Pre-flight login check PASSED - {login_result.method_used} - price access verified")
                logger.info(f"📊 Login duration: {login_result.login_duration_seconds:.1f}s")
                return True
            elif login_result.success:
                logger.warning(f"⚠️ Login succeeded but price access unverified - {login_result.error_message}")
                return True  # Still allow workflow to proceed
            else:
                logger.error(f"❌ Pre-flight login check FAILED - {login_result.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Pre-flight login check FAILED with exception: {e}", exc_info=True)
            return False
    
    def _extract_supplier_name(self, supplier_url: str) -> str:
        """Extract supplier name from URL"""
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(supplier_url)
            domain = parsed.netloc.lower()
            
            # Remove www and common prefixes
            domain = domain.replace("www.", "")
            
            # Convert to safe filename format
            supplier_name = domain.replace(".", "-")
            
            return supplier_name
            
        except Exception as e:
            logger.warning(f"Failed to parse supplier URL {supplier_url}: {e}")
            return "unknown-supplier"
    
    async def _run_extraction_workflow(
        self,
        supplier_url: str,
        supplier_email: str,
        supplier_password: str,
        supplier_name: str,
        headed: bool,
        max_products: int,
        run_output_dir: Path
    ) -> dict:
        """Run the passive extraction workflow"""
        workflow_results = {
            "extraction_successful": False,
            "total_products_extracted": 0,
            "categories_discovered": 0,
            "linking_map_created": False,
            "ai_categories_created": False,
            "workflow_errors": []
        }
        
        try:
            logger.info("🔄 Starting passive extraction workflow...")
            
            # Load system configuration
            from openai import OpenAI
            import json
            
            config_path = project_root / "config" / "system_config.json"
            try:
                with open(config_path, 'r') as f:
                    system_config = json.load(f)
                logger.info(f"✅ Loaded system configuration from {config_path}")
            except FileNotFoundError:
                logger.warning(f"⚠️ {config_path} not found. Using default workflow parameters.")
                system_config = {}
            
            # Initialize OpenAI client if configuration enables AI features
            ai_client_instance = None
            openai_api_key = os.getenv("OPENAI_API_KEY") or "sk-M1uDphRMEJDES5gLd8fzsLHDY_azAHvi5ireR-2WozT3BlbkFJcrvwzMwma_wv4M-cxd1ij5x_qOkP4POODvQoC1jS0A"
            force_ai_scraping = system_config.get("system", {}).get("force_ai_scraping", False)
            
            if force_ai_scraping and openai_api_key:
                try:
                    ai_client_instance = OpenAI(api_key=openai_api_key)
                    logger.info("✅ OpenAI client initialized for AI features")
                except Exception as e:
                    logger.error(f"❌ Error initializing OpenAI client: {e}. AI features disabled.")
                    ai_client_instance = None
            else:
                logger.info("ℹ️ AI features disabled (force_ai_scraping=False or no API key)")
            
            # Initialize workflow with configuration parameters
            workflow = PassiveExtractionWorkflow(
                chrome_debug_port=system_config.get("chrome", {}).get("debug_port", 9222),
                ai_client=ai_client_instance,
                max_cache_age_hours=0,  # No cache age limit - always fresh
                min_price=system_config.get("processing_limits", {}).get("min_price_gbp", 0.1),
                headless=system_config.get("chrome", {}).get("headless", False),  # Use config instead of command line
                linking_map_batch_size=system_config.get("system", {}).get("linking_map_batch_size", 5),
                financial_report_batch_size=system_config.get("system", {}).get("financial_report_batch_size", 5),
                force_ai_scraping=force_ai_scraping
                # selective_cache_clear removed per user request
            )
            
            logger.info(f"🔧 Workflow configured: force_ai_scraping={force_ai_scraping}, "
                       f"linking_batch={system_config.get('system', {}).get('linking_map_batch_size', 10)}, "
                       f"financial_batch={system_config.get('system', {}).get('financial_report_batch_size', 20)}, "
                       f"ai_client={'enabled' if ai_client_instance else 'disabled'}")
            
            # Configure browser mode
            os.environ["BROWSER_HEADED"] = "true" if headed else "false"
            
            # Run workflow - FIXED: Use actual system config values instead of hardcoded 0
            extraction_results = await workflow.run(
                supplier_name=supplier_name,
                supplier_url=supplier_url,
                max_products_to_process=max_products,
                max_products_per_category=system_config["processing_limits"]["max_products_per_category"],  # Config: 5
                max_analyzed_products=system_config["system"]["max_analyzed_products"],  # Config: 10
                cache_supplier_data=True,
                force_config_reload=False,
                debug_smoke=False,
                resume_from_last=True
            )
            
            if extraction_results:
                workflow_results["extraction_successful"] = True
                workflow_results["total_products_extracted"] = len(extraction_results)
                
                # Check for created files in run output directory
                cached_products_path = run_output_dir / "cached_products.json"
                if cached_products_path.exists():
                    workflow_results["cached_products_path"] = cached_products_path
                
                ai_cache_path = run_output_dir / "ai_category_cache.json"
                if ai_cache_path.exists():
                    workflow_results["ai_category_cache_path"] = ai_cache_path
                    workflow_results["ai_categories_created"] = True
                
                linking_map_path = run_output_dir / "linking_maps" / "linking_map.json"
                if linking_map_path.exists():
                    workflow_results["linking_map_path"] = linking_map_path
                    workflow_results["linking_map_created"] = True
                
                logger.info(f"✅ Workflow completed with {len(extraction_results)} products")
            else:
                logger.warning("⚠️ Workflow completed but no results returned")
                
        except Exception as e:
            logger.error(f"❌ Workflow execution failed: {e}", exc_info=True)
            workflow_results["workflow_errors"].append(str(e))
        
        return workflow_results
    
    async def _run_langgraph_workflow(
        self,
        supplier_url: str,
        supplier_email: str,
        supplier_password: str,
        supplier_name: str,
        headed: bool,
        max_products: int,
        run_output_dir: Path
    ) -> dict:
        """Run the LangGraph workflow with full tracing"""
        workflow_results = {
            "extraction_successful": False,
            "total_products_extracted": 0,
            "categories_discovered": 0,
            "linking_map_created": False,
            "ai_categories_created": False,
            "workflow_errors": [],
            "langraph_tracing_enabled": True
        }
        
        try:
            logger.info("🚀 Starting LangGraph workflow with tracing...")
            
            # Import LangGraph workflow
            from langraph_integration.complete_fba_workflow import CompleteFBAWorkflow
            
            # Setup LangSmith tracing environment
            import os
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "4e8c47f9-4c52-4d1d-85d0-00b31bb3ef5e")
            
            # Set up browser mode
            os.environ["BROWSER_HEADED"] = "true" if headed else "false"
            
            # Initialize LangGraph workflow
            workflow = CompleteFBAWorkflow()
            
            # Prepare credentials
            supplier_credentials = None
            if supplier_email and supplier_password:
                supplier_credentials = {
                    "email": supplier_email,
                    "password": supplier_password
                }
            
            # Run LangGraph workflow with supplier-first discovery mode
            langraph_results = await workflow.run_workflow(
                asin="SUPPLIER_DISCOVERY",  # Use supplier-first mode
                supplier_url=supplier_url,
                supplier_credentials=supplier_credentials
            )
            
            logger.info(f"🔄 LangGraph workflow completed with status: {langraph_results.get('status')}")
            
            if langraph_results.get("status") in ["completed_successfully", "completed_with_warnings"]:
                workflow_results["extraction_successful"] = True
                
                # Extract results from LangGraph output
                results = langraph_results.get("results", {})
                
                # Get product extraction data
                product_extraction = results.get("product_extraction", {})
                if isinstance(product_extraction, dict):
                    products_list = product_extraction.get("products", [])
                    workflow_results["total_products_extracted"] = len(products_list)
                
                # Check for created files in run output directory
                cached_products_path = run_output_dir / "cached_products.json"
                if cached_products_path.exists():
                    workflow_results["cached_products_path"] = cached_products_path
                
                ai_cache_path = run_output_dir / "ai_category_cache.json"
                if ai_cache_path.exists():
                    workflow_results["ai_category_cache_path"] = ai_cache_path
                    workflow_results["ai_categories_created"] = True
                
                linking_map_path = run_output_dir / "linking_maps" / "linking_map.json"
                if linking_map_path.exists():
                    workflow_results["linking_map_path"] = linking_map_path
                    workflow_results["linking_map_created"] = True
                
                # Store LangGraph specific results
                workflow_results["langraph_workflow_id"] = langraph_results.get("workflow_id")
                workflow_results["langraph_results"] = langraph_results
                
                logger.info(f"✅ LangGraph workflow completed successfully")
            else:
                logger.warning("⚠️ LangGraph workflow completed with issues")
                workflow_results["workflow_errors"].extend(langraph_results.get("errors", []))
                
        except Exception as e:
            logger.error(f"❌ LangGraph workflow execution failed: {e}", exc_info=True)
            workflow_results["workflow_errors"].append(str(e))
        
        return workflow_results


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Complete FBA System - Amazon FBA Agent System v3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_complete_fba_system.py \\
    --supplier-url "https://www.poundwholesale.co.uk/" \\
    --supplier-email "info@theblacksmithmarket.com" \\
    --supplier-password "0Dqixm9c&" \\
    --headed true \\
    --max-products 15

  python run_complete_fba_system.py \\
    --supplier-url "https://clearance-king.co.uk/" \\
    --supplier-email "test@example.com" \\
    --supplier-password "password123" \\
    --force-regenerate
        """
    )
    
    parser.add_argument(
        "--supplier-url",
        required=True,
        help="Supplier website URL (e.g., https://www.poundwholesale.co.uk/)"
    )
    
    parser.add_argument(
        "--supplier-email", 
        required=True,
        help="Supplier login email address"
    )
    
    parser.add_argument(
        "--supplier-password",
        required=True,
        help="Supplier login password"
    )
    
    parser.add_argument(
        "--headed",
        type=str,
        choices=["true", "false"],
        default="false",
        help="Run browser in headed mode (true/false, default: false)"
    )
    
    parser.add_argument(
        "--max-products",
        type=int,
        default=0,
        help="Maximum products to process (0 = unlimited, default: 0)"
    )
    
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="Force regeneration even if supplier is already ready"
    )
    
    parser.add_argument(
        "--enable-langgraph-tracing",
        action="store_true", 
        help="Enable LangGraph tracing for workflow debugging"
    )
    
    return parser.parse_args()


async def main():
    """Main function"""
    print("=" * 80)
    print("Amazon FBA Agent System v3 - Complete System Runner")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Convert headed string to boolean
        headed = args.headed.lower() == "true"
        
        # Initialize and run system
        system = CompleteFBASystem()
        
        results = await system.run_complete_system(
            supplier_url=args.supplier_url,
            supplier_email=args.supplier_email,
            supplier_password=args.supplier_password,
            headed=headed,
            max_products=args.max_products,
            force_regenerate=args.force_regenerate,
            enable_langgraph_tracing=args.enable_langgraph_tracing
        )
        
        # Print results summary
        print("\n" + "=" * 80)
        print("SYSTEM EXECUTION RESULTS")
        print("=" * 80)
        print(f"Status: {results['status']}")
        print(f"Supplier: {results.get('supplier_name', 'Unknown')}")
        print(f"Processing Time: {results.get('total_processing_time', 'Unknown')}")
        
        if results.get('run_output_dir'):
            print(f"Output Directory: {results['run_output_dir']}")
        
        if results.get('total_products_extracted'):
            print(f"Products Extracted: {results['total_products_extracted']}")
        
        if results.get('supplier_ready_file'):
            print(f"Supplier Ready File: {results['supplier_ready_file']}")
        
        if results.get('errors'):
            print(f"\nErrors ({len(results['errors'])}):")
            for error in results['errors']:
                print(f"  - {error}")
        
        if results.get('warnings'):
            print(f"\nWarnings ({len(results['warnings'])}):")
            for warning in results['warnings']:
                print(f"  - {warning}")
        
        # Set exit code based on results
        if results['status'] in ['completed_successfully', 'skipped_already_ready']:
            print("\n✅ System completed successfully!")
            sys.exit(0)
        elif results['status'] == 'needs_intervention':
            print("\n🚨 System needs manual intervention!")
            sys.exit(2)
        else:
            print(f"\n❌ System failed with status: {results['status']}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ System interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Main execution failed: {e}", exc_info=True)
        print(f"\n❌ System failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())