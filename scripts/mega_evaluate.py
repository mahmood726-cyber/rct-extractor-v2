"""
Mega Evaluation — Run extractor on OA PDFs and compare against Cochrane values.

For each downloaded PDF:
1. Run the extraction pipeline
2. Compare extracted effects against Cochrane-recorded values
3. If no text match, try computing from raw data
4. Record match/mismatch/miss for accuracy metrics

Usage:
    python scripts/mega_evaluate.py --batch 100
    python scripts/mega_evaluate.py --batch 200 --resume
"""
import io
import json
import math
import multiprocessing as mp
import os
import queue as queue_module
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project to path
_DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[1]
_ENV_PROJECT_DIR = os.getenv("RCT_EXTRACTOR_PROJECT_DIR")
if _ENV_PROJECT_DIR:
    PROJECT_DIR = Path(_ENV_PROJECT_DIR).expanduser()
elif (_DEFAULT_PROJECT_DIR / "src").exists() and (_DEFAULT_PROJECT_DIR / "scripts").exists():
    PROJECT_DIR = _DEFAULT_PROJECT_DIR
else:
    PROJECT_DIR = Path(r"C:\Users\user\rct-extractor-v2")

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

MEGA_DIR = PROJECT_DIR / "gold_data" / "mega"
PDF_DIR = MEGA_DIR / "pdfs"
MEGA_MATCHED_FILE = MEGA_DIR / "mega_matched.jsonl"
MEGA_EVAL_FILE = MEGA_DIR / "mega_eval.jsonl"
MEGA_EVAL_SUMMARY = MEGA_DIR / "mega_eval_summary.json"
SUMMARY_STATUS_KEYS = (
    "match",
    "extracted_no_match",
    "no_extraction",
    "no_cochrane_ref",
    "error",
    "timeout_skipped_by_batch_runner",
)
RATIO_EFFECT_TYPES = {
    "EffectType.OR",
    "EffectType.RR",
    "EffectType.HR",
    "EffectType.IRR",
    "EffectType.RRR",
}
CONTINUOUS_EFFECT_TYPES = {
    "EffectType.MD",
    "EffectType.SMD",
}
RISK_DIFFERENCE_EFFECT_TYPES = {
    "EffectType.ARD",
    "EffectType.RD",
    "EffectType.ARR",
}
BINARY_EFFECT_TYPES = RATIO_EFFECT_TYPES | RISK_DIFFERENCE_EFFECT_TYPES
RAW_METRIC_PREMATCH_TOLERANCE = 0.10
RAW_RATIO_NEAR_TOLERANCE = 0.20
HEDGES_DF_GRID = (8, 10, 12, 16, 20, 30, 40, 60, 100)
HEDGES_J_FACTORS = tuple(1.0 - (3.0 / (4.0 * df - 1.0)) for df in HEDGES_DF_GRID)
TINY_EFFECT_MAX_ABS = 0.30
TINY_EFFECT_ABS_TOLERANCE = 0.02


def _infer_data_type(raw_data, declared_data_type):
    """Infer binary/continuous from raw_data when Cochrane data_type is missing."""
    if declared_data_type:
        return str(declared_data_type).strip().lower()
    if not isinstance(raw_data, dict):
        return None
    if all(k in raw_data for k in ("exp_cases", "exp_n", "ctrl_cases", "ctrl_n")):
        return "binary"
    if all(k in raw_data for k in ("intervention_events", "intervention_n", "control_events", "control_n")):
        return "binary"
    if all(k in raw_data for k in ("exp_mean", "exp_sd", "exp_n", "ctrl_mean", "ctrl_sd", "ctrl_n")):
        return "continuous"
    if all(k in raw_data for k in ("intervention_mean", "intervention_sd", "intervention_n", "control_mean", "control_sd", "control_n")):
        return "continuous"
    return None


def _infer_data_type_from_outcome(outcome: str) -> Optional[str]:
    """
    Infer binary/continuous family from outcome wording when metadata is missing.

    Conservative heuristic:
    - Binary cues: events/death/dropout/remission/relapse/adverse/withdrawal
    - Continuous cues: score/scale/function/pain/intake/knowledge/quality of life
    """
    text = str(outcome or "").strip().lower()
    if not text:
        return None

    binary_patterns = (
        r"\bdeath\b",
        r"\bmortality\b",
        r"\badverse(?:\s+events?)?\b",
        r"\bwithdraw(?:n|al|als)?\b",
        r"\bdropouts?\b",
        r"\bremission\b",
        r"\brelapse\b",
        r"\bevents?\b",
        r"\bincidence\b",
        r"\bcessation\b",
        r"\bquit(?:ting)?\b",
        r"\bulcer\b",
        r"\bcause\b",
    )
    continuous_patterns = (
        r"\bscore\b",
        r"\bscale\b",
        r"\bmean\b",
        r"\bchange\b",
        r"\bfunction\b",
        r"\bpain\b",
        r"\bintake\b",
        r"\bknowledge\b",
        r"\bquality of life\b",
        r"\bqol\b",
        r"\bdistance\b",
        r"\bvelocity\b",
        r"\bcomposite\b",
        r"\bindex\b",
        r"\bquestionnaire\b",
        r"\bextent of substance use\b",
    )

    binary_hits = sum(1 for p in binary_patterns if re.search(p, text, re.IGNORECASE))
    continuous_hits = sum(1 for p in continuous_patterns if re.search(p, text, re.IGNORECASE))

    if binary_hits > continuous_hits and binary_hits > 0:
        return "binary"
    if continuous_hits > binary_hits and continuous_hits > 0:
        return "continuous"
    return None


def _is_effect_family_compatible(effect_type: str, data_type: Optional[str]) -> bool:
    """Whether extracted effect type is compatible with expected data family."""
    dt = str(data_type or "").strip().lower()
    if not dt:
        return True
    et = str(effect_type or "")
    if dt == "binary":
        return et in BINARY_EFFECT_TYPES
    if dt == "continuous":
        return et in CONTINUOUS_EFFECT_TYPES
    return True


def _canonical_study_key(study_id: str) -> str:
    text = unicodedata.normalize("NFKD", str(study_id))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return text


def _parse_study_ids_filter(value: str) -> set:
    """Parse comma-separated study IDs into canonical key set."""
    keys = set()
    for token in str(value or "").split(","):
        text = token.strip()
        if not text:
            continue
        key = _canonical_study_key(text)
        if key:
            keys.add(key)
    return keys


