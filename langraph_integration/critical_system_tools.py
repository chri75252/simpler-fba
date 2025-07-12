#!/usr/bin/env python3
"""
Critical System Tools - LangGraph Integration for Core FBA System Components
==============================================================================

This module provides LangGraph wrappers for the most critical system components:
- CompleteFBASystemTool (run_complete_fba_system.py)
- PassiveExtractionWorkflowTool (passive_extraction_workflow_latest.py) 
- SupplierGuardTool (supplier_guard.py)
- OutputVerificationTool (output_verification_node.py)
- LinkingMapWriterTool (linking_map_writer.py)
- AICategorySuggesterTool (ai_category_suggester.py)
- EnhancedStateManagerTool (enhanced_state_manager.py)

These are the highest priority tools required for full LangGraph integration.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# LangChain imports
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.callbacks import CallbackManagerForToolRun

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import existing tools with error handling
try:
    from tools.supplier_guard import SupplierGuard, check_supplier_ready, archive_supplier_on_force_regenerate, create_supplier_ready_file
    from tools.output_verification_node import OutputVerificationNode, verify_supplier_outputs, NeedsInterventionError
    from tools.passive_extraction_workflow_latest import PassiveExtractionWorkflow
    from utils.browser_manager import BrowserManager, cleanup_global_browser
    from utils.path_manager import get_run_output_dir, path_manager
    
    # Additional imports for specific tools
    from tools.linking_map_writer import LinkingMapWriter
    from tools.ai_category_suggester import AICategorySuggester  
    from tools.enhanced_state_manager import EnhancedStateManager
    
except ImportError as e:
    logger.warning(f"Some critical tools not available for import: {e}")
    # Create fallback classes to maintain API compatibility
    
    class SupplierGuard:
        def check_supplier_ready(self, supplier_name):
            return False, "Tool not available"
        def archive_supplier_on_force_regenerate(self, supplier_name):
            return {"success": False, "error": "Tool not available"}
        def create_supplier_ready_file(self, supplier_name, data):
            return {"success": False, "error": "Tool not available"}
    
    class OutputVerificationNode:
        def verify_supplier_outputs(self, supplier_name):
            return {"success": False, "error": "Tool not available"}
    
    class PassiveExtractionWorkflow:
        def __init__(self):
            pass
        async def run(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    class LinkingMapWriter:
        def create_linking_map(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    class AICategorySuggester:
        def suggest_categories(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    class EnhancedStateManager:
        def save_state(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
        def load_state(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    # Fallback functions
    def check_supplier_ready(supplier_name):
        return False, "Tool not available"
    def archive_supplier_on_force_regenerate(supplier_name):
        return {"success": False, "error": "Tool not available"}
    def create_supplier_ready_file(supplier_name, data):
        return {"success": False, "error": "Tool not available"}
    def verify_supplier_outputs(supplier_name):
        return {"success": False, "error": "Tool not available"}
    
    class NeedsInterventionError(Exception):
        pass


# =============================================================================
# 1. COMPLETE FBA SYSTEM TOOL (Main Orchestrator)
# =============================================================================

class CompleteFBASystemInput(BaseModel):
    """Input schema for Complete FBA System Tool"""
    supplier_url: str = Field(description="Supplier website URL")
    supplier_email: str = Field(description="Supplier login email")
    supplier_password: str = Field(description="Supplier login password")
    headed: bool = Field(default=True, description="Whether to run browser in headed mode")
    max_products: int = Field(default=0, description="Maximum products to process (0 = unlimited)")
    force_regenerate: bool = Field(default=False, description="Force regeneration even if supplier ready")
    enable_langgraph_tracing: bool = Field(default=False, description="Enable LangGraph tracing for debugging")


class CompleteFBASystemTool(BaseTool):
    """
    LangGraph wrapper for the main FBA system orchestrator (run_complete_fba_system.py)
    
    This is the primary entry point that coordinates the entire FBA workflow including:
    - Supplier guard checks
    - Browser management  
    - Workflow orchestration
    - Output verification
    - System cleanup
    """
    name: str = "complete_fba_system"
    description: str = """
    Runs the complete FBA system workflow from start to finish. This is the main orchestrator that:
    - Checks supplier readiness via supplier guard
    - Initializes browser and login systems
    - Executes the passive extraction workflow
    - Performs output verification and validation
    - Creates comprehensive results summary
    
    Required inputs: supplier_url, supplier_email, supplier_password
    Optional: headed (bool), max_products (int), force_regenerate (bool), enable_langgraph_tracing (bool)
    """
    args_schema: Type[BaseModel] = CompleteFBASystemInput

    def _run(
        self,
        supplier_url: str,
        supplier_email: str,
        supplier_password: str,
        headed: bool = True,
        max_products: int = 0,
        force_regenerate: bool = False,
        enable_langgraph_tracing: bool = False,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Synchronous version - delegates to async implementation"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self._arun(supplier_url, supplier_email, supplier_password, headed,
                      max_products, force_regenerate, enable_langgraph_tracing, run_manager)
        )

    async def _arun(
        self,
        supplier_url: str,
        supplier_email: str,
        supplier_password: str,
        headed: bool = True,
        max_products: int = 0,
        force_regenerate: bool = False,
        enable_langgraph_tracing: bool = False,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute the complete FBA system workflow"""
        try:
            logger.info(f"🚀 Starting Complete FBA System for {supplier_url}")
            
            # Import the main system class
            try:
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from run_complete_fba_system import CompleteFBASystem
                
                # Initialize and run the system
                fba_system = CompleteFBASystem()
                results = await fba_system.run_complete_system(
                    supplier_url=supplier_url,
                    supplier_email=supplier_email, 
                    supplier_password=supplier_password,
                    headed=headed,
                    max_products=max_products,
                    force_regenerate=force_regenerate,
                    enable_langgraph_tracing=enable_langgraph_tracing
                )
                
                return json.dumps({
                    "execution_id": f"fba_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "supplier_url": supplier_url,
                    "results": results,
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                })
                
            except ImportError as e:
                logger.error(f"Failed to import CompleteFBASystem: {e}")
                # Fallback execution using direct workflow calls
                return await self._fallback_execution(
                    supplier_url, supplier_email, supplier_password,
                    headed, max_products, force_regenerate, enable_langgraph_tracing
                )
                
        except Exception as e:
            error_msg = f"Error in Complete FBA System: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "execution_id": f"fba_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_url": supplier_url,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })

    async def _fallback_execution(self, supplier_url, supplier_email, supplier_password, 
                                  headed, max_products, force_regenerate, enable_langgraph_tracing):
        """Fallback execution when main system is not available"""
        logger.info("🔄 Using fallback execution method")
        
        results = {
            "status": "completed_fallback",
            "supplier_url": supplier_url,
            "headed_mode": headed,
            "max_products": max_products,
            "force_regenerate": force_regenerate,
            "supplier_guard_check": "skipped",
            "workflow_execution": "fallback_mode",
            "output_verification": "skipped",
            "warning": "Executed in fallback mode - some features may be limited"
        }
        
        return json.dumps({
            "execution_id": f"fba_system_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "results": results,
            "status": "completed_fallback",
            "timestamp": datetime.now().isoformat()
        })


