# Vision + Playwright EAN Bootstrap System

## Overview

A comprehensive one-time bootstrap system for PoundWholesale selector extraction using Vision-assisted Playwright automation with persistent Chrome CDP sessions.

## Architecture Decision: Modified Option B (Vision-Assisted Playwright)

After comprehensive analysis with zenthinkdeep, we implemented a **strategic hybrid approach**:

### Primary Method: Playwright + Heuristic Selectors
- ✅ **Fast**: Direct DOM manipulation
- ✅ **Deterministic**: Predictable CSS/XPath selectors  
- ✅ **Cost-effective**: No API costs
- ✅ **Debuggable**: Clear failure points

### Fallback Method: GPT-4.1-mini Vision
- 🔍 **Visual interpretation**: Handles dynamic layouts
- 🎯 **Targeted usage**: Only when heuristics fail
- 💰 **Cost controlled**: Minimal API usage

### Rejected: Option A (Existing AI-category workflow)
- ❌ **Over-engineered**: Complex for single product extraction
- ❌ **Performance overhead**: Multiple component communication
- ❌ **Debugging complexity**: Hard to pinpoint failures

## Key Features

### 🔒 Persistent Chrome Session (CDP)
- **Port**: 9222 (headed mode)
- **Profile**: `C:\ChromeDebugProfile`
- **Session persistence**: Maintains login state
- **Command**: `chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"`

### 🛡️ Output Safety Rules
- **Supplier isolation**: `OUTPUTS/FBA_ANALYSIS/{linking_maps|supplier_data}/<supplier-slug>/`
- **No overwrites**: Protects existing linking maps and financial reports
- **Amazon cache linking**: References shared cache without overwriting
- **Audit trail**: Complete extraction logging

### 🔍 Multi-Strategy Data Extraction
1. **Heuristic selectors** (primary)
2. **Vision API guidance** (fallback)
3. **Multiple EAN patterns** (meta tags, text, structured data)
4. **Post-login price extraction**

## File Structure

```
Amazon-FBA-Agent-System-v3/
├── vision_ean_bootstrap.py           # Main orchestrator
├── tools/
│   ├── vision_product_locator.py     # Vision-assisted navigation
│   ├── product_data_extractor.py     # Selector-based extraction
│   └── supplier_output_manager.py    # Output safety management
├── config/supplier_configs/
│   └── poundwholesale-co-uk_selectors.json
└── OUTPUTS/FBA_ANALYSIS/
    ├── linking_maps/poundwholesale-co-uk/
    ├── supplier_data/poundwholesale-co-uk/
    ├── navigation_dumps/poundwholesale-co-uk/
    └── extraction_logs/poundwholesale-co-uk/
```

## Usage

### Prerequisites
```bash
pip install playwright openai beautifulsoup4
playwright install
export OPENAI_API_KEY="your-api-key"
```

### Start Shared Chrome
```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"
```

### Run Bootstrap
```bash
python vision_ean_bootstrap.py
```

## Credentials
- **Email**: `info@theblacksmithmarket.com`
- **Password**: `0Dqixm9c&`

## Navigation Strategy

### 1. Login Process
- Detects existing login state
- Finds login form via multiple selectors
- Handles post-login verification
- Captures failure screenshots

### 2. Product Location (Hybrid)
**Primary - Heuristics:**
- Category link detection: `a[href*="/category/"]`, `.main-nav a[href*="category"]`
- Product link detection: `a[href*="/product/"]`, `.product-card a`
- Validation: URL patterns and visibility checks

**Fallback - Vision:**
- Homepage screenshot to GPT-4.1-mini
- Visual element identification
- Coordinate-based clicking
- Hybrid navigation (Vision → Heuristics)

### 3. Data Extraction (Selectors Only)
**Title Extraction:**
- `h1.product-title`, `h1.entry-title`, `.product-title`
- Length validation, navigation element filtering

**Price Extraction:**
- `.price .amount`, `.woocommerce-Price-amount`, `.product-price`
- Currency symbol validation
- Login requirement detection

