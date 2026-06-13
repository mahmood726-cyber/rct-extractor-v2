"""
Validate the DTA derivation engine against the DTA70 gold set.

DTA70 is a real R package (mahmood789/DTA70): 76 diagnostic-accuracy datasets,
6,348 study rows, each with a complete TP/FP/FN/TN 2x2 table. We use it two ways:

  1. DERIVATION CHECK (the maths): for every gold row, confirm the engine's
     TwoByTwo derivation reproduces sensitivity / specificity / DOR computed
     independently from the raw counts. This validates the exact arithmetic the
     extractor relies on, over 6,348 real tables, to 1e-9.

  2. ROUND-TRIP EXTRACTION (structural): synthesise a plain-language 2x2 sentence
     from a sample of gold rows and confirm the count extractor recovers the
     exact cells. This is a regression check on the count regex against realistic
     count magnitudes -- NOT an external-text accuracy claim (the text is
     synthesised here), which is what the EuropePMC real-PDF harness measures.

If the gold file is absent (DTA70 not on this machine), the tests skip with a
clear reason rather than fabricating a result.
"""
import json
from pathlib import Path

import pytest

from dta_extractor._engine import counts
from dta_extractor._engine.models import TwoByTwo

GOLD = Path(__file__).resolve().parents[1] / "dta_extractor" / "validation" / "gold" / "dta70_2x2.json"


def _load():
    if not GOLD.exists():
        pytest.skip(
            f"DTA70 gold file not present at {GOLD}. Build it with: "
            f"python -m dta_extractor.validation.dta70_to_gold"
        )
    with open(GOLD, encoding="utf-8") as fh:
        return json.load(fh)


def test_gold_file_shape():
    data = _load()
    assert data["n_rows"] == len(data["records"]) > 1000
    assert data["n_datasets"] >= 70
    for r in data["records"][:5]:
        assert all(k in r for k in ("TP", "FP", "FN", "TN", "dataset"))


def test_derivation_matches_independent_arithmetic_all_rows():
    """Engine-derived Se/Sp/DOR == independently computed values, every row."""
    data = _load()
    checked = 0
    for r in data["records"]:
        tp, fp, fn, tn = r["TP"], r["FP"], r["FN"], r["TN"]
        t2 = TwoByTwo(tp=tp, fp=fp, fn=fn, tn=tn)
        # independent reference arithmetic
        nd, nh = tp + fn, fp + tn
        if nd > 0:
            assert t2.sensitivity == pytest.approx(tp / nd, abs=1e-9)
        if nh > 0:
            assert t2.specificity == pytest.approx(tn / nh, abs=1e-9)
        if fp * fn > 0:
            assert t2.dor == pytest.approx((tp * tn) / (fp * fn), abs=1e-6, rel=1e-9)
        checked += 1
    assert checked == data["n_rows"]


def test_roundtrip_extraction_on_synthesised_sentences():
    """Count extractor recovers exact cells from synthesised 2x2 prose."""
    data = _load()
    # sample deterministically (every 53rd row) so the test is fast & stable
    rows = data["records"][::53]
    assert len(rows) > 50
    recovered = 0
    for r in rows:
        tp, fp, fn, tn = r["TP"], r["FP"], r["FN"], r["TN"]
        # a 2x2 needs both arms populated to be a valid extractable table
        if (tp + fn) == 0 or (fp + tn) == 0:
            continue
        sentence = (
            f"In the {r['dataset']} study there were {tp} true positives, "
            f"{fp} false positives, {fn} false negatives and {tn} true negatives."
        )
        tabs = counts.extract_two_by_two(sentence)
        assert len(tabs) >= 1, sentence
        t = tabs[0]
        assert (t.tp, t.fp, t.fn, t.tn) == (tp, fp, fn, tn), sentence
        recovered += 1
    # the synthesised form is one the extractor explicitly supports -> 100%
    assert recovered > 50
