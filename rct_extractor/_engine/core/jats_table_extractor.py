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
# D13: the arm N declared in the COLUMN HEADER -- "Drug (N=150)", "Placebo (n = 148)".
_HDR_N = re.compile(r'(?:\bN\s*[=:]\s*|\(\s*n\s*[=:]\s*)(\d{1,6})', re.I)


def _strip_tag(tag: str) -> str:
    return tag.rsplit('}', 1)[-1].lower()


def _iter_tables(root) -> List[Any]:
    return [el for el in root.iter() if _strip_tag(el.tag) == 'table']


def _row_cells(tr) -> List[str]:
    """Cells with @colspan EXPANDED so column index j means the same column on every row.

    D13: the arm N lives in a header cell that typically spans the arm's sub-columns
    ("Drug (N=150)" over ``n | Mean | SD``). Without expanding colspan, header index j
    and body index j address different columns and the N is attached to the wrong arm.
    A swapped arm N does not merely lose precision -- it computes a confident SE from
    the other arm's denominator, which is the "worse than no join" failure.
    """
    cells: List[str] = []
    for c in tr:
        if _strip_tag(c.tag) not in ('td', 'th'):
            continue
        txt = re.sub(r'\s+', ' ', ''.join(c.itertext())).strip()
        try:
            span = int(c.get('colspan') or 1)
        except (TypeError, ValueError):
            span = 1
        cells.extend([txt] * max(1, min(span, 30)))
    return cells


def _grid(table) -> List[List[str]]:
    rows = [el for el in table.iter() if _strip_tag(el.tag) == 'tr']
    grid = [_row_cells(r) for r in rows]
    return _align(grid)


def _align(grid: List[List[str]]) -> List[List[str]]:
    """If a header row is exactly one cell short of the body it omits the stub column;
    prepend one so header index j addresses the same column as body index j."""
    if len(grid) < 2:
        return grid
    body = max((len(r) for r in grid[1:]), default=0)
    out = list(grid)
    for i in range(min(2, len(out))):
        if len(out[i]) == body - 1:
            out[i] = [""] + out[i]
    return out


def _n_header_rows(grid: List[List[str]]) -> int:
    """How many leading rows are header rows? Stop at the first row carrying data cells."""
    last = 0
    for i, r in enumerate(grid[:4]):
        if any(_parse_mean_sd(c) for c in r[1:]):
            break
        last = i
    return last


def _header_ns(grid: List[List[str]]) -> Dict[int, float]:
    """D13 FIX: column index -> the arm N DECLARED IN THE HEADER.

    Before this, ``_from_row_mean_sd_cells`` passed n1/n2=None unconditionally and the
    per-arm-N branch in ``_md_effect`` was dead code on real data: every table-derived
    effect fell through to the ``no_n`` pooled-SD fallback (measured 159/159 on the
    cached OA corpus). That fallback inflates the SE ~8.6x on a standard table, costing
    ~74x pooled weight and silently turning a significant effect non-significant.

    Only reads an N that the header states explicitly. Never infers one.
    """
    if not grid:
        return {}
    hdr = grid[:_n_header_rows(grid) + 1]
    width = max((len(r) for r in hdr), default=0)
    ns: Dict[int, float] = {}
    for j in range(width):
        for r in hdr:
            if j >= len(r):
                continue
            m = _HDR_N.search(r[j] or "")
            if not m:
                continue
            try:
                v = float(m.group(1))
            except ValueError:
                break
            if v >= 2:          # an arm of n<2 has no estimable SE; treat as undeclared
                ns[j] = v
            break
    return ns


def _parse_mean_sd(cell: str) -> Optional[Tuple[float, float]]:
    m = _MEAN_SD_CELL.match(cell) or _MEAN_PM_SD.match(cell)
    if not m:
        return None
    try:
        return float(m.group(1)), float(m.group(2))
    except ValueError:
        return None


def _md_effect(mean1: float, sd1: float, mean2: float, sd2: float,
               n1: Optional[float], n2: Optional[float], label: str,
               n_source: str = "row") -> Optional[Dict[str, Any]]:
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
        # Provenance, not existence. A downstream gate of the form "standard_error is
        # not None" is satisfied BY the no_n fallback -- i.e. by the defect. Consumers
        # must gate on HOW the SE was derived, so the derivation is stated here:
        #   table_arm_means            -- per-arm N stated in the data row (best)
        #   table_arm_means_header_n   -- per-arm N read from the column header (D13)
        #   table_arm_means_no_n       -- NO per-arm N; SE is a coarse SD-only proxy,
        #                                 ~8.6x inflated on a standard table. NOT poolable.
        "se_method": (("table_arm_means_header_n" if n_source == "header" else "table_arm_means")
                      if (n1 and n2) else "table_arm_means_no_n"),
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


def _from_row_mean_sd_cells(cells: List[str],
                            header_ns: Optional[Dict[int, float]] = None) -> Optional[Dict[str, Any]]:
    """Layout A: two or more 'mean (SD)' cells in the row.

    D13: each arm's N is looked up by the COLUMN the cell sits in, so arm1 gets arm1's
    declared N. Columns with no declared N still fall back to the coarse no_n SE.
    """
    pairs = [(j, _parse_mean_sd(c)) for j, c in enumerate(cells)]
    pairs = [(j, p) for j, p in pairs if p]
    if len(pairs) < 2:
        return None
    (j1, (m1, s1)), (j2, (m2, s2)) = pairs[0], pairs[1]
    hn = header_ns or {}
    return _md_effect(m1, s1, m2, s2, hn.get(j1), hn.get(j2), _row_label(cells),
                      n_source="header")


def _from_row_ncolumns(cells: List[str],
                       header_ns: Optional[Dict[int, float]] = None) -> Optional[Dict[str, Any]]:
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
    base = len(nums) - len(run)          # column index of run[0]
    if len(run) == 6:      # n1 m1 s1 n2 m2 s2 -- the row states its own Ns
        n1, m1, s1, n2, m2, s2 = run
        return _md_effect(m1, s1, m2, s2, n1, n2, _row_label(cells))
    if len(run) == 4:      # m1 s1 m2 s2 -- D13: fall back to the header-declared N
        m1, s1, m2, s2 = run
        hn = header_ns or {}
        return _md_effect(m1, s1, m2, s2, hn.get(base), hn.get(base + 2), _row_label(cells),
                          n_source="header")
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
        grid = _grid(table)
        header_ns = _header_ns(grid)     # D13: read the arm N the header declares
        for cells in grid:
            if len(cells) < 3:
                continue
            eff = (_from_row_mean_sd_cells(cells, header_ns)
                   or _from_row_ncolumns(cells, header_ns))
            if not eff:
                continue
            key = (eff["arm1_mean"], eff["arm1_sd"], eff["arm2_mean"], eff["arm2_sd"])
            if key in seen:
                continue
            seen.add(key)
            out.append(eff)
    return out
