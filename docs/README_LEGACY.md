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
5. **Multi-Cycle Operation**: Automatically suggests new categories after processing batches, creating continuous discovery loops until ALL AI-suggested categories are exhausted
6. **Financial Reporting**: Generates comprehensive CSV reports with detailed financial analysis

### Key Features
- **Multi-Cycle AI Category Progression**: System automatically suggests new categories after processing batches
- **Infinite Workflow Operation**: Continuous operation until ALL AI-suggested categories are exhausted (not limited by product counts)
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
│   ├── system_config.json                    # Main configuration file
│   └── supplier_configs/                     # Supplier-specific configurations
├── tools/                                    # Core system components
│   ├── passive_extraction_workflow_latest.py # PRIMARY ENTRY POINT
│   ├── amazon_playwright_extractor.py        # Amazon data extraction
│   ├── configurable_supplier_scraper.py      # Supplier website scraping
│   ├── FBA_Financial_calculator.py           # Financial analysis and CSV generation
│   ├── cache_manager.py                      # Cache management
│   ├── main_orchestrator.py                  # Legacy orchestrator
│   └── utils/                                # Utility modules
├── run_complete_fba_analysis.py             # Legacy entry point
├── OUTPUTS/
│   ├── FBA_ANALYSIS/                         # Analysis results and reports
│   │   ├── ai_category_cache/               # AI category suggestions cache
│   │   ├── amazon_cache/                    # Amazon product data cache
│   │   ├── Linking map/                     # Product linking mappings
│   │   ├── fba_financial_report_*.csv       # Financial reports (generated here)
│   │   └── fba_summary_*.json               # FBA summary reports
│   ├── cached_products/                     # Supplier product cache
│   └── AMAZON_SCRAPE/                       # Amazon scraping artifacts
└── docs/                                    # Documentation
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
    "selective_cache_clear": false,     // UNTESTED - DO NOT CHANGE
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
- `clear_failed_extractions`: false - When true, automatically removes Amazon cache files with failed Keepa extractions
- `force_ai_scraping`: true - Forces AI category suggestions regardless of cache state
- `max_products_per_category`: Controls how many products to process per AI-suggested category
- `max_analyzed_products`: Controls when to trigger new AI category suggestions

**IMPORTANT:** The system runs until ALL AI-suggested categories are exhausted, regardless of these parameters. These only control the pace of processing.

**For Testing (Multi-Cycle AI):**
- Set `max_products_per_category: 3` and `max_analyzed_products: 5` to trigger multiple AI cycles quickly

**For Production (Infinite Mode):**
- Set `max_products_per_category: 50` and `max_analyzed_products: 100` for efficient operation
- **CRITICAL:** The system continues until ALL AI-suggested categories are exhausted, not limited by product counts

## Quick Start Guide

### Standard Operation
```bash
# Navigate to system directory
cd C:\Users\chris\Amazon-FBA-Agent-System\Amazon-FBA-Agent-System-v3\

# Standard run (processes products until max_analyzed_products reached)
python tools/passive_extraction_workflow_latest.py

# Custom product limit
python tools/passive_extraction_workflow_latest.py --max-products 20
```

### Infinite Mode Operation
```bash
# Infinite processing with automatic AI category progression
# Runs until ALL AI-suggested categories are exhausted
python tools/passive_extraction_workflow_latest.py --max-products 0
```

### Multi-Cycle AI Testing
```bash
# First, edit config/system_config.json:
# - Set max_products_per_category: 3
# - Set max_analyzed_products: 5
# Then run:
python tools/passive_extraction_workflow_latest.py --max-products 15

# Expected: 3 FBA summaries + 3 CSV files + 3 AI cache entries
```

## Output Files and Locations

### Key Output Directories
- **AI Cache**: `OUTPUTS/FBA_ANALYSIS/ai_category_cache/clearance-king_co_uk_ai_category_cache.json`
  - **Behavior**: Appends new entries (no overwriting existing entries)
  - **Content**: AI-suggested categories with timestamps and scraping history
