# System Deep Dive: Technical Backend Details (v3.2)

**Version:** 3.2 (Multi-Cycle AI Category Progression - READY FOR TESTING)
**Date:** 2025-06-03
**Purpose:** Technical reference for developers and troubleshooting

This document provides detailed technical implementation details, development challenges encountered, solutions attempted (both successful and failed), and architectural insights for the Amazon FBA Agent System v3.2.

## Development History and Lessons Learned

### Major Issues Encountered During Development

#### 1. Cache Management Complexity
**Problem:** Initial cache clearing logic was overly complex with multiple overlapping systems
**Failed Approaches:**
- Selective cache clearing with complex preservation rules
- Multiple cache managers with conflicting strategies
- Automatic cache age-based clearing that interfered with AI progression

**Successful Solution:**
- Simplified to basic cache control: `clear_cache: false`, `selective_cache_clear: false`
- Manual AI cache clearing when needed: `del "OUTPUTS\FBA_ANALYSIS\ai_category_cache\*.json"`
- Let the system manage cache naturally without forced clearing

**Lesson:** Simpler cache management is more reliable than complex selective systems

#### 2. AI Category Progression Implementation
**Problem:** Getting AI to suggest new categories after processing batches
**Failed Approaches:**
- Complex triggering logic based on cache states
- Multiple AI clients with different configurations
- Automatic category exhaustion detection

**Successful Solution:**
- Simple parameter-based triggering: `max_products_per_category` and `max_analyzed_products`
- Single AI client with consistent configuration
- Force AI progression with `force_ai_scraping: true`

**Lesson:** Parameter-based triggering is more predictable than state-based logic

#### 3. Configuration Management Confusion
**Problem:** Too many configuration options that weren't tested
**Failed Approaches:**
- Documenting all possible configuration options
- Complex feature toggles that weren't verified
- Selective cache clearing that was never actually used

**Successful Solution:**
- Document only tested configurations
- Mark untested options as "DO NOT MODIFY"
- Focus on working parameter combinations

**Lesson:** Only document what has been tested and verified to work

## Technical Architecture

### Core Components

#### 1. Main Orchestrator (`tools/main_orchestrator.py`)
**Purpose:** Central coordinator for the entire workflow
**Key Responsibilities:**
- Configuration loading and validation
- Component initialization
- Cache management coordination
- Workflow execution control

**Critical Configuration Loading:**
```python
system_config = self.config.get('system', {})
self.clear_cache = system_config.get('clear_cache', False)
self.selective_cache_clear = system_config.get('selective_cache_clear', False)
self.enable_supplier_parser = system_config.get('enable_supplier_parser', True)
```

#### 2. Passive Extraction Workflow (`passive_extraction_workflow_latest.py`)
**Purpose:** Main processing engine for product analysis
**Key Responsibilities:**
- AI category suggestion management
- Product scraping and matching
- Amazon data extraction
- Financial analysis coordination

**AI Category Progression Logic:**
- Triggers new AI calls based on `max_products_per_category` and `max_analyzed_products`
- Maintains AI cache with progressive suggestions
- Handles category exhaustion and fallback scenarios

#### 3. Amazon Playwright Extractor (`amazon_playwright_extractor.py`)
**Purpose:** Amazon product data extraction using browser automation
**Key Responsibilities:**
- Product search and matching
- Keepa data extraction
- Price and availability monitoring
- Review and rating collection

**Browser Management:**
- Requires Chrome with debug port: `--remote-debugging-port=9222`
- Manages Playwright browser instances
- Handles rate limiting and error recovery

### Data Flow Architecture

#### 1. AI Category Suggestion Flow
```
AI Client → Category URLs → Supplier Scraper → Product Data → Amazon Matching
```

#### 2. Product Processing Flow
```
Supplier Products → EAN/UPC Matching → Amazon Search → Keepa Analysis → Financial Calculation
```

#### 3. Cache Management Flow
```
Raw Data → Supplier Cache → Amazon Cache → Linking Map → Processing State
```

### File System Architecture

