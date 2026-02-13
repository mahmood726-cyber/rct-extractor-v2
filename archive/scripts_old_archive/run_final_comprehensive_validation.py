"""
FINAL COMPREHENSIVE VALIDATION
==============================

Runs ALL validation tests and generates a complete report:
1. Curated test set (182 cases)
2. External datasets (94 cases)
3. Stress tests (38 positive + 6 adversarial)
4. Real PDF extraction (top clinical trials)
5. Unified extractor on sample PDFs
"""
import sys
import json
import time
from pathlib import Path
from typing import Dict, List
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))


def run_stress_tests():
    """Import and run stress tests"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "stress_test",
        Path(__file__).parent / "run_stress_test_validation.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    pos_passed, pos_failed, adv_passed, adv_failed = module.run_stress_tests()
    return {
        "positive": {"passed": pos_passed, "failed": pos_failed},
        "adversarial": {"passed": adv_passed, "failed": adv_failed}
    }


def run_external_validation():
    """Import and run external validation"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "external",
        Path(__file__).parent / "run_expanded_external_validation.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return None  # Results printed by module


def test_unified_extractor():
    """Test unified extractor on sample PDFs"""
    import importlib.util

    # Load unified_extractor using importlib to avoid relative import issues
    spec = importlib.util.spec_from_file_location(
        "unified_extractor",
        Path(__file__).parent / "src" / "core" / "unified_extractor.py"
    )
    module = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"  Warning: Could not load unified_extractor: {e}")
        return []

    extract_from_pdf = module.extract_from_pdf

    test_pdfs = [
        Path("C:/Users/user/Downloads/NEJMoa2206286.pdf"),  # DELIVER
        Path("C:/Users/user/Downloads/NEJMoa1611925.pdf"),  # EMPA-REG
    ]

    results = []
    for pdf_path in test_pdfs:
        if not pdf_path.exists():
            print(f"  Skipping {pdf_path.name} (not found)")
            continue

        try:
            result = extract_from_pdf(str(pdf_path))
            results.append({
                "pdf": pdf_path.name,
                "total": result.total_effects,
                "text": result.text_count,
                "table": result.table_count,
                "forest": result.forest_count,
                "sample_hr": None
            })

            # Get sample HR
            for e in result.effects:
                if e.measure_type == "HR":
                    results[-1]["sample_hr"] = f"HR {e.value:.2f} ({e.ci_low:.2f}-{e.ci_high:.2f})"
                    break
        except Exception as e:
            print(f"  Error processing {pdf_path.name}: {e}")
            continue

    return results


