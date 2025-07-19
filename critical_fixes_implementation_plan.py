#!/usr/bin/env python3
"""
CRITICAL FIXES IMPLEMENTATION PLAN - ZEN MCP ANALYSIS
====================================================
Comprehensive plan for implementing remaining critical fixes to achieve working infinite mode system.

PRIORITY CLASSIFICATION:
🚨 CRITICAL: Required for working system in infinite mode
⚠️ MEDIUM: Important but not system-breaking  
📋 FUTURE TODO: Improvements with implementation complexity/risk
"""

import json
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

class CriticalFixesPlanner:
    """Comprehensive implementation plan for critical system fixes"""
    
    def __init__(self):
        self.base_dir = Path("/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32")
        self.implementation_plan = {}
    
    def categorize_fixes_by_criticality(self):
        """Categorize fixes by implementation priority and risk"""
        log.info("🎯 CATEGORIZING: Fixes by Criticality and Risk Assessment")
        
        categorization = {
            "critical_fixes": {
                "description": "Must be implemented for working infinite mode system",
                "risk_tolerance": "Low risk, straightforward implementation only",
                "fixes": {
                    "fix_1_processing_state_resumption": {
                        "priority": "🚨 CRITICAL",
                        "description": "Fix hybrid processing to continue supplier scraping from correct index",
                        "current_bug": "System skips remaining 120 products after restart, goes to Amazon extraction",
                        "expected_behavior": "Continue scraping from product 30 where left off",
                        "implementation_complexity": "LOW",
                        "implementation_risk": "LOW", 
                        "testing_requirements": "Verify resumption from specific index",
                        "blocking_issue": True
                    },
                    "fix_2_chunk_skip_logic": {
                        "priority": "🚨 CRITICAL",
                        "description": "Prevent 276-chunk reprocessing of same products",
                        "current_bug": "Same 149 products processed 276 times before financial reports",
                        "expected_behavior": "Process each product only once, skip redundant chunks",
                        "implementation_complexity": "LOW",
                        "implementation_risk": "LOW",
                        "testing_requirements": "Verify no duplicate processing in logs",
                        "blocking_issue": True
                    },
                    "fix_3_authentication_fallback": {
                        "priority": "🚨 CRITICAL", 
                        "description": "Add authentication triggers during supplier scraping",
                        "current_bug": "Authentication fallback not triggered during supplier phase",
                        "expected_behavior": "Re-authenticate when price access fails during scraping",
                        "implementation_complexity": "MEDIUM",
                        "implementation_risk": "LOW",
                        "testing_requirements": "Verify authentication trigger on logout",
                        "blocking_issue": True
                    }
                }
            },
            "medium_priority_fixes": {
                "description": "Important for system quality but not blocking",
                "risk_tolerance": "Medium risk acceptable",
                "fixes": {
                    "fix_4_match_method_accuracy": {
                        "priority": "⚠️ MEDIUM",
                        "description": "Fix match_method labeling (EAN vs title)",
                        "current_bug": "Shows 'EAN' when title matching used",
                        "expected_behavior": "Accurate match method labeling",
                        "implementation_complexity": "LOW",
                        "implementation_risk": "LOW",
                        "testing_requirements": "Verify correct method labels in linking map",
                        "blocking_issue": False
                    },
                    "fix_5_financial_report_timing": {
                        "priority": "⚠️ MEDIUM",
                        "description": "Implement periodic financial reports per config toggle",
                        "current_bug": "Reports only at end vs config setting of 3",
                        "expected_behavior": "Generate reports every N products as configured",
                        "implementation_complexity": "MEDIUM",
                        "implementation_risk": "MEDIUM",
                        "testing_requirements": "Verify periodic report generation",
                        "blocking_issue": False
                    }
                }
            },
            "future_todos": {
                "description": "Improvements with complexity/risk not suitable for immediate implementation",
                "risk_tolerance": "High risk, complex implementation",
                "fixes": {
                    "future_1_multi_price_extraction": {
                        "priority": "📋 FUTURE TODO",
                        "description": "Extract multiple prices (regular + subscription)",
                        "current_behavior": "Single price extraction",
                        "proposed_behavior": "Create duplicate linking map entries for multiple prices",
                        "implementation_complexity": "HIGH",
                        "implementation_risk": "HIGH",
                        "reason_for_deferral": "Requires significant changes to price extraction logic",
                        "blocking_issue": False
                    },
                    "future_2_advanced_state_validation": {
                        "priority": "📋 FUTURE TODO", 
                        "description": "Comprehensive state consistency validation",
                        "implementation_complexity": "HIGH",
                        "implementation_risk": "MEDIUM",
                        "reason_for_deferral": "Complex cross-component validation logic",
                        "blocking_issue": False
                    }
                }
            }
        }
        
        self.implementation_plan["categorization"] = categorization
        return categorization
    
    def create_implementation_sequence(self):
        """Create detailed implementation sequence with testing checkpoints"""
        log.info("📋 CREATING: Implementation Sequence with Testing Checkpoints")
        
        sequence = {
            "implementation_order": [
                {
                    "step": 1,
                    "fix_id": "fix_1_processing_state_resumption",
                    "title": "🚨 CRITICAL: Processing State Resumption Logic",
                    "implementation_steps": [
                        "1.1: Identify hybrid processing resumption logic location",
                        "1.2: Modify condition to check supplier scraping completion",
                        "1.3: Add logic to continue from last processed index",
                        "1.4: Update state validation logic"
                    ],
                    "testing_requirements": [
                        "Test 1.1: Run system, interrupt after 29 products",
                        "Test 1.2: Restart system, verify continues from product 30",
                        "Test 1.3: Verify no products skipped or duplicated",
                        "Test 1.4: Complete full run to verify end-to-end"
                    ],
                    "success_criteria": [
                        "✅ System resumes from correct index after interruption", 
                        "✅ No products skipped between runs",
                        "✅ Logs show 'RESUMING supplier scraping from index X'"
                    ],
                    "rollback_plan": "Revert to original resumption logic if issues detected"
                },
                {
                    "step": 2,
                    "fix_id": "fix_2_chunk_skip_logic", 
                    "title": "🚨 CRITICAL: 276-Chunk Skip Logic",
                    "implementation_steps": [
                        "2.1: Add chunk processing skip condition",
                        "2.2: Implement already-processed product detection", 
                        "2.3: Skip redundant chunk processing when appropriate",
                        "2.4: Ensure financial reports still generate"
                    ],
                    "testing_requirements": [
                        "Test 2.1: Verify chunks not reprocessed when products exist",
                        "Test 2.2: Verify financial reports generate correctly",
                        "Test 2.3: Check logs show 'Skipping chunk - already processed'",
                        "Test 2.4: Performance test - no 276x redundant processing"
                    ],
                    "success_criteria": [
                        "✅ No redundant chunk processing in logs",
                        "✅ Products processed only once", 
                        "✅ Financial reports generate at appropriate time",
                        "✅ Significant performance improvement"
                    ],
                    "rollback_plan": "Disable skip logic if financial reports affected"
                },
                {
                    "step": 3,
                    "fix_id": "fix_3_authentication_fallback",
                    "title": "🚨 CRITICAL: Authentication Fallback Integration",
                    "implementation_steps": [
                        "3.1: Add authentication check before each category",
                        "3.2: Integrate price missing counter during supplier scraping",
                        "3.3: Trigger re-authentication when thresholds reached",
                        "3.4: Verify authentication status logging"
                    ],
                    "testing_requirements": [
                        "Test 3.1: Manually logout during supplier scraping",
                        "Test 3.2: Verify system detects price access failure", 
                        "Test 3.3: Verify authentication fallback triggers",
                        "Test 3.4: Verify successful re-authentication"
                    ],
                    "success_criteria": [
                        "✅ Authentication checked before each category",
                        "✅ Re-authentication triggered on price failures",
                        "✅ System continues processing after re-auth",
                        "✅ Logs show authentication trigger events"
                    ],
                    "rollback_plan": "Disable authentication checks if system becomes unstable"
                },
                {
                    "step": 4,
                    "fix_id": "fix_4_match_method_accuracy",
                    "title": "⚠️ MEDIUM: Match Method Labeling Accuracy", 
                    "implementation_steps": [
                        "4.1: Locate match method assignment logic",
                        "4.2: Track actual search method used",
                        "4.3: Update linking map with correct method",
                        "4.4: Verify labeling accuracy"
                    ],
                    "testing_requirements": [
                        "Test 4.1: Force EAN search failure to trigger title search",
                        "Test 4.2: Verify linking map shows 'title' method",
                        "Test 4.3: Verify EAN searches show 'EAN' method",
                        "Test 4.4: Check random sample for accuracy"
                    ],
                    "success_criteria": [
                        "✅ Match method accurately reflects search used",
                        "✅ Title searches labeled as 'title'", 
                        "✅ EAN searches labeled as 'EAN'",
                        "✅ Linking map entries consistent"
                    ],
                    "rollback_plan": "Revert to previous labeling if issues detected"
                }
            ],
            "testing_standards_compliance": {
                "reference": "CLAUDE.MD sections: CRITICAL TESTING & VERIFICATION STANDARDS, UPDATE PROTOCOL",
                "mandatory_verification": [
                    "🚨 MANDATORY_FIX_TESTING: Thoroughly test each fix",
                    "🚨 NO_CLAIMS_WITHOUT_VERIFICATION: Verify actual functionality",
                    "🚨 MANDATORY_FILE_VERIFICATION_PROTOCOL: Check files exist with correct content",
                    "⚠️ UPDATE_PROTOCOL_COMPLIANCE: Cascading updates for any changes"
                ],
                "success_validation": [
                    "✅ ZERO ERRORS: No errors in execution logs",
                    "✅ END-TO-END COMPLETION: Complete functional pipeline working",
                    "✅ ACTUAL_SYSTEM_TESTING: Use actual system, never test versions"
                ]
            }
        }
        
        self.implementation_plan["sequence"] = sequence
        return sequence
    
    def generate_implementation_code_templates(self):
        """Generate code templates for each critical fix"""
        log.info("🔧 GENERATING: Implementation Code Templates")
        
        templates = {
            "fix_1_processing_state_resumption": {
                "location": "tools/passive_extraction_workflow_latest.py - hybrid processing logic",
                "template": '''
# 🚨 CRITICAL FIX: Processing State Resumption Logic
def _should_continue_supplier_scraping(self):
    """Check if supplier scraping should continue from last index"""
    if not hasattr(self, 'state_manager') or not self.state_manager:
        return True
    
    state = self.state_manager.get_processing_state()
    last_index = state.get('last_processed_index', 0)
    
    # Load cached products to check total count
    cache_path = self._get_supplier_cache_path()
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            cached_products = json.load(f)
        
        total_products = len(cached_products)
        if last_index < total_products:
            self.log.info(f"🔄 SUPPLIER SCRAPING INCOMPLETE: {last_index}/{total_products} - continuing from index {last_index}")
            return True
        else:
            self.log.info(f"✅ SUPPLIER SCRAPING COMPLETE: {last_index}/{total_products} - proceeding to Amazon extraction")
            return False
    
    return True

# MODIFY existing hybrid processing logic:
def _run_hybrid_processing_mode(self, ...):
    # BEFORE chunk processing, check if supplier scraping should continue
    if self._should_continue_supplier_scraping():
        # Continue supplier scraping from last index
        self._continue_supplier_scraping_from_index()
    else:
        # Proceed to Amazon extraction phase
        self._proceed_to_amazon_extraction()
''',
                "testing_code": '''
# Test case for processing state resumption
def test_processing_state_resumption():
    # 1. Start system, let it process 29 products
    # 2. Interrupt system  
    # 3. Restart system
    # 4. Verify continues from product 30
    # 5. Verify no products skipped
    pass
'''
            },
            "fix_2_chunk_skip_logic": {
                "location": "tools/passive_extraction_workflow_latest.py - chunk processing loop",
                "template": '''
# 🚨 CRITICAL FIX: 276-Chunk Skip Logic
def _should_skip_chunk_processing(self):
    """Check if chunk processing should be skipped due to already processed products"""
    # Check if we have extracted products
    cache_path = self._get_supplier_cache_path()
    if not os.path.exists(cache_path):
        return False
    
    # Check if we have processed products through Amazon
    linking_map = self._load_linking_map(self.supplier_name)
    if not linking_map:
        return False
    
    # Check if financial reports already exist
    financial_reports_dir = self._get_financial_reports_dir()
    if financial_reports_dir.exists():
        report_files = list(financial_reports_dir.glob("fba_financial_report_*.csv"))
        if report_files:
            latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
            # Check if report is recent (within last hour)
            import time
            if (time.time() - latest_report.stat().st_mtime) < 3600:
                self.log.info(f"✅ RECENT FINANCIAL REPORT EXISTS: {latest_report.name} - skipping chunk reprocessing")
                return True
    
    return False

# MODIFY chunk processing loop:
for chunk_start in range(0, len(category_urls_to_scrape), chunk_size):
    if self._should_skip_chunk_processing():
        self.log.info(f"⏭️ SKIPPING CHUNK {chunk_start//chunk_size + 1}: Products already processed")
        continue
    
    # Continue with normal chunk processing...
''',
                "testing_code": '''
# Test case for chunk skip logic
def test_chunk_skip_logic():
    # 1. Run system to completion
    # 2. Restart system immediately  
    # 3. Verify chunks are skipped
    # 4. Verify financial reports not regenerated
    # 5. Check logs for "SKIPPING CHUNK" messages
    pass
'''
            },
            "fix_3_authentication_fallback": {
                "location": "tools/passive_extraction_workflow_latest.py - supplier scraping loop",
                "template": '''
# 🚨 CRITICAL FIX: Authentication Fallback Integration
async def _check_authentication_before_category(self, category_url):
    """Check authentication before processing each category"""
    if hasattr(self, 'auth_service') and self.auth_service:
        try:
            # Check if session is still authenticated
            page = await self.browser_manager.get_page()
            is_authenticated = await self.auth_service._is_session_authenticated(page)
            
            if not is_authenticated:
                self.log.warning("🔐 AUTHENTICATION LOST: Re-authenticating before category processing")
                credentials = self._get_credentials()
                success, method = await self.auth_service.ensure_authenticated_session(page, credentials, force_reauth=True)
                
                if success:
                    self.log.info(f"✅ RE-AUTHENTICATION SUCCESSFUL: {method}")
                else:
                    self.log.error("❌ RE-AUTHENTICATION FAILED: Cannot continue")
                    return False
            
            return True
        except Exception as e:
            self.log.error(f"Authentication check error: {e}")
            return True  # Continue on error to avoid blocking
    
    return True

# MODIFY supplier scraping loop:
for category_url in category_urls:
    # Check authentication before each category
    if not await self._check_authentication_before_category(category_url):
        break
    
    # Continue with category processing...
''',
                "testing_code": '''
# Test case for authentication fallback
def test_authentication_fallback():
    # 1. Start system
    # 2. Manually logout during supplier scraping
    # 3. Verify system detects logout
    # 4. Verify re-authentication occurs
    # 5. Verify processing continues
    pass
'''
            }
        }
        
        self.implementation_plan["templates"] = templates
        return templates
    
    def generate_comprehensive_plan(self):
        """Generate comprehensive implementation plan"""
        log.info("📊 GENERATING: Comprehensive Implementation Plan")
        
        # Generate all plan components
        self.categorize_fixes_by_criticality()
        self.create_implementation_sequence()
        self.generate_implementation_code_templates()
        
        plan_summary = {
            "plan_overview": {
                "objective": "Implement critical fixes for working infinite mode system",
                "total_fixes": 7,
                "critical_fixes": 3,
                "medium_priority": 2, 
                "future_todos": 2,
                "estimated_implementation_time": "2-3 hours with testing",
                "risk_assessment": "LOW - focusing on straightforward, low-risk fixes"
            },
            "success_definition": {
                "infinite_mode_working": "System processes all categories and products without interruption",
                "no_duplicate_processing": "Each product processed exactly once",
                "resumption_working": "System resumes from correct position after interruption", 
                "authentication_robust": "System re-authenticates when needed",
                "performance_optimized": "No redundant 276-chunk processing"
            },
            "detailed_plan": self.implementation_plan,
            "next_steps": [
                "1. Start with Fix 1: Processing State Resumption Logic",
                "2. Test thoroughly before proceeding to next fix",
                "3. Implement fixes in sequence with testing checkpoints", 
                "4. Follow CLAUDE.MD testing standards for each fix",
                "5. Verify infinite mode operation at completion"
            ]
        }
        
        # Save plan
        plan_path = self.base_dir / "CRITICAL_FIXES_IMPLEMENTATION_PLAN.json"
        with open(plan_path, 'w') as f:
            json.dump(plan_summary, f, indent=2)
        
        log.info(f"✅ Implementation plan saved: {plan_path}")
        return plan_summary

