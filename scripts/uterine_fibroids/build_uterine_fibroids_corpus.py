"""
Build the uterine-fibroids (leiomyoma) RCT corpus index from PubMed (reuses the
malaria corpus helpers). Defines UTERINE_FIBROIDS_TERM, the canonical query the
EuropePMC acquire path (scripts/pdf_eval/acquire_via_europepmc.py) AST-parses.

Output: data/field_portability/uterine_fibroids/uterine_fibroids_matched.jsonl

Usage:
  python scripts/uterine_fibroids/build_uterine_fibroids_corpus.py --retmax 3000 --email you@org
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

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "uterine_fibroids"
OUT_FILE = OUT_DIR / "uterine_fibroids_matched.jsonl"

UTERINE_FIBROIDS_TERM = (
    '("uterine fibroid"[Title/Abstract] OR "uterine fibroids"[Title/Abstract] '
    'OR "uterine leiomyoma"[Title/Abstract] OR "leiomyomata"[Title/Abstract] '
    'OR "myoma"[Title/Abstract] OR "fibroids"[Title/Abstract] '
    'OR "heavy menstrual bleeding"[Title/Abstract]) '
    'AND ("relugolix"[Title/Abstract] OR "elagolix"[Title/Abstract] '
    'OR "linzagolix"[Title/Abstract] OR "ulipristal"[Title/Abstract] '
    'OR "uterine artery embolization"[Title/Abstract] '
    'OR "uterine artery embolisation"[Title/Abstract] '
    'OR "myomectomy"[Title/Abstract] OR "tranexamic"[Title/Abstract] '
    'OR "GnRH"[Title/Abstract] OR "focused ultrasound"[Title/Abstract] '
    'OR "radiofrequency ablation"[Title/Abstract] OR "menstrual blood loss"[Title/Abstract]) '
    'AND (randomized controlled trial[Publication Type] '
    'OR randomized[Title/Abstract] OR randomised[Title/Abstract])'
)


def main():
    ap = argparse.ArgumentParser(description="Build uterine-fibroids RCT corpus index")
    ap.add_argument("--term", default=UTERINE_FIBROIDS_TERM)
    ap.add_argument("--retmax", type=int, default=3000)
    ap.add_argument("--email", default="research@example.org")
    ap.add_argument("--batch", type=int, default=180)
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"esearch uterine-fibroids RCTs (retmax={args.retmax})...")
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
