"""Real Google maps, rendered at build time into offline PNGs.

Google's Routes API returns each leg as an encoded polyline; the Static Maps API
draws that polyline onto a genuine Google basemap and hands back a PNG. We
download the PNG here, during the build, and the guide embeds it as base64.

That gives the family a Google map with Google's own roads, labels and route
geometry that still works with no signal — and the API key never leaves this
machine, so nothing billable ships inside a public GitHub Pages site.

Drawing Google route geometry on a Google basemap is also the licensed way
round: Maps Platform terms forbid putting Google content on someone else's map,
which is why the OSM stack in make_maps.py stays entirely OSM-sourced.
"""
import json
import os
import urllib.parse
import urllib.request

from routing import PLACES

D = os.path.dirname(os.path.abspath(__file__))
MAPS = os.path.join(os.path.dirname(D), "maps")
os.makedirs(MAPS, exist_ok=True)
KEY = open(os.path.join(D, ".maps-api-key")).read().strip()
CACHE_PATH = os.path.join(D, "polylines_cache.json")
_cache = json.load(open(CACHE_PATH, encoding="utf-8")) if os.path.exists(CACHE_PATH) else {}

DEPART = "2026-09-24T02:15:00Z"


def polyline(*stops, quality="OVERVIEW"):
    """Encoded polyline for the driving route through stops (PLACES keys).

    OVERVIEW keeps the string short enough that several legs fit inside the
    Static Maps URL limit; HIGH_QUALITY is available when a single leg is drawn
    on its own.
    """
    key = ">".join(stops) + "|" + quality
    if key in _cache:
        return _cache[key]
    pts = [PLACES[s] for s in stops]
    body = {
        "origin": {"location": {"latLng": {"latitude": pts[0][0], "longitude": pts[0][1]}}},
        "destination": {"location": {"latLng": {"latitude": pts[-1][0], "longitude": pts[-1][1]}}},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
        "departureTime": DEPART,
        "polylineQuality": quality,
    }
    if len(pts) > 2:
        body["intermediates"] = [
            {"location": {"latLng": {"latitude": la, "longitude": lo}}} for la, lo in pts[1:-1]
        ]
    req = urllib.request.Request(
        "https://routes.googleapis.com/directions/v2:computeRoutes",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": KEY,
            "X-Goog-FieldMask": "routes.polyline.encodedPolyline,routes.distanceMeters,routes.duration",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    rt = d["routes"][0]
    out = {
        "enc": rt["polyline"]["encodedPolyline"],
        "km": round(rt["distanceMeters"] / 1000, 1),
        "min": round(int(rt["duration"].rstrip("s")) / 60),
    }
    _cache[key] = out
    json.dump(_cache, open(CACHE_PATH, "w"), separators=(",", ":"))
    return out


def _decode(enc):
    """Google's encoded-polyline format → [(lat, lon), …]."""
    pts, i, lat, lon = [], 0, 0, 0
    while i < len(enc):
        for axis in range(2):
            shift = result = 0
            while True:
                b = ord(enc[i]) - 63
                i += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if axis == 0:
                lat += delta
            else:
                lon += delta
        pts.append((lat / 1e5, lon / 1e5))
    return pts


def _encode(pts):
    out, plat, plon = [], 0, 0
    for lat, lon in pts:
        ilat, ilon = round(lat * 1e5), round(lon * 1e5)
        for d in (ilat - plat, ilon - plon):
            d = ~(d << 1) if d < 0 else d << 1
            while d >= 0x20:
                out.append(chr((0x20 | (d & 0x1F)) + 63))
                d >>= 5
            out.append(chr(d + 63))
        plat, plon = ilat, ilon
    return "".join(out)


def _simplify(pts, tol):
    """Douglas-Peucker. Drops points that sit within `tol` degrees of the line
    they fall on, so the road's shape survives but the string gets much shorter."""
    if len(pts) < 3:
        return pts
    ax, ay = pts[0]
    bx, by = pts[-1]
    dx, dy = bx - ax, by - ay
    norm = (dx * dx + dy * dy) ** 0.5 or 1e-12
    worst, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        px, py = pts[i]
        d = abs(dy * px - dx * py + bx * ay - by * ax) / norm
        if d > worst:
            worst, idx = d, i
    if worst <= tol:
        return [pts[0], pts[-1]]
    return _simplify(pts[:idx + 1], tol)[:-1] + _simplify(pts[idx:], tol)


def shorten(enc, budget=2200):
    """Shrink an encoded polyline until it fits `budget` characters."""
    if len(enc) <= budget:
        return enc
    pts = _decode(enc)
    tol = 0.0002
    for _ in range(14):
        out = _encode(_simplify(pts, tol))
        if len(out) <= budget:
            print(f"    פוליליין {len(enc)} → {len(out)} תווים (סטייה מרבית ~{tol * 111000:.0f} מ׳)")
            return out
        tol *= 1.6
    return out


def static_map(out, paths=(), markers=(), size="640x640", scale=2, maptype="roadmap"):
    """Download a Google basemap PNG with the given routes and pins drawn on it."""
    parts = [f"size={size}", f"scale={scale}", f"maptype={maptype}", "region=TH"]
    for p in paths:
        parts.append(
            f"path=color:{p.get('color', '0x1e5c3fdd')}|weight:{p.get('w', 5)}|enc:{shorten(p['enc'])}"
        )
    for m in markers:
        parts.append(
            f"markers=color:{m.get('color', 'red')}|label:{m['label']}|{m['lat']},{m['lon']}"
        )
    url = "https://maps.googleapis.com/maps/api/staticmap?" + "&".join(parts) + f"&key={KEY}"
    if len(url) > 16384:
        raise ValueError(f"static map URL is {len(url)} chars, over Google's 16,384 limit")
    with urllib.request.urlopen(url, timeout=60) as r:
        data = r.read()
    path = os.path.join(MAPS, out)
    with open(path, "wb") as f:
        f.write(data)
    if path.endswith(".png"):  # the build pipeline embeds JPEGs
        jpg = path[:-4] + ".jpg"
        os.system(f'sips -s format jpeg -s formatOptions 82 -Z 900 "{path}" --out "{jpg}" >/dev/null 2>&1')
        os.remove(path)
        path = jpg
    print(f"  {out}  {len(data)//1024} KB  (URL {len(url)} chars)")
    return path
