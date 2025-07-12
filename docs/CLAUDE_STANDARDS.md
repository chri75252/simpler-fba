<!-- AUTO-GENERATED: DO NOT EDIT DIRECTLY -->
<!-- This file is automatically synced from ../CLAUDE_STANDARDS.md -->
<!-- Generated: 2025-06-23 00:54:53 -->
<!-- Source: ../CLAUDE_STANDARDS.md -->

# CLAUDE_STANDARDS.md - Amazon FBA Agent System v3.6 Development Standards

This file provides comprehensive guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

The Amazon FBA Agent System v3.5 is an enterprise-grade automation platform for identifying profitable Amazon FBA opportunities. It combines AI-driven supplier scraping, intelligent product matching, and comprehensive financial analysis to evaluate products at scale.

## 🚨 **CRITICAL INSTRUCTIONS FOR ALL DEVELOPMENT**

### **📋 TODO MANAGEMENT PROTOCOL**
**⚠️ MANDATORY: At the start of EVERY chat session or after `/compact`, ALWAYS:**

1. **Automated TODO Reading (CRITICAL):**
   ```bash
   # Read master TODO list if exists
   cat /root/.claude/todos/MASTER_TODO_LIST_before_pytest_fix.json 2>/dev/null || echo "No master TODO list found"
   
   # Check for any additional native todo files
   ls -la /root/.claude/todos/ 2>/dev/null || echo "No todos directory found"
   ```

2. **Display Current TODO Status:**
   - Show all pending high-priority tasks first
   - Show in-progress tasks with status updates
   - Show completed tasks from current session
   - Total count by priority level

3. **TODO Lifecycle Management:**
   - Use TodoWrite tool for session-based tracking
   - Update native todos files when tasks are completed
   - Sync between TodoWrite and native files every major milestone
   - Create new native todo files for major new initiatives

**TODO PRIORITY SYSTEM:**
- **HIGH**: System-critical, user-blocking, or explicitly requested tasks
- **MEDIUM**: Important improvements, documentation updates, optimizations  
- **LOW**: Nice-to-have features, code cleanup, auxiliary scripts

### **🔄 UPDATE PROTOCOL - CRITICAL COMPLIANCE**
**Whenever you update ANY file, script, output, or folder:**

1. **Cascading Updates Required:**
   - ✅ Check ALL related files that reference the changed item
   - ✅ Update ALL scripts that use the modified paths/functions
   - ✅ Update ALL documentation that mentions the changed item
   - ✅ Update ALL configuration files with new references

2. **Documentation Sync (MANDATORY):**
   - ✅ Update ALL relevant documentation in `docs/`
   - ✅ Update README.md with new paths/procedures
   - ✅ Update architecture diagrams if applicable
   - ✅ Update troubleshooting guides with new references

3. **Path Consistency Check:**
   - ✅ Verify path_manager.py reflects changes
   - ✅ Update system_config.json if paths changed
   - ✅ Test that all scripts still work with new paths

## Core Architecture

### Primary Workflow
The system follows a sophisticated pipeline orchestrated by `tools/passive_extraction_workflow_latest.py`:

```
AI Category Selection → Supplier Scraping → Amazon Matching → Financial Analysis → Report Generation
```

### Multi-Tier AI Fallback System
The system uses a 4-tier AI approach with >99% success rate:
1. **Tier 1 (v2 Mode)**: Temperature 0.1, clearance-first optimization
2. **Tier 2 (Legacy)**: Temperature 0.3, comprehensive category analysis  
3. **Tier 3 (Minimal)**: Temperature 0.5, basic fallback
4. **Tier 4 (Manual)**: Dynamic scraping-based discovery

### Key Components
- **`tools/passive_extraction_workflow_latest.py`** - Main orchestrator and entry point
- **`tools/configurable_supplier_scraper.py`** - Intelligent supplier website scraping
- **`tools/amazon_playwright_extractor.py`** - Amazon data extraction with anti-bot protection
- **`tools/FBA_Financial_calculator.py`** - ROI calculations and profitability analysis
- **`tools/cache_manager.py`** - State management and caching (240x performance improvement)
- **`tools/vision_product_locator.py`** - GPT-4 Vision integration for product detection

### Processing Phases
- **Phase 1**: £0.1-£10.0 price range (bulk processing)
- **Phase 2**: £10.0-£20.0 price range (high-value focus)
- **Auto-transition**: Based on product price patterns

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (required for anti-bot protection)
pip install playwright
playwright install chromium

# Set environment variables (security requirement)
export OPENAI_API_KEY="your-api-key"
export KEEPA_API_KEY="your-keepa-key"
```

### Running the System
```bash
# Standard production run (unlimited processing)
python tools/passive_extraction_workflow_latest.py --max-products 0

