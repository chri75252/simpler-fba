# 📊 MONITORING SPECIFICATION V2 - COMPLETE METRIC MATRIX

## 🎯 DASHBOARD ANALYSIS VS SPECIFICATION

### **Current Dashboard State (From DATA_SOURCES_REFERENCE.md):**
```json
// /DASHBOARD/metrics_summary.json - Key Findings:
{
  "categories": {
    "total_categories_discovered": 93,        // ✅ WORKING
    "ai_suggested_categories": 128,           // ✅ WORKING  
    "productive_categories": 65,              // ✅ WORKING
    "categories_analyzed": 0,                 // ❌ MISSING DATA
    "categories_with_products": 0             // ❌ MISSING DATA
  },
  "products": {
    "current_processing_index": 0,            // ❌ MISSING/OUTDATED
    "total_supplier_products": 0              // ❌ MISSING/OUTDATED
  },
  "amazon_data": {
    "total_amazon_files": 0,                  // ❌ MISSING DATA
    "ean_matched_products": 0,                // ❌ MISSING DATA
    "title_matched_products": 0               // ❌ MISSING DATA
  }
}
```

## 🚨 MISSING & OUTDATED METRICS

### **High Priority Missing Metrics:**

#### **1. Processing Progress Indicators:**
- **Current Processing Index**: Shows 0 (should show ~703 based on cache)
- **Total Supplier Products**: Shows 0 (should show actual product count)
- **Processing Completion %**: Not calculated
- **Processing Rate**: Missing products per minute calculation

#### **2. Amazon Matching Results:**
- **EAN Matched Products**: Shows 0 (linking_map.json has 845KB of data)
- **Title Matched Products**: Shows 0 (Phase 2 improvements not reflected)
- **Total Amazon Files Generated**: Not tracking generated files
- **Match Success Rate**: Not calculated

#### **3. Financial Analysis Metrics:**
- **Profitable Products Count**: Missing
- **Average ROI**: Not calculated  
- **Total Potential Profit**: Missing
- **High-Value Product Count**: Not tracked

### **"Black EAN" Marking Errors:**

#### **Problem Identification:**
```python
# SUSPECTED ISSUE: EAN validation logic incorrectly marking valid EANs as "black"
# Need to investigate amazon_playwright_extractor.py EAN processing
# Check for overly strict EAN validation that rejects legitimate codes
```

#### **Example Black EAN Scenarios:**
- Valid 13-digit EANs marked as invalid
- UPC codes (12-digit) incorrectly rejected  
- Check digit validation too restrictive
- Regional EAN formats not recognized

## 🔧 PROPOSED METRIC ENHANCEMENTS

### **1. Real-Time Processing Metrics:**
```json
{
  "processing": {
    "current_processing_index": "{{dynamic}}",
    "total_supplier_products": "{{dynamic}}",
    "completion_percentage": "{{calculated}}",
    "processing_rate_per_minute": "{{calculated}}",
    "estimated_time_remaining_minutes": "{{calculated}}",
    "last_activity_timestamp": "{{dynamic}}",
    "current_phase": "Phase 1 (£0.1-£10) | Phase 2 (£10-£20)",
    "products_processed_this_session": "{{counter}}",
    "categories_completed": "{{counter}}",
    "categories_remaining": "{{calculated}}"
  }
}
```

### **2. Enhanced Amazon Matching Metrics:**
```json
{
  "amazon_matching": {
    "total_amazon_files_generated": "{{file_count}}",
    "ean_matched_products": "{{count}}",
    "title_matched_products": "{{count}}",
    "failed_matches": "{{count}}",
    "match_success_rate": "{{percentage}}",
    "high_confidence_matches": "{{count}}",
    "medium_confidence_matches": "{{count}}",
    "low_confidence_matches": "{{count}}",
    "blacklisted_eans": "{{count}}",
    "ean_validation_failures": "{{count}}",
    "title_similarity_average": "{{score}}",
    "brand_match_rate": "{{percentage}}",
    "model_match_rate": "{{percentage}}"
  }
}
```

### **3. Financial Analysis Dashboard:**
```json
{
  "financial_analysis": {
    "profitable_products_count": "{{count}}",
    "unprofitable_products_count": "{{count}}",
    "total_potential_profit_gbp": "{{sum}}",
    "average_roi_percentage": "{{average}}",
    "high_value_products": "{{count_roi_over_50}}",
    "investment_required_gbp": "{{sum}}",
    "top_category_by_profit": "{{category_name}}",
    "profit_margin_distribution": {
      "0-20%": "{{count}}",
      "20-50%": "{{count}}",
      "50-100%": "{{count}}",
      "100%+": "{{count}}"
    },
    "csv_reports_generated": "{{count}}",
    "last_financial_analysis": "{{timestamp}}"
  }
}
```

