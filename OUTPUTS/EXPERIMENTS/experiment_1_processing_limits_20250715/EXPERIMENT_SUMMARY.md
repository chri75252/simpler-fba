# Experiment 1: Processing Limits Toggle Group

## 📋 EXPERIMENT CONFIGURATION

**Timestamp**: 2025-07-15 18:18:10 - 18:20:07  
**Duration**: ~2 minutes  
**Log File**: run_custom_poundwholesale_20250715_181810.log  

### Configuration Changes Applied:
```json
{
  "processing_limits": {
    "max_products_per_category": 10,
    "min_price_gbp": 1.0,
    "max_price_gbp": 20.0
  },
  "system": {
    "max_products": 30,
    "max_analyzed_products": 25,
    "max_products_per_category": 10
  }
}
```

## 📊 OBSERVED RESULTS

### **Configuration Loading** ✅ **VERIFIED**
**Evidence**: Log file lines 27-34 show successful configuration loading
**Proof**: Authentication successful, price access confirmed at £1.02

### **Products Extracted**: 12 total products
**Evidence**: processing_states/poundwholesale_co_uk_processing_state.json
**Proof**: `"products_extracted_total": 12` at timestamp 2025-07-15T14:19:53.057947+00:00

### **Price Range Analysis**: ❌ **PRICE FILTERING NOT WORKING**
**Evidence**: cached_products/poundwholesale-co-uk_products_cache.json
**Proof**: Products below £1.00 minimum found:
- £0.63 (Duzzit Amazing Baking Soda Wipes)
- £0.66 (Duzzit Floor Wipes)
- £0.72 (Multiple products)
- £0.79 (Home & Garden Stove Polish)
- £0.84 (Home & Garden Multi-Purpose)
- £0.88 (Rapide Lime Scented)

### **Products per Category**: 10 products from first category
**Evidence**: All 10 products from "multi-purpose-cleaners" category
**Proof**: All products show same source_url in cache file

### **Categories Processed**: 2 categories started
**Evidence**: processing_states shows batch 1 processing
**Proof**: Moved from "multi-purpose-cleaners" to "sponges-scourers-cloths"

## 🔍 CRITICAL FINDINGS

### **❌ TOGGLE FAILURE: Price Filtering**
**Processing_limits.min_price_gbp**: 1.0 → **NOT ENFORCED**
**Evidence**: 7 out of 10 products below £1.00 minimum
**Impact**: Price filtering toggle is not integrated or not working

### **✅ TOGGLE SUCCESS: Products per Category**
**System.max_products_per_category**: 10 → **WORKING**
**Evidence**: Exactly 10 products extracted from first category
**Impact**: Category limit toggle is properly integrated

### **⚠️ TOGGLE UNCLEAR: Processing Limits vs System**
**Duplicate Settings**: Both processing_limits and system have max_products_per_category
**Evidence**: System section value (10) appears to take precedence
**Impact**: Configuration hierarchy unclear

## 🎯 VERIFICATION STATUS

| Toggle | Expected | Observed | Status | Evidence |
|--------|----------|----------|--------|----------|
| max_products_per_category | 10 per category | 10 products from first category | ✅ PASS | processing_state.json |
| min_price_gbp | No products < £1.00 | 7 products < £1.00 | ❌ FAIL | products_cache.json |
| max_price_gbp | No products > £20.00 | Highest £1.32 | ⚠️ UNTESTED | products_cache.json |

## 📁 ARCHIVED FILES

- `cached_products/poundwholesale-co-uk_products_cache.json` (12 products)
- `CACHE/processing_states/poundwholesale_co_uk_processing_state.json` (progress tracking)
- `run_custom_poundwholesale_20250715_181810.log` (full debug log)

---

**Status**: ❌ **INCOMPLETE – CRITICAL ISSUE FOUND**  
**Issue**: Price filtering toggle not working - products below minimum price being scraped  
**Next Action**: Investigate price filtering implementation in workflow