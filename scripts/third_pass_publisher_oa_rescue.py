#!/usr/bin/env python3
"""Third-pass publisher-targeted OA PDF rescue for author-meta bundle."""

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


CROSSREF_URL = "https://api.crossref.org/works/{doi}"
DOI_URL = "https://doi.org/{doi}"
USER_AGENT = "rct-extractor-v2-thirdpass-oa/1.0"
TRANSIENT_HTTP_CODES = {408, 425, 429, 500, 502, 503, 504}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_pmid(value: object) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _normalize_doi(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = text.replace("https://doi.org/", "").replace("http://doi.org/", "")
    text = text.replace("doi:", "")
    return text.strip()


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


def _looks_like_pdf_url(url: str) -> bool:
    if not url:
        return False
    parsed = urllib.parse.urlparse(url)
    path = (parsed.path or "").lower()
    if path.endswith(".pdf") or "/pdf/" in path or path.endswith("/pdf"):
        return True
    params = urllib.parse.parse_qs(parsed.query or "", keep_blank_values=True)
    for key, values in params.items():
        key_l = key.lower()
        values_l = [str(v).lower() for v in values]
        if key_l in {"blobtype", "format"} and "pdf" in values_l:
            return True
        if key_l in {"download", "filename"} and any(v.endswith(".pdf") for v in values_l):
            return True
    return False


def _request_url(
    url: str,
    *,
    timeout_sec: float,
    max_retries: int,
    accept: str,
) -> Tuple[bytes, str, str]:
    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": accept,
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
    raise RuntimeError(f"request failed without exception: {url}")


def _request_json(url: str, *, timeout_sec: float, max_retries: int) -> Dict:
    body, _, _ = _request_url(
        url,
        timeout_sec=timeout_sec,
        max_retries=max_retries,
        accept="application/json,*/*",
    )
    return json.loads(body.decode("utf-8", errors="replace"))


def _download_pdf(
    url: str,
    output_path: Path,
    *,
    timeout_sec: float,
    max_retries: int,
) -> Tuple[bool, str, int]:
    try:
        body, final_url, _ = _request_url(
            url,
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


def _extract_pdf_links_from_html(html_text: str, base_url: str, max_links: int) -> List[str]:
    patterns = [
        re.compile(r'(?i)citation_pdf_url["\']?\s+content=["\']([^"\']+)["\']'),
        re.compile(r'(?i)(?:href|src)\s*=\s*["\']([^"\']+)["\']'),
        re.compile(r'(?i)(https?://[^"\'\s<>]+\.pdf(?:\?[^"\'\s<>]*)?)'),
        re.compile(r'(?i)"pdfUrl"\s*:\s*"([^"]+)"'),
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
            if not _looks_like_pdf_url(absolute):
                continue
            if absolute in seen:
                continue
            seen.add(absolute)
            out.append(absolute)
            if len(out) >= max_links:
                return out
    return out


def _discover_pdf_links_from_landing(
    url: str,
    *,
    timeout_sec: float,
    max_retries: int,
    max_links: int,
) -> List[str]:
    try:
        body, final_url, content_type = _request_url(
            url,
            timeout_sec=timeout_sec,
            max_retries=max_retries,
            accept="text/html,application/xhtml+xml,application/pdf,*/*",
        )
    except Exception:
        return []
    if body.startswith(b"%PDF") and _looks_like_pdf_url(final_url):
        return [final_url]
    if "html" not in content_type and "xml" not in content_type:
        return []
    html_text = body.decode("utf-8", errors="replace")
    return _extract_pdf_links_from_html(html_text, base_url=final_url, max_links=max_links)


def _crossref_pdf_links(
    doi: str,
    *,
    timeout_sec: float,
    max_retries: int,
) -> List[str]:
    if not doi:
        return []
    url = CROSSREF_URL.format(doi=urllib.parse.quote(doi, safe=""))
    try:
        payload = _request_json(url=url, timeout_sec=timeout_sec, max_retries=max_retries)
    except Exception:
        return []
    message = payload.get("message") or {}
    links = message.get("link") or []
    out: List[str] = []
    seen: Set[str] = set()
    for item in links:
        if not isinstance(item, dict):
            continue
        link_url = str(item.get("URL") or "").strip()
        content_type = str(item.get("content-type") or "").lower()
        if not link_url:
            continue
        if link_url in seen:
            continue
        if "pdf" not in content_type and not _looks_like_pdf_url(link_url):
            continue
        seen.add(link_url)
        out.append(link_url)
    return out


def _publisher_candidates(doi: str, resolved_url: str) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()

    def _add(url: str) -> None:
        if not url or url in seen:
            return
        seen.add(url)
        out.append(url)

    doi_q = urllib.parse.quote(doi, safe="/")
    prefix = doi.split("/", 1)[0] if "/" in doi else doi
    suffix = doi.split("/", 1)[1] if "/" in doi else ""
    host = urllib.parse.urlparse(resolved_url).netloc.lower()
    path = urllib.parse.urlparse(resolved_url).path

    # Wiley
    if prefix in {"10.1111", "10.1002"} or "wiley.com" in host:
        _add(f"https://onlinelibrary.wiley.com/doi/pdf/{doi_q}")
        _add(f"https://onlinelibrary.wiley.com/doi/epdf/{doi_q}")
        _add(f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi_q}")

    # Springer
    if prefix == "10.1007" or "springer.com" in host:
        _add(f"https://link.springer.com/content/pdf/{doi_q}.pdf")
        _add(f"https://link.springer.com/content/pdf/{doi_q}.pdf?download=1")
        _add(f"https://link.springer.com/article/{doi_q}")

    # AHA journals
    if prefix == "10.1161" or "ahajournals.org" in host:
        _add(f"https://www.ahajournals.org/doi/pdf/{doi_q}")
        _add(f"https://www.ahajournals.org/doi/epdf/{doi_q}")

    # SAGE
    if prefix == "10.1177" or "sagepub.com" in host:
        _add(f"https://journals.sagepub.com/doi/pdf/{doi_q}")
        _add(f"https://journals.sagepub.com/doi/epdf/{doi_q}")

    # Taylor & Francis
    if prefix == "10.1080" or "tandfonline.com" in host:
        _add(f"https://www.tandfonline.com/doi/pdf/{doi_q}?download=true")
        _add(f"https://www.tandfonline.com/doi/full/{doi_q}")
        if "/full/" in path:
            _add(f"https://{host}{path.replace('/full/', '/pdf/', 1)}?download=true")

    # OUP
    if prefix == "10.1093" or "academic.oup.com" in host:
        _add(f"https://academic.oup.com/doi/pdf/{doi_q}")
        _add(f"https://academic.oup.com/doi/full/{doi_q}")

    # Elsevier / ScienceDirect
    if prefix == "10.1016" or "elsevier.com" in host or "sciencedirect.com" in host:
        pii_raw = suffix.upper()
        pii_clean = re.sub(r"[^A-Z0-9]", "", pii_raw)
        for pii in [pii_raw, pii_clean]:
            if not pii:
                continue
            _add(f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft?isDTMRedir=true&download=true")
            _add(f"https://www.sciencedirect.com/science/article/pii/{pii}/pdf")
            _add(f"https://www.sciencedirect.com/science/article/pii/{pii}")

    # LWW
    if prefix == "10.1097" or "lww.com" in host:
        _add(f"https://journals.lww.com/doi/pdf/{doi_q}")
        _add(f"https://journals.lww.com/doi/full/{doi_q}")

    return out


def _resolve_doi_url(
    doi: str,
    *,
    timeout_sec: float,
    max_retries: int,
) -> str:
    url = DOI_URL.format(doi=urllib.parse.quote(doi, safe="/"))
    try:
        _, final_url, _ = _request_url(
            url,
            timeout_sec=timeout_sec,
            max_retries=max_retries,
            accept="text/html,*/*",
        )
        return final_url
    except Exception:
        return ""


def _run_on_rows(
    rows: List[Dict],
    *,
    output_dir: Path,
    timeout_sec: float,
    max_retries: int,
    max_links_per_landing: int,
    max_candidates: int,
    workers: int,
) -> Tuple[List[Dict], Dict[str, int]]:
    lock = threading.Lock()
    stats = {
        "input_rows": len(rows),
        "target_rows": 0,
        "downloaded_new": 0,
        "still_unresolved": 0,
    }

    tasks: List[int] = []
    for idx, row in enumerate(rows):
        if str(row.get("status") or "") == "fallback_failed" and _normalize_doi(row.get("doi")):
            tasks.append(idx)
    stats["target_rows"] = len(tasks)

    def _worker(idx: int) -> Tuple[int, Dict]:
        row = dict(rows[idx])
        doi = _normalize_doi(row.get("doi"))
        pmid = _normalize_pmid(row.get("pmid"))
        pmcid = str(row.get("pmcid") or "").strip().upper()
        kind = str(row.get("kind") or "item")
        suffix = pmcid if pmcid else "NO_PMCID"
        filename = f"{_safe_name(kind)}__{pmid}__{suffix}.pdf"
        output_path = output_dir / filename
        if output_path.exists() and output_path.stat().st_size > 1024:
            row["status"] = "already_downloaded"
            row["size_bytes"] = int(output_path.stat().st_size)
            row["local_pdf_path"] = str(output_path)
            row["third_pass_status"] = "already_present"
            return idx, row

        resolved = _resolve_doi_url(doi, timeout_sec=timeout_sec, max_retries=max_retries)
        candidate_urls: List[Tuple[str, str, bool]] = []
        seen: Set[str] = set()

        def _add(url: str, source: str, allow_landing: bool) -> None:
            if not url or url in seen:
                return
            seen.add(url)
            candidate_urls.append((url, source, allow_landing))

        for url in _crossref_pdf_links(doi, timeout_sec=timeout_sec, max_retries=max_retries):
            _add(url, "crossref_link", False)

        _add(DOI_URL.format(doi=urllib.parse.quote(doi, safe="/")), "doi_landing", True)
        if resolved:
            _add(resolved, "resolved_landing", True)

        for url in _publisher_candidates(doi, resolved):
            _add(url, "publisher_template", False)

        if max_candidates > 0:
            candidate_urls = candidate_urls[:max_candidates]

        attempts: List[str] = []
        for url, source, allow_landing in candidate_urls:
            attempts.append(source)
            ok, final_url, size = _download_pdf(
                url=url,
                output_path=output_path,
                timeout_sec=timeout_sec,
                max_retries=max_retries,
            )
            if ok:
                row["status"] = f"downloaded_thirdpass_{source}"
                row["download_url"] = final_url or url
                row["size_bytes"] = int(size)
                row["local_pdf_path"] = str(output_path)
                row["third_pass_status"] = "downloaded"
                row["third_pass_method"] = source
                row["third_pass_attempt_sources"] = attempts
                return idx, row

            if not allow_landing:
                continue
            for link in _discover_pdf_links_from_landing(
                url=url,
                timeout_sec=timeout_sec,
                max_retries=max_retries,
                max_links=max_links_per_landing,
            ):
                ok, final_url, size = _download_pdf(
                    url=link,
                    output_path=output_path,
                    timeout_sec=timeout_sec,
                    max_retries=max_retries,
                )
                if ok:
                    row["status"] = f"downloaded_thirdpass_{source}"
                    row["download_url"] = final_url or link
                    row["size_bytes"] = int(size)
                    row["local_pdf_path"] = str(output_path)
                    row["third_pass_status"] = "downloaded"
                    row["third_pass_method"] = source
                    row["third_pass_attempt_sources"] = attempts
                    row["third_pass_landing_hit"] = link
                    return idx, row

        row["third_pass_status"] = "failed"
        row["third_pass_attempt_sources"] = attempts
        return idx, row

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(_worker, idx) for idx in tasks]
        for future in as_completed(futures):
            idx, row = future.result()
            with lock:
                rows[idx] = row
                if str(row.get("third_pass_status") or "") == "downloaded":
                    stats["downloaded_new"] += 1
                else:
                    stats["still_unresolved"] += 1

    return rows, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--timeout-sec", type=float, default=15.0)
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--max-candidates", type=int, default=12)
    parser.add_argument("--max-links-per-landing", type=int, default=10)
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()

    if not args.bundle_dir.exists():
        raise FileNotFoundError(f"--bundle-dir not found: {args.bundle_dir}")
    if args.timeout_sec <= 0:
        raise ValueError("--timeout-sec must be > 0")
    if args.max_retries < 0:
        raise ValueError("--max-retries must be >= 0")
    if args.max_candidates <= 0:
        raise ValueError("--max-candidates must be > 0")
    if args.max_links_per_landing <= 0:
        raise ValueError("--max-links-per-landing must be > 0")
    if args.workers <= 0:
        raise ValueError("--workers must be > 0")

    meta_path = args.bundle_dir / "meta_downloads.json"
    trial_path = args.bundle_dir / "rct_trial_downloads.json"
    if not meta_path.exists() or not trial_path.exists():
        raise FileNotFoundError("bundle dir must contain meta_downloads.json and rct_trial_downloads.json")

    meta_rows = _load_rows(meta_path)
    trial_rows = _load_rows(trial_path)

    meta_rows, meta_stats = _run_on_rows(
        meta_rows,
        output_dir=args.bundle_dir / "meta_pdfs",
        timeout_sec=float(args.timeout_sec),
        max_retries=int(args.max_retries),
        max_links_per_landing=int(args.max_links_per_landing),
        max_candidates=int(args.max_candidates),
        workers=int(args.workers),
    )
    trial_rows, trial_stats = _run_on_rows(
        trial_rows,
        output_dir=args.bundle_dir / "rct_trial_pdfs",
        timeout_sec=float(args.timeout_sec),
        max_retries=int(args.max_retries),
        max_links_per_landing=int(args.max_links_per_landing),
        max_candidates=int(args.max_candidates),
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
            "max_candidates": int(args.max_candidates),
            "max_links_per_landing": int(args.max_links_per_landing),
            "workers": int(args.workers),
        },
        "counts": {
            "meta_third_pass": meta_stats,
            "trial_third_pass": trial_stats,
            "meta_status_after": _status_counts(meta_rows),
            "trial_status_after": _status_counts(trial_rows),
        },
        "paths": {
            "meta_downloads_json": str(meta_path),
            "rct_trial_downloads_json": str(trial_path),
            "third_pass_summary_json": str(args.bundle_dir / "third_pass_summary.json"),
        },
    }
    (args.bundle_dir / "third_pass_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