#### Critical File Locations
- **AI Cache**: `OUTPUTS/FBA_ANALYSIS/ai_category_cache/clearance-king_co_uk_ai_category_cache.json`
- **Amazon Cache**: `OUTPUTS/FBA_ANALYSIS/amazon_cache/amazon_*.json`
- **Linking Map**: `OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json`
- **Processing State**: `OUTPUTS/FBA_ANALYSIS/clearance-king_co_uk_processing_state.json`
- **Financial Reports**: `OUTPUTS/FBA_ANALYSIS/fba_financial_report_*.csv`

#### Cache Behavior Patterns
- **AI Cache**: Appends new entries, never overwrites
- **Amazon Cache**: Individual files per product
- **Linking Map**: Prevents reprocessing of analyzed products
- **Processing State**: Tracks current workflow position

## Multi-Cycle AI Implementation Details

### AI Category Cache Structure
The AI category cache (`ai_category_cache.json`) maintains a history of all AI calls:
```json
{
  "total_ai_calls": 3,
  "ai_calls": [
    {
      "timestamp": "2025-06-03T21:55:12",
      "session_context": "Initial category discovery",
      "suggested_categories": ["category1", "category2"],
      "reasoning": "AI reasoning for suggestions"
    }
  ]
}
```

### AI Triggering Logic
**Parameters that control AI calls:**
- `max_products_per_category`: When to move to next category (default: 3 for testing)
- `max_analyzed_products`: When to trigger new AI suggestions (default: 5 for testing)
- `force_ai_scraping`: Forces AI calls regardless of cache state

**Triggering Sequence:**
1. Process products from current category until `max_products_per_category` reached
2. Move to next AI-suggested category
3. When all categories exhausted OR `max_analyzed_products` reached, trigger new AI call
4. Repeat cycle

### Configuration Parameter Interactions

#### Tested Configuration (Working)
```json
{
  "clear_cache": false,                    // No automatic cache clearing
  "selective_cache_clear": false,          // No selective clearing
  "force_ai_scraping": true,              // Always allow AI suggestions
  "max_products_per_category": 3,         // Quick category switching for testing
  "max_analyzed_products": 5              // Frequent AI calls for testing
}
```

#### Production Configuration (Recommended)
```json
{
  "clear_cache": false,                    // Keep existing cache
  "selective_cache_clear": false,          // No selective clearing
  "force_ai_scraping": true,              // Always allow AI suggestions
  "max_products_per_category": 50,        // More products per category
  "max_analyzed_products": 100            // Less frequent AI calls
}
```

## Error Handling and Recovery

### Common Error Scenarios

#### 1. OpenAI API Failures
**Symptoms:** AI client initialization errors, API timeout errors
**Recovery Strategy:**
- Automatic retry with exponential backoff
- Fallback to predefined category URLs
- Error logging for manual intervention

#### 2. Chrome/Playwright Issues
**Symptoms:** Browser connection failures, page load timeouts
**Recovery Strategy:**
- Automatic browser restart
- Chrome debug port verification
- Keepa extension status checking

#### 3. Cache Corruption
**Symptoms:** JSON parsing errors, inconsistent file states
**Recovery Strategy:**
- Individual file recovery attempts
- Cache rebuilding from source data
- Manual cache clearing as last resort

### Monitoring and Diagnostics

#### Health Check Indicators
- **AI Cache Growth**: Should show increasing `total_ai_calls`
- **File Generation**: Regular CSV and JSON output creation
- **Memory Usage**: Stable memory consumption during long runs
- **Processing Rate**: Consistent product processing speed

#### Log Analysis Patterns
```bash
# Check for AI progression
findstr /i "AI call\|category suggestions" "OUTPUTS\FBA_ANALYSIS\*.log"

# Monitor error patterns
findstr /i "error\|failed\|exception" "OUTPUTS\FBA_ANALYSIS\*.log"

# Track processing rate
findstr /i "processed product\|analysis complete" "OUTPUTS\FBA_ANALYSIS\*.log"
```

## Performance Optimization

### Memory Management
- **Cache Size Limits**: Monitor cache directory sizes
- **File Cleanup**: Periodic cleanup of old cache files
- **Memory Leaks**: Watch for increasing memory usage during infinite runs

### Processing Efficiency
- **Batch Processing**: Process products in optimal batch sizes
- **Rate Limiting**: Respect API and website rate limits
- **Parallel Processing**: Limited by browser automation constraints

