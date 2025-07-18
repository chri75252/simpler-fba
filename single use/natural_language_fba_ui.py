#!/usr/bin/env python3
"""
Natural Language FBA UI - Conversational Interface for Amazon FBA Analysis
==========================================================================

This provides a simple, Claude Code-style natural language interface where users can:
- Input criteria in natural language: "Analyze poundwholesale.co.uk for products with >20% ROI"
- Get responses in natural language about results, errors, or additional information needed
- Execute workflows using the proven original scripts (passive_extraction_workflow_latest.py)

USAGE:
    python natural_language_fba_ui.py

EXAMPLES:
    > "Analyze poundwholesale.co.uk for products with >20% ROI and >£5 profit"
    > "Check supplier xyz.com for items under £5 with good margins"
    > "Find profitable products on clearance-king.co.uk"
    > "Show me the last analysis results"
    > "What errors occurred in the last run?"
"""

import asyncio
import json
import logging
import os
import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class NaturalLanguageParser:
    """Parse natural language requests into structured parameters"""
    
    def __init__(self):
        # Common patterns for different request types
        self.url_pattern = re.compile(r'(https?://[^\s]+|[a-zA-Z0-9][a-zA-Z0-9\-]*\.[a-zA-Z]{2,})')
        self.roi_pattern = re.compile(r'(?:>|greater than|more than|above)\s*(\d+(?:\.\d+)?)%?\s*ROI', re.IGNORECASE)
        self.profit_pattern = re.compile(r'(?:>|greater than|more than|above)\s*£?(\d+(?:\.\d+)?)\s*profit', re.IGNORECASE)
        self.price_pattern = re.compile(r'(?:<|less than|under|below)\s*£?(\d+(?:\.\d+)?)', re.IGNORECASE)
        self.max_products_pattern = re.compile(r'(?:up to|maximum|max|limit)\s*(\d+)\s*products?', re.IGNORECASE)
    
    def parse_request(self, user_input: str) -> Dict[str, Any]:
        """Parse natural language input into structured parameters"""
        try:
            request = {
                "intent": self._determine_intent(user_input),
                "supplier_url": self._extract_url(user_input),
                "roi_threshold": self._extract_roi(user_input),
                "profit_threshold": self._extract_profit(user_input),
                "max_price": self._extract_max_price(user_input),
                "max_products": self._extract_max_products(user_input),
                "original_input": user_input,
                "needs_credentials": self._check_credentials_needed(user_input)
            }
            
            log.info(f"Parsed request: {request}")
            return request
            
        except Exception as e:
            log.error(f"Failed to parse request: {e}")
            return {
                "intent": "error",
                "error": str(e),
                "original_input": user_input
            }
    
    def _determine_intent(self, text: str) -> str:
        """Determine the user's intent from their input"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["analyze", "check", "find", "search"]):
            return "analyze_supplier"
        elif any(word in text_lower for word in ["show", "display", "results", "last"]):
            return "show_results"
        elif any(word in text_lower for word in ["error", "errors", "what went wrong", "failed"]):
            return "show_errors"
        elif any(word in text_lower for word in ["help", "how", "what can"]):
            return "help"
        else:
            return "analyze_supplier"  # Default intent
    
    def _extract_url(self, text: str) -> Optional[str]:
        """Extract supplier URL from text"""
        matches = self.url_pattern.findall(text)
        if matches:
            url = matches[0]
            # Add https:// if not present
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            return url
        return None
    
    def _extract_roi(self, text: str) -> Optional[float]:
        """Extract ROI threshold from text"""
        match = self.roi_pattern.search(text)
        if match:
            return float(match.group(1))
        return None
    
    def _extract_profit(self, text: str) -> Optional[float]:
        """Extract profit threshold from text"""
        match = self.profit_pattern.search(text)
        if match:
            return float(match.group(1))
        return None
    
    def _extract_max_price(self, text: str) -> Optional[float]:
        """Extract maximum price filter from text"""
        match = self.price_pattern.search(text)
        if match:
            return float(match.group(1))
        return None
    
    def _extract_max_products(self, text: str) -> Optional[int]:
        """Extract maximum products limit from text"""
        match = self.max_products_pattern.search(text)
        if match:
            return int(match.group(1))
        return None
    
    def _check_credentials_needed(self, text: str) -> bool:
        """Check if login credentials are mentioned or needed"""
        return any(word in text.lower() for word in ["login", "credentials", "password", "account"])

class OutputFileAnalyzer:
    """Analyze output files and generate natural language summaries"""
    
    def __init__(self):
        self.outputs_dir = Path("OUTPUTS")
        self.fba_analysis_dir = self.outputs_dir / "FBA_ANALYSIS"
        self.cache_dir = self.outputs_dir / "CACHE"
    
    def analyze_latest_results(self) -> Dict[str, Any]:
        """Analyze the most recent analysis results"""
        try:
            # Find the most recent FBA analysis file
            if not self.fba_analysis_dir.exists():
                return {"status": "no_results", "message": "No analysis results found"}
            
            analysis_files = list(self.fba_analysis_dir.glob("*.json"))
            if not analysis_files:
                return {"status": "no_results", "message": "No analysis files found"}
            
            # Get the most recent file
            latest_file = max(analysis_files, key=lambda f: f.stat().st_mtime)
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            return self._generate_summary(results, latest_file)
            
        except Exception as e:
            log.error(f"Failed to analyze results: {e}")
            return {"status": "error", "message": f"Failed to analyze results: {e}"}
    
    def _generate_summary(self, results: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """Generate natural language summary of results"""
        try:
            summary = {
                "status": "success",
                "file": str(file_path),
                "timestamp": results.get("started_at", "Unknown"),
                "summary": "",
                "details": {},
                "errors": [],
                "recommendations": []
            }
            
            # Analyze overall status
            overall_status = results.get("status", "unknown")
            
            if overall_status == "completed_successfully":
                summary["summary"] = "✅ Analysis completed successfully!"
            elif overall_status == "completed_with_errors":
                summary["summary"] = "⚠️ Analysis completed but encountered some issues."
            elif overall_status == "failed":
                summary["summary"] = "❌ Analysis failed to complete."
            else:
                summary["summary"] = f"📊 Analysis status: {overall_status}"
            
            # Extract phase results
            phases = results.get("phases", {})
            for phase_name, phase_data in phases.items():
                phase_status = phase_data.get("status", "unknown")
                
                if phase_status == "completed":
                    summary["details"][phase_name] = "✅ Completed successfully"
                elif phase_status == "failed":
                    error_msg = phase_data.get("error", "Unknown error")
                    summary["details"][phase_name] = f"❌ Failed: {error_msg}"
                    summary["errors"].append(f"{phase_name}: {error_msg}")
                else:
                    summary["details"][phase_name] = f"📊 Status: {phase_status}"
            
            # Extract workflow results if available
            workflow_result = None
            for phase_data in phases.values():
                if "workflow_result" in phase_data:
                    workflow_result = phase_data["workflow_result"]
                    break
            
            if workflow_result:
                # Analyze automation status
                automation = workflow_result.get("automation_status", {})
                if automation.get("scripts_generated"):
                    summary["recommendations"].append("✅ Automation scripts were generated successfully")
                if automation.get("vision_discovery"):
                    summary["recommendations"].append("✅ Vision-based discovery completed")
                if not automation.get("browser_connected"):
                    summary["recommendations"].append("⚠️ Browser connection issues detected")
                
                # Check for errors
                workflow_errors = workflow_result.get("errors", [])
                summary["errors"].extend(workflow_errors)
            
            # Generate recommendations based on errors
            if summary["errors"]:
                if any("headless" in error.lower() for error in summary["errors"]):
                    summary["recommendations"].append("💡 Try running with --headed flag for browser visibility")
                if any("unicode" in error.lower() or "charmap" in error.lower() for error in summary["errors"]):
                    summary["recommendations"].append("💡 Unicode encoding issues detected - recent fixes should resolve this")
                if any("asin" in error.lower() for error in summary["errors"]):
                    summary["recommendations"].append("💡 ASIN validation issues - try supplier-first discovery mode")
            
            return summary
            
        except Exception as e:
            log.error(f"Failed to generate summary: {e}")
            return {
                "status": "error",
                "message": f"Failed to generate summary: {e}",
                "raw_results": results
            }

class WorkflowRouter:
    """Route requests to appropriate workflow engines"""
    
    def __init__(self):
        self.original_workflow = "tools/passive_extraction_workflow_latest.py"
        self.langgraph_workflow = "langraph_integration/complete_fba_workflow.py"
    
    async def execute_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the parsed request using appropriate workflow"""
        try:
            intent = request.get("intent")
            
            if intent == "analyze_supplier":
                return await self._execute_supplier_analysis(request)
            elif intent == "show_results":
                analyzer = OutputFileAnalyzer()
                return analyzer.analyze_latest_results()
            elif intent == "show_errors":
                return await self._show_errors()
            elif intent == "help":
                return self._show_help()
            else:
                return {"status": "error", "message": f"Unknown intent: {intent}"}
                
        except Exception as e:
            log.error(f"Failed to execute request: {e}")
            return {"status": "error", "message": f"Execution failed: {e}"}
    
    async def _execute_supplier_analysis(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute supplier analysis using the original proven workflow"""
        try:
            supplier_url = request.get("supplier_url")
            if not supplier_url:
                return {
                    "status": "missing_info",
                    "message": "I need a supplier website URL to analyze. Please provide a URL like 'poundwholesale.co.uk'."
                }
            
            # Build command for original workflow
            cmd = ["python", self.original_workflow]
            cmd.extend(["--supplier-url", supplier_url])
            
            # Add optional parameters
            if request.get("max_products"):
                cmd.extend(["--max-products", str(request["max_products"])])
            
            if request.get("profit_threshold"):
                cmd.extend(["--min-price", str(request["profit_threshold"])])
            
            # Always use headed mode for better user experience
            cmd.extend(["--headless", "false"])
            
            log.info(f"Executing command: {' '.join(cmd)}")
            
            # Execute the workflow
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            return {
                "status": "executed",
                "command": " ".join(cmd),
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "message": "Analysis workflow executed. Check the output above for results."
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "message": "Analysis timed out after 5 minutes. The supplier website might be slow or there could be connection issues."
            }
        except Exception as e:
            log.error(f"Failed to execute analysis: {e}")
            return {"status": "error", "message": f"Analysis execution failed: {e}"}
    
    async def _show_errors(self) -> Dict[str, Any]:
        """Show recent errors from log files and output files"""
        try:
            analyzer = OutputFileAnalyzer()
            results = analyzer.analyze_latest_results()
            
            if results.get("errors"):
                return {
                    "status": "errors_found",
                    "message": f"Found {len(results['errors'])} errors in the last analysis:",
                    "errors": results["errors"],
                    "recommendations": results.get("recommendations", [])
                }
            else:
                return {
                    "status": "no_errors",
                    "message": "No errors found in the last analysis results."
                }
        except Exception as e:
            return {"status": "error", "message": f"Failed to check errors: {e}"}
    
    def _show_help(self) -> Dict[str, Any]:
        """Show help information"""
        return {
            "status": "help",
            "message": """
🤖 Natural Language FBA Assistant

I can help you analyze supplier websites for profitable Amazon FBA products using natural language commands.

**Example Commands:**
• "Analyze poundwholesale.co.uk for products with >20% ROI"
• "Check supplier xyz.com for items under £5 with good margins"
• "Find profitable products on clearance-king.co.uk"
• "Show me the last analysis results"
• "What errors occurred in the last run?"

**What I can understand:**
• Supplier URLs (poundwholesale.co.uk, clearance-king.co.uk, etc.)
• ROI thresholds (>20% ROI, above 15% ROI)
• Profit thresholds (>£5 profit, more than £10 profit)
• Price limits (under £5, less than £20)
• Product limits (up to 100 products, maximum 50 items)

**Features:**
• Uses the proven original workflow scripts
• Provides natural language explanations of results
• Shows errors in plain English with suggestions
• Supports both headed and headless browser modes
            """.strip()
        }

class NaturalLanguageFBAUI:
    """Main natural language interface for FBA analysis"""
    
    def __init__(self):
        self.parser = NaturalLanguageParser()
        self.router = WorkflowRouter()
        self.analyzer = OutputFileAnalyzer()
        
        print("🤖 Natural Language FBA Assistant")
        print("=" * 50)
        print("I can help you analyze supplier websites for profitable FBA products.")
        print("Type your requests in natural language, or 'help' for examples.")
        print("Type 'quit' to exit.\n")
    
    async def run(self):
        """Run the interactive natural language interface"""
        try:
            while True:
                try:
                    # Get user input
                    user_input = input("FBA Assistant: ").strip()
                    
                    if not user_input:
                        continue
                    
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("👋 Goodbye! Happy FBA hunting!")
                        break
                    
                    # Parse the request
                    print(f"\n🔍 Understanding: '{user_input}'...")
                    request = self.parser.parse_request(user_input)
                    
                    # Execute the request
                    print("⚡ Processing...")
                    result = await self.router.execute_request(request)
                    
                    # Display the result
                    self._display_result(result)
                    print()  # Add spacing
                    
                except KeyboardInterrupt:
                    print("\n👋 Goodbye! Happy FBA hunting!")
                    break
                except Exception as e:
                    print(f"❌ An error occurred: {e}")
                    log.error(f"UI error: {e}")
                    
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            log.error(f"Fatal UI error: {e}")
    
    def _display_result(self, result: Dict[str, Any]):
        """Display results in a user-friendly format"""
        status = result.get("status", "unknown")
        
        if status == "executed":
            print("✅ Analysis completed!")
            print(f"📋 Command: {result.get('command', 'Unknown')}")
            
            if result.get("returncode") == 0:
                print("🎉 Workflow executed successfully!")
                print("\n📊 Output:")
                if result.get("stdout"):
                    print(result["stdout"])
            else:
                print("⚠️ Workflow completed with issues:")
                if result.get("stderr"):
                    print("❌ Errors:")
                    print(result["stderr"])
                if result.get("stdout"):
                    print("📋 Output:")
                    print(result["stdout"])
        
        elif status == "success":
            print("📊 Analysis Results:")
            print(result.get("summary", "No summary available"))
            
            details = result.get("details", {})
            if details:
                print("\n📋 Details:")
                for phase, status_msg in details.items():
                    print(f"  • {phase}: {status_msg}")
            
            errors = result.get("errors", [])
            if errors:
                print(f"\n⚠️ Issues found ({len(errors)}):")
                for error in errors[:5]:  # Limit to first 5 errors
                    print(f"  • {error}")
            
            recommendations = result.get("recommendations", [])
            if recommendations:
                print("\n💡 Recommendations:")
                for rec in recommendations:
                    print(f"  • {rec}")
        
        elif status == "missing_info":
            print(f"❓ {result.get('message', 'Missing information')}")
            
        elif status == "errors_found":
            print(f"⚠️ {result.get('message', 'Errors found')}")
            errors = result.get("errors", [])
            for error in errors[:5]:
                print(f"  • {error}")
            
            recommendations = result.get("recommendations", [])
            if recommendations:
                print("\n💡 Suggestions:")
                for rec in recommendations:
                    print(f"  • {rec}")
        
        elif status == "no_errors":
            print("✅ No errors found in recent analysis!")
            
        elif status == "no_results":
            print("📭 No analysis results found yet.")
            print("💡 Try running an analysis first: 'Analyze poundwholesale.co.uk'")
            
        elif status == "help":
            print(result.get("message", "Help information not available"))
            
        elif status == "timeout":
            print(f"⏰ {result.get('message', 'Operation timed out')}")
            
        elif status == "error":
            print(f"❌ {result.get('message', 'An error occurred')}")
            
        else:
            print(f"📋 Status: {status}")
            if "message" in result:
                print(result["message"])

def main():
    """Main entry point"""
    try:
        # Check if we're in the right directory
        if not os.path.exists("tools/passive_extraction_workflow_latest.py"):
            print("❌ Error: Please run this from the Amazon-FBA-Agent-System-v3 directory")
            print("The original workflow scripts need to be accessible.")
            return
        
        # Initialize and run the UI
        ui = NaturalLanguageFBAUI()
        asyncio.run(ui.run())
        
    except Exception as e:
        print(f"❌ Failed to start natural language UI: {e}")
        log.error(f"Startup error: {e}")

if __name__ == "__main__":
    main()