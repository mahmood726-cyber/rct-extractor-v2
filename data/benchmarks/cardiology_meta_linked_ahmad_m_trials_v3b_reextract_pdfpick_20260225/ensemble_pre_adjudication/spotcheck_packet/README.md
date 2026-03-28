# Ensemble Spot-Check Packet

- Generated UTC: 2026-02-26T04:53:43.710259+00:00
- Rows sampled: 10
- Bucket counts: {'exclude': 3, 'fill': 1, 'high_conf_include': 3, 'low_conf_include': 3}

## Files

- CSV sheet: `data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225/ensemble_pre_adjudication/spotcheck_packet/spotcheck_sheet.csv`
- JSONL sheet: `data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225/ensemble_pre_adjudication/spotcheck_packet/spotcheck_sheet.jsonl`
- Summary JSON: `data/benchmarks/cardiology_meta_linked_ahmad_m_trials_v3b_reextract_pdfpick_20260225/ensemble_pre_adjudication/spotcheck_packet/spotcheck_summary.json`

## Manual Check Guidance

- Verify `consensus_included` against the PDF.
- If included=true, verify effect type, point estimate, and CI.
- Record corrections in the `manual_check_*` columns.
