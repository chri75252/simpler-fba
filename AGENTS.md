# FBA Agent System: Component Architecture

**Last Updated:** 2025-07-15

This document provides a detailed breakdown of the individual "agents" or autonomous components that make up the Amazon FBA Agent System. Each agent has a specialized role, and they work together in a pipeline to automate the process of finding profitable products.

---

## High-Level Workflow

The system operates as a sequential pipeline, where the output of one agent often becomes the input for the next. The `PassiveExtractionWorkflow` class acts as the central orchestrator, coordinating the execution of these agents.

**Browser Automation Note:** Playwright is the primary library for browser automation. If Playwright cannot be installed, use the `browser_automation` Selenium adapter which mimics the Playwright API.

```
[ Start ]
    |
    ▼
[ 1. Authentication Agent ]
 (Ensures session is logged in)
    |
    ▼
[ 2. Supplier Scraping Agent ]
 (Scrapes product data from supplier website)
    |
    ▼
[ 3. Amazon Matching & Extraction Agent ]
 (Finds products on Amazon and extracts data)
    |
    ▼
[ 4. Financial Analysis Agent ]
 (Calculates profitability)
    |
    ▼
[ 5. State Management Agent ]
 (Tracks progress and saves results)
    |
    ▼
[ End ]
```

---

## Agent Definitions

### 1. Authentication Agent

-   **Primary Script:** `tools/supplier_authentication_service.py`
-   **Core Responsibility:** To ensure the browser session is authenticated with the supplier website (`poundwholesale.co.uk`) before any scraping begins. It is responsible for handling the entire login lifecycle.
-   **Inputs:**
    -   Credentials (email, password) from `config/system_config.json`.
    -   A Playwright `Page` object to perform actions on.
-   **Outputs:**
    -   An authenticated browser state (via session cookies).
    -   A boolean success/failure status returned to the orchestrator.
-   **Key Logic & Tools:**
    -   It uses the `tools/standalone_playwright_login.py` script as its primary tool.
    -   **Verification Flaw (Identified):** The agent has a two-step verification process. It first looks for visual cues like a "Logout" button, which is unreliable. Its more robust, secondary check is to verify that it can see product prices, which are only visible to logged-in users. The system currently proceeds only if the price check is successful.
-   **Notes:** This agent connects to the user's pre-launched Chrome instance running on a debug port, allowing for visible or "background tab" execution.

### 2. Supplier Scraping Agent

-   **Primary Script:** `tools/configurable_supplier_scraper.py`
-   **Core Responsibility:** To systematically navigate the supplier's category URLs and extract raw product data (title, price, EAN, etc.) for every item it finds.
-   **Inputs:**
    -   A list of category URLs, loaded from `config/poundwholesale_categories.json`.
    -   Configuration settings from `config/system_config.json` (e.g., `max_products_per_category`).
-   **Outputs:**
    -   A list of product data dictionaries, which are held in memory.
    -   **Primary File Output:** `OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json`.
-   **Key Logic & Tools:**
    -   Uses Playwright to navigate pages and BeautifulSoup (implicitly) to parse HTML and find data based on selectors defined in the supplier's config.
-   **Limitations (Identified):** The agent currently scrapes all specified categories and holds the results in memory, only writing to the cache file **at the very end**. This is risky, as a crash during a long scrape would cause all collected data to be lost.

### 3. Amazon Matching & Extraction Agent

-   **Primary Script:** `tools/amazon_playwright_extractor.py` (specifically the `FixedAmazonExtractor` class)
-   **Core Responsibility:** For each supplier product, this agent's job is to find the corresponding product on `amazon.co.uk` and extract a comprehensive set of data from the product detail page.
-   **Inputs:**
    -   A single supplier product object, containing an EAN (if available) and a title.
-   **Outputs:**
    -   A detailed JSON object containing all extracted Amazon data (price, BSR, reviews, etc.).
    -   **Primary File Output:** Individual JSON files in `OUTPUTS/FBA_ANALYSIS/amazon_cache/` (e.g., `amazon_{ASIN}_{EAN}.json`).
-   **Key Logic & Tools:**
    -   **EAN-First Strategy:** It first searches Amazon using the product's EAN for a high-confidence match.
    -   **Title Fallback:** If the EAN search fails or returns no organic results, it falls back to searching by the product's title.
    -   It uses Playwright to control the browser and extract data using CSS selectors.
-   **Notes:** This agent currently uses a "legacy" browser connection, creating its own connection to the debug port instead of using the central `BrowserManager`.

### 4. Financial Analysis Agent

-   **Primary Script:** `tools/FBA_Financial_calculator.py`
-   **Core Responsibility:** To take the data from both the supplier and Amazon and calculate key financial metrics to determine if a product is profitable.
-   **Inputs:**
    -   The combined data object for a single product (containing both supplier and Amazon details).
    -   Financial parameters (VAT rate, referral fees, etc.) from `config/system_config.json`.
-   **Outputs:**
    -   A dictionary of calculated financial data (e.g., `ROI`, `NetProfit`, `fees`).
    -   **Primary File Output:** Appends a row to the final `OUTPUTS/FBA_ANALYSIS/financial_reports/fba_financial_report_{timestamp}.csv`.
-   **Key Logic & Tools:**
    -   This is a pure calculation script; it does not interact with the browser. It applies the business logic defined in its functions to the input data.

### 5. State Management Agent

-   **Primary Script:** `utils/enhanced_state_manager.py`
-   **Core Responsibility:** To act as the system's memory. It tracks which products have already been processed, allowing the workflow to be stopped and resumed without losing progress or re-doing work.
-   **Inputs:**
    -   Status updates from the orchestrator (e.g., "now processing product X," "product Y was profitable").
-   **Outputs:**
    -   **Primary File Output:** `OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json`.
-   **Key Logic & Tools:**
    -   It maintains a dictionary of product URLs that have been processed and their final status.
    -   It tracks the `last_processed_index` to know where to resume from on the next run.
    -   It includes logic to detect when all cached products have been processed, preventing the system from running unnecessarily.