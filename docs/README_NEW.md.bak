# Amazon FBA Agent System v3.2 - Complete Documentation

**Version:** 3.2 (Multi-Cycle AI Category Progression - READY FOR TESTING)
**Date:** 2025-06-03
**Status:** Ready for Multi-Cycle AI Testing and Verification

## System Overview

The Amazon FBA Agent System is a sophisticated automation platform that identifies profitable products by scraping supplier websites, matching them with Amazon listings, and calculating profitability metrics.

### System Purpose and Workflow
The system automates the process of finding profitable products for Amazon FBA by:
1. **AI-Driven Category Discovery**: Uses OpenAI to intelligently suggest supplier categories to scrape
2. **Supplier Product Scraping**: Extracts product data from supplier websites (currently Clearance King UK)
3. **Amazon Product Matching**: Matches supplier products to Amazon listings using EAN/UPC codes and title fallback
4. **Profitability Analysis**: Calculates FBA fees, profit margins, and ROI using Keepa data
5. **Multi-Cycle Operation**: Automatically suggests new categories after processing batches, creating continuous discovery loops
6. **Financial Reporting**: Generates comprehensive CSV reports with detailed financial analysis

### Key Features
- **Multi-Cycle AI Category Progression**: System automatically suggests new categories after processing batches
- **Infinite Workflow Operation**: Continuous operation with automatic AI category progression
- **Smart Product Matching**: EAN/UPC-based matching with intelligent title fallback
- **Comprehensive Financial Analysis**: Automated FBA calculator execution every 40-50 products
- **State Persistence**: Resume capability with full workflow state management
- **Rate Limiting**: Intelligent timing gaps to prevent API throttling

## System Requirements

### Prerequisites
- Python 3.8+
- Chrome browser with debug port enabled
- Keepa browser extension installed and configured
- OpenAI API key

### Required Chrome Setup
```bash
# Start Chrome with debug port (required for automation)
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"
```

### Directory Structure
```
Amazon-FBA-Agent-System-v3/
├── config/
│   ├── system_config.json          # Main configuration file
│   └── supplier_configs/           # Supplier-specific configurations
├── tools/                          # Core system components
├── OUTPUTS/
│   ├── FBA_ANALYSIS/              # Analysis results and reports
│   │   ├── ai_category_cache/     # AI category suggestions cache
│   │   ├── amazon_cache/          # Amazon product data cache
│   │   └── financial_reports/     # CSV financial reports
│   └── cached_products/           # Supplier product cache
└── docs/                          # Documentation
```

## Configuration Guide

### Main Configuration File: config/system_config.json

**CRITICAL CONFIGURATION SETTINGS (TESTED AND VERIFIED):**
```json
{
  "system": {
    "clear_cache": false,
    "selective_cache_clear": false,
    "force_ai_scraping": true,
    "max_products_per_category": 3,     // For testing - change to 50+ for production
    "max_analyzed_products": 5          // For testing - change to 100+ for production
  },
  "integrations": {
    "openai": {
      "enabled": true,
      "api_key": "sk-02XZ3ucKVViULVaTp4_Ad6byZCT6Fofr-BwRsD5mTcT3BlbkFJ7_HTmTRScAn0m-ITc_CX5a2beXTOcbK1-Qmm0s6nwA",
      "model": "gpt-4o-mini-search-preview-2025-03-11",
      "web_search_enabled": true
    }
  }
}
```

**UNTESTED CONFIGURATION OPTIONS - DO NOT MODIFY:**
The following settings exist in the configuration but have NOT been tested. Keep them at their current values:
```json
{
  "system": {
    "enable_supplier_parser": false,    // UNTESTED - DO NOT CHANGE
    "test_mode": false,                 // UNTESTED - DO NOT CHANGE
    "bypass_ai_scraping": false,        // UNTESTED - DO NOT CHANGE
    "enable_system_monitoring": true    // UNTESTED - DO NOT CHANGE
  }
}
```

### Configuration Parameters Explained

**TESTED PARAMETERS (Safe to Modify):**
- `clear_cache`: false - We use existing cache data for efficiency
- `selective_cache_clear`: false - We do not use selective cache clearing
- `force_ai_scraping`: true - Forces AI category suggestions regardless of cache state
- `max_products_per_category`: Controls how many products to process per AI-suggested category
- `max_analyzed_products`: Controls when to trigger new AI category suggestions

**For Testing (Multi-Cycle AI):**
- Set `max_products_per_category: 3` and `max_analyzed_products: 5` to trigger multiple AI cycles quickly

