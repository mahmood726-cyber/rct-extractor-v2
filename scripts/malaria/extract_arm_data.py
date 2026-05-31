"""
Run arm-level / 2x2 extraction across the malaria PDF corpus and report yield.

For every downloaded PDF: extract per-arm proportions and pair them into 2x2
tables. Reports how much poolable raw data we recover -- especially on the PDFs
that yielded zero effect estimates -- and the internal-consistency rate (reported
% vs 100*events/total) as a built-in accuracy signal.

Outputs:
  data/field_portability/malaria/arm_data.jsonl       (per-trial proportions + 2x2)
  data/field_portability/malaria/arm_data_report.md

Usage:
  python scripts/malaria/extract_arm_data.py --limit 0
"""
import argparse
import io
import json
import sys
import glob
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.pdf.pdf_parser import PDFParser
from src.specialties.malaria_arm_data import extract_proportions, pair_2x2

MAL = Path(__file__).resolve().parents[2] / "data" / "field_portability" / "malaria"
PDF_DIR = MAL / "rct_trial_pdfs"
OUT_JSONL = MAL / "arm_data.jsonl"
OUT_MD = MAL / "arm_data_report.md"


def main():
    ap = argparse.ArgumentParser(description="Corpus arm-level / 2x2 extraction")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    # which PDFs yielded zero effect estimates (for the coverage-unlock metric)
    zero_yield = set()
    cc = MAL / "cross_check.jsonl"
    if cc.exists():
        for l in open(cc, encoding="utf-8"):
            r = json.loads(l)
            if r["n_pdf_effects"] == 0:
                zero_yield.add(r["study_id"])

    pdfs = sorted(glob.glob(str(PDF_DIR / "*.pdf")))
    if args.limit:
        pdfs = pdfs[:args.limit]
    parser = PDFParser()

    n_trials = 0
    trials_with_prop = 0
    trials_with_2x2 = 0
    total_props = 0
    consistent_props = 0
    total_2x2 = 0
    unlocked = 0           # zero-effect PDFs that now yield >=1 2x2
    records = []

    for i, pdf in enumerate(pdfs):
        sid = os.path.basename(pdf).split("_PMC")[0]
        try:
            c = parser.parse(pdf)
            txt = "\n".join(p.full_text for p in c.pages)
        except Exception:
            continue
        n_trials += 1
        props = extract_proportions(txt)
        tables = pair_2x2(props)
        total_props += len(props)
        consistent_props += sum(1 for p in props if p["pct_consistent"])
        total_2x2 += len(tables)
        if props:
            trials_with_prop += 1
        if tables:
            trials_with_2x2 += 1
            if sid in zero_yield:
                unlocked += 1
        if props or tables:
            records.append({
                "study_id": sid, "n_proportions": len(props),
                "n_2x2": len(tables),
                "proportions": props[:30], "tables_2x2": tables[:15],
            })
        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(pdfs)} processed", flush=True)

    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    cons_rate = consistent_props / total_props if total_props else 0
    lines = [
        "# Malaria Arm-level / 2x2 Extraction Report", "",
        f"- PDFs processed: **{n_trials}**",
        f"- Trials with >=1 per-arm proportion: **{trials_with_prop}**",
        f"- Trials with >=1 paired 2x2 table: **{trials_with_2x2}**",
        f"- Total per-arm proportions extracted: **{total_props}**",
        f"- Total 2x2 tables: **{total_2x2}**",
        f"- Proportion internal-consistency (reported % == 100*n/N): "
        f"**{consistent_props}/{total_props}** ({cons_rate:.1%})",
        f"- **Coverage unlock:** zero-effect-estimate PDFs now yielding a 2x2: "
        f"**{unlocked}**", "",
        f"Per-trial detail: `{OUT_JSONL.name}`",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print("=" * 60)
    print(f"trials with 2x2: {trials_with_2x2}  total 2x2: {total_2x2}  "
          f"consistency: {cons_rate:.1%}  unlocked: {unlocked}")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
