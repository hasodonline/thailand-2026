"""KML layers for Google My Maps: styled pins + the real driving routes.

Import these into a My Maps map and the guide gets a genuine, interactive
Google map — draggable, pins that open an info panel, layers the viewer can
switch on and off — with no API key in the public HTML and nothing billable.
The same map opens in the Google Maps app on a phone with every layer intact.

Two hard constraints from My Maps' importer shape this file:
  * <Folder> is NOT supported on import, so one KML cannot become several
    layers. Each layer is written as its OWN file and imported separately.
  * HTML info balloons are NOT supported either, so descriptions are plain
    text with newlines rather than markup.

Route lines are the actual road geometry from the router, simplified just
enough to keep each file small, so the map shows the road we really drive.
"""
import os
import xml.sax.saxutils as esc

from routing import PLACES, route, gleg

D = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(D), "maps", "kml")
os.makedirs(OUT_DIR, exist_ok=True)

# (key, day, title, description) — the pins, in the order we reach them
PINS = [
    ("city", "19–22.9", "🏨 המלון בעיר",
     "שלושה לילות. שוק ההליכה של שבת ושל ראשון במרחק הליכה. "
     "המזוודות הגדולות נשארות כאן גם בזמן שאתם אצל הפילים."),
    ("waterpark", "ראשון 20.9", "💦 פארק המים גרנד קניון",
     "מחצבה מוצפת בטורקיז: מסלול מכשולים מתנפח ענק, מגלשות מגובה 10 מ׳, "
     "קפיצות לצוק וקיאקים.\n⭐4.3 · 4,417 ביקורות · 10:00–19:00 · ~฿1,000–1,200 לאדם"),
    ("rafting", "שני 21.9 · בוקר", "🚣 8Adventures — ראפטינג",
     "מסלול 8 ק״מ, דרגה 2–3, מגיל 7. ספטמבר הוא שיא המים.\n"
     "⚠️ לא את מסלול 10 הק״מ — הוא דורש גיל 15.\n"
     "⭐4.8 · 491 ביקורות · לבקש את משבצת 10:00"),
    ("buatong", "שני 21.9 · אחה״צ", "💦 המפל הדביק (Bua Tong)",
     "הסלע מצופה מינרלים ולכן מחוספס — מטפסים במעלה המפל יחפים, "
     "שלוש קומות, עם חבלים בקטעים התלולים.\nכניסה חינם · 08:00–17:00 · "
     "50 דקות מהראפטינג, ולכן באותו יום"),
    ("baankangwat", "שלישי 22.9 · בוקר", "🎨 באן קאנג ואט — כפר האמנים",
     "סדנאות ובתי מלאכה: קדרות, צביעת בדים, עבודות עור, הדפס. "
     "מקום שעושים בו משהו בידיים, לא רק מסתכלים."),
    ("chailai", "22–24.9", "🐘 צ׳אי לאי אורכיד",
     "שני לילות עם הפילים. בקתות במבוק על הנהר, גשר עץ תלוי, "
     "והפילים באים למרפסת בארוחת הבוקר.\n"
     "✅ מוזמן ושולם · להגיע לפני 16:00 (שעת הפילים)"),
    ("hotsprings", "חמישי 24.9", "♨️ המעיינות החמים של סן קמפאנג",
     "גייזר טבעי של 20 מטר. קונים סלסלת ביצי שליו ומבשלים אותן "
     "בתעלות הרותחות. אמבטיות רגליים, בריכות מינרליות וגנים לפיקניק.\n"
     "⭐4.4 · 11,499 ביקורות · 07:00–18:00 · ฿100/฿50"),
    ("tharnthong", "24–26.9", "🏔️ הבקתות בעמק מאה און",
     "שני לילות בהרים. בקתות של 1–3 חדרי שינה.\n"
     "דקה אחת ממפל מאה קמפונג, שתיים מהכפר ההררי, 48 דקות מ-Skyline.\n"
     "⭐4.5 · 1,145 ביקורות"),
    ("mkwaterfall", "חמישי–שישי", "💦 מפל מאה קמפונג",
     "שביל שמטפס לאורך המפל בין העצים, עם תצפית על העמק. "
     "דקה מהבקתה — הולכים ברגל.\n⭐4.5 · 2,925 ביקורות"),
    ("skyline", "שישי 25.9", "🎢 Skyline Adventure",
     "28 קווי אומגה, כולל הארוך והגבוה בצ׳יאנג מאי. 38 פלטפורמות, "
     "נדנדות ענק, וקארט לוּגֶ׳ בסוף.\nמגיל 4 · ⭐4.8 · 1,291 ביקורות\n"
     "฿2,250–2,450 לאדם · 08:00–17:00"),
    ("airport", "שבת 26.9", "✈️ שדה התעופה צ׳יאנג מאי",
     "PG242 ממריאה 11:35 לקוסמוי. יוצאים מהבקתות ~09:00."),
]

