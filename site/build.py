import base64, json, os, re, sys

d = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(d)   # project folder: photos/, maps/ and the final HTML live here
html = ""
for part in ["part1.html", "part2.html", "part3.html"]:
    with open(os.path.join(d, part), encoding="utf-8") as f:
        html += f.read() + "\n"

missing = []
def repl(m):
    slug = m.group(1)
    p = os.path.join(root, "photos", f"c_{slug}.jpg")
    if not os.path.exists(p):
        missing.append(slug)
        return ""
    with open(p, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/jpeg;base64,{b64}"

out = re.sub(r"\{\{IMG:([a-z0-9-]+)\}\}", repl, html)

def repl_map(m):
    slug = m.group(1)
    p = os.path.join(root, "maps", f"{slug}.jpg")
    if not os.path.exists(p):
        missing.append(slug)
        return ""
    with open(p, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/jpeg;base64,{b64}"

out = re.sub(r"\{\{MAP:([a-z0-9-]+)\}\}", repl_map, out)

# --- booking references -------------------------------------------------
# Real codes live in site/private-refs.json, which is gitignored. A booking
# reference plus a surname is enough to change or cancel a reservation, so the
# public build masks them instead.
PUBLIC = "--public" in sys.argv
refs_path = os.path.join(d, "private-refs.json")
refs = {}
if os.path.exists(refs_path) and not PUBLIC:
    refs = json.load(open(refs_path, encoding="utf-8"))

def repl_ref(m):
    return refs.get(m.group(1), "••••••")

out = re.sub(r"\{\{REF:([a-z]+)\}\}", repl_ref, out)
out = out.replace("{{FAM}}", refs.get("_FAM", "משפחה ישראלית"))
out = out.replace("{{FAM2}}", refs.get("_FAM2", "המזמין"))

if missing:
    print("MISSING:", missing); sys.exit(1)


# The interactive Google My Maps embed. Drop the map id into site/mymaps-id.txt
# and every build swaps the placeholder for a live, responsive iframe; until
# then the guide shows how to create it. The static JPEG above always stays —
# it is what works with no signal.
# The interactive map. Built by make_webmap.py from Google's own HIGH_QUALITY
# route geometry — no simplification, unlike the static JPEG which had to fit
# inside a URL. The key it carries is referrer-locked to this site, restricted
# to Maps JS alone, and capped at 300 loads/day against a 10,000/month free
# allowance, so it cannot run up a bill even if lifted from the page source.
wm_path = os.path.join(d, "webmap.html")
if os.path.exists(wm_path):
    embed = ('<p>מפת Google אמיתית עם <strong>המסלולים המקוריים שלה</strong>, בלי קירוב. '
             'אפשר לגרור, לזום, ללחוץ על סיכה לפרטים, '
             'ו<strong>לכבות ולהדליק כל יום</strong> בכפתורים שמתחת.</p>'
             + open(wm_path, encoding="utf-8").read())
else:
    embed = '<p>המפה האינטראקטיבית תיבנה בהרצה הבאה של make_webmap.py.</p>'
out = out.replace("{{MYMAPS}}", embed)

if PUBLIC:
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)
    outpath = os.path.join(root, "docs", "index.html")
else:
    outpath = os.path.join(root, "thailand-2026-guide.html")
with open(outpath, "w", encoding="utf-8") as f:
    f.write(out)
print(("PUBLIC " if PUBLIC else "private ") + outpath.split("/")[-1], round(len(out)/1e6,2), "MB")
