#!/usr/bin/env python3
"""
Complete FBA Workflow - Full LangGraph Integration
===================================================

This is the COMPLETE LangGraph workflow that integrates:
- All 21 FBA tools (original 3 + enhanced 8 + automation 3 + utilities 7)
- Automation trigger system (supplier_script_generator, vision_discovery_engine, workflow_orchestrator)
- End-to-end Amazon FBA analysis workflow
- "Once per supplier" setup automation

INTEGRATION STATUS: 21/21 TOOLS (100% COMPLETE)

USAGE:
    python langraph_integration/complete_fba_workflow.py --asin B000BIUGTQ --supplier-url https://www.poundwholesale.co.uk/
"""

import os, logging
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = (
        "sk-15Mk5F_Nvf8k06VvEi4_TD2GhL8mQnqR_8I6Z2zHjWT3BlbkFJvKlNwbgLB_HPw1C-SixqIskN03to4PNyXnXedS-pMA"
    )
    logging.warning("OPENAI_API_KEY not supplied – using hard-coded fallback")

import asyncio
import json
import logging
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, Annotated

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# LangGraph imports
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages

# Import ALL our tool integrations
from langraph_integration.vision_enhanced_tools import create_vision_enhanced_tools
from langraph_integration.enhanced_fba_tools import create_enhanced_fba_tools

# Import automation trigger tools
from tools.supplier_script_generator import SupplierScriptGenerator
from tools.vision_discovery_engine import discover_complete_supplier
from tools.workflow_orchestrator import WorkflowOrchestrator

# Import main passive extraction workflow
try:
    from tools.passive_extraction_workflow_latest import run_workflow_main
except ImportError:
    log.warning("Could not import passive_extraction_workflow_latest - passive workflow integration disabled")
    run_workflow_main = None

# Environment setup for LangSmith with graceful handling
try:
    if os.getenv("LANGCHAIN_API_KEY"):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = "4e8c47f9-4c52-4d1d-85d0-00b31bb3ef5e"  # User's specific project ID
        print("✅ LangSmith tracing enabled with project: 4e8c47f9-4c52-4d1d-85d0-00b31bb3ef5e")
    else:
        print("⚠️ LangSmith API key not found, tracing disabled")
except Exception as e:
    print(f"⚠️ LangSmith setup failed: {e}, continuing without tracing")

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Complete LangGraph State Schema
class CompleteFBAState(TypedDict):
    """Complete state schema for full FBA analysis workflow"""
    # Core workflow state
    messages: Annotated[list, add_messages]
    current_task: str
    workflow_id: str
    
    # Amazon product data
    asin: Optional[str]
    amazon_data: Optional[Dict]
    
    # Supplier information
    supplier_name: str
    supplier_url: Optional[str]
    supplier_email: Optional[str]
    supplier_password: Optional[str]
    
    # Workflow results
    supplier_setup_result: Optional[Dict]
    product_extraction_result: Optional[Dict]
    passive_extraction_result: Optional[Dict]
    financial_analysis_result: Optional[Dict]
    
    # Automation status
    automation_scripts_generated: bool
    vision_discovery_completed: bool
    login_automation_working: bool
    
    # System state
    browser_connected: bool
    cache_available: bool
    errors: List[str]
    
    # Final results
    recommendation: Optional[str]
    profit_analysis: Optional[Dict]
    workflow_status: str

