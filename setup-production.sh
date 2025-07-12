#!/bin/bash
echo "🚀 Setting up Amazon FBA Tool Environment..."

# Set timeouts and error handling
set -e
export PIP_TIMEOUT=60
export PIP_RETRIES=2

# Core Python setup
pip install --upgrade pip
pip install uv

# Install from requirements.txt first (if it exists)
if [ -f requirements.txt ]; then
    echo "📦 Installing from requirements.txt..."
    pip install -r requirements.txt
fi

# Install additional dependencies efficiently
echo "📦 Installing additional dependencies..."
pip install --timeout=60 \
    openai aiohttp beautifulsoup4 pandas playwright \
    python-dotenv requests lxml fake-useragent \
    click rich tabulate \
    pytest pytest-asyncio pytest-cov faker pytest-timeout pytest-xdist

# Browser setup (container-safe)
echo "🌐 Setting up browsers..."
if command -v apt-get >/dev/null 2>&1; then
    export PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
    playwright install chromium --with-deps
else
    playwright install chromium || echo "⚠️ Browser install skipped in restricted environment"
fi

# Verify installation using safe Python execution
echo "✅ Verifying installation..."

# Create temporary test script to avoid nested quote issues
cat > /tmp/verify_deps.py << 'EOF'
try:
    import openai, aiohttp, bs4, pandas, playwright, dotenv, pytest, faker
    print('✅ All dependencies imported successfully')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')
    exit(1)
EOF

python /tmp/verify_deps.py
rm -f /tmp/verify_deps.py

# Test core system imports safely
echo "🧪 Testing core system imports..."
cat > /tmp/test_core.py << 'EOF'
import sys
sys.path.insert(0, 'tools')
sys.path.insert(0, 'utils')

try:
    import tools.passive_extraction_workflow_latest
    print("✅ Core system imports working")
    
    # Test enhanced components
    from utils.path_manager import get_api_log_path
    log_path = get_api_log_path("setup_test")
    print(f"✅ Path manager working: {log_path}")
    
    from utils.enhanced_state_manager import EnhancedStateManager
    state_manager = EnhancedStateManager("setup-test")
    print("✅ Enhanced state manager working")
    
except Exception as e:
    print(f"⚠️ Core import issue: {e}")
    print("This may be normal if dependencies are missing")
EOF

python /tmp/test_core.py
rm -f /tmp/test_core.py

# Create required directories
echo "📁 Creating required directories..."
python -c "
import os
required_dirs = [
    'logs/api_calls', 'logs/application', 'logs/tests', 'logs/monitoring',
    'logs/security', 'logs/debug', 'OUTPUTS/CACHE/processing_states',
    'OUTPUTS/FBA_ANALYSIS', 'OUTPUTS/REPORTS', 'OUTPUTS/BACKUPS'
]
for dir_path in required_dirs:
    os.makedirs(dir_path, exist_ok=True)
print('✅ All directories created')
"

echo ""
echo "✅ FBA Tool setup complete!"
echo ""
echo "🔑 IMPORTANT: Set your OpenAI API key:"
echo "   export OPENAI_API_KEY='your-api-key-here'"
echo "   # Or create a .env file with: OPENAI_API_KEY=your-api-key-here"
echo ""
echo "🧪 Test the system:"
echo "   python tools/passive_extraction_workflow_latest.py --max-products 5"
echo "   pytest -q  # Run tests"
echo "   ./health-check.sh  # Health check"