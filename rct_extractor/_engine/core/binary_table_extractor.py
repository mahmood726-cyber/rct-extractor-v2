"""Header-aware binary 2x2 extractor for JATS tables — THE CRACK, behind a gate.

WHY: malaria/TB report binary outcomes as `5 (50.0)` under an arm column whose
header declares the denominator ("Placebo (N=10)"). Our pipeline looks for literal
`n/N` and returns zero on this shape. Measured on 60 malaria/TB OA papers:
55% carry >=2 `n (%)` cells vs 13% carrying `n/N` (route0b_shapes.jsonl).

METHODS-CONTRACT §15 — a join/extractor that silently mismatches FABRICATES data
with full confidence and is worse than nothing. v1 of this file did exactly that:
  * PMC4353311 -> emitted arm="k statistic" (a diagnostic-agreement table, no arms)
  * PMC4580123 -> emitted 9/27 (32.1%): 9/27 is 33.3%, so N was wrong (true N=28)
Both are recorded here because the failure is the reason for the gates below.

PRECISION DESIGN (each gate exists because v1 broke without it):
  G1 percentage-as-checksum, TIGHT: events/N must reproduce the printed pct to
     within rounding (<=0.55pp for 1dp, <=1.05pp for integer pct). v1 used a 5%
     relative tolerance and accepted a wrong denominator.
  G2 arm columns must be arm-like: a declared N in the header, and NOT a statistics
     column (p, CI, RR, OR, k statistic, "crude results", ...). v1 had no such test.
  G3 the table must be an OUTCOME table: >=2 arm-like columns; baseline/demographic
     captions excluded.
  G4 N is never invented. Header N first; pct-inferred N only when it lands on a
     near-integer AND is consistent across >=2 cells of the same column; such cells
     are flagged mode='inferred_N_from_pct' (lower confidence) so downstream can filter.
  G5 every cell carries provenance: pmcid, table label, row label, column header.

This module EXTRACTS ONLY. It does not select the primary outcome — that is the
known selection residual (~0.67 joint ceiling) and is out of scope.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

N_PCT = re.compile(r"^\s*(\d{1,5})\s*\(\s*(\d{1,3}(?:\.\d+)?)\s*%?\s*\)\s*$")
N_OVER_N = re.compile(r"^\s*(\d{1,5})\s*/\s*(\d{1,5})\s*(?:\(\s*(\d{1,3}(?:\.\d+)?)\s*%?\s*\))?\s*$")
HDR_N = re.compile(r"(?:\bN\s*[=:]\s*|\(\s*n\s*[=:]\s*)(\d{1,6})", re.I)

# G2: columns that are statistics, not arms
NOT_AN_ARM = re.compile(
    r"\b(p[-\s]?value|\bp\b|95\s*%|\bci\b|confidence|risk ratio|\brr\b|odds|\bor\b|"
    r"hazard|\bhr\b|kappa|k statistic|crude|adjusted|difference|total\b|overall|"
    r"statistic|estimate|sensitivity|specificity|ppv|npv|auc|mean|median|sd\b|iqr)", re.I)

# G3: not outcome tables
BASELINE_CAP = re.compile(
    r"\b(baseline|demographic|characteristic|enrol?ment criteria|inclusion|exclusion|"
    r"laboratory reference|schedule|composition|reagent|primer|sequence|"
    r"subgroup analys|univariate|multivariate|regression)\b", re.I)

# G9 (hand-check): PMC10960763 is a case-control study; "Cases N=495 / Controls N=1473"
# are not trial arms. Extracting them as arms yields a confidently wrong 2x2.
CASE_CONTROL = re.compile(r"\b(case[s]?\b.{0,12}\bcontrol|controls?\s*\(?\s*n\s*=)", re.I)

# G9b: demographic ROW labels that are never outcomes (PMC12890141 emitted "Male").
BASELINE_ROW = re.compile(r"^\s*(male|female|men|women|age|sex|gender|race|ethnicity|"
                          r"weight|height|bmi|smok\w*|education|employed)\b", re.I)


@dataclass
class Cell:
    outcome: str
    arm: str
    events: int
    total: int
    pct_printed: Optional[float]
    mode: str                    # header_N | inferred_N_from_pct | explicit_n_over_N
    confidence: str              # high | medium
    pmcid: str = ""
    table_label: str = ""
    checks: List[str] = field(default_factory=list)


def _txt(x: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip()


def _rows(table_xml: str) -> List[List[str]]:
    """Rows with @colspan EXPANDED so column indices line up across rows.

    G8 (hand-check finding): without this, header and body drift out of alignment and
    the arm label attaches to the wrong column. PMC10533414 had a 3-cell header and
    4-cell body rows (header omits the stub); we emitted Tafenoquine's 6/50 as
    "Primaquine plus DP". The registry CORROBORATED that pair, because the numbers were
    real — just from the wrong arm. A swapped arm inverts the effect direction, which is
    precisely the §15 "worse than no join" failure.
    """
    out = []
    for tr in re.findall(r"<tr\b.*?</tr>", table_xml, re.S):
        cells: List[str] = []
        for c in re.findall(r"<(?:td|th)\b[^>]*>.*?</(?:td|th)>", tr, re.S):
            m = re.match(r"<(?:td|th)\b([^>]*)>", c)
            attrs = m.group(1) if m else ""
            sp = re.search(r"colspan\s*=\s*[\"']?(\d{1,2})", attrs, re.I)
            n = max(1, min(int(sp.group(1)), 30)) if sp else 1
            cells.extend([_txt(c)] * n)
        if cells:
            out.append(cells)
    return out


def _align(rows: List[List[str]]) -> List[List[str]]:
    """G8: if the header row is exactly one cell short of the body, it omits the stub
    column — prepend one so header index j means the same column as body index j."""
    if len(rows) < 2:
        return rows
    body = max((len(r) for r in rows[1:]), default=0)
    fixed = list(rows)
    for i in range(min(2, len(fixed))):
        if len(fixed[i]) == body - 1:
            fixed[i] = [""] + fixed[i]
    return fixed


def _caption(table_xml: str) -> str:
    m = re.search(r"<caption\b.*?</caption>", table_xml, re.S)
    lab = re.search(r"<label\b.*?</label>", table_xml, re.S)
    parts = [_txt(x.group(0)) for x in (lab, m) if x]
    return " ".join(parts).strip()


def _pct_ok(events: int, total: int, pct: float) -> Tuple[bool, float]:
    """G1: tight checksum. 1dp printed -> +-0.55pp; integer printed -> +-1.05pp."""
    if total <= 0 or events > total:
        return False, -1.0
    calc = 100.0 * events / total
    one_dp = ("." in f"{pct}") and not f"{pct}".endswith(".0")
    tol = 0.55 if one_dp else 1.05
    return abs(calc - pct) <= tol, calc


def _n_header_rows(rows: List[List[str]]) -> int:
    """How many leading rows are header rows?

    D3: a header can span several rows — a GROUP row (colspan) above an ARM row.
    A row is part of the header while it declares no data-shaped cells and the row
    below still looks header-ish. We stop at the first row whose non-stub cells are
    data (n (%) / n/N), which is the first body row.
    """
    last = 0
    for i, r in enumerate(rows[:4]):
        data_cells = sum(1 for c in r[1:] if N_PCT.match(c or "") or N_OVER_N.match(c or ""))
        if data_cells:
            break
        last = i
    return last


def _header_arms(rows: List[List[str]]) -> Tuple[int, Dict[int, Tuple[str, Optional[int]]]]:
    """Compose a column -> (arm label, N) map across ALL header rows.

    D3 FIX. The defect: a GROUP row spans columns via @colspan and the ARM row beneath
    carries the labels and the Ns, so the arm identity of column j is the PAIR
    (group_row[j], arm_row[j]) — NEITHER ROW ALONE IDENTIFIES THE ARM. Picking a single
    header row attaches the wrong label and produced 37.5% arm-assignment precision:
      * PMC7985421  — Part 1 | Part 2 spanning arm sub-columns
      * PMC7044511  — arm label on one row, N on another
      * PMC10958962 — subgroup columns (>=65 y) beneath an arm group
    Measured prevalence: 80/154 tables (52%) across 45 malaria/TB papers, PLOS 43/80.

    Shape-agnostic on purpose: never keys on <th>, because PLOS writes header rows as
    <thead><tr><td> — the bug that zeroed 39/40 tables in F:\\allmeta\\oa68k\\jats.py
    (D1; fixed and regression-tested there).
    """
    hi = _n_header_rows(rows)
    hdr_rows = rows[:hi + 1]
    width = max((len(r) for r in hdr_rows), default=0)
    arms: Dict[int, Tuple[str, Optional[int]]] = {}
    for j in range(1, width):
        parts, n = [], None
        for r in hdr_rows:
            if j >= len(r):
                continue
            cell = (r[j] or "").strip()
            if not cell or cell in parts:      # colspan repeats the group label
                continue
            parts.append(cell)
            m = HDR_N.search(cell)
            if m and n is None:
                n = int(m.group(1))            # N may live on ANY header row (PMC7044511)
        label = " / ".join(parts)
        if not label or NOT_AN_ARM.search(label):   # G2
            continue
        arms[j] = (label, n)
    return hi, arms


def extract_2x2(table_xml: str, pmcid: str = "") -> List[Cell]:
    cap = _caption(table_xml)
    if BASELINE_CAP.search(cap):               # G3
        return []
    rows = _align(_rows(table_xml))
    if len(rows) < 3:
        return []
    if CASE_CONTROL.search(cap) or CASE_CONTROL.search(" ".join(rows[0])):   # G9
        return []
    hi, arms = _header_arms(rows)
    # G8: if header and body still disagree on width, column->arm mapping is unsafe.
    body_w = max((len(r) for r in rows[hi + 1:]), default=0)
    if body_w and len(rows[hi]) != body_w:
        return []
    named_n = {j: v for j, v in arms.items() if v[1]}
    if len(named_n) < 2:                       # G3: not an arm-structured outcome table
        return []

    # G6: a column's header N is only TRUSTED once a NON-ZERO cell in that column
    # has reproduced its printed percentage. Hand-check found `0 (0)` cells make the
    # checksum vacuous — 0/2, 0/39 and 0/1000 all print 0% — so a zero cell can
    # certify any denominator. PMC8516506 was emitted as 0/2 on exactly that hole.
    verified_cols = set()
    for r in rows[hi + 1:]:
        for j, c in enumerate(r):
            if j not in named_n:
                continue
            m1 = N_PCT.match(c)
            if not m1:
                continue
            e, pct = int(m1.group(1)), float(m1.group(2))
            if e > 0 and pct > 0 and _pct_ok(e, named_n[j][1], pct)[0]:
                verified_cols.add(j)

    out: List[Cell] = []
    seen: set = set()
    for r in rows[hi + 1:]:
        if len(r) < 2:
            continue
        label = r[0]
        if not label or N_PCT.match(label) or N_OVER_N.match(label) or NOT_AN_ARM.fullmatch(label or ""):
            continue
        if BASELINE_ROW.match(label):          # G9b
            continue
        for j, c in enumerate(r):
            if j not in named_n:
                continue
            arm_label, arm_n = named_n[j]
            m2 = N_OVER_N.match(c)
            if m2:
                e, n = int(m2.group(1)), int(m2.group(2))
                p = float(m2.group(3)) if m2.group(3) else None
                if e > n or n <= 0:
                    continue
                if p is not None:
                    ok, calc = _pct_ok(e, n, p)
                    if not ok:                 # G1
                        continue
                key = (label, arm_label, e, n)
                if key in seen:                # G7: dedup (PMC13266303 emitted twice)
                    continue
                seen.add(key)
                out.append(Cell(label, arm_label, e, n, p, "explicit_n_over_N", "high",
                                pmcid, cap[:80], ["self-contained n/N"]))
                continue
            m1 = N_PCT.match(c)
            if not m1:
                continue
            e, pct = int(m1.group(1)), float(m1.group(2))
            ok, calc = _pct_ok(e, arm_n, pct)
            if not ok:
                # G4: header N failed the checksum -> do NOT emit a guessed N.
                # (v1 emitted 9/27 for a printed 32.1%; the real denominator was 28.)
                continue
            if e == 0 and j not in verified_cols:
                continue                       # G6: vacuous checksum, N unverified
            key = (label, arm_label, e, arm_n)
            if key in seen:                    # G7
                continue
            seen.add(key)
            conf = "high" if (e > 0 or j in verified_cols) else "medium"
            out.append(Cell(label, arm_label, e, arm_n, pct, "header_N", conf,
                            pmcid, cap[:80], [f"pct {calc:.1f}=={pct}"]))
    return out


def extract_from_fulltext(xml: str, pmcid: str = "") -> List[Cell]:
    cells: List[Cell] = []
    for t in re.findall(r"<table-wrap\b.*?</table-wrap>", xml, re.S):
        cells.extend(extract_2x2(t, pmcid))
    return cells


def to_dicts(cells: List[Cell]) -> List[dict]:
    return [asdict(c) for c in cells]


# --- ADDED ON PORT INTO rct-extractor-v2, 2026-07-16 -------------------------
# Everything above this line is byte-identical to the module as it stood in the
# untracked oa-reachability scratch directory (sha256 d239691392c011dc). Only the
# adapter below is new, so the gates above stay auditable against their origin.
#
# WHY THE PORT: api.py routed `tables_xml` to the CONTINUOUS reader only, so a
# canonical malaria primary in a results table ("147/150 (98.0%)" vs "131/148
# (88.5%)") returned ZERO effects -- while this reader, which recovers all four
# cells from that same table, sat unwired in a directory that was not even under
# version control. The gap was never a decision: the continuous reader was built
# 2026-07-11 as "the #1 recall lever" when no binary reader existed anywhere, and
# this one was written later, elsewhere. Two parsers that never met.

def extract_arm_proportions_from_xml(xml: str, pmcid: str = "") -> List[Dict]:
    """JATS/HTML tables -> arm-level proportion dicts.

    Shaped like ``malaria_arm_data.extract_proportions()`` output so table-derived
    2x2 cells merge into ``arm_level["proportions"]`` beside the prose-derived ones.

    SCOPE: extraction only. This deliberately does NOT pair arms into 2x2 tables or
    pick a primary outcome -- that is the known selection residual (~0.67 joint
    ceiling), and inventing a pairing here would launder a selection choice as an
    extraction result. Consumers pair explicitly.
    """
    out: List[Dict] = []
    for c in extract_from_fulltext(xml, pmcid):
        computed = round(100.0 * c.events / c.total, 2) if c.total else None
        out.append({
            "events": c.events,
            "total": c.total,
            "pct": c.pct_printed if c.pct_printed is not None else computed,
            "computed_pct": computed,
            # Every cell here already passed the G1 printed-percentage checksum (or
            # carried a self-contained n/N), which is what makes it non-fabricating.
            "pct_consistent": True,
            "endpoint": c.outcome,
            "arm": c.arm,
            "pcr_status": None,
            "analysis_population": None,
            "source": "jats_table_2x2",
            "n_source": c.mode,          # header_N | inferred_N_from_pct | explicit_n_over_N
            "confidence": c.confidence,
            "table_label": c.table_label,
            "pmcid": c.pmcid,
            "checks": list(c.checks),
            "source_text": f"{c.table_label} :: {c.outcome} | {c.arm}: {c.events}/{c.total}"[:120],
            "needs_review": c.confidence != "high",
        })
    return out
