#!/usr/bin/env python3
"""Final targeted OA rescue for unresolved Elsevier (10.1016/*) DOIs."""

from __future__ import annotations

import argparse
import html
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)
DOI_URL = "https://doi.org/{doi}"
TRANSIENT_HTTP_CODES = {408, 425, 429, 500, 502, 503, 504}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_doi(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = text.replace("https://doi.org/", "").replace("http://doi.org/", "")
    text = text.replace("doi:", "")
    return text.strip()


def _normalize_pmid(value: object) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _safe_name(text: object) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(text or "file")).strip("_")
    return cleaned or "file"


def _load_rows(path: Path) -> List[Dict]:
    payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    rows = payload.get("rows")
    return [dict(row) for row in rows] if isinstance(rows, list) else []


def _write_rows(path: Path, rows: Sequence[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"rows": list(rows)}, indent=2, ensure_ascii=False), encoding="utf-8")


def _status_counts(rows: Sequence[Dict]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for row in rows:
        key = str(row.get("status") or "unknown")
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def _request(
    url: str,
    *,
    timeout_sec: float,
    max_retries: int,
    accept: str,
    referer: str = "https://www.sciencedirect.com/",
) -> Tuple[bytes, str, str]:
    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": accept,
                "Referer": referer,
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                body = resp.read()
                final_url = str(resp.geturl() or url)
                content_type = str(resp.headers.get("content-type") or "").lower()
                return body, final_url, content_type
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code in TRANSIENT_HTTP_CODES and attempt < max_retries:
                time.sleep(0.4 * (attempt + 1))
                continue
            raise
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(0.4 * (attempt + 1))
                continue
            raise
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"request failed: {url}")


def _download_pdf(
    url: str,
    output_path: Path,
    *,
    timeout_sec: float,
    max_retries: int,
) -> Tuple[bool, str, int]:
    try:
        body, final_url, _ = _request(
            url=url,
            timeout_sec=timeout_sec,
            max_retries=max_retries,
            accept="application/pdf,*/*",
        )
    except Exception:
        return False, "", 0
    if len(body) < 1024 or not body.startswith(b"%PDF"):
        return False, final_url, 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(body)
    return True, final_url, len(body)


def _extract_piis(text: str) -> List[str]:
    # Typical Elsevier PII patterns
    patterns = [
        re.compile(r"/pii/([A-Za-z0-9()\-]+)", re.IGNORECASE),
        re.compile(r'"pii"\s*:\s*"([A-Za-z0-9()\-]+)"', re.IGNORECASE),
        re.compile(r'"articlePII"\s*:\s*"([A-Za-z0-9()\-]+)"', re.IGNORECASE),
        re.compile(r"science/article/pii/([A-Za-z0-9()\-]+)", re.IGNORECASE),
    ]
    out: List[str] = []
    seen: Set[str] = set()
    for pattern in patterns:
        for raw in pattern.findall(text):
            pii = str(raw or "").strip().upper()
            pii = re.sub(r"[^A-Z0-9()\-]", "", pii)
            if not pii:
                continue
            if pii in seen:
                continue
            seen.add(pii)
            out.append(pii)
    return out


def _extract_pdf_urls_from_html(html_text: str, base_url: str) -> List[str]:
    patterns = [
        re.compile(r'(?i)citation_pdf_url["\']?\s+content=["\']([^"\']+)["\']'),
        re.compile(r'(?i)"pdfUrl"\s*:\s*"([^"]+)"'),
        re.compile(r'(?i)(https://pdf\.sciencedirectassets\.com/[^"\'\s<>]+)'),
        re.compile(r'(?i)(https://www\.sciencedirect\.com/science/article/pii/[^"\'\s<>]+/pdfft[^"\'\s<>]*)'),
        re.compile(r'(?i)(/science/article/pii/[^"\'\s<>]+/pdfft[^"\'\s<>]*)'),
    ]
    out: List[str] = []
    seen: Set[str] = set()
    for pattern in patterns:
        for raw in pattern.findall(html_text):
            if not isinstance(raw, str):
                continue
            clean = html.unescape(raw.strip().replace("\\/", "/"))
            if not clean:
                continue
            absolute = urllib.parse.urljoin(base_url, clean)
            if absolute in seen:
                continue
            seen.add(absolute)
            out.append(absolute)
    return out


