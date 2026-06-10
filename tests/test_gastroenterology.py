"""
Tests for the gastroenterology specialty profile (ibd / hpylori / gerd / mash),
registry wiring, and arm-level extraction. Mirrors the nephrology / stroke /
respiratory / hepatitis / HIV / malaria tests.

Routing note (coordinated with the existing hepatitis specialty): gastroenterology
keywords are LUMINAL-GI + MASH-specific (ulcerative colitis, Crohn's disease, IBD,
Mayo score, CDAI, mucosal healing, Helicobacter pylori, erosive oesophagitis,
GERD, NASH, MASH, NAFLD, MAFLD). We deliberately do NOT claim bare 'hepatitis',
'cirrhosis', 'HCC', or 'liver fibrosis' alone -- a VIRAL hepatitis-C SVR trial must
still route to the existing `hepatitis` specialty, NOT gastroenterology. The tests
below ground that contract against real detect_specialty output.
"""
import pytest

from rct_extractor._engine.specialties.gastroenterology import (
    GASTROENTEROLOGY_ENDPOINTS, detect_gastroenterology_subspecialty,
    normalize_gastroenterology_endpoint, get_gastroenterology_endpoint_patterns,
)
from rct_extractor._engine.specialties.registry import (
    detect_specialty, SPECIALTY_REGISTRY,
)
from rct_extractor._engine.specialties.gastroenterology_arm_data import (
    extract_arm_level, extract_proportions, extract_continuous,
)


# --- subspecialty detection ---

@pytest.mark.parametrize("text,expected", [
    ("Vedolizumab versus placebo in moderately-to-severely active ulcerative colitis "
     "(UC); the primary endpoint was clinical remission, with endoscopic remission "
     "(mucosal healing) and steroid-free remission at week 52.", "ibd"),
    ("Upadacitinib versus placebo in Crohn's disease; change in CDAI (Crohn's Disease "
     "Activity Index) and clinical response at week 12.", "ibd"),
    ("Vonoprazan-amoxicillin dual therapy versus bismuth quadruple therapy for "
     "Helicobacter pylori eradication; the eradication rate was assessed by urea "
     "breath test.", "hpylori"),
    ("Esomeprazole versus placebo for healing of erosive esophagitis in gastro-"
     "esophageal reflux disease (GERD); heartburn-free days were a secondary "
     "endpoint.", "gerd"),
    ("Resmetirom versus placebo in nonalcoholic steatohepatitis (NASH); NASH "
     "resolution and at least 1 stage fibrosis improvement; MRI-PDFF liver fat "
     "reduction.", "mash"),
])
def test_subspecialty_detection(text, expected):
    sub, conf = detect_gastroenterology_subspecialty(text)
    assert sub == expected and 0 < conf <= 1


@pytest.mark.parametrize("phrase,canonical", [
    ("clinical remission", "CLINICAL_REMISSION"),
    ("clinical response", "CLINICAL_RESPONSE"),
    ("mucosal healing", "ENDOSCOPIC_REMISSION"),
    ("endoscopic improvement", "ENDOSCOPIC_REMISSION"),
    ("steroid-free remission", "STEROID_FREE_REMISSION"),
    ("Crohn's Disease Activity Index", "CDAI_CHANGE"),
    ("CDAI", "CDAI_CHANGE"),
    ("Mayo score", "MAYO_SCORE"),
    ("H. pylori eradication", "ERADICATION"),
    ("eradication rate", "ERADICATION"),
    ("erosive esophagitis healing", "HEALING_ESOPHAGITIS"),
    ("heartburn-free days", "HEARTBURN_FREE"),
    ("NASH resolution", "NASH_RESOLUTION"),
    ("fibrosis improvement", "FIBROSIS_IMPROVEMENT"),
    ("MRI-PDFF", "LIVER_FAT"),
    ("liver fat", "LIVER_FAT"),
])
def test_endpoint_normalization(phrase, canonical):
    assert normalize_gastroenterology_endpoint(phrase) == canonical


def test_endpoints_have_required_fields():
    valid = {"ibd", "hpylori", "gerd", "mash"}
    for name, info in GASTROENTEROLOGY_ENDPOINTS.items():
        assert info["aliases"] and info["measure_types"]
        assert info["subspecialty"] in valid


def test_subspecialty_patterns_cover_all_four():
    for sub in ("ibd", "hpylori", "gerd", "mash"):
        assert get_gastroenterology_endpoint_patterns(sub), sub


# --- registry wiring ---

