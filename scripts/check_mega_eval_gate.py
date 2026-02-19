#!/usr/bin/env python3
"""Gate mega_eval_summary against non-regression thresholds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Any


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True, help="Baseline gate JSON.")
    parser.add_argument("--current-summary", type=Path, required=True, help="Current mega_eval_summary JSON.")
    parser.add_argument(
        "--extraction-rate-slack",
        type=float,
        default=0.0,
        help="Allowed absolute drop in extraction rate before failing.",
    )
    parser.add_argument("--report", type=Path, default=None, help="Optional output report JSON.")
    args = parser.parse_args()

    if args.extraction_rate_slack < 0:
        raise ValueError("--extraction-rate-slack must be >= 0")

    baseline = _load_json(args.baseline)
    current = _load_json(args.current_summary)

    baseline_no_extraction = int(baseline.get("no_extraction", 0))
    baseline_extraction_rate = float(baseline.get("extraction_rate", 0.0))

    counts = dict(current.get("counts") or {})
    current_no_extraction = int(counts.get("no_extraction", 0))
    current_extraction_rate = float(current.get("extraction_rate", 0.0))

    no_extraction_ok = current_no_extraction <= baseline_no_extraction
    extraction_rate_ok = current_extraction_rate >= (baseline_extraction_rate - args.extraction_rate_slack)
    passed = no_extraction_ok and extraction_rate_ok

    print("Mega Eval Gate")
    print("==============")
    print(
        f"{'PASS' if no_extraction_ok else 'FAIL'} no_extraction: "
        f"baseline={baseline_no_extraction} current={current_no_extraction}"
    )
    print(
        f"{'PASS' if extraction_rate_ok else 'FAIL'} extraction_rate: "
        f"baseline={baseline_extraction_rate:.6f} current={current_extraction_rate:.6f} "
        f"slack={args.extraction_rate_slack:.6f}"
    )

    report = {
        "baseline_file": str(args.baseline).replace("\\", "/"),
        "current_summary_file": str(args.current_summary).replace("\\", "/"),
        "baseline": {
            "no_extraction": baseline_no_extraction,
            "extraction_rate": baseline_extraction_rate,
        },
        "current": {
            "no_extraction": current_no_extraction,
            "extraction_rate": current_extraction_rate,
        },
        "checks": {
            "no_extraction_not_increased": no_extraction_ok,
            "extraction_rate_not_dropped": extraction_rate_ok,
        },
        "extraction_rate_slack": args.extraction_rate_slack,
        "passed": passed,
    }

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
        print(f"\nWrote gate report: {args.report}")

    if not passed:
        print("\nMega eval gate failed.")
        return 1

    print("\nMega eval gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
