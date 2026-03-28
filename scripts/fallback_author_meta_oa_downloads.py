#!/usr/bin/env python3
"""Second-pass OA PDF resolution for author-meta bundle downloads."""

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


ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
UNPAYWALL_URL = "https://api.unpaywall.org/v2/{doi}?email={email}"
USER_AGENT = "rct-extractor-v2-author-meta-oa-fallback/1.0"

TRANSIENT_HTTP_CODES = {408, 425, 429, 500, 502, 503, 504}
PDF_URL_PATTERNS = (
    "https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf",
    "https://europepmc.org/articles/{pmcid}?pdf=render",
    "https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_pmid(value: object) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _normalize_pmcid(value: object) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return ""
    match = re.search(r"PMC(\d+)", text, flags=re.IGNORECASE)
    if match:
        return f"PMC{match.group(1)}"
    return f"PMC{text}" if text.isdigit() else ""


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


def _chunked(items: Sequence[str], size: int) -> Iterable[List[str]]:
    for start in range(0, len(items), size):
        yield list(items[start : start + size])


def _load_rows(path: Path) -> List[Dict]:
    payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    rows = payload.get("rows")
    if isinstance(rows, list):
        return [dict(row) for row in rows if isinstance(row, dict)]
    return []


def _write_rows(path: Path, rows: Sequence[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"rows": list(rows)}, indent=2, ensure_ascii=False), encoding="utf-8")


def _looks_like_pdf_url(url: str) -> bool:
    if not url:
        return False
    parsed = urllib.parse.urlparse(url)
    path = (parsed.path or "").lower()
    if path.endswith(".pdf") or "/pdf/" in path or path.endswith("/pdf"):
        return True
    qs = urllib.parse.parse_qs(parsed.query or "", keep_blank_values=True)
    for key, values in qs.items():
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
    accept: str = "application/pdf,application/json,text/html;q=0.9,*/*;q=0.8",
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
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"request failed without error: {url}")


def _request_json(url: str, *, timeout_sec: float, max_retries: int) -> Dict:
    body, _, _ = _request_url(url, timeout_sec=timeout_sec, max_retries=max_retries, accept="application/json,*/*")
    return json.loads(body.decode("utf-8", errors="replace"))


def _extract_pdf_links_from_html(html_text: str, base_url: str, max_links: int) -> List[str]:
    patterns = [
        re.compile(r'(?i)citation_pdf_url["\']?\s+content=["\']([^"\']+)["\']'),
        re.compile(r'(?i)(?:href|src)\s*=\s*["\']([^"\']+)["\']'),
        re.compile(r'(?i)(https?://[^"\'\s<>]+\.pdf(?:\?[^"\'\s<>]*)?)'),
    ]
    out: List[str] = []
    seen: Set[str] = set()
    for pattern in patterns:
        for link in pattern.findall(html_text):
            if not isinstance(link, str):
                continue
            clean = html.unescape(link.strip())
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


def _fetch_unpaywall_candidates(
    doi: str,
    *,
    email: str,
    timeout_sec: float,
    max_retries: int,
) -> List[Dict[str, str]]:
    if not doi:
        return []
    url = UNPAYWALL_URL.format(doi=urllib.parse.quote(doi, safe=""), email=urllib.parse.quote(email, safe="@._+-"))
    try:
        payload = _request_json(url, timeout_sec=timeout_sec, max_retries=max_retries)
    except Exception:
        return []

    raw_locations: List[Dict] = []
    best = payload.get("best_oa_location")
    if isinstance(best, dict):
        raw_locations.append(best)
    raw_locations.extend(loc for loc in (payload.get("oa_locations") or []) if isinstance(loc, dict))

    out: List[Dict[str, str]] = []
    seen: Set[str] = set()
    for loc in raw_locations:
        host_type = str(loc.get("host_type") or "").strip().lower()
        for source in ("url_for_pdf", "url"):
            candidate_url = str(loc.get(source) or "").strip()
            if not candidate_url or candidate_url in seen:
                continue
            seen.add(candidate_url)
            out.append(
                {
                    "url": candidate_url,
                    "source": source,
                    "host_type": host_type,
                }
            )
    return out


