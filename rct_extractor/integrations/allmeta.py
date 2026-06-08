"""allmeta bridge -- emit the ``ma-studies-v1`` cross-tool format.

The allmeta apps (https://github.com/mahmood726-cyber/allmeta) are browser-based
and cannot import Python. They exchange data through a localStorage/JSON contract
called ``ma-studies-v1`` (see allmeta ``shared/ma-studies-v1.js``):

    {
      "_schema": "ma-studies-v1",
      "_savedAt": "<ISO 8601>",
      "studies": [
        {"label": str, "est": float, "se": float,
         "moderator": float|null, "group": str|null, "year": float|null}
      ]
    }

``est``/``se`` are on the analysis scale (log scale for ratio measures). This
module turns extractor records into that payload, so the workflow is:

    allmeta Search/Screen  ->  export screened abstracts  ->  rct-extract
        ->  ma-studies-v1 JSON  ->  paste/load into any allmeta MA app.

Use the ``rct-extract-allmeta`` console script, or call :func:`to_ma_studies`.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..api import extract
from ._common import effect_to_est_se, pick_effect, twobytwo_to_est_se


def to_ma_studies(
    records: List[Dict[str, Any]],
    *,
    specialty: str = "auto",
    endpoint: Optional[str] = None,
    measure: str = "OR",
    saved_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build an ``ma-studies-v1`` payload from trial records.

    Args:
        records: ``[{label|name, text, year?, group?, moderator?}]``.
        specialty: forced specialty or ``"auto"``.
        endpoint: restrict to a canonical endpoint when choosing the effect.
        measure: analysis measure (``OR``/``RR`` use raw 2x2 when available;
            any ratio/difference effect with a CI is otherwise converted).
        saved_at: ISO timestamp for ``_savedAt`` (defaults to now, UTC).

    Returns:
        A validated ``ma-studies-v1`` dict ready to hand to an allmeta app.
    """
    studies: List[Dict[str, Any]] = []
    for i, r in enumerate(records):
        text = r.get("text", "")
        label = r.get("label") or r.get("name") or r.get("study") or f"Study {i + 1}"
        if not text:
            continue
        res = extract(text, specialty=specialty)

        est_se = None
        # Prefer raw 2x2 for ratio measures (counts -> exact log-effect + SE).
        if measure.upper() in ("OR", "RR") and res.get("arm_level"):
            tables = res["arm_level"].get("poolable_2x2", [])
            if endpoint:
                tables = [t for t in tables if t.get("endpoint") == endpoint] or tables
            if tables:
                est_se = twobytwo_to_est_se(tables[0], measure)
        # Fall back to a precomputed effect estimate. Enforce the allmeta
        # ma-studies-v1 / Cochrane Sec.10.4 single-family guard: only accept an
        # effect whose type exactly matches the requested measure, so we never
        # serialize a mixed ratio family (HR vs OR vs RR) into the bus.
        if est_se is None:
            e = pick_effect(res.get("effects", []), endpoint=endpoint, measure=measure)
            if e is not None and str(e.get("type", "")).upper() == measure.upper():
                est_se = effect_to_est_se(e)
        if est_se is None:
            continue

        est, se = est_se
        year = r.get("year")
        mod = r.get("moderator")
        studies.append({
            "label": str(label),
            "est": est,
            "se": se,
            "moderator": float(mod) if isinstance(mod, (int, float)) else None,
            "group": str(r["group"]) if r.get("group") else None,
            "year": float(year) if isinstance(year, (int, float)) else None,
        })

    return {
        "_schema": "ma-studies-v1",
        "_savedAt": saved_at or datetime.now(timezone.utc).isoformat(),
        "studies": studies,
    }


def _load_records(path: str) -> List[Dict[str, Any]]:
    """Load records from a .json (list of {label,text}) or a dir of *.txt files."""
    p = Path(path)
    if p.is_dir():
        return [{"label": f.stem, "text": f.read_text(encoding="utf-8")}
                for f in sorted(p.glob("*.txt"))]
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "studies" in data:
        # already a payload; pass through the text-bearing records if present
        return data.get("records", data["studies"])
    return data


def main(argv=None) -> int:
    """``rct-extract-allmeta`` -- records -> ma-studies-v1 JSON."""
    ap = argparse.ArgumentParser(
        prog="rct-extract-allmeta",
        description="Convert abstracts to allmeta ma-studies-v1 JSON for the browser MA apps.",
    )
    ap.add_argument("input", help="JSON file [{label,text,year?}] or a dir of *.txt files")
    ap.add_argument("-o", "--output", help="write the ma-studies-v1 JSON here (default stdout)")
    ap.add_argument("-s", "--specialty", default="auto", help="force a specialty (default: auto)")
    ap.add_argument("-m", "--measure", default="OR", help="analysis measure (default: OR)")
    ap.add_argument("--endpoint", default=None, help="restrict to a canonical endpoint")
    ap.add_argument("--saved-at", default=None, help="ISO timestamp for _savedAt")
    args = ap.parse_args(argv)

    records = _load_records(args.input)
    payload = to_ma_studies(
        records, specialty=args.specialty, endpoint=args.endpoint,
        measure=args.measure, saved_at=args.saved_at,
    )
    text = json.dumps(payload, indent=2)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"wrote {len(payload['studies'])} studies to {args.output}")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
