"""Stitch OSM tiles into real maps with route + numbered markers.

Route lines are the ACTUAL road geometry returned by the router (hundreds of
points following every switchback), not hand-placed waypoints. Use road() to
build them; passing literal coordinate lists draws a line that lies about
where the road goes.
"""
import math, os, time, urllib.request
from PIL import Image, ImageDraw, ImageFont
from routing import route as _route

D = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(D, "tilecache"); os.makedirs(CACHE, exist_ok=True)
MAPS = os.path.join(os.path.dirname(D), "maps"); os.makedirs(MAPS, exist_ok=True)
UA = {"User-Agent": "FamilyTripPlanner/1.0 (personal, low-volume trip-guide build)"}

def ll2px(lat, lon, z):
    n = 2 ** z * 256
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y

def get_tile(z, x, y):
    p = os.path.join(CACHE, f"{z}_{x}_{y}.png")
    if not os.path.exists(p):
        url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r, open(p, "wb") as f:
            f.write(r.read())
        time.sleep(0.15)
    return Image.open(p).convert("RGB")

def road(*stops, color=None, w=6, dash=False):
    """A route line that follows the real road through `stops` (routing.PLACES keys)."""
    r = _route(*stops, full_geometry=True)
    d = {"pts": [tuple(p) for p in r["geometry"]], "w": w, "dash": dash,
         "km": r["km"], "min": r["min"]}
    if color:
        d["color"] = color
    return d


