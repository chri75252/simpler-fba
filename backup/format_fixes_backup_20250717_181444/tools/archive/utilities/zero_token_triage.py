"""
Zero-token triage: scrapes only DOM elements rendered by
Helium 10, Jungle Scout, SellerAmp and Keepa overlay on the PDP.
Decides REJECT vs. CANDIDATE before any API call.
"""
import os, re, logging
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

log = logging.getLogger(__name__)
PROFILE = os.getenv("CHROME_PROFILE_PATH") or ""
URL_TMPL = "https://www.amazon.co.uk/dp/{asin}"

# Hard-fail thresholds (tweak as needed)
MAX_BSR         = 50000
MIN_ROI         = 28.0
MIN_NET_PROFIT  = 2.50
MIN_DROPS_PM    = 15
MAX_VARIATIONS  = 50

_PRICE_RE = re.compile(r"[£$€]\s?([\d,.]+)")
_INT_RE   = re.compile(r"(\d[\d,]*)")

def _to_float(txt:str)->float:
    m=_PRICE_RE.search(txt or "")
    return float(m.group(1).replace(",","")) if m else 0.0

def _to_int(txt:str)->int:
    m=_INT_RE.search(txt or "")
    return int(m.group(1).replace(",","")) if m else 0

def triage(asin:str, landed_cost:float)->dict:
    pw = sync_playwright().start()
    ctx = pw.chromium.launch_persistent_context(PROFILE,
        headless=True,
        args=["--disable-blink-features=AutomationControlled"])
    page = ctx.new_page()
    page.set_default_timeout(30000)
    out={"asin":asin}
    try:
        page.goto(URL_TMPL.format(asin=asin), wait_until="networkidle")
        page.wait_for_selector("div[data-testid='roi-value']", timeout=15000)
        # scrape
        roi_txt   = page.inner_text("div[data-testid='roi-value']").rstrip("%")
        profit_txt= page.inner_text("div[data-testid='profit-value']")
        bsr_txt   = page.inner_text("span[data-component-type='s-product-image-container']")
        drops_el  = page.query_selector("div.h10-drops-bar span.value")
        var_el    = page.query_selector("span.js-variation-count")
        amazon_el = page.query_selector("span.sas-offer-badge-amazon")
        haz_el    = page.query_selector("div.sas-alert-hazmat[data-status='red']")
        ip_el     = page.query_selector("div.sas-alert-ip[data-status='red']")

        roi        = float(roi_txt) if roi_txt else 0.0
        net_profit = _to_float(profit_txt)
        bsr        = _to_int(bsr_txt)
        drops_pm   = _to_int(drops_el.inner_text()) if drops_el else 0
        variations = _to_int(var_el.inner_text()) if var_el else 1
        amazon_rt  = bool(amazon_el)
        hazmat     = bool(haz_el)
        ip_block   = bool(ip_el)

        reasons=[]
        if roi < MIN_ROI or net_profit < MIN_NET_PROFIT: reasons.append("Low ROI/profit")
        if bsr > MAX_BSR:                    reasons.append("High BSR")
        if drops_pm < MIN_DROPS_PM:         reasons.append("Low demand")
        if variations > MAX_VARIATIONS:     reasons.append("Too many vars")
        if amazon_rt:                       reasons.append("Amazon Retail")
        if hazmat or ip_block:              reasons.append("Hazard/IP")

        out.update(dict(
            verdict="REJECT" if reasons else "CANDIDATE",
            reasons=reasons,
            roi=roi,
            net_profit=net_profit,
            bsr=bsr,
            drops_pm=drops_pm,
            variations=variations
        ))
        return out

    except PWTimeout:
        return {"asin":asin,"verdict":"ERROR","reasons":["Timeout"]}
    except Exception as e:
        log.error("triage error",e)
        return {"asin":asin,"verdict":"ERROR","reasons":[str(e)]}
    finally:
        ctx.close()