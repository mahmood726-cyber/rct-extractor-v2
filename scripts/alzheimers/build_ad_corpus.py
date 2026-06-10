"""
Build the Alzheimer's disease / dementia RCT corpus index from PubMed (reuses the
malaria corpus helpers). Canonical NCBI query is ALZHEIMERS_TERM.

NOTE: the build host had the NCBI `eutils.` subdomain DNS-blocked, so the
real-PDF gold for the accuracy report was acquired via the EuropePMC-sourced
harness (scripts/pdf_eval/acquire_epmc_gold.py), identical gold method, scored on
the full PDF body. This builder is kept for parity and works wherever NCBI
E-utilities are reachable.

Output: data/field_portability/alzheimers/alzheimers_matched.jsonl
Usage:  python scripts/alzheimers/build_ad_corpus.py --retmax 3000 --email you@org
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

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "alzheimers"
OUT_FILE = OUT_DIR / "alzheimers_matched.jsonl"

ALZHEIMERS_TERM = (
    '("Alzheimer disease"[Title/Abstract] OR "Alzheimer\'s disease"[Title/Abstract] '
    'OR dementia[Title/Abstract] OR "mild cognitive impairment"[Title/Abstract]) '
    'AND (randomized controlled trial[Publication Type] '
    'OR randomized[Title/Abstract] OR randomised[Title/Abstract])'
)


def main():
    ap = argparse.ArgumentParser(description="Build Alzheimer's disease RCT corpus index")
    ap.add_argument("--term", default=ALZHEIMERS_TERM)
    ap.add_argument("--retmax", type=int, default=3000)
    ap.add_argument("--email", default="research@example.org")
    ap.add_argument("--batch", type=int, default=180)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"esearch Alzheimer's RCTs (retmax={args.retmax})...")
    pmids = esearch_pmids(args.term, args.retmax, args.email)
    print(f"  PMIDs: {len(pmids)}")
    if not pmids:
        sys.exit("no PMIDs")

    records = {}
    for batch in chunks(pmids, args.batch):
        meta = efetch_records(batch, args.email)
        idmap = idconv_batch(batch, args.email)
        for pmid in batch:
            m = meta.get(pmid)
            if not m:
                continue
            ids = idmap.get(pmid, {})
            records[pmid] = {
                "study_id": pmid, "pmid": pmid, "pmcid": ids.get("pmcid"),
                "doi": ids.get("doi"), "title": m.get("title"),
                "journal": m.get("journal"), "year": m.get("year"),
                "abstract": m.get("abstract"), "has_pdf": bool(ids.get("pmcid")),
            }

    with OUT_FILE.open("w", encoding="utf-8") as f:
        for r in records.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_pmc = sum(1 for r in records.values() if r["pmcid"])
    print(f"WROTE {len(records)} records ({n_pmc} with PMCID) -> {OUT_FILE}")


if __name__ == "__main__":
    main()
