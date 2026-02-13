# RCT Extractor v5 — The Straight Path Plan

## Inspired by Surah Al-Fatiha

> **بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ**
> In the name of Allah, the Most Gracious, the Most Merciful

The seven verses of Al-Fatiha guide this plan's seven phases:

| Verse | Theme | Plan Phase |
|-------|-------|------------|
| 1. Bismillah | **Beginning with purpose** | Phase 0: Foundation & Intent |
| 2. Alhamdulillah | **Gratitude for what works** | Phase 1: Preserve Working Components |
| 3. Ar-Rahman, Ar-Raheem | **Mercy in approach** | Phase 2: Gentle Fixes (Don't Break Things) |
| 4. Maliki Yawm id-Deen | **Accountability** | Phase 3: Honest Validation on Real PDFs |
| 5. Iyyaka Na'budu | **Devotion to truth** | Phase 4: Fix Known Failures (DECLARE-TIMI) |
| 6. Ihdina Sirat | **The Straight Path** | Phase 5: Table CI Recovery (The Main Gap) |
| 7. Sirat al-Mustaqeem | **Path of the Blessed** | Phase 6: Production Readiness |

---

## Multi-Persona Consultation

### The Seeker (User Advocate)
> "I want to extract effect estimates from real RCT PDFs automatically. I don't care about synthetic snippets — show me it works on actual papers from NEJM, Lancet, BMC Medicine."

### The Craftsman (Engineer)
> "The current system has 98.5% precision on curated corpus. But 18/22 missing CIs are in tables. The biggest gain comes from structured table parsing, not more regex patterns."

### The Guardian (Methodologist)
> "Snippet validation is circular — we test on text we designed patterns for. True validation requires held-out PDFs with independent ground truth. ClinicalTrials.gov results are the gold standard."

### The Shepherd (Product Owner)
> "Users need primary outcomes, not 4.3 effects per paper. They need CSV export for RevMan. They need confidence in the numbers."

### The Healer (Data Steward)
> "The 107-PDF corpus is good. But 21 papers have zero extractions because they're not RCTs. Clean the corpus. Verify every PDF is a real RCT with results."

---

## Phase 0: Foundation & Intent (Bismillah)

**Purpose:** Establish clear goals and success criteria before writing any code.

### 0.1 Define Success Metrics
| Metric | Current | Target | Validation Method |
|--------|---------|--------|-------------------|
| Corpus size (real RCT PDFs) | 46 curated | 100+ | PMC download + manual verification |
| Extraction yield | 80.4% | 90%+ | PDFs with ≥1 extraction / total RCT PDFs |
| CI completion (text) | 89% | 95%+ | CIs found / extractions (excluding table-only) |
| CI completion (tables) | ~20% | 70%+ | Table-based CI recovery |
| Primary outcome F1 | 0% | 80%+ | Labeled primary outcomes vs ground truth |
| DECLARE-TIMI HR=0.83 | MISSED | FOUND | Specific regression test |

### 0.2 Acquire 100+ Real RCT Result PDFs
**Source priority:**
1. **BMC Medicine / Trials / BMJ Open** — fully OA, CC-BY
2. **PLOS Medicine / PLOS ONE** — OA
3. **JAMA Network Open** — OA subset
4. **Europe PMC OA subset** — curated RCT filter

**Verification checklist per PDF:**
- [ ] Contains "randomized" or "randomised"
- [ ] Has results section (not protocol/methods-only)
- [ ] Reports ≥1 effect estimate with CI
- [ ] Is phase 2/3 clinical trial

**Script:** `scripts/acquire_verified_rct_corpus.py`

### 0.3 Create Independent Ground Truth
**Method:** For 50 PDFs, manually extract:
- Primary outcome effect type, value, CI
- Secondary outcomes (up to 3)
- Whether CI is in text vs table

**Format:** `data/ground_truth/real_pdf_ground_truth.json`

---

## Phase 1: Preserve Working Components (Alhamdulillah)

**Gratitude:** The current system works well for ratio effects in running text.

### 1.1 Lock Known-Good Patterns
- HR patterns: 36/36 ground truth trials covered
- OR patterns: working (RA-BEAM)
- RR patterns: working (ACTT-1, RE-LY, DEFINE)

### 1.2 Preserve Regression Tests
- 25 current tests → keep all
- Add: `test_declare_timi_hr_083` (currently fails, will fix in Phase 4)
- Add: `test_real_pdf_extraction_yield` (new)

### 1.3 Document What Works
Create `docs/WORKING_PATTERNS.md`:
- List all patterns with real-world examples
- Note which PDFs each pattern was validated against

---

## Phase 2: Gentle Fixes (Ar-Rahman, Ar-Raheem)

**Mercy:** Fix bugs without breaking working functionality.

### 2.1 Complete the % Guard
**Current:** `\b(?!\s*%)` — misses "aOR95%CI" (no space)
**Fix:** `\b(?!\s*%|%)`

```python
# In enhanced_extractor_v3.py, all value-only patterns
r'\baOR\b\s+(\d+\.?\d*)\b(?!\s*%|%)'  # catches both "95%" and "95 %"
```

### 2.2 Add Return Type Hints
```python
def _ci_key(lower: float, upper: float) -> tuple[int, int]:
```

### 2.3 Add SHA256 to Unified Manifest
```python
import hashlib
sha256 = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
```

### 2.4 Create Ground Truth Schema
```python
# src/core/schemas/ground_truth.py
from pydantic import BaseModel

class GroundTruthEffect(BaseModel):
    effect_type: str
    value: float
    ci_lower: float
    ci_upper: float
    outcome: str
    is_primary: bool
    ci_location: Literal["text", "table", "figure"]
```

---

## Phase 3: Honest Validation on Real PDFs (Maliki Yawm id-Deen)

**Accountability:** Measure true performance on unseen real PDFs.

### 3.1 Create Held-Out Test Set
- 20 PDFs never used for pattern development
- Manually annotated ground truth
- Stratified: 10 HR, 5 OR/RR, 3 MD, 2 mixed

### 3.2 Run Blind Validation
```bash
python scripts/run_blind_validation.py \
  --pdfs data/held_out_test_set/ \
  --ground-truth data/ground_truth/held_out_gt.json \
  --output output/blind_validation_v5.json
```

### 3.3 Report Honest Metrics
- **Sensitivity:** Effects found / effects in ground truth
- **Precision:** Correct effects / extracted effects
- **CI accuracy:** Correct CIs / CIs found
- **Primary outcome accuracy:** Primary identified / primaries in GT

### 3.4 Publish Failure Cases
Every missed effect gets documented:
```json
{
  "pdf": "PMC12345678",
  "missed_effect": "HR 0.83 (0.73-0.95)",
  "reason": "CI in table, not text",
  "source_location": "Table 2, row 3"
}
```

---

## Phase 4: Fix Known Failures (Iyyaka Na'budu)

**Devotion to truth:** Fix embarrassing misses in landmark trials.

### 4.1 DECLARE-TIMI 58 HR=0.83

**Ground truth source_text:** `HR 0.83 (95% CI, 0.73-0.95; P=0.005)`

**Diagnosis:** Pattern should match. Debug:
```python
text = "HR 0.83 (95% CI, 0.73-0.95; P=0.005)"
extractions = extractor.extract(text)
# Why is this returning empty or wrong?
```

**Likely issue:** The comma after "CI" or semicolon before P-value.

**Fix:** Add pattern variant:
```python
r'HR\s+(\d+\.?\d*)\s*\(\s*95%?\s*CI\s*,\s*(\d+\.?\d*)\s*[-–—]\s*(\d+\.?\d*)'
```

**Regression test:**
```python
def test_declare_timi_hr_083():
    text = "HR 0.83 (95% CI, 0.73-0.95; P=0.005)"
    exts = extractor.extract(text)
    assert len(exts) == 1
    assert exts[0].point_estimate == 0.83
    assert exts[0].ci.lower == 0.73
    assert exts[0].ci.upper == 0.95
```

### 4.2 Fix ARD 0% CI Completion

**Diagnosis:** ARD patterns exist but may not match real-world formats.

**Action:** Find 5 real PDFs with ARD, extract source text, verify patterns.

### 4.3 Fix MD/SMD Table CI Gap

**Diagnosis:** Cohen's d values often in tables without inline CI.

**Action:** Table CI recovery (Phase 5).

---

## Phase 5: Table CI Recovery (Ihdina Sirat al-Mustaqeem)

**The Straight Path:** 82% of missing CIs are in tables. This is the main gap.

### 5.1 Structured Table Extraction

Use pdfplumber's table detection:
```python
import pdfplumber

def extract_tables_with_ci(pdf_path: Path) -> list[dict]:
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                # Find header row with "CI" or "95%"
                # Match effect values to CI columns
                ...
    return tables
```

### 5.2 Table CI Patterns

For table cells, CIs often appear as:
- `0.74 (0.65-0.85)` — value with CI in same cell
- `0.74` in one cell, `0.65-0.85` in adjacent cell
- `0.74` in one cell, `0.65` and `0.85` in separate cells

**Strategy:**
1. Detect table structure (headers, rows)
2. Identify "HR", "OR", "CI", "95%" columns
3. Align values with CIs by row position

### 5.3 Table-Aware Proximity Search

Extend `CIProximitySearch` with table mode:
```python
def search_ci_in_table_context(
    self,
    table_cells: list[str],
    value: float,
    effect_type: str
) -> Optional[ProximityResult]:
    """Search adjacent cells for CI."""
    ...
```

### 5.4 Validation Target

| Metric | Before | After Phase 5 |
|--------|--------|---------------|
| Table CI recovery | ~20% | 70%+ |
| Overall CI completion | 85.6% | 92%+ |
| PMC12459455 Cohen d CIs | 0/5 | 4/5 |
| PMC12620794 SMD CIs | 0/5 | 4/5 |

---

## Phase 6: Production Readiness (Sirat al-Mustaqeem)

**Path of the Blessed:** Deliver a tool users can trust.

### 6.1 Primary Outcome Detection

**Heuristic signals:**
- First effect mentioned in abstract
- Effect labeled "primary" in text
- Effect in "Primary Endpoint" table section
- Effect with smallest P-value (tiebreaker)

**Implementation:**
```python
class Extraction:
    ...
    is_primary: bool = False
    primary_confidence: float = 0.0
```

### 6.2 CSV/RevMan Export

```python
def export_to_csv(extractions: list[Extraction], path: Path):
    """Export for RevMan/Covidence import."""
    df = pd.DataFrame([
        {
            "study_id": e.study_id,
            "effect_type": e.effect_type,
            "effect_size": e.point_estimate,
            "ci_lower": e.ci.lower,
            "ci_upper": e.ci.upper,
            "is_primary": e.is_primary,
        }
        for e in extractions
    ])
    df.to_csv(path, index=False)
```

### 6.3 Confidence Scores

Each extraction gets a calibrated confidence:
- 0.95+: Text-based, standard format, validated pattern
- 0.80-0.95: Table-based, structured extraction
- 0.60-0.80: Proximity recovery, less certain
- <0.60: Flag for human review

### 6.4 Version Cleanup

Single source of truth:
```python
# src/core/__init__.py
__version__ = "5.0.0"
```

All other version strings reference this.

---

## Implementation Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 0 | 2 days | 100+ verified RCT PDFs, independent GT for 50 |
| 1 | 1 day | Locked patterns, new regression tests |
| 2 | 1 day | % guard fix, type hints, schema |
| 3 | 2 days | Blind validation on held-out set |
| 4 | 2 days | DECLARE-TIMI fixed, ARD diagnosed |
| 5 | 5 days | Table CI recovery module |
| 6 | 3 days | Primary detection, CSV export, confidence |

**Total: 16 days to v5.0.0**

---

## Success Criteria (The Straight Path)

When we can say:

1. **"We tested on 100+ real RCT PDFs we never trained on"** — not snippets
2. **"DECLARE-TIMI HR=0.83 is extracted correctly"** — landmark trial works
3. **"Table CIs are recovered at 70%+ rate"** — the main gap closed
4. **"Primary outcomes are identified with 80% accuracy"** — users get what matters
5. **"Results export to CSV for RevMan"** — practical utility

Then we have followed **الصِّرَاطَ الْمُسْتَقِيمَ** — the Straight Path.

---

## Closing Du'a

> **رَبَّنَا آتِنَا مِن لَّدُنكَ رَحْمَةً وَهَيِّئْ لَنَا مِنْ أَمْرِنَا رَشَدًا**
> "Our Lord, grant us from Yourself mercy and prepare for us from our affair right guidance." (18:10)

May this tool serve researchers seeking truth in clinical evidence, with precision, honesty, and humility about its limitations.

---

*Plan created: 2026-02-05*
*Version: v5 Fatiha*
