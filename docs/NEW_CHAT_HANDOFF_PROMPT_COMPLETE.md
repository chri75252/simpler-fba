# Amazon FBA Agent System - Complete Testing Protocol

**Version:** 3.2 (Multi-Cycle AI Category Progression - READY FOR TESTING)
**Date:** 2025-06-03
**Purpose:** Complete instructions for continuing work in new chat sessions

## A. System Overview

### Full Workflow Objective
The Amazon FBA Agent System automates the discovery of profitable products for Amazon FBA by:
1. Using AI to suggest supplier categories to scrape
2. Extracting product data from supplier websites
3. Matching products to Amazon listings using EAN/UPC codes
4. Calculating profitability using FBA fees and Keepa data
5. Generating comprehensive financial reports
6. Automatically progressing to new categories in continuous loops

### Current System Status
- **Location**: `C:\Users\chris\Amazon-FBA-Agent-System\Amazon-FBA-Agent-System-v3\`
- **Status**: Ready for multi-cycle AI testing and verification
- **Capabilities**: Multi-cycle AI category progression, infinite workflow operation, comprehensive financial analysis
- **Limitations**: Currently supports only Clearance King UK supplier

### System Capabilities Ready for Testing
- **✅ Multi-Cycle AI Category Progression**: System should trigger new AI category suggestions after processing batches
- **✅ AI Memory & Learning**: Each cycle should build on previous suggestions and avoid repeating categories
- **✅ Progressive Strategy Evolution**: AI should adapt strategy based on previous results and session context
- **✅ Category Evolution**: Categories should evolve from broad exploration to focused targeting
- **✅ Infinite Mode Operation**: Should work with `--max-products 0` for continuous operation
- **✅ State Persistence**: Resume functionality should maintain workflow state across interruptions
- **✅ Comprehensive File Generation**: All output files should be created correctly with proper timestamps

## B. Testing Protocol (3 Phases)

### Phase 1: Multi-Cycle AI Testing (1 run + 2 automatic loops)

#### Step 1: Pre-Test Setup
```bash
# Navigate to system directory
cd C:\Users\chris\Amazon-FBA-Agent-System\Amazon-FBA-Agent-System-v3\ 

# Clear AI cache first (CRITICAL)
del "OUTPUTS\FBA_ANALYSIS\ai_category_cache\*.json"
```

#### Step 2: Configuration Parameters
Edit `config/system_config.json` and set these EXACT values:
```json
{
  "system": {
    "clear_cache": false,
    "selective_cache_clear": false,
    "force_ai_scraping": true,
    "max_products_per_category": 5,
    "max_analyzed_products": 2
  },
  "integrations": {
    "openai": {
      "enabled": true,
      "api_key": "sk-02XZ3ucKVViULVaTp4_Ad6byZCT6Fofr-BwRsD5mTcT3BlbkFJ7_HTmTRScAn0m-ITc_CX5a2beXTOcbK1-Qmm0s6nwA",
      "model": "gpt-4o-mini-search-preview-2025-03-11"
    }
  }
}
```

#### Step 3: Execute Test
```bash
# Run the test (let it complete 1 initial run + 2 additional loops automatically)
python passive_extraction_workflow_latest.py --max-products 15
```

#### Step 4: Verification (Check Files, NOT Logs)
**Expected Output Files:**
- **3 FBA Summary Files**: `OUTPUTS/FBA_ANALYSIS/fba_summary_clearance-king_co_uk_YYYYMMDD_HHMMSS.json`
- **3 CSV Financial Reports**: `OUTPUTS/FBA_ANALYSIS/fba_financial_report_YYYYMMDD_HHMMSS.csv`
- **3 AI Cache Entries**: Check `OUTPUTS/FBA_ANALYSIS/ai_category_cache/clearance-king_co_uk_ai_category_cache.json` for 3 separate AI calls with different timestamps

**Verification Commands:**
```bash
# Count FBA summary files
dir "OUTPUTS\FBA_ANALYSIS\fba_summary_*.json" /b | find /c /v ""

# Count CSV financial reports
dir "OUTPUTS\FBA_ANALYSIS\fba_financial_report_*.csv" /b | find /c /v ""

