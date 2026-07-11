"""
rct_extractor.api -- the clean public extraction API.

One function, ``extract(text, specialty=...)``, runs the full text->effects
pipeline for any of the 28 disease specialties (auto-detected or forced), plus
``extract_batch`` for many abstracts and ``to_metakit_config`` to emit the
universal meta-starter-kit interchange JSON consumed by RapidMeta / allmeta /
E156 capsules / Pairwise70.

This module is a thin, additive facade over the existing engine in ``src`` --
it does not change extractor behaviour, it just gives installers one stable,
documented entry point instead of a dozen internal imports.
"""
from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

# The disease specialties that ship a full text->arm-level extractor
# (each has a src/specialties/<name>_arm_data.py with extract_arm_level()).
# Order is the canonical order used in the README and CLI help.
SPECIALTIES: Tuple[str, ...] = (
    "ards",
    "perioperative",
    "chronic_pain",
    "postoperative_pain",
    "anaemia",
    "itp",
    "transfusion",
    "allergic_rhinitis",
    "urticaria",
    "orthopaedic",
    "low_back_pain",
    "wound_healing",
    "hiv",
    "malaria",
    "typhoid",
    "schistosomiasis",
    "sickle_cell",
    "cholera",
    "maternal_neonatal",
    "tuberculosis",
    "hepatitis",
    "meningitis",
    "pneumonia",
    "diarrhoeal",
    "malnutrition",
    "helminths",
    "hypertension",
    "cervical_cancer",
    "endometriosis",
    "menopause_hrt",
    "infertility_ivf",
    "gestational_diabetes",
    "uterine_fibroids",
    "benign_prostatic_hyperplasia",
    "erectile_dysfunction",
    "urinary_incontinence",
    "diabetes",
    "osteoporosis",
    "kidney_transplant",
    "cystic_fibrosis",
    "liver_transplant",
    "heart_lung_transplant",
    "neonatology",
    "emergency_resuscitation",
    "vascular_surgery",
    "bronchiectasis",
    "interstitial_lung_disease",
    "bariatric_surgery",
    "geriatrics_frailty",
    "plastic_reconstructive_surgery",
    "rehabilitation_physiotherapy",
    "palliative_care",
    "pulmonary_hypertension",
    "pcos",
    "respiratory",
    "cardiology",
    "oncology",
    "stroke",
    "nephrology",
    "psychiatry",
    "rheumatology",
    "gastroenterology",
    "dermatology",
    "ophthalmology",
    "cataract",
    "insomnia",
    "allergic_conjunctivitis",
    "chronic_rhinosinusitis",
    "obstructive_sleep_apnea",
    "otitis_media",
    "alcohol_use_disorder",
    "oesophageal_cancer",
    "prostate_cancer",
    "ovarian_cancer",
    "pancreatic_cancer",
    "gastric_cancer",
    "hepatocellular_carcinoma",
    "melanoma",
    "leukaemia",
    "lymphoma",
    "multiple_myeloma",
    "glioma",
    "sarcoma",
    "thyroid_cancer",
    "endometrial_cancer",
    "testicular_cancer",
    "myelodysplastic_syndrome",
    "influenza",
    "head_neck_cancer",
    "bladder_cancer",
    "renal_cell_carcinoma",
    "dyslipidaemia",
    "venous_thromboembolism",
    "peripheral_artery_disease",
    "obesity",
    "thyroid",
    "parkinsons",
    "alzheimers",
    "multiple_sclerosis",
    "migraine",
    "schizophrenia",
    "cirrhosis",
    "osteoarthritis",
    "covid19",
    "sepsis",
)

__all__ = [
    "SPECIALTIES",
    "list_specialties",
    "detect_specialty",
    "extract",
    "extract_batch",
    "extract_dose_response",
    "to_metakit_config",
    "effect_direction",
]

# Effect types whose null value is 1 (ratios) vs 0 (differences). Direction is the
# side of the null the POINT ESTIMATE falls on — a geometric fact, independent of
# whether the outcome is desirable. It is NOT "favors treatment": that also needs the
# outcome's polarity (is the event good or bad?), which the extractor does not know.
_RATIO_TYPES = frozenset({"HR", "OR", "RR", "IRR", "GMR"})
_DIFF_TYPES = frozenset({"MD", "SMD", "WMD", "ARD", "ARR", "RMST"})


