"""Build the trip book.

The guide used to be one 3.9 MB file with every photo and map inlined as
base64, because it had to survive a Thai mountain road with no signal. That
requirement is gone — the family prints it — so this build does the opposite:
small HTML, real asset files, live Google maps.

Two outputs, same assets:
  docs/index.html    public. Booking references are masked; the only key in it
                     is the referrer-locked Maps key.
  docs/private.html  gitignored. Real references, for the phone and the printer.

Maps come in three flavours, all Google:
  {{GMAP:overview|cap}}        the rich JS map — real route polylines, own pins
  {{GMAP:dir|a>b>c|cap}}       Embed API directions, one per day
  {{GMAP:q|query|cap}}         Embed API place
Embed API is free and unmetered, so per-day maps cost nothing and don't eat
the 300/day quota that guards the JS map.
"""
import base64
import json
import os
import re
import shutil
import sys

D = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(D)
OUT = os.path.join(ROOT, "docs")
ASSETS = os.path.join(OUT, "assets")

PUBLIC = "--public" in sys.argv
WEB_KEY = open(os.path.join(D, ".web-map-key")).read().strip()

missing = []


# ---------------------------------------------------------------- assets
def copy_asset(src, name):
    os.makedirs(ASSETS, exist_ok=True)
    dst = os.path.join(ASSETS, name)
    if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
        shutil.copy2(src, dst)
    return "assets/" + name


def repl_img(m):
    slug = m.group(1)
    src = os.path.join(ROOT, "photos", f"c_{slug}.jpg")
    if not os.path.exists(src):
        missing.append(f"photo:{slug}")
        return ""
    return copy_asset(src, f"{slug}.jpg")


# ---------------------------------------------------------------- maps
def embed(url, caption, printable=None):
    """One map card: a lazy iframe on screen, a still image on paper."""
    still = (f'<img class="printmap" src="{printable}" alt="{caption}">'
             if printable else "")
    return (f'<div class="mapbox"><iframe data-src="{url}" loading="lazy" '
            f'referrerpolicy="no-referrer-when-downgrade" allowfullscreen '
            f'title="{caption}"></iframe>{still}'
            f'<div class="cap">🗺️ {caption}</div></div>')


def print_map(keys):
    """A still Google map of one day's route, for the printed book.

    The live iframe is blank on paper, and a trip book that loses its maps
    when you print it defeats the point. Generated once and cached in
    maps/ — regenerating costs a Static Maps call per route per build.
    """
    slug = "route-" + "-".join(keys)
    cached = os.path.join(ROOT, "maps", slug + ".jpg")
    if not os.path.exists(cached):
        try:
            import google_maps
            r = google_maps.polyline(*keys, quality="OVERVIEW")
            marks = []
            for i, k in enumerate(keys):
                lat, lon = routing.PLACES[k]
                marks.append({"lat": lat, "lon": lon, "color": "0x1e5c3f",
                              "label": str(i + 1)})
            google_maps.static_map(slug + ".png", size="640x420",
                                   paths=[{"enc": r["enc"], "color": "0x1e5c3fcc", "w": 5}],
                                   markers=marks)
        except Exception as e:                      # a missing map beats a failed build
            print(f"  ⚠️  אין מפת הדפסה ל-{slug}: {str(e)[:70]}")
            return None
    return copy_asset(cached, slug + ".jpg") if os.path.exists(cached) else None


def repl_gmap(m):
    kind, body = m.group(1), m.group(2)
    if kind == "overview":
        wm = os.path.join(D, "webmap.html")
        cap = body
        if not os.path.exists(wm):
            missing.append("webmap.html")
            return ""
        still = os.path.join(ROOT, "maps", "map-north-google.jpg")
        img = (f'<img class="printmap" src="{copy_asset(still, "map-north-google.jpg")}" '
               f'alt="{cap}">' if os.path.exists(still) else "")
        return (f'<div class="wide overviewmap">{open(wm, encoding="utf-8").read()}{img}'
                f'<p class="cap" style="font-size:14.5px;color:var(--ink-faint);'
                f'padding:0 4px 6px">🗺️ {cap} — לחצו על סיכה לפרטים, '
                f'ועל שם מסלול כדי להסתיר אותו</p></div>')

    spec, _, cap = body.partition("|")
    if kind == "dir":
        keys = [k.strip() for k in spec.split(">")]
        try:
            ids = [PIDS[k]["id"] for k in keys]
        except KeyError as e:
            missing.append(f"place_id:{e}")
            return ""
        url = (f"https://www.google.com/maps/embed/v1/directions?key={WEB_KEY}"
               f"&origin=place_id:{ids[0]}&destination=place_id:{ids[-1]}")
        if len(ids) > 2:
            url += "&waypoints=" + "%7C".join("place_id:" + i for i in ids[1:-1])
        url += "&mode=driving&region=TH&language=iw"
        return embed(url, cap, print_map(keys))
    if kind == "q":
        from urllib.parse import quote
        url = (f"https://www.google.com/maps/embed/v1/place?key={WEB_KEY}"
               f"&q={quote(spec)}&zoom=12&region=TH&language=iw")
        return embed(url, cap)
    missing.append(f"gmap:{kind}")
    return ""


# ---------------------------------------------------------------- nav links
NAV_SETS = {
    "north": [("chailai", "🐘 צ׳אי לאי"), ("woomacamoo", "🏘️ Woo Ma Ca Moo"),
              ("skyline", "🎢 Skyline"), ("rafting", "🚣 ראפטינג"),
              ("buatong", "💦 המפל הדביק"), ("waterpark", "💦 פארק המים"),
              ("hotsprings", "♨️ המעיינות"), ("maekampong", "🏘️ הכפר ההררי"),
              ("mkwaterfall", "💦 מפל הכפר"), ("baankangwat", "🎨 כפר האמנים"),
              ("airport", "✈️ שדה צ׳יאנג מאי")],
}


