"""
Comprehensive Validation v2.5 for RCT Extractor
================================================

Combines ALL validation tests:
1. Original stress tests (44 cases)
2. Original external datasets (94 cases)
3. Extended R package datasets (99 cases)
4. Extended stress tests (41 cases)
5. Extended adversarial tests (20 cases)

Total: 298+ test cases
"""
import sys
import json
import importlib.util
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))


def run_module(name: str, filepath: Path):
    """Run a validation module and return results"""
    spec = importlib.util.spec_from_file_location(name, filepath)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"  Error loading {name}: {e}")
        return None


def main():
    print("=" * 80)
    print("COMPREHENSIVE VALIDATION v2.5")
    print("RCT Extractor - All Tests Combined")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)

    base_path = Path(__file__).parent
    results = {}

    # 1. Original Stress Tests (44 cases)
    print("\n" + "=" * 80)
    print("1. ORIGINAL STRESS TESTS")
    print("=" * 80)
    module = run_module("stress_test", base_path / "run_stress_test_validation.py")
    if module:
        pos_p, pos_f, adv_p, adv_f = module.run_stress_tests()
        results["original_stress"] = {
            "positive": {"passed": pos_p, "failed": pos_f},
            "adversarial": {"passed": adv_p, "failed": adv_f}
        }

    # 2. Original External Datasets (94 cases)
    print("\n" + "=" * 80)
    print("2. ORIGINAL EXTERNAL DATASETS")
    print("=" * 80)
    # Load the output file
    ext_file = base_path / "output" / "expanded_external_validation.json"
    if ext_file.exists():
        with open(ext_file) as f:
            ext_data = json.load(f)
        results["original_external"] = {
            "total": ext_data["summary"]["total_cases"],
            "passed": ext_data["summary"]["correct"],  # Key is "correct" not "passed"
            "accuracy": ext_data["summary"]["accuracy"]
        }
        print(f"  Loaded from file: {ext_data['summary']['correct']}/{ext_data['summary']['total_cases']} ({ext_data['summary']['accuracy']:.1f}%)")
    else:
        print("  External validation file not found, running...")
        module = run_module("external", base_path / "run_expanded_external_validation.py")

    # 3. Extended Validation (160 cases)
    print("\n" + "=" * 80)
    print("3. EXTENDED VALIDATION v2")
    print("=" * 80)
    module = run_module("extended", base_path / "run_extended_validation_v2.py")
    if module:
        ext_results = module.main()
        results["extended"] = ext_results

    # Load massive validation results
    print("\n" + "=" * 80)
    print("4. MASSIVE-SCALE VALIDATION (from file)")
    print("=" * 80)
    massive_file = base_path / "output" / "massive_validation.json"
    if massive_file.exists():
        with open(massive_file) as f:
            massive_data = json.load(f)
        results["massive"] = massive_data["summary"]
        print(f"  PDFs Processed: {massive_data['summary']['total_pdfs']:,}")
        print(f"  Effects Extracted: {massive_data['summary']['total_hrs'] + massive_data['summary']['total_ors'] + massive_data['summary']['total_rrs']:,}")
        print(f"  Pages Scanned: {massive_data['summary']['total_pages']:,}")

    # Load ultimate validation results
    print("\n" + "=" * 80)
    print("5. MULTI-METHOD VALIDATION (from file)")
    print("=" * 80)
    ultimate_file = base_path / "output" / "ultimate_validation.json"
    if ultimate_file.exists():
        with open(ultimate_file) as f:
            ultimate_data = json.load(f)
        results["ultimate"] = ultimate_data["summary"]
        print(f"  PDFs Processed: {ultimate_data['summary']['pdfs_processed']}")
        print(f"  Total Effects: {ultimate_data['summary']['total_effects']}")
        print(f"  Text: {ultimate_data['summary']['total_text']} ({ultimate_data['summary']['total_text']/ultimate_data['summary']['total_effects']*100:.1f}%)")
        print(f"  Table: {ultimate_data['summary']['total_table']} ({ultimate_data['summary']['total_table']/ultimate_data['summary']['total_effects']*100:.1f}%)")
        print(f"  Forest: {ultimate_data['summary']['total_forest']} ({ultimate_data['summary']['total_forest']/ultimate_data['summary']['total_effects']*100:.1f}%)")

    # Summary
    print("\n" + "=" * 80)
    print("COMPREHENSIVE VALIDATION SUMMARY v2.5")
    print("=" * 80)

    # Count total cases
    total_cases = 0
    total_passed = 0

    # Original stress tests
    if "original_stress" in results:
        orig = results["original_stress"]
        orig_total = orig["positive"]["passed"] + orig["positive"]["failed"] + orig["adversarial"]["passed"] + orig["adversarial"]["failed"]
        orig_passed = orig["positive"]["passed"] + orig["adversarial"]["passed"]
        total_cases += orig_total
        total_passed += orig_passed

    # Original external
    if "original_external" in results:
        total_cases += results["original_external"]["total"]
        total_passed += results["original_external"]["passed"]

    # Extended validation
    if "extended" in results:
        total_cases += results["extended"]["overall"]["total"]
        total_passed += results["extended"]["overall"]["passed"]

    print(f"""
VALIDATION LAYER SUMMARY
========================

1. ORIGINAL STRESS TESTS (v2.4)
   Positive: {results.get('original_stress', {}).get('positive', {}).get('passed', 'N/A')}/{results.get('original_stress', {}).get('positive', {}).get('passed', 0) + results.get('original_stress', {}).get('positive', {}).get('failed', 0)}
   Adversarial: {results.get('original_stress', {}).get('adversarial', {}).get('passed', 'N/A')}/{results.get('original_stress', {}).get('adversarial', {}).get('passed', 0) + results.get('original_stress', {}).get('adversarial', {}).get('failed', 0)}

2. ORIGINAL EXTERNAL DATASETS (v2.4)
   Cases: {results.get('original_external', {}).get('passed', 'N/A')}/{results.get('original_external', {}).get('total', 'N/A')}

3. EXTENDED VALIDATION (v2.5)
   R Packages: {results.get('extended', {}).get('r_package_validation', {}).get('passed', 'N/A')}/{results.get('extended', {}).get('r_package_validation', {}).get('total', 'N/A')}
   Stress Tests: {results.get('extended', {}).get('extended_stress_tests', {}).get('passed', 'N/A')}/{results.get('extended', {}).get('extended_stress_tests', {}).get('total', 'N/A')}
   Adversarial: {results.get('extended', {}).get('extended_adversarial', {}).get('passed', 'N/A')}/{results.get('extended', {}).get('extended_adversarial', {}).get('total', 'N/A')}

4. MASSIVE-SCALE (Production)
   PDFs: {results.get('massive', {}).get('total_pdfs', 'N/A'):,}
   Effects: {results.get('massive', {}).get('total_hrs', 0) + results.get('massive', {}).get('total_ors', 0) + results.get('massive', {}).get('total_rrs', 0):,}

5. MULTI-METHOD (Text + Table + Forest)
   PDFs: {results.get('ultimate', {}).get('pdfs_processed', 'N/A')}
   Effects: {results.get('ultimate', {}).get('total_effects', 'N/A')}

================================================================================
OVERALL ACCURACY: {total_passed}/{total_cases} ({total_passed/total_cases*100:.1f}%)
================================================================================
""")

    # Save comprehensive results
    output = {
        "timestamp": datetime.now().isoformat(),
        "version": "v2.5",
        "summary": {
            "total_test_cases": total_cases,
            "total_passed": total_passed,
            "accuracy": total_passed / total_cases * 100
        },
        "results": results
    }

    output_file = base_path / "output" / "comprehensive_validation_v2.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"  Results saved to: {output_file}")
    print("=" * 80)

    return output


if __name__ == "__main__":
    main()
