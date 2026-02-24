#!/usr/bin/env python3
"""Augment a prepared cohort with DOI-validated OA PDFs from Unpaywall."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EMAIL = "tooling@proton.me"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pdf.pdf_parser import PDFParser


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def _write_jsonl(path: Path, rows: Sequence[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _normalize_doi(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = text.replace("https://doi.org/", "").replace("http://doi.org/", "")
    text = text.replace("doi:", "")
    return text.strip()


def _to_float(value: object) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _infer_outcome_type(effect_type: str) -> str:
    normalized = str(effect_type or "").upper()
    if normalized in {"MD", "SMD"}:
        return "continuous"
    return "binary"


def _build_gold_record(item: Dict) -> Dict:
    return {
        "study_id": item["study_id"],
        "pdf_filename": item["pdf_filename"],
        "excluded": False,
        "cochrane_effect": item["target_value"],
        "cochrane_ci_lower": item["target_ci_lower"],
        "cochrane_ci_upper": item["target_ci_upper"],
        "cochrane_outcome": item["target_outcome"],
        "cochrane_outcome_type": item.get("outcome_type") or _infer_outcome_type(item.get("target_effect_type")),
        "gold": {
            "point_estimate": item["target_value"],
            "ci_lower": item["target_ci_lower"],
            "ci_upper": item["target_ci_upper"],
            "effect_type": item["target_effect_type"],
            "source_text": item["target_source_text"],
            "page_number": None,
            "raw_data": None,
        },
        "external_meta": {
            "trial_name": item["trial_name"],
            "pmc_id": item.get("pmc_id"),
            "pmid": item.get("pmid"),
            "doi": item.get("doi"),
            "journal": item["journal"],
            "year": item["year"],
        },
    }


def _headers() -> Dict[str, str]:
    return {"User-Agent": "Mozilla/5.0"}


def _fetch_unpaywall_locations(doi: str, email: str, timeout_sec: float) -> List[Tuple[str, str]]:
    url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    response = requests.get(url, timeout=timeout_sec, headers=_headers())
    if response.status_code != 200:
        return []
    payload = response.json()
    locations = payload.get("oa_locations") or []
    candidates: List[Tuple[str, str]] = []
    seen = set()
    for loc in locations:
        pdf_url = str(loc.get("url_for_pdf") or "").strip()
        host_type = str(loc.get("host_type") or "")
        if pdf_url and pdf_url not in seen:
            candidates.append((pdf_url, host_type))
            seen.add(pdf_url)
    return candidates


def _download_pdf(url: str, output_path: Path, timeout_sec: float) -> bool:
    response = requests.get(url, timeout=timeout_sec, headers=_headers(), allow_redirects=True, stream=True)
    response.raise_for_status()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        first_chunk = b""
        for chunk in response.iter_content(chunk_size=1024 * 64):
            if not chunk:
                continue
            if not first_chunk:
                first_chunk = chunk
            handle.write(chunk)
    if not first_chunk.startswith(b"%PDF"):
        output_path.unlink(missing_ok=True)
        return False
    return True


def _pdf_contains_doi(pdf_path: Path, doi: str, parser: PDFParser) -> bool:
    content = parser.parse(str(pdf_path))
    text = "\n".join((page.full_text or "") for page in content.pages).lower()
    return doi.lower() in text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-cohort-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pdf-dir", type=Path, required=True)
    parser.add_argument("--unpaywall-email", type=str, default=DEFAULT_EMAIL)
    parser.add_argument("--request-timeout-sec", type=float, default=25.0)
    parser.add_argument("--sleep-sec", type=float, default=0.1)
    parser.add_argument("--max-attempts", type=int, default=None)
    args = parser.parse_args()

    manifest_path = args.input_cohort_dir / "manifest.jsonl"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")

    input_protocol_path = args.input_cohort_dir / "protocol_lock.json"
    input_protocol = _load_json(input_protocol_path) if input_protocol_path.exists() else {}
    rows = _load_jsonl(manifest_path)
    parser_pdf = PDFParser()

    stats = Counter()
    failures: List[Dict[str, str]] = []
    attempts = 0

    for row in rows:
        if row.get("local_pdf"):
            stats["already_local"] += 1
            continue
        doi = _normalize_doi(row.get("doi"))
        if not doi:
            stats["missing_doi"] += 1
            failures.append({"study_id": row.get("study_id", ""), "reason": "missing_doi"})
            continue
        if args.max_attempts is not None and attempts >= args.max_attempts:
            stats["skipped_max_attempts"] += 1
            continue
        attempts += 1
        stats["attempted_rows"] += 1

        candidates = _fetch_unpaywall_locations(
            doi=doi,
            email=args.unpaywall_email,
            timeout_sec=args.request_timeout_sec,
        )
        if not candidates:
            stats["no_oa_pdf_candidate"] += 1
            failures.append({"study_id": row.get("study_id", ""), "reason": "no_oa_pdf_candidate"})
            continue

        success = False
        for url, host_type in candidates[:5]:
            filename = f"{row.get('study_id', 'study')}__doi.pdf"
            pdf_path = args.pdf_dir / filename
            try:
                if not _download_pdf(url=url, output_path=pdf_path, timeout_sec=args.request_timeout_sec):
                    continue
                if not _pdf_contains_doi(pdf_path=pdf_path, doi=doi, parser=parser_pdf):
                    stats["downloaded_without_doi_match"] += 1
                    pdf_path.unlink(missing_ok=True)
                    continue

                row["pdf_filename"] = filename
                row["pdf_path"] = _relative_path(pdf_path)
                row["local_pdf"] = True
                row["download_status"] = "downloaded_from_unpaywall"
                row["download_url"] = url
                row["content_valid"] = True
                row["content_validation_reason"] = "matched_doi_in_pdf_text"
                row["identity_validation_method"] = "doi_text_match"
                row["unpaywall_host_type"] = host_type
                stats["downloaded_and_validated"] += 1
                success = True
                break
            except Exception as exc:
                failures.append(
                    {
                        "study_id": row.get("study_id", ""),
                        "reason": "download_or_parse_error",
                        "url": url,
                        "error": str(exc)[:200],
                    }
                )
                continue

        if not success:
            row["local_pdf"] = False
            row["download_status"] = row.get("download_status") or "unpaywall_failed"
            row["content_valid"] = False
            row["content_validation_reason"] = row.get("content_validation_reason") or "no_doi_matched_oa_pdf"
            stats["failed_after_candidates"] += 1

        if args.sleep_sec > 0:
            time.sleep(args.sleep_sec)

    frozen_rows = [row for row in rows if row.get("local_pdf")]
    output_manifest = args.output_dir / "manifest.jsonl"
    output_gold = args.output_dir / "frozen_gold.jsonl"
    output_seed = args.output_dir / "seed_results_empty.json"
    output_protocol = args.output_dir / "protocol_lock.json"

    _write_jsonl(output_manifest, rows)
    _write_jsonl(output_gold, [_build_gold_record(row) for row in frozen_rows])
    output_seed.parent.mkdir(parents=True, exist_ok=True)
    output_seed.write_text("[]\n", encoding="utf-8")

    journal_counts_selected = dict(sorted(Counter(str(row.get("journal") or "") for row in rows).items()))
    journal_counts_frozen = dict(sorted(Counter(str(row.get("journal") or "") for row in frozen_rows).items()))
    validation_stats = {
        "passed": len(frozen_rows),
        "failed": len(rows) - len(frozen_rows),
    }

    protocol = {
        "protocol_version": "1.0.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "external_validated_with_unpaywall_fallback",
        "identity_validation_applied": True,
        "parent_cohort_dir": str(args.input_cohort_dir).replace("\\", "/"),
        "parent_protocol_lock": _relative_path(input_protocol_path) if input_protocol_path.exists() else None,
        "selected_trials_total": len(rows),
        "frozen_trials_total": len(frozen_rows),
        "journal_counts_selected": journal_counts_selected,
        "journal_counts_frozen": journal_counts_frozen,
        "validation_stats": validation_stats,
        "augmentation_stats": dict(stats),
        "augmentation_failures_sample": failures[:200],
        "source_protocol_mode": input_protocol.get("mode"),
        "source_validation_stats": input_protocol.get("validation_stats", {}),
        "unpaywall_email": args.unpaywall_email,
        "request_timeout_sec": args.request_timeout_sec,
        "output_manifest": _relative_path(output_manifest),
        "output_frozen_gold": _relative_path(output_gold),
        "output_seed_results": _relative_path(output_seed),
        "pdf_dir": _relative_path(args.pdf_dir),
    }
    output_protocol.parent.mkdir(parents=True, exist_ok=True)
    output_protocol.write_text(json.dumps(protocol, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("Unpaywall augmentation complete")
    print("==============================")
    print(f"Input selected rows: {len(rows)}")
    print(f"Frozen rows after augmentation: {len(frozen_rows)}")
    print(f"Stats: {dict(stats)}")
    print(f"Wrote: {output_manifest}")
    print(f"Wrote: {output_gold}")
    print(f"Wrote: {output_seed}")
    print(f"Wrote: {output_protocol}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
