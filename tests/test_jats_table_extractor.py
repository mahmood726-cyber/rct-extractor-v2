#!/usr/bin/env python3
"""JATS/HTML table -> computed continuous MD extraction (recovers continuous
primaries the prose extractor misses because they live only in a results table)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from rct_extractor._engine.core.jats_table_extractor import (
    extract_continuous_effects_from_xml as ext,
)


# Layout A: one "mean (SD)" cell per arm.
TABLE_A = """<article><table-wrap><table>
  <thead><tr><th>Outcome</th><th>Drug</th><th>Placebo</th></tr></thead>
  <tbody>
    <tr><td>Pain score</td><td>45.3 (19.9)</td><td>58.5 (18.6)</td></tr>
    <tr><td>Age (mean)</td><td>63.3 (7.2)</td><td>63.7 (10.1)</td></tr>
  </tbody>
</table></table-wrap></article>"""

# Layout B: separate n | Mean | SD columns per arm.
TABLE_B = """<article><table-wrap><table>
  <thead><tr><th>Outcome</th><th>n</th><th>Mean</th><th>SD</th><th>n</th><th>Mean</th><th>SD</th></tr></thead>
  <tbody>
    <tr><td>OMAS Month 3</td><td>28</td><td>65.54</td><td>20.2</td><td>30</td><td>52.10</td><td>15.7</td></tr>
  </tbody>
</table></table-wrap></article>"""


class TestLayoutA:
    def test_mean_sd_cells_yield_md(self):
        effs = ext(TABLE_A)
        by = {e["endpoint"]: e for e in effs}
        assert "Pain score" in by
        p = by["Pain score"]
        assert p["type"] == "MD"
        assert abs(p["effect_size"] - (45.3 - 58.5)) < 1e-6   # -13.2
        assert p["source"] == "jats_table"
        assert p["arm1_mean"] == 45.3 and p["arm2_sd"] == 18.6


class TestLayoutB:
    def test_n_mean_sd_columns_yield_md_with_n(self):
        effs = ext(TABLE_B)
        assert len(effs) == 1
        e = effs[0]
        assert abs(e["effect_size"] - (65.54 - 52.10)) < 1e-6   # 13.44
        assert e["arm1_n"] == 28 and e["arm2_n"] == 30
        assert e["se_method"] == "table_arm_means"
        # SE = sqrt(20.2^2/28 + 15.7^2/30)
        import math
        assert abs(e["standard_error"] - math.sqrt(20.2**2/28 + 15.7**2/30)) < 1e-3


class TestRobustness:
    def test_empty_and_malformed(self):
        assert ext("") == []
        assert ext("not xml at all") == []
        assert ext("<table><tr><td>only</td><td>text</td></tr></table>") == []

    def test_dedup(self):
        dup = TABLE_A.replace("</tbody>", "<tr><td>Pain score</td><td>45.3 (19.9)</td><td>58.5 (18.6)</td></tr></tbody>")
        effs = ext(dup)
        pain = [e for e in effs if e["endpoint"] == "Pain score"]
        assert len(pain) == 1   # identical arm signature deduped
