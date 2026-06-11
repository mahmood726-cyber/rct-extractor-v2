"""
Build the chronic-pain RCT corpus index from PubMed (reuses malaria helpers).

Output: data/field_portability/chronic_pain/chronic_pain_matched.jsonl

Usage:
  python scripts/chronic_pain/build_chronic_pain_corpus.py --retmax 4000 --email you@org
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

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "chronic_pain"
OUT_FILE = OUT_DIR / "chronic_pain_matched.jsonl"

CHRONIC_PAIN_TERM = (
    '("chronic pain"[Title/Abstract] OR "neuropathic pain"[Title/Abstract] '
    'OR fibromyalgia[Title/Abstract] OR "postherpetic neuralgia"[Title/Abstract] '
    'OR "diabetic peripheral neuropathy"[Title/Abstract] OR "painful neuropathy"[Title/Abstract] '
    'OR "chronic musculoskeletal pain"[Title/Abstract] OR "pain intensity"[Title/Abstract] '
    'OR "spinal cord stimulation"[Title/Abstract]) '
    'AND (pain[Title/Abstract]) '
    'AND (randomized controlled trial[Publication Type] '
    'OR randomized[Title/Abstract] OR randomised[Title/Abstract])'
)


def main():
    ap = argparse.ArgumentParser(description="Build chronic-pain RCT corpus index")
    ap.add_argument("--term", default=CHRONIC_PAIN_TERM)
    ap.add_argument("--retmax", type=int, default=4000)
    ap.add_argument("--email", default="research@example.org")
    ap.add_argument("--batch", type=int, default=180)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"esearch chronic-pain RCTs (retmax={args.retmax})...")
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
