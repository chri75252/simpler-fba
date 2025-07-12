# harrisonsdirect-co-uk Automation Usage

## Generated Scripts

### 1. Login Automation
```bash
cd suppliers/harrisonsdirect-co-uk/scripts
python harrisonsdirect-co-uk_login.py
```

### 2. Product Extraction  
```bash
cd suppliers/harrisonsdirect-co-uk/scripts
python harrisonsdirect-co-uk_product_extractor.py
```

### 3. LangGraph Integration
```bash
cd suppliers/harrisonsdirect-co-uk/scripts
python harrisonsdirect-co-uk_langgraph_integration.py
```

## Integration with Main System

Add to LangGraph workflow:
```python
from suppliers.harrisonsdirect-co-uk.scripts.harrisonsdirect-co-uk_langgraph_integration import setup_harrisonsdirect_co_uk_supplier

# In workflow
result = await setup_harrisonsdirect_co_uk_supplier(page, credentials)
```

## Generated: 2025-07-05T21:37:59.593831