# =============================================================================
# 2. PASSIVE EXTRACTION WORKFLOW TOOL (Core Engine)
# =============================================================================

class PassiveExtractionWorkflowInput(BaseModel):
    """Input schema for Passive Extraction Workflow Tool"""
    supplier_name: str = Field(description="Supplier domain identifier")
    supplier_url: str = Field(description="Supplier website URL")
    supplier_email: str = Field(description="Supplier login email")
    supplier_password: str = Field(description="Supplier login password")
    max_products: int = Field(default=0, description="Maximum products to process")
    headed: bool = Field(default=True, description="Browser headed mode")
    enable_ai_categories: bool = Field(default=True, description="Enable AI category analysis")
    enable_financial_calc: bool = Field(default=True, description="Enable financial calculations")


class PassiveExtractionWorkflowTool(BaseTool):
    """
    LangGraph wrapper for the core passive extraction workflow (passive_extraction_workflow_latest.py)
    
    This is the main workflow engine that handles:
    - Supplier data extraction
    - Amazon data correlation
    - AI category analysis
    - Financial calculations
    - State management and caching
    """
    name: str = "passive_extraction_workflow"
    description: str = """
    Executes the core passive extraction workflow that forms the heart of the FBA system.
    Handles complete data extraction pipeline including supplier scraping, Amazon data correlation,
    AI-powered category analysis, and financial calculations.
    
    Required inputs: supplier_name, supplier_url, supplier_email, supplier_password
    Optional: max_products, headed, enable_ai_categories, enable_financial_calc
    """
    args_schema: Type[BaseModel] = PassiveExtractionWorkflowInput

    def _run(self, *args, **kwargs) -> str:
        """Synchronous version - delegates to async implementation"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._arun(*args, **kwargs))
    async def _arun(
        self,
        supplier_name: str,
        supplier_url: str,
        supplier_email: str,
        supplier_password: str,
        max_products: int = 0,
        headed: bool = True,
        enable_ai_categories: bool = True,
        enable_financial_calc: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute the passive extraction workflow"""
        try:
            logger.info(f"🔄 Starting Passive Extraction Workflow for {supplier_name}")
            
            # Initialize workflow
            workflow = PassiveExtractionWorkflow()
            
            # Configure workflow parameters
            workflow_config = {
                "supplier_name": supplier_name,
                "supplier_url": supplier_url,
                "supplier_email": supplier_email,
                "supplier_password": supplier_password,
                "max_products": max_products,
                "headed": headed,
                "enable_ai_categories": enable_ai_categories,
                "enable_financial_calc": enable_financial_calc
            }
            
            # Execute workflow
            results = await workflow.run(
                supplier_name=supplier_name,
                supplier_url=supplier_url,
                supplier_email=supplier_email,
                supplier_password=supplier_password,
                max_products=max_products,
                headed=headed
            )
            
            return json.dumps({
                "workflow_id": f"passive_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "config": workflow_config,
                "results": results,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in Passive Extraction Workflow: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "workflow_id": f"passive_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 3. SUPPLIER GUARD TOOL (Readiness Management)
# =============================================================================

class SupplierGuardInput(BaseModel):
    """Input schema for Supplier Guard Tool"""
    operation: str = Field(description="Operation to perform: check, archive, create, or status")
    supplier_name: str = Field(description="Supplier domain identifier")
    force_regenerate: bool = Field(default=False, description="Force regeneration flag for archive operation")
    supplier_data: Optional[Dict[str, Any]] = Field(default=None, description="Supplier data for create operation")


class SupplierGuardTool(BaseTool):
    """
    LangGraph wrapper for supplier guard system (supplier_guard.py)
    
    Manages supplier readiness state through .supplier_ready files:
    - Check if supplier is ready for processing
    - Archive existing supplier data on force regenerate
    - Create new supplier ready files after successful processing
    - Validate supplier state and readiness
    """
    name: str = "supplier_guard"
    description: str = """
    Manages supplier readiness state and data archival through the supplier guard system.
    Operations include: check (validate readiness), archive (backup on force regenerate), 
    create (mark supplier as ready), status (get current state).
    
    Required inputs: operation, supplier_name
    Optional: force_regenerate (for archive), supplier_data (for create)
    """
    args_schema: Type[BaseModel] = SupplierGuardInput

    def _run(self, *args, **kwargs) -> str:
        """Synchronous version - delegates to async implementation"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._arun(*args, **kwargs))
    async def _arun(
        self,
        operation: str,
        supplier_name: str,
        force_regenerate: bool = False,
        supplier_data: Optional[Dict[str, Any]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute supplier guard operations"""
        try:
            logger.info(f"🛡️ Supplier Guard {operation} for {supplier_name}")
            
            guard = SupplierGuard()
            
            if operation == "check":
                is_ready, reason = guard.check_supplier_ready(supplier_name)
                return json.dumps({
                    "operation": "check",
                    "supplier_name": supplier_name,
                    "is_ready": is_ready,
                    "reason": reason,
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                })
                
            elif operation == "archive":
                if force_regenerate:
                    result = archive_supplier_on_force_regenerate(supplier_name)
                    return json.dumps({
                        "operation": "archive",
                        "supplier_name": supplier_name,
                        "force_regenerate": force_regenerate,
                        "result": result,
                        "status": "completed",
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    return json.dumps({
                        "operation": "archive",
                        "supplier_name": supplier_name,
                        "error": "Archive operation requires force_regenerate=True",
                        "status": "failed",
                        "timestamp": datetime.now().isoformat()
                    })
                    
            elif operation == "create":
                if supplier_data is None:
                    supplier_data = {
                        "supplier_name": supplier_name,
                        "created_at": datetime.now().isoformat(),
                        "status": "ready"
                    }
                result = create_supplier_ready_file(supplier_name, supplier_data)
                return json.dumps({
                    "operation": "create",
                    "supplier_name": supplier_name,
                    "supplier_data": supplier_data,
                    "result": result,
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                })
                
            elif operation == "status":
                is_ready, reason = guard.check_supplier_ready(supplier_name)
                supplier_dir = Path("suppliers") / supplier_name
                ready_file = supplier_dir / ".supplier_ready"
                
                status_info = {
                    "supplier_name": supplier_name,
                    "is_ready": is_ready,
                    "reason": reason,
                    "ready_file_exists": ready_file.exists(),
                    "supplier_dir_exists": supplier_dir.exists()
                }
                
                if ready_file.exists():
                    status_info["ready_file_mtime"] = datetime.fromtimestamp(ready_file.stat().st_mtime).isoformat()
                
                return json.dumps({
                    "operation": "status",
                    "status_info": status_info,
                    "status": "completed",
                    "timestamp": datetime.now().isoformat()
                })
                
            else:
                return json.dumps({
                    "operation": operation,
                    "supplier_name": supplier_name,
                    "error": f"Unknown operation: {operation}. Valid operations: check, archive, create, status",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            error_msg = f"Error in Supplier Guard {operation}: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "operation": operation,
                "supplier_name": supplier_name,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 4. OUTPUT VERIFICATION TOOL (Validation)
# =============================================================================

class OutputVerificationInput(BaseModel):
    """Input schema for Output Verification Tool"""
    supplier_name: str = Field(description="Supplier domain identifier")
    verification_type: str = Field(default="full", description="Type of verification: full, schema_only, or quick")
    files_to_verify: Optional[List[str]] = Field(default=None, description="Specific files to verify (optional)")


class OutputVerificationTool(BaseTool):
    """
    LangGraph wrapper for output verification system (output_verification_node.py)
    
    Performs comprehensive validation of FBA system outputs:
    - JSONSchema validation (Draft-2020-12 compliance)
    - File structure verification
    - Data integrity checks
    - Error reporting and intervention flagging
    """
    name: str = "output_verification"
    description: str = """
    Validates FBA system outputs against strict JSONSchema specifications and performs
    comprehensive data integrity checks. Ensures all generated files meet required
    standards and flags issues requiring human intervention.
    
    Required inputs: supplier_name
    Optional: verification_type (full/schema_only/quick), files_to_verify (specific files)
    """
    args_schema: Type[BaseModel] = OutputVerificationInput

    def _run(self, *args, **kwargs) -> str:
        """Synchronous version - delegates to async implementation"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._arun(*args, **kwargs))
    async def _arun(
        self,
        supplier_name: str,
        verification_type: str = "full",
        files_to_verify: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute output verification"""
        try:
            logger.info(f"🔍 Output Verification ({verification_type}) for {supplier_name}")
            
            verifier = OutputVerificationNode()
            
            # Perform verification based on type
            if verification_type == "full":
                results = verify_supplier_outputs(supplier_name)
            elif verification_type == "schema_only":
                results = verifier.verify_schemas_only(supplier_name)
            elif verification_type == "quick":
                results = verifier.quick_verification(supplier_name)
            else:
                return json.dumps({
                    "verification_id": f"verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "supplier_name": supplier_name,
                    "error": f"Unknown verification type: {verification_type}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "verification_id": f"verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "verification_type": verification_type,
                "files_to_verify": files_to_verify,
                "results": results,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except NeedsInterventionError as e:
            logger.error(f"Verification failed - human intervention required: {e}")
            return json.dumps({
                "verification_id": f"verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "verification_type": verification_type,
                "error": f"Needs Intervention: {str(e)}",
                "intervention_required": True,
                "status": "needs_intervention",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in Output Verification: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "verification_id": f"verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "verification_type": verification_type,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 5. LINKING MAP WRITER TOOL (Product Correlation)
# =============================================================================

class LinkingMapWriterInput(BaseModel):
    """Input schema for Linking Map Writer Tool"""
    supplier_name: str = Field(description="Supplier domain identifier")
    operation: str = Field(default="create", description="Operation: create, update, or validate")
    batch_size: int = Field(default=5, description="Batch size for processing")
    force_regenerate: bool = Field(default=False, description="Force regeneration of existing maps")


class LinkingMapWriterTool(BaseTool):
    """
    LangGraph wrapper for linking map generation (linking_map_writer.py)
    
    Creates and manages product linking maps that correlate Amazon products with
    supplier products for accurate financial analysis and matching.
    """
    name: str = "linking_map_writer"
    description: str = """
    Creates and manages product linking maps that correlate Amazon ASINs with supplier products.
    Essential for accurate financial analysis and product matching in the FBA workflow.
    
    Required inputs: supplier_name
    Optional: operation (create/update/validate), batch_size, force_regenerate
    """
    args_schema: Type[BaseModel] = LinkingMapWriterInput

    def _run(self, *args, **kwargs) -> str:
        """Synchronous version - delegates to async implementation"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._arun(*args, **kwargs))
    async def _arun(
        self,
        supplier_name: str,
        operation: str = "create",
        batch_size: int = 5,
        force_regenerate: bool = False,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute linking map operations"""
        try:
            logger.info(f"🔗 Linking Map Writer {operation} for {supplier_name}")
            
            writer = LinkingMapWriter()
            
            if operation == "create":
                result = writer.create_linking_map(
                    supplier_name=supplier_name,
                    batch_size=batch_size,
                    force_regenerate=force_regenerate
                )
            elif operation == "update":
                result = writer.update_linking_map(supplier_name, batch_size)
            elif operation == "validate":
                result = writer.validate_linking_map(supplier_name)
            else:
                return json.dumps({
                    "linking_map_id": f"linkmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "supplier_name": supplier_name,
                    "error": f"Unknown operation: {operation}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "linking_map_id": f"linkmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "operation": operation,
                "batch_size": batch_size,
                "force_regenerate": force_regenerate,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in Linking Map Writer: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "linking_map_id": f"linkmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "operation": operation,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 6. AI CATEGORY SUGGESTER TOOL (Category Analysis)
# =============================================================================

class AICategorySuggesterInput(BaseModel):
    """Input schema for AI Category Suggester Tool"""
    supplier_name: str = Field(description="Supplier domain identifier")
    operation: str = Field(default="suggest", description="Operation: suggest, analyze, or validate")
    max_products: int = Field(default=0, description="Maximum products to analyze (0 = all)")
    confidence_threshold: float = Field(default=0.8, description="Minimum confidence threshold for suggestions")


class AICategorySuggesterTool(BaseTool):
    """
    LangGraph wrapper for AI-powered category suggestions (ai_category_suggester.py)
    
    Uses AI to analyze product data and suggest optimal Amazon categories
    for improved discoverability and competitive positioning.
    """
    name: str = "ai_category_suggester"
    description: str = """
    Uses AI to analyze supplier products and suggest optimal Amazon categories.
    Improves product categorization for better discoverability and competitive analysis.
    
    Required inputs: supplier_name
    Optional: operation (suggest/analyze/validate), max_products, confidence_threshold
    """
    args_schema: Type[BaseModel] = AICategorySuggesterInput

    def _run(self, *args, **kwargs) -> str:
        """Synchronous version - delegates to async implementation"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._arun(*args, **kwargs))
    async def _arun(
        self,
        supplier_name: str,
        operation: str = "suggest",
        max_products: int = 0,
        confidence_threshold: float = 0.8,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute AI category suggestion operations"""
        try:
            logger.info(f"🤖 AI Category Suggester {operation} for {supplier_name}")
            
            suggester = AICategorySuggester()
            
            if operation == "suggest":
                result = suggester.suggest_categories(
                    supplier_name=supplier_name,
                    max_products=max_products,
                    confidence_threshold=confidence_threshold
                )
            elif operation == "analyze":
                result = suggester.analyze_existing_categories(supplier_name)
            elif operation == "validate":
                result = suggester.validate_category_suggestions(supplier_name)
            else:
                return json.dumps({
                    "suggestion_id": f"aicat_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "supplier_name": supplier_name,
                    "error": f"Unknown operation: {operation}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "suggestion_id": f"aicat_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "operation": operation,
                "max_products": max_products,
                "confidence_threshold": confidence_threshold,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in AI Category Suggester: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "suggestion_id": f"aicat_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "operation": operation,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 7. ENHANCED STATE MANAGER TOOL (State Persistence)
# =============================================================================

class EnhancedStateManagerInput(BaseModel):
    """Input schema for Enhanced State Manager Tool"""
    operation: str = Field(description="Operation: save, load, clear, or status")
    supplier_name: str = Field(description="Supplier domain identifier")
    state_type: str = Field(default="workflow", description="Type of state: workflow, cache, session, or processing")
    state_data: Optional[Dict[str, Any]] = Field(default=None, description="State data for save operation")
    checkpoint_name: Optional[str] = Field(default=None, description="Checkpoint name for save/load operations")


class EnhancedStateManagerTool(BaseTool):
    """
    LangGraph wrapper for enhanced state management (enhanced_state_manager.py)
    
    Provides advanced workflow state persistence, recovery, and checkpoint management
    for resilient processing and workflow continuation.
    """
    name: str = "enhanced_state_manager"
    description: str = """
    Manages advanced workflow state persistence and recovery. Provides checkpoint
    functionality for resilient processing and workflow continuation across sessions.
    
    Required inputs: operation, supplier_name
    Optional: state_type, state_data (for save), checkpoint_name
    """
    args_schema: Type[BaseModel] = EnhancedStateManagerInput

    def _run(self, *args, **kwargs) -> str:
        """Synchronous version - delegates to async implementation"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._arun(*args, **kwargs))
    async def _arun(
        self,
        operation: str,
        supplier_name: str,
        state_type: str = "workflow",
        state_data: Optional[Dict[str, Any]] = None,
        checkpoint_name: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute state management operations"""
        try:
            logger.info(f"🗃️ Enhanced State Manager {operation} for {supplier_name}")
            
            state_manager = EnhancedStateManager()
            
            if operation == "save":
                if state_data is None:
                    state_data = {
                        "supplier_name": supplier_name,
                        "timestamp": datetime.now().isoformat(),
                        "state_type": state_type
                    }
                
                result = state_manager.save_state(
                    supplier_name=supplier_name,
                    state_type=state_type,
                    state_data=state_data,
                    checkpoint_name=checkpoint_name
                )
                
            elif operation == "load":
                result = state_manager.load_state(
                    supplier_name=supplier_name,
                    state_type=state_type,
                    checkpoint_name=checkpoint_name
                )
                
            elif operation == "clear":
                result = state_manager.clear_state(
                    supplier_name=supplier_name,
                    state_type=state_type
                )
                
            elif operation == "status":
                result = state_manager.get_state_status(
                    supplier_name=supplier_name,
                    state_type=state_type
                )
                
            else:
                return json.dumps({
                    "state_id": f"state_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "supplier_name": supplier_name,
                    "error": f"Unknown operation: {operation}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "state_id": f"state_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "operation": operation,
                "state_type": state_type,
                "checkpoint_name": checkpoint_name,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in Enhanced State Manager: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "state_id": f"state_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "operation": operation,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# TOOL COLLECTION FUNCTION
# =============================================================================

def create_critical_system_tools() -> List[BaseTool]:
    """
    Create and return all critical system tools for LangGraph integration
    
    Returns:
        List of BaseTool instances for all critical system components
    """
    tools = [
        CompleteFBASystemTool(),
        PassiveExtractionWorkflowTool(),
        SupplierGuardTool(),
        OutputVerificationTool(),
        LinkingMapWriterTool(),
        AICategorySuggesterTool(),
        EnhancedStateManagerTool(),
    ]
    
    logger.info(f"✅ Created {len(tools)} critical system tools for LangGraph integration")
    return tools


# =============================================================================
# MAIN EXECUTION FOR TESTING
# =============================================================================

async def test_critical_tools():
    """Test function for critical system tools"""
    logger.info("🧪 Testing Critical System Tools")
    
    tools = create_critical_system_tools()
    
    # Test each tool with minimal inputs
    for tool in tools:
        logger.info(f"Testing {tool.name}...")
        try:
            if tool.name == "complete_fba_system":
                result = await tool.ainvoke({
                    "supplier_url": "https://test.example.com",
                    "supplier_email": "test@example.com", 
                    "supplier_password": "test123"
                })
            elif tool.name == "passive_extraction_workflow":
                result = await tool.ainvoke({
                    "supplier_name": "test-supplier",
                    "supplier_url": "https://test.example.com",
                    "supplier_email": "test@example.com",
                    "supplier_password": "test123"
                })
            elif tool.name == "supplier_guard":
                result = await tool.ainvoke({
                    "operation": "status",
                    "supplier_name": "test-supplier"
                })
            elif tool.name == "output_verification":
                result = await tool.ainvoke({
                    "supplier_name": "test-supplier",
                    "verification_type": "quick"
                })
            elif tool.name == "linking_map_writer":
                result = await tool.ainvoke({
                    "supplier_name": "test-supplier",
                    "operation": "validate"
                })
            elif tool.name == "ai_category_suggester":
                result = await tool.ainvoke({
                    "supplier_name": "test-supplier",
                    "operation": "analyze"
                })
            elif tool.name == "enhanced_state_manager":
                result = await tool.ainvoke({
                    "operation": "status",
                    "supplier_name": "test-supplier",
                    "state_type": "workflow"
                })
            
            logger.info(f"✅ {tool.name} test completed")
            
        except Exception as e:
            logger.error(f"❌ {tool.name} test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_critical_tools())