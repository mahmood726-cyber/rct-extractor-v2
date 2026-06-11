"""
Build the dyslipidaemia / lipid-lowering RCT corpus index from PubMed
(reuses the malaria corpus helpers).

Output: data/field_portability/dyslipidaemia/dyslipidaemia_matched.jsonl

Dyslipidaemia is a very large field (statin/ezetimibe/PCSK9 trials number in the
thousands), so --retmax is a SAMPLE cap, not the true population count.

NOTE: the real-PDF accuracy eval for this specialty was run via
scripts/pdf_eval/acquire_and_gold_epmc.py (EuropePMC-sourced) because the NCBI
E-utilities host was DNS-unreachable in the build environment. This builder is
retained for the canonical eutils pipeline and exposes DYSLIPIDAEMIA_TERM for
scripts/pdf_eval/acquire_specialty_gold_corpus.py.

Usage:
  python scripts/dyslipidaemia/build_dyslipidaemia_corpus.py --retmax 4000 --email you@org
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

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "dyslipidaemia"
OUT_FILE = OUT_DIR / "dyslipidaemia_matched.jsonl"

DYSLIPIDAEMIA_TERM = (
    '(dyslipidemia[Title/Abstract] OR dyslipidaemia[Title/Abstract] OR '
    'hypercholesterolemia[Title/Abstract] OR hypercholesterolaemia[Title/Abstract] OR '
    'hyperlipidemia[Title/Abstract] OR hyperlipidaemia[Title/Abstract] OR '
    'statin[Title/Abstract] OR "LDL cholesterol"[Title/Abstract] OR '
    '"lipid lowering"[Title/Abstract] OR "cholesterol lowering"[Title/Abstract] OR '
    'ezetimibe[Title/Abstract] OR evolocumab[Title/Abstract] OR alirocumab[Title/Abstract] OR '
    'inclisiran[Title/Abstract]) '
    'AND (randomized controlled trial[Publication Type] '
    'OR randomized[Title/Abstract] OR randomised[Title/Abstract])'
)


def main():
    ap = argparse.ArgumentParser(description="Build dyslipidaemia RCT corpus index")
    ap.add_argument("--term", default=DYSLIPIDAEMIA_TERM)
    ap.add_argument("--retmax", type=int, default=4000)
    ap.add_argument("--email", default="research@example.org")
    ap.add_argument("--batch", type=int, default=180)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"esearch dyslipidaemia RCTs (retmax={args.retmax})...")
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