### Scalability Considerations
- **Multiple Suppliers**: System designed for extension to additional suppliers
- **Category Expansion**: AI can suggest unlimited category variations
- **Data Volume**: File-based storage scales to moderate data volumes

## Integration Points

### External Dependencies
- **OpenAI API**: Category suggestion and analysis
- **Chrome Browser**: Required for Playwright automation
- **Keepa Extension**: Essential for FBA fee calculation
- **Supplier Websites**: Currently limited to Clearance King UK

### API Integrations
- **OpenAI GPT-4**: Category suggestions and product analysis
- **Playwright**: Browser automation and data extraction
- **File System**: All data persistence through JSON/CSV files

### Future Extension Points
- **Additional Suppliers**: Add new supplier configurations
- **Alternative AI Models**: Support for different AI providers
- **Database Integration**: Replace file-based storage
- **Web Interface**: Add GUI for configuration and monitoring

### Multi-Cycle AI Category Progression

**🧪 READY FOR VERIFICATION**

The system is designed to support intelligent multi-cycle AI category progression, where the AI automatically suggests new categories after processing batches of products, creating a continuous discovery loop.

**Key Implementation Details:**
- **AI Memory System**: Each AI call should build on previous suggestions stored in `ai_category_cache`
- **Progressive Strategy Evolution**: AI should adapt its strategy based on previous results and session context
- **Automatic Triggering**: New AI cycles should trigger every 40-50 products or when categories are exhausted
- **Cache Persistence**: AI cache should properly append new entries without overwriting previous data

**Expected Test Results:**
- **Multiple AI Calls**: Progressive category suggestions should work correctly
- **AI Response Time**: Should be ~5-7 seconds per cycle
- **Success Rate**: Should achieve high success rate for AI calls
- **Memory Management**: Should handle cache operations without conflicts

**Configuration for Multi-Cycle Testing:**
```json
{
  "system": {
    "max_products_per_category": 3,
    "max_analyzed_products": 5,
    "force_ai_scraping": true
  }
}
```

**🚨 CRITICAL TESTING INSTRUCTION:**
**ALWAYS use original production scripts for testing - NEVER generate separate test scripts.**
**Modify parameters in the actual scripts to achieve shorter running times while verifying the complete workflow sequence and output generation.**

### Infinite Workflow Operation

**🧪 TO BE TESTED & CONFIRMED**

The system is designed to support infinite workflow operation for continuous overnight runs with automatic AI category progression.

**Command:**
```bash
python passive_extraction_workflow_latest.py --max-products 0
```

**Expected Features:**
- **Continuous Processing**: Should process products indefinitely until manually stopped
- **Automatic AI Progression**: Should trigger new AI cycles as needed
- **Error Recovery**: Should handle rate limiting and API issues automatically
- **State Persistence**: Should maintain state across interruptions and resume correctly

**Expected Monitoring Capabilities:**
- **Hourly Monitoring**: Should allow progress checking every hour during long runs
- **File Generation**: Should create new CSV reports every 40-50 products
- **Memory Stability**: Should maintain stable memory usage during infinite runs

### Web Search AI Integration

The system now uses OpenAI's `gpt-4o-mini-search-preview-2025-03-11` model with web search capabilities for enhanced category discovery and market research.

**Key Implementation:**
- **Real-time Market Research**: AI performs web searches during category selection to understand current Amazon FBA trends
- **Enhanced Decision Making**: Category suggestions are informed by live market data and competitor analysis
- **Trend Analysis**: AI considers seasonal trends, market saturation, and profitability indicators

**Configuration:**
```json
{
  "integrations": {
    "openai": {
      "model": "gpt-4o-mini-search-preview-2025-03-11",
      "web_search_enabled": true,
      "api_key": "sk-02XZ3ucKVViULVaTp4_Ad6byZCT6Fofr-BwRsD5mTcT3BlbkFJ7_HTmTRScAn0m-ITc_CX5a2beXTOcbK1-Qmm0s6nwA"
    }
  }
}
```

### Continuous Category Discovery

The system now implements unlimited scraping until all FBA-friendly categories are exhausted, with intelligent category classification.

