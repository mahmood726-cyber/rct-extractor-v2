"""Structured continuous-outcome extraction from JATS / HTML result tables.

The prose effect extractor (enhanced_extractor_v3) works on flattened text, so it
misses continuous primaries reported ONLY as arm-level ``mean (SD)`` in a results
table -- the single largest real-corpus recall gap (confirmed on the efetch/EPMC
selection eval: Durand/Keene/Papay-class studies). This module parses the actual
``<table>`` STRUCTURE and computes the mean difference from the arm cells.

Two common Cochrane continuous layouts are handled:

  A. one cell per arm holding ``mean (SD)``:
        | Outcome | 63.3 (7.2) | 63.7 (10.1) |
  B. separate ``n | Mean | SD`` columns per arm:
        | Outcome | 29 | 31.38 | 17.97 | 30 | 21.50 | 15.71 |

For each 2-arm data row it emits a computed MD effect:
    MD = mean1 - mean2,  SE = sqrt(sd1^2/n1 + sd2^2/n2)  (or the SD-only pooled
    form when per-arm N is unavailable), 95% CI = MD +- 1.96*SE.

The output dicts are shaped like the effect dicts from ``to_dict`` (``type``,
``effect_size``, ``ci_lower``, ``ci_upper``, ``endpoint``, ``source_text``) plus
``source='jats_table'`` and the raw arm data, so they can be merged into the
candidate pool and ordered/selected like any other effect.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

try:
    import xml.etree.ElementTree as ET
except Exception:  # pragma: no cover
    ET = None  # type: ignore

_MEAN_SD_CELL = re.compile(r'^\s*(-?\d+\.?\d*)\s*[\(（]\s*(-?\d+\.?\d*)\s*[\)）]')
_NUM = re.compile(r'-?\d+\.?\d*')
# a "±" form: "63.3 ± 7.2"
_MEAN_PM_SD = re.compile(r'^\s*(-?\d+\.?\d*)\s*(?:±|\+/-|\+-)\s*(-?\d+\.?\d*)')
_LABEL_HAS_TEXT = re.compile(r'[A-Za-z]')


def _strip_tag(tag: str) -> str:
    return tag.rsplit('}', 1)[-1].lower()


def _iter_tables(root) -> List[Any]:
    return [el for el in root.iter() if _strip_tag(el.tag) == 'table']


def _row_cells(tr) -> List[str]:
    cells = []
    for c in tr:
        if _strip_tag(c.tag) in ('td', 'th'):
            cells.append(re.sub(r'\s+', ' ', ''.join(c.itertext())).strip())
    return cells


def _grid(table) -> List[List[str]]:
    rows = [el for el in table.iter() if _strip_tag(el.tag) == 'tr']
    return [_row_cells(r) for r in rows]


def _parse_mean_sd(cell: str) -> Optional[Tuple[float, float]]:
    m = _MEAN_SD_CELL.match(cell) or _MEAN_PM_SD.match(cell)
    if not m:
        return None
    try:
        return float(m.group(1)), float(m.group(2))
    except ValueError:
        return None


def _md_effect(mean1: float, sd1: float, mean2: float, sd2: float,
               n1: Optional[float], n2: Optional[float], label: str) -> Optional[Dict[str, Any]]:
    if sd1 <= 0 or sd2 <= 0:
        return None
    md = mean1 - mean2
    if n1 and n2 and n1 > 0 and n2 > 0:
        se = math.sqrt(sd1 * sd1 / n1 + sd2 * sd2 / n2)
    else:
        # No per-arm N: fall back to the equal-n-agnostic pooled-SD scale (SE not
        # identifiable without N -> report MD with a coarse SE from the SDs). Flagged.
        se = math.sqrt((sd1 * sd1 + sd2 * sd2) / 2.0)
    if not math.isfinite(se) or se <= 0:
        return None
    return {
        "type": "MD",
        "effect_size": round(md, 4),
        "ci_lower": round(md - 1.96 * se, 4),
        "ci_upper": round(md + 1.96 * se, 4),
        "p_value": None,
        "standard_error": round(se, 6),
        "se_method": "table_arm_means" if (n1 and n2) else "table_arm_means_no_n",
        "endpoint": label[:120],
        "source_text": f"{label[:60]}: {mean1} ({sd1}) vs {mean2} ({sd2})",
        "source": "jats_table",
        "arm1_mean": mean1, "arm1_sd": sd1, "arm1_n": n1,
        "arm2_mean": mean2, "arm2_sd": sd2, "arm2_n": n2,
        "needs_review": True,
    }


def _row_label(cells: List[str]) -> str:
    for c in cells:
        if _LABEL_HAS_TEXT.search(c) and not _parse_mean_sd(c):
            return c
    return ""


def _from_row_mean_sd_cells(cells: List[str]) -> Optional[Dict[str, Any]]:
    """Layout A: two or more 'mean (SD)' cells in the row."""
    pairs = [_parse_mean_sd(c) for c in cells]
    pairs = [p for p in pairs if p]
    if len(pairs) < 2:
        return None
    (m1, s1), (m2, s2) = pairs[0], pairs[1]
    return _md_effect(m1, s1, m2, s2, None, None, _row_label(cells))


def _from_row_ncolumns(cells: List[str]) -> Optional[Dict[str, Any]]:
    """Layout B: a label then numeric run(s) of (n, mean, sd) per arm, or (mean, sd)."""
    # collect the trailing numeric run
    nums: List[float] = []
    for c in cells:
        if _LABEL_HAS_TEXT.search(c):
            nums.append(math.nan)          # a text/label cell breaks the numeric run
            continue
        toks = _NUM.findall(c)
        if len(toks) == 1:
            try:
                nums.append(float(toks[0]))
            except ValueError:
                nums.append(math.nan)
        else:
            # a cell with 0 or >1 numbers breaks the clean numeric run
            nums.append(math.nan)
    # keep only the contiguous trailing finite run
    run: List[float] = []
    for v in reversed(nums):
        if math.isfinite(v):
            run.append(v)
        else:
            break
    run.reverse()
    if len(run) == 6:      # n1 m1 s1 n2 m2 s2
        n1, m1, s1, n2, m2, s2 = run
        return _md_effect(m1, s1, m2, s2, n1, n2, _row_label(cells))
    if len(run) == 4:      # m1 s1 m2 s2
        m1, s1, m2, s2 = run
        return _md_effect(m1, s1, m2, s2, None, None, _row_label(cells))
    return None


def extract_continuous_effects_from_xml(raw: str) -> List[Dict[str, Any]]:
    """Parse JATS/HTML tables in ``raw`` and return computed MD effects.

    Robust to malformed markup (falls back to no tables). Deduplicates on the
    (mean1, sd1, mean2, sd2) signature.
    """
    if not raw or ET is None:
        return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        # tolerate a document fragment / stray entities by wrapping
        try:
            root = ET.fromstring("<root>" + raw + "</root>")
        except ET.ParseError:
            return []
    out: List[Dict[str, Any]] = []
    seen = set()
    for table in _iter_tables(root):
        for cells in _grid(table):
            if len(cells) < 3:
                continue
            eff = _from_row_mean_sd_cells(cells) or _from_row_ncolumns(cells)
            if not eff:
                continue
            key = (eff["arm1_mean"], eff["arm1_sd"], eff["arm2_mean"], eff["arm2_sd"])
            if key in seen:
                continue
            seen.add(key)
            out.append(eff)
    return out
