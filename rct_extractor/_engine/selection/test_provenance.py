"""Tests for provenance — the source-stratum tag + abstract counts-only discipline."""
try:
    from provenance import tag, is_count, is_effect_with_ci, disagreement, STRATA
except ImportError:
    from .provenance import tag, is_count, is_effect_with_ci, disagreement, STRATA

def test_count_and_effect_detection():
    assert is_count({"events": 7, "total": 98})
    assert not is_count({"events": 100, "total": 98})     # events>total
    assert is_effect_with_ci({"value": 0.72, "ci_lower": 0.6, "ci_upper": 0.88})

def test_abstract_count_accepted():
    r = tag({"events": 7, "total": 98}, "abstract", "virally suppressed 7/98")
    assert r["provenance"]["verifiable"] and not r["provenance"]["flagged"]
    assert r["provenance"]["confidence"] > 0

def test_abstract_prose_direction_flagged_fail_closed():
    # a bare interpretive claim with no number -> flagged, confidence 0
    r = tag({"value": None}, "abstract", "the drug was well tolerated and highly effective")
    assert r["provenance"]["flagged"] and r["provenance"]["confidence"] == 0.0

def test_abstract_count_beside_spin_keeps_number_flags_context():
    r = tag({"events": 40, "total": 50}, "abstract", "highly effective: 40/50 responded")
    assert r["provenance"]["verifiable"] and not r["provenance"]["flagged"]
    assert r["provenance"]["spin_risk"] is True   # context flagged, number kept

def test_registry_is_high_confidence_not_spin_gated():
    r = tag({"param_value": 0.86, "ci_lower_limit": 0.75, "ci_upper_limit": 0.97}, "registry")
    assert r["provenance"]["confidence"] >= 0.95 and not r["provenance"]["flagged"]

def test_disagreement_registered_vs_published():
    agree, rd = disagreement({"value": 0.72}, {"value": 0.72})
    assert agree and rd == 0.0
    agree2, rd2 = disagreement({"value": 0.72}, {"value": 0.95})
    assert agree2 is False and rd2 > 0.10

def test_unknown_stratum_rejected():
    try:
        tag({"events": 1, "total": 2}, "twitter"); assert False
    except ValueError:
        pass

if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try: fn(); p += 1; print(f"  PASS {fn.__name__}")
        except AssertionError as e: print(f"  FAIL {fn.__name__}: {e}")
    print(f"{p}/{len(fns)} passed"); sys.exit(0 if p == len(fns) else 1)
