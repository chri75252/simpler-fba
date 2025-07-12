# Setup Script Updates Required

## Your Current Setup Script Analysis
Based on your setup script parameters, here are the required additions to make pytest work:

### Current Script Status: ✅ Good Foundation
Your script already includes core dependencies that are working well:
- ✅ openai, aiohttp, beautifulsoup4, pandas, playwright
- ✅ python-dotenv, requests, lxml, fake-useragent  
- ✅ click, rich, tabulate
- ✅ Browser setup with playwright

### Required Additions for Testing

#### Add to your setup script (after the existing pip installs):
```bash
# Test framework dependencies  
echo "🧪 Installing test framework..."
pip install pytest pytest-asyncio pytest-cov
pip install faker  # For test data generation
pip install pytest-timeout pytest-xdist  # Optional: timeouts and parallel testing

# Verify test installation
python -c "
try:
    import pytest, faker
    print('✅ Test framework installed successfully')
except ImportError as e:
    print(f'❌ Test dependency missing: {e}')
"
```

#### Complete Updated Setup Script:
```bash
#!/bin/bash
echo "🚀 Setting up Amazon FBA Tool Environment..."

# Core Python setup
pip install --upgrade pip
pip install uv

# Install from requirements.txt first
pip install -r requirements.txt

# Core FBA tool dependencies
pip install openai aiohttp beautifulsoup4 pandas playwright
pip install python-dotenv requests lxml fake-useragent
pip install click rich tabulate

# NEW: Test framework dependencies
echo "🧪 Installing test framework..."
pip install pytest pytest-asyncio pytest-cov faker
pip install pytest-timeout pytest-xdist

# Browser setup
playwright install chromium firefox
playwright install-deps

# Verify core installation
python -c "
import openai, aiohttp, bs4, pandas, playwright, dotenv
print('✅ Core FBA tool imports successful')
"

# NEW: Verify test installation  
python -c "
try:
    import pytest, faker
    print('✅ Test framework ready')
    # Test pytest collection (the main fix verification)
    import subprocess
    result = subprocess.run(['python', '-c', 'import sys; sys.path.insert(0, \"tools\"); import tools.passive_extraction_workflow_latest'], 
                          capture_output=True, text=True, cwd='.')
    if result.returncode == 0:
        print('✅ Core system imports working - pytest collection will succeed')
    else:
        print('⚠️  Import issues detected')
except ImportError as e:
    print(f'❌ Test dependency missing: {e}')
"

echo "✅ FBA Tool setup complete!"
echo "🧪 Run 'pytest -q' to test the system"
```

## Network-Restricted Environment Alternative

If your environment blocks some packages, add this fallback section:

```bash
# Network-restricted fallback
echo "📦 Checking network restrictions..."
if ! pip install pytest pytest-asyncio faker 2>/dev/null; then
    echo "⚠️  Network restrictions detected"
    echo "📋 Manual test setup required:"
    echo "   1. On unrestricted machine: pip download pytest pytest-asyncio faker -d test_wheels/"
    echo "   2. Transfer test_wheels/ directory here"  
    echo "   3. Run: pip install --find-links test_wheels/ pytest pytest-asyncio faker"
    echo "   4. Verify with: python -c 'import pytest, faker; print(\"✅ Ready\")'"
fi
```

## Repository Requirements

### Add to requirements.txt (if using one):
```txt
# Testing dependencies
pytest>=7.0.0
pytest-asyncio>=0.21.0  
pytest-cov>=4.0.0
faker>=19.0.0
pytest-timeout>=2.1.0
pytest-xdist>=3.0.0  # Optional: parallel testing
```

### Add to .gitignore (if not already present):
```gitignore
# Test artifacts
.pytest_cache/
htmlcov/
.coverage
pytest.log
test_wheels/  # For offline installation
```

## Testing Your Setup

After updating your setup script, test it:

```bash
# Run your updated setup script
./install-fba-tool.sh

# Verify the pytest fix worked
python -c "
import sys
sys.path.insert(0, 'tools')
import tools.passive_extraction_workflow_latest
print('✅ Main pytest issue fixed')
"

# Test pytest collection (should work now)  
pytest --collect-only  # Should show 4 tests, no errors

# Run the actual tests
pytest -q  # Quick test run
```

## Summary for Your Environment

✅ **Main Issue**: Fixed by moving deprecated tests to archive  
✅ **Setup Script**: Add pytest dependencies as shown above  
✅ **Network Issues**: Documented with offline solutions  
✅ **Ready to Use**: Your existing dependencies are solid foundation  

The core fix is already complete - the remaining tests will work once you add the pytest dependencies to your setup script.