def render(bbox, z, out, routes=(), markers=(), scale_labels=True):
    """bbox=(lat_top, lon_left, lat_bot, lon_right)"""
    x0, y0 = ll2px(bbox[0], bbox[1], z)
    x1, y1 = ll2px(bbox[2], bbox[3], z)
    tx0, ty0, tx1, ty1 = int(x0 // 256), int(y0 // 256), int(x1 // 256), int(y1 // 256)
    W, H = (tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256
    img = Image.new("RGB", (W, H), "#ddd")
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            try:
                img.paste(get_tile(z, tx, ty), ((tx - tx0) * 256, (ty - ty0) * 256))
            except Exception as e:
                print("tile fail", z, tx, ty, e)
    ox, oy = tx0 * 256, ty0 * 256
    dr = ImageDraw.Draw(img, "RGBA")

    def pt(lat, lon):
        x, y = ll2px(lat, lon, z)
        return x - ox, y - oy

    for route in routes:
        col = route.get("color", (30, 92, 63, 230))
        pts = [pt(a, b) for a, b in route["pts"]]
        if route.get("dash"):
            # Walk the polyline by arc length so the dash pattern stays even
            # regardless of how densely the router sampled the road.
            on, off, w = 13.0, 9.0, route.get("w", 5)
            travelled, drawing, pen = 0.0, True, pts[0]
            for i in range(len(pts) - 1):
                (xa, ya), (xb, yb) = pts[i], pts[i + 1]
                seg = math.hypot(xb - xa, yb - ya)
                pos = 0.0
                while pos < seg:
                    need = (on if drawing else off) - travelled
                    step = min(need, seg - pos)
                    t1 = (pos + step) / seg
                    nxt = (xa + (xb - xa) * t1, ya + (yb - ya) * t1)
                    if drawing:
                        dr.line([pen, nxt], fill=col, width=w)
                    pen, pos, travelled = nxt, pos + step, travelled + step
                    if travelled >= (on if drawing else off) - 1e-9:
                        drawing, travelled = not drawing, 0.0
        else:
            dr.line(pts, fill=col, width=route.get("w", 6), joint="curve")

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
        font_s = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
    except Exception:
        font = font_s = ImageFont.load_default()

    for m in markers:
        x, y = pt(m["lat"], m["lon"])
        r = m.get("r", 21)
        col = m.get("color", (30, 92, 63, 255))
        dr.ellipse([x - r - 3, y - r - 3, x + r + 3, y + r + 3], fill=(255, 255, 255, 255))
        dr.ellipse([x - r, y - r, x + r, y + r], fill=col)
        label = str(m["n"])
        f = font if len(label) < 3 else font_s
        bb = dr.textbbox((0, 0), label, font=f)
        dr.text((x - (bb[2] - bb[0]) / 2 - bb[0], y - (bb[3] - bb[1]) / 2 - bb[1]), label, fill="white", font=f)

    # crop to bbox
    cx0, cy0 = pt(bbox[0], bbox[1])
    cx1, cy1 = pt(bbox[2], bbox[3])
    img = img.crop((int(cx0), int(cy0), int(cx1), int(cy1)))
    img.save(os.path.join(MAPS, out), quality=82)
    print(out, img.size, os.path.getsize(os.path.join(MAPS, out)) // 1024, "KB")

if __name__ == "__main__":
    GREEN = (30, 92, 63, 255); TEAL = (19, 107, 122, 255); RED = (166, 59, 34, 255); GOLD = (185, 138, 36, 235)

    # ---- 1. Thailand overview ----
    CM = (18.7883, 98.9853); CD = (19.3924, 98.9294); PAI = (19.3583, 98.4418); CR = (19.9105, 99.8406)
    KP = (9.7400, 100.0200); BKK = (13.7500, 100.4913); USM = (9.5479, 100.0623)
    render(
        bbox=(21.3, 96.6, 8.2, 103.4), z=7, out="map-thailand.jpg",
        routes=[
            {"pts": [BKK, (16.2, 99.6), CM], "color": GOLD, "dash": True, "w": 5},
            {"pts": [CM, (14.5, 99.6), USM], "color": GOLD, "dash": True, "w": 5},
            {"pts": [USM, KP], "color": TEAL, "w": 5},
            {"pts": [KP, USM, (11.5, 100.4), BKK], "color": GOLD, "dash": True, "w": 4},
        ],
        markers=[
            {"n": 1, "lat": CM[0], "lon": CM[1], "color": GREEN},
            {"n": 2, "lat": KP[0], "lon": KP[1], "color": TEAL},
            {"n": 3, "lat": BKK[0], "lon": BKK[1], "color": RED},
        ])

    # ---- 2. North Thailand: the loop we actually drive ----
    # Every line below follows the real road network. The numbered markers
    # match the order the family reaches them.
    from routing import PLACES
    P = lambda k: PLACES[k]
    FADE = (30, 92, 63, 165)
    NORTH_LEGS = [                        # (from, to, is_day_trip)
        ("airport", "city",        True),   # 19.9 landing
        ("city", "waterpark",      True),   # 20.9 water park & back
        ("city", "baankangwat",    False),  # 21.9 craft village…
        ("baankangwat", "chailai", False),  # …then the elephants
        ("chailai", "raya",        False),  # 23.9 down to the Ping
        ("raya", "buatong",        False),  # 24.9 sticky waterfall…
        ("buatong", "treehouse",   False),  # …then the tree house
        ("treehouse", "rafting",   False),  # 25.9 rafting…
        ("rafting", "raya",        False),  # …then back to the river
        ("raya", "airport",        True),   # 26.9 flight south
    ]
    legs = [road(a, b, color=(FADE if d else GREEN), w=(4 if d else 6), dash=d)
            for a, b, d in NORTH_LEGS]
    print("  north legs:", sum(len(l["pts"]) for l in legs), "real road points")
    render(
        bbox=(19.42, 98.52, 18.60, 99.22), z=10, out="map-north.jpg",
        routes=legs,
        markers=[
            {"n": 1, "lat": P("city")[0],        "lon": P("city")[1],        "color": GREEN},
            {"n": 2, "lat": P("waterpark")[0],   "lon": P("waterpark")[1],   "color": FADE[:3] + (255,)},
            {"n": 3, "lat": P("baankangwat")[0], "lon": P("baankangwat")[1], "color": FADE[:3] + (255,)},
            {"n": 4, "lat": P("chailai")[0],     "lon": P("chailai")[1],     "color": RED},
            {"n": 5, "lat": P("raya")[0],        "lon": P("raya")[1],        "color": RED},
            {"n": 6, "lat": P("buatong")[0],     "lon": P("buatong")[1],     "color": TEAL},
            {"n": 7, "lat": P("treehouse")[0],   "lon": P("treehouse")[1],   "color": RED},
            {"n": 8, "lat": P("rafting")[0],     "lon": P("rafting")[1],     "color": TEAL},
        ])

    # ---- 3. Koh Phangan ----
    TS = (9.7069, 99.9906); TNP = (9.7860, 100.0745); CHA = (9.7920, 100.0083)
    BOTTLE = (9.7995, 100.0405); KOMA = (9.7873, 99.9709); HR = (9.6742, 100.0688); PHAENG = (9.7482, 100.0201)
    render(
        bbox=(9.86, 99.93, 9.63, 100.13), z=13, out="map-phangan.jpg",
        routes=[{"pts": [TS, (9.72, 100.03), (9.755, 100.065), TNP], "color": TEAL, "w": 5}],
        markers=[
            {"n": 1, "lat": TS[0], "lon": TS[1], "color": TEAL},
            {"n": 2, "lat": TNP[0], "lon": TNP[1], "color": TEAL},
            {"n": 3, "lat": CHA[0], "lon": CHA[1], "color": TEAL},
            {"n": 4, "lat": BOTTLE[0], "lon": BOTTLE[1], "color": TEAL},
            {"n": 5, "lat": KOMA[0], "lon": KOMA[1], "color": TEAL},
            {"n": 6, "lat": PHAENG[0], "lon": PHAENG[1], "color": TEAL},
            {"n": 7, "lat": HR[0], "lon": HR[1], "color": (120, 120, 120, 255)},
        ])

    # ---- 4. Bangkok ----
    GP = (13.7500, 100.4913); WA = (13.7437, 100.4889); CHAT = (13.7999, 100.5504)
    ICON = (13.7263, 100.5100); ASIA = (13.7046, 100.5027); HOTEL = (13.7048, 100.5060); LUM = (13.7314, 100.5414)
    render(
        bbox=(13.83, 100.44, 13.68, 100.60), z=13, out="map-bangkok.jpg",
        markers=[
            {"n": 1, "lat": 13.7100, "lon": 100.5125, "color": RED},
            {"n": 2, "lat": GP[0], "lon": GP[1], "color": RED},
            {"n": 3, "lat": WA[0], "lon": WA[1], "color": RED},
            {"n": 4, "lat": ICON[0], "lon": ICON[1], "color": RED},
            {"n": 5, "lat": ASIA[0], "lon": ASIA[1], "color": RED},
            {"n": 6, "lat": CHAT[0], "lon": CHAT[1], "color": RED},
            {"n": 7, "lat": LUM[0], "lon": LUM[1], "color": RED},
        ])

    # ---- 5. Floating markets southwest ----
    MAEKLONG = (13.4067, 99.9986); DAMNOEN = (13.5209, 99.9550)
    render(
        bbox=(13.85, 99.75, 13.30, 100.65), z=10, out="map-markets.jpg",
        routes=[{"pts": [HOTEL, (13.65, 100.25), MAEKLONG, DAMNOEN], "color": RED, "w": 5, "dash": True}],
        markers=[
            {"n": 1, "lat": HOTEL[0], "lon": HOTEL[1], "color": RED},
            {"n": 2, "lat": MAEKLONG[0], "lon": MAEKLONG[1], "color": RED},
            {"n": 3, "lat": DAMNOEN[0], "lon": DAMNOEN[1], "color": RED},
        ])
    print("done")
