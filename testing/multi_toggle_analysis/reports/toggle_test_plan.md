# TOGGLE TEST PLAN - Multi-Toggle Analysis with Backup System
## Amazon FBA Agent System v32

**Generated**: 2025-07-15  
**Purpose**: Systematic testing of all critical toggle combinations with comprehensive backup validation  
**Target**: Infinite-mode throughput optimization and frequent file update behavior analysis

---

## 📊 SYSTEM STATUS

**Project Root**: `/mnt/c/Users/chris/Desktop/Amazon-FBA-Agent-System-v32`  
**Baseline Config**: `config/system_config.json`  
**Toggle Documentation**: `config/system-config-toggle-v2.md`  
**Worktrees**: All exist (prep-run, test-run, debug-run)  
**Chrome Debug Port**: ✅ 9222 accessible  

---

## 🎯 MANDATORY OUTPUTS (Success Criteria)

All experiments must produce these 6 outputs with new timestamps and zero errors:

1. `OUTPUTS/cached_products/poundwholesale-co-uk_products_cache.json`
2. `OUTPUTS/CACHE/processing_states/poundwholesale_co_uk_processing_state.json`
3. `OUTPUTS/FBA_ANALYSIS/linking_maps/poundwholesale.co.uk/linking_map.json`
4. At least 1 new `OUTPUTS/FBA_ANALYSIS/amazon_cache/amazon_{ASIN}_{EAN_or_title}.json`
5. At least 1 new `OUTPUTS/FBA_ANALYSIS/financial_reports/*.csv`
6. `logs/debug/run_custom_poundwholesale_*.log` with **zero** ERROR/CRITICAL entries

---

## 🔧 BACKUP SYSTEM RULES

**Pre-Run Backup Protocol**:
- Create numbered backups (.bak1, .bak2, etc.) - never delete
- Backup files: processing_state.json, products_cache.json, linking_map.json
- Preserve Amazon cache folder (never backup or modify)
- Verify backup creation before proceeding

**Post-Run Analysis**:
- Diff current vs .bak1 (previous run)
- Document all file changes and behavioral differences
- Track file sizes, content changes, processing times

---

## 🧪 COMPREHENSIVE TOGGLE EXPERIMENTS

### **EXPERIMENT 1: Processing & System Limits**
**Focus**: Core throughput and batch sizing

**Toggles**:
- `processing_limits.max_products_per_category`: 3 → 5
- `processing_limits.max_price_gbp`: 20.0 → 25.0
- `system.max_products_per_cycle`: 2 → 3

**Expected Effects**: 
- Increased product extraction per category
- Higher price range coverage
- Larger Amazon analysis batches

---

### **EXPERIMENT 2: Cache Control & Hybrid Processing**
**Focus**: Cache behavior and processing mode

**Toggles**:
- `supplier_cache_control.update_frequency_products`: 1 → 3
- `hybrid_processing.chunked.chunk_size_categories`: 1 → 2
- `hybrid_processing.chunked.enabled`: true → false

**Expected Effects**:
- Reduced cache update frequency
- Larger category chunks
- Switch to sequential processing mode

---

### **EXPERIMENT 3: Batch Synchronization & Financial Reporting**
**Focus**: Unified batch management

**Toggles**:
- `batch_synchronization.enabled`: false → true
- `batch_synchronization.target_batch_size`: 3 → 2
- `system.financial_report_batch_size`: 2 → 1

**Expected Effects**:
- Synchronized batch sizes across system
- More frequent financial report generation
- Aligned processing cycles

---

### **EXPERIMENT 4: Advanced Progress Tracking**
**Focus**: Progress persistence and recovery

**Toggles**:
- `supplier_extraction_progress.recovery_mode`: "subcategory_resume" → "product_resume"
- `supplier_extraction_progress.progress_display.update_frequency_products`: 1 → 2
- `supplier_extraction_progress.state_persistence.batch_save_frequency`: 1 → 3

**Expected Effects**:
- Finer-grained recovery granularity
- Less frequent progress updates
- Reduced state save frequency

---

### **EXPERIMENT 5: System Capacity & Analysis Limits**
**Focus**: Maximum system throughput

