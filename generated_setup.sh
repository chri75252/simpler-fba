#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "🚀 Starting environment setup for the FBA Tool..."

# 1. Update package lists and install essential system libraries
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

# 2. Upgrade Pip and install uv
echo "🐍 Upgrading pip and installing uv..."
python3 -m pip install --upgrade pip
python3 -m pip install uv

# 3. Install Python Dependencies
echo "📄 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    uv pip install -r requirements.txt --system
else
    echo "⚠️ Warning: requirements.txt not found. Skipping dependency installation."
fi

# 4. Install additional development and production dependencies
echo "📦 Installing additional dependencies..."
uv pip install --system \
    selenium selenium-wire undetected-chromedriver \
    jupyter notebook ipython \
    scrapy requests-html httpx \
    matplotlib seaborn plotly \
    XlsxWriter ruff \
    sqlalchemy alembic \
    pytest-xdist

# 5. Install Playwright and its browser dependencies
echo "🌐 Installing Playwright and its browser dependencies..."
python3 -m playwright install --with-deps

# 6. Create .env file
echo "🔑 Creating .env file..."
cat > .env << \EOF
# Amazon FBA Agent System v3.5 Environment Variables
# =======================================================

# OpenAI API Keys and Models Configuration
# ----------------------------------------

# Primary API Key (for main workflow - gpt-4o-mini-2024-07-18)
OPENAI_API_KEY=sk-RJSRfU30ywTv0LwNHjWzfRS-qRxVnW5XkByG5q2kclT3BlbkFJ6etO9DSwGzLtithHVgenswqw8Ex_0WE9pEANNHavsA

# Secondary API Key (for supplier scraper - gpt-4.1-mini-2025-04-14)
OPENAI_API_KEY_SUPPLIER=sk-EGOSwv2-9i45pT0FdMI07yBwY1PSGcWXUTMJ9GXqr6T3BlbkFJ5Z8_KOMFOkkkyMdYvi-lIeXRBhkAG7ogQ7uUuqYN0A

# Model Configuration
# ---------------------
OPENAI_MODEL_PRIMARY=gpt-4.1-mini-2025-04-14
OPENAI_MODEL_SUPPLIER=gpt-4.1-mini-2025-04-14
OPENAI_MODEL_AMAZON_EXTRACTOR=gpt-4.1-mini-2025-04-14

# System Configuration
# ---------------------
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Optional: Additional API keys (for future use)
# -----------------------------------------------
# KEEPA_API_KEY=your-keepa-key-here
# SELLERAMP_API_KEY=your-selleramp-key-here

# Optional: Database configuration (for future upgrade)
# ------------------------------------------------------
# DATABASE_URL=sqlite:///./fba_system.db

# GitHub Integration for Tier-2/Tier-3 Sync Automation
# --------------------------------------------------------

# GitHub Personal Access Token for checkpoint automation
# Scope: repo + workflow (for branch creation and pushing)
GITHUB_TOKEN=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

# Git configuration for automated commits
GIT_USER_NAME=FBA-Bot
GIT_USER_EMAIL=chri75252@gmail.com

# Default stable branch for checkpoint operations
DEFAULT_BRANCH=june-15

# GitHub repository URL
GITHUB_REPO_URL=https://github.com/chri75252/fba-tool-claude.git

# LangSmith Tracing Configuration
# ----------------------------------
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_PROJECT=4e8c47f9-4c52-4d1d-85d0-00b31bb3ef5e
LANGCHAIN_API_KEY=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
EOF

# 7. Create required directories
echo "📁 Creating required directories..."
python3 -c "
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

# 8. Verification
echo "✅ Verifying installation..."

# Verify dependencies
echo "🐍 Verifying Python dependencies..."
python3 -c "
try:
    import aiohttp
    import beautifulsoup4
    import requests
    import pandas
    import playwright
    import dotenv
    import selenium
    import jupyter
    import scrapy
    import matplotlib
    import openpyxl
    import sqlalchemy
    import pytest
    print('✅ All major dependencies are installed.')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')
    exit(1)
"

# Verify .env file and environment variables
echo "🔑 Verifying .env file and environment variables..."
python3 -c "
from dotenv import load_dotenv
import os
load_dotenv()
if os.getenv('OPENAI_API_KEY'):
    print('✅ OPENAI_API_KEY is set.')
else:
    print('❌ OPENAI_API_KEY is not set.')
    exit(1)
"

echo "✅ Environment setup complete. The system is ready to run."