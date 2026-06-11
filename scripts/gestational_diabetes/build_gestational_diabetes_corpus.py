"""
Build the gestational-diabetes (GDM) RCT corpus index from PubMed (reuses the
malaria corpus helpers). Defines GESTATIONAL_DIABETES_TERM, the canonical query
the EuropePMC acquire path (scripts/pdf_eval/acquire_via_europepmc.py) AST-parses.

Output: data/field_portability/gestational_diabetes/gestational_diabetes_matched.jsonl

Usage:
  python scripts/gestational_diabetes/build_gestational_diabetes_corpus.py --retmax 3000 --email you@org
"""
import argparse
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from scripts.malaria.build_malaria_corpus import (
    esearch_pmids, efetch_records, idconv_batch, chunks,
)

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "gestational_diabetes"
OUT_FILE = OUT_DIR / "gestational_diabetes_matched.jsonl"

GESTATIONAL_DIABETES_TERM = (
    '("gestational diabetes"[Title/Abstract] OR "gestational diabetes mellitus"[Title/Abstract] '
    'OR "GDM"[Title/Abstract] OR "hyperglycemia in pregnancy"[Title/Abstract] '
    'OR "hyperglycaemia in pregnancy"[Title/Abstract] '
    'OR "diabetes in pregnancy"[Title/Abstract] '
    'OR "glucose intolerance in pregnancy"[Title/Abstract]) '
    'AND ("metformin"[Title/Abstract] OR "glyburide"[Title/Abstract] '
    'OR "glibenclamide"[Title/Abstract] OR "insulin"[Title/Abstract] '
    'OR "macrosomia"[Title/Abstract] OR "large for gestational age"[Title/Abstract] '
    'OR "neonatal hypoglycemia"[Title/Abstract] OR "neonatal hypoglycaemia"[Title/Abstract] '
    'OR "glycemic"[Title/Abstract] OR "glycaemic"[Title/Abstract] '
    'OR "dietary"[Title/Abstract] OR "lifestyle"[Title/Abstract]) '
    'AND (randomized controlled trial[Publication Type] '
    'OR randomized[Title/Abstract] OR randomised[Title/Abstract])'
)


def main():
    ap = argparse.ArgumentParser(description="Build gestational-diabetes RCT corpus index")
    ap.add_argument("--term", default=GESTATIONAL_DIABETES_TERM)
    ap.add_argument("--retmax", type=int, default=3000)
    ap.add_argument("--email", default="research@example.org")
    ap.add_argument("--batch", type=int, default=180)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"esearch gestational-diabetes RCTs (retmax={args.retmax})...")
    pmids = esearch_pmids(args.term, args.retmax, args.email)
    print(f"  PMIDs: {len(pmids)}")
    if not pmids:
        sys.exit("no PMIDs")

    records = {}
    for bi, batch in enumerate(chunks(pmids, args.batch)):
        meta = efetch_records(batch, args.email)
        idmap = idconv_batch(batch, args.email)
        for pmid in batch:
            m = meta.get(pmid)
            if not m:
                continue
            ids = idmap.get(pmid, {})
            pmcid = ids.get("pmcid")
            records[pmid] = {
                "study_id": f"PMID{pmid}", "pmid": pmid, "pmcid": pmcid,
                "doi": ids.get("doi"), "nct_id": m["nct_id"], "nct_ids": m["nct_ids"],
                "other_registry_ids": m.get("other_registry_ids", []),
                "title": m["title"], "journal": m["journal"], "year": m["year"],
                "abstract": m["abstract"], "has_pdf": bool(pmcid),
            }
        if (bi + 1) % 4 == 0:
            n_pdf = sum(1 for r in records.values() if r["has_pdf"])
            print(f"  batch {bi+1}: total={len(records)} with_pdf={n_pdf}")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for r in records.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_pdf = sum(1 for r in records.values() if r["has_pdf"])
    print("=" * 60)
    print(f"Wrote {len(records)} -> {OUT_FILE}")
    print(f"  OA PDF: {n_pdf}")


if __name__ == "__main__":
    main()
