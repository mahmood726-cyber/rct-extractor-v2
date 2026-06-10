"""
Tests for the rheumatology (inflammatory arthritis / connective-tissue disease)
specialty profile (ra / psa / axspa / gout / sle), registry wiring, and arm-level
extraction. Mirrors the stroke / respiratory / hepatitis / HIV / malaria tests.

This profile SUPERSEDES the thin generic `autoimmune` bucket (ACR20/50/70 /
PASI90 / SRI). The registry-wiring tests below assume the orchestrator has wired
'rheumatology' into SPECIALTY_REGISTRY and the detect_specialty keyword/elif
blocks (and removed 'autoimmune').

Routing note: rheumatology deliberately does NOT claim bare 'psoriasis' /
'plaque psoriasis' (those route to a future dermatology specialty) nor bare
'inflammatory bowel' / 'crohn' / 'colitis' (gastroenterology). It anchors on
arthritis / spondyloarthritis / lupus / gout terms.
"""
import pytest

from rct_extractor._engine.specialties.rheumatology import (
    RHEUMATOLOGY_ENDPOINTS, detect_rheumatology_subspecialty,
    normalize_rheumatology_endpoint, get_rheumatology_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.rheumatology_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Adalimumab plus methotrexate versus methotrexate alone in rheumatoid arthritis; "
     "ACR20 response and DAS28 remission at week 24.", "ra"),
    ("Secukinumab versus placebo in psoriatic arthritis; ACR20 response and minimal "
     "disease activity (MDA) at week 24.", "psa"),
    ("Certolizumab pegol versus placebo in ankylosing spondylitis and axial "
     "spondyloarthritis; ASAS40 response and change in BASDAI at week 16.", "axspa"),
    ("Febuxostat versus allopurinol in gout; serum urate below 6 mg/dL target "
     "attainment and gout flare rate.", "gout"),
    ("Anifrolumab versus placebo in systemic lupus erythematosus; SRI-4 and BICLA "
     "response with SLEDAI change.", "sle"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_rheumatology_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("ACR20", "ACR20"),
    ("acr 50", "ACR50"),
    ("acr70", "ACR70"),
    ("DAS28 remission", "DAS28_REMISSION"),
    ("das28<2.6", "DAS28_REMISSION"),
    ("HAQ-DI", "HAQ_DI"),
    ("modified total Sharp score", "RADIOGRAPHIC_PROGRESSION"),
    ("minimal disease activity", "MDA"),
    ("PASI90", "PASI_RESPONSE"),
    ("ASAS40", "ASAS40"),
    ("asas20", "ASAS20"),
    ("change in BASDAI", "BASDAI_CHANGE"),
    ("asdas change", "ASDAS_CHANGE"),
    ("gout flare", "GOUT_FLARE"),
    ("serum urate < 6", "URATE_TARGET"),
    ("change in serum urate", "SERUM_URATE"),
    ("SRI-4", "SRI4"),
    ("bicla", "BICLA"),
    ("sledai change", "SLEDAI_CHANGE"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_rheumatology_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"ra", "psa", "axspa", "gout", "sle"}
    for name, info in RHEUMATOLOGY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


def test_endpoint_patterns_cover_all_subspecialties():
    for sub in ("ra", "psa", "axspa", "gout", "sle"):
        assert get_rheumatology_endpoint_patterns(sub)


# --- registry wiring (post-orchestrator) ---

def test_rheumatology_registered():
    assert "rheumatology" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["rheumatology"]
    assert e["detection_function"] is detect_rheumatology_subspecialty
    assert e["normalizer"] is normalize_rheumatology_endpoint
    assert set(e["subspecialties"]) == {"ra", "psa", "axspa", "gout", "sle"}


def test_detect_specialty_routes_to_rheumatology():
    spec, sub, _ = detect_specialty(
        "A randomized trial of adalimumab versus placebo in rheumatoid arthritis; "
        "the primary outcome was ACR20 response at week 24, with ACR50 and DAS28 "
        "remission as secondary endpoints.")
    assert spec == "rheumatology" and sub == "ra"

    spec2, sub2, _ = detect_specialty(
        "Secukinumab versus placebo in patients with ankylosing spondylitis and axial "
        "spondyloarthritis; ASAS40 response at week 16 and change in BASDAI.")
    assert spec2 == "rheumatology" and sub2 == "axspa"

    spec3, sub3, _ = detect_specialty(
        "Anifrolumab versus placebo in systemic lupus erythematosus; SRI-4 response, "
        "BICLA, and SLEDAI change.")
    assert spec3 == "rheumatology" and sub3 == "sle"


def test_rheumatology_does_not_break_neighbors():
    assert detect_specialty("dolutegravir-based antiretroviral therapy; week 48 viral "
                            "suppression and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty("artemether-lumefantrine for falciparum malaria; day 28 "
                            "ACPR")[0] == "malaria"
    assert detect_specialty("sofosbuvir-velpatasvir for chronic hepatitis C; sustained "
                            "virologic response SVR12")[0] == "hepatitis"
    assert detect_specialty("sacubitril valsartan in heart failure; cardiovascular "
                            "death and heart failure hospitalization")[0] == "cardiology"
    assert detect_specialty("Endovascular thrombectomy in acute ischaemic stroke; "
                            "functional independence (modified Rankin scale 0-2) and "
                            "successful reperfusion (TICI 2b-3)")[0] == "stroke"


# --- arm-level extraction ---

def test_acr20_2x2_adalimumab_vs_placebo():
    t = ("An ACR20 response was achieved in 120/200 (60.0%) in the adalimumab group "
         "and in 50/200 (25.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "ACR20"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"adalimumab", "placebo"}


def test_das28_change_continuous_poolable():
    r = extract_continuous("the mean change in DAS28 was 2.4 ± 1.1 in the tofacitinib arm")
    assert r and r[0]["endpoint"] == "DAS28_CHANGE" and r[0]["poolable"] is True
    # rheumatology indices are NOT log-normal -> no pooling note
    assert r[0].get("pooling_note") is None


def test_haq_di_continuous_poolable():
    r = extract_continuous("mean HAQ-DI was 1.2 ± 0.6 in the methotrexate group")
    assert r and r[0]["endpoint"] == "HAQ_DI" and r[0]["poolable"] is True
    assert r[0].get("pooling_note") is None