- **Financial Reports**: `OUTPUTS/FBA_ANALYSIS/fba_financial_report_YYYYMMDD_HHMMSS.csv`
  - **Behavior**: Creates new file each time
  - **Location**: Generated directly in `OUTPUTS/FBA_ANALYSIS/` (not in financial_reports subdirectory)
- **FBA Summaries**: `OUTPUTS/FBA_ANALYSIS/fba_summary_clearance-king_co_uk_YYYYMMDD_HHMMSS.json`
  - **Behavior**: Creates new file each time
  - **Content**: Complete workflow summary with processed product counts
- **Amazon Cache**: `OUTPUTS/FBA_ANALYSIS/amazon_cache/{ASIN}_{EAN}.json`
  - **Behavior**: Creates new file for each product
  - **Naming**: Enhanced filename logic ALWAYS includes supplier context for traceability:
    - With EAN: `amazon_{ASIN}_{supplier_EAN}.json`
    - Title-based: `amazon_{ASIN}_title_{hash}.json`
    - URL-based: `amazon_{ASIN}_url_{hash}.json`
    - Fallback: `amazon_{ASIN}_unknown_{timestamp}.json`
  - **Content**: Complete Amazon product data including Keepa metrics, FBA/FBM seller counts, pricing data
- **State Files**: `OUTPUTS/FBA_ANALYSIS/clearance-king_co_uk_processing_state.json`
  - **Behavior**: Same file updated with current processing index
  - **Content**: Last processed product index for resuming operations
- **Linking Map**: `OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json`
  - **Behavior**: Appends new entries (no overwriting existing entries)
  - **Content**: Confirmed links between supplier products and Amazon ASINs with duplicate entry fallback protection

