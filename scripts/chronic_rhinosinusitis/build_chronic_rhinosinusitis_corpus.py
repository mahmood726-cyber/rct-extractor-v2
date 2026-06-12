"""
Build the chronic-rhinosinusitis (CRS) RCT corpus index from PubMed (reuses the
malaria corpus helpers).

Output: data/field_portability/chronic_rhinosinusitis/chronic_rhinosinusitis_matched.jsonl

Usage:
  python scripts/chronic_rhinosinusitis/build_chronic_rhinosinusitis_corpus.py --retmax 3000
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

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "chronic_rhinosinusitis"
OUT_FILE = OUT_DIR / "chronic_rhinosinusitis_matched.jsonl"

CHRONIC_RHINOSINUSITIS_TERM = (
    '("chronic rhinosinusitis"[Title/Abstract] OR '
    '"nasal polyps"[Title/Abstract] OR '
    '"nasal polyposis"[Title/Abstract] OR '
    '"chronic rhinosinusitis with nasal polyps"[Title/Abstract] OR '
    '"sinonasal outcome test"[Title/Abstract] OR '
    '"endoscopic sinus surgery"[Title/Abstract] OR '
    '"nasal polyp score"[Title/Abstract]) '
    'AND (randomized controlled trial[Publication Type] '
    'OR randomized[Title/Abstract] OR randomised[Title/Abstract])'
)


def main():
    ap = argparse.ArgumentParser(description="Build chronic-rhinosinusitis RCT corpus index")
    ap.add_argument("--term", default=CHRONIC_RHINOSINUSITIS_TERM)
    ap.add_argument("--retmax", type=int, default=3000)
    ap.add_argument("--email", default="mahmood726@gmail.com")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pmids = esearch_pmids(args.term, args.retmax, args.email)
    print(f"PMIDs: {len(pmids)}")
    n = 0
    with OUT_FILE.open("w", encoding="utf-8") as f:
        for batch in chunks(pmids, 180):
            meta = efetch_records(batch, args.email)
            idmap = idconv_batch(batch, args.email)
            for pmid in batch:
                m = meta.get(pmid)
                if not m:
                    continue
                ids = idmap.get(pmid, {})
                rec = {
                    "study_id": pmid,
                    "pmid": pmid,
                    "pmcid": ids.get("pmcid"),
                    "doi": ids.get("doi"),
                    "title": m.get("title"),
                    "journal": m.get("journal"),
                    "year": m.get("year"),
                    "abstract": m.get("abstract"),
                    "has_pdf": bool(ids.get("pmcid")),
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
    print(f"WROTE {n} records -> {OUT_FILE}")


if __name__ == "__main__":
    main()
