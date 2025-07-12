#!/usr/bin/env python3
"""
MOVED TO tests/ - Import Validation Only
======================================

This script has been moved to tests/ directory and reduced to import-only checks.
For full end-to-end testing, use the CI pipeline.

Quick import validation:
python test_langraph_fixes.py --import-check-only
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Redirect to proper import validation"""
    print("🔄 This script has been moved to tests/ directory")
    print("📋 For import validation, run:")
    print("   python tests/test_import_validation.py")
    print("🏃 For full end-to-end testing, use CI pipeline")
    
    # Check if import-check-only flag is provided
    if "--import-check-only" in sys.argv:
        print("\n🧪 Running quick import check...")
        try:
            from tests.test_import_validation import main as import_main
            return import_main()
        except Exception as e:
            print(f"❌ Import validation failed: {e}")
            return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)