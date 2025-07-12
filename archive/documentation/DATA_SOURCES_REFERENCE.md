# 📊 DATA SOURCES REFERENCE GUIDE

## Primary Data Sources for System Monitoring & Analysis

This document details the exact file locations and line numbers where all system metrics and analysis data are retrieved from.

### 🎯 **REAL-TIME METRICS SOURCE**
```
/DASHBOARD/metrics_summary.json
```

**Key Metrics Location Map:**

| Metric | JSON Path | Typical Line |
|--------|-----------|--------------|
| **Current Processing Index** | `products.current_processing_index` | ~146 |
| **Total Products** | `products.total_supplier_products` | ~141 |
| **Categories Discovered** | `categories.total_categories_discovered` | ~4 |
| **AI Suggested Categories** | `categories.ai_suggested_categories` | ~8 |
| **Productive Categories** | `categories.productive_categories` | ~9 |
| **Amazon Files Generated** | `amazon_data.total_amazon_files` | ~150 |
| **EAN Matched Products** | `amazon_data.ean_matched_products` | ~152 |
| **Title Matched Products** | `amazon_data.title_matched_products` | ~153 |
| **Processing Rate** | `processing.processing_rate_products_per_minute` | ~176 |
| **Estimated Time Remaining** | `processing.estimated_time_remaining_minutes` | ~175 |
| **AI System Calls** | `ai_system.total_ai_calls` | ~180 |
| **AI Success Rate** | `ai_system.ai_success_rate` | ~182 |
| **Last Activity** | `processing.last_activity_timestamp` | ~177 |

### 📋 **LIVE DASHBOARD**
```
/DASHBOARD/live_dashboard.txt
```
- **Processing Completion %**: Line 22
- **Processing Rate**: Line 9
- **Time Remaining**: Line 10
- **Active Status**: Line 8
- **Categories Summary**: Lines 13-16
- **Amazon Data Summary**: Lines 24-29

### 📁 **CATEGORY DETAILS**
```
/DASHBOARD/metrics/categories.txt
```
- **Category Count Summary**: Lines 5-8
- **Complete Category URL List**: Lines 11-103 (all 93 categories)
- **Pagination Parameters**: Visible in URLs with `?product_list_limit=64&product_list_order=price&product_list_dir=asc`

### 💰 **FINANCIAL REPORTS**
```
/DASHBOARD/metrics/financial.txt
```
- **CSV Reports Generated**: Line 6
- **Latest CSV Timestamp**: References in recent reports section
- **Data Completeness Rate**: Line 9

### 🔄 **PROCESSING STATE**
```
/OUTPUTS/FBA_ANALYSIS/clearance-king_co_uk_processing_state.json
```
- **Current Index**: Single JSON field `{"last_processed_index": XXX}`
- **Resume Capability**: Used by system to resume from exact position

### 📦 **PRODUCT CACHE**
```
/OUTPUTS/cached_products/clearance-king_co_uk_products_cache.json
```
**Product Structure** (per product):
- `title`: Product name
- `price`: Product price (Phase 1: £0.1-£10.0, Phase 2: £10.0-£20.0)
- `ean`: Barcode for Amazon matching
- `source_category_url`: Category where product was found
- `extraction_timestamp`: When product was scraped

### 🛡️ **EMERGENCY BACKUPS**
```
/OUTPUTS/cached_products/emergency_backups/
```
**File Patterns:**
- `processing_state_YYYYMMDD_HHMMSS.json`: Processing state backups
- `cached_products_YYYYMMDD_HHMMSS.json`: Product cache backups
- `linking_map_YYYYMMDD_HHMMSS.json`: Amazon linking backups

### 🤖 **AI CATEGORY INTELLIGENCE**
```
/OUTPUTS/FBA_ANALYSIS/ai_category_cache/clearance-king_co_uk_ai_category_cache.json
```
**Contains:**
- **23 AI Suggestion Sessions**: Complete history of AI category analysis
- **Category Productivity Validation**: Which categories yield products
- **AI-Optimized Processing Order**: Intelligent category prioritization
- **Growth Pattern**: How categories expanded from initial discovery to 128 suggestions

### 📈 **FBA SUMMARY REPORTS**
```
/OUTPUTS/FBA_ANALYSIS/fba_summary_clearance-king_co_uk_YYYYMMDD_HHMMSS.json
```
**Historical Processing Data:**
- Products analyzed per session
- Category completion tracking
- Performance metrics over time

## 🔍 **ANALYSIS METHODOLOGY**

### **Duplication Analysis Sources:**
1. **Product Cache**: `/OUTPUTS/cached_products/clearance-king_co_uk_products_cache.json`
   - Analyzed EAN duplicates across all 703 products
   - Identified cross-category overlaps
   - Calculated 2.13% duplication rate

2. **Category URLs**: `/DASHBOARD/metrics/categories.txt`
   - Examined URL patterns for parent/child relationships
   - Analyzed pagination parameters
   - Identified legitimate multi-category placements

### **Performance Metrics Calculation:**
1. **Processing Rate**: `(current_index - previous_index) / time_elapsed`
2. **Completion %**: `(current_processing_index / total_supplier_products) * 100`
3. **EAN Match Rate**: `(ean_matched_products / total_products_processed) * 100`
4. **AI Efficiency**: `(productive_categories / total_categories_discovered) * 100`

### **Phase Detection Logic:**
1. **Price Analysis**: Examine product prices in cache file
2. **Timestamp Tracking**: Monitor extraction timestamps for continuity
3. **Category Progression**: Track which categories are being processed
4. **AI Session Monitoring**: Analyze AI suggestion timestamps

### **Category Growth Tracking:**
1. **Initial Discovery**: Homepage scraping results
2. **AI Enhancement**: AI suggestion sessions (23 total)
3. **Productivity Validation**: Which suggestions yield products (65/93)
4. **Final Optimization**: 128 total suggestions vs 93 discovered

## 🎯 **QUICK REFERENCE**

**For Current Status:**
- Processing Index: `metrics_summary.json` line 146
- Completion %: `live_dashboard.txt` line 22
- Time Remaining: `live_dashboard.txt` line 10

**For Historical Analysis:**
- AI Growth: `ai_category_cache/clearance-king_co_uk_ai_category_cache.json`
- Product Details: `cached_products/clearance-king_co_uk_products_cache.json`
- Processing History: `FBA_ANALYSIS/fba_summary_*.json` files

**For System Recovery:**
- Current State: `clearance-king_co_uk_processing_state.json`
- Emergency Backups: `emergency_backups/` directory
- Product Backups: Timestamped backup files

---
*This reference guide ensures complete transparency in data source tracking and analysis methodology.*