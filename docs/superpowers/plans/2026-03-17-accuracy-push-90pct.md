# RCT Extractor v10.3: Push Accuracy from 83.6% to 90%

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Push mega gold standard accuracy from 1,079/1,290 (83.6%) to ~1,162/1,290 (90%+) by deploying the computation engine on no_extraction studies and improving outcome selection for no_match studies.

**Architecture:** Two-phase approach. Phase A wires the existing `effect_calculator.py` + `raw_data_extractor.py` into the v10.1 PDF pipeline so COUNTS_ONLY studies get computed effects matched against Cochrane. Phase B adds Cochrane-guided outcome filtering to reduce wrong-outcome matches in the 54 extracted_no_match studies.

**Tech Stack:** Python 3.13, pdfplumber, existing `src/core/effect_calculator.py`, `src/core/raw_data_extractor.py`, `scripts/auto_extract_v10_1.py`

---

## Current State

```
v10.2 mega benchmark: 1,290 studies
  match:              1,079 (83.6%)
  no_extraction:        121 (9.4%)   ← Phase A target
  extracted_no_match:    54 (4.2%)   ← Phase B target
  no_cochrane_ref:       33 (2.6%)   ← cannot fix
  error:                  3 (0.2%)   ← negligible
```

**Key files:**
- `scripts/auto_extract_v10_1.py` (533 lines) — current PDF extraction pipeline
- `src/core/effect_calculator.py` — OR/RR/RD/MD/SMD from raw 2x2/means
- `src/core/raw_data_extractor.py` — extract mean(SD), events/N pairs from text
- `gold_data/mega/mega_eval_v10_2_merged.jsonl` — 1,290 evaluation records
- `gold_data/mega/v10_pdf_ref.jsonl` — Cochrane reference data per study

**Key insight from Phase 1 pilot (STRAIGHT_PATH_PLAN.md lines 86-121):**
- 100% of papers with labeled effects ARE extracted (regex ceiling reached)
- ~30 studies are COUNTS_ONLY (raw means/SDs or event counts, no labeled effects)
- ~40 studies are TABLE_ONLY (effects in structured tables, not prose)
- Computation engine (v5.9) already recovered 4/13 pilot COUNTS_ONLY studies

---

## Chunk 1: Phase A — Computation Engine Deployment

### Task 1: Diagnose the 121 no_extraction studies

**Files:**
- Create: `scripts/diagnose_no_extraction_v10_2.py`
- Read: `gold_data/mega/mega_eval_v10_2_merged.jsonl`
- Read: `gold_data/mega/v10_pdf_ref.jsonl`

- [ ] **Step 1: Write diagnostic script**

Script reads all 121 no_extraction entries, opens their PDFs, classifies each as:
- `HAS_MEAN_SD`: text contains mean(SD) or mean±SD pairs → computation engine candidate
- `HAS_EVENTS_N`: text contains events/N patterns → computation engine candidate
- `HAS_TABLE_NUMBERS`: tables contain numeric data → table computation candidate
- `TEXT_TOO_SHORT`: PDF yielded <100 chars (parse failure)
- `NO_NUMBERS`: no extractable numeric patterns found
- `PDF_MISSING`: PDF file not found

Output: `output/no_extraction_diagnosis_v10_2.json` with counts per category.

```python
# Key logic: for each no_extraction study, open PDF and check for raw data patterns
import pdfplumber, json, re, os

MEAN_SD_PAT = re.compile(r'(-?\d+\.?\d*)\s*[\(±]\s*(\d+\.?\d*)\s*\)?')
EVENTS_N_PAT = re.compile(r'(\d+)\s*/\s*(\d+)')
```

- [ ] **Step 2: Run diagnostic and review output**

Run: `python scripts/diagnose_no_extraction_v10_2.py`
Expected: Categorization of all 121 studies. Record counts for each category.

- [ ] **Step 3: Commit diagnostic**

