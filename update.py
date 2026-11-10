"""Monthly updater: find papers indexed in PubMed since the last run, append new ones, re-render.

Query (Reading 1):
  ("DonateLife"[All Fields] AND "Victoria"[All Fields])
  OR ("organ donation"[All Fields] AND "redcrossblood.org.au"[Affiliation])

Usage:  python update.py            (uses NCBI_API_KEY / NCBI_EMAIL env vars if set)
        python update.py --dry-run  (show what would be added, change nothing)
Standard library only.
"""
import os
import sys
import time
import datetime
import urllib.parse
import urllib.request

import organ_papers as op

QUERY = ('("DonateLife"[All Fields] AND "Victoria"[All Fields]) '
         'OR ("organ donation"[All Fields] AND "redcrossblood.org.au"[Affiliation])')
BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
OVERLAP_DAYS = 7          # re-check a week before last run; duplicates are skipped by PMID


def call(endpoint, **params):
    params.update(tool="organ-donation-list", email=os.environ.get("NCBI_EMAIL", ""))
    if os.environ.get("NCBI_API_KEY"):
        params["api_key"] = os.environ["NCBI_API_KEY"]
    url = BASE + endpoint + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as r:
        body = r.read().decode("utf-8")
    time.sleep(0.4)       # stay under NCBI's 3 requests/second limit
    return body


def search_pmids(since, today):
    import json
    pmids, start = [], 0
    while True:
        out = json.loads(call("esearch.fcgi", db="pubmed", term=QUERY, retmode="json",
                              retmax=200, retstart=start, datetype="edat",
                              mindate=since.strftime("%Y/%m/%d"), maxdate=today.strftime("%Y/%m/%d")))
        res = out["esearchresult"]
        pmids += res["idlist"]
        start += 200
        if start >= int(res["count"]):
            return pmids


def fetch_records(pmids):
    papers = []
    for i in range(0, len(pmids), 100):
        text = call("efetch.fcgi", db="pubmed", id=",".join(pmids[i:i + 100]),
                    rettype="medline", retmode="text")
        papers += [op.to_paper(r) for r in op.split_records(text)]
    return papers


def main():
    dry = "--dry-run" in sys.argv
    db = op.load()
    today = datetime.date.today()
    last = datetime.date.fromisoformat(db["last_run"]) if db.get("last_run") else datetime.date(2000, 1, 1)
    since = last - datetime.timedelta(days=OVERLAP_DAYS)

    have = {p["pmid"] for p in db["papers"]}
    new_ids = [i for i in search_pmids(since, today) if i not in have]
    print("Found %d new PMIDs since %s" % (len(new_ids), since))
    new = fetch_records(new_ids) if new_ids else []

    for p in new:
        print("  + %s  %s" % (p["pmid"], p["title"][:80]))
    if dry:
        return
    db["papers"] += new                    # append
    db["last_run"] = today.isoformat()
    op.save(db)
    print("Rendered %d papers" % op.render(db))


if __name__ == "__main__":
    main()
