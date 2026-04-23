<!-- sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files. -->

# Multipersona Review Report: RCT Extractor v2/v3/v4

**Date:** 2026-02-05
**Project:** `C:\Users\user\rct-extractor-v2` (256 files, ~142K lines)
**Reviewers:** Planner / Builder / Verifier (3-persona model)

---

## Executive Summary

| Persona | P0 | P1 | P2 | Total |
|---------|----|----|----|----|
| Planner (arch/config) | 3 | 6 | 7 | 16 |
| Builder (math/logic) | 6 | 8 | 7 | 21 |
| Verifier (tests/security) | 2 | 13 | 8 | 23 |
| **After dedup** | **10** | **19** | **15** | **44** |

**Key verdict:** The performance claims (100% sensitivity, 0% FPR, ECE=0.012) are **not credible** due to training/test data leakage, synthetic-only test data, insufficient negative controls, and a heuristic (not empirical) calibration function. The extraction engine itself is substantial engineering (180+ patterns, 4 independent extractors, proof-carrying numbers), but packaging, versioning, and test coverage have severe gaps.

---

## P0 Issues (Must Fix — Blocks Correctness or Shipping)

### P0-1 [Verifier] Training/Test Data Leakage Invalidates All Claims
**Files:** `src/core/enhanced_extractor_v3.py` lines 293, 396; `data/held_out_test_set.py`
The "held-out" test set was never actually held out. Source code comments prove patterns were iteratively added to reach 100%:
- Line 293: `# NEW PATTERNS for held-out test cases`
- Line 396: `# v4.1.1 ADDITIONS - Phase 1 Pattern Gap Closure (HR 96.6% -> 100%)`

Both validation datasets are synthetic single-sentence snippets, not real PDF-extracted text. The 100% sensitivity, 0% FPR, and ECE=0.012 claims are artifacts of overfitting.
**Fix:** Freeze patterns. Build genuinely independent test set from real PMC Open Access PDFs with dual human annotation. Re-run validation and report honest metrics.

### P0-2 [Verifier] JS Bridge Uses eval() on File Contents
**File:** `src/bridges/js_extractor_bridge.py` line 97
`_create_wrapper_script` reads a JS file and `eval()`s it in Node.js. The file path comes from a constructor parameter with no validation or allowlist. If the path is controllable or the file tampered with, this enables arbitrary code execution with full system access.
**Fix:** Remove `eval()` fallback entirely. Use only `require()` with path validation. If the JS bridge is unused in production, remove it or gate behind explicit opt-in.

### P0-3 [Planner] Version Chaos — 8+ Conflicting Version Strings
**Files:** pyproject.toml (`"2.0.0"`), src/\_\_init\_\_.py (`"2.0.0"`), Dockerfile (`"4.0.6"`), API (`"4.1.0"`), extraction_schema (`"4.3.5"`), requirements.txt (`"v4.0.6"`), various run scripts (4.0.3–4.3.1)
No single source of truth. Validation reports stamp different versions. CLI says v2.0 while API says v4.1.0.
**Fix:** Define version once in `src/__init__.__version__`, use `dynamic = ["version"]` in pyproject.toml, grep-replace all others.

### P0-4 [Planner] Core Runtime Deps Missing from pyproject.toml
**Files:** pyproject.toml (only lists pydantic/pyyaml/rapidfuzz); `src/core/unified_extractor.py`, `src/figures/forest_plot_extractor.py`, `src/tables/results_table_extractor.py` — all do unconditional `import numpy`
Anyone installing via `pip install .` gets `ModuleNotFoundError: No module named 'numpy'`. scipy also missing.
**Fix:** Add `numpy>=1.24` and `scipy>=1.10` to pyproject.toml core dependencies.

### P0-5 [Planner] CI Workflows Invoke Scripts with Non-Existent CLI Flags
**Files:** `.github/workflows/test.yml` lines 185, 254
- `python scripts/run_full_ctg_validation.py --sample 100` — script has NO argparse, flag is silently ignored
- `python run_r_package_validation.py --all` — script only accepts `--package/--verbose/--output`, exits with error
**Fix:** Add `--sample` argparse to ctg script; add `--all` flag to r_package script or remove from CI.

### P0-6 [Builder] Strict CI Inequality Rejects Valid Boundary Extractions
**File:** `src/core/enhanced_extractor_v3.py` line 1576
CI consistency check uses `ci_low < value < ci_high` (strict), but plausibility check uses `ci_low <= value <= ci_high` (non-strict). Extractions where point estimate equals a CI boundary (e.g., "HR 0.50, 95% CI 0.50-0.80") are rejected as CI_INCONSISTENT.
**Fix:** Change to `ci_low <= value <= ci_high`.