def _parse_articleids(articleids: Sequence[Dict]) -> Tuple[str, str]:
    doi = ""
    pmcid = ""
    for item in articleids or []:
        idtype = str(item.get("idtype") or "").strip().lower()
        value = str(item.get("value") or "").strip()
        if idtype == "doi" and value:
            doi = _normalize_doi(value)
        if idtype in {"pmc", "pmcid"} and value:
            norm = _normalize_pmcid(value)
            if norm:
                pmcid = norm
    return doi, pmcid


def _fetch_pubmed_metadata(
    pmids: Sequence[str],
    *,
    timeout_sec: float,
    sleep_sec: float,
    api_key: str,
    batch_size: int = 150,
) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    if not pmids:
        return out
    for batch in _chunked(list(pmids), batch_size):
        params: List[Tuple[str, str]] = [
            ("db", "pubmed"),
            ("id", ",".join(batch)),
            ("retmode", "json"),
        ]
        if api_key:
            params.append(("api_key", api_key))
        url = f"{ESUMMARY_URL}?{urllib.parse.urlencode(params)}"
        try:
            payload = _request_json(url, timeout_sec=timeout_sec, max_retries=1)
        except Exception:
            payload = {}
        result = payload.get("result") or {}
        for uid in result.get("uids") or []:
            pmid = _normalize_pmid(uid)
            if not pmid:
                continue
            rec = result.get(uid) or {}
            doi, pmcid = _parse_articleids(rec.get("articleids") or [])
            out[pmid] = {
                "doi": doi,
                "pmcid": pmcid,
                "availablefromurl": str(rec.get("availablefromurl") or "").strip(),
                "title": str(rec.get("title") or ""),
                "pubdate": str(rec.get("pubdate") or ""),
                "journal": str(rec.get("fulljournalname") or rec.get("source") or ""),
            }
        for pmid in batch:
            if pmid not in out:
                out[pmid] = {
                    "doi": "",
                    "pmcid": "",
                    "availablefromurl": "",
                    "title": "",
                    "pubdate": "",
                    "journal": "",
                }
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    return out


def _download_pdf_from_url(
    url: str,
    output_path: Path,
    *,
    timeout_sec: float,
    max_retries: int,
) -> Tuple[bool, str, int]:
    try:
        body, final_url, _ = _request_url(url, timeout_sec=timeout_sec, max_retries=max_retries)
    except Exception:
        return False, "", 0
    if not body.startswith(b"%PDF") or len(body) < 1024:
        return False, final_url, 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(body)
    return True, final_url, len(body)