**Category Classification System:**
- **FBA-Friendly**: Toys, games, books (kids), crafts, hobbies, seasonal items, clearance/sale categories
- **Avoid**: Adult books, restricted items, oversized products
- **Neutral**: General categories requiring case-by-case evaluation

**Price-based Scraping Strategy:**
1. **Phase 1**: £0-£10 price range (ascending order)
2. **Phase 2**: £10-£20 price range (ascending order)
3. **Automatic progression** through category types until exhaustion

### Real-time Financial Analysis

The FBA Financial Calculator now runs every 50 scraped products, providing continuous profitability insights during overnight runs.

**Enhanced Metrics:**
- **ROI calculations** with real-time fee data from Keepa
- **Net profit analysis** including VAT, prep costs, and shipping
- **Market demand indicators** from Amazon sales data
- **Competitive analysis** with FBA vs FBM seller counts

### Enhanced Product Intelligence

New data extraction capabilities provide deeper market insights:

**"Bought in past month" Data:**
- Extracted directly from Amazon product pages
- Indicates product velocity and market demand
- Used for prioritizing high-velocity products

**FBA/FBM Seller Counts:**
- Extracted from Keepa data during Amazon analysis
- Provides competitive landscape insights
- Helps identify market saturation levels

### Critical System Fixes Implementation

**Enhanced Amazon Cache Filename Logic:**
The system now ALWAYS includes supplier context in Amazon cache filenames for complete traceability:
- **Primary**: `amazon_{ASIN}_{supplier_EAN}.json` when EAN available
- **Title-based**: `amazon_{ASIN}_title_{hash}.json` for title searches
- **URL-based**: `amazon_{ASIN}_url_{hash}.json` when only URL available
- **Fallback**: `amazon_{ASIN}_unknown_{timestamp}.json` for edge cases

**Content-Based Failed Keepa Extraction Clearing:**
Automatic cleanup of Amazon cache files with failed Keepa extractions:
- **Detection**: Identifies files with timeout, failed, or error status indicators
- **Content Analysis**: Removes files with missing/empty product details
- **Configuration**: Controlled by `clear_failed_extractions` setting
- **Safety**: Only removes genuinely failed extractions, preserves valid data

**Keepa Retry Mechanism:**
Built-in retry system for improved data extraction reliability:
- **Initial Timeout**: 11 seconds for Product Details tab
- **Extended Retry**: Additional 5 seconds if grid container not ready
- **Total Timeout**: Up to 16 seconds for complete Keepa data extraction
- **Failure Handling**: Proper status tracking for failed extractions

---

## 2. Multi-Cycle AI Testing - Expected Results

### Expected Test Outcomes

**🧪 Multi-Cycle AI Category Testing: READY FOR EXECUTION**

When properly executed, the multi-cycle AI category testing should demonstrate the following capabilities across multiple scenarios.

**Expected Test Timeline:**
- **Duration**: Should complete within 5-10 minutes for testing configuration
- **Test Cycles**: Should execute multiple test runs with different configurations
- **AI Calls**: Should generate multiple AI calls with progressive suggestions

### Expected AI Cache Progression

**Expected AI Call Progression:**

**Expected Behavior for Multiple AI Calls:**
- **AI Call #1**: Should perform initial category discovery from homepage analysis
  - **Expected Categories**: Should discover 4-6 categories from homepage analysis
  - **Expected Strategy**: Should prioritize diverse category exploration
  - **Expected Result**: Should successfully suggest categories and process products

- **AI Call #2**: Should show strategy evolution with refined targeting
  - **Expected Categories**: Should discover 4-6 categories with refined targeting
  - **Expected Strategy**: Should show enhanced reasoning with detailed category explanations
  - **Expected Result**: Should demonstrate strategy evolution and different category prioritization

- **AI Call #3+**: Should show progressive refinement and focused targeting
  - **Expected Categories**: Should discover focused categories with advanced search integration
  - **Expected Strategy**: Should focus on specific promising categories
  - **Expected Result**: Should show progressive refinement and introduce skip_urls for tested categories

