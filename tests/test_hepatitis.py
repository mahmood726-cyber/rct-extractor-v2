"""
Tests for the hepatitis specialty profile, registry wiring, and arm-level extraction.
Mirrors the HIV / malaria tests.
"""
import pytest

from rct_extractor._engine.specialties.hepatitis import (
    HEPATITIS_ENDPOINTS, detect_hepatitis_subspecialty, normalize_hepatitis_endpoint,
    get_hepatitis_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, normalize_endpoint_by_specialty, get_all_endpoints,
    SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.hepatitis_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("RCT of sofosbuvir-velpatasvir vs sofosbuvir-ledipasvir for chronic hepatitis C; "
     "SVR12 (undetectable HCV RNA 12 weeks after treatment).", "treatment"),
    ("Three-dose recombinant hepatitis B vaccine vs placebo; seroprotection "
     "(anti-HBs >=10 mIU/mL) in healthcare workers.", "prevention"),
    ("Maternal tenofovir to prevent mother-to-child transmission of hepatitis B; "
     "infant HBsAg at 7 months in HBeAg-positive mothers.", "pmtct"),
    ("Entecavir vs placebo in chronic hepatitis B; incident hepatocellular carcinoma "
     "and progression to cirrhosis over 5 years.", "outcomes"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_hepatitis_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("sustained virologic response", "SVR"),
    ("HBeAg seroconversion", "HBEAG_SEROCONVERSION"),
    ("HBsAg loss", "HBSAG_LOSS"),
    ("undetectable HBV DNA", "HBV_DNA_SUPPRESSION"),
    ("seroprotection rate", "SEROPROTECTION"),
    ("mother-to-child transmission", "PERINATAL_TRANSMISSION"),
    ("hepatocellular carcinoma", "HCC"),
    ("hepatic decompensation", "CIRRHOSIS"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_hepatitis_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    for name, info in HEPATITIS_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in {"treatment", "prevention", "pmtct", "outcomes"}


# --- registry wiring ---

def test_hepatitis_registered():
    assert "hepatitis" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["hepatitis"]
    assert e["detection_function"] is detect_hepatitis_subspecialty
    assert e["normalizer"] is normalize_hepatitis_endpoint
    assert set(e["subspecialties"]) == {"treatment", "prevention", "pmtct", "outcomes"}


def test_detect_specialty_routes_to_hepatitis():
    spec, sub, _ = detect_specialty(
        "sofosbuvir-velpatasvir for chronic hepatitis C virus infection; "
        "SVR12 sustained virologic response in treatment-naive adults")
    assert spec == "hepatitis" and sub == "treatment"


def test_hepatitis_does_not_break_hiv_malaria_or_cardio():
    assert detect_specialty("dolutegravir-based antiretroviral therapy; week 48 viral "
                            "suppression and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty("artemether-lumefantrine for falciparum malaria; day 28 ACPR")[0] == "malaria"
    assert detect_specialty("sacubitril valsartan in heart failure; cardiovascular death")[0] == "cardiology"


# --- arm-level extraction ---

def test_svr_2x2():
    t = ("SVR12 was achieved by 285/300 (95.0%) in the glecaprevir-pibrentasvir group "
         "and 250/295 (84.7%) in the sofosbuvir group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert len(tabs) == 1
    t0 = tabs[0]
    assert t0["endpoint"] == "SVR"
    # fixed-dose combo regimen kept whole (audit P1-6), not fragmented to a component
    assert {t0["arm1"]["label"], t0["arm2"]["label"]} == {"glecaprevir-pibrentasvir", "sofosbuvir"}
    assert (t0["arm1"]["events"], t0["arm1"]["total"]) == (285, 300)


def test_perinatal_transmission_2x2():
    t = ("Mother-to-child transmission occurred in 2/100 (2.0%) in the tenofovir group "
         "versus 12/95 (12.6%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "PERINATAL_TRANSMISSION"


def test_alt_continuous_poolable():
    r = extract_continuous("mean change in ALT was 35 ± 12 U/L in the entecavir arm")
    assert r and r[0]["endpoint"] == "ALT_LEVEL" and r[0]["poolable"] is True


def test_hbv_dna_is_lognormal():
    r = extract_continuous("mean HBV DNA reduction 4.5 ± 0.8 log10 IU/mL in the tenofovir arm")
    assert r and r[0]["endpoint"] == "HBV_DNA_LEVEL" and r[0]["poolable"] is False
    assert r[0]["pooling_note"]


# --- regression: generic infectious_disease catch-all must not steal routing ---
# (ID keywords viral/bacterial/infection/antibiotic/antiviral are deliberately
# broad; a specific specialty that also matched must win. Fixed 2026-06-08.)

def test_infectious_disease_does_not_steal_from_hepatitis():
    spec, _, _ = detect_specialty(
        "Antiviral treatment of viral hepatitis B (HBV) infection reduced HBV "
        "DNA; bacterial co-infection excluded; antibiotic prophylaxis given.")
    assert spec == "hepatitis"


def test_infectious_disease_still_wins_for_generic_covid():
    # When NO specific specialty matches, the ID fallback is still selected.
    spec, _, _ = detect_specialty(
        "covid-19 sars-cov-2 antiviral therapy; viral infection; "
        "bacterial superinfection; antibiotic stewardship.")
    assert spec == "infectious_disease"
