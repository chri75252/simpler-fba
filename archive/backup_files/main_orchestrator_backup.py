"""
Main orchestrator for the complete FBA system
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path

from tools.configurable_supplier_scraper import ConfigurableSupplierScraper
from tools.supplier_parser import SupplierDataParser
from tools.supplier_api import SupplierAPIHandler
from tools.price_analyzer import PriceAnalyzer
from tools.currency_converter import CurrencyConverter
from tools.fba_calculator import FBACalculator
from tools.system_monitor import SystemMonitor

log = logging.getLogger(__name__)

class FBASystemOrchestrator:
    """
    Main orchestrator for the entire FBA analysis system.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.monitor = SystemMonitor()
        
        # Initialize components
        self.scraper = ConfigurableSupplierScraper()
        self.parser = SupplierDataParser()
        self.api_handler = SupplierAPIHandler()
        self.fba_calculator = FBACalculator()
        self.currency_converter = CurrencyConverter()
        self.price_analyzer = PriceAnalyzer(
            self.fba_calculator,
            self.currency_converter
        )
        
        # Results storage
        self.results = []
        
    async def run(self, suppliers: List[str], max_products: int = 100):
        """
        Run complete analysis for specified suppliers.
        
        Args:
            suppliers: List of supplier IDs to process
            max_products: Maximum products to process per supplier
        """
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
                    
                # Parse product data
                product_data = self.parser.parse_supplier_data(
                    supplier_id,
                    str(element),
                    full_url
                )
                
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
                
            # Analyze profitability
            analysis = await self.price_analyzer.analyze_product_profitability(
                supplier_product,
                amazon_product
            )
            
            # Check criteria
            min_roi = self.config.get('analysis', {}).get('min_roi_percent', 35)
            min_profit = self.config.get('analysis', {}).get('min_profit_per_unit', 3.0)
            
            if (analysis.roi_percent >= min_roi and
                analysis.net_profit >= min_profit):
                
                return {
                    'supplier_id': supplier_id,
                    'supplier_product': supplier_product,
                    'amazon_product': amazon_product,
                    'analysis': analysis,
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
        
        # Calculate summary statistics
        total_analyzed = self.monitor.products_processed
        profitable_found = len(self.results)
        success_rate = (profitable_found / total_analyzed * 100) if total_analyzed > 0 else 0
        
        avg_roi = 0
        avg_profit = 0
        if self.results:
            avg_roi = sum(r['analysis'].roi_percent for r in self.results) / len(self.results)
            avg_profit = sum(r['analysis'].net_profit for r in self.results) / len(self.results)
        
        return {
            'summary': {
                'total_products_analyzed': total_analyzed,
                'profitable_products_found': profitable_found,
                'success_rate': round(success_rate, 2),
                'avg_roi': round(avg_roi, 2),
                'avg_profit': round(avg_profit, 2)
            },
            'top_products': sorted(
                self.results,
                key=lambda x: x['analysis'].roi_percent,
                reverse=True
            )[:10],
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
            await self.currency_converter.close()
        except Exception as e:
            log.error(f"Error during cleanup: {e}")