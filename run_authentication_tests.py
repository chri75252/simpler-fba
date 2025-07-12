#!/usr/bin/env python3
"""
Authentication System Test Runner
Executes comprehensive tests for the multi-tier authentication system
and provides detailed test results and coverage analysis.
"""

import sys
import os
import subprocess
import json
from datetime import datetime
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

def install_test_dependencies():
    """Install required test dependencies"""
    dependencies = [
        'pytest',
        'pytest-asyncio',
        'freezegun',
        'pytest-mock'
    ]
    
    print("🔧 Installing test dependencies...")
    for dep in dependencies:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', dep], 
                         check=True, capture_output=True, text=True)
            print(f"  ✅ {dep} installed")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to install {dep}: {e}")
            return False
    return True

def create_test_directories():
    """Create test directory structure if it doesn't exist"""
    test_dirs = [
        'tests',
        'tests/unit', 
        'tests/integration',
        'tests/reports'
    ]
    
    for test_dir in test_dirs:
        Path(test_dir).mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py files
    for test_dir in ['tests', 'tests/unit', 'tests/integration']:
        init_file = Path(test_dir) / '__init__.py'
        if not init_file.exists():
            init_file.write_text('')

def run_authentication_tests():
    """Run comprehensive authentication system tests"""
    
    print("🧪 Running Authentication System Tests")
    print("=" * 60)
    
    # Create test directories
    create_test_directories()
    
    # Install dependencies
    if not install_test_dependencies():
        print("❌ Failed to install test dependencies")
        return False
    
    test_files = [
        'tests/unit/test_authentication_manager.py',
        'tests/integration/test_authentication_integration.py'
    ]
    
    # Check test files exist
    missing_files = []
    for test_file in test_files:
        if not Path(test_file).exists():
            missing_files.append(test_file)
    
    if missing_files:
        print(f"❌ Missing test files: {missing_files}")
        return False
    
    # Run tests
    all_passed = True
    test_results = {}
    
    for test_file in test_files:
        print(f"\n🔍 Running {test_file}...")
        print("-" * 40)
        
        try:
            # Run pytest with verbose output and capture results
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                test_file, 
                '-v',
                '--tb=short',
                '--no-header',
                '--disable-warnings'
            ], capture_output=True, text=True, timeout=300)
            
            test_results[test_file] = {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'passed': result.returncode == 0
            }
            
            if result.returncode == 0:
                print(f"✅ {test_file} - ALL TESTS PASSED")
                print(result.stdout)
            else:
                print(f"❌ {test_file} - TESTS FAILED")
                print("STDOUT:", result.stdout)
                if result.stderr:
                    print("STDERR:", result.stderr)
                all_passed = False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_file} - TIMEOUT (exceeded 5 minutes)")
            test_results[test_file] = {
                'returncode': -1,
                'stdout': '',
                'stderr': 'Test timeout',
                'passed': False
            }
            all_passed = False
            
        except Exception as e:
            print(f"💥 {test_file} - EXCEPTION: {e}")
            test_results[test_file] = {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'passed': False
            }
            all_passed = False
    
    # Generate test report
    generate_test_report(test_results, all_passed)
    
    return all_passed

def generate_test_report(test_results, all_passed):
    """Generate comprehensive test report"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"tests/reports/authentication_test_report_{timestamp}.json"
    
    # Create detailed report
    report = {
        'timestamp': datetime.now().isoformat(),
        'overall_result': 'PASSED' if all_passed else 'FAILED',
        'total_test_files': len(test_results),
        'passed_files': sum(1 for r in test_results.values() if r['passed']),
        'failed_files': sum(1 for r in test_results.values() if not r['passed']),
        'test_results': test_results,
        'summary': {
            'authentication_manager_unit_tests': test_results.get('tests/unit/test_authentication_manager.py', {}).get('passed', False),
            'authentication_integration_tests': test_results.get('tests/integration/test_authentication_integration.py', {}).get('passed', False)
        }
    }
    
    # Save report
    os.makedirs('tests/reports', exist_ok=True)
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("🧪 AUTHENTICATION SYSTEM TEST SUMMARY")
    print("=" * 60)
    print(f"📅 Timestamp: {report['timestamp']}")
    print(f"🎯 Overall Result: {report['overall_result']}")
    print(f"📊 Test Files: {report['passed_files']}/{report['total_test_files']} passed")
    
    print("\n📋 Test File Results:")
    for test_file, result in test_results.items():
        status = "✅ PASSED" if result['passed'] else "❌ FAILED"
        print(f"  {test_file}: {status}")
    
    print(f"\n📄 Detailed report saved: {report_file}")
    
    if all_passed:
        print("\n🎉 ALL AUTHENTICATION TESTS PASSED!")
        print("   The multi-tier authentication system is ready for deployment.")
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("   Review the test output above and fix issues before deployment.")
    
    return report_file

def cleanup_test_artifacts():
    """Clean up test artifacts and temporary files"""
    
    print("\n🧹 Cleaning up test artifacts...")
    
    cleanup_paths = [
        'tests/__pycache__',
        'tests/unit/__pycache__',
        'tests/integration/__pycache__',
        'tools/__pycache__',
        '.pytest_cache'
    ]
    
    import shutil
    
    for path in cleanup_paths:
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
                print(f"  🗑️ Removed {path}")
            except Exception as e:
                print(f"  ⚠️ Could not remove {path}: {e}")
    
    print("✅ Test cleanup completed")

def main():
    """Main test execution function"""
    
    print("🚀 Amazon FBA Agent System v32 - Authentication System Test Suite")
    print("🔐 Testing multi-tier authentication with circuit breaker patterns")
    print("📋 Test Coverage: Unit tests, Integration tests, End-to-end scenarios")
    print()
    
    try:
        # Run comprehensive tests
        success = run_authentication_tests()
        
        # Cleanup
        cleanup_test_artifacts()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        cleanup_test_artifacts()
        sys.exit(1)
        
    except Exception as e:
        print(f"\n\n💥 Unexpected error during testing: {e}")
        cleanup_test_artifacts()
        sys.exit(1)

if __name__ == "__main__":
    main()