def _discover_from_landing(
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
    text = body.decode("utf-8", errors="replace")
    return _extract_pdf_links_from_html(text, base_url=final_url, max_links=max_links)


def _status_counts(rows: Sequence[Dict]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for row in rows:
        key = str(row.get("status") or "unknown")
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


def _resolve_rows(
    rows: List[Dict],
    *,
    output_dir: Path,
    metadata: Dict[str, Dict],
    timeout_sec: float,
    max_retries: int,
    max_candidates: int,
    max_links_per_landing: int,
    unpaywall_email: str,
    workers: int,
) -> Tuple[List[Dict], Dict[str, int]]:
    unresolved_statuses = {"no_pmcid", "download_failed"}
    lock = threading.Lock()
    stats = {
        "input_rows": len(rows),
        "fallback_target_rows": 0,
        "downloaded_new": 0,
        "still_unresolved": 0,
        "skipped_already_available": 0,
    }

    tasks: List[int] = []
    for idx, row in enumerate(rows):
        if str(row.get("status") or "") in unresolved_statuses:
            tasks.append(idx)
        else:
            stats["skipped_already_available"] += 1
    stats["fallback_target_rows"] = len(tasks)

    def _worker(idx: int) -> Tuple[int, Dict]:
        row = dict(rows[idx])
        pmid = _normalize_pmid(row.get("pmid"))
        kind = str(row.get("kind") or "item")
        if not pmid:
            row["fallback_attempted"] = True
            row["fallback_status"] = "missing_pmid"
            row["status"] = "fallback_failed"
            return idx, row

        meta = metadata.get(pmid) or {}
        doi = _normalize_doi(row.get("doi") or meta.get("doi"))
        pmcid = _normalize_pmcid(row.get("pmcid") or meta.get("pmcid"))
        availablefromurl = str(meta.get("availablefromurl") or "").strip()

        row["doi"] = doi or None
        row["pmcid"] = pmcid or None
        if not row.get("title"):
            row["title"] = str(meta.get("title") or "")
        if not row.get("pubdate"):
            row["pubdate"] = str(meta.get("pubdate") or "")
        if not row.get("journal"):
            row["journal"] = str(meta.get("journal") or "")

        suffix = pmcid if pmcid else "NO_PMCID"
        filename = f"{_safe_name(kind)}__{pmid}__{suffix}.pdf"
        output_path = output_dir / filename
        if output_path.exists() and output_path.stat().st_size > 1024:
            row["status"] = "already_downloaded"
            row["size_bytes"] = int(output_path.stat().st_size)
            row["local_pdf_path"] = str(output_path)
            row["fallback_attempted"] = True
            row["fallback_status"] = "already_present"
            return idx, row

        candidate_urls: List[Tuple[str, str, bool]] = []
        seen: Set[str] = set()

        if pmcid:
            for pattern in PDF_URL_PATTERNS:
                url = pattern.format(pmcid=pmcid)
                if url not in seen:
                    seen.add(url)
                    candidate_urls.append((url, "pmcid_direct", True))

        if doi:
            unpaywall = _fetch_unpaywall_candidates(
                doi=doi,
                email=unpaywall_email,
                timeout_sec=timeout_sec,
                max_retries=max_retries,
            )
            for cand in unpaywall:
                url = str(cand.get("url") or "").strip()
                source = str(cand.get("source") or "unpaywall")
                if not url or url in seen:
                    continue
                seen.add(url)
                allow_landing = source == "url"
                candidate_urls.append((url, f"unpaywall_{source}", allow_landing))

            doi_url = f"https://doi.org/{urllib.parse.quote(doi, safe='/')}"
            if doi_url not in seen:
                seen.add(doi_url)
                candidate_urls.append((doi_url, "doi_landing", True))

        if availablefromurl and availablefromurl not in seen:
            seen.add(availablefromurl)
            candidate_urls.append((availablefromurl, "pubmed_availablefromurl", True))

        if max_candidates > 0:
            candidate_urls = candidate_urls[:max_candidates]

        attempts: List[str] = []
        for url, source, allow_landing in candidate_urls:
            attempts.append(source)
            direct_ok, final_url, size_bytes = _download_pdf_from_url(
                url=url,
                output_path=output_path,
                timeout_sec=timeout_sec,
                max_retries=max_retries,
            )
            if direct_ok:
                row["status"] = f"downloaded_fallback_{source}"
                row["download_url"] = final_url or url
                row["size_bytes"] = int(size_bytes)
                row["local_pdf_path"] = str(output_path)
                row["fallback_attempted"] = True
                row["fallback_status"] = "downloaded"
                row["fallback_method"] = source
                row["fallback_candidate_sources"] = attempts
                return idx, row

            if not allow_landing:
                continue

            landing_links = _discover_from_landing(
                url=url,
                timeout_sec=timeout_sec,
                max_retries=max_retries,
                max_links=max_links_per_landing,
            )
            for link in landing_links:
                direct_ok, final_url, size_bytes = _download_pdf_from_url(
                    url=link,
                    output_path=output_path,
                    timeout_sec=timeout_sec,
                    max_retries=max_retries,
                )
                if direct_ok:
                    row["status"] = f"downloaded_fallback_{source}"
                    row["download_url"] = final_url or link
                    row["size_bytes"] = int(size_bytes)
                    row["local_pdf_path"] = str(output_path)
                    row["fallback_attempted"] = True
                    row["fallback_status"] = "downloaded"
                    row["fallback_method"] = source
                    row["fallback_candidate_sources"] = attempts
                    row["fallback_landing_hit"] = link
                    return idx, row

        row["status"] = "fallback_failed"
        row["fallback_attempted"] = True
        row["fallback_status"] = "failed"
        row["fallback_candidate_sources"] = attempts
        return idx, row

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(_worker, idx) for idx in tasks]
        for future in as_completed(futures):
            idx, row = future.result()
            with lock:
                rows[idx] = row
                if str(row.get("fallback_status") or "") == "downloaded":
                    stats["downloaded_new"] += 1
                elif str(row.get("status") or "") == "fallback_failed":
                    stats["still_unresolved"] += 1

    return rows, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--unpaywall-email", type=str, default="tooling@proton.me")
    parser.add_argument("--timeout-sec", type=float, default=15.0)
    parser.add_argument("--sleep-sec", type=float, default=0.08)
    parser.add_argument("--max-retries", type=int, default=1)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--max-candidates", type=int, default=8)
    parser.add_argument("--max-links-per-landing", type=int, default=8)
    parser.add_argument("--api-key", type=str, default="")
    args = parser.parse_args()

    if not args.bundle_dir.exists():
        raise FileNotFoundError(f"--bundle-dir not found: {args.bundle_dir}")
    if args.timeout_sec <= 0:
        raise ValueError("--timeout-sec must be > 0")
    if args.sleep_sec < 0:
        raise ValueError("--sleep-sec must be >= 0")
    if args.max_retries < 0:
        raise ValueError("--max-retries must be >= 0")
    if args.workers <= 0:
        raise ValueError("--workers must be > 0")
    if args.max_candidates <= 0:
        raise ValueError("--max-candidates must be > 0")
    if args.max_links_per_landing <= 0:
        raise ValueError("--max-links-per-landing must be > 0")

    meta_path = args.bundle_dir / "meta_downloads.json"
    trial_path = args.bundle_dir / "rct_trial_downloads.json"
    if not meta_path.exists() or not trial_path.exists():
        raise FileNotFoundError("bundle directory must contain meta_downloads.json and rct_trial_downloads.json")

    meta_rows = _load_rows(meta_path)
    trial_rows = _load_rows(trial_path)

    unresolved_statuses = {"no_pmcid", "download_failed"}
    pmids: Set[str] = set()
    for row in [*meta_rows, *trial_rows]:
        if str(row.get("status") or "") in unresolved_statuses:
            pmid = _normalize_pmid(row.get("pmid"))
            if pmid:
                pmids.add(pmid)

    metadata = _fetch_pubmed_metadata(
        sorted(pmids),
        timeout_sec=float(args.timeout_sec),
        sleep_sec=float(args.sleep_sec),
        api_key=str(args.api_key or ""),
    )

    meta_dir = args.bundle_dir / "meta_pdfs"
    trial_dir = args.bundle_dir / "rct_trial_pdfs"
    meta_rows, meta_stats = _resolve_rows(
        meta_rows,
        output_dir=meta_dir,
        metadata=metadata,
        timeout_sec=float(args.timeout_sec),
        max_retries=int(args.max_retries),
        max_candidates=int(args.max_candidates),
        max_links_per_landing=int(args.max_links_per_landing),
        unpaywall_email=str(args.unpaywall_email),
        workers=int(args.workers),
    )
    trial_rows, trial_stats = _resolve_rows(
        trial_rows,
        output_dir=trial_dir,
        metadata=metadata,
        timeout_sec=float(args.timeout_sec),
        max_retries=int(args.max_retries),
        max_candidates=int(args.max_candidates),
        max_links_per_landing=int(args.max_links_per_landing),
        unpaywall_email=str(args.unpaywall_email),
        workers=int(args.workers),
    )

    _write_rows(meta_path, meta_rows)
    _write_rows(trial_path, trial_rows)

    summary = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "bundle_dir": str(args.bundle_dir),
            "unpaywall_email": str(args.unpaywall_email),
            "timeout_sec": float(args.timeout_sec),
            "sleep_sec": float(args.sleep_sec),
            "max_retries": int(args.max_retries),
            "workers": int(args.workers),
            "max_candidates": int(args.max_candidates),
            "max_links_per_landing": int(args.max_links_per_landing),
            "api_key_present": bool(args.api_key),
        },
        "counts": {
            "meta_fallback": meta_stats,
            "trial_fallback": trial_stats,
            "meta_status_after": _status_counts(meta_rows),
            "trial_status_after": _status_counts(trial_rows),
        },
        "paths": {
            "meta_downloads_json": str(meta_path),
            "rct_trial_downloads_json": str(trial_path),
            "fallback_summary_json": str(args.bundle_dir / "fallback_summary.json"),
        },
    }

    (args.bundle_dir / "fallback_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(json.dumps(summary["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
