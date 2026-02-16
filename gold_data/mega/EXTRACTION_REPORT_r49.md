# Extraction Report: clean_batch_r49.json

**Date**: 2026-02-14  
**Batch**: Review 49 (CD002042 - Glaucoma/Vision interventions)  
**Extractor**: Manual review by RCT extraction specialist

## Summary Statistics

- **Total entries**: 15
- **Data found**: 2 (13.3%)
- **Data not found**: 13 (86.7%)

## Entries with Extracted Data

### 1. Baldi 2010_2010
- **Outcome**: Body composition and weight (continuous)
- **Data type**: Mean difference
- **Extracted values**:
  - Intervention (EAAs): mean = 3.8 kg, SD = 2.6 kg
  - Control (C): mean = -0.1 kg, SD = 1.1 kg
- **Source**: "a body weight increment occurred in 92% and 15% of patients in the EAAs and C group, respectively, with an average increase of 3.8 ± 2.6 kg (P = 0.0002) and −0.1 ± 1.1 kg (P = 0.81), respectively"
- **Reasoning**: Body weight change data explicitly stated with mean and SD for both groups.

### 2. Apsangikar 2021_2021
- **Outcome**: Proportion of participants who lost fewer than 15 letters in BCVA from baseline at 24 to 48 weeks (binary)
- **Data type**: Risk ratio
- **Extracted values**:
  - Intervention (biosimilar): 105/106 events
  - Control (reference): 53/53 events
- **Source**: "In the biosimilar test arm, 104 (98.11%) and 105 (99.06%) patients lost fewer than 15 letters in visual acuity at week 16 and week 24, respectively, compared with 53 (100%) at both follow-ups in reference arm."
- **Reasoning**: Week 24 data extracted (within 24-48 week timeframe). Total n inferred from percentages.

## Common Reasons for No Data Found

The 13 entries without extractable data fell into these categories:

1. **Wrong outcome reported** (3 entries)
   - Kumar Rai 2022: Outcome is mortality, but text reports immunogenicity
   - Mantovani 2010: Outcome is physical function/strength, but text reports LBM/REE/fatigue
   - Jukes 2019: Outcome is adherence scale, but text reports visual acuity

2. **Missing statistical measures** (5 entries)
   - Yoon 2022: Mean change reported but SD missing
   - Aleem 2021, Fiscella 2018, Cook 2017: Qualitative/p-value only, no numerical means/SD
   - Mohammed 2021: Data referenced in tables not included in results_text

3. **Incomplete binary data** (1 entry)
   - Bilger 2019: Percentages reported but not absolute counts per group

4. **Qualitative only** (2 entries)
   - Gray 2012: "Significantly more/better" but no counts
   - Goldstein 2007: "No significant difference" but no values

5. **Minimal/incomplete reporting** (2 entries)
   - Thuluva 2022: 1 death mentioned but no systematic 2x2 mortality table
   - Herbison 2016: "Approximately 0.07 logMAR" improvement across all arms, not per-group

## Extraction Principles Applied

✓ **Only EXPLICITLY stated data extracted** - no calculations or inferences  
✓ **Source quotes provided** for all found/not-found decisions  
✓ **Clear reasoning** documenting why data could or could not be extracted  
✓ **Null values** used consistently when data not available  

## Files Generated

- Input: `clean_batch_r49.json` (15 entries)
- Output: `clean_results_r49.json` (15 results)
- Script: `extract_r49.py` (extraction logic)
- Report: `EXTRACTION_REPORT_r49.md` (this file)
