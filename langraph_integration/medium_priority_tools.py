#!/usr/bin/env python3
"""
Medium Priority Tools - LangGraph Integration for Core Processing Components
=============================================================================

This module provides LangGraph wrappers for medium priority system components:
- AmazonPlaywrightExtractorTool (amazon_playwright_extractor.py)
- CategoryNavigatorTool (category_navigator.py) 
- ConfigurableSupplierScraperTool (configurable_supplier_scraper.py)
- CacheManagerTool (cache_manager.py)
- VisionDiscoveryEngineTool (vision_discovery_engine.py)
- WorkflowOrchestratorTool (workflow_orchestrator.py)
- SupplierScriptGeneratorTool (supplier_script_generator.py)

These tools provide essential processing capabilities for the FBA system.
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
    from tools.amazon_playwright_extractor import AmazonExtractor
    from tools.category_navigator import CategoryNavigator
    from tools.configurable_supplier_scraper import ConfigurableSupplierScraper
    from tools.cache_manager import CacheManager
    from tools.vision_discovery_engine import VisionDiscoveryEngine
    from tools.workflow_orchestrator import WorkflowOrchestrator
    from tools.supplier_script_generator import SupplierScriptGenerator
    from utils.browser_manager import BrowserManager
    
except ImportError as e:
    logger.warning(f"Some medium priority tools not available for import: {e}")
    # Create fallback classes to maintain API compatibility
    
    class AmazonExtractor:
        def __init__(self, chrome_debug_port=9222):
            pass
        async def extract_data(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    class CategoryNavigator:
        def __init__(self, supplier_name, page):
            pass
        async def navigate_categories(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    class ConfigurableSupplierScraper:
        def __init__(self, supplier_name, page):
            pass
        async def extract_products(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    class CacheManager:
        def __init__(self):
            pass
        async def save_products(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
        async def load_products(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
        async def clear_cache(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    class VisionDiscoveryEngine:
        def __init__(self):
            pass
        async def discover_products(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    class WorkflowOrchestrator:
        def __init__(self):
            pass
        async def orchestrate(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    class SupplierScriptGenerator:
        def __init__(self):
            pass
        async def generate_all_scripts(self, *args, **kwargs):
            return {"success": False, "error": "Tool not available"}
    
    class BrowserManager:
        @staticmethod
        async def get_browser():
            return None
        @staticmethod
        async def get_page():
            return None


# =============================================================================
# 1. AMAZON PLAYWRIGHT EXTRACTOR TOOL (Amazon Data Extraction)
# =============================================================================

class AmazonPlaywrightExtractorInput(BaseModel):
    """Input schema for Amazon Playwright Extractor Tool"""
    asin: str = Field(description="Amazon ASIN to extract data for")
    operation: str = Field(default="extract", description="Operation: extract, extract_with_keepa, or extract_with_selleramp")
    chrome_debug_port: int = Field(default=9222, description="Chrome debug port")
    enable_ai_fallback: bool = Field(default=False, description="Enable AI fallback for extraction")
    extraction_depth: str = Field(default="standard", description="Extraction depth: quick, standard, or comprehensive")


class AmazonPlaywrightExtractorTool(BaseTool):
    """
    LangGraph wrapper for Amazon data extraction (amazon_playwright_extractor.py)
    
    Extracts comprehensive product data from Amazon including:
    - Basic product information (title, price, availability)
    - Reviews and ratings data
    - Seller information
    - Keepa price history (optional)
    - SellerAmp data (optional)
    """
    name: str = "amazon_playwright_extractor"
    description: str = """
    Extracts comprehensive product data from Amazon product pages using Playwright automation.
    Supports basic extraction, Keepa price history, and SellerAmp data integration.
    
    Required inputs: asin
    Optional: operation (extract/extract_with_keepa/extract_with_selleramp), 
             chrome_debug_port, enable_ai_fallback, extraction_depth
    """
    args_schema: Type[BaseModel] = AmazonPlaywrightExtractorInput

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
        asin: str,
        operation: str = "extract",
        chrome_debug_port: int = 9222,
        enable_ai_fallback: bool = False,
        extraction_depth: str = "standard",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute Amazon data extraction"""
        try:
            logger.info(f"🛒 Amazon Extractor {operation} for ASIN: {asin}")
            
            # Initialize extractor
            extractor = AmazonExtractor(chrome_debug_port=chrome_debug_port)
            
            # Build Amazon URL
            amazon_url = f"https://www.amazon.co.uk/dp/{asin}"
            
            # Configure extraction options
            extraction_options = {
                "enable_ai_fallback": enable_ai_fallback,
                "extraction_depth": extraction_depth,
                "include_keepa": "keepa" in operation,
                "include_selleramp": "selleramp" in operation
            }
            
            # Execute extraction based on operation type
            if operation == "extract":
                result = await extractor.extract_data(amazon_url, **extraction_options)
            elif operation == "extract_with_keepa":
                result = await extractor.extract_with_keepa(amazon_url, **extraction_options)
            elif operation == "extract_with_selleramp":
                result = await extractor.extract_with_selleramp(amazon_url, **extraction_options)
            else:
                return json.dumps({
                    "extraction_id": f"amazon_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "asin": asin,
                    "error": f"Unknown operation: {operation}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "extraction_id": f"amazon_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "asin": asin,
                "amazon_url": amazon_url,
                "operation": operation,
                "extraction_options": extraction_options,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in Amazon Extractor: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "extraction_id": f"amazon_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "asin": asin,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 2. CATEGORY NAVIGATOR TOOL (Category Navigation)
# =============================================================================

class CategoryNavigatorInput(BaseModel):
    """Input schema for Category Navigator Tool"""
    supplier_name: str = Field(description="Supplier domain identifier")
    operation: str = Field(default="navigate", description="Operation: navigate, discover, or validate")
    target_categories: Optional[List[str]] = Field(default=None, description="Specific categories to target")
    max_pages_per_category: int = Field(default=5, description="Maximum pages per category")
    max_depth: int = Field(default=3, description="Maximum category depth to explore")


class CategoryNavigatorTool(BaseTool):
    """
    LangGraph wrapper for category navigation (category_navigator.py)
    
    Handles intelligent navigation through supplier category structures:
    - Sitemap-driven category discovery
    - Category hierarchy mapping
    - Product URL collection per category
    """
    name: str = "category_navigator"
    description: str = """
    Navigates supplier website category structures to discover and map product hierarchies.
    Uses sitemap-driven discovery and intelligent category traversal.
    
    Required inputs: supplier_name
    Optional: operation (navigate/discover/validate), target_categories, 
             max_pages_per_category, max_depth
    """
    args_schema: Type[BaseModel] = CategoryNavigatorInput

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
        operation: str = "navigate",
        target_categories: Optional[List[str]] = None,
        max_pages_per_category: int = 5,
        max_depth: int = 3,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute category navigation"""
        try:
            logger.info(f"🗂️ Category Navigator {operation} for {supplier_name}")
            
            # Get browser page (using browser manager if available)
            browser_manager = BrowserManager()
            page = await browser_manager.get_page()
            
            # Initialize navigator
            navigator = CategoryNavigator(supplier_name, page)
            
            # Configure navigation options
            nav_config = {
                "target_categories": target_categories or [],
                "max_pages_per_category": max_pages_per_category,
                "max_depth": max_depth
            }
            
            # Execute navigation based on operation type
            if operation == "navigate":
                result = await navigator.navigate_categories(nav_config)
            elif operation == "discover":
                result = await navigator.discover_categories(nav_config)
            elif operation == "validate":
                result = await navigator.validate_categories(nav_config)
            else:
                return json.dumps({
                    "navigation_id": f"nav_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "supplier_name": supplier_name,
                    "error": f"Unknown operation: {operation}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "navigation_id": f"nav_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "operation": operation,
                "config": nav_config,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in Category Navigator: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "navigation_id": f"nav_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "operation": operation,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 3. CONFIGURABLE SUPPLIER SCRAPER TOOL (Enhanced Scraping)
# =============================================================================

class ConfigurableSupplierScraperInput(BaseModel):
    """Input schema for Configurable Supplier Scraper Tool"""
    supplier_name: str = Field(description="Supplier domain identifier")
    operation: str = Field(default="scrape", description="Operation: scrape, configure, or validate")
    max_pages: int = Field(default=10, description="Maximum pages to scrape")
    max_products: int = Field(default=100, description="Maximum products to extract")
    scrape_config: Optional[Dict[str, Any]] = Field(default=None, description="Custom scraping configuration")


class ConfigurableSupplierScraperTool(BaseTool):
    """
    LangGraph wrapper for configurable supplier scraping (configurable_supplier_scraper.py)
    
    Provides advanced supplier scraping with configurable selectors and extraction logic.
    Supports multiple scraping strategies and adaptive extraction methods.
    """
    name: str = "configurable_supplier_scraper"
    description: str = """
    Advanced configurable scraping tool for supplier websites with adaptive extraction.
    Supports multiple scraping strategies and custom selector configurations.
    
    Required inputs: supplier_name
    Optional: operation (scrape/configure/validate), max_pages, max_products, scrape_config
    """
    args_schema: Type[BaseModel] = ConfigurableSupplierScraperInput

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
        operation: str = "scrape",
        max_pages: int = 10,
        max_products: int = 100,
        scrape_config: Optional[Dict[str, Any]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute configurable supplier scraping"""
        try:
            logger.info(f"🕷️ Configurable Scraper {operation} for {supplier_name}")
            
            # Get browser page
            browser_manager = BrowserManager()
            page = await browser_manager.get_page()
            
            # Initialize scraper
            scraper = ConfigurableSupplierScraper(supplier_name, page)
            
            # Configure scraping parameters
            if scrape_config is None:
                scrape_config = {
                    "max_pages": max_pages,
                    "max_products": max_products,
                    "extract_images": True,
                    "extract_variants": True,
                    "use_ai_fallback": False
                }
            
            # Execute scraping based on operation type
            if operation == "scrape":
                result = await scraper.extract_products(scrape_config)
            elif operation == "configure":
                result = await scraper.configure_selectors(scrape_config)
            elif operation == "validate":
                result = await scraper.validate_configuration(scrape_config)
            else:
                return json.dumps({
                    "scraping_id": f"scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "supplier_name": supplier_name,
                    "error": f"Unknown operation: {operation}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "scraping_id": f"scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "operation": operation,
                "config": scrape_config,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in Configurable Supplier Scraper: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "scraping_id": f"scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "operation": operation,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 4. CACHE MANAGER TOOL (Enhanced Caching)
# =============================================================================

class CacheManagerInput(BaseModel):
    """Input schema for Cache Manager Tool"""
    operation: str = Field(description="Operation: save, load, clear, validate, or status")
    cache_type: str = Field(default="products", description="Type of cache: products, amazon, categories, or processing")
    supplier_name: Optional[str] = Field(default=None, description="Supplier name for cache operations")
    cache_data: Optional[Dict[str, Any]] = Field(default=None, description="Data to cache (for save operation)")
    cache_key: Optional[str] = Field(default=None, description="Specific cache key")


class CacheManagerTool(BaseTool):
    """
    LangGraph wrapper for cache management (cache_manager.py)
    
    Provides advanced caching capabilities with integrity validation,
    performance monitoring, and automated cleanup.
    """
    name: str = "cache_manager"
    description: str = """
    Advanced cache management with integrity validation and performance monitoring.
    Handles multiple cache types including products, Amazon data, categories, and processing states.
    
    Required inputs: operation
    Optional: cache_type, supplier_name, cache_data (for save), cache_key
    """
    args_schema: Type[BaseModel] = CacheManagerInput

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
        cache_type: str = "products",
        supplier_name: Optional[str] = None,
        cache_data: Optional[Dict[str, Any]] = None,
        cache_key: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute cache management operations"""
        try:
            logger.info(f"🗃️ Cache Manager {operation} for {cache_type}")
            
            # Initialize cache manager
            cache_manager = CacheManager()
            
            # Execute operation
            if operation == "save":
                if cache_data is None:
                    return json.dumps({
                        "cache_id": f"cache_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "operation": operation,
                        "error": "cache_data required for save operation",
                        "status": "failed",
                        "timestamp": datetime.now().isoformat()
                    })
                
                if supplier_name:
                    result = await cache_manager.save_products(supplier_name, cache_data)
                else:
                    result = await cache_manager.save_data(cache_type, cache_data, cache_key)
                    
            elif operation == "load":
                if supplier_name:
                    result = await cache_manager.load_products(supplier_name)
                else:
                    result = await cache_manager.load_data(cache_type, cache_key)
                    
            elif operation == "clear":
                if supplier_name:
                    result = await cache_manager.clear_supplier_cache(supplier_name)
                else:
                    result = await cache_manager.clear_cache(cache_type)
                    
            elif operation == "validate":
                result = await cache_manager.validate_integrity(cache_type)
                
            elif operation == "status":
                result = await cache_manager.get_cache_status(cache_type)
                
            else:
                return json.dumps({
                    "cache_id": f"cache_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "operation": operation,
                    "error": f"Unknown operation: {operation}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "cache_id": f"cache_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "operation": operation,
                "cache_type": cache_type,
                "supplier_name": supplier_name,
                "cache_key": cache_key,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in Cache Manager: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "cache_id": f"cache_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "operation": operation,
                "cache_type": cache_type,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 5. VISION DISCOVERY ENGINE TOOL (Product Discovery)
# =============================================================================

class VisionDiscoveryEngineInput(BaseModel):
    """Input schema for Vision Discovery Engine Tool"""
    supplier_url: str = Field(description="Supplier website URL")
    supplier_name: str = Field(description="Supplier domain identifier")
    operation: str = Field(default="discover", description="Operation: discover, analyze, or validate")
    discovery_depth: str = Field(default="standard", description="Discovery depth: quick, standard, or comprehensive")
    max_products: int = Field(default=50, description="Maximum products to discover")


class VisionDiscoveryEngineTool(BaseTool):
    """
    LangGraph wrapper for vision-powered product discovery (vision_discovery_engine.py)
    
    Uses AI vision capabilities to discover and analyze products on supplier websites
    without predefined selectors or configurations.
    """
    name: str = "vision_discovery_engine"
    description: str = """
    AI vision-powered product discovery engine that can discover products on supplier
    websites without predefined configurations or selectors.
    
    Required inputs: supplier_url, supplier_name
    Optional: operation (discover/analyze/validate), discovery_depth, max_products
    """
    args_schema: Type[BaseModel] = VisionDiscoveryEngineInput

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
        supplier_name: str,
        operation: str = "discover",
        discovery_depth: str = "standard",
        max_products: int = 50,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute vision-powered product discovery"""
        try:
            logger.info(f"👁️ Vision Discovery {operation} for {supplier_name}")
            
            # Initialize discovery engine
            discovery_engine = VisionDiscoveryEngine()
            
            # Configure discovery parameters
            discovery_config = {
                "supplier_url": supplier_url,
                "supplier_name": supplier_name,
                "discovery_depth": discovery_depth,
                "max_products": max_products
            }
            
            # Execute discovery based on operation type
            if operation == "discover":
                result = await discovery_engine.discover_products(discovery_config)
            elif operation == "analyze":
                result = await discovery_engine.analyze_product_structure(discovery_config)
            elif operation == "validate":
                result = await discovery_engine.validate_discoveries(discovery_config)
            else:
                return json.dumps({
                    "discovery_id": f"vision_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "supplier_name": supplier_name,
                    "error": f"Unknown operation: {operation}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "discovery_id": f"vision_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_url": supplier_url,
                "supplier_name": supplier_name,
                "operation": operation,
                "config": discovery_config,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in Vision Discovery Engine: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "discovery_id": f"vision_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "operation": operation,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 6. WORKFLOW ORCHESTRATOR TOOL (Process Coordination)
# =============================================================================

class WorkflowOrchestratorInput(BaseModel):
    """Input schema for Workflow Orchestrator Tool"""
    workflow_type: str = Field(description="Type of workflow: complete, extraction, analysis, or validation")
    supplier_name: str = Field(description="Supplier domain identifier")
    workflow_config: Optional[Dict[str, Any]] = Field(default=None, description="Workflow configuration")
    enable_monitoring: bool = Field(default=True, description="Enable workflow monitoring")


class WorkflowOrchestratorTool(BaseTool):
    """
    LangGraph wrapper for workflow orchestration (workflow_orchestrator.py)
    
    Coordinates complex multi-step workflows with dependency management,
    error handling, and progress monitoring.
    """
    name: str = "workflow_orchestrator"
    description: str = """
    Orchestrates complex multi-step workflows with dependency management and monitoring.
    Handles complete FBA workflows, extraction pipelines, analysis workflows, and validation.
    
    Required inputs: workflow_type, supplier_name
    Optional: workflow_config, enable_monitoring
    """
    args_schema: Type[BaseModel] = WorkflowOrchestratorInput

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
        workflow_type: str,
        supplier_name: str,
        workflow_config: Optional[Dict[str, Any]] = None,
        enable_monitoring: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute workflow orchestration"""
        try:
            logger.info(f"🎯 Workflow Orchestrator {workflow_type} for {supplier_name}")
            
            # Initialize orchestrator
            orchestrator = WorkflowOrchestrator()
            
            # Set default configuration if not provided
            if workflow_config is None:
                workflow_config = {
                    "supplier_name": supplier_name,
                    "enable_monitoring": enable_monitoring,
                    "workflow_type": workflow_type,
                    "created_at": datetime.now().isoformat()
                }
            
            # Execute workflow based on type
            if workflow_type == "complete":
                result = await orchestrator.orchestrate_complete_workflow(supplier_name, workflow_config)
            elif workflow_type == "extraction":
                result = await orchestrator.orchestrate_extraction_workflow(supplier_name, workflow_config)
            elif workflow_type == "analysis":
                result = await orchestrator.orchestrate_analysis_workflow(supplier_name, workflow_config)
            elif workflow_type == "validation":
                result = await orchestrator.orchestrate_validation_workflow(supplier_name, workflow_config)
            else:
                return json.dumps({
                    "orchestration_id": f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "supplier_name": supplier_name,
                    "error": f"Unknown workflow type: {workflow_type}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "orchestration_id": f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "workflow_type": workflow_type,
                "supplier_name": supplier_name,
                "config": workflow_config,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in Workflow Orchestrator: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "orchestration_id": f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "workflow_type": workflow_type,
                "supplier_name": supplier_name,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# 7. SUPPLIER SCRIPT GENERATOR TOOL (Dynamic Script Generation)
# =============================================================================

class SupplierScriptGeneratorInput(BaseModel):
    """Input schema for Supplier Script Generator Tool"""
    supplier_name: str = Field(description="Supplier domain identifier")
    supplier_url: str = Field(description="Supplier website URL")
    operation: str = Field(default="generate_all", description="Operation: generate_all, generate_login, generate_extractor, or validate")
    force_regenerate: bool = Field(default=False, description="Force regeneration of existing scripts")
    script_config: Optional[Dict[str, Any]] = Field(default=None, description="Script generation configuration")


class SupplierScriptGeneratorTool(BaseTool):
    """
    LangGraph wrapper for supplier script generation (supplier_script_generator.py)
    
    Generates custom supplier-specific scripts including login handlers,
    product extractors, and configuration files.
    """
    name: str = "supplier_script_generator"
    description: str = """
    Generates custom supplier-specific scripts and configurations including login handlers,
    product extractors, and selector configurations for new suppliers.
    
    Required inputs: supplier_name, supplier_url
    Optional: operation (generate_all/generate_login/generate_extractor/validate), 
             force_regenerate, script_config
    """
    args_schema: Type[BaseModel] = SupplierScriptGeneratorInput

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
        operation: str = "generate_all",
        force_regenerate: bool = False,
        script_config: Optional[Dict[str, Any]] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Execute supplier script generation"""
        try:
            logger.info(f"⚙️ Script Generator {operation} for {supplier_name}")
            
            # Initialize script generator
            generator = SupplierScriptGenerator()
            
            # Set default configuration if not provided
            if script_config is None:
                script_config = {
                    "supplier_name": supplier_name,
                    "supplier_url": supplier_url,
                    "force_regenerate": force_regenerate,
                    "include_login": True,
                    "include_extractor": True,
                    "include_config": True
                }
            
            # Execute generation based on operation type
            if operation == "generate_all":
                result = await generator.generate_all_scripts(supplier_name, supplier_url, script_config)
            elif operation == "generate_login":
                result = await generator.generate_login_script(supplier_name, supplier_url, script_config)
            elif operation == "generate_extractor":
                result = await generator.generate_extractor_script(supplier_name, supplier_url, script_config)
            elif operation == "validate":
                result = await generator.validate_generated_scripts(supplier_name, script_config)
            else:
                return json.dumps({
                    "generation_id": f"generate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "supplier_name": supplier_name,
                    "error": f"Unknown operation: {operation}",
                    "status": "failed",
                    "timestamp": datetime.now().isoformat()
                })
            
            return json.dumps({
                "generation_id": f"generate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "supplier_url": supplier_url,
                "operation": operation,
                "config": script_config,
                "result": result,
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = f"Error in Supplier Script Generator: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "generation_id": f"generate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "supplier_name": supplier_name,
                "operation": operation,
                "error": error_msg,
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            })


# =============================================================================
# TOOL COLLECTION FUNCTION
# =============================================================================

def create_medium_priority_tools() -> List[BaseTool]:
    """
    Create and return all medium priority tools for LangGraph integration
    
    Returns:
        List of BaseTool instances for all medium priority components
    """
    tools = [
        AmazonPlaywrightExtractorTool(),
        CategoryNavigatorTool(),
        ConfigurableSupplierScraperTool(),
        CacheManagerTool(),
        VisionDiscoveryEngineTool(),
        WorkflowOrchestratorTool(),
        SupplierScriptGeneratorTool(),
    ]
    
    logger.info(f"✅ Created {len(tools)} medium priority tools for LangGraph integration")
    return tools


# =============================================================================
# MAIN EXECUTION FOR TESTING
# =============================================================================

async def test_medium_priority_tools():
    """Test function for medium priority tools"""
    logger.info("🧪 Testing Medium Priority Tools")
    
    tools = create_medium_priority_tools()
    
    # Test each tool with minimal inputs
    for tool in tools:
        logger.info(f"Testing {tool.name}...")
        try:
            if tool.name == "amazon_playwright_extractor":
                result = await tool.ainvoke({
                    "asin": "B08N5WRWNW",
                    "operation": "extract",
                    "extraction_depth": "quick"
                })
            elif tool.name == "category_navigator":
                result = await tool.ainvoke({
                    "supplier_name": "test-supplier",
                    "operation": "discover"
                })
            elif tool.name == "configurable_supplier_scraper":
                result = await tool.ainvoke({
                    "supplier_name": "test-supplier",
                    "operation": "validate"
                })
            elif tool.name == "cache_manager":
                result = await tool.ainvoke({
                    "operation": "status",
                    "cache_type": "products"
                })
            elif tool.name == "vision_discovery_engine":
                result = await tool.ainvoke({
                    "supplier_url": "https://test.example.com",
                    "supplier_name": "test-supplier",
                    "operation": "analyze"
                })
            elif tool.name == "workflow_orchestrator":
                result = await tool.ainvoke({
                    "workflow_type": "validation",
                    "supplier_name": "test-supplier"
                })
            elif tool.name == "supplier_script_generator":
                result = await tool.ainvoke({
                    "supplier_name": "test-supplier",
                    "supplier_url": "https://test.example.com",
                    "operation": "validate"
                })
            
            logger.info(f"✅ {tool.name} test completed")
            
        except Exception as e:
            logger.error(f"❌ {tool.name} test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_medium_priority_tools())