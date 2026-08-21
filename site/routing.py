"""Real road routing for the trip: true geometry + distance + duration.

Uses OSRM (road-network routing) and caches every result to routes_cache.json,
so the map and the itinerary are always drawn from the SAME verified data.

REALISM was calibrated (Aug 2026) by comparing OSRM free-flow against
traffic-aware Google Routes on all 12 legs of the real itinerary: the median
ratio was 1.03 and every leg agrees within ~10 minutes at 1.05. The previous
1.20 was a guess that inflated every drive by about 16%.

Everything DISPLAYED in the guide — durations and map polylines alike — comes
from this OSM-derived stack, so the published site stays on one license.
Google is used only offline, as a measuring stick to calibrate the factor.
"""
import json, os, time, urllib.request, urllib.parse

D = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(D, "routes_cache.json")
REALISM = 1.05

# Coordinates verified against Google Places (Aug 2026). Two were materially
# wrong before: Lannawild was 9.5 km off, 8Adventures 8.5 km off.
PLACES = {
    "airport":      (18.7677, 98.9620),  # CNX
    "city":         (18.7810, 98.9860),  # hotel, south Old City
    "waterpark":    (18.6974, 98.8919),  # Grand Canyon Water Park, Hang Dong
    "skyline":      (18.9532, 99.3342),  # Skyline Adventure, Doi Saket (Google Places)
    "lannawild":    (18.8930, 99.3499),  # Lan Na Wild, Mae On (Google Places)
    "hotsprings":   (18.8145, 99.2294),  # San Kamphaeng hot springs
    "thegiant":     (18.8924, 99.3513),  # The Giant treehouse cafe, Mae Kampong
    "baankangwat":  (18.7720, 98.9420),  # Baan Kang Wat artist village
    "chomcafe":     (18.7480, 98.9440),  # Chom Cafe, Mae Hia
    "chailai":      (18.6583, 98.6336),  # Chai Lai Orchid, Mae Sapok
    "huaytungtao":  (18.8620, 98.9270),  # Huay Tung Tao lake
    "buatong":      (19.0694, 99.0791),  # Bua Tong sticky waterfall
    "treehouse":    (19.3194, 98.8905),  # Tree House Hideaway, Ban Mae Mae
    "rafting":      (19.2207, 98.8492),  # 8Adventures Camp, Kuet Chang
    "raya":         (18.8486, 98.9853),  # Raya Heritage, Ping riverside
    "maerim":       (18.9160, 98.9350),  # Mae Rim town (route reference)

    # Koh Phangan
    "thongsala":    (9.7069, 99.9906),   # ferry pier / main town
    "thongnaipan":  (9.7860, 100.0745),  # Thong Nai Pan beaches
    "chaloklum":    (9.7920, 100.0083),  # Chaloklum fishing village
    "bottlebeach":  (9.7995, 100.0405),  # Bottle Beach trailhead
    "kohma":        (9.7873, 99.9709),   # Koh Ma / Mae Haad snorkelling
    "haadrin":      (9.6742, 100.0688),  # Haad Rin
    "phaeng":       (9.7482, 100.0201),  # Phaeng waterfall / viewpoint

    # Bangkok
    "bkkhotel":     (13.7500, 100.4913),
    "maeklong":     (13.4098, 99.9990),  # Maeklong railway market
    "damnoen":      (13.5209, 99.9556),  # Damnoen Saduak floating market
}

_cache = json.load(open(CACHE_PATH, encoding="utf-8")) if os.path.exists(CACHE_PATH) else {}


