"""Tests for effect_family — the ratio/difference confusion fix (AACT + tropical PDF)."""
try:
    from effect_family import normalize_param_type, classify_from_text
except ImportError:
    from .effect_family import normalize_param_type, classify_from_text

def test_param_type_ratio_vs_difference():
    assert normalize_param_type("Rate Ratio") == "ratio"
    assert normalize_param_type("Risk Difference (RD)") == "difference"
    assert normalize_param_type("Hazard Ratio (HR)") == "ratio"
    assert normalize_param_type("LS Mean Difference") == "difference"      # difference beats "mean"
    assert normalize_param_type("Difference in response rates") == "difference"
    assert normalize_param_type("Geometric Mean Ratio") == "ratio"

def test_param_type_families():
    assert normalize_param_type("Cox Proportional Hazard") == "ratio"
    assert normalize_param_type("Standardized Mean Difference") == "standardized"
    assert normalize_param_type("Slope") == "slope"
    assert normalize_param_type("Vaccine efficacy") == "ratio"             # VE = 1-RR
    assert normalize_param_type("LS Means") == "single_arm"                # not an effect
    assert normalize_param_type("Percentage of Participants") == "proportion"

def test_prose_fixes_the_malaria_type_errors():
    # both were mislabeled in the malaria adjudication set (31/33 -> 33/33 after this)
    assert classify_from_text("aRR, 0.99 [95% CI, 0.77-1.28]", "ARD")[0] == "ratio"
    assert classify_from_text("61% (95% CI, 52 to 70)", "MD")[0] == "proportion"

def test_prose_tb_rate_difference_and_hr():
    assert classify_from_text("incidence-rate difference -0.0231 per 100 py", "RD")[0] == "difference"
    assert classify_from_text("hazard ratio, 0.86; 95% CI, 0.75 to 0.97", "HR")[0] == "ratio"
    # a ratio token beats a nearby difference word
    assert classify_from_text("adjusted risk ratio for the difference in events, 0.72")[0] == "ratio"

def test_never_mix_scales_contract():
    # the whole point: ratio and difference are distinct families a pool must not mix
    assert normalize_param_type("Odds Ratio (OR)") != normalize_param_type("Risk Difference (RD)")

if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try: fn(); p += 1; print(f"  PASS {fn.__name__}")
        except AssertionError as e: print(f"  FAIL {fn.__name__}: {e}")
    print(f"{p}/{len(fns)} passed"); sys.exit(0 if p == len(fns) else 1)
