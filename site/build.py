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
mid_path = os.path.join(d, "mymaps-id.txt")
mid = open(mid_path).read().strip() if os.path.exists(mid_path) else ""
if mid:
    embed = (
        '<p>מפה אמיתית של Google: אפשר לגרור, לזום, ללחוץ על כל סיכה לפרטים, '
        '<strong>ולכבות ולהדליק שכבות</strong> של כל יום.</p>'
        '<div style="position:relative;width:100%;padding-bottom:72%;'
        'border-radius:14px;overflow:hidden;margin:14px 0">'
        f'<iframe src="https://www.google.com/maps/d/embed?mid={mid}&ehbc=2E312F" '
        'style="position:absolute;inset:0;width:100%;height:100%;border:0" '
        'loading="lazy" allowfullscreen></iframe></div>'
        f'<p>📱 <a href="https://www.google.com/maps/d/viewer?mid={mid}" '
        'target="_blank" rel="noopener"><strong>פתחו במפות Google בטלפון</strong></a> — '
        'המפה נשמרת אצלכם תחת "שמורים ← מפות", עם כל הסיכות והשכבות, '
        'ואפשר לקבל ניווט לכל נקודה.</p>')
else:
    embed = ('<p>קובצי השכבות מוכנים ב-<code>docs/kml/</code>. '
             'מייבאים אותם ל-Google My Maps (קובץ אחד לכל שכבה), '
             'ואז מדביקים את מזהה המפה ב-<code>site/mymaps-id.txt</code> '
             'והמפה החיה תופיע כאן אוטומטית בבנייה הבאה.</p>')
out = out.replace("{{MYMAPS}}", embed)

if PUBLIC:
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)
    outpath = os.path.join(root, "docs", "index.html")
else:
    outpath = os.path.join(root, "thailand-2026-guide.html")
with open(outpath, "w", encoding="utf-8") as f:
    f.write(out)
print(("PUBLIC " if PUBLIC else "private ") + outpath.split("/")[-1], round(len(out)/1e6,2), "MB")
