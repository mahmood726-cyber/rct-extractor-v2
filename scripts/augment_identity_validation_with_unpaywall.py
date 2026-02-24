#!/usr/bin/env python3
"""Augment a prepared cohort with DOI-validated OA PDFs from Unpaywall."""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import time
from urllib.parse import parse_qs, urljoin, urlparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EMAIL = "tooling@proton.me"
TRANSIENT_HTTP_CODES = {408, 425, 429, 500, 502, 503, 504}

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
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Accept": "application/pdf,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8",
    }


def _safe_study_slug(value: object) -> str:
    text = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(value or "study"))
    text = re.sub(r"_+", "_", text).strip("._-")
    return text or "study"


def _looks_like_pdf_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    path = (parsed.path or "").lower()
    if path.endswith(".pdf") or "/pdf/" in path or path.endswith("/pdf"):
        return True
    params = parse_qs(parsed.query or "", keep_blank_values=True)
    for key, values in params.items():
        key_l = key.lower()
        values_l = [str(v).lower() for v in values]
        if key_l in {"blobtype", "format"} and "pdf" in values_l:
            return True
        if key_l in {"download", "filename"} and any(value.endswith(".pdf") for value in values_l):
            return True
    return False


def _request_with_retries(
    *,
    url: str,
    timeout_sec: float,
    stream: bool,
    max_retries: int,
) -> requests.Response:
    backoff = 0.6
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(
                url,
                timeout=timeout_sec,
                headers=_headers(),
                allow_redirects=True,
                stream=stream,
            )
            if response.status_code in TRANSIENT_HTTP_CODES and attempt < max_retries:
                response.close()
                time.sleep(backoff * (attempt + 1))
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            if attempt >= max_retries:
                raise
            time.sleep(backoff * (attempt + 1))
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"Request failed without an exception for URL: {url}")


def _extract_pdf_links_from_html(html_text: str, base_url: str, max_links: int) -> List[str]:
    candidates: List[str] = []
    seen = set()

    patterns = [
        re.compile(r'(?i)citation_pdf_url["\']?\s+content=["\']([^"\']+)["\']'),
        re.compile(r'(?i)(?:href|src)\s*=\s*["\']([^"\']+)["\']'),
        re.compile(r'(?i)(https?://[^"\'\s<>]+\.pdf(?:\?[^"\'\s<>]*)?)'),
    ]

    for pattern in patterns:
        for raw_link in pattern.findall(html_text):
            if not isinstance(raw_link, str):
                continue
            clean = html.unescape(raw_link.strip())
            if not clean:
                continue
            absolute = urljoin(base_url, clean)
            if not _looks_like_pdf_url(absolute):
                continue
            if absolute in seen:
                continue
            seen.add(absolute)
            candidates.append(absolute)
            if len(candidates) >= max_links:
                return candidates
    return candidates


def _fetch_unpaywall_locations(
    *,
    doi: str,
    email: str,
    timeout_sec: float,
    max_retries: int,
) -> List[Dict[str, str]]:
    url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    try:
        response = _request_with_retries(url=url, timeout_sec=timeout_sec, stream=False, max_retries=max_retries)
    except requests.RequestException:
        return []
    payload = response.json()
    raw_locations: List[Dict] = []
    best = payload.get("best_oa_location")
    if isinstance(best, dict):
        raw_locations.append(best)
    raw_locations.extend(loc for loc in (payload.get("oa_locations") or []) if isinstance(loc, dict))

    candidates: List[Dict[str, str]] = []
    seen = set()
    for loc in raw_locations:
        host_type = str(loc.get("host_type") or "").strip().lower()
        for field_name in ("url_for_pdf", "url"):
            candidate_url = str(loc.get(field_name) or "").strip()
            if not candidate_url or candidate_url in seen:
                continue
            seen.add(candidate_url)
            candidates.append(
                {
                    "url": candidate_url,
                    "host_type": host_type,
                    "source": field_name,
                }
            )
    return candidates


def _discover_pdf_links_from_landing(
    *,
    landing_url: str,
    timeout_sec: float,
    max_retries: int,
    max_links: int,
) -> List[str]:
    response = _request_with_retries(
        url=landing_url,
        timeout_sec=timeout_sec,
        stream=False,
        max_retries=max_retries,
    )
    final_url = str(response.url or landing_url)
    body = response.content or b""
    if body.startswith(b"%PDF") and _looks_like_pdf_url(final_url):
        return [final_url]

    content_type = str(response.headers.get("content-type") or "").lower()
    if "html" not in content_type and "xml" not in content_type:
        return []
    text = response.text or ""
    return _extract_pdf_links_from_html(text, base_url=final_url, max_links=max_links)