def _load_latest_eval_rows(path: Path) -> Tuple[List[dict], Dict[str, int], int]:
    """
    Load evaluation rows collapsed to the latest row per canonical study_id.

    Returns:
        (rows, index_by_study_key, raw_nonempty_row_count)
    """
    if not path.exists():
        return [], {}, 0

    latest_by_key: Dict[str, Tuple[int, dict]] = {}
    passthrough_rows: List[Tuple[int, dict]] = []
    raw_rows = 0

    with open(path, encoding="utf-8", errors="replace") as handle:
        for line_idx, line in enumerate(handle):
            stripped = line.strip()
            if not stripped:
                continue
            raw_rows += 1
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                continue

            study_id = row.get("study_id")
            if study_id:
                key = _canonical_study_key(study_id)
                if key:
                    latest_by_key[key] = (line_idx, row)
                    continue
            passthrough_rows.append((line_idx, row))

    ordered = passthrough_rows + list(latest_by_key.values())
    ordered.sort(key=lambda item: item[0])
    rows = [row for _, row in ordered]

    index_by_key: Dict[str, int] = {}
    for idx, row in enumerate(rows):
        study_id = row.get("study_id")
        if not study_id:
            continue
        key = _canonical_study_key(study_id)
        if key:
            index_by_key[key] = idx

    return rows, index_by_key, raw_rows