### File Generation Patterns
- **FBA Summary**: Generated once per workflow completion
- **Financial Report**: Generated every 40-50 products OR at workflow completion
- **AI Cache**: Appends new entries with each AI call (multiple entries in same file)
- **Amazon Cache**: Individual JSON files for each product analyzed, named with ASIN and supplier EAN

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
python tools/passive_extraction_workflow_latest.py --max-products 5
```

## Script Architecture and Workflow Documentation

This section details the purpose, role, inputs, outputs, and dependencies of each major script and utility module in the system.

**(For a deeper dive into specific complex mechanisms like selective cache clearing, AI-driven scraping, the linking map, and resume logic, please refer to `docs/SYSTEM_DEEP_DIVE.md`.)**

### Core Scripts

#### 1. `tools/passive_extraction_workflow_latest.py` - **PRIMARY ENTRY POINT**
- **Status:** ✅ **Active** (Main workflow script - used directly)
- **Purpose:** Implements the complete logic for extracting and processing product data from supplier websites and Amazon. This is the main script we use directly.
- **Role in Workflow:** Primary entry point for all operations. Coordinates supplier product discovery (AI-driven), scraping (via `ConfigurableSupplierScraper`), Amazon product searching & data extraction (via `FixedAmazonExtractor`), data combination, profitability calculations (using Keepa fee data), and caching. Manages its own processing state and AI category progression.
- **Input Requirements:**
  - `config/system_config.json` (indirectly, via constants and `CacheManager`)
  - `config/supplier_configs/*.json` (used by `ConfigurableSupplierScraper`)
  - Environment variables for certain parameters (e.g., `MIN_PRICE`, `MAX_PRICE`, OpenAI keys)
  - Expects a running Chrome instance for Amazon extraction
- **Output Generated:**
  - **Data:** Returns a list of processed product data (dictionaries)
  - **Cache Files:**
    - `OUTPUTS/cached_products/{supplier_name}_products_cache.json`: Caches product data scraped from supplier sites
    - `OUTPUTS/FBA_ANALYSIS/amazon_cache/amazon_{ASIN}_{EAN_optional}.json`: Caches product data extracted from Amazon pages
    - `OUTPUTS/FBA_ANALYSIS/ai_category_cache/{supplier_name}_ai_categories.json`: Caches AI-suggested categories and scraping history
    - `OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json`: Stores confirmed links between supplier products and Amazon ASINs
    - `OUTPUTS/FBA_ANALYSIS/{supplier_name}_processing_state.json`: Stores the last processed product index for resuming
  - **Log File:** `fba_extraction_{YYYYMMDD}.log` (root) - Detailed logs for the workflow run
  - **Financial Report:** Calls `FBA_Financial_calculator.run_calculations` to generate `OUTPUTS/FBA_ANALYSIS/fba_financial_report_{timestamp}.csv`
- **Dependencies:**
  - `amazon_playwright_extractor.AmazonExtractor`
  - `configurable_supplier_scraper.ConfigurableSupplierScraper`
  - `cache_manager.CacheManager`
  - `FBA_Financial_calculator.run_calculations`
  - `utils.fba_calculator.FBACalculator`
  - `openai.OpenAI` (optional)
  - `bs4.BeautifulSoup`, `playwright.async_api`, standard libraries

#### 2. `run_complete_fba_analysis.py` (Project Root) - **LEGACY ENTRY POINT**
- **Status:** ⚠️ **Legacy** (Available but not used in current workflow)
- **Purpose:** Legacy entry point that calls the main orchestrator. We now use `passive_extraction_workflow_latest.py` directly.
- **Role in Workflow:** Sets up environment, loads configuration, initializes `FBASystemOrchestrator`, and triggers workflow through orchestrator.
- **Input Requirements:**
  - `config/system_config.json`: For global settings, API keys, workflow toggles, and cache configurations
- **Output Generated:**
  - **Console Output:** Logs progress and summary information
  - **Log File:** `fba_extraction_{YYYYMMDD}.log` (root) & potentially others in `logs/`
  - **Data Files:** Indirectly orchestrates creation of all output files
- **Dependencies:**
  - `tools.main_orchestrator.FBASystemOrchestrator`
  - `config/system_config.json`
  - Standard Python libraries (`asyncio`, `logging`, `json`, `pathlib`)

#### 3. `tools/main_orchestrator.py`
- **Status:** ⚙️ **Config-Driven Active** (Used by legacy entry point only)
- **Purpose:** Acts as the central coordinator for the entire FBA analysis system when called by `run_complete_fba_analysis.py`.
- **Role in Workflow:** Initialized by `run_complete_fba_analysis.py`. Loads configurations, initializes components, manages workflow execution (primarily through `run_with_passive_workflow` which calls `passive_extraction_workflow_latest.py`), handles AI client setup, and orchestrates cache clearing and report generation.
- **Input Requirements:**
  - `config`: A Python dictionary (loaded from `config/system_config.json`) containing all system settings
- **Output Generated:**
  - **Console Output:** Logs its own progress and component status
  - **Data Files:** Orchestrates creation of analysis files and reports. Calls `generate_report()` and `save_report()` which outputs main JSON report to `OUTPUTS/FBA_ANALYSIS/report_{YYYYMMDD_HHMMSS}.json`
  - **Cache Management:** Initiates cache clearing based on `clear_cache` and `selective_cache_clear` flags
- **Dependencies:**
  - `tools.configurable_supplier_scraper.ConfigurableSupplierScraper`
  - `tools.amazon_playwright_extractor.AmazonExtractor`
  - `tools.supplier_parser.SupplierDataParser` (conditionally used)
  - `tools.supplier_api.SupplierAPIHandler` (conditionally used)
  - `tools.system_monitor.SystemMonitor`
  - `tools.passive_extraction_workflow_latest.run_workflow_main` (dynamically imported and called)
  - `openai.OpenAI` (optional)
  - Standard Python libraries

#### 4. `tools/configurable_supplier_scraper.py`
- **Status:** ✅ **Active**
- **Purpose:** Scrapes product information from supplier websites using dynamically loaded configurations.
- **Role in Workflow:** Called by `passive_extraction_workflow_latest.py`. Fetches HTML from supplier URLs, parses product elements, and extracts details based on selectors in `config/supplier_configs/{supplier_domain}.json`. Includes AI fallbacks.
- **Input Requirements:**
  - `supplier_url`: URL of the supplier page
  - `config/supplier_configs/{supplier_domain}.json`: Loaded via `config.supplier_config_loader`
  - `ai_client` (Optional): OpenAI client for AI fallback
- **Output Generated:**
  - **Data:** List of dictionaries (scraped products) returned to the caller
  - **File Output:** None directly
- **Dependencies:**
  - `config.supplier_config_loader`
  - `aiohttp`, `bs4.BeautifulSoup`, `openai.OpenAI` (optional), standard libraries

#### 5. `tools/amazon_playwright_extractor.py`
- **Status:** ✅ **Active**
- **Purpose:** Extracts comprehensive product information from Amazon using Playwright.
- **Role in Workflow:** Used by `FixedAmazonExtractor` (subclass in `passive_extraction_workflow_latest.py`). Navigates Amazon, handles CAPTCHAs, extracts detailed product data.
- **Extracted Data Includes:**
  - **Basic Product Info**: ASIN, title, price, availability, EAN/UPC codes
  - **Sales Metrics**: BSR (Best Sellers Rank), ratings, review counts
  - **Seller Information**: FBA seller count, FBM seller count, total offer count, "bought in past month" data
  - **Keepa Data**: Historical pricing, sales velocity, fee calculations (Amazon referral fees, FBA fees)
  - **Note**: SellerAmp data extraction is currently commented out for system optimization
- **Input Requirements:**
  - `asin` or `title`: For Amazon search
  - `chrome_debug_port`: For Chrome instance
  - `ai_client` (Optional): OpenAI client
- **Output Generated:**
  - **Data:** Dictionary of Amazon product data returned to the caller
  - **File Output:** `OUTPUTS/AMAZON_SCRAPE/captcha_{asin}_{timestamp}.png` (if CAPTCHA encountered)
- **Dependencies:**
  - `playwright.async_api`, `openai.OpenAI` (optional), standard libraries

#### 6. `tools/FBA_Financial_calculator.py`
- **Status:** ✅ **Active** (for batch reporting and called by passive workflow)
- **Purpose:** Calculates financial metrics (ROI, net profit) and generates a CSV report.
- **Role in Workflow:** Called by `passive_extraction_workflow_latest.py` at the end of its run. Can also be run standalone for batch analysis. Uses fee data already present in cached inputs (e.g., from Keepa via `amazon_playwright_extractor.py`).
- **Input Requirements:**
  - Supplier cache (`OUTPUTS/cached_products/{supplier_name}_products_cache.json`)
  - Amazon cache (`OUTPUTS/FBA_ANALYSIS/amazon_cache/`)
  - Linking map (`OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json`)
  - Hardcoded parameters for VAT, prep costs, shipping
- **Output Generated:**
  - **File Output:** `OUTPUTS/FBA_ANALYSIS/fba_financial_report_{timestamp}.csv` (generated directly in FBA_ANALYSIS directory)
  - **Complete Schema:** EAN, EAN_OnPage, ASIN, Title, SupplierURL, AmazonURL, bought_in_past_month, fba_seller_count, fbm_seller_count, total_offer_count, SupplierPrice_incVAT, SupplierPrice_exVAT, SellingPrice_incVAT, AmazonPrice_exVAT, ReferralFee, FBAFee, OutputVAT, InputVAT, NetProceeds, HMRC, NetProfit, ROI, Breakeven, ProfitMargin
- **Dependencies:**
  - `pandas`, standard libraries

#### 7. `tools/cache_manager.py`
- **Status:** ✅ **Active**
- **Purpose:** Centralized management of cached data (clearing, validation).
- **Role in Workflow:** Instantiated and used by `passive_extraction_workflow_latest.py` to perform cache operations based on configuration settings from `system_config.json`. Implements different strategies, like `"smart_selective"` which removes analyzed/processed items from supplier cache files.
- **Input Requirements:**
  - `config`: Python dictionary with cache settings, including `linking_map_path`
- **Output Generated:**
  - Modifies cache directories (e.g., `OUTPUTS/cached_products/`). Can create backup files
- **Dependencies:**
  - Standard libraries (`asyncio`, `json`, `logging`, `os`, `shutil`, `pathlib`, etc.)

#### 8. `tools/supplier_parser.py`
- **Status:** ⚙️ **Config-Driven Active** (Activity depends on `system.enable_supplier_parser` in `config/system_config.json`)
- **Purpose:** Parses raw HTML from supplier product pages using configurations.
- **Role in Workflow:** Instantiated by `main_orchestrator.py`. If `enable_supplier_parser` is true, `main_orchestrator.py`'s `scrape_supplier` method will use it. Otherwise, raw element data might be used.
- **Input Requirements:**
  - `supplier_id`, `html_content`, `url`
  - `config/supplier_configs/{supplier_id}.json`
- **Output Generated:**
  - **Data:** Dictionary of parsed product data
- **Dependencies:**
  - `bs4.BeautifulSoup`, standard libraries

#### 9. `tools/system_monitor.py`
- **Status:** ⚠️ **Legacy** (Only initiated by main_orchestrator.py - legacy entry point)
- **Purpose:** Monitors and logs system resources.
- **Role in Workflow:** Instantiated by `main_orchestrator.py`. Runs in background if enabled in its internal logic. Not used by current primary workflow.
- **Output Generated:**
  - **File Output:** `logs/monitoring/system_metrics_{timestamp}.json`
- **Dependencies:**
  - `psutil` (optional), standard libraries

#### 10. `tools/supplier_api.py`
- **Status:** ⚙️ **Config-Driven Active** (Activity depends on `api_config.enabled` in `config/supplier_configs/{supplier_name}.json`)
- **Purpose:** Handles interactions with supplier APIs.
- **Role in Workflow:** Instantiated by `main_orchestrator.py`. Used if a specific supplier's configuration enables API interaction.
- **Input Requirements:**
  - `supplier_id`, API credentials/endpoints from supplier config
- **Output Generated:**
  - **Data:** List of product data from API
- **Dependencies:**
  - `requests` or `aiohttp`, standard libraries

### Utility Modules (`tools/utils/`)
This directory contains various helper modules used by the core workflow scripts.

- **`tools/utils/fba_calculator.py`**:
  - **Status:** ⚠️ **Inactive (Commented Out in current primary workflow)**
  - **Purpose:** Utility class (`FBACalculator`) for calculating Amazon FBA fees based on product details. Kept for potential future use or manual calculations.
  - **Usage:** Was used by `passive_extraction_workflow_latest.py` (commented out) and legacy `main_orchestrator.py`

- **`tools/utils/price_analyzer.py`**:
  - **Status:** ⚠️ **Legacy Only** (Only used by legacy main_orchestrator.py)
  - **Purpose:** Advanced price and profit analysis functionality.
  - **Usage:** Initialized and used by `main_orchestrator.py` (legacy entry point only)

- **`tools/utils/currency_converter.py`**:
  - **Status:** ⚠️ **Legacy Only** (Only used by legacy main_orchestrator.py)
  - **Purpose:** Converts amounts between currencies.
  - **Usage:** Initialized by `main_orchestrator.py` and used by `PriceAnalyzer` (legacy entry point only)

- **`tools/utils/analysis_tools.py`**:
  - **Status:** ❓ **Conditionally Active** (Not directly imported by current primary scripts)
  - **Purpose:** General analysis helper functions
  - **Usage:** Available for import but not currently used by primary workflow

- **`tools/utils/data_extractor.py`**, **`data_normalizer.py`**, **`product_validator.py`**, **`playwright_helpers.py`**:
  - **Status:** ❓ **Conditionally Active** (Not directly imported by current primary scripts)
  - **Purpose:** Provide helper functions for data extraction, normalization, validation, and Playwright automation
  - **Usage:** Available for import but not currently used by primary workflow

- **`tools/utils/cleanup_processed_cache.py`**:
  - **Status:** ⚠️ **Standalone Tool** (Manual execution only - not called by current scripts)
  - **Purpose:** Removes products from supplier cache that have already been processed (found in linking map)
  - **Usage:** Manual execution tool for cache maintenance, creates backups before cleaning

- **`tools/utils/cleanup_battery_cache.py`**:
  - **Status:** ❓ **Conditionally Active** (Purpose unclear from current codebase)
  - **Purpose:** Specialized cache cleaning functionality

## Output File Structure and Data Flow

### Key Output Directories
- **`OUTPUTS/`**: Root directory for all runtime artifacts.
  - **`OUTPUTS/AMAZON_SCRAPE/`**: Stores artifacts from Amazon scraping, like CAPTCHA images.
    - `captcha_{asin}_{timestamp}.png`
  - **`OUTPUTS/cached_products/`**: Caches raw product data scraped from various supplier sites.
    - `{supplier_name}_products_cache.json`
  - **`OUTPUTS/FBA_ANALYSIS/`**: Main directory for analysis results and related caches.
    - **`amazon_cache/`**: Caches raw product data extracted from Amazon product pages.
      - `amazon_{ASIN}_{EAN_optional}.json`
    - **`ai_category_cache/`**: Caches AI-suggested categories for supplier sites.
      - `{supplier_name}_ai_categories.json`
    - **`homepage_analysis/`**: ⚠️ **LEGACY/UNUSED** - Homepage analysis files from previous development sessions
      - **Status**: NOT used by current system - can be safely ignored or deleted
      - **Current Behavior**: System uses real-time category discovery instead of cached analysis
      - Files: `clearance_king_nav_analysis_*.json`, `homepage_analysis_*.json`, `debug_homepage_scraping_*.json`
    - **`Linking map/`**: Stores the critical mapping between supplier products and Amazon ASINs.
      - `linking_map.json`
    - `fba_financial_report_{timestamp}.csv`: Financial reports generated directly in this directory
    - `fba_summary_{supplier_name}_{timestamp}.json`: FBA summary reports
    - `{supplier_name}_processing_state.json`: Tracks the last processed product index for a supplier run.
    - `cleared_for_manual_review.jsonl`: Log of unanalyzed products cleared by the orchestrator's selective cache logic (legacy).
- **`logs/`**: Contains general system logs.
  - `fba_extraction_{YYYYMMDD}.log`: Detailed logs from `passive_extraction_workflow_latest.py`.
  - `test_orchestrator.log`: Logs from `main_orchestrator.py`.
  - **`monitoring/`**: Logs from `system_monitor.py`.
    - `system_metrics_{timestamp}.json`

### Primary Data Files and Formats
1.  **Supplier Product Cache (`OUTPUTS/cached_products/{supplier_name}_products_cache.json`)**:
    - **Format:** JSON array of objects.
    - **Schema (per object):** `{ "title": "Product Title", "price": 10.99, "url": "product_url", "image_url": "image_url", "ean": "123...", "source_supplier": "supplier_name", ... }`
2.  **Amazon Product Cache (`OUTPUTS/FBA_ANALYSIS/amazon_cache/amazon_{ASIN}_{EAN_optional}.json`)**:
    - **Format:** JSON object.
    - **Schema:** Comprehensive data including `asin`, `title`, `current_price`, `sales_rank`, `category`, Keepa data, FBA/FBM seller counts, etc.
3.  **Linking Map (`OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json`)**:
    - **Format:** JSON array of objects.
    - **Schema (per object):** `{ "supplier_product_identifier": "EAN_xxx / URL_xxx", ..., "chosen_amazon_asin": "ASIN", ... }`
4.  **FBA Financial Report (`OUTPUTS/FBA_ANALYSIS/fba_financial_report_{timestamp}.csv`)**:
    - **Format:** CSV.
    - **Complete Schema:** EAN, EAN_OnPage, ASIN, Title, SupplierURL, AmazonURL, bought_in_past_month, fba_seller_count, fbm_seller_count, total_offer_count, SupplierPrice_incVAT, SupplierPrice_exVAT, SellingPrice_incVAT, AmazonPrice_exVAT, ReferralFee, FBAFee, OutputVAT, InputVAT, NetProceeds, HMRC, NetProfit, ROI, Breakeven, ProfitMargin
5.  **Processing State (`OUTPUTS/FBA_ANALYSIS/{supplier_name}_processing_state.json`)**:
    - **Format:** JSON object.
    - **Schema:** `{ "last_processed_index": 0 }` (tracks index within the list of supplier products for a run).
6.  **Cleared Unanalyzed Products Log (`OUTPUTS/FBA_ANALYSIS/cleared_for_manual_review.jsonl`)**:
    - **Format:** JSON Lines (one JSON object per line).
    - **Schema (per object):** Individual supplier product object, augmented with `_source_file_deleted` and `_cleared_timestamp`.

### Data Flow Summary
1.  **Supplier Scraping (`configurable_supplier_scraper.py`, AI-driven via `passive_extraction_workflow_latest.py`)**: Outputs raw supplier product data. Cached in `OUTPUTS/cached_products/`.
2.  **Amazon Matching & Extraction (`passive_extraction_workflow_latest.py` -> `amazon_playwright_extractor.py`)**: Uses supplier data (after filtering against `linking_map.json`), outputs detailed Amazon product data. Cached in `OUTPUTS/FBA_ANALYSIS/amazon_cache/`. Updates `Linking map`.
3.  **Profitability Calculation & Reporting**:
    - `passive_extraction_workflow_latest.py`: Calculates initial metrics using Keepa fee data and generates FBA summary reports.
    - `FBA_Financial_calculator.py`: Uses cached data to generate comprehensive `fba_financial_report_{timestamp}.csv` with complete financial analysis.

## Cache Behavior and State Management

**📝 NOTE: Current Configuration**
Our current testing configuration uses:
- `"clear_cache": false` - We use existing cache data for efficiency
- `"selective_cache_clear": false` - Listed in untested parameters, do not modify

The system uses the following mechanisms for state management and resuming operations:

### State Management Files
1.  **`OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json`**:
    - **Purpose:** Critical record of supplier products successfully matched to an Amazon ASIN. Prevents re-analysis of these links.
    - **Used by:** `passive_extraction_workflow_latest.py` to skip already processed products
    - **Behavior:** Appends new entries, includes duplicate entry fallback protection

2.  **`OUTPUTS/FBA_ANALYSIS/{supplier_name}_processing_state.json`**:
    - **Purpose:** Tracks `last_processed_index` for a supplier's product list within the current run
    - **Used by:** `passive_extraction_workflow_latest.py` to resume iteration from the correct position
    - **Behavior:** Same file updated with current processing index

## Important Notes

### Critical Instructions
- **Always use original production scripts** - NEVER generate separate test scripts
- **Always verify by checking actual files** - NEVER trust logs alone
- **Only modify tested configuration parameters** - Leave untested options unchanged
- **Clear AI cache before testing** - Delete ai_category_cache files for fresh starts
- **Use `tools/passive_extraction_workflow_latest.py` directly** - This is the primary entry point, not `run_complete_fba_analysis.py`
- **Ignore any test scripts** - For testing purposes, never use test scripts, always modify and test actual production scripts directly

### System Limitations
- Currently supports only Clearance King UK supplier
- Requires manual Chrome setup with debug port
- Keepa extension must be installed and active for fee calculations
- OpenAI API key required for AI category suggestions

### Script Consolidation Notes
- **Primary Entry Point:** `passive_extraction_workflow_latest.py` contains ALL critical functionality
- **Legacy Entry Point:** `run_complete_fba_analysis.py` is available but not used in current workflow
- **No Missing Functionality:** All critical code snippets, workflow details, and functionality are preserved in the primary script
- **Verified Integration:** All components properly integrate through the primary workflow script

For technical implementation details, see `SYSTEM_DEEP_DIVE.md`
For complete testing protocols, see `NEW_CHAT_HANDOFF_PROMPT.md`