# Check AI cache entries
type "OUTPUTS\FBA_ANALYSIS\ai_category_cache\clearance-king_co_uk_ai_category_cache.json"
```

**CRITICAL INSTRUCTIONS:**
- **Use Original Scripts Only**: NEVER generate separate test scripts
- **Let Process Loop**: Tool should complete 1 initial run + 2 additional loops automatically
- **No Manual Restarts**: Process should loop on its own without stopping/restarting
- **Verify by Files**: Check actual file generation, paths, and content manually - DO NOT trust logs alone

### Phase 2: Persistence Testing

#### Step 1: Execute Persistence Test
```bash
# Run with smaller product limit
python passive_extraction_workflow_latest.py --max-products 10
```

#### Step 2: Kill Process Mid-Execution
- Monitor the terminal output
- When you see products being processed, manually kill the process (Ctrl+C)

#### Step 3: Restart and Verify Continuation
```bash
# Restart with same command
python passive_extraction_workflow_latest.py --max-products 10
```

**Expected Behavior:**
- System should resume from where it left off
- Should not reprocess already analyzed products
- Should continue with remaining products from the batch
-If applicable, older chached products to be analtzed prior to newly scraped products. 

### Phase 3: Infinite Mode Operation

#### Step 1: Change Configuration Parameters
Edit `config/system_config.json` and change these EXACT values:
```json
{
  "system": {
    "clear_cache": false,
    "selective_cache_clear": false,
    "force_ai_scraping": true,
    "max_products_per_category": 50,
    "max_analyzed_products": 100
  }
}
```

#### Step 2: Execute Infinite Mode
```bash
# Start infinite processing - runs until ALL AI-suggested categories are exhausted
python passive_extraction_workflow_latest.py --max-products 0
```

#### Step 3: Monitoring Schedule
**Expected Performance Metrics:**
- AI Response Time: Should be ~5-7 seconds per cycle
- Success Rate: Should achieve high success rate for AI calls
- File Generation: Should create all expected outputs correctly
- Memory Management: Should handle cache operations without conflicts

## 📚 DOCUMENTATION REFERENCES
- **Main README**: `docs/README.md` (UPDATED with latest test results)
- **Technical Deep Dive**: `docs/SYSTEM_DEEP_DIVE.md`
- **Supplier Configuration**: `docs/SUPPLIER_PARSER_TOGGLE_FEATURE.md`
- **Updated README**: `docs/README_UPDATED.md`

## 🚨 CRITICAL MONITORING POINTS
1. **AI Client Initialization**: Watch for OpenAI connection errors
2. **Multi-Cycle Progression**: Verify AI calls increment in cache
3. **File Generation**: Ensure CSV reports generate every 40-50 products
4. **Memory Usage**: Monitor for memory leaks during infinite runs
5. **Rate Limiting**: System handles automatically but monitor logs


```

## 🎯 IMMEDIATE NEXT STEPS

### 1. Execute Multi-Cycle AI Testing
**Detailed Testing Protocol:**
- **Clear AI Cache First**: Delete `OUTPUTS/FBA_ANALYSIS/ai_category_cache/*.json` before starting
- **Run Tool Once**: Execute `python passive_extraction_workflow_latest.py --max-products 15`
- **Let Process Loop**: Tool should complete 1 initial run + 2 additional loops automatically (NO manual restarts)
- **Verify by Files, NOT Logs**: Check actual file generation, paths, and content manually
- **Expected Output**: 3 FBA summaries + 3 CSV files + 3 AI cache entries
- **Verify Output**: Scraped products but unanalyzed should be analyzed before newly scraped products
- **Test Configuration**: max_products_per_category: 3, max_analyzed_products: 5, force_ai_scraping: true

## 🔍 EXPECTED TEST RESULTS (REFERENCE)
**Expected AI Cycle Progression:**
When testing is completed successfully, you should see:
1. **AI Call #1**: Initial category discovery from homepage analysis
2. **AI Call #2**: Strategy evolution with refined targeting
3. **AI Call #3**: Progressive refinement and focused targeting
4. **AI Call #4+**: Continued progression with intelligent category filtering


