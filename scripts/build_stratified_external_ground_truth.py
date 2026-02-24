#!/usr/bin/env python3
"""Build prepare-compatible JSONL from the stratified validation dataset."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "stratified_validation_dataset.py"
DEFAULT_OUTPUT_JSONL = PROJECT_ROOT / "data" / "ground_truth" / "stratified_external_validation_ground_truth.jsonl"
DEFAULT_OUTPUT_SUMMARY = PROJECT_ROOT / "data" / "ground_truth" / "stratified_external_validation_ground_truth_summary.json"


def _headers() -> Dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
    }


def _normalize_pmid(value: object) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _normalize_pmcid(value: object) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return ""
    if not text.startswith("PMC"):
        text = f"PMC{text}"
    return text


def _normalize_doi(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
    return re.sub(r"\s+", "", text)


def _effect_type_token(effect_type: object) -> str:
    value = str(getattr(effect_type, "value", effect_type) or "").strip().upper()
    mapping = {
        "HAZARD RATIO": "HR",
        "ODDS RATIO": "OR",
        "RISK RATIO": "RR",
        "MEAN DIFFERENCE": "MD",
        "STANDARDIZED MEAN DIFFERENCE": "SMD",
        "INCIDENCE RATE RATIO": "IRR",
        "ABSOLUTE RISK DIFFERENCE": "ARD",
        "RELATIVE RISK REDUCTION": "RRR",
    }
    return mapping.get(value, value or "RR")


def _load_trials(module_path: Path) -> List[object]:
    if not module_path.exists():
        raise FileNotFoundError(f"Missing module: {module_path}")
    spec = importlib.util.spec_from_file_location("stratified_validation_dataset", str(module_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    trials = getattr(module, "STRATIFIED_VALIDATION_TRIALS", None)
    if not isinstance(trials, list):
        raise RuntimeError("Expected STRATIFIED_VALIDATION_TRIALS list in module.")
    return trials


def _fetch_idconv_for_pmid(
    *,
    pmid: str,
    timeout_sec: float,
    retries: int,
    cache: Dict[str, Optional[Dict[str, str]]],
) -> Optional[Dict[str, str]]:
    pmid_norm = _normalize_pmid(pmid)
    if not pmid_norm:
        return None
    if pmid_norm in cache:
        return cache[pmid_norm]

    url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={pmid_norm}&format=json"
    api_key = str(os.environ.get("NCBI_API_KEY") or "").strip()
    if api_key:
        url = f"{url}&api_key={api_key}"
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers=_headers())
            with urllib.request.urlopen(request, timeout=timeout_sec) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
            records = payload.get("records") or []
            record = records[0] if records and isinstance(records[0], dict) else {}
            normalized = {
                "pmid": _normalize_pmid(record.get("pmid")),
                "pmcid": _normalize_pmcid(record.get("pmcid")),
                "doi": _normalize_doi(record.get("doi")),
            }
            cache[pmid_norm] = normalized
            return normalized
        except Exception as exc:  # noqa: BLE001 - keep robust against network/parser errors
            last_exc = exc
            if attempt >= retries:
                break
            time.sleep(0.4 * (attempt + 1))
    cache[pmid_norm] = None
    if last_exc is not None:
        return None
    return None


def _journal_text(value: object) -> str:
    return str(getattr(value, "value", value) or "").strip()


def _area_text(value: object) -> str:
    return str(getattr(value, "value", value) or "").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-module", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUTPUT_JSONL)
    parser.add_argument("--output-summary", type=Path, default=DEFAULT_OUTPUT_SUMMARY)
    parser.add_argument(
        "--resolve-idconv",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Resolve PMCID/DOI from PMID via NCBI idconv.",
    )
    parser.add_argument("--request-timeout-sec", type=float, default=15.0)
    parser.add_argument("--http-retries", type=int, default=1)
    parser.add_argument("--sleep-sec", type=float, default=0.05)
    args = parser.parse_args()

    if args.request_timeout_sec <= 0:
        raise ValueError("--request-timeout-sec must be > 0")
    if args.http_retries < 0:
        raise ValueError("--http-retries must be >= 0")
    if args.sleep_sec < 0:
        raise ValueError("--sleep-sec must be >= 0")

    trials = _load_trials(args.input_module)
    idconv_cache: Dict[str, Optional[Dict[str, str]]] = {}
    rows: List[Dict] = []
    stats = Counter()
    journal_counts = Counter()
    year_blocks = Counter()

    for idx, trial in enumerate(trials, start=1):
        pmid = _normalize_pmid(getattr(trial, "pmid", ""))
        pmcid = ""
        doi = ""
        if args.resolve_idconv and pmid:
            resolved = _fetch_idconv_for_pmid(
                pmid=pmid,
                timeout_sec=args.request_timeout_sec,
                retries=args.http_retries,
                cache=idconv_cache,
            )
            if resolved is None:
                stats["idconv_lookup_failed"] += 1
            else:
                pmcid = _normalize_pmcid(resolved.get("pmcid"))
                doi = _normalize_doi(resolved.get("doi"))
                if pmcid:
                    stats["resolved_pmcid"] += 1
                else:
                    stats["missing_pmcid"] += 1
                if doi:
                    stats["resolved_doi"] += 1
                else:
                    stats["missing_doi"] += 1
        else:
            stats["idconv_skipped"] += 1

        journal = _journal_text(getattr(trial, "journal", ""))
        year = int(getattr(trial, "year", 0) or 0)
        year_block = str(getattr(getattr(trial, "year_block", ""), "value", "") or "")
        effect_type = _effect_type_token(getattr(trial, "effect_type", "RR"))
        expected_value = float(getattr(trial, "expected_value"))
        ci_low = float(getattr(trial, "expected_ci_lower"))
        ci_high = float(getattr(trial, "expected_ci_upper"))
        source_text = str(getattr(trial, "source_text", "") or "").strip()
        trial_name = str(getattr(trial, "trial_name", "") or "").strip()

        effects = [
            {
                "effect_type": effect_type,
                "value": expected_value,
                "ci_lower": ci_low,
                "ci_upper": ci_high,
                "p_value": None,
                "outcome": "Primary endpoint",
                "timepoint": "",
                "comparison": "",
                "analysis_population": "ITT",
                "source_type": "stratified_validation_dataset",
                "source_text": source_text,
                "extractor_id": "STRATIFIED",
            }
        ]

        row = {
            "trial_name": trial_name,
            "nct_id": "",
            "pmc_id": pmcid,
            "pmid": pmid,
            "doi": doi,
            "therapeutic_area": _area_text(getattr(trial, "therapeutic_area", "")),
            "journal": journal,
            "year": year if year > 0 else None,
            "difficulty": "stratified",
            "source": "stratified_validation_dataset",
            "effects": effects,
            "source_text": source_text,
            "year_block": year_block,
            "notes": str(getattr(trial, "notes", "") or ""),
        }
        rows.append(row)

        journal_counts[journal] += 1
        year_blocks[year_block] += 1
        stats["rows_total"] += 1
        if pmid:
            stats["rows_with_pmid"] += 1
        if pmcid:
            stats["rows_with_pmcid"] += 1
        if doi:
            stats["rows_with_doi"] += 1

        if idx % 10 == 0 or idx == len(trials):
            print(f"[{idx}/{len(trials)}] {trial_name} pmcid={'yes' if pmcid else 'no'} doi={'yes' if doi else 'no'}")
        if args.sleep_sec > 0:
            time.sleep(args.sleep_sec)

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_module": str(args.input_module).replace("\\", "/"),
        "output_jsonl": str(args.output_jsonl).replace("\\", "/"),
        "resolve_idconv": bool(args.resolve_idconv),
        "request_timeout_sec": args.request_timeout_sec,
        "http_retries": args.http_retries,
        "counts": dict(stats),
        "journal_counts": dict(sorted(journal_counts.items())),
        "year_block_counts": dict(sorted(year_blocks.items())),
    }
    args.output_summary.parent.mkdir(parents=True, exist_ok=True)
    args.output_summary.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("\nStratified ground-truth build complete")
    print("=====================================")
    print(f"Rows written: {len(rows)}")
    print(f"Rows with PMCID: {stats.get('rows_with_pmcid', 0)}")
    print(f"Rows with DOI: {stats.get('rows_with_doi', 0)}")
    print(f"Wrote: {args.output_jsonl}")
    print(f"Wrote: {args.output_summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
