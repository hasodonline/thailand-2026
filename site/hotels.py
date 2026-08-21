"""Hotel search via SerpApi's Google Hotels engine, scored against OUR route.

Google Hotels aggregates live prices from Booking, Agoda and Expedia, which is
the closest thing to a usable hotel-pricing API for an individual: Booking's own
Demand API needs an approved affiliate partnership, and Google's Places API
returns ratings and hours but no rates at all.

The point of this module is not just to list hotels. A hotel is only good for
this trip if it is cheap, well reviewed AND positioned so the drives still work
— so every candidate gets its real road distance measured to the places we
actually drive to, and the ranking uses all three.
"""
import json
import os
import urllib.parse
import urllib.request

from routing import PLACES, gleg

D = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.path.join(D, ".serpapi-key")).read().strip()
CACHE_PATH = os.path.join(D, "hotels_cache.json")
_cache = json.load(open(CACHE_PATH, encoding="utf-8")) if os.path.exists(CACHE_PATH) else {}

# Google Hotels caps a query at 6 travellers, so we search 5+1 — the closest
# shape to the real party — and treat the result as the comparison baseline.
# The actual booking is 7 people across 2-3 rooms, so confirm the final pick
# directly with the property; expect roughly one extra bed's worth on top.
ADULTS, CHILDREN = 5, 1


def search(q, check_in, check_out, min_rating=8.0, hotel_class=None, max_price=None):
    """One Google Hotels search. Cached — the free tier is 250 searches/month."""
    params = {
        "engine": "google_hotels", "q": q,
        "check_in_date": check_in, "check_out_date": check_out,
        "adults": ADULTS, "children": CHILDREN, "children_ages": "12",
        "currency": "THB", "gl": "il", "hl": "en",
        "api_key": KEY,
    }
    if hotel_class:
        params["hotel_class"] = hotel_class
    if max_price:
        params["max_price"] = max_price
    ck = json.dumps({k: v for k, v in params.items() if k != "api_key"}, sort_keys=True)
    if ck in _cache:
        return _cache[ck]
    url = "https://serpapi.com/search?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as r:
        d = json.load(r)
    if "error" in d:
        raise RuntimeError(d["error"])
    out = d.get("properties", [])
    _cache[ck] = out
    json.dump(_cache, open(CACHE_PATH, "w"), ensure_ascii=False)
    return out


def drive_times(lat, lon, targets):
    """Real road minutes from a hotel to each place we drive to from it.

    The candidate is registered under a key derived from its own coordinates.
    A fixed key like "_cand" would make the router's cache return the FIRST
    hotel's times for every hotel afterwards — which silently makes every
    candidate look identical.
    """
    key = f"_c{lat:.4f}_{lon:.4f}"
    PLACES[key] = (lat, lon)
    out = {}
    for t in targets:
        try:
            out[t] = gleg(key, t)[1]
        except Exception:
            out[t] = None
    return out


def rows(props, nights):
    """Flatten SerpApi results into comparable rows."""
    res = []
    for p in props:
        rate = (p.get("total_rate") or {}).get("extracted_lowest")
        if not rate:
            nightly = (p.get("rate_per_night") or {}).get("extracted_lowest")
            rate = nightly * nights if nightly else None
        gps = p.get("gps_coordinates") or {}
        res.append({
            "name": p.get("name", "?"),
            "total": rate,
            "per_night": round(rate / nights) if rate else None,
            "rating": p.get("overall_rating"),
            "reviews": p.get("reviews"),
            "stars": p.get("hotel_class"),
            "lat": gps.get("latitude"), "lon": gps.get("longitude"),
            "amenities": p.get("amenities", []),
            "link": p.get("link"),
        })
    return [r for r in res if r["total"] and r["lat"]]