def effect_direction(effect_type: Optional[str], value: Optional[float]) -> Optional[str]:
    """Direction of an effect's point estimate relative to its null.

    Returns ``"increase"`` (intervention arm higher / more of the outcome),
    ``"decrease"`` (intervention arm lower / less), ``"null"`` (at the null), or
    ``None`` when direction is undefined for this type (e.g. NNT/NNH/RRR) or the
    value is missing. For ratio measures (HR/OR/RR/IRR/GMR) the null is 1; for
    differences (MD/SMD/WMD/ARD/ARR/RMST) the null is 0. Deterministic — the value
    alone decides it — so it can never disagree with the number it describes.

    This is the sign that decides which way an estimate pushes a pooled result, so
    an inverted arm orientation (see the T1.5 control-first fix) shows up here as a
    flipped direction.
    """
    if value is None or effect_type is None:
        return None
    et = str(effect_type).upper()
    if et in _RATIO_TYPES:
        if value > 1.0:
            return "increase"
        if value < 1.0:
            return "decrease"
        return "null"
    if et in _DIFF_TYPES:
        if value > 0.0:
            return "increase"
        if value < 0.0:
            return "decrease"
        return "null"
    return None


def extract_dose_response(text: str) -> Dict[str, Any]:
    """Extract dose-response relationships from a block of text.

    This is a SEPARATE extraction mode from :func:`extract` (which targets RCT
    arm-comparison effects). It is built for the data a dose-response
    meta-analysis pools: per-unit (trend/slope) estimates, categorical
    dose-level estimates (dose category vs reference), the exposure/dose metric
    and units, the number of dose categories, the reference category, and any
    reported nonlinearity (P for nonlinearity / J-/U-shape / spline).

    Args:
        text: Abstract or full-text body of a dose-response / cohort study.

    Returns:
        A dict (see ``DoseResponseResult.to_dict``)::

            {
              "effects": [ {relation_type, effect_type, point_estimate,
                            ci_lower, ci_upper, dose_amount, dose_unit,
                            increment_text, category_label, reference_label,
                            ...}, ... ],
              "n_per_unit": int, "n_categorical": int,
              "dose_metric": str|None, "dose_units": [str, ...],
              "n_dose_categories": int|None, "reference_category": str|None,
              "nonlinearity_reported": bool, "nonlinearity_shape": str|None,
              "p_nonlinearity": float|None,
            }
    """
    from rct_extractor._engine.core.doseresponse_extractor import (
        DoseResponseExtractor,
    )

    return DoseResponseExtractor().extract(text).to_dict()


def list_specialties() -> List[str]:
    """Return the list of supported disease specialties (full arm-level support)."""
    return list(SPECIALTIES)


def detect_specialty(text: str) -> Tuple[str, Optional[str], float]:
    """Auto-detect ``(specialty, subspecialty, confidence)`` from abstract text.

    Thin re-export of ``src.specialties.registry.detect_specialty`` so callers
    do not have to reach into the internal package layout.
    """
    from rct_extractor._engine.specialties.registry import detect_specialty as _detect

    return _detect(text)


@lru_cache(maxsize=None)
def _arm_module(specialty: str):
    """Import and cache the per-specialty arm-data module."""
    return importlib.import_module(f"rct_extractor._engine.specialties.{specialty}_arm_data")


@lru_cache(maxsize=1)
def _shared_extractor():
    """A single cached EnhancedExtractor instance (reused across calls)."""
    from rct_extractor._engine.core.enhanced_extractor_v3 import EnhancedExtractor

    return EnhancedExtractor()


@lru_cache(maxsize=1)
def _shared_diagnostic_extractor():
    """A single cached DiagnosticAccuracyExtractor instance (reused across calls)."""
    from rct_extractor._engine.core.diagnostic_accuracy_extractor import (
        DiagnosticAccuracyExtractor,
    )

    return DiagnosticAccuracyExtractor()


