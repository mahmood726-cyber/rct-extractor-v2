"""
Dose-Response Extractor
=======================

Extracts dose-response relationships from epidemiology / cohort / dose-response
meta-analysis text. This is a NEW extraction mode, additive to the RCT effect
extractor; it targets the data a dose-response meta-analysis actually pools:

  * PER-UNIT (trend / slope) estimates - the effect per fixed increment of an
    exposure, e.g. "RR 1.05 (95% CI 1.02-1.08) per 10 g/day increase".
  * CATEGORICAL dose-level estimates - the effect for a dose category versus a
    reference category, e.g. "highest vs lowest quintile RR 0.74 (0.65-0.85)".
  * Document-level dose-response METADATA - the exposure/dose metric and units,
    number of dose categories (tertiles=3 / quartiles=4 / quintiles=5 ...), the
    reference category, and any reported NONLINEARITY (P for nonlinearity,
    J-/U-/inverse shape, spline modelling).

Design mirrors DiagnosticAccuracyExtractor:
  * a registry (pattern_map) of compiled patterns keyed by relationship type,
  * a negative-context guard (planning / hypothetical / sample-size language),
  * plausibility verification (CI brackets the point, ratio positivity),
  * NO unbounded `[\\w\\s]+?` / `.+?` quantifiers over free text (ReDoS-safe):
    every "glue" gap between anchors is hard-bounded (`{0,N}`), and dose-unit
    alternations are explicit literals.

Spelling / Unicode traps handled (see CLAUDE.md + lessons.md):
  * British/American spelling: "fibre|fiber", "litre|liter", "gramme|gram",
    "haemoglobin" handled via `ha?emoglobin` (extra-vowel rule, NOT [ae]).
  * Greek question mark U+037E is normalised to ';' before matching.
  * en/em dash, figure dash, minus sign all accepted as range separators.
  * European decimal comma in CI pairs is NOT mis-split (a lookbehind keeps a
    "1,05" decimal from being read as a "1 to 05" range).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


# =============================================================================
# ENUMS
# =============================================================================
class DoseRelationType(Enum):
    """Kind of dose-response datum extracted."""
    PER_UNIT = "per_unit"        # effect per fixed increment (the trend/slope)
    CATEGORICAL = "categorical"  # effect for a dose category vs a reference


class DoseEffectType(Enum):
    """Ratio effect metric the dose-response estimate is expressed on."""
    RR = "RR"     # risk ratio / relative risk
    OR = "OR"     # odds ratio
    HR = "HR"     # hazard ratio
    IRR = "IRR"   # incidence-rate ratio


# =============================================================================
# DATACLASSES
# =============================================================================
@dataclass
class DoseResponseExtraction:
    """A single dose-response effect (per-unit or categorical)."""
    relation_type: DoseRelationType
    effect_type: DoseEffectType
    point_estimate: float
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    ci_level: float = 0.95

    # Dose / exposure descriptors
    dose_amount: Optional[float] = None   # e.g. 10 (for "per 10 g/day")
    dose_unit: Optional[str] = None       # e.g. "g/day", "mg", "SD", "serving/week"
    increment_text: Optional[str] = None  # verbatim "per 10 g/day" / "per 1-SD"
    category_label: Optional[str] = None  # e.g. "highest quintile", "Q4", ">30 g/day"
    reference_label: Optional[str] = None # e.g. "lowest quintile", "Q1"

    # Source tracking
    source_text: str = ""
    char_start: int = 0
    char_end: int = 0

    # Verification
    is_verified: bool = False
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relation_type": self.relation_type.value,
            "effect_type": self.effect_type.value,
            "point_estimate": self.point_estimate,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "ci_level": self.ci_level,
            "dose_amount": self.dose_amount,
            "dose_unit": self.dose_unit,
            "increment_text": self.increment_text,
            "category_label": self.category_label,
            "reference_label": self.reference_label,
            "source_text": self.source_text,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "is_verified": self.is_verified,
            "warnings": list(self.warnings),
        }


@dataclass
class DoseResponseResult:
    """Full dose-response extraction for a block of text."""
    effects: List[DoseResponseExtraction] = field(default_factory=list)
    dose_metric: Optional[str] = None        # best-effort exposure name
    dose_units: List[str] = field(default_factory=list)
    n_dose_categories: Optional[int] = None  # 3/4/5/10 ... from tertile/quartile...
    reference_category: Optional[str] = None
    nonlinearity_reported: bool = False
    nonlinearity_shape: Optional[str] = None  # "J-shaped" / "U-shaped" / "inverse" / "linear"
    p_nonlinearity: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effects": [e.to_dict() for e in self.effects],
            "n_per_unit": sum(1 for e in self.effects
                              if e.relation_type is DoseRelationType.PER_UNIT),
            "n_categorical": sum(1 for e in self.effects
                                 if e.relation_type is DoseRelationType.CATEGORICAL),
            "dose_metric": self.dose_metric,
            "dose_units": list(self.dose_units),
            "n_dose_categories": self.n_dose_categories,
            "reference_category": self.reference_category,
            "nonlinearity_reported": self.nonlinearity_reported,
            "nonlinearity_shape": self.nonlinearity_shape,
            "p_nonlinearity": self.p_nonlinearity,
        }


# =============================================================================
# SHARED REGEX FRAGMENTS (all bounded; ReDoS-safe)
# =============================================================================
_NUM = r"\d+(?:\.\d+)?"
# A 95% CI clause. The decimal-comma lookbehind `(?<!\d,\d)` is NOT usable here
# (variable-length); instead we require the range separator to be a dash/"to",
# OR a comma that is NOT flanked by single digits on both sides (so "1,05" stays
# one number while "1.02, 1.08" splits correctly). We accept dash and "to" as the
# primary separators and a comma only when followed by a space.
_CI = (
    r"(?:\(|\[)?\s*(?i:95\s*%?\s*(?:confidence\s+interval|CI|C\.I\.))?\s*[=:,]?\s*"
    r"(?P<lo>" + _NUM + r")\s*(?:-|‐|‑|‒|–|—|−|to|,\s)\s*"
    r"(?P<hi>" + _NUM + r")\s*(?:\)|\])?"
)
# Effect-type word -> canonical label. Spelled-out tried before abbreviations.
# Abbreviations are case-sensitive with a letter-boundary lookbehind so the word
# "or" can never be read as an odds ratio (mirrors the gold harvester).
_TYPE_MAP = [
    (r"incidence[- ]rate[- ]ratio", "IRR", False),
    (r"rate[- ]ratio", "IRR", False),
    (r"hazard[- ]ratio", "HR", False),
    (r"odds[- ]ratio", "OR", False),
    (r"risk[- ]ratio", "RR", False),
    (r"relative[- ]risk", "RR", False),
    (r"(?<![A-Za-z])a?HR\b", "HR", True),
    (r"(?<![A-Za-z])a?OR\b", "OR", True),
    (r"(?<![A-Za-z])a?RR\b", "RR", True),
    (r"(?<![A-Za-z])IRR\b", "IRR", True),
]

# Dose units (explicit literal alternation; British+American spellings).
# Order matters: longer / more specific units first so "g/day" wins over "g".
_DOSE_UNIT = (
    r"(?:"
    r"(?:m|µ|u|n|k)?g\s*/\s*(?:day|d|kg|week|wk|m2|m\^2|L|dL|mL)"  # mg/day, g/kg, µg/L...
    r"|(?:m|µ|u|n|k)?mol\s*/\s*(?:L|day|d)"
    r"|servings?\s*/\s*(?:day|d|week|wk)"
    r"|drinks?\s*/\s*(?:day|d|week|wk)"
    r"|cups?\s*/\s*(?:day|d|week|wk)"
    r"|portions?\s*/\s*(?:day|d|week|wk)"
    r"|times\s*/\s*(?:day|d|week|wk)"
    r"|hours?\s*/\s*(?:day|d|week|wk)|h\s*/\s*(?:day|d|wk|week)"
    r"|(?:m|µ|u|n|k)?g|(?:m|µ|u|n|k)?mol|mL|dL|L\b"
    r"|kcal(?:\s*/\s*day)?|MET[- ]?(?:hours?|h)?(?:\s*/\s*(?:week|wk|day|d))?"
    r"|kg\s*/\s*m\^?2|kg/m2|units?|IU|mmHg"
    r"|years?|cigarettes?(?:\s*/\s*day)?|pack[- ]?years?"
    r"|SD|standard\s+deviation|increment"
    # NOTE: quantile buckets (quartile/quintile/tertile/decile/category) are
    # deliberately NOT per-unit "units" -- "per/by quartile" denotes a
    # categorical grouping, not a fixed-increment slope, and is handled by the
    # categorical branch instead.
    r")"
)
# An "increment" phrase: "per 10 g/day", "per 1-SD", "for each 100 mg increase",
# "per additional serving/day". Bounded glue only.
_INCREMENT = (
    r"(?:per|for\s+(?:each|every)|each|every|with\s+(?:each|every)|by)\s+"
    r"(?:additional\s+|extra\s+|one\s+|a\s+|an\s+)?"
    r"(?P<amt>" + _NUM + r")?\s*[- ]?\s*"
    r"(?P<unit>" + _DOSE_UNIT + r")"
    r"(?:\s+(?:increase|increment|higher|rise|intake|consumption|exposure))?"
)


# =============================================================================
# EXTRACTOR
# =============================================================================
class DoseResponseExtractor:
    """Pattern-based dose-response extractor (no ML, deterministic)."""

    # --- PER-UNIT (trend/slope) patterns ------------------------------------
    # Two orderings: effect-then-increment and increment-then-effect.
    # Built dynamically per effect type in __init__ to keep type labels correct.

    # --- CATEGORICAL dose-level signal (order-independent) -------------------
    # Categorical dose-level estimates are recognised when, within the window
    # around an effect+CI, there is a DOSE-CATEGORY token together with either a
    # second (distinct) category token OR a comparison/reference cue. This handles
    # "highest vs lowest quintile", "compared with the lowest ..., the highest
    # ...", AND middle-reference designs ("compared with Q2, ... Q4 (HR ...)")
    # where the reference is not the bottom group.
    _HIGH_CAT = re.compile(
        r"\b(highest|top|upper|extreme|greatest|"
        r"Q[2-9]|quartile\s*[2-9]|quintile\s*[2-9]|tertile\s*[2-3]|decile\s*(?:[2-9]|10)|"
        r"(?:2|3|4|5|6|7|8|9|10)(?:st|nd|rd|th)\s+(?:quartile|quintile|tertile|decile))\b",
        re.IGNORECASE,
    )
    _LOW_REF = re.compile(
        r"\b(lowest|bottom|first\s+(?:quartile|quintile|tertile|decile|category)|"
        r"Q1\b|T1\b|reference|referent|ref\b|"
        r"quartile\s*1|quintile\s*1|tertile\s*1|decile\s*1|"
        r"1(?:st)?\s+(?:quartile|quintile|tertile|decile))\b",
        re.IGNORECASE,
    )
    # A comparison cue (with no explicit second category named) is also enough to
    # treat a category estimate as a dose-level comparison.
    _CMP_CUE = re.compile(
        r"\b(?:versus|vs\.?|compared\s+(?:with|to)|relative\s+to|reference|"
        r"referent|\bref\b)\b", re.IGNORECASE)
    # Any quantile/dose category token at all (used with a cue when no low/high
    # pair is present).
    _ANY_CAT = re.compile(
        r"\b(Q[1-9]|T[1-3]|quartile\s*[1-9]|quintile\s*[1-9]|tertile\s*[1-3]|"
        r"decile\s*(?:[1-9]|10)|highest|lowest|top|bottom|"
        r"(?:1|2|3|4|5|6|7|8|9|10)(?:st|nd|rd|th)\s+"
        r"(?:quartile|quintile|tertile|decile))\b", re.IGNORECASE)

    # --- Dose category count words ------------------------------------------
    _NCAT_MAP = [
        (r"\bdeciles?\b", 10),
        (r"\bquintiles?\b", 5),
        (r"\bquartiles?\b", 4),
        (r"\btertiles?\b", 3),
        (r"\btterciles?\b", 3),
        (r"\bthirds\b", 3),
    ]

    # --- Nonlinearity markers -----------------------------------------------
    _NONLIN_SHAPE = [
        (r"\bU[- ]?shaped\b", "U-shaped"),
        (r"\bJ[- ]?shaped\b", "J-shaped"),
        (r"\binverse[- ]?(?:U|J)[- ]?shaped\b", "inverse"),
        (r"\breverse[- ]?(?:U|J)[- ]?shaped\b", "inverse"),
        (r"\bnon[- ]?linear\b", "nonlinear"),
        (r"\bnonlinear\b", "nonlinear"),
        (r"\blinear\s+(?:dose[- ]response|trend|association|relationship)\b", "linear"),
    ]
    _PNONLIN = re.compile(
        r"P[\s\-]*(?:value)?[\s\-]*(?:for[\s\-]+)?non[\s\-]?linear(?:ity)?"
        r"\s*[=<>:]?\s*"
        r"(?P<p>" + _NUM + r"(?:\s*[×x]\s*10\s*[-−]?\s*\d+)?)",
        re.IGNORECASE,
    )

    # --- Reference-category markers -----------------------------------------
    _REFERENCE = re.compile(
        r"(?:(lowest|bottom|first)\s+(quartile|quintile|tertile|decile|category|group)"
        r"|(quartile|quintile|tertile|decile)\s*1\b"
        r"|\bQ1\b|\bT1\b"
        r"|\(?\s*(?:reference|referent|ref\.?)\s*\)?)",
        re.IGNORECASE,
    )

    # --- Dose-response self-identification (gate) ---------------------------
    _DR_CONTEXT = re.compile(
        r"dose[- ]response|dose[- ]dependent|exposure[- ]response|"
        r"per\s+(?:\d|one|additional|SD|standard\s+deviation|unit|increment)|"
        r"for\s+(?:each|every)\s+(?:\d|one|additional|SD|unit|increment)|"
        r"quartiles?|quintiles?|tertiles?|deciles?|"
        r"highest\s+(?:vs\.?|versus)\s+lowest|linear\s+trend|trend\s+test|"
        r"P\s*(?:[- ]?value)?\s*for\s+trend",
        re.IGNORECASE,
    )

    # --- Negative context (planning / hypothetical) -------------------------
    _NEGATIVE_CONTEXT = [
        r"(?:assuming|hypothetical|expected|required|target|planned)\s+"
        r"(?:risk|effect|ratio|reduction|increase)",
        r"(?:power|sample\s+size)\s+(?:calculation|analysis)",
        r"(?:we\s+aimed|protocol|will\s+be\s+(?:assessed|measured))",
    ]

    def __init__(self):
        self._dr_unit_re = re.compile(_DOSE_UNIT, re.IGNORECASE)
        self._increment_re = re.compile(_INCREMENT, re.IGNORECASE)
        self._negative = [re.compile(p, re.IGNORECASE) for p in self._NEGATIVE_CONTEXT]
        self._ncat = [(re.compile(p, re.IGNORECASE), n) for p, n in self._NCAT_MAP]
        self._nonlin_shape = [(re.compile(p, re.IGNORECASE), s)
                              for p, s in self._NONLIN_SHAPE]
        # Generic effect+CI matcher per type: "<type> ... <pt> ... <CI>".
        # Glue between anchors is hard-bounded (ReDoS-safe). Dose-response
        # CLASSIFICATION (per-unit vs categorical) is decided afterwards by
        # inspecting a bounded window around each match, which makes the engine
        # robust to word order ("RR per X was 1.05", "per X, RR 1.05",
        # "highest vs lowest RR 0.74", "compared with the lowest..., the highest
        # ... RR 0.74") without enumerating every permutation.
        self._effect_patterns = []   # list of (compiled, label)
        for type_re, label, cs in _TYPE_MAP:
            flags = 0 if cs else re.IGNORECASE
            # pt must sit IMMEDIATELY before the CI (tiny gap). This prevents the
            # point estimate from binding to an intervening dose amount such as
            # the "1000" in "RR for every 1000 mg increase was 1.00 (95% CI ...)"
            # -- the classic wrong-number-capture trap (see CLAUDE.md). The
            # type->pt glue stays wide so "RR per 100 mg/day was 1.05 (CI)" works.
            body = (type_re + r"[^.\n]{0,55}?(?P<pt>" + _NUM + r")"
                    + r"[^.\n]{0,10}?" + _CI)
            self._effect_patterns.append((re.compile(body, flags), label))

    # ----------------------------------------------------------------------
    # helpers
    # ----------------------------------------------------------------------
    @staticmethod
    def _normalize(text: str) -> str:
        """Normalise Unicode artefacts that break matching."""
        if not text:
            return ""
        return text.replace(";", ";")  # Greek question mark -> semicolon

    @staticmethod
    def _f(s: Optional[str]) -> Optional[float]:
        if s is None:
            return None
        try:
            return float(s)
        except ValueError:
            return None

    def _is_negative_context(self, text: str, start: int) -> bool:
        ctx = text[max(0, start - 100): start + 50]
        return any(p.search(ctx) for p in self._negative)

    @staticmethod
    def _plausible(pt: float, lo: Optional[float], hi: Optional[float]) -> bool:
        if pt is None or pt <= 0 or pt > 1000:
            return False
        if lo is not None and hi is not None:
            if not (lo <= hi):
                return False
            # CI should bracket point (small rounding slack)
            if not (lo - 0.05 <= pt <= hi + 0.05):
                return False
        return True

    def _unit_from_increment(self, inc_text: str):
        """Pull (amount, unit) out of a matched increment phrase."""
        m = self._increment_re.search(inc_text)
        if not m:
            return None, None
        amt = self._f(m.group("amt"))
        unit = m.group("unit")
        if unit:
            unit = re.sub(r"\s+", "", unit).strip()
        return amt, unit

    # ----------------------------------------------------------------------
    # extraction
    # ----------------------------------------------------------------------
    def extract(self, text: str) -> DoseResponseResult:
        text = self._normalize(text)
        result = DoseResponseResult()
        if not text or len(text) < 20:
            return result

        seen = set()  # (round(pt), round(lo), round(hi)) -> dedup numeric tuple
        # Window of context to inspect on each side of an effect+CI match to
        # classify it as dose-response (per-unit increment or dose category).
        WIN = 110

        for pat, label in self._effect_patterns:
            for m in pat.finditer(text):
                if self._is_negative_context(text, m.start()):
                    continue
                pt = self._f(m.group("pt"))
                lo = self._f(m.groupdict().get("lo"))
                hi = self._f(m.groupdict().get("hi"))
                if not self._plausible(pt, lo, hi):
                    continue

                win = text[max(0, m.start() - WIN): m.end() + WIN]
                inc_m = self._increment_re.search(win)
                high_m = self._HIGH_CAT.search(win)
                low_m = self._LOW_REF.search(win)
                any_cat = self._ANY_CAT.search(win)
                cmp_cue = self._CMP_CUE.search(win)

                # Decide relationship type. Per-unit (explicit "per/each X unit")
                # takes precedence; otherwise a dose-category signal makes it a
                # categorical dose-level estimate -- either a high+low pair, or
                # any quantile token paired with a comparison/reference cue
                # (covers middle-reference designs). Anything else is NOT a
                # dose-response datum and is skipped (this engine emits only
                # dose-response effects, never every ratio in the paper).
                cat_label = ref_label = None
                if inc_m is not None:
                    relation = DoseRelationType.PER_UNIT
                elif high_m is not None and low_m is not None:
                    relation = DoseRelationType.CATEGORICAL
                    cat_label = high_m.group(0)
                    ref_label = low_m.group(0)
                elif any_cat is not None and cmp_cue is not None:
                    relation = DoseRelationType.CATEGORICAL
                    cat_label = any_cat.group(0)
                    ref_label = cmp_cue.group(0)
                else:
                    continue

                key = (round(pt, 3), round(lo or 0, 3), round(hi or 0, 3))
                if key in seen:
                    continue
                seen.add(key)

                ext = DoseResponseExtraction(
                    relation_type=relation,
                    effect_type=DoseEffectType(label),
                    point_estimate=pt, ci_lower=lo, ci_upper=hi,
                    source_text=win.strip()[:240],
                    char_start=m.start(), char_end=m.end(),
                )
                if relation is DoseRelationType.PER_UNIT:
                    amt, unit = self._unit_from_increment(inc_m.group(0))
                    ext.dose_amount = amt
                    ext.dose_unit = unit
                    ext.increment_text = re.sub(r"\s+", " ", inc_m.group(0)).strip()
                else:
                    ext.category_label = (re.sub(r"\s+", " ", cat_label).strip()
                                          if cat_label else None)
                    ext.reference_label = (re.sub(r"\s+", " ", ref_label).strip()
                                           if ref_label else None)
                self._verify(ext)
                result.effects.append(ext)

        # --- Document-level metadata ---
        self._populate_metadata(text, result)
        return result

    def _populate_metadata(self, text: str, result: DoseResponseResult):
        # dose units actually seen
        units = []
        for m in self._dr_unit_re.finditer(text):
            u = re.sub(r"\s+", "", m.group(0))
            if u and u.lower() not in ("category", "increment") and u not in units:
                units.append(u)
            if len(units) >= 12:
                break
        result.dose_units = units

        # number of dose categories (largest named partition wins)
        best_n = None
        for rx, n in self._ncat:
            if rx.search(text):
                best_n = max(best_n or 0, n)
        # explicit "X dose categories/groups/levels"
        m = re.search(r"(\d{1,2})\s+dose\s+(?:categor|group|level)", text, re.IGNORECASE)
        if m:
            best_n = max(best_n or 0, int(m.group(1)))
        result.n_dose_categories = best_n

        # reference category
        rm = self._REFERENCE.search(text)
        if rm:
            result.reference_category = re.sub(r"\s+", " ", rm.group(0)).strip()

        # nonlinearity
        for rx, shape in self._nonlin_shape:
            if rx.search(text):
                result.nonlinearity_reported = True
                result.nonlinearity_shape = shape
                break
        pm = self._PNONLIN.search(text)
        if pm:
            result.nonlinearity_reported = True
            pval = self._parse_p(pm.group("p"))
            result.p_nonlinearity = pval

        # best-effort dose metric: nearest exposure noun before "intake/consumption"
        result.dose_metric = self._guess_metric(text)

    @staticmethod
    def _parse_p(s: str) -> Optional[float]:
        s = s.strip().replace(" ", "")
        m = re.match(r"^(" + _NUM + r")[×x]10[-−]?(\d+)$", s)
        if m:
            try:
                return float(m.group(1)) * (10 ** -int(m.group(2)))
            except ValueError:
                return None
        try:
            return float(s)
        except ValueError:
            return None

    # Up to three words immediately preceding an exposure noun. Bounded; no
    # catastrophic backtracking (fixed {0,2} repetition of a word token).
    _METRIC_RE = re.compile(
        r"\b([A-Za-z][\w-]+(?:\s+[A-Za-z][\w-]+){0,2})\s+"
        r"(?:intake|consumption|exposure|concentration)s?\b",
        re.IGNORECASE,
    )
    _METRIC_FILLER = {
        "of", "in", "the", "a", "an", "with", "for", "higher", "high", "increased",
        "increase", "increasing", "day", "week", "each", "per", "additional",
        "greater", "lower", "level", "levels", "total", "daily", "dietary",
        "habitual", "and", "or", "to", "was", "were", "is", "are", "across",
    }

    def _guess_metric(self, text: str) -> Optional[str]:
        m = self._METRIC_RE.search(text)
        if not m:
            return None
        tokens = re.sub(r"\s+", " ", m.group(1)).strip().split()
        # keep the nearest (rightmost) non-filler tokens, up to 2
        kept = []
        for tok in reversed(tokens):
            if tok.lower() in self._METRIC_FILLER:
                break
            kept.insert(0, tok)
            if len(kept) >= 2:
                break
        return " ".join(kept) if kept else None

    def _verify(self, ext: DoseResponseExtraction):
        warnings = []
        if ext.ci_lower is not None and ext.ci_upper is not None:
            if not (ext.ci_lower <= ext.point_estimate <= ext.ci_upper):
                # allow rounding slack already applied in _plausible; flag here
                if not (ext.ci_lower - 0.05 <= ext.point_estimate <= ext.ci_upper + 0.05):
                    warnings.append("point not within CI")
            if ext.ci_lower > ext.ci_upper:
                warnings.append("CI bounds reversed")
        if ext.point_estimate <= 0:
            warnings.append("non-positive ratio")
        ext.warnings = warnings
        ext.is_verified = len(warnings) == 0


# =============================================================================
# CONVENIENCE
# =============================================================================
def extract_dose_response(text: str) -> DoseResponseResult:
    """Extract dose-response data from a block of text."""
    return DoseResponseExtractor().extract(text)


def get_dose_response_field_count() -> int:
    """Number of distinct dose-response fields the engine populates."""
    # effects(list) + 6 document-level fields populated by _populate_metadata
    return len(DoseResponseResult().to_dict())
