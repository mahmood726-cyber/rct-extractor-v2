#!/usr/bin/env python3
"""
Manual extraction for clean_batch_r48.json
Reading each study carefully and extracting explicitly stated data.
"""

import json
import sys

def main():
    # Load the batch
    with open('C:/Users/user/rct-extractor-v2/gold_data/mega/clean_batch_r48.json', 'r', encoding='utf-8') as f:
        studies = json.load(f)

    print(f"Total studies: {len(studies)}\n")

    # Print each study for manual review
    for i, study in enumerate(studies, 1):
        print(f"\n{'='*80}")
        print(f"STUDY {i}: {study['study_id']}")
        print(f"Outcome: {study['outcome']}")
        print(f"Data type: {study.get('data_type', 'unknown')}")
        print(f"Old status: {study.get('old_status', 'unknown')}")
        print(f"{'='*80}")

        # Print existing extractions if any
        if study.get('existing_extractions'):
            print("\nExisting extractions:")
            for ext in study['existing_extractions']:
                print(f"  - {ext.get('effect_type', 'unknown')}: {ext.get('point_estimate')} "
                      f"[{ext.get('ci_lower')}, {ext.get('ci_upper')}]")

        print("\nResults text (first 1500 chars):")
        print(study.get('results_text', '')[:1500])
        print("\n...")

        # Prompt for manual entry
        print(f"\n[Review required for Study {i}]")

    print(f"\n\n{'='*80}")
    print("Review complete. Now proceeding with manual data entry...")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
