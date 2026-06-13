"""
Entity extraction for DTA studies: the three things a DTA study is *about*.

  * index test         -- the test being evaluated (e.g. "rapid antigen test")
  * reference standard -- the truth used to classify disease (e.g. "RT-PCR")
  * target condition   -- what is being detected (e.g. "SARS-CoV-2 infection")

Implementation note: these are short noun phrases anchored on the canonical DTA
cue phrases (STARD / Cochrane DTA wording). Rather than a single greedy phrase
regex -- which both grabs the wrong span (leftmost-longest) and risks
catastrophic backtracking when a pattern STARTS with an open phrase -- we anchor
on the literal cue and then collect a bounded run of tokens forward or backward
in plain Python. That is linear-time and picks the phrase ADJACENT to the cue.

Spelling note (see rules/lessons.md): UK medical spellings that INSERT an extra
vowel must use `a?`/`o?` (e.g. "tumour" -> "tumou?r", "oesophageal" ->
"o?esophageal"). The registry's target vocabulary handles those; entity capture
here is spelling-agnostic because it copies tokens verbatim.
"""
from __future__ import annotations

import re
from typing import List, Optional

# A single token of an entity phrase: alphanumerics plus the punctuation that
# occurs inside test/condition names (RT-PCR, SARS-CoV-2, tTG-IgA, 18F-FDG).
_TOKEN = re.compile(r"[A-Za-z0-9][\w./+-]*")

# Words that terminate an entity phrase (clause connectors / boilerplate).
_STOP = {
    "for", "using", "use", "used", "against", "compared", "versus", "vs",
    "as", "to", "in", "with", "and", "or", "of", "the", "a", "an", "was",
    "were", "is", "are", "by", "from", "on", "at", "that", "which", "study",
    "studies", "patients", "participants", "individuals", "subjects",
}
# Leading filler stripped from the front of a captured phrase.
_LEAD = {"the", "a", "an", "using", "with", "by"}

_MAX_TOKENS = 6


def _tokens_after(text: str, pos: int, max_tokens: int = _MAX_TOKENS) -> Optional[str]:
    """Collect up to `max_tokens` tokens starting at/after `pos`, stopping at a
    stop-word once at least one content token has been taken."""
    out: List[str] = []
    i = pos
    n = len(text)
    while i < n and len(out) < max_tokens + len(_LEAD):
        m = _TOKEN.match(text, i)
        if not m:
            # allow a single separator (space/paren/colon) then continue
            if text[i] in " \t([:":
                i += 1
                continue
            break
        tok = m.group(0)
        low = tok.lower()
        if not out and low in _LEAD:
            i = m.end()
            continue
        if out and low in _STOP:
            break
        out.append(tok)
        i = m.end()
        if len(out) >= max_tokens:
            break
    phrase = " ".join(out).strip(".,;:()[]")
    return phrase if phrase else None


def _tokens_before(text: str, pos: int, max_tokens: int = 4) -> Optional[str]:
    """Collect up to `max_tokens` tokens ending at `pos`, scanning backward and
    stopping at a stop-word. Returns the phrase ADJACENT to (just before) pos."""
    toks = [(m.group(0), m.start()) for m in _TOKEN.finditer(text, 0, pos)]
    out: List[str] = []
    for tok, _start in reversed(toks):
        if tok.lower() in _STOP:
            break
        out.append(tok)
        if len(out) >= max_tokens:
            break
    if not out:
        return None
    phrase = " ".join(reversed(out)).strip(".,;:()[]")
    return phrase or None


# ---- cue anchors (all leading-literal => fail fast, linear time) -----------
_INDEX_CUES = [
    re.compile(r"diagnostic\s+(?:accuracy|performance|value)\s+of\s+", re.IGNORECASE),
    re.compile(r"\baccuracy\s+of\s+", re.IGNORECASE),
    re.compile(r"index\s+test\s+(?:was|were|:|\(|is)?\s*", re.IGNORECASE),
    re.compile(r"performance\s+of\s+", re.IGNORECASE),
]
_REFERENCE_AFTER_CUES = [
    re.compile(r"(?:reference|gold|criterion)\s+standard\s+(?:was|were|of|:|\(|is)\s*", re.IGNORECASE),
    re.compile(r"(?:compared|verified|confirmed)\s+(?:with|against|by|using)\s+", re.IGNORECASE),
]
# "<X> (served) as the reference standard" -> take tokens BEFORE the anchor
_REFERENCE_BEFORE_ANCHOR = re.compile(
    r"\s+(?:served\s+)?as\s+(?:the\s+|a\s+)?(?:reference|gold|criterion)\s+standard",
    re.IGNORECASE,
)
_TARGET_CUES = [
    re.compile(r"(?:detection|diagnosis|identification|screening|prediction)\s+of\s+", re.IGNORECASE),
    re.compile(r"(?:for\s+diagnosing|to\s+diagnose|to\s+detect|to\s+identify)\s+", re.IGNORECASE),
    re.compile(r"(?:patients?|participants?|individuals?)\s+with\s+(?:suspected\s+)?", re.IGNORECASE),
]


def _first_after(cues, text: str) -> Optional[str]:
    for cue in cues:
        m = cue.search(text)
        if m:
            phrase = _tokens_after(text, m.end())
            if phrase:
                return phrase
    return None


def extract_index_test(text: str) -> Optional[str]:
    return _first_after(_INDEX_CUES, text)


def extract_reference_standard(text: str) -> Optional[str]:
    # forward cue first ("reference standard was X")
    phrase = _first_after(_REFERENCE_AFTER_CUES, text)
    if phrase:
        return phrase
    # else "<X> as the reference standard" -> tokens immediately before
    m = _REFERENCE_BEFORE_ANCHOR.search(text)
    if m:
        return _tokens_before(text, m.start())
    return None


def extract_target_condition(text: str) -> Optional[str]:
    return _first_after(_TARGET_CUES, text)


def extract_entities(text: str) -> dict:
    return {
        "index_test": extract_index_test(text),
        "reference_standard": extract_reference_standard(text),
        "target_condition": extract_target_condition(text),
    }
