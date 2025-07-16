# Gemini Project Context: Amazon FBA Agent System (v3.5)

**Last Updated:** 2025-07-16

**Objective:** This document serves as the definitive, evidence-backed guide to the Amazon FBA Agent System. It consolidates all verified information about the project's architecture, data flow, critical configurations, nuanced logic, and our shared analysis process.

---

## 1. Project Overview

This project is a specialized FBA (Fulfillment by Amazon) sourcing tool, custom-tailored to scrape and analyze products from the supplier `poundwholesale.co.uk`. The system is designed to be a robust, resumable, and deterministic workflow.

-   **Current State:** The system is fully operational in a **non-AI, selector-based mode**. It does not use any vision or language models for category selection or data extraction.
-   **Entry Point:** The primary script to run the system is `run_custom_poundwholesale.py`.
-   **Core Engine:** The main logic is orchestrated by the `PassiveExtractionWorkflow` class in `tools/passive_extraction_workflow_latest.py`.

---

## 2. Core Architecture & Data Flow

The system follows a sequential, multi-stage process that is designed to be interruptible and resumable at any point. The data flow is critical to understanding its efficiencies and limitations.

### Workflow Diagram

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

### Output File Tracker

| Output Type          | File Path (relative to `output_root`)                               | Content                                                              |
| -------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Supplier Cache**   | `cached_products/poundwholesale-co-uk_products_cache.json`          | Raw product data scraped from the supplier (deduplicated by URL/EAN). |
| **Amazon Data Cache**| `FBA_ANALYSIS/amazon_cache/amazon_{ASIN}_{EAN or title}.json`       | Detailed product data from a single Amazon page.                     |
| **Linking Map**      | `FBA_ANALYSIS/linking_maps/poundwholesale.co.uk/linking_map.json`   | Links supplier EANs to the corresponding Amazon ASINs.               |
| **Financial Report** | `FBA_ANALYSIS/financial_reports/fba_financial_report_{timestamp}.csv` | Complete financial breakdown for all profitable products.            |
| **Processing State** | `CACHE/processing_states/poundwholesale-co-uk_processing_state.json`| Tracks processed products/categories for resumability.               |
| **Logs**             | `logs/debug/run_custom_poundwholesale_{timestamp}.log`              | Full debug logs for each run.                                        |

---

## 3. Analysis and Rectification Log (Key Discoveries)

This section documents the critical nuances of the system's logic that were not immediately apparent and were clarified during our analysis.

### **Discovery 1: The `supplier_cache_control` Logic**

-   **Initial Misconception:** I initially believed the `update_frequency_products` toggle was not working at all or was implemented inside the scraper.
-   **Rectification:** You correctly pointed out that the logic was present but flawed. The workflow was calling the cache save only once *after* all categories were scraped, rendering the frequency setting useless.
-   **Current State:** The code has **not yet been modified** to fix this. It remains a known issue where data from an in-progress category will be lost upon interruption.

### **Discovery 2: The Amazon ASIN Cache Reuse Mechanism**

-   **Initial Misconception:** I incorrectly stated that the system had no fallback for handling multiple EANs pointing to the same ASIN, leading to redundant Amazon searches.
-   **Rectification:** You provided the code snippet for `_check_amazon_cache_by_asin`, which proved this assumption wrong. The system is, in fact, quite intelligent here.
-   **Verified Logic:** The system **does** check for an existing ASIN in the cache, even if it was saved under a different EAN. It performs a `glob.glob(f"amazon_{asin}_*.json")` search. If it finds a match, it reuses the data and copies it to a new file with the new EAN, preventing a redundant live extraction. This is a critical efficiency feature.

### **Discovery 3: The True Nature of Deduplication**

-   **Initial Misconception:** I did not initially distinguish clearly between the different layers of deduplication.
-   **Rectification:** Our discussion clarified that there are three distinct deduplication steps:
    1.  **Supplier Cache:** Prevents the same supplier URL or EAN from being processed twice.
    2.  **Amazon Cache:** Prevents re-fetching data for an ASIN that has already been seen.
    3.  **Linking Map:** Ensures the final EAN-to-ASIN map is clean.
-   **Conclusion:** The combination of these three steps makes the system highly resistant to processing duplicate data, although the linking map can still contain multiple EANs pointing to the same ASIN, which is expected behavior.

---

