#!/usr/bin/env python
"""
Convert the DTA70 R package (76 real DTA datasets, 6,348 study rows with complete
TP/FP/FN/TN) into a flat JSON gold file for Python-side validation.

DTA70 lives as `.rda` files; this reads them with pyreadr (no R needed) and emits
one JSON record per study row:

    {"dataset": "...", "row": i, "TP": .., "FP": .., "FN": .., "TN": ..}

This gold file is used by tests/test_dta70_derivation.py to confirm the DTA
derivation engine (TwoByTwo.sensitivity etc.) reproduces sensitivity/specificity
computed independently from the raw counts -- i.e. it validates the MATHS of the
extractor's derivation step against 6,348 real 2x2 tables.

It does NOT, on its own, validate text extraction (DTA70 has no abstract text);
that is what the EuropePMC real-PDF harness measures. The two are complementary
and reported separately, per the honesty contract.

Usage:
    python -m dta_extractor.validation.dta70_to_gold \
        --src "F:/Projects/mahmood789/DTA70/data" \
        --out dta_extractor/validation/gold/dta70_2x2.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path

REQUIRED = ("TP", "FP", "FN", "TN")


def _default_src() -> str:
    for cand in (
        r"F:/Projects/mahmood789/DTA70/data",
        r"C:/Users/mahmo/code/DTA70/data",
        str(Path.home() / "DTA70" / "data"),
    ):
        if os.path.isdir(cand):
            return cand
    return ""


def build(src: str, out: str) -> dict:
    import pyreadr  # local import so the package imports without pyreadr present

    files = sorted(glob.glob(os.path.join(src, "*.rda")))
    if not files:
        raise SystemExit(f"No .rda files found under {src!r}")

    records = []
    skipped = []
    for f in files:
        name = Path(f).stem
        result = pyreadr.read_r(f)
        for _obj_name, df in result.items():
            cols = {c.lower(): c for c in df.columns}
            if not all(c.lower() in cols for c in REQUIRED):
                skipped.append((name, list(df.columns)))
                continue
            for i, row in df.iterrows():
                try:
                    tp = int(round(float(row[cols["tp"]])))
                    fp = int(round(float(row[cols["fp"]])))
                    fn = int(round(float(row[cols["fn"]])))
                    tn = int(round(float(row[cols["tn"]])))
                except (ValueError, TypeError):
                    continue
                if min(tp, fp, fn, tn) < 0:
                    continue
                records.append(
                    {"dataset": name, "row": int(i), "TP": tp, "FP": fp, "FN": fn, "TN": tn}
                )

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "DTA70 R package (mahmood789/DTA70)",
        "n_datasets": len(files),
        "n_rows": len(records),
        "skipped_datasets": [s[0] for s in skipped],
        "records": records,
    }
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=0)
    return payload


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", default=_default_src(), help="DTA70 data/ directory")
    ap.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent / "gold" / "dta70_2x2.json"),
    )
    args = ap.parse_args()
    if not args.src:
        raise SystemExit("DTA70 source not found; pass --src explicitly")
    payload = build(args.src, args.out)
    print(
        f"Wrote {payload['n_rows']} 2x2 rows from {payload['n_datasets']} datasets "
        f"-> {args.out}"
    )
    if payload["skipped_datasets"]:
        print(f"Skipped (no TP/FP/FN/TN cols): {len(payload['skipped_datasets'])}")


if __name__ == "__main__":
    main()