def route(*stops, full_geometry=True):
    """Route through stops (place keys). Returns dict with km, minutes, geometry."""
    key = ">".join(stops) + ("|full" if full_geometry else "")
    if key in _cache:
        return _cache[key]
    coords = ";".join(f"{PLACES[s][1]},{PLACES[s][0]}" for s in stops)
    ov = "full" if full_geometry else "false"
    url = (f"https://router.project-osrm.org/route/v1/driving/{coords}"
           f"?overview={ov}&geometries=geojson")
    with urllib.request.urlopen(url, timeout=30) as r:
        d = json.load(r)
    time.sleep(0.6)
    rt = d["routes"][0]
    out = {
        "km": round(rt["distance"] / 1000, 1),
        "min_raw": round(rt["duration"] / 60),
        "min": round(rt["duration"] / 60 * REALISM),
        "geometry": [[c[1], c[0]] for c in rt["geometry"]["coordinates"]] if full_geometry else [],
    }
    _cache[key] = out
    json.dump(_cache, open(CACHE_PATH, "w"), separators=(",", ":"))
    return out


def leg(a, b):
    r = route(a, b, full_geometry=False)
    return r["km"], r["min"]


# ─────────────────────────────────────────────────────────────────────────
#  Google Routes API — traffic-aware durations (the numbers we plan with)
#
#  Split of responsibilities, on purpose:
#   · Google  → DURATIONS. Traffic-aware, matches what Google Maps shows.
#   · OSRM    → GEOMETRY drawn on the map. OSM-derived lines on OSM tiles
#               stay license-compatible; Google forbids rendering its route
#               geometry over a non-Google basemap.
# ─────────────────────────────────────────────────────────────────────────
GKEY_PATH = os.path.join(D, ".maps-api-key")
GKEY = open(GKEY_PATH).read().strip() if os.path.exists(GKEY_PATH) else None
GCACHE_PATH = os.path.join(D, "routes_cache_google.json")
_gcache = json.load(open(GCACHE_PATH, encoding="utf-8")) if os.path.exists(GCACHE_PATH) else {}

# a normal departure on the trip: Thu 24 Sep 2026, 09:15 local (UTC+7)
DEFAULT_DEPART = "2026-09-24T02:15:00Z"


def gleg(a, b, depart=DEFAULT_DEPART):
    """Traffic-aware (km, minutes) from Google Routes. Falls back to OSRM."""
    key = f"{a}>{b}@{depart}"
    if key in _gcache:
        return _gcache[key]["km"], _gcache[key]["min"]
    if not GKEY:
        return leg(a, b)
    (la1, lo1), (la2, lo2) = PLACES[a], PLACES[b]
    body = {
        "origin": {"location": {"latLng": {"latitude": la1, "longitude": lo1}}},
        "destination": {"location": {"latLng": {"latitude": la2, "longitude": lo2}}},
        "travelMode": "DRIVE", "routingPreference": "TRAFFIC_AWARE",
        "departureTime": depart,
    }
    req = urllib.request.Request(
        "https://routes.googleapis.com/directions/v2:computeRoutes",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": GKEY,
                 "X-Goog-FieldMask": "routes.distanceMeters,routes.duration"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    time.sleep(0.25)
    rt = d["routes"][0]
    out = {"km": round(rt["distanceMeters"] / 1000, 1),
           "min": round(int(rt["duration"].rstrip("s")) / 60)}
    _gcache[key] = out
    json.dump(_gcache, open(GCACHE_PATH, "w"), separators=(",", ":"))
    return out["km"], out["min"]


if __name__ == "__main__":
    import sys
    pairs = [
        ("airport", "city"), ("city", "waterpark"), ("city", "skyline"),
        ("city", "lannawild"), ("city", "baankangwat"), ("baankangwat", "chailai"),
        ("city", "chailai"), ("lannawild", "chailai"), ("chailai", "buatong"),
        ("buatong", "treehouse"), ("buatong", "raya"), ("treehouse", "rafting"),
        ("rafting", "raya"), ("raya", "airport"), ("city", "buatong"),
        ("lannawild", "buatong"), ("treehouse", "raya"), ("city", "rafting"),
    ]
    print(f"{'קטע':34}{'ק\"מ':>8}{'ריאלי':>9}")
    for a, b in pairs:
        km, mn = leg(a, b)
        print(f"{a + ' → ' + b:34}{km:8.0f}{mn:7.0f}ד")