"""
Scrape Amazon search results (by GTIN or title) and return best match.
No Product-Advertising API required.
"""
from __future__ import annotations
import logging, difflib, os, re
from typing import Dict, Any, Optional
from urllib.parse import quote
from playwright.sync_api import sync_playwright

log = logging.getLogger(__name__)
PROFILE = os.getenv("CHROME_PROFILE_PATH") or ""

def _search_url(term:str)->str:
    return f"https://www.amazon.co.uk/s?k={quote(term)}&i=aps&tag=dummy-21"

def _ctx():
    pw = sync_playwright().start()
    ctx = pw.chromium.launch_persistent_context(PROFILE, headless=True)
    page = ctx.new_page()
    page.set_default_timeout(40000)
    return ctx,page

ASIN_RE = re.compile(r"/([A-Z0-9]{10})(?:[/?]|$)")

def extract_asin(url:str)->str:
    m = ASIN_RE.search(url)
    return m.group(1) if m else ""

def find_best(product:Dict[str,Any])->Dict[str,Any]:
    term = product.get("gtin") or product["title"]
    ctx,p = _ctx()
    try:
        p.goto(_search_url(term), wait_until="networkidle")
        cards = p.locator("div[data-component-type='s-search-result']")
        best = {}; best_score = 0.0
        for i in range(min(cards.count(),10)):
            el = cards.nth(i)
            url = el.locator("h2 a").get_attribute("href") or ""
            title = el.locator("h2 a span").inner_text()[:300]
            asin  = extract_asin(url)
            sim   = difflib.SequenceMatcher(None,
                                            product["title"].lower(), title.lower()).ratio()
            if sim > best_score:
                best_score = sim
                price_txt = el.locator(".a-price-whole").first.inner_text() or "0"
                price = float(price_txt.replace(",","")) if price_txt else 0.0
                best = {"asin":asin,"url":"https://www.amazon.co.uk"+url,
                        "title":title,"amazon_price":price,"confidence":round(sim,2)}
        return best or {"asin":""}
    except Exception as exc:
        log.error("Amazon scrape failed: %s", exc)
        return {"asin":"","error":str(exc)}
    finally:
        ctx.close()