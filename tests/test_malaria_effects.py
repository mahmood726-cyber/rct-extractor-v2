"""
Tests for the malaria effect-estimate augmenter (src/specialties/malaria_effects.py).

Locks in: efficacy-percentage extraction, bracketed/colon adjusted ratios,
flexible CI punctuation (paren/bracket labels, leading-dot numbers, "to"/comma
separators, Lancet middle dot), dedup against core, and precision on
non-numeric method sentences.
"""
import pytest
from src.specialties.malaria_effects import augment_malaria_effects as aug


@pytest.mark.parametrize("text,etype,val,lo,hi", [
    # Protective / vaccine efficacy percentages (the core has no concept of these)
    ("protective efficacy 42.7%, 95% CI 22.5-57.7; p=0.0003", "EFFICACY_PCT", 42.7, 22.5, 57.7),
    ("vaccine efficacy (VE) was 56% (95% CI 51-60)", "EFFICACY_PCT", 56.0, 51.0, 60.0),
    ("protective efficacy was 42·7%, 95% CI 22·5-57·7", "EFFICACY_PCT", 42.7, 22.5, 57.7),  # middle dot
    # Bracketed / colon / equals adjusted ratios
    ("adjusted odds ratio [aOR]: 0.50; 95%CI: 0.34-0.75", "OR", 0.50, 0.34, 0.75),
    ("adjusted risk ratio [aRR] = 0.78, 95% confidence interval [CI] 0.45-1.35", "RR", 0.78, 0.45, 1.35),
    ("adjusted incidence rate ratio (aIRR) = 1.23, 95% CI = 1.01, 1.50", "IRR", 1.23, 1.01, 1.50),
    ("aHR: 0.838 (95% CI [0.716, 0.981]; p=0.028)", "HR", 0.838, 0.716, 0.981),
    ("model-adjusted odds ratio (aOR) of 0.46 [95% confidence interval (CI): 0.25-0.83]", "OR", 0.46, 0.25, 0.83),
    # IRR comma form, "to" separator, leading-dot numbers
    ("incidence rate ratio, 0.67; 95% CI, 0.50-0.90; P=0.008", "IRR", 0.67, 0.50, 0.90),
    ("incidence rate ratio, 0.34; 95% CI, 0.23 to 0.51", "IRR", 0.34, 0.23, 0.51),
    ("incidence rate ratio, 0.74; 95% CI, .58-.95", "IRR", 0.74, 0.58, 0.95),
    # Mean difference with negatives + paren CI label
    ("mean difference (MD): -7.63; 95% confidence interval (CI): -11.06, -4.21", "MD", -7.63, -11.06, -4.21),
    # Bare uppercase abbreviation with '=' and comma-separated CI (+ nbsp)
    ("reduced malaria (OR = 0.45, 95% CI: 0.36, 0.56, P<0.01)", "OR", 0.45, 0.36, 0.56),
    ("OR = 0.82, 95 % CI: 0.69, 0.97", "OR", 0.82, 0.69, 0.97),
    ("HR = 0.67 (95% CI 0.50-0.90)", "HR", 0.67, 0.50, 0.90),
    # Linking phrase between measure and value (found mining published typhoid MAs):
    # "<measure> for <subgroup> was/were <value>", incl. zero MD, spelled-out CI,
    # and plural ("risks, were") + Lancet middle dot.
    ("mean difference for diarrhoea was 0 days (95% CI -0.54 to 0.54)", "MD", 0.0, -0.54, 0.54),
    ("weighted mean difference for length of illness was -0.07 days, "
     "95% confidence interval -0.55 to 0.40", "MD", -0.07, -0.55, 0.40),
    ("relative risks, were 1·05 (95% CI 1·04-1·07; I2 97%)", "RR", 1.05, 1.04, 1.07),
    # Bare abbreviation with an "of" / "for <subgroup> of" linking phrase
    # (hepatitis MA misses; strict-superset extension of _BARE_RATIO_RE)
    ("pooled OR of 1.02 (95% CI 0.86-1.20)", "OR", 1.02, 0.86, 1.20),
    ("the pooled HR for OS of 1.04 (95%CI: 0.93-1.16)", "HR", 1.04, 0.93, 1.16),
])
def test_augmenter_recovers(text, etype, val, lo, hi):
    r = aug(text)
    assert len(r) >= 1, f"expected an extraction from: {text}"
    hit = next((x for x in r if x["type"] == etype), None)
    assert hit is not None, f"expected type {etype} in {[x['type'] for x in r]}"
    assert abs(hit["effect_size"] - val) < 1e-6
    assert abs(hit["ci_lower"] - lo) < 1e-6
    assert abs(hit["ci_upper"] - hi) < 1e-6


