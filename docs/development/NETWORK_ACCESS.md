# Network Access Requirements and Limitations

## Overview
This document outlines network access requirements for the Amazon FBA Agent System testing environment and provides solutions for restricted network environments.

## Current Network Restrictions

### Blocked Operations
- Direct `pip install` from GitHub repositories (`git+https://github.com/...`)
- Access to `raw.githubusercontent.com` for package downloads
- External package repositories outside of standard PyPI

### Impact on Testing
- Some test dependencies may fail to install in restricted environments
- CI/CD pipelines may require alternative package sources
- Development environments need offline package management

## Required Dependencies

### Core Testing Dependencies
```bash
# Standard PyPI packages (usually accessible)
pip install pytest pytest-asyncio faker
pip install beautifulsoup4 aiohttp requests
pip install pandas numpy

# Test-specific packages
pip install pytest-cov pytest-xdist pytest-timeout
pip install mock unittest-mock
```

### Dependency Installation Solutions

#### 1. Pre-built Wheels (Recommended for Restricted Environments)
```bash
# Download wheels on unrestricted machine:
pip download -r requirements.txt -d wheels/
pip download pytest pytest-asyncio faker -d wheels/

# Transfer wheels/ directory to restricted environment
# Install from local wheels:
pip install --find-links wheels/ -r requirements.txt
pip install --find-links wheels/ pytest pytest-asyncio faker
```

#### 2. Corporate Proxy Configuration
```bash
# Configure pip to use corporate proxy
pip config set global.proxy https://proxy.company.com:8080
pip config set global.trusted-host pypi.org pypi.python.org files.pythonhosted.org

# Alternative: Environment variables
export HTTP_PROXY=https://proxy.company.com:8080
export HTTPS_PROXY=https://proxy.company.com:8080
```

#### 3. Internal Package Mirror
```bash
# Configure pip to use internal PyPI mirror
pip config set global.index-url https://pypi.internal.company.com/simple/
pip config set global.trusted-host pypi.internal.company.com
```

#### 4. Offline Installation Bundle
```bash
# Create complete offline bundle
pip download -r requirements.txt -d offline_packages/
pip download pytest pytest-asyncio faker pytest-cov -d offline_packages/

# Create installation script
cat > install_offline.sh << 'EOF'
#!/bin/bash
cd offline_packages
pip install *.whl
EOF
```

## Setup Script Updates

### Recommended Addition to setup script:
```bash
# Add to install-fba-tool.sh after existing dependencies:

echo "📦 Installing test dependencies..."

# Try standard installation first
if pip install pytest pytest-asyncio faker pytest-cov 2>/dev/null; then
    echo "✅ Test dependencies installed from PyPI"
else
    echo "⚠️  Network restrictions detected"
    echo "📋 Manual installation required:"
    echo "   1. Download wheels on unrestricted machine:"
    echo "      pip download pytest pytest-asyncio faker pytest-cov -d test_wheels/"
    echo "   2. Transfer test_wheels/ to this environment"  
    echo "   3. Run: pip install --find-links test_wheels/ pytest pytest-asyncio faker pytest-cov"
fi

# Verify test environment
echo "🧪 Verifying test environment..."
python -c "
try:
    import pytest, faker
    print('✅ Test environment ready')
except ImportError as e:
    print(f'❌ Missing test dependency: {e}')
    print('📋 Run pytest installation steps above')
" 2>/dev/null
```

## Alternative Testing Approaches

### 1. Docker-based Testing
```dockerfile
# Dockerfile.test
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y git

# Copy requirements and install in container
COPY requirements.txt test-requirements.txt ./
RUN pip install -r requirements.txt -r test-requirements.txt

# Copy source code
COPY . /app
WORKDIR /app

# Run tests
CMD ["pytest", "-q", "--cov"]
```

### 2. Vendored Dependencies
```bash
# Include test dependencies in repository (not recommended for production)
mkdir vendor/
pip download pytest pytest-asyncio faker -d vendor/
# Add vendor/ to repository
# Install with: pip install --find-links vendor/ pytest pytest-asyncio faker
```

### 3. Development Environment Setup
```bash
# Create development environment with all dependencies
python -m venv test_env
source test_env/bin/activate  # Linux/Mac
# test_env\Scripts\activate  # Windows

# Install all dependencies in virtual environment
pip install -r requirements.txt
pip install pytest pytest-asyncio faker pytest-cov pytest-timeout
```

## Security Considerations

### Do NOT:
- Add `--trusted-host` for unknown domains
- Use `--break-system-packages` flag
- Bypass SSL verification with `--trusted-host`
- Install packages from unverified sources

### DO:
- Use corporate approved package sources
- Verify wheel integrity with checksums
- Use virtual environments for testing
- Document all network access requirements
- Follow corporate security policies

## Testing in Restricted Environments

### Minimal Test Setup
```bash
# Essential dependencies only
pip install pytest  # Core testing framework
python -m pytest tests/ -v  # Run with verbose output
```

### Mock Network Dependencies
```python
# For tests requiring network access
import pytest
from unittest.mock import patch

@pytest.fixture
def mock_network():
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"status": "ok"}
        yield mock_get
```

## Support and Troubleshooting

### Common Issues:
1. **SSL Certificate errors**: Configure corporate certificates
2. **Proxy authentication**: Set up proxy credentials
3. **Package not found**: Check internal package mirror availability
4. **Permission denied**: Use virtual environments

### Contact:
- IT Support for proxy/firewall configuration
- DevOps team for internal package mirror setup
- Security team for approved package sources

---

**Last Updated**: 2025-06-15  
**Environment**: Network-restricted corporate environment  
**Status**: Documented limitations and solutions