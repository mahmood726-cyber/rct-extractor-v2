#!/usr/bin/env python3
"""Fail if current real-RCT metrics regress beyond an allowed drop."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

DEFAULT_METRICS = [
    "strict_match_rate",
    "lenient_match_rate",
    "effect_type_accuracy",
    "ci_completeness",
    "ma_ready_yield",
]


def _load_rates(path: Path) -> Dict[str, float]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if "rates" not in data:
        raise ValueError(f"Missing 'rates' object in metrics file: {path}")
    return data["rates"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True, help="Baseline metrics JSON.")
    parser.add_argument("--current", type=Path, required=True, help="Current metrics JSON.")
    parser.add_argument(
        "--metrics",
        nargs="*",
        default=DEFAULT_METRICS,
        help="Metric keys under the 'rates' section to gate.",
    )
    parser.add_argument(
        "--max-drop",
        type=float,
        default=0.02,
        help="Maximum allowed absolute drop (0.02 = 2 percentage points).",
    )
    parser.add_argument("--report", type=Path, default=None, help="Optional path to write gate report JSON.")
    args = parser.parse_args()

    if args.max_drop < 0:
        raise ValueError("--max-drop must be non-negative.")

    baseline_rates = _load_rates(args.baseline)
    current_rates = _load_rates(args.current)

    failures: List[Dict] = []
    summary: List[Dict] = []

    for metric in args.metrics:
        if metric not in baseline_rates:
            raise KeyError(f"Metric '{metric}' missing from baseline file: {args.baseline}")
        if metric not in current_rates:
            raise KeyError(f"Metric '{metric}' missing from current file: {args.current}")

        baseline_value = float(baseline_rates[metric])
        current_value = float(current_rates[metric])
        delta = current_value - baseline_value
        passed = delta >= -args.max_drop
        row = {
            "metric": metric,
            "baseline": baseline_value,
            "current": current_value,
            "delta": delta,
            "max_allowed_drop": args.max_drop,
            "passed": passed,
        }
        summary.append(row)
        if not passed:
            failures.append(row)

    print("Regression Gate")
    print("===============")
    for row in summary:
        status = "PASS" if row["passed"] else "FAIL"
        print(
            f"{status:4} {row['metric']:>22}  "
            f"baseline={row['baseline']:.3%}  "
            f"current={row['current']:.3%}  "
            f"delta={row['delta']:+.3%}"
        )

    report = {
        "baseline_file": str(args.baseline).replace("\\", "/"),
        "current_file": str(args.current).replace("\\", "/"),
        "max_drop": args.max_drop,
        "metrics": summary,
        "passed": len(failures) == 0,
        "failures": failures,
    }

    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
        print(f"\nWrote gate report: {args.report}")

    if failures:
        print(f"\nRegression gate failed: {len(failures)} metric(s) exceeded drop threshold.")
        return 1

    print("\nRegression gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
