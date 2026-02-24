#!/usr/bin/env python3
"""Map extracted cardiology trial PMIDs to citing cardiology meta-analyses."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


IDCONV_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
ELINK_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
USER_AGENT = "rct-extractor-v2-cardiology-meta-map/1.0"

META_KEYWORDS = (
    "meta-analysis",
    "meta analysis",
    "systematic review",
    "network meta",
    "pooled analysis",
    "umbrella review",
)

STRICT_EXCLUDE_KEYWORDS = (
    "guideline",
    "consensus statement",
    "position statement",
    "narrative review",
)

CARDIOLOGY_KEYWORDS = (
    "cardio",
    "cardiac",
    "heart",
    "coronary",
    "myocard",
    "atrial fibrillation",
    "arrhythm",
    "ventric",
    "hypertension",
    "atheroscl",
    "angina",
    "valv",
    "stroke",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_pmcid(value: object) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return ""
    if text.startswith("PMC"):
        suffix = text[3:]
        if suffix.isdigit():
            return f"PMC{suffix}"
        return ""
    if text.isdigit():
        return f"PMC{text}"
    return ""


def _normalize_pmid(value: object) -> str:
    text = "".join(ch for ch in str(value or "") if ch.isdigit())
    return text


def _load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _load_latest_rows(path: Path) -> Dict[str, Dict]:
    latest: Dict[str, Dict] = {}
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            rel = str(row.get("pdf_relpath") or "").replace("\\", "/")
            if not rel:
                continue
            latest[rel] = row
    return latest


def _pmcid_from_relpath(relpath: str) -> str:
    upper = relpath.upper()
    idx = upper.find("PMC")
    if idx < 0:
        return ""
    tail = upper[idx + 3 :]
    digits = []
    for ch in tail:
        if ch.isdigit():
            digits.append(ch)
        else:
            break
    if not digits:
        return ""
    return f"PMC{''.join(digits)}"


def _request_json(url: str, timeout_sec: float) -> Dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        data = response.read().decode("utf-8", errors="replace")
    return json.loads(data)


def _idconv_batches(
    pmcids: Sequence[str],
    timeout_sec: float,
    sleep_sec: float,
    api_key: str,
    batch_size: int = 200,
) -> Dict[str, Optional[str]]:
    mapping: Dict[str, Optional[str]] = {}
    for start in range(0, len(pmcids), batch_size):
        batch = list(pmcids[start : start + batch_size])
        params: List[Tuple[str, str]] = [("ids", ",".join(batch)), ("format", "json")]
        if api_key:
            params.append(("api_key", api_key))
        url = f"{IDCONV_URL}?{urllib.parse.urlencode(params)}"
        payload = _request_json(url, timeout_sec=timeout_sec)
        seen: Set[str] = set()
        for record in payload.get("records", []):
            pmcid = _normalize_pmcid(record.get("pmcid"))
            if not pmcid:
                pmcid = _normalize_pmcid(record.get("pmcidid"))
            if not pmcid:
                continue
            seen.add(pmcid)
            pmid = _normalize_pmid(record.get("pmid"))
            mapping[pmcid] = pmid if pmid else None
        for pmcid in batch:
            norm = _normalize_pmcid(pmcid)
            if norm and norm not in seen:
                mapping[norm] = None
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    return mapping


def _fetch_citedin_links(
    pmids: Sequence[str],
    timeout_sec: float,
    sleep_sec: float,
    api_key: str,
    batch_size: int = 40,
) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for start in range(0, len(pmids), batch_size):
        batch = list(pmids[start : start + batch_size])
        params: List[Tuple[str, str]] = [
            ("dbfrom", "pubmed"),
            ("db", "pubmed"),
            ("linkname", "pubmed_pubmed_citedin"),
            ("retmode", "json"),
        ]
        params.extend(("id", pmid) for pmid in batch)
        if api_key:
            params.append(("api_key", api_key))
        url = f"{ELINK_URL}?{urllib.parse.urlencode(params)}"
        payload = _request_json(url, timeout_sec=timeout_sec)
        for linkset in payload.get("linksets", []):
            ids = linkset.get("ids") or []
            trial_pmid = _normalize_pmid(ids[0] if ids else "")
            if not trial_pmid:
                continue
            links: Set[str] = set()
            for db in linkset.get("linksetdbs") or []:
                if str(db.get("dbto") or "").lower() != "pubmed":
                    continue
                for item in db.get("links") or []:
                    cite_pmid = _normalize_pmid(item)
                    if cite_pmid:
                        links.add(cite_pmid)
            out[trial_pmid] = sorted(links)
        for pmid in batch:
            if pmid not in out:
                out[pmid] = []
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    return out


def _fetch_summaries(
    pmids: Sequence[str],
    timeout_sec: float,
    sleep_sec: float,
    api_key: str,
    batch_size: int = 150,
) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for start in range(0, len(pmids), batch_size):
        batch = list(pmids[start : start + batch_size])
        params: List[Tuple[str, str]] = [
            ("db", "pubmed"),
            ("id", ",".join(batch)),
            ("retmode", "json"),
        ]
        if api_key:
            params.append(("api_key", api_key))
        url = f"{ESUMMARY_URL}?{urllib.parse.urlencode(params)}"
        payload = _request_json(url, timeout_sec=timeout_sec)
        result = payload.get("result") or {}
        for uid in result.get("uids") or []:
            key = _normalize_pmid(uid)
            if not key:
                continue
            record = result.get(uid) or {}
            pubtypes = [str(item) for item in (record.get("pubtype") or [])]
            out[key] = {
                "pmid": key,
                "title": str(record.get("title") or ""),
                "fulljournalname": str(record.get("fulljournalname") or ""),
                "source": str(record.get("source") or ""),
                "pubdate": str(record.get("pubdate") or ""),
                "sortpubdate": str(record.get("sortpubdate") or ""),
                "pubtype": pubtypes,
            }
        for pmid in batch:
            if pmid not in out:
                out[pmid] = {
                    "pmid": pmid,
                    "title": "",
                    "fulljournalname": "",
                    "source": "",
                    "pubdate": "",
                    "sortpubdate": "",
                    "pubtype": [],
                }
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    return out


def _is_meta(summary: Dict, *, mode: str) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    pubtypes = [str(item).lower() for item in (summary.get("pubtype") or [])]
    title = str(summary.get("title") or "").lower()
    if any(item in {"meta-analysis", "systematic review", "network meta-analysis"} for item in pubtypes):
        reasons.append("pubtype")
    if any(keyword in title for keyword in META_KEYWORDS):
        reasons.append("title_keyword")
    if mode == "strict":
        if any(term in title for term in STRICT_EXCLUDE_KEYWORDS) and not reasons:
            return False, []
        if not reasons:
            return False, []
    return (len(reasons) > 0), reasons


def _is_cardiology(summary: Dict) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    text = " ".join(
        [
            str(summary.get("title") or "").lower(),
            str(summary.get("fulljournalname") or "").lower(),
            str(summary.get("source") or "").lower(),
        ]
    )
    for keyword in CARDIOLOGY_KEYWORDS:
        if keyword in text:
            reasons.append(keyword)
    return (len(reasons) > 0), sorted(set(reasons))


def _row_has_extractable_best(row: Dict) -> bool:
    if str(row.get("status") or "") != "extracted":
        return False
    best = row.get("best_match") or {}
    return best.get("effect_size") is not None


def _trial_rows_from_results(latest: Dict[str, Dict]) -> List[Dict]:
    rows: List[Dict] = []
    for relpath, row in sorted(latest.items(), key=lambda item: item[0]):
        if not _row_has_extractable_best(row):
            continue
        pmcid = _normalize_pmcid(row.get("pmcid")) or _pmcid_from_relpath(relpath)
        if not pmcid:
            continue
        rows.append(
            {
                "study_id": str(row.get("study_id") or ""),
                "pdf_relpath": relpath,
                "pmcid": pmcid,
                "best_match": row.get("best_match") or {},
            }
        )
    return rows


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-jsonl",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/results.jsonl"),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/meta_mapping_summary.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/meta_mapping_report.md"),
    )
    parser.add_argument(
        "--edges-jsonl",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/meta_mapping_edges.jsonl"),
    )
    parser.add_argument(
        "--trial-map-json",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/meta_mapping_trials.json"),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("output/cardiology_oa_full_v1_fast/cache_meta_map"),
    )
    parser.add_argument("--max-trials", type=int, default=None)
    parser.add_argument("--max-citing-per-trial", type=int, default=300)
    parser.add_argument("--max-meta-per-trial", type=int, default=80)
    parser.add_argument("--timeout-sec", type=float, default=25.0)
    parser.add_argument(
        "--meta-mode",
        choices=["strict", "sensitive"],
        default="strict",
        help="strict: require explicit meta/systematic signals; sensitive: broader keyword capture.",
    )
    parser.add_argument(
        "--require-cardiology",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Require cardiology keywords in citing meta-analysis title/journal.",
    )
    parser.add_argument("--sleep-sec", type=float, default=None)
    args = parser.parse_args()

    if not args.results_jsonl.exists():
        raise FileNotFoundError(f"Results JSONL not found: {args.results_jsonl}")
    if args.max_trials is not None and args.max_trials <= 0:
        raise ValueError("--max-trials must be > 0")
    if args.max_citing_per_trial <= 0:
        raise ValueError("--max-citing-per-trial must be > 0")
    if args.max_meta_per_trial <= 0:
        raise ValueError("--max-meta-per-trial must be > 0")
    if args.timeout_sec <= 0:
        raise ValueError("--timeout-sec must be > 0")

    api_key = str(os.environ.get("NCBI_API_KEY") or "").strip()
    default_sleep = 0.12 if api_key else 0.34
    sleep_sec = float(args.sleep_sec) if args.sleep_sec is not None else default_sleep

    cache_dir = args.cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    pmcid_cache_path = cache_dir / "pmcid_to_pmid.json"
    citedin_cache_path = cache_dir / "trial_citedin.json"
    summary_cache_path = cache_dir / "pmid_summary.json"

    pmcid_cache = _load_json(pmcid_cache_path)
    citedin_cache = _load_json(citedin_cache_path)
    summary_cache = _load_json(summary_cache_path)

    latest = _load_latest_rows(args.results_jsonl)
    trial_rows = _trial_rows_from_results(latest)
    if args.max_trials is not None:
        trial_rows = trial_rows[: int(args.max_trials)]

    pmcids = sorted({row["pmcid"] for row in trial_rows if row.get("pmcid")})
    missing_pmcids = [pmcid for pmcid in pmcids if pmcid not in pmcid_cache]
    if missing_pmcids:
        resolved = _idconv_batches(
            missing_pmcids,
            timeout_sec=float(args.timeout_sec),
            sleep_sec=sleep_sec,
            api_key=api_key,
            batch_size=200,
        )
        pmcid_cache.update(resolved)
        _write_json(pmcid_cache_path, pmcid_cache)

    trial_rows_with_pmid: List[Dict] = []
    pmid_to_trials: Dict[str, List[Dict]] = defaultdict(list)
    unresolved_pmcids = 0
    for row in trial_rows:
        pmcid = row.get("pmcid", "")
        pmid = _normalize_pmid(pmcid_cache.get(pmcid))
        if not pmid:
            unresolved_pmcids += 1
            continue
        row_copy = dict(row)
        row_copy["pmid"] = pmid
        trial_rows_with_pmid.append(row_copy)
        pmid_to_trials[pmid].append(row_copy)

    trial_pmids = sorted(pmid_to_trials.keys())
    missing_citedin = [pmid for pmid in trial_pmids if pmid not in citedin_cache]
    if missing_citedin:
        citedin_updates = _fetch_citedin_links(
            missing_citedin,
            timeout_sec=float(args.timeout_sec),
            sleep_sec=sleep_sec,
            api_key=api_key,
            batch_size=40,
        )
        citedin_cache.update(citedin_updates)
        _write_json(citedin_cache_path, citedin_cache)

    all_citing_pmids: Set[str] = set()
    for pmid in trial_pmids:
        links = list(citedin_cache.get(pmid) or [])
        if len(links) > int(args.max_citing_per_trial):
            links = links[: int(args.max_citing_per_trial)]
        for cite in links:
            norm = _normalize_pmid(cite)
            if norm:
                all_citing_pmids.add(norm)

    missing_summaries = [pmid for pmid in sorted(all_citing_pmids) if pmid not in summary_cache]
    if missing_summaries:
        summary_updates = _fetch_summaries(
            missing_summaries,
            timeout_sec=float(args.timeout_sec),
            sleep_sec=sleep_sec,
            api_key=api_key,
            batch_size=150,
        )
        summary_cache.update(summary_updates)
        _write_json(summary_cache_path, summary_cache)

    edges: List[Dict] = []
    trial_map_rows: List[Dict] = []
    meta_to_trials: Dict[str, Set[str]] = defaultdict(set)
    candidate_meta_pmids: Set[str] = set()

    for trial_pmid in trial_pmids:
        trials = pmid_to_trials.get(trial_pmid, [])
        citing_pmids = list(citedin_cache.get(trial_pmid) or [])
        if len(citing_pmids) > int(args.max_citing_per_trial):
            citing_pmids = citing_pmids[: int(args.max_citing_per_trial)]

        matched_meta_pmids: List[str] = []
        for cite_pmid in citing_pmids:
            cite_norm = _normalize_pmid(cite_pmid)
            if not cite_norm:
                continue
            summary = summary_cache.get(cite_norm) or {}
            is_meta, meta_reasons = _is_meta(summary, mode=str(args.meta_mode))
            if not is_meta:
                continue
            is_cardiology, cardio_reasons = _is_cardiology(summary)
            if bool(args.require_cardiology) and not is_cardiology:
                continue
            candidate_meta_pmids.add(cite_norm)
            matched_meta_pmids.append(cite_norm)
            meta_to_trials[cite_norm].add(trial_pmid)

            for trial in trials:
                edge = {
                    "trial_pmid": trial_pmid,
                    "trial_pmcid": trial.get("pmcid"),
                    "trial_study_id": trial.get("study_id"),
                    "trial_pdf_relpath": trial.get("pdf_relpath"),
                    "meta_pmid": cite_norm,
                    "meta_title": summary.get("title"),
                    "meta_pubdate": summary.get("pubdate"),
                    "meta_journal": summary.get("fulljournalname") or summary.get("source"),
                    "meta_pubtypes": summary.get("pubtype") or [],
                    "meta_match_reasons": meta_reasons,
                    "cardiology_match_terms": cardio_reasons,
                }
                edges.append(edge)

        unique_meta = sorted(set(matched_meta_pmids))
        if len(unique_meta) > int(args.max_meta_per_trial):
            unique_meta = unique_meta[: int(args.max_meta_per_trial)]
        trial_map_rows.append(
            {
                "trial_pmid": trial_pmid,
                "trial_study_ids": sorted({t.get("study_id") for t in trials if t.get("study_id")}),
                "trial_pmcids": sorted({t.get("pmcid") for t in trials if t.get("pmcid")}),
                "citing_total_considered": len(citing_pmids),
                "meta_matches_total": len(set(matched_meta_pmids)),
                "meta_pmids": unique_meta,
            }
        )

    meta_rows: List[Dict] = []
    for meta_pmid in sorted(candidate_meta_pmids):
        summary = summary_cache.get(meta_pmid) or {}
        meta_rows.append(
            {
                "meta_pmid": meta_pmid,
                "trial_pmid_count": len(meta_to_trials.get(meta_pmid) or set()),
                "title": summary.get("title"),
                "pubdate": summary.get("pubdate"),
                "journal": summary.get("fulljournalname") or summary.get("source"),
                "pubtype": summary.get("pubtype") or [],
            }
        )
    meta_rows.sort(key=lambda row: (-int(row["trial_pmid_count"]), str(row.get("meta_pmid"))))

    status_counts = Counter(str((latest.get(row.get("pdf_relpath", ""), {}) or {}).get("status") or "") for row in trial_rows)
    trials_with_meta = sum(1 for row in trial_map_rows if int(row.get("meta_matches_total") or 0) > 0)

    summary_payload = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "results_jsonl": str(args.results_jsonl).replace("\\", "/"),
            "max_trials": args.max_trials,
            "max_citing_per_trial": int(args.max_citing_per_trial),
            "max_meta_per_trial": int(args.max_meta_per_trial),
            "require_cardiology": bool(args.require_cardiology),
            "meta_mode": str(args.meta_mode),
        },
        "ncbi": {
            "api_key_present": bool(api_key),
            "request_sleep_sec": sleep_sec,
            "timeout_sec": float(args.timeout_sec),
        },
        "counts": {
            "trial_rows_considered": len(trial_rows),
            "trial_rows_with_pmid": len(trial_rows_with_pmid),
            "unresolved_pmcid_rows": unresolved_pmcids,
            "unique_trial_pmids": len(trial_pmids),
            "unique_citing_pmids_considered": len(all_citing_pmids),
            "unique_candidate_meta_pmids": len(candidate_meta_pmids),
            "trials_with_meta_matches": trials_with_meta,
            "edge_rows": len(edges),
        },
        "rates": {
            "trial_pmid_resolution_rate": (
                len(trial_rows_with_pmid) / len(trial_rows) if trial_rows else 0.0
            ),
            "trial_with_meta_rate": (
                trials_with_meta / len(trial_map_rows) if trial_map_rows else 0.0
            ),
        },
        "distributions": {
            "status_counts_considered_rows": dict(sorted(status_counts.items())),
        },
        "top_meta_rows": meta_rows[:50],
        "cache_sizes": {
            "pmcid_to_pmid": len(pmcid_cache),
            "trial_citedin": len(citedin_cache),
            "pmid_summary": len(summary_cache),
        },
        "paths": {
            "edges_jsonl": str(args.edges_jsonl).replace("\\", "/"),
            "trial_map_json": str(args.trial_map_json).replace("\\", "/"),
            "cache_dir": str(cache_dir).replace("\\", "/"),
        },
    }

    args.edges_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.edges_jsonl.open("w", encoding="utf-8", newline="\n") as handle:
        for row in edges:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    args.trial_map_json.parent.mkdir(parents=True, exist_ok=True)
    args.trial_map_json.write_text(
        json.dumps({"generated_at_utc": _utc_now(), "trials": trial_map_rows}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines: List[str] = []
    lines.append("# Cardiology Trial to Meta-Analysis Mapping")
    lines.append("")
    lines.append(f"- Generated UTC: {summary_payload['generated_at_utc']}")
    lines.append(f"- Trial rows considered: {summary_payload['counts']['trial_rows_considered']}")
    lines.append(f"- Trial rows with PMID: {summary_payload['counts']['trial_rows_with_pmid']}")
    lines.append(f"- Trial PMID resolution rate: {_fmt_pct(summary_payload['rates']['trial_pmid_resolution_rate'])}")
    lines.append(f"- Unique trial PMIDs: {summary_payload['counts']['unique_trial_pmids']}")
    lines.append(f"- Trials with >=1 meta match: {summary_payload['counts']['trials_with_meta_matches']}")
    lines.append(f"- Trial-with-meta rate: {_fmt_pct(summary_payload['rates']['trial_with_meta_rate'])}")
    lines.append(f"- Unique cardiology meta PMIDs: {summary_payload['counts']['unique_candidate_meta_pmids']}")
    lines.append(f"- Edge rows: {summary_payload['counts']['edge_rows']}")
    lines.append("")
    lines.append("## Top Meta Papers By Linked Trials")
    lines.append("")
    lines.append("| Meta PMID | Linked Trials | Pubdate | Journal | Title |")
    lines.append("| --- | ---: | --- | --- | --- |")
    for row in meta_rows[:30]:
        lines.append(
            f"| {row.get('meta_pmid')} | {row.get('trial_pmid_count')} | "
            f"{row.get('pubdate') or ''} | {row.get('journal') or ''} | {row.get('title') or ''} |"
        )
    lines.append("")
    lines.append(f"- Edges JSONL: `{args.edges_jsonl}`")
    lines.append(f"- Trial map JSON: `{args.trial_map_json}`")
    lines.append("")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {args.output_json}")
    print(f"Wrote: {args.output_md}")
    print(f"Wrote: {args.edges_jsonl}")
    print(f"Wrote: {args.trial_map_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
