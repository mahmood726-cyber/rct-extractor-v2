"""
Build the cervical-cancer / HPV RCT corpus index from PubMed (reuses the malaria
corpus helpers).

Output: data/field_portability/cervical_cancer/cervical_cancer_matched.jsonl
  {study_id, pmid, pmcid, doi, nct_id, other_registry_ids, title, journal, year,
   abstract, has_pdf}

Usage:
  python scripts/cervical_cancer/build_cervical_cancer_corpus.py --retmax 3000 --email you@org
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

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "cervical_cancer"
OUT_FILE = OUT_DIR / "cervical_cancer_matched.jsonl"

CERVICAL_CANCER_TERM = (
    '("cervical cancer"[Title/Abstract] OR "cervical intraepithelial neoplasia"[Title/Abstract] '
    'OR "cervical precancer"[Title/Abstract] OR "HPV vaccine"[Title/Abstract] '
    'OR "human papillomavirus"[Title/Abstract] OR "cervical screening"[Title/Abstract] '
    'OR "visual inspection with acetic acid"[Title/Abstract] OR "CIN2"[Title/Abstract] '
    'OR "CIN3"[Title/Abstract]) '
    'AND (randomized controlled trial[Publication Type] '
    'OR randomized[Title/Abstract] OR randomised[Title/Abstract])'
)


def main():
    ap = argparse.ArgumentParser(description="Build cervical-cancer / HPV RCT corpus index")
    ap.add_argument("--term", default=CERVICAL_CANCER_TERM)
    ap.add_argument("--retmax", type=int, default=3000)
    ap.add_argument("--email", default="research@example.org")
    ap.add_argument("--batch", type=int, default=180)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"esearch cervical-cancer / HPV RCTs (retmax={args.retmax})...")
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
    n_nct = sum(1 for r in records.values() if r["nct_id"])
    n_abs = sum(1 for r in records.values() if r["abstract"])
    print("=" * 60)
    print(f"Wrote {len(records)} -> {OUT_FILE}")
    print(f"  OA PDF: {n_pdf}  NCT: {n_nct}  abstract: {n_abs}")


if __name__ == "__main__":
    main()
