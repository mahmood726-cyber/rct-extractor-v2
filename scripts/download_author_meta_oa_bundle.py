#!/usr/bin/env python3
"""Download OA PDFs for author meta-analyses and referenced RCT papers."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


IDCONV_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
ELINK_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

USER_AGENT = "rct-extractor-v2-author-meta-oa/1.0"

RCT_PUBTYPE_HINTS = {
    "randomized controlled trial",
    "controlled clinical trial",
    "clinical trial",
    "clinical trial, phase i",
    "clinical trial, phase ii",
    "clinical trial, phase iii",
    "clinical trial, phase iv",
    "pragmatic clinical trial",
    "multicenter study",
}
NON_RCT_PUBTYPE_EXCLUDES = {
    "meta-analysis",
    "systematic review",
    "review",
    "practice guideline",
    "guideline",
    "comment",
    "editorial",
    "letter",
}
NON_RCT_TITLE_HINTS = (
    "meta-analysis",
    "meta analysis",
    "systematic review",
    "narrative review",
    "scoping review",
    "protocol",
)

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
    if text.startswith("PMC"):
        suffix = text[3:]
        return f"PMC{suffix}" if suffix.isdigit() else ""
    return f"PMC{text}" if text.isdigit() else ""


def _chunked(items: Sequence[str], size: int) -> Iterable[List[str]]:
    for start in range(0, len(items), size):
        yield list(items[start : start + size])


def _request_bytes(url: str, timeout_sec: float) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        return response.read()


def _request_json(url: str, timeout_sec: float) -> Dict:
    raw = _request_bytes(url=url, timeout_sec=timeout_sec)
    return json.loads(raw.decode("utf-8", errors="replace"))


def _load_pmids(pmids_file: Path) -> List[str]:
    text = pmids_file.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return []
    out: List[str] = []
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            values = payload.get("pmids") or payload.get("ids") or []
        elif isinstance(payload, list):
            values = payload
        else:
            values = []
        for value in values:
            pmid = _normalize_pmid(value)
            if pmid:
                out.append(pmid)
    except json.JSONDecodeError:
        for token in re.split(r"[\s,;]+", text):
            pmid = _normalize_pmid(token)
            if pmid:
                out.append(pmid)
    deduped: List[str] = []
    seen: Set[str] = set()
    for pmid in out:
        if pmid in seen:
            continue
        seen.add(pmid)
        deduped.append(pmid)
    return deduped


def _fetch_refs_for_meta_pmids(
    meta_pmids: Sequence[str],
    *,
    timeout_sec: float,
    sleep_sec: float,
    api_key: str,
) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for pmid in meta_pmids:
        params: List[Tuple[str, str]] = [
            ("dbfrom", "pubmed"),
            ("db", "pubmed"),
            ("id", pmid),
            ("linkname", "pubmed_pubmed_refs"),
            ("retmode", "json"),
        ]
        if api_key:
            params.append(("api_key", api_key))
        url = f"{ELINK_URL}?{urllib.parse.urlencode(params)}"
        refs: Set[str] = set()
        try:
            payload = _request_json(url=url, timeout_sec=timeout_sec)
            linksets = payload.get("linksets") or []
            if linksets:
                linksetdbs = linksets[0].get("linksetdbs") or []
                for db in linksetdbs:
                    if str(db.get("linkname") or "").lower() != "pubmed_pubmed_refs":
                        continue
                    for link_id in db.get("links") or []:
                        ref_pmid = _normalize_pmid(link_id)
                        if ref_pmid:
                            refs.add(ref_pmid)
        except Exception:
            refs = set()
        out[pmid] = sorted(refs)
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    return out


def _fetch_summaries(
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
            payload = _request_json(url=url, timeout_sec=timeout_sec)
        except Exception:
            payload = {}
        result = payload.get("result") or {}
        for uid in result.get("uids") or []:
            pmid = _normalize_pmid(uid)
            if not pmid:
                continue
            rec = result.get(uid) or {}
            out[pmid] = {
                "pmid": pmid,
                "title": str(rec.get("title") or ""),
                "pubdate": str(rec.get("pubdate") or ""),
                "journal": str(rec.get("fulljournalname") or rec.get("source") or ""),
                "pubtype": [str(x) for x in (rec.get("pubtype") or [])],
            }
        for pmid in batch:
            if pmid not in out:
                out[pmid] = {
                    "pmid": pmid,
                    "title": "",
                    "pubdate": "",
                    "journal": "",
                    "pubtype": [],
                }
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    return out


def _fetch_idconv_for_pmids(
    pmids: Sequence[str],
    *,
    timeout_sec: float,
    sleep_sec: float,
    api_key: str,
    batch_size: int = 200,
) -> Dict[str, Dict[str, Optional[str]]]:
    out: Dict[str, Dict[str, Optional[str]]] = {}
    if not pmids:
        return out
    for batch in _chunked(list(pmids), batch_size):
        params: List[Tuple[str, str]] = [
            ("ids", ",".join(batch)),
            ("format", "json"),
        ]
        if api_key:
            params.append(("api_key", api_key))
        url = f"{IDCONV_URL}?{urllib.parse.urlencode(params)}"
        try:
            payload = _request_json(url=url, timeout_sec=timeout_sec)
        except Exception:
            payload = {}
        seen: Set[str] = set()
        for rec in payload.get("records") or []:
            pmid = _normalize_pmid(rec.get("pmid") or rec.get("requested-id"))
            if not pmid:
                continue
            seen.add(pmid)
            out[pmid] = {
                "pmcid": _normalize_pmcid(rec.get("pmcid")),
                "doi": str(rec.get("doi") or "") or None,
            }
        for pmid in batch:
            if pmid not in seen and pmid not in out:
                out[pmid] = {"pmcid": None, "doi": None}
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    return out


def _is_rct_candidate(summary: Dict) -> Tuple[bool, str]:
    pubtypes = [str(item or "").lower().strip() for item in (summary.get("pubtype") or [])]
    title = str(summary.get("title") or "").lower()

    if any(token in NON_RCT_PUBTYPE_EXCLUDES for token in pubtypes):
        return False, "excluded_pubtype"

    if any(token in RCT_PUBTYPE_HINTS for token in pubtypes):
        return True, "rct_pubtype"

    if any(bad in title for bad in NON_RCT_TITLE_HINTS):
        return False, "excluded_title_hint"

    if re.search(r"\b(randomi[sz]ed|randomly assigned|placebo|clinical trial|double-blind|single-blind)\b", title):
        return True, "rct_title_hint"

    return False, "not_rct"


def _read_pdf_header(url: str, timeout_sec: float) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        return response.read()


def _download_pdf_for_pmcid(
    pmcid: str,
    output_path: Path,
    *,
    timeout_sec: float,
    retries: int,
) -> Tuple[bool, str, int]:
    for pattern in PDF_URL_PATTERNS:
        url = pattern.format(pmcid=pmcid)
        for _ in range(max(1, retries)):
            try:
                payload = _read_pdf_header(url=url, timeout_sec=timeout_sec)
                if len(payload) > 1024 and payload.startswith(b"%PDF"):
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(payload)
                    return True, url, len(payload)
            except urllib.error.HTTPError as exc:
                if exc.code in {404, 403}:
                    break
            except Exception:
                continue
    return False, "", 0


def _candidate_existing_pdf_paths(pmcid: str, roots: Sequence[Path]) -> List[Path]:
    candidates: List[Path] = []
    for root in roots:
        if not root.exists():
            continue
        candidates.append(root / f"{pmcid}.pdf")
        candidates.append(root / f"{pmcid.upper()}.pdf")
    return candidates


def _sanitize_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_") or "file"


def _download_records(
    items: Sequence[Dict],
    *,
    out_dir: Path,
    existing_roots: Sequence[Path],
    timeout_sec: float,
    retries: int,
    workers: int,
    copy_existing: bool,
) -> List[Dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    results: List[Dict] = []

    def _worker(item: Dict) -> Dict:
        pmid = str(item.get("pmid") or "")
        pmcid = _normalize_pmcid(item.get("pmcid"))
        kind = str(item.get("kind") or "")
        filename = f"{_sanitize_filename(kind)}__{pmid}__{pmcid or 'NO_PMCID'}.pdf"
        output_path = out_dir / filename

        row = {
            "kind": kind,
            "pmid": pmid,
            "pmcid": pmcid or None,
            "title": item.get("title") or "",
            "pubdate": item.get("pubdate") or "",
            "journal": item.get("journal") or "",
            "status": "unknown",
            "download_url": None,
            "size_bytes": None,
            "local_pdf_path": None,
            "existing_source_path": None,
            "rct_reason": item.get("rct_reason"),
        }

        if not pmcid:
            row["status"] = "no_pmcid"
            return row

        if output_path.exists() and output_path.stat().st_size > 1024:
            row["status"] = "already_downloaded"
            row["size_bytes"] = int(output_path.stat().st_size)
            row["local_pdf_path"] = str(output_path)
            return row

        for existing in _candidate_existing_pdf_paths(pmcid=pmcid, roots=existing_roots):
            if existing.exists() and existing.stat().st_size > 1024:
                row["existing_source_path"] = str(existing)
                if copy_existing:
                    out_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(existing, output_path)
                    row["status"] = "copied_existing"
                    row["size_bytes"] = int(output_path.stat().st_size)
                    row["local_pdf_path"] = str(output_path)
                else:
                    row["status"] = "existing_local"
                    row["size_bytes"] = int(existing.stat().st_size)
                    row["local_pdf_path"] = str(existing)
                return row

        ok, url, size_bytes = _download_pdf_for_pmcid(
            pmcid=pmcid,
            output_path=output_path,
            timeout_sec=timeout_sec,
            retries=retries,
        )
        if ok:
            row["status"] = "downloaded"
            row["download_url"] = url
            row["size_bytes"] = int(size_bytes)
            row["local_pdf_path"] = str(output_path)
            return row

        row["status"] = "download_failed"
        return row

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(_worker, item) for item in items]
        for future in as_completed(futures):
            row = future.result()
            with lock:
                results.append(row)
    results.sort(key=lambda x: (str(x.get("kind") or ""), str(x.get("pmid") or "")))
    return results


def _to_counts(rows: Sequence[Dict]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        key = str(row.get("status") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download OA meta and referenced RCT PDFs for an author PMID list."
    )
    parser.add_argument("--meta-pmids-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--existing-pdf-root",
        action="append",
        default=[],
        help="Optional existing PDF root to reuse (can pass multiple times).",
    )
    parser.add_argument("--copy-existing", action="store_true")
    parser.add_argument("--timeout-sec", type=float, default=30.0)
    parser.add_argument("--sleep-sec", type=float, default=0.12)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--api-key", type=str, default=os.environ.get("NCBI_API_KEY", ""))
    args = parser.parse_args()

    if not args.meta_pmids_file.exists():
        raise FileNotFoundError(f"--meta-pmids-file not found: {args.meta_pmids_file}")
    if args.timeout_sec <= 0:
        raise ValueError("--timeout-sec must be > 0")
    if args.sleep_sec < 0:
        raise ValueError("--sleep-sec must be >= 0")
    if args.workers <= 0:
        raise ValueError("--workers must be > 0")
    if args.retries <= 0:
        raise ValueError("--retries must be > 0")

    output_dir = args.output_dir
    meta_pdf_dir = output_dir / "meta_pdfs"
    trial_pdf_dir = output_dir / "rct_trial_pdfs"
    existing_roots = [Path(p) for p in args.existing_pdf_root]

    meta_pmids = _load_pmids(args.meta_pmids_file)
    if not meta_pmids:
        raise ValueError("No PMIDs parsed from --meta-pmids-file")

    print(f"Meta PMIDs loaded: {len(meta_pmids)}")
    meta_summaries = _fetch_summaries(
        meta_pmids,
        timeout_sec=args.timeout_sec,
        sleep_sec=args.sleep_sec,
        api_key=args.api_key,
    )
    meta_idconv = _fetch_idconv_for_pmids(
        meta_pmids,
        timeout_sec=args.timeout_sec,
        sleep_sec=args.sleep_sec,
        api_key=args.api_key,
    )

    print("Fetching PubMed references for meta PMIDs...")
    refs_by_meta = _fetch_refs_for_meta_pmids(
        meta_pmids,
        timeout_sec=args.timeout_sec,
        sleep_sec=args.sleep_sec,
        api_key=args.api_key,
    )

    all_ref_pmids: Set[str] = set()
    for refs in refs_by_meta.values():
        all_ref_pmids.update(refs)
    all_ref_pmids_sorted = sorted(all_ref_pmids)
    print(f"Unique referenced PMIDs: {len(all_ref_pmids_sorted)}")

    ref_summaries = _fetch_summaries(
        all_ref_pmids_sorted,
        timeout_sec=args.timeout_sec,
        sleep_sec=args.sleep_sec,
        api_key=args.api_key,
    )

    trial_pmids: List[str] = []
    trial_reason_by_pmid: Dict[str, str] = {}
    for pmid in all_ref_pmids_sorted:
        keep, reason = _is_rct_candidate(ref_summaries.get(pmid) or {})
        if keep:
            trial_pmids.append(pmid)
            trial_reason_by_pmid[pmid] = reason
    print(f"Referenced RCT candidate PMIDs: {len(trial_pmids)}")

    trial_idconv = _fetch_idconv_for_pmids(
        trial_pmids,
        timeout_sec=args.timeout_sec,
        sleep_sec=args.sleep_sec,
        api_key=args.api_key,
    )

    meta_items: List[Dict] = []
    for pmid in meta_pmids:
        summary = meta_summaries.get(pmid) or {}
        ids = meta_idconv.get(pmid) or {}
        meta_items.append(
            {
                "kind": "meta",
                "pmid": pmid,
                "pmcid": ids.get("pmcid"),
                "doi": ids.get("doi"),
                "title": summary.get("title") or "",
                "pubdate": summary.get("pubdate") or "",
                "journal": summary.get("journal") or "",
            }
        )

    trial_items: List[Dict] = []
    for pmid in trial_pmids:
        summary = ref_summaries.get(pmid) or {}
        ids = trial_idconv.get(pmid) or {}
        trial_items.append(
            {
                "kind": "rct_trial",
                "pmid": pmid,
                "pmcid": ids.get("pmcid"),
                "doi": ids.get("doi"),
                "title": summary.get("title") or "",
                "pubdate": summary.get("pubdate") or "",
                "journal": summary.get("journal") or "",
                "rct_reason": trial_reason_by_pmid.get(pmid),
            }
        )

    print("Downloading meta PDFs...")
    meta_downloads = _download_records(
        meta_items,
        out_dir=meta_pdf_dir,
        existing_roots=existing_roots,
        timeout_sec=args.timeout_sec,
        retries=args.retries,
        workers=args.workers,
        copy_existing=bool(args.copy_existing),
    )

    print("Downloading referenced RCT PDFs...")
    trial_downloads = _download_records(
        trial_items,
        out_dir=trial_pdf_dir,
        existing_roots=existing_roots,
        timeout_sec=args.timeout_sec,
        retries=args.retries,
        workers=args.workers,
        copy_existing=bool(args.copy_existing),
    )

    rct_refs_by_meta: Dict[str, List[str]] = {}
    for meta_pmid, refs in refs_by_meta.items():
        keep: List[str] = []
        for ref_pmid in refs:
            if ref_pmid in trial_reason_by_pmid:
                keep.append(ref_pmid)
        rct_refs_by_meta[meta_pmid] = sorted(keep)

    meta_pdf_count = len([x for x in meta_downloads if x.get("status") in {"downloaded", "already_downloaded", "copied_existing", "existing_local"}])
    trial_pdf_count = len([x for x in trial_downloads if x.get("status") in {"downloaded", "already_downloaded", "copied_existing", "existing_local"}])

    bundle = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "meta_pmids_file": str(args.meta_pmids_file),
            "output_dir": str(args.output_dir),
            "existing_pdf_roots": [str(p) for p in existing_roots],
            "copy_existing": bool(args.copy_existing),
            "timeout_sec": float(args.timeout_sec),
            "sleep_sec": float(args.sleep_sec),
            "workers": int(args.workers),
            "retries": int(args.retries),
            "api_key_present": bool(args.api_key),
        },
        "counts": {
            "meta_pmids_total": len(meta_pmids),
            "meta_pmids_with_refs": sum(1 for refs in refs_by_meta.values() if refs),
            "unique_ref_pmids_total": len(all_ref_pmids_sorted),
            "rct_ref_pmids_total": len(trial_pmids),
            "meta_pdfs_available_total": meta_pdf_count,
            "rct_trial_pdfs_available_total": trial_pdf_count,
            "meta_download_status": _to_counts(meta_downloads),
            "rct_trial_download_status": _to_counts(trial_downloads),
        },
        "paths": {
            "meta_pdfs_dir": str(meta_pdf_dir),
            "rct_trial_pdfs_dir": str(trial_pdf_dir),
            "meta_downloads_json": str(output_dir / "meta_downloads.json"),
            "rct_trial_downloads_json": str(output_dir / "rct_trial_downloads.json"),
            "meta_to_rct_refs_json": str(output_dir / "meta_to_rct_refs.json"),
            "bundle_summary_json": str(output_dir / "bundle_summary.json"),
        },
    }

    _write_json(output_dir / "meta_downloads.json", {"rows": meta_downloads})
    _write_json(output_dir / "rct_trial_downloads.json", {"rows": trial_downloads})
    _write_json(output_dir / "meta_to_rct_refs.json", {"rows": rct_refs_by_meta})
    _write_json(output_dir / "bundle_summary.json", bundle)

    print("Done.")
    print(json.dumps(bundle["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
