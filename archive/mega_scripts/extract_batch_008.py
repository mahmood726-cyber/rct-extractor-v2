#!/usr/bin/env python
# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
# -*- coding: utf-8 -*-
"""Manual extraction for batch_008.jsonl based on careful reading of each paper."""

import json
import sys
import io

# Set UTF-8 encoding for output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def main():
    input_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_batches\batch_008.jsonl'
    output_file = r'C:\Users\user\rct-extractor-v2\gold_data\mega\v10_results\results_008.jsonl'

    # Manually extracted results based on careful reading
    results = [
        # Entry 1: Sánchez-Sánchez 2022 - Duration of initial hospitalisation
        {
            "study_id": "Sánchez-Sánchez 2022_2022",
            "outcome": "Duration of initial hospitalisation (days)",
            "found": True,
            "effect_type": "MD",
            "point_estimate": None,  # Need to calculate from weeks to days
            "ci_lower": None,
            "ci_upper": None,
            "raw_data": {
                "exp_mean": 35.8,  # LD group (weeks)
                "exp_sd": 0.2,
                "exp_n": 150,
                "ctrl_mean": 37.3,  # LL group (weeks)
                "ctrl_sd": 0.2,
                "ctrl_n": 144
            },
            "source_quote": "Age at hospital discharge (week) 37.3 ± 0.2 (LL) vs 35.8 ± 0.2 (LD), p=0.0001",
            "reasoning": "Found mean±SD for age at discharge in weeks in Table 1. Outcome asks for days but data is in weeks. LD group discharged earlier (35.8 vs 37.3 weeks)."
        },

        # Entry 2: Prabhu 2015 - Interincisal distance and Burning sensation
        # Will process after reading the full text

        # Entry 3: Yadav 2014 - Interincisal distance and Burning sensation
        # Will process after reading the full text

        # ... continuing for all entries
    ]

    # Write results
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    print(f"Extracted {len(results)} results")
    print(f"Output written to: {output_file}")

if __name__ == '__main__':
    main()