**For Production (Infinite Mode):**
- Set `max_products_per_category: 50` and `max_analyzed_products: 100` for efficient operation

## Quick Start Guide

### Standard Operation
```bash
# Navigate to system directory
cd C:\Users\chris\Amazon-FBA-Agent-System\Amazon-FBA-Agent-System-v3\

# Standard run (processes products until max_analyzed_products reached)
python passive_extraction_workflow_latest.py

# Custom product limit
python passive_extraction_workflow_latest.py --max-products 20
```

### Infinite Mode Operation
```bash
# Infinite processing with automatic AI category progression
python passive_extraction_workflow_latest.py --max-products 0
```

### Multi-Cycle AI Testing
```bash
# First, edit config/system_config.json:
# - Set max_products_per_category: 3
# - Set max_analyzed_products: 5
# Then run:
python passive_extraction_workflow_latest.py --max-products 15

# Expected: 3 FBA summaries + 3 CSV files + 3 AI cache entries
```

## Output Files and Locations

### Key Output Directories
- **AI Cache**: `OUTPUTS/FBA_ANALYSIS/ai_category_cache/clearance-king_co_uk_ai_category_cache.json`
- **Financial Reports**: `OUTPUTS/FBA_ANALYSIS/fba_financial_report_YYYYMMDD_HHMMSS.csv`
- **FBA Summaries**: `OUTPUTS/FBA_ANALYSIS/fba_summary_clearance-king_co_uk_YYYYMMDD_HHMMSS.json`
- **Amazon Cache**: `OUTPUTS/FBA_ANALYSIS/amazon_cache/amazon_*.json`
- **State Files**: `OUTPUTS/FBA_ANALYSIS/clearance-king_co_uk_processing_state.json`
- **Linking Map**: `OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json`

### File Generation Patterns
- **FBA Summary**: Generated once per workflow completion
- **Financial Report**: Generated every 40-50 products OR at workflow completion
- **AI Cache**: Appends new entries with each AI call (multiple entries in same file)
- **Amazon Cache**: Individual JSON files for each product analyzed

## Monitoring Commands

### Check System Status
```bash
# Check AI cache progression
type "OUTPUTS\FBA_ANALYSIS\ai_category_cache\clearance-king_co_uk_ai_category_cache.json"

# Check recent financial reports
dir "OUTPUTS\FBA_ANALYSIS\fba_financial_report_*.csv" /od

# Monitor running processes
tasklist | findstr python
```

### Health Indicators
- **Healthy Operation**: New AI calls every 40-50 products
- **File Generation**: New CSV reports every 40-50 products
- **Memory Usage**: Should remain stable during infinite runs
- **Processing Speed**: ~2-3 products per minute average

## Troubleshooting

### Common Issues

**AI Client Initialization Failures:**
```bash
# Check API key in config/system_config.json
# Verify internet connectivity
# Test API key manually:
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.openai.com/v1/models
```

**Chrome/Browser Issues:**
```bash
# Restart Chrome with debug port
taskkill /f /im chrome.exe
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"
```

**Cache Issues:**
```bash
# Clear all caches and restart
rmdir /s "OUTPUTS\FBA_ANALYSIS\amazon_cache"
rmdir /s "OUTPUTS\FBA_ANALYSIS\ai_category_cache"
del "OUTPUTS\cached_products\*.json"
```

### Recovery Procedures

**Complete System Reset:**
```bash
# Stop all processes
taskkill /f /im python.exe

# Clear all caches
rmdir /s "OUTPUTS\FBA_ANALYSIS"
rmdir /s "OUTPUTS\cached_products"

# Recreate directory structure
mkdir OUTPUTS\FBA_ANALYSIS\ai_category_cache
mkdir OUTPUTS\FBA_ANALYSIS\amazon_cache
mkdir OUTPUTS\cached_products

# Restart with minimal test
python passive_extraction_workflow_latest.py --max-products 5
```

## Important Notes

### Critical Instructions
- **Always use original production scripts** - NEVER generate separate test scripts
- **Always verify by checking actual files** - NEVER trust logs alone
- **Only modify tested configuration parameters** - Leave untested options unchanged
- **Clear AI cache before testing** - Delete ai_category_cache files for fresh starts

### System Limitations
- Currently supports only Clearance King UK supplier
- Requires manual Chrome setup with debug port
- Keepa extension must be installed and active
- OpenAI API key required for category suggestions

For technical implementation details, see `SYSTEM_DEEP_DIVE.md`
For complete testing protocols, see `NEW_CHAT_HANDOFF_PROMPT.md`
