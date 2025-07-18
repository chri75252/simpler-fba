"""
Main orchestrator for the complete FBA system
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path
import shutil

from configurable_supplier_scraper import ConfigurableSupplierScraper
from amazon_playwright_extractor import AmazonExtractor  
from tools.utils.fba_calculator import FBACalculator
from supplier_parser import SupplierDataParser
from supplier_api import SupplierAPIHandler
# from tools.utils.price_analyzer import PriceAnalyzer # Commented out
# from tools.utils.currency_converter import CurrencyConverter # Commented out
from system_monitor import SystemMonitor

# OpenAI import for centralized client management
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

log = logging.getLogger(__name__)

class SimpleDataStore:
    """Simple in-memory data store for results."""
    def __init__(self):
        self.data = {}
    
    def insert_one(self, collection, doc):
        if collection not in self.data:
            self.data[collection] = []
        self.data[collection].append(doc)
        
    def get_all(self, collection):
        return self.data.get(collection, [])

class FBASystemOrchestrator:
    """
    Main orchestrator for the entire FBA analysis system.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.monitor = SystemMonitor()
        
        # Initialize OpenAI clients with model-specific configurations
        self.ai_clients = self._initialize_ai_clients()
        
        # Initialize components (using working v3 core scripts)
        self.amazon_extractor = AmazonExtractor(ai_client=self.ai_clients.get('amazon_extractor'))
        self.scraper = ConfigurableSupplierScraper()  # No AI client - pure HTML parsing
        self.parser = SupplierDataParser()
        self.api_handler = SupplierAPIHandler()
        # self.fba_calculator = FBACalculator() # Commented out
        # self.currency_converter = CurrencyConverter() # Commented out
        # self.price_analyzer = PriceAnalyzer( # Commented out
        #     self.fba_calculator, # Commented out
        #     self.currency_converter # Commented out
        # ) # Commented out
        
        # Initialize simple data store
        self.data_store = SimpleDataStore()
        
        # Results storage
        self.results = []
        
        # Enhanced cache management
        self.cache_config = self.config.get('cache', {})
        self.selective_clear_config = self.cache_config.get('selective_clear_config', {})
        
        # Cache directories from config
        cache_dirs = self.cache_config.get('directories', {})
        self.cache_dirs = [
            Path(cache_dirs.get('product_data', 'cache/products')),
            Path(cache_dirs.get('supplier_cache', 'OUTPUTS/cached_products')),
            Path(cache_dirs.get('amazon_cache', 'OUTPUTS/FBA_ANALYSIS/amazon_cache')),
            Path(cache_dirs.get('analysis_results', 'cache/analysis'))
        ]
        
        # Preserve these directories during selective clearing
        self.preserve_dirs = []
        if self.selective_clear_config.get('preserve_ai_categories', True):
            self.preserve_dirs.append(Path(cache_dirs.get('ai_category_cache', 'OUTPUTS/FBA_ANALYSIS/ai_category_cache')))
        if self.selective_clear_config.get('preserve_linking_map', True):
            self.preserve_dirs.append(Path(cache_dirs.get('linking_map', 'OUTPUTS/FBA_ANALYSIS/Linking map')))
        
        # System configuration flags
        system_config = self.config.get('system', {})
        self.test_mode = system_config.get('test_mode', False)
        self.clear_cache = system_config.get('clear_cache', False)
        self.selective_cache_clear = system_config.get('selective_cache_clear', True)
        self.bypass_ai_scraping = system_config.get('bypass_ai_scraping', False)
        self.enable_supplier_parser = system_config.get('enable_supplier_parser', True)
        
        # Workflow control configuration
        self.workflow_control = self.config.get('workflow_control', {})
        self.ai_scraping_triggers = self.workflow_control.get('ai_scraping_triggers', {})
        self.extraction_modes = self.workflow_control.get('extraction_modes', {})
        
        # Determine active extraction mode based on configuration
        self.active_extraction_mode = self._determine_extraction_mode()
        
        log.info(f"Orchestrator initialized with mode: {self.active_extraction_mode}")
        log.info(f"Test mode: {self.test_mode}, Clear cache: {self.clear_cache}, Selective clear: {self.selective_cache_clear}")
        log.info(f"Bypass AI scraping: {self.bypass_ai_scraping}")
        log.info(f"Supplier parser enabled: {self.enable_supplier_parser}")
    
    def _initialize_ai_clients(self) -> Dict[str, Any]:
        """
        Initialize OpenAI clients with model-specific configurations.
        
        Returns:
            Dict containing initialized AI clients for different components
        """
        ai_clients = {}
        
        if not OpenAI:
            log.warning("OpenAI library not available. AI functionality will be disabled.")
            return ai_clients
        
        # Get OpenAI configuration
        openai_config = self.config.get('integrations', {}).get('openai', {})
        
        if not openai_config.get('enabled', False):
            log.info("OpenAI integration disabled in configuration.")
            return ai_clients
        
        api_key = openai_config.get('api_key')
        if not api_key:
            log.warning("No OpenAI API key found in configuration. AI functionality will be disabled.")
            return ai_clients
        
        try:
            # Initialize client for passive extraction workflow (gpt-4o-mini-2024-07-18)
            passive_client = OpenAI(api_key=api_key)
            ai_clients['passive_extraction'] = {
                'client': passive_client,
                'model': 'gpt-4o-mini-2024-07-18',
                'max_tokens': openai_config.get('max_tokens', 1000),
                'temperature': openai_config.get('temperature', 0.1)
            }
            log.info("OpenAI client initialized for passive extraction workflow with model: gpt-4o-mini-2024-07-18")
            
            # Initialize client for Amazon playwright extractor (gpt-4.1-mini-2025-04-14)
            amazon_client = OpenAI(api_key=api_key)
            ai_clients['amazon_extractor'] = {
                'client': amazon_client,
                'model': 'gpt-4.1-mini-2025-04-14',
                'max_tokens': openai_config.get('max_tokens', 1000),
                'temperature': openai_config.get('temperature', 0.1)
            }
            log.info("OpenAI client initialized for Amazon extractor with model: gpt-4.1-mini-2025-04-14")
            
        except Exception as e:
            log.error(f"Failed to initialize OpenAI clients: {e}")
            ai_clients = {}
        
        return ai_clients
    
    def _determine_extraction_mode(self) -> str:
        """
        Determine the active extraction mode based on configuration flags.
        
        Returns:
            str: The active extraction mode name
        """
        # Check bypass conditions from AI scraping triggers
        bypass_conditions = self.ai_scraping_triggers.get('bypass_conditions', {})
        
        # Test mode bypass
        if self.test_mode and bypass_conditions.get('test_mode', False):
            log.info("Test mode enabled - bypassing AI scraping")
            return self._get_fallback_mode()
        
        # Direct bypass flag
        if self.bypass_ai_scraping and bypass_conditions.get('bypass_ai_scraping', False):
            log.info("AI scraping bypass flag enabled")
            return self._get_fallback_mode()
        
        # Direct Amazon extraction mode
        if bypass_conditions.get('direct_amazon_extraction', False):
            log.info("Direct Amazon extraction mode enabled")
            return 'direct_amazon_mode'
        
        # Predefined categories mode
        if bypass_conditions.get('use_predefined_categories', False):
            log.info("Using predefined categories mode")
            return 'hybrid_mode'
        
        # Default to full AI workflow
        return 'full_ai_workflow'
    
    def _get_fallback_mode(self) -> str:
        """
        Get the fallback extraction mode when AI scraping is bypassed.
        
        Returns:
            str: The fallback mode name
        """
        fallback_behavior = self.ai_scraping_triggers.get('fallback_behavior', {})
        
        if fallback_behavior.get('use_supplier_category_urls', True):
            return 'hybrid_mode'
        elif fallback_behavior.get('proceed_to_amazon_extraction', True):
            return 'direct_amazon_mode'
        else:
            return 'full_ai_workflow'
    
    async def selective_clear_cache_dirs(self):
        """
        Perform selective cache clearing based on configuration.
        Preserves specified directories and clears only what's configured to be cleared.
        """
        log.info("Starting selective cache clearing process...")
        
        if not self.selective_cache_clear:
            log.info("Selective cache clearing disabled, performing full clear")
            await self.clear_cache_dirs()
            return
        
        # Clear unanalyzed products only
        if self.selective_clear_config.get('clear_unanalyzed_only', True):
            pass # Placeholder after removing the call, actual method will be removed next
        
        # Clear failed extractions
        if self.selective_clear_config.get('clear_failed_extractions', True):
            await self._clear_failed_extractions()
        
        # Clear regular cache directories but preserve specified ones
        for cache_dir in self.cache_dirs:
            if cache_dir in self.preserve_dirs:
                log.info(f"Preserving directory: {cache_dir}")
                continue
                
            if cache_dir.exists():
                try:
                    # If preserve_analyzed_products is True, only clear unanalyzed
                    if self.selective_clear_config.get('preserve_analyzed_products', True):
                        await self._selective_clear_directory(cache_dir)
                    else:
                        shutil.rmtree(cache_dir)
                        log.info(f"Cleared directory: {cache_dir}")
                except Exception as e:
                    log.error(f"Failed to clear directory {cache_dir}: {e}")
            else:
                log.info(f"Directory does not exist, skipping: {cache_dir}")
        
        log.info("Selective cache clearing process completed.")
    
    async def _clear_failed_extractions(self):
        """Clear failed extraction attempts."""
        log.info("Clearing failed extractions...")
        
        # Clear error files and failed extraction markers
        error_patterns = ['*error*.json', '*failed*.json', '*timeout*.json']
        
        for cache_dir in self.cache_dirs:
            if cache_dir.exists():
                for pattern in error_patterns:
                    for error_file in cache_dir.glob(pattern):
                        try:
                            error_file.unlink()
                            log.info(f"Removed error file: {error_file}")
                        except Exception as e:
                            log.error(f"Failed to remove error file {error_file}: {e}")
    
    async def _selective_clear_directory(self, directory: Path):
        """
        Selectively clear a directory, preserving analyzed products.
        
        Args:
            directory: Directory to selectively clear
        """
        if not directory.exists():
            return
        
        # For now, implement basic selective clearing
        # In a full implementation, this would check each file against the linking map
        temp_files = list(directory.glob('*temp*.json'))
        cache_files = list(directory.glob('*cache*.json'))
        
        for temp_file in temp_files:
            try:
                temp_file.unlink()
                log.info(f"Removed temporary file: {temp_file}")
            except Exception as e:
                log.error(f"Failed to remove temporary file {temp_file}: {e}")
        
        # Keep analyzed cache files, remove unanalyzed ones
        for cache_file in cache_files:
            if 'unanalyzed' in cache_file.name or 'pending' in cache_file.name:
                try:
                    cache_file.unlink()
                    log.info(f"Removed unanalyzed cache file: {cache_file}")
                except Exception as e:
                    log.error(f"Failed to remove cache file {cache_file}: {e}")
        
    async def clear_cache_dirs(self):
        """Clear all cache directories completely."""
        log.info("Starting cache clearing process...")
        for cache_dir in self.cache_dirs:
            if cache_dir.exists():
                try:
                    shutil.rmtree(cache_dir)
                    log.info(f"Cleared directory: {cache_dir}")
                except Exception as e:
                    log.error(f"Failed to clear directory {cache_dir}: {e}")
            else:
                log.info(f"Directory does not exist, skipping: {cache_dir}")
        log.info("Cache clearing process completed.")
    
    async def run(self, suppliers: List[str], max_products: int = 100):
        """
        Run complete analysis for specified suppliers.
        
        Args:
            suppliers: List of supplier IDs to process
            max_products: Maximum products to process per supplier
        """
        # Clear cache if enabled - simplified approach
        if self.clear_cache:
            log.info("Main orchestrator: clear_cache=True, but cache clearing is now handled by PassiveExtractionWorkflow")
            # Cache clearing is now handled by PassiveExtractionWorkflow for better control
            # await self.clear_cache_dirs()
        
        # Start monitoring
        monitor_task = asyncio.create_task(
            self.monitor.start_monitoring(interval=30)
        )
        
        try:
            for supplier_id in suppliers:
                log.info(f"Processing supplier: {supplier_id}")
                await self.process_supplier(supplier_id, max_products)
                
            # Generate final report
            report = await self.generate_report()
            await self.save_report(report)
            
        finally:
            # Stop monitoring
            self.monitor.stop_monitoring()
            
            # Wait for monitor task to complete
            try:
                await asyncio.wait_for(monitor_task, timeout=5.0)
            except asyncio.TimeoutError:
                monitor_task.cancel()
            
            # Cleanup
            await self.cleanup()
    
    async def process_supplier(self, supplier_id: str, max_products: int):
        """Process a single supplier."""
        start_time = datetime.now()
        
        try:
            # Get supplier configuration
            supplier_config = self.config.get('suppliers', {}).get(supplier_id)
            if not supplier_config:
                log.error(f"No configuration found for supplier: {supplier_id}")
                return
                
            # Determine data source (API or scraping)
            if supplier_config.get('api_config', {}).get('enabled'):
                products = await self.fetch_from_api(supplier_id, max_products)
            else:
                products = await self.scrape_supplier(supplier_id, max_products)
                
            # Process products
            for product in products[:max_products]:
                try:
                    result = await self.analyze_product(product, supplier_id)
                    if result and result.get('profitable'):
                        self.results.append(result)
                        log.info(f"Found profitable product: {product.get('title')}")
                        
                    self.monitor.increment_products_processed()
                    
                except Exception as e:
                    self.monitor.log_error(e, {'product': product, 'supplier': supplier_id})
                    
            # Record timing
            duration = (datetime.now() - start_time).total_seconds()
            self.monitor.record_task_timing(duration)
            
        except Exception as e:
            self.monitor.log_error(e, {'supplier': supplier_id})
            log.error(f"Error processing supplier {supplier_id}: {e}")
    
    async def fetch_from_api(self, supplier_id: str, max_products: int) -> List[Dict[str, Any]]:
        """Fetch products from supplier API."""
        products = []
        page = 1
        
        while len(products) < max_products:
            try:
                # This would use actual API endpoints
                response = await self.api_handler.fetch_data(
                    supplier_id=supplier_id,
                    endpoint=f'/products?page={page}&limit=50',
                    auth_token=self.config.get('api_keys', {}).get(supplier_id)
                )
                
                if not response.get('products'):
                    break
                    
                products.extend(response['products'])
                page += 1
                
            except Exception as e:
                log.error(f"API fetch error for {supplier_id}: {e}")
                break
                
        return products
    
    async def scrape_supplier(self, supplier_id: str, max_products: int) -> List[Dict[str, Any]]:
        """Scrape products from supplier website."""
        config = self.config.get('suppliers', {}).get(supplier_id, {})
        base_url = config.get('base_url')
        
        if not base_url:
            log.error(f"No base URL configured for {supplier_id}")
            return []
            
        products = []
        
        # Get category URLs
        category_urls = config.get('category_urls', {}).get('main_categories', [])
        
        for category_url in category_urls:
            if len(products) >= max_products:
                break
                
            full_url = f"{base_url.rstrip('/')}/{category_url.lstrip('/')}"
            
            # Scrape category
            html = await self.scraper.get_page_content(full_url)
            if not html:
                continue
                
            # Extract products
            product_elements = self.scraper.extract_product_elements(html, full_url)
            
            for element in product_elements:
                if len(products) >= max_products:
                    break
                    
                # Parse product data - conditionally use supplier parser
                if self.enable_supplier_parser:
                    log.debug(f"Using supplier parser for {supplier_id}")
                    product_data = self.parser.parse_supplier_data(
                        supplier_id,
                        element,
                        full_url
                    )
                else:
                    log.debug(f"Supplier parser disabled, using raw element data for {supplier_id}")
                    # Use raw element data without specialized parsing
                    product_data = {
                        'supplier_id': supplier_id,
                        'url': full_url,
                        'raw_element': str(element) if hasattr(element, '__str__') else element,
                        '_parser_disabled': True
                    }
                
                if product_data and not product_data.get('_validation_errors'):
                    products.append(product_data)
                    
        return products
    
    async def analyze_product(self, supplier_product: Dict[str, Any], 
                            supplier_id: str) -> Optional[Dict[str, Any]]:
        """Analyze a single product for profitability."""
        try:
            # For this implementation, we'll create a mock Amazon product
            # In a real implementation, this would integrate with Amazon matching
            amazon_product = self._create_mock_amazon_product(supplier_product)
            
            if not amazon_product:
                return None
                
            # Analyze profitability - THIS IS THE KEY USAGE TO COMMENT OUT or adapt
            # analysis = await self.price_analyzer.analyze_product_profitability( # Commented out
            #     supplier_product, # Commented out
            #     amazon_product # Commented out
            # ) # Commented out

            # Placeholder for analysis if PriceAnalyzer is commented out
            # We need a basic structure for 'analysis' or the rest of the logic will fail
            # For now, let's assume a simple passthrough or mock structure if PriceAnalyzer is disabled.
            # This part needs careful consideration based on how an "inactive" PriceAnalyzer should affect the flow.
            # For now, to avoid breakage, we will create a mock analysis object.
            # TODO: Re-evaluate how this section should behave if PriceAnalyzer is inactive.
            # For the purpose of making it "inactive", we'll assume no analysis is done here by it.
            # The downstream code expects an 'analysis' object with 'roi_percent' and 'net_profit'.

            # Mock analysis if PriceAnalyzer is inactive
            analysis_mock = type('AnalysisMock', (), {'roi_percent': 0, 'net_profit': 0})()

            
            # Check criteria
            min_roi = self.config.get('analysis', {}).get('min_roi_percent', 35)
            min_profit = self.config.get('analysis', {}).get('min_profit_per_unit', 3.0)
            
            # if (analysis.roi_percent >= min_roi and # Original line
            #     analysis.net_profit >= min_profit): # Original line
            if (analysis_mock.roi_percent >= min_roi and # Using mock
                analysis_mock.net_profit >= min_profit): # Using mock
                
                return {
                    'supplier_id': supplier_id,
                    'supplier_product': supplier_product,
                    'amazon_product': amazon_product,
                    # 'analysis': analysis, # Original line
                    'analysis': analysis_mock, # Using mock
                    'profitable': True,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            log.error(f"Error analyzing product: {e}")
            
        return None
    
    def _create_mock_amazon_product(self, supplier_product: Dict[str, Any]) -> Dict[str, Any]:
        """Create a mock Amazon product for testing purposes."""
        # In a real implementation, this would use the Amazon matching workflow
        return {
            'asin': 'B' + str(hash(supplier_product.get('title', '')))[-9:],
            'title': supplier_product.get('title', 'Unknown Product'),
            'current_price': float(supplier_product.get('price', 0)) * 2.5,  # Mock markup
            'sales_rank': 25000,  # Mock sales rank
            'category': 'Home & Kitchen',
            'weight_pounds': 1.0,
            'dimensions_inches': (8, 6, 4),
            'review_count': 100,
            'rating': 4.2,
            'match_confidence': 0.8
        }
    
    async def generate_report(self) -> Dict[str, Any]:
        """Generate final analysis report."""
        health_report = await self.monitor.generate_health_report()
        
        # The following sections for 'summary' and 'top_products' have been removed.
        # This data is more accurately reported by passive_extraction_workflow_latest.py
        # in its fba_summary_{session_id}.json file.
        # Keeping these sections here led to conflicting or potentially inaccurate data due to
        # differences in how self.monitor.products_processed and self.results are 
        # populated in the orchestrator context versus the detailed workflow context.

        # Original code for summary statistics (now removed):
        # total_analyzed = self.monitor.products_processed
        # profitable_found = len(self.results)
        # success_rate = (profitable_found / total_analyzed * 100) if total_analyzed > 0 else 0
        # avg_roi = 0
        # avg_profit = 0
        # if self.results:
        #     avg_roi = sum(r['analysis'].roi_percent for r in self.results) / len(self.results)
        #     avg_profit = sum(r['analysis'].net_profit for r in self.results) / len(self.results)
        
        return {
            # 'summary': { # Section removed
            #     'total_products_analyzed': total_analyzed,
            #     'profitable_products_found': profitable_found,
            #     'success_rate': round(success_rate, 2),
            #     'avg_roi': round(avg_roi, 2),
            #     'avg_profit': round(avg_profit, 2)
            # },
            # 'top_products': sorted( # Section removed
            #     self.results,
            #     key=lambda x: x['analysis'].roi_percent,
            #     reverse=True
            # )[:10],
            'system_health': health_report,
            'timestamp': datetime.now().isoformat()
        }
    
    async def save_report(self, report: Dict[str, Any]):
        """Save analysis report."""
        output_dir = Path(self.config.get('output', {}).get('base_dir', 'OUTPUTS/FBA_ANALYSIS'))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = output_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
            log.info(f"Report saved to {filename}")
        except Exception as e:
            log.error(f"Failed to save report: {e}")
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            await self.scraper.close_session()
            await self.api_handler.close()
            # await self.currency_converter.close() # Commented out
        except Exception as e:
            log.error(f"Error during cleanup: {e}")
    
    async def run_with_passive_workflow(self, max_products: int = 100, force_ai_category_progression_flag: bool = False):
        log.info(f"Running passive workflow with max_products={max_products}, force_ai_progression={force_ai_category_progression_flag}")
        
        # Ensure PassiveExtractionWorkflow is imported correctly
        import sys
        from pathlib import Path
        # Add root directory to sys.path to allow importing passive_extraction_workflow_latest
        # Assuming main_orchestrator.py is in tools/ and passive_extraction_workflow_latest.py is in the parent (root) directory
        root_dir = Path(__file__).resolve().parent.parent 
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))
        from passive_extraction_workflow_latest import PassiveExtractionWorkflow

        # Get the AI client for passive extraction
        passive_ai_config = self.ai_clients.get('passive_extraction', {})
        passive_ai_client = passive_ai_config.get('client') if passive_ai_config else None
        
        if not passive_ai_client and self.ai_clients:
             log.warning("Passive extraction AI client not available, AI features in this workflow may be limited.")
        elif not self.ai_clients:
             log.warning("No AI clients initialized at all. AI features in this workflow will be disabled.")

        workflow = PassiveExtractionWorkflow(
            chrome_debug_port=self.config.get('chrome_debug_port', 9222),
            ai_client=passive_ai_client
        )

        # Pass the config to the workflow for cache clearing
        workflow.config = self.config

        if force_ai_category_progression_flag:
            workflow.force_ai_category_progression = True 
            log.info("Orchestrator: Forcing AI category progression for this workflow run.")

        # Determine suppliers to process
        suppliers_object = self.config.get("suppliers", {}) # Ensure this is suppliers_object
        if not suppliers_object:
            log.error("No suppliers object configured in system_config.json. Passive workflow cannot run.")
            return []

        # For this test, specifically target "clearance-king"
        target_supplier_key = "clearance-king" 
        if target_supplier_key not in suppliers_object: # Check against suppliers_object
            log.error(f"Supplier key '{target_supplier_key}' not found in suppliers configuration. Passive workflow cannot run.")
            return []
        
        # Access the config using the key from the suppliers_object dictionary
        target_supplier_config = suppliers_object[target_supplier_key] 
        supplier_url = target_supplier_config.get("base_url") 
        supplier_name = target_supplier_config.get("name", target_supplier_key)

        if not supplier_url:
            log.error(f"No base_url configured for supplier '{target_supplier_key}'. Passive workflow cannot run.")
            return []
        
        log.info(f"Orchestrator: Processing supplier - URL: {supplier_url}, Name: {supplier_name}")

        all_results = []
        try:
            # cache_supplier_data=True is the default in PassiveExtractionWorkflow.run()
            # force_config_reload=False is the default in PassiveExtractionWorkflow.run() (means don't clear supplier cache)
            supplier_results = await workflow.run(
                supplier_url=supplier_url, 
                supplier_name=supplier_name, 
                max_products_to_process=max_products
            )
            if supplier_results:
                all_results.extend(supplier_results)
            
            if hasattr(workflow, 'linking_map') and hasattr(workflow, '_save_linking_map'):
                workflow._save_linking_map()

        except Exception as e:
            log.error(f"Error running passive workflow for supplier {supplier_name}: {e}", exc_info=True)

        log.info(f"Passive workflow completed. Processed {len(all_results)} products.")
        return all_results
    
    async def clear_caches(self):
        """Clear all cached data to ensure fresh analysis."""
        log.info("Clearing all caches...")

        # Use absolute paths and current working directory
        import os
        cwd = Path.cwd()
        log.info(f"Current working directory: {cwd}")

        cache_dirs = [
            cwd / 'cache',
            cwd / 'OUTPUTS' / 'cached_products',
            cwd / 'OUTPUTS' / 'FBA_ANALYSIS' / 'amazon_cache',
            Path('cache'),  # Relative fallback
            Path('OUTPUTS/cached_products'),  # Relative fallback
        ]

        files_removed = 0
        for cache_dir in cache_dirs:
            log.info(f"Checking cache directory: {cache_dir} (exists: {cache_dir.exists()})")
            if cache_dir.exists():
                for file in cache_dir.glob('*.json'):
                    try:
                        file.unlink()
                        files_removed += 1
                        log.info(f"Removed cache file: {file}")
                    except Exception as e:
                        log.warning(f"Could not remove {file}: {e}")

        log.info(f"Cache clearing completed. Removed {files_removed} files.")
    
    def get_extraction_mode_config(self) -> Dict[str, Any]:
        """
        Get the configuration for the current extraction mode.
        
        Returns:
            Dict containing the extraction mode configuration
        """
        return self.extraction_modes.get(self.active_extraction_mode, {})
    
    def should_bypass_ai_scraping(self) -> bool:
        """
        Check if AI scraping should be bypassed based on current configuration.
        
        Returns:
            bool: True if AI scraping should be bypassed
        """
        if not self.ai_scraping_triggers.get('enabled', True):
            return True
            
        bypass_conditions = self.ai_scraping_triggers.get('bypass_conditions', {})
        
        # Check all bypass conditions
        if self.test_mode and bypass_conditions.get('test_mode', False):
            return True
            
        if self.bypass_ai_scraping and bypass_conditions.get('bypass_ai_scraping', False):
            return True
            
        if bypass_conditions.get('direct_amazon_extraction', False):
            return True
            
        if bypass_conditions.get('use_predefined_categories', False):
            return True
            
        return False
    
    def get_fallback_behavior(self) -> Dict[str, Any]:
        """
        Get the fallback behavior configuration when AI scraping is bypassed.
        
        Returns:
            Dict containing fallback behavior settings
        """
        return self.ai_scraping_triggers.get('fallback_behavior', {})
