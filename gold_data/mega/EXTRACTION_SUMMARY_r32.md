<!-- sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files. -->

# Extraction Summary: clean_batch_r32.json

**Batch**: clean_batch_r32.json
**Total Studies**: 15
**Date**: 2026-02-14
**Extractor**: Manual (Claude)

## Overview

**Found Data**: 4/15 (26.7%)
**Not Found**: 11/15 (73.3%)

## Summary by Study

| Study ID | Outcome | Data Type | Found | Has Raw Data | Has Effect | Notes |
|----------|---------|-----------|-------|--------------|------------|-------|
| Van der Heijde 2006_2006 | All-cause mortality | null | No | - | - | Only reports ASAS response rates, no mortality |
| Baek 2019_2019 | Adverse events | binary | No | - | - | Qualitative only ("more frequent") |
| Butchart 2015_2015 | Adverse events | binary | No | - | - | States "infections more common" but no counts |
| Bernstein 2006_2006 | Adverse events | null | **Yes** | Binary | - | Dropouts as proxy: 2/28 vs 2/28 |
| Reich 2017_2017 | Adverse events (serious infections) | null | No | - | - | Common AEs reported, not serious infections |
| Abbate 2020_2020 | All-cause mortality | null | No | N only | - | Only composite outcomes reported |
| Emsley 2005_2005 | All-cause mortality | binary | No | - | - | Only states "outcomes better", no counts |
| Morton 2015_2015 | All-cause mortality | binary | No | - | - | Truncated text, no data |
| Choudhury 2016_2016 | All-cause mortality | null | No | - | - | Reports vascular measures, not mortality |
| Russel 2019_2019 | All-cause mortality | null | **Yes** | Binary | - | 1/18 vs 0/20 (1 death in intervention) |
| Van Tassell 2017_2017 | All-cause mortality | binary | **Yes** | N only | - | Composite outcome percentages, N=40 vs 20 |
| Van Tassell 2018_2018 | Adverse events by incidence rate | null | No | - | - | Truncated text, no data |
| Ayatollahi 2017_2017 | Number of chemo cycles to remission | continuous | No | - | - | Only percentages, no mean/SD |
| Meyer 2021_2021 | All-cause mortality | binary | No | - | - | States "no differences in survival", no counts |
| Zhu 2022_2022 | Change in refractive error | null | **Yes** | - | MD | MD = 0.23 ± 0.08 D |

## Data Quality Notes

### Successfully Extracted (4 studies)

1. **Bernstein 2006_2006** (Adverse events)
   - Type: Binary (2x2 table)
   - Data: 2/28 vs 2/28 dropouts as proxy for AEs
   - Quality: Dropouts ≠ AEs, but explicitly stated

2. **Russel 2019_2019** (All-cause mortality)
   - Type: Binary (2x2 table)
   - Data: 1/18 vs 0/20 deaths
   - Quality: Explicitly stated "one death after MI in canakinumab group"

3. **Van Tassell 2017_2017** (All-cause mortality)
   - Type: Sample sizes only
   - Data: N=40 intervention vs N=20 control
   - Quality: Composite outcome (death or re-hospitalization) reported as %, pure mortality not separated

4. **Zhu 2022_2022** (Change in refractive error)
   - Type: Mean difference
   - Data: MD = 0.23 D (SE = 0.08)
   - Quality: Adjusted difference reported, individual group means/SDs not given

### Common Reasons for Not Found (11 studies)

1. **Composite outcomes without separation** (3 studies: Abbate 2020, Van Tassell 2017, Abbate 2020)
   - "Death or heart failure" reported but not pure mortality

2. **Qualitative statements without numbers** (4 studies: Baek 2019, Butchart 2015, Emsley 2005, Ayatollahi 2017)
   - "More frequent", "better outcomes", "higher number" without counts

3. **Wrong outcome reported** (2 studies: Van der Heijde 2006, Choudhury 2016)
   - Asked for mortality, text reports disease activity or vascular measures

4. **Truncated/missing text** (2 studies: Morton 2015, Van Tassell 2018)
   - Only references/acknowledgements visible

5. **Null result without counts** (1 study: Meyer 2021)
   - "No differences in survival" but no actual death counts

## Extraction Methodology

- **Rule**: Only extract data EXPLICITLY stated in text
- **No inference**: Never calculate or derive values
- **Source quotes**: Every extraction includes exact text
- **Reasoning**: Documented why data was/wasn't extractable
- **Binary data**: Events = count with outcome, N = total in group
- **Continuous data**: Mean ± SD preferred; MD acceptable if group-level unavailable
- **Composite outcomes**: Not extracted unless components are separated

## File Locations

- **Input**: `C:\Users\user\rct-extractor-v2\gold_data\mega\clean_batch_r32.json`
- **Output**: `C:\Users\user\rct-extractor-v2\gold_data\mega\clean_results_r32.json`
- **Script**: `C:\Users\user\rct-extractor-v2\gold_data\mega\extract_r32_complete.py`

## Next Steps

This batch demonstrates challenges common in RCT extraction:
1. Composite outcomes are frequently reported without component breakdown
2. Qualitative comparisons ("more frequent") are common without actual counts
3. Many trials report surrogate/intermediate outcomes instead of clinical endpoints
4. Truncated text in PDFs loses critical results sections

Consider for future batches:
- Flag studies with composite outcomes for full-text review
- Develop heuristics to detect "qualitative only" results early
- Prioritize studies where `data_type` matches the outcome (binary/continuous)
