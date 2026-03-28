#!/usr/bin/env python3
"""Scaffold a reusable field-portability bundle for a new specialty."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "field"


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _write_json(path: Path, payload: Dict) -> None:
    _write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _render_field_profile(field_name: str, field_slug: str, author_name: str) -> str:
    return (
        f'field_name: "{field_name}"\n'
        f'field_slug: "{field_slug}"\n'
        "\n"
        "author:\n"
        f'  full_name: "{author_name}"\n'
        '  meta_pmids_file: "author_meta_pmids.json"\n'
        "\n"
        "search:\n"
        "  pubmed_term_override: null\n"
        "  require_meta: true\n"
        "  require_author_name_in_authors: true\n"
        "  require_field_keyword_match: true\n"
        "  field_keywords:\n"
        '    - "keyword1"\n'
        '    - "keyword2"\n'
        "\n"
        "corpus:\n"
        f'  pdf_input_dir: "data/field_portability/{field_slug}/rct_trial_pdfs"\n'
        "\n"
        "validators:\n"
        '  mode: "balanced"\n'
        "  effect_override_confidence: 0.97\n"
        "  rct_override_confidence: 0.99\n"
        "  dual_validator:\n"
        "    enabled: true\n"
        '    provider_a: "rules_a"\n'
        '    provider_b: "rules_b"\n'
        "    min_agreement_confidence: 0.65\n"
        '    conflict_policy: "keep"\n'
        "    max_candidates: 120\n"
        "\n"
        "quality_targets:\n"
        "  min_coverage_on_included_gold: 0.95\n"
        "  max_fp_rate_on_excluded_gold: 0.02\n"
        "  min_effect_type_match_rate: 0.98\n"
        "  min_point_within_10pct_rate: 0.98\n"
        "  min_ci_within_10pct_rate: 0.98\n"
        "\n"
        "paths:\n"
        f'  benchmark_dir: "data/benchmarks/{field_slug}_meta_linked_v1"\n'
        f'  output_dir: "output/{field_slug}_extract_v1"\n'
    )


def _render_readme(field_name: str, field_slug: str) -> str:
    return f"""# {field_name} Field Portability Bundle

This folder is a scaffold for running the extractor workflow in `{field_name}`.

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
- `output/{field_slug}_extract_v1/results.jsonl`
- `output/{field_slug}_extract_v1/results_ai_validated_balanced.jsonl`
- benchmark eval JSON/MD files
"""


def _render_commands_ps1(field_name: str, field_slug: str, author_name: str) -> str:
    return f"""# {field_name} runbook (PowerShell)

# 1) Build field-linked benchmark subset
# Replace <seed_benchmark_cohort_jsonl> with your cohort seed file.
python scripts/build_author_meta_benchmark_subset.py `
  --benchmark-cohort-jsonl <seed_benchmark_cohort_jsonl> `
  --output-dir data/benchmarks/{field_slug}_meta_linked_v1 `
  --author-full-name "{author_name}" `
  --author-meta-pmids-file data/field_portability/{field_slug}/author_meta_pmids.json `
  --require-meta `
  --no-require-cardiology

# 2) Extract field PDFs
python scripts/extract_pdf_corpus.py `
  --input-dir data/field_portability/{field_slug}/rct_trial_pdfs `
  --output-jsonl output/{field_slug}_extract_v1/results.jsonl `
  --summary-json output/{field_slug}_extract_v1/summary.json `
  --summary-md output/{field_slug}_extract_v1/report.md `
  --recursive `
  --workers 2

# 3) Apply deterministic validators
python scripts/apply_ai_validators_to_results.py `
  --input-jsonl output/{field_slug}_extract_v1/results.jsonl `
  --output-jsonl output/{field_slug}_extract_v1/results_ai_validated_balanced.jsonl `
  --summary-json output/{field_slug}_extract_v1/results_ai_validated_balanced_summary.json `
  --validator-mode balanced

