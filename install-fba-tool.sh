#!/bin/bash
echo "🎯 Amazon FBA Tool - Windows Installation"
echo "========================================"

# Make scripts executable
chmod +x *.sh

echo "Step 1: Core setup..."
# Your existing Codex setup script handles this

echo "Step 2: Development tools..."
./setup-dev.sh

echo "Step 3: Browser setup..."
./setup-browser.sh

echo ""
echo "🎉 FBA Tool Installation Complete!"
echo ""
echo "Next steps:"
echo "1. Install Keepa browser extension in Chrome"
echo "2. Test with: python tools/passive_extraction_workflow_latest.py --max-products 5"
echo "3. Run health check: ./health-check.sh"
