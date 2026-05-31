"""
Tests for the HIV specialty profile, registry wiring, and arm-level extraction.
Mirrors the malaria tests.
"""
import pytest

from src.specialties.hiv import (
    HIV_ENDPOINTS, detect_hiv_subspecialty, normalize_hiv_endpoint,
    get_hiv_endpoint_patterns,
)
from src.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from src.specialties.hiv_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of dolutegravir vs efavirenz-based ART; week 48 viral suppression "
     "(HIV-1 RNA <50 copies, FDA snapshot) and CD4 recovery.", "treatment"),
    ("Long-acting cabotegravir vs daily oral TDF/FTC for pre-exposure "
     "prophylaxis; HIV incidence per 100 person-years.", "prevention"),
    ("Maternal ART to prevent mother-to-child transmission of HIV; infant HIV "
     "infection at 6 weeks.", "pmtct"),
    ("Isoniazid preventive therapy in people living with HIV; incident "
     "tuberculosis and IRIS.", "coinfection"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_hiv_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("week 48 viral suppression", "VIRAL_SUPPRESSION"),
    ("confirmed virologic failure", "VIROLOGIC_FAILURE"),
    ("change in CD4 count", "CD4_COUNT"),
    ("HIV acquisition", "HIV_ACQUISITION"),
    ("mother-to-child transmission", "MTCT"),
    ("incident tuberculosis", "TB_INCIDENCE"),
    ("loss to follow-up", "RETENTION"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_hiv_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in HIV_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"treatment", "prevention", "pmtct", "coinfection"}


# --- registry wiring ---

def test_hiv_registered():
    assert "hiv" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["hiv"]
    assert e["detection_function"] is detect_hiv_subspecialty
    assert e["normalizer"] is normalize_hiv_endpoint
    assert set(e["subspecialties"]) == {"treatment", "prevention", "pmtct", "coinfection"}


def test_detect_specialty_routes_to_hiv():
    spec, sub, _ = detect_specialty(
        "dolutegravir-based antiretroviral therapy; week 48 viral suppression "
        "and CD4 recovery in adults with HIV")
    assert spec == "hiv" and sub == "treatment"


def test_hiv_does_not_break_malaria_or_cardio():
    assert detect_specialty("artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty("sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


# --- arm-level extraction ---

def test_viral_suppression_2x2():
    t = ("Week 48 viral suppression was achieved by 320/350 (91.4%) in the "
         "dolutegravir group and 290/345 (84.1%) in the efavirenz group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "VIRAL_SUPPRESSION"
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"dolutegravir", "efavirenz"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (320, 350)


def test_mtct_2x2():
    t = ("Infant HIV infection at 6 weeks occurred in 5/200 (2.5%) in the maternal "
         "ART group versus 18/195 (9.2%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "MTCT"


def test_cd4_continuous_poolable():
    r = extract_continuous("mean CD4 count increase 250 ± 60 cells/mm3 in the DTG arm")
    assert r and r[0]["endpoint"] == "CD4_COUNT" and r[0]["poolable"] is True


def test_hiv_rna_is_lognormal():
    r = extract_continuous("mean HIV RNA reduction 3.2 ± 0.5 log10 copies in the DTG arm")
    assert r and r[0]["endpoint"] == "HIV_RNA" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]
