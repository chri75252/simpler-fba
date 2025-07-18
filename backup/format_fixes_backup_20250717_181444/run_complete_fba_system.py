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
from typing import Optional, Any

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
from utils.browser_manager import global_cleanup
from utils.path_manager import get_run_output_dir, path_manager
import shutil

# Configure enhanced detailed logging system to match test_run_1.log format
def setup_detailed_logging():
    """Setup comprehensive logging system with component-level detail"""
    # Create detailed log file path
    log_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    detailed_log_path = path_manager.get_log_path("debug", f"run_complete_fba_system_{log_timestamp}.log")
    
    # Configure root logger for detailed output
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create detailed formatter matching test_run_1.log
    detailed_formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    
    # Console handler for user feedback
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Detailed file handler for comprehensive debugging
    file_handler = logging.FileHandler(detailed_log_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # 🚨 FIX: Suppress OpenAI debug logs to prevent huge HTML content blocks
    openai_logger = logging.getLogger('openai')
    openai_logger.setLevel(logging.INFO)  # Suppress DEBUG logs from OpenAI client
    
    # Configure component-specific loggers to match test_run_1.log
    component_loggers = [
        'configurable_supplier_scraper',
        'tools.passive_extraction_workflow_latest',
        'utils.browser_manager',
        'tools.supplier_authentication_service',
        'vision_login_handler',
        'suppliers.poundwholesale-co-uk.scripts.poundwholesale-co-uk_login'
    ]
    
    for logger_name in component_loggers:
        component_logger = logging.getLogger(logger_name)
        component_logger.setLevel(logging.DEBUG)
        component_logger.propagate = True
    
    return detailed_log_path

# Setup enhanced logging
detailed_log_path = setup_detailed_logging()
logger = logging.getLogger(__name__)
logger.info(f"🔍 Enhanced detailed logging enabled - output: {detailed_log_path}")


class CompleteFBASystem:
    """Complete FBA system orchestrator with supplier guard integration"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.archived_files = {}
        self.system_config = self._load_system_config()
        logger.info("🚀 Complete FBA System v3 initialized")
    
    def _load_system_config(self) -> dict:
        """Load system configuration to check toggles"""
        try:
            import json
            config_path = Path("config/system_config.json")
            with open(config_path, 'r') as f:
                content = f.read()
            
            # Use JSONDecoder to parse only the first valid JSON object
            # This handles the "Extra data" issue in system_config.json
            decoder = json.JSONDecoder()
            config, _ = decoder.raw_decode(content)
            return config
        except Exception as e:
            logger.warning(f"Failed to load system config: {e}, using defaults")
            return {"system": {"archive_system": False, "max_products": 0}}  # Default to disabled for testing
    
    def archive_expected_output_files(self, supplier_name: str) -> dict:
        """
        Archive expected output files based on the mode defined in system_config.json.
        Supports "full" and "specific_supplier" modes.
        """
        archive_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_base = Path(f"archive_pre_test_{archive_timestamp}")
        archive_base.mkdir(exist_ok=True)
        
        archived_files = {}
        expected_paths = []

        # Get archive configuration
        archive_config = self.system_config.get("system", {}).get("archive_system", {})
        archive_mode = archive_config.get("mode", "full") # Default to full reset for safety
        
        logger.info(f"Archive mode set to: '{archive_mode}'")

        # --- DYNAMIC PATH BUILDING LOGIC ---
        if archive_mode == "specific_supplier":
            target_supplier = archive_config.get("target_supplier")
            if not target_supplier:
                logger.error("Archive mode is 'specific_supplier' but no 'target_supplier' is defined in config. Aborting archive.")
                return {}
            
            logger.info(f"Performing a supplier-specific archive for: '{target_supplier}'")
            
            from utils.path_manager import path_manager
            base_output_dir = Path("OUTPUTS")

            expected_paths = [
                Path(f"suppliers/{target_supplier}"),
                Path(f"OUTPUTS/processing_states/{target_supplier.replace('.', '_')}_processing_state.json"),
                base_output_dir / "FBA_ANALYSIS" / "ai_category_cache" / f"{target_supplier}_ai_category_cache.json",
                base_output_dir / "FBA_ANALYSIS" / "linking_maps" / target_supplier,
                base_output_dir / "cached_products" / f"{target_supplier}_products_cache.json",
                base_output_dir / "FBA_ANALYSIS" / supplier_name, # Note: uses the current run's supplier_name for the run output dir
                base_output_dir / "FBA_ANALYSIS" / "financial_reports" / target_supplier
            ]

        elif archive_mode == "full":
            logger.info("Performing a full system archive.")
            expected_paths = [
                Path("suppliers"), # Archive all suppliers
                Path("OUTPUTS/FBA_ANALYSIS"),
                Path("OUTPUTS/cached_products"),
                Path("OUTPUTS/processing_states"),
                # Intentionally excluding logs/debug from automatic archiving
            ]
        
        else:
            logger.warning(f"Unknown archive mode: '{archive_mode}'. Skipping archive.")
            return {}

        # --- ARCHIVING EXECUTION (using the correct shutil.move) ---
        for path in expected_paths:
            if path.exists():
                archive_dest = archive_base / path.name
                try:
                    # Use shutil.move to ensure original is removed
                    shutil.move(str(path), str(archive_dest))
                    archived_files[str(path)] = {
                        "archived_to": str(archive_dest),
                        "archived_at": archive_timestamp,
                        "original_existed": True
                    }
                    logger.info(f"📦 Archived {path} to {archive_dest}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to archive {path}: {e}")
            else:
                archived_files[str(path)] = {
                    "archived_to": None,
                    "archived_at": archive_timestamp,
                    "original_existed": False
                }
                logger.info(f"📝 Noted non-existent path for verification: {path}")
        
        self.archived_files = archived_files
        logger.info(f"✅ Archive complete - {len(archived_files)} paths processed")
        return archived_files
    
    def verify_output_files_generated(self, supplier_name: str) -> dict:
        """Verify expected output files were generated with proper timestamps and content"""
        verification_results = {
            "verification_timestamp": datetime.now().isoformat(),
            "files_verified": {},
            "verification_success": True,
            "issues_found": []
        }
        
        # Expected output files to verify
        expected_files = [
            f"suppliers/{supplier_name}/config/login_config.json",
            f"suppliers/{supplier_name}/scripts/{supplier_name}_login.py",
            "OUTPUTS/FBA_ANALYSIS/cached_products.json",
            "OUTPUTS/FBA_ANALYSIS/ai_category_cache.json",
            "OUTPUTS/FBA_ANALYSIS/linking_maps/linking_map.json"
        ]
        
        for file_path in expected_files:
            path_obj = Path(file_path)
            file_verification = {
                "exists": path_obj.exists(),
                "timestamp": None,
                "size_bytes": None,
                "content_preview": None,
                "issues": []
            }
            
            if path_obj.exists():
                try:
                    stat_info = path_obj.stat()
                    file_verification["timestamp"] = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                    file_verification["size_bytes"] = stat_info.st_size
                    
                    # Verify timestamp is recent (within last 10 minutes)
                    file_age = datetime.now() - datetime.fromtimestamp(stat_info.st_mtime)
                    if file_age.total_seconds() > 600:
                        file_verification["issues"].append(f"File is old ({file_age}) - may not be from recent test")
                        verification_results["verification_success"] = False
                    
                    # Read and verify content for JSON files
                    if file_path.endswith('.json'):
                        try:
                            with open(path_obj, 'r', encoding='utf-8') as f:
                                content = f.read(500)  # First 500 chars
                                file_verification["content_preview"] = content
                                
                                # Verify it's valid JSON
                                f.seek(0)
                                import json
                                json.load(f)
                                
                                # Specific validation for login config
                                if "login_config.json" in file_path:
                                    if "vision_discovered" not in content:
                                        file_verification["issues"].append("Missing vision_discovered field")
                                        verification_results["verification_success"] = False
                                    if "auto_discovered" not in content:
                                        file_verification["issues"].append("Missing auto_discovered field")
                                        verification_results["verification_success"] = False
                                        
                        except Exception as e:
                            file_verification["issues"].append(f"Content verification failed: {e}")
                            verification_results["verification_success"] = False
                    
                    logger.info(f"✅ Verified {file_path}: {file_verification['size_bytes']} bytes, {file_verification['timestamp']}")
                    
                except Exception as e:
                    file_verification["issues"].append(f"File stat error: {e}")
                    verification_results["verification_success"] = False
                    logger.error(f"❌ Failed to verify {file_path}: {e}")
            else:
                file_verification["issues"].append("File does not exist")
                verification_results["verification_success"] = False
                logger.error(f"❌ Missing expected file: {file_path}")
            
            verification_results["files_verified"][file_path] = file_verification
            
            if file_verification["issues"]:
                verification_results["issues_found"].extend([
                    f"{file_path}: {issue}" for issue in file_verification["issues"]
                ])
        
        # Summary logging
        if verification_results["verification_success"]:
            logger.info(f"✅ Output verification PASSED - all {len(expected_files)} files verified")
        else:
            logger.error(f"❌ Output verification FAILED - {len(verification_results['issues_found'])} issues found")
            for issue in verification_results["issues_found"]:
                logger.error(f"  • {issue}")
        
        return verification_results
    
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
            
            # Archive expected output files before testing (if enabled)
            archive_enabled = self.system_config.get("system", {}).get("archive_system", False)
            if archive_enabled:
                logger.info("📦 Archiving expected output files for verification...")
                archived_files = self.archive_expected_output_files(supplier_name)
                results["archived_files"] = archived_files
            else:
                logger.info("📦 Archive system disabled - skipping file archiving")
                results["archived_files"] = {"archive_disabled": True}
            
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
            
            # Archive existing supplier data if force regenerating (if archive enabled)
            if force_regenerate:
                if archive_enabled:
                    backup_dir = archive_supplier_on_force_regenerate(supplier_name, force_regenerate)
                    if backup_dir:
                        logger.info(f"📦 Archived existing data to: {backup_dir}")
                        results["backup_directory"] = str(backup_dir)
                else:
                    logger.info("📦 Archive system disabled - skipping supplier data backup")
                    results["backup_directory"] = "archive_disabled"
            
            # Check and generate supplier automation package if needed
            from tools.supplier_script_generator import IntelligentSupplierScriptGenerator
            supplier_directory = Path(f"suppliers/{supplier_name}")
            
            if not supplier_directory.exists() or force_regenerate:
                logger.info(f"🔍 {'New supplier detected' if not supplier_directory.exists() else 'Force regenerate requested'}: {supplier_name}. Generating automation package...")
                generator = IntelligentSupplierScriptGenerator(supplier_url, force_regenerate)
                generation_results = await generator.generate_all_scripts()
                if not generation_results.get("success", False):
                    logger.error(f"❌ Failed to generate supplier automation package for {supplier_name}")
                    results["status"] = "supplier_generation_failed"
                    results["errors"].append("Intelligent supplier script generation failed")
                    return results
                logger.info(f"✅ Intelligent supplier automation package generated successfully for {supplier_name}")
            else:
                logger.info(f"✅ Existing supplier package found for {supplier_name}. Bypassing script generation.")
            
            # Initialize centralized browser session and perform dynamic supplier authentication
            from utils.browser_manager import get_page_for_url, global_cleanup
            import importlib.util
            
            authenticated_page = None
            try:
                logger.info("🚀 Initializing centralized browser session...")
                authenticated_page = await get_page_for_url(supplier_url, reuse_existing=True)
                if not authenticated_page:
                    raise Exception("Failed to get a browser page from the manager.")
                
                logger.info("🔐 Performing dynamic supplier authentication...")
                
                # Dynamic import of supplier-specific login script
                supplier_script_path = Path(f"suppliers/{supplier_name}/scripts/{supplier_name}_login.py")
                
                if supplier_script_path.exists():
                    logger.info(f"📦 Loading dynamic supplier login script: {supplier_script_path}")
                    
                    # Import the supplier-specific login module
                    spec = importlib.util.spec_from_file_location(f"{supplier_name}_login", supplier_script_path)
                    if spec and spec.loader:
                        supplier_login_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(supplier_login_module)
                        
                        # Call the supplier-specific login function
                        login_successful = False
                        
                        if hasattr(supplier_login_module, 'perform_login'):
                            credentials = {"email": supplier_email, "password": supplier_password}
                            login_successful = await supplier_login_module.perform_login(authenticated_page, credentials)
                        else:
                            # Try class-based approach (new format)
                            class_name = f"{supplier_name.replace('-', '_').title()}Login"
                            if hasattr(supplier_login_module, class_name):
                                login_class = getattr(supplier_login_module, class_name)
                                login_instance = login_class(supplier_email, supplier_password)
                                login_instance.page = authenticated_page
                                login_result = await login_instance.perform_login()
                                login_successful = login_result.get('success', False)
                            else:
                                logger.error(f"❌ Login script {supplier_script_path} missing 'perform_login' function or class")
                                results["status"] = "authentication_failed"
                                results["errors"].append("Invalid supplier login script - missing perform_login function or class")
                                await global_cleanup()
                                return results
                        
                        if not login_successful:
                            logger.error("❌ Dynamic supplier authentication failed. Aborting workflow.")
                            results["status"] = "authentication_failed"
                            results["errors"].append("Dynamic supplier authentication failed")
                            await global_cleanup()
                            return results
                        
                        logger.info("✅ Dynamic supplier authentication successful. Proceeding with authenticated workflow.")
                        
                        # Now that authentication succeeded, create run output directory
                        run_output_dir = get_run_output_dir(supplier_name)
                        results["run_output_dir"] = str(run_output_dir)
                        logger.info(f"📁 Run output directory: {run_output_dir}")
                        
                    else:
                        logger.error(f"❌ Failed to load supplier login script: {supplier_script_path}")
                        results["status"] = "authentication_failed" 
                        results["errors"].append("Failed to load supplier login script")
                        await global_cleanup()
                        return results
                else:
                    logger.error(f"❌ Supplier login script not found: {supplier_script_path}")
                    logger.info("💡 Run supplier script generator to create login scripts")
                    results["status"] = "authentication_failed"
                    results["errors"].append(f"Supplier login script not found: {supplier_script_path}")
                    await global_cleanup()
                    return results
                
            except Exception as e:
                logger.error(f"❌ Browser setup or dynamic authentication failed: {e}", exc_info=True)
                results["status"] = "browser_setup_failed"
                results["errors"].append(f"Dynamic authentication error: {e}")
                if authenticated_page:
                    await global_cleanup()
                return results
            
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
                run_output_dir=run_output_dir,
                authenticated_page=authenticated_page
            )
            
            results.update(workflow_results)
            
            if workflow_results.get("extraction_successful"):
                # MANDATORY: Verify output files were generated with proper timestamps and content
                logger.info("🔍 Verifying output files were generated correctly...")
                file_verification_results = self.verify_output_files_generated(supplier_name)
                results["file_verification"] = file_verification_results
                
                # Original output verification
                try:
                    verification_results = verify_supplier_outputs(supplier_name, run_output_dir)
                    results["verification_results"] = verification_results
                    
                    # Check both file verification and schema verification
                    file_verification_passed = file_verification_results.get("verification_success", False)
                    schema_verification_passed = verification_results.get("overall_status") == "passed"
                    
                    if file_verification_passed and schema_verification_passed:
                        logger.info("✅ Complete output verification passed (files + schema)")
                        
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
                        if not file_verification_passed:
                            results["errors"].append("File verification failed")
                            logger.error("❌ File verification failed")
                        if not schema_verification_passed:
                            results["errors"].append("Schema verification failed")  
                            logger.error("❌ Schema verification failed")
                        
                except NeedsInterventionError as e:
                    results["status"] = "needs_intervention" 
                    results["errors"].append(f"Needs intervention: {e}")
                    logger.error(f"🚨 Needs intervention: {e}")
                    
            else:
                results["status"] = "extraction_failed"
                results["errors"].append("Extraction workflow failed")
                logger.error("❌ Extraction workflow failed")
                
                # Even if extraction failed, verify what files were generated
                logger.info("🔍 Verifying files generated despite extraction failure...")
                file_verification_results = self.verify_output_files_generated(supplier_name)
                results["file_verification"] = file_verification_results
            
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
                await global_cleanup()
                logger.info("🧹 Browser cleanup completed")
            except Exception as e:
                logger.warning(f"Browser cleanup warning: {e}")
        
        return results
    
    
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
        run_output_dir: Path,
        authenticated_page: Optional[Any] = None
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
            
            # Initialize workflow with minimal parameters - testing params loaded from config
            workflow = PassiveExtractionWorkflow(
                ai_client=ai_client_instance
                # All other parameters (chrome_debug_port, linking_map_batch_size, etc.) 
                # will be loaded from system_config.json by the workflow
            )
            
            logger.info(f"🔧 Workflow configured: force_ai_scraping={force_ai_scraping}, "
                       f"linking_batch={system_config.get('system', {}).get('linking_map_batch_size', 10)}, "
                       f"financial_batch={system_config.get('system', {}).get('financial_report_batch_size', 20)}, "
                       f"ai_client={'enabled' if ai_client_instance else 'disabled'}")
            
            # Configure browser mode
            os.environ["BROWSER_HEADED"] = "true" if headed else "false"
            
            # Run workflow - supplier-specific parameters from config, CLI overrides allowed
            extraction_results = await workflow.run(
                supplier_name=supplier_name,
                supplier_url=supplier_url,
                max_products_to_process=max_products,  # CLI override if provided
                max_products_per_category=system_config.get("processing_limits", {}).get("max_products_per_category", 5),
                max_analyzed_products=system_config.get("system", {}).get("max_analyzed_products", 10),
                cache_supplier_data=True,
                force_config_reload=False,
                debug_smoke=False,
                resume_from_last=True,
                authenticated_page=authenticated_page
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
    
    # Load system config to get default max_products
    try:
        import json
        config_path = Path("config/system_config.json")
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Use JSONDecoder to parse only the first valid JSON object
        decoder = json.JSONDecoder()
        system_config, _ = decoder.raw_decode(content)
        default_max_products = system_config.get("system", {}).get("max_products", 0)
    except Exception as e:
        logger.warning(f"Failed to load max_products from config: {e}, using default 0")
        default_max_products = 0
    
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
        default=default_max_products,
        help=f"Maximum products to process (0 = unlimited, default: {default_max_products} from config)"
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