def _fetch_landing(doi: str, *, timeout_sec: float, max_retries: int) -> Tuple[str, str]:
    url = DOI_URL.format(doi=urllib.parse.quote(doi, safe="/"))
    try:
        body, final_url, content_type = _request(
            url=url,
            timeout_sec=timeout_sec,
            max_retries=max_retries,
            accept="text/html,application/xhtml+xml,*/*",
            referer="https://doi.org/",
        )
    except Exception:
        return "", ""
    if "html" not in content_type and "xml" not in content_type:
        return final_url, ""
    return final_url, body.decode("utf-8", errors="replace")


def _pii_candidates_from_doi(doi: str) -> List[str]:
    suffix = doi.split("/", 1)[1] if "/" in doi else ""
    out: List[str] = []
    seen: Set[str] = set()
    # Case: doi already contains pii-like string
    for cand in [suffix.upper(), re.sub(r"[^A-Z0-9()\-]", "", suffix.upper())]:
        if cand and cand.startswith("S") and len(cand) >= 12 and cand not in seen:
            seen.add(cand)
            out.append(cand)
    return out


def _science_direct_urls_for_pii(pii: str) -> List[str]:
    base = f"https://www.sciencedirect.com/science/article/pii/{pii}"
    return [
        f"{base}/pdfft?isDTMRedir=true&download=true",
        f"{base}/pdfft",
        f"{base}/pdf",
        f"{base}/pdf?download=true",
        f"{base}?download=true",
        f"https://www.sciencedirect.com/science/article/abs/pii/{pii}",
        f"https://api.elsevier.com/content/article/pii/{pii}?httpAccept=application/pdf",
    ]


def _rescue_row(
    row: Dict,
    *,
    output_dir: Path,
    timeout_sec: float,
    max_retries: int,
) -> Dict:
    out = dict(row)
    doi = _normalize_doi(out.get("doi"))
    if not doi.startswith("10.1016/"):
        out["elsevier_final_status"] = "skip_not_1016"
        return out
    if str(out.get("status") or "") != "fallback_failed":
        out["elsevier_final_status"] = "skip_not_failed"
        return out

    pmid = _normalize_pmid(out.get("pmid"))
    kind = str(out.get("kind") or "item")
    pmcid = str(out.get("pmcid") or "").strip().upper()
    suffix = pmcid if pmcid else "NO_PMCID"
    filename = f"{_safe_name(kind)}__{pmid}__{suffix}.pdf"
    output_path = output_dir / filename
    if output_path.exists() and output_path.stat().st_size > 1024:
        out["status"] = "already_downloaded"
        out["size_bytes"] = int(output_path.stat().st_size)
        out["local_pdf_path"] = str(output_path)
        out["elsevier_final_status"] = "already_present"
        return out

    attempts: List[str] = []
    seen_urls: Set[str] = set()

    def _try_url(url: str, source: str) -> bool:
        if not url or url in seen_urls:
            return False
        seen_urls.add(url)
        attempts.append(source)
        ok, final_url, size = _download_pdf(
            url=url,
            output_path=output_path,
            timeout_sec=timeout_sec,
            max_retries=max_retries,
        )
        if ok:
            out["status"] = "downloaded_final_elsevier"
            out["download_url"] = final_url or url
            out["size_bytes"] = int(size)
            out["local_pdf_path"] = str(output_path)
            out["elsevier_final_status"] = "downloaded"
            out["elsevier_final_method"] = source
            out["elsevier_final_attempts"] = attempts
            return True
        return False

    # Step 1: DOI landing
    final_url, landing_html = _fetch_landing(doi, timeout_sec=timeout_sec, max_retries=max_retries)
    if _try_url(DOI_URL.format(doi=urllib.parse.quote(doi, safe="/")), "doi_landing_direct"):
        return out
    if final_url and _try_url(final_url, "resolved_direct"):
        return out

    # Step 2: derive PII
    piis: List[str] = []
    seen_piis: Set[str] = set()
    for pii in _pii_candidates_from_doi(doi):
        if pii not in seen_piis:
            seen_piis.add(pii)
            piis.append(pii)
    if final_url:
        for pii in _extract_piis(final_url):
            if pii not in seen_piis:
                seen_piis.add(pii)
                piis.append(pii)
    if landing_html:
        for pii in _extract_piis(landing_html):
            if pii not in seen_piis:
                seen_piis.add(pii)
                piis.append(pii)

    # Step 3: direct ScienceDirect templates
    for pii in piis:
        for url in _science_direct_urls_for_pii(pii):
            if _try_url(url, "pii_template"):
                return out

    # Step 4: landing-extracted PDF links
    if landing_html:
        for url in _extract_pdf_urls_from_html(landing_html, base_url=final_url or DOI_URL.format(doi=urllib.parse.quote(doi, safe="/"))):
            if _try_url(url, "landing_pdf_url"):
                return out

    out["elsevier_final_status"] = "failed"
    out["elsevier_final_attempts"] = attempts
    return out


