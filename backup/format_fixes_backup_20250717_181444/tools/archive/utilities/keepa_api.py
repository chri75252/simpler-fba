"""
Tiny Keepa REST wrapper – only the endpoints we need.
Keeps the public interface identical to the old mock so the agent needn't change.
"""
from __future__ import annotations
import os, time, logging, requests
from typing import Dict, Any, List

log = logging.getLogger(__name__)
KEEPA_API_KEY = os.getenv("KEEPA_API_KEY")

BASE = "https://api.keepa.com"

def _call(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if not KEEPA_API_KEY:
        raise RuntimeError("KEEPA_API_KEY not set")
    params["key"] = KEEPA_API_KEY
    r = requests.get(f"{BASE}/{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()

# ─────────────────────────────────
# Public helper mimicking old output
# ─────────────────────────────────
def extract_keepa_data(asin: str) -> Dict[str, Any]:
    """Return price/rank history + metrics, or error structure on failure."""
    try:
        data = _call("product", {"domain": 2, "buybox": 1, "history": 1, "asin": asin})
        if not data.get("products"):
            return {"asin": asin, "error": "No data found"}
        p = data["products"][0]
        # Keepa history arrays are huge; slice last 90 days & derive metrics.
        hist = p["csv"]          # idx 0 = Amazon price, 1 = sales rank, etc.
        # timestamp is minutes since 2011-01-01 UTC ⇒ convert:
        def _ts(k): return int((k*60)+1293840000)   # unix sec
        price_hist = [{"date": _ts(t), "price": v/100.0}
                      for t, v in hist[0][-720:] if v > 0]
        rank_hist  = [{"date": _ts(t), "rank":  v}
                      for t, v in hist[1][-720:] if v > 0]
        avg_price  = sum(x["price"] for x in price_hist)/len(price_hist) if price_hist else 0
        min_price  = min(x["price"] for x in price_hist) if price_hist else 0
        avg_rank   = sum(x["rank"]  for x in rank_hist)/len(rank_hist)   if rank_hist else 0
        return {
            "asin": asin,
            "price_history": price_hist,
            "sales_rank_history": rank_hist,
            "current_price": price_hist[-1]["price"] if price_hist else None,
            "current_sales_rank": rank_hist[-1]["rank"] if rank_hist else None,
            "avg_price_90d": round(avg_price, 2),
            "min_price_90d": round(min_price, 2),
            "avg_sales_rank_90d": int(avg_rank),
        }
    except Exception as exc:
        log.error("Keepa API failure: %s", exc)
        return {"asin": asin, "error": str(exc), "price_history": [], "sales_rank_history": []}