def test_gastroenterology_registered():
    assert "gastroenterology" in SPECIALTY_REGISTRY
    e = SPECIALTY_REGISTRY["gastroenterology"]
    assert e["detection_function"] is detect_gastroenterology_subspecialty
    assert e["normalizer"] is normalize_gastroenterology_endpoint
    assert set(e["subspecialties"]) == {"ibd", "hpylori", "gerd", "mash"}


def test_detect_specialty_routes_to_gastroenterology():
    # UC / Crohn's clinical-remission sentence routes to gastroenterology/ibd.
    spec, sub, _ = detect_specialty(
        "Vedolizumab versus placebo in moderately-to-severely active ulcerative "
        "colitis (UC); the primary endpoint was clinical remission, with endoscopic "
        "remission (mucosal healing) and steroid-free remission at week 52.")
    assert spec == "gastroenterology" and sub == "ibd"

    # H. pylori eradication sentence routes to gastroenterology/hpylori.
    spec2, sub2, _ = detect_specialty(
        "Vonoprazan-amoxicillin dual therapy versus bismuth quadruple therapy for "
        "Helicobacter pylori eradication; the eradication rate was assessed by urea "
        "breath test.")
    assert spec2 == "gastroenterology" and sub2 == "hpylori"

    # MASH (NASH-specific) sentence routes to gastroenterology/mash, NOT hepatitis.
    spec3, sub3, _ = detect_specialty(
        "Resmetirom versus placebo in nonalcoholic steatohepatitis (NASH) with liver "
        "fibrosis; NASH resolution and at least 1 stage fibrosis improvement; "
        "MRI-PDFF liver fat reduction.")
    assert spec3 == "gastroenterology" and sub3 == "mash"


def test_viral_hepatitis_c_svr_stays_hepatitis():
    # CRUCIAL: a viral hepatitis-C SVR trial must NOT be stolen by gastroenterology
    # -- it stays with the existing `hepatitis` specialty (no NASH/MASH/NAFLD or
    # luminal-GI anchors present, so gastroenterology scores zero).
    spec, sub, _ = detect_specialty(
        "Sofosbuvir-velpatasvir for 12 weeks in chronic hepatitis C virus infection; "
        "the primary outcome was sustained virologic response (SVR12).")
    assert spec == "hepatitis"


def test_gastroenterology_does_not_break_neighbors():
    assert detect_specialty("dolutegravir-based antiretroviral therapy; week 48 viral "
                            "suppression and CD4 recovery in adults with HIV")[0] == "hiv"
    assert detect_specialty("artemether-lumefantrine for falciparum malaria; day 28 "
                            "ACPR")[0] == "malaria"
    # viral hepatitis-C SVR still routes to hepatitis (the load-bearing contract).
    assert detect_specialty("sofosbuvir-velpatasvir for chronic hepatitis C; sustained "
                            "virologic response SVR12")[0] == "hepatitis"
    assert detect_specialty("sacubitril valsartan in heart failure; cardiovascular "
                            "death and heart failure hospitalization")[0] == "cardiology"
    assert detect_specialty("upadacitinib in rheumatoid arthritis; ACR20 and DAS28 "
                            "remission at week 12")[0] == "rheumatology"


# --- arm-level extraction ---

def test_clinical_remission_2x2():
    t = ("Clinical remission was achieved in 120/300 (40.0%) in the vedolizumab group "
         "and in 45/300 (15.0%) in the placebo group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "CLINICAL_REMISSION"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"vedolizumab", "placebo"}


def test_eradication_2x2():
    t = ("H. pylori eradication was achieved in 95/100 (95.0%) in the vonoprazan group "
         "and in 80/100 (80.0%) in the omeprazole group")
    tabs = extract_arm_level(t)["poolable_2x2"]
    assert tabs and tabs[0]["endpoint"] == "ERADICATION"
    assert {tabs[0]["arm1"]["label"], tabs[0]["arm2"]["label"]} == {"vonoprazan", "omeprazole"}


def test_cdai_continuous_poolable():
    r = extract_continuous("the mean CDAI score was 150 ± 40 in the upadacitinib arm")
    assert r and r[0]["endpoint"] == "CDAI_CHANGE" and r[0]["poolable"] is True
    # GI clinical indices are NOT log-normal -> no pooling note.
    assert r[0].get("pooling_note") is None


def test_liver_fat_continuous_poolable():
    r = extract_continuous("mean MRI-PDFF liver fat was 18 ± 6 in the resmetirom arm")
    assert r and r[0]["endpoint"] == "LIVER_FAT" and r[0]["poolable"] is True
    assert r[0].get("pooling_note") is None
