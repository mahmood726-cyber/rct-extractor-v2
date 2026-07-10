#!/usr/bin/env python3
"""api.extract now surfaces diagnostic-accuracy measures (Se/Sp/PPV/NPV/LR/DOR/
AUC/...) so diagnostic-test / prediction-model studies -- which report no poolable
HR/OR/RR/MD -- are handled instead of returning a silent empty extraction.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import rct_extractor as rx


DIAG_TEXT = (
    "The model showed sensitivity 0.81 (95% CI 0.75-0.87) and specificity 0.76 "
    "(95% CI 0.70-0.82); AUC 0.83 (95% CI 0.79-0.87)."
)
RCT_TEXT = (
    "The primary outcome was mortality, hazard ratio 0.70 (95% CI 0.55-0.89). "
    "A sensitivity analysis confirmed robustness."
)


class TestDtaExtraction:
    def test_diagnostic_study_populates_diagnostic(self):
        r = rx.extract(DIAG_TEXT, specialty="cardiology")
        types = {d["type"] for d in r.get("diagnostic", [])}
        assert {"Sensitivity", "Specificity", "AUC"}.issubset(types)
        # values + CI carried, normalized to 0-1
        auc = next(d for d in r["diagnostic"] if d["type"] == "AUC")
        assert abs(auc["point_estimate"] - 0.83) < 1e-6
        assert auc["ci_lower"] == 0.79 and auc["ci_upper"] == 0.87

    def test_therapeutic_rct_has_no_false_diagnostic(self):
        # "sensitivity analysis" must NOT produce a Sensitivity measure.
        r = rx.extract(RCT_TEXT, specialty="cardiology")
        assert r["diagnostic"] == []
        assert any(e["type"] == "HR" for e in r["effects"])

    def test_opt_out(self):
        r = rx.extract(DIAG_TEXT, specialty="cardiology", with_diagnostic=False)
        assert "diagnostic" not in r

    def test_key_always_present_when_enabled(self):
        # default on: the key is present (empty list) even for a pure RCT, so a
        # consumer can rely on it existing.
        r = rx.extract(RCT_TEXT, specialty="cardiology")
        assert "diagnostic" in r and isinstance(r["diagnostic"], list)
