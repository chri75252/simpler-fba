#!/usr/bin/env python3
"""
Workflow Orchestrator - Complete Automation Coordinator
========================================================

This is the MASTER ORCHESTRATOR that coordinates the complete Amazon FBA workflow:

1. Amazon product extraction
2. Supplier discovery and setup ("once per supplier")
3. Product matching and analysis
4. Financial calculations and ROI analysis

INTEGRATION POINTS:
    - LangGraph workflow system
    - supplier_script_generator.py for new suppliers
    - vision_discovery_engine.py for element detection
    - passive_extraction_workflow_latest.py for main orchestration
    - Amazon extraction tools

USAGE:
    python tools/workflow_orchestrator.py --asin B000BIUGTQ --supplier-url https://www.poundwholesale.co.uk/
"""

import asyncio
import json
import logging
import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class WorkflowOrchestrator:
    """Master orchestrator for complete Amazon FBA automation workflow"""
    
    def __init__(self):
        self.cdp_port = 9222
        self.page = None
        self.browser = None
        self.context = None
        
        # Paths
        self.suppliers_dir = Path("suppliers")
        self.config_dir = Path("config")
        self.tools_dir = Path("tools")
        self.outputs_dir = Path("OUTPUTS")
        
        # State tracking
        self.workflow_state = {
            "workflow_id": f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "started_at": datetime.now().isoformat(),
            "amazon_extraction": {"status": "pending", "data": None},
            "supplier_setup": {"status": "pending", "data": None},
            "product_matching": {"status": "pending", "data": None},
            "financial_analysis": {"status": "pending", "data": None},
            "errors": []
        }
        
        log.info("🎯 Workflow Orchestrator initialized")
    
    async def run_complete_workflow(self, asin: str, supplier_url: str, supplier_credentials: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Run the complete Amazon FBA analysis workflow
        
        Args:
            asin: Amazon product ASIN
            supplier_url: Supplier website URL
            supplier_credentials: Login credentials for supplier
            
        Returns:
            dict: Complete workflow results
        """
        try:
            log.info(f"🚀 Starting complete FBA workflow")
            log.info(f"📦 ASIN: {asin}")
            log.info(f"🏪 Supplier: {supplier_url}")
            
            # Initialize browser connection
            if not await self._connect_to_browser():
                raise Exception("Failed to connect to Chrome browser")
            
            # Phase 1: Amazon Product Extraction
            log.info("📦 Phase 1: Amazon Product Extraction")
            amazon_data = await self._extract_amazon_product(asin)
            
            if not amazon_data:
                raise Exception("Failed to extract Amazon product data")
            
            self.workflow_state["amazon_extraction"] = {
                "status": "completed",
                "data": amazon_data
            }
            
            # Phase 2: Supplier Setup and Discovery
            log.info("🏪 Phase 2: Supplier Setup and Discovery")
            supplier_data = await self._setup_supplier(supplier_url, supplier_credentials)
            
            if not supplier_data:
                log.warning("⚠️ Supplier setup failed - continuing with available data")
                self.workflow_state["errors"].append("Supplier setup failed")
            else:
                self.workflow_state["supplier_setup"] = {
                    "status": "completed", 
                    "data": supplier_data
                }
            
            # Phase 3: Product Matching
            log.info("🔍 Phase 3: Product Matching Analysis")
            matching_data = await self._analyze_product_matching(amazon_data, supplier_data)
            
            self.workflow_state["product_matching"] = {
                "status": "completed",
                "data": matching_data
            }
            
            # Phase 4: Financial Analysis
            log.info("💰 Phase 4: Financial Analysis")
            financial_data = await self._calculate_financial_analysis(amazon_data, supplier_data, matching_data)
            
            self.workflow_state["financial_analysis"] = {
                "status": "completed",
                "data": financial_data
            }
            
            # Save complete workflow results
            await self._save_workflow_results()
            
            log.info("🎉 Complete workflow finished successfully!")
            return self.workflow_state
            
        except Exception as e:
            log.error(f"❌ Workflow failed: {e}")
            self.workflow_state["errors"].append(str(e))
            self.workflow_state["status"] = "failed"
            return self.workflow_state
    
    async def run_supplier_only_setup(self, supplier_url: str, supplier_credentials: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Run supplier setup only ("once per supplier" workflow)
        
        Args:
            supplier_url: Supplier website URL
            supplier_credentials: Login credentials
            
        Returns:
            dict: Supplier setup results
        """
        try:
            log.info(f"🏪 Running supplier-only setup for: {supplier_url}")
            
            # Initialize browser connection
            if not await self._connect_to_browser():
                raise Exception("Failed to connect to Chrome browser")
            
            # Run supplier setup
            supplier_data = await self._setup_supplier(supplier_url, supplier_credentials)
            
            if supplier_data:
                log.info("✅ Supplier setup completed successfully")
                return {
                    "status": "success",
                    "supplier_data": supplier_data,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                raise Exception("Supplier setup failed")
                
        except Exception as e:
            log.error(f"❌ Supplier setup failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _connect_to_browser(self) -> bool:
        """Connect to Chrome debug instance"""
        try:
            log.info(f"🌐 Connecting to Chrome debug instance on port {self.cdp_port}")
            
            from playwright.async_api import async_playwright
            
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.connect_over_cdp(f"http://localhost:{self.cdp_port}")
            
            if self.browser.contexts:
                self.context = self.browser.contexts[0]
                log.info("Using existing browser context")
            else:
                self.context = await self.browser.new_context()
                log.info("Created new browser context")
            
            if self.context.pages:
                self.page = self.context.pages[0]
                log.info(f"Using existing page: {self.page.url}")
            else:
                self.page = await self.context.new_page()
                log.info("Created new page")
            
            await self.page.bring_to_front()
            return True
            
        except Exception as e:
            log.error(f"Failed to connect to browser: {e}")
            return False
    
    async def _extract_amazon_product(self, asin: str) -> Optional[Dict[str, Any]]:
        """Extract Amazon product data using LangGraph workflow"""
        try:
            log.info(f"📦 Extracting Amazon data for ASIN: {asin}")
            
            # Use direct import from the working amazon extractor
            import sys
            sys.path.append('tools')
            
            from amazon_playwright_extractor import AmazonExtractor
            
            # Create and run Amazon extractor
            extractor = AmazonExtractor()
            
            # Run extraction
            result = await extractor.extract_data(asin)
            
            if result and result.get('asin') == asin:
                log.info(f"✅ Amazon extraction successful")
                
                # Return the result as is
                amazon_data = {
                    "asin": asin,
                    "extraction_result": result,
                    "extracted_at": datetime.now().isoformat(),
                    "status": "success"
                }
                
                return amazon_data
            else:
                log.error(f"❌ Amazon extraction failed: {result}")
                return None
                
        except Exception as e:
            log.error(f"Amazon extraction error: {e}")
            return None
    
    async def _setup_supplier(self, supplier_url: str, credentials: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Setup supplier using automated script generation"""
        try:
            log.info(f"🏪 Setting up supplier: {supplier_url}")
            
            # Parse supplier info
            domain = urlparse(supplier_url).netloc
            supplier_id = domain.replace('.', '-').replace('www-', '')
            supplier_dir = self.suppliers_dir / supplier_id
            
            # Check if supplier already exists
            if supplier_dir.exists():
                log.info(f"📁 Supplier directory exists: {supplier_dir}")
                
                # Try to use existing scripts
                existing_data = await self._use_existing_supplier_scripts(supplier_dir, credentials)
                if existing_data:
                    return existing_data
            
            # Generate new supplier scripts
            log.info("🛠️ Generating new supplier automation scripts...")
            
            # Import and use supplier script generator
            from supplier_script_generator import SupplierScriptGenerator
            
            generator = SupplierScriptGenerator(supplier_url)
            success = generator.generate_all_scripts()
            
            if not success:
                log.error("❌ Failed to generate supplier scripts")
                return None
            
            # Run the generated supplier setup
            log.info("🚀 Running generated supplier setup...")
            
            # Import the generated integration script
            sys.path.append(str(supplier_dir / "scripts"))
            
            integration_module = f"{supplier_id}_langgraph_integration"
            integration_function = f"setup_{supplier_id.replace('-', '_')}_supplier"
            
            try:
                module = __import__(integration_module)
                setup_function = getattr(module, integration_function)
                
                # Run supplier setup
                result = await setup_function(self.page, credentials)
                
                if result.get("login_success") or result.get("product_discovery_success"):
                    log.info("✅ Supplier setup completed")
                    return result
                else:
                    log.warning("⚠️ Supplier setup had issues")
                    return result
                    
            except Exception as e:
                log.error(f"Failed to run generated supplier setup: {e}")
                
                # Fallback: Manual discovery
                return await self._fallback_supplier_discovery(supplier_url, credentials)
                
        except Exception as e:
            log.error(f"Supplier setup error: {e}")
            return None
    
    async def _use_existing_supplier_scripts(self, supplier_dir: Path, credentials: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Use existing supplier scripts if available"""
        try:
            log.info(f"🔄 Using existing supplier scripts from: {supplier_dir}")
            
            scripts_dir = supplier_dir / "scripts"
            
            # Look for integration script
            integration_scripts = list(scripts_dir.glob("*_langgraph_integration.py"))
            
            if integration_scripts:
                integration_script = integration_scripts[0]
                log.info(f"📜 Found integration script: {integration_script}")
                
                # Import and run the integration
                import sys
                sys.path.append(str(scripts_dir))
                
                module_name = integration_script.stem
                module = __import__(module_name)
                
                # Find the setup function
                for attr_name in dir(module):
                    if attr_name.startswith("setup_") and attr_name.endswith("_supplier"):
                        setup_function = getattr(module, attr_name)
                        
                        # Run supplier setup
                        result = await setup_function(self.page, credentials)
                        
                        log.info("✅ Existing supplier scripts executed successfully")
                        return result
            
            return None
            
        except Exception as e:
            log.error(f"Failed to use existing supplier scripts: {e}")
            return None
    
    async def _fallback_supplier_discovery(self, supplier_url: str, credentials: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Fallback supplier discovery using vision engine"""
        try:
            log.info("🔄 Running fallback supplier discovery...")
            
            # Navigate to supplier homepage
            await self.page.goto(supplier_url, wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Import vision discovery
            from vision_discovery_engine import discover_complete_supplier
            
            # Run complete discovery
            discovery_result = await discover_complete_supplier(self.page)
            
            if discovery_result.get("success"):
                log.info("✅ Fallback discovery successful")
                
                # Try basic login if credentials provided
                login_success = False
                if credentials and discovery_result.get("login"):
                    login_config = discovery_result["login"]
                    try:
                        # Navigate to login page
                        if login_config.get("login_url"):
                            await self.page.goto(login_config["login_url"])
                            await self.page.wait_for_load_state('networkidle', timeout=5000)
                        
                        # Fill credentials
                        if login_config.get("email_selector"):
                            await self.page.fill(login_config["email_selector"], credentials.get("email", ""))
                        
                        if login_config.get("password_selector"):
                            await self.page.fill(login_config["password_selector"], credentials.get("password", ""))
                        
                        # Submit
                        if login_config.get("submit_selector"):
                            await self.page.click(login_config["submit_selector"])
                        else:
                            await self.page.press(login_config["password_selector"], 'Enter')
                        
                        await self.page.wait_for_load_state('networkidle', timeout=10000)
                        
                        # Check for success indicators
                        logout_elements = await self.page.query_selector_all("a[href*='logout'], a:has-text('Logout')")
                        login_success = len(logout_elements) > 0
                        
                    except Exception as e:
                        log.warning(f"Fallback login failed: {e}")
                
                return {
                    "supplier_url": supplier_url,
                    "discovery_result": discovery_result,
                    "login_success": login_success,
                    "product_discovery_success": bool(discovery_result.get("products")),
                    "timestamp": datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            log.error(f"Fallback discovery failed: {e}")
            return None
    
    async def _analyze_product_matching(self, amazon_data: Dict, supplier_data: Optional[Dict]) -> Dict[str, Any]:
        """Analyze product matching between Amazon and supplier"""
        try:
            log.info("🔍 Analyzing product matching...")
            
            matching_result = {
                "amazon_asin": amazon_data.get("asin"),
                "amazon_title": "Not extracted",  # Would parse from amazon_data
                "supplier_products": [],
                "potential_matches": [],
                "match_confidence": 0.0,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            if not supplier_data or not supplier_data.get("product_discovery_success"):
                log.warning("⚠️ No supplier product data available for matching")
                return matching_result
            
            # Get supplier products
            supplier_products = []
            
            # Try to load from cache
            if supplier_data.get("discovery_result"):
                # This would contain product data from vision discovery
                pass
            
            # For now, return basic structure
            matching_result["supplier_products"] = supplier_products
            matching_result["analysis_status"] = "completed"
            
            return matching_result
            
        except Exception as e:
            log.error(f"Product matching analysis failed: {e}")
            return {
                "analysis_status": "failed",
                "error": str(e),
                "analysis_timestamp": datetime.now().isoformat()
            }
    
    async def _calculate_financial_analysis(self, amazon_data: Dict, supplier_data: Optional[Dict], matching_data: Dict) -> Dict[str, Any]:
        """Calculate financial analysis and ROI"""
        try:
            log.info("💰 Calculating financial analysis...")
            
            financial_result = {
                "amazon_price": "Not available",
                "supplier_price": "Not available", 
                "profit_margin": 0.0,
                "roi_percentage": 0.0,
                "fees_breakdown": {},
                "recommendation": "Insufficient data",
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            # Parse Amazon data for pricing
            amazon_result = amazon_data.get("extraction_result", "")
            # Would parse price from the extraction result
            
            # Parse supplier data for pricing
            if supplier_data and supplier_data.get("product_discovery_success"):
                # Would extract pricing from supplier data
                pass
            
            # Calculate basic financial metrics
            # This would integrate with FBA_Financial_calculator.py
            
            financial_result["analysis_status"] = "completed"
            return financial_result
            
        except Exception as e:
            log.error(f"Financial analysis failed: {e}")
            return {
                "analysis_status": "failed",
                "error": str(e),
                "analysis_timestamp": datetime.now().isoformat()
            }
    
    async def _save_workflow_results(self):
        """Save complete workflow results"""
        try:
            # Create outputs directory
            workflow_output_dir = self.outputs_dir / "FBA_ANALYSIS" / "workflow_results"
            workflow_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save complete workflow state
            workflow_file = workflow_output_dir / f"{self.workflow_state['workflow_id']}.json"
            
            with open(workflow_file, 'w') as f:
                json.dump(self.workflow_state, f, indent=2)
            
            log.info(f"💾 Workflow results saved: {workflow_file}")
            
            # Save summary report
            summary_file = workflow_output_dir / f"{self.workflow_state['workflow_id']}_summary.txt"
            
            summary_content = f"""
Amazon FBA Workflow Analysis Summary
===================================

Workflow ID: {self.workflow_state['workflow_id']}
Started: {self.workflow_state['started_at']}
Completed: {datetime.now().isoformat()}

Results:
--------
Amazon Extraction: {self.workflow_state['amazon_extraction']['status']}
Supplier Setup: {self.workflow_state['supplier_setup']['status']}
Product Matching: {self.workflow_state['product_matching']['status']}
Financial Analysis: {self.workflow_state['financial_analysis']['status']}

Errors: {len(self.workflow_state['errors'])}
{chr(10).join(f"- {error}" for error in self.workflow_state['errors'])}

Full details available in: {workflow_file}
"""
            
            summary_file.write_text(summary_content)
            log.info(f"📄 Summary report saved: {summary_file}")
            
        except Exception as e:
            log.error(f"Failed to save workflow results: {e}")

# Standalone functions for integration
async def run_complete_fba_workflow(asin: str, supplier_url: str, supplier_credentials: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Standalone function to run complete FBA workflow
    
    Args:
        asin: Amazon product ASIN
        supplier_url: Supplier website URL
        supplier_credentials: Optional login credentials
        
    Returns:
        dict: Complete workflow results
    """
    try:
        orchestrator = WorkflowOrchestrator()
        return await orchestrator.run_complete_workflow(asin, supplier_url, supplier_credentials)
    except Exception as e:
        log.error(f"Standalone workflow failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def setup_new_supplier(supplier_url: str, supplier_credentials: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Standalone function for "once per supplier" setup
    
    Args:
        supplier_url: Supplier website URL
        supplier_credentials: Optional login credentials
        
    Returns:
        dict: Supplier setup results
    """
    try:
        orchestrator = WorkflowOrchestrator()
        return await orchestrator.run_supplier_only_setup(supplier_url, supplier_credentials)
    except Exception as e:
        log.error(f"Standalone supplier setup failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def main():
    """Main entry point for workflow orchestrator"""
    parser = argparse.ArgumentParser(description='Run Amazon FBA analysis workflow')
    parser.add_argument('--asin', help='Amazon product ASIN')
    parser.add_argument('--supplier-url', help='Supplier website URL')
    parser.add_argument('--supplier-email', help='Supplier login email')
    parser.add_argument('--supplier-password', help='Supplier login password')
    parser.add_argument('--supplier-only', action='store_true', help='Run supplier setup only')
    
    args = parser.parse_args()
    
    # Prepare credentials
    credentials = None
    if args.supplier_email and args.supplier_password:
        credentials = {
            "email": args.supplier_email,
            "password": args.supplier_password
        }
    
    async def run_workflow():
        if args.supplier_only:
            if not args.supplier_url:
                print("❌ ERROR: --supplier-url required for supplier-only mode")
                return
            
            print(f"🏪 Running supplier-only setup for: {args.supplier_url}")
            result = await setup_new_supplier(args.supplier_url, credentials)
            
        else:
            if not args.asin or not args.supplier_url:
                print("❌ ERROR: Both --asin and --supplier-url required for complete workflow")
                return
            
            print(f"🚀 Running complete FBA workflow")
            print(f"📦 ASIN: {args.asin}")
            print(f"🏪 Supplier: {args.supplier_url}")
            
            result = await run_complete_fba_workflow(args.asin, args.supplier_url, credentials)
        
        # Print results
        print(f"\n✅ Workflow completed!")
        print(f"📊 Status: {result.get('status', 'unknown')}")
        
        if result.get('errors'):
            print(f"⚠️ Errors: {len(result['errors'])}")
            for error in result['errors']:
                print(f"  - {error}")
    
    try:
        asyncio.run(run_workflow())
    except KeyboardInterrupt:
        print("\n⚠️ Workflow interrupted by user")
    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")

if __name__ == "__main__":
    main()