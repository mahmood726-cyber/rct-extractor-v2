#!/usr/bin/env python3
"""Generate PDF evidence snippets for residual far-miss extracted_no_match studies."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.mega_evaluate import _canonical_study_key, _load_latest_eval_rows, load_entries_with_pdfs
from src.pdf.pdf_parser import PDFParser


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "were",
    "was",
    "are",
    "any",
    "all",
    "vs",
    "subgrouped",
    "subgroup",
    "analysis",
    "based",
    "time",
    "since",
    "studies",
    "study",
    "post",
    "intervention",
    "without",
    "high",
    "risk",
    "bias",
}


def _load_diag_rows(path: Path) -> List[dict]:
    obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    rows = obj.get("rows")
    if isinstance(rows, list):
        return rows
    return []


def _extract_keywords(outcome: str, max_keywords: int) -> List[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z-]{2,}", str(outcome or "").lower())
    out: List[str] = []
    seen = set()
    for token in tokens:
        if token in STOPWORDS:
            continue
        if token in seen:
            continue
        seen.add(token)
        out.append(token)
        if len(out) >= max_keywords:
            break
    return out


def _number_tokens(value: Optional[float]) -> List[str]:
    if value is None:
        return []
    try:
        v = float(value)
    except (TypeError, ValueError):
        return []

    out = []
    for decimals in (4, 3, 2, 1):
        token = f"{v:.{decimals}f}".rstrip("0").rstrip(".")
        if token in {"0", "-0"}:
            continue
        if token and token not in out:
            out.append(token)
    if abs(v) >= 10:
        token = str(int(round(v)))
        if token not in out:
            out.append(token)
    return out


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _collect_snippets(
    pages: List[str],
    keywords: List[str],
    number_tokens: List[str],
    context_chars: int,
    max_snippets: int,
) -> List[dict]:
    snippets: List[dict] = []
    seen = set()

    def add_snippet(page_num: int, trigger: str, text: str, idx: int, base_score: int) -> None:
        start = max(0, idx - context_chars)
        end = min(len(text), idx + context_chars)
        snippet = text[start:end].strip()
        snippet = _normalize_text(snippet)
        if not snippet:
            return
        key = (page_num, snippet[:180])
        if key in seen:
            return
        seen.add(key)
        snippets.append(
            {
                "page": page_num,
                "trigger": trigger,
                "score": base_score,
                "snippet": snippet,
            }
        )

    for page_num, raw_text in enumerate(pages, start=1):
        text = _normalize_text(raw_text)
        if not text:
            continue
        lowered = text.lower()
        for keyword in keywords:
            pos = lowered.find(keyword)
            if pos >= 0:
                add_snippet(page_num, f"keyword:{keyword}", text, pos, 3)
        for token in number_tokens:
            for m in re.finditer(re.escape(token), text):
                add_snippet(page_num, f"number:{token}", text, m.start(), 2)
                break

    snippets.sort(key=lambda row: (-int(row["score"]), int(row["page"])))
    return snippets[:max_snippets]


def _write_markdown(path: Path, rows: List[dict]) -> None:
    lines: List[str] = []
    lines.append("# Far-Miss PDF Triage")
    lines.append("")
    lines.append(f"- Studies triaged: {len(rows)}")
    lines.append("")
    lines.append("| Study | Category | Cochrane | Best Candidate | Rel Gap | PDF Parse |")
    lines.append("|---|---|---:|---:|---:|---|")
    for row in rows:
        best = row.get("best_gap") or {}
        lines.append(
            f"| {row.get('study_id')} | {row.get('category')} | "
            f"{best.get('cochrane_effect', 'n/a')} | {best.get('candidate', 'n/a')} | "
            f"{round(float(best.get('rel_gap')), 4) if best.get('rel_gap') is not None else 'n/a'} | "
            f"{row.get('parse_status', 'n/a')} |"
        )
    lines.append("")

    for row in rows:
        best = row.get("best_gap") or {}
        lines.append(f"## {row.get('study_id')}")
        lines.append("")
        lines.append(f"- Category: {row.get('category')}")
        lines.append(f"- PMCID: {row.get('pmcid')}")
        lines.append(f"- Outcome: {best.get('cochrane_outcome')}")
        lines.append(f"- Cochrane effect: {best.get('cochrane_effect')}")
        lines.append(
            f"- Best extracted candidate: {best.get('candidate')} "
            f"({best.get('extracted_type')}, {best.get('transform')})"
        )
        lines.append(f"- Parse status: {row.get('parse_status')}")
        lines.append("")
        snippets = row.get("snippets") or []
        if not snippets:
            lines.append("No snippets found.")
            lines.append("")
            continue
        for idx, snip in enumerate(snippets, start=1):
            lines.append(f"{idx}. [p{snip.get('page')}] {snip.get('trigger')}")
            lines.append(f"   {snip.get('snippet')}")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostic-json", type=Path, default=Path("output/residual_18_diagnostic.json"))
    parser.add_argument("--eval-jsonl", type=Path, default=Path("gold_data/mega/mega_eval.jsonl"))
    parser.add_argument("--output-json", type=Path, default=Path("output/far_miss_triage.json"))
    parser.add_argument("--output-md", type=Path, default=Path("output/far_miss_triage.md"))
    parser.add_argument("--max-keywords", type=int, default=6)
    parser.add_argument("--max-snippets", type=int, default=8)
    parser.add_argument("--context-chars", type=int, default=220)
    parser.add_argument("--ocr-threshold", type=float, default=100.0)
    args = parser.parse_args()

    diag_rows = _load_diag_rows(args.diagnostic_json)
    far_rows = [row for row in diag_rows if str(row.get("category")) == "far_miss_gt_20pct"]
    if not far_rows:
        print("No far_miss_gt_20pct rows found.")
        return 0

    eval_rows, _, _ = _load_latest_eval_rows(args.eval_jsonl)
    eval_by_key: Dict[str, dict] = {}
    for row in eval_rows:
        sid = row.get("study_id")
        if sid:
            eval_by_key[_canonical_study_key(sid)] = row

    entry_by_key: Dict[str, dict] = {}
    for entry in load_entries_with_pdfs():
        sid = entry.get("study_id")
        if sid:
            entry_by_key[_canonical_study_key(sid)] = entry

    parser_obj = PDFParser(ocr_threshold=float(args.ocr_threshold), output_images=False)
    results: List[dict] = []
    for row in far_rows:
        sid = str(row.get("study_id") or "")
        key = _canonical_study_key(sid)
        eval_row = eval_by_key.get(key, {})
        entry = entry_by_key.get(key, {})
        best = row.get("best_gap") or {}

        out_row = {
            "study_id": sid,
            "pmcid": entry.get("pmcid") or eval_row.get("pmcid"),
            "category": row.get("category"),
            "best_gap": best,
            "pdf_path": entry.get("pdf_path"),
            "parse_status": "not_attempted",
            "parse_elapsed_sec": None,
            "snippets": [],
            "keywords": [],
            "number_tokens": [],
            "top_extracted": (eval_row.get("extracted") or [])[:5],
        }

        pdf_path = entry.get("pdf_path")
        if not pdf_path:
            out_row["parse_status"] = "missing_pdf_path"
            results.append(out_row)
            continue

        started = time.perf_counter()
        try:
            parsed = parser_obj.parse(pdf_path)
            pages = [page.full_text or "" for page in parsed.pages]
            outcome = str(best.get("cochrane_outcome") or "")
            keywords = _extract_keywords(outcome, max_keywords=max(1, int(args.max_keywords)))
            tokens = []
            tokens.extend(_number_tokens(best.get("cochrane_effect")))
            tokens.extend(_number_tokens(best.get("candidate")))
            tokens.extend(_number_tokens(best.get("extracted_raw")))
            unique_tokens = []
            seen_tokens = set()
            for token in tokens:
                if token in seen_tokens:
                    continue
                seen_tokens.add(token)
                unique_tokens.append(token)

            snippets = _collect_snippets(
                pages=pages,
                keywords=keywords,
                number_tokens=unique_tokens,
                context_chars=max(80, int(args.context_chars)),
                max_snippets=max(1, int(args.max_snippets)),
            )
            out_row["keywords"] = keywords
            out_row["number_tokens"] = unique_tokens
            out_row["snippets"] = snippets
            out_row["parse_status"] = "ok"
            out_row["parse_method"] = parsed.extraction_method
            out_row["num_pages"] = parsed.num_pages
        except Exception as exc:  # pragma: no cover - diagnostic script
            out_row["parse_status"] = f"error:{exc}"
        finally:
            out_row["parse_elapsed_sec"] = round(time.perf_counter() - started, 4)

        results.append(out_row)

    report = {
        "far_miss_count": len(results),
        "rows": results,
        "settings": {
            "diagnostic_json": str(args.diagnostic_json),
            "eval_jsonl": str(args.eval_jsonl),
            "max_keywords": args.max_keywords,
            "max_snippets": args.max_snippets,
            "context_chars": args.context_chars,
            "ocr_threshold": args.ocr_threshold,
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_markdown(args.output_md, results)

    print(f"Far-miss studies triaged: {len(results)}")
    print(f"Saved JSON: {args.output_json}")
    print(f"Saved MD: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
