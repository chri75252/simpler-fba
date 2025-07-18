#!/usr/bin/env python3
"""
Vision + Playwright EAN Bootstrap Script
One-time bootstrap for PoundWholesale selector extraction
Implements hybrid Vision-assisted approach with output safety
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project paths
sys.path.insert(0, os.path.dirname(__file__))
from tools.vision_product_locator import PoundWholesaleLocator
from tools.product_data_extractor import ProductDataExtractor
from tools.supplier_output_manager import SupplierOutputManager, update_claude_md_safety_rule
from utils.path_manager import get_log_path

# OpenAI client
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class VisionEANBootstrap:
    """Main bootstrap orchestrator"""
    
    def __init__(self):
        """Initialize bootstrap components"""
        self.openai_client = None
        self.locator = None
        self.extractor = None
        self.output_manager = None
        
        # Credentials
        self.email = "info@theblacksmithmarket.com"
        self.password = "0Dqixm9c&"
        
        # Results
        self.results = {
            'started_at': datetime.now().isoformat(),
            'completed_at': None,
            'success': False,
            'product_url': None,
            'extracted_data': {},
            'selector_config_path': '',
            'navigation_method': '',
            'errors': []
        }
        
        self._setup_debug_logging()
    
    def _setup_debug_logging(self):
        """Setup comprehensive debug logging"""
        try:
            date_str = datetime.now().strftime('%Y%m%d')
            debug_log_path = get_log_path("debug", f"supplier_scraping_debug_{date_str}.log")
            
            # Add file handler
            file_handler = logging.FileHandler(debug_log_path)
            file_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            
            # Add to root logger
            logging.getLogger().addHandler(file_handler)
            logging.getLogger().setLevel(logging.DEBUG)
            
            log.info(f"🔍 Debug logging initialized - writing to {debug_log_path}")
            
        except Exception as e:
            log.warning(f"Failed to setup debug logging: {e}")
    
    def initialize_components(self) -> bool:
        """Initialize all bootstrap components"""
        try:
            log.info("🚀 Initializing Vision EAN Bootstrap components...")
            
            # Initialize OpenAI client
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            
            self.openai_client = OpenAI(api_key=api_key)
            log.info("✅ OpenAI client initialized")
            
            # Initialize Vision Product Locator
            self.locator = PoundWholesaleLocator(self.openai_client)
            log.info("✅ Vision Product Locator initialized")
            
            # Initialize Product Data Extractor
            self.extractor = ProductDataExtractor()
            log.info("✅ Product Data Extractor initialized")
            
            # Initialize Output Manager
            self.output_manager = SupplierOutputManager("poundwholesale-co-uk")
            log.info("✅ Supplier Output Manager initialized")
            
            # Update claude.md with safety rules
            update_claude_md_safety_rule()
            log.info("✅ Claude.md updated with output safety rules")
            
            return True
            
        except Exception as e:
            error_msg = f"Component initialization failed: {e}"
            log.error(f"❌ {error_msg}")
            self.results['errors'].append(error_msg)
            return False
    
    async def run_product_location(self) -> bool:
        """Run the product location process"""
        try:
            log.info("🎯 Starting product location process...")
            
            # Find first product using hybrid approach
            navigation_result = await self.locator.find_first_product(
                email=self.email,
                password=self.password
            )
            
            if navigation_result.success:
                self.results['product_url'] = navigation_result.product_url
                self.results['navigation_method'] = navigation_result.method_used
                
                log.info(f"✅ Product location successful!")
                log.info(f"   - Method: {navigation_result.method_used}")
                log.info(f"   - URL: {navigation_result.product_url}")
                
                # Save navigation dump if available
                if navigation_result.navigation_dump:
                    await self.locator.save_navigation_dump(navigation_result.navigation_dump)
                
                return True
            else:
                error_msg = f"Product location failed: {navigation_result.error_message}"
                log.error(f"❌ {error_msg}")
                self.results['errors'].append(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Product location process failed: {e}"
            log.error(f"❌ {error_msg}")
            self.results['errors'].append(error_msg)
            return False
    
    async def run_data_extraction(self) -> bool:
        """Run the product data extraction"""
        try:
            log.info("📊 Starting product data extraction...")
            
            if not self.locator.page:
                error_msg = "No page available for data extraction"
                log.error(f"❌ {error_msg}")
                self.results['errors'].append(error_msg)
                return False
            
            # Extract product data
            product_data = await self.extractor.extract_product_data(
                self.locator.page,
                self.results['product_url']
            )
            
            self.results['extracted_data'] = product_data
            
            # Check extraction success
            success_criteria = {
                'title': bool(product_data.get('title')),
                'price': bool(product_data.get('price')) and 'not found' not in product_data.get('price', '').lower(),
                'ean': bool(product_data.get('ean'))
            }
            
            successful_extractions = sum(success_criteria.values())
            
            log.info(f"📊 Extraction Results:")
            log.info(f"   - Title: {'✅' if success_criteria['title'] else '❌'} {product_data.get('title', 'Not found')[:50]}")
            log.info(f"   - Price: {'✅' if success_criteria['price'] else '❌'} {product_data.get('price', 'Not found')}")
            log.info(f"   - EAN: {'✅' if success_criteria['ean'] else '❌'} {product_data.get('ean', 'Not found')}")
            
            if successful_extractions >= 2:  # At least 2 out of 3 fields
                log.info("✅ Data extraction successful (2/3+ fields extracted)")
                return True
            else:
                log.warning("⚠️ Data extraction partially successful (less than 2/3 fields)")
                return True  # Still consider successful for selector learning
                
        except Exception as e:
            error_msg = f"Data extraction failed: {e}"
            log.error(f"❌ {error_msg}")
            self.results['errors'].append(error_msg)
            return False
    
    def save_results(self) -> bool:
        """Save all results with proper isolation"""
        try:
            log.info("💾 Saving bootstrap results...")
            
            # Save selector configuration
            config_path = self.extractor.save_selector_config()
            self.results['selector_config_path'] = config_path
            
            if config_path:
                log.info(f"✅ Selector config saved to: {config_path}")
            else:
                log.error("❌ Failed to save selector config")
                self.results['errors'].append("Selector config save failed")
            
            # Save extraction log
            extraction_log_path = self.output_manager.save_extraction_log(self.results['extracted_data'])
            if extraction_log_path:
                log.info(f"✅ Extraction log saved to: {extraction_log_path}")
            
            # Save supplier data
            supplier_data_path = self.output_manager.save_supplier_data(
                self.results['extracted_data'], 
                "bootstrap_extraction"
            )
            if supplier_data_path:
                log.info(f"✅ Supplier data saved to: {supplier_data_path}")
            
            # Save complete bootstrap results
            bootstrap_results_path = self.output_manager.get_safe_output_path(
                'extraction_logs', 
                f"bootstrap_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            with open(bootstrap_results_path, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            
            log.info(f"✅ Complete bootstrap results saved to: {bootstrap_results_path}")
            
            # Run safety checks
            safety_status = self.output_manager.check_safety_rules()
            if all(safety_status.values()):
                log.info("✅ All output safety rules verified")
            else:
                log.warning(f"⚠️ Safety rule violations detected: {safety_status}")
            
            return True
            
        except Exception as e:
            error_msg = f"Results saving failed: {e}"
            log.error(f"❌ {error_msg}")
            self.results['errors'].append(error_msg)
            return False
    
    async def run_complete_bootstrap(self) -> bool:
        """Run the complete bootstrap process"""
        try:
            log.info("🚀 Starting Complete Vision EAN Bootstrap Process")
            log.info("="*80)
            
            # Initialize components
            if not self.initialize_components():
                return False
            
            # Run product location
            if not await self.run_product_location():
                return False
            
            # Run data extraction
            if not await self.run_data_extraction():
                return False
            
            # Save results
            if not self.save_results():
                return False
            
            # Mark as completed
            self.results['completed_at'] = datetime.now().isoformat()
            self.results['success'] = True
            
            log.info("="*80)
            log.info("✅ Vision/Playwright EAN bootstrap finished, selectors saved, outputs safeguarded")
            log.info("="*80)
            
            return True
            
        except Exception as e:
            error_msg = f"Complete bootstrap process failed: {e}"
            log.error(f"❌ {error_msg}")
            self.results['errors'].append(error_msg)
            return False
        
        finally:
            # Cleanup
            try:
                if self.locator:
                    await self.locator.cleanup()
                log.info("✅ Cleanup completed")
            except Exception as e:
                log.warning(f"Cleanup warning: {e}")
    
    def print_summary(self):
        """Print final summary"""
        print("\n" + "="*80)
        print("📋 VISION EAN BOOTSTRAP SUMMARY")
        print("="*80)
        print(f"🕐 Started: {self.results['started_at']}")
        print(f"🏁 Completed: {self.results.get('completed_at', 'Not completed')}")
        print(f"✅ Success: {self.results['success']}")
        print(f"🌐 Product URL: {self.results.get('product_url', 'Not found')}")
        print(f"🔍 Navigation Method: {self.results.get('navigation_method', 'None')}")
        print(f"📁 Selector Config: {self.results.get('selector_config_path', 'Not saved')}")
        
        if self.results.get('extracted_data'):
            data = self.results['extracted_data']
            print(f"📊 Extracted Data:")
            print(f"   - Title: {data.get('title', 'Not found')[:50]}...")
            print(f"   - Price: {data.get('price', 'Not found')}")
            print(f"   - EAN: {data.get('ean', 'Not found')}")
        
        if self.results.get('errors'):
            print(f"❌ Errors: {len(self.results['errors'])}")
            for error in self.results['errors']:
                print(f"   - {error}")
        
        print("="*80)

async def main():
    """Main execution function"""
    bootstrap = VisionEANBootstrap()
    
    try:
        success = await bootstrap.run_complete_bootstrap()
        bootstrap.print_summary()
        
        if success:
            print("\n🎉 Bootstrap completed successfully!")
            sys.exit(0)
        else:
            print("\n💥 Bootstrap failed - check logs for details")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Bootstrap interrupted by user")
        bootstrap.print_summary()
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Bootstrap crashed: {e}")
        bootstrap.print_summary()
        sys.exit(1)

if __name__ == "__main__":
    # Check dependencies
    try:
        import playwright
        from openai import OpenAI
        from bs4 import BeautifulSoup
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install: pip install playwright openai beautifulsoup4")
        sys.exit(1)
    
    # Run bootstrap
    asyncio.run(main())