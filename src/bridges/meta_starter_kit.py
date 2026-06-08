"""
Meta-Starter-Kit bridge.

Turns extractor output into a meta-starter-kit review config (the universal
interchange format: github.com/mahmood726-cyber/meta-starter-kit). That config
is consumed by the kit's forest-plot/pooling build, by E156 capsules, and by the
other meta systems -- so this one bridge wires the cardiology/malaria extractor
into all of them via loose coupling (the JSON contract), keeping the kit itself
zero-dependency.

Topic routing:
- cardiology / general -> precomputed effect estimates (effect, ci_low, ci_high)
- malaria binary outcomes -> raw 2x2 (tE,tN,cE,cN) from arm-level extraction,
  which lets the kit compute the pooled effect from counts; falls back to
  precomputed effects when no 2x2 is available.

Config schema (meta-starter-kit/schema.json): {title, effect_measure in
OR/HR/RR/MD/SMD/RD, trials:[{name, nct?, pmid?, year?, (tE,tN,cE,cN) | (effect,ci_low,ci_high)}]}
"""
from __future__ import annotations
from typing import List, Dict, Optional, Any

# meta-starter-kit's supported effect measures (IRR/GMR/NNT/EFFICACY_PCT/RRR are
# not in the kit enum and are mapped/ skipped explicitly).
METAKIT_MEASURES = {"OR", "HR", "RR", "MD", "SMD", "RD"}
_RATIO_MEASURES = {"OR", "HR", "RR"}
_TYPE_TO_MEASURE = {"OR": "OR", "HR": "HR", "RR": "RR", "MD": "MD",
                    "SMD": "SMD", "ARD": "RD", "RD": "RD"}


def _meta_fields(nct=None, pmid=None, year=None):
    d = {}
    if nct:
        d["nct"] = str(nct)
    if pmid:
        d["pmid"] = str(pmid)
    if isinstance(year, int) or (isinstance(year, str) and year.isdigit()):
        d["year"] = int(year)
    return d


def effect_trial(name: str, effect: float, ci_low: float, ci_high: float,
                 nct=None, pmid=None, year=None) -> Dict[str, Any]:
    """A precomputed-effect trial row."""
    return {"name": name, **_meta_fields(nct, pmid, year),
            "effect": float(effect), "ci_low": float(ci_low), "ci_high": float(ci_high)}


def binary_trial(name: str, tE: int, tN: int, cE: int, cN: int,
                 nct=None, pmid=None, year=None) -> Dict[str, Any]:
    """A 2x2 (events/total per arm) trial row."""
    return {"name": name, **_meta_fields(nct, pmid, year),
            "tE": int(tE), "tN": int(tN), "cE": int(cE), "cN": int(cN)}


def table2x2_to_trial(table: Dict, name: str, **meta) -> Dict[str, Any]:
    """Convert an extract_arm_level() 2x2 table to a binary trial row."""
    return binary_trial(name, table["arm1"]["events"], table["arm1"]["total"],
                        table["arm2"]["events"], table["arm2"]["total"], **meta)


def effect_dict_to_trial(e: Dict, name: str, **meta) -> Optional[Dict[str, Any]]:
    """Convert an extract_malaria_effects()/to_dict() effect to a trial row.
    Returns None if it has no usable CI."""
    if e.get("ci_lower") is None or e.get("ci_upper") is None:
        return None
    return effect_trial(name, e["effect_size"], e["ci_lower"], e["ci_upper"], **meta)


def make_config(title: str, effect_measure: str, trials: List[Dict],
                intervention="", comparator="", condition="", outcome="",
                authors="") -> Dict[str, Any]:
    """Assemble + validate a meta-starter-kit config. Raises ValueError on a
    config the kit would reject (so problems surface here, not in the build)."""
    em = effect_measure.upper()
    if em not in METAKIT_MEASURES:
        raise ValueError(f"effect_measure {em!r} not in {sorted(METAKIT_MEASURES)}")
    good = []
    for t in trials:
        if "name" not in t:
            continue
        has_2x2 = all(k in t for k in ("tE", "tN", "cE", "cN"))
        has_eff = all(k in t for k in ("effect", "ci_low", "ci_high"))
        if has_2x2 and (em not in _RATIO_MEASURES):
            continue   # counts only make sense for ratio measures in the kit
        if has_2x2 or has_eff:
            good.append(t)
    if len(good) < 2:
        raise ValueError(f"need >=2 valid trials, got {len(good)}")
    cfg = {"title": title, "effect_measure": em, "trials": good}
    for k, v in (("intervention", intervention), ("comparator", comparator),
                 ("condition", condition), ("outcome", outcome), ("authors", authors)):
        if v:
            cfg[k] = v
    return cfg


