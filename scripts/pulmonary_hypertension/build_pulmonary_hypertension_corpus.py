"""
Build the pulmonary-hypertension RCT corpus index from PubMed (malaria helpers).

Output: data/field_portability/pulmonary_hypertension/pulmonary_hypertension_matched.jsonl

NOTE: the real-PDF accuracy eval for this specialty was run via
scripts/pdf_eval/acquire_and_gold_epmc.py (EuropePMC-sourced) because the NCBI
E-utilities host was DNS-unreachable in the build environment. This builder is
retained for the canonical eutils pipeline and exposes PULMONARY_HYPERTENSION_TERM.

Usage:
  python scripts/pulmonary_hypertension/build_pulmonary_hypertension_corpus.py --retmax 4000
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

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "pulmonary_hypertension"
OUT_FILE = OUT_DIR / "pulmonary_hypertension_matched.jsonl"

PULMONARY_HYPERTENSION_TERM = (
    '("pulmonary arterial hypertension"[Title/Abstract] OR '
    '"pulmonary hypertension"[Title/Abstract] OR bosentan[Title/Abstract] OR '
    'macitentan[Title/Abstract] OR ambrisentan[Title/Abstract] OR '
    'riociguat[Title/Abstract] OR selexipag[Title/Abstract] OR '
    'treprostinil[Title/Abstract] OR sotatercept[Title/Abstract]) '
    'AND (randomized controlled trial[Publication Type] '
    'OR randomized[Title/Abstract] OR randomised[Title/Abstract])'
)


def main():
    ap = argparse.ArgumentParser(description="Build pulmonary-hypertension RCT corpus index")
    ap.add_argument("--term", default=PULMONARY_HYPERTENSION_TERM)
    ap.add_argument("--retmax", type=int, default=4000)
    ap.add_argument("--email", default="research@example.org")
    ap.add_argument("--batch", type=int, default=180)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"esearch pulmonary-hypertension RCTs (retmax={args.retmax})...")
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
    print(f"wrote {len(records)} records ({n_pdf} with PDF) -> {OUT_FILE}")


if __name__ == "__main__":
    main()
