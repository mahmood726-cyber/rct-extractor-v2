"""
Build the soft-tissue sarcoma RCT corpus index from PubMed (reuses malaria helpers).
Output: data/field_portability/sarcoma/sarcoma_matched.jsonl
Usage: python scripts/sarcoma/build_sarcoma_corpus.py --retmax 3000
"""
import argparse, io, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from scripts.malaria.build_malaria_corpus import (
    esearch_pmids, efetch_records, idconv_batch, chunks,
)

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "sarcoma"
OUT_FILE = OUT_DIR / "sarcoma_matched.jsonl"

SARCOMA_TERM = (
    '("soft tissue sarcoma"[Title/Abstract] OR "sarcoma"[Title/Abstract] '
    'OR "gastrointestinal stromal tumor"[Title/Abstract] '
    'OR "leiomyosarcoma"[Title/Abstract] OR "liposarcoma"[Title/Abstract]) '
    'AND (randomized controlled trial[Publication Type] '
    'OR randomized[Title/Abstract] OR randomised[Title/Abstract])'
)


def main():
    ap = argparse.ArgumentParser(description="Build soft-tissue sarcoma RCT corpus index")
    ap.add_argument("--term", default=SARCOMA_TERM)
    ap.add_argument("--retmax", type=int, default=3000)
    ap.add_argument("--email", default="research@example.org")
    ap.add_argument("--batch", type=int, default=180)
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"esearch sarcoma RCTs (retmax={args.retmax})...")
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
            records[pmid] = {
                "study_id": f"sarcoma_{pmid}", "pmid": pmid,
                "pmcid": ids.get("pmcid"), "doi": ids.get("doi") or m.get("doi"),
                "nct_id": m.get("nct_id"), "other_registry_ids": m.get("other_registry_ids", []),
                "title": m.get("title"), "journal": m.get("journal"),
                "year": m.get("year"), "abstract": m.get("abstract"), "has_pdf": False,
            }
        print(f"  batch {bi+1}: {len(records)} records so far")
    with OUT_FILE.open("w", encoding="utf-8") as f:
        for r in records.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} -> {OUT_FILE}")


if __name__ == "__main__":
    main()
