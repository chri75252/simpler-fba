# poundwholesale-co-uk Automation Usage

## Generated Scripts

### 1. Login Automation
```bash
cd suppliers/poundwholesale-co-uk/scripts
python poundwholesale-co-uk_login.py
```

### 2. Product Extraction  
```bash
cd suppliers/poundwholesale-co-uk/scripts
python poundwholesale-co-uk_product_extractor.py
```

### 3. LangGraph Integration
```bash
cd suppliers/poundwholesale-co-uk/scripts
python poundwholesale-co-uk_langgraph_integration.py
```

## Integration with Main System

Add to LangGraph workflow:
```python
from suppliers.poundwholesale-co-uk.scripts.poundwholesale-co-uk_langgraph_integration import setup_poundwholesale_co_uk_supplier

# In workflow
result = await setup_poundwholesale_co_uk_supplier(page, credentials)
```

## Generated: 2025-07-05T20:51:29.864163