def _diagnostic_to_dict(d: Any) -> Dict[str, Any]:
    """Serialize a DiagnosticExtraction to a plain effect-style dict."""
    return {
        "type": d.measure_type.value,           # Sensitivity / Specificity / AUC / ...
        "measure": d.measure_type.value,
        "point_estimate": d.point_estimate,
        "ci_lower": d.ci_lower,
        "ci_upper": d.ci_upper,
        "ci_level": d.ci_level,
        "normalized_value": d.normalized_value,
        "is_percentage": d.is_percentage,
        "source_text": d.source_text,
        "char_start": d.char_start,
        "char_end": d.char_end,
        "warnings": list(d.warnings),
    }


# M1 kind-aware primary selection --------------------------------------------
import re as _re

# Cues that the study's PRIMARY outcome is a CONTINUOUS measure (a mean difference),
# and cues that it is a BINARY/time-to-event measure (a ratio). Scored only in the
# neighbourhood of a "primary outcome/endpoint" mention so a secondary outcome's
# wording does not decide the primary's kind.
_CONT_CUE = _re.compile(
    r"mean\s+(?:change|difference|reduction)|change\s+from\s+baseline|least[-\s]?squares?\s+mean"
    r"|\bLS\s*mean|change\s+in\s+(?:score|the\s+\w+\s+score|[\w\s]{0,20}?score|[\w\s]{0,20}?level"
    r"|weight|bmi|hba1c|blood\s+pressure|egfr|pain)|\bscore\b|\bscale\b|questionnaire",
    _re.IGNORECASE)
_RATIO_CUE = _re.compile(
    r"hazard\s+ratio|odds\s+ratio|risk\s+ratio|relative\s+risk|incidence|\bmortalit|\bdeath\b"
    r"|proportion\s+of|event\s+rate|number\s+needed|\bcure\b|\bresponse\s+rate|survival",
    _re.IGNORECASE)
_PRIMARY_RE = _re.compile(r"primary\s+(?:outcome|end\s?point|efficacy)", _re.IGNORECASE)


def _infer_primary_kind(text: str) -> Optional[str]:
    """Return 'diff' (continuous primary), 'ratio' (binary/TTE primary), or None.

    Looks only in a +-200-char window around each 'primary outcome/endpoint' mention
    and tallies continuous vs ratio cues; needs a clear majority to commit."""
    if not text:
        return None
    low = text.lower()
    cont = ratio = 0
    for m in _PRIMARY_RE.finditer(low):
        w = low[max(0, m.start() - 60):m.end() + 200]
        cont += len(_CONT_CUE.findall(w))
        ratio += len(_RATIO_CUE.findall(w))
    if cont >= 2 and cont > ratio * 2:
        return "diff"
    if ratio >= 2 and ratio > cont * 2:
        return "ratio"
    return None


def _kind_of(effect_type: Optional[str]) -> Optional[str]:
    et = str(effect_type or "").upper()
    if et in _RATIO_TYPES:
        return "ratio"
    if et in _DIFF_TYPES:
        return "diff"
    return None


def _best_diff_effect(effects: List[Dict[str, Any]], text: str):
    """Pick the best difference-type effect to promote to primary. Prefer one whose
    endpoint/source names a primary-outcome cue; else one with per-arm N (a complete
    table row); else the first difference-type effect."""
    diffs = [e for e in effects if isinstance(e, dict) and _kind_of(e.get("type")) == "diff"]
    if not diffs:
        return None
    named = [e for e in diffs
             if _PRIMARY_RE.search((e.get("endpoint") or "") + " " + (e.get("source_text") or ""))]
    if named:
        return named[0]
    with_n = [e for e in diffs if e.get("arm1_n") and e.get("arm2_n")]
    return (with_n or diffs)[0]


def _subspecialty_for(specialty: str, text: str) -> Tuple[Optional[str], Optional[float]]:
    """Run a forced specialty's own subspecialty detector, if it has one."""
    from rct_extractor._engine.specialties.registry import SPECIALTY_REGISTRY

    reg = SPECIALTY_REGISTRY.get(specialty, {})
    fn = reg.get("detection_function")
    if fn is None:
        return None, None
    try:
        result = fn(text)
        # Most detectors return (subspecialty, confidence); oncology returns
        # (subspecialty, subtype, confidence). Tolerate both shapes.
        if isinstance(result, tuple) and len(result) == 3:
            sub, _subtype, conf = result
        else:
            sub, conf = result
        return sub, conf
    except Exception:
        return None, None