### P0-7 [Builder] ARD Normalization Fails for Small Percentage Values
**File:** `src/core/enhanced_extractor_v3.py` lines 1882–1891
`normalize_ard()` uses `abs(value) > 1.0` to detect percentages. When ARD is reported as "risk difference -0.5 percentage points" without `%` symbol, all values have `abs() < 1.0`, so function returns raw values as decimal scale — interpreting -0.5 as 50% absolute risk difference.
**Fix:** Extend context window for percentage detection; flag ambiguous cases for review instead of silent interpretation.

### P0-8 [Builder] NNT CI Calculation Wrong When RD CI Crosses Zero
**File:** `src/core/meta_analysis.py` lines 470–481
When RD CI spans zero (e.g., -6% to +1%), the NNT CI is discontinuous (NNTB → ∞ → NNTH). The code uses `abs()` to produce a continuous CI, which is mathematically wrong.
**Fix:** Detect sign change in RD CI bounds. Report NNTB/NNTH separately with infinity gap, or skip NNT CI with warning.

### P0-9 [Builder] ECE=0.012 Claim Is a Hardcoded Heuristic, Not Empirical Calibration
**File:** `src/core/enhanced_extractor_v3.py` lines 1780–1809
`_calibrate_confidence()` is a hand-tuned piecewise linear function with arbitrary breakpoints. It is NOT Platt scaling, isotonic regression, or any standard method. The separate `confidence_calibration.py` implements proper binned calibration but is not connected to the main extractor.
**Fix:** Either wire `ConfidenceCalibrator` from confidence_calibration.py into the extractor, or remove the ECE claim and rename method to `_adjust_confidence`.

### P0-10 [Builder] OddsRatioCI and RiskRatioCI Missing Point-in-CI Validation
**File:** `src/core/models.py` lines 180–185
`HazardRatioCI` validates `ci_low <= hr <= ci_high`, but `OddsRatioCI` only checks `ci_low < ci_high` (not that OR is within CI). `RiskRatioCI` has no validator at all. An OR with value outside its CI passes validation silently.
**Fix:** Add `ci_low <= value <= ci_high` validators to both models.

---

## P1 Issues (Significant — Fix Before Release)

### P1-1 [Verifier] No Tests for proof_carrying_numbers.py (597 lines, 0% coverage)
7 verification checks, ProofCarryingNumber class, create_verified_extraction factory — all untested. Zero imports in tests/.

### P1-2 [Verifier] No Tests for team_of_rivals.py (1043 lines, 0% coverage)
4 extractors, Critic, ConsensusEngine — all untested. Critic fallback always prefers PatternExtractor when no majority, undermining the architectural premise.

### P1-3 [Verifier] API CORS Allows All Origins with Credentials
**File:** `src/api/main.py` lines 143–149
`allow_origins=["*"]` + `allow_credentials=True` allows any website to make authenticated cross-origin requests.

### P1-4 [Verifier] No API Input Size Limits
**File:** `src/api/main.py`
`ExtractionRequest.text` has no `max_length`. PDF upload has no size limit. Memory exhaustion attack vector.

### P1-5 [Verifier] Negative Controls Contain Valid Effect Estimates — 0% FPR Is Keyword Filter
**File:** `data/negative_controls.py`
Only 20 entries. Several contain real effect estimates (HR 0.76, OR 0.82, etc.) that are only excluded because of hardcoded negative context keywords ("meta-analysis", "retrospective", "mice", etc.). 95% CI for 0/20 FPR is [0%, 16.1%].

### P1-6 [Verifier] Multi-Language Patterns Silently Fail — float() Rejects Comma Decimals
**File:** `src/core/enhanced_extractor_v3.py`
Patterns match `"0,74"` but `float("0,74")` raises ValueError, caught by bare `except`, producing no extraction. European-format extraction is non-functional.

### P1-7 [Verifier] OCR Handling Requires External Preprocessing Not In Extractor
**Files:** `run_comprehensive_validation.py` lines 75–77; `enhanced_extractor_v3.py`
Validation script calls `correct_ocr_errors()` before extraction. The extractor itself does NOT do OCR correction. `extractor.extract("HR O.74 (95% Cl O.65-O.85)")` returns empty list.

### P1-8 [Verifier] Tests Assert "Runs Without Error" Not Correctness
**Files:** `tests/test_multi_language.py`, `tests/test_ocr_stress.py`
Multiple tests only assert `isinstance(results, list)`. A function returning `[]` for all inputs passes every test.

### P1-9 [Planner] pytest.ini and pyproject.toml Both Configure pytest Divergently
pytest.ini has `--strict-markers` + 7 custom markers + log config; pyproject.toml has none of that. pytest.ini wins, making pyproject.toml config dead.
**Fix:** Consolidate to one location.

### P1-10 [Planner] `src/utils/` Missing `__init__.py`
Not a proper Python package. Breaks in strict packaging environments.

