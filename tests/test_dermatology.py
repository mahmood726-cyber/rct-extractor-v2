"""
Tests for the dermatology (inflammatory skin disease) specialty profile
(psoriasis / atopic_dermatitis / acne / hidradenitis), registry wiring, and
arm-level extraction. Mirrors the nephrology / stroke / respiratory / hepatitis /
HIV / malaria tests.

Routing note (coordinated with rheumatology): dermatology claims SKIN disease only
-- (plaque) psoriasis, PASI, atopic dermatitis / eczema, EASI, SCORAD, acne
(vulgaris), hidradenitis suppurativa, HiSCR, IGA, vIGA. It deliberately does NOT
claim 'psoriatic arthritis' or bare 'ACR' (those belong to rheumatology). The
'psorias-' stem does NOT match the distinct 'psoriatic' stem, so a psoriatic-
arthritis / ACR20 trial keeps routing to rheumatology. The tests below ground that
contract against real detect_specialty output.
"""
import pytest

from rct_extractor._engine.specialties.dermatology import (
    DERMATOLOGY_ENDPOINTS, detect_dermatology_subspecialty,
    normalize_dermatology_endpoint, get_dermatology_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.dermatology_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Secukinumab versus placebo in moderate-to-severe plaque psoriasis; the "
     "primary endpoint was PASI90 at week 16 and IGA 0 or 1 (clear or almost "
     "clear).", "psoriasis"),
    ("Dupilumab versus placebo in moderate-to-severe atopic dermatitis (eczema); "
     "EASI75, vIGA-AD 0/1, and peak pruritus NRS improvement at week 16.",
     "atopic_dermatitis"),
    ("Topical clascoterone versus vehicle in acne vulgaris; IGA success and "
     "inflammatory lesion count reduction at week 12.", "acne"),
    ("Adalimumab versus placebo in hidradenitis suppurativa; Hidradenitis "
     "Suppurativa Clinical Response (HiSCR) at week 12.", "hidradenitis"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_dermatology_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("PASI75", "PASI75"),
    ("PASI90", "PASI90"),
    ("PASI100", "PASI100"),
    ("IGA 0 or 1", "IGA_RESPONSE"),
    ("clear or almost clear", "IGA_RESPONSE"),
    ("change in PASI", "PASI_CHANGE"),
    ("EASI75", "EASI75"),
    ("EASI90", "EASI90"),
    ("vIGA-AD", "IGA_AD_RESPONSE"),
    ("peak pruritus NRS", "PRURITUS_NRS"),
    ("change in EASI", "EASI_CHANGE"),
    ("SCORAD", "SCORAD"),
    ("acne IGA success", "IGA_ACNE_SUCCESS"),
    ("inflammatory lesion count", "LESION_COUNT"),
    ("HiSCR", "HISCR"),
    ("hidradenitis suppurativa clinical response", "HISCR"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_dermatology_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"psoriasis", "atopic_dermatitis", "acne", "hidradenitis"}
    for name, info in DERMATOLOGY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


def test_subspecialty_patterns_cover_all_four():
    for sub in ("psoriasis", "atopic_dermatitis", "acne", "hidradenitis"):
        assert get_dermatology_endpoint_patterns(sub), sub


# --- registry wiring ---

def test_dermatology_registered():
    assert "dermatology" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["dermatology"]
    assert e["detection_function"] is detect_dermatology_subspecialty
    assert e["normalizer"] is normalize_dermatology_endpoint
    assert set(e["subspecialties"]) == {
        "psoriasis", "atopic_dermatitis", "acne", "hidradenitis"}


def test_detect_specialty_routes_to_dermatology():
    # Plaque-psoriasis (SKIN) PASI90 sentence -> dermatology/psoriasis.
    spec, sub, _ = detect_specialty(
        "Secukinumab versus placebo in adults with moderate-to-severe plaque "
        "psoriasis; the primary endpoint was PASI90 at week 16, with IGA 0 or 1 "
        "(clear or almost clear) as a key secondary endpoint.")
    assert spec == "dermatology" and sub == "psoriasis"

    # Atopic-dermatitis EASI75 sentence -> dermatology/atopic_dermatitis (must
    # NOT be stolen by respiratory on the bare 'dupilumab' keyword).
    spec2, sub2, _ = detect_specialty(
        "Dupilumab versus placebo in adults with moderate-to-severe atopic "
        "dermatitis; the co-primary endpoints were EASI75 and peak pruritus NRS "
        "improvement at week 16.")
    assert spec2 == "dermatology" and sub2 == "atopic_dermatitis"


def test_psoriatic_arthritis_stays_rheumatology():
    # CRUCIAL: a psoriatic-ARTHRITIS / ACR20 trial must keep routing to
    # rheumatology -- dermatology only claims SKIN 'psoriasis', not 'psoriatic
    # arthritis'.
    spec, sub, _ = detect_specialty(
        "Ixekizumab versus placebo in patients with active psoriatic arthritis; "
        "the primary endpoint was ACR20 response at week 24, with minimal disease "
        "activity as a secondary endpoint.")
    assert spec == "rheumatology"


def test_dermatology_does_not_break_neighbors():
    assert detect_specialty("dolutegravir-based antiretroviral therapy; week 48 viral "
                            "suppression and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty("artemether-lumefantrine for falciparum malaria; day 28 "
                            "ACPR")[0] == "malaria"
    assert detect_specialty("sofosbuvir-velpatasvir for chronic hepatitis C; sustained "
                            "virologic response SVR12")[0] == "hepatitis"
    assert detect_specialty("sacubitril valsartan in heart failure; cardiovascular "
                            "death and heart failure hospitalization")[0] == "cardiology"
    # psoriatic arthritis / ACR20 belongs to rheumatology, NOT dermatology
    assert detect_specialty("upadacitinib in psoriatic arthritis; ACR20 and ACR50 "
                            "response at week 24")[0] == "rheumatology"


# --- arm-level extraction ---

def test_pasi90_2x2():
    t = ("PASI90 was achieved by 150/300 (50.0%) in the secukinumab group and by "
         "15/300 (5.0%) in the placebo group at week 16.")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "PASI90"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"secukinumab", "placebo"}


def test_pasi_change_continuous_is_poolable():
    # PASI change is a bounded clinical severity index -> poolable raw-scale MD,
    # NOT log-normal (no pooling_note).
    r = extract_continuous("the mean change in PASI was -18.5 ± 4.2 in the ixekizumab arm")
    assert r and r[0]["endpoint"] == "PASI_CHANGE"
    assert r[0]["poolable"] is True
    assert r[0]["pooling_note"] is None


def test_easi_change_continuous_is_poolable():
    r = extract_continuous("the mean change from baseline in EASI was -22.0 ± 6.0 in the dupilumab group")
    assert r and r[0]["endpoint"] == "EASI_CHANGE"
    assert r[0]["poolable"] is True
    assert r[0]["pooling_note"] is None