def extract(
    text: str,
    specialty: str = "auto",
    *,
    with_effects: bool = True,
    with_arm_level: bool = True,
    with_diagnostic: bool = True,
    tables_xml: Optional[str] = None,
    consistency: bool = True,
) -> Dict[str, Any]:
    """Extract structured trial data from a single abstract / block of text.

    Args:
        text: Raw abstract or results text.
        specialty: One of :data:`SPECIALTIES`, or ``"auto"`` (default) to
            auto-detect via the registry.
        with_effects: Include precomputed effect estimates (HR/OR/RR/MD + CI).
        with_arm_level: Include arm-level extraction (poolable 2x2 + continuous).
        with_diagnostic: Include diagnostic-accuracy measures (sensitivity,
            specificity, PPV/NPV, LR+/LR-, DOR, AUC, accuracy, Youden) for
            diagnostic-test / prediction-model studies, which report no poolable
            HR/OR/RR/MD. Populated under ``diagnostic`` (empty list when none), so
            a DTA study is no longer a silent empty extraction.
        consistency: Screen extracted effects for internal consistency across
            ALL specialties — flags implausible (point estimate, CI, p, 2x2)
            combinations and applies the safe repairs (reversed-CI swap),
            attaching a ``consistency`` dict + ``needs_review`` to each effect.
            Never silently drops; hard failures are kept but flagged. For
            malaria the same screen also gates the augmented-effects pass.

    Returns:
        ``{specialty, subspecialty, confidence, effects, arm_level, diagnostic}``
        where ``effects`` is a list of effect dicts (``type``, ``effect_size``,
        ``ci_lower``, ``ci_upper``, ``endpoint``, ...), ``diagnostic`` is a list of
        diagnostic-accuracy measure dicts (``type``/``measure``, ``point_estimate``,
        ``ci_lower``, ``ci_upper``, ``normalized_value``, ...) present when
        ``with_diagnostic`` is set, and ``arm_level`` is the
        ``extract_arm_level`` dict (``poolable_2x2``, ``tables_2x2``,
        ``continuous``) or ``None`` when the detected specialty has no arm-level
        extractor.

    Raises:
        ValueError: if ``specialty`` is not ``"auto"`` and not a known specialty.
    """
    if specialty in (None, "", "auto"):
        spec, sub, conf = detect_specialty(text)
    else:
        spec = specialty.lower()
        if spec not in SPECIALTIES:
            raise ValueError(
                f"unknown specialty {specialty!r}; choose from {list(SPECIALTIES)} or 'auto'"
            )
        sub, conf = _subspecialty_for(spec, text)

    out: Dict[str, Any] = {
        "specialty": spec,
        "subspecialty": sub,
        "confidence": conf,
        "effects": [],
        "arm_level": None,
    }

    if with_effects:
        extractor = _shared_extractor()
        if spec == "malaria":
            from rct_extractor._engine.specialties.malaria_effects import extract_malaria_effects

            out["effects"] = extract_malaria_effects(
                extractor, text, consistency=consistency
            )
        else:
            from rct_extractor._engine.core.enhanced_extractor_v3 import to_dict

            effs = [to_dict(x) for x in extractor.extract(text)]
            if consistency:
                from rct_extractor._engine.specialties.internal_consistency import annotate
                # flag + safe-repair, keep everything (drop_hard=False) so the
                # caller decides on hard-flagged effects — never silently drop.
                effs = annotate(effs, drop_hard=False)
                # Source-grounding + multi-candidate disambiguation: catches the
                # internally-consistent-but-wrong errors (wrong estimand / wrong
                # comparison) that the numeric screen cannot. Flag-only.
                from rct_extractor._engine.specialties.source_grounding import annotate_grounding, order_effects
                effs = annotate_grounding(effs, text)
                # Put the primary-outcome effect first so effects[0] is the target
                # estimand (the INPULSIS class: a secondary HR was returned before
                # the primary mean difference).
                effs = order_effects(effs, text)
            out["effects"] = effs

    # Merge continuous mean differences recovered from result-table STRUCTURE, when
    # the caller supplies the JATS/HTML source. These recover primaries reported ONLY
    # in a results table (arm-level mean(SD)) -- the largest real-corpus recall gap --
    # which the prose extractor cannot see. Appended AFTER the prose effects so the
    # prose primary pick (effects[0]) is preserved by default; each is tagged
    # source='jats_table' and needs_review.
    if tables_xml:
        from rct_extractor._engine.core.jats_table_extractor import (
            extract_continuous_effects_from_xml,
        )
        out["effects"] = list(out["effects"]) + extract_continuous_effects_from_xml(tables_xml)

    # M1: kind-aware primary selection. When the paper's PRIMARY outcome is clearly a
    # continuous measure but the top-ranked effect is a ratio (the prose ranker cannot
    # promote a table-derived MD -- it has no text position), promote the best
    # difference-type effect to the front. Conservative: only fires on a confident
    # continuous inference AND a ratio currently at [0]; leaves ratio-primary and
    # ambiguous studies untouched.
    if with_effects and out["effects"] and _kind_of(out["effects"][0].get("type")) == "ratio":
        if _infer_primary_kind(text) == "diff":
            best = _best_diff_effect(out["effects"], text)
            if best is not None and best is not out["effects"][0]:
                out["effects"].remove(best)
                out["effects"].insert(0, best)

    # Emit the two fields that decide whether a pooled estimate is correct but were
    # previously never produced (audit gap 35):
    #   * direction  -- side of the null the point estimate falls on (deterministic).
    #   * is_primary -- the extractor's OWN primary-outcome pick. effects[0] is the
    #     target estimand after order_effects() promoted the primary outcome to the
    #     front (standard path) / the top-ranked effect otherwise. Surfacing it as an
    #     explicit flag lets it be scored against a gold primary-outcome label.
    for i, eff in enumerate(out["effects"]):
        if not isinstance(eff, dict):
            continue
        eff["direction"] = effect_direction(eff.get("type"), eff.get("effect_size"))
        eff["is_primary"] = (i == 0)

    if with_arm_level and spec in SPECIALTIES:
        out["arm_level"] = _arm_module(spec).extract_arm_level(text)

    if with_diagnostic:
        # Diagnostic-accuracy / prediction studies report Se/Sp/AUC etc., not a
        # comparative HR/OR/RR/MD. Surfacing them here means such a study is handled
        # instead of returning an empty `effects` list (a silent no-extraction).
        out["diagnostic"] = [
            _diagnostic_to_dict(x) for x in _shared_diagnostic_extractor().extract(text)
        ]

    return out