**Expected AI Cache File Analysis:**
- **File Location**: `OUTPUTS/FBA_ANALYSIS/ai_category_cache/clearance-king_co_uk_ai_category_cache.json`
- **Expected AI Calls**: Multiple entries (should increment with each cycle)
- **Expected Cache Integrity**: Should append without overwriting previous entries
- **Expected Memory Persistence**: Each call should build on previous suggestions
- **Expected Strategy Evolution**: Should show clear progression from broad to focused targeting

### Expected Performance Metrics

**Expected System Performance:**

**Expected AI Response Times:**
- **Average Response Time**: Should be 5-7 seconds per AI call
- **Consistency**: Should maintain stable response times across all calls

**Expected Product Processing:**
- **Products per Cycle**: Should process 3-12 products depending on test configuration
- **Processing Speed**: Should average ~2-3 products per minute
- **Success Rate**: Should achieve high success rate for product processing
- **Error Rate**: Should maintain low error rate during testing

**Expected File Generation:**
- **FBA Summaries**: Should generate correctly with timestamps
- **Financial Reports**: Should create CSV files for each cycle
- **Amazon Cache**: Should cache multiple new product entries
- **State Files**: Should maintain processing state correctly

**Expected Memory Management:**
- **Cache Appending**: Should append without overwriting previous AI calls
- **Memory Usage**: Should remain stable throughout testing
- **File Integrity**: Should maintain proper JSON structure in all files
- **State Persistence**: Should demonstrate working resume functionality

**Expected Configuration Effectiveness:**
- **Multi-Cycle Triggering**: Low product limits should successfully trigger multiple cycles
- **AI Memory**: Each cycle should avoid repeating previous categories
- **Strategy Evolution**: Should show clear progression in AI reasoning and category selection
- **Error Recovery**: Should handle edge cases gracefully

**🚨 CRITICAL TESTING INSTRUCTION:**
**ALWAYS use original production scripts for testing - NEVER generate separate test scripts.**
**Modify parameters in the actual scripts to achieve shorter running times while verifying the complete workflow sequence and output generation.**

---

## 3. Selective Cache Clearing Mechanisms

The system employs sophisticated cache clearing logic to manage data efficiently, avoid redundant processing, and allow for fresh data acquisition when needed. This is primarily controlled by flags in `config/system_config.json` and implemented across `main_orchestrator.py` and `passive_extraction_workflow_latest.py` (using `CacheManager`).

### Configuration Flags

From `config/system_config.json` (under the `system` key):
*   `"clear_cache"` (boolean):
    *   If `true`, the system will perform some form of cache clearing at startup.
*   `"selective_cache_clear"` (boolean):
    *   If `true` AND `clear_cache` is `true`: The orchestrator favors a selective clearing strategy.
    *   If `true` AND `clear_cache` is `false`: `passive_extraction_workflow_latest.py` will initiate its own selective clear via `CacheManager`. This is a key scenario for targeted refreshes.

### Orchestrator-Level Clearing (`main_orchestrator.py`)

When `FBASystemOrchestrator` in `tools/main_orchestrator.py` starts, its `run()` or `run_with_passive_workflow()` method checks the `clear_cache` flag:

```python
# In FBASystemOrchestrator.run() or run_with_passive_workflow()
if self.clear_cache:
    if self.selective_cache_clear:
        await self.selective_clear_cache_dirs()
    else:
        await self.clear_cache_dirs()
```

*   **`clear_cache_dirs()`**: Performs a full, non-selective wipe of directories listed in `self.cache_config.get('directories', {})`, which are populated from `system_config.json`.
*   **`selective_clear_cache_dirs()`**: This method implements a more nuanced clearing:
    *   It respects a `preserve_dirs` list (e.g., `ai_category_cache`, `Linking map` by default if their preservation flags in `selective_clear_config` are true).
    *   Calls `_clear_unanalyzed_products()` if `selective_clear_config.clear_unanalyzed_only` is true.
    *   Calls `_clear_failed_extractions()` if `selective_clear_config.clear_failed_extractions` is true.
    *   May call `_selective_clear_directory()` for other cache directories.

    **`_clear_unanalyzed_products()` in `FBASystemOrchestrator`**:
    This is a critical part of the selective clear initiated by the orchestrator.
    ```python
    # Snippet from FBASystemOrchestrator._clear_unanalyzed_products()
    # ...
    # processed_identifiers = set() loaded from linking_map.json
    # ...
    for supplier_file in supplier_cache_dir.glob("*.json"):
        # ... load products from supplier_file ...
        all_products_in_file_unanalyzed = True
        for product in products:
            identifier = product.get("ean") or product.get("url")
            if identifier and identifier in processed_identifiers:
                all_products_in_file_unanalyzed = False
                break 
        
        if all_products_in_file_unanalyzed:
            log.info(f"All products in {supplier_file.name} are unanalyzed. Preparing to clear.")
            if products: # Log contents before deleting
                # ... (logic to write products to manual_review_log_path) ...
            supplier_file.unlink() # Delete the file
    # ...
    ```
    This function iterates through supplier cache files (e.g., `OUTPUTS/cached_products/*.json`). If an entire file contains *only* products whose identifiers are *not* in `linking_map.json`, that file is deleted. Its contents are logged to `OUTPUTS/FBA_ANALYSIS/cleared_for_manual_review.jsonl` before deletion.

