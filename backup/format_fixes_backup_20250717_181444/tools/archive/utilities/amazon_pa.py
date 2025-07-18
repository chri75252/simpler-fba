"""
Very thin Amazon Product-Advertising API (v5) helper for fast ASIN look-ups.
Only used by AmazonMatchingAgent for GTIN→ASIN and price retrieval.
"""
import os, logging, datetime, hashlib, hmac, requests, urllib.parse
from typing import Optional, Dict

log = logging.getLogger(__name__)
AK  = os.getenv("AMAZON_PA_ACCESS_KEY")
SK  = os.getenv("AMAZON_PA_SECRET_KEY")
TAG = os.getenv("AMAZON_PA_ASSOC_TAG")

ENDPOINT = "webservices.amazon.co.uk"
HOST     = f"https://{ENDPOINT}"
URI      = "/paapi5/getitems"

def _sign(payload: str, t: str) -> str:
    kDate = hmac.new(("AWS4"+SK).encode(), t[:8].encode(), "sha256").digest()
    kReg  = hmac.new(kDate, b"eu-west-1", "sha256").digest()
    kSvc  = hmac.new(kReg,  b"ProductAdvertisingAPI", "sha256").digest()
    kSig  = hmac.new(kSvc,  ("aws4_request").encode(), "sha256").digest()
    return hmac.new(kSig, payload.encode(), "sha256").hexdigest()

def item_lookup(gtin: str) -> Optional[Dict]:
    """Return minimal item dict {asin, price, url, title} or None."""
    if not (AK and SK and TAG):
        log.warning("Amazon PA keys missing – skipping")
        return None
    t = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "ItemIds": [gtin],
        "IdType": "EAN" if len(gtin)==13 else "UPC",
        "Resources": ["Images.Primary.Small", "ItemInfo.Title",
                      "Offers.Listings.Price"],
        "PartnerTag": TAG,
        "PartnerType": "Associates"
    }
    import json
    body = json.dumps(payload)
    hdrs = {
        "content-encoding": "amz-1.0",
        "content-type": "application/json; charset=utf-8",
        "host": ENDPOINT,
        "x-amz-date": t,
        "x-amz-target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems"
    }
    signed = _sign("POST\n"+URI+"\n\n"+("\n".join(f"{k}:{v}" for k,v in hdrs.items()))+
                   "\n\n"+hashlib.sha256(body.encode()).hexdigest(), t)
    hdrs["Authorization"] = (
      f"AWS4-HMAC-SHA256 Credential={AK}/{t[:8]}/eu-west-1/"
      "ProductAdvertisingAPI/aws4_request, SignedHeaders=content-encoding;"
      "content-type;host;x-amz-date;x-amz-target, Signature="+signed
    )
    r = requests.post(HOST+URI, headers=hdrs, data=body, timeout=20)
    if r.status_code!=200:
        log.error("PA-API error %s %s", r.status_code, r.text[:200])
        return None
    j = r.json()
    try:
        itm = j["ItemsResult"]["Items"][0]
        price = itm["Offers"]["Listings"][0]["Price"]["Amount"]/100
        return {
            "asin":   itm["ASIN"],
            "price":  price,
            "url":    itm["DetailPageURL"],
            "title":  itm["ItemInfo"]["Title"]["DisplayValue"]
        }
    except Exception as exc:
        log.error("PA parse error: %s", exc)
        return None