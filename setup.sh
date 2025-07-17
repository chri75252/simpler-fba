#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Environment Setup for FBA Tool ---

echo "🚀 Starting environment setup for the FBA Tool..."

# 1. Update package lists and install essential system libraries
# These are often needed for Python packages with C extensions and for Playwright.
echo "📦 Updating package lists and installing essential system libraries..."
sudo apt-get update && sudo apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    libgstreamer1.0-0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-libav

# 2. Upgrade Pip
# Ensures the latest package versions can be fetched and installed correctly.
echo "🐍 Upgrading pip..."
python3 -m pip install --upgrade pip

# 3. Install Python Dependencies
# Installs all the required Python packages from the requirements.txt file.
if [ -f "requirements.txt" ]; then
    echo "📄 Found requirements.txt, installing dependencies..."
    pip install -r requirements.txt
else
    echo "⚠️ Warning: requirements.txt not found. Skipping dependency installation."
fi

# 4. Install Playwright and its browser dependencies
# This is a critical step for any web scraping and automation tasks.
echo "🌐 Installing Playwright and its browser dependencies (this may take a few minutes)..."
playwright install --with-deps

echo "✅ Environment setup complete. The system is ready to run."