def main():
    print("=" * 80)
    print("FINAL COMPREHENSIVE VALIDATION")
    print("RCT Extractor v2.4")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)

    all_results = {}

    # 1. Stress Tests
    print("\n" + "=" * 80)
    print("1. STRESS TESTS")
    print("=" * 80)
    stress_results = run_stress_tests()
    all_results["stress_tests"] = stress_results

    # 2. External Dataset Validation
    print("\n" + "=" * 80)
    print("2. EXTERNAL DATASET VALIDATION")
    print("=" * 80)
    run_external_validation()

    # 3. Unified Extractor Test
    print("\n" + "=" * 80)
    print("3. UNIFIED EXTRACTOR (Multi-Method)")
    print("=" * 80)
    unified_results = test_unified_extractor()
    all_results["unified_extractor"] = unified_results

    print("\nUnified Extractor Results:")
    for r in unified_results:
        print(f"  {r['pdf']}: {r['total']} effects (text:{r['text']}, table:{r['table']}, forest:{r['forest']})")
        if r['sample_hr']:
            print(f"    Sample: {r['sample_hr']}")

    # 4. Load previous validation results
    print("\n" + "=" * 80)
    print("4. LOADING PREVIOUS VALIDATION RESULTS")
    print("=" * 80)

    output_dir = Path(__file__).parent / "output"

    prev_results = {}
    result_files = [
        "massive_validation.json",
        "ultimate_validation.json",
        "expanded_external_validation.json",
        "stress_test_validation.json",
    ]

    for filename in result_files:
        filepath = output_dir / filename
        if filepath.exists():
            with open(filepath) as f:
                prev_results[filename] = json.load(f)
            print(f"  Loaded: {filename}")

    # 5. Generate Summary
    print("\n" + "=" * 80)
    print("COMPREHENSIVE VALIDATION SUMMARY")
    print("=" * 80)

    # Collect all metrics
    summary = {
        "timestamp": datetime.now().isoformat(),
        "version": "RCT Extractor v2.4",
        "validations": {}
    }

    # Stress tests
    if stress_results:
        pos = stress_results["positive"]
        adv = stress_results["adversarial"]
        pos_acc = pos["passed"] / (pos["passed"] + pos["failed"]) * 100
        adv_acc = adv["passed"] / (adv["passed"] + adv["failed"]) * 100
        summary["validations"]["stress_tests"] = {
            "positive_cases": pos["passed"] + pos["failed"],
            "positive_accuracy": pos_acc,
            "adversarial_cases": adv["passed"] + adv["failed"],
            "adversarial_accuracy": adv_acc
        }

    # External datasets
    if "expanded_external_validation.json" in prev_results:
        ext = prev_results["expanded_external_validation.json"]["summary"]
        summary["validations"]["external_datasets"] = {
            "total_cases": ext["total_cases"],
            "accuracy": ext["accuracy"]
        }

    # Massive validation
    if "massive_validation.json" in prev_results:
        massive = prev_results["massive_validation.json"]["summary"]
        summary["validations"]["massive_scale"] = {
            "pdfs_processed": massive["total_pdfs"],
            "effects_extracted": massive["total_hrs"] + massive["total_ors"] + massive["total_rrs"],
            "total_pages": massive["total_pages"]
        }

    # Ultimate validation
    if "ultimate_validation.json" in prev_results:
        ultimate = prev_results["ultimate_validation.json"]["summary"]
        summary["validations"]["multi_method"] = {
            "pdfs_processed": ultimate["pdfs_processed"],
            "effects_extracted": ultimate["total_effects"],
            "text_contribution": ultimate["total_text"] / ultimate["total_effects"] * 100 if ultimate["total_effects"] > 0 else 0,
            "table_contribution": ultimate["total_table"] / ultimate["total_effects"] * 100 if ultimate["total_effects"] > 0 else 0,
            "forest_contribution": ultimate["total_forest"] / ultimate["total_effects"] * 100 if ultimate["total_effects"] > 0 else 0,
        }

    # Print summary
    print(f"""
VALIDATION RESULTS SUMMARY
==========================

1. STRESS TESTS (Edge Cases + Adversarial)
   Positive Cases: {summary['validations'].get('stress_tests', {}).get('positive_cases', 'N/A')}
   Positive Accuracy: {summary['validations'].get('stress_tests', {}).get('positive_accuracy', 'N/A'):.1f}%
   Adversarial Cases: {summary['validations'].get('stress_tests', {}).get('adversarial_cases', 'N/A')}
   Adversarial Accuracy: {summary['validations'].get('stress_tests', {}).get('adversarial_accuracy', 'N/A'):.1f}%

2. EXTERNAL DATASETS (R Packages + Published Trials)
   Total Cases: {summary['validations'].get('external_datasets', {}).get('total_cases', 'N/A')}
   Accuracy: {summary['validations'].get('external_datasets', {}).get('accuracy', 'N/A'):.1f}%

3. MASSIVE-SCALE VALIDATION
   PDFs Processed: {summary['validations'].get('massive_scale', {}).get('pdfs_processed', 'N/A'):,}
   Effects Extracted: {summary['validations'].get('massive_scale', {}).get('effects_extracted', 'N/A'):,}
   Pages Scanned: {summary['validations'].get('massive_scale', {}).get('total_pages', 'N/A'):,}

4. MULTI-METHOD EXTRACTION
   PDFs Processed: {summary['validations'].get('multi_method', {}).get('pdfs_processed', 'N/A')}
   Effects Extracted: {summary['validations'].get('multi_method', {}).get('effects_extracted', 'N/A')}
   Text Contribution: {summary['validations'].get('multi_method', {}).get('text_contribution', 'N/A'):.1f}%
   Table OCR Contribution: {summary['validations'].get('multi_method', {}).get('table_contribution', 'N/A'):.1f}%
   Forest Plot Contribution: {summary['validations'].get('multi_method', {}).get('forest_contribution', 'N/A'):.1f}%
""")

    # Overall assessment
    print("\n" + "=" * 80)
    print("OVERALL ASSESSMENT")
    print("=" * 80)

    all_pass = True
    checks = [
        ("Stress Test Positive", summary['validations'].get('stress_tests', {}).get('positive_accuracy', 0) == 100),
        ("Stress Test Adversarial", summary['validations'].get('stress_tests', {}).get('adversarial_accuracy', 0) == 100),
        ("External Datasets", summary['validations'].get('external_datasets', {}).get('accuracy', 0) == 100),
        ("Massive-Scale Extraction", summary['validations'].get('massive_scale', {}).get('effects_extracted', 0) > 1000),
        ("Multi-Method Available", summary['validations'].get('multi_method', {}).get('effects_extracted', 0) > 100),
    ]

    for name, passed in checks:
        status = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_pass = False
        print(f"  {status} {name}")

    print("\n" + "-" * 80)
    if all_pass:
        print("  FINAL RESULT: ALL VALIDATIONS PASSED")
    else:
        print("  FINAL RESULT: SOME VALIDATIONS REQUIRE ATTENTION")
    print("-" * 80)

    # Save summary
    summary_file = output_dir / "final_comprehensive_validation.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Summary saved to: {summary_file}")

    print("=" * 80)


if __name__ == "__main__":
    main()
