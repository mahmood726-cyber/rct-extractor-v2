"""
Build the cirrhosis RCT corpus index from PubMed (reuses malaria corpus helpers).
Canonical NCBI query is CIRRHOSIS_TERM. NCBI eutils was DNS-blocked on the build
host; real-PDF gold acquired via the EuropePMC harness
(scripts/pdf_eval/acquire_epmc_gold.py). Builder kept for parity.
Output: data/field_portability/cirrhosis/cirrhosis_matched.jsonl
"""
import argparse, io, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from scripts.malaria.build_malaria_corpus import esearch_pmids, efetch_records, idconv_batch, chunks

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "cirrhosis"
OUT_FILE = OUT_DIR / "cirrhosis_matched.jsonl"
CIRRHOSIS_TERM = (
    '(cirrhosis[Title/Abstract] OR "portal hypertension"[Title/Abstract] '
    'OR "hepatic encephalopathy"[Title/Abstract] OR "variceal"[Title/Abstract]) '
    'AND (randomized controlled trial[Publication Type] '
    'OR randomized[Title/Abstract] OR randomised[Title/Abstract])'
)


def main():
    ap = argparse.ArgumentParser(description="Build cirrhosis RCT corpus index")
    ap.add_argument("--term", default=CIRRHOSIS_TERM)
    ap.add_argument("--retmax", type=int, default=3000)
    ap.add_argument("--email", default="research@example.org")
    ap.add_argument("--batch", type=int, default=180)
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
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
            records[pmid] = {"study_id": pmid, "pmid": pmid, "pmcid": ids.get("pmcid"),
                "doi": ids.get("doi"), "title": m.get("title"), "journal": m.get("journal"),
                "year": m.get("year"), "abstract": m.get("abstract"), "has_pdf": bool(ids.get("pmcid"))}
    with OUT_FILE.open("w", encoding="utf-8") as f:
        for r in records.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"WROTE {len(records)} records -> {OUT_FILE}")


if __name__ == "__main__":
    main()
