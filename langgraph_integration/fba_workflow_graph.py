# fba_workflow_graph.py
# Place in: langgraph_integration/ directory (create this folder)
# Main LangGraph workflow orchestrator

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
import logging
import json
import os

# Import your existing scripts as modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.passive_extraction_workflow_latest import PassiveExtractionWorkflow
from tools.FBA_Financial_calculator import FBAFinancialCalculator
from config.system_config_loader import SystemConfigLoader

class FBAWorkflowState(TypedDict):
    """Complete state management for FBA workflow"""
    # Supplier data
    supplier_products: List[Dict]
    supplier_cache_file: str
    supplier_extraction_complete: bool
    
    # Amazon data  
    amazon_matches: Dict[str, Any]
    linking_map: List[Dict]
    amazon_analysis_complete: bool
    
    # Financial data
    financial_reports: List[str]
    profitable_products: List[Dict]
    
    # Processing state
    current_phase: str  # SUPPLIER_EXTRACTION, AMAZON_ANALYSIS, COMPLETED
    processing_index: int
    error_state: str
    retry_count: int
    
    # Configuration
    workflow_config: Dict
    system_config: Dict
    
    # Results
    session_summary: Dict
    execution_logs: List[str]

class FBAWorkflowOrchestrator:
    """LangGraph orchestrator for FBA workflow"""
    
    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.config_loader = SystemConfigLoader()
        
        # Initialize state graph
        self.graph = self._build_workflow_graph()
        
    def _build_workflow_graph(self) -> StateGraph:
        """Build the complete LangGraph workflow"""
        
        # Create state graph
        workflow = StateGraph(FBAWorkflowState)
        
        # Add nodes (agents)
        workflow.add_node("initialization", self._initialization_agent)
        workflow.add_node("supplier_extraction", self._supplier_extraction_agent)
        workflow.add_node("amazon_analysis", self._amazon_analysis_agent)
        workflow.add_node("financial_calculation", self._financial_calculation_agent)
        workflow.add_node("error_recovery", self._error_recovery_agent)
        workflow.add_node("completion", self._completion_agent)
        
        # Define workflow edges
        workflow.add_edge(START, "initialization")
        workflow.add_conditional_edges(
            "initialization",
            self._route_from_initialization,
            {
                "supplier_extraction": "supplier_extraction",
                "amazon_analysis": "amazon_analysis", 
                "completion": "completion",
                "error": "error_recovery"
            }
        )
        workflow.add_conditional_edges(
            "supplier_extraction",
            self._route_from_supplier,
            {
                "amazon_analysis": "amazon_analysis",
                "error": "error_recovery",
                "completion": "completion"
            }
        )
        workflow.add_conditional_edges(
            "amazon_analysis", 
            self._route_from_amazon,
            {
                "financial_calculation": "financial_calculation",
                "error": "error_recovery",
                "completion": "completion"
            }
        )
        workflow.add_conditional_edges(
            "financial_calculation",
            self._route_from_financial,
            {
                "completion": "completion",
                "amazon_analysis": "amazon_analysis",  # For batch processing
                "error": "error_recovery"
            }
        )
        workflow.add_conditional_edges(
            "error_recovery",
            self._route_from_error,
            {
                "supplier_extraction": "supplier_extraction",
                "amazon_analysis": "amazon_analysis",
                "completion": "completion"
            }
        )
        workflow.add_edge("completion", END)
        
        # Add persistence
        memory = SqliteSaver.from_conn_string("sqlite:///fba_workflow.db")
        return workflow.compile(checkpointer=memory)
    
    # ========== AGENT IMPLEMENTATIONS ==========
    
    def _initialization_agent(self, state: FBAWorkflowState) -> FBAWorkflowState:
        """Initialize workflow and determine starting phase"""
        try:
            self.log.info("🔄 LangGraph: Initialization agent starting...")
            
            # Load configurations
            workflow_config = self.config_loader.get_workflow_config('poundwholesale_workflow')
            system_config = self.config_loader.get_system_config()
            
            # Update state
            state.update({
                "workflow_config": workflow_config,
                "system_config": system_config,
                "current_phase": "INITIALIZATION",
                "retry_count": 0,
                "execution_logs": state.get("execution_logs", []) + ["Initialization completed"]
            })
            
            # Determine starting phase using existing logic
            from tools.passive_extraction_workflow_latest import PassiveExtractionWorkflow
            temp_workflow = PassiveExtractionWorkflow(
                self.config_loader, workflow_config, None
            )
            
            # Use existing phase detection logic
            supplier_cache_file = os.path.join(
                temp_workflow.supplier_cache_dir,
                f"{workflow_config['supplier_name'].replace('.', '-')}_products_cache.json"
            )
            
            supplier_cache_count = 0
            if os.path.exists(supplier_cache_file):
                with open(supplier_cache_file, 'r') as f:
                    supplier_products = json.load(f)
                    supplier_cache_count = len(supplier_products)
                    state["supplier_products"] = supplier_products
            
            linking_map_count = len(temp_workflow.linking_map) if temp_workflow.linking_map else 0
            
            # Phase detection
            if supplier_cache_count == 0:
                state["current_phase"] = "SUPPLIER_EXTRACTION"
            elif linking_map_count == 0:
                state["current_phase"] = "AMAZON_ANALYSIS"
            elif linking_map_count < supplier_cache_count:
                state["current_phase"] = "AMAZON_ANALYSIS"
            else:
                state["current_phase"] = "COMPLETED"
            
            self.log.info(f"🔍 LangGraph Phase Detection: {state['current_phase']}")
            return state
            
        except Exception as e:
            self.log.error(f"🚨 Initialization agent error: {e}")
            state["error_state"] = f"Initialization failed: {str(e)}"
            return state
    
    def _supplier_extraction_agent(self, state: FBAWorkflowState) -> FBAWorkflowState:
        """Handle supplier product extraction"""
        try:
            self.log.info("🔄 LangGraph: Supplier extraction agent starting...")
            
            # Create workflow instance
            workflow = PassiveExtractionWorkflow(
                self.config_loader,
                state["workflow_config"],
                None  # Browser manager will be created internally
            )
            
            # Execute supplier extraction
            supplier_products = workflow._extract_supplier_products()
            
            state.update({
                "supplier_products": supplier_products,
                "supplier_extraction_complete": True,
                "current_phase": "AMAZON_ANALYSIS",
                "execution_logs": state.get("execution_logs", []) + [f"Supplier extraction completed: {len(supplier_products)} products"]
            })
            
            return state
            
        except Exception as e:
            self.log.error(f"🚨 Supplier extraction agent error: {e}")
            state["error_state"] = f"Supplier extraction failed: {str(e)}"
            state["retry_count"] = state.get("retry_count", 0) + 1
            return state
    
    def _amazon_analysis_agent(self, state: FBAWorkflowState) -> FBAWorkflowState:
        """Handle Amazon product analysis"""
        try:
            self.log.info("🔄 LangGraph: Amazon analysis agent starting...")
            
            # Create workflow instance
            workflow = PassiveExtractionWorkflow(
                self.config_loader,
                state["workflow_config"],
                None
            )
            
            # Process products for Amazon analysis
            supplier_products = state.get("supplier_products", [])
            if not supplier_products:
                state["error_state"] = "No supplier products available for Amazon analysis"
                return state
            
            # Execute Amazon analysis (using existing logic)
            linking_map_entries = []
            for product in supplier_products:
                try:
                    amazon_data = workflow._extract_amazon_data(product)
                    if amazon_data:
                        linking_entry = workflow._create_linking_map_entry(product, amazon_data)
                        linking_map_entries.append(linking_entry)
                except Exception as e:
                    self.log.warning(f"Amazon analysis failed for product {product.get('title', 'Unknown')}: {e}")
            
            state.update({
                "linking_map": linking_map_entries,
                "amazon_analysis_complete": True,
                "current_phase": "FINANCIAL_CALCULATION",
                "execution_logs": state.get("execution_logs", []) + [f"Amazon analysis completed: {len(linking_map_entries)} matches"]
            })
            
            return state
            
        except Exception as e:
            self.log.error(f"🚨 Amazon analysis agent error: {e}")
            state["error_state"] = f"Amazon analysis failed: {str(e)}"
            state["retry_count"] = state.get("retry_count", 0) + 1
            return state
    
    def _financial_calculation_agent(self, state: FBAWorkflowState) -> FBAWorkflowState:
        """Handle financial calculations and reporting"""
        try:
            self.log.info("🔄 LangGraph: Financial calculation agent starting...")
            
            linking_map = state.get("linking_map", [])
            if not linking_map:
                state["error_state"] = "No linking map available for financial calculation"
                return state
            
            # Initialize financial calculator
            calculator = FBAFinancialCalculator(
                state["system_config"],
                state["workflow_config"]["supplier_name"]
            )
            
            # Generate financial reports
            report_files = []
            profitable_products = []
            
            for entry in linking_map:
                try:
                    financial_data = calculator.calculate_profitability(entry)
                    if financial_data and financial_data.get("profitable", False):
                        profitable_products.append(financial_data)
                except Exception as e:
                    self.log.warning(f"Financial calculation failed for entry: {e}")
            
            # Generate report file
            if profitable_products:
                report_file = calculator.generate_report(profitable_products)
                report_files.append(report_file)
            
            state.update({
                "financial_reports": report_files,
                "profitable_products": profitable_products,
                "current_phase": "COMPLETED",
                "execution_logs": state.get("execution_logs", []) + [f"Financial calculation completed: {len(profitable_products)} profitable products"]
            })
            
            return state
            
        except Exception as e:
            self.log.error(f"🚨 Financial calculation agent error: {e}")
            state["error_state"] = f"Financial calculation failed: {str(e)}"
            state["retry_count"] = state.get("retry_count", 0) + 1
            return state
    
    def _error_recovery_agent(self, state: FBAWorkflowState) -> FBAWorkflowState:
        """Handle error recovery and retry logic"""
        try:
            self.log.info("🔄 LangGraph: Error recovery agent starting...")
            
            error_state = state.get("error_state", "Unknown error")
            retry_count = state.get("retry_count", 0)
            
            if retry_count >= 3:
                self.log.error(f"🚨 Maximum retries exceeded. Final error: {error_state}")
                state["current_phase"] = "FAILED"
                return state
            
            # Clear error state for retry
            state["error_state"] = ""
            
            # Determine retry phase based on where error occurred
            if "Supplier extraction" in error_state:
                state["current_phase"] = "SUPPLIER_EXTRACTION"
            elif "Amazon analysis" in error_state:
                state["current_phase"] = "AMAZON_ANALYSIS"
            elif "Financial calculation" in error_state:
                state["current_phase"] = "FINANCIAL_CALCULATION"
            else:
                state["current_phase"] = "INITIALIZATION"
            
            state["execution_logs"] = state.get("execution_logs", []) + [f"Error recovery: Retrying from {state['current_phase']} (attempt {retry_count + 1})"]
            
            return state
            
        except Exception as e:
            self.log.error(f"🚨 Error recovery agent error: {e}")
            state["current_phase"] = "FAILED"
            return state
    
    def _completion_agent(self, state: FBAWorkflowState) -> FBAWorkflowState:
        """Handle workflow completion and summary"""
        try:
            self.log.info("🔄 LangGraph: Completion agent starting...")
            
            # Generate session summary
            summary = {
                "supplier_products_count": len(state.get("supplier_products", [])),
                "amazon_matches_count": len(state.get("linking_map", [])),
                "profitable_products_count": len(state.get("profitable_products", [])),
                "financial_reports": state.get("financial_reports", []),
                "total_retry_count": state.get("retry_count", 0),
                "execution_logs": state.get("execution_logs", [])
            }
            
            state.update({
                "session_summary": summary,
                "current_phase": "COMPLETED",
                "execution_logs": state.get("execution_logs", []) + ["Workflow completed successfully"]
            })
            
            self.log.info(f"✅ LangGraph Workflow Completed: {summary}")
            return state
            
        except Exception as e:
            self.log.error(f"🚨 Completion agent error: {e}")
            state["error_state"] = f"Completion failed: {str(e)}"
            return state
    
    # ========== ROUTING FUNCTIONS ==========
    
    def _route_from_initialization(self, state: FBAWorkflowState) -> str:
        """Route from initialization based on detected phase"""
        if state.get("error_state"):
            return "error"
        
        phase = state.get("current_phase", "SUPPLIER_EXTRACTION")
        if phase == "SUPPLIER_EXTRACTION":
            return "supplier_extraction"
        elif phase == "AMAZON_ANALYSIS":
            return "amazon_analysis"
        elif phase == "COMPLETED":
            return "completion"
        else:
            return "supplier_extraction"
    
    def _route_from_supplier(self, state: FBAWorkflowState) -> str:
        """Route from supplier extraction"""
        if state.get("error_state"):
            return "error"
        if state.get("supplier_extraction_complete"):
            return "amazon_analysis"
        return "completion"
    
    def _route_from_amazon(self, state: FBAWorkflowState) -> str:
        """Route from Amazon analysis"""
        if state.get("error_state"):
            return "error"
        if state.get("amazon_analysis_complete"):
            return "financial_calculation"
        return "completion"
    
    def _route_from_financial(self, state: FBAWorkflowState) -> str:
        """Route from financial calculation"""
        if state.get("error_state"):
            return "error"
        return "completion"
    
    def _route_from_error(self, state: FBAWorkflowState) -> str:
        """Route from error recovery"""
        phase = state.get("current_phase", "INITIALIZATION")
        if phase == "FAILED":
            return "completion"
        elif phase == "SUPPLIER_EXTRACTION":
            return "supplier_extraction"
        elif phase == "AMAZON_ANALYSIS":
            return "amazon_analysis"
        else:
            return "completion"
    
    # ========== PUBLIC INTERFACE ==========
    
    def run_workflow(self, initial_state: Dict = None) -> Dict:
        """Run the complete FBA workflow"""
        try:
            # Initialize state
            if initial_state is None:
                initial_state = {
                    "supplier_products": [],
                    "amazon_matches": {},
                    "linking_map": [],
                    "financial_reports": [],
                    "profitable_products": [],
                    "current_phase": "INITIALIZATION",
                    "processing_index": 0,
                    "error_state": "",
                    "retry_count": 0,
                    "execution_logs": []
                }
            
            # Execute workflow
            result = self.graph.invoke(initial_state)
            
            return result
            
        except Exception as e:
            self.log.error(f"🚨 Workflow execution failed: {e}")
            return {"error": str(e), "current_phase": "FAILED"}

# Main execution interface
if __name__ == "__main__":
    # Initialize and run workflow
    orchestrator = FBAWorkflowOrchestrator()
    result = orchestrator.run_workflow()
    
    print("🎯 FBA LangGraph Workflow Result:")
    print(json.dumps(result.get("session_summary", {}), indent=2))