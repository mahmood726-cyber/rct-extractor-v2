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
    r'(-?\d+\.?\d*)\s*(?:\u00b1|\+/?-)\s*(\d+\.?\d*)',
)

# n = 30 or N = 30 or (n=30)
_SAMPLE_SIZE_PATTERN = re.compile(
    r'[nN]\s*[=\u00bc]\s*(\d+)',
)

# Group header with n: "Treatment (n=30)" or "Control (N=25)"
_GROUP_N_PATTERN = re.compile(
    r'([\w\s-]{2,40}?)\s*\(\s*[nN]\s*[=\u00bc]\s*(\d+)\s*\)',
)


def extract_continuous_two_group(text: str) -> List[RawDataExtraction]:
    """
    Extract two-group continuous data: mean(SD) pairs with sample sizes.

    Looks for patterns like:
    - "Treatment: 45.3 (19.9), n=22; Control: 58.5 (18.6), n=20"
    - "Group A 49.1 (5.0) n=22 vs Group B 48.1 (5.7) n=26"
    - Table rows: "Outcome  45.3 (19.9)  58.5 (18.6)"
    """
    results = []

    # Strategy 1: Inline "X (SD) vs Y (SD)" comparisons
    # Pattern: value(sd) ... vs/versus/compared ... value(sd)
    vs_pattern = re.compile(
        r'(-?\d+\.?\d*)\s*'
        r'(?:\(\s*(\d+\.?\d*)\s*\)|(?:\u00b1|\+/?-)\s*(\d+\.?\d*))'
        r'\s*(?:vs\.?|versus|compared\s+(?:to|with)|and)\s*'
        r'(-?\d+\.?\d*)\s*'
        r'(?:\(\s*(\d+\.?\d*)\s*\)|(?:\u00b1|\+/?-)\s*(\d+\.?\d*))',
        re.IGNORECASE
    )
    for m in vs_pattern.finditer(text):
        mean1 = float(m.group(1))
        sd1 = float(m.group(2) or m.group(3))
        mean2 = float(m.group(4))
        sd2 = float(m.group(5) or m.group(6))

        # Look for nearby sample sizes
        context = text[max(0, m.start() - 200):m.end() + 200]
        n_matches = _SAMPLE_SIZE_PATTERN.findall(context)

        arm1 = ArmData(mean=mean1, sd=sd1)
        arm2 = ArmData(mean=mean2, sd=sd2)

        if len(n_matches) >= 2:
            arm1.n = int(n_matches[0])
            arm2.n = int(n_matches[1])

        ext = RawDataExtraction(
            arm1=arm1, arm2=arm2,
            data_type="continuous",
            source_text=m.group(0)[:200],
            confidence=0.7 if arm1.n else 0.4,
        )
        results.append(ext)

    # Strategy 2: Table-like rows with two mean(SD) values
    # Look for lines with exactly 2 mean(SD) patterns
    for line in text.split('\n'):
        ms = list(_MEAN_SD_PATTERN.finditer(line))
        if len(ms) == 2:
            mean1, sd1 = float(ms[0].group(1)), float(ms[0].group(2))
            mean2, sd2 = float(ms[1].group(1)), float(ms[1].group(2))

            # Heuristic: SD should be smaller than mean for most outcomes
            # and both SDs should be in similar range
            if sd1 > 0 and sd2 > 0:
                sd_ratio = max(sd1, sd2) / min(sd1, sd2)
                if sd_ratio < 10:  # SDs within 10x of each other
                    # Look for sample sizes in nearby context
                    line_pos = text.find(line)
                    context = text[max(0, line_pos - 500):line_pos + len(line) + 200]
                    n_matches = _SAMPLE_SIZE_PATTERN.findall(context)

                    arm1 = ArmData(mean=mean1, sd=sd1)
                    arm2 = ArmData(mean=mean2, sd=sd2)

                    if len(n_matches) >= 2:
                        arm1.n = int(n_matches[0])
                        arm2.n = int(n_matches[1])

                    ext = RawDataExtraction(
                        arm1=arm1, arm2=arm2,
                        data_type="continuous",
                        source_text=line.strip()[:200],
                        confidence=0.5 if arm1.n else 0.3,
                    )
                    results.append(ext)

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

