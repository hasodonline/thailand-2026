"""Google Maps deep links for every leg of the trip.

Why deep links instead of an embedded map:

  * The guide is one self-contained HTML file with every image inlined, so it
    opens with no signal — on the plane, up a mountain, on a ferry. An embedded
    map is a blank grey box the moment the data drops.
  * The site is public on GitHub Pages. A Maps JavaScript key in public HTML is
    a billable secret anyone can lift; referrer restrictions are the only guard
    and they are easy to spoof.
  * A deep link hands the job to the Google Maps app the family already has:
    live traffic, voice navigation, their downloaded offline maps, their
    account. It needs no API key and there is nothing to break.

Place IDs pin each link to the exact business rather than a fuzzy name search
(there are two "Chai Lai Orchid" entries in Google's own index). Place IDs are
the one field Google's terms explicitly permit storing indefinitely.
"""
import json
import os
import urllib.parse

D = os.path.dirname(os.path.abspath(__file__))
PIDS = json.load(open(os.path.join(D, "place_ids.json"), encoding="utf-8"))

BASE = "https://www.google.com/maps/dir/?api=1&travelmode=driving"


def _place(key):
    p = PIDS[key]
    return urllib.parse.quote(p["name"]), p["id"]


def nav(origin, destination, *waypoints):
    """Turn-by-turn link from origin to destination through any waypoints."""
    oq, oid = _place(origin)
    dq, did = _place(destination)
    url = f"{BASE}&origin={oq}&origin_place_id={oid}&destination={dq}&destination_place_id={did}"
    if waypoints:
        wq = "%7C".join(_place(w)[0] for w in waypoints)
        wid = "%7C".join(_place(w)[1] for w in waypoints)
        url += f"&waypoints={wq}&waypoint_place_ids={wid}"
    return url


def pin(key):
    """Link that just drops a pin on the place."""
    q, pid = _place(key)
    return f"https://www.google.com/maps/search/?api=1&query={q}&query_place_id={pid}"


if __name__ == "__main__":
    print("— ניווט לכל יום —")
    for label, args in [
        ("19.9  שדה → מלון",            ("airport", "waterpark")),
        ("21.9  עיר → כפר → פילים",     ("baankangwat", "chailai")),
        ("23.9  פילים → Raya",          ("chailai", "raya")),
        ("24.9  Raya → מפל → בית העץ",  ("raya", "treehouse", "buatong")),
        ("25.9  בית העץ → אומגה → Raya",("treehouse", "raya", "rafting")),
        ("26.9  Raya → שדה",            ("raya", "airport")),
    ]:
        print(f"\n{label}\n  {nav(*args)}")
