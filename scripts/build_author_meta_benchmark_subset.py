#!/usr/bin/env python3
"""Build dual-human benchmark subset linked to a specific author's cardiology meta-analyses."""

from __future__ import annotations

import argparse
import json
import os
import random
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
USER_AGENT = "rct-extractor-v2-author-meta-subset/1.0"

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

META_HINTS = (
    "meta-analysis",
    "meta analysis",
    "network meta",
    "systematic review",
    "pooled analysis",
    "umbrella review",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _request_json(url: str, timeout_sec: float) -> Dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body)


def _normalize_pmid(value: object) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _load_jsonl(path: Path) -> List[Dict]:
    out: List[Dict] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                out.append(row)
    return out


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Sequence[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _esearch_pmids(
    *,
    term: str,
    retmax: int,
    timeout_sec: float,
    api_key: str,
) -> List[str]:
    params = {
        "db": "pubmed",
        "retmode": "json",
        "retmax": str(retmax),
        "sort": "pub+date",
        "term": term,
    }
    if api_key:
        params["api_key"] = api_key
    url = f"{ESEARCH_URL}?{urllib.parse.urlencode(params)}"
    payload = _request_json(url, timeout_sec=timeout_sec)
    ids = payload.get("esearchresult", {}).get("idlist", []) or []
    return [str(_normalize_pmid(v)) for v in ids if _normalize_pmid(v)]


def _esummary_pmids(
    *,
    pmids: Sequence[str],
    timeout_sec: float,
    api_key: str,
    batch_size: int,
    sleep_sec: float,
) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for start in range(0, len(pmids), batch_size):
        batch = [p for p in pmids[start : start + batch_size] if p]
        if not batch:
            continue
        params = {
            "db": "pubmed",
            "retmode": "json",
            "id": ",".join(batch),
        }
        if api_key:
            params["api_key"] = api_key
        url = f"{ESUMMARY_URL}?{urllib.parse.urlencode(params)}"
        payload = _request_json(url, timeout_sec=timeout_sec)
        result = payload.get("result") or {}
        uids = result.get("uids") or []
        for uid in uids:
            pmid = _normalize_pmid(uid)
            if not pmid:
                continue
            rec = result.get(uid) or {}
            authors = rec.get("authors") if isinstance(rec.get("authors"), list) else []
            out[pmid] = {
                "pmid": pmid,
                "title": str(rec.get("title") or ""),
                "fulljournalname": str(rec.get("fulljournalname") or ""),
                "source": str(rec.get("source") or ""),
                "pubdate": str(rec.get("pubdate") or ""),
                "sortpubdate": str(rec.get("sortpubdate") or ""),
                "pubtype": [str(v) for v in (rec.get("pubtype") or [])],
                "authors": [str(a.get("name") or "") for a in authors if isinstance(a, dict)],
            }
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    return out


def _text_for_record(rec: Dict) -> str:
    return " ".join(
        [
            str(rec.get("title") or "").lower(),
            str(rec.get("fulljournalname") or "").lower(),
            str(rec.get("source") or "").lower(),
        ]
    )


def _record_is_meta(rec: Dict) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    pubtypes = [str(v).lower() for v in (rec.get("pubtype") or [])]
    if any(v in {"meta-analysis", "systematic review", "network meta-analysis"} for v in pubtypes):
        reasons.append("pubtype")
    title = str(rec.get("title") or "").lower()
    if any(h in title for h in META_HINTS):
        reasons.append("title_hint")
    return (len(reasons) > 0), reasons


def _record_is_cardiology(rec: Dict) -> Tuple[bool, List[str]]:
    text = _text_for_record(rec)
    hits = [k for k in CARDIOLOGY_KEYWORDS if k in text]
    return (len(hits) > 0), sorted(set(hits))


def _author_name_match(author_name: str, rec: Dict) -> bool:
    want = str(author_name or "").strip().lower()
    if not want:
        return True
    parts = [p for p in want.replace(",", " ").split() if p]
    if not parts:
        return True
    authors = [str(v).lower() for v in (rec.get("authors") or []) if str(v).strip()]
    if not authors:
        return False
    initials = {p[0] for p in parts if p}
    surname_candidates = {parts[0], parts[-1]}
    for a in authors:
        a_tokens = [t for t in a.replace(".", " ").replace(",", " ").split() if t]
        if all(p in a for p in parts):
            return True
        # Handle abbreviated author lists like "Ahmad M".
        surname_hit = any((s in a_tokens) or (f"{s} " in f"{a} ") for s in surname_candidates)
        if not surname_hit:
            continue
        if len(parts) == 1:
            return True
        token_initials = {t[0] for t in a_tokens if t}
        if token_initials & initials:
            return True
    return False


def _status_rank(status: str) -> int:
    if status == "no_extraction":
        return 0
    if status == "timeout":
        return 1
    if status == "error":
        return 2
    if status == "extracted":
        return 3
    return 4


def _allocate_by_status(entries: Sequence[Dict], target_n: int) -> Dict[str, int]:
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    for row in entries:
        grouped[str(row.get("status_snapshot") or "unknown")].append(row)
    total = len(entries)
    if target_n <= 0 or total <= 0:
        return {k: 0 for k in grouped}

    alloc: Dict[str, int] = {}
    fractional: List[Tuple[str, float]] = []
    used = 0
    for key, rows in grouped.items():
        raw = (len(rows) * target_n) / total
        base = int(raw)
        alloc[key] = min(base, len(rows))
        used += alloc[key]
        fractional.append((key, raw - base))
    remain = target_n - used
    fractional.sort(key=lambda x: x[1], reverse=True)
    for key, _ in fractional:
        if remain <= 0:
            break
        cap = len(grouped[key]) - alloc[key]
        if cap <= 0:
            continue
        alloc[key] += 1
        remain -= 1
    return alloc


def _sample_entries(entries: Sequence[Dict], target_n: Optional[int], seed: int) -> List[Dict]:
    if target_n is None or target_n >= len(entries):
        out = list(entries)
    else:
        alloc = _allocate_by_status(entries, target_n)
        rng = random.Random(seed)
        grouped: Dict[str, List[Dict]] = defaultdict(list)
        for row in entries:
            grouped[str(row.get("status_snapshot") or "unknown")].append(row)
        out = []
        for key, rows in sorted(grouped.items()):
            keep = alloc.get(key, 0)
            if keep <= 0:
                continue
            rows_copy = list(rows)
            rows_copy.sort(
                key=lambda r: (
                    -int(r.get("linked_meta_matches_total") or 0),
                    str(r.get("pdf_relpath") or ""),
                )
            )
            head_n = max(0, keep // 2)
            head = rows_copy[:head_n]
            tail = rows_copy[head_n:]
            rng.shuffle(tail)
            out.extend((head + tail)[:keep])
    out.sort(
        key=lambda r: (
            _status_rank(str(r.get("status_snapshot") or "")),
            -int(r.get("linked_meta_matches_total") or 0),
            str(r.get("pdf_relpath") or ""),
        )
    )
    for idx, row in enumerate(out, start=1):
        row["author_subset_id"] = f"author_meta_{idx:05d}"
    return out


def _blinded_row(entry: Dict) -> Dict:
    return {
        "author_subset_id": entry.get("author_subset_id"),
        "benchmark_id": entry.get("benchmark_id"),
        "study_id": entry.get("study_id"),
        "pdf_relpath": entry.get("pdf_relpath"),
        "pdf_abs_path": entry.get("pdf_abs_path"),
        "pmcid": entry.get("pmcid"),
        "pmid": entry.get("pmid"),
        "linked_meta_matches_total": entry.get("linked_meta_matches_total"),
        "linked_author_meta_pmids": entry.get("linked_author_meta_pmids"),
        "annotation": {
            "included": None,
            "effect_type": None,
            "point_estimate": None,
            "ci_lower": None,
            "ci_upper": None,
            "p_value": None,
            "source_text": "",
            "page_number": None,
            "notes": "",
        },
    }


def _adjudication_row(entry: Dict) -> Dict:
    return {
        "author_subset_id": entry.get("author_subset_id"),
        "benchmark_id": entry.get("benchmark_id"),
        "study_id": entry.get("study_id"),
        "pdf_relpath": entry.get("pdf_relpath"),
        "pdf_abs_path": entry.get("pdf_abs_path"),
        "pmcid": entry.get("pmcid"),
        "pmid": entry.get("pmid"),
        "linked_meta_matches_total": entry.get("linked_meta_matches_total"),
        "linked_author_meta_pmids": entry.get("linked_author_meta_pmids"),
        "gold": {
            "included": None,
            "effect_type": None,
            "point_estimate": None,
            "ci_lower": None,
            "ci_upper": None,
            "p_value": None,
            "source_text": "",
            "page_number": None,
            "notes": "",
        },
        "adjudication_notes": "",
    }


def _write_readme(path: Path, manifest: Dict) -> None:
    lines: List[str] = []
    lines.append("# Author Meta Linked Benchmark Subset")
    lines.append("")
    lines.append(f"- Generated UTC: {manifest.get('generated_at_utc')}")
    lines.append(f"- Author query: `{manifest.get('inputs', {}).get('pubmed_term')}`")
    lines.append(
        f"- Candidate PubMed metas: {manifest.get('counts', {}).get('author_meta_candidates_after_filters', 0)}"
    )
    lines.append(
        f"- Candidate metas linked in cohort: {manifest.get('counts', {}).get('author_meta_linked_to_benchmark', 0)}"
    )
    lines.append(f"- Selected trial rows: {manifest.get('counts', {}).get('selected_rows', 0)}")
    lines.append("")
    lines.append("## Note")
    lines.append("")
    lines.append(
        "- Author-name queries can include homonyms. Review `author_meta_candidates.json` before external claims."
    )
    lines.append("")
    lines.append("## Files")
    lines.append("")
    paths = manifest.get("paths", {})
    for key in (
        "author_meta_candidates_json",
        "author_meta_pmids_json",
        "benchmark_subset_jsonl",
        "blinded_template_annotator_a_jsonl",
        "blinded_template_annotator_b_jsonl",
        "adjudication_template_jsonl",
        "model_seed_adjudicator_only_jsonl",
        "manifest_json",
    ):
        value = paths.get(key)
        if value:
            lines.append(f"- `{value}`")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _collect_manual_pmids(pmids_csv: Optional[str], pmids_file: Optional[Path]) -> List[str]:
    out: List[str] = []
    if pmids_csv:
        for token in str(pmids_csv).split(","):
            pmid = _normalize_pmid(token)
            if pmid:
                out.append(pmid)
    if pmids_file is not None and pmids_file.exists():
        text = pmids_file.read_text(encoding="utf-8", errors="replace")
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
            for line in text.splitlines():
                pmid = _normalize_pmid(line.strip())
                if pmid:
                    out.append(pmid)
    deduped: List[str] = []
    seen = set()
    for pmid in out:
        if pmid in seen:
            continue
        seen.add(pmid)
        deduped.append(pmid)
    return deduped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark-cohort-jsonl",
        type=Path,
        default=Path("data/benchmarks/cardiology_meta_linked_v1/benchmark_cohort.jsonl"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/benchmarks/cardiology_meta_linked_mahmood_ahmad_v1"),
    )
    parser.add_argument("--author-full-name", type=str, default="Ahmad Mahmood")
    parser.add_argument(
        "--author-meta-pmids",
        type=str,
        default=None,
        help="Optional comma-separated PMID list to bypass PubMed author search.",
    )
    parser.add_argument(
        "--author-meta-pmids-file",
        type=Path,
        default=None,
        help="Optional file with PMIDs (json {pmids:[...]} or one PMID per line).",
    )
    parser.add_argument(
        "--pubmed-term",
        type=str,
        default=None,
        help="Optional full PubMed term override.",
    )
    parser.add_argument("--retmax", type=int, default=300)
    parser.add_argument("--timeout-sec", type=float, default=30.0)
    parser.add_argument("--batch-size", type=int, default=150)
    parser.add_argument("--sleep-sec", type=float, default=None)
    parser.add_argument("--target-n", type=int, default=None)
    parser.add_argument("--seed", type=int, default=20260224)
    parser.add_argument("--max-meta-pmids-per-row", type=int, default=30)
    parser.add_argument(
        "--require-author-name-in-authors",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Require author-name token match in esummary author list.",
    )
    parser.add_argument(
        "--require-meta",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--require-cardiology",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    args = parser.parse_args()

    if not args.benchmark_cohort_jsonl.exists():
        raise FileNotFoundError(f"Benchmark cohort not found: {args.benchmark_cohort_jsonl}")
    if args.retmax <= 0:
        raise ValueError("--retmax must be > 0")
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be > 0")
    if args.timeout_sec <= 0:
        raise ValueError("--timeout-sec must be > 0")
    if args.target_n is not None and args.target_n <= 0:
        raise ValueError("--target-n must be > 0 when provided")
    if args.author_meta_pmids_file is not None and not args.author_meta_pmids_file.exists():
        raise FileNotFoundError(f"--author-meta-pmids-file not found: {args.author_meta_pmids_file}")

    api_key = str(os.environ.get("NCBI_API_KEY") or "").strip()
    sleep_sec = float(args.sleep_sec) if args.sleep_sec is not None else (0.12 if api_key else 0.34)

    benchmark_rows = _load_jsonl(args.benchmark_cohort_jsonl)
    if not benchmark_rows:
        raise ValueError(f"No rows in benchmark cohort: {args.benchmark_cohort_jsonl}")

    manual_pmids = _collect_manual_pmids(args.author_meta_pmids, args.author_meta_pmids_file)
    if manual_pmids:
        term = str(args.pubmed_term or f"manual_pmids:{len(manual_pmids)}")
        pmids = list(manual_pmids)
    else:
        if args.pubmed_term:
            term = str(args.pubmed_term)
        else:
            author_term = f"{args.author_full_name}[Author - Full]"
            term = (
                f"{author_term} AND "
                "(Meta-Analysis[Publication Type] OR Systematic Review[Publication Type] "
                "OR systematic[sb] OR meta-analysis[Title] OR systematic review[Title])"
            )
        pmids = _esearch_pmids(
            term=term,
            retmax=int(args.retmax),
            timeout_sec=float(args.timeout_sec),
            api_key=api_key,
        )
    summary = _esummary_pmids(
        pmids=pmids,
        timeout_sec=float(args.timeout_sec),
        api_key=api_key,
        batch_size=int(args.batch_size),
        sleep_sec=float(sleep_sec),
    )

    candidates_all: List[Dict] = []
    author_meta_pmids: List[str] = []
    for pmid in pmids:
        rec = summary.get(pmid) or {"pmid": pmid, "title": "", "pubtype": [], "authors": []}
        author_ok = True if manual_pmids else (
            _author_name_match(args.author_full_name, rec)
            if bool(args.require_author_name_in_authors)
            else True
        )
        is_meta, meta_reasons = _record_is_meta(rec)
        is_cardio, cardio_terms = _record_is_cardiology(rec)

        accepted = author_ok
        if bool(args.require_meta):
            accepted = accepted and is_meta
        if bool(args.require_cardiology):
            accepted = accepted and is_cardio

        row = {
            "pmid": pmid,
            "title": rec.get("title"),
            "pubdate": rec.get("pubdate"),
            "journal": rec.get("fulljournalname") or rec.get("source"),
            "pubtype": rec.get("pubtype") or [],
            "authors": rec.get("authors") or [],
            "author_name_match": bool(author_ok),
            "is_meta": bool(is_meta),
            "meta_reasons": meta_reasons,
            "is_cardiology": bool(is_cardio),
            "cardiology_terms": cardio_terms,
            "accepted": bool(accepted),
        }
        candidates_all.append(row)
        if accepted:
            author_meta_pmids.append(pmid)

    author_meta_set = set(author_meta_pmids)
    subset_rows: List[Dict] = []
    linked_meta_counter: Counter = Counter()
    for row in benchmark_rows:
        linked_pmids = [_normalize_pmid(v) for v in (row.get("linked_meta_pmids") or [])]
        overlap = [p for p in linked_pmids if p in author_meta_set]
        if not overlap:
            continue
        out_row = dict(row)
        out_row["linked_author_meta_pmids"] = overlap[: int(args.max_meta_pmids_per_row)]
        out_row["linked_author_meta_count"] = len(overlap)
        subset_rows.append(out_row)
        for pmid in set(overlap):
            linked_meta_counter[pmid] += 1

    subset_rows = _sample_entries(subset_rows, target_n=args.target_n, seed=int(args.seed))

    # Stable IDs for subset.
    for idx, row in enumerate(subset_rows, start=1):
        row["author_subset_id"] = f"author_meta_{idx:05d}"

    annotator_a = [_blinded_row(r) for r in subset_rows]
    annotator_b = [_blinded_row(r) for r in subset_rows]
    adjudication = [_adjudication_row(r) for r in subset_rows]
    model_seed = subset_rows

    subset_status_counts = Counter(str(r.get("status_snapshot") or "") for r in subset_rows)

    linked_author_meta_rows: List[Dict] = []
    by_pmid = {row.get("pmid"): row for row in candidates_all}
    for pmid, linked_count in sorted(linked_meta_counter.items(), key=lambda item: (-item[1], item[0])):
        src = by_pmid.get(pmid) or {"pmid": pmid}
        linked_author_meta_rows.append(
            {
                "pmid": pmid,
                "linked_trial_rows": int(linked_count),
                "title": src.get("title"),
                "pubdate": src.get("pubdate"),
                "journal": src.get("journal"),
                "pubtype": src.get("pubtype") or [],
                "authors": src.get("authors") or [],
            }
        )

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "author_meta_candidates_json": "author_meta_candidates.json",
        "author_meta_pmids_json": "author_meta_pmids.json",
        "linked_author_meta_json": "linked_author_meta.json",
        "benchmark_subset_jsonl": "benchmark_subset.jsonl",
        "blinded_template_annotator_a_jsonl": "blinded_template_annotator_a.jsonl",
        "blinded_template_annotator_b_jsonl": "blinded_template_annotator_b.jsonl",
        "adjudication_template_jsonl": "adjudication_template.jsonl",
        "model_seed_adjudicator_only_jsonl": "model_seed_adjudicator_only.jsonl",
        "manifest_json": "manifest.json",
        "readme_md": "README.md",
    }

    _write_json(output_dir / files["author_meta_candidates_json"], {"rows": candidates_all})
    _write_json(output_dir / files["author_meta_pmids_json"], {"pmids": author_meta_pmids})
    _write_json(output_dir / files["linked_author_meta_json"], {"rows": linked_author_meta_rows})
    _write_jsonl(output_dir / files["benchmark_subset_jsonl"], subset_rows)
    _write_jsonl(output_dir / files["blinded_template_annotator_a_jsonl"], annotator_a)
    _write_jsonl(output_dir / files["blinded_template_annotator_b_jsonl"], annotator_b)
    _write_jsonl(output_dir / files["adjudication_template_jsonl"], adjudication)
    _write_jsonl(output_dir / files["model_seed_adjudicator_only_jsonl"], model_seed)

    manifest = {
        "generated_at_utc": _utc_now(),
        "inputs": {
            "benchmark_cohort_jsonl": str(args.benchmark_cohort_jsonl).replace("\\", "/"),
            "author_full_name": args.author_full_name,
            "author_meta_pmids_manual_count": len(manual_pmids),
            "author_meta_pmids_file": (
                str(args.author_meta_pmids_file).replace("\\", "/")
                if args.author_meta_pmids_file is not None
                else None
            ),
            "pubmed_term": term,
            "retmax": int(args.retmax),
            "require_author_name_in_authors": bool(args.require_author_name_in_authors),
            "require_meta": bool(args.require_meta),
            "require_cardiology": bool(args.require_cardiology),
            "target_n": args.target_n,
            "seed": int(args.seed),
            "api_key_present": bool(api_key),
        },
        "counts": {
            "pubmed_ids_retrieved": len(pmids),
            "author_meta_candidates_after_filters": len(author_meta_pmids),
            "author_meta_linked_to_benchmark": len(linked_meta_counter),
            "subset_rows_before_sampling": sum(1 for _ in benchmark_rows if any(_normalize_pmid(v) in author_meta_set for v in (_.get("linked_meta_pmids") or []))),
            "selected_rows": len(subset_rows),
            "selected_unique_pmids": len({str(r.get("pmid") or "") for r in subset_rows if r.get("pmid")}),
            "selected_status_counts": dict(sorted(subset_status_counts.items())),
        },
        "paths": files,
    }
    _write_json(output_dir / files["manifest_json"], manifest)
    _write_readme(output_dir / files["readme_md"], manifest)

    print(f"Wrote: {output_dir / files['author_meta_candidates_json']}")
    print(f"Wrote: {output_dir / files['author_meta_pmids_json']}")
    print(f"Wrote: {output_dir / files['linked_author_meta_json']}")
    print(f"Wrote: {output_dir / files['benchmark_subset_jsonl']}")
    print(f"Wrote: {output_dir / files['blinded_template_annotator_a_jsonl']}")
    print(f"Wrote: {output_dir / files['blinded_template_annotator_b_jsonl']}")
    print(f"Wrote: {output_dir / files['adjudication_template_jsonl']}")
    print(f"Wrote: {output_dir / files['model_seed_adjudicator_only_jsonl']}")
    print(f"Wrote: {output_dir / files['manifest_json']}")
    print(f"Wrote: {output_dir / files['readme_md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
