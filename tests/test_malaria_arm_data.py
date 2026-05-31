"""
Tests for arm-level / 2x2 extraction (src/specialties/malaria_arm_data.py).
"""
import pytest
from src.specialties.malaria_arm_data import (
    extract_proportions, pair_2x2, extract_arm_level,
)


def test_n_over_N_pct():
    r = extract_proportions("ACPR was 121/125 (96.8%) in the AL group")
    assert len(r) == 1
    p = r[0]
    assert p["events"] == 121 and p["total"] == 125 and p["endpoint"] == "ACPR"
    assert p["pct_consistent"]


def test_pct_then_n_over_N():
    r = extract_proportions("day 42 cure rate was 100% (106/106) with DHA-PPQ")
    assert r and r[0]["events"] == 106 and r[0]["total"] == 106
    assert r[0]["endpoint"] == "ACPR"


def test_n_of_N():
    r = extract_proportions("treatment failure occurred in 8 of 150 (5.3%) recipients")
    assert r and r[0]["events"] == 8 and r[0]["total"] == 150
    assert r[0]["endpoint"] == "TREATMENT_FAILURE"


def test_pct_consistency_flag():
    # 96.8% is consistent with 121/125; 50% is NOT
    ok = extract_proportions("ACPR 121/125 (96.8%)")[0]
    bad = extract_proportions("ACPR 121/125 (50.0%)")[0]
    assert ok["pct_consistent"] and not bad["pct_consistent"]


def test_requires_endpoint():
    # a bare proportion with no malaria endpoint nearby is not captured
    assert extract_proportions("the figure showed 121/125 (96.8%) of pixels") == []


def test_implausible_proportion_rejected():
    assert extract_proportions("ACPR 200/125 (96.8%)") == []   # events > total


@pytest.mark.parametrize("text,ep,a1,a2", [
    ("ACPR was 121/125 (96.8%) in the AL group and 130/148 (87.8%) in the SP group",
     "ACPR", "artemether-lumefantrine", "sulfadoxine-pyrimethamine"),
    ("treatment failure in 8 of 150 (5.3%) chloroquine recipients vs 18 of 148 (12.2%) in the placebo arm",
     "TREATMENT_FAILURE", "chloroquine", "placebo"),
])
def test_2x2_pairing(text, ep, a1, a2):
    tables = extract_arm_level(text)["tables_2x2"]
    assert len(tables) >= 1
    t = next(t for t in tables if t["endpoint"] == ep)
    arms = {t["arm1"]["label"], t["arm2"]["label"]}
    assert {a1, a2} <= arms
    assert t["both_consistent"]


def test_2x2_recovers_raw_counts():
    t = extract_arm_level(
        "cure rate 100% (106/106) with dihydroartemisinin-piperaquine versus 95% (140/147) with artemether-lumefantrine"
    )["tables_2x2"][0]
    totals = {t["arm1"]["total"], t["arm2"]["total"]}
    assert totals == {106, 147}


# --- Multi-persona review P0 regressions ---

def test_p0_1_nearest_endpoint_not_first_in_list():
    # proportion is anaemia's, even though "ACPR" appears earlier in the window
    r = extract_proportions("ACPR analysis aside, anaemia occurred in 8 of 150 (5.3%) children")
    assert r and r[0]["endpoint"] == "ANAEMIA"


def test_p0_3_et_al_not_drug_arm():
    # "et al." must NOT be read as the AL (artemether-lumefantrine) arm
    r = extract_proportions("Smith et al. reported ACPR in 121 of 125 (96.8%)")
    assert r and r[0]["arm"] != "artemether-lumefantrine"


def test_p0_3_uppercase_AL_still_tags():
    r = extract_proportions("ACPR was 121/125 (96.8%) in the AL group")
    assert r and r[0]["arm"] == "artemether-lumefantrine"


def test_p0_4_page_x_of_y_rejected():
    assert extract_proportions("see ACPR data on page 8 of 150 of the report") == []
    assert extract_proportions("at day 8 of 150 follow-up, ACPR was assessed") == []