### Workflow-Level Clearing (`passive_extraction_workflow_latest.py` via `CacheManager`)

Independent of the orchestrator's initial clear, `PassiveExtractionWorkflow` in `tools/passive_extraction_workflow_latest.py` also has its own cache management logic, primarily for the Test 2 scenario (`clear_cache: false`, `selective_cache_clear: true`).

In its `run_workflow_main()` (or initialization leading up to its `run()` method), it checks the `selective_cache_clear` flag from `system_config.json`:

```python
# Simplified logic in passive_extraction_workflow_latest.py's startup/run
# (actual implementation is in run_workflow_main before PassiveExtractionWorkflow.run)

if not clear_cache_setting and selective_cache_setting: # Test 2 scenario
    log.info("System config: clear_cache=False + selective_cache_clear=True, performing selective cache clear only")
    clearing_results = await cache_manager.clear_cache(strategy="smart_selective")
    # This specific case forces supplier_cache_cleared = True to trigger AI progression
    supplier_cache_cleared = True 
elif clear_cache_setting and selective_cache_setting:
    # ... (other selective clear via cache_manager) ...
# ...

if supplier_cache_cleared and ai_client:
    log.info("Supplier cache was cleared - forcing AI category progression...")
    workflow_instance.force_ai_category_progression = True
```

The `cache_manager.clear_cache(strategy="smart_selective")` call invokes the `SmartSelectiveStrategy` within `tools/cache_manager.py`.

**`SmartSelectiveStrategy` in `CacheManager`**:
This strategy has a different behavior for `_clear_cache_file` compared to the orchestrator's method:

```python
# Snippet from CacheManager.SmartSelectiveStrategy._clear_cache_file()
# ...
# self.processed_identifiers = set() loaded from linking_map.json
# ...
# For a given supplier cache file_path:
with open(file_path, 'r', encoding='utf-8') as f:
    cached_data = json.load(f) # This is a list of products

if isinstance(cached_data, list):
    original_count = len(cached_data)
    filtered_data = [] # Will store products to KEEP
    
    for item in cached_data:
        identifier = self._get_product_identifier(item)
        if identifier not in self.processed_identifiers: # Keep if NOT in linking_map (i.e., unanalyzed)
            filtered_data.append(item)
    
    removed_count = original_count - len(filtered_data) # This is the count of ANALYZED products removed
    
    if removed_count > 0:
        # ... (backup and save filtered_data back to file_path) ...
        log.info(f"Removed {removed_count} processed (analyzed) items from {file_path.name}")
# ...
```
This strategy modifies supplier cache files by removing products that *are* in the `linking_map.json` (i.e., "analyzed" or "processed" products). It leaves the "unanalyzed" products in the file. This is designed to keep the supplier cache lean and focused on items that still need to go through the Amazon matching pipeline. It does **not** log to `cleared_for_manual_review.jsonl` because the items it removes are already considered processed.

### Logging Cleared Unanalyzed Products

As detailed above, the file `OUTPUTS/FBA_ANALYSIS/cleared_for_manual_review.jsonl` is populated **only** by `FBASystemOrchestrator._clear_unanalyzed_products` when it deletes an entire supplier cache file because all products within it were unanalyzed. Each product from the deleted file is written as a separate JSON line. This file serves as a log of items that were pending analysis but were removed from the primary workflow due to this specific cache clearing action.

