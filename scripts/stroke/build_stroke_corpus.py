"""
Build the stroke (cerebrovascular) RCT corpus index from PubMed (reuses the
malaria corpus helpers).

Covers acute ischemic stroke (thrombolysis / thrombectomy), intracerebral
haemorrhage, secondary prevention, and recovery / rehabilitation trials.

Output: data/field_portability/stroke/stroke_matched.jsonl
  {study_id, pmid, pmcid, doi, nct_id, other_registry_ids, title, journal, year,
   abstract, has_pdf}

Usage:
  python scripts/stroke/build_stroke_corpus.py --retmax 3000 --email you@org
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

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "stroke"
OUT_FILE = OUT_DIR / "stroke_matched.jsonl"

# Ischemic stroke OR intracerebral haemorrhage OR thrombolysis OR thrombectomy
# RCTs. British + American spellings included (ischaemic/ischemic,
# haemorrhage/hemorrhage); the [Title/Abstract] tags keep recall tight.
STROKE_TERM = (
    '("ischaemic stroke"[Title/Abstract] OR "ischemic stroke"[Title/Abstract] OR '
    '"acute stroke"[Title/Abstract] OR "intracerebral haemorrhage"[Title/Abstract] OR '
    '"intracerebral hemorrhage"[Title/Abstract] OR thrombolysis[Title/Abstract] OR '
    'thrombectomy[Title/Abstract] OR alteplase[Title/Abstract] OR '
    'tenecteplase[Title/Abstract] OR "modified Rankin"[Title/Abstract] OR '
    'NIHSS[Title/Abstract]) '
    'AND (randomized controlled trial[Publication Type] '
    'OR randomized[Title/Abstract] OR randomised[Title/Abstract])'
)


def main():
    ap = argparse.ArgumentParser(description="Build stroke RCT corpus index")
    ap.add_argument("--term", default=STROKE_TERM)
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