def _run(
    rows: List[Dict],
    *,
    output_dir: Path,
    timeout_sec: float,
    max_retries: int,
    workers: int,
) -> Tuple[List[Dict], Dict[str, int]]:
    lock = threading.Lock()
    idxs = [
        i
        for i, row in enumerate(rows)
        if str(row.get("status") or "") == "fallback_failed"
        and _normalize_doi(row.get("doi")).startswith("10.1016/")
    ]
    stats = {
        "target_rows": len(idxs),
        "downloaded_new": 0,
        "still_unresolved": 0,
    }

    def _worker(i: int) -> Tuple[int, Dict]:
        return i, _rescue_row(
            rows[i],
            output_dir=output_dir,
            timeout_sec=timeout_sec,
            max_retries=max_retries,
        )

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futures = [ex.submit(_worker, i) for i in idxs]
        for fut in as_completed(futures):
            i, row = fut.result()
            with lock:
                rows[i] = row
                if str(row.get("elsevier_final_status") or "") == "downloaded":
                    stats["downloaded_new"] += 1
                else:
                    stats["still_unresolved"] += 1
    return rows, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--timeout-sec", type=float, default=12.0)
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()

    if not args.bundle_dir.exists():
        raise FileNotFoundError(f"--bundle-dir not found: {args.bundle_dir}")
    if args.timeout_sec <= 0:
        raise ValueError("--timeout-sec must be > 0")
    if args.max_retries < 0:
        raise ValueError("--max-retries must be >= 0")
    if args.workers <= 0:
        raise ValueError("--workers must be > 0")

    meta_path = args.bundle_dir / "meta_downloads.json"
    trial_path = args.bundle_dir / "rct_trial_downloads.json"
    if not meta_path.exists() or not trial_path.exists():
        raise FileNotFoundError("bundle dir must include meta_downloads.json and rct_trial_downloads.json")

    meta_rows = _load_rows(meta_path)
    trial_rows = _load_rows(trial_path)

    meta_rows, meta_stats = _run(
        meta_rows,
        output_dir=args.bundle_dir / "meta_pdfs",
        timeout_sec=float(args.timeout_sec),
        max_retries=int(args.max_retries),
        workers=int(args.workers),
    )
    trial_rows, trial_stats = _run(
        trial_rows,
        output_dir=args.bundle_dir / "rct_trial_pdfs",
        timeout_sec=float(args.timeout_sec),
        max_retries=int(args.max_retries),
        workers=int(args.workers),
    )

    _write_rows(meta_path, meta_rows)
    _write_rows(trial_path, trial_rows)

    summary = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "bundle_dir": str(args.bundle_dir),
            "timeout_sec": float(args.timeout_sec),
            "max_retries": int(args.max_retries),
            "workers": int(args.workers),
        },
        "counts": {
            "meta_elsevier_final": meta_stats,
            "trial_elsevier_final": trial_stats,
            "meta_status_after": _status_counts(meta_rows),
            "trial_status_after": _status_counts(trial_rows),
        },
        "paths": {
            "meta_downloads_json": str(meta_path),
            "rct_trial_downloads_json": str(trial_path),
            "elsevier_final_summary_json": str(args.bundle_dir / "elsevier_final_summary.json"),
        },
    }
    (args.bundle_dir / "elsevier_final_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
