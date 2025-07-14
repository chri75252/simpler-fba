# Amazon FBA Tool - AGENTS.md Guide

## Project Purpose
Automated Amazon FBA product research and profitability analysis tool that scrapes supplier websites, matches products with Amazon listings, and calculates profit potential.

## Key Components
- `tools/passive_extraction_workflow_latest.py`: Main workflow engine
- `tools/configurable_supplier_scraper.py`: Supplier website scraping
- `tools/amazon_playwright_extractor.py`: Amazon data extraction
- `tools/FBA_Financial_calculator.py`: Profit calculations

## Coding Patterns
- Use async/await for all web scraping operations
- Implement proper rate limiting (2-3 second delays)
- Cache API responses in OUTPUTS/FBA_ANALYSIS/
- Always validate EAN/UPC codes before Amazon matching
- Generate CSV reports for financial analysis

## Configuration
- Main config: `config/system_config.json`
- Supplier configs: `config/supplier_configs/`
- Environment variables: `.env` file

## Testing Commands
