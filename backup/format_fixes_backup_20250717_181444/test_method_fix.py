#!/usr/bin/env python3
"""
Quick test to verify the method signature fix
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_method_signature():
    """Test if the _save_final_report method signature is fixed"""
    print("🔍 Testing method signature fix...")
    
    try:
        from tools.passive_extraction_workflow_latest import PassiveExtractionWorkflow
        
        # Create a mock instance for testing
        workflow = PassiveExtractionWorkflow()
        
        # Test method exists and accepts 2 parameters
        import inspect
        method = getattr(workflow, '_save_final_report')
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        print(f"✅ Method signature: {sig}")
        print(f"✅ Parameters: {params}")
        print(f"✅ Parameter count: {len(params)}")
        
        if len(params) == 2:  # self + 2 parameters
            print("✅ SUCCESS: Method accepts correct number of parameters!")
            return True
        else:
            print(f"❌ FAILED: Method accepts {len(params)} parameters, expected 2")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_method_signature()
    if success:
        print("\n🎉 FIX VERIFIED: The method signature issue has been resolved!")
        print("📁 Linking maps and financial reports should now generate correctly.")
    else:
        print("\n❌ FIX FAILED: Method signature issues remain")