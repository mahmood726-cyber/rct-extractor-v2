"""Beast bridge -- emit Beast ``Trial``-shaped records.

Beast (https://github.com/mahmood726-cyber/Beast) is a meta-analysis
trend-tracker. Its universal unit is ``beast.effects.Trial``, which carries one
of three data shapes:

* binary 2x2:  ``e_events, e_n, c_events, c_n``
* continuous:  ``e_mean, e_sd, e_n, c_mean, c_sd, c_n``
* generic:     ``yi, sei`` (effect size + SE, already on the analysis scale)

This adapter turns extractor records into Trial-shaped **dicts** (it deliberately
does not import ``beast``, so it has no dependency on Beast being installed).
Beast can register a source that calls :func:`to_beast_trials` and feeds the
dicts straight into ``Trial(**d)``.

Preference: a poolable 2x2 (raw counts) when available -- which lets Beast apply
its own conditional continuity correction and cumulative-over-time logic --
otherwise a generic ``(yi, sei)`` from a precomputed effect + CI.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from ..api import extract
from ._common import Z975, pick_effect

_RATIO_TYPES = {"OR", "RR", "HR", "IRR", "GMR", "RRR"}


def _generic_from_effect(effect: Dict) -> Optional[Dict[str, float]]:
    """Return ``{yi, sei}`` (analysis scale) for a precomputed effect, or None."""
    eff = effect.get("effect_size")
    lo = effect.get("ci_lower")
    hi = effect.get("ci_upper")
    if eff is None or lo is None or hi is None:
        return None
    etype = str(effect.get("type", "")).upper()
    try:
        if etype in _RATIO_TYPES:
            if eff <= 0 or lo <= 0 or hi <= 0:
                return None
            yi = math.log(float(eff))
            sei = (math.log(float(hi)) - math.log(float(lo))) / (2 * Z975)
        else:
            yi = float(eff)
            sei = (float(hi) - float(lo)) / (2 * Z975)
    except (ValueError, ZeroDivisionError):
        return None
    if not (math.isfinite(yi) and math.isfinite(sei) and sei > 0):
        return None
    return {"yi": yi, "sei": sei}


def to_beast_trials(
    records: List[Dict[str, Any]],
    *,
    specialty: str = "auto",
    endpoint: Optional[str] = None,
    measure: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Convert trial records to Beast ``Trial``-shaped dicts.

    Args:
        records: ``[{study|name|label, text, year?}]``.
        specialty: forced specialty or ``"auto"``.
        endpoint: restrict the chosen effect/table to a canonical endpoint.
        measure: preferred analysis measure when picking a precomputed effect.

    Returns:
        ``[{study, year, ...}]`` dicts; each has either binary count fields or
        ``yi``/``sei``. Records that yield no poolable data are skipped.
    """
    out: List[Dict[str, Any]] = []
    for i, r in enumerate(records):
        text = r.get("text", "")
        study = r.get("study") or r.get("name") or r.get("label") or f"Study {i + 1}"
        if not text:
            continue
        year = r.get("year")
        year = int(year) if isinstance(year, (int, float)) else None
        res = extract(text, specialty=specialty)

        trial: Optional[Dict[str, Any]] = None
        # Prefer raw 2x2 counts.
        if res.get("arm_level"):
            tables = res["arm_level"].get("poolable_2x2", [])
            if endpoint:
                tables = [t for t in tables if t.get("endpoint") == endpoint] or tables
            if tables:
                t = tables[0]
                trial = {
                    "study": str(study), "year": year,
                    "e_events": t["arm1"]["events"], "e_n": t["arm1"]["total"],
                    "c_events": t["arm2"]["events"], "c_n": t["arm2"]["total"],
                }
        # Fall back to a generic (yi, sei) from a precomputed effect.
        if trial is None:
            e = pick_effect(res.get("effects", []), endpoint=endpoint, measure=measure)
            gi = _generic_from_effect(e) if e is not None else None
            if gi is not None:
                trial = {"study": str(study), "year": year, **gi}
        if trial is not None:
            out.append(trial)
    return out


# Reference implementation Beast can drop into beast/sources/rct_extractor.py.
# Kept as a string so this module has zero dependency on `beast` being present.
BEAST_SOURCE_TEMPLATE = '''\
"""rct_extractor source -- pull trial effects per topic via the extractor engine.

Requires: pip install "git+https://github.com/mahmood726-cyber/rct-extractor-v2.git"
"""
from __future__ import annotations
from typing import Optional

from beast.effects import Trial
from beast.sources.base import Source, TopicSpec, register_source


@register_source
class RctExtractorSource(Source):
    """Run the rct-extractor on a corpus of abstracts and emit Trials.

    TopicSpec.params:
      corpus:    path to a JSON list [{study, text, year?}] or a dir of *.txt
      specialty: one of the 17 disease specialties, or "auto" (default)
      endpoint:  optional canonical endpoint to restrict to
    """
    name = "rct_extractor"

    def fetch(self, topic: TopicSpec, as_of_year: Optional[int] = None) -> list[Trial]:
        import json
        from pathlib import Path
        from rct_extractor.integrations.beast import to_beast_trials

        corpus = topic.params["corpus"]
        p = Path(corpus)
        if p.is_dir():
            records = [{"study": f.stem, "text": f.read_text(encoding="utf-8")}
                       for f in sorted(p.glob("*.txt"))]
        else:
            records = json.loads(p.read_text(encoding="utf-8"))

        dicts = to_beast_trials(
            records,
            specialty=topic.params.get("specialty", "auto"),
            endpoint=topic.params.get("endpoint"),
            measure=topic.measure,
        )
        trials = [Trial(**d) for d in dicts]
        if as_of_year is not None:
            trials = [t for t in trials if t.year is None or t.year <= as_of_year]
        if not trials:
            raise ValueError(f"no poolable trials extracted for topic {topic.id!r}")
        return trials
'''
