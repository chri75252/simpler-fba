#!/usr/bin/env python3
"""
Utility Tools - LangGraph Integration for Supporting Components
================================================================

This module provides LangGraph wrappers for utility and helper components:
- StandalonePlaywrightLoginTool (standalone_playwright_login.py)
- FBAFinancialCalculatorTool (FBA_Financial_calculator.py)
- SystemMonitorTool (system_monitor.py)
- SupplierOutputManagerTool (supplier_output_manager.py)
- ProductDataExtractorTool (product_data_extractor.py)
- LoginHealthCheckerTool (login health checking)
- SecurityChecksTool (security_checks.py)
- MainOrchestratorTool (main_orchestrator.py)

These tools provide essential utility functions and supporting capabilities.
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
    from tools.standalone_playwright_login import StandalonePlaywrightLogin
    from tools.FBA_Financial_calculator import FBAFinancialCalculator
    from tools.system_monitor import SystemMonitor
    from tools.supplier_output_manager import SupplierOutputManager
    from tools.product_data_extractor import ProductDataExtractor
    from tools.security_checks import SecurityChecker
    from tools.main_orchestrator import MainOrchestrator
    from utils.browser_manager import BrowserManager
    
except ImportError as e:
    logger.warning(f"Some utility tools not available for import: {e}")
    # Create fallback classes to maintain API compatibility
    
    class StandalonePlaywrightLogin:
        def __init__(self):
            pass
        async def login_workflow(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    class FBAFinancialCalculator:
        def __init__(self):
            pass
        async def calculate_roi_and_profit(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
        async def run_calculations(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    class SystemMonitor:
        def __init__(self):
            pass
        async def get_system_status(self, *args, **kwargs):
            return {"error": "Tool not available"}
        async def monitor_performance(self, *args, **kwargs):
            return {"error": "Tool not available"}
    
    class SupplierOutputManager:
        def __init__(self, supplier_name):
            pass
        async def organize_outputs(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
        async def save_data(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    class ProductDataExtractor:
        def __init__(self, supplier_name, page):
            pass
        async def extract_product_data(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    class SecurityChecker:
        def __init__(self):
            pass
        async def validate_outputs(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    class MainOrchestrator:
        def __init__(self):
            pass
        async def coordinate(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    class BrowserManager:
        @staticmethod
        async def get_browser():
            return None


# =============================================================================
# 1. STANDALONE PLAYWRIGHT LOGIN TOOL (Login Management)
# =============================================================================

class StandalonePlaywrightLoginInput(BaseModel):
    """Input schema for Standalone Playwright Login Tool"""
    supplier_url: str = Field(description="Supplier website URL")
    supplier_email: str = Field(description="Supplier login email")
    supplier_password: str = Field(description="Supplier login password")
    operation: str = Field(default="login", description="Operation: login, verify, or logout")
    headless: bool = Field(default=False, description="Run browser in headless mode")
    verify_access: bool = Field(default=True, description="Verify price access after login")


class StandalonePlaywrightLoginTool(BaseTool):
    """
    LangGraph wrapper for standalone login handling (standalone_playwright_login.py)
    
    Handles automated login to supplier websites with verification and session management.
    """
    name: str = "standalone_playwright_login"
    description: str = """
    Handles automated login to supplier websites with session management and access verification.
    Supports login, verification, and logout operations with browser automation.
    
    Required inputs: supplier_url, supplier_email, supplier_password
    Optional: operation (login/verify/logout), headless, verify_access
    """
    args_schema: Type[BaseModel] = StandalonePlaywrightLoginInput

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
        supplier_url: str,
        supplier_email: str,
        supplier_password: str,
        operation: str = "login",
        headless: bool = False,
        verify_access: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute login operations"""
        try:
            logger.info(f"🔐 Standalone Login {operation} for {supplier_url}")
            
            # Initialize login handler
            login_handler = StandalonePlaywrightLogin()
            
            # Configure login parameters
            login_config = {
                "supplier_url": supplier_url,
                "supplier_email": supplier_email,
                "supplier_password": supplier_password,
                "headless": headless,
                "verify_access": verify_access
            }
            
            # Execute operation
            if operation == "login":
                result = await login_handler.login_workflow(
                    supplier_url, supplier_email, supplier_password, 
                    headless=headless, verify_access=verify_access
                )
            elif operation == "verify":
                result = await login_handler.verify_login_status(supplier_url)
            elif operation == "logout":
                result = await login_handler.logout_workflow(supplier_url)
            else:
                return json.dumps({
                    "login_id": f"login_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "supplier_url": supplier_url,
                    "error": f"Unknown operation: {operation}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "login_id": f"login_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_url": supplier_url,
                "operation": operation,
                "config": login_config,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in Standalone Login: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "login_id": f"login_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_url": supplier_url,
                "operation": operation,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 2. FBA FINANCIAL CALCULATOR TOOL (Financial Analysis)
# =============================================================================

class FBAFinancialCalculatorInput(BaseModel):
    """Input schema for FBA Financial Calculator Tool"""
    operation: str = Field(default="calculate", description="Operation: calculate, batch_calculate, or analyze_trends")
    amazon_price: Optional[float] = Field(default=None, description="Amazon product price")
    supplier_price: Optional[float] = Field(default=None, description="Supplier product price")
    category: Optional[str] = Field(default=None, description="Amazon category for fee calculation")
    supplier_name: Optional[str] = Field(default=None, description="Supplier name for batch operations")
    calculation_config: Optional[Dict[str, Any]] = Field(default=None, description="Custom calculation configuration")


class FBAFinancialCalculatorTool(BaseTool):
    """
    LangGraph wrapper for FBA financial calculations (FBA_Financial_calculator.py)
    
    Performs comprehensive financial analysis including ROI, profit calculations,
    fee estimation, and profitability analysis.
    """
    name: str = "fba_financial_calculator"
    description: str = """
    Performs comprehensive FBA financial analysis including ROI calculations, profit analysis,
    Amazon fee estimation, and profitability assessments.
    
    Required inputs: operation
    Optional: amazon_price, supplier_price, category, supplier_name, calculation_config
    """
    args_schema: Type[BaseModel] = FBAFinancialCalculatorInput

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
        operation: str = "calculate",
        amazon_price: Optional[float] = None,
        supplier_price: Optional[float] = None,
        category: Optional[str] = None,
        supplier_name: Optional[str] = None,
        calculation_config: Optional[Dict[str, Any]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute financial calculations"""
        try:
            logger.info(f"💰 FBA Calculator {operation}")
            
            # Initialize calculator
            calculator = FBAFinancialCalculator()
            
            # Set default configuration if not provided
            if calculation_config is None:
                calculation_config = {
                    "include_shipping": True,
                    "include_vat": True,
                    "include_amazon_fees": True,
                    "profit_margin_threshold": 0.15
                }
            
            # Execute calculation based on operation type
            if operation == "calculate":
                if amazon_price is None or supplier_price is None:
                    return json.dumps({
                        "calculation_id": f"calc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "operation": operation,
                        "error": "amazon_price and supplier_price required for calculate operation",
                        "status": "failed",
                        "timestamp": datetime.now().isoformat()
                    })
                
                result = await calculator.calculate_roi_and_profit(
                    amazon_price=amazon_price,
                    supplier_price=supplier_price,
                    category=category,
                    **calculation_config
                )
                
            elif operation == "batch_calculate":
                if supplier_name is None:
                    return json.dumps({
                        "calculation_id": f"calc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "operation": operation,
                        "error": "supplier_name required for batch_calculate operation",
                        "status": "failed",
                        "timestamp": datetime.now().isoformat()
                    })
                
                result = await calculator.run_calculations(supplier_name, calculation_config)
                
            elif operation == "analyze_trends":
                result = await calculator.analyze_profitability_trends(supplier_name, calculation_config)
                
            else:
                return json.dumps({
                    "calculation_id": f"calc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "operation": operation,
                    "error": f"Unknown operation: {operation}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "calculation_id": f"calc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "operation": operation,
                "inputs": {
                    "amazon_price": amazon_price,
                    "supplier_price": supplier_price,
                    "category": category,
                    "supplier_name": supplier_name
                },
                "config": calculation_config,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in FBA Calculator: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "calculation_id": f"calc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "operation": operation,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 3. SYSTEM MONITOR TOOL (Performance Monitoring)
# =============================================================================

class SystemMonitorInput(BaseModel):
    """Input schema for System Monitor Tool"""
    operation: str = Field(default="status", description="Operation: status, metrics, health, or performance")
    component: Optional[str] = Field(default=None, description="Specific component to monitor")
    monitoring_duration: int = Field(default=60, description="Monitoring duration in seconds")


class SystemMonitorTool(BaseTool):
    """
    LangGraph wrapper for system monitoring (system_monitor.py)
    
    Provides system performance monitoring, health checks, and metrics collection
    for browser operations, memory usage, and workflow performance.
    """
    name: str = "system_monitor"
    description: str = """
    Monitors system performance, health, and metrics including browser operations,
    memory usage, and workflow performance tracking.
    
    Required inputs: operation
    Optional: component (specific component to monitor), monitoring_duration
    """
    args_schema: Type[BaseModel] = SystemMonitorInput

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
        operation: str = "status",
        component: Optional[str] = None,
        monitoring_duration: int = 60,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute system monitoring"""
        try:
            logger.info(f"📊 System Monitor {operation}")
            
            # Initialize monitor
            monitor = SystemMonitor()
            
            # Execute monitoring based on operation type
            if operation == "status":
                result = await monitor.get_system_status(component)
            elif operation == "metrics":
                result = await monitor.get_performance_metrics(component)
            elif operation == "health":
                result = await monitor.run_health_check(component)
            elif operation == "performance":
                result = await monitor.monitor_performance(component, monitoring_duration)
            else:
                return json.dumps({
                    "monitor_id": f"monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "operation": operation,
                    "error": f"Unknown operation: {operation}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "monitor_id": f"monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "operation": operation,
                "component": component,
                "monitoring_duration": monitoring_duration,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in System Monitor: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "monitor_id": f"monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "operation": operation,
                "component": component,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 4. SUPPLIER OUTPUT MANAGER TOOL (Output Management)
# =============================================================================

class SupplierOutputManagerInput(BaseModel):
    """Input schema for Supplier Output Manager Tool"""
    supplier_name: str = Field(description="Supplier domain identifier")
    operation: str = Field(default="organize", description="Operation: organize, save, load, or cleanup")
    data_type: str = Field(default="products", description="Type of data: products, cache, reports, logs")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Data to save (for save operation)")
    output_format: str = Field(default="json", description="Output format: json, csv, or excel")


class SupplierOutputManagerTool(BaseTool):
    """
    LangGraph wrapper for supplier output management (supplier_output_manager.py)
    
    Manages organization, saving, loading, and cleanup of supplier-related output files
    including products, cache, reports, and logs.
    """
    name: str = "supplier_output_manager"
    description: str = """
    Manages organization and handling of supplier output files including products,
    cache data, reports, and logs with multiple format support.
    
    Required inputs: supplier_name, operation
    Optional: data_type, data (for save), output_format
    """
    args_schema: Type[BaseModel] = SupplierOutputManagerInput

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
        operation: str = "organize",
        data_type: str = "products",
        data: Optional[Dict[str, Any]] = None,
        output_format: str = "json",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute output management operations"""
        try:
            logger.info(f"📁 Output Manager {operation} for {supplier_name}")
            
            # Initialize output manager
            output_manager = SupplierOutputManager(supplier_name)
            
            # Execute operation
            if operation == "organize":
                result = await output_manager.organize_outputs(data_type)
            elif operation == "save":
                if data is None:
                    return json.dumps({
                        "output_id": f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "supplier_name": supplier_name,
                        "error": "data required for save operation",
                        "status": "failed",
                        "timestamp": datetime.now().isoformat()
                    })
                result = await output_manager.save_data(data_type, data, output_format)
            elif operation == "load":
                result = await output_manager.load_data(data_type, output_format)
            elif operation == "cleanup":
                result = await output_manager.cleanup_old_files(data_type)
            else:
                return json.dumps({
                    "output_id": f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "supplier_name": supplier_name,
                    "error": f"Unknown operation: {operation}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "output_id": f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "operation": operation,
                "data_type": data_type,
                "output_format": output_format,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in Output Manager: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "output_id": f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "operation": operation,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 5. PRODUCT DATA EXTRACTOR TOOL (Data Extraction)
# =============================================================================

class ProductDataExtractorInput(BaseModel):
    """Input schema for Product Data Extractor Tool"""
    supplier_name: str = Field(description="Supplier domain identifier")
    product_url: str = Field(description="Product URL to extract data from")
    operation: str = Field(default="extract", description="Operation: extract, validate, or analyze")
    extraction_config: Optional[Dict[str, Any]] = Field(default=None, description="Extraction configuration")


class ProductDataExtractorTool(BaseTool):
    """
    LangGraph wrapper for product data extraction (product_data_extractor.py)
    
    Extracts detailed product data from supplier product pages with configurable
    extraction strategies and validation.
    """
    name: str = "product_data_extractor"
    description: str = """
    Extracts detailed product data from supplier product pages with configurable
    strategies, validation, and quality checks.
    
    Required inputs: supplier_name, product_url
    Optional: operation (extract/validate/analyze), extraction_config
    """
    args_schema: Type[BaseModel] = ProductDataExtractorInput

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
        product_url: str,
        operation: str = "extract",
        extraction_config: Optional[Dict[str, Any]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute product data extraction"""
        try:
            logger.info(f"🔍 Product Extractor {operation} for {supplier_name}")
            
            # Get browser page
            browser_manager = BrowserManager()
            page = await browser_manager.get_page()
            
            # Initialize extractor
            extractor = ProductDataExtractor(supplier_name, page)
            
            # Set default configuration if not provided
            if extraction_config is None:
                extraction_config = {
                    "extract_images": True,
                    "extract_variants": True,
                    "extract_specifications": True,
                    "validate_data": True
                }
            
            # Execute extraction based on operation type
            if operation == "extract":
                result = await extractor.extract_product_data(product_url, extraction_config)
            elif operation == "validate":
                result = await extractor.validate_extracted_data(product_url, extraction_config)
            elif operation == "analyze":
                result = await extractor.analyze_product_structure(product_url, extraction_config)
            else:
                return json.dumps({
                    "extraction_id": f"extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "supplier_name": supplier_name,
                    "error": f"Unknown operation: {operation}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "extraction_id": f"extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "product_url": product_url,
                "operation": operation,
                "config": extraction_config,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in Product Extractor: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "extraction_id": f"extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "product_url": product_url,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 6. SECURITY CHECKS TOOL (Security Validation)
# =============================================================================

class SecurityChecksInput(BaseModel):
    """Input schema for Security Checks Tool"""
    operation: str = Field(default="validate", description="Operation: validate, scan, or audit")
    target_type: str = Field(default="outputs", description="Target type: outputs, files, or system")
    target_path: Optional[str] = Field(default=None, description="Specific path to validate")
    security_config: Optional[Dict[str, Any]] = Field(default=None, description="Security check configuration")


class SecurityChecksTool(BaseTool):
    """
    LangGraph wrapper for security validation (security_checks.py)
    
    Performs security validation of outputs, files, and system components
    to ensure data safety and compliance.
    """
    name: str = "security_checks"
    description: str = """
    Performs comprehensive security validation including output scanning,
    file validation, and system security checks.
    
    Required inputs: operation
    Optional: target_type, target_path, security_config
    """
    args_schema: Type[BaseModel] = SecurityChecksInput

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
        operation: str = "validate",
        target_type: str = "outputs",
        target_path: Optional[str] = None,
        security_config: Optional[Dict[str, Any]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute security checks"""
        try:
            logger.info(f"🔒 Security Checks {operation} for {target_type}")
            
            # Initialize security checker
            security_checker = SecurityChecker()
            
            # Set default configuration if not provided
            if security_config is None:
                security_config = {
                    "check_sensitive_data": True,
                    "validate_file_permissions": True,
                    "scan_for_malicious_content": True,
                    "check_data_integrity": True
                }
            
            # Execute security check based on operation type
            if operation == "validate":
                result = await security_checker.validate_outputs(target_type, target_path, security_config)
            elif operation == "scan":
                result = await security_checker.scan_for_vulnerabilities(target_type, target_path, security_config)
            elif operation == "audit":
                result = await security_checker.audit_security_posture(target_type, security_config)
            else:
                return json.dumps({
                    "security_id": f"security_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "operation": operation,
                    "error": f"Unknown operation: {operation}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "security_id": f"security_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "operation": operation,
                "target_type": target_type,
                "target_path": target_path,
                "config": security_config,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in Security Checks: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "security_id": f"security_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "operation": operation,
                "target_type": target_type,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 7. MAIN ORCHESTRATOR TOOL (High-Level Coordination)
# =============================================================================

class MainOrchestratorInput(BaseModel):
    """Input schema for Main Orchestrator Tool"""
    operation: str = Field(description="Operation: coordinate, monitor, or status")
    workflow_type: str = Field(default="complete", description="Type of workflow to coordinate")
    coordination_config: Optional[Dict[str, Any]] = Field(default=None, description="Coordination configuration")


class MainOrchestratorTool(BaseTool):
    """
    LangGraph wrapper for main orchestration (main_orchestrator.py)
    
    Provides high-level coordination and monitoring of complex multi-component
    workflows with dependency management and error handling.
    """
    name: str = "main_orchestrator"
    description: str = """
    High-level coordination tool for complex multi-component workflows with
    dependency management, monitoring, and error handling.
    
    Required inputs: operation
    Optional: workflow_type, coordination_config
    """
    args_schema: Type[BaseModel] = MainOrchestratorInput

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
        workflow_type: str = "complete",
        coordination_config: Optional[Dict[str, Any]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute main orchestration"""
        try:
            logger.info(f"🎯 Main Orchestrator {operation} for {workflow_type}")
            
            # Initialize orchestrator
            orchestrator = MainOrchestrator()
            
            # Set default configuration if not provided
            if coordination_config is None:
                coordination_config = {
                    "enable_monitoring": True,
                    "enable_error_recovery": True,
                    "enable_progress_tracking": True,
                    "workflow_type": workflow_type
                }
            
            # Execute orchestration based on operation type
            if operation == "coordinate":
                result = await orchestrator.coordinate(workflow_type, coordination_config)
            elif operation == "monitor":
                result = await orchestrator.monitor_workflows(coordination_config)
            elif operation == "status":
                result = await orchestrator.get_coordination_status(workflow_type)
            else:
                return json.dumps({
                    "orchestration_id": f"orch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "operation": operation,
                    "error": f"Unknown operation: {operation}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "orchestration_id": f"orch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "operation": operation,
                "workflow_type": workflow_type,
                "config": coordination_config,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in Main Orchestrator: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "orchestration_id": f"orch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "operation": operation,
                "workflow_type": workflow_type,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# TOOL COLLECTION FUNCTION
# =============================================================================

def create_utility_tools() -> List[BaseTool]:
    """
    Create and return all utility tools for LangGraph integration
    
    Returns:
        List of BaseTool instances for all utility components
    """
    tools = [
        StandalonePlaywrightLoginTool(),
        FBAFinancialCalculatorTool(),
        SystemMonitorTool(),
        SupplierOutputManagerTool(),
        ProductDataExtractorTool(),
        SecurityChecksTool(),
        MainOrchestratorTool(),
    ]
    
    logger.info(f"✅ Created {len(tools)} utility tools for LangGraph integration")
    return tools


# =============================================================================
# MAIN EXECUTION FOR TESTING
# =============================================================================

async def test_utility_tools():
    """Test function for utility tools"""
    logger.info("🧪 Testing Utility Tools")
    
    tools = create_utility_tools()
    
    # Test each tool with minimal inputs
    for tool in tools:
        logger.info(f"Testing {tool.name}...")
        try:
            if tool.name == "standalone_playwright_login":
                result = await tool.ainvoke({
                    "supplier_url": "https://test.example.com",
                    "supplier_email": "test@example.com",
                    "supplier_password": "test123",
                    "operation": "verify"
                })
            elif tool.name == "fba_financial_calculator":
                result = await tool.ainvoke({
                    "operation": "calculate",
                    "amazon_price": 12.99,
                    "supplier_price": 5.99,
                    "category": "Home & Kitchen"
                })
            elif tool.name == "system_monitor":
                result = await tool.ainvoke({
                    "operation": "status"
                })
            elif tool.name == "supplier_output_manager":
                result = await tool.ainvoke({
                    "supplier_name": "test-supplier",
                    "operation": "organize",
                    "data_type": "products"
                })
            elif tool.name == "product_data_extractor":
                result = await tool.ainvoke({
                    "supplier_name": "test-supplier",
                    "product_url": "https://test.example.com/product/123",
                    "operation": "analyze"
                })
            elif tool.name == "security_checks":
                result = await tool.ainvoke({
                    "operation": "validate",
                    "target_type": "outputs"
                })
            elif tool.name == "main_orchestrator":
                result = await tool.ainvoke({
                    "operation": "status",
                    "workflow_type": "complete"
                })
            
            logger.info(f"✅ {tool.name} test completed")
            
        except Exception as e:
            logger.error(f"❌ {tool.name} test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_utility_tools())