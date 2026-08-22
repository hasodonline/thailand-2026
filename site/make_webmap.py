"""Interactive Google map for the guide, built from Google's own data.

Accuracy is the whole point of this module. Two things make it exact:

  * Route lines are Google's HIGH_QUALITY polylines, embedded verbatim. The
    static JPEG had to squeeze each line under the Static Maps URL limit, so
    it shipped a Douglas-Peucker approximation (~22 m off). JavaScript has no
    such limit, so nothing is simplified here — this is the road Google itself
    would navigate.
  * Pins are anchored to Google place IDs, so clicking one opens the real
    listing rather than a coordinate we typed in.

Markers use AdvancedMarkerElement, which needs a Map ID registered in Cloud
console — without one it renders nothing and logs no error, which is exactly
how the first attempt failed. The ID lives in .map-id.

Cost is bounded, not hoped for. The key is restricted to this site's referrer
and to Maps JS alone, and the project carries a hard 300 map-loads/day quota —
9,300/month against a 10,000 free allowance, so overspend is arithmetically
impossible even if the key is copied out of the page source.

The static map stays in the guide above this one: it is embedded as base64 and
keeps working with no signal, which is the situation this family will actually
be in on a mountain road.
"""
import json
import os

from google_maps import polyline
from navlinks import PIDS
from routing import PLACES

D = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.path.join(D, ".web-map-key")).read().strip()
MAP_ID = open(os.path.join(D, ".map-id")).read().strip()

# (place key, colour, title, subtitle) — colour groups sleeps vs activities
PINS = [
    ("city",        "#a63b22", "🏨 המלון בעיר",              "לילות 19–22 · שווקי ההליכה בהליכה"),
    ("waterpark",   "#136b7a", "💦 פארק המים גרנד קניון",     "ראשון 20.9 · ⭐4.3 (4,417)"),
    ("rafting",     "#1e5c3f", "🚣 8Adventures — ראפטינג",    "שני 21.9 · מסלול 8 ק״מ, מגיל 7"),
    ("buatong",     "#1e5c3f", "💦 המפל הדביק",               "שני 21.9 · מטפסים יחפים · חינם"),
    ("baankangwat", "#b98a24", "🎨 כפר האמנים",               "שלישי 22.9 · סדנאות"),
    ("chailai",     "#a63b22", "🐘 צ׳אי לאי אורכיד",          "לילות 22–24 · הפילים ✅ שולם"),
    ("hotsprings",  "#6b3fa0", "♨️ המעיינות החמים",           "חמישי 24.9 · גייזר 20 מ׳"),
    ("woomacamoo",  "#a63b22", "🏘️ Woo Ma Ca Moo",            "לילות 24–26 ✅ שולם · ⭐4.8 · 8 דק׳ הליכה למסעדה"),
    ("maekampong",  "#6b3fa0", "🏘️ כפר מאה קמפונג",          "הדוכנים · נסגרים ב-17:00 · ⭐4.5 (6,034)"),
    ("mkwaterfall", "#6b3fa0", "💦 מפל מאה קמפונג",           "50 דק׳ הליכה / 8 דק׳ ברכב מהבקתות"),
    ("skyline",     "#136b7a", "🎢 Skyline Adventure",        "שישי 25.9 · 28 קווי אומגה"),
    ("airport",     "#666666", "✈️ שדה התעופה",               "שבת 26.9 · PG242 ב-11:35"),
]

ROUTES = [
    (("city", "waterpark"),                            "ראשון · פארק המים",        "#b98a24", 4),
    (("city", "rafting", "buatong", "city"),           "שני · ראפטינג והמפל",      "#1e5c3f", 5),
    (("city", "baankangwat", "chailai"),               "שלישי · אל הפילים",        "#a63b22", 5),
    (("chailai", "city", "hotsprings", "woomacamoo"),  "חמישי · אל עמק ההרים",     "#6b3fa0", 5),
    (("woomacamoo", "skyline"),                        "שישי · Skyline",           "#136b7a", 5),
    (("woomacamoo", "airport"),                        "שבת · לשדה התעופה",        "#999999", 4),
]


def build():
    pins = []
    for key, colour, title, sub in PINS:
        lat, lon = PLACES[key]
        icon, _, label = title.partition(" ")
        pins.append({"lat": lat, "lng": lon, "color": colour, "title": label,
                     "icon": icon, "sub": sub,
                     "pid": PIDS.get(key, {}).get("id", "")})

    routes = []
    for stops, name, colour, weight in ROUTES:
        r = polyline(*stops, quality="HIGH_QUALITY")
        routes.append({"enc": r["enc"], "name": name, "color": colour,
                       "weight": weight, "km": round(r["km"]), "min": r["min"]})

    data = json.dumps({"pins": pins, "routes": routes}, ensure_ascii=False)
    html = f'''<div class="livemap">
  <div id="tmap"></div>
  <div id="tlegend" class="maplegend"></div>
</div>
<script>
(function(){{
  const D = {data};
  window.initTMap = function(){{
    const map = new google.maps.Map(document.getElementById('tmap'), {{
      center: {{lat: 18.94, lng: 98.99}}, zoom: 10, mapId: '{MAP_ID}',
      mapTypeControl: false, streetViewControl: false, fullscreenControl: true
    }});
    const info = new google.maps.InfoWindow();
    const {{ AdvancedMarkerElement }} = google.maps.marker;
    D.pins.forEach(p => {{
      const dot = document.createElement('div');
      dot.className = 'tpin';
      dot.style.background = p.color;
      dot.textContent = p.icon;
      const mk = new AdvancedMarkerElement({{
        map, position: {{lat: p.lat, lng: p.lng}}, title: p.title, content: dot
      }});
      mk.addListener('gmp-click', () => {{
        const link = p.pid
          ? '<a href="https://www.google.com/maps/search/?api=1&query=' + p.lat + ',' + p.lng +
            '&query_place_id=' + p.pid + '" target="_blank" rel="noopener">פתח במפות Google ←</a>'
          : '';
        info.setContent('<div class="tinfo"><b>' + p.icon + ' ' + p.title + '</b><br>' + p.sub + '<br>' + link + '</div>');
        info.open(map, mk);
      }});
    }});
    const legend = document.getElementById('tlegend');
    D.routes.forEach(r => {{
      const path = google.maps.geometry.encoding.decodePath(r.enc);
      const line = new google.maps.Polyline({{
        path, map, strokeColor: r.color, strokeOpacity: 0.85, strokeWeight: r.weight
      }});
      const chip = document.createElement('button');
      chip.className = 'mapchip';
      chip.innerHTML = '<i style="background:' + r.color + '"></i>' + r.name +
                       ' <span>' + r.km + ' ק״מ · ' + r.min + ' דק׳</span>';
      chip.onclick = () => {{
        const on = line.getMap() !== null;
        line.setMap(on ? null : map);
        chip.classList.toggle('off', on);
      }};
      legend.appendChild(chip);
    }});
  }};
}})();
</script>
<script async
  src="https://maps.googleapis.com/maps/api/js?key={KEY}&libraries=marker,geometry&callback=initTMap&loading=async&language=iw&region=TH"></script>'''
    out = os.path.join(D, "webmap.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    pts = sum(len(r["enc"]) for r in routes)
    print(f"  webmap.html  {len(html) // 1024} KB · {len(pins)} סיכות · "
          f"{len(routes)} מסלולים · {pts:,} תווי גאומטריה (ללא פישוט)")
    return out


if __name__ == "__main__":
    build()