# "X of Y patients" or "X out of Y"
_EVENTS_OF_N_PATTERN = re.compile(
    r'(\d+)\s+(?:of|out\s+of)\s+(\d+)\s*(?:patients?|subjects?|participants?|women|men|children)',
    re.IGNORECASE,
)


def extract_binary_two_group(text: str) -> List[RawDataExtraction]:
    """
    Extract two-group binary data: events/N or events(%) comparisons.

    Looks for patterns like:
    - "Treatment 15/56 (26.8%) vs Placebo 18/57 (31.6%)"
    - "7 (6.8%) in group A and 11 (10.3%) in group B"
    - "mesh 7/40 vs AC 17/39"
    """
    results = []

    # Strategy 1: "X/N (%) vs Y/N (%)" inline comparisons
    vs_binary = re.compile(
        r'(\d+)\s*/\s*(\d+)\s*(?:\(\s*\d+\.?\d*\s*%?\s*\))?\s*'
        r'(?:vs\.?|versus|compared\s+(?:to|with)|and)\s*'
        r'(\d+)\s*/\s*(\d+)\s*(?:\(\s*\d+\.?\d*\s*%?\s*\))?',
        re.IGNORECASE
    )
    for m in vs_binary.finditer(text):
        e1, n1, e2, n2 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
        if e1 <= n1 and e2 <= n2 and n1 > 0 and n2 > 0:
            ext = RawDataExtraction(
                arm1=ArmData(events=e1, n=n1),
                arm2=ArmData(events=e2, n=n2),
                data_type="binary",
                source_text=m.group(0)[:200],
                confidence=0.8,
            )
            results.append(ext)

    # Strategy 2: "X patients (Y%) in group A and Z patients (W%) in group B"
    group_pct = re.compile(
        r'(\d+)\s*(?:patients?|subjects?)?\s*\(\s*(\d+\.?\d*)\s*%\s*\)\s*'
        r'(?:in\s+(?:the\s+)?)?(?:group\s+)?\w+\s*'
        r'(?:and|vs\.?|versus|compared)\s*'
        r'(\d+)\s*(?:patients?|subjects?)?\s*\(\s*(\d+\.?\d*)\s*%\s*\)',
        re.IGNORECASE
    )
    for m in group_pct.finditer(text):
        e1, pct1, e2, pct2 = int(m.group(1)), float(m.group(2)), int(m.group(3)), float(m.group(4))
        # Derive N from events and percentage
        if pct1 > 0 and pct2 > 0:
            n1 = round(e1 / (pct1 / 100))
            n2 = round(e2 / (pct2 / 100))
            if e1 <= n1 and e2 <= n2:
                ext = RawDataExtraction(
                    arm1=ArmData(events=e1, n=n1, percentage=pct1),
                    arm2=ArmData(events=e2, n=n2, percentage=pct2),
                    data_type="binary",
                    source_text=m.group(0)[:200],
                    confidence=0.7,
                )
                results.append(ext)

    # Strategy 3: Table rows with two events/N values
    for line in text.split('\n'):
        ms = list(_EVENTS_N_PCT_PATTERN.finditer(line))
        if len(ms) == 2:
            e1, n1 = int(ms[0].group(1)), int(ms[0].group(2))
            e2, n2 = int(ms[1].group(1)), int(ms[1].group(2))
            if e1 <= n1 and e2 <= n2 and n1 > 0 and n2 > 0:
                ext = RawDataExtraction(
                    arm1=ArmData(events=e1, n=n1),
                    arm2=ArmData(events=e2, n=n2),
                    data_type="binary",
                    source_text=line.strip()[:200],
                    confidence=0.6,
                )
                results.append(ext)

    return results


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def extract_raw_data(text: str) -> List[RawDataExtraction]:
    """
    Extract all raw two-group data from text.

    Returns both binary and continuous extractions, sorted by confidence.
    """
    results = []
    results.extend(extract_binary_two_group(text))
    results.extend(extract_continuous_two_group(text))

    # Sort by confidence (highest first)
    results.sort(key=lambda x: x.confidence, reverse=True)

    return results