@pytest.mark.parametrize("text", [
    "protective efficacy is not optimum against severe disease",
    "vaccine efficacy varies by route of inoculation",
    "odds ratios were calculated with logistic regression",
    "Relative risks for binomial outcomes and mean differences for continuous outcomes were calculated",
    "the rate of malaria was 0.5 per person year",
    "expressing the data as a risk ratio",
    # lowercase conjunction "or" must never be read as an odds ratio
    "treated with artemether or 0.45 mg/kg primaquine (95% CI 0.36, 0.56)",
    # the "of" linker must not fire without a ratio abbreviation in front
    "we saw an improvement of 12 points (95% CI 10-14) over baseline",
    # a bare abbreviation with NO trailing 95% CI must not match (respiratory rate)
    "respiratory rate (RR, 18 breaths per minute) was recorded at baseline",
])
def test_augmenter_rejects_non_numeric(text):
    assert aug(text) == [], f"false positive on: {text}"


def test_dedup_against_core():
    text = "incidence rate ratio, 0.67; 95% CI, 0.50-0.90"
    # A core extraction already covering this span WITH a CI -> augmenter skips it
    existing = [{"char_start": 0, "char_end": len(text),
                 "ci_lower": 0.50, "ci_upper": 0.90}]
    assert aug(text, existing) == []


def test_augmenter_supplies_ci_when_core_lacks_it():
    # if core got the value but NO CI, the augmenter still emits its CI-bearing copy
    text = "incidence rate ratio, 0.67; 95% CI, 0.50-0.90"
    existing = [{"char_start": 0, "char_end": len(text),
                 "ci_lower": None, "ci_upper": None}]
    r = aug(text, existing)
    assert r and r[0]["ci_lower"] == 0.50 and r[0]["ci_upper"] == 0.90


def test_origin_tag():
    r = aug("vaccine efficacy was 56% (95% CI 51-60)")
    assert r and r[0]["origin"] == "malaria_augment"


def test_efficacy_point_within_ci_not_required_but_plausible():
    # Efficacy point should fall inside its CI for a sane extraction
    r = aug("protective efficacy 42.7%, 95% CI 22.5-57.7")
    x = r[0]
    assert x["ci_lower"] <= x["effect_size"] <= x["ci_upper"]


def test_multiple_effects_in_one_clause():
    """A combined clause must yield every effect, not just the first."""
    from src.core.enhanced_extractor_v3 import EnhancedExtractor
    from src.specialties.malaria_effects import extract_malaria_effects
    e = EnhancedExtractor()
    text = "(OR, 0.26; 95% CI, 0.12 to 0.56; RR, 0.34; 95% CI, 0.15 to 0.61)"
    types = {x["type"] for x in extract_malaria_effects(e, text)}
    assert {"OR", "RR"} <= types


def test_p0_2_vital_signs_not_extracted():
    from src.core.enhanced_extractor_v3 import EnhancedExtractor
    from src.specialties.malaria_effects import extract_malaria_effects
    e = EnhancedExtractor()
    for t in ["respiratory rate RR, 18; 95% CI 16-20 breaths per minute",
              "mean heart rate HR, 72; 95% CI 60-85 bpm"]:
        types_vals = [(x["type"], x["effect_size"]) for x in extract_malaria_effects(e, t)]
        assert ("RR", 18.0) not in types_vals and ("HR", 72.0) not in types_vals


def test_p0_2_real_ratio_still_works():
    r = aug("recurrence RR, 0.18; 95% CI 0.10-0.30")
    assert any(x["type"] == "RR" and abs(x["effect_size"] - 0.18) < 1e-6 for x in r)


def test_cross_mention_dedup():
    from src.core.enhanced_extractor_v3 import EnhancedExtractor
    from src.specialties.malaria_effects import extract_malaria_effects
    e = EnhancedExtractor()
    t = ("hazard ratio 0.45 (95% CI 0.30-0.68). Later: HR 0.45 (95% CI 0.30 to 0.68). "
         "Figure: hazard ratio 0.45 [95% CI 0.30, 0.68].")
    assert len([x for x in extract_malaria_effects(e, t) if x["type"] == "HR"]) == 1
    # opting out keeps duplicates
    assert len([x for x in extract_malaria_effects(e, t, dedup=False) if x["type"] == "HR"]) >= 2


def test_dedup_keys_on_endpoint():
    from src.core.enhanced_extractor_v3 import EnhancedExtractor
    from src.specialties.malaria_effects import extract_malaria_effects
    e = EnhancedExtractor()
    # identical RR for two DIFFERENT endpoints must NOT be merged
    t = ("Clinical malaria risk ratio 0.74 (95% CI 0.61-0.90). "
         "Severe malaria risk ratio 0.74 (95% CI 0.61 to 0.90).")
    eps = {x.get("endpoint") for x in extract_malaria_effects(e, t) if x["type"] == "RR"}
    assert {"CLINICAL_MALARIA", "SEVERE_MALARIA"} <= eps


def test_efficacy_log_rr_field():
    import math
    from src.core.enhanced_extractor_v3 import EnhancedExtractor
    from src.specialties.malaria_effects import extract_malaria_effects
    e = EnhancedExtractor()
    eff = [x for x in extract_malaria_effects(e, "vaccine efficacy was 56% (95% CI 51-60)")
           if x["type"] in ("RRR", "EFFICACY_PCT")][0]
    assert abs(eff["log_rr"] - math.log(0.44)) < 1e-4   # ln(1 - 56/100)
    assert eff["log_rr_lower"] < eff["log_rr_upper"]    # CI flips, stays ordered
    assert "log" in eff["pooling_note"]
