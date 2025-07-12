#!/bin/bash
echo "🧪 Amazon FBA Tool - Setup Testing Script"
echo "=========================================="

# Function to run Python test safely (no nested quotes issues)
run_python_test() {
    local test_name="$1"
    local python_code="$2"
    
    echo "Testing: $test_name"
    
    # Create temporary Python file instead of using nested quotes
    cat > /tmp/test_script.py << 'EOF'
import sys
import os
sys.path.insert(0, 'tools')
sys.path.insert(0, 'utils')

try:
    # Test imports
    import tools.passive_extraction_workflow_latest
    print("✅ Core system imports working")
    
    # Test path manager
    from utils.path_manager import get_api_log_path
    log_path = get_api_log_path("test")
    print(f"✅ Path manager working: {log_path}")
    
    # Test enhanced state manager
    from utils.enhanced_state_manager import EnhancedStateManager
    state_manager = EnhancedStateManager("test-supplier")
    print("✅ Enhanced state manager working")
    
except Exception as e:
    print(f"⚠️ Test failed: {e}")
    sys.exit(1)

print("✅ All tests passed!")
EOF

    python /tmp/test_script.py
    local result=$?
    rm -f /tmp/test_script.py
    return $result
}

echo ""
echo "Step 1: Checking Python environment..."
python --version || { echo "❌ Python not found"; exit 1; }

echo ""
echo "Step 2: Installing dependencies..."
pip install -r requirements.txt || { echo "❌ Failed to install requirements"; exit 1; }

echo ""
echo "Step 3: Verifying installation..."
run_python_test "Core System" || { echo "❌ Core system test failed"; exit 1; }

echo ""
echo "Step 4: Creating required directories..."
python -c "
from utils.path_manager import path_manager
import os

# Create all required directories
required_dirs = [
    'logs/api_calls',
    'logs/application', 
    'logs/tests',
    'logs/monitoring',
    'logs/security',
    'logs/debug',
    'OUTPUTS/CACHE/processing_states',
    'OUTPUTS/FBA_ANALYSIS',
    'OUTPUTS/REPORTS',
    'OUTPUTS/BACKUPS'
]

for dir_path in required_dirs:
    os.makedirs(dir_path, exist_ok=True)
    print(f'✅ Created directory: {dir_path}')

print('✅ All directories created successfully')
"

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Set environment variable: export OPENAI_API_KEY='your-key-here'"
echo "2. Test with: python tools/passive_extraction_workflow_latest.py --max-products 5"
echo "3. Run health check: ./health-check.sh"