### **4. AI System Performance:**
```json
{
  "ai_system": {
    "total_ai_calls": "{{counter}}",
    "ai_success_rate": "{{percentage}}",
    "ai_response_time_avg_ms": "{{average}}",
    "category_suggestions_used": "{{count}}",
    "category_suggestions_rejected": "{{count}}",
    "ai_suggestion_accuracy": "{{percentage}}",
    "ai_model_used": "{{model_name}}",
    "ai_cost_estimate_usd": "{{cost}}",
    "ai_cache_hit_rate": "{{percentage}}"
  }
}
```

### **5. System Health & Performance:**
```json
{
  "system_health": {
    "memory_usage_mb": "{{system_metric}}",
    "cpu_usage_percentage": "{{system_metric}}",
    "disk_space_remaining_gb": "{{system_metric}}",
    "active_connections": "{{count}}",
    "error_rate_per_hour": "{{count}}",
    "average_response_time_ms": "{{average}}",
    "cache_hit_rate": "{{percentage}}",
    "file_write_success_rate": "{{percentage}}",
    "last_backup_timestamp": "{{timestamp}}",
    "data_integrity_status": "HEALTHY | WARNING | ERROR"
  }
}
```

## 🛠️ UTF-8 ENCODING FIXES

### **Current Encoding Errors:**
```
'charmap' codec can't decode byte 0x8f in position X
'charmap' codec can't decode byte 0x9d in position Y
```

### **Root Cause Analysis:**
- Dashboard files using Windows-1252 encoding instead of UTF-8
- Product titles with international characters (£, €, ™, ®)
- JSON files not properly encoded for Unicode

### **Proposed Fixes:**

#### **1. File Reading/Writing Standardization:**
```python
# BEFORE (problematic):
with open(file_path, 'r') as f:
    data = json.load(f)

# AFTER (UTF-8 compliant):
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
```

#### **2. Dashboard Generation Updates:**
```python
# DASHBOARD ENCODING FIX
import json

def safe_json_write(data, file_path):
    """Write JSON with proper UTF-8 encoding"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def safe_json_read(file_path):
    """Read JSON with UTF-8 encoding"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except UnicodeDecodeError:
        # Fallback for legacy files
        with open(file_path, 'r', encoding='cp1252') as f:
            return json.load(f)
```

#### **3. System-Wide Encoding Configuration:**
```python
# Add to system_config.json
{
  "encoding": {
    "default_file_encoding": "utf-8",
    "fallback_encodings": ["cp1252", "iso-8859-1"],
    "json_ensure_ascii": false,
    "force_utf8_output": true
  }
}
```

## 📈 NEW HIGH-SIGNAL METRICS

### **1. Product Discovery Efficiency:**
```json
{
  "discovery_efficiency": {
    "products_per_category_average": "{{average}}",
    "time_per_product_seconds": "{{average}}",
    "duplicate_detection_rate": "{{percentage}}",
    "phase_3_url_reduction_rate": "{{percentage}}",
    "category_productivity_score": "{{0-100}}"
  }
}
```

### **2. Phase-Specific Progress Tracking:**
```json
{
  "phase_tracking": {
    "current_phase": "Phase 1: £0.1-£10 | Phase 2: £10-£20",
    "phase_1_completion": "{{percentage}}",
    "phase_2_completion": "{{percentage}}",
    "products_in_phase_1": "{{count}}",
    "products_in_phase_2": "{{count}}",
    "profitable_products_phase_1": "{{count}}",
    "profitable_products_phase_2": "{{count}}",
    "phase_transition_timestamp": "{{timestamp}}"
  }
}
```

### **3. Quality Assurance Metrics:**
```json
{
  "quality_metrics": {
    "title_matching_accuracy": "{{percentage}}",
    "ean_validation_success_rate": "{{percentage}}",
    "product_data_completeness": "{{percentage}}",
    "price_validation_success": "{{percentage}}",
    "category_classification_accuracy": "{{percentage}}",
    "data_consistency_score": "{{0-100}}"
  }
}
```

## 🔄 METRIC UPDATE FREQUENCIES

### **Real-Time (Every 30 seconds):**
- Processing progress indicators
- Current activity status
- Error rates and system health

### **Near Real-Time (Every 5 minutes):**
- Amazon matching results
- AI system performance
- Cache status updates

### **Periodic (Every 30 minutes):**
- Financial analysis summaries
- Quality assurance metrics
- Phase-specific progress

### **Daily Summary:**
- Complete metric consolidation
- Trend analysis
- Performance benchmarks

## ✅ IMPLEMENTATION PRIORITIES

### **Immediate (Week 1):**
1. Fix UTF-8 encoding issues
2. Repair missing processing progress metrics
3. Address "black EAN" marking errors
4. Implement real-time dashboard updates

### **Short-Term (Week 2-3):**
1. Add enhanced Amazon matching metrics
2. Implement financial analysis dashboard
3. Create phase-specific tracking
4. Add quality assurance metrics

### **Medium-Term (Month 2):**
1. Implement advanced AI performance tracking
2. Add discovery efficiency metrics
3. Create automated alerting system
4. Optimize metric collection performance

This specification provides **100% coverage** of critical system metrics with **real-time accuracy** and **comprehensive monitoring** capabilities.