def extract_batch(
    records: List[Dict[str, Any]],
    specialty: str = "auto",
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    """Extract from many records.

    Args:
        records: list of ``{"text": ..., ...metadata...}`` dicts. Any extra keys
            (e.g. ``name``, ``nct``, ``pmid``, ``year``) are passed through into
            each result under ``"record"``.
        specialty: forced specialty or ``"auto"`` (per-record detection).
        kwargs: forwarded to :func:`extract`.

    Returns:
        One result dict per input record, each augmented with ``"record"``
        (the original input metadata, text omitted from the echo to keep it light).
    """
    results = []
    for r in records:
        text = r.get("text", "")
        res = extract(text, specialty=specialty, **kwargs)
        res["record"] = {k: v for k, v in r.items() if k != "text"}
        results.append(res)
    return results


def to_metakit_config(
    records: List[Dict[str, Any]],
    *,
    title: str,
    effect_measure: str,
    endpoint: Optional[str] = None,
    topics: Optional[List[str]] = None,
    **meta: Any,
) -> Dict[str, Any]:
    """Build a meta-starter-kit interchange config straight from trial records.

    This is the universal hand-off format consumed by RapidMeta, allmeta,
    Pairwise70 and the E156 capsules. Each record is ``{name, text, nct?, pmid?,
    year?}``. For ratio measures (OR/HR/RR) the bridge prefers raw 2x2 counts
    recovered from arm-level extraction; otherwise it falls back to precomputed
    effect+CI.

    Thin wrapper over ``src.bridges.meta_starter_kit.build_config_from_records``.
    """
    from rct_extractor._engine.bridges.meta_starter_kit import build_config_from_records

    return build_config_from_records(
        records,
        _shared_extractor(),
        title=title,
        effect_measure=effect_measure,
        endpoint=endpoint,
        topics=topics,
        **meta,
    )