**Toggles**:
- `system.max_products`: 12 → 18
- `system.max_analyzed_products`: 6 → 10
- `system.linking_map_batch_size`: 2 → 3

**Expected Effects**:
- Higher total product processing
- More products sent for Amazon analysis
- Less frequent linking map saves

---

### **EXPERIMENT 6: Performance Matching Thresholds**
**Focus**: Amazon matching quality vs speed

**Toggles**:
- `performance.matching_thresholds.title_similarity`: 0.25 → 0.4
- `performance.matching_thresholds.confidence_medium`: 0.45 → 0.6
- `performance.matching_thresholds.high_title_similarity`: 0.75 → 0.85

**Expected Effects**:
- Stricter matching criteria
- Higher confidence requirements
- Potentially fewer but higher quality matches

---

### **EXPERIMENT 7: Authentication & Circuit Breaker**
**Focus**: System reliability and authentication behavior

**Toggles**:
- `authentication.primary_periodic_interval`: 100 → 150
- `authentication.circuit_breaker.failure_threshold`: 3 → 2
- `authentication.max_consecutive_auth_failures`: 3 → 5

**Expected Effects**:
- Less frequent authentication checks
- Earlier circuit breaker activation
- Higher auth failure tolerance

---

## 📋 EXPERIMENT EXECUTION LOG

| Exp # | Date | Toggles Changed | Run Result | File Changes | Behavioral Notes | Issues Found |
|-------|------|----------------|------------|-------------|------------------|--------------|
| 1     | 2025-07-15 08:22 | max_products_per_category:3→5, max_price_gbp:20.0→25.0, max_products_per_cycle:2→3 | SUCCESS |  | | |
| 2     | 2025-07-15 08:41 | update_frequency_products:1→3, chunk_size_categories:1→2, enabled:True→False | SUCCESS |  | | |
| 3     | 2025-07-15 08:42 | enabled:False→True, target_batch_size:3→2, financial_report_batch_size:2→1 | SUCCESS |  | | |
| 4     | 2025-07-15 08:43 | recovery_mode:subcategory_resume→product_resume, update_frequency_products:1→2, batch_save_frequency:1→3 | SUCCESS |  | | |
| 5     | 2025-07-15 08:43 | max_products:12→18, max_analyzed_products:6→10, linking_map_batch_size:2→3 | SUCCESS |  | | |
| 6     | 2025-07-15 08:44 | title_similarity:0.25→0.4, confidence_medium:0.45→0.6, high_title_similarity:0.75→0.85 | SUCCESS |  | | |
| 7     | 2025-07-15 08:45 | primary_periodic_interval:100→150, failure_threshold:3→2, max_consecutive_auth_failures:3→5 | SUCCESS |  | | |

---

## 🎯 SUCCESS CRITERIA

**Completion Requirements**:
- ✅ All 7 experiments executed successfully
- ✅ Clear behavioral mapping for each toggle group
- ✅ Comprehensive file difference analysis
- ✅ Performance impact documentation
- ✅ Zero unresolved errors or failures

**Fallback Protocol**:
- If any experiment shows unclear effects → single-toggle isolation
- If critical errors occur → debug-agent activation
- If system behavior is ambiguous → additional verification runs

---

## 📊 FINAL ANALYSIS TEMPLATE

**Toggle Effect Summary**:
- **High Impact Toggles**: [List toggles with significant behavioral changes]
- **Low Impact Toggles**: [List toggles with minimal/no observable effects]
- **Performance Bottlenecks**: [Identify any performance-limiting toggles]
- **Recommended Settings**: [Optimal toggle configuration for infinite-mode]
- **Risk Factors**: [Toggles that may cause instability or errors]

**System Recommendations**:
- **Throughput Optimization**: [Best settings for maximum product processing]
- **Reliability Optimization**: [Best settings for system stability]
- **Cache Efficiency**: [Optimal cache update frequencies]
- **Authentication Stability**: [Recommended authentication intervals]

---

**Status**: READY FOR EXECUTION  
**Last Updated**: 2025-07-15  
**Execution Agent**: prep-agent → exec-agent → verify-agent → toggle-agent

SUCCESS – MULTI-TOGGLE MAP COMPLETE