def repl_shots(m):
    """{{SHOTS:slug|alt}} — the photo strip at the top of a lodging card."""
    slug, _, alt = m.group(1).partition("|")
    srcs = []
    for i in range(1, 7):
        p = os.path.join(ROOT, "photos", f"c_h-{slug}-{i}.jpg")
        if os.path.exists(p):
            srcs.append(copy_asset(p, f"h-{slug}-{i}.jpg"))
    if not srcs:
        missing.append(f"shots:{slug}")
        return ""
    cells = "".join(
        f'<button type="button"><img src="{s}" alt="{alt} — תמונה {i + 1}" '
        f'loading="lazy"><span class="cap" hidden>{alt}</span></button>'
        for i, s in enumerate(srcs))
    return f'<div class="stayshots">{cells}</div>'


def repl_navlinks(m):
    keys = NAV_SETS.get(m.group(1))
    if not keys:
        return ""
    out = ['<div class="wrap"><p style="font-size:15px;color:var(--ink-faint);'
           'margin:34px 0 8px">🧭 <strong>ניווט בלחיצה</strong> — נפתח '
           'באפליקציית Google Maps עם תנועה חיה</p><div class="navlinks">']
    for k, label in keys:
        if k in PIDS:
            out.append(f'<a href="{navlinks.pin(k)}" target="_blank" '
                       f'rel="noopener">{label}</a>')
    out.append("</div></div>")
    return "".join(out)


# ---------------------------------------------------------------- day nav
DAYS = [
    ("d-0917", "17.9", "ה׳"), ("d-0918", "18.9", "ו׳"), ("d-0919", "19.9", "ש׳"),
    ("d-0920", "20.9", "א׳"), ("d-0921", "21.9", "ב׳"), ("d-0922", "22.9", "ג׳"),
    ("d-0923", "23.9", "ד׳"), ("d-0924", "24.9", "ה׳"), ("d-0925", "25.9", "ו׳"),
    ("d-0926n", "26.9", "ש׳"), ("d-0927", "27–30.9", ""), ("d-1001", "1.10", "ה׳"),
    ("d-1002", "2.10", "ו׳"), ("d-1003", "3.10", "ש׳"), ("d-1004", "4.10", "א׳"),
    ("d-1005", "5.10", "ב׳"), ("d-1006", "6.10", "ג׳"),
]


def daynav():
    links = "".join(
        f'<a href="#{i}">{d}{f"<span class=d>{w}</span>" if w else ""}</a>'
        for i, d, w in DAYS)
    return f'<nav class="daynav" aria-label="ימי הטיול"><div class="track">{links}</div></nav>'


# ---------------------------------------------------------------- build
sys.path.insert(0, D)
import navlinks                                    # noqa: E402
import routing                                     # noqa: E402
from navlinks import PIDS                          # noqa: E402

html = ""
for part in ["part1.html", "part2.html", "part3.html"]:
    with open(os.path.join(D, part), encoding="utf-8") as f:
        html += f.read() + "\n"

refs = {}
refs_path = os.path.join(D, "private-refs.json")
if os.path.exists(refs_path) and not PUBLIC:
    refs = json.load(open(refs_path, encoding="utf-8"))

html = re.sub(r"\{\{IMG:([a-z0-9-]+)\}\}", repl_img, html)
html = re.sub(r"\{\{GMAP:([a-z]+)\|(.*?)\}\}", repl_gmap, html)
html = re.sub(r"\{\{SHOTS:([^}]+)\}\}", repl_shots, html)
html = re.sub(r"\{\{NAVLINKS:([a-z]+)\}\}", repl_navlinks, html)
html = re.sub(r"\{\{REF:([a-z0-9]+)\}\}", lambda m: refs.get(m.group(1), "••••••"), html)
html = html.replace("{{DAYNAV}}", daynav())

left = re.findall(r"\{\{[^}]{1,60}\}\}", html)
if left:                       # a typo'd placeholder must never reach the page
    missing.extend("unreplaced:" + x for x in sorted(set(left)))
if missing:
    print("MISSING:", sorted(set(missing)))
    sys.exit(1)

css = open(os.path.join(D, "style.css"), encoding="utf-8").read()
js = open(os.path.join(D, "app.js"), encoding="utf-8").read()

doc = f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>תאילנד 2026 · ספר הטיול</title>
<meta name="description" content="ספר הטיול המשפחתי לתאילנד, 17.9–6.10.2026 — צפון, קופנגן ובנגקוק.">
<meta name="theme-color" content="#1E5C3F">
<style>{css}</style>
</head>
<body>
{html}
<dialog class="lb"><button class="x" aria-label="סגירה">✕</button><img alt=""><p class="cap"></p></dialog>
<button class="themetoggle" type="button" aria-label="החלפת ערכת צבעים">◐</button>
<script>{js}</script>
</body>
</html>
"""

os.makedirs(OUT, exist_ok=True)
name = "index.html" if PUBLIC else "private.html"
path = os.path.join(OUT, name)
with open(path, "w", encoding="utf-8") as f:
    f.write(doc)

n_assets = len(os.listdir(ASSETS)) if os.path.isdir(ASSETS) else 0
print(f"  {'PUBLIC ' if PUBLIC else 'private'} docs/{name}  "
      f"{len(doc) / 1024:.0f} KB  ·  {n_assets} קבצי נכסים  ·  "
      f"{len(re.findall(r'class=.mapbox', doc))} מפות embed  ·  "
      f"{len(re.findall(r'<article class=.day', doc))} ימים")
