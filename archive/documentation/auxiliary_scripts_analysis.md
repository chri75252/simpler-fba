# 🛠️ AUXILIARY SCRIPTS - PURPOSE & COVERAGE ANALYSIS

## 📋 EXISTING SCRIPT ANALYSIS

### **1. health-check.sh**
**Purpose**: System health verification and dependency validation
**Coverage**: 
- ✅ Python environment validation
- ✅ Core package imports (openai, aiohttp, bs4, pandas, playwright)
- ✅ Chrome debug port connectivity (localhost:9222)
- ✅ Directory structure verification
- ✅ Configuration file existence

**Strengths**: Comprehensive basic health check
**Gaps**: No cache file validation, missing AI API connectivity test

### **2. setup-dev.sh**
**Purpose**: Development environment initialization
**Coverage**:
- ✅ Testing framework installation (pytest, pytest-asyncio, pytest-mock)
- ✅ Code quality tools (black, flake8, isort)
- ✅ Enhanced scraping libraries (scrapy, requests-html, aiofiles)
- ✅ Data analysis tools (matplotlib, seaborn, plotly)
- ✅ Excel export capabilities (openpyxl, xlswriter)

**Strengths**: Comprehensive dev environment setup
**Gaps**: No production dependency separation, missing AI model validation

### **3. setup-browser.sh**
**Purpose**: Browser environment configuration for scraping
**Coverage**:
- Browser automation setup
- Chrome/Chromium configuration
- Extension management (Keepa, SellerAmp)

**Strengths**: Specialized browser setup
**Gaps**: Limited to browser configuration only

### **4. install-fba-tool.sh**
**Purpose**: Main tool installation and setup
**Coverage**:
- Core application installation
- Production environment setup
- System configuration

**Strengths**: Production-ready installation
**Gaps**: Missing post-installation validation

## 🔍 MISSING SCRIPT REQUIREMENTS

### **1. Database/Cache Validation Script**
```bash
#!/bin/bash
# validate-cache.sh - Cache integrity and performance validation

echo "🗃️ FBA Cache Validation"
echo "======================"

# Check cache file integrity
echo "Validating cache files..."
python -c "
import json, os
from pathlib import Path

cache_files = [
    'OUTPUTS/cached_products/clearance-king_co_uk_products_cache.json',
    'OUTPUTS/FBA_ANALYSIS/Linking map/linking_map.json',
    'OUTPUTS/FBA_ANALYSIS/ai_category_cache/clearance-king_co_uk_ai_category_cache.json'
]

for cache_file in cache_files:
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f'✅ {os.path.basename(cache_file)}: {len(data)} entries')
        except Exception as e:
            print(f'❌ {os.path.basename(cache_file)}: {e}')
    else:
        print(f'⚠️ {os.path.basename(cache_file)}: Not found')
"

# Check cache performance
echo "Testing cache performance..."
python -c "
import time, json
cache_file = 'OUTPUTS/cached_products/clearance-king_co_uk_products_cache.json'
if os.path.exists(cache_file):
    start = time.time()
    with open(cache_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    load_time = time.time() - start
    print(f'Cache load time: {load_time:.3f}s')
    if load_time < 1.0:
        print('✅ Cache performance: Good')
    else:
        print('⚠️ Cache performance: Slow')
"
echo "Cache validation complete!"
```

### **2. API Connectivity Test Script**
```bash
#!/bin/bash
# test-apis.sh - External API connectivity validation

echo "🌐 API Connectivity Test"
echo "======================="

# Test OpenAI API
echo "Testing OpenAI API..."
python -c "
import os
from openai import OpenAI

try:
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    response = client.chat.completions.create(
        model='gpt-4o-mini-2024-07-18',
        messages=[{'role': 'user', 'content': 'test'}],
        max_tokens=5
    )
    print('✅ OpenAI API: Connected')
except Exception as e:
    print(f'❌ OpenAI API: {e}')
"

# Test Amazon connectivity  
echo "Testing Amazon access..."
curl -s --head "https://www.amazon.co.uk" | head -n 1 | grep -q "200 OK" && echo "✅ Amazon: Accessible" || echo "❌ Amazon: Not accessible"

# Test supplier connectivity
echo "Testing supplier access..."
curl -s --head "https://www.clearance-king.co.uk" | head -n 1 | grep -q "200 OK" && echo "✅ Clearance King: Accessible" || echo "❌ Clearance King: Not accessible"

echo "API connectivity test complete!"
```

