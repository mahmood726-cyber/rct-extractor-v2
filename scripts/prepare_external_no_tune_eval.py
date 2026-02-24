#!/usr/bin/env python3
"""Prepare a frozen external no-tune evaluation cohort."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "ground_truth" / "external_validation_ground_truth.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "external_no_tune_v1"
DEFAULT_PDF_DIR = PROJECT_ROOT / "test_pdfs" / "external_no_tune_v1" / "pdfs"

RATIO_TYPES = {"HR", "OR", "RR", "IRR", "GMR", "NNT", "NNH"}
DIFF_TYPES = {"MD", "SMD", "ARD", "ARR", "RRR", "RD", "WMD"}


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_jsonl(path: Path) -> List[Dict]:
    records: List[Dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL line {line_number}: {exc}") from exc
    return records


def _write_jsonl(path: Path, records: Iterable[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load_rows_from_module() -> List[Dict]:
    module_path = PROJECT_ROOT / "data" / "external_validation_dataset.py"
    if not module_path.exists():
        raise FileNotFoundError(f"Module source not found: {module_path}")

    spec = importlib.util.spec_from_file_location("external_validation_dataset", str(module_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    trials = getattr(module, "ALL_EXTERNAL_VALIDATION_TRIALS", None)
    if trials is None:
        raise RuntimeError("ALL_EXTERNAL_VALIDATION_TRIALS not found in external_validation_dataset.py")

    rows: List[Dict] = []
    for trial in trials:
        extractions = trial.consensus if trial.consensus else trial.extractor_a
        effects: List[Dict] = []
        for extraction in extractions:
            source_type = extraction.source_type.value if hasattr(extraction.source_type, "value") else str(
                extraction.source_type
            )
            effects.append(
                {
                    "effect_type": extraction.effect_type,
                    "value": extraction.effect_size,
                    "ci_lower": extraction.ci_lower,
                    "ci_upper": extraction.ci_upper,
                    "p_value": extraction.p_value,
                    "outcome": extraction.outcome,
                    "timepoint": extraction.timepoint,
                    "comparison": extraction.comparison,
                    "analysis_population": extraction.analysis_population,
                    "source_type": source_type,
                    "source_text": extraction.source_text,
                    "extractor_id": extraction.extractor_id,
                }
            )

        rows.append(
            {
                "trial_name": trial.trial_name,
                "nct_id": trial.nct_number,
                "pmc_id": trial.pmc_id,
                "pmid": trial.pmid,
                "doi": trial.doi,
                "therapeutic_area": trial.therapeutic_area,
                "journal": trial.journal,
                "year": trial.year,
                "difficulty": getattr(trial.difficulty, "value", str(trial.difficulty)),
                "source": "external_validation_module",
                "effects": effects,
                "source_text": trial.source_text,
            }
        )
    return rows


def _normalize_effect_type(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().upper()
    if not normalized:
        return None
    alias_map = {
        "RISK RATIO": "RR",
        "ODDS RATIO": "OR",
        "HAZARD RATIO": "HR",
        "MEAN DIFFERENCE": "MD",
        "STANDARDIZED MEAN DIFFERENCE": "SMD",
        "STD MEAN DIFFERENCE": "SMD",
        "INCIDENCE RATE RATIO": "IRR",
        "RATE RATIO": "RR",
    }
    return alias_map.get(normalized, normalized)


def _normalize_journal(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def _infer_outcome_type(effect_type: Optional[str]) -> str:
    normalized = _normalize_effect_type(effect_type)
    if normalized in DIFF_TYPES:
        return "continuous"
    if normalized in RATIO_TYPES:
        return "binary"
    return "binary"


def _slug(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "_", lowered)
    lowered = re.sub(r"_+", "_", lowered).strip("_")
    return lowered or "study"


def _normalize_doi(value: object) -> str:
    doi = str(value or "").strip().lower()
    if not doi:
        return ""
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix) :]
    return re.sub(r"\s+", "", doi)


def _normalize_pmid(value: object) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _normalize_pmc_id(value: object) -> str:
    pmc = str(value or "").strip().upper()
    if not pmc:
        return ""
    if not pmc.startswith("PMC"):
        pmc = f"PMC{pmc}"
    return pmc


def _fetch_idconv_record(
    *,
    identifier: str,
    timeout_sec: float,
    cache: Dict[str, Optional[Dict[str, str]]],
) -> Optional[Dict[str, str]]:
    normalized_id = str(identifier or "").strip()
    if not normalized_id:
        return None
    if normalized_id in cache:
        return cache[normalized_id]

    url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={normalized_id}&format=json"
    api_key = str(os.environ.get("NCBI_API_KEY") or "").strip()
    if api_key:
        url = f"{url}&api_key={api_key}"
    request = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception:
        cache[normalized_id] = None
        return None

    records = payload.get("records") or []
    if not records or not isinstance(records[0], dict):
        cache[normalized_id] = None
        return None
    record = records[0]

    normalized = {
        "pmcid": _normalize_pmc_id(record.get("pmcid")),
        "pmid": _normalize_pmid(record.get("pmid")),
        "doi": _normalize_doi(record.get("doi")),
        "requested_id": str(record.get("requested-id") or normalized_id).strip(),
    }
    cache[normalized_id] = normalized
    return normalized


def _resolve_trial_pmc_id(
    *,
    source_pmc_id: object,
    expected_pmid: object,
    expected_doi: object,
    timeout_sec: float,
    cache: Dict[str, Optional[Dict[str, str]]],
) -> Tuple[str, str, Dict[str, str]]:
    source_pmc = _normalize_pmc_id(source_pmc_id)
    pmid_norm = _normalize_pmid(expected_pmid)
    doi_norm = _normalize_doi(expected_doi)

    pmid_record = _fetch_idconv_record(identifier=pmid_norm, timeout_sec=timeout_sec, cache=cache) if pmid_norm else None
    doi_record = _fetch_idconv_record(identifier=doi_norm, timeout_sec=timeout_sec, cache=cache) if doi_norm else None

    pmid_pmc = _normalize_pmc_id((pmid_record or {}).get("pmcid"))
    doi_pmc = _normalize_pmc_id((doi_record or {}).get("pmcid"))

    resolution_details = {
        "source_pmc_id": source_pmc,
        "pmcid_from_pmid": pmid_pmc,
        "pmcid_from_doi": doi_pmc,
    }

    if pmid_pmc:
        if source_pmc and source_pmc == pmid_pmc:
            return pmid_pmc, "source_pmc_verified_by_pmid", resolution_details
        if source_pmc and source_pmc != pmid_pmc:
            return pmid_pmc, "source_pmc_replaced_by_pmid", resolution_details
        return pmid_pmc, "resolved_from_pmid", resolution_details

    if doi_pmc:
        if source_pmc and source_pmc == doi_pmc:
            return doi_pmc, "source_pmc_verified_by_doi", resolution_details
        if source_pmc and source_pmc != doi_pmc:
            return doi_pmc, "source_pmc_replaced_by_doi", resolution_details
        return doi_pmc, "resolved_from_doi", resolution_details

    if source_pmc:
        return source_pmc, "kept_source_pmc_unverified", resolution_details

    return "", "unresolved_no_pmcid", resolution_details


def _fetch_pmc_idconv_record(
    pmc_id: str,
    *,
    timeout_sec: float,
    cache: Dict[str, Dict[str, str]],
) -> Optional[Dict[str, str]]:
    normalized_pmc = _normalize_pmc_id(pmc_id)
    if not normalized_pmc:
        return None
    if normalized_pmc in cache:
        return cache[normalized_pmc]
    url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={normalized_pmc}&format=json"
    api_key = str(os.environ.get("NCBI_API_KEY") or "").strip()
    if api_key:
        url = f"{url}&api_key={api_key}"
    request = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception:
        return None
    records = payload.get("records")
    if not records:
        return None
    record = records[0]
    if not isinstance(record, dict):
        return None
    normalized = {
        "pmid": _normalize_pmid(record.get("pmid")),
        "doi": _normalize_doi(record.get("doi")),
    }
    cache[normalized_pmc] = normalized
    return normalized


def _pmc_metadata_matches_trial(
    *,
    pmc_id: str,
    expected_pmid: object,
    expected_doi: object,
    timeout_sec: float,
    cache: Dict[str, Dict[str, str]],
) -> Tuple[bool, str, Optional[Dict[str, str]]]:
    expected_pmid_norm = _normalize_pmid(expected_pmid)
    expected_doi_norm = _normalize_doi(expected_doi)
    if not expected_pmid_norm and not expected_doi_norm:
        return True, "no_expected_metadata", None

    actual = _fetch_pmc_idconv_record(pmc_id=pmc_id, timeout_sec=timeout_sec, cache=cache)
    if actual is None:
        return False, "idconv_lookup_failed", None

    actual_pmid = actual.get("pmid", "")
    actual_doi = actual.get("doi", "")
    pmid_match = bool(expected_pmid_norm and actual_pmid and expected_pmid_norm == actual_pmid)
    doi_match = bool(expected_doi_norm and actual_doi and expected_doi_norm == actual_doi)
    if pmid_match or doi_match:
        if pmid_match and doi_match:
            return True, "matched_pmid_and_doi", actual
        if pmid_match:
            return True, "matched_pmid", actual
        return True, "matched_doi", actual

    mismatch_fields: List[str] = []
    if expected_pmid_norm and actual_pmid and expected_pmid_norm != actual_pmid:
        mismatch_fields.append("pmid")
    if expected_doi_norm and actual_doi and expected_doi_norm != actual_doi:
        mismatch_fields.append("doi")
    if mismatch_fields:
        return False, f"metadata_mismatch:{'+'.join(mismatch_fields)}", actual
    return False, "metadata_inconclusive", actual


def _pick_primary_effect(effects: Sequence[Dict]) -> Optional[Dict]:
    if not effects:
        return None

    by_priority = {"abstract": 0, "full_text": 1, "table": 2, "forest_plot": 3, "supplementary": 4}
    scored: List[Tuple[int, int, Dict]] = []
    for index, effect in enumerate(effects):
        value = _to_float(effect.get("value"))
        if value is None:
            continue
        source_type = str(effect.get("source_type") or "").strip().lower()
        priority = by_priority.get(source_type, 100)
        scored.append((priority, index, effect))

    if not scored:
        return None

    scored.sort(key=lambda item: (item[0], item[1]))
    return scored[0][2]


def _headers() -> Dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
    }


def _download_pdf_from_url(url: str, output_path: Path, timeout_sec: float) -> bool:
    request = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        content = response.read()
    if not content.startswith(b"%PDF"):
        return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(content)
    return True


def _oa_pdf_url(pmc_id: str, timeout_sec: float) -> Optional[str]:
    oa_url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmc_id}"
    request = urllib.request.Request(oa_url, headers=_headers())
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        xml_payload = response.read().decode("utf-8", errors="replace")
    root = ET.fromstring(xml_payload)
    for link in root.findall(".//link"):
        if link.get("format") != "pdf":
            continue
        href = str(link.get("href") or "")
        if href.startswith("ftp://ftp.ncbi.nlm.nih.gov/"):
            href = href.replace("ftp://ftp.ncbi.nlm.nih.gov/", "https://ftp.ncbi.nlm.nih.gov/")
        if href:
            return href
    return None


def download_pdf_for_pmc(pmc_id: str, output_path: Path, timeout_sec: float) -> Tuple[bool, Optional[str]]:
    normalized_pmc = str(pmc_id).strip()
    if not normalized_pmc:
        return False, None
    if not normalized_pmc.upper().startswith("PMC"):
        normalized_pmc = f"PMC{normalized_pmc}"
    normalized_pmc = normalized_pmc.upper()

    urls = [
        f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={normalized_pmc}&blobtype=pdf",
        f"https://www.ncbi.nlm.nih.gov/pmc/articles/{normalized_pmc}/pdf/",
    ]
    try:
        oa_url = _oa_pdf_url(normalized_pmc, timeout_sec=timeout_sec)
        if oa_url:
            urls.append(oa_url)
    except Exception:
        pass

    seen_urls = set()
    for url in urls:
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        try:
            if _download_pdf_from_url(url, output_path=output_path, timeout_sec=timeout_sec):
                return True, url
        except Exception:
            continue
    return False, None


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _build_gold_record(item: Dict) -> Dict:
    return {
        "study_id": item["study_id"],
        "pdf_filename": item["pdf_filename"],
        "excluded": False,
        "cochrane_effect": item["target_value"],
        "cochrane_ci_lower": item["target_ci_lower"],
        "cochrane_ci_upper": item["target_ci_upper"],
        "cochrane_outcome": item["target_outcome"],
        "cochrane_outcome_type": item["outcome_type"],
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
            "pmc_id": item["pmc_id"],
            "pmid": item.get("pmid"),
            "doi": item.get("doi"),
            "journal": item["journal"],
            "year": item["year"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--source",
        choices=["jsonl", "module"],
        default="jsonl",
        help="Ground-truth source type: jsonl file or data.external_validation_dataset module.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    parser.add_argument(
        "--journal-allowlist",
        type=str,
        default="NEJM,Lancet,AJP",
        help="Comma-separated journal list; empty means no filtering.",
    )
    parser.add_argument("--max-trials", type=int, default=None)
    parser.add_argument(
        "--download-missing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Attempt to download PMCID PDFs when local files are missing.",
    )
    parser.add_argument(
        "--require-local-pdf",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Only include studies with local PDF files in frozen_gold.jsonl.",
    )
    parser.add_argument("--sleep-sec", type=float, default=0.35, help="Pause between download attempts.")
    parser.add_argument("--request-timeout-sec", type=float, default=80.0)
    parser.add_argument(
        "--validate-pdf-content",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Validate PMCID metadata against expected DOI/PMID before freezing.",
    )
    parser.add_argument(
        "--resolve-pmcid-from-metadata",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Resolve/correct PMCID from expected PMID/DOI using NCBI idconv before download. "
            "Useful when source PMCID labels are stale or incorrect."
        ),
    )
    args = parser.parse_args()

    if args.source == "jsonl" and not args.input.exists():
        raise FileNotFoundError(f"Input dataset not found: {args.input}")
    if args.max_trials is not None and args.max_trials <= 0:
        raise ValueError("--max-trials must be > 0 when set.")
    if args.sleep_sec < 0:
        raise ValueError("--sleep-sec must be >= 0.")
    if args.request_timeout_sec <= 0:
        raise ValueError("--request-timeout-sec must be > 0.")

    allowlist_tokens = [token.strip() for token in args.journal_allowlist.split(",") if token.strip()]
    allowlist_normalized = {_normalize_journal(token) for token in allowlist_tokens}
    rank_by_journal = {_normalize_journal(token): index for index, token in enumerate(allowlist_tokens)}
    if args.source == "jsonl":
        rows = _load_jsonl(args.input)
    else:
        rows = _load_rows_from_module()

    selected: List[Dict] = []
    skipped = Counter()
    pmc_resolution_stats = Counter()
    seen_study_ids = set()
    resolve_cache: Dict[str, Optional[Dict[str, str]]] = {}

    for row in rows:
        journal = str(row.get("journal") or "").strip()
        if allowlist_normalized and _normalize_journal(journal) not in allowlist_normalized:
            skipped["journal_filtered"] += 1
            continue

        pmc_id = _normalize_pmc_id(row.get("pmc_id"))
        pmc_resolution_reason = "source_pmc_kept"
        pmc_resolution_details: Dict[str, str] = {}
        if args.resolve_pmcid_from_metadata:
            pmc_id, pmc_resolution_reason, pmc_resolution_details = _resolve_trial_pmc_id(
                source_pmc_id=row.get("pmc_id"),
                expected_pmid=row.get("pmid"),
                expected_doi=row.get("doi"),
                timeout_sec=args.request_timeout_sec,
                cache=resolve_cache,
            )
        else:
            if not pmc_id:
                skipped["missing_pmc_id"] += 1
                continue
        pmc_resolution_stats[pmc_resolution_reason] += 1

        primary_effect = _pick_primary_effect(row.get("effects") or [])
        if primary_effect is None:
            skipped["missing_numeric_effect"] += 1
            continue

        trial_name = str(row.get("trial_name") or pmc_id).strip()
        year = row.get("year")
        study_id = _slug(trial_name)
        if year is not None:
            study_id = f"{study_id}_{year}"
        if study_id in seen_study_ids:
            study_id = f"{study_id}_{pmc_id.lower()}"
        seen_study_ids.add(study_id)

        effect_type = _normalize_effect_type(primary_effect.get("effect_type"))
        target_value = _to_float(primary_effect.get("value"))
        target_ci_lower = _to_float(primary_effect.get("ci_lower"))
        target_ci_upper = _to_float(primary_effect.get("ci_upper"))
        if target_value is None:
            skipped["missing_numeric_effect"] += 1
            continue

        selected.append(
            {
                "study_id": study_id,
                "trial_name": trial_name,
                "journal": journal,
                "year": year,
                "pmc_id": pmc_id,
                "pmc_id_source": _normalize_pmc_id(row.get("pmc_id")),
                "pmc_resolution_reason": pmc_resolution_reason,
                "pmc_resolution_details": pmc_resolution_details,
                "pmid": row.get("pmid"),
                "doi": row.get("doi"),
                "pdf_filename": f"{pmc_id}.pdf" if pmc_id else f"{study_id}_no_pmcid.pdf",
                "target_effect_type": effect_type,
                "target_value": target_value,
                "target_ci_lower": target_ci_lower,
                "target_ci_upper": target_ci_upper,
                "target_outcome": str(primary_effect.get("outcome") or "").strip(),
                "target_source_text": str(primary_effect.get("source_text") or "").strip(),
                "outcome_type": _infer_outcome_type(effect_type),
                "source_dataset": "external_validation_ground_truth",
            }
        )

    if rank_by_journal:
        fallback_rank = len(rank_by_journal)
        selected.sort(
            key=lambda row: (rank_by_journal.get(_normalize_journal(row["journal"]), fallback_rank), row["study_id"])
        )
    else:
        selected.sort(key=lambda row: row["study_id"])
    if args.max_trials is not None:
        selected = selected[: args.max_trials]

    args.pdf_dir.mkdir(parents=True, exist_ok=True)
    download_stats = Counter()
    validation_stats = Counter()
    failed_downloads: List[Dict[str, str]] = []
    idconv_cache: Dict[str, Dict[str, str]] = {}

    for index, row in enumerate(selected, start=1):
        pdf_path = args.pdf_dir / row["pdf_filename"]
        row["pdf_path"] = _relative_path(pdf_path)

        row["local_pdf"] = False
        if not row.get("pmc_id"):
            row["download_status"] = "missing_pmc_id"
            download_stats["missing_pmc_id"] += 1
        elif pdf_path.exists() and pdf_path.stat().st_size > 1024:
            row["local_pdf"] = True
            row["download_status"] = "already_present"
            download_stats["already_present"] += 1
        elif not args.download_missing:
            row["download_status"] = "not_attempted"
            download_stats["not_attempted"] += 1
        else:
            ok, source_url = download_pdf_for_pmc(
                pmc_id=row["pmc_id"],
                output_path=pdf_path,
                timeout_sec=args.request_timeout_sec,
            )
            if ok:
                row["local_pdf"] = True
                row["download_status"] = "downloaded"
                row["download_url"] = source_url
                download_stats["downloaded"] += 1
            else:
                row["download_status"] = "failed"
                failed_downloads.append({"study_id": row["study_id"], "pmc_id": row["pmc_id"]})
                download_stats["failed"] += 1

        if row.get("local_pdf") and args.validate_pdf_content:
            valid, reason, actual = _pmc_metadata_matches_trial(
                pmc_id=row.get("pmc_id", ""),
                expected_pmid=row.get("pmid"),
                expected_doi=row.get("doi"),
                timeout_sec=args.request_timeout_sec,
                cache=idconv_cache,
            )
            row["content_valid"] = valid
            row["content_validation_reason"] = reason
            if actual is not None:
                row["pmc_metadata_pmid"] = actual.get("pmid")
                row["pmc_metadata_doi"] = actual.get("doi")
            if valid:
                validation_stats["passed"] += 1
            else:
                row["local_pdf"] = False
                row["download_status"] = "content_mismatch"
                validation_stats["failed"] += 1
                failed_downloads.append(
                    {
                        "study_id": row["study_id"],
                        "pmc_id": row["pmc_id"],
                        "reason": reason,
                    }
                )
        elif row.get("local_pdf"):
            validation_stats["skipped"] += 1

        print(
            f"[{index}/{len(selected)}] {row['study_id']}: "
            f"{row['download_status']}",
            flush=True,
        )
        if args.sleep_sec > 0:
            time.sleep(args.sleep_sec)

    if args.require_local_pdf:
        frozen_items = [row for row in selected if row.get("local_pdf")]
    else:
        frozen_items = list(selected)

    manifest_path = args.output_dir / "manifest.jsonl"
    frozen_gold_path = args.output_dir / "frozen_gold.jsonl"
    protocol_lock_path = args.output_dir / "protocol_lock.json"
    seed_results_path = args.output_dir / "seed_results_empty.json"

    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(manifest_path, selected)
    _write_jsonl(frozen_gold_path, [_build_gold_record(item) for item in frozen_items])
    seed_results_path.write_text("[]\n", encoding="utf-8")

    journal_counts_all = Counter(row["journal"] for row in selected)
    journal_counts_frozen = Counter(row["journal"] for row in frozen_items)

    source_descriptor = (
        _relative_path(args.input)
        if args.source == "jsonl"
        else "data.external_validation_dataset:ALL_EXTERNAL_VALIDATION_TRIALS"
    )
    source_sha = _sha256_file(args.input) if args.source == "jsonl" else None

    protocol = {
        "protocol_version": "1.0.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "external_no_tune",
        "source": args.source,
        "input_dataset": source_descriptor,
        "input_dataset_sha256": source_sha,
        "output_manifest": _relative_path(manifest_path),
        "output_manifest_sha256": _sha256_file(manifest_path),
        "output_frozen_gold": _relative_path(frozen_gold_path),
        "output_frozen_gold_sha256": _sha256_file(frozen_gold_path),
        "output_seed_results": _relative_path(seed_results_path),
        "output_seed_results_sha256": _sha256_file(seed_results_path),
        "pdf_dir": _relative_path(args.pdf_dir),
        "require_local_pdf": args.require_local_pdf,
        "download_missing": args.download_missing,
        "validate_pdf_content": args.validate_pdf_content,
        "resolve_pmcid_from_metadata": args.resolve_pmcid_from_metadata,
        "pmc_resolution_stats": dict(sorted(pmc_resolution_stats.items())),
        "requested_journal_allowlist": allowlist_tokens,
        "selected_trials_total": len(selected),
        "frozen_trials_total": len(frozen_items),
        "journal_counts_selected": dict(sorted(journal_counts_all.items())),
        "journal_counts_frozen": dict(sorted(journal_counts_frozen.items())),
        "download_stats": dict(download_stats),
        "validation_stats": dict(validation_stats),
        "skipped_rows": dict(skipped),
        "failed_downloads": failed_downloads,
    }
    protocol_lock_path.write_text(
        json.dumps(protocol, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("\nExternal no-tune cohort prepared")
    print("================================")
    print(f"Selected trials: {len(selected)}")
    print(f"Frozen trials:   {len(frozen_items)}")
    print(f"Journal counts (selected): {dict(sorted(journal_counts_all.items()))}")
    if args.resolve_pmcid_from_metadata:
        print(f"PMCID resolution stats: {dict(sorted(pmc_resolution_stats.items()))}")
    print(f"Download stats: {dict(download_stats)}")
    print(f"Validation stats: {dict(validation_stats)}")
    print(f"Wrote: {manifest_path}")
    print(f"Wrote: {frozen_gold_path}")
    print(f"Wrote: {seed_results_path}")
    print(f"Wrote: {protocol_lock_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
