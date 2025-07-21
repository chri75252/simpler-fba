#!/bin/bash
# FIXED Codex Environment Setup Script  
# Save as: codex_environment_setup_fixed.sh
# Place in: ROOT directory of your project

echo "🔧 Starting Codex Environment Setup..."

# Update system packages
apt-get update && apt-get upgrade -y

# Install essential dependencies
apt-get install -y wget curl unzip xvfb

# Install Google Chrome (stable version)
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
apt-get update
apt-get install -y google-chrome-stable

# 🚨 FIXED: Get Chrome version and download compatible ChromeDriver
CHROME_VERSION=$(google-chrome --version | cut -d " " -f3 | cut -d "." -f1-3)
echo "Chrome version detected: $CHROME_VERSION"

# For Chrome 115+ use Chrome for Testing API
if [ $(echo $CHROME_VERSION | cut -d "." -f1) -ge 115 ]; then
    echo "Using Chrome for Testing API for ChromeDriver..."
    # Get the exact ChromeDriver version for this Chrome version
    CHROMEDRIVER_URL=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json" | \
        python3 -c "
import sys, json
data = json.load(sys.stdin)
for version in data['versions']:
    if version['version'].startswith('$CHROME_VERSION'):
        for download in version['downloads'].get('chromedriver', []):
            if download['platform'] == 'linux64':
                print(download['url'])
                break
        break
")
    
    if [ -n "$CHROMEDRIVER_URL" ]; then
        wget -O /tmp/chromedriver.zip "$CHROMEDRIVER_URL"
    else
        # Fallback to latest stable
        wget -O /tmp/chromedriver.zip "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/118.0.5993.70/linux64/chromedriver-linux64.zip"
    fi
else
    # For older Chrome versions use legacy method
    CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION")
    wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
fi

# Extract and install ChromeDriver
unzip /tmp/chromedriver.zip -d /tmp/
if [ -f /tmp/chromedriver ]; then
    mv /tmp/chromedriver /usr/local/bin/
elif [ -f /tmp/chromedriver-linux64/chromedriver ]; then
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/
fi

chmod +x /usr/local/bin/chromedriver
rm -rf /tmp/chromedriver* /tmp/chrome*

# Verify installation
echo "✅ Chrome version: $(google-chrome --version)"
echo "✅ ChromeDriver version: $(chromedriver --version)"
echo "✅ Environment setup completed successfully"