#!/bin/bash
echo "🌐 Setting up Browser Environment for FBA Tool..."

# Kill existing Chrome processes
taskkill /f /im chrome.exe 2>/dev/null || true

# Create Chrome debug profile directory
mkdir -p "C:\ChromeDebugProfile" 2>/dev/null || true

# Start Chrome with debug port (Windows)
echo "Starting Chrome for Windows..."
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile" &

echo "✅ Chrome debug mode started on port 9222"
echo "⚠️  Remember to install Keepa extension manually"
echo "🔗 Chrome should be accessible at: http://localhost:9222"
