#!/usr/bin/env python3
"""
Vision-Enhanced LangChain Tools for Amazon FBA Agent System

Wraps existing Playwright scripts as LangChain tools with Vision API fallback,
intelligent caching, and error handling for LangGraph integration.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# LangChain imports
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.callbacks import CallbackManagerForToolRun
from openai import OpenAI

# Import existing scripts
from tools.amazon_playwright_extractor import AmazonExtractor
from tools.vision_product_locator import PoundWholesaleLocator
from tools.vision_login_handler import VisionLoginHandler

# Import our browser manager
from utils.browser_manager import BrowserManager

# Import cache manager
try:
    from tools.cache_manager import CacheManager
except ImportError:
    # Fallback for testing
    class CacheManager:
        def __init__(self, config):
            self.config = config
        async def get_cached_data(self, key): return None
        async def set_cached_data(self, key, data): pass

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Pydantic models for tool inputs
class AmazonExtractionInput(BaseModel):
    """Input schema for Amazon product extraction"""
    asin: str = Field(description="Amazon Standard Identification Number (ASIN) of the product to extract")
    use_cache: bool = Field(default=True, description="Whether to use cached data if available")

class SupplierLoginInput(BaseModel):
    """Input schema for supplier login"""
    supplier_url: str = Field(description="Base URL of the supplier website")
    email: str = Field(description="Login email for the supplier")
    password: str = Field(description="Login password for the supplier")
    supplier_name: str = Field(default="unknown", description="Name/identifier for the supplier")

class SupplierProductLocationInput(BaseModel):
    """Input schema for locating products on supplier sites"""
    supplier_url: str = Field(description="Supplier website URL")
    email: str = Field(description="Login email")
    password: str = Field(description="Login password")
    supplier_name: str = Field(default="unknown", description="Supplier identifier")
    use_vision: bool = Field(default=True, description="Whether to use Vision API for navigation")

class ProductExtractionInput(BaseModel):
    """Input schema for extracting product data from any URL"""
    product_url: str = Field(description="Direct URL to the product page")
    supplier_name: str = Field(description="Supplier identifier for context isolation")
    extraction_fields: List[str] = Field(
        default=["title", "price", "sku", "ean", "stock_status"],
        description="List of fields to extract"
    )

# Vision-Enhanced Tool Classes
class VisionAmazonExtractorTool(BaseTool):
    """Enhanced Amazon product extraction with caching and error handling"""
    
    name: str = "amazon_product_extractor"
    description: str = """Extract comprehensive product data from Amazon using ASIN.
    
    This tool connects to a shared Chrome browser, navigates to Amazon product pages,
    and extracts detailed product information including pricing, availability, 
    reviews, and seller data. Uses intelligent caching to avoid redundant requests.
    
    Returns structured product data including title, price, ASIN, reviews, etc."""
    
    args_schema: Type[BaseModel] = AmazonExtractionInput
    openai_client: OpenAI = Field(...)
    cache_manager: Optional[CacheManager] = Field(default=None)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __init__(self, openai_client: OpenAI, cache_manager: Optional[CacheManager] = None, **kwargs):
        super().__init__(openai_client=openai_client, cache_manager=cache_manager, **kwargs)
    
    async def _arun(
        self,
        asin: str,
        use_cache: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> Dict[str, Any]:
        """Async implementation of Amazon product extraction"""
        
        # Check cache first
        cache_key = f"amazon_product_{asin}"
        if use_cache and self.cache_manager:
            try:
                cached_data = await self.cache_manager.get_cached_data(cache_key)
                if cached_data:
                    log.info(f"Using cached data for ASIN: {asin}")
                    return {
                        "success": True,
                        "source": "cache",
                        "asin": asin,
                        "data": cached_data,
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                log.warning(f"Cache check failed for {asin}: {e}")
        
        try:
            # Initialize Amazon extractor with AI client - use CDP connection to user's Chrome
            extractor = AmazonExtractor(ai_client=self.openai_client)
            
            # Connect to user's debug Chrome instance (NOT PlaywrightBrowserManager)
            log.info(f"Connecting to user's Chrome debug instance on port 9222")
            await extractor.connect()
            
            # ENHANCED DEBUGGING: Check browser state before extraction
            if extractor.browser and extractor.browser.contexts:
                context = extractor.browser.contexts[0]
                pages = context.pages
                log.info(f"DEBUG: Browser has {len(pages)} pages before Amazon extraction")
                if pages:
                    current_page = pages[0]
                    current_url = current_page.url
                    log.info(f"DEBUG: Current page URL before Amazon extraction: {current_url}")
                    
                    # Take screenshot before navigation for debugging
                    try:
                        await current_page.screenshot(path=f"before_amazon_navigation_{asin}.png")
                        log.info(f"DEBUG: Screenshot saved before Amazon navigation")
                    except Exception as screenshot_error:
                        log.warning(f"DEBUG: Could not take screenshot: {screenshot_error}")
            
            log.info(f"DEBUG: About to call extractor.extract_data for ASIN: {asin}")
            
            # Use the extractor's main extraction method - this should navigate to Amazon
            product_data = await extractor.extract_data(asin)
            
            # ENHANCED DEBUGGING: Check browser state after extraction
            if extractor.browser and extractor.browser.contexts:
                context = extractor.browser.contexts[0] 
                pages = context.pages
                log.info(f"DEBUG: Browser has {len(pages)} pages after Amazon extraction")
                if pages:
                    current_page = pages[0]
                    final_url = current_page.url
                    log.info(f"DEBUG: Final page URL after Amazon extraction: {final_url}")
                    
                    # Take screenshot after navigation for debugging
                    try:
                        await current_page.screenshot(path=f"after_amazon_navigation_{asin}.png")
                        log.info(f"DEBUG: Screenshot saved after Amazon navigation")
                    except Exception as screenshot_error:
                        log.warning(f"DEBUG: Could not take screenshot: {screenshot_error}")
                    
                    # Check if we're actually on Amazon
                    if "amazon.co.uk" in final_url or "amazon.com" in final_url:
                        log.info(f"DEBUG: ✅ Successfully navigated to Amazon: {final_url}")
                    else:
                        log.error(f"DEBUG: ❌ NAVIGATION FAILED - Still on non-Amazon page: {final_url}")
                        # This is the core issue we're trying to fix
            
            # Check if extraction was successful
            extraction_successful = bool(
                product_data and 
                product_data.get("title") and 
                not product_data.get("error")
            )
            
            # Add success flag for consistency
            product_data["extraction_successful"] = extraction_successful
            
            # Cache the results if successful
            if self.cache_manager and extraction_successful:
                try:
                    await self.cache_manager.set_cached_data(cache_key, product_data)
                    log.debug(f"Cached extraction results for ASIN: {asin}")
                except Exception as e:
                    log.warning(f"Failed to cache results for {asin}: {e}")
            
            return {
                "success": extraction_successful,
                "source": "extraction",
                "asin": asin,
                "data": product_data,
                "timestamp": datetime.now().isoformat()
            }
                
        except Exception as e:
            log.error(f"Amazon extraction failed for ASIN {asin}: {e}")
            return {
                "success": False,
                "asin": asin,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now().isoformat()
            }
    
    def _run(
        self,
        asin: str,
        use_cache: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> Dict[str, Any]:
        """Sync wrapper for async implementation"""
        return asyncio.run(self._arun(asin, use_cache, run_manager))

class VisionSupplierLoginTool(BaseTool):
    """Vision-assisted login to supplier websites"""
    
    name: str = "supplier_login"
    description: str = """Login to supplier websites using Vision-assisted navigation.
    
    This tool uses GPT-4 Vision to identify login forms and elements on supplier websites,
    automatically filling credentials and handling various login flows. Supports both
    heuristic selectors and AI-powered element identification.
    
    Returns login status and maintains session state for subsequent operations."""
    
    args_schema: Type[BaseModel] = SupplierLoginInput
    openai_client: OpenAI = Field(...)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __init__(self, openai_client: OpenAI, **kwargs):
        super().__init__(openai_client=openai_client, **kwargs)
    
    async def _arun(
        self,
        supplier_url: str,
        email: str,
        password: str,
        supplier_name: str = "unknown",
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> Dict[str, Any]:
        """Async implementation of supplier login"""
        
        try:
            browser_manager = BrowserManager()
            
            # Use persistent context for login state preservation
            async with browser_manager.managed_page(supplier_name, persistent=True) as page:
                # Initialize vision login handler with just OpenAI client
                login_handler = VisionLoginHandler(openai_client=self.openai_client)
                
                # Set the page directly since the handler expects to manage its own browser
                login_handler.page = page
                
                log.info(f"Attempting login to {supplier_url} for supplier: {supplier_name}")
                
                # Perform login with Vision assistance
                login_result = await login_handler.perform_login()
                
                return {
                    "success": login_result.success,
                    "supplier_name": supplier_name,
                    "supplier_url": supplier_url,
                    "method_used": login_result.method_used,
                    "login_detected": login_result.login_detected,
                    "price_access_verified": login_result.price_access_verified,
                    "error_message": login_result.error_message,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            log.error(f"Login failed for {supplier_name}: {e}")
            return {
                "success": False,
                "supplier_name": supplier_name,
                "supplier_url": supplier_url,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _run(
        self,
        supplier_url: str,
        email: str,
        password: str,
        supplier_name: str = "unknown",
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> Dict[str, Any]:
        """Sync wrapper for async implementation"""
        return asyncio.run(self._arun(supplier_url, email, password, supplier_name, run_manager))

class VisionProductLocatorTool(BaseTool):
    """Vision-enhanced product location and navigation"""
    
    name: str = "supplier_product_locator"
    description: str = """Locate and navigate to products on supplier websites using AI vision.
    
    Uses a hybrid approach combining heuristic selectors with GPT-4 Vision fallback
    to find and navigate to product pages on any supplier website. Handles complex
    navigation flows and dynamic content.
    
    Returns the URL of located product page and navigation metadata."""
    
    args_schema: Type[BaseModel] = SupplierProductLocationInput
    openai_client: OpenAI = Field(...)
    cache_manager: Optional[CacheManager] = Field(default=None)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __init__(self, openai_client: OpenAI, cache_manager: Optional[CacheManager] = None, **kwargs):
        super().__init__(openai_client=openai_client, cache_manager=cache_manager, **kwargs)
    
    async def _arun(
        self,
        supplier_url: str,
        email: str,
        password: str,
        supplier_name: str = "unknown",
        use_vision: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> Dict[str, Any]:
        """Async implementation of product location"""
        
        try:
            browser_manager = BrowserManager()
            
            # Use persistent context to maintain login state
            async with browser_manager.managed_page(supplier_name, persistent=True) as page:
                # Initialize vision product locator with just OpenAI client
                locator = PoundWholesaleLocator(openai_client=self.openai_client)
                
                # Set the page directly since the locator expects to manage its own browser
                locator.page = page
                
                log.info(f"Locating products on {supplier_url} for supplier: {supplier_name}")
                
                # First attempt: heuristic approach
                navigation_result = await locator.find_product_via_heuristics()
                
                # Fallback to Vision if heuristics fail and Vision is enabled
                if not navigation_result.success and use_vision:
                    log.info("Heuristics failed, falling back to Vision API...")
                    navigation_result = await locator.find_product_via_vision()
                
                # Cache successful navigation patterns
                if navigation_result.success and self.cache_manager:
                    cache_key = f"navigation_pattern_{supplier_name}"
                    pattern_data = {
                        "method_used": navigation_result.method_used,
                        "product_url": navigation_result.product_url,
                        "navigation_dump": navigation_result.navigation_dump
                    }
                    await self.cache_manager.set_cached_data(cache_key, pattern_data)
                
                return {
                    "success": navigation_result.success,
                    "supplier_name": supplier_name,
                    "product_url": navigation_result.product_url,
                    "method_used": navigation_result.method_used,
                    "navigation_dump": navigation_result.navigation_dump,
                    "error_message": navigation_result.error_message,
                    "screenshot_path": navigation_result.screenshot_path,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            log.error(f"Product location failed for {supplier_name}: {e}")
            return {
                "success": False,
                "supplier_name": supplier_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _run(
        self,
        supplier_url: str,
        email: str,
        password: str,
        supplier_name: str = "unknown",
        use_vision: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> Dict[str, Any]:
        """Sync wrapper for async implementation"""
        return asyncio.run(self._arun(supplier_url, email, password, supplier_name, use_vision, run_manager))

class VisionProductExtractorTool(BaseTool):
    """Extract product data from any supplier product page"""
    
    name: str = "supplier_product_extractor"
    description: str = """Extract comprehensive product data from supplier product pages.
    
    Uses intelligent field detection to extract product information including
    title, price, SKU, EAN, stock status, and other relevant data. Adapts to
    different website structures and formats.
    
    Returns structured product data with extraction confidence scores."""
    
    args_schema: Type[BaseModel] = ProductExtractionInput
    openai_client: OpenAI = Field(...)
    cache_manager: Optional[CacheManager] = Field(default=None)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def __init__(self, openai_client: OpenAI, cache_manager: Optional[CacheManager] = None, **kwargs):
        super().__init__(openai_client=openai_client, cache_manager=cache_manager, **kwargs)
    
    async def _arun(
        self,
        product_url: str,
        supplier_name: str,
        extraction_fields: List[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> Dict[str, Any]:
        """Async implementation of product extraction"""
        
        if extraction_fields is None:
            extraction_fields = ["title", "price", "sku", "ean", "stock_status"]
        
        # Check cache first
        cache_key = f"product_extraction_{supplier_name}_{hash(product_url)}"
        if self.cache_manager:
            cached_data = await self.cache_manager.get_cached_data(cache_key)
            if cached_data:
                log.info(f"Using cached extraction for {product_url}")
                return {
                    "success": True,
                    "source": "cache",
                    "product_url": product_url,
                    "data": cached_data,
                    "timestamp": datetime.now().isoformat()
                }
        
        try:
            browser_manager = BrowserManager()
            
            # Use supplier-specific context
            async with browser_manager.managed_page(supplier_name, persistent=True) as page:
                log.info(f"Extracting product data from: {product_url}")
                
                # Navigate to product page
                await page.goto(product_url, wait_until='domcontentloaded')
                await page.wait_for_load_state('networkidle', timeout=10000)
                
                # Check if supplier requires login and perform login if needed
                login_success = await self._ensure_supplier_login(supplier_name, page)
                if not login_success:
                    log.warning(f"Could not complete login for {supplier_name}, continuing with extraction")
                
                # Extract product data using configurable selectors
                from tools.configurable_supplier_scraper import ConfigurableSupplierScraper
                
                # Try headless first for speed, fallback to headed if needed
                extraction_result = None
                for headless_mode in [True, False]:  # Try headless first, then headed fallback
                    try:
                        scraper = ConfigurableSupplierScraper(
                            ai_client=self.openai_client,
                            headless=headless_mode,
                            use_shared_chrome=True
                        )
                        
                        log.info(f"Attempting supplier extraction in {'headless' if headless_mode else 'headed'} mode")
                        extraction_result = await scraper.scrape_products_from_url(
                            url=product_url,
                            max_products=10
                        )
                        
                        # If we got results, break out of the retry loop
                        if extraction_result and len(extraction_result) > 0:
                            log.info(f"Supplier extraction successful in {'headless' if headless_mode else 'headed'} mode")
                            break
                        else:
                            log.warning(f"No products extracted in {'headless' if headless_mode else 'headed'} mode")
                            if headless_mode:  # Only retry if we were in headless mode
                                log.info("Retrying in headed mode for supplier extraction...")
                                continue
                            
                    except Exception as scraper_error:
                        log.error(f"Supplier extraction failed in {'headless' if headless_mode else 'headed'} mode: {scraper_error}")
                        if headless_mode:  # Only retry if we were in headless mode
                            log.info("Retrying in headed mode due to error...")
                            continue
                        else:
                            # If headed mode also failed, re-raise the error
                            raise scraper_error
                
                # Handle the fact that scraper returns a list of products, not a dict
                extraction_successful = bool(extraction_result and len(extraction_result) > 0)
                
                # Cache successful extractions
                if extraction_successful and self.cache_manager:
                    cached_data = {
                        "products": extraction_result,
                        "extraction_successful": True,
                        "timestamp": datetime.now().isoformat()
                    }
                    await self.cache_manager.set_cached_data(cache_key, cached_data)
                
                return {
                    "success": extraction_successful,
                    "source": "extraction",
                    "product_url": product_url,
                    "supplier_name": supplier_name,
                    "data": extraction_result,
                    "products_found": len(extraction_result) if extraction_result else 0,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            log.error(f"Product extraction failed for {product_url}: {e}")
            return {
                "success": False,
                "product_url": product_url,
                "supplier_name": supplier_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _ensure_supplier_login(self, supplier_name: str, page) -> bool:
        """Ensure supplier login is completed before product extraction"""
        try:
            log.info(f"Checking login requirements for supplier: {supplier_name}")
            
            # Check if supplier has login script available
            # Convert www.poundwholesale.co.uk -> poundwholesale-co-uk
            supplier_slug = supplier_name.replace(".", "-").replace("www-", "")
            login_script_path = f"suppliers/{supplier_slug}/scripts/{supplier_slug}_login.py"
            
            # Import supplier-specific login module dynamically
            import sys
            import os
            from pathlib import Path
            
            # Check if login script exists
            if not os.path.exists(login_script_path):
                log.info(f"No login script found for {supplier_name}, proceeding without login")
                return True
            
            log.info(f"Found login script: {login_script_path}")
            
            # Add suppliers directory to Python path
            suppliers_dir = Path("suppliers").absolute()
            sys.path.insert(0, str(suppliers_dir))
            
            try:
                # Import the login module
                module_name = f"{supplier_slug}.scripts.{supplier_slug}_login"
                import importlib
                login_module = importlib.import_module(module_name)
                
                # Get the standalone login function
                function_name = f"{supplier_slug.replace('-', '_')}_login"
                if hasattr(login_module, function_name):
                    login_function = getattr(login_module, function_name)
                    
                    log.info(f"Attempting login for {supplier_name}")
                    login_success = await login_function(page=page)
                    
                    if login_success:
                        log.info(f"✅ Login successful for {supplier_name}")
                        return True
                    else:
                        log.warning(f"⚠️ Login failed for {supplier_name}")
                        return False
                        
                else:
                    log.warning(f"Login function not found in {module_name}")
                    return False
                    
            except ImportError as e:
                log.warning(f"Could not import login module for {supplier_name}: {e}")
                return False
            except Exception as e:
                log.error(f"Login attempt failed for {supplier_name}: {e}")
                return False
            finally:
                # Remove from path to avoid conflicts
                if str(suppliers_dir) in sys.path:
                    sys.path.remove(str(suppliers_dir))
                    
        except Exception as e:
            log.error(f"Error in login check for {supplier_name}: {e}")
            return False
    
    def _run(
        self,
        product_url: str,
        supplier_name: str,
        extraction_fields: List[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> Dict[str, Any]:
        """Sync wrapper for async implementation"""
        return asyncio.run(self._arun(product_url, supplier_name, extraction_fields, run_manager))

# Tool factory function
def create_vision_enhanced_tools(
    openai_api_key: str,
    cache_config: Optional[Dict] = None
) -> List[BaseTool]:
    """
    Factory function to create all vision-enhanced tools
    
    Args:
        openai_api_key: OpenAI API key for Vision API
        cache_config: Configuration for cache manager
        
    Returns:
        List of configured LangChain tools
    """
    
    # Initialize OpenAI client
    openai_client = OpenAI(api_key=openai_api_key)
    
    # Initialize cache manager if config provided
    cache_manager = None
    if cache_config:
        cache_manager = CacheManager(cache_config)
    
    # Create tools
    tools = [
        VisionAmazonExtractorTool(openai_client, cache_manager),
        VisionSupplierLoginTool(openai_client),
        VisionProductLocatorTool(openai_client, cache_manager),
        VisionProductExtractorTool(openai_client, cache_manager)
    ]
    
    log.info(f"Created {len(tools)} vision-enhanced tools")
    return tools

# Example usage and testing
async def test_tools():
    """Test the vision-enhanced tools"""
    
    # Get OpenAI API key from environment
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("OPENAI_API_KEY not found in environment")
        return
    
    # Create tools
    tools = create_vision_enhanced_tools(openai_api_key)
    
    # Test Amazon extractor
    amazon_tool = tools[0]
    print("\nTesting Amazon Product Extractor...")
    
    try:
        result = await amazon_tool._arun("B08N5WRWNW")  # Example ASIN
        print(f"Amazon extraction result: {result['success']}")
        if result['success']:
            print(f"Product title: {result['data'].get('title', 'N/A')}")
    except Exception as e:
        print(f"Amazon test failed: {e}")
    
    print("Tool tests completed!")

if __name__ == "__main__":
    asyncio.run(test_tools())