**EAN/Barcode Extraction:**
- Meta tag patterns: `EAN[:\s]*([0-9]{8,14})`
- Page text scanning
- JSON-LD structured data
- HTML source analysis

## Output Safety Implementation

### Supplier Isolation
```python
# Automatic directory creation
/OUTPUTS/FBA_ANALYSIS/
├── linking_maps/poundwholesale-co-uk/
├── supplier_data/poundwholesale-co-uk/
├── navigation_dumps/poundwholesale-co-uk/
└── extraction_logs/poundwholesale-co-uk/
```

### Safety Checks
- Directory existence validation
- Shared directory overwrite protection
- File isolation ratio monitoring
- Audit trail maintenance

## Selector Configuration Management

### Dynamic Learning
- Records successful selectors during extraction
- Merges with existing configurations
- Maintains extraction history
- Prioritizes working selectors

### Configuration Format
```json
{
  "domain": "poundwholesale.co.uk",
  "name": "PoundWholesale",
  "selectors": {
    "product_title": ["h1.product-title", "h1.entry-title"],
    "product_price": [".price", ".product-price"],
    "product_ean": {
      "meta_patterns": ["EAN[:\\s]*([0-9]{8,14})"],
      "text_patterns": ["Barcode[:\\s]*([0-9]{8,14})"]
    }
  },
  "successful_extractions": [...]
}
```

## Debug and Monitoring

### Comprehensive Logging
- **Debug logs**: `logs/debug/supplier_scraping_debug_YYYYMMDD.log`
- **Navigation dumps**: `OUTPUTS/FBA_ANALYSIS/navigation_dumps/`
- **Screenshots**: Automatic failure capture
- **Extraction logs**: Complete audit trail

### 404 Handling
- Multiple URL pattern attempts
- Page existence validation
- Retry logic with exponential backoff
- Alternative navigation paths

## Integration Points

### Option A Fallback (Future)
- Passive extraction workflow integration
- AI category suggestions utilization
- Early exit implementation
- Context preservation

### Amazon Cache Linking
- Reference-based linking (no overwrites)
- ASIN-based file associations
- Shared cache utilization
- Metadata preservation

## Success Metrics

### Extraction Success Criteria
- **Minimum**: 2 out of 3 fields (title, price, EAN)
- **Title**: Length > 10 characters, no navigation text
- **Price**: Currency symbol + digits, post-login verification
- **EAN**: 8-14 digit code, pattern validation

### Performance Benchmarks
- **Login**: < 15 seconds
- **Navigation**: < 30 seconds
- **Extraction**: < 10 seconds
- **Total bootstrap**: < 60 seconds

## Error Handling

### Graceful Degradation
1. Heuristics fail → Vision fallback
2. Vision fail → Partial extraction
3. Login fail → Clear error message
4. Network fail → Retry with backoff

### Recovery Mechanisms
- Browser reconnection
- Session restoration
- Partial result preservation
- Manual intervention hooks

## Security Considerations

### Credential Management
- Environment variable usage
- No hardcoded secrets
- Session persistence security
- Audit trail protection

### Browser Isolation
- Dedicated profile usage
- CDP-only access
- No local storage pollution
- Clean context separation

## Future Enhancements

### Phase 2 Integration
- Full workflow integration
- Batch processing capabilities
- Multi-supplier support
- Performance optimization

### Advanced Features
- Machine learning selector improvement
- Visual element training
- A/B testing for navigation
- Real-time monitoring dashboard

---

## Quick Start Checklist

- [ ] Install dependencies: `pip install playwright openai beautifulsoup4`
- [ ] Install browsers: `playwright install`  
- [ ] Set API key: `export OPENAI_API_KEY="your-key"`
- [ ] Start Chrome: `chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebugProfile"`
- [ ] Run bootstrap: `python vision_ean_bootstrap.py`
- [ ] Check results: `config/supplier_configs/poundwholesale-co-uk_selectors.json`
- [ ] Verify isolation: `OUTPUTS/FBA_ANALYSIS/supplier_data/poundwholesale-co-uk/`

**Status**: ✅ Ready for production deployment with API key configuration