def metakit_measure_for(effect_type: str) -> Optional[str]:
    """Map an extractor effect-type code to a kit effect_measure, or None."""
    return _TYPE_TO_MEASURE.get(str(effect_type).upper())


# All 17 disease specialties ship a <name>_arm_data module with extract_arm_level().
_ARM_SPECIALTIES = (
    "hiv", "malaria", "typhoid", "schistosomiasis", "sickle_cell", "cholera",
    "maternal_neonatal", "tuberculosis", "hepatitis", "meningitis", "pneumonia",
    "diarrhoeal", "malnutrition", "helminths", "hypertension", "cervical_cancer",
    "diabetes",
)
_ARM_CACHE: Dict[str, Any] = {}


def _arm_extractor_for(specialty: str):
    """Return the extract_arm_level() callable for a specialty, or None."""
    if specialty not in _ARM_SPECIALTIES:
        return None
    if specialty not in _ARM_CACHE:
        import importlib
        mod = importlib.import_module(f"src.specialties.{specialty}_arm_data")
        _ARM_CACHE[specialty] = getattr(mod, "extract_arm_level", None)
    return _ARM_CACHE[specialty]


def _effects_for(specialty: str, extractor, text: str) -> List[Dict]:
    """Precomputed effect dicts: malaria augmenter for malaria, core otherwise."""
    if specialty == "malaria":
        from src.specialties.malaria_effects import extract_malaria_effects
        return extract_malaria_effects(extractor, text)
    from src.core.enhanced_extractor_v3 import to_dict
    return [to_dict(x) for x in extractor.extract(text)]


def build_config_from_records(records: List[Dict], extractor, *, title: str,
                              effect_measure: str, endpoint: Optional[str] = None,
                              prefer_2x2: bool = True,
                              topics: Optional[List[str]] = None, **meta) -> Dict[str, Any]:
    """Topic-routed: build a config from a list of trial records.

    records: [{name, text, nct?, pmid?, year?}]. For each record, pick the effect
    that matches `effect_measure` (and `endpoint`, if given). For a ratio measure,
    prefer a poolable 2x2 (raw counts) over a precomputed ratio.

    topics: if given (e.g. ['malaria','cardiology']), only records whose
    auto-detected specialty is in the list are processed -- the extractor engages
    only for those topics and leaves everything else to the caller's own flow.

    Works for all 17 disease specialties: raw 2x2 counts are recovered via each
    specialty's <name>_arm_data.extract_arm_level(); precomputed effects come
    from the malaria augmenter for malaria text and from the core extractor
    otherwise.
    """
    from src.specialties.registry import detect_specialty

    em = effect_measure.upper()
    want = {t.lower() for t in topics} if topics else None
    trials = []
    for r in records:
        text = r.get("text", "")
        if not text:
            continue
        m = _meta_fields(r.get("nct"), r.get("pmid"), r.get("year"))
        spec = detect_specialty(text)[0]
        if want is not None and spec not in want:
            continue   # auto-detect: only engage for the requested topics
        row = None
        # ratio measure -> prefer raw 2x2 from this specialty's arm-level extractor
        if prefer_2x2 and em in _RATIO_MEASURES:
            arm = _arm_extractor_for(spec)
            if arm is not None:
                tables = arm(text).get("poolable_2x2", [])
                if endpoint:
                    tables = [t for t in tables if t["endpoint"] == endpoint] or tables
                if tables:
                    row = table2x2_to_trial(tables[0], r["name"], **m)
        if row is None:                              # fall back to precomputed effect
            for e in _effects_for(spec, extractor, text):
                if metakit_measure_for(e.get("type")) == em and (
                    endpoint is None or e.get("endpoint") == endpoint
                ):
                    row = effect_dict_to_trial(e, r["name"], **m)
                    if row:
                        break
        if row:
            trials.append(row)
    return make_config(title, em, trials, **meta)
