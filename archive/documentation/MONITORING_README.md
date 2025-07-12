# Enhanced FBA Monitoring System with File-Based Aggregation

## Overview

This comprehensive file-based monitoring system detects unusual conditions, errors, and data quality issues by reading ONLY from actual output files (never from logs). It implements advanced alert aggregation, severity escalation, and detailed progress tracking to ensure accurate real-time system status.

## 🎯 Key Features

- **📁 File-Based Analysis**: Reads directly from Amazon cache, CSV reports, AI cache, and state files
- **📊 Alert Aggregation**: Groups multiple instances of same issue with detailed reporting
- **⚡ Severity Escalation**: Auto-escalates WARNING→CRITICAL→URGENT based on instance count
- **📈 Progress Tracking**: Comprehensive progress monitoring from actual file contents
- **🎯 Data Quality Metrics**: Calculates quality scores from real data analysis
- **🔄 Atomic Operations**: Safe flag file operations with backup and recovery

## 🚨 What It Monitors (File-Based Analysis Only)

### Data Sources Analyzed
- **Amazon Cache Files**: `OUTPUTS/FBA_ANALYSIS/amazon_cache/amazon_*.json`
- **AI Category Cache**: `OUTPUTS/FBA_ANALYSIS/ai_category_cache/*_ai_category_cache.json`
- **Financial CSV Reports**: `OUTPUTS/FBA_ANALYSIS/financial_reports/fba_financial_report_*.csv`
- **Processing State**: `OUTPUTS/FBA_ANALYSIS/*_processing_state.json`
- **Supplier Cache**: `OUTPUTS/cached_products/*_products_cache.json`
- **FBA Summaries**: `OUTPUTS/FBA_ANALYSIS/fba_summary_*.json`
- **Linking Map**: `OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json`

### System Health (From Process Analysis)
- **Process Status**: Detects when FBA system processes stop running
- **Disk Space**: Warns when storage is running low
- **Memory Usage**: Monitors process resource consumption

### Data Quality Issues (From File Content Analysis)
- **Missing Keepa Data**: Products without `keepa.product_details_tab_data`
- **Keepa Timeouts**: Status contains "timeout" in Amazon cache files
- **Incomplete Fee Data**: Missing FBA/referral fees in Keepa data
- **CSV Data Quality**: Missing columns, empty rows in financial reports
- **EAN/ASIN Mismatches**: Data consistency across files

### AI System Issues (From AI Cache Analysis)
- **Redundant AI Suggestions**: Duplicate URLs in `suggested_urls` arrays
- **Excessive AI Suggestions**: >20 suggestions indicating infinite loops
- **Unproductive Categories**: AI suggestions yielding zero products
- **Processing Stuck**: No progress in `last_processed_index` for >30 minutes

### Progress Tracking (From Actual File Counts)
- **Products Progress**: Supplier cache vs Amazon cache vs processing state
- **Financial Analysis**: CSV generation and data completeness rates
- **AI Category Progress**: Suggestion counts, validation results, scraping success
- **Data Quality Metrics**: Keepa success rate, linking efficiency, overall quality score

## 🛠️ Installation

1. **Install Required Dependencies**:
   ```bash
   pip install psutil plyer
   ```

2. **Files Included**:
   - `monitoring_system.py` - Main monitoring engine
   - `flag_notifier.py` - Desktop/email notification system
   - `check_flags.py` - Quick flag summary tool
   - `start_monitoring.bat` - Easy startup script

## 🚀 Usage

### Option 1: Easy Start (Recommended)
```bash
# Double-click or run:
start_monitoring.bat
```
This starts both monitoring and notification systems in background windows.

### Option 2: Manual Start
```bash
# Start monitoring system (continuous)
python monitoring_system.py

# Start notification system (separate terminal)
python flag_notifier.py
```

### Option 3: One-Time Checks
```bash
# Run single monitoring check
python monitoring_system.py --check-once

# Check current flags
python check_flags.py

# Show only critical flags
python check_flags.py --critical-only
```

## 📁 Flag System

### Flag Files Location
Flags are created in: `MONITORING_FLAGS/`