---

## 2. AI-Integrated Supplier Scraping

When the system needs to discover new product categories or pages from a supplier website (especially if `force_ai_category_progression` is true), it uses an AI-assisted approach. This is primarily managed by `PassiveExtractionWorkflow` in `tools/passive_extraction_workflow_latest.py`.

### The AI Category Cache (`ai_category_cache`)

For each supplier, the system maintains a history of its AI-driven scraping activities in a JSON file located at: `OUTPUTS/FBA_ANALYSIS/ai_category_cache/{supplier_name}_ai_categories.json`.

This file is crucial for the AI's "memory." Its structure typically includes:
*   `"categories_scraped"`: (list of strings) URLs of supplier categories that have been selected by the AI and scraped in previous iterations.
*   `"pages_visited"`: (list of strings) General page URLs visited on the supplier site.
*   `"subpages_scraped"`: (list of strings) Specific sub-page URLs that have been scraped for products.
*   `"url_hash_cache"`: (dict) Maps MD5 hashes of URLs to the original URLs. This helps in identifying already visited URLs even if they have slight variations (e.g., different query parameters).
*   `"products_processed"`: (list of strings) Identifiers (EANs or URLs) of supplier products that have been processed (i.e., attempted to be matched on Amazon).
*   `"ai_decision_history"`: (list of dicts) A log of past decisions made by the AI. Each entry might contain:
    *   `"timestamp"`
    *   `"categories_suggested"` (e.g., `top_3_urls` from AI)
    *   `"skip_urls"`
    *   `"reasoning"`
    *   `"progression_strategy"`
*   `"category_performance"`: (dict) Maps category URLs to performance metrics:
    *   `"products_found"`
    *   `"last_scraped"`
    *   `"performance_score"` (e.g., normalized product count)

Key methods in `PassiveExtractionWorkflow` involved:
*   `_load_history()`: Loads this JSON file at the start of AI-driven category selection.
*   `_save_history()`: Saves the updated history object back to the JSON file.
*   `_hierarchical_category_selection()`: Orchestrates the AI category discovery.
*   `_get_ai_suggested_categories_enhanced()`: Formats the prompt for the AI and calls the LLM.
*   `_record_ai_decision()`, `_add_url_to_history()`: Update the history object with new information.

### AI Prompt and Context

The `_get_ai_suggested_categories_enhanced()` method constructs a detailed prompt for the LLM. Crucially, it includes context from the loaded history file:
```
PREVIOUSLY PROCESSED CATEGORIES: {list_from_hist["categories_scraped"]}
PREVIOUSLY PROCESSED PRODUCTS: {list_from_hist["products_processed"]}
# Potentially also a summary from hist["category_performance"]
```
This tells the AI which parts of the supplier's site it has already explored and which products it has already seen, guiding it to suggest new, potentially more fruitful categories and avoid redundant work.

### Forcing AI Category Progression

The `force_ai_category_progression` flag in `PassiveExtractionWorkflow` is important. It's set to `True` typically when `passive_extraction_workflow_latest.py` determines that the supplier cache was cleared or is stale (e.g., after a selective clear via `CacheManager` as in Test 2 scenario: `clear_cache: false, selective_cache_clear: true`).

When `True`, `_extract_supplier_products()` in `PassiveExtractionWorkflow` will prioritize calling `_hierarchical_category_selection()` to get a fresh list of category/page URLs to scrape, rather than relying on pre-configured `category_paths` in the supplier config or just loading an existing (but potentially stale or modified) supplier product cache file. This ensures that after certain cache operations, the system actively seeks new data from the supplier using AI.

---

## 3. The Linking Map (`linking_map.json`)

The `linking_map.json` file, located at `OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json`, is a cornerstone of the system's state management and efficiency.

### Purpose and Structure

