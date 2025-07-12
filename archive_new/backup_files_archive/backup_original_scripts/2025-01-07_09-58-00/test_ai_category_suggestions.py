#!/usr/bin/env python3
"""
Test AI Category Suggestions
Tests the fixed AI system to ensure it suggests actual discovered URLs
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.passive_extraction_workflow_latest import PassiveExtractionWorkflow

async def test_ai_suggestions():
    """Test the AI category suggestion system"""
    
    print("🧪 Testing AI Category Suggestions")
    print("=" * 50)
    
    # Initialize the workflow with AI client
    workflow = PassiveExtractionWorkflow()

    # Initialize AI client manually for testing
    try:
        import openai
        workflow.ai_client = openai.OpenAI(
            api_key="sk-02XZ3ucKVViULVaTp4_Ad6byZCT6Fofr-BwRsD5mTcT3BlbkFJ7_HTmTRScAn0m-ITc_CX5a2beXTOcbK1-Qmm0s6nwA"
        )
        print("✅ AI client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize AI client: {e}")
        return None
    
    # Mock discovered categories (the actual ones we found)
    discovered_categories = [
        {"name": "CLEARANCE", "url": "https://www.clearance-king.co.uk/clearance-lines.html"},
        {"name": "50P & UNDER", "url": "https://www.clearance-king.co.uk/50p-under.html"},
        {"name": "POUND LINES", "url": "https://www.clearance-king.co.uk/pound-lines.html"},
        {"name": "BABY & KIDS", "url": "https://www.clearance-king.co.uk/baby-kids.html"},
        {"name": "GIFTS & TOYS", "url": "https://www.clearance-king.co.uk/gifts-toys.html"},
        {"name": "HEALTH & BEAUTY", "url": "https://www.clearance-king.co.uk/health-beauty.html"},
        {"name": "HOUSEHOLD", "url": "https://www.clearance-king.co.uk/household.html"},
        {"name": "PETS", "url": "https://www.clearance-king.co.uk/pets.html"},
        {"name": "SMOKING", "url": "https://www.clearance-king.co.uk/smoking.html"},
        {"name": "STATIONERY & CRAFTS", "url": "https://www.clearance-king.co.uk/stationery-crafts.html"},
        {"name": "MAILING SUPPLIES", "url": "https://www.clearance-king.co.uk/mailing-supplies.html"},
        {"name": "OTHERS", "url": "https://www.clearance-king.co.uk/catalog/category/view/s/others/id/408/"}
    ]
    
    print(f"📋 Testing with {len(discovered_categories)} discovered categories:")
    for i, cat in enumerate(discovered_categories, 1):
        print(f"  {i}. {cat['name']}: {cat['url']}")
    
    try:
        # Test the AI suggestion method
        print(f"\n🤖 Calling AI for category suggestions...")
        
        ai_suggestions = await workflow._get_ai_suggested_categories_enhanced(
            supplier_url="https://www.clearance-king.co.uk",
            supplier_name="clearance-king.co.uk",
            discovered_categories=discovered_categories,
            previous_categories=[],  # No previous categories
            processed_products=0
        )
        
        print(f"\n✅ AI Suggestions received!")
        print(f"📊 Results:")
        
        # Check top 3 URLs
        top_3 = ai_suggestions.get("top_3_urls", [])
        print(f"\n🎯 Top 3 URLs ({len(top_3)}):")
        for i, url in enumerate(top_3, 1):
            # Check if URL is from discovered categories
            is_valid = any(cat["url"] == url for cat in discovered_categories)
            status = "✅ VALID" if is_valid else "❌ INVALID (not from discovered list)"
            print(f"  {i}. {url}")
            print(f"     {status}")
        
        # Check secondary URLs
        secondary = ai_suggestions.get("secondary_urls", [])
        print(f"\n🔄 Secondary URLs ({len(secondary)}):")
        for i, url in enumerate(secondary, 1):
            is_valid = any(cat["url"] == url for cat in discovered_categories)
            status = "✅ VALID" if is_valid else "❌ INVALID (not from discovered list)"
            print(f"  {i}. {url}")
            print(f"     {status}")
        
        # Check skip URLs
        skip = ai_suggestions.get("skip_urls", [])
        print(f"\n⏭️ Skip URLs ({len(skip)}):")
        for i, url in enumerate(skip, 1):
            print(f"  {i}. {url}")
        
        # Validation summary
        all_suggested = top_3 + secondary
        valid_suggestions = [url for url in all_suggested if any(cat["url"] == url for cat in discovered_categories)]
        invalid_suggestions = [url for url in all_suggested if not any(cat["url"] == url for cat in discovered_categories)]
        
        print(f"\n📈 VALIDATION SUMMARY:")
        print(f"  Total suggestions: {len(all_suggested)}")
        print(f"  Valid suggestions: {len(valid_suggestions)}")
        print(f"  Invalid suggestions: {len(invalid_suggestions)}")
        
        if invalid_suggestions:
            print(f"\n❌ INVALID SUGGESTIONS (these should not exist):")
            for url in invalid_suggestions:
                print(f"  - {url}")
        
        # Check reasoning
        reasoning = ai_suggestions.get("detailed_reasoning", {})
        if reasoning:
            print(f"\n🧠 AI Reasoning:")
            for key, value in reasoning.items():
                print(f"  {key}: {value}")
        
        # Overall assessment
        if len(invalid_suggestions) == 0 and len(valid_suggestions) > 0:
            print(f"\n🎉 TEST PASSED: AI only suggested URLs from the discovered categories list!")
        elif len(invalid_suggestions) > 0:
            print(f"\n❌ TEST FAILED: AI suggested {len(invalid_suggestions)} invalid URLs not from the discovered list!")
        else:
            print(f"\n⚠️ TEST INCONCLUSIVE: No suggestions made")
            
        return ai_suggestions
        
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_ai_suggestions())
