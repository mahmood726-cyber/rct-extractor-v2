"""
DTA extraction orchestrator.

Ties together entities + accuracy measures + 2x2 counts + derivation/consistency
into structured `DTAStudyRecord`s, plus a flat dict of everything found (useful
for accuracy evaluation against an independently-harvested gold set).

Pairing heuristic (mirrors the RCT engine's nearest-keyword arm/endpoint
pairing, kept deliberately simple and explicit):
  * Each explicit 2x2 table becomes its own record; its derived measures are
    cross-checked against the nearest text-stated measures.
  * If no explicit 2x2 exists but BOTH sensitivity and specificity are stated,
    one record is built from the stated pair (and a 2x2 is derived if group
    sizes are recoverable).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional

from . import counts, entities, measures
from .derive import check_consistency, derive_measures_from_2x2, merge_measures
from .models import DTAMeasure, DTAStudyRecord, TwoByTwo
from .registry import detect_domain

# recover group sizes for 2x2 derivation
_N_DISEASED = re.compile(
    r"(\d{1,6})\s+(?:were\s+)?(?:disease[d]?|cases?|positive(?:\s+(?:cases|patients))?)"
    r"\b(?:[^.]{0,30}reference)?",
    re.IGNORECASE,
)


def _nearest_measures(
    all_measures: List[DTAMeasure], center: int, window: int = 400
) -> Dict[str, DTAMeasure]:
    """Stated measures whose span sits within `window` chars of `center`."""
    near: Dict[str, DTAMeasure] = {}
    for m in all_measures:
        if abs(m.char_start - center) <= window and m.measure not in near:
            near[m.measure] = m
    return near


def extract(text: str, domain: str = "auto") -> dict:
    """Extract all DTA data from `text`.

    Returns a dict with keys:
      domain, entities, measures (list), two_by_two (list), records (list of
      DTAStudyRecord dicts), poolable (bool).
    """
    if not text or not text.strip():
        return {
            "domain": None,
            "entities": {"index_test": None, "reference_standard": None, "target_condition": None},
            "measures": [],
            "two_by_two": [],
            "records": [],
            "poolable": False,
        }

    # NFKC normalises typographic ligatures from PDF text (U+FB01 "fi" -> "fi"),
    # without which "speci<fi-ligature>city" is never matched as "specificity".
    text = unicodedata.normalize("NFKC", text)

    dom = detect_domain(text) if domain == "auto" else domain
    ents = entities.extract_entities(text)
    all_measures = measures.extract_measures(text)
    tables = counts.extract_two_by_two(text)

    records: List[DTAStudyRecord] = []

    if tables:
        for t2 in tables:
            stated = _nearest_measures(all_measures, t2.char_start)
            derived = derive_measures_from_2x2(t2)
            rec = DTAStudyRecord(
                index_test=ents["index_test"],
                reference_standard=ents["reference_standard"],
                target_condition=ents["target_condition"],
                two_by_two=t2,
                measures=merge_measures(stated, derived),
                consistency=check_consistency(t2, stated),
                poolable=True,
            )
            records.append(rec)
    else:
        by_name = {m.measure: m for m in all_measures}
        if "sensitivity" in by_name and "specificity" in by_name:
            se = by_name["sensitivity"]
            sp = by_name["specificity"]
            # try to derive a 2x2 if we can find group sizes
            t2: Optional[TwoByTwo] = None
            mdis = _N_DISEASED.search(text)
            stated_only = {m.measure: m for m in all_measures}
            rec = DTAStudyRecord(
                index_test=ents["index_test"],
                reference_standard=ents["reference_standard"],
                target_condition=ents["target_condition"],
                two_by_two=t2,
                measures=stated_only,
                poolable=True,
            )
            records.append(rec)

    poolable = any(r.poolable for r in records)

    return {
        "domain": dom,
        "entities": ents,
        "measures": [m.to_dict() for m in all_measures],
        "two_by_two": [t.to_dict() for t in tables],
        "records": [r.to_dict() for r in records],
        "poolable": poolable,
    }


class DTAExtractor:
    """Object wrapper for callers that prefer an instantiable extractor."""

    def __init__(self, domain: str = "auto"):
        self.domain = domain

    def extract(self, text: str) -> dict:
        return extract(text, domain=self.domain)
