# Amazon FBA Agent System v3 - Updated Documentation (Revised)

This document provides an updated overview of the Amazon FBA Agent System v3, detailing the workflow, configuration, script outputs, and integration notes for the enhanced system. It is designed to help users understand the system components, configuration options, and how to run the tool effectively, including the new test mode and cache clearing toggle. This version incorporates specific user questions and clarifications.

---

## Overview

The Amazon FBA Agent System v3 is a modular, extensible pipeline designed to analyze supplier products for Amazon FBA profitability. It integrates user-edited core scripts with enhanced modules to provide a comprehensive workflow from supplier scraping to final profit analysis.

---

## Key Scripts and Their Outputs

### 1. `run_complete_fba_analysis.py`

-   **Purpose:** Main entry point to run the complete FBA analysis workflow.
-   **Functionality:** Orchestrates the entire pipeline, including cache clearing (if enabled), the passive extraction workflow, and result summarization.
-   **Outputs:**
    -   **Analysis Reports and Summaries:** Saved under `OUTPUTS/FBA_ANALYSIS/`.
        -   `report_YYYYMMDD_HHMMSS.json`: This file contains overall statistics for the entire analysis run. Information includes: total number of suppliers processed, total products considered, number of products successfully analyzed, number of profitable products found (based on defined criteria), counts of various errors encountered, and total execution time.
        -   `fba_summary_SUPPLIERNAME_YYYYMMDD_HHMMSS.json`: Generated for each supplier processed in a session. This file lists each product from that supplier that was analyzed. For each product, it includes:
            -   Supplier product details (name, price, EAN, URL).
            -   Amazon product details if a match was found (ASIN, title, price, BSR).
            -   Calculated FBA fees.
            -   Profitability metrics (e.g., potential ROI, net profit).
            -   Any errors or warnings specific to that product's analysis (e.g., "Amazon product not found," "Low match quality").
    -   **Detailed Execution Logs:** Saved in `logs/complete_analysis.log`.
        -   This log file provides a timestamped, step-by-step account of the script's execution. It includes:
            -   System initialization messages and configuration loaded.
            -   Status of cache clearing operations.
            -   Start and end markers for major workflow stages (e.g., "Starting passive extraction for supplier X").
            -   Logs for individual product processing: EAN/title search attempts on Amazon, data extraction successes/failures from Amazon pages, FBA fee calculation inputs/outputs.
            -   Warnings encountered (e.g., missing data fields, timeouts, products skipped due to criteria).
            -   Detailed error messages and stack traces if critical issues occur.
            -   Summary statistics at the end of the run (can be a subset of what's in `report_...json`).
    -   **Cache Clearing:** Performed on the directory `OUTPUTS/FBA_ANALYSIS/supplier_cache/SUPPLIERNAME/` if enabled.
        -   **Cache Clearing Behavior ----> CLARIFICATION:** When `"clear_cache": true` is set, the system currently **deletes all files** within the specific supplier's cache directory (e.g., `OUTPUTS/FBA_ANALYSIS/supplier_cache/clearance-king_co_uk/`). This cache stores the raw list of products scraped from the supplier's website (e.g., `clearance-king_co_uk_products_YYYYMMDD_HHMMSS.json`).
        -   This means it clears *previously scraped supplier product lists* for that supplier before starting a new scrape. It does **not** clear the `linking_map.json` (which stores EAN-ASIN links and other analysis metadata) nor does it clear already saved detailed Amazon product data files (e.g., `amazon_ASIN_...json`).
        -   **Prioritization of Scraped Products:** The system is designed to first check if a fresh supplier scrape is needed (or if `clear_cache` forces it). If supplier products are already cached (and not cleared), it uses those. The analysis of *which* products to process from the supplier list (cached or freshly scraped) then proceeds, typically prioritizing those not yet in the `linking_map.json` or those marked for re-analysis.
        -   **Desired Behavior (Latter):** Your preference for clearing only "scraped and not analyzed" products is a more advanced cache invalidation strategy. The current implementation is a simpler "clear all for this supplier's raw scrape cache." Implementing selective clearing would be a future enhancement.
-   **Configuration:**
    -   Reads configuration from `config/config.json` or inline defaults.
    -   **Cache Clearing Toggle ----> CLARIFICATION:** The boolean flag `"clear_cache"` in `config/config.json` controls this. As explained above, `true` clears the raw supplier product list cache for the run.
    -   **`"test_mode"` Flag ----> WHAT DOES TEST_MODE DO EXACTLY?:**
        -   When `"test_mode": true` in `config/config.json`, the `passive_extraction_workflow_latest.py` script will process only a small, fixed number of products from each supplier (e.g., the first 10 products found after scraping or from the supplier cache).
        -   This significantly speeds up a run for testing purposes.
        -   It's different from `"max_products_per_supplier"`, which is a general limit for normal runs. `test_mode` effectively overrides this with a much smaller, hardcoded limit (e.g., 10) for the duration of the test run.
        -   All other pipeline stages (Amazon search, data extraction, FBA calculation, logging, reporting) execute as normal for this limited set of products. The *way* these stages run isn't changed, only the *volume* of products they process.
-   **Usage Example:**
    ```bash
    python Amazon-FBA-Agent-System-v3/run_complete_fba_analysis.py
    ```
-   **Test Mode Behavior ----> AI INTEGRATED SCRAPING GUARANTEE:**
    -   If "AI integrated scraping" refers to an LLM suggesting supplier categories/pages to scrape, this suggestion process would still run if it's part of the initial supplier data gathering step.
    -   However, after the AI suggests (for example) 5 categories and those are scraped yielding 100 products, if `test_mode` is `true`, the subsequent `passive_extraction_workflow_latest.py` will only take a small number (e.g., 10) of those 100 products for full Amazon analysis.
    -   So, the AI suggestion part runs, but the *depth of analysis* of its output is limited by `test_mode`.

---

### 2. `main_orchestrator.py`

-   **Purpose:** Coordinates the execution of all workflow modules.
-   **Functionality:** Calls core modules such as passive extraction, supplier parsing, (potentially price analysis if enabled), and FBA fee calculation in sequence.
-   **Outputs ----> MENTION TYPES OF OUTPUTS (SEE DEDICATED SECTION BELOW):**
    -   This script itself doesn't directly create final user-facing files but orchestrates other scripts that do. Its primary output is through logging, detailing the flow of control between different modules. The final files are generated by scripts like `passive_extraction_workflow_latest.py` and `run_complete_fba_analysis.py` (for summary reports). Please see the "Detailed Output File Descriptions" section below.
-   **Notes:**
    -   The **`supplier_api.py`** and **`currency_converter.py`** modules are currently **commented out** within `main_orchestrator.py` and are not part of the active workflow.
    -   The **`price_analyzer.py` ----> CLARIFICATION & COMMENT OUT:**
        -   **Purpose & Timing:** `price_analyzer.py` is intended to be used *after* initial supplier data is scraped and *after* corresponding Amazon product data (including selling price) is found, and typically *after* FBA fees are calculated by `fba_calculator.py`. Its role is to apply more complex business logic to determine profitability beyond just raw FBA fees – for example, checking against desired ROI percentages, minimum profit margins, or sales velocity indicators (if BSR is used).
        -   **Current Status:** As per your request, this module will be treated as **commented out / not active** in the primary workflow for now. It can be integrated later for advanced filtering.
    -   The orchestrator respects the `"clear_cache"` flag from the configuration.
    -   **Linking Map ----> OVERRIDE & BACKUP CLARIFICATION:**
        -   **Not Overridden:** The main `linking_map.json` (located at `OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json`) is **updated, not completely overridden** on each run. The system loads the existing map, adds new EAN-ASIN links or updates existing ones if a product is re-analyzed, and then saves the entire map back. This preserves history across runs.
        -   **Backup:** The system is designed to create a timestamped backup of the `linking_map.json` at the **start of each analysis run**. This backup is saved in a subfolder like `OUTPUTS/FBA_ANALYSIS/Linking map/backup/linking_map_backup_YYYYMMDD_HHMMSS.json`. This is a safety measure to prevent accidental data loss if a run is interrupted or an error occurs during the update of the main linking map.

---

### 3. `passive_extraction_workflow_latest.py`

-   **Purpose:** Implements the passive extraction workflow, which includes scraping supplier products (if not cached), searching for them on Amazon, extracting Amazon product data, and calculating FBA fees.
-   **Functionality:**
    -   Performs EAN and title-based Amazon searches.
    -   Extracts detailed Amazon product data (price, images, BSR, reviews, etc.).
    -   Integrates with `fba_calculator.py` for fee calculations.
    -   Maintains and updates the **linking map** (persistent memory).
-   **Outputs ----> MENTION FILES/FOLDERS (SEE DEDICATED SECTION BELOW):**
    -   This script is a primary generator of data files. See the "Detailed Output File Descriptions" section.
-   **Enhancements:**
    -   **Linking Map for AI Memory ----> HOW AI AVOIDS RESUGGESTING:**
        -   The `linking_map.json` (or a similar persistent file managed by `data_store.py`) is key. When the AI is used to suggest supplier categories or pages to scrape, the following happens:
            1.  Before asking the AI for new suggestions, the system reads the `linking_map.json` (or a dedicated list within it/alongside it) to find all supplier category URLs or page identifiers that have *already been successfully scraped and processed* in previous runs or earlier in the current run.
            2.  This list of "already processed/visited supplier locations" is then provided to the AI as part of its input prompt.
            3.  The AI is explicitly instructed in its prompt to *generate suggestions for new categories/pages that are NOT in the provided list of already processed locations*.
            4.  When a new AI-suggested category/page is successfully scraped, its URL/identifier is then added to this "processed" list in the `linking_map.json` (or related file) so it won't be suggested again by the AI in the future.
        -   This mechanism ensures the AI focuses on unexplored parts of supplier websites.
-   **Usage:** Invoked internally by `main_orchestrator.py`.

---

### 4. `config/config.json`

-   **Purpose:** Central configuration file for the system.
-   **Key Parameters (Examples):**
    -   `"clear_cache"` (boolean): `true` to clear raw supplier scrape cache before run, `false` to use existing cache.
    -   `"test_mode"` (boolean): `true` to process a very small number of products (e.g., 10) for quick testing, `false` for normal operation.
    -   `"max_products_per_supplier"` (integer): Max products to analyze from a supplier in a normal run.
    -   `"suppliers"` (object): Contains configurations for each supplier (e.g., URL, specific parsing rules if any).
    -   `"enable_profitable_filtering"` (boolean): (Currently effectively off if `price_analyzer.py` is commented out) Toggles advanced profitability checks.
    -   `"enable_system_monitoring"` (boolean): Toggles logging of system performance metrics.
-   **Example:**
    ```json
    {
      "clear_cache": true,
      "test_mode": false,
      "max_products_per_supplier": 100,
      "suppliers": {
        "clearance-king.co.uk": {
          "url": "https://www.clearance-king.co.uk",
          "parser_type": "default" // Example, might specify a parser from supplier_parser.py
        }
      },
      "enable_profitable_filtering": false, // Assuming price_analyzer is off for now
      "enable_system_monitoring": true
    }
    ```

---

## Detailed Output File Descriptions

The system generates several types of output files, primarily stored under the `OUTPUTS/` directory:

1.  **Overall Run Report:**
    -   **File:** `OUTPUTS/FBA_ANALYSIS/report_YYYYMMDD_HHMMSS.json`
    -   **Content:** JSON object with summary statistics for the entire analysis session (e.g., total products processed, profitable found, errors, timings).
    -   **Generated by:** `run_complete_fba_analysis.py` at the end of the orchestrator's execution.

2.  **Supplier-Specific Summary:**
    -   **File:** `OUTPUTS/FBA_ANALYSIS/fba_summary_SUPPLIERNAME_YYYYMMDD_HHMMSS.json`
    -   **Content:** JSON array, where each object represents a product analyzed from that supplier. Includes supplier details, matched Amazon details, FBA fees, and profitability.
    -   **Generated by:** `passive_extraction_workflow_latest.py` (or orchestrated by it) for each supplier session.

3.  **Linking Map (Memory System):**
    -   **File:** `OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json`
    -   **Content:** JSON