## 4. Verified Toggle Behavior (`system_config.json`)

This is a definitive guide to the most important toggles and their actual behavior.

### **Data Flow & Processing Limits**

-   `system.max_products`: A hard limit on the total number of products to process in a single run.
-   `system.max_products_per_category`: **This is the functional toggle.** It limits how many products are scraped from each category URL.
-   `processing_limits.max_products_per_category`: **This is a non-functional, duplicate toggle.** It is ignored by the system.

### **Workflow, Caching, and Recovery**

-   **`hybrid_processing.enabled: true`**: When `true`, the system operates in "chunked" mode, alternating between scraping a `chunk_size_categories` number of categories and analyzing them on Amazon.
-   **`supplier_cache_control.update_frequency_products`**: **This toggle is NOT implemented correctly.** The cache is only saved after a full category is scraped.
-   **`supplier_extraction_progress.recovery_mode: "product_resume"`**: The recommended setting. Ensures the system resumes from the exact product it was processing.

### **Non-Integrated Toggles (CRITICAL EXCEPTIONS)**

The following settings are **ignored** in the config file and are instead controlled by **environment variables**:

-   `analysis.min_roi_percent` (uses env var `MIN_ROI_PERCENT`)
-   `analysis.min_profit_per_unit` (uses env var `MIN_PROFIT_PER_UNIT`)
-   `analysis.min_rating` (uses env var `MIN_RATING`)
-   `analysis.min_reviews` (uses env var `MIN_REVIEWS`)
-   `analysis.max_sales_rank` (uses env var `MAX_SALES_RANK`)

---

## 5. How to Run the System for Different Scenarios

### **A. Quick Test Run (Finite Mode)**

This is for testing changes and ensuring the system runs without errors.

```json
{
  "system": {
    "max_products": 20,
    "max_analyzed_products": 20,
    "max_products_per_category": 5
  },
  "hybrid_processing": {
    "enabled": false
  }
}
```

### **B. Full Catalog Analysis ("Infinite" Mode)**

This configuration is designed for maximum reliability and the ability to analyze results while the system runs.

```json
{
  "system": {
    "max_products": 999999,
    "max_analyzed_products": 999999,
    "max_products_per_category": 999999,
    "max_products_per_cycle": 50
  },
  "supplier_cache_control": {
    "enabled": true,
    "update_frequency_products": 10,
    "force_update_on_interruption": true
  },
  "hybrid_processing": {
    "enabled": true,
    "processing_modes": {
      "chunked": {
        "enabled": true,
        "chunk_size_categories": 10
      }
    }
  },
  "batch_synchronization": {
    "enabled": false
  }
}
```

---

## 6. Deeper Analysis of Key Components

### **`PassiveExtractionWorkflow` (`tools/passive_extraction_workflow_latest.py`)**

This class is the central orchestrator. Key observations:

-   **Stateful Design:** The class heavily relies on the `EnhancedStateManager` to load and save its progress. The `run()` method begins by loading the state and `linking_map`, demonstrating its resumable nature.
-   **Configuration-Driven:** All major parameters (product limits, batch sizes, etc.) are correctly read from `self.system_config` at runtime.
-   **Hybrid Mode Logic:** The `run()` method contains a critical fork. If `hybrid_processing` is enabled, it delegates control to the `_run_hybrid_processing_mode()` method, which fundamentally changes the execution flow from sequential to chunk-based.
-   **Error Handling:** The main processing loops have `try...except` blocks to catch errors during scraping or analysis, allowing the workflow to continue with the next item rather than crashing.

### **Batches vs. Chunks: A Critical Distinction**

-   **Batches (`supplier_extraction_batch_size`):** This is a **memory management** feature. It groups categories together for logging and state tracking during the supplier scraping phase. It does **not** affect when the system switches to Amazon analysis.
-   **Chunks (`hybrid_processing.chunked.chunk_size_categories`):** This is a **workflow control** feature. It dictates how many categories are scraped before the *entire system* pauses scraping and switches to analyzing the products from that chunk on Amazon.

### **Test Environment Setup (`requirements.txt`)**

The testing framework (`pytest`) will fail without the correct dependencies. A `requirements.txt` file is necessary for a stable development and testing environment.

```
# requirements.txt
playwright
beautifulsoup4
requests
python-dotenv
pandas
openai
pytest
freezegun
jsonschema
```