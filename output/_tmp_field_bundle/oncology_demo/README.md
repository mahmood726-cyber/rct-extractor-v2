# Oncology Demo Field Portability Bundle

This folder is a scaffold for running the extractor workflow in `Oncology Demo`.

## Files
- `field_profile.yaml`: field configuration
- `author_meta_pmids.json`: optional manual PMID seed list
- `commands.ps1`: Windows runbook
- `commands.sh`: Bash runbook
- `notes.md`: working notes

## Quick Start
1. Edit `field_profile.yaml` and set keywords, author name, and paths.
2. Add PMIDs to `author_meta_pmids.json` if you want manual control.
3. Put field PDFs in `rct_trial_pdfs/`.
4. Run `commands.ps1` (Windows) or `commands.sh` (bash).

## Expected Outputs
- `output/oncology_demo_extract_v1/results.jsonl`
- `output/oncology_demo_extract_v1/results_ai_validated_balanced.jsonl`
- benchmark eval JSON/MD files
