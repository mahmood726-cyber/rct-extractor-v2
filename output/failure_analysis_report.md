# Extraction Failure Analysis Report

Generated: 2026-02-03T19:12:46.104127

## Summary
- Total PDFs analyzed: 58
- Zero-extraction PDFs: 15
- Extractions missing CI: 66

## Zero-Extraction Categories

### NON_RCT: 14 PDFs
- **PMC10148668.pdf**: Found 4 non-RCT keywords
- **PMC10719107.pdf**: Found 5 non-RCT keywords
- **PMC11187303.pdf**: Found 2 non-RCT keywords
- **PMC11303790.pdf**: Found 4 non-RCT keywords
- **PMC11512672.pdf**: Found 2 non-RCT keywords
- ... and 9 more

### TABLE_ONLY: 1 PDFs
- **PMC12691396.pdf**: Found 81 table-like lines

## Missing CI Categories

### IN_TABLE: 36 extractions
- **PMC10052556.pdf**: RR = 0.42
  - Evidence: Found CI (0.3, 0.84) in table-like format
- **PMC10052556.pdf**: RR = 0.46
  - Evidence: Found CI (0.3, 0.84) in table-like format
- **PMC10052556.pdf**: RR = 0.62
  - Evidence: Found CI (0.3, 0.84) in table-like format
- **PMC12002045.pdf**: RR = 1.06
  - Evidence: Found CI (0.92, 1.22) in table-like format
- **PMC12266184.pdf**: HR = 0.75
  - Evidence: Found CI (0.63, 0.9) in table-like format
- ... and 31 more

### NOT_REPORTED: 29 extractions
- **PMC12206259.pdf**: HR = 0.8
  - Evidence: Ground truth indicates no CI reported
- **PMC12206259.pdf**: HR = 1.0
  - Evidence: Ground truth indicates no CI reported
- **PMC12206259.pdf**: HR = 0.9
  - Evidence: Ground truth indicates no CI reported
- **PMC12206259.pdf**: HR = 3.88
  - Evidence: Ground truth indicates no CI reported
- **PMC12312311.pdf**: ARD = -15.18
  - Evidence: Ground truth indicates no CI reported
- ... and 24 more

### TEXT_FRAGMENTED: 1 extractions
- **PMC12723918.pdf**: HR = 0.45
  - Evidence: Found CI (0.23, 0.88) but text appears fragmented

## Recommendations

### High Priority Fixes
2. **IN_TABLE**: Implement table extraction using pdfplumber
4. **NON_RCT**: Improve corpus curation to exclude non-RCT papers