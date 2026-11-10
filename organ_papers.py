"""Shared helpers: parse PubMed MEDLINE text, store papers in JSON, render the HTML page.
Standard library only."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data" / "papers.json"
OUT_FILE = ROOT / "docs" / "index.html"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

TITLE = "Selected Victorian Scientific Papers on Organ Donation"


# ---------- parsing MEDLINE-format text ----------

def split_records(text):
    return [r for r in re.split(r"\n\s*\n(?=PMID- )", text.strip()) if r.strip()]


def parse_fields(rec):
    d, key = {}, None
    for line in rec.split("\n"):
        m = re.match(r"^([A-Z]{2,4})\s*- (.*)$", line)
        if m:
            key = m.group(1)
            d.setdefault(key, []).append(m.group(2))
        elif key and line.startswith("      "):
            d[key][-1] += " " + line.strip()
    return d


def to_paper(rec):
    """Turn one MEDLINE record into the dict we store."""
    d = parse_fields(rec)
    authors = d.get("AU", [])
    auth = ", ".join(authors[:6]) + (", et al" if len(authors) > 6 else "")
    dp = d["DP"][0]
    dep = d.get("DEP", [""])[0]
    if len(dp.split()) == 1 and dep[:4] == dp and len(dep) == 8:   # year only -> use e-pub date
        dp = "%s %s %d" % (dp, MONTHS[int(dep[4:6]) - 1], int(dep[6:8]))
    parts = dp.split()
    month = MONTHS.index(parts[1][:3]) + 1 if len(parts) > 1 and parts[1][:3] in MONTHS else 0
    day = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    doi, other_lid = "", ""
    for l in d.get("LID", []):
        if l.endswith("[doi]"):
            doi = l.replace("[doi]", "").strip()
        elif not l.endswith("[pii]"):
            other_lid = l.strip()
    pg = d.get("PG", [""])[0] or other_lid
    loc = dp
    vi, ip = d.get("VI", [""])[0], d.get("IP", [""])[0]
    if vi:
        loc += ";" + vi + ("(%s)" % ip if ip else "")
    if pg:
        loc += ":" + pg
    return {
        "pmid": d["PMID"][0].strip(),
        "title": d["TI"][0].strip().rstrip("."),
        "authors": auth,
        "journal": d["TA"][0],
        "loc": loc,
        "doi": doi,
        "abstract": d.get("AB", [""])[0],
        "sort": "%04d-%02d-%02d" % (int(parts[0]), month, day),
        "edat": d.get("EDAT", [""])[0],
    }


# ---------- storage ----------

def load():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return {"last_run": "", "papers": []}


def save(db):
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(db, indent=1, ensure_ascii=False), encoding="utf-8")


# ---------- rendering ----------

SECTION = re.compile(
    r"(?<![A-Za-z])((?:[A-Z]{4,}(?: [A-Z]+){0,5})|"
    r"(?:Background|Objectives?|Methods|Results|Conclusions?)):\s")


def abstract_html(ab):
    if not ab:
        return '<p class="noabs">No abstract is available for this record in PubMed.</p>'
    parts = SECTION.split(ab)
    if len(parts) == 1:
        return "<p>%s</p>" % html.escape(ab)
    out = []
    if parts[0].strip():
        out.append("<p>%s</p>" % html.escape(parts[0].strip()))
    for i in range(1, len(parts), 2):
        lab = parts[i].strip()
        lab = lab.capitalize() if lab.isupper() else lab
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        out.append("<p><strong>%s:</strong> %s</p>" % (html.escape(lab), html.escape(body)))
    return "\n".join(out)


def item_html(p):
    ref = "%s. <strong>%s.</strong> %s. %s." % (
        html.escape(p["authors"]), html.escape(p["title"]),
        html.escape(p["journal"]), html.escape(p["loc"]))
    if p["doi"]:
        ref += " doi:%s" % html.escape(p["doi"])
    links = ('<a href="https://pubmed.ncbi.nlm.nih.gov/%s/" target="_blank" rel="noopener">PubMed Link</a>'
             % p["pmid"])
    if p["doi"]:
        links += (' <span class="sep">|</span> <a href="https://doi.org/%s" target="_blank" '
                  'rel="noopener">DOI Hyperlink</a>' % html.escape(p["doi"], quote=True))
    links += ' <span class="sep">|</span> <span class="pmid">PMID %s</span>' % p["pmid"]
    return ('<li>\n<p class="ref">%s</p>\n<p class="links">%s</p>\n'
            '<details><summary>Abstract</summary><div class="abs">\n%s\n</div></details>\n</li>'
            % (ref, links, abstract_html(p["abstract"])))


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { --bg:#fff; --fg:#1d2330; --muted:#5f6878; --line:#dde1e8; --link:#0b5cad; --card:#f6f8fb; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#14171d; --fg:#e4e7ee; --muted:#9aa3b2; --line:#2b313c; --link:#7db7f2; --card:#1b2029; }
  }
  body { margin:0; background:var(--bg); color:var(--fg);
         font:16px/1.55 Georgia, "Times New Roman", serif; }
  main { max-width: 860px; margin: 0 auto; padding: 32px 16px 64px; }
  h1 { font-size: 1.9rem; line-height: 1.25; margin: 0 0 8px; }
  .note { font-size: 0.78rem; color: var(--muted); font-family: system-ui, sans-serif;
          border-bottom: 1px solid var(--line); padding-bottom: 16px; margin-bottom: 8px; }
  .note p { margin: 4px 0; }
  kbd { font: inherit; font-family: ui-monospace, monospace; border:1px solid var(--line);
        border-radius:3px; padding:0 4px; background:var(--card); }
  ol { padding-left: 2.2em; }
  li { padding: 14px 0; border-bottom: 1px solid var(--line); }
  .ref { margin: 0 0 4px; }
  .links { margin: 0 0 6px; font-family: system-ui, sans-serif; font-size: 0.88rem; }
  .links a { color: var(--link); }
  .sep, .pmid { color: var(--muted); }
  details { font-family: system-ui, sans-serif; font-size: 0.9rem; }
  summary { cursor: pointer; color: var(--link); display: inline-block; }
  .abs { background: var(--card); border-left: 3px solid var(--line);
         padding: 4px 14px; margin-top: 6px; }
  .abs p { margin: 8px 0; }
  .noabs { color: var(--muted); font-style: italic; }
</style>
</head>
<body>
<main>
<h1>__TITLE__</h1>
<div class="note">
<p>Note: this is not meant to be a comprehensive list. It is an AI-assisted list that updates automatically each month from PubMed searches, so it does not claim to be completely inclusive. It may also include studies that are adjacent to organ donation or that are national rather than Victorian in scope.</p>
<p>To search this page: press <kbd>Ctrl</kbd>+<kbd>F</kbd> (Windows/Linux) or <kbd>&#8984;</kbd>+<kbd>F</kbd> (Mac), type your term, then <kbd>Enter</kbd> for the next match and <kbd>Shift</kbd>+<kbd>Enter</kbd> for the previous one; <kbd>Esc</kbd> closes the search. On a phone or tablet, use &ldquo;Find in page&rdquo; in the browser menu. Most browsers will also search inside collapsed abstracts.</p>
__UPDATED__</div>
<ol>
__ITEMS__
</ol>
</main>
</body>
</html>
"""


def render(db):
    papers = sorted(db["papers"], key=lambda p: (p["sort"], p.get("edat", "")), reverse=True)
    updated = ""
    if db.get("last_run"):
        updated = "<p>List last updated: %s. It is refreshed monthly from PubMed.</p>\n" % db["last_run"]
    page = (PAGE.replace("__TITLE__", TITLE)
                .replace("__UPDATED__", updated)
                .replace("__ITEMS__", "\n".join(item_html(p) for p in papers)))
    OUT_FILE.parent.mkdir(exist_ok=True)
    OUT_FILE.write_text(page, encoding="utf-8")
    return len(papers)