def main():
    """Main execution function"""
    planner = CriticalFixesPlanner()
    plan = planner.generate_comprehensive_plan()
    
    print("\n🎯 CRITICAL FIXES IMPLEMENTATION PLAN:")
    print("=" * 50)
    print(f"📊 Total Fixes: {plan['plan_overview']['total_fixes']}")
    print(f"🚨 Critical: {plan['plan_overview']['critical_fixes']}")
    print(f"⚠️ Medium: {plan['plan_overview']['medium_priority']}")
    print(f"📋 Future TODO: {plan['plan_overview']['future_todos']}")
    
    print("\n🚨 CRITICAL FIXES (IMMEDIATE IMPLEMENTATION):")
    for i, step in enumerate(plan['detailed_plan']['sequence']['implementation_order'][:3], 1):
        print(f"   {i}. {step['title']}")
    
    print("\n⚠️ MEDIUM PRIORITY (AFTER CRITICAL):")
    for i, step in enumerate(plan['detailed_plan']['sequence']['implementation_order'][3:], 4):
        print(f"   {i}. {step['title']}")
    
    print("\n📋 FUTURE TODOS (DEFERRED):")
    future_fixes = plan['detailed_plan']['categorization']['future_todos']['fixes']
    for fix_id, fix_info in future_fixes.items():
        print(f"   - {fix_info['description']}")
        print(f"     Reason: {fix_info['reason_for_deferral']}")
    
    print(f"\n📄 Full plan: CRITICAL_FIXES_IMPLEMENTATION_PLAN.json")
    print("\n🚀 READY TO START IMPLEMENTATION")

if __name__ == "__main__":
    main()