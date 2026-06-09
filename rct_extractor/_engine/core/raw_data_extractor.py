"""
Raw Data Extractor — Find two-group raw statistics in PDF text.

Extracts per-arm data that can be passed to effect_calculator:
- Binary: events/N or events (percent) per group
- Continuous: mean (SD) or mean +/- SD per group, with sample sizes

This is a fallback for when the main regex extractor finds no pre-computed
effect estimates. The extracted raw data is then fed to effect_calculator
to compute OR, RR, MD, SMD, etc.

Design principle: high precision, moderate recall. It's better to miss
some extractable data than to extract wrong numbers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class ArmData:
    """Raw statistics for one treatment arm."""
    label: str = ""          # e.g., "treatment", "control", "placebo"
    n: Optional[int] = None
    # Binary
    events: Optional[int] = None
    percentage: Optional[float] = None
    # Continuous
    mean: Optional[float] = None
    sd: Optional[float] = None
    se: Optional[float] = None


@dataclass
class RawDataExtraction:
    """Extracted raw data from two groups."""
    arm1: ArmData = field(default_factory=ArmData)
    arm2: ArmData = field(default_factory=ArmData)
    data_type: str = ""      # "binary" or "continuous"
    outcome_name: str = ""
    source_text: str = ""
    confidence: float = 0.0  # 0-1 extraction confidence

    def to_raw_data_dict(self) -> Optional[dict]:
        """Convert to the raw_data dict format used by effect_calculator."""
        if self.data_type == "binary":
            if (self.arm1.events is not None and self.arm1.n is not None and
                    self.arm2.events is not None and self.arm2.n is not None):
                return {
                    "intervention_events": self.arm1.events,
                    "intervention_n": self.arm1.n,
                    "control_events": self.arm2.events,
                    "control_n": self.arm2.n,
                }
        elif self.data_type == "continuous":
            if (self.arm1.mean is not None and self.arm1.sd is not None and
                    self.arm1.n is not None and
                    self.arm2.mean is not None and self.arm2.sd is not None and
                    self.arm2.n is not None):
                return {
                    "intervention_mean": self.arm1.mean,
                    "intervention_sd": self.arm1.sd,
                    "intervention_n": self.arm1.n,
                    "control_mean": self.arm2.mean,
                    "control_sd": self.arm2.sd,
                    "control_n": self.arm2.n,
                }
        return None


# ============================================================
# CONTINUOUS DATA PATTERNS
# ============================================================

# mean (SD) or mean (sd) or mean(SD)
_MEAN_SD_PATTERN = re.compile(
    r'(-?\d+\.?\d*)\s*\(\s*(\d+\.?\d*)\s*\)',
)

# mean ± SD or mean +/- SD
_MEAN_PM_SD_PATTERN = re.compile(
    r'(-?\d+\.?\d*)\s*(?:\+/-|\+/?-|\u00b1)\s*(\d+\.?\d*)',
    re.IGNORECASE,
)

# n = 30 or N = 30 or (n=30)
_SAMPLE_SIZE_PATTERN = re.compile(
    r'\b[nN]\s*(?:[=:\u00bc]\s*)?(\d{1,4})\b',
)

# Group header with n: "Treatment (n=30)" or "Control (N=25)"
_GROUP_N_PATTERN = re.compile(
    r'([\w\s-]{2,40}?)\s*\(\s*[nN]\s*(?:[=:\u00bc]\s*)?(\d{1,4})\s*\)',
)


def _normalize_extraction_text(text: str) -> str:
    """Normalize common PDF/OCR artifacts before regex extraction."""
    if not text:
        return ""

    normalized = text
    normalized = normalized.replace("\u00a0", " ")
    normalized = re.sub(r'[\u2000-\u200f\u202f\u2060]+', ' ', normalized)

    # PDF/OCR artifacts for +/- symbols.
    normalized = re.sub(r'\(cid:\d+\)', ' +/- ', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'cid\s*:?\s*\d+', ' +/- ', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'(?<=\d)[\x00-\x08\x0b\x0c\x0e-\x1f]+(?=\d)', ' +/- ', normalized)
    normalized = normalized.replace('\u00b1', ' +/- ')

    # Common OCR punctuation fixes.
    normalized = re.sub(r'[\u2212\u2012\u2013\u2014\u2015]', '-', normalized)
    normalized = re.sub(r'(?<=\d)[\u00b7\u2022](?=\d)', '.', normalized)
    normalized = re.sub(r'(?<=\d),(?=\d{1,2}\b)', '.', normalized)
    normalized = re.sub(r'[^\S\r\n]+', ' ', normalized)
    return normalized


def _coerce_percentage(value: float) -> Optional[float]:
    """Coerce OCR-corrupted percentages (e.g., 846 -> 84.6)."""
    if value <= 0:
        return None
    if value <= 100:
        return value
    if value <= 1000:
        candidate = value / 10.0
        if candidate <= 100:
            return candidate
    if value <= 10000:
        candidate = value / 100.0
        if candidate <= 100:
            return candidate
    return None


def _extract_context_sample_sizes(context: str) -> List[int]:
    """Extract likely sample sizes from nearby text context."""
    sample_sizes: List[int] = []
    for value in _SAMPLE_SIZE_PATTERN.findall(context):
        sample_sizes.append(int(value))
    for _, value in _GROUP_N_PATTERN.findall(context):
        sample_sizes.append(int(value))

    # Keep order while de-duplicating.
    unique: List[int] = []
    seen = set()
    for n in sample_sizes:
        if n in seen:
            continue
        seen.add(n)
        unique.append(n)
    return unique


def extract_continuous_two_group(text: str) -> List[RawDataExtraction]:
    """
    Extract two-group continuous data: mean(SD) pairs with sample sizes.

    Looks for patterns like:
    - "Treatment: 45.3 (19.9), n=22; Control: 58.5 (18.6), n=20"
    - "Group A 49.1 (5.0) n=22 vs Group B 48.1 (5.7) n=26"
    - Table rows: "Outcome  45.3 (19.9)  58.5 (18.6)"
    """
    text = _normalize_extraction_text(text)
    results: List[RawDataExtraction] = []
    seen = set()

    def _append_continuous(
        mean1: float,
        sd1: float,
        mean2: float,
        sd2: float,
        source_text: str,
        line_pos: int,
        with_n_conf: float,
        without_n_conf: float,
        explicit_n: Optional[Tuple[int, int]] = None,
    ) -> bool:
        if sd1 <= 0 or sd2 <= 0:
            return False
        if abs(mean1) > 10000 or abs(mean2) > 10000:
            return False

        sd_ratio = max(sd1, sd2) / max(min(sd1, sd2), 1e-9)
        if sd_ratio >= 20:
            return False

        context = text[max(0, line_pos - 600):line_pos + len(source_text) + 250]
        n_matches = _extract_context_sample_sizes(context)
        arm1 = ArmData(mean=mean1, sd=sd1)
        arm2 = ArmData(mean=mean2, sd=sd2)
        if explicit_n is not None:
            n1, n2 = explicit_n
            if n1 < 5 or n2 < 5:
                return False
            arm1.n = int(n1)
            arm2.n = int(n2)
            confidence = with_n_conf
        elif len(n_matches) >= 2:
            arm1.n = int(n_matches[0])
            arm2.n = int(n_matches[1])
            confidence = with_n_conf
        else:
            confidence = without_n_conf

        key = (
            round(mean1, 4),
            round(sd1, 4),
            round(mean2, 4),
            round(sd2, 4),
            arm1.n,
            arm2.n,
        )
        if key in seen:
            return False
        seen.add(key)

        results.append(
            RawDataExtraction(
                arm1=arm1,
                arm2=arm2,
                data_type="continuous",
                source_text=source_text[:200],
                confidence=confidence,
            )
        )
        return True

    def _is_integer_like(value: float) -> bool:
        return abs(value - round(value)) < 1e-6

    # Strategy 1: Inline "X (SD) vs Y (SD)" comparisons.
    vs_pattern = re.compile(
        r'(-?\d+\.?\d*)\s*'
        r'(?:\(\s*(\d+\.?\d*)\s*\)|(?:\u00b1|\+/-|\+/?-)\s*(\d+\.?\d*))'
        r'\s*(?:vs\.?|versus|compared\s+(?:to|with)|and)\s*'
        r'(-?\d+\.?\d*)\s*'
        r'(?:\(\s*(\d+\.?\d*)\s*\)|(?:\u00b1|\+/-|\+/?-)\s*(\d+\.?\d*))',
        re.IGNORECASE
    )
    for m in vs_pattern.finditer(text):
        _append_continuous(
            mean1=float(m.group(1)),
            sd1=float(m.group(2) or m.group(3)),
            mean2=float(m.group(4)),
            sd2=float(m.group(5) or m.group(6)),
            source_text=m.group(0),
            line_pos=m.start(),
            with_n_conf=0.7,
            without_n_conf=0.4,
        )

    # Strategy 2: Table-like rows with two mean(SD) or mean±SD values.
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        line_pos = text.find(line)
        if line_pos < 0:
            line_pos = 0

        ms_paren = list(_MEAN_SD_PATTERN.finditer(stripped))
        if len(ms_paren) >= 2:
            first = ms_paren[0]
            second = ms_paren[1]
            _append_continuous(
                mean1=float(first.group(1)),
                sd1=float(first.group(2)),
                mean2=float(second.group(1)),
                sd2=float(second.group(2)),
                source_text=stripped,
                line_pos=line_pos,
                with_n_conf=0.55,
                without_n_conf=0.35,
            )

        ms_pm = list(_MEAN_PM_SD_PATTERN.finditer(stripped))
        if len(ms_pm) >= 2:
            first = ms_pm[0]
            second = ms_pm[1]
            _append_continuous(
                mean1=float(first.group(1)),
                sd1=float(first.group(2)),
                mean2=float(second.group(1)),
                sd2=float(second.group(2)),
                source_text=stripped,
                line_pos=line_pos,
                with_n_conf=0.5,
                without_n_conf=0.3,
            )

        # Strategy 3: Explicit table rows with inline N values.
        # Common layouts:
        #   mean sd n mean sd n
        #   n mean sd n mean sd
        token_texts = re.findall(r'-?\d+\.?\d*', stripped)
        num_tokens = [float(x) for x in token_texts]
        structured_hit = False
        if len(num_tokens) >= 6:
            for i in range(0, len(num_tokens) - 5):
                t = num_tokens[i:i + 6]
                s = token_texts[i:i + 6]

                # Layout A: mean1 sd1 n1 mean2 sd2 n2
                n1_a = t[2]
                n2_a = t[5]
                if (
                    _is_integer_like(n1_a)
                    and _is_integer_like(n2_a)
                    and "." not in s[2]
                    and "." not in s[5]
                    and 5 <= int(round(n1_a)) <= 5000
                    and 5 <= int(round(n2_a)) <= 5000
                    and 0 < t[1] <= 250
                    and 0 < t[4] <= 250
                ):
                    added = _append_continuous(
                        mean1=t[0],
                        sd1=t[1],
                        mean2=t[3],
                        sd2=t[4],
                        source_text=stripped,
                        line_pos=line_pos,
                        with_n_conf=0.65,
                        without_n_conf=0.65,
                        explicit_n=(int(round(n1_a)), int(round(n2_a))),
                    )
                    structured_hit = structured_hit or added

                # Layout B: n1 mean1 sd1 n2 mean2 sd2
                n1_b = t[0]
                n2_b = t[3]
                if (
                    _is_integer_like(n1_b)
                    and _is_integer_like(n2_b)
                    and "." not in s[0]
                    and "." not in s[3]
                    and 5 <= int(round(n1_b)) <= 5000
                    and 5 <= int(round(n2_b)) <= 5000
                    and 0 < t[2] <= 250
                    and 0 < t[5] <= 250
                ):
                    added = _append_continuous(
                        mean1=t[1],
                        sd1=t[2],
                        mean2=t[4],
                        sd2=t[5],
                        source_text=stripped,
                        line_pos=line_pos,
                        with_n_conf=0.65,
                        without_n_conf=0.65,
                        explicit_n=(int(round(n1_b)), int(round(n2_b))),
                    )
                    structured_hit = structured_hit or added

        # Strategy 4: split-column rows with 4-6 numeric tokens.
        # Example: "ANB 5.65 1.28 5.25 0.99"
        # Skip this fallback when an inline-N structured parse already succeeded.
        if not structured_hit and 4 <= len(num_tokens) <= 6:
            for i in range(0, len(num_tokens) - 3):
                mean1, sd1, mean2, sd2 = num_tokens[i:i + 4]

                # Reject likely n-columns misread as means in short table rows.
                if len(num_tokens) >= 5 and (
                    (5 <= mean2 <= 5000 and _is_integer_like(mean2))
                    or (5 <= sd2 <= 5000 and _is_integer_like(sd2))
                ):
                    continue

                if sd1 <= 0 or sd2 <= 0:
                    continue
                if sd1 > 200 or sd2 > 200:
                    continue
                if abs(mean1) > 1000 or abs(mean2) > 1000:
                    continue
                _append_continuous(
                    mean1=mean1,
                    sd1=sd1,
                    mean2=mean2,
                    sd2=sd2,
                    source_text=stripped,
                    line_pos=line_pos,
                    with_n_conf=0.45,
                    without_n_conf=0.25,
                )
                break

    return results


# ============================================================
# BINARY DATA PATTERNS
# ============================================================

# events/N (percent) pattern
_EVENTS_N_PCT_PATTERN = re.compile(
    r'(\d+)\s*/\s*(\d+)\s*\(\s*(\d+\.?\d*)\s*%?\s*\)',
)

# events (percent) without denominator
_EVENTS_PCT_PATTERN = re.compile(
    r'(\d+)\s*\(\s*(\d+\.?\d*)\s*%\s*\)',
)

# events (percent) allowing missing percent symbol (common in PDF tables)
_EVENTS_PARENS_ANY_PCT = re.compile(
    r'(\d+)\s*\(\s*(\d+\.?\d*)\s*%?\s*\)',
)

# "X of Y patients" or "X out of Y"
_EVENTS_OF_N_PATTERN = re.compile(
    r'(\d+)\s+(?:of|out\s+of)\s+(\d+)\s*(?:patients?|subjects?|participants?|women|men|children)',
    re.IGNORECASE,
)

# v6.2: "(X/N)" format without percentage — common in results text
_EVENTS_SLASH_N_PAREN = re.compile(
    r'\(\s*(\d+)\s*/\s*(\d+)\s*\)',
)

# v6.2: "X/N" bare format (no parens, no percentage)
_EVENTS_SLASH_N_BARE = re.compile(
    r'(?<!\d[.])(\d+)\s*/\s*(\d+)(?!\s*%)',
)

# percentage vs percentage comparisons (with optional percent signs)
_PCT_VS_PCT_PATTERN = re.compile(
    r'(\d{1,3}(?:\.\d+)?)\s*%?\s*'
    r'(?:vs\.?|versus|compared\s+(?:to|with)|and)\s*'
    r'(\d{1,3}(?:\.\d+)?)\s*%?',
    re.IGNORECASE,
)

# percentage tokens for table-like percentage rows
_PCT_TOKEN_PATTERN = re.compile(r'(\d{1,3}(?:\.\d+)?)\s*%')


def extract_binary_two_group(text: str) -> List[RawDataExtraction]:
    """
    Extract two-group binary data: events/N or events(%) comparisons.

    Looks for patterns like:
    - "Treatment 15/56 (26.8%) vs Placebo 18/57 (31.6%)"
    - "7 (6.8%) in group A and 11 (10.3%) in group B"
    - "mesh 7/40 vs AC 17/39"
    """
    text = _normalize_extraction_text(text)
    results: List[RawDataExtraction] = []
    seen_pairs = set()

    def _append_binary(
        e1: int,
        n1: int,
        e2: int,
        n2: int,
        source_text: str,
        confidence: float,
        pct1: Optional[float] = None,
        pct2: Optional[float] = None,
    ) -> None:
        if n1 <= 0 or n2 <= 0:
            return
        if e1 < 0 or e2 < 0 or e1 > n1 or e2 > n2:
            return
        key = (e1, n1, e2, n2)
        if key in seen_pairs:
            return
        seen_pairs.add(key)
        results.append(
            RawDataExtraction(
                arm1=ArmData(events=e1, n=n1, percentage=pct1),
                arm2=ArmData(events=e2, n=n2, percentage=pct2),
                data_type="binary",
                source_text=source_text[:200],
                confidence=confidence,
            )
        )

    # Strategy 1: "X/N (%) vs Y/N (%)" inline comparisons
    vs_binary = re.compile(
        r'(\d+)\s*/\s*(\d+)\s*(?:\(\s*\d+\.?\d*\s*%?\s*\))?\s*'
        r'(?:vs\.?|versus|compared\s+(?:to|with)|and)\s*'
        r'(\d+)\s*/\s*(\d+)\s*(?:\(\s*\d+\.?\d*\s*%?\s*\))?',
        re.IGNORECASE
    )
    for m in vs_binary.finditer(text):
        e1, n1, e2, n2 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        _append_binary(e1, n1, e2, n2, source_text=m.group(0), confidence=0.8)

    # Strategy 2: "X patients (Y%) in group A and Z patients (W%) in group B"
    group_pct = re.compile(
        r'(\d+)\s*(?:patients?|subjects?)?\s*\(\s*(\d+\.?\d*)\s*%\s*\)\s*'
        r'(?:in\s+(?:the\s+)?)?(?:group\s+)?\w+\s*'
        r'(?:and|vs\.?|versus|compared)\s*'
        r'(\d+)\s*(?:patients?|subjects?)?\s*\(\s*(\d+\.?\d*)\s*%\s*\)',
        re.IGNORECASE
    )
    for m in group_pct.finditer(text):
        e1 = int(m.group(1))
        e2 = int(m.group(3))
        pct1 = _coerce_percentage(float(m.group(2)))
        pct2 = _coerce_percentage(float(m.group(4)))
        # Derive N from events and percentage
        if pct1 is not None and pct2 is not None:
            n1 = round(e1 / (pct1 / 100.0))
            n2 = round(e2 / (pct2 / 100.0))
            _append_binary(e1, n1, e2, n2, source_text=m.group(0), confidence=0.7, pct1=pct1, pct2=pct2)

    # Strategy 3: Table rows with two events/N values (with percentage)
    for line in text.split('\n'):
        ms = list(_EVENTS_N_PCT_PATTERN.finditer(line))
        if len(ms) == 2:
            e1, n1 = int(ms[0].group(1)), int(ms[0].group(2))
            e2, n2 = int(ms[1].group(1)), int(ms[1].group(2))
            _append_binary(e1, n1, e2, n2, source_text=line.strip(), confidence=0.6)

    # Strategy 4: Two table-style events(percent) values where '%' may be omitted.
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        line_pos = text.find(line)
        if line_pos < 0:
            line_pos = 0
        context = text[max(0, line_pos - 250):line_pos + len(line) + 250]
        context_ns = _extract_context_sample_sizes(context)
        matches = list(_EVENTS_PARENS_ANY_PCT.finditer(stripped))
        if len(matches) < 2:
            continue
        for i in range(len(matches) - 1):
            m1 = matches[i]
            m2 = matches[i + 1]
            e1 = int(m1.group(1))
            e2 = int(m2.group(1))
            pct1 = _coerce_percentage(float(m1.group(2)))
            pct2 = _coerce_percentage(float(m2.group(2)))
            if pct1 is None or pct2 is None:
                continue
            n1 = round(e1 / (pct1 / 100.0))
            n2 = round(e2 / (pct2 / 100.0))
            if (
                n1 < 5
                or n2 < 5
                or n1 > 3000
                or n2 > 3000
                or e1 > n1
                or e2 > n2
                or abs((e1 / n1) * 100.0 - pct1) > 1.5
                or abs((e2 / n2) * 100.0 - pct2) > 1.5
            ):
                # OCR can distort percentages; if context has sample sizes, try those as fallback.
                if len(context_ns) >= 2:
                    candidate_pairs = [
                        (int(context_ns[0]), int(context_ns[1])),
                        (int(context_ns[1]), int(context_ns[0])),
                    ]
                    chosen = None
                    best_err = None
                    for cand_n1, cand_n2 in candidate_pairs:
                        if cand_n1 < 5 or cand_n2 < 5 or e1 > cand_n1 or e2 > cand_n2:
                            continue
                        err = abs((e1 / cand_n1) * 100.0 - pct1) + abs((e2 / cand_n2) * 100.0 - pct2)
                        if best_err is None or err < best_err:
                            best_err = err
                            chosen = (cand_n1, cand_n2)
                    if chosen is not None and best_err is not None and best_err <= 6.0:
                        _append_binary(
                            e1,
                            chosen[0],
                            e2,
                            chosen[1],
                            source_text=stripped,
                            confidence=0.42,
                            pct1=pct1,
                            pct2=pct2,
                        )
                continue

            _append_binary(e1, n1, e2, n2, source_text=stripped, confidence=0.45, pct1=pct1, pct2=pct2)

    # Strategy 5: Two (X/N) patterns within proximity (up to 200 chars apart)
    # Common format: "treatment (92/155) ... placebo (87/164)"
    # Often split across lines in PDF text, so search full text not per-line
    paren_matches = list(_EVENTS_SLASH_N_PAREN.finditer(text))
    for i, m1 in enumerate(paren_matches):
        e1, n1 = int(m1.group(1)), int(m1.group(2))
        if e1 > n1 or n1 < 5:
            continue
        for m2 in paren_matches[i+1:]:
            gap = m2.start() - m1.end()
            if gap > 200:
                break  # too far apart
            if gap < 0:
                continue
            e2, n2 = int(m2.group(1)), int(m2.group(2))
            if e2 > n2 or n2 < 5:
                continue
            src = text[m1.start():m2.end()]
            _append_binary(e1, n1, e2, n2, source_text=src, confidence=0.5)

    # Strategy 6: "X/N vs Y/N" bare format (no parens, no percentage)
    vs_bare = re.compile(
        r'(\d+)\s*/\s*(\d+)\s*'
        r'(?:vs\.?|versus|compared\s+(?:to|with)|and)\s*'
        r'(\d+)\s*/\s*(\d+)',
        re.IGNORECASE
    )
    for m in vs_bare.finditer(text):
        e1, n1, e2, n2 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        if e1 <= n1 and e2 <= n2 and n1 >= 5 and n2 >= 5:
            _append_binary(e1, n1, e2, n2, source_text=m.group(0), confidence=0.7)

    # Strategy 7: Two "X of Y patients/subjects" mentions in proximity.
    of_n_matches = list(_EVENTS_OF_N_PATTERN.finditer(text))
    for i, m1 in enumerate(of_n_matches):
        e1, n1 = int(m1.group(1)), int(m1.group(2))
        if n1 < 5 or e1 > n1:
            continue
        for m2 in of_n_matches[i + 1:]:
            gap = m2.start() - m1.end()
            if gap > 260:
                break
            if gap < 0:
                continue
            e2, n2 = int(m2.group(1)), int(m2.group(2))
            if n2 < 5 or e2 > n2:
                continue
            source = text[m1.start():m2.end()]
            _append_binary(e1, n1, e2, n2, source_text=source, confidence=0.65)

    # Strategy 8: Proportion rows (0.xx) with nearby group sample sizes.
    # Example: "PSA within 2 weeks 0.27 0.29 0.28 0.28 0.30 0.29"
    # with nearby header "(N=308) (N=295) (N=290)".
    proportion_row_hint = re.compile(
        r'\b(?:proportion|risk|rate|screen|screening|psa|event|outcome|discussed|intend)\b',
        re.IGNORECASE,
    )
    proportion_token_pattern = re.compile(r'(?<!\d)(?:0?\.\d{1,3}|1(?:\.0{1,3})?)(?!\d)')
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        if not proportion_row_hint.search(stripped):
            continue

        prop_tokens = [float(token) for token in proportion_token_pattern.findall(stripped)]
        if len(prop_tokens) < 3:
            continue

        line_pos = text.find(line)
        if line_pos < 0:
            line_pos = 0
        context = text[max(0, line_pos - 600):line_pos + len(line) + 120]
        n_values = [n for n in _extract_context_sample_sizes(context) if 5 <= int(n) <= 5000]
        if len(n_values) < 2:
            continue

        # For rows with adjusted+unadjusted columns, prioritize every other value first.
        if len(prop_tokens) >= 6:
            collapsed_props = [prop_tokens[0], prop_tokens[2], prop_tokens[4]]
        else:
            collapsed_props = prop_tokens[:3]

        candidate_pairs = []
        if len(n_values) >= 3 and len(collapsed_props) >= 3:
            candidate_pairs.append((collapsed_props[0], int(n_values[0]), collapsed_props[2], int(n_values[2])))
            candidate_pairs.append((collapsed_props[1], int(n_values[1]), collapsed_props[2], int(n_values[2])))
        if len(n_values) >= 2 and len(collapsed_props) >= 2:
            candidate_pairs.append((collapsed_props[0], int(n_values[0]), collapsed_props[1], int(n_values[1])))

        seen_local = set()
        for p1, n1, p2, n2 in candidate_pairs:
            key = (round(p1, 4), n1, round(p2, 4), n2)
            if key in seen_local:
                continue
            seen_local.add(key)
            if not (0.0 <= p1 <= 1.0 and 0.0 <= p2 <= 1.0):
                continue
            e1 = int(round(p1 * n1))
            e2 = int(round(p2 * n2))
            if e1 > n1 or e2 > n2:
                continue
            if abs((e1 / n1) - p1) > 0.03:
                continue
            if abs((e2 / n2) - p2) > 0.03:
                continue
            _append_binary(
                e1,
                n1,
                e2,
                n2,
                source_text=stripped,
                confidence=0.28,
                pct1=p1 * 100.0,
                pct2=p2 * 100.0,
            )

    # Strategy 9: Percentage-vs-percentage with nearby sample sizes.
    # Example: "45% vs 30%, n=100 n=100" -> 45/100 vs 30/100.
    for m in _PCT_VS_PCT_PATTERN.finditer(text):
        try:
            pct1 = float(m.group(1))
            pct2 = float(m.group(2))
        except (TypeError, ValueError):
            continue
        if not (0 <= pct1 <= 100 and 0 <= pct2 <= 100):
            continue

        context = text[max(0, m.start() - 220):m.end() + 220]
        n_values = [int(n) for n in _extract_context_sample_sizes(context) if 5 <= int(n) <= 5000]
        if len(n_values) < 2:
            if len(n_values) == 1:
                # Common phrasing: "x% vs y%, n=100 n=100" may collapse to one unique N.
                n_values = [n_values[0], n_values[0]]
            else:
                continue

        # Consider nearby pair orientations and choose lowest pct reconstruction error.
        candidates = []
        unique_ns = []
        seen_n = set()
        for n in n_values:
            if n in seen_n:
                continue
            seen_n.add(n)
            unique_ns.append(n)
        for i, n1 in enumerate(unique_ns[:4]):
            for n2 in unique_ns[:4]:
                if n1 == n2 and len(unique_ns) > 1:
                    continue
                e1 = int(round((pct1 / 100.0) * n1))
                e2 = int(round((pct2 / 100.0) * n2))
                if e1 > n1 or e2 > n2:
                    continue
                err = abs((e1 / n1) * 100.0 - pct1) + abs((e2 / n2) * 100.0 - pct2)
                candidates.append((err, e1, n1, e2, n2))
            if i >= 2:
                break
        if not candidates:
            continue
        candidates.sort(key=lambda item: item[0])
        best_err, e1, n1, e2, n2 = candidates[0]
        if best_err > 3.5:
            continue
        _append_binary(
            e1,
            n1,
            e2,
            n2,
            source_text=m.group(0),
            confidence=0.4,
            pct1=pct1,
            pct2=pct2,
        )

    # Strategy 10: Table-like rows with two explicit percentages and nearby group N.
    # Example:
    #   "(N=120) (N=118)"
    #   "adverse events 12.5% 18.6%"
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        pct_tokens = [float(v) for v in _PCT_TOKEN_PATTERN.findall(stripped)]
        if len(pct_tokens) < 2:
            continue
        pct1, pct2 = pct_tokens[0], pct_tokens[1]
        if not (0 <= pct1 <= 100 and 0 <= pct2 <= 100):
            continue

        line_pos = text.find(line)
        if line_pos < 0:
            line_pos = 0
        context = text[max(0, line_pos - 350):line_pos + len(line) + 220]
        n_values = [int(n) for n in _extract_context_sample_sizes(context) if 5 <= int(n) <= 5000]
        if len(n_values) < 2:
            if len(n_values) == 1:
                n_values = [n_values[0], n_values[0]]
            else:
                continue
        n1, n2 = int(n_values[0]), int(n_values[1])
        e1 = int(round((pct1 / 100.0) * n1))
        e2 = int(round((pct2 / 100.0) * n2))
        if e1 > n1 or e2 > n2:
            continue
        err = abs((e1 / n1) * 100.0 - pct1) + abs((e2 / n2) * 100.0 - pct2)
        if err > 4.0:
            continue
        _append_binary(
            e1,
            n1,
            e2,
            n2,
            source_text=stripped,
            confidence=0.34,
            pct1=pct1,
            pct2=pct2,
        )

    return results


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def extract_raw_data(text: str) -> List[RawDataExtraction]:
    """
    Extract all raw two-group data from text.

    Returns both binary and continuous extractions, sorted by confidence.
    """
    normalized = _normalize_extraction_text(text)
    results = []
    results.extend(extract_binary_two_group(normalized))
    results.extend(extract_continuous_two_group(normalized))

    # Sort by confidence (highest first)
    results.sort(key=lambda x: x.confidence, reverse=True)

    return results