# --- P0-7: PCR-corrected vs uncorrected separation ---

def test_pcr_status_tagged():
    p = extract_proportions("PCR-corrected ACPR was 121/125 (96.8%)")[0]
    assert p["pcr_status"] == "corrected"
    p2 = extract_proportions("PCR-uncorrected ACPR was 100/125 (80.0%)")[0]
    assert p2["pcr_status"] == "uncorrected"


def test_pcr_corrected_uncorrected_not_paired():
    t = ("PCR-corrected ACPR was 121/125 (96.8%) in the AL group versus "
         "PCR-uncorrected ACPR 110/148 (74.3%) in the SP group")
    assert extract_arm_level(t)["tables_2x2"] == []


def test_same_pcr_status_pairs():
    t = ("PCR-corrected ACPR was 121/125 (96.8%) in the AL group and "
         "130/148 (87.8%) in the SP group")
    tabs = extract_arm_level(t)["tables_2x2"]
    assert len(tabs) == 1 and tabs[0]["pcr_status"] == "corrected"


def test_multi_arm_flagged_not_poolable():
    t = ("ACPR was 121/125 (96.8%) in AL group, 130/148 (87.8%) in SP group, "
         "and 140/150 (93.3%) in DP group")
    r = extract_arm_level(t)
    assert r["tables_2x2"] and all(x["multi_arm"] for x in r["tables_2x2"])
    assert r["poolable_2x2"] == []   # multi-arm excluded from poolable


def test_clean_two_arm_is_poolable():
    t = "ACPR was 121/125 (96.8%) in the AL group and 130/148 (87.8%) in the SP group"
    assert len(extract_arm_level(t)["poolable_2x2"]) == 1


def test_analysis_population_tagged():
    p = extract_proportions("per-protocol ACPR was 121/125 (96.8%)")[0]
    assert p["analysis_population"] == "pp"


# --- Continuous per-arm extraction ---

def test_continuous_mean_sd_poolable():
    from src.specialties.malaria_arm_data import extract_continuous
    # haemoglobin is ~symmetric -> mean+SD poolable as-is
    r = extract_continuous("mean haemoglobin 10.5 ± 1.2 g/dL (n=50) in the AL group")
    assert r and r[0]["stat"] == "mean_sd" and r[0]["mean"] == 10.5 and r[0]["sd"] == 1.2
    assert r[0]["n"] == 50 and r[0]["poolable"] and r[0]["endpoint"] == "HAEMOGLOBIN"


def test_continuous_lognormal_not_poolable_raw():
    from src.specialties.malaria_arm_data import extract_continuous
    # parasite clearance time is log-normal -> raw mean+SD not poolable as MD
    r = extract_continuous("mean parasite clearance time 28.4 ± 6.2 h (n=50) in the AL group")
    assert r and r[0]["endpoint"] == "PARASITE_CLEARANCE_TIME"
    assert r[0]["poolable"] is False and r[0]["pooling_note"]


def test_mean_sd_rejects_difference_or_se():
    from src.specialties.malaria_arm_data import extract_continuous
    assert extract_continuous("adjusted mean difference in haemoglobin was 1.8 ± 0.4 g/dL") == []


def test_continuous_median_iqr_not_poolable():
    from src.specialties.malaria_arm_data import extract_continuous
    r = extract_continuous("median fever clearance time was 18 (IQR 12-26) hours")
    assert r and r[0]["stat"] == "median_iqr" and r[0]["poolable"] is False


def test_haemoglobin_spelling_both():
    # the [ae]+ fix: both British and American spellings route to HAEMOGLOBIN
    from src.specialties.malaria_arm_data import extract_continuous
    assert extract_continuous("haemoglobin mean 10.5 ± 1.2 g/dL")[0]["endpoint"] == "HAEMOGLOBIN"
    assert extract_continuous("hemoglobin mean 10.5 ± 1.2 g/dL")[0]["endpoint"] == "HAEMOGLOBIN"
