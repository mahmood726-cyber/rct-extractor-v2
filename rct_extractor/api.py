"""
rct_extractor.api -- the clean public extraction API.

One function, ``extract(text, specialty=...)``, runs the full text->effects
pipeline for any of the 27 disease specialties (auto-detected or forced), plus
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

# The 27 disease specialties that ship a full text->arm-level extractor
# The 18 disease specialties that ship a full text->arm-level extractor
# (each has a src/specialties/<name>_arm_data.py with extract_arm_level()).
# Order is the canonical order used in the README and CLI help.
SPECIALTIES: Tuple[str, ...] = (
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
    "diabetes",
    "osteoporosis",
    "kidney_transplant",
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
    "oesophageal_cancer",
    "prostate_cancer",
    "ovarian_cancer",
    "pancreatic_cancer",
    "gastric_cancer",
    "hepatocellular_carcinoma",
    "melanoma",
    "leukaemia",
    "lymphoma",
    "head_neck_cancer",
    "bladder_cancer",
    "renal_cell_carcinoma",
    "dyslipidaemia",
    "venous_thromboembolism",
    "peripheral_artery_disease",
    "obesity",
    "thyroid",
)

__all__ = [
    "SPECIALTIES",
    "list_specialties",
    "detect_specialty",
    "extract",
    "extract_batch",
    "to_metakit_config",
]


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
    consistency: bool = True,
) -> Dict[str, Any]:
    """Extract structured trial data from a single abstract / block of text.

    Args:
        text: Raw abstract or results text.
        specialty: One of :data:`SPECIALTIES`, or ``"auto"`` (default) to
            auto-detect via the registry.
        with_effects: Include precomputed effect estimates (HR/OR/RR/MD + CI).
        with_arm_level: Include arm-level extraction (poolable 2x2 + continuous).
        consistency: For malaria, screen augmented effects for internal
            consistency (no effect on other specialties).

    Returns:
        ``{specialty, subspecialty, confidence, effects, arm_level}`` where
        ``effects`` is a list of effect dicts (``type``, ``effect_size``,
        ``ci_lower``, ``ci_upper``, ``endpoint``, ...) and ``arm_level`` is the
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

            out["effects"] = [to_dict(x) for x in extractor.extract(text)]

    if with_arm_level and spec in SPECIALTIES:
        out["arm_level"] = _arm_module(spec).extract_arm_level(text)

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