# Debug mode with visible browser
python tools/passive_extraction_workflow_latest.py --headless false --max-products 5

# Specific supplier processing
python tools/passive_extraction_workflow_latest.py --supplier-url "https://www.poundwholesale.co.uk/"

# System health check
python tools/passive_extraction_workflow_latest.py --health-check

# Shared Chrome connection (port 9222)
python tools/configurable_supplier_scraper.py --use-shared-chrome
```

### Testing and Quality
```bash
# Run test suite
python -m pytest tests/                    # All tests
python -m pytest --cov tools/             # With coverage
python -m pytest -m "not slow"            # Skip slow tests
python -m pytest tests/test_specific.py   # Single test file

# Code quality
python -m black tools/                     # Format code
python -m ruff check tools/                # Lint code  
python -m mypy tools/                      # Type checking

# Security scanning
python -m bandit -r tools/                 # Security analysis
grep -r "sk-" tools/                       # Find hardcoded API keys
```

### Build and Package
```bash
# Build package
python -m build

# Install in development mode
pip install -e .

# Use CLI tools
fba-extract --help                         # Main extraction tool
fba-monitor --help                         # Monitoring system
```

## 📁 Core Directory Structure

### Root Level Organization
```
/Amazon-FBA-Agent-System-v3/
├── CLAUDE_STANDARDS.md            # THIS FILE - Development standards (SOURCE OF TRUTH)
├── claude.md                      # Auto-generated automation target (DO NOT EDIT)
├── docs/                          # 📄 ALL documentation files
├── logs/                          # 📋 ALL log files (organized by type)
├── tools/                         # 🔧 Core application scripts  
├── config/                        # ⚙️ Configuration files
├── tests/                         # 🧪 Test files and test-related outputs
├── OUTPUTS/                       # 📊 Application data outputs (FBA analysis, etc.)
├── archive/                       # 📦 Deprecated/legacy files
└── utils/                         # 🛠️ Utility functions and helpers
```

## 📋 Essential File Organization Rules

### Log Files (AUTO-UPDATE TRIGGER: New log categories, components, or debugging needs)
- **Destination**: `logs/{category}/`
- **Naming**: `{component}_{YYYYMMDD}.{ext}`
- **Categories**: application, api_calls, tests, monitoring, security, debug

#### Log Directory Structure:
```
logs/
├── application/               # Main script execution logs
├── api_calls/                # External API interaction logs  
├── tests/                    # Test execution logs
├── monitoring/               # System monitoring and metrics
├── security/                 # Security and audit logs
└── debug/                   # Debug and troubleshooting logs
```

### Output Files (AUTO-UPDATE TRIGGER: New output types, analysis components, or data structures)
- **FBA Analysis**: `OUTPUTS/FBA_ANALYSIS/`
- **Cache Files**: `OUTPUTS/CACHE/`
- **Reports**: `OUTPUTS/REPORTS/`

#### Application Outputs Structure:
```
OUTPUTS/
├── FBA_ANALYSIS/              # Core FBA analysis results
│   ├── financial_reports/     # Financial calculations and ROI data
│   ├── amazon_cache/         # Amazon product data cache
│   ├── supplier_data/        # Supplier product information
│   └── linking_maps/         # Product matching data
├── CACHE/                     # Application cache files
└── REPORTS/                   # Generated reports and summaries
```

### Path Management (AUTO-UPDATE TRIGGER: New utility functions, path requirements, or directory changes)
Always use path helper functions from `utils/path_manager.py`:
```python
from utils.path_manager import get_log_path, get_output_path

