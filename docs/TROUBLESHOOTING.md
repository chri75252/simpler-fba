# Amazon FBA Agent System v3.5 - Troubleshooting Guide

## 🚀 Installation & Setup

### Prerequisites

1. **Python 3.8+** with pip
2. **Chrome browser** (for debug port functionality)
3. **OpenAI API key** 

### Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install Playwright browser binaries (REQUIRED for web scraping)
pip install playwright
playwright install

# For production environments, install only Chromium
playwright install chromium
```

### Playwright Installation Issues

If you encounter issues with Playwright installation:

```bash
# Clear Playwright cache and reinstall
playwright uninstall
pip uninstall playwright
pip install playwright==1.40.0
playwright install chromium
```

**Common Playwright Issues:**

1. **Permission denied errors**: Run with `sudo` on Linux/Mac or Administrator on Windows
2. **Network issues**: Use `--with-deps` flag: `playwright install chromium --with-deps`
3. **Container environments**: Set `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`

## 🔧 Configuration

### Playwright Configuration

The system uses Playwright for anti-bot evasion and reliable scraping:

- **Headless mode**: Use `--headless true` (default) or `--headless false` for debugging
- **Anti-detection**: Automated browser fingerprinting and human-like delays  
- **Resource management**: Dedicated browser instances with proper cleanup

**Usage Examples:**

```bash
# Run with headless browser (default - production mode)
python tools/passive_extraction_workflow_latest.py --max-products 5

# Run with headed browser (for debugging)
python tools/passive_extraction_workflow_latest.py --max-products 5 --headless false

# Test specific supplier with headless browser
python tools/passive_extraction_workflow_latest.py --supplier-url "https://www.poundwholesale.co.uk/" --max-products 1 --debug-smoke --headless true
```

### Browser Debug Port Setup

The system requires Chrome with remote debugging:

```bash
# Windows
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"

# Linux/Mac  
google-chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome-debug"
```

## 🐛 Common Issues

### 1. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'playwright'`

**Solution**:
```bash
pip install playwright
playwright install
```

### 2. Browser Connection Issues

**Problem**: `TimeoutError: Timeout 30000ms exceeded`

**Solutions**:
- Check Chrome debug port: `curl http://localhost:9222/json`
- Restart Chrome with debug flags
- Use `--headless` flag to reduce resource usage

**Shared Chrome Connection (--use-shared-chrome) Issues:**

If you see `"Failed to connect to shared Chrome at http://localhost:9222"`:

1. **Verify Chrome Debug Instance:**
   ```bash
   # Check if Chrome is running with remote debugging
   curl http://localhost:9222/json/version
   ```

2. **Start Shared Chrome Instance:**
   ```bash
   # Windows
   chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"
   
   # Linux/Mac  
   google-chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome-debug"
   ```

3. **Test CDP Connection:**
   ```bash
   # Should return Chrome version info
   curl http://localhost:9222/json/version
   ```

4. **Fallback Behavior:** The system automatically falls back to standalone browser launch if CDP connection fails

### 3. Anti-Bot Detection

**Problem**: Websites blocking requests or returning captcha

**Solutions**:
- Run in **headed mode** (remove `--headless` flag)
- Use slower rate limiting in `config/system_config.json`
- Check supplier-specific configurations in `config/supplier_configs/`

### 4. Missing Directories

**Problem**: Test failures due to missing OUTPUTS directories

**Solution**:
```python
from utils.path_manager import ensure_output_subdirs
ensure_output_subdirs()
```

### 5. aiohttp vs Playwright Migration

**Status**: Migration completed for main scraper
- ✅ `configurable_supplier_scraper.py`: Migrated to Playwright
- ✅ `passive_extraction_workflow_latest.py`: Retains aiohttp for simple HTTP requests  
- ✅ `currency_converter.py`: Retains aiohttp for API calls

**No action needed** - both libraries are used appropriately for their specific use cases.

## 📊 Performance Optimization

### Playwright Performance

- **Headed vs Headless**: Headed mode better for anti-detection, headless faster
- **Resource cleanup**: Always ensure `close_session()` is called
- **Concurrent instances**: Limit to 3-5 concurrent browsers to avoid memory issues

### Network Configuration

```json
{
  "performance": {
    "max_concurrent_requests": 5,
    "request_timeout_seconds": 30,
    "rate_limiting": {
      "rate_limit_delay": 3.0,
      "batch_delay": 15.0
    }
  }
}
```

## 🔍 Debugging

### Enable Debug Logging

```python
import logging
logging.getLogger('playwright').setLevel(logging.DEBUG)
```

### Test Playwright Installation

```bash
# Test Playwright installation
python -c "from playwright.sync_api import sync_playwright; print('✅ Playwright working')"

# Test browser launch
python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    browser.close()
    print('✅ Browser launch working')
"
```

### Verify System Health

```bash
# Run health check
./health-check.sh

# Run basic tests
pytest tests/test_basic_functionality.py -v
```

## 🚨 Emergency Recovery

If the system becomes unresponsive:

1. **Kill all browser processes**:
   ```bash
   # Windows
   taskkill /f /im chrome.exe
   taskkill /f /im chromium.exe
   
   # Linux/Mac
   pkill -f chrome
   pkill -f chromium
   ```

2. **Clear cache and restart**:
   ```bash
   python -c "from tools.cache_manager import CacheManager; CacheManager().clear_all()"
   ```

3. **Reset browser profile**:
   ```bash
   rm -rf /tmp/chrome-debug  # Linux/Mac
   rmdir /s "C:\ChromeDebugProfile"  # Windows
   ```

## 📞 Support

For additional support:
1. Check logs in `logs/debug/` directory
2. Run `pytest -v` to identify specific issues
3. Verify API key configuration in `.env` file
4. Ensure all required directories exist with `ensure_output_subdirs()`