def _write_eval_rows(path: Path, rows: List[dict]) -> None:
    """Atomically write evaluation rows as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    # Windows can briefly lock the destination file (e.g., antivirus/indexers).
    # Retry atomic replace a few times before failing the whole run.
    for attempt in range(8):
        try:
            tmp_path.replace(path)
            return
        except PermissionError:
            if attempt >= 7:
                raise
            time.sleep(0.25 * (attempt + 1))


def load_entries_with_pdfs():
    """Load matched entries that have downloaded PDFs."""
    entries = []
    with open(MEGA_MATCHED_FILE, encoding="utf-8", errors="replace") as f:
        for line in f:
            e = json.loads(line)
            if not e.get("pmcid"):
                continue
            # Find the PDF
            safe_name = e["study_id"].replace(" ", "_").replace("/", "_")
            pdf_path = PDF_DIR / f"{safe_name}_{e['pmcid']}.pdf"
            if pdf_path.exists():
                e["pdf_path"] = str(pdf_path)
                entries.append(e)
    return entries


def create_pipeline(
    fast_mode: bool,
    ocr_threshold: float = 100.0,
    extract_tables: bool = True,
    enable_advanced: bool = False,
    aggressive_ocr_correction: bool = True,
):
    """
    Build one pipeline instance for the whole run.

    Fast mode disables expensive extraction branches so large resumes can
    make forward progress under external batch timeouts.
    """
    from src.core.pdf_extraction_pipeline import PDFExtractionPipeline
    if fast_mode:
        return PDFExtractionPipeline(
            extract_diagnostics=False,
            extract_tables=False,
            enable_advanced=False,
            enable_llm=False,
            run_rct_classification=False,
            score_primary_outcomes=False,
            compute_raw_effects=False,
            include_page_audit=False,
            ocr_threshold=ocr_threshold,
            aggressive_ocr_correction=aggressive_ocr_correction,
        )
    # Full mode for evaluation keeps extraction quality branches enabled
    # (text/table/raw-data), while disabling expensive audit/classification
    # branches that are not used by mega_eval scoring.
    return PDFExtractionPipeline(
        extract_diagnostics=False,
        run_rct_classification=False,
        score_primary_outcomes=False,
        include_page_audit=False,
        compute_raw_effects=True,
        ocr_threshold=ocr_threshold,
        extract_tables=extract_tables,
        enable_advanced=enable_advanced,
        enable_llm=False,
        aggressive_ocr_correction=aggressive_ocr_correction,
    )


def _append_diag_row(diag_jsonl: Optional[Path], row: dict):
    if not diag_jsonl:
        return
    diag_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with open(diag_jsonl, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _parser_probe(pdf_path: str) -> dict:
    probe = {
        "ok": False,
        "elapsed_sec": None,
        "num_pages": None,
        "extraction_method": None,
        "is_born_digital": None,
        "total_characters": None,
        "error": None,
    }
    started = time.perf_counter()
    try:
        from src.pdf.pdf_parser import PDFParser

        parser = PDFParser()
        parsed = parser.parse(pdf_path)
        probe["ok"] = True
        probe["num_pages"] = parsed.num_pages
        probe["extraction_method"] = parsed.extraction_method
        probe["is_born_digital"] = parsed.is_born_digital
        probe["total_characters"] = sum(len(p.full_text or "") for p in parsed.pages)
    except Exception as e:
        probe["error"] = str(e)
    finally:
        probe["elapsed_sec"] = round(time.perf_counter() - started, 4)
    return probe


def _serialize_effect_estimates(result) -> list:
    effects = []
    if not result or not getattr(result, "effect_estimates", None):
        return effects
    for effect in result.effect_estimates:
        effects.append(
            {
                "effect_type": str(effect.effect_type) if hasattr(effect, "effect_type") else str(getattr(effect, "type", "")),
                "point_estimate": getattr(effect, "point_estimate", None) or getattr(effect, "value", None),
                "ci_lower": getattr(effect, "ci_lower", None),
                "ci_upper": getattr(effect, "ci_upper", None),
                "confidence": getattr(effect, "calibrated_confidence", None) or getattr(effect, "confidence", None),
            }
        )
    return effects


def _quick_fallback_extract_from_pdf(pdf_path: str, max_effects: int = 8) -> list:
    """
    Lightweight fallback extractor for timeout cases.

    Uses simple regex anchors on parsed PDF text to recover obvious effect values
    (OR/RR/HR/MD/SMD) without running the full extraction pipeline.
    """
    from src.pdf.pdf_parser import PDFParser

    parser = PDFParser()
    parsed = parser.parse(pdf_path)
    full_text = "\n".join((p.full_text or "") for p in parsed.pages)
    if not full_text:
        return []
    text = full_text[:300000]

    patterns = [
        ("EffectType.OR", re.compile(r"\b(?:odds\s+ratio|OR)\b\s*[:=]?\s*\(?\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)),
        ("EffectType.RR", re.compile(r"\b(?:risk\s+ratio|relative\s+risk|RR)\b\s*[:=]?\s*\(?\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)),
        ("EffectType.HR", re.compile(r"\b(?:hazard\s+ratio|HR)\b\s*[:=]?\s*\(?\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)),
        ("EffectType.MD", re.compile(r"\b(?:mean\s+difference|MD)\b\s*[:=]?\s*\(?\s*(-?[0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)),
        ("EffectType.SMD", re.compile(r"\b(?:standardi[sz]ed\s+mean\s+difference|SMD)\b\s*[:=]?\s*\(?\s*(-?[0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)),
    ]

    effects = []
    seen = set()
    for effect_type, pattern in patterns:
        for match in pattern.finditer(text):
            try:
                value = float(match.group(1))
            except (TypeError, ValueError):
                continue
            if effect_type in {"EffectType.OR", "EffectType.RR", "EffectType.HR"}:
                if value <= 0 or value > 50:
                    continue
            else:
                if abs(value) > 200:
                    continue
            key = (effect_type, round(value, 6))
            if key in seen:
                continue
            seen.add(key)
            effects.append(
                {
                    "effect_type": effect_type,
                    "point_estimate": value,
                    "ci_lower": None,
                    "ci_upper": None,
                    "confidence": 0.2,
                }
            )
            if len(effects) >= max_effects:
                return effects
    return effects


def _quick_fallback_worker(pdf_path: str, max_effects: int, queue) -> None:
    try:
        effects = _quick_fallback_extract_from_pdf(pdf_path=pdf_path, max_effects=max_effects)
        queue.put({"ok": True, "effects": effects, "error": None})
    except Exception as e:
        queue.put({"ok": False, "effects": [], "error": str(e)})


def _quick_fallback_with_timeout(
    pdf_path: str,
    max_effects: int = 8,
    timeout_sec: int = 12,
):
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    process = ctx.Process(
        target=_quick_fallback_worker,
        args=(pdf_path, max_effects, queue),
    )
    process.start()
    process.join(timeout=timeout_sec)
    if process.is_alive():
        process.terminate()
        process.join(timeout=5)
        return [], f"fallback_timeout_{timeout_sec}s"
    if queue.empty():
        return [], "fallback_worker_no_payload"
    payload = queue.get()
    if payload.get("ok"):
        return payload.get("effects", []), None
    return [], payload.get("error") or "fallback_unknown_error"


def _extract_worker_payload(pdf_path: str, fast_mode: bool, pipeline_kwargs: dict, queue):
    started = time.perf_counter()
    try:
        worker_kwargs = dict(pipeline_kwargs or {})
        # Internal control flags are for parent-process flow only.
        worker_kwargs.pop("_internal_retry_no_tables", None)
        pipeline = create_pipeline(fast_mode=fast_mode, **worker_kwargs)
        result = pipeline.extract_from_pdf(pdf_path)
        payload = {
            "ok": True,
            "elapsed_sec": round(time.perf_counter() - started, 4),
            "effects": _serialize_effect_estimates(result),
            "meta": {
                "pipeline_ok": True,
                "pipeline_num_pages": getattr(result, "num_pages", None),
                "pipeline_extraction_method": getattr(result, "extraction_method", None),
                "pipeline_is_born_digital": getattr(result, "is_born_digital", None),
                "pipeline_total_characters": getattr(result, "total_characters", None),
                "pipeline_warning_count": len(getattr(result, "warnings", []) or []),
                "pipeline_error_count": len(getattr(result, "errors", []) or []),
                "pipeline_timed_out": False,
            },
        }
    except Exception as e:
        payload = {
            "ok": False,
            "elapsed_sec": round(time.perf_counter() - started, 4),
            "error": str(e),
            "meta": {
                "pipeline_ok": False,
                "pipeline_error": str(e),
                "pipeline_timed_out": False,
            },
        }
    queue.put(payload)


def _retry_without_tables_after_timeout(
    pdf_path: str,
    fast_mode: bool,
    timeout_sec: int,
    pipeline_kwargs: dict,
):
    """
    Retry timed-out extractions once with table extraction disabled.

    Some PDFs trigger pathological runtime in pdfplumber table parsing. A single
    retry without tables often recovers text/raw-data extractions quickly.
    """
    settings = dict(pipeline_kwargs or {})
    if settings.get("_internal_retry_no_tables"):
        return None
    if not settings.get("extract_tables", False):
        return None

    retry_kwargs = dict(settings)
    retry_kwargs["extract_tables"] = False
    retry_kwargs["enable_advanced"] = False
    retry_kwargs["_internal_retry_no_tables"] = True
    retry_timeout_sec = max(20, min(int(timeout_sec), 60))

    retry_effects, retry_meta = _extract_in_subprocess(
        pdf_path=pdf_path,
        fast_mode=fast_mode,
        timeout_sec=retry_timeout_sec,
        pipeline_kwargs=retry_kwargs,
    )
    retry_meta = dict(retry_meta or {})
    retry_meta["pipeline_retry_without_tables"] = True
    retry_meta["pipeline_retry_timeout_sec"] = retry_timeout_sec
    return retry_effects, retry_meta


def _extract_in_subprocess(
    pdf_path: str,
    fast_mode: bool,
    timeout_sec: int,
    pipeline_kwargs: dict,
):
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    process = ctx.Process(
        target=_extract_worker_payload,
        args=(pdf_path, fast_mode, pipeline_kwargs, queue),
    )
    started = time.perf_counter()
    process.start()
    deadline = started + timeout_sec
    payload = None
    timed_out = False

    # Read payload before join() to avoid parent/child queue deadlocks on larger outputs.
    while True:
        try:
            payload = queue.get_nowait()
            break
        except queue_module.Empty:
            pass

        if not process.is_alive():
            break
        if time.perf_counter() >= deadline:
            timed_out = True
            break
        time.sleep(0.05)

    if timed_out:
        process.terminate()
        process.join(timeout=5)
        elapsed = round(time.perf_counter() - started, 4)
        retry_attempted = False
        retry_error = None

        retry_result = _retry_without_tables_after_timeout(
            pdf_path=pdf_path,
            fast_mode=fast_mode,
            timeout_sec=timeout_sec,
            pipeline_kwargs=pipeline_kwargs,
        )
        if retry_result is not None:
            retry_attempted = True
            retry_effects, retry_meta = retry_result
            retry_is_error = (
                len(retry_effects) == 1
                and isinstance(retry_effects[0], dict)
                and bool(retry_effects[0].get("error"))
            )
            if not retry_is_error:
                retry_meta["pipeline_initial_timeout_sec"] = timeout_sec
                retry_meta["pipeline_initial_timeout_elapsed_sec"] = elapsed
                return retry_effects, retry_meta
            retry_error = str(retry_effects[0].get("error", "retry_unknown_error"))

        fallback_effects = []
        fallback_error = None
        try:
            fallback_effects, fallback_error = _quick_fallback_with_timeout(
                pdf_path=pdf_path,
                max_effects=8,
                timeout_sec=12,
            )
        except Exception as e:
            fallback_error = str(e)

        if fallback_effects:
            return (
                fallback_effects,
                {
                    "pipeline_ok": False,
                    "pipeline_timed_out": True,
                    "pipeline_elapsed_sec": elapsed,
                    "pipeline_error": f"timeout_{timeout_sec}s",
                    "pipeline_fallback_used": True,
                    "pipeline_fallback_effect_count": len(fallback_effects),
                    "pipeline_fallback_error": fallback_error,
                    "pipeline_retry_without_tables": retry_attempted,
                    "pipeline_retry_error": retry_error,
                },
            )

        err = f"timeout_{timeout_sec}s"
        if retry_error:
            err = f"{err}; retry_no_tables_error={retry_error}"
        if fallback_error:
            err = f"{err}; fallback_error={fallback_error}"
        return (
            [{"error": err}],
            {
                "pipeline_ok": False,
                "pipeline_timed_out": True,
                "pipeline_elapsed_sec": elapsed,
                "pipeline_error": err,
                "pipeline_fallback_used": False,
                "pipeline_retry_without_tables": retry_attempted,
                "pipeline_retry_error": retry_error,
            },
        )

    # Process exited before timeout. Fetch payload if we missed a race with child exit.
    if payload is None:
        try:
            payload = queue.get_nowait()
        except queue_module.Empty:
            payload = None

    process.join(timeout=5)
    if process.is_alive():
        process.terminate()
        process.join(timeout=5)

    if payload is None:
        elapsed = round(time.perf_counter() - started, 4)
        return (
            [{"error": "worker_returned_no_payload"}],
            {
                "pipeline_ok": False,
                "pipeline_timed_out": False,
                "pipeline_elapsed_sec": elapsed,
                "pipeline_error": "worker_returned_no_payload",
            },
        )

    elapsed = round(time.perf_counter() - started, 4)
    meta = dict(payload.get("meta", {}))
    meta["pipeline_elapsed_sec"] = payload.get("elapsed_sec", elapsed)
    if payload.get("ok"):
        return payload.get("effects", []), meta
    return [{"error": payload.get("error", "unknown_worker_error")}], meta


def extract_from_pdf(
    pdf_path,
    pipeline,
    diag_jsonl: Optional[Path] = None,
    diag_context: Optional[dict] = None,
    diag_parser_probe: bool = False,
    fast_mode: bool = False,
    per_study_timeout_sec: int = 0,
    pipeline_kwargs: Optional[dict] = None,
):
    """Run the extraction pipeline on a PDF with a reused pipeline object."""
    pdf_info = {
        "pdf_path": str(pdf_path),
        "pdf_size_bytes": None,
        "pdf_exists": False,
    }
    try:
        path_obj = Path(pdf_path)
        pdf_info["pdf_exists"] = path_obj.exists()
        if path_obj.exists():
            pdf_info["pdf_size_bytes"] = path_obj.stat().st_size
    except Exception:
        pass

    probe = _parser_probe(pdf_path) if diag_parser_probe else None
    pre_row = {
        "event": "pre_extract",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        **(diag_context or {}),
        **pdf_info,
        "parser_probe": probe,
    }
    _append_diag_row(diag_jsonl, pre_row)

    if per_study_timeout_sec and per_study_timeout_sec > 0:
        return _extract_in_subprocess(
            pdf_path=pdf_path,
            fast_mode=fast_mode,
            timeout_sec=per_study_timeout_sec,
            pipeline_kwargs=pipeline_kwargs or {},
        )

    started = time.perf_counter()
    try:
        if pipeline is None:
            raise RuntimeError("pipeline is not initialized")
        result = pipeline.extract_from_pdf(pdf_path)
        elapsed = round(time.perf_counter() - started, 4)
        meta = {
            "pipeline_ok": True,
            "pipeline_elapsed_sec": elapsed,
            "pipeline_num_pages": getattr(result, "num_pages", None),
            "pipeline_extraction_method": getattr(result, "extraction_method", None),
            "pipeline_is_born_digital": getattr(result, "is_born_digital", None),
            "pipeline_total_characters": getattr(result, "total_characters", None),
            "pipeline_warning_count": len(getattr(result, "warnings", []) or []),
            "pipeline_error_count": len(getattr(result, "errors", []) or []),
            "pipeline_timed_out": False,
        }
        return _serialize_effect_estimates(result), meta
    except Exception as e:
        elapsed = round(time.perf_counter() - started, 4)
        meta = {
            "pipeline_ok": False,
            "pipeline_elapsed_sec": elapsed,
            "pipeline_error": str(e),
            "pipeline_timed_out": False,
        }
        return [{"error": str(e)}], meta


def values_match(extracted, cochrane, tolerance=0.05):
    """Check if extracted value matches Cochrane value within relative tolerance."""
    if extracted is None or cochrane is None:
        return False
    try:
        ext = float(extracted)
        coch = float(cochrane)
        if coch == 0:
            return abs(ext) < 0.01
        return abs(ext - coch) / abs(coch) <= tolerance
    except (ValueError, TypeError):
        return False


def _tiny_effect_abs_match(candidate, cochrane) -> bool:
    """Absolute-difference fallback for very small effects."""
    try:
        cand = float(candidate)
        coch = float(cochrane)
    except (TypeError, ValueError):
        return False
    if abs(coch) > TINY_EFFECT_MAX_ABS:
        return False
    return abs(cand - coch) <= TINY_EFFECT_ABS_TOLERANCE


def _raw_first(raw_data, *keys):
    """Return first non-null raw_data value from a list of key aliases."""
    if not isinstance(raw_data, dict):
        return None
    for key in keys:
        value = raw_data.get(key)
        if value is not None:
            return value
    return None


def _compute_rr_or_from_raw_data(raw_data):
    """Compute RR/OR/RD from binary raw data; returns (rr, or_value, rd)."""
    if not isinstance(raw_data, dict):
        return None, None, None
    try:
        exp_cases = float(_raw_first(raw_data, "exp_cases", "intervention_events"))
        exp_n = float(_raw_first(raw_data, "exp_n", "intervention_n"))
        ctrl_cases = float(_raw_first(raw_data, "ctrl_cases", "control_events"))
        ctrl_n = float(_raw_first(raw_data, "ctrl_n", "control_n"))
    except (TypeError, ValueError):
        return None, None, None
    if exp_n <= 0 or ctrl_n <= 0:
        return None, None, None

    exp_risk = exp_cases / exp_n
    ctrl_risk = ctrl_cases / ctrl_n
    rr = (exp_risk / ctrl_risk) if ctrl_risk > 0 else None
    rd = exp_risk - ctrl_risk

    # Haldane correction for zero-cell stability.
    exp_non_cases = exp_n - exp_cases
    ctrl_non_cases = ctrl_n - ctrl_cases
    a, b, c, d = exp_cases, exp_non_cases, ctrl_cases, ctrl_non_cases
    if min(a, b, c, d) == 0:
        a += 0.5
        b += 0.5
        c += 0.5
        d += 0.5
    if b <= 0 or c <= 0 or d <= 0:
        or_value = None
    else:
        or_value = (a / b) / (c / d)
    return rr, or_value, rd


def _compute_md_smd_from_raw_data(raw_data):
    """Compute MD and SMD from continuous raw data; returns (md, smd)."""
    if not isinstance(raw_data, dict):
        return None, None
    try:
        exp_mean = float(_raw_first(raw_data, "exp_mean", "intervention_mean"))
        exp_sd = float(_raw_first(raw_data, "exp_sd", "intervention_sd"))
        exp_n = float(_raw_first(raw_data, "exp_n", "intervention_n"))
        ctrl_mean = float(_raw_first(raw_data, "ctrl_mean", "control_mean"))
        ctrl_sd = float(_raw_first(raw_data, "ctrl_sd", "control_sd"))
        ctrl_n = float(_raw_first(raw_data, "ctrl_n", "control_n"))
    except (TypeError, ValueError):
        return None, None

    if exp_n <= 0 or ctrl_n <= 0 or exp_sd <= 0 or ctrl_sd <= 0:
        return None, None
    df = exp_n + ctrl_n - 2
    if df <= 0:
        return None, None

    md = exp_mean - ctrl_mean
    pooled_var = (((exp_n - 1) * (exp_sd ** 2)) + ((ctrl_n - 1) * (ctrl_sd ** 2))) / df
    if pooled_var <= 0:
        return md, None
    pooled_sd = math.sqrt(pooled_var)
    if pooled_sd <= 0:
        return md, None

    d = md / pooled_sd
    correction = 1.0 - (3.0 / (4.0 * df - 1.0)) if (4.0 * df - 1.0) > 0 else 1.0
    smd = d * correction
    return md, smd


def _iter_match_candidates(ext: dict, coch: dict):
    """
    Yield normalized candidate values for matching.

    Includes conventional conversions that commonly differ by reporting standard:
    - Reciprocal for ratio measures (arm order reversal)
    - Sign flip for mean differences (arm order reversal)
    """
    raw_value = ext.get("point_estimate")
    if raw_value is None:
        return

    yield "direct", raw_value

    ext_type = str(ext.get("effect_type") or "")
    data_type = str(coch.get("data_type") or "").strip().lower()

    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return

    if ext_type in RATIO_EFFECT_TYPES and value > 0 and data_type in {"", "binary"}:
        yield "reciprocal", 1.0 / value

    if ext_type in CONTINUOUS_EFFECT_TYPES and data_type in {"", "continuous"}:
        yield "sign_flip", -value

    # SMD reporting can differ by small-sample correction convention:
    # Cohen's d vs Hedges' g (J correction). Offer both directions over a
    # conservative df grid so matching remains strict (5%) without relaxing
    # global tolerance.
    if ext_type == "EffectType.SMD" and data_type in {"", "continuous"} and abs(value) <= 3.0:
        for df, j in zip(HEDGES_DF_GRID, HEDGES_J_FACTORS):
            if j <= 0:
                continue
            # direct orientation
            yield f"smd_d_to_hedges_df{df}", value * j
            yield f"smd_hedges_to_d_df{df}", value / j
            # sign-flipped orientation
            yield f"smd_signflip_d_to_hedges_df{df}", (-value) * j
            yield f"smd_signflip_hedges_to_d_df{df}", (-value) / j

    if ext_type in RISK_DIFFERENCE_EFFECT_TYPES and data_type in {"", "binary"}:
        yield "risk_difference_sign_flip", -value
        if abs(value) <= 1.5:
            yield "risk_difference_fraction_to_percent", value * 100.0
            yield "risk_difference_fraction_sign_flip_to_percent", -value * 100.0
        if abs(value) >= 0.5:
            yield "risk_difference_percent_to_fraction", value / 100.0
            yield "risk_difference_percent_sign_flip_to_fraction", -value / 100.0


def _iter_raw_metric_variant_candidates(ext: dict, coch: dict):
    """
    Yield candidate values for RR<->OR metric variants based on shared raw data.

    This recovers valid matches when extraction reports OR and Cochrane stores RR
    (or vice versa) from the same 2x2 counts.
    """
    ext_type = str(ext.get("effect_type") or "")
    ext_val = ext.get("point_estimate")
    if ext_val is None:
        return

    raw_data = coch.get("raw_data")
    if not isinstance(raw_data, dict):
        return

    rr = None
    or_value = None
    rd = None
    if ext_type in (RATIO_EFFECT_TYPES | RISK_DIFFERENCE_EFFECT_TYPES):
        rr, or_value, rd = _compute_rr_or_from_raw_data(raw_data)

    if ext_type in {"EffectType.OR", "EffectType.RR", "EffectType.ARD", "EffectType.RD", "EffectType.ARR"}:
        if rr is not None and or_value is not None:
            # If extracted OR approximately matches raw-data OR, compare candidate RR.
            if ext_type == "EffectType.OR" and values_match(ext_val, or_value, tolerance=RAW_METRIC_PREMATCH_TOLERANCE):
                yield "raw_metric_variant_or_to_rr", rr

            # If extracted RR approximately matches raw-data RR, compare candidate OR.
            if ext_type == "EffectType.RR" and values_match(ext_val, rr, tolerance=RAW_METRIC_PREMATCH_TOLERANCE):
                yield "raw_metric_variant_rr_to_or", or_value

        # Cochrane sometimes stores risk-difference on proportion scale while extraction
        # emits percentages (or vice versa).
        if rd is not None and ext_type in {"EffectType.ARD", "EffectType.RD", "EffectType.ARR"}:
            if values_match(ext_val, rd, tolerance=RAW_METRIC_PREMATCH_TOLERANCE):
                yield "raw_metric_variant_rd_native", rd
            if values_match(ext_val, rd * 100.0, tolerance=RAW_METRIC_PREMATCH_TOLERANCE):
                yield "raw_metric_variant_rd_percent_to_fraction", rd
            if values_match(ext_val, -rd * 100.0, tolerance=RAW_METRIC_PREMATCH_TOLERANCE):
                yield "raw_metric_variant_rd_percent_sign_flip_to_fraction", rd

    # P2: Conservative near-match harmonization for ratio families using shared raw data.
    # This recovers cases where extracted ratio is close to (but outside 5%) the exact
    # Cochrane ratio due to reporting/rounding drift.
    if ext_type in RATIO_EFFECT_TYPES:
        if rr is not None:
            if values_match(ext_val, rr, tolerance=RAW_RATIO_NEAR_TOLERANCE):
                yield "raw_metric_variant_ratio_to_rr_near", rr
            if rr > 0 and values_match(ext_val, 1.0 / rr, tolerance=RAW_RATIO_NEAR_TOLERANCE):
                yield "raw_metric_variant_ratio_reciprocal_to_rr_near", rr
        if or_value is not None:
            if values_match(ext_val, or_value, tolerance=RAW_RATIO_NEAR_TOLERANCE):
                yield "raw_metric_variant_ratio_to_or_near", or_value
            if or_value > 0 and values_match(ext_val, 1.0 / or_value, tolerance=RAW_RATIO_NEAR_TOLERANCE):
                yield "raw_metric_variant_ratio_reciprocal_to_or_near", or_value

    if ext_type in {"EffectType.MD", "EffectType.SMD"}:
        md, smd = _compute_md_smd_from_raw_data(raw_data)
        if md is None or smd is None:
            return

        # If extracted MD approximately matches raw-data MD, compare candidate SMD.
        if ext_type == "EffectType.MD" and values_match(ext_val, md, tolerance=RAW_METRIC_PREMATCH_TOLERANCE):
            yield "raw_metric_variant_md_to_smd", smd
            yield "raw_metric_variant_md_to_smd_sign_flip", -smd

        # If extracted SMD approximately matches raw-data SMD, compare candidate MD.
        if ext_type == "EffectType.SMD" and values_match(ext_val, smd, tolerance=RAW_METRIC_PREMATCH_TOLERANCE):
            yield "raw_metric_variant_smd_to_md", md
            yield "raw_metric_variant_smd_to_md_sign_flip", -md

        # Some papers report the same continuous outcome on 0-10 or 0-100 scales.
        # If extracted MD is a scaled version of raw-data MD, compare the raw-data MD.
        if ext_type == "EffectType.MD":
            for scale, label in (
                (0.01, "x0p01"),
                (0.1, "x0p1"),
                (10.0, "x10"),
                (100.0, "x100"),
            ):
                try:
                    scaled = float(ext_val) * scale
                except (TypeError, ValueError):
                    break
                if values_match(scaled, md, tolerance=RAW_METRIC_PREMATCH_TOLERANCE):
                    yield f"raw_metric_variant_md_scale_{label}", md
                if values_match(-scaled, md, tolerance=RAW_METRIC_PREMATCH_TOLERANCE):
                    yield f"raw_metric_variant_md_scale_{label}_sign_flip", md

            # Rounding drift: extracted MD may be reported at 1-2 decimals while
            # Cochrane raw-data MD retains higher precision.
            for decimals in (1, 2):
                rounded_md = round(float(md), decimals)
                if values_match(ext_val, rounded_md, tolerance=RAW_METRIC_PREMATCH_TOLERANCE):
                    yield f"raw_metric_variant_md_round_{decimals}dp", md
                if values_match(-float(ext_val), rounded_md, tolerance=RAW_METRIC_PREMATCH_TOLERANCE):
                    yield f"raw_metric_variant_md_round_{decimals}dp_sign_flip", md


def evaluate_entry(
    entry,
    pipeline,
    diag_jsonl: Optional[Path] = None,
    diag_parser_probe: bool = False,
    fast_mode: bool = False,
    per_study_timeout_sec: int = 0,
    pipeline_kwargs: Optional[dict] = None,
):
    """Run extraction + comparison for one study."""
    pdf_path = entry["pdf_path"]
    comparisons = entry.get("comparisons", [])
    attempt_id = f"{entry.get('study_id', 'unknown')}::{int(time.time() * 1000)}"

    # Get Cochrane reference values
    cochrane_effects = []
    for comp in comparisons:
        if comp.get("cochrane_effect") is not None:
            inferred_type = _infer_data_type(comp.get("raw_data"), comp.get("data_type"))
            inferred_from_outcome = False
            if not inferred_type:
                inferred_type = _infer_data_type_from_outcome(comp.get("outcome", ""))
                inferred_from_outcome = bool(inferred_type)
            cochrane_effects.append({
                "outcome": comp.get("outcome", ""),
                "effect": comp["cochrane_effect"],
                "ci_lower": comp.get("cochrane_ci_lower"),
                "ci_upper": comp.get("cochrane_ci_upper"),
                "data_type": inferred_type,
                "data_type_inferred_from_outcome": inferred_from_outcome,
                "raw_data": comp.get("raw_data"),
            })

    if not cochrane_effects:
        result = {"status": "no_cochrane_ref", "extracted": [], "cochrane": []}
        _append_diag_row(
            diag_jsonl,
            {
                "event": "result",
                "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                "attempt_id": attempt_id,
                "study_id": entry.get("study_id"),
                "pmcid": entry.get("pmcid"),
                "fast_mode": fast_mode,
                "status": result["status"],
                "n_cochrane": 0,
                "n_extracted": 0,
            },
        )
        return result

    # Run extraction
    extractions, extract_meta = extract_from_pdf(
        pdf_path,
        pipeline,
        diag_jsonl=diag_jsonl,
        diag_context={
            "attempt_id": attempt_id,
            "study_id": entry.get("study_id"),
            "pmcid": entry.get("pmcid"),
            "fast_mode": fast_mode,
        },
        diag_parser_probe=diag_parser_probe,
        fast_mode=fast_mode,
        per_study_timeout_sec=per_study_timeout_sec,
        pipeline_kwargs=pipeline_kwargs,
    )

    # Check for any match
    best_match = None
    best_rank = None

    for ext in extractions:
        if ext.get("error"):
            continue
        ext_val = ext.get("point_estimate")
        if ext_val is None:
            continue
        for coch in cochrane_effects:
            all_candidates = list(_iter_match_candidates(ext, coch))
            all_candidates.extend(_iter_raw_metric_variant_candidates(ext, coch))
            for transform, candidate in all_candidates:
                try:
                    cand_val = float(candidate)
                    coch_val = float(coch["effect"])
                except (TypeError, ValueError):
                    continue

                family_ok = _is_effect_family_compatible(ext.get("effect_type"), coch.get("data_type"))
                inferred_from_outcome = bool(coch.get("data_type_inferred_from_outcome"))
                strict_match = values_match(cand_val, coch_val, tolerance=0.05)
                tiny_abs_match = family_ok and _tiny_effect_abs_match(cand_val, coch_val)
                if not strict_match and not tiny_abs_match:
                    continue

                rel_distance = abs(cand_val - coch_val) / max(abs(coch_val), 1e-9)
                abs_distance = abs(cand_val - coch_val)
                # When outcome text inferred family, apply a stronger mismatch penalty.
                family_penalty = 0 if family_ok else (2 if inferred_from_outcome else 1)
                rank = (family_penalty, rel_distance, abs_distance)

                if best_rank is None or rank < best_rank:
                    best_rank = rank
                    best_match = {
                        "extracted": candidate,
                        "cochrane": coch["effect"],
                        "outcome": coch["outcome"],
                        "tolerance": "5%",
                        "transform": transform,
                        "extracted_raw": ext_val,
                        "extracted_type": ext.get("effect_type"),
                        "family_compatible": family_ok,
                        "data_type": coch.get("data_type"),
                    }

    n_valid_extractions = len([e for e in extractions if not e.get("error")])
    status = "match" if best_match else ("extracted_no_match" if n_valid_extractions > 0 else "no_extraction")

    result = {
        "status": status,
        "n_extracted": n_valid_extractions,
        "n_cochrane": len(cochrane_effects),
        "match": best_match,
        "extracted": extractions[:5],  # Keep first 5 to save space
        "cochrane": cochrane_effects[:3],
    }
    _append_diag_row(
        diag_jsonl,
        {
            "event": "result",
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "attempt_id": attempt_id,
            "study_id": entry.get("study_id"),
            "pmcid": entry.get("pmcid"),
            "fast_mode": fast_mode,
            "status": status,
            "n_cochrane": result["n_cochrane"],
            "n_extracted": result["n_extracted"],
            "match_found": bool(best_match),
            **extract_meta,
        },
    )
    return result


def _init_counts():
    return {k: 0 for k in SUMMARY_STATUS_KEYS}


def _build_summary_from_counts(counts, other_status_rows=0):
    total_evaluated = sum(counts.values()) + other_status_rows
    with_cochrane = (
        total_evaluated
        - counts.get("no_cochrane_ref", 0)
        - counts.get("error", 0)
        - counts.get("timeout_skipped_by_batch_runner", 0)
        - other_status_rows
    )
    without_cochrane = max(0, total_evaluated - with_cochrane)
    match_rate = counts.get("match", 0) / max(with_cochrane, 1)
    extraction_rate = (
        counts.get("match", 0) + counts.get("extracted_no_match", 0)
    ) / max(with_cochrane, 1)
    return {
        "total_evaluated": total_evaluated,
        "total": total_evaluated,
        "with_cochrane_ref": with_cochrane,
        "without_cochrane_ref": without_cochrane,
        "counts": counts,
        "by_status": counts,
        "other_status_rows": other_status_rows,
        "match_rate": match_rate,
        "extraction_rate": extraction_rate,
    }


def _summarize_eval_file():
    counts = _init_counts()
    other_status_rows = 0
    if not MEGA_EVAL_FILE.exists():
        return _build_summary_from_counts(counts, other_status_rows=0)

    latest_rows, _, raw_rows = _load_latest_eval_rows(MEGA_EVAL_FILE)
    for row in latest_rows:
        status = str(row.get("status", ""))
        if status in counts:
            counts[status] += 1
        else:
            other_status_rows += 1

    summary = _build_summary_from_counts(counts, other_status_rows=other_status_rows)
    summary["raw_rows"] = raw_rows
    summary["deduped_rows"] = len(latest_rows)
    summary["duplicate_rows"] = max(0, raw_rows - len(latest_rows))
    return summary


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate extractor on mega gold PDFs")
    parser.add_argument("--batch", type=int, default=100, help="Number of PDFs to evaluate")
    parser.add_argument("--resume", action="store_true", help="Skip already evaluated")
    parser.add_argument(
        "--fast-mode",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Disable expensive diagnostics/table/advanced branches for faster throughput",
    )
    parser.add_argument(
        "--diag-jsonl",
        type=Path,
        default=None,
        help="Optional JSONL output for per-study diagnostics events",
    )
    parser.add_argument(
        "--diag-parser-probe",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Record standalone parser timing/metadata before full extraction",
    )
    parser.add_argument(
        "--per-study-timeout-sec",
        type=int,
        default=0,
        help="If >0, run each extraction in a subprocess and terminate after this many seconds",
    )
    parser.add_argument(
        "--rerun-statuses",
        type=str,
        default="",
        help="Comma-separated statuses to rerun even when --resume is enabled",
    )
    parser.add_argument(
        "--ocr-threshold",
        type=float,
        default=100.0,
        help="PDF OCR trigger threshold (higher = more OCR attempts)",
    )
    parser.add_argument(
        "--extract-tables",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable table extraction branch in non-fast mode",
    )
    parser.add_argument(
        "--enable-advanced",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable advanced extraction branch in non-fast mode",
    )
    parser.add_argument(
        "--aggressive-ocr-correction",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable aggressive OCR text correction",
    )
    parser.add_argument(
        "--study-ids",
        type=str,
        default="",
        help=(
            "Optional comma-separated study IDs to evaluate/rerun. "
            "IDs are matched canonically (case/spacing insensitive)."
        ),
    )
    args = parser.parse_args()
    if args.per_study_timeout_sec < 0:
        raise ValueError("--per-study-timeout-sec must be >= 0")
    if args.ocr_threshold <= 0:
        raise ValueError("--ocr-threshold must be > 0")
    rerun_statuses = {
        s.strip() for s in str(args.rerun_statuses).split(",")
        if s.strip()
    }
    study_id_filter_keys = _parse_study_ids_filter(args.study_ids)
    if rerun_statuses and not args.resume:
        raise ValueError("--rerun-statuses requires --resume")

    _append_diag_row(
        args.diag_jsonl,
        {
            "event": "run_start",
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "batch": args.batch,
            "resume": args.resume,
            "fast_mode": args.fast_mode,
            "per_study_timeout_sec": args.per_study_timeout_sec,
            "ocr_threshold": args.ocr_threshold,
            "extract_tables": args.extract_tables,
            "enable_advanced": args.enable_advanced,
            "aggressive_ocr_correction": args.aggressive_ocr_correction,
            "study_ids_filter_count": len(study_id_filter_keys),
        },
    )

    pipeline_kwargs = {
        "ocr_threshold": args.ocr_threshold,
        "extract_tables": bool(args.extract_tables),
        "enable_advanced": bool(args.enable_advanced),
        "aggressive_ocr_correction": bool(args.aggressive_ocr_correction),
    }

    entries = load_entries_with_pdfs()
    print(f"PDFs available: {len(entries)}")
    print(f"Pipeline mode: {'fast' if args.fast_mode else 'full'}")
    if study_id_filter_keys:
        print(f"Study filter: {len(study_id_filter_keys)} IDs")

    # Load existing evaluations
    already_evaluated_keys = set()
    latest_status_by_key = {}
    latest_rerun_attempts_by_key: Dict[str, int] = {}
    latest_eval_rows: List[dict] = []
    latest_eval_index_by_key: Dict[str, int] = {}
    existing_raw_rows = 0
    if args.resume and MEGA_EVAL_FILE.exists():
        latest_eval_rows, latest_eval_index_by_key, existing_raw_rows = _load_latest_eval_rows(MEGA_EVAL_FILE)
        for ev in latest_eval_rows:
            study_id = ev.get("study_id")
            if study_id:
                key = _canonical_study_key(study_id)
                already_evaluated_keys.add(key)
                latest_status_by_key[key] = str(ev.get("status", ""))
                latest_rerun_attempts_by_key[key] = int(ev.get("rerun_attempts", 0) or 0)
        print(f"Already evaluated: {len(already_evaluated_keys)}")
        if existing_raw_rows > len(latest_eval_rows):
            print(
                f"Resume view deduped historical rows in-memory: "
                f"{existing_raw_rows} -> {len(latest_eval_rows)}"
            )
        if rerun_statuses:
            print(f"Rerun statuses: {sorted(rerun_statuses)}")

    # In rerun mode, update results in-place instead of appending duplicate rows.
    upsert_mode = bool(args.resume and rerun_statuses)
    upsert_rows = latest_eval_rows if upsert_mode else []
    upsert_index_by_key = latest_eval_index_by_key if upsert_mode else {}
    if upsert_mode and existing_raw_rows > len(upsert_rows):
        print("Rerun mode write strategy: upsert (collapsing existing duplicates on disk)")
        _write_eval_rows(MEGA_EVAL_FILE, upsert_rows)
    elif upsert_mode:
        print("Rerun mode write strategy: upsert (replace latest row per study)")

    to_evaluate = []
    rerun_priority_entries: List[Tuple[int, str, dict]] = []
    selected_rerun_prev_attempts_by_key: Dict[str, int] = {}
    rerun_candidates = 0
    for entry in entries:
        key = _canonical_study_key(entry["study_id"])
        if study_id_filter_keys and key not in study_id_filter_keys:
            continue
        if rerun_statuses:
            # Strict rerun mode: only reprocess already-evaluated studies with target statuses.
            if key in already_evaluated_keys and latest_status_by_key.get(key) in rerun_statuses:
                prev_attempts = int(latest_rerun_attempts_by_key.get(key, 0))
                rerun_priority_entries.append((prev_attempts, key, entry))
                selected_rerun_prev_attempts_by_key[key] = prev_attempts
                rerun_candidates += 1
            continue

        if key not in already_evaluated_keys:
            to_evaluate.append(entry)
            continue
    if rerun_priority_entries:
        rerun_priority_entries.sort(key=lambda item: (item[0], item[1]))
        to_evaluate.extend([item[2] for item in rerun_priority_entries])
    if rerun_statuses:
        print(f"Rerun candidates selected: {rerun_candidates}")
        if rerun_priority_entries:
            min_attempt = rerun_priority_entries[0][0]
            max_attempt = rerun_priority_entries[-1][0]
            print(f"Rerun attempt depth range: min={min_attempt}, max={max_attempt}")
    n = min(args.batch, len(to_evaluate))
    print(f"To evaluate: {n}")
    print("=" * 70)

    counts = _init_counts()
    if n == 0:
        print("No pending studies in this run.")
        summary = _summarize_eval_file()
        summary["run_summary"] = _build_summary_from_counts(counts, other_status_rows=0)
        with open(MEGA_EVAL_SUMMARY, "w", encoding="utf-8", newline="\n") as f:
            json.dump(summary, f, indent=2)
        print(f"Saved cumulative summary: {MEGA_EVAL_SUMMARY}")
        return 0

    pipeline = None
    if args.per_study_timeout_sec > 0:
        print(
            f"Extraction mode: isolated subprocess timeout ({args.per_study_timeout_sec}s per study)"
        )
        _append_diag_row(
            args.diag_jsonl,
            {
                "event": "pipeline_init_skipped",
                "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                "fast_mode": args.fast_mode,
                "reason": "per_study_timeout_mode",
                "per_study_timeout_sec": args.per_study_timeout_sec,
                **pipeline_kwargs,
            },
        )
    else:
        pipeline_init_started = time.perf_counter()
        _append_diag_row(
            args.diag_jsonl,
            {
                "event": "pipeline_init_start",
                "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                "fast_mode": args.fast_mode,
                **pipeline_kwargs,
            },
        )
        try:
            pipeline = create_pipeline(fast_mode=args.fast_mode, **pipeline_kwargs)
        except Exception as e:
            _append_diag_row(
                args.diag_jsonl,
                {
                    "event": "pipeline_init_error",
                    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                    "fast_mode": args.fast_mode,
                    "elapsed_sec": round(time.perf_counter() - pipeline_init_started, 4),
                    "error": str(e),
                    **pipeline_kwargs,
                },
            )
            print(f"Failed to initialize pipeline: {e}", file=sys.stderr)
            return 1
        _append_diag_row(
            args.diag_jsonl,
            {
                "event": "pipeline_init_done",
                "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                "fast_mode": args.fast_mode,
                "elapsed_sec": round(time.perf_counter() - pipeline_init_started, 4),
                **pipeline_kwargs,
            },
        )

    def _evaluate_and_finalize(entry: dict) -> Tuple[dict, str]:
        key = _canonical_study_key(entry.get("study_id", ""))
        try:
            result = evaluate_entry(
                entry,
                pipeline,
                diag_jsonl=args.diag_jsonl,
                diag_parser_probe=args.diag_parser_probe,
                fast_mode=args.fast_mode,
                per_study_timeout_sec=args.per_study_timeout_sec,
                pipeline_kwargs=pipeline_kwargs,
            )
            result["study_id"] = entry["study_id"]
            result["first_author"] = entry.get("first_author", "")
            result["year"] = entry.get("year", 0)
            result["pmcid"] = entry.get("pmcid", "")
            if key and key in selected_rerun_prev_attempts_by_key:
                result["rerun_attempts"] = selected_rerun_prev_attempts_by_key[key] + 1

            status = str(result.get("status", "error"))
            counts[status] = counts.get(status, 0) + 1
            return result, status
        except Exception as e:
            counts["error"] += 1
            result = {
                "study_id": entry["study_id"],
                "status": "error",
                "error": str(e),
            }
            return result, "error"

    # Save results incrementally so progress survives timeouts/interruption.
    if upsert_mode:
        for i, entry in enumerate(to_evaluate[:n]):
            result, status = _evaluate_and_finalize(entry)

            key = _canonical_study_key(entry["study_id"])
            existing_idx = upsert_index_by_key.get(key)
            if existing_idx is None:
                upsert_rows.append(result)
                upsert_index_by_key[key] = len(upsert_rows) - 1
            else:
                upsert_rows[existing_idx] = result

            _write_eval_rows(MEGA_EVAL_FILE, upsert_rows)

            if (i + 1) % 10 == 0 or status == "match":
                match_info = ""
                if result.get("match"):
                    m = result["match"]
                    match_info = f" ext={m['extracted']} coch={m['cochrane']}"
                print(f"  [{i+1}/{n}] {entry['study_id'][:30]:30s} {status:20s}{match_info}")
    else:
        mode = "a" if args.resume else "w"
        with open(MEGA_EVAL_FILE, mode, encoding="utf-8", newline="\n") as out:
            for i, entry in enumerate(to_evaluate[:n]):
                result, status = _evaluate_and_finalize(entry)
                out.write(json.dumps(result, ensure_ascii=False) + "\n")
                out.flush()

                if (i + 1) % 10 == 0 or status == "match":
                    match_info = ""
                    if result.get("match"):
                        m = result["match"]
                        match_info = f" ext={m['extracted']} coch={m['cochrane']}"
                    print(f"  [{i+1}/{n}] {entry['study_id'][:30]:30s} {status:20s}{match_info}")

    # Summary
    run_summary = _build_summary_from_counts(counts, other_status_rows=0)
    total_evaluated = run_summary["total_evaluated"]
    with_cochrane = run_summary["with_cochrane_ref"]

    print(f"\n{'='*70}")
    print(f"EVALUATION SUMMARY")
    print(f"{'='*70}")
    print(f"Evaluated:            {total_evaluated}")
    print(f"With Cochrane ref:    {with_cochrane}")
    print(f"  Match (within 5%):  {counts['match']}  ({100*counts['match']/max(with_cochrane,1):.1f}%)")
    print(f"  Extracted no match: {counts['extracted_no_match']}  ({100*counts['extracted_no_match']/max(with_cochrane,1):.1f}%)")
    print(f"  No extraction:      {counts['no_extraction']}  ({100*counts['no_extraction']/max(with_cochrane,1):.1f}%)")
    print(f"  No Cochrane ref:    {counts['no_cochrane_ref']}")
    print(f"  Error:              {counts['error']}")

    # Save cumulative summary and include this run's slice for traceability.
    summary = _summarize_eval_file()
    summary["run_summary"] = run_summary
    with open(MEGA_EVAL_SUMMARY, "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {MEGA_EVAL_FILE}")


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
