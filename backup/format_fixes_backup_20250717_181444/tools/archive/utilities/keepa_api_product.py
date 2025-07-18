"""
One-token Keepa call for deep analysis of CANDIDATE ASINs:
90d price & BSR history + BuyBox.
"""
import os, time, requests
from typing import Dict, Any

KEY = os.getenv("KEEPA_API_KEY")
API = "https://api.keepa.com/product"
DOM = 3

def fetch_product(asin:str) -> Dict[str, Any]:
    if not KEY:
        raise RuntimeError("KEEPA_API_KEY missing")
    params = {
        "key": KEY, "domain": DOM, "asin": asin,
        "history": 1, "buybox": 1, "stats": 90
    }
    t0 = time.time()
    r  = requests.get(API, params=params, timeout=30)
    r.raise_for_status()
    p  = r.json()["products"][0]
    return {"asin":asin, "raw":p, "elapsed":round(time.time()-t0,2)}