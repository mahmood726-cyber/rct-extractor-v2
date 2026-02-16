# Manual Extraction Results: Batch r23

## Overview

This directory contains manual extraction results for batch r23 from the mega gold standard.

**Date**: 2026-02-14
**Extractor**: Claude Opus 4.6
**Input**: `clean_batch_r23.json` (15 studies)
**Output**: `clean_results_r23.json` (15 extraction results)

## Results Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| Total entries | 15 | 100% |
| Successful extractions | 7 | 46.7% |
| No data found | 8 | 53.3% |

### By Data Type

| Data Type | Count |
|-----------|-------|
| Binary outcomes | 5 |
| Continuous outcomes | 2 |
| Direct effect estimates | 0 |

## Files

- **clean_batch_r23.json**: Input file with study excerpts and requested outcomes
- **clean_results_r23.json**: Output file with extracted numerical data
- **extract_r23.py**: Python script used for manual extraction
- **EXTRACTION_REPORT_r23.txt**: Detailed extraction report with all sources
- **README_r23.md**: This file

## Extraction Principles

All extractions followed strict rules:

1. **ONLY extract explicitly stated data** - never calculate, infer, or impute
2. **Require exact counts for binary data** - percentages alone are insufficient
3. **Match requested outcome exactly** - e.g., "change" vs "follow-up value"
4. **Provide source quotes** - every extraction includes verbatim text
5. **Document reasoning** - especially for found=false cases

## Quality Assurance

- All 15 entries have complete required fields
- Source quotes verified against input text
- Calculations spot-checked (e.g., Zeng 2017: 1/50=2%, 17/50=34%)
- JSON format validated

## Successful Extractions (7)

1. **Orbo 2014** - LNG-IUS response rate: 53/53 vs 46/48
2. **Bruintjes 2019** - Quality of recovery: 179.5±13.6 vs 172.3±19.2
3. **Cybulski 2003** - Sinus rhythm restoration: 88/106 vs 24/54
4. **Beatch 2016** - AF conversion: 59/129 vs 1/68
5. **Zapata 2014** - Time in SpO2 target: 58±4% vs 33.7±4.7%
6. **Zeng 2017** - Transfusion rate: 1/50 vs 17/50
7. **Peng 2021** - DVT occurrence: 0/47 vs 0/46

## Common Reasons for No Data Found (8)

- **Percentages without sample sizes** (Taha 2022, Tsukada 2019)
- **Qualitative results only** (Zendedel 2015)
- **Wrong outcome measure reported** (Alavi Foumani, Yen 2021, Yen 2017)
- **Requested outcome not in excerpt** (Bjerk 2013)
- **Events without denominators** (Xue 2021)

## Usage

The output file `clean_results_r23.json` can be used to:

1. Validate automated extraction systems
2. Build gold standard datasets
3. Analyze extraction success rates by outcome type
4. Train ML models for outcome extraction

## Format

Each entry in `clean_results_r23.json` contains:

```json
{
  "study_id": "string",
  "found": boolean,
  "effect_type": "OR"|"RR"|"MD"|"SMD"|"NONE",
  "point_estimate": number|null,
  "ci_lower": number|null,
  "ci_upper": number|null,
  "intervention_events": number|null,
  "intervention_n": number|null,
  "control_events": number|null,
  "control_n": number|null,
  "intervention_mean": number|null,
  "intervention_sd": number|null,
  "control_mean": number|null,
  "control_sd": number|null,
  "source_quote": "string",
  "reasoning": "string"
}
```

## Notes

- All numerical values are exactly as stated in source text
- No rounding or precision adjustments applied
- Null values indicate data not available (never estimated)
- Source quotes are verbatim from results_text field
- Reasoning explains extraction logic or why data wasn't found
