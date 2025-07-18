# Toggle Experiment Plan - Data Consistency Hotfix & Definitive Report

## 📋 EXPERIMENT OVERVIEW

**Project**: Amazon-FBA-Agent-System-v32  
**Main workflow**: tools/passive_extraction_workflow_latest.py  
**Current config**: config/system_config.json  
**Toggle reference**: config/system-config-toggle-v2.md  
**Status**: ✅ Data consistency hotfix implemented

## 🔧 DATA CONSISTENCY HOTFIX COMPLETED

### ✅ **Fix 1: EAN Search → Title Match Logic**
- **Location**: `passive_extraction_workflow_latest.py` lines 2721-2725
- **Implementation**: Modified `_get_amazon_data` method to prevent title search when EAN search succeeds
- **Impact**: Prevents weak title matches from overriding valid EAN search results

### ✅ **Fix 2: Amazon Cache Reuse Logic**  
- **Location**: `passive_extraction_workflow_latest.py` lines 2639-2702
- **Implementation**: Enhanced `_check_amazon_cache_by_asin` with intelligent ASIN/EAN matching
- **Impact**: Reduces redundant Amazon scraping through smart cache reuse

### ✅ **Fix 3: Supplier Cache Deduplication**
- **Location**: `passive_extraction_workflow_latest.py` lines 2203-2239
- **Implementation**: Enhanced `_save_products_to_cache` with EAN-based deduplication
- **Impact**: Prevents duplicate products in supplier cache

## 📊 SEQUENTIAL TOGGLE EXPERIMENTS

### **Experiment 1: Processing Limits Toggle Group**
**Target Toggles**: `processing_limits.*`
**Configuration Changes**:
```json
{
  "processing_limits": {
    "max_products_per_category": 5 → 10,
    "min_price_gbp": 0.1 → 1.0,
    "max_price_gbp": 25.0 → 20.0
  }
}
```
**Expected Behavior**: 
- More products per category (10 vs 5)
- Higher price floor (£1.00 vs £0.10)
- Lower price ceiling (£20.00 vs £25.00)

**Verification Criteria**:
- Product count per category increases
- Price filtering applied correctly
- No products below £1.00 or above £20.00

---

### **Experiment 2: System Controls Toggle Group**
**Target Toggles**: `system.*`
**Configuration Changes**:
```json
{
  "system": {
    "max_products": 50 → 30,
    "max_analyzed_products": 50 → 25,
    "max_products_per_cycle": 5 → 3,
    "supplier_extraction_batch_size": 3 → 2
  }
}
```
**Expected Behavior**:
- Total product limit reduced (30 vs 50)
- Analysis limit reduced (25 vs 30)
- Smaller processing cycles (3 vs 5)
- Smaller category batches (2 vs 3)

**Verification Criteria**:
- Total products extracted ≤ 30
- Products analyzed ≤ 25
- Batch processing in groups of 2 categories
- Amazon analysis in cycles of 3 products

---

### **Experiment 3: Supplier Cache Control Toggle Group**
**Target Toggles**: `supplier_cache_control.*`
**Configuration Changes**:
```json
{
  "supplier_cache_control": {
    "enabled": true → true,
    "update_frequency_products": 3 → 1,
    "force_update_on_interruption": true → true,
    "validation": {
      "verify_cache_integrity": true → false,
      "backup_before_update": false → true
    }
  }
}
```
**Expected Behavior**:
- Cache saves every 1 product (vs every 3)
- Cache integrity verification disabled
- Backup creation enabled

**Verification Criteria**:
- Cache file timestamps update every product
- No cache validation overhead
- Backup files created during updates

---

### **Experiment 4: Hybrid Processing Toggle Group**
**Target Toggles**: `hybrid_processing.*`
**Configuration Changes**:
```json
{
  "hybrid_processing": {
    "enabled": true → true,
    "processing_modes": {
      "chunked": {
        "enabled": true → false,
        "chunk_size_categories": 1 → 1
      },
      "sequential": {
        "enabled": false → true
      }
    }
  }
}
```
**Expected Behavior**:
- Switch from chunked to sequential processing
- Complete all supplier extraction before Amazon analysis
- No interleaved processing

