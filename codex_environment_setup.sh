#!/bin/bash
# Codex Environment Setup Script

# Update system packages
apt-get update && apt-get upgrade -y

# Install essential dependencies
apt-get install -y wget curl unzip xvfb

# Install Google Chrome (stable version)
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
apt-get update
apt-get install -y google-chrome-stable

# Install ChromeDriver (compatible version)
CHROME_VERSION=$(google-chrome --version | cut -d " " -f3 | cut -d "." -f1)
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}")
wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
unzip /tmp/chromedriver.zip -d /usr/local/bin/
chmod +x /usr/local/bin/chromedriver
rm /tmp/chromedriver.zip

echo "✅ Environment setup completed successfully"