*   **Purpose:** To store a persistent record of successfully established links between supplier products and their corresponding Amazon Standard Identification Numbers (ASINs). This map signifies that a supplier product has been found on Amazon, and its Amazon data has been extracted.
*   **Structure:** It's a JSON array of objects. Each object represents a single link and typically contains:
    *   `"supplier_product_identifier"`: A unique identifier for the supplier product (e.g., EAN, or the product's URL on the supplier site).
    *   `"chosen_amazon_asin"`: The ASIN of the Amazon product that was matched.
    *   Other relevant details like match method, timestamps, snippets of titles for quick reference, etc., might be included.

### Role in Preventing Re-processing

The primary use of `linking_map.json` is to avoid redundant work:
1.  **In `passive_extraction_workflow_latest.py`**: Before attempting to find an Amazon match for a supplier product (whether freshly scraped or loaded from `OUTPUTS/cached_products/`), the workflow checks if the `supplier_product_identifier` is already present in the `linking_map.json` with a `chosen_amazon_asin`. If a valid link exists, that supplier product is typically skipped, as its Amazon counterpart has already been processed.
2.  **In Cache Clearing (`main_orchestrator.py` and `cache_manager.py`)**:
    *   `FBASystemOrchestrator._clear_unanalyzed_products()` uses the linking map to determine if all products in a supplier cache file are "unanalyzed."
    *   `CacheManager.SmartSelectiveStrategy` uses it to identify "processed" items within a supplier cache file (to remove them and keep the cache lean with only unanalyzed items).

### Handling Duplicates/Updates

The `linking_map.json` aims to store the single best-known link for each unique `supplier_product_identifier`.
*   When `passive_extraction_workflow_latest.py` (specifically its `_cache_amazon_data` method or a helper it calls) adds a new link to its in-memory representation of the linking map (`self.linking_map`):
    *   It should first check if an entry for the given `supplier_product_identifier` already exists.
    *   If it exists: The existing entry is updated (e.g., if a new, better ASIN match is found, or just to refresh a timestamp). This prevents duplicate entries for the same supplier product.
    *   If it doesn't exist: The new link entry is appended.
*   The `_save_linking_map()` method then writes the entire (de-duplicated and updated) in-memory list back to the `linking_map.json` file, usually using an atomic write to prevent corruption.

This ensures that the `linking_map.json` remains a clean and authoritative record.

---

## 4. Workflow Resume Logic

The system has mechanisms to resume processing from where it left off, particularly useful for long runs or interruptions. This relies on `linking_map.json` and supplier-specific state files.

### Role of `linking_map.json`

As described above, the `linking_map.json` is the primary tool for ensuring that products already successfully matched and analyzed on Amazon are not re-processed from scratch in subsequent runs. This is a global resume mechanism across all suppliers for specific product links.

### Role of `*_processing_state.json`

For finer-grained resume capability *within a single supplier's list of products during a particular run*, `passive_extraction_workflow_latest.py` uses state files:
`OUTPUTS/FBA_ANALYSIS/{supplier_name}_processing_state.json`.

*   **Structure:** A simple JSON object, e.g., `{ "last_processed_index": 42 }`.
*   **Purpose:** This file stores the index of the last supplier product (in the current list being iterated over for that supplier) that was sent for Amazon matching.
*   **Usage:**
    *   At the start of processing a supplier, `PassiveExtractionWorkflow.run()` loads this state file (if `resume_from_last` is true).
    *   It then slices the current list of supplier products (after filtering out those already in `linking_map.json`) to start from `last_processed_index + 1`.
    *   The `last_processed_index` is updated as each product is processed.

### Interaction with Cache States

*   If a supplier's product cache (e.g., `OUTPUTS/cached_products/{supplier_name}_products_cache.json`) is cleared (either fully or selectively modified by `CacheManager`), and then fresh products are scraped for that supplier:
    *   The `last_processed_index` from an old `_processing_state.json` might become invalid (e.g., pointing beyond the bounds of the new, smaller list of products).
    *   `passive_extraction_workflow_latest.py` contains logic to detect this (e.g., if `self.last_processed_index >= len(current_product_list)`). If stale, it usually resets the index to 0 for the new list and may trigger a fresh data fetch for that supplier.
*   The system prioritizes the `linking_map.json` to avoid full re-processing of linked items. The `_processing_state.json` then helps resume iteration over the remaining (unlinked) items for the current batch.

This combination provides both broad (don't re-analyze linked products) and specific (continue from where you left off in the current list) resume capabilities. 