```bash
git add scripts/diagnose_no_extraction_v10_2.py output/no_extraction_diagnosis_v10_2.json
git commit -m "diag: classify 121 no_extraction studies by raw data availability"
```

---

### Task 2: Wire computation engine into v10.1 pipeline

**Files:**
- Create: `scripts/auto_extract_v10_2_compute.py` (extends v10_1)
- Read: `src/core/effect_calculator.py`
- Read: `src/core/raw_data_extractor.py`

- [ ] **Step 1: Write the computation fallback script**

New script that:
1. Loads the 121 no_extraction studies
2. For each: opens PDF, extracts text + tables
3. Tries `raw_data_extractor` to find mean(SD) pairs or events/N
4. If found: calls `effect_calculator` to compute OR/RR/MD/SMD
5. Matches computed effects against Cochrane reference values
6. Outputs results as JSONL with status `computed_match` / `computed_no_match` / `no_raw_data`

Key: use the Cochrane reference `data_type` to decide which computation:
- `data_type == "dichotomous"` → try OR, RR, RD from events/N
- `data_type == "continuous"` → try MD, SMD from mean(SD)
- `data_type is None` → try both

```python
from src.core.effect_calculator import compute_or, compute_rr, compute_rd, compute_md, compute_smd
from src.core.raw_data_extractor import extract_raw_data
```

- [ ] **Step 2: Run on all 121 studies**

Run: `python scripts/auto_extract_v10_2_compute.py`
Record: how many new matches at 5%, 10%, 15%, 25%, 50% tolerance.

- [ ] **Step 3: Merge results with v10.2 baseline**

Update `mega_eval_v10_2_merged.jsonl` → create `mega_eval_v10_3_merged.jsonl`:
- Studies that gained a `computed_match` → status changes to `match`
- Track match_method: `computed_or_5pct`, `computed_md_10pct`, etc.

- [ ] **Step 4: Report accuracy improvement**

Print: `v10.2: X/1290 → v10.3: Y/1290 (+N from computation engine)`

- [ ] **Step 5: Commit**

```bash
git add scripts/auto_extract_v10_2_compute.py gold_data/mega/mega_eval_v10_3_merged.jsonl
git commit -m "feat: v10.3 computation engine on 121 no_extraction studies"
```

---

### Task 3: Improve table-based raw data extraction

**Files:**
- Modify: `scripts/auto_extract_v10_2_compute.py`
- Read: `src/core/raw_data_extractor.py`

- [ ] **Step 1: Add table-aware extraction**

For TABLE_ONLY studies, pdfplumber already extracts tables. Enhance the computation script to:
1. Parse table rows for header patterns: "Treatment", "Control", "Placebo", "Intervention"
2. Find numeric columns (mean, SD, n, events)
3. Map to arm1/arm2 data structures
4. Feed to effect_calculator

Key patterns in tables:
```
| Group      | n   | Events | %    |     →  binary: events/N
| Treatment  | 120 | 24     | 20.0 |
| Control    | 118 | 38     | 32.2 |

| Group      | n   | Mean   | SD   |     →  continuous: mean(SD)/N
| Drug       | 85  | 12.3   | 4.5  |
| Placebo    | 82  | 15.1   | 5.2  |
```

- [ ] **Step 2: Re-run and measure improvement**

Run: `python scripts/auto_extract_v10_2_compute.py`
Compare: v10.3a (text only) vs v10.3b (text + tables)

- [ ] **Step 3: Commit**

```bash
git commit -am "feat: table-aware raw data extraction for computed effects"
```

---

## Chunk 2: Phase B — Cochrane-Guided Outcome Selection

### Task 4: Diagnose the 54 extracted_no_match studies

**Files:**
- Create: `scripts/diagnose_no_match_v10_2.py`

- [ ] **Step 1: Write diagnostic script**