def _download_pdf(url: str, output_path: Path, timeout_sec: float, max_retries: int) -> bool:
    with _request_with_retries(url=url, timeout_sec=timeout_sec, stream=True, max_retries=max_retries) as response:
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


def _pdf_contains_doi_local(pdf_path: Path, doi: str, parser: PDFParser) -> bool:
    content = parser.parse(str(pdf_path))
    text = "\n".join((page.full_text or "") for page in content.pages).lower()
    compact_text = re.sub(r"[^a-z0-9./]", "", text)
    compact_doi = re.sub(r"[^a-z0-9./]", "", doi.lower())
    return bool(compact_doi) and compact_doi in compact_text


def _pdf_contains_doi(
    *,
    pdf_path: Path,
    doi: str,
    parser: PDFParser,
    parse_timeout_sec: float,
) -> bool:
    # Parse in a subprocess with timeout to prevent single malformed PDFs
    # from stalling full augmentation runs.
    if parse_timeout_sec > 0:
        inline = (
            "import re,sys;"
            "from pathlib import Path;"
            "ROOT=Path(sys.argv[3]);"
            "sys.path.insert(0,str(ROOT));"
            "from src.pdf.pdf_parser import PDFParser;"
            "pdf=sys.argv[1]; doi=sys.argv[2].lower();"
            "p=PDFParser(); c=p.parse(pdf);"
            "t='\\n'.join((pg.full_text or '') for pg in c.pages).lower();"
            "ct=re.sub(r'[^a-z0-9./]','',t);"
            "cd=re.sub(r'[^a-z0-9./]','',doi);"
            "print('1' if cd and cd in ct else '0')"
        )
        try:
            proc = subprocess.run(
                [sys.executable, "-c", inline, str(pdf_path), doi, str(PROJECT_ROOT)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=parse_timeout_sec,
                check=False,
            )
            if proc.returncode == 0:
                out = (proc.stdout or "").strip().splitlines()
                return bool(out) and out[-1].strip() == "1"
            return False
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"pdf_parse_timeout:{parse_timeout_sec}s:{pdf_path.name}") from exc

    return _pdf_contains_doi_local(pdf_path=pdf_path, doi=doi, parser=parser)


def _candidate_sort_key(candidate: Dict[str, str], prefer_repository: bool) -> Tuple[int, int, int, str]:
    host = str(candidate.get("host_type") or "").lower()
    source = str(candidate.get("source") or "")
    url = str(candidate.get("url") or "")

    if prefer_repository:
        host_rank = 0 if host == "repository" else 1
    else:
        host_rank = 0 if host == "publisher" else 1

    source_rank = 0 if source == "url_for_pdf" else 1
    pdf_rank = 0 if _looks_like_pdf_url(url) else 1
    return host_rank, source_rank, pdf_rank, url


