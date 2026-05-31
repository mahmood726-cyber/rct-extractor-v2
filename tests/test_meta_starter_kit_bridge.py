"""
Tests for the meta-starter-kit bridge (src/bridges/meta_starter_kit.py).

Confirms the extractor -> meta-starter-kit config conversion produces configs the
kit accepts (schema-valid), for both the 2x2 (malaria binary) and precomputed
effect (cardiology) paths.
"""
import json
import os
import pytest

from src.core.enhanced_extractor_v3 import EnhancedExtractor
from src.bridges.meta_starter_kit import (
    effect_trial, binary_trial, table2x2_to_trial, effect_dict_to_trial,
    make_config, metakit_measure_for, build_config_from_records,
)

_SCHEMA_PATH = "C:/Projects/meta-starter-kit/schema.json"


def _validate(cfg):
    try:
        import jsonschema
    except ImportError:
        # manual minimal check
        assert cfg["effect_measure"] in {"OR", "HR", "RR", "MD", "SMD", "RD"}
        assert len(cfg["trials"]) >= 2
        for t in cfg["trials"]:
            assert "name" in t
            assert all(k in t for k in ("tE", "tN", "cE", "cN")) or \
                   all(k in t for k in ("effect", "ci_low", "ci_high"))
        return
    if os.path.exists(_SCHEMA_PATH):
        jsonschema.validate(cfg, json.load(open(_SCHEMA_PATH)))


def test_measure_mapping():
    assert metakit_measure_for("ARD") == "RD"
    assert metakit_measure_for("HR") == "HR"
    assert metakit_measure_for("IRR") is None   # not in the kit enum


def test_make_config_rejects_bad_measure():
    with pytest.raises(ValueError):
        make_config("t", "IRR", [binary_trial("a", 1, 10, 2, 10),
                                 binary_trial("b", 1, 10, 2, 10)])


def test_make_config_requires_two_trials():
    with pytest.raises(ValueError):
        make_config("t", "RR", [binary_trial("a", 1, 10, 2, 10)])


def test_make_config_drops_counts_for_continuous_measure():
    # counts are meaningless for MD -> dropped, leaving too few -> error
    with pytest.raises(ValueError):
        make_config("t", "MD", [binary_trial("a", 1, 10, 2, 10),
                                binary_trial("b", 1, 10, 2, 10)])


def test_binary_path_schema_valid():
    e = EnhancedExtractor()
    recs = [
        {"name": "A", "pmid": "1", "year": 2019,
         "text": "ACPR was 121/125 (96.8%) in the AL group and 130/148 (87.8%) in the SP group"},
        {"name": "B", "pmid": "2", "year": 2020,
         "text": "ACPR occurred in 100/110 (90.9%) in the AL group versus 90/115 (78.3%) in the SP group"},
    ]
    cfg = build_config_from_records(recs, e, title="AL vs SP ACPR", effect_measure="RR",
                                    endpoint="ACPR", intervention="AL", comparator="SP")
    assert cfg["effect_measure"] == "RR" and len(cfg["trials"]) == 2
    t = cfg["trials"][0]
    assert (t["tE"], t["tN"], t["cE"], t["cN"]) == (121, 125, 130, 148)
    _validate(cfg)


def test_effect_path_schema_valid():
    e = EnhancedExtractor()
    recs = [
        {"name": "FIDELIO", "nct": "NCT02540993", "text": "hazard ratio 0.82 (95% CI 0.73 to 0.93)"},
        {"name": "FIGARO", "nct": "NCT02545049", "text": "HR 0.87 (95% CI 0.76-0.98)"},
    ]
    cfg = build_config_from_records(recs, e, title="Finerenone HR", effect_measure="HR")
    assert len(cfg["trials"]) == 2
    assert abs(cfg["trials"][0]["effect"] - 0.82) < 1e-6
    _validate(cfg)


def test_effect_dict_to_trial_needs_ci():
    assert effect_dict_to_trial({"effect_size": 0.5, "ci_lower": None, "ci_upper": None}, "x") is None
    t = effect_dict_to_trial({"effect_size": 0.5, "ci_lower": 0.3, "ci_upper": 0.8}, "x", pmid="9")
    assert t["effect"] == 0.5 and t["ci_low"] == 0.3 and t["pmid"] == "9"


def test_hiv_2x2_path():
    e = EnhancedExtractor()
    recs = [
        {"name": "T1", "nct": "N1", "text": "viral suppression by 320/350 (91.4%) in the dolutegravir group and 290/345 (84.1%) in the efavirenz group"},
        {"name": "T2", "nct": "N2", "text": "viral suppression in 200/220 (90.9%) on dolutegravir versus 180/215 (83.7%) on efavirenz"},
    ]
    cfg = build_config_from_records(recs, e, title="DTG vs EFV", effect_measure="RR",
                                    endpoint="VIRAL_SUPPRESSION", topics=["hiv"])
    assert len(cfg["trials"]) == 2
    assert (cfg["trials"][0]["tE"], cfg["trials"][0]["tN"]) == (320, 350)
    _validate(cfg)