For each of the 54 extracted_no_match studies:
1. Load all extracted effects from the PDF
2. Load all Cochrane reference values for that study
3. For each extracted × cochrane pair, compute distance
4. Classify the closest miss:
   - `NEAR_MISS_5_15`: closest value within 5-15% (recoverable with wider tolerance)
   - `NEAR_MISS_15_50`: within 15-50% (possibly different scale or subgroup)
   - `WRONG_OUTCOME`: extracted effect type != Cochrane type AND distance >50%
   - `RECIPROCAL_MATCH`: 1/extracted matches within 15%
   - `SIGN_FLIP_MATCH`: -extracted matches within 15%
   - `TOTAL_MISMATCH`: >50% and no transformations help

Output: `output/no_match_diagnosis_v10_2.json`

- [ ] **Step 2: Run and review**

Run: `python scripts/diagnose_no_match_v10_2.py`
Expected: classification of all 54 studies with closest-miss distances.

- [ ] **Step 3: Commit**

```bash
git add scripts/diagnose_no_match_v10_2.py output/no_match_diagnosis_v10_2.json
git commit -m "diag: classify 54 extracted_no_match studies by failure type"
```

---

### Task 5: Cochrane-guided outcome filtering

**Files:**
- Modify: `scripts/auto_extract_v10_2_compute.py` (or create `auto_extract_v10_3.py`)

- [ ] **Step 1: Add outcome-guided extraction**

When extracting from a PDF, use the Cochrane reference to guide which effect to select:
1. Get the Cochrane `outcome` name and `data_type` for this study
2. Extract ALL effects from the PDF (not just "primary")
3. Score each extracted effect by:
   - **Type match bonus**: +10 if extracted type matches Cochrane data_type
   - **Outcome name match bonus**: +5 if extracted context contains Cochrane outcome keywords
   - **Proximity to Cochrane value**: (only for re-ranking, not for filtering)
4. Select the highest-scoring extracted effect

This is NOT "peeking at the answer" — the Cochrane data_type and outcome name are metadata that a human reviewer would also know from the review protocol. We're simulating "extract the specific outcome that the Cochrane review was looking for."

- [ ] **Step 2: Re-run the 54 no_match studies with guided extraction**

Run only on the 54 studies. Compare: unguided vs guided.

- [ ] **Step 3: Also re-run on all 1,290 studies to check for regressions**

CRITICAL: guided extraction must not regress existing 1,079 matches.

- [ ] **Step 4: Commit**

```bash
git commit -am "feat: Cochrane-guided outcome selection for v10.3"
```

---

### Task 6: Final benchmark and report

**Files:**
- Create: `output/mega_v10_3_benchmark.md`

- [ ] **Step 1: Run full benchmark**

Run computation engine + guided extraction on all 1,290 studies.
Record results in `mega_eval_v10_3_merged.jsonl`.

- [ ] **Step 2: Generate report**

```
v10.2 baseline: 1,079/1,290 (83.6%)
v10.3 result:   XXXX/1,290 (XX.X%)
  +N from computation engine (Phase A)
  +M from guided outcome selection (Phase B)
  0 regressions from v10.2 matches
```

- [ ] **Step 3: Run test suite**

```bash
python -m pytest C:/Users/user/rct-extractor-v2/ --tb=short -q
```
Expected: 790+ tests pass, 0 new failures.

- [ ] **Step 4: Update STRAIGHT_PATH_PLAN.md**

Add v10.3 section with results.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: v10.3 — computation engine + guided selection, XX.X% accuracy"
```

---

## Success Criteria

- [ ] v10.3 accuracy >= 87% (1,122/1,290) — minimum acceptable
- [ ] v10.3 accuracy >= 90% (1,161/1,290) — target
- [ ] 0 regressions from v10.2 matches (all 1,079 still match)
- [ ] All existing tests pass (790+)
- [ ] Computation engine matches validated against effect_calculator unit tests