### P1-11 [Planner] Absolute `src.*` Imports Inside Package Break pip install
**Files:** `src/core/extraction_validators.py`, `src/api/main.py`
When installed as a package, `from src.core.xxx import ...` fails. These work only via sys.path hacks.

### P1-12 [Planner] Hardcoded Local Path in wasserstein_bridge.py
**File:** `src/bridges/wasserstein_bridge.py` line 29
`WASSERSTEIN_DIR = r"C:\Users\user\Downloads\wasserstein"` — fails on any other machine.

### P1-13 [Planner] Dockerfile `python -m src.cli` Missing `__main__.py`
Documented entrypoint doesn't work. `src/cli/__main__.py` does not exist.

### P1-14 [Builder] Integrity Hash Omits Effect Type and CI Bounds
**File:** `src/core/proof_carrying_numbers.py` line 143
Hash only includes `value|source_text|char_start`. Two extractions with same value but different types produce identical hash.

### P1-15 [Builder] `if self.p_value:` Drops p_value=0.0
**File:** `src/core/proof_carrying_numbers.py` line 248
Truthiness check treats 0.0 as False. Fix: `if self.p_value is not None:`.

### P1-16 [Builder] StateMachineExtractor `text.find()` Misaligns Token Positions
**File:** `src/core/team_of_rivals.py` line 562
`find()` returns first occurrence from position, not the specific token from `findall`. Fix: use `re.finditer`.

### P1-17 [Builder] Inconsistent Borderline p-value Tolerance
**Files:** `proof_carrying_numbers.py` (0.04–0.06) vs `deterministic_verifier.py` (0.03–0.07)
Same check, different windows. Should be consolidated.

### P1-18 [Builder] Confidence Calibration Threshold Logic Fails on Non-Monotonic Bins
**File:** `src/core/confidence_calibration.py` lines 156–168
Descending bin walk doesn't verify cumulative condition. Non-monotonic accuracy bins produce incorrect thresholds.

### P1-19 [Verifier] No End-to-End Integration Test
No test exercises: PDF → text extraction → effect extraction → PCN verification → output. The test_pdf_pipeline.py requires actual PDFs gated behind a marker, with no fixtures included.

---

## P2 Issues (Minor — Fix When Convenient)

| # | Source | Issue |
|---|--------|-------|
| P2-1 | Builder | European comma normalization `(\d),(\d)` corrupts comma-formatted integers (e.g., "1,234" → "1.234") |
| P2-2 | Builder | Duplicate HR pattern at lines 346/362 (harmless, dedup set prevents double-extraction) |
| P2-3 | Builder | GrammarExtractor re-compiles regex on every character position (100K+ compilations) |
| P2-4 | Builder | O(n²) extraction grouping in ConsensusEngine |
| P2-5 | Builder | SymPy used for trivial arithmetic that plain Python handles |
| P2-6 | Builder | Effect direction classification ignores outcome polarity |
| P2-7 | Builder | Misleading confidence multiplier 0.5 for implausible values (guarded by boolean, harmless) |
| P2-8 | Verifier | `datetime.now()` in ProofCertificates makes outputs non-reproducible |
| P2-9 | Verifier | API exception detail leaks internal paths |
| P2-10 | Verifier | Dockerfile pip install runs as root |
| P2-11 | Verifier | Unused `import random` in external_validation_dataset.py |
| P2-12 | Planner | `results_table_extractor.py` orphaned — never imported anywhere |
| P2-13 | Planner | `extraction_validators.py` orphaned — never imported |
| P2-14 | Planner | `extraction_schema.py` only used by orphaned module — parallel type system |
| P2-15 | Planner | 50 root `run_*.py` scripts: 3 backup files, 7 versioned copies, fragile sys.path imports |

---

## Recommended Fix Order

### Phase 1: Critical correctness (P0s)
1. **P0-5** CI boundary inequality — one-line fix
2. **P0-9** Model validators — add 2 validators
3. **P0-7** NNT CI zero-crossing — add sign check + warning
4. **P0-6** ARD normalization — extend context window
5. **P0-3** Add numpy/scipy to pyproject.toml deps
6. **P0-4** Fix CI workflow flags
7. **P0-2** Version consolidation
8. **P0-8** Wire real calibration or remove ECE claim
9. **P0-1** Validation methodology — freeze patterns, build independent test set (longer term)

### Phase 2: Significant gaps (P1s)
1. P1-6 Fix European comma → float conversion
2. P1-15 Fix p_value truthiness check
3. P1-14 Expand integrity hash
4. P1-3/P1-4 API security (CORS + size limits)
5. P1-1/P1-2 Add tests for PCN and team_of_rivals
6. P1-8 Strengthen test assertions
7. P1-10/P1-11/P1-13 Packaging fixes
8. P1-12 Remove hardcoded path

### Phase 3: Cleanup (P2s)
Address as time permits, prioritizing P2-1 (comma normalization) and P2-8 (determinism).