# Correct usage
log_file = get_log_path("application", f"script_name_{datetime.now().strftime('%Y%m%d')}.log")
output_file = get_output_path("FBA_ANALYSIS", "financial_reports", f"report_{datetime.now().strftime('%Y%m%d')}.csv")
```

### State File Management Standards (AUTO-UPDATE TRIGGER: New processing states, supplier configs, or metadata requirements)
- **Location**: `OUTPUTS/CACHE/processing_states/`
- **Format**: JSON with comprehensive metadata
- **Required Fields**:
  ```json
  {
    "schema_version": "1.0",
    "created_at": "2025-06-15T10:30:00Z",
    "last_updated": "2025-06-15T12:45:30Z",
    "supplier_name": "clearance-king",
    "last_processed_index": 150,
    "total_products": 500,
    "processing_status": "in_progress"
  }
  ```

## Configuration (AUTO-UPDATE TRIGGER: New suppliers, system settings, or browser requirements)

### System Configuration
Main config: `config/system_config.json`
- Set all max_* values to 0 for unlimited processing
- AI mode configuration (v2/legacy/minimal)
- Browser and processing settings

### Supplier Configuration  
Individual configs: `config/supplier_configs/*.json`
- Supplier-specific scraping rules
- Category mappings and pricing filters
- Authentication and navigation settings

### Browser Setup
For Amazon extraction, Chrome must run with debug port:
```bash
chrome.exe --remote-debugging-port=9222
```

## Data Flow and Storage

### Processing Pipeline
1. **Category Discovery**: AI-selected categories from supplier sites
2. **Product Extraction**: Scraping with anti-bot measures
3. **Amazon Matching**: EAN/UPC primary, title similarity secondary  
4. **Financial Analysis**: FBA fees, ROI calculation, competition analysis
5. **Report Generation**: CSV financial reports and JSON summaries

### Output Structure
- **`OUTPUTS/FBA_ANALYSIS/`** - Financial reports and analysis results
- **`OUTPUTS/CACHE/`** - Processing states and temporary files
- **`logs/`** - Organized by category (application, api_calls, debug, etc.)

## Key Architecture Patterns

### Error Handling and Recovery
- Multi-tier AI fallback ensures >99% success rate
- State persistence prevents data loss (saves every 40 products)
- Graceful degradation from AI to manual discovery
- Comprehensive logging for debugging

### Performance Optimizations
- Smart caching system (240x improvement achieved)
- Async operations where possible
- Rate limiting to respect API quotas
- Browser connection reuse

### Security Considerations (AUTO-UPDATE TRIGGER: New security protocols, API changes, or safety requirements)
⚠️ **CRITICAL**: This system currently has hardcoded API keys in 15+ files that must be moved to environment variables before production use.

#### Output Safety Rules (AUTO-UPDATE TRIGGER: New supplier integrations or output isolation requirements)
- All supplier outputs must be isolated to supplier-specific subdirectories
- No cross-contamination between supplier data
- Automatic subdirectory creation for new suppliers

## Testing Strategy

The system uses pytest with specific markers:
- `slow`: Long-running tests (skip with `-m "not slow"`)
- `integration`: Cross-component tests
- `unit`: Isolated component tests
- `api`: Tests requiring external API access  
- `requires_browser`: Tests needing browser automation

Test fixtures in `tests/conftest.py` provide mocked components for isolated testing.

## Troubleshooting

### Common Issues
- **Browser connection failed**: Restart Chrome with `--remote-debugging-port=9222`
- **AI API failures**: Check API keys and quotas
- **Cache corruption**: Clear cache files in `OUTPUTS/CACHE/`
- **Memory issues**: Monitor with `python tools/memory_optimizer.py`

### Health Monitoring
- System status via `--health-check` flag
- Performance metrics in `logs/monitoring/`
- Cache validation tools available

## Documentation References

For detailed information, see:
- **`docs/README.md`** - Complete system overview and usage guide
- **`docs/SYSTEM_DEEP_DIVE.md`** - Technical architecture and performance analysis
- **`config/supplier_config.md`** - Supplier configuration documentation

## 🚨 CRITICAL IMPLEMENTATION NOTES

### **Vision + Playwright EAN Bootstrap System (June 2025)**

**Status**: ✅ IMPLEMENTED & TESTED  
**Location**: `vision_ean_bootstrap.py`, `tools/vision_product_locator.py`

#### **Key Achievements**:
- ✅ **CDP Browser Connection**: Successfully connects to shared Chrome (port 9222)
- ✅ **Login Detection**: Correctly detects existing login state 
- ✅ **Homepage Product Detection**: Finds 10+ product links on homepage
- ✅ **Output Safety Rules**: Proper supplier isolation in OUTPUTS/FBA_ANALYSIS/
- ✅ **Debug Logging**: Comprehensive logging to logs/debug/
- ✅ **Vision API Integration**: GPT-4.1-mini-2025-04-14 fallback working
- ✅ **Linking Map Generation**: Automated linking map creation

## Development Notes

- Python 3.12+ required
- Uses Playwright for robust browser automation
- File-based JSON storage (database upgrade recommended for scale)
- Modular design supports easy extension and maintenance
- Comprehensive documentation in `docs/` directory

The system is production-ready with excellent architectural design, requiring only security remediation for hardcoded API keys before enterprise deployment.

---

**Last Updated**: 2025-06-22  
**Version**: 3.6  
**Maintained By**: Amazon FBA Agent System Team  
**Status**: ACTIVE STANDARD - All development must comply

**File Generation Info**: This is the SOURCE OF TRUTH for all development standards. The file `claude.md` is auto-generated from this file for automation compatibility.