# 4) Optional dual-validator audit (no-key fallback)
python scripts/apply_dual_llm_borderline_validators.py `
  --input-jsonl output/{field_slug}_extract_v1/results_ai_validated_balanced.jsonl `
  --output-jsonl output/{field_slug}_extract_v1/results_ai_validated_balanced_dual_rules.jsonl `
  --summary-json output/{field_slug}_extract_v1/results_ai_validated_balanced_dual_rules_summary.json `
  --audit-jsonl output/{field_slug}_extract_v1/results_ai_validated_balanced_dual_rules_audit.jsonl `
  --provider-a rules_a `
  --provider-b rules_b `
  --max-candidates 120 `
  --min-agreement-confidence 0.65 `
  --conflict-policy keep
"""


def _render_commands_sh(field_name: str, field_slug: str, author_name: str) -> str:
    return f"""#!/usr/bin/env bash
set -euo pipefail

# {field_name} runbook (bash)

python scripts/build_author_meta_benchmark_subset.py \\
  --benchmark-cohort-jsonl <seed_benchmark_cohort_jsonl> \\
  --output-dir data/benchmarks/{field_slug}_meta_linked_v1 \\
  --author-full-name "{author_name}" \\
  --author-meta-pmids-file data/field_portability/{field_slug}/author_meta_pmids.json \\
  --require-meta \\
  --no-require-cardiology

python scripts/extract_pdf_corpus.py \\
  --input-dir data/field_portability/{field_slug}/rct_trial_pdfs \\
  --output-jsonl output/{field_slug}_extract_v1/results.jsonl \\
  --summary-json output/{field_slug}_extract_v1/summary.json \\
  --summary-md output/{field_slug}_extract_v1/report.md \\
  --recursive \\
  --workers 2

python scripts/apply_ai_validators_to_results.py \\
  --input-jsonl output/{field_slug}_extract_v1/results.jsonl \\
  --output-jsonl output/{field_slug}_extract_v1/results_ai_validated_balanced.jsonl \\
  --summary-json output/{field_slug}_extract_v1/results_ai_validated_balanced_summary.json \\
  --validator-mode balanced

python scripts/apply_dual_llm_borderline_validators.py \\
  --input-jsonl output/{field_slug}_extract_v1/results_ai_validated_balanced.jsonl \\
  --output-jsonl output/{field_slug}_extract_v1/results_ai_validated_balanced_dual_rules.jsonl \\
  --summary-json output/{field_slug}_extract_v1/results_ai_validated_balanced_dual_rules_summary.json \\
  --audit-jsonl output/{field_slug}_extract_v1/results_ai_validated_balanced_dual_rules_audit.jsonl \\
  --provider-a rules_a \\
  --provider-b rules_b \\
  --max-candidates 120 \\
  --min-agreement-confidence 0.65 \\
  --conflict-policy keep
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--field-name", type=str, required=True, help="Human-readable specialty name.")
    parser.add_argument("--field-slug", type=str, default=None, help="Filesystem-friendly slug; inferred from field name if omitted.")
    parser.add_argument("--author-full-name", type=str, default="Surname Given")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/field_portability"),
        help="Root folder where field bundle is created.",
    )
    parser.add_argument("--force", action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()

    field_name = str(args.field_name).strip()
    if not field_name:
        raise ValueError("--field-name must not be empty")
    field_slug = _slugify(args.field_slug or field_name)
    bundle_dir = args.output_root / field_slug

    if bundle_dir.exists() and any(bundle_dir.iterdir()) and not bool(args.force):
        raise FileExistsError(f"Bundle directory exists and is not empty: {bundle_dir}. Use --force to overwrite files.")
    bundle_dir.mkdir(parents=True, exist_ok=True)

    profile_path = bundle_dir / "field_profile.yaml"
    pmids_path = bundle_dir / "author_meta_pmids.json"
    readme_path = bundle_dir / "README.md"
    notes_path = bundle_dir / "notes.md"
    commands_ps1 = bundle_dir / "commands.ps1"
    commands_sh = bundle_dir / "commands.sh"
    pdf_dir = bundle_dir / "rct_trial_pdfs"
    manifest_path = bundle_dir / "bundle_manifest.json"

    _write_text(profile_path, _render_field_profile(field_name, field_slug, str(args.author_full_name)))
    _write_json(pmids_path, {"pmids": []})
    _write_text(readme_path, _render_readme(field_name, field_slug))
    _write_text(notes_path, "# Notes\n\n- Add field-specific assumptions and caveats.\n")
    _write_text(commands_ps1, _render_commands_ps1(field_name, field_slug, str(args.author_full_name)))
    _write_text(commands_sh, _render_commands_sh(field_name, field_slug, str(args.author_full_name)))
    pdf_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "generated_at_utc": _utc_now(),
        "field_name": field_name,
        "field_slug": field_slug,
        "author_full_name": str(args.author_full_name),
        "bundle_dir": str(bundle_dir).replace("\\", "/"),
        "files": {
            "field_profile_yaml": str(profile_path).replace("\\", "/"),
            "author_meta_pmids_json": str(pmids_path).replace("\\", "/"),
            "commands_ps1": str(commands_ps1).replace("\\", "/"),
            "commands_sh": str(commands_sh).replace("\\", "/"),
            "readme_md": str(readme_path).replace("\\", "/"),
            "notes_md": str(notes_path).replace("\\", "/"),
            "rct_trial_pdfs_dir": str(pdf_dir).replace("\\", "/"),
        },
    }
    _write_json(manifest_path, manifest)

    print(f"Wrote: {profile_path}")
    print(f"Wrote: {pmids_path}")
    print(f"Wrote: {commands_ps1}")
    print(f"Wrote: {commands_sh}")
    print(f"Wrote: {readme_path}")
    print(f"Wrote: {notes_path}")
    print(f"Wrote: {manifest_path}")
    print(f"Created directory: {pdf_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
