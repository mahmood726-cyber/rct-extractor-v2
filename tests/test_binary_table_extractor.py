"""THE PARSE-DEFECT LIBRARY — one named defect, one real example, one permanent test.

Mahmood, 2026-07-16: "just map the parsing defects one by one. It is doable."

The thesis is his detector thesis applied to parsing: once a parse defect has
happened once, it becomes a permanent template that catches its recurrence. The
library grows monotonically and never forgets. It is DOABLE because the set is
BOUNDED — publisher table conventions are finite (PLOS, BMC, OUP, Elsevier,
Springer, ASM + a few JATS idioms each), not an open research problem.

Every fixture below is REDUCED FROM A REAL DOCUMENT — the PMCID is named in each
test. No hypothetical shapes: a defect earns an entry by having occurred.

Rule (learned the hard way today at 37.5% arm precision): a fix for one venue must
not break another. Every fix re-runs the WHOLE suite.

Run: python -m pytest tests/test_binary_table_extractor.py -q

PORTED 2026-07-16 from oa-reachability/tests/test_parse_defects.py, unchanged except
for the import path. The module under test lived UNTRACKED in a scratch directory
beside the production extractor that could not read binary tables; porting it into
this repo puts it under version control and under the production test suite.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rct_extractor._engine.core.binary_table_extractor import extract_2x2


def _wrap(rows_xml: str, caption: str = "Table 2 Adverse events") -> str:
    return (f"<table-wrap><label>Table 2</label><caption><title>{caption}</title>"
            f"</caption><table>{rows_xml}</table></table-wrap>")


# ---------------------------------------------------------------- D2 (FIXED)
def test_D2_header_omits_stub_column_off_by_one():
    """D2 — header row omits the stub cell; body rows include it. PMC10533414 (Lancet ID).

    Header had 3 cells, body rows 4 -> column j meant different things in each, so
    Tafenoquine's 6/50 was emitted as "Primaquine plus DP". The registry CORROBORATED
    that pair (the numbers were real) — only the arm was wrong. A swapped arm inverts
    the effect. This is the §15 "worse than no join" failure, live.
    """
    x = _wrap(
        "<thead><tr><td>DP alone (n=50)</td><td>Tafenoquine plus DP (n=50)</td>"
        "<td>Primaquine plus DP (n=50)</td></tr></thead>"
        "<tbody>"
        "<tr><td>Electrocardiogram QT</td><td>4 (8%)</td><td>6 (12%)</td><td>2 (4%)</td></tr>"
        "<tr><td>Headache</td><td>2 (4%)</td><td>2 (4%)</td><td>3 (6%)</td></tr>"
        "</tbody>")
    cells = extract_2x2(x, "PMC10533414")
    got = {(c.arm, c.events) for c in cells if c.outcome.startswith("Electro")}
    assert ("DP alone (n=50)", 4) in got
    assert ("Tafenoquine plus DP (n=50)", 6) in got, "D2: arm shifted by the stub column"
    assert ("Primaquine plus DP (n=50)", 2) in got


# ---------------------------------------------------------------- D4 (FIXED)
def test_D4_statistics_column_is_not_an_arm():
    """D4 — a stats column read as a trial arm. PMC4353311.

    v1 emitted arm="k statistic" and arm="Crude results" from a diagnostic-agreement
    table that has no arms at all.
    """
    x = _wrap(
        "<thead><tr><td>Group</td><td>Vaccine (n=100)</td><td>k statistic (n=100)</td>"
        "</tr></thead>"
        "<tbody><tr><td>Cured</td><td>40 (40)</td><td>55 (55)</td></tr>"
        "<tr><td>Failed</td><td>10 (10)</td><td>20 (20)</td></tr></tbody>")
    cells = extract_2x2(x, "PMC4353311")
    assert not any("statistic" in c.arm.lower() for c in cells), "D4: stats column as arm"


# ---------------------------------------------------------------- D5 (FIXED)
def test_D5_wrong_denominator_must_fail_the_checksum():
    """D5 — loose tolerance accepted a wrong N. PMC4580123.

    v1 emitted 9/27 for a printed 32.1%. 9/27 = 33.3%; the true denominator was 28.
    The printed percentage is a CHECKSUM and must be enforced tightly.
    """
    x = _wrap(
        "<thead><tr><td>Event</td><td>Arm A (N = 27)</td><td>Arm B (N = 27)</td></tr></thead>"
        "<tbody><tr><td>DILI</td><td>9 (32.1)</td><td>10 (37.0)</td></tr></tbody>")
    cells = extract_2x2(x, "PMC4580123")
    bad = [c for c in cells if c.events == 9 and c.total == 27]
    assert not bad, "D5: 9/27 is 33.3%, not the printed 32.1% -> must be dropped"


# ---------------------------------------------------------------- D6 (FIXED)
def test_D6_zero_cell_cannot_certify_a_denominator():
    """D6 — `0 (0)` makes the checksum vacuous. PMC8516506.

    0/2, 0/39 and 0/1000 all print 0%, so a zero cell certifies ANY denominator.
    A column's N is only trusted once a NON-ZERO cell has checksummed against it.
    """
    x = _wrap(
        "<thead><tr><td>Outcome</td><td>Arm A (n = 2)</td><td>Arm B (n = 2)</td></tr></thead>"
        "<tbody><tr><td>Low birth weight</td><td>0 (0)</td><td>0 (0)</td></tr></tbody>")
    cells = extract_2x2(x, "PMC8516506")
    assert not cells, "D6: no non-zero cell ever verified N -> nothing may be emitted"


# ---------------------------------------------------------------- D7 (FIXED)
def test_D7_case_control_groups_are_not_trial_arms():
    """D7 — "Cases N=495 / Controls N=1473" read as arms. PMC10960763 (case-control)."""
    x = _wrap(
        "<thead><tr><td>Category</td><td>Cases N = 495</td><td>Controls N = 1473</td>"
        "</tr></thead>"
        "<tbody><tr><td>50 to &lt;400</td><td>234 (47.3)</td><td>720 (48.9)</td></tr></tbody>",
        caption="Table 3 Cases and controls by category")
    assert not extract_2x2(x, "PMC10960763"), "D7: case-control groups are not arms"


# ---------------------------------------------------------------- D8 (FIXED)
def test_D8_baseline_row_is_not_an_outcome():
    """D8 — demographic row emitted as an outcome. PMC12890141 emitted "Male"."""
    x = _wrap(
        "<thead><tr><td>Variable</td><td>1HP (N = 249)</td><td>3HP (N = 251)</td></tr></thead>"
        "<tbody><tr><td>Male</td><td>82 (32.9%)</td><td>111 (44.2%)</td></tr>"
        "<tr><td>Discontinued treatment</td><td>18 (7.2%)</td><td>11 (4.4%)</td></tr></tbody>")
    cells = extract_2x2(x, "PMC12890141")
    assert not any(c.outcome.lower().startswith("male") for c in cells), "D8: baseline row"
    assert any(c.outcome.startswith("Discontinued") for c in cells), "D8 overreach: real outcome lost"


# ---------------------------------------------------------------- D9 (FIXED)
def test_D9_no_duplicate_emission():
    """D9 — same cell emitted twice. PMC13266303 emitted "Mild" twice."""
    x = _wrap(
        "<thead><tr><td>Severity</td><td>Dose 1 (n=108)</td><td>Dose 2 (n=101)</td></tr></thead>"
        "<tbody><tr><td>Mild</td><td>3 (2.8)</td><td>10 (9.9)</td></tr></tbody>")
    cells = extract_2x2(x, "PMC13266303")
    keys = [(c.outcome, c.arm, c.events, c.total) for c in cells]
    assert len(keys) == len(set(keys)), "D9: duplicate cells"


# ------------------------------------------------------- D3 (LIVE — MUST FAIL)
def test_D3_multirow_nested_header_arm_assignment():
    """D3 — MULTI-ROW NESTED HEADER. PMC7985421, PMC7044511, PMC10958962. **LIVE DEFECT.**

    Precise pattern (not just "nesting"): a GROUP row spans several columns via
    @colspan, and the ARM row beneath it carries the labels and the Ns. The arm
    identity of column j is the PAIR (group_row[j], arm_row[j]) — neither row alone
    identifies the arm. Our single-header-row model picks one row and attaches the
    wrong label. This is the direct cause of 37.5% arm-assignment precision.

    FIXED 2026-07-16 by composing ALL header rows into a column->arm map.

    ⚠️ Assertion corrected when the fix landed, and the correction is the point: the
    original assertion expected the BARE label "TTP399 (n = 9)". That contradicted
    D3's own definition — if neither row alone identifies the arm, then the arm
    identity IS the pair. The bare label cannot distinguish Part 1's TTP399 (n=9)
    from Part 2's TTP399 (n=40); the composed label can, and that disambiguation is
    exactly what the defect destroys. This is not tuning-to-pass (§2): the fix was
    not touched, the assertion that misstated the defect was.
    """
    x = _wrap(
        "<thead>"
        "<tr><td></td><td colspan='2'>Part 1</td><td colspan='2'>Part 2</td></tr>"
        "<tr><td>Event</td><td>TTP399 (n = 9)</td><td>Placebo (n = 56)</td>"
        "<td>TTP399 (n = 40)</td><td>Placebo (n = 20)</td></tr>"
        "</thead>"
        "<tbody><tr><td>Hypoglycaemia</td><td>6 (66.7)</td><td>1 (1.8)</td>"
        "<td>4 (10.0)</td><td>2 (10.0)</td></tr></tbody>")
    cells = extract_2x2(x, "PMC7985421")
    got = {(c.arm, c.events) for c in cells}
    # the two same-named TTP399 arms must be distinguishable and carry the right N
    assert ("Part 1 / TTP399 (n = 9)", 6) in got, f"D3: nested header -> wrong arm: {got}"
    assert ("Part 2 / TTP399 (n = 40)", 4) in got, f"D3: group row lost: {got}"
    assert ("Part 1 / Placebo (n = 56)", 1) in got
    by_arm = {c.arm: c.total for c in cells}
    assert by_arm["Part 1 / TTP399 (n = 9)"] == 9, "D3: N taken from the wrong group"
    assert by_arm["Part 2 / TTP399 (n = 40)"] == 40


# --- ADDED ON PORT: the WIRING gate -----------------------------------------
# Every test above exercises extract_2x2 directly. That is exactly how this reader
# came to be fully working, fully tested, and NOT CALLED BY ANYTHING: its tests
# passed in a scratch directory while production routed table XML to a reader that
# could not read binary at all. A test that drives only the function it fixes cannot
# see that. These drive rct_extractor.api.extract -- the production entrypoint.

from rct_extractor.api import extract  # noqa: E402

# The canonical malaria primary the cross-vendor attack showed api.py returning 0 for:
# PCR-adjusted ACPR day 28, DHA-PPQ 147/150 (98.0%) vs AL 131/148 (88.5%).
MALARIA_TABLE = """<article><table-wrap><label>Table 2</label>
<caption><p>Efficacy outcomes at day 28</p></caption><table>
 <thead><tr><th>Outcome</th><th>DHA-PPQ (N=150)</th><th>AL (N=148)</th></tr></thead>
 <tbody>
  <tr><td>PCR-adjusted ACPR day 28</td><td>147/150 (98.0)</td><td>131/148 (88.5)</td></tr>
  <tr><td>Treatment failure</td><td>3 (2.0)</td><td>17 (11.5)</td></tr>
 </tbody></table></table-wrap></article>"""
MALARIA_TEXT = "Children with uncomplicated falciparum malaria were randomised to DHA-PPQ or AL."


def _table_props(res):
    props = (res.get("arm_level") or {}).get("proportions") or []
    return [p for p in props if p.get("source") == "jats_table_2x2"]


def test_production_extract_recovers_the_binary_table():
    """THE WIRING GATE. Before this, production returned 0 effects for this table."""
    cells = _table_props(extract(MALARIA_TEXT, tables_xml=MALARIA_TABLE))
    assert len(cells) == 4, f"production recovered {len(cells)}/4 cells"
    got = {(c["endpoint"], c["events"], c["total"]) for c in cells}
    assert ("PCR-adjusted ACPR day 28", 147, 150) in got
    assert ("PCR-adjusted ACPR day 28", 131, 148) in got
    assert ("Treatment failure", 3, 150) in got      # N read from the column header
    assert ("Treatment failure", 17, 148) in got


def test_production_rescue_route_now_fires_on_arms():
    """rung7 counts a rescue when >=2 arm proportions carry events AND total. That
    route got 0/98 rescues because binary tables never reached it."""
    props = (extract(MALARIA_TEXT, tables_xml=MALARIA_TABLE).get("arm_level") or {}).get("proportions") or []
    good = len([z for z in props if z.get("events") is not None and z.get("total")])
    assert good >= 2


def test_production_without_tables_recovers_nothing_from_tables():
    """Control: the recovery is attributable to the table route, not the prose."""
    assert _table_props(extract(MALARIA_TEXT)) == []


def test_production_wiring_mutation_goes_red(monkeypatch):
    """Mutation-test the CALLER: unwire the reader and production must lose the cells.
    If this passes, api.py is no longer calling the reader."""
    from rct_extractor._engine.core import binary_table_extractor as B
    monkeypatch.setattr(B, "extract_from_fulltext", lambda xml, pmcid="": [])
    assert _table_props(extract(MALARIA_TEXT, tables_xml=MALARIA_TABLE)) == [], \
        "MUTATION DID NOT BITE -- production is not calling the binary reader"


def test_production_does_not_fabricate_from_a_baseline_table():
    """The gates must survive the port: a baseline table yields no outcome cells."""
    baseline = MALARIA_TABLE.replace("Efficacy outcomes at day 28",
                                     "Baseline characteristics of enrolled participants")
    assert _table_props(extract(MALARIA_TEXT, tables_xml=baseline)) == []


def test_production_refuses_a_wrong_denominator():
    """G1 end-to-end: a printed pct that the header N cannot reproduce is dropped,
    rather than emitted as a confident wrong cell."""
    bad = MALARIA_TABLE.replace("<td>3 (2.0)</td>", "<td>9 (32.1)</td>")   # 9/150 = 6.0%, not 32.1%
    cells = _table_props(extract(MALARIA_TEXT, tables_xml=bad))
    assert not any(c["events"] == 9 for c in cells)
