#!/usr/bin/env python3
"""Internal-consistency diagnostic over a batch of real abstracts.

Runs the (now all-specialty) consistency screen on every record's source text
and reports, in aggregate: how many extracted effects are flagged / repaired /
need review, a breakdown by flag code, and — where a gold value is available —
whether the consistency flags line up with genuine extraction errors (extracted
effect vs gold point estimate).

This is the "run it on a real batch" diagnostic: it quantifies the data-quality
picture now that the screen actually runs, and surfaces concrete bad extractions
to fix. Sources are limited to PubMed-abstract / CT.gov / AACT text, per the
project constraint.

Usage:
    python scripts/consistency_audit.py [path/to/records.jsonl] [--report out.md]

The default batch is data/validation_dataset.jsonl (156 curated abstracts);
point it at a fresh PubMed/CT.gov pull to audit uncurated extractions.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rct_extractor.api import extract  # noqa: E402


def _gold(rec: dict):
    g = rec.get("gold_standard") or {}
    return g.get("point_estimate"), g.get("ci_lower"), g.get("ci_upper")


def audit(records: list[dict]) -> dict:
    total_records = 0
    total_effects = 0
    checkable = 0
    flagged = 0
    repaired = 0
    needs_review = 0
    hard = 0
    flag_codes = Counter()
    # gold cross-check
    gold_records = 0
    gold_matched = 0       # extractor point within 10% of gold
    gold_missed = 0        # extractor point off by >10% from gold
    flag_on_miss = 0       # of the gold-misses, how many the screen flagged
    examples = []          # a few flagged extractions to eyeball
    miss_examples = []     # gold-misses (the actionable extraction errors)

    for rec in records:
        text = rec.get("source_text") or rec.get("text")
        if not text:
            continue
        total_records += 1
        try:
            out = extract(text)
        except Exception as exc:  # never let one bad record kill the audit
            examples.append({"id": rec.get("id"), "error": repr(exc)[:120]})
            continue
        effects = out.get("effects") or []
        total_effects += len(effects)

        gpt, glo, ghi = _gold(rec)
        primary = effects[0] if effects else None

        for e in effects:
            c = e.get("consistency") or {}
            if c.get("checkable"):
                checkable += 1
            fl = c.get("flags") or []
            if fl:
                flagged += 1
                flag_codes.update(fl)
                if len(examples) < 12:
                    examples.append({"id": rec.get("id"), "trial": rec.get("trial_name"),
                                     "type": e.get("type"), "es": e.get("effect_size"),
                                     "ci": [e.get("ci_lower"), e.get("ci_upper")],
                                     "flags": fl, "score": c.get("score")})
            if c.get("repair") == "swapped_ci_bounds":
                repaired += 1
            if e.get("needs_review"):
                needs_review += 1
            if c.get("checkable") and c.get("score") == 0.0:
                hard += 1

        # gold cross-check on the primary effect
        if gpt is not None and primary and primary.get("effect_size") is not None:
            gold_records += 1
            try:
                rel = abs(primary["effect_size"] - gpt) / (abs(gpt) or 1.0)
            except TypeError:
                rel = 1.0
            if rel <= 0.10:
                gold_matched += 1
            else:
                gold_missed += 1
                flags = (primary.get("consistency") or {}).get("flags") or []
                if flags:
                    flag_on_miss += 1
                miss_examples.append({
                    "trial": rec.get("trial_name"),
                    "gold": gpt, "gold_type": rec.get("effect_type"),
                    "extracted": primary.get("effect_size"), "extracted_type": primary.get("type"),
                    "flags": flags,
                    "text": (text or "")[:140].replace("\n", " "),
                })

    return {
        "total_records": total_records,
        "total_effects": total_effects,
        "checkable": checkable,
        "flagged": flagged,
        "flagged_pct": round(100 * flagged / total_effects, 1) if total_effects else 0.0,
        "repaired": repaired,
        "needs_review": needs_review,
        "hard_failures": hard,
        "flag_codes": dict(flag_codes.most_common()),
        "gold_records": gold_records,
        "gold_matched": gold_matched,
        "gold_missed": gold_missed,
        "flag_on_miss": flag_on_miss,
        "examples": examples,
        "miss_examples": miss_examples,
    }


def to_markdown(stats: dict, batch_name: str) -> str:
    L = []
    L.append(f"# Internal-consistency audit — `{batch_name}`\n")
    L.append("Run of the all-specialty consistency screen over a real abstract batch.\n")
    L.append("## Coverage\n")
    L.append(f"- Records processed: **{stats['total_records']}**")
    L.append(f"- Effects extracted: **{stats['total_effects']}** (checkable: {stats['checkable']})")
    L.append(f"- Flagged: **{stats['flagged']}** ({stats['flagged_pct']}%) · "
             f"repaired (reversed-CI): {stats['repaired']} · needs-review: {stats['needs_review']} · "
             f"hard failures: {stats['hard_failures']}\n")
    L.append("## Flags by code\n")
    if stats["flag_codes"]:
        for code, n in stats["flag_codes"].items():
            L.append(f"- `{code}`: {n}")
    else:
        L.append("- (none — every extraction was internally consistent)")
    L.append("\n## Gold cross-check (primary effect vs gold point estimate)\n")
    gr = stats["gold_records"]
    if gr:
        acc = round(100 * stats["gold_matched"] / gr, 1)
        L.append(f"- Gold-comparable records: **{gr}**")
        L.append(f"- Extracted within 10% of gold: **{stats['gold_matched']}** ({acc}%)")
        L.append(f"- Extracted off by >10%: **{stats['gold_missed']}** "
                 f"(of which the consistency screen flagged {stats['flag_on_miss']})")
        if stats["gold_missed"] and not stats["flag_on_miss"]:
            L.append("\n> **Finding:** internal consistency ≠ correctness. The gold-misses below are "
                     "each *internally consistent* (point inside its CI, etc.) but grab the wrong "
                     "estimand / comparison / unit — so the consistency screen cannot catch them. "
                     "These need source-grounding + multi-candidate-disambiguation checks (next increment).")
        L.append("\n### Gold-miss extractions (the actionable errors)\n")
        for m in stats["miss_examples"][:20]:
            L.append(f"- **{m['trial']}**: gold {m['gold_type']} `{m['gold']}` → extracted "
                     f"{m['extracted_type']} `{m['extracted']}` · flags={m['flags']}")
            L.append(f"  - _{m['text']}_")
    else:
        L.append("- (no gold point estimates in this batch)")
    L.append("\n## Sample flagged / errored extractions\n")
    for ex in stats["examples"][:12]:
        L.append(f"- {json.dumps(ex, ensure_ascii=False)}")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch", nargs="?", default=str(ROOT / "data" / "validation_dataset.jsonl"))
    ap.add_argument("--report", default=str(ROOT / "output" / "consistency_audit.md"))
    args = ap.parse_args()

    path = Path(args.batch)
    records = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    stats = audit(records)
    md = to_markdown(stats, path.name)

    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")

    # concise console summary
    print(f"records={stats['total_records']} effects={stats['total_effects']} "
          f"flagged={stats['flagged']} ({stats['flagged_pct']}%) repaired={stats['repaired']} "
          f"needs_review={stats['needs_review']} hard={stats['hard_failures']}")
    print("flag_codes:", stats["flag_codes"] or "(none)")
    if stats["gold_records"]:
        print(f"gold: {stats['gold_matched']}/{stats['gold_records']} within 10% "
              f"({round(100*stats['gold_matched']/stats['gold_records'],1)}%), "
              f"missed={stats['gold_missed']} (flagged {stats['flag_on_miss']})")
    print("report ->", out)


if __name__ == "__main__":
    main()
