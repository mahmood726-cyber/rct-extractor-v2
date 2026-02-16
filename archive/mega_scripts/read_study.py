#!/usr/bin/env python3
"""Read individual studies from clean_batch_4.json"""

import json
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python read_study.py <study_number>")
        sys.exit(1)

    study_num = int(sys.argv[1]) - 1  # 0-indexed

    with open(r"C:\Users\user\rct-extractor-v2\gold_data\mega\clean_batch_4.json", 'r', encoding='utf-8') as f:
        studies = json.load(f)

    if study_num >= len(studies):
        print(f"Study {study_num+1} not found. Only {len(studies)} studies available.")
        sys.exit(1)

    study = studies[study_num]

    print(f"=== Study {study_num+1}/{len(studies)} ===")
    print(f"ID: {study.get('study_id')}")
    print(f"Outcome: {study.get('outcome')}")
    print(f"Data type: {study.get('data_type')}")
    print(f"Old status: {study.get('old_status')}")
    print()
    print("=== ABSTRACT ===")
    print(study.get('abstract', '')[:2000])
    print()
    print("=== RESULTS TEXT ===")
    print(study.get('results_text', '')[:2000])
    print()
    if study.get('existing_extractions'):
        print("=== EXISTING EXTRACTIONS ===")
        for ext in study['existing_extractions']:
            print(json.dumps(ext, indent=2))

if __name__ == "__main__":
    main()
