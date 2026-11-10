# Selected Victorian Scientific Papers on Organ Donation

A static web page (`docs/index.html`) listing papers in Vancouver style, newest first, with PubMed and DOI
links and collapsible abstracts. A GitHub Action refreshes it monthly from PubMed. No server, no database:
the data lives in `data/papers.json`.

## One-time setup

1. Copy this folder's contents into your repo and push to `main`.
2. In the repo: **Settings > Pages > Build and deployment**, choose *Deploy from a branch*, branch `main`,
   folder `/docs`. The page will be at `https://<user>.github.io/<repo>/`.
3. (Optional) **Settings > Secrets and variables > Actions**: add secret `NCBI_API_KEY` (free from your NCBI
   account; raises the rate limit) and variable `NCBI_EMAIL` (your contact email, which NCBI asks for).
4. Check the **Actions** tab. You can run "Monthly PubMed update" manually with *Run workflow* to test it.

`data/papers.json` and `docs/index.html` are already seeded with the original 45 papers
(`python seed.py` rebuilds them from `seed/pubmed-42497798-set.txt`).

## How the monthly update works

`update.py` searches PubMed for records **added to PubMed since the last run** (Entrez date, with a 7-day
overlap) using:

    ("DonateLife"[All Fields] AND "Victoria"[All Fields])
    OR ("organ donation"[All Fields] AND "redcrossblood.org.au"[Affiliation])

New PMIDs not already in `papers.json` are fetched, appended, and the page is re-rendered in date order.
Preview without changing anything: `python update.py --dry-run`.

## Notes

- New papers are added automatically without review. If you want to remove one, delete its entry from
  `data/papers.json` and re-run `python -c "import organ_papers as o; o.render(o.load())"`. It is only re-added
  if it is still inside the 7-day overlap window of the next run.
- Only Python 3.9+ standard library is used.
