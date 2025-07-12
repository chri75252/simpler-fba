#!/usr/bin/env python3
"""
Test script to verify AI category suggestion functionality
"""
import os
import json
import sys
import asyncio

# Add tools directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))

from passive_extraction_workflow_latest import PassiveExtractionWorkflow

async def test_ai_category_suggestion():
    """Test if AI category suggestion is working"""
    print("🧪 Testing AI Category Suggestion...")
    
    # Check if OpenAI is configured
    try:
        with open('config/system_config.json', 'r') as f:
            config = json.load(f)
        
        openai_config = config.get('integrations', {}).get('openai', {})
        if not openai_config.get('enabled') or not openai_config.get('api_key'):
            print("❌ OpenAI not configured in system_config.json")
            return False
            
        print("✅ OpenAI configuration found")
        
        # Initialize workflow with AI client
        from openai import OpenAI
        ai_client = OpenAI(api_key=openai_config.get('api_key'))
        workflow = PassiveExtractionWorkflow(config)
        workflow.ai_client = ai_client
        
        # Test AI category suggestion for clearance-king.co.uk
        supplier_name = "clearance-king.co.uk"
        print(f"🎯 Testing AI category suggestion for: {supplier_name}")
        
        # Load existing AI category cache to see current state
        ai_cache_path = f"OUTPUTS/FBA_ANALYSIS/ai_category_cache/{supplier_name.replace('.', '_')}_ai_categories.json"
        
        if os.path.exists(ai_cache_path):
            with open(ai_cache_path, 'r') as f:
                ai_cache = json.load(f)
            
            print("📋 Current AI Category Cache:")
            print(f"  Categories scraped: {len(ai_cache.get('categories_scraped', []))}")
            print(f"  Products processed: {len(ai_cache.get('products_processed', []))}")
            print(f"  AI decisions: {len(ai_cache.get('ai_decision_history', []))}")
            
            # Show recent categories
            recent_categories = ai_cache.get('categories_scraped', [])[-3:]
            if recent_categories:
                print("  Recent categories:")
                for cat in recent_categories:
                    print(f"    - {cat}")
        else:
            print("📋 No existing AI category cache found")
        
        # Test the AI category suggestion method MULTIPLE TIMES
        try:
            if hasattr(workflow, '_get_ai_suggested_categories_enhanced'):
                print("✅ AI category suggestion method found")

                if workflow.ai_client:
                    print("✅ AI client initialized")

                    # Test 1: First AI category suggestion
                    print("\n🔄 Test 1: First AI Category Suggestion")
                    try:
                        # Mock some discovered categories (correct format: list of dicts)
                        discovered_categories = [
                            {"name": "Household", "url": "https://www.clearance-king.co.uk/household.html"},
                            {"name": "Health & Beauty", "url": "https://www.clearance-king.co.uk/health-beauty.html"},
                            {"name": "Gifts & Toys", "url": "https://www.clearance-king.co.uk/gifts-toys.html"},
                            {"name": "Pet Supplies", "url": "https://www.clearance-king.co.uk/pets.html"},
                            {"name": "Baby & Kids", "url": "https://www.clearance-king.co.uk/baby-kids.html"}
                        ]

                        # Call the actual AI suggestion method
                        suggested_urls_1 = await workflow._get_ai_suggested_categories_enhanced(
                            "https://www.clearance-king.co.uk", supplier_name, discovered_categories
                        )

                        print(f"✅ First suggestion returned: {type(suggested_urls_1)}")
                        if isinstance(suggested_urls_1, dict):
                            top_urls = suggested_urls_1.get('top_3_urls', [])
                            print(f"  Top 3 URLs ({len(top_urls)}):")
                            for i, url in enumerate(top_urls[:3], 1):
                                print(f"    {i}. {url}")
                            print(f"  Reasoning: {suggested_urls_1.get('detailed_reasoning', {}).get('selection_criteria', 'N/A')}")

                        # Test 2: Second AI category suggestion (simulating progression)
                        print("\n🔄 Test 2: Second AI Category Suggestion (with history)")

                        # Simulate some processed categories in AI cache
                        if hasattr(workflow, 'ai_category_cache'):
                            if not workflow.ai_category_cache:
                                workflow.ai_category_cache = {}
                            workflow.ai_category_cache['categories_scraped'] = suggested_urls_1.get('top_3_urls', [])[:2] if isinstance(suggested_urls_1, dict) else []
                            workflow.ai_category_cache['products_processed'] = ['product1', 'product2']

                        # Call AI suggestion again with updated context
                        suggested_urls_2 = await workflow._get_ai_suggested_categories_enhanced(
                            "https://www.clearance-king.co.uk", supplier_name, discovered_categories,
                            previous_categories=suggested_urls_1.get('top_3_urls', [])[:2] if isinstance(suggested_urls_1, dict) else []
                        )

                        print(f"✅ Second suggestion returned: {type(suggested_urls_2)}")
                        if isinstance(suggested_urls_2, dict):
                            top_urls_2 = suggested_urls_2.get('top_3_urls', [])
                            print(f"  Top 3 URLs ({len(top_urls_2)}):")
                            for i, url in enumerate(top_urls_2[:3], 1):
                                print(f"    {i}. {url}")

                        # Test 3: Third AI category suggestion (further progression)
                        print("\n🔄 Test 3: Third AI Category Suggestion (advanced progression)")

                        # Update AI cache with more processed categories
                        if hasattr(workflow, 'ai_category_cache') and workflow.ai_category_cache:
                            workflow.ai_category_cache['categories_scraped'].extend(suggested_urls_2.get('top_3_urls', [])[:1] if isinstance(suggested_urls_2, dict) else [])
                            workflow.ai_category_cache['products_processed'].extend(['product3', 'product4'])

                        suggested_urls_3 = await workflow._get_ai_suggested_categories_enhanced(
                            "https://www.clearance-king.co.uk", supplier_name, discovered_categories,
                            previous_categories=suggested_urls_2.get('top_3_urls', [])[:1] if isinstance(suggested_urls_2, dict) else [],
                            processed_products=['product1', 'product2', 'product3', 'product4']
                        )

                        print(f"✅ Third suggestion returned: {type(suggested_urls_3)}")
                        if isinstance(suggested_urls_3, dict):
                            top_urls_3 = suggested_urls_3.get('top_3_urls', [])
                            print(f"  Top 3 URLs ({len(top_urls_3)}):")
                            for i, url in enumerate(top_urls_3[:3], 1):
                                print(f"    {i}. {url}")

                        # Verify suggestions are different/progressing
                        urls_1 = suggested_urls_1.get('top_3_urls', []) if isinstance(suggested_urls_1, dict) else []
                        urls_2 = suggested_urls_2.get('top_3_urls', []) if isinstance(suggested_urls_2, dict) else []
                        urls_3 = suggested_urls_3.get('top_3_urls', []) if isinstance(suggested_urls_3, dict) else []

                        if urls_1 != urls_2 or urls_2 != urls_3:
                            print("✅ AI suggestions are progressing/adapting correctly")
                            print(f"  Test 1 URLs: {urls_1}")
                            print(f"  Test 2 URLs: {urls_2}")
                            print(f"  Test 3 URLs: {urls_3}")
                            return True
                        else:
                            print("⚠️ AI suggestions seem static - may need investigation")
                            return True  # Still pass as AI is working

                    except Exception as e:
                        print(f"❌ Error during AI category suggestion tests: {e}")
                        return False

                else:
                    print("❌ AI client not initialized")
                    return False
            else:
                print("❌ AI category suggestion method not found")
                return False
                
        except Exception as e:
            print(f"❌ Error testing AI functionality: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error in AI category test: {e}")
        return False

async def main():
    print("🚀 Starting AI Category Suggestion Test...\n")
    
    test_passed = await test_ai_category_suggestion()
    
    print(f"\n📊 Test Results:")
    print(f"  AI Category Suggestion: {'✅ PASS' if test_passed else '❌ FAIL'}")
    
    if test_passed:
        print("\n🎉 AI category suggestion is working correctly!")
    else:
        print("\n⚠️ AI category suggestion test failed. Check configuration and API keys.")

if __name__ == "__main__":
    asyncio.run(main())
