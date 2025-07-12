#!/usr/bin/env python3
"""
Complete Tool Registry - Comprehensive LangGraph Integration Hub
================================================================

This module provides the central registry for ALL FBA system tools with LangGraph wrappers.
It combines critical system tools, medium priority tools, utility tools, and existing
vision-enhanced tools into a unified interface for complete system integration.

Registry includes:
- Critical System Tools (7 tools): Main orchestrator, workflow engine, guards, verification
- Medium Priority Tools (7 tools): Amazon extraction, category navigation, scraping, caching
- Utility Tools (7 tools): Login, financial calc, monitoring, output management
- Vision Enhanced Tools (4 tools): Vision-assisted extraction and navigation
- Enhanced FBA Tools (12 tools): Financial, scraping, cache, monitoring, output management

Total: 37+ tools with comprehensive LangGraph integration coverage
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union, Tuple

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# LangChain imports
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.callbacks import CallbackManagerForToolRun

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import all tool modules with error handling
try:
    # Critical System Tools
    from langraph_integration.critical_system_tools import create_critical_system_tools
    critical_tools_available = True
except ImportError as e:
    logger.warning(f"Critical system tools not available: {e}")
    critical_tools_available = False

try:
    # Medium Priority Tools
    from langraph_integration.medium_priority_tools import create_medium_priority_tools
    medium_tools_available = True
except ImportError as e:
    logger.warning(f"Medium priority tools not available: {e}")
    medium_tools_available = False

try:
    # Utility Tools
    from langraph_integration.utility_tools import create_utility_tools
    utility_tools_available = True
except ImportError as e:
    logger.warning(f"Utility tools not available: {e}")
    utility_tools_available = False

try:
    # Vision Enhanced Tools
    from langraph_integration.vision_enhanced_tools import create_vision_enhanced_tools
    vision_tools_available = True
except ImportError as e:
    logger.warning(f"Vision enhanced tools not available: {e}")
    vision_tools_available = False

try:
    # Enhanced FBA Tools
    from langraph_integration.enhanced_fba_tools import create_enhanced_fba_tools
    enhanced_tools_available = True
except ImportError as e:
    logger.warning(f"Enhanced FBA tools not available: {e}")
    enhanced_tools_available = False


class ToolRegistryError(Exception):
    """Custom exception for tool registry errors"""
    pass


class ToolCategory:
    """Tool category enumeration"""
    CRITICAL = "critical"
    MEDIUM = "medium"
    UTILITY = "utility"
    VISION = "vision"
    ENHANCED = "enhanced"
    ALL = "all"


class ToolRegistry:
    """
    Central registry for all FBA system tools with LangGraph integration
    
    Provides unified access to all tool categories with filtering, search,
    and validation capabilities.
    """
    
    def __init__(self):
        self.tools_cache = {}
        self.registry_initialized = False
        logger.info("🏛️ Tool Registry initialized")
    
    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """
        Get tools by category
        
        Args:
            category: Tool category (critical, medium, utility, vision, enhanced, all)
            
        Returns:
            List of tools in the specified category
        """
        if not self.registry_initialized:
            self._initialize_registry()
        
        if category == ToolCategory.ALL:
            return self._get_all_tools()
        
        return self.tools_cache.get(category, [])
    
    def get_tool_by_name(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a specific tool by name
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            The tool if found, None otherwise
        """
        if not self.registry_initialized:
            self._initialize_registry()
        
        for tools in self.tools_cache.values():
            for tool in tools:
                if tool.name == tool_name:
                    return tool
        return None
    
    def search_tools(self, search_term: str) -> List[BaseTool]:
        """
        Search tools by name or description
        
        Args:
            search_term: Term to search for in tool names or descriptions
            
        Returns:
            List of matching tools
        """
        if not self.registry_initialized:
            self._initialize_registry()
        
        matching_tools = []
        search_lower = search_term.lower()
        
        for tools in self.tools_cache.values():
            for tool in tools:
                if (search_lower in tool.name.lower() or 
                    search_lower in tool.description.lower()):
                    matching_tools.append(tool)
        
        return matching_tools
    
    def get_registry_status(self) -> Dict[str, Any]:
        """
        Get comprehensive registry status and statistics
        
        Returns:
            Dictionary with registry status information
        """
        if not self.registry_initialized:
            self._initialize_registry()
        
        status = {
            "registry_initialized": self.registry_initialized,
            "total_tools": len(self._get_all_tools()),
            "categories": {},
            "availability": {
                "critical_tools": critical_tools_available,
                "medium_tools": medium_tools_available,
                "utility_tools": utility_tools_available,
                "vision_tools": vision_tools_available,
                "enhanced_tools": enhanced_tools_available
            },
            "tool_list": []
        }
        
        for category, tools in self.tools_cache.items():
            status["categories"][category] = {
                "count": len(tools),
                "tools": [tool.name for tool in tools]
            }
        
        # Create comprehensive tool list
        for tool in self._get_all_tools():
            status["tool_list"].append({
                "name": tool.name,
                "description": tool.description[:100] + "..." if len(tool.description) > 100 else tool.description,
                "category": self._get_tool_category(tool.name)
            })
        
        return status
    
    def validate_tool_integration(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate tool integration and functionality
        
        Args:
            tool_name: Specific tool to validate (optional, validates all if None)
            
        Returns:
            Validation results
        """
        if not self.registry_initialized:
            self._initialize_registry()
        
        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "total_tools_tested": 0,
            "passed": 0,
            "failed": 0,
            "results": []
        }
        
        tools_to_test = [self.get_tool_by_name(tool_name)] if tool_name else self._get_all_tools()
        tools_to_test = [t for t in tools_to_test if t is not None]
        
        for tool in tools_to_test:
            validation_results["total_tools_tested"] += 1
            
            try:
                # Basic validation checks
                has_name = hasattr(tool, 'name') and tool.name
                has_description = hasattr(tool, 'description') and tool.description
                has_args_schema = hasattr(tool, 'args_schema')
                has_arun = hasattr(tool, '_arun')
                
                if all([has_name, has_description, has_args_schema, has_arun]):
                    validation_results["passed"] += 1
                    status = "passed"
                    message = "All validation checks passed"
                else:
                    validation_results["failed"] += 1
                    status = "failed"
                    missing = []
                    if not has_name: missing.append("name")
                    if not has_description: missing.append("description")
                    if not has_args_schema: missing.append("args_schema")
                    if not has_arun: missing.append("_arun method")
                    message = f"Missing: {', '.join(missing)}"
                
                validation_results["results"].append({
                    "tool_name": tool.name,
                    "status": status,
                    "message": message
                })
                
            except Exception as e:
                validation_results["failed"] += 1
                validation_results["results"].append({
                    "tool_name": getattr(tool, 'name', 'unknown'),
                    "status": "error",
                    "message": f"Validation error: {str(e)}"
                })
        
        return validation_results
    
    def _initialize_registry(self):
        """Initialize the tool registry by loading all available tools"""
        logger.info("🔄 Initializing tool registry...")
        
        # Load Critical System Tools
        if critical_tools_available:
            try:
                self.tools_cache[ToolCategory.CRITICAL] = create_critical_system_tools()
                logger.info(f"✅ Loaded {len(self.tools_cache[ToolCategory.CRITICAL])} critical system tools")
            except Exception as e:
                logger.error(f"❌ Failed to load critical system tools: {e}")
                self.tools_cache[ToolCategory.CRITICAL] = []
        else:
            self.tools_cache[ToolCategory.CRITICAL] = []
        
        # Load Medium Priority Tools
        if medium_tools_available:
            try:
                self.tools_cache[ToolCategory.MEDIUM] = create_medium_priority_tools()
                logger.info(f"✅ Loaded {len(self.tools_cache[ToolCategory.MEDIUM])} medium priority tools")
            except Exception as e:
                logger.error(f"❌ Failed to load medium priority tools: {e}")
                self.tools_cache[ToolCategory.MEDIUM] = []
        else:
            self.tools_cache[ToolCategory.MEDIUM] = []
        
        # Load Utility Tools
        if utility_tools_available:
            try:
                self.tools_cache[ToolCategory.UTILITY] = create_utility_tools()
                logger.info(f"✅ Loaded {len(self.tools_cache[ToolCategory.UTILITY])} utility tools")
            except Exception as e:
                logger.error(f"❌ Failed to load utility tools: {e}")
                self.tools_cache[ToolCategory.UTILITY] = []
        else:
            self.tools_cache[ToolCategory.UTILITY] = []
        
        # Load Vision Enhanced Tools
        if vision_tools_available:
            try:
                # Vision tools require OpenAI API key
                openai_api_key = os.getenv("OPENAI_API_KEY", "")
                if openai_api_key:
                    self.tools_cache[ToolCategory.VISION] = create_vision_enhanced_tools(openai_api_key)
                    logger.info(f"✅ Loaded {len(self.tools_cache[ToolCategory.VISION])} vision enhanced tools")
                else:
                    logger.warning("⚠️ OpenAI API key not available - skipping vision tools")
                    self.tools_cache[ToolCategory.VISION] = []
            except Exception as e:
                logger.error(f"❌ Failed to load vision enhanced tools: {e}")
                self.tools_cache[ToolCategory.VISION] = []
        else:
            self.tools_cache[ToolCategory.VISION] = []
        
        # Load Enhanced FBA Tools
        if enhanced_tools_available:
            try:
                self.tools_cache[ToolCategory.ENHANCED] = create_enhanced_fba_tools()
                logger.info(f"✅ Loaded {len(self.tools_cache[ToolCategory.ENHANCED])} enhanced FBA tools")
            except Exception as e:
                logger.error(f"❌ Failed to load enhanced FBA tools: {e}")
                self.tools_cache[ToolCategory.ENHANCED] = []
        else:
            self.tools_cache[ToolCategory.ENHANCED] = []
        
        self.registry_initialized = True
        total_tools = len(self._get_all_tools())
        logger.info(f"🎉 Tool registry initialized with {total_tools} total tools")
    
    def _get_all_tools(self) -> List[BaseTool]:
        """Get all tools from all categories"""
        all_tools = []
        for tools in self.tools_cache.values():
            all_tools.extend(tools)
        return all_tools
    
    def _get_tool_category(self, tool_name: str) -> str:
        """Get the category of a tool by its name"""
        for category, tools in self.tools_cache.items():
            for tool in tools:
                if tool.name == tool_name:
                    return category
        return "unknown"


# Global registry instance
_global_registry = None


def get_tool_registry() -> ToolRegistry:
    """
    Get the global tool registry instance (singleton pattern)
    
    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_all_fba_tools() -> List[BaseTool]:
    """
    Get all FBA tools from all categories
    
    Returns:
        List of all available FBA tools
    """
    registry = get_tool_registry()
    return registry.get_tools_by_category(ToolCategory.ALL)


def get_critical_tools() -> List[BaseTool]:
    """Get critical system tools"""
    registry = get_tool_registry()
    return registry.get_tools_by_category(ToolCategory.CRITICAL)


def get_medium_priority_tools() -> List[BaseTool]:
    """Get medium priority tools"""
    registry = get_tool_registry()
    return registry.get_tools_by_category(ToolCategory.MEDIUM)


def get_utility_tools() -> List[BaseTool]:
    """Get utility tools"""
    registry = get_tool_registry()
    return registry.get_tools_by_category(ToolCategory.UTILITY)


def get_vision_tools() -> List[BaseTool]:
    """Get vision enhanced tools"""
    registry = get_tool_registry()
    return registry.get_tools_by_category(ToolCategory.VISION)


def get_enhanced_tools() -> List[BaseTool]:
    """Get enhanced FBA tools"""
    registry = get_tool_registry()
    return registry.get_tools_by_category(ToolCategory.ENHANCED)


def find_tool(tool_name: str) -> Optional[BaseTool]:
    """
    Find a tool by name
    
    Args:
        tool_name: Name of the tool to find
        
    Returns:
        The tool if found, None otherwise
    """
    registry = get_tool_registry()
    return registry.get_tool_by_name(tool_name)


def search_tools(search_term: str) -> List[BaseTool]:
    """
    Search for tools by name or description
    
    Args:
        search_term: Search term
        
    Returns:
        List of matching tools
    """
    registry = get_tool_registry()
    return registry.search_tools(search_term)


def get_registry_status() -> Dict[str, Any]:
    """
    Get comprehensive registry status
    
    Returns:
        Dictionary with registry status and statistics
    """
    registry = get_tool_registry()
    return registry.get_registry_status()


def validate_all_tools() -> Dict[str, Any]:
    """
    Validate all tools in the registry
    
    Returns:
        Validation results for all tools
    """
    registry = get_tool_registry()
    return registry.validate_tool_integration()


def create_workflow_toolset(workflow_type: str) -> List[BaseTool]:
    """
    Create a curated toolset for specific workflow types
    
    Args:
        workflow_type: Type of workflow (complete, extraction, analysis, monitoring)
        
    Returns:
        List of tools optimized for the specified workflow
    """
    registry = get_tool_registry()
    
    if workflow_type == "complete":
        # Complete FBA workflow - all critical tools plus key supporting tools
        tools = registry.get_tools_by_category(ToolCategory.CRITICAL)
        tools.extend([
            registry.get_tool_by_name("amazon_playwright_extractor"),
            registry.get_tool_by_name("configurable_supplier_scraper"),
            registry.get_tool_by_name("cache_manager"),
            registry.get_tool_by_name("fba_financial_calculator"),
            registry.get_tool_by_name("system_monitor")
        ])
        return [t for t in tools if t is not None]
    
    elif workflow_type == "extraction":
        # Data extraction focused workflow
        return [
            registry.get_tool_by_name("passive_extraction_workflow"),
            registry.get_tool_by_name("amazon_playwright_extractor"),
            registry.get_tool_by_name("configurable_supplier_scraper"),
            registry.get_tool_by_name("vision_discovery_engine"),
            registry.get_tool_by_name("product_data_extractor"),
            registry.get_tool_by_name("cache_manager")
        ]
    
    elif workflow_type == "analysis":
        # Analysis and financial calculation focused
        return [
            registry.get_tool_by_name("ai_category_suggester"),
            registry.get_tool_by_name("linking_map_writer"),
            registry.get_tool_by_name("fba_financial_calculator"),
            registry.get_tool_by_name("output_verification"),
            registry.get_tool_by_name("cache_manager")
        ]
    
    elif workflow_type == "monitoring":
        # Monitoring and maintenance focused
        return [
            registry.get_tool_by_name("system_monitor"),
            registry.get_tool_by_name("supplier_guard"),
            registry.get_tool_by_name("security_checks"),
            registry.get_tool_by_name("enhanced_state_manager"),
            registry.get_tool_by_name("supplier_output_manager")
        ]
    
    else:
        logger.warning(f"Unknown workflow type: {workflow_type}")
        return registry.get_tools_by_category(ToolCategory.ALL)


# =============================================================================
# TESTING AND VALIDATION
# =============================================================================

async def run_comprehensive_tests():
    """Run comprehensive tests on all tools"""
    logger.info("🧪 Starting comprehensive tool tests...")
    
    registry = get_tool_registry()
    status = registry.get_registry_status()
    
    logger.info(f"📊 Registry Status:")
    logger.info(f"   Total tools: {status['total_tools']}")
    logger.info(f"   Categories: {list(status['categories'].keys())}")
    
    for category, info in status['categories'].items():
        logger.info(f"   {category}: {info['count']} tools")
    
    # Validate all tools
    validation_results = registry.validate_tool_integration()
    logger.info(f"🔍 Validation Results:")
    logger.info(f"   Tested: {validation_results['total_tools_tested']}")
    logger.info(f"   Passed: {validation_results['passed']}")
    logger.info(f"   Failed: {validation_results['failed']}")
    
    # Test workflow toolsets
    workflow_types = ["complete", "extraction", "analysis", "monitoring"]
    for workflow_type in workflow_types:
        toolset = create_workflow_toolset(workflow_type)
        valid_tools = [t for t in toolset if t is not None]
        logger.info(f"🔧 {workflow_type.title()} workflow: {len(valid_tools)} tools")
    
    return {
        "registry_status": status,
        "validation_results": validation_results,
        "test_completed": True,
        "timestamp": datetime.now().isoformat()
    }


def print_registry_summary():
    """Print a formatted summary of the tool registry"""
    registry = get_tool_registry()
    status = registry.get_registry_status()
    
    print("\n" + "="*70)
    print("🏛️  FBA SYSTEM TOOL REGISTRY SUMMARY")
    print("="*70)
    print(f"📊 Total Tools Available: {status['total_tools']}")
    print(f"🔧 Registry Status: {'✅ Initialized' if status['registry_initialized'] else '❌ Not Initialized'}")
    print()
    
    print("📂 TOOL CATEGORIES:")
    for category, info in status['categories'].items():
        print(f"   {category.upper()}: {info['count']} tools")
        for tool_name in info['tools']:
            print(f"      • {tool_name}")
        print()
    
    print("🔍 AVAILABILITY STATUS:")
    for component, available in status['availability'].items():
        status_icon = "✅" if available else "❌"
        print(f"   {status_icon} {component.replace('_', ' ').title()}")
    
    print("\n" + "="*70)
    print("🚀 Registry ready for LangGraph integration!")
    print("="*70)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Print registry summary
        print_registry_summary()
        
        # Run comprehensive tests
        test_results = await run_comprehensive_tests()
        
        # Save test results
        results_file = Path(__file__).parent / "tool_registry_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(test_results, f, indent=2)
        
        logger.info(f"💾 Test results saved to: {results_file}")
    
    asyncio.run(main())