**Verification Criteria**:
- All categories processed first
- Amazon analysis begins after all supplier scraping
- Processing state reflects phase separation

---

### **Experiment 5: Batch Synchronization Toggle Group**
**Target Toggles**: `batch_synchronization.*`
**Configuration Changes**:
```json
{
  "batch_synchronization": {
    "enabled": false → true,
    "synchronize_all_batch_sizes": false → true,
    "target_batch_size": 2 → 4
  }
}
```
**Expected Behavior**:
- All batch sizes synchronized to 4
- Predictable batch operations
- Aligned processing intervals

**Verification Criteria**:
- All batch operations occur at multiples of 4
- Synchronized saves and reports
- Consistent memory usage patterns

## 📋 MANDATORY OUTPUT VERIFICATION

For each experiment, verify these files exist with correct timestamps:

### **Core Output Files**:
- `OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json`
- `OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json`
- `OUTPUTS/FBA_ANALYSIS/linking_maps/poundwholesale.co.uk/linking_map.json`
- `OUTPUTS/FBA_ANALYSIS/amazon_cache/amazon_{ASIN}_{EAN_or_title}.json` (≥1 new)
- `OUTPUTS/FBA_ANALYSIS/financial_reports/*.csv`
- `logs/debug/run_custom_poundwholesale_<timestamp>.log`

### **Verification Protocol**:
1. **Timestamp Check**: Files must be created/modified during experiment run
2. **Content Verification**: Files must contain actual business data
3. **Size Validation**: Files must be non-empty and contain realistic data
4. **Supplier Validation**: Files must reference poundwholesale.co.uk

## 🚨 BACKUP POLICY

### **State File Management**:
- **Experiments 1-2**: Keep existing state files to test resume functionality
- **Experiments 3-5**: Backup state files as `.bakNN` before running
- **Amazon Cache**: Never delete, compare by timestamp
- **Supplier Cache**: Backup before deduplication testing

### **Backup Procedure**:
```bash
# Create backup directory
mkdir -p OUTPUTS/BACKUP/experiment_N_YYYYMMDD

# Backup state files
cp OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json OUTPUTS/BACKUP/experiment_N_YYYYMMDD/
cp OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json OUTPUTS/BACKUP/experiment_N_YYYYMMDD/
```

## 📊 RESULTS TRACKING

### **Experiment Results Template**:
```
| Experiment | Toggle Group | Keys Changed | Expected | Observed | Pass/Fail | Notes |
|------------|--------------|--------------|----------|----------|-----------|--------|
| 1          | processing_limits | max_products_per_category: 5→10 | 10 per cat | [ACTUAL] | [P/F] | [NOTES] |
| 1          | processing_limits | min_price_gbp: 0.1→1.0 | No products <£1 | [ACTUAL] | [P/F] | [NOTES] |
| 1          | processing_limits | max_price_gbp: 25→20 | No products >£20 | [ACTUAL] | [P/F] | [NOTES] |
```

### **Success Criteria**:
- **Configuration Loading**: All config changes reflected in logs
- **Behavioral Changes**: Observable differences in system behavior
- **Data Consistency**: No regressions in matching or caching
- **Output Validation**: All mandatory files created with correct content

## 🎯 FINAL DELIVERABLES

1. **✅ Data Consistency Hotfix**: All three fixes implemented and validated
2. **📊 Experiment Results**: Complete toggle effect report with evidence
3. **📋 Toggle Definitions**: Definitive toggle description with proof references
4. **✅ Success Validation**: All success criteria met with verification

## 🚀 EXECUTION SEQUENCE

1. **✅ COMPLETED**: Data consistency hotfix implementation
2. **🔄 IN PROGRESS**: Sequential toggle experiments execution
3. **📋 PENDING**: Definitive toggle report generation
4. **✅ PENDING**: Final success criteria validation

---

**Generated**: 2025-07-15  
**Status**: Ready for Sequential Execution  
**Next Phase**: Begin Experiment 1 - Processing Limits Toggle Group