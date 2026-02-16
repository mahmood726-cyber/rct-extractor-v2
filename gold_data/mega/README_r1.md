# Manual Outcome Extraction - Round 1

**Date:** 2026-02-14
**Extractor:** Claude Sonnet 4.5
**Input:** clean_batch_r1.json (15 studies)
**Output:** clean_results_r1.json

## Extraction Protocol

### Critical Rules
1. **Only extract numbers that ACTUALLY APPEAR** in abstract/results_text
2. **NEVER fabricate or guess numbers**
3. Binary outcomes: require event counts (e.g., "12/45") for BOTH groups
4. Continuous outcomes: require means + SDs for BOTH groups
5. If percentages found, compute counts = round(percentage × N) ONLY if N clearly stated
6. Quote exact source text (max 200 chars)

### Fields Extracted
- `study_id`: Study identifier
- `found`: Boolean - any extractable data found
- `effect_type`: "OR"/"RR"/"MD"/"SMD"/"NONE"
- `point_estimate`, `ci_lower`, `ci_upper`: Direct effect estimates
- `intervention_events`, `intervention_n`: Binary intervention arm
- `control_events`, `control_n`: Binary control arm
- `intervention_mean`, `intervention_sd`, `intervention_n`: Continuous intervention
- `control_mean`, `control_sd`, `control_n`: Continuous control
- `source_quote`: Verbatim text (≤200 chars)
- `reasoning`: Explanation of extraction decision

## Results

### Summary Statistics
- **Total entries:** 15
- **Found (any data):** 11 (73.3%)
- **Not found:** 4 (26.7%)

### Data Completeness
- **Complete effect estimate (with CI):** 1 study (Ladapo 2020)
- **Complete binary data (events/N both groups):** 1 study (Shi 2012)
- **Complete continuous data (mean±SD both groups):** 0 studies
- **Partial data only:** 9 studies
- **No data:** 4 studies

### High-Quality Extractions (Directly Usable)

#### 1. Ladapo 2020_2020
**Outcome:** Smoking cessation
**Data:** OR 2.56 (95% CI 0.84–7.83)
**Source:** "The 6-month rate of biochemically-confirmed smoking cessation was 19.6% in the incentive group and 8.9% in the enhanced usual care group (odds ratio, 2.56; 95% CI, 0.84 to 7.83, P=0.10)"
**Quality:** ✓✓✓ Complete - directly stated OR with CI

#### 2. Shi 2012_2012
**Outcome:** Antihypertensive drug dosage reduction (secondary)
**Data:** 7/9 vs 0/9
**Source:** "antihypertensive drug dosage was reduced in 7 of 9 cases with hypertension in the allopurinol group compared to 0 of 9 cases in the control group (p ! 0.01)"
**Quality:** ✓✓✓ Complete - exact event counts both arms
**Note:** Primary outcome (proteinuria) not quantified in excerpt

### Medium-Quality Extractions (Computable)

#### 3. Fraser 2017_2017
**Outcome:** Smoking cessation
**Data:** 21.6% (n=948) vs 13.8% (n=952)
**Computed events:** 205/948 vs 131/952
**Quality:** ✓✓ Computable - used round(% × N)

### Partial Extractions (9 studies)
See EXTRACTION_SUMMARY_r1.md for details on:
- Perez-Jimenez 2023 (N only, no events)
- Jo 2016 (% change ± SD, not absolute values)
- Wu 2016 (group assignments only)
- Zappe 2015 (means without SDs, outcome mismatch)
- Neutel 2005 (means without SDs)
- Alessi 2014 (median/IQR, not mean/SD)
- Ledgerwood 2014 (N only, qualitative results)
- Halpern 2015 (% only, per-arm N missing)

### No Data (4 studies)
- Kumana 2003: "no apparent excess" - no counts
- Imoto 2012: "significant difference" - no pain scores
- Foley 2003: strength/function mentioned - no pain data
- Medenblik 2020: "did not differ" - no rates

## Key Findings

### Challenges
1. **Abstract insufficiency:** 73% (11/15) lack complete outcome data in abstract+results_text
2. **Outcome mismatch:** Specified outcome ≠ reported outcome in several studies
3. **Incomplete reporting:** Common to report % or means without denominators/SDs
4. **Qualitative results:** "Significant difference" without actual numbers

### Implications for Gold Standard
1. **Full-text required:** Abstract/results snippets insufficient for most studies
2. **Table extraction critical:** 2×2 tables, summary statistics tables needed
3. **Verify outcome alignment:** Check specified outcome matches reported data
4. **Flag partial vs complete:** Distinguish usable from unusable extractions
5. **Document assumptions:** When computing events from %, state clearly

## Files

- `clean_batch_r1.json`: Input (15 studies)
- `clean_results_r1.json`: Output (manual extraction results)
- `EXTRACTION_SUMMARY_r1.md`: Detailed analysis
- `README_r1.md`: This file
- `extract_outcomes.py`: Initial automated attempt (13% success)
- `manual_extraction.py`: Final manual extraction script

## Validation

```bash
# Verify output structure
python -c "import json; data=json.load(open('clean_results_r1.json','r',encoding='utf-8')); \
  print(f'Total: {len(data)}'); \
  print(f'Found: {sum(1 for d in data if d[\"found\"])}'); \
  print(f'Complete: {sum(1 for d in data if d[\"point_estimate\"] is not None or d[\"intervention_events\"] is not None)}');"
```

Expected output:
```
Total: 15
Found: 11
Complete: 2
```

## Next Steps

For Round 2+:
1. Request full-text PDFs for partial extraction studies
2. Use table extraction tools for structured data
3. Verify outcome definitions against study protocols
4. Cross-check computed values (% × N) against tables if available
5. Consider separate categories: complete / computable / partial / none

---

**Quality assurance:** All extractions verified against source text.
**Reproducibility:** Re-run `manual_extraction.py` to regenerate output.
