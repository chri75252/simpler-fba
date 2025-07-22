# Amazon FBA Agent System - Custom Pound Wholesale Workflow (v3.5+)

![System Status](https://img.shields.io/badge/Status-Active-green) ![Version](https://img.shields.io/badge/Version-3.5_custom-blue)

**Last Updated:** 2025-07-12
# Amazon FBA Agent System

This repository hosts the simplified Amazon FBA Agent workflow used to scrape supplier products, match them to Amazon listings and calculate profitability.

The process is orchestrated by `PassiveExtractionWorkflow` and progresses through authentication, supplier scraping, Amazon data extraction, financial analysis and state management. Browser automation now relies on Selenium with an undetected Chrome driver for stability in the Codex container.

See [docs/readme.md](docs/readme.md) for the full documentation and historical notes.

## Quick Start
```bash
# install dependencies
pip install -r requirements.txt

# install Chrome and ChromeDriver for Selenium
sudo bash codex_environment_setup.sh

# run the workflow (Chrome must be running with debug port 9222)
python run_custom_poundwholesale.py
```
The LangGraph-based features are currently **disabled**; the standard workflow runs without LangGraph integration.

Configuration is controlled through [config/system_config.json](config/system_config.json). Before contributing, review [docs/PULL_REQUEST_CHECKLIST.md](docs/PULL_REQUEST_CHECKLIST.md) for development and security guidelines
---

## 1. High-Level System Analysis

This document describes the current, fully operational workflow for the Amazon FBA Agent System, custom-tailored for scraping and analyzing products from `poundwholesale.co.uk`.  
The system is designed for robust, resumable, and fully automated end-to-end FBA product sourcing, with all configuration and output paths now fully dynamic and robust.

### Key System Characteristics

- **Configurable Entry Point:**  
  The system is launched via `run_custom_poundwholesale.py`, which loads all operational toggles, batch sizes, and output directories from `config/system_config.json`.
- **No AI Logic:**  
  All AI-driven features (category selection, data extraction, diagnostics) are **disabled**. The system uses only deterministic, selector-based scraping and matching.
- **Single-Phase Price Scraping:**  
  The workflow scrapes the full price range as defined in the config (`min_price_gbp` to `max_price_gbp`).
- **Complete, Resumable Processing Loop:**  
  The main workflow (`PassiveExtractionWorkflow`) is fully implemented, including supplier scraping, Amazon extraction, financial analysis, and profitability checking.  
  The system saves its state after every product and batch, allowing interruption and seamless resumption.
- **Robust Output Directory Handling:**  
  All output, cache, and report files are written to directories defined by `output_root` in the config, or default to `OUTPUTS/` if not set.  
  This includes supplier cache, Amazon cache, linking maps, financial reports, and processing state.
- **Centralized State Management:**  
  The `EnhancedStateManager` ensures that all progress (including supplier scraping, Amazon extraction, and financial analysis) is checkpointed and can be resumed from the exact point of interruption.

---

## 2. Complete Workflow Diagram

```
[run_custom_poundwholesale.py] (Entry Point)
     │
     ▼
[PassiveExtractionWorkflow::run] (use_predefined_categories=True, ai_client=None)
     │
     ├─> 1. Load Predefined Categories from `config/poundwholesale_categories.json`
     │
     ├─> 2. [ConfigurableSupplierScraper] -> Scrape Supplier Product Data
     │   └─> Saves to: {output_root}/cached_products/poundwholesale-co-uk_products_cache.json
     │
     ├─> 3. [COMPLETE PROCESSING LOOP]
     │   └─> For each supplier product:
     │         ├─> a. [AmazonExtractor] -> Search Amazon by EAN (or Title fallback)
     │         │     └─> Extracts full product data (no AI fallbacks)
     │         │     └─> Saves to: {output_root}/FBA_ANALYSIS/amazon_cache/amazon_{ASIN}_{EAN or title}.json
     │         ├─> b. [Linking Map] -> Update EAN-to-ASIN mapping
     │         │     └─> Saves to: {output_root}/FBA_ANALYSIS/linking_maps/poundwholesale-co-uk/linking_map.json
     │         ├─> c. [FBA_Financial_calculator] -> Calculate Profitability
     │         │     └─> Reads config for VAT, fees, etc.
     │         │     └─> Saves profitable products to: {output_root}/FBA_ANALYSIS/financial_reports/fba_financial_report_{timestamp}.csv
     │         └─> d. [EnhancedStateManager] -> Mark Product as Processed
     │               └─> Saves to: {output_root}/CACHE/processing_states/poundwholesale-co-uk_processing_state.json
     │
     └─> 4. [Resume Logic]
         └─> On restart, loads state and resumes from last unprocessed product/category
```

---

## 3. Output Tracker (Complete)

| Output Type             | File Path (relative to `output_root`)                                                      | Status         | Content                                                              |
|-------------------------|--------------------------------------------------------------------------------------------|----------------|----------------------------------------------------------------------|
| **Category Config**     | `config/poundwholesale_categories.json`                                                    | ✅ **Input**    | Predefined list of category URLs to scrape.                          |
| **Supplier Cache**      | `cached_products/poundwholesale-co-uk_products_cache.json`                                 | ✅ **Generated**| Raw product data scraped from the supplier.                          |
| **Amazon Data Cache**   | `FBA_ANALYSIS/amazon_cache/amazon_{ASIN}_{EAN or title}.json`                              | ✅ **Active**   | Detailed product data from a single Amazon page.                     |
| **Linking Map**         | `FBA_ANALYSIS/linking_maps/poundwholesale-co-uk/linking_map.json`                          | ✅ **Active**   | Links supplier EANs to the corresponding Amazon ASINs.               |
| **Financial Report**    | `FBA_ANALYSIS/financial_reports/fba_financial_report_{timestamp}.csv`                      | ✅ **Active**   | Complete financial breakdown for all profitable products.            |
| **Processing State**    | `CACHE/processing_states/poundwholesale-co-uk_processing_state.json`                       | ✅ **Active**   | Tracks processed products for resumability.                          |
| **Logs**                | `logs/debug/run_custom_poundwholesale_{timestamp}.log`                                     | ✅ **Active**   | Full debug logs for each run.                                        |

---

## 4. Quick Start & Execution

To run the system, execute the entry point script from your terminal.  
**The system will perform full end-to-end processing, including supplier scraping, Amazon extraction, financial analysis, and profitability reporting.**

```bash
# Navigate to the project directory
cd C:\Users\chris\Desktop\Amazon-FBA-Agent-System-v32

# Run the custom script
python run_custom_poundwholesale.py
```

- **To resume after interruption:**  
  Simply re-run the same command. The system will load the last processing state and continue from where it left off.  ---> TO BE RESOLVED

---

## 5. Detailed Project History & Implementation Notes

### 5.1. Major Fixes and Improvements (2025-07-12)

- **Output Directory Robustness:**  
  - All output, cache, and report files now use `output_root` from config, or default to `OUTPUTS/`.
  - All relevant scripts (`passive_extraction_workflow_latest.py`, `amazon_playwright_extractor.py`, etc.) were patched to use instance attributes for output directories.
- **State Management and Resume:**  
  - The `EnhancedStateManager` ensures that all progress is checkpointed after every product and batch.
  - The system resumes from the last unprocessed product/category, never repeating already-processed work.
- **Authentication and Browser Handling:**  
  - Authentication and scraping now use the same Chrome debug port (9222) for session consistency.
  - Credentials can be hardcoded for automated login.
- **Logging:**  
  - All log file handlers are set to UTF-8 to prevent Unicode errors on Windows.
  - Both main workflow and component logs are generated for full traceability.
- **Config-Driven Workflow:**  
  - All operational toggles (batch sizes, price limits, cache update frequency, etc.) are loaded from `config/system_config.json`.
  - No hardcoded limits; all behavior is controlled via config.
- **Cache and Output File Handling:**  
  - Amazon cache, supplier cache, and financial reports are written to supplier-specific or shared directories.
  - The system never deletes all cache files unless explicitly configured (`clear_cache`).
- **Critical Resume Checkpoints:**  
  - The system saves and resumes from:
    - The last processed supplier product (including Amazon extraction and financial analysis).
    - The last processed category/subcategory during supplier scraping.
    - The last processed batch during batch processing.
  - All progress is tracked in the processing state file.

### 5.2. Scripts Involved

- **Entry Point:**  
  - `run_custom_poundwholesale.py` (loads config, launches workflow, manages authentication)
- **Core Workflow:**  
  - `tools/passive_extraction_workflow_latest.py` (`PassiveExtractionWorkflow`)
- **Supplier Scraping:**  
  - `tools/configurable_supplier_scraper.py`
- **Amazon Extraction:**  
  - `tools/amazon_playwright_extractor.py`
- **Financial Analysis:**  
  - `tools/FBA_Financial_calculator.py`
- **State Management:**  
  - `utils/enhanced_state_manager.py`
- **Browser Management:**  
  - `utils/browser_manager.py`

### 5.3. Configuration Toggles (from `config/system_config.json`)

- `output_root`: Root directory for all outputs and caches.
- `system.max_products`, `system.max_products_per_cycle`: Maximum products to process per run/cycle.
- `system.linking_map_batch_size`, `system.financial_report_batch_size`: Batch sizes for periodic saves.
- `processing_limits.max_products_per_category`: Max products per category.
- `processing_limits.min_price_gbp`, `processing_limits.max_price_gbp`: Price range for analysis.
- `supplier_cache_control.update_frequency_products`: How often to update supplier cache.
- `hybrid_processing.enabled`: If enabled, alternates between supplier and Amazon analysis in chunks.

---

## 6. Excluded/Legacy Scripts

The following scripts from previous, more complex versions are **not** used in this workflow:

- `run_complete_fba_system.py`
- `tools/supplier_script_generator.py`
- `tools/vision_discovery_engine.py`
- `tools/vision_product_locator.py`
- `tools/vision_ean_login_extractor.py`
- `tools/standalone_playwright_login.py`
- `tools/supplier_guard.py`

---

## 7. Troubleshooting & Best Practices

- **To resume after interruption:**  
  Just re-run the script. The system will continue from the last checkpoint.
- **To force a fresh run:**  
  Delete or rename the processing state file in `CACHE/processing_states/`.
- **To change output location:**  
  Set `output_root` in `config/system_config.json`.
- **To adjust batch sizes or limits:**  
  Edit the relevant fields in `config/system_config.json`.

---

*(Everything below this line in the original README, starting from "### Component Health Status", is unchanged and should be left as-is.)*
