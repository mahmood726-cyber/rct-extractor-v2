# Mega Hang Diagnostics Summary

- Generated UTC: 2026-02-18T00:10:03.278074+00:00
- Source diagnostics: `output\mega_hang_diagnostics_upsert_clear_timeouts.jsonl`
- Attempts seen: 200
- Completed attempts: 200
- Pre-only attempts (likely timed out during extraction): 0
- Pipeline timed-out (completed result rows): 196
- Fallback used: 96 attempts, 232 effects

## Timing

- Parser probe: count=0, median=None, p95=None, max=None
- Pipeline elapsed (completed only): count=196, median=8.0685, p95=8.0855, max=8.1225

## Completed Status Mix

- no_extraction: 100
- extracted_no_match: 82
- match: 14
- no_cochrane_ref: 4

## Top Pre-Only Attempts

| Rank | Study ID | PMCID | Parser Probe (s) | PDF Size (bytes) |
|---:|---|---|---:|---:|