def _existing_local_pdf_path(row: Dict, preferred_pdf_dir: Path) -> Optional[Path]:
    relative_pdf = str(row.get("pdf_path") or "").strip()
    if relative_pdf:
        candidate = PROJECT_ROOT / Path(relative_pdf.replace("/", "\\"))
        if candidate.exists() and candidate.stat().st_size > 1024:
            return candidate

    pdf_filename = str(row.get("pdf_filename") or "").strip()
    if pdf_filename:
        candidate = preferred_pdf_dir / pdf_filename
        if candidate.exists() and candidate.stat().st_size > 1024:
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-cohort-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pdf-dir", type=Path, required=True)
    parser.add_argument("--unpaywall-email", type=str, default=DEFAULT_EMAIL)
    parser.add_argument("--request-timeout-sec", type=float, default=25.0)
    parser.add_argument("--sleep-sec", type=float, default=0.1)
    parser.add_argument("--max-attempts", type=int, default=None)
    parser.add_argument("--max-candidates-per-study", type=int, default=12)
    parser.add_argument("--max-landing-pages-per-study", type=int, default=3)
    parser.add_argument("--max-links-per-landing-page", type=int, default=8)
    parser.add_argument("--http-retries", type=int, default=2)
    parser.add_argument("--pdf-parse-timeout-sec", type=float, default=25.0)
    parser.add_argument(
        "--prefer-repository",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Prefer repository candidates before publisher links.",
    )
    args = parser.parse_args()

    manifest_path = args.input_cohort_dir / "manifest.jsonl"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")
    if args.request_timeout_sec <= 0:
        raise ValueError("--request-timeout-sec must be > 0")
    if args.sleep_sec < 0:
        raise ValueError("--sleep-sec must be >= 0")
    if args.max_candidates_per_study <= 0:
        raise ValueError("--max-candidates-per-study must be > 0")
    if args.max_landing_pages_per_study < 0:
        raise ValueError("--max-landing-pages-per-study must be >= 0")
    if args.max_links_per_landing_page <= 0:
        raise ValueError("--max-links-per-landing-page must be > 0")
    if args.http_retries < 0:
        raise ValueError("--http-retries must be >= 0")
    if args.pdf_parse_timeout_sec < 0:
        raise ValueError("--pdf-parse-timeout-sec must be >= 0")

    input_protocol_path = args.input_cohort_dir / "protocol_lock.json"
    input_protocol = _load_json(input_protocol_path) if input_protocol_path.exists() else {}
    rows = _load_jsonl(manifest_path)
    parser_pdf = PDFParser()

    stats = Counter()
    failures: List[Dict[str, str]] = []
    attempts = 0

    for row in rows:
        if row.get("local_pdf"):
            existing_pdf = _existing_local_pdf_path(row=row, preferred_pdf_dir=args.pdf_dir)
            if existing_pdf is not None:
                row["pdf_path"] = _relative_path(existing_pdf)
                stats["already_local"] += 1
                continue
            row["local_pdf"] = False
            row["download_status"] = "stale_local_pdf_flag"
            stats["stale_local_pdf_flag"] += 1

        doi = _normalize_doi(row.get("doi"))
        if not doi:
            stats["missing_doi"] += 1
            failures.append({"study_id": row.get("study_id", ""), "reason": "missing_doi"})
            continue

        filename = f"{_safe_study_slug(row.get('study_id', 'study'))}__doi.pdf"
        cached_pdf_path = args.pdf_dir / filename
        if cached_pdf_path.exists() and cached_pdf_path.stat().st_size > 1024:
            try:
                if _pdf_contains_doi(
                    pdf_path=cached_pdf_path,
                    doi=doi,
                    parser=parser_pdf,
                    parse_timeout_sec=args.pdf_parse_timeout_sec,
                ):
                    row["pdf_filename"] = filename
                    row["pdf_path"] = _relative_path(cached_pdf_path)
                    row["local_pdf"] = True
                    row["download_status"] = "reused_cached_download"
                    row["download_url"] = row.get("download_url")
                    row["content_valid"] = True
                    row["content_validation_reason"] = "matched_doi_in_cached_pdf_text"
                    row["identity_validation_method"] = "doi_text_match_cached"
                    stats["reused_cached_download"] += 1
                    continue
                stats["cached_pdf_doi_mismatch"] += 1
                cached_pdf_path.unlink(missing_ok=True)
            except Exception as exc:
                if isinstance(exc, TimeoutError):
                    stats["pdf_parse_timeouts"] += 1
                stats["cached_pdf_parse_errors"] += 1
                failures.append(
                    {
                        "study_id": row.get("study_id", ""),
                        "reason": "cached_pdf_parse_error",
                        "pdf_path": _relative_path(cached_pdf_path),
                        "error": str(exc)[:200],
                    }
                )

        if args.max_attempts is not None and attempts >= args.max_attempts:
            stats["skipped_max_attempts"] += 1
            continue
        attempts += 1
        stats["attempted_rows"] += 1

        base_candidates = _fetch_unpaywall_locations(
            doi=doi,
            email=args.unpaywall_email,
            timeout_sec=args.request_timeout_sec,
            max_retries=args.http_retries,
        )
        if not base_candidates:
            stats["no_oa_pdf_candidate"] += 1
            failures.append({"study_id": row.get("study_id", ""), "reason": "no_oa_pdf_candidate"})
            continue

        base_candidates = sorted(
            base_candidates,
            key=lambda candidate: _candidate_sort_key(candidate, prefer_repository=args.prefer_repository),
        )
        stats["unpaywall_candidates_total"] += len(base_candidates)

        download_candidates: List[Dict[str, str]] = []
        seen_candidate_urls = set()
        for candidate in base_candidates:
            candidate_url = str(candidate.get("url") or "").strip()
            if not candidate_url or candidate_url in seen_candidate_urls:
                continue
            seen_candidate_urls.add(candidate_url)
            source = str(candidate.get("source") or "")
            if source == "url_for_pdf" or _looks_like_pdf_url(candidate_url):
                download_candidates.append(candidate)

        landing_pages_checked = 0
        for candidate in base_candidates:
            if len(download_candidates) >= args.max_candidates_per_study:
                break
            if landing_pages_checked >= args.max_landing_pages_per_study:
                break
            source = str(candidate.get("source") or "")
            landing_url = str(candidate.get("url") or "").strip()
            host_type = str(candidate.get("host_type") or "")
            if source != "url" or not landing_url:
                continue
            if host_type != "repository":
                continue

            landing_pages_checked += 1
            stats["landing_pages_checked"] += 1
            try:
                discovered_links = _discover_pdf_links_from_landing(
                    landing_url=landing_url,
                    timeout_sec=args.request_timeout_sec,
                    max_retries=args.http_retries,
                    max_links=args.max_links_per_landing_page,
                )
            except Exception as exc:
                stats["landing_page_errors"] += 1
                failures.append(
                    {
                        "study_id": row.get("study_id", ""),
                        "reason": "landing_page_error",
                        "url": landing_url,
                        "error": str(exc)[:200],
                    }
                )
                continue

            if not discovered_links:
                stats["landing_pages_without_pdf_links"] += 1
                continue

            stats["landing_pages_with_pdf_links"] += 1
            for link in discovered_links:
                if link in seen_candidate_urls:
                    continue
                seen_candidate_urls.add(link)
                download_candidates.append(
                    {
                        "url": link,
                        "host_type": host_type,
                        "source": "landing_discovered_pdf",
                    }
                )
                if len(download_candidates) >= args.max_candidates_per_study:
                    break

        if not download_candidates:
            stats["no_downloadable_candidate"] += 1
            failures.append({"study_id": row.get("study_id", ""), "reason": "no_downloadable_candidate"})
            continue

        row["unpaywall_candidate_count"] = len(download_candidates)

        success = False
        for candidate in download_candidates[: args.max_candidates_per_study]:
            url = str(candidate.get("url") or "").strip()
            host_type = str(candidate.get("host_type") or "")
            source = str(candidate.get("source") or "")
            pdf_path = args.pdf_dir / filename
            stats["download_attempts"] += 1
            try:
                if not _download_pdf(
                    url=url,
                    output_path=pdf_path,
                    timeout_sec=args.request_timeout_sec,
                    max_retries=args.http_retries,
                ):
                    stats["non_pdf_response"] += 1
                    continue
                if not _pdf_contains_doi(
                    pdf_path=pdf_path,
                    doi=doi,
                    parser=parser_pdf,
                    parse_timeout_sec=args.pdf_parse_timeout_sec,
                ):
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
                row["unpaywall_candidate_source"] = source
                stats["downloaded_and_validated"] += 1
                success = True
                break
            except Exception as exc:
                if isinstance(exc, TimeoutError):
                    stats["pdf_parse_timeouts"] += 1
                stats["download_errors"] += 1
                failures.append(
                    {
                        "study_id": row.get("study_id", ""),
                        "reason": "download_or_parse_error",
                        "url": url,
                        "candidate_source": source,
                        "error": str(exc)[:200],
                    }
                )
                continue

        if not success:
            row["local_pdf"] = False
            row["download_status"] = "unpaywall_failed"
            row["content_valid"] = False
            row["content_validation_reason"] = "no_doi_matched_oa_pdf"
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
        "augmentation_failures_total": len(failures),
        "augmentation_failures_sample": failures[:200],
        "source_protocol_mode": input_protocol.get("mode"),
        "source_validation_stats": input_protocol.get("validation_stats", {}),
        "unpaywall_email": args.unpaywall_email,
        "request_timeout_sec": args.request_timeout_sec,
        "http_retries": args.http_retries,
        "pdf_parse_timeout_sec": args.pdf_parse_timeout_sec,
        "max_candidates_per_study": args.max_candidates_per_study,
        "max_landing_pages_per_study": args.max_landing_pages_per_study,
        "max_links_per_landing_page": args.max_links_per_landing_page,
        "prefer_repository": args.prefer_repository,
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