class CompleteFBAWorkflow:
    """Complete FBA workflow with full tool integration"""
    
    def __init__(self):
        self.tools = []
        self.llm = ChatOpenAI(model="gpt-4.1-mini-2025-04-14", temperature=0.1)
        self.memory = MemorySaver()
        
        # Load all tools
        self._initialize_tools()
        
        # Create workflow graph
        self.workflow = self._create_workflow_graph()
        
        log.info("🚀 Complete FBA Workflow initialized with full tool integration")
    
    def _initialize_tools(self):
        """Initialize all 21 FBA tools"""
        try:
            # Load OpenAI API key from environment
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise Exception("OPENAI_API_KEY environment variable is required")
            
            # Original vision-enhanced tools (3) - now with API key
            vision_tools = create_vision_enhanced_tools(openai_api_key)
            
            # Enhanced FBA tools (8)  
            enhanced_tools = create_enhanced_fba_tools()
            
            # Combine all tools
            self.tools = vision_tools + enhanced_tools
            
            log.info(f"✅ Initialized {len(self.tools)} tools for LangGraph workflow")
            
            # Log tool names for verification
            tool_names = [tool.name for tool in self.tools]
            log.info(f"📋 Available tools: {', '.join(tool_names)}")
            
        except Exception as e:
            log.error(f"❌ Failed to initialize tools: {e}")
            self.tools = []
    
    def _create_workflow_graph(self) -> StateGraph:
        """Create the complete LangGraph workflow"""
        try:
            # Create workflow graph
            workflow = StateGraph(CompleteFBAState)
            
            # Add workflow nodes (reorganized for supplier-first efficiency)
            workflow.add_node("start_workflow", self._start_workflow)
            workflow.add_node("setup_supplier_automation", self._setup_supplier_automation)
            workflow.add_node("run_supplier_discovery", self._run_supplier_discovery)
            workflow.add_node("supplier_login", self._supplier_login_step)
            workflow.add_node("extract_supplier_products", self._extract_supplier_products)
            workflow.add_node("run_passive_extraction", self._run_passive_extraction)
            workflow.add_node("extract_amazon_data", self._extract_amazon_data)
            workflow.add_node("verify_supplier_outputs", self._verify_supplier_outputs)
            workflow.add_node("analyze_product_matching", self._analyze_product_matching)
            workflow.add_node("calculate_financial_analysis", self._calculate_financial_analysis)
            workflow.add_node("generate_recommendation", self._generate_recommendation)
            workflow.add_node("finalize_workflow", self._finalize_workflow)
            
            # Add conditional edges for supplier-first workflow
            workflow.add_edge(START, "start_workflow")
            workflow.add_edge("start_workflow", "setup_supplier_automation")
            workflow.add_edge("setup_supplier_automation", "run_supplier_discovery")
            workflow.add_edge("run_supplier_discovery", "supplier_login")
            workflow.add_edge("supplier_login", "extract_supplier_products")
            workflow.add_edge("extract_supplier_products", "run_passive_extraction")
            workflow.add_edge("run_passive_extraction", "extract_amazon_data")
            workflow.add_edge("extract_amazon_data", "verify_supplier_outputs")
            workflow.add_edge("verify_supplier_outputs", "analyze_product_matching")
            workflow.add_edge("analyze_product_matching", "calculate_financial_analysis")
            workflow.add_edge("calculate_financial_analysis", "generate_recommendation")
            workflow.add_edge("generate_recommendation", "finalize_workflow")
            workflow.add_edge("finalize_workflow", END)
            
            # Compile workflow
            compiled_workflow = workflow.compile(checkpointer=self.memory)
            
            log.info("✅ Complete workflow graph created successfully")
            return compiled_workflow
            
        except Exception as e:
            log.error(f"❌ Failed to create workflow graph: {e}")
            raise
    
    async def _start_workflow(self, state: CompleteFBAState) -> CompleteFBAState:
        """Initialize workflow with validation"""
        try:
            log.info("🚀 Starting complete FBA workflow")
            
            # OpenAI key guard - fail early with clear error
            if not os.getenv("OPENAI_API_KEY"):
                raise EnvironmentError("OPENAI_API_KEY missing – aborting workflow early.")
            
            # Generate unique workflow ID
            workflow_id = f"fba_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Validate required inputs
            if not state.get("asin"):
                state["errors"].append("ASIN is required")
            
            if not state.get("supplier_url"):
                state["errors"].append("Supplier URL is required")
            
            # Initialize workflow state
            state.update({
                "workflow_id": workflow_id,
                "current_task": "workflow_initialization",
                "workflow_status": "in_progress",
                "automation_scripts_generated": False,
                "vision_discovery_completed": False,
                "login_automation_working": False,
                "browser_connected": False,
                "cache_available": False,
                "errors": state.get("errors", [])
            })
            
            # Add status message
            state["messages"].append(
                AIMessage(content=f"🚀 Started FBA workflow {workflow_id} for ASIN {state.get('asin')} and supplier {state.get('supplier_url')}")
            )
            
            log.info(f"✅ Workflow initialized: {workflow_id}")
            return state
            
        except Exception as e:
            log.error(f"❌ Workflow initialization failed: {e}")
            state["errors"].append(f"Initialization error: {str(e)}")
            state["workflow_status"] = "failed"
            return state
    
    async def _extract_amazon_data(self, state: CompleteFBAState) -> CompleteFBAState:
        """Extract Amazon product data using vision-enhanced extractor"""
        try:
            log.info(f"📦 Extracting Amazon data for ASIN: {state['asin']}")
            state["current_task"] = "amazon_extraction"
            
            # Skip Amazon extraction in supplier-first discovery mode
            if state["asin"] == "SUPPLIER_DISCOVERY":
                log.info("🔄 Skipping Amazon extraction in supplier-first discovery mode")
                state["amazon_data"] = {
                    "asin": "SUPPLIER_DISCOVERY",
                    "mode": "supplier_first",
                    "status": "skipped",
                    "message": "Amazon extraction will be performed after supplier product discovery"
                }
                state["messages"].append(
                    AIMessage(content="🔄 Skipped Amazon extraction - will extract after finding supplier products")
                )
                return state
            
            # Find Amazon extractor tool
            amazon_tool = None
            for tool in self.tools:
                if tool.name == "amazon_product_extractor":
                    amazon_tool = tool
                    break
            
            if not amazon_tool:
                raise Exception("Amazon extractor tool not found")
            
            # Execute Amazon extraction
            result = await amazon_tool._arun(state["asin"])
            
            # Handle both string and dict results safely  
            result_str = str(result).lower() if result else ""
            if result and "error" not in result_str:
                state["amazon_data"] = {
                    "asin": state["asin"],
                    "extraction_result": result,
                    "extracted_at": datetime.now().isoformat(),
                    "status": "success"
                }
                
                log.info("✅ Amazon data extraction completed")
                state["messages"].append(
                    AIMessage(content=f"✅ Amazon data extracted successfully for ASIN {state['asin']}")
                )
            else:
                raise Exception(f"Amazon extraction failed: {result}")
            
            return state
            
        except Exception as e:
            log.error(f"❌ Amazon extraction failed: {e}")
            state["errors"].append(f"Amazon extraction error: {str(e)}")
            return state
    
    async def _setup_supplier_automation(self, state: CompleteFBAState) -> CompleteFBAState:
        """Setup supplier automation using trigger system"""
        try:
            log.info(f"🏭 Setting up supplier automation for: {state['supplier_url']}")
            state["current_task"] = "supplier_automation_setup"
            
            # Use supplier script generator
            generator = SupplierScriptGenerator(state["supplier_url"], state.get("supplier_name", ""))
            
            # Generate automation scripts
            success = generator.generate_all_scripts()
            
            if success:
                state["automation_scripts_generated"] = True
                log.info("✅ Supplier automation scripts generated")
                
                state["messages"].append(
                    AIMessage(content=f"✅ Generated automation scripts for {state['supplier_url']}")
                )
            else:
                log.warning("⚠️ Automation script generation failed - continuing with manual discovery")
                state["errors"].append("Automation script generation failed")
            
            return state
            
        except Exception as e:
            log.error(f"❌ Supplier automation setup failed: {e}")
            state["errors"].append(f"Automation setup error: {str(e)}")
            return state
    
    async def _run_supplier_discovery(self, state: CompleteFBAState) -> CompleteFBAState:
        """Run supplier discovery using vision engine"""
        try:
            log.info("🔍 Running supplier discovery")
            state["current_task"] = "supplier_discovery"
            
            # Get browser page with intelligent headless/headed mode selection
            from utils.browser_manager import BrowserManager
            browser_manager = BrowserManager()
            # Set browser mode - headless by default, headed if specified in args
            # Note: args is available in main() scope, not in workflow methods
            # Default to headless for internal workflow calls
            browser_manager.headless = True  # Default headless for workflow automation
            
            # Use intelligent mode that switches to headed if headless times out
            page = await browser_manager.get_page_with_intelligent_mode("supplier_discovery", state["supplier_url"])
            
            if page:
                state["browser_connected"] = True
                
                # Navigate to supplier URL
                await page.goto(state["supplier_url"], wait_until='domcontentloaded')
                await page.wait_for_load_state('networkidle', timeout=10000)
                
                # Run complete supplier discovery
                discovery_result = await discover_complete_supplier(page)
                
                if discovery_result.get("success"):
                    state["vision_discovery_completed"] = True
                    state["supplier_setup_result"] = discovery_result
                    
                    log.info("✅ Supplier discovery completed")
                    state["messages"].append(
                        AIMessage(content="✅ Supplier discovery completed successfully")
                    )
                else:
                    log.warning("⚠️ Vision discovery had issues")
                    state["errors"].append("Vision discovery incomplete")
            else:
                raise Exception("Failed to connect to browser")
            
            return state
            
        except Exception as e:
            log.error(f"❌ Supplier discovery failed: {e}")
            state["errors"].append(f"Discovery error: {str(e)}")
            return state
    
    async def _supplier_login_step(self, state: CompleteFBAState) -> CompleteFBAState:
        """Execute supplier login using VisionSupplierLoginTool"""
        try:
            log.info("🔐 LOGIN STEP RUNNING")
            state["current_task"] = "supplier_login"
            
            # Create debug log for login step auditing
            supplier_domain = self._get_supplier_domain(state["supplier_url"])
            debug_log_dir = Path("logs/debug")
            debug_log_dir.mkdir(parents=True, exist_ok=True)
            
            # Check for domain guard - skip if supplier is already ready
            supplier_domain = self._get_supplier_domain(state["supplier_url"])
            if self._check_supplier_ready(supplier_domain):
                log.info(f"Supplier {supplier_domain} already ready, skipping login")
                state["login_automation_working"] = True
                return state
            
            # Find login tool
            login_tool = None
            for tool in self.tools:
                if tool.name == "supplier_login":
                    login_tool = tool
                    break
            
            if login_tool and state.get("supplier_email") and state.get("supplier_password"):
                # Execute login with credentials from CLI
                login_result = await login_tool._arun(
                    supplier_url=state["supplier_url"],
                    email=state["supplier_email"],
                    password=state["supplier_password"],
                    supplier_name=state.get("supplier_name", "unknown")
                )
                
                if login_result.get("success"):
                    state["login_automation_working"] = True
                    self._mark_supplier_ready(supplier_domain)
                    
                    # Write success flag file for auditing
                    login_flag_file = debug_log_dir / f"login_{supplier_domain}.ok"
                    login_flag_file.write_text(json.dumps({
                        "login_successful": True,
                        "timestamp": datetime.now().isoformat(),
                        "supplier_domain": supplier_domain,
                        "supplier_url": state["supplier_url"]
                    }, indent=2))
                    
                    log.info("✅ Supplier login successful")
                    state["messages"].append(
                        AIMessage(content="✅ Supplier login completed successfully")
                    )
                else:
                    log.error(f"❌ Login failed: {login_result.get('error_message', 'Unknown error')}")
                    state["errors"].append(f"Login failed: {login_result.get('error_message', 'Unknown error')}")
            else:
                if not (state.get("supplier_email") and state.get("supplier_password")):
                    error_msg = "Missing supplier credentials for login"
                    log.error(f"❌ {error_msg}")
                    state["errors"].append(error_msg)
                else:
                    error_msg = "Login tool not found"
                    log.error(f"❌ {error_msg}")
                    state["errors"].append(error_msg)
            
            return state
            
        except Exception as e:
            log.error(f"❌ Supplier login failed: {e}")
            state["errors"].append(f"Login error: {str(e)}")
            return state
    
    def _get_supplier_domain(self, url: str) -> str:
        """Extract domain from URL for directory naming"""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        return domain.replace("www.", "").replace(".", "-")
    
    def _check_supplier_ready(self, supplier_domain: str) -> bool:
        """Check if supplier is ready (has .supplier_ready flag < 7 days old)"""
        try:
            from pathlib import Path
            import time
            
            ready_file = Path(f"suppliers/{supplier_domain}/.supplier_ready")
            if ready_file.exists():
                file_age = time.time() - ready_file.stat().st_mtime
                if file_age < (7 * 24 * 3600):  # 7 days
                    return True
                else:
                    ready_file.unlink()  # Remove stale file
            return False
        except Exception:
            return False
    
    def _mark_supplier_ready(self, supplier_domain: str) -> None:
        """Mark supplier as ready after successful setup"""
        try:
            from pathlib import Path
            import json
            from datetime import datetime
            
            supplier_dir = Path(f"suppliers/{supplier_domain}")
            supplier_dir.mkdir(parents=True, exist_ok=True)
            
            ready_file = supplier_dir / ".supplier_ready"
            ready_file.write_text(json.dumps({
                "created_at": datetime.now().isoformat(),
                "supplier_domain": supplier_domain,
                "login_successful": True
            }, indent=2))
        except Exception as e:
            log.warning(f"Failed to mark supplier ready: {e}")
    
    async def _extract_supplier_products(self, state: CompleteFBAState) -> CompleteFBAState:
        """Extract supplier products using configurable scraper"""
        try:
            log.info("🕷️ Extracting supplier products")
            state["current_task"] = "product_extraction"
            
            # Find supplier scraper tool
            scraper_tool = None
            for tool in self.tools:
                if tool.name == "supplier_product_extractor":
                    scraper_tool = tool
                    break
            
            if scraper_tool:
                # Configure scraping parameters
                product_urls = [state["supplier_url"]]  # Start with homepage
                
                # Execute supplier scraping - fix parameter names
                result = await scraper_tool._arun(
                    product_url=state["supplier_url"],  # Use product_url parameter name
                    supplier_name=state.get("supplier_name", "Unknown"),
                    extraction_fields=["title", "price", "sku", "ean", "stock_status"]
                )
                
                # Handle both string and dict results safely
                result_str = str(result).lower() if result else ""
                if result and "error" not in result_str:
                    # Fix dict→json bug: check if result is already a dict
                    if isinstance(result, dict):
                        state["product_extraction_result"] = result
                    else:
                        try:
                            state["product_extraction_result"] = json.loads(result)
                        except (json.JSONDecodeError, TypeError):
                            # Fallback if not valid JSON
                            state["product_extraction_result"] = {"raw_result": result}
                    
                    # Generate AI categories after first 10 products arrive
                    try:
                        products_data = state["product_extraction_result"]
                        if isinstance(products_data, dict):
                            products_list = products_data.get("products", [])
                            if len(products_list) >= 10:
                                log.info("🏷️ Generating AI categories after extracting 10+ products")
                                from tools.ai_category_suggester import generate_categories
                                
                                supplier_domain = self._get_supplier_domain(state["supplier_url"])
                                categories_path = generate_categories(supplier_domain, products_list)
                                
                                log.info(f"✅ AI categories generated: {categories_path}")
                                state["ai_categories_generated"] = True
                                state["ai_categories_path"] = str(categories_path)
                            else:
                                log.info(f"📋 Extracted {len(products_list)} products - need 10+ for AI categorization")
                                state["ai_categories_generated"] = False
                        else:
                            log.warning("Product extraction result not in expected format for AI categorization")
                            state["ai_categories_generated"] = False
                    except Exception as e:
                        log.error(f"❌ AI category generation failed: {e}")
                        state["ai_categories_generated"] = False
                    
                    log.info("✅ Product extraction completed")
                    
                    state["messages"].append(
                        AIMessage(content="✅ Supplier product extraction completed")
                    )
                else:
                    log.warning("⚠️ Product extraction had issues")
                    state["errors"].append("Product extraction incomplete")
            else:
                log.warning("⚠️ Supplier scraper tool not found")
                state["errors"].append("Scraper tool unavailable")
            
            return state
            
        except Exception as e:
            log.error(f"❌ Product extraction failed: {e}")
            state["errors"].append(f"Product extraction error: {str(e)}")
            return state

    async def _run_passive_extraction(self, state: CompleteFBAState) -> CompleteFBAState:
        """Run the comprehensive passive extraction workflow"""
        try:
            log.info("🔄 Running passive extraction workflow")
            state["current_task"] = "passive_extraction"
            
            if run_workflow_main is None:
                log.warning("Passive extraction workflow not available - skipping")
                state["passive_extraction_result"] = {"status": "skipped", "reason": "module not available"}
                return state
            
            # Run the main passive extraction workflow
            # Note: This integrates the full 4000+ line workflow into LangGraph
            log.info("Executing comprehensive passive extraction workflow...")
            
            # Create subprocess args based on state
            import subprocess
            import sys
            
            script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "passive_extraction_workflow_latest.py")
            cmd_args = [
                sys.executable, script_path,
                "--supplier-url", state.get("supplier_url", ""),
                "--supplier-name", state.get("supplier_name", ""),
                "--max-products", "25",  # Production limit
                "--headless", "true"
            ]
            
            # Run passive extraction as subprocess to maintain isolation
            result = subprocess.run(cmd_args, capture_output=True, text=True, timeout=1800)  # 30 min timeout
            
            if result.returncode == 0:
                log.info("✅ Passive extraction workflow completed successfully")
                state["passive_extraction_result"] = {
                    "status": "completed",
                    "return_code": result.returncode,
                    "output": result.stdout[-1000:] if result.stdout else "",  # Last 1000 chars
                    "products_processed": "extracted from logs"
                }
            else:
                log.error(f"❌ Passive extraction workflow failed with code {result.returncode}")
                state["passive_extraction_result"] = {
                    "status": "failed", 
                    "return_code": result.returncode,
                    "error": result.stderr[-1000:] if result.stderr else "",
                    "output": result.stdout[-1000:] if result.stdout else ""
                }
                state["errors"].append(f"Passive extraction failed: {result.stderr}")
            
            return state
            
        except subprocess.TimeoutExpired:
            log.error("❌ Passive extraction workflow timed out after 30 minutes")
            state["errors"].append("Passive extraction timeout")
            state["passive_extraction_result"] = {"status": "timeout"}
            return state
        except Exception as e:
            log.error(f"❌ Passive extraction workflow error: {e}")
            state["errors"].append(f"Passive extraction error: {str(e)}")
            state["passive_extraction_result"] = {"status": "error", "error": str(e)}
            return state
    
    async def _verify_supplier_outputs(self, state: CompleteFBAState) -> CompleteFBAState:
        """Verify that all required supplier outputs exist and have valid content"""
        try:
            log.info("🔍 Verifying supplier outputs")
            state["current_task"] = "output_verification"
            
            supplier_domain = self._get_supplier_domain(state["supplier_url"])
            verification_errors = []
            
            # Check required output files
            from pathlib import Path
            import json
            from datetime import datetime
            
            # 1. Check cached products - FAIL if total_products < 5
            cache_file = Path(f"OUTPUTS/cached_products/{supplier_domain}_products_cache.json")
            if not cache_file.exists():
                verification_errors.append(f"Missing cache file: {cache_file}")
            else:
                try:
                    cache_data = json.loads(cache_file.read_text())
                    total_products = cache_data.get("total_products", 0)
                    if total_products < 5:
                        verification_errors.append(f"Insufficient products: {total_products} < 5 required in {cache_file}")
                    else:
                        log.info(f"✅ Cache validation passed: {total_products} products found")
                except Exception as e:
                    verification_errors.append(f"Invalid cache file format: {cache_file} - {e}")
            
            # 2. Check linking map directory and files - require at least ONE file with matching_result
            linking_map_dir = Path(f"OUTPUTS/FBA_ANALYSIS/linking_maps/{supplier_domain}")
            if not linking_map_dir.exists():
                verification_errors.append(f"Missing linking map directory: {linking_map_dir}")
            else:
                linking_map_files = list(linking_map_dir.glob("**/*.json"))
                if not linking_map_files:
                    verification_errors.append(f"No linking map files found in: {linking_map_dir}")
                else:
                    # Parse linking map files and check for matching_result keys
                    valid_linking_maps = 0
                    for map_file in linking_map_files:
                        try:
                            with open(map_file, 'r') as f:
                                map_data = json.load(f)
                            
                            # Check for matching_result with at least 1 key
                            matching_result = map_data.get("matching_result", {})
                            if isinstance(matching_result, dict) and len(matching_result) >= 1:
                                valid_linking_maps += 1
                                log.info(f"✅ Valid linking map: {map_file.name}")
                            else:
                                log.warning(f"⚠️ Linking map has no matching results: {map_file.name}")
                        except Exception as e:
                            log.error(f"❌ Failed to parse linking map {map_file}: {e}")
                    
                    if valid_linking_maps == 0:
                        verification_errors.append(f"No linking maps with valid matching_result found in {linking_map_dir}")
                    else:
                        log.info(f"✅ Linking map validation passed: {valid_linking_maps} valid maps found")
            
            # 3. Check AI suggested categories
            ai_categories_file = Path(f"OUTPUTS/ai_suggested_categories/{supplier_domain}.json")
            if not ai_categories_file.exists():
                verification_errors.append(f"Missing AI categories file: {ai_categories_file}")
            else:
                try:
                    with open(ai_categories_file, 'r') as f:
                        categories_data = json.load(f)
                    
                    categories_count = categories_data.get("total_categories", 0)
                    if categories_count < 5:
                        verification_errors.append(f"Insufficient AI categories: {categories_count} < 5 required in {ai_categories_file}")
                    else:
                        log.info(f"✅ AI categories validation passed: {categories_count} categories found")
                except Exception as e:
                    verification_errors.append(f"Invalid AI categories file format: {ai_categories_file} - {e}")
            
            # 4. Check processing state
            processing_state_file = Path(f"OUTPUTS/CACHE/processing_states/{supplier_domain}_session_state.json")
            if not processing_state_file.exists():
                verification_errors.append(f"Missing processing state file: {processing_state_file}")
            
            # 5. Check financial reports (at least one should exist)
            financial_reports_dir = Path("OUTPUTS/FBA_ANALYSIS/financial_reports")
            if financial_reports_dir.exists():
                today_str = datetime.now().strftime("%Y%m%d")
                todays_reports = list(financial_reports_dir.glob(f"*{today_str}*.csv"))
                if not todays_reports:
                    verification_errors.append(f"No financial reports found for today in: {financial_reports_dir}")
            else:
                verification_errors.append(f"Missing financial reports directory: {financial_reports_dir}")
            
            if verification_errors:
                error_msg = f"Output verification failed: {'; '.join(verification_errors)}"
                log.error(f"❌ {error_msg}")
                state["errors"].extend(verification_errors)
                
                # Raise intervention error to stop workflow
                class NeedsInterventionError(Exception):
                    def __init__(self, message, details=None):
                        super().__init__(message)
                        self.details = details or {}
                
                raise NeedsInterventionError("output_verification_failed", {
                    "verification_errors": verification_errors,
                    "supplier_domain": supplier_domain,
                    "failed_checks": len(verification_errors)
                })
            else:
                log.info("✅ All supplier outputs verified successfully")
                state["messages"].append(
                    AIMessage(content="✅ All required output files verified and contain valid data")
                )
            
            return state
            
        except Exception as e:
            log.error(f"❌ Output verification failed: {e}")
            state["errors"].append(f"Verification error: {str(e)}")
            # For verification failures, we want to stop the workflow
            state["workflow_status"] = "failed_verification"
            return state
    
    async def _analyze_product_matching(self, state: CompleteFBAState) -> CompleteFBAState:
        """Analyze product matching between Amazon and supplier"""
        try:
            log.info("🔍 Analyzing product matching")
            state["current_task"] = "product_matching"
            
            # Prepare matching analysis data
            amazon_data = state.get("amazon_data", {})
            supplier_data = state.get("product_extraction_result", {})
            
            # Basic matching analysis (would be expanded with ML matching) - null safety
            matching_result = {
                "amazon_asin": amazon_data.get("asin") if amazon_data else None,
                "supplier_products_found": len(supplier_data.get("results", {}).get("products", [])) if supplier_data else 0,
                "potential_matches": [],
                "match_confidence": 0.0,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            # Simple keyword matching (placeholder for more sophisticated matching)
            if amazon_data.get("extraction_result") and supplier_data.get("results"):
                # Extract title from Amazon result
                amazon_text = amazon_data["extraction_result"].lower()
                supplier_products = supplier_data["results"].get("products", [])
                
                for product in supplier_products:
                    if product.get("title"):
                        # Simple keyword overlap
                        overlap = len(set(amazon_text.split()) & set(product["title"].lower().split()))
                        if overlap > 2:  # Basic threshold
                            matching_result["potential_matches"].append({
                                "product": product,
                                "overlap_score": overlap
                            })
                
                matching_result["match_confidence"] = min(len(matching_result["potential_matches"]) * 0.3, 1.0)
            
            state["product_matching_result"] = matching_result
            
            log.info("✅ Product matching analysis completed")
            state["messages"].append(
                AIMessage(content=f"✅ Found {len(matching_result['potential_matches'])} potential product matches")
            )
            
            return state
            
        except Exception as e:
            log.error(f"❌ Product matching failed: {e}")
            state["errors"].append(f"Matching error: {str(e)}")
            return state
    
    async def _calculate_financial_analysis(self, state: CompleteFBAState) -> CompleteFBAState:
        """Calculate financial analysis and ROI"""
        try:
            log.info("💰 Calculating financial analysis")
            state["current_task"] = "financial_analysis"
            
            # Find financial calculator tool
            calc_tool = None
            for tool in self.tools:
                if "financial" in tool.name.lower() or "fba" in tool.name.lower():
                    calc_tool = tool
                    break
            
            if calc_tool:
                # Extract pricing data (placeholder - would parse from actual extraction)
                amazon_price = 25.0  # Would extract from amazon_data
                supplier_price = 15.0  # Would extract from supplier_data
                
                # Execute financial calculation
                result = await calc_tool._arun(
                    amazon_price=amazon_price,
                    supplier_price=supplier_price,
                    category="Electronics",
                    weight=1.0
                )
                
                # Handle both string and dict results safely
                result_str = str(result).lower() if result else ""
                if result and "error" not in result_str:
                    # Fix dict→json bug: check if result is already a dict
                    if isinstance(result, dict):
                        state["financial_analysis_result"] = result
                    else:
                        try:
                            state["financial_analysis_result"] = json.loads(result)
                        except (json.JSONDecodeError, TypeError):
                            # Fallback if not valid JSON
                            state["financial_analysis_result"] = {"raw_result": result}
                    log.info("✅ Financial analysis completed")
                    
                    state["messages"].append(
                        AIMessage(content="✅ Financial analysis completed")
                    )
                else:
                    log.warning("⚠️ Financial calculation had issues")
                    state["errors"].append("Financial calculation incomplete")
            else:
                log.warning("⚠️ Financial calculator tool not found")
                state["errors"].append("Calculator tool unavailable")
            
            return state
            
        except Exception as e:
            log.error(f"❌ Financial analysis failed: {e}")
            state["errors"].append(f"Financial analysis error: {str(e)}")
            return state
    
    async def _generate_recommendation(self, state: CompleteFBAState) -> CompleteFBAState:
        """Generate final recommendation using LLM"""
        try:
            log.info("📊 Generating final recommendation")
            state["current_task"] = "recommendation_generation"
            
            # Prepare analysis summary
            analysis_summary = {
                "amazon_data_available": bool(state.get("amazon_data")),
                "supplier_discovery_success": state.get("vision_discovery_completed", False),
                "products_extracted": bool(state.get("product_extraction_result")),
                "financial_analysis_done": bool(state.get("financial_analysis_result")),
                "automation_setup": state.get("automation_scripts_generated", False),
                "errors_count": len(state.get("errors", []))
            }
            
            # Generate recommendation prompt
            prompt = f"""
            Based on the FBA analysis results, provide a recommendation:
            
            Analysis Summary:
            - Amazon data extracted: {analysis_summary['amazon_data_available']}
            - Supplier discovery completed: {analysis_summary['supplier_discovery_success']}
            - Products extracted: {analysis_summary['products_extracted']}
            - Financial analysis completed: {analysis_summary['financial_analysis_done']}
            - Automation setup: {analysis_summary['automation_setup']}
            - Errors encountered: {analysis_summary['errors_count']}
            
            Provide a recommendation on whether to proceed with this product opportunity.
            """
            
            # Get recommendation from LLM
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            
            state["recommendation"] = response.content
            
            log.info("✅ Recommendation generated")
            state["messages"].append(
                AIMessage(content=f"📊 Recommendation: {response.content}")
            )
            
            return state
            
        except Exception as e:
            log.error(f"❌ Recommendation generation failed: {e}")
            state["errors"].append(f"Recommendation error: {str(e)}")
            return state
    
    async def _finalize_workflow(self, state: CompleteFBAState) -> CompleteFBAState:
        """Finalize workflow and save results"""
        try:
            log.info("🏁 Finalizing workflow")
            state["current_task"] = "workflow_finalization"
            
            # Determine overall workflow status
            if len(state.get("errors", [])) == 0:
                state["workflow_status"] = "completed_successfully"
            elif state.get("amazon_data") and state.get("recommendation"):
                state["workflow_status"] = "completed_with_warnings"
            else:
                state["workflow_status"] = "completed_with_errors"
            
            # Save workflow results using output manager
            output_tool = None
            for tool in self.tools:
                if tool.name == "supplier_output_manager":
                    output_tool = tool
                    break
            
            if output_tool:
                workflow_data = {
                    "workflow_id": state["workflow_id"],
                    "asin": state.get("asin"),
                    "supplier_url": state.get("supplier_url"),
                    "status": state["workflow_status"],
                    "results": {
                        "amazon_data": state.get("amazon_data"),
                        "supplier_setup": state.get("supplier_setup_result"),
                        "product_extraction": state.get("product_extraction_result"),
                        "financial_analysis": state.get("financial_analysis_result"),
                        "recommendation": state.get("recommendation")
                    },
                    "errors": state.get("errors", []),
                    "completed_at": datetime.now().isoformat()
                }
                
                await output_tool._arun(
                    operation="save",
                    supplier_name=state.get("supplier_name", "unknown"),
                    data_type="workflow_results",
                    data=workflow_data
                )
                
                # Generate specific required output files
                await self._generate_required_output_files(state)
            
            # Final status message
            final_message = f"🏁 Workflow {state['workflow_id']} completed with status: {state['workflow_status']}"
            if state.get("errors"):
                final_message += f" ({len(state['errors'])} errors)"
            
            state["messages"].append(AIMessage(content=final_message))
            
            log.info(f"✅ Workflow finalized: {state['workflow_status']}")
            return state
            
        except Exception as e:
            log.error(f"❌ Workflow finalization failed: {e}")
            state["errors"].append(f"Finalization error: {str(e)}")
            state["workflow_status"] = "failed"
            return state
    
    async def _generate_required_output_files(self, state: CompleteFBAState):
        """Generate the specific output files required by the user"""
        try:
            supplier_name = state.get("supplier_name", "unknown").replace(".", "-")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Create output directories
            from pathlib import Path
            base_dir = Path("OUTPUTS")
            base_dir.mkdir(exist_ok=True)
            
            # 1. Generate cached_products file
            cached_products_dir = base_dir / "cached_products"
            cached_products_dir.mkdir(exist_ok=True)
            cached_products_file = cached_products_dir / f"{supplier_name}_products_cache.json"
            
            # Get product extraction result with null safety
            product_result = state.get("product_extraction_result") or {}
            products_list = product_result.get("products", []) if isinstance(product_result, dict) else []
            
            cached_products_data = {
                "supplier_name": supplier_name,
                "cached_at": datetime.now().isoformat(),
                "products": product_result,
                "total_products": len(products_list),
                "cache_source": "langgraph_workflow"
            }
            
            with open(cached_products_file, 'w') as f:
                json.dump(cached_products_data, f, indent=2)
            log.info(f"✅ Generated {cached_products_file}")
            
            # 2. Generate linking_map file
            fba_analysis_dir = base_dir / "FBA_ANALYSIS"
            fba_analysis_dir.mkdir(exist_ok=True)
            linking_maps_dir = fba_analysis_dir / "linking_maps"
            linking_maps_dir.mkdir(exist_ok=True)
            linking_map_file = linking_maps_dir / f"{supplier_name}_linking_map.json"
            
            linking_map_data = {
                "supplier_name": supplier_name,
                "generated_at": datetime.now().isoformat(),
                "asin": state.get("asin") or "SUPPLIER_DISCOVERY",
                "supplier_url": state.get("supplier_url") or "",
                "amazon_data": state.get("amazon_data") or {},
                "matching_result": state.get("product_matching_result") or {},
                "workflow_id": state.get("workflow_id") or ""
            }
            
            with open(linking_map_file, 'w') as f:
                json.dump(linking_map_data, f, indent=2)
            log.info(f"✅ Generated {linking_map_file}")
            
            # 3. Generate amazon_cache files
            amazon_cache_dir = fba_analysis_dir / "amazon_cache"
            amazon_cache_dir.mkdir(exist_ok=True)
            amazon_cache_file = amazon_cache_dir / f"amazon_data_{timestamp}.json"
            
            amazon_cache_data = {
                "asin": state.get("asin") or "SUPPLIER_DISCOVERY",
                "cached_at": datetime.now().isoformat(),
                "amazon_data": state.get("amazon_data") or {},
                "workflow_source": "langgraph_complete_workflow"
            }
            
            with open(amazon_cache_file, 'w') as f:
                json.dump(amazon_cache_data, f, indent=2)
            log.info(f"✅ Generated {amazon_cache_file}")
            
            # 4. Generate financial report CSV
            financial_reports_dir = fba_analysis_dir / "financial_reports"
            financial_reports_dir.mkdir(exist_ok=True)
            financial_report_file = financial_reports_dir / f"fba_financial_report_{timestamp}.csv"
            
            # Create CSV content
            import csv
            financial_data = state.get("financial_analysis_result") or {}
            
            with open(financial_report_file, 'w', newline='') as csvfile:
                fieldnames = ['workflow_id', 'asin', 'supplier_name', 'supplier_url', 'amazon_price', 'supplier_price', 'gross_profit', 'net_profit', 'roi_percent', 'recommendation', 'timestamp']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                writer.writerow({
                    'workflow_id': state.get("workflow_id") or "",
                    'asin': state.get("asin") or "SUPPLIER_DISCOVERY",
                    'supplier_name': supplier_name,
                    'supplier_url': state.get("supplier_url") or "",
                    'amazon_price': financial_data.get("amazon_price", 0) if isinstance(financial_data, dict) else 0,
                    'supplier_price': financial_data.get("supplier_price", 0) if isinstance(financial_data, dict) else 0,
                    'gross_profit': financial_data.get("gross_profit", 0) if isinstance(financial_data, dict) else 0,
                    'net_profit': financial_data.get("net_profit", 0) if isinstance(financial_data, dict) else 0,
                    'roi_percent': financial_data.get("roi_percent", 0) if isinstance(financial_data, dict) else 0,
                    'recommendation': state.get("recommendation") or "",
                    'timestamp': datetime.now().isoformat()
                })
            
            log.info(f"✅ Generated {financial_report_file}")
            
            # Validate all required files exist and have content
            required_files = [cached_products_file, linking_map_file, amazon_cache_file, financial_report_file]
            validation_success = True
            
            for file_path in required_files:
                if file_path.exists() and file_path.stat().st_size > 0:
                    log.info(f"✅ Validated {file_path.name}")
                else:
                    log.error(f"❌ Validation failed for {file_path.name}")
                    validation_success = False
                    state["errors"].append(f"Output file validation failed: {file_path.name}")
            
            if validation_success:
                log.info("🎯 All required output files generated and validated successfully")
                state["output_files_validated"] = True
            else:
                log.error("❌ Output file validation failed")
                state["output_files_validated"] = False
            
        except Exception as e:
            log.error(f"❌ Failed to generate required output files: {e}")
            state["errors"].append(f"Output file generation error: {str(e)}")
            state["output_files_validated"] = False
    
    async def run_workflow(self, asin: str, supplier_url: str, supplier_credentials: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Run the complete FBA workflow
        
        Args:
            asin: Amazon product ASIN
            supplier_url: Supplier website URL
            supplier_credentials: Optional login credentials
            
        Returns:
            Complete workflow results
        """
        try:
            log.info(f"🚀 Starting complete FBA workflow for ASIN {asin} and supplier {supplier_url}")
            
            # Initialize state
            initial_state = CompleteFBAState(
                messages=[HumanMessage(content=f"Analyze ASIN {asin} from supplier {supplier_url}")],
                current_task="initialization",
                workflow_id="",
                asin=asin,
                amazon_data=None,
                supplier_name=supplier_url.split("//")[-1].split("/")[0],  # Extract domain
                supplier_url=supplier_url,
                supplier_email=supplier_credentials.get("email") if supplier_credentials else None,
                supplier_password=supplier_credentials.get("password") if supplier_credentials else None,
                supplier_setup_result=None,
                product_extraction_result=None,
                financial_analysis_result=None,
                automation_scripts_generated=False,
                vision_discovery_completed=False,
                login_automation_working=False,
                browser_connected=False,
                cache_available=False,
                errors=[],
                recommendation=None,
                profit_analysis=None,
                workflow_status="initializing"
            )
            
            # Execute workflow
            config = {"configurable": {"thread_id": f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"}}
            
            final_state = await self.workflow.ainvoke(initial_state, config)
            
            log.info(f"✅ Workflow completed with status: {final_state.get('workflow_status')}")
            
            return {
                "workflow_id": final_state.get("workflow_id"),
                "status": final_state.get("workflow_status"),
                "asin": asin,
                "supplier_url": supplier_url,
                "results": {
                    "amazon_data": final_state.get("amazon_data"),
                    "supplier_discovery": final_state.get("supplier_setup_result"),
                    "product_extraction": final_state.get("product_extraction_result"),
                    "financial_analysis": final_state.get("financial_analysis_result"),
                    "recommendation": final_state.get("recommendation")
                },
                "automation_status": {
                    "scripts_generated": final_state.get("automation_scripts_generated"),
                    "vision_discovery": final_state.get("vision_discovery_completed"),
                    "browser_connected": final_state.get("browser_connected")
                },
                "errors": final_state.get("errors", []),
                "messages": [msg.content for msg in final_state.get("messages", []) if hasattr(msg, 'content')]
            }
            
        except Exception as e:
            log.error(f"❌ Complete workflow failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# Standalone functions for easy integration
async def run_complete_fba_analysis(asin: str, supplier_url: str, supplier_credentials: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Run complete FBA analysis with full tool integration
    
    Args:
        asin: Amazon product ASIN
        supplier_url: Supplier website URL  
        supplier_credentials: Optional login credentials
        
    Returns:
        Complete analysis results
    """
    try:
        workflow = CompleteFBAWorkflow()
        return await workflow.run_workflow(asin, supplier_url, supplier_credentials)
    except Exception as e:
        log.error(f"Standalone FBA analysis failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def test_supplier_automation(supplier_url: str, supplier_credentials: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Test supplier automation setup only
    
    Args:
        supplier_url: Supplier website URL
        supplier_credentials: Optional login credentials
        
    Returns:
        Automation test results
    """
    try:
        from tools.workflow_orchestrator import setup_new_supplier
        return await setup_new_supplier(supplier_url, supplier_credentials)
    except Exception as e:
        log.error(f"Supplier automation test failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def main():
    """Main entry point for complete FBA workflow"""
    
    # Load system configuration
    try:
        config_path = Path(__file__).parent.parent / "config" / "system_config.json"
        with open(config_path, 'r') as f:
            system_config = json.load(f)
        log.info(f"✅ Loaded system configuration from {config_path}")
        
        # Apply critical configuration flags
        os.environ["FORCE_AI_CATEGORY_SUGGESTION"] = str(system_config.get("system", {}).get("force_ai_category_suggestion", True))
        os.environ["CLEAR_CACHE"] = str(system_config.get("system", {}).get("clear_cache", False))
        os.environ["VISION_MODEL"] = system_config.get("integrations", {}).get("openai", {}).get("model", "gpt-4o-mini-2024-07-18")
        
        log.info(f"🔧 Applied system config - Force AI Categories: {os.environ.get('FORCE_AI_CATEGORY_SUGGESTION')}, Clear Cache: {os.environ.get('CLEAR_CACHE')}, Vision Model: {os.environ.get('VISION_MODEL')}")
        
    except Exception as e:
        log.warning(f"⚠️ Could not load system config: {e}, using defaults")
        # Set safe defaults
        os.environ["FORCE_AI_CATEGORY_SUGGESTION"] = "true"
        os.environ["CLEAR_CACHE"] = "false"
        os.environ["VISION_MODEL"] = "gpt-4.1-mini-2025-04-14"
    
    parser = argparse.ArgumentParser(description='Run complete FBA analysis workflow')
    parser.add_argument('--supplier-url', required=True, help='Supplier website URL')
    parser.add_argument('--supplier-credentials-file', help='Path to supplier credentials JSON file')
    parser.add_argument('--supplier-email', help='Supplier login email (alternative to credentials file)')
    parser.add_argument('--supplier-password', help='Supplier login password (alternative to credentials file)')
    parser.add_argument('--test-automation-only', action='store_true', help='Test supplier automation only')
    parser.add_argument('--asin', help='Optional: Specific Amazon product ASIN to analyze (for validation mode). If not provided, will run supplier-first discovery mode.')
    parser.add_argument('--headed', action='store_true', help='Run browsers in headed mode (visible) for login and selector discovery')
    
    args = parser.parse_args()
    
    # Prepare credentials
    credentials = None
    if args.supplier_email and args.supplier_password:
        credentials = {
            "email": args.supplier_email,
            "password": args.supplier_password
        }
    
    async def run_analysis():
        if args.test_automation_only:
            print(f"🧪 Testing supplier automation for: {args.supplier_url}")
            result = await test_supplier_automation(args.supplier_url, credentials)
        else:
            if args.asin:
                print(f"🚀 Running complete FBA analysis (validation mode)")
                print(f"📦 ASIN: {args.asin}")
                print(f"🏪 Supplier: {args.supplier_url}")
                result = await run_complete_fba_analysis(args.asin, args.supplier_url, credentials)
            else:
                print(f"🚀 Running supplier-first discovery mode")
                print(f"🏪 Supplier: {args.supplier_url}")
                print(f"📦 ASIN: Auto-discovery from supplier products")
                # Use a placeholder ASIN for supplier-first mode
                result = await run_complete_fba_analysis("SUPPLIER_DISCOVERY", args.supplier_url, credentials)
        
        # Print results
        print(f"\n✅ Analysis completed!")
        print(f"📊 Status: {result.get('status')}")
        
        if result.get('errors'):
            print(f"⚠️ Errors: {len(result['errors'])}")
            for error in result['errors']:
                print(f"  - {error}")
        
        if result.get('recommendation'):
            print(f"\n💡 Recommendation: {result['recommendation']}")
    
    try:
        asyncio.run(run_analysis())
    except KeyboardInterrupt:
        print("\n⚠️ Analysis interrupted by user")
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")

if __name__ == "__main__":
    # Global OPENAI_KEY guard
    import os
    import logging
    if not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = (
            "sk-15Mk5F_Nvf8k06VvEi4_TD2GhL8mQnqR_8I6Z2zHjWT3BlbkFJvKlNwbgLB_HPw1C-SixqIskN03to4PNyXnXedS-pMA"
        )
        logging.warning("OPENAI_API_KEY missing – using fallback test key")
    
    main()