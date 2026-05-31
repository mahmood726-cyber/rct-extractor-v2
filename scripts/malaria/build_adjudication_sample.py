"""
Build a random sample of PDF extractions for independent LLM adjudication.

Pulls a deterministic, type-stratified random sample of effect estimates the
extractor produced from PDFs, each with the source-text span it came from, so an
independent judge (another LLM, or a human) can verify whether the extracted
(type, value, CI) is correct given the text.

Output: data/field_portability/malaria/adjudication_sample.jsonl
"""
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

MAL = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "malaria"
CC = MAL / "cross_check.jsonl"
OUT = MAL / "adjudication_sample.jsonl"

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40


def main():
    rows = [json.loads(l) for l in open(CC, encoding="utf-8")]
    items = []
    for r in rows:
        for x in r.get("pdf_effects", []):
            if not x.get("source_text"):
                continue
            items.append({
                "study_id": r["study_id"], "pmid": r.get("pmid"),
                "type": x["type"], "value": x["value"],
                "ci_lower": x.get("ci_lower"), "ci_upper": x.get("ci_upper"),
                "endpoint": x.get("endpoint"), "origin": x.get("origin"),
                "needs_review": x.get("needs_review", False),
                "source_text": x["source_text"],
            })
    # deterministic type-stratified sampling (no RNG: stride per type)
    by_type = {}
    for it in items:
        by_type.setdefault(it["type"], []).append(it)
    sample = []
    types = sorted(by_type)
    per = max(1, N // max(1, len(types)))
    for t in types:
        lst = by_type[t]
        stride = max(1, len(lst) // per)
        sample.extend(lst[::stride][:per])
    sample = sample[:N]
    for i, it in enumerate(sample):
        it["id"] = i + 1

    with open(OUT, "w", encoding="utf-8") as f:
        for it in sample:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"Wrote {len(sample)} items -> {OUT}")
    print(f"type mix: {({t: sum(1 for s in sample if s['type']==t) for t in types})}")


if __name__ == "__main__":
    main()