# (stops, filename slug, layer name shown in My Maps, colour aabbggrr, width)
ROUTES = [
    (("city", "waterpark"), "sun-waterpark", "ראשון · פארק המים", "dd24a8b9", 4),
    (("city", "rafting", "buatong", "city"), "mon-rafting-waterfall", "שני · ראפטינג והמפל הדביק", "dd3f5c1e", 5),
    (("city", "baankangwat", "chailai"), "tue-elephants", "שלישי · אל הפילים", "dd223ba6", 5),
    (("chailai", "city", "hotsprings", "tharnthong"), "thu-hotsprings-mountains", "חמישי · אל עמק ההרים", "dda03f6b", 5),
    (("tharnthong", "skyline"), "fri-skyline", "שישי · Skyline", "dd7a6b13", 5),
    (("tharnthong", "airport"), "sat-airport", "שבת · לשדה התעופה", "99999999", 3),
]


def _simplify(pts, tol=0.0004):
    """Douglas-Peucker, so a 1,300-point road fits comfortably in an import.

    Closed loops need splitting first: when the first and last point coincide
    the baseline has zero length, every perpendicular distance computes as ~0,
    and the whole route collapses to two points. The Monday route (city → …
    → city) hit exactly that and imported as an invisible 2-point line.
    """
    if len(pts) < 3:
        return pts
    if abs(pts[0][0] - pts[-1][0]) < 1e-7 and abs(pts[0][1] - pts[-1][1]) < 1e-7:
        mid = len(pts) // 2
        return _simplify(pts[:mid + 1], tol)[:-1] + _simplify(pts[mid:], tol)
    (ax, ay), (bx, by) = pts[0], pts[-1]
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


def _write(name, inner, doc_name):
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
           f'<name>{esc.escape(doc_name)}</name>{inner}</Document></kml>')
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"  {name:34}{len(xml)//1024:>4} KB")
    return path


def build():
    print("שכבות ל-Google My Maps — כל קובץ מיובא בנפרד:\n")
    files = []

    # layer 1 — every place, as pins
    pins = []
    for key, day, title, desc in PINS:
        lat, lon = PLACES[key]
        body = f"{day}\n\n{desc}"
        pins.append(f'<Placemark><name>{esc.escape(title)}</name>'
                    f'<description>{esc.escape(body)}</description>'
                    f'<Point><coordinates>{lon},{lat},0</coordinates></Point></Placemark>')
    files.append(_write("00-places.kml", "".join(pins), "המקומות"))

    # one file per route, so each becomes its own switchable layer
    for n, (stops, slug_name, name, colour, width) in enumerate(ROUTES, 1):
        r = route(*stops, full_geometry=True)
        pts = _simplify([(la, lo) for la, lo in r["geometry"]])
        coords = " ".join(f"{lo},{la},0" for la, lo in pts)
        mins = sum(gleg(stops[i], stops[i + 1])[1] for i in range(len(stops) - 1))
        label = f"{name} — {r['km']:.0f} ק\u05f4מ · {mins} דק\u05f3"
        inner = (f'<Placemark><name>{esc.escape(label)}</name>'
                 f'<Style><LineStyle><color>{colour}</color>'
                 f'<width>{width}</width></LineStyle></Style>'
                 f'<LineString><tessellate>1</tessellate>'
                 f'<coordinates>{coords}</coordinates></LineString></Placemark>')
        slug = f"{n:02d}-{slug_name}.kml"
        files.append(_write(slug, inner, name))
    print(f"\n  {len(files)} קבצים ב-maps/kml/ · מייבאים אותם ל-My Maps אחד אחרי השני")
    return files


if __name__ == "__main__":
    build()
