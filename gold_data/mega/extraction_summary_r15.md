# Extraction Summary for clean_batch_r15.json

**Date:** 2026-02-14
**Batch file:** `clean_batch_r15.json`
**Output file:** `clean_results_r15.json`
**Total studies:** 15
**Extraction success rate:** 7/15 (46.7%)

## Extraction Results

### Successfully Extracted (7 studies)

1. **Tabak 2012_2012** - Fruit and vegetable intake
   - Type: Continuous (MD)
   - Data: intervention mean=1.5, SD=2.5 vs control mean=-0.3, SD=2.7
   - Note: Change scores for vegetable availability

2. **Kamath 2021_2021** - Function (AOFAS)
   - Type: Continuous (MD)
   - Data: intervention mean=78.783 vs control mean=71.211
   - Note: SDs not reported; values from "fair results" subgroups

3. **Levin 2011_2011** - Participants abstinent at end of treatment
   - Type: Binary (percentages only)
   - Data: dronabinol 17.7% vs placebo 15.6%
   - Note: Denominators not provided in results_text

4. **Levin 2016_2016** - Participants abstinent at end of treatment
   - Type: Binary (percentages only)
   - Data: medication 27.9% vs placebo 29.5%
   - Note: Denominators not provided in results_text

5. **Palefsky 2022_2022** - Development of anal cancer
   - Type: Binary
   - Data: treatment events=9, active-monitoring events=21
   - Note: Denominators not stated (abstract mentions n=4446, 1:1 randomization)

6. **Verhaeghe 2021_2021** - Operative delivery
   - Type: Binary
   - Data: manual rotation 35/117 (29.9%) vs expectant management 40/119 (33.6%)
   - Note: Complete data with events and denominators

7. **Beeckman 2021_2021** - Pressure ulcer
   - Type: Binary (RR reported)
   - Data: RR=0.64 (95% CI 0.41-0.99), treatment 4.0% vs control 6.3%
   - Note: Direct RR and CI; total n=1605 but n per group not stated

### Not Extracted (8 studies)

1. **Roset-Salla 2016_2016** - Fruit and vegetable intake
   - Reason: Only relative change scores reported (5.8 points improvement in Gerber index), not raw means/SDs

2. **Verbestel 2014_2014** - Fruit and vegetable intake
   - Reason: No specific numerical data; only statement that "no intervention effects" and consumption decreased in both groups

3. **Wyse 2012_2012** - Fruit and vegetable intake
   - Reason: Only P-values reported (P<0.001 at 2mo, P=0.021 at 6mo), no means/SDs/counts

4. **Kulkarni 2015_2015** - Function (binary: excellent/good/satisfactory)
   - Reason: Only qualitative statement ("slightly better but not significant"), no counts

5. **Gunerhan 2009_2009** - Infectious complications
   - Reason: Only statement that "groups did not differ", no specific counts for infectious complications

6. **Harvey 2012_2012** - Maternal adverse events
   - Reason: results_text truncated, contains only methods section

7. **Roth 2013_2018** - Gestational diabetes
   - Reason: Only statement that "groups were similar", no specific counts for gestational diabetes

8. **Moriya 2015_2015** - Non-infectious complications
   - Reason: Data quality issue - results_text appears to be from wrong paper (materials engineering, not clinical trial)

## Key Observations

### Data Quality Issues
- **Moriya 2015:** Wrong paper content (materials science instead of clinical trial)
- **Harvey 2012:** Truncated results_text (only methods visible)

### Common Reasons for Extraction Failure
1. **P-values only** (no effect sizes): 1 study
2. **Qualitative descriptions only**: 3 studies
3. **Relative/change scores without raw data**: 1 study
4. **Truncated or wrong text**: 2 studies
5. **Percentages without denominators**: Partial data in 3 "found" studies

### Partial Extractions
Three studies (Levin 2011, Levin 2016, Palefsky 2022) were marked as "found" but have incomplete data:
- Percentages or event counts given but missing denominators
- Would need full text or supplementary materials for complete extraction

## Recommendations

1. **For Moriya 2015:** Re-extract results_text from correct source
2. **For Harvey 2012:** Extract complete results section
3. **For percentage-only studies:** Attempt to recover sample sizes from methods or full text
4. **For qualitative-only studies:** May be inherently unextractable without access to raw data tables

## File Locations

- Batch file: `C:\Users\user\rct-extractor-v2\gold_data\mega\clean_batch_r15.json`
- Results file: `C:\Users\user\rct-extractor-v2\gold_data\mega\clean_results_r15.json`
- Extraction script: `C:\Users\user\rct-extractor-v2\gold_data\mega\extract_r15.py`