**Monitoring Commands:**
```bash
# Check AI cache progression
type "OUTPUTS\FBA_ANALYSIS\ai_category_cache\clearance-king_co_uk_ai_category_cache.json"

# Check recent file generation
dir "OUTPUTS\FBA_ANALYSIS\fba_financial_report_*.csv" /od

# Monitor process status
tasklist | findstr python


### 2. Persistence Testing (After Multi-Cycle Test)
- **Run Once**: `python passive_extraction_workflow_latest.py --max-products 10`
- **Kill Process**: Stop manually mid-execution
- **Restart**: Run same command to verify continuation from where it left off
- **Verify Output**: Scraped products but unanalyzed should be analyzed before newly scraped products

### 3. Test Infinite Mode
- **Change Config**: Set max_products_to_process: 0 for infinite mode
- **Run Command**: `python passive_extraction_workflow_latest.py --max-products 0`
- **Monitor Schedule**: Every 8 minutes for first 24 minutes, then hourly if no errors
- **If Errors Found**: Stop immediately, troubleshoot, and rectify before continuing

## 💡 SYSTEM CAPABILITIES TO BE VERIFIED
- 🧪 Multi-cycle AI category progression (ready for testing)
- 🧪 Infinite workflow operation (ready for testing)
- ✅ Automatic error recovery (implemented)
- ✅ State persistence and resume (implemented)
- ✅ Comprehensive financial analysis (working)
- ✅ Smart product matching (EAN/UPC + title fallback) (working)
- ✅ Rate limiting and API management (working)
- ✅ Cache management and optimization (working)

**🚨 CRITICAL TESTING INSTRUCTION:**
**ALWAYS use original production scripts for testing - NEVER generate separate test scripts.**
**Modify parameters in the actual scripts to achieve shorter running times while verifying the complete workflow sequence and output generation.**
**NEVER "UNCOMMENT OUT" ANY COMMENTED OUT CODE SNIPPET IF NOT INSTRUCTED TO DO SO **
**The Amazon FBA Agent System is ready for multi-cycle AI testing and verification!**


## C. Critical Instructions

### File Verification Locations
- **AI Cache**: `OUTPUTS/FBA_ANALYSIS/ai_category_cache/clearance-king_co_uk_ai_category_cache.json` --> New (additional- no overwriting of existing entry) entry
- **FBA Summaries**: `OUTPUTS/FBA_ANALYSIS/fba_summary_clearance-king_co_uk_YYYYMMDD_HHMMSS.json` --> new file
- **Financial Reports**: `OUTPUTS/FBA_ANALYSIS/fba_financial_report_YYYYMMDD_HHMMSS.csv` --> new file/csv
- **Amazon Cache**: `OUTPUTS/FBA_ANALYSIS/amazon_cache/amazon_*.json` --> new file
- **Processing State**: `OUTPUTS/FBA_ANALYSIS/clearance-king_co_uk_processing_state.json` same file updated

### Parameter Changes Between Phases
**Phase 1 & 2 (Testing):**
- `max_products_per_category: 3`
- `max_analyzed_products: 5`

**Phase 3 (Infinite Mode):**
- `max_products_per_category: 50`
- `max_analyzed_products: 100`
- **IMPORTANT:** The system runs until ALL AI-suggested categories are exhausted, regardless of these parameters. These only control the pace of processing.

### Emergency Recovery
```bash
# If system becomes unresponsive
taskkill /f /im python.exe

# If Chrome issues
taskkill /f /im chrome.exe
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"

# If cache corruption
del "OUTPUTS\FBA_ANALYSIS\ai_category_cache\*.json"
rmdir /s "OUTPUTS\FBA_ANALYSIS\amazon_cache"
```

### Success Criteria
**Phase 1 Success**: 3 FBA summaries + 3 CSV files + 3 AI cache entries generated automatically
**Phase 2 Success**: System resumes from interruption point without reprocessing
**Phase 3 Success**: Continuous operation with regular file generation and AI progression

**CRITICAL: Always use original production scripts, never create test scripts. Always verify by checking actual generated files, never trust logs alone.**