### **3. Performance Monitoring Script**
```bash
#!/bin/bash
# monitor-performance.sh - Real-time performance monitoring

echo "📊 FBA Performance Monitor"
echo "========================="

# System resource monitoring
echo "System Resources:"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory: $(free | grep Mem | awk '{printf("%.1f%%", $3/$2 * 100.0)}')"
echo "Disk: $(df -h . | awk 'NR==2{print $5}')"

# Process monitoring
echo -e "\nFBA Process Status:"
pgrep -f "passive_extraction_workflow" > /dev/null && echo "✅ Main workflow: Running" || echo "❌ Main workflow: Stopped"
pgrep -f "chrome.*debug-port" > /dev/null && echo "✅ Chrome debug: Running" || echo "❌ Chrome debug: Stopped"

# File monitoring
echo -e "\nFile Activity:"
echo "Cache size: $(du -sh OUTPUTS/cached_products/ 2>/dev/null | cut -f1 || echo 'N/A')"
echo "Linking map: $(du -sh OUTPUTS/FBA_ANALYSIS/Linking\ map/ 2>/dev/null | cut -f1 || echo 'N/A')"
echo "Last modified: $(stat -c %y OUTPUTS/cached_products/clearance-king_co_uk_products_cache.json 2>/dev/null | cut -d' ' -f1-2 || echo 'N/A')"

echo -e "\nMonitoring complete!"
```

### **4. Log Analysis Script**
```bash
#!/bin/bash
# analyze-logs.sh - Log analysis and error detection

echo "📜 FBA Log Analysis"
echo "=================="

# Find recent log files
LOG_FILES=$(find . -name "*.log" -mtime -1 | head -5)

if [ -z "$LOG_FILES" ]; then
    echo "No recent log files found"
    exit 1
fi

echo "Analyzing recent logs..."
for log_file in $LOG_FILES; do
    echo -e "\n📁 $(basename $log_file):"
    
    # Error count
    error_count=$(grep -i "error" "$log_file" | wc -l)
    echo "  Errors: $error_count"
    
    # Warning count  
    warning_count=$(grep -i "warning" "$log_file" | wc -l)
    echo "  Warnings: $warning_count"
    
    # Success indicators
    success_count=$(grep -i "success\|completed\|✅" "$log_file" | wc -l)
    echo "  Success: $success_count"
    
    # Recent errors (last 10)
    echo "  Recent errors:"
    grep -i "error" "$log_file" | tail -3 | sed 's/^/    /'
done

echo -e "\nLog analysis complete!"
```

### **5. Backup Management Script**
```bash
#!/bin/bash
# manage-backups.sh - Backup creation and management

echo "💾 FBA Backup Management"
echo "======================="

BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Creating backup in $BACKUP_DIR..."

# Backup critical files
cp -r OUTPUTS/cached_products/ "$BACKUP_DIR/" 2>/dev/null && echo "✅ Product cache backed up"
cp -r OUTPUTS/FBA_ANALYSIS/Linking\ map/ "$BACKUP_DIR/" 2>/dev/null && echo "✅ Linking map backed up"
cp -r config/ "$BACKUP_DIR/" 2>/dev/null && echo "✅ Configuration backed up"

# Backup key scripts
mkdir -p "$BACKUP_DIR/scripts"
cp tools/passive_extraction_workflow_latest.py "$BACKUP_DIR/scripts/" 2>/dev/null && echo "✅ Main workflow backed up"
cp tools/amazon_playwright_extractor.py "$BACKUP_DIR/scripts/" 2>/dev/null && echo "✅ Extractor backed up"

# Create manifest
find "$BACKUP_DIR" -type f -exec sha256sum {} \; > "$BACKUP_DIR/MANIFEST.sha256"
echo "✅ Backup manifest created"

# Compress backup
tar -czf "${BACKUP_DIR}.tar.gz" "$BACKUP_DIR" && rm -rf "$BACKUP_DIR"
echo "✅ Backup compressed: ${BACKUP_DIR}.tar.gz"

# Cleanup old backups (keep last 10)
ls -t backup_*.tar.gz | tail -n +11 | xargs rm -f 2>/dev/null
echo "✅ Old backups cleaned up"

echo "Backup management complete!"
```

## 📊 SCRIPT COVERAGE MATRIX

| Function | Existing | Missing | Priority |
|----------|----------|---------|----------|
| Health Check | ✅ health-check.sh | Cache validation | HIGH |
| Dev Setup | ✅ setup-dev.sh | API validation | MEDIUM |
| Browser Setup | ✅ setup-browser.sh | - | - |
| Installation | ✅ install-fba-tool.sh | Post-install validation | MEDIUM |
| Cache Management | ❌ | validate-cache.sh | HIGH |
| API Testing | ❌ | test-apis.sh | HIGH |
| Performance Monitor | ❌ | monitor-performance.sh | MEDIUM |
| Log Analysis | ❌ | analyze-logs.sh | MEDIUM |
| Backup Management | ❌ | manage-backups.sh | LOW |
| Error Recovery | ❌ | recover-from-errors.sh | LOW |

## ✅ RECOMMENDED IMPLEMENTATION ORDER

### **Immediate (Week 1):**
1. **validate-cache.sh** - Critical for data integrity
2. **test-apis.sh** - Essential for connectivity validation

### **Short-term (Week 2):**
3. **monitor-performance.sh** - Real-time system monitoring
4. **analyze-logs.sh** - Error detection and debugging

### **Medium-term (Month 2):**
5. **manage-backups.sh** - Automated backup management
6. **recover-from-errors.sh** - Error recovery automation

This analysis provides **complete coverage** of auxiliary script requirements with **prioritized implementation** for maximum system reliability.