#!/usr/bin/env python3
"""
LangGraph FBA Agent Workflow

Main LangGraph workflow that orchestrates Vision-Enhanced Tools for Amazon FBA analysis.
Integrates with existing cache_manager.py patterns and maintains LangSmith tracing.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_core.runnables import RunnableLambda
    from langchain_openai import ChatOpenAI
    LANGGRAPH_AVAILABLE = True
except ImportError as e:
    LANGGRAPH_AVAILABLE = False
    logging.warning(f"LangGraph imports unavailable: {e}")

# Import our Vision-Enhanced Tools
from langraph_integration.vision_enhanced_tools import create_vision_enhanced_tools

# Environment setup for LangSmith
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "pr-healthy-inspection-84"

# Configure logging  
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# LangGraph State Schema
class FBAAgentState(TypedDict):
    """State schema for FBA analysis workflow"""
    # Core workflow state
    current_task: str
    asin: Optional[str]
    supplier_name: str
    supplier_url: Optional[str]
    
    # Authentication
    supplier_email: Optional[str] 
    supplier_password: Optional[str]
    
    # Cache references (not raw data)
    amazon_data_key: Optional[str]
    supplier_data_key: Optional[str]
    linking_map_key: Optional[str]
    
    # Vision/AI context
    vision_cache_hits: int
    retry_count: int
    errors: List[str]
    
    # Results and status
    extraction_results: Dict[str, Any]
    workflow_status: str
    
    # Human intervention
    requires_intervention: bool
    intervention_reason: Optional[str]
    
    # Messages for conversation flow
    messages: List[Dict[str, Any]]

# Node Functions for LangGraph
async def initialize_workflow_node(state: FBAAgentState) -> FBAAgentState:
    """Initialize the FBA workflow with input validation"""
    log.info("Initializing FBA analysis workflow")
    
    state["current_task"] = "initialize"
    state["workflow_status"] = "started"
    state["vision_cache_hits"] = 0
    state["retry_count"] = 0
    state["errors"] = []
    state["extraction_results"] = {}
    state["requires_intervention"] = False
    
    # Validate required inputs
    if not state.get("asin"):
        state["errors"].append("ASIN is required for Amazon extraction")
    
    if not state.get("supplier_name") or not state.get("supplier_url"):
        state["errors"].append("Supplier name and URL are required")
    
    if state["errors"]:
        state["workflow_status"] = "error"
        state["requires_intervention"] = True
        state["intervention_reason"] = "Missing required inputs"
    
    log.info(f"Workflow initialized with status: {state['workflow_status']}")
    return state

async def amazon_extraction_node(state: FBAAgentState) -> FBAAgentState:
    """Extract Amazon product data using Vision-Enhanced Tools"""
    log.info(f"Extracting Amazon data for ASIN: {state.get('asin')}")
    
    state["current_task"] = "amazon_extraction"
    
    try:
        # Get OpenAI API key from environment
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Create Vision-Enhanced Tools with cache configuration
        cache_config = {
            "type": "json_file",
            "directory": "OUTPUTS/CACHE/processing_states",
            "ttl_hours": 24
        }
        tools = create_vision_enhanced_tools(openai_api_key, cache_config)
        amazon_tool = tools[0]  # VisionAmazonExtractorTool
        
        # Extract Amazon product data using real tool
        log.info(f"Using real Amazon extraction tool for ASIN: {state['asin']}")
        extraction_result = await amazon_tool._arun(
            asin=state["asin"],
            use_cache=True
        )
        
        # Log the actual result structure for debugging
        log.info(f"Amazon extraction result structure: {type(extraction_result)}")
        log.info(f"Amazon extraction result keys: {list(extraction_result.keys()) if isinstance(extraction_result, dict) else 'Not a dict'}")
        if isinstance(extraction_result, dict):
            log.info(f"Success field: {extraction_result.get('success')}")
            log.info(f"Has data field: {'data' in extraction_result}")
            if extraction_result.get('data'):
                data = extraction_result['data']
                log.info(f"Data keys: {list(data.keys()) if isinstance(data, dict) else 'Data not a dict'}")
                if isinstance(data, dict):
                    log.info(f"Data title: {data.get('title', 'No title')[:50] if data.get('title') else 'No title'}")
                    log.info(f"Data extraction_successful: {data.get('extraction_successful')}")
        
        # Check if extraction was successful
        if extraction_result.get("success"):
            amazon_data = extraction_result["data"]
            amazon_data["extraction_source"] = extraction_result["source"]
            
            # Store in results
            state["extraction_results"]["amazon"] = amazon_data
            state["amazon_data_key"] = f"amazon_{state['asin']}_{datetime.now().strftime('%Y%m%d')}"
            
            log.info(f"Amazon extraction completed successfully (source: {extraction_result['source']})")
            
            # Log key extracted data
            if amazon_data.get("title"):
                log.info(f"Product title: {amazon_data['title'][:100]}...")
            if amazon_data.get("price"):
                log.info(f"Product price: {amazon_data['price']}")
        else:
            # Extraction failed
            error_msg = f"Amazon extraction failed: {extraction_result.get('error', 'Unknown error')}"
            log.error(error_msg)
            state["errors"].append(error_msg)
            state["retry_count"] += 1
            
            # Store failed result for debugging
            state["extraction_results"]["amazon"] = {
                "extraction_successful": False,
                "error": extraction_result.get("error"),
                "error_type": extraction_result.get("error_type"),
                "asin": state["asin"],
                "timestamp": datetime.now().isoformat()
            }
            
            if state["retry_count"] >= 3:
                state["requires_intervention"] = True
                state["intervention_reason"] = "Amazon extraction failed after 3 retries"
        
    except Exception as e:
        error_msg = f"Amazon extraction tool error: {str(e)}"
        log.error(error_msg)
        state["errors"].append(error_msg)
        state["retry_count"] += 1
        
        # Store error result
        state["extraction_results"]["amazon"] = {
            "extraction_successful": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "asin": state["asin"],
            "timestamp": datetime.now().isoformat()
        }
        
        if state["retry_count"] >= 3:
            state["requires_intervention"] = True
            state["intervention_reason"] = "Amazon extraction tool failed after 3 retries"
    
    return state

def _get_supplier_domain(supplier_url: str) -> str:
    """Extract domain from supplier URL for directory naming"""
    from urllib.parse import urlparse
    parsed = urlparse(supplier_url)
    domain = parsed.netloc.lower()
    # Remove www. prefix and replace dots with hyphens for directory naming
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain.replace('.', '-')

def _check_supplier_ready(supplier_name: str) -> bool:
    """Check if supplier domain guard flag exists and is still valid (7-day cache)"""
    try:
        suppliers_dir = Path("suppliers")
        domain_dir = suppliers_dir / supplier_name
        ready_flag = domain_dir / ".supplier_ready"
        
        if not ready_flag.exists():
            return False
        
        # Check if flag is still valid (7 days)
        flag_time = datetime.fromtimestamp(ready_flag.stat().st_mtime)
        expiry_time = flag_time + timedelta(days=7)
        
        if datetime.now() > expiry_time:
            log.info(f"Supplier ready flag expired for {supplier_name}, removing...")
            ready_flag.unlink(missing_ok=True)
            return False
        
        log.info(f"Supplier {supplier_name} still ready (flag created: {flag_time})")
        return True
        
    except Exception as e:
        log.warning(f"Error checking supplier ready flag for {supplier_name}: {e}")
        return False

def _mark_supplier_ready(supplier_name: str) -> None:
    """Mark supplier as ready by creating domain guard flag"""
    try:
        suppliers_dir = Path("suppliers")
        domain_dir = suppliers_dir / supplier_name
        
        # Create directory if it doesn't exist
        domain_dir.mkdir(parents=True, exist_ok=True)
        
        # Create ready flag
        ready_flag = domain_dir / ".supplier_ready"
        ready_flag.write_text(f"Supplier ready as of {datetime.now().isoformat()}")
        
        log.info(f"Marked supplier {supplier_name} as ready")
        
    except Exception as e:
        log.warning(f"Error marking supplier ready for {supplier_name}: {e}")

async def supplier_login_node(state: FBAAgentState) -> FBAAgentState:
    """Handle supplier login using Vision-Enhanced Tools with domain guard logic"""
    log.info(f"Logging into supplier: {state.get('supplier_name')}")
    
    state["current_task"] = "supplier_login"
    supplier_name = state["supplier_name"]
    supplier_url = state["supplier_url"]
    
    # Check domain guard - if supplier is already ready, skip login
    if _check_supplier_ready(supplier_name):
        log.info(f"Supplier {supplier_name} already ready, skipping login")
        state["extraction_results"]["supplier_login"] = {
            "success": True,
            "supplier_name": supplier_name,
            "method_used": "domain_guard_cache",
            "login_detected": True,
            "price_access_verified": True,
            "cached": True,
            "timestamp": datetime.now().isoformat()
        }
        return state
    
    # Validate credentials
    if not state.get("supplier_email") or not state.get("supplier_password"):
        error_msg = f"Missing credentials for supplier {supplier_name}"
        log.error(error_msg)
        state["errors"].append(error_msg)
        state["requires_intervention"] = True
        state["intervention_reason"] = "Missing supplier credentials"
        return state
    
    try:
        # Get OpenAI API key from environment
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Create Vision-Enhanced Tools with cache configuration
        cache_config = {
            "type": "json_file",
            "directory": "OUTPUTS/CACHE/processing_states",
            "ttl_hours": 24
        }
        tools = create_vision_enhanced_tools(openai_api_key, cache_config)
        login_tool = tools[1]  # VisionSupplierLoginTool
        
        # Perform actual login using real tool
        log.info(f"Using real supplier login tool for: {supplier_name}")
        login_result = await login_tool._arun(
            supplier_url=supplier_url,
            email=state["supplier_email"],
            password=state["supplier_password"],
            supplier_name=supplier_name
        )
        
        # Log the actual result structure for debugging
        log.info(f"Login result structure: {type(login_result)}")
        log.info(f"Login result keys: {list(login_result.keys()) if isinstance(login_result, dict) else 'Not a dict'}")
        if isinstance(login_result, dict):
            log.info(f"Login success: {login_result.get('success')}")
            log.info(f"Method used: {login_result.get('method_used')}")
            log.info(f"Login detected: {login_result.get('login_detected')}")
        
        # Check if login was successful
        if login_result.get("success"):
            # Mark supplier as ready for future operations
            _mark_supplier_ready(supplier_name)
            
            # Store successful login result
            state["extraction_results"]["supplier_login"] = login_result
            
            log.info(f"Supplier login successful for {supplier_name} (method: {login_result.get('method_used')})")
        else:
            # Login failed
            error_msg = f"Supplier login failed for {supplier_name}: {login_result.get('error', 'Unknown error')}"
            log.error(error_msg)
            state["errors"].append(error_msg)
            state["retry_count"] += 1
            
            # Store failed result for debugging
            state["extraction_results"]["supplier_login"] = {
                "success": False,
                "supplier_name": supplier_name,
                "error": login_result.get("error"),
                "error_message": login_result.get("error_message"),
                "timestamp": datetime.now().isoformat()
            }
            
            if state["retry_count"] >= 3:
                state["requires_intervention"] = True
                state["intervention_reason"] = "Supplier login failed after 3 retries"
        
    except Exception as e:
        error_msg = f"Supplier login tool error for {supplier_name}: {str(e)}"
        log.error(error_msg)
        state["errors"].append(error_msg)
        state["retry_count"] += 1
        
        # Store error result
        state["extraction_results"]["supplier_login"] = {
            "success": False,
            "supplier_name": supplier_name,
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat()
        }
        
        if state["retry_count"] >= 3:
            state["requires_intervention"] = True
            state["intervention_reason"] = "Supplier login tool failed after 3 retries"
    
    return state

async def product_location_node(state: FBAAgentState) -> FBAAgentState:
    """Locate products on supplier website using Vision-Enhanced Tools"""
    log.info(f"Locating products on: {state.get('supplier_url')}")
    
    state["current_task"] = "product_location"
    
    try:
        # For now, simulate product location
        # In full implementation, this would use VisionProductLocatorTool
        location_result = {
            "success": True,
            "product_url": f"{state['supplier_url']}/sample-product-123",
            "method_used": "vision_enhanced",
            "navigation_dump": ["homepage", "category_page", "product_page"],
            "timestamp": datetime.now().isoformat()
        }
        
        state["extraction_results"]["product_location"] = location_result
        
        # Check if Vision API was used
        if location_result.get("method_used") == "vision_enhanced":
            state["vision_cache_hits"] += 1
        
        log.info("Product location completed successfully")
        
    except Exception as e:
        error_msg = f"Product location failed: {str(e)}"
        log.error(error_msg)
        state["errors"].append(error_msg)
        state["requires_intervention"] = True
        state["intervention_reason"] = "Product location failed"
    
    return state

async def supplier_extraction_node(state: FBAAgentState) -> FBAAgentState:
    """Extract supplier product data using Vision-Enhanced Tools"""
    log.info("Extracting supplier product data")
    
    state["current_task"] = "supplier_extraction"
    
    try:
        # Get product URL from location results
        product_url = state["extraction_results"]["product_location"]["product_url"]
        
        # For now, simulate extraction
        # In full implementation, this would use VisionProductExtractorTool
        supplier_data = {
            "url": product_url,
            "title": "Sample Supplier Product",
            "price": "£15.99",
            "sku": "SUP123456",
            "ean": "1234567890123",
            "stock_status": "in_stock",
            "extraction_successful": True,
            "timestamp": datetime.now().isoformat()
        }
        
        state["extraction_results"]["supplier"] = supplier_data
        state["supplier_data_key"] = f"supplier_{state['supplier_name']}_{datetime.now().strftime('%Y%m%d')}"
        
        log.info("Supplier extraction completed successfully")
        
    except Exception as e:
        error_msg = f"Supplier extraction failed: {str(e)}"
        log.error(error_msg)
        state["errors"].append(error_msg)
        state["requires_intervention"] = True
        state["intervention_reason"] = "Supplier extraction failed"
    
    return state

async def create_linking_map_node(state: FBAAgentState) -> FBAAgentState:
    """Create linking map between Amazon and supplier products"""
    log.info("Creating product linking map")
    
    state["current_task"] = "create_linking_map"
    
    try:
        amazon_data = state["extraction_results"].get("amazon", {})
        supplier_data = state["extraction_results"].get("supplier", {})
        
        # Create linking map
        linking_map = {
            "amazon_asin": amazon_data.get("asin"),
            "amazon_title": amazon_data.get("title"),
            "amazon_price": amazon_data.get("price"),
            "supplier_name": state["supplier_name"],
            "supplier_url": supplier_data.get("url"),
            "supplier_title": supplier_data.get("title"),
            "supplier_price": supplier_data.get("price"),
            "supplier_sku": supplier_data.get("sku"),
            "supplier_ean": supplier_data.get("ean"),
            "match_confidence": 0.95,  # Simulated confidence score
            "created_at": datetime.now().isoformat()
        }
        
        state["extraction_results"]["linking_map"] = linking_map
        state["linking_map_key"] = f"linking_{state['asin']}_{state['supplier_name']}"
        state["workflow_status"] = "completed"
        
        log.info("Linking map created successfully")
        
    except Exception as e:
        error_msg = f"Linking map creation failed: {str(e)}"
        log.error(error_msg)
        state["errors"].append(error_msg)
        state["workflow_status"] = "error"
    
    return state

async def error_handling_node(state: FBAAgentState) -> FBAAgentState:
    """Handle errors and determine if human intervention is needed"""
    log.warning("Processing workflow errors")
    
    state["current_task"] = "error_handling"
    
    # Analyze errors
    critical_errors = [error for error in state["errors"] if "failed" in error.lower()]
    
    if critical_errors:
        state["requires_intervention"] = True
        state["intervention_reason"] = f"Critical errors: {'; '.join(critical_errors[:2])}"
        state["workflow_status"] = "requires_intervention"
    else:
        # Minor errors, can continue
        state["workflow_status"] = "warning"
    
    log.info(f"Error handling completed. Status: {state['workflow_status']}")
    return state

def should_require_intervention(state: FBAAgentState) -> str:
    """Conditional edge to determine if human intervention is needed"""
    if state.get("requires_intervention", False):
        return "human_intervention"
    elif state.get("workflow_status") == "completed":
        return END
    elif state.get("workflow_status") == "error":
        return END  # Stop on errors instead of looping
    elif state.get("errors") and state.get("current_task") != "error_handling":
        return "error_handling"  # Only go to error handling if not already there
    else:
        # Continue workflow
        current_task = state.get("current_task", "")
        if current_task == "initialize":
            return "amazon_extraction"
        elif current_task == "amazon_extraction":
            return "supplier_login"
        elif current_task == "supplier_login":
            return "product_location"
        elif current_task == "product_location":
            return "supplier_extraction"
        elif current_task == "supplier_extraction":
            return "create_linking_map"
        elif current_task == "error_handling":
            return END  # End after error handling
        else:
            return END

def create_fba_workflow() -> StateGraph:
    """Create the main FBA analysis workflow"""
    log.info("Creating FBA LangGraph workflow")
    
    # Create the state graph
    workflow = StateGraph(FBAAgentState)
    
    # Add nodes
    workflow.add_node("initialize", initialize_workflow_node)
    workflow.add_node("amazon_extraction", amazon_extraction_node)
    workflow.add_node("supplier_login", supplier_login_node)
    workflow.add_node("product_location", product_location_node) 
    workflow.add_node("supplier_extraction", supplier_extraction_node)
    workflow.add_node("create_linking_map", create_linking_map_node)
    workflow.add_node("error_handling", error_handling_node)
    workflow.add_node("human_intervention", lambda state: {**state, "workflow_status": "paused_for_human"})
    
    # Set entry point
    workflow.set_entry_point("initialize")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "initialize",
        should_require_intervention
    )
    
    workflow.add_conditional_edges(
        "amazon_extraction", 
        should_require_intervention
    )
    
    workflow.add_conditional_edges(
        "supplier_login",
        should_require_intervention
    )
    
    workflow.add_conditional_edges(
        "product_location",
        should_require_intervention
    )
    
    workflow.add_conditional_edges(
        "supplier_extraction",
        should_require_intervention
    )
    
    workflow.add_conditional_edges(
        "create_linking_map",
        should_require_intervention
    )
    
    workflow.add_conditional_edges(
        "error_handling",
        should_require_intervention
    )
    
    # Human intervention leads to end for now
    workflow.add_edge("human_intervention", END)
    
    return workflow

# Main execution function
async def run_fba_analysis(
    asin: str,
    supplier_name: str,
    supplier_url: str,
    supplier_email: Optional[str] = None,
    supplier_password: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run the complete FBA analysis workflow
    
    Args:
        asin: Amazon product ASIN
        supplier_name: Name/identifier for the supplier
        supplier_url: Supplier website URL
        supplier_email: Login email (if authentication required)
        supplier_password: Login password (if authentication required)
        
    Returns:
        Complete workflow results
    """
    
    # Create workflow
    workflow = create_fba_workflow()
    
    # Add memory for checkpoints and set recursion limit
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory, debug=True)
    
    # Initialize state
    initial_state: FBAAgentState = {
        "current_task": "",
        "asin": asin,
        "supplier_name": supplier_name,
        "supplier_url": supplier_url,
        "supplier_email": supplier_email,
        "supplier_password": supplier_password,
        "amazon_data_key": None,
        "supplier_data_key": None,
        "linking_map_key": None,
        "vision_cache_hits": 0,
        "retry_count": 0,
        "errors": [],
        "extraction_results": {},
        "workflow_status": "pending",
        "requires_intervention": False,
        "intervention_reason": None,
        "messages": []
    }
    
    # Run workflow
    config = {"configurable": {"thread_id": f"fba_analysis_{asin}_{supplier_name}"}}
    
    try:
        log.info(f"Starting FBA analysis for ASIN: {asin}, Supplier: {supplier_name}")
        
        # Execute workflow
        final_state = None
        async for output in app.astream(initial_state, config):
            for node_name, node_output in output.items():
                log.info(f"Completed node: {node_name}")
                final_state = node_output
        
        log.info(f"Workflow completed with status: {final_state.get('workflow_status')}")
        return final_state
        
    except Exception as e:
        log.error(f"Workflow execution failed: {e}")
        return {
            "workflow_status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Example usage and testing
async def test_fba_workflow():
    """Test the FBA workflow with sample data"""
    print("🚀 Testing FBA LangGraph Workflow")
    
    # Test with sample data
    result = await run_fba_analysis(
        asin="B000BIUGTQ",
        supplier_name="poundwholesale-co-uk", 
        supplier_url="https://www.poundwholesale.co.uk",
        supplier_email="info@theblacksmithmarket.com",
        supplier_password="0Dqixm9c&"
    )
    
    print(f"\n📊 Workflow Results:")
    print(f"Status: {result.get('workflow_status')}")
    print(f"Vision Cache Hits: {result.get('vision_cache_hits', 0)}")
    print(f"Retry Count: {result.get('retry_count', 0)}")
    print(f"Errors: {len(result.get('errors', []))}")
    
    if result.get('extraction_results'):
        print(f"\n📦 Extraction Results:")
        for key, data in result['extraction_results'].items():
            print(f"  {key}: {'✅' if data.get('success') or data.get('extraction_successful') else '❌'}")
    
    if result.get('requires_intervention'):
        print(f"\n⚠️ Requires Human Intervention: {result.get('intervention_reason')}")
    
    print("\n🎉 FBA Workflow Test Completed!")
    return result

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test FBA LangGraph Workflow')
    parser.add_argument('--asin', default='B000BIUGTQ', help='ASIN to test with')
    parser.add_argument('--supplier-name', default='poundwholesale-co-uk', help='Supplier name')
    parser.add_argument('--supplier-url', default='https://www.poundwholesale.co.uk', help='Supplier URL')
    parser.add_argument('--supplier-email', default='info@theblacksmithmarket.com', help='Supplier email')
    parser.add_argument('--supplier-password', default='0Dqixm9c&', help='Supplier password')
    
    args = parser.parse_args()
    
    async def test_with_args():
        print("🚀 Testing FBA LangGraph Workflow")
        result = await run_fba_analysis(
            asin=args.asin,
            supplier_name=args.supplier_name,
            supplier_url=args.supplier_url,
            supplier_email=args.supplier_email,
            supplier_password=args.supplier_password
        )
        
        print(f"\n📊 Workflow Results:")
        print(f"Status: {result.get('workflow_status')}")
        print(f"Vision Cache Hits: {result.get('vision_cache_hits', 0)}")
        print(f"Retry Count: {result.get('retry_count', 0)}")
        print(f"Errors: {len(result.get('errors', []))}")
        
        if result.get('extraction_results'):
            print(f"\n📦 Extraction Results:")
            for key, data in result['extraction_results'].items():
                print(f"  {key}: {'✅' if data.get('success') or data.get('extraction_successful') else '❌'}")
        
        if result.get('requires_intervention'):
            print(f"\n⚠️ Requires Human Intervention: {result.get('intervention_reason')}")
        
        print("\n🎉 FBA Workflow Test Completed!")
        return result
    
    # Test the workflow with command line arguments
    asyncio.run(test_with_args())