### Flag Types Created
- `SYSTEM_STOPPED` - FBA processes have stopped
- `REDUNDANT_AI_SUGGESTIONS` - Duplicate AI category suggestions
- `MISSING_KEEPA_DATA` - Products without Keepa extraction
- `KEEPA_TIMEOUT_SPIKE` - High number of Keepa timeouts
- `CSV_MISSING_COLUMNS` - Financial reports missing data
- `PROCESSING_STUCK` - System stuck on same product
- `LOW_DISK_SPACE` - Storage running low

### Flag Severities
- 🔴 **CRITICAL**: Requires immediate action
- 🟡 **WARNING**: Should be investigated
- 🔵 **INFO**: Informational only

## 🔔 Notifications

### Desktop Notifications
Automatically enabled if `plyer` is installed. Shows popup alerts for new flags.

### Email Notifications
1. **Create email config**:
   ```bash
   python flag_notifier.py --create-email-config
   ```

2. **Edit `email_config.json`**:
   ```json
   {
     "enabled": true,
     "smtp_server": "smtp.gmail.com",
     "smtp_port": 587,
     "from_email": "your-email@gmail.com",
     "to_email": "your-email@gmail.com",
     "username": "your-email@gmail.com",
     "password": "your-app-password"
   }
   ```

3. **Restart notification system**

## 🤖 AI Assistant Integration

### When You Get Alerted
1. **Check flags**: `python check_flags.py`
2. **Message AI**: "Check monitoring flags"
3. **AI will**: Read flag files and investigate issues
4. **AI provides**: Solutions and recommendations

### Example Workflow
```
1. 🔔 Desktop notification: "FBA Alert: KEEPA_TIMEOUT_SPIKE"
2. 💬 You message AI: "Check monitoring flags"
3. 🤖 AI reads flags and responds: "Found Keepa timeout issue. Keepa appears logged out. Recommend checking login status..."
4. ✅ You follow AI recommendations
5. 🧹 Clear flags: python monitoring_system.py --clear-flags
```

## 📊 Monitoring Configuration

### Check Intervals
- **Monitoring System**: Every 5 minutes
- **Notification System**: Every 1 minute
- **Customizable**: Edit `check_interval` in scripts

### Thresholds (Customizable)
- Keepa timeouts: >5 in last 50 files
- Missing Keepa data: >10 in last 50 files
- Processing stuck: >30 minutes on same product
- Low disk space: <5GB warning, <1GB critical

## 🔧 Commands Reference

### Monitoring System
```bash
# Continuous monitoring
python monitoring_system.py

# Single check
python monitoring_system.py --check-once

# Show all flags
python monitoring_system.py --show-flags

# Clear all flags
python monitoring_system.py --clear-flags

# Clear specific flag types
python monitoring_system.py --clear-flags KEEPA_TIMEOUT_SPIKE MISSING_KEEPA_DATA
```

### Flag Checker
```bash
# Show flag summary
python check_flags.py

# Show only critical flags
python check_flags.py --critical-only
```

### Notification System
```bash
# Continuous notifications
python flag_notifier.py

# Single check
python flag_notifier.py --check-once

# Create email config
python flag_notifier.py --create-email-config
```

## 🎯 Best Practices

1. **Start monitoring BEFORE starting FBA system**
2. **Check flags every few hours during long runs**
3. **Always message AI when you see flags**: "Check monitoring flags"
4. **Clear flags after resolving issues**
5. **Monitor disk space during long runs**

## 🚨 Critical Alerts

If you see these flags, **stop FBA processing immediately**:
- `SYSTEM_STOPPED` - Process crashed
- `LOW_DISK_SPACE` - Out of storage
- `PROCESSING_STUCK` - System hung
- `KEEPA_TIMEOUT_SPIKE` - Keepa login failed

## 📝 Logs

- **Monitoring logs**: `monitoring_system.log`
- **Notification logs**: `flag_notifier.log`
- **Flag files**: `MONITORING_FLAGS/*.json`

## 🔄 Integration with FBA System

The monitoring system is designed to work alongside your existing FBA workflow:

1. **Start monitoring first**
2. **Start FBA processing**
3. **Monitor gets alerts automatically**
4. **You get notified of issues**
5. **Message AI for investigation**
6. **Resolve issues and continue**

This ensures you catch problems early and avoid wasted processing time!
