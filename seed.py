"""One-off: build data/papers.json from the original PubMed export, then render the page.
Run once:  python seed.py
"""
import organ_papers as op

SEED_FILE = op.ROOT / "seed" / "pubmed-42497798-set.txt"
SEED_DATE = "2026-11-10"          # the monthly updater adds papers indexed after this date

text = SEED_FILE.read_text(encoding="utf-8")
papers = [op.to_paper(r) for r in op.split_records(text)]
op.save({"last_run": SEED_DATE, "papers": papers})
n = op.render(op.load())
print("Seeded and rendered %d papers" % n)
