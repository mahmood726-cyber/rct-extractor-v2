# Extraction Summary - clean_batch_r1.json

**Date:** 2026-02-14
**Input:** C:\Users\user\rct-extractor-v2\gold_data\mega\clean_batch_r1.json (15 entries)
**Output:** C:\Users\user\rct-extractor-v2\gold_data\mega\clean_results_r1.json

## Extraction Rules Applied

1. **Only extract numbers that ACTUALLY APPEAR in the text** (abstract + results_text fields)
2. **NEVER fabricate or guess numbers**
3. For binary outcomes: look for event counts (e.g., "12/45", "27%") for BOTH groups
4. For continuous outcomes: look for means and SDs for BOTH groups
5. If percentages found, compute counts = round(percentage × N) ONLY if N is clearly stated
6. Quote exact source text (max 200 chars)

## Results Summary

**Total entries:** 15
**Entries with extractable data:** 11/15 (73.3%)
**Entries with NO extractable data:** 4/15 (26.7%)

### Breakdown by Data Type Found

| Category | Count | Studies |
|----------|-------|---------|
| **Direct effect estimate** (OR/RR/MD with CI) | 1 | Ladapo 2020 |
| **Raw binary data** (events/N both groups) | 1 | Shi 2012 |
| **Raw continuous data** (mean±SD both groups) | 0 | None |
| **Partial data only** (N, %, means without SD) | 9 | See below |
| **No extractable data** | 4 | Kumana 2003, Imoto 2012, Foley 2003, Medenblik 2020 |

## Detailed Findings

### 1. Complete Extraction (2 studies)

#### Ladapo 2020 (smoking cessation)
- **Found:** OR 2.56 (95% CI 0.84–7.83)
- **Source:** "odds ratio, 2.56; 95% CI, 0.84 to 7.83, P=0.10"
- **Also found:** 19.6% vs 8.9% but total N not clear in excerpt

#### Shi 2012 (proteinuria - secondary outcome)
- **Found:** 7/9 vs 0/9 (antihypertensive drug dosage reduction)
- **Source:** "reduced in 7 of 9 cases...in the allopurinol group compared to 0 of 9 cases in the control group"
- **Note:** Primary outcome (proteinuria) not quantified in excerpt

### 2. Partial Extraction (9 studies)

#### Fraser 2017 (smoking cessation)
- **Found:** 21.6% vs 13.8%, n=948 vs n=952
- **Can compute:** events = round(0.216×948)=205 vs round(0.138×952)=131
- **Issue:** Used percentage × N calculation (allowed per rules)

#### Perez-Jimenez 2023 (breastfeeding)
- **Found:** N=40 each group, 3 losses
- **Missing:** Event counts not reported

#### Jo 2016 (creatinine clearance)
- **Found:** Change -41.3% ± 26.1% vs -21.1% ± 45.1%, n=23 vs n=20
- **Issue:** Percentage changes, not absolute values; outcome mismatch (reported protein-to-creatinine ratio not creatinine clearance)

#### Wu 2016 (adverse events)
- **Found:** Group assignments (A, B, C, D)
- **Missing:** Event counts

#### Zappe 2015 (all-cause mortality)
- **Found:** Mean SBP changes -10.6, -13.3 mmHg (various groups)
- **Issue:** Outcome mismatch (reported BP not mortality); no SDs

#### Neutel 2005 (24h SBP)
- **Found:** Mean BP reductions -9.0/-6.9 vs -10.4/-7.7 mmHg
- **Missing:** SDs, n=44 total (breakdown unclear)

#### Alessi 2014 (smoking cessation)
- **Found:** Median 51.7% [IQR 62.8%] vs 0% [IQR 32.1%], n=24 vs n=21
- **Issue:** Median/IQR not mean/SD; "percent days CO-negative" not binary cessation

#### Ledgerwood 2014 (smoking cessation)
- **Found:** N=81, 3 groups
- **Missing:** Specific abstinence rates ("significant reductions" only)

#### Halpern 2015 (smoking cessation)
- **Found:** 9.4–16.0% (4 incentive arms) vs 6.0% (usual care), N=2538 total
- **Missing:** Per-arm N breakdown

### 3. No Extraction (4 studies)

#### Kumana 2003 (all-cause death)
- **Reason:** "no apparent excess of adverse events" – no death counts

#### Imoto 2012 (knee pain)
- **Reason:** "statistically significant difference" – no actual pain scores

#### Foley 2003 (knee pain)
- **Reason:** Mentions strength/functional gains – no pain severity numbers

#### Medenblik 2020 (smoking cessation)
- **Reason:** "did not differ" – no specific rates

## Quality Assessment

### High Quality Extractions (directly usable)
1. **Ladapo 2020:** OR with CI ✓
2. **Shi 2012:** Binary counts (7/9 vs 0/9) ✓

### Medium Quality (computable with assumptions)
3. **Fraser 2017:** Can compute events from % × N

### Low Quality (partial data, cannot compute effect)
4–11. Remaining 8 studies with partial data

### No Data
12–15. 4 studies with no extractable outcome data

## Lessons Learned

1. **Abstract/results text often insufficient:** Many studies only provide qualitative statements ("significant difference") without numbers
2. **Outcome mismatch:** Specified outcome doesn't match reported outcome (e.g., mortality → BP, creatinine clearance → proteinuria %)
3. **Incomplete reporting:** Event counts often missing even when percentages/means reported
4. **Need full text:** Abstract+results snippets rarely contain complete 2×2 tables or mean±SD for both groups
5. **Percentage reporting:** Common to report percentages without raw counts (requires N × % calculation)

## Recommendations

For gold standard creation:
1. **Full-text access required** for most studies
2. **Tables are critical** – rarely extractable from prose alone
3. **Verify outcome alignment** between specified and reported outcomes
4. **Flag partial extractions** separately from complete extractions
5. **Document calculation steps** when computing events from percentages

---

**Extraction completed by:** Claude Sonnet 4.5
**Method:** Manual review of abstract + results_text fields
**Confidence:** High for found=true entries, reasoning documented for each
