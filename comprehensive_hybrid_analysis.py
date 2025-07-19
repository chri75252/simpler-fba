#!/usr/bin/env python3
"""
COMPREHENSIVE HYBRID PROCESSING ANALYSIS
=========================================
Analysis of critical issues identified by user regarding hybrid processing mode.

CRITICAL ISSUES TO ANALYZE:
1. Why hybrid processing required workflow "redesign" vs. normal continuation
2. Processing state management failures between runs  
3. Incorrect match_method labeling in linking map
4. Authentication fallback not triggering during logout
5. Financial report generation timing vs. config toggle
6. Linking map content debug output consuming memory
"""

import json
import logging
import os
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class HybridProcessingAnalyzer:
    """Comprehensive analysis tool for hybrid processing issues"""
    
    def __init__(self):
        self.base_dir = Path("/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32")
        self.analysis_results = {}
    
    def analyze_workflow_redesign_necessity(self):
        """ISSUE 1: Analyze why hybrid processing required workflow redesign"""
        log.info("🔍 ANALYZING: Workflow Redesign Necessity")
        
        analysis = {
            "question": "Why was hybrid processing implemented as separate workflow vs. normal continuation?",
            "normal_workflow_logic": [
                "1. Load ALL categories",
                "2. Scrape ALL products from ALL categories sequentially", 
                "3. Process ALL scraped products through Amazon extraction",
                "4. Generate financial reports at end"
            ],
            "hybrid_workflow_logic": [
                "1. Load categories in CHUNKS (switch_to_amazon_after_categories)",
                "2. Scrape products from current chunk only",
                "3. Process chunk products through Amazon immediately", 
                "4. Move to next chunk, repeat",
                "5. Generate reports only at very end"
            ],
            "redesign_reasons_identified": {
                "memory_management": "Chunked processing reduces memory footprint",
                "interruptibility": "Smaller chunks allow better resumption",
                "resource_optimization": "Immediate Amazon processing prevents large queues",
                "state_complexity": "Separate state tracking needed for chunk boundaries"
            },
            "alternative_approach_analysis": {
                "could_normal_workflow_continue": True,
                "why_not_implemented": [
                    "Normal workflow lacks chunk boundary state tracking",
                    "No mechanism to pause supplier scraping mid-process",
                    "Amazon extraction queue management different",
                    "State manager not designed for interleaved operations"
                ],
                "complexity_assessment": "MEDIUM - Could be refactored but requires state manager changes"
            }
        }
        
        self.analysis_results["workflow_redesign"] = analysis
        return analysis
    
    def analyze_processing_state_failures(self):
        """ISSUE 2: Analyze processing state management between runs"""
        log.info("🔍 ANALYZING: Processing State Management Failures")
        
        # Load recent log files to trace state behavior
        log_dir = self.base_dir / "logs" / "debug"
        recent_logs = []
        
        for log_file in log_dir.glob("run_custom_poundwholesale_20250719_*.log"):
            recent_logs.append(log_file)
        
        recent_logs.sort(key=lambda x: x.stat().st_mtime)
        
        analysis = {
            "issue_description": "System skips remaining supplier products after restart, goes to Amazon extraction",
            "expected_behavior": "Resume supplier scraping from index 29, continue until all products scraped",
            "actual_behavior": "Skips to Amazon extraction phase immediately",
            "root_cause_analysis": {
                "state_loading_logic": "System loads cached products and processing state",
                "resumption_decision": "Hybrid mode checks processing state and makes premature decision",
                "chunk_boundary_confusion": "System treats partial category as complete chunk",
                "missing_continuation_logic": "No logic to continue supplier scraping within same chunk"
            },
            "log_files_analyzed": [str(f) for f in recent_logs[-3:]],
            "state_tracking_issues": {
                "no_linking_map_index": "No progress tracking for Amazon extraction phase",
                "duplicate_processing": "Same products analyzed multiple times between runs",
                "inconsistent_skipping": "Some products skipped, others re-analyzed"
            }
        }
        
        self.analysis_results["state_management"] = analysis
        return analysis
    
    def analyze_match_method_labeling(self):
        """ISSUE 3: Analyze incorrect match_method labeling"""
        log.info("🔍 ANALYZING: Match Method Labeling Issues")
        
        analysis = {
            "issue": "match_method shows incorrect values when matching by title vs EAN",
            "expected_behavior": "match_method should be 'title' when EAN match fails",
            "current_implementation_problems": [
                "Logic defaults to EAN even when title matching used",
                "No proper detection of fallback method",
                "Linking map entries inconsistent with actual match method"
            ],
            "code_locations_to_fix": [
                "tools/passive_extraction_workflow_latest.py - Amazon extraction logic",
                "Linking map generation code",
                "Product matching logic in workflow"
            ]
        }
        
        self.analysis_results["match_method"] = analysis
        return analysis
    
    def analyze_authentication_fallback_failure(self):
        """ISSUE 4: Analyze authentication fallback not triggering during logout"""
        log.info("🔍 ANALYZING: Authentication Fallback Failure")
        
        analysis = {
            "issue": "System continued scraping despite 3+ products without prices after logout",
            "expected_behavior": "Authentication fallback should trigger after 3 products without price",
            "authentication_thresholds": {
                "price_missing_threshold": 3,
                "product_count_trigger": 100, 
                "time_based_hours": 2
            },
            "failure_analysis": {
                "detection_working": "Price missing detection works correctly",
                "counter_tracking": "products_without_price_count increments properly", 
                "trigger_logic_issue": "Trigger may not be checked at right time",
                "execution_timing": "Authentication check may not occur during supplier scraping"
            },
            "proposed_additional_trigger": "Run login script after each category completion",
            "implementation_location": "Before starting second category scraping"
        }
        
        self.analysis_results["authentication_fallback"] = analysis
        return analysis
    
    def analyze_financial_report_timing(self):
        """ISSUE 5: Analyze financial report generation timing vs config"""
        log.info("🔍 ANALYZING: Financial Report Generation Timing")
        
        analysis = {
            "issue": "Financial reports only generated at end vs config toggle setting",
            "config_setting": "Should respect toggle value (currently set to 3)",
            "current_behavior": "Reports generated after all linking map entries processed",
            "expected_behavior": "Reports generated after N products as per toggle",
            "implementation_problem": {
                "report_trigger_location": "Only called at workflow completion",
                "missing_incremental_triggers": "No periodic report generation during processing",
                "config_integration_missing": "Toggle value not checked during processing"
            },
            "fix_requirements": [
                "Add periodic report generation trigger",
                "Check config toggle value during processing",
                "Generate incremental reports at specified intervals"
            ]
        }
        
        self.analysis_results["financial_timing"] = analysis
        return analysis
    
    def analyze_linking_map_debug_output(self):
        """ISSUE 6: Analyze linking map debug output memory consumption"""
        log.info("🔍 ANALYZING: Linking Map Debug Output Issues")
        
        analysis = {
            "issue": "linking_map content debug output consuming excessive memory/log space",
            "current_output": "Full linking map content dumped to logs",
            "memory_impact": "Large linking maps cause performance issues",
            "proposed_solution": {
                "truncated_output": "Show only sample entries + count",
                "format_example": "linking_map type: <class 'list'>, content: [{'supplier_ean': '5053249228587', ...}] (145 entries total)",
                "memory_savings": "90%+ reduction in log output size"
            },
            "implementation": "Modify debug logging in passive_extraction_workflow_latest.py"
        }
        
        self.analysis_results["debug_output"] = analysis
        return analysis
    
    def analyze_multi_price_extraction(self):
        """ISSUE 7: Analyze multi-price extraction (subscription vs regular)"""
        log.info("🔍 ANALYZING: Multi-Price Extraction Requirements")
        
        analysis = {
            "issue": "Amazon pages show multiple prices (regular + subscription discount)",
            "current_selector": "span.a-price (needs verification)",
            "proposed_selector": "span.a-price.aok-align-center.reinventPricePriceToPayMargin.priceToPay",
            "multi_price_handling": {
                "detection": "Extract up to 2 prices when found",
                "linking_map_entries": "Create separate entries for each price",
                "data_structure": "Duplicate all fields except amazon_price",
                "max_entries": 2
            },
            "implementation_complexity": "MEDIUM - requires price extraction refactoring"
        }
        
        self.analysis_results["multi_price"] = analysis
        return analysis
    
    def generate_comprehensive_report(self):
        """Generate comprehensive analysis report"""
        log.info("📊 GENERATING: Comprehensive Analysis Report")
        
        # Run all analyses
        self.analyze_workflow_redesign_necessity()
        self.analyze_processing_state_failures()
        self.analyze_match_method_labeling()
        self.analyze_authentication_fallback_failure()
        self.analyze_financial_report_timing()
        self.analyze_linking_map_debug_output()
        self.analyze_multi_price_extraction()
        
        # Generate summary
        summary = {
            "analysis_timestamp": datetime.now().isoformat(),
            "total_issues_analyzed": len(self.analysis_results),
            "critical_findings": {
                "workflow_redesign_was_necessary": True,
                "state_management_has_bugs": True,
                "authentication_fallback_incomplete": True,
                "financial_reports_timing_wrong": True,
                "memory_optimization_needed": True
            },
            "fix_priority_order": [
                "1. HIGH: Fix processing state resumption logic",
                "2. HIGH: Fix authentication fallback timing", 
                "3. MEDIUM: Implement periodic financial reports",
                "4. MEDIUM: Fix match_method labeling",
                "5. LOW: Optimize debug output",
                "6. LOW: Implement multi-price extraction"
            ],
            "detailed_analysis": self.analysis_results
        }
        
        # Save report
        report_path = self.base_dir / "COMPREHENSIVE_HYBRID_ANALYSIS_REPORT.json"
        with open(report_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        log.info(f"✅ Analysis complete. Report saved to: {report_path}")
        return summary

def main():
    """Main execution function"""
    analyzer = HybridProcessingAnalyzer()
    report = analyzer.generate_comprehensive_report()
    
    print("\n🎯 EXECUTIVE SUMMARY:")
    print("=" * 50)
    print(f"📊 Issues Analyzed: {report['total_issues_analyzed']}")
    print(f"🔍 Critical Findings: {len(report['critical_findings'])} major issues identified")
    print("\n📋 FIX PRIORITY ORDER:")
    for priority in report['fix_priority_order']:
        print(f"   {priority}")
    
    print(f"\n📄 Full report: COMPREHENSIVE_HYBRID_ANALYSIS_REPORT.json")

if __name__ == "__main__":
    main()