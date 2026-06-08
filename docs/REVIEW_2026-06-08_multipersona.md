# Multipersona review + bug hunt — rct-extractor-v2 (master @ 1981da9)

**Date:** 2026-06-08
**Scope:** the recent additions — the 8 new specialties (meningitis, pneumonia,
diarrhoeal, malnutrition, helminths, hypertension, diabetes, cervical_cancer),
the union registry from the 14-extractor merge, and the new `rct_extractor`
package + `rct-extract` / `rct-extract-allmeta` CLIs.
**Method:** four reviewer personas (meta-analysis statistician, software
engineer, packaging/distribution, security), full reading of the shared
arm-data engine + effect augmenter + integration bridges, empirical routing
probes, a clean-venv `pip install`, and a targeted sub-agent deep-read of all
10 touched specialty profile modules.

**Test baseline:** 1343 passed / 128 skipped (pre-review). **After fixes:**
**1356 passed / 128 skipped** (13 new regression tests; zero regressions).

---

## Summary of findings

| # | Persona | Severity | Status | One-liner |
|---|---------|----------|--------|-----------|
| 1 | Statistician | **HIGH** | **FIXED** | `RRR`/`EFFICACY_PCT` pooled as a raw ratio (`log(56)`) instead of `log(1−x/100)` in the allmeta bridge |
| 2 | SW engineer | **HIGH** | **FIXED** | `infectious_disease` catch-all steals routing from specific specialties (hepatitis → ID) |
| 3 | Statistician | **HIGH** | **FIXED** | Pneumonia `bacterae?mia` misses the American "bacteremia/bacteremic" (IPD events dropped) |
| 4 | Statistician | MEDIUM | **FIXED** | median+IQR branch didn't flag log-normal endpoints (silently poolable on raw scale) |
| 5 | Statistician | LOW | **FIXED** | `isch[ae]mic` / `h[ae]morrhag(e\|ic)` miss one spelling (diabetes, hypertension, maternal_neonatal, typhoid) |
| 6 | SW engineer | LOW | **FIXED** | `rct-extract -i F -o OUT` (human format) wrote a silent 0-byte file |
| 7 | Packaging | **HIGH** | **DEFERRED** | wheel installs generic top-level `src` + `configs` packages → site-packages namespace collision |
| 8 | Statistician | INFO | noted | layering note on RRR (contract vs pooling scale); no action |

Security persona: **no findings** — no `eval`/`exec`/`subprocess`/`os.system`,
no network calls in the package, no nested-quantifier ReDoS in the new
profiles, and `importlib.import_module` only ever receives registry-validated
specialty names (no import injection). CLI file paths are user-supplied to the
user's own process — no privilege boundary is crossed.

---

## Fixed this pass

### 1. [HIGH, statistician] RRR / vaccine-efficacy pooled on the wrong scale
`rct_extractor/integrations/_common.py` listed `RRR` in `RATIO_TYPES`, so
`effect_to_est_se` computed `est = log(effect_size)`. But the core extractor
(`enhanced_extractor_v3.py:1737`, `EffectType.RRR: (0.0, 100.0)`; VE→RRR
mapping at :1615) stores RRR/efficacy as a **percentage on 0–100**, and
`ma_contract.py` classifies RRR as a *difference* type. So a vaccine-efficacy
trial (e.g. `VE = 56%, 95% CI 51–60`) reached the allmeta bridge as
`log(56) = 4.03` — meaningless. This is directly reachable:
`rct-extract-allmeta corpus/ -m RRR` (or `-m EFFICACY_PCT`), exactly the
malaria/vaccine student use-case.

**Fix:** new `PCT_TYPES = {"RRR","EFFICACY_PCT"}` handled as
`RR = 1 − x/100 → est = log(RR)`, with the CI flipped (higher reduction = lower
RR) and `x ≥ 100` / `RR ≤ 0` rejected. This matches the log(1−VE) pooling field
`malaria_effects._add_log_rr` already attaches and the `advanced-stats` rule
(*always pool logRR, back-transform after*). `RRR` removed from `RATIO_TYPES`.
Tests: `test_rrr_pooled_on_log_rr_scale_not_as_raw_ratio`,
`test_efficacy_pct_uses_same_log_rr_conversion`,
`test_pct_measure_at_or_above_100_is_rejected`, `test_negative_efficacy_handled`.

### 2. [HIGH, SW engineer] `infectious_disease` steals routing
`registry.detect_specialty` picks `argmax(score)`, ties broken by insertion
order. The `infectious_disease` bucket's keywords (`viral`, `bacterial`,
`infection`, `antibiotic`, `antiviral`) are deliberately broad and co-occur with
every specific ID specialty, so an abstract like *"antiviral treatment of viral
hepatitis B infection … bacterial co-infection … antibiotic"* scored ID=5 vs
hepatitis=3 and routed to a bucket with **no** detection/normalizer/arm-level
extractor — losing all specialty extraction. (Realistic HBV abstracts route
correctly; the misroute bites keyword-sparse borderline abstracts.)

**Fix:** `infectious_disease` is now a fallback — it only wins when no specific
specialty matched (`_FALLBACK_SPECIALTIES`). Since it has no extractor, routing
away from it is strictly safer; no test asserts ID detection. Pure-COVID text
(no specific match) still routes to `infectious_disease`. Tests:
`test_infectious_disease_does_not_steal_from_hepatitis`,
`test_infectious_disease_still_wins_for_generic_covid`.

### 3. [HIGH, statistician] Pneumonia "bacteremia" American spelling missed
`pneumonia.py:262` `bacterae?mic`/`bacterae?mia` expand to *bacterae* + optional
*e* — they match `bacteraemia` but **never** `bacteremia`/`bacteremic` (the
dominant international spelling). Verified end-to-end: tagging "bacteremic
pneumonia" returned `None`, so bacteraemic-pneumonia / IPD events in those
abstracts went untagged at arm-data extraction. **Fix:** `bactera?emic` /
`bactera?emia` (matches both). Test: `test_bacteremia_both_spellings_tag_ipd`.

### 4. [MEDIUM, statistician] median+IQR ignored log-normal flag
In the shared engine `malaria_arm_data.extract_continuous`, the mean+SD branch
flags log-normal endpoints (parasite clearance/density, viral load, EPG, UACR…)
with `poolable=False` + a pooling note, but the **median+IQR branch** emitted
`poolable="after_iqr_to_sd"` with no log-normal check — a Wan-transformed
raw-scale mean+SD for a log-normal outcome would silently enter a pool on the
wrong scale. **Fix:** mirror the mean+SD branch (lognormal → `poolable=False` +
note). Affects every specialty reusing the engine. Tests:
`test_median_iqr_lognormal_flagged_not_poolable`,
`test_median_iqr_non_lognormal_remains_poolable_after_transform`.

### 5. [LOW, statistician] `[ae]` double-vowel spelling traps
`isch[ae]mic` matches *ischemic* but not *ischaemic*; `h[ae]morrhag(e|ic)`
matches *hemorrhag…* but not *haemorrhag…* (the British form inserts an extra
vowel, keeping both — `lessons.md`'s "`h[ae]morrhage` is fine" claim is
**empirically wrong**; see note below). In diabetes/hypertension these were
masked by a bare `stroke` fallback (cosmetic), but in maternal_neonatal
("hypoxic-ischaemic encephalopathy") and typhoid ("intestinal haemorrhage") the
British full-text form was genuinely missed unless an abbreviation was present.
**Fix:** `ischa?emic` / `ha?emorrhag…` everywhere (matches both spellings).

> **`lessons.md` correction:** the rule *"`h[ae]morrhage` … ARE fine because
> there the variation is genuinely one-char"* is incorrect — `haemorrhage`
> carries BOTH the `a` and `e` (h-**ae**-morrhage ⊃ h-e-morrhage), so it needs
> `ha?emorrhag`, exactly like haemoglobin. `h[ae]morrhage` silently misses the
> British spelling. Recommend updating the lessons file.

### 6. [LOW, SW engineer] human-format `--output` wrote an empty file
`rct-extract -i FILE -o OUT` (no `--json`) printed the summary to stdout but
wrote a **0-byte** file (`lines` was only populated in the `--json` branch).
**Fix:** `_print_summary` → `_format_summary` returns the text; it is both
printed and collected, so the file now contains the summaries. Test:
`test_human_output_to_file_is_not_empty`.

---

## Deferred / residual (for Mahmood)

### 7. [HIGH, packaging] generic `src` + `configs` top-level packages — **DEFERRED**
`pyproject.toml` ships `include = ["rct_extractor*", "src*", "configs*"]`, so
`pip install rct-extractor` drops top-level **`src`** and **`configs`** packages
into the user's `site-packages` (confirmed in `top_level.txt`). Any other
installed distribution that also ships a top-level `src`/`configs` will shadow
or be shadowed — a classic install-collision footgun for external users, and
the README's own "`src` top-level smell" note. The package otherwise installs,
imports, and runs cleanly from a clean venv (all three entry points register;
`import rct_extractor`, `rct-extract --list-specialties`, `--version`, and
extraction all work).
**Remediation (non-trivial):** move the engine under the namespace —
`rct_extractor/_engine/…` (or `rct_extractor/src`) — and rewrite `from src.…`
imports + the `rct-extract-pdf = src.cli.cli:main` entry point. ~hundreds of
import sites; needs its own PR with the full suite as the guard. **Not done here**
to keep this pass low-risk and green. Interim mitigation if a release is
imminent: at minimum rename/relocate `configs` (small) and document the `src`
collision risk in the README install section.

### 8. [INFO, statistician] RRR layering note — no action
`ma_contract.py` classifies `RRR` as a *difference* type (it validates the
**as-reported** natural-scale point + CI), while fix #1 transforms RRR to the
**log-RR** scale for *pooling* in the allmeta bridge. These are different layers
(storage/validation vs analysis-scale transform) and are not in conflict — the
0–100 value is stored as reported and only the pooling input is log-transformed.
Flagged so a future reader doesn't "reconcile" them into a regression.

---

## What was checked and found correct (no change)

- **`_common.py` core stats:** ratio measures → `log(point)`, `se =
  (log hi − log lo)/(2·z₍.975₎)`; differences → natural scale; 2×2 log-OR
  `se=√(1/a+1/b+1/c+1/d)`, log-RR `se=√(1/a−1/(a+b)+1/c−1/(c+d))`; conditional
  0.5 correction only on a zero cell. All correct.
- **Wan (2014) IQR→SD:** `mean=(Q1+m+Q3)/3`, `SD=IQR / (2·Φ⁻¹((0.75n−0.125)/
  (n+0.25)))` with 1.35 normal-approx fallback. Correct.
- **Augmenter dedup / PCR-corrected-vs-uncorrected guard / multi-arm
  shared-control flagging / ITT-vs-PP / negated-count rejection** in the shared
  engine — all sound.
- **`_BARE_RATIO_RE` TB+hepatitis union:** the `was` / `for <subgroup> of`
  linker alternatives are reachable (verified) and a strict superset of the
  original separator; no dead branch, no ReDoS. (NB: this augmenter is only
  invoked for `specialty=="malaria"` in `api.extract`; the TB/hepatitis linker
  extensions therefore currently benefit only the malaria path — by design after
  the union merge, but worth knowing.)
- **Registry wiring:** all 17 arm-level specialties importable + detected;
  per-specialty `_CONTINUOUS`/`_LOGNORMAL` sets are internally consistent
  (`_LOGNORMAL ⊆ _CONTINUOUS`); log-normal flagging correct for HBV DNA / HCV
  RNA / anti-HBs titre / UACR / EPG / GMT immunogenicity.
- **Subspecialty detectors:** confidences in [0,1]; default subspecialties are in
  the registry's declared lists; no duplicate `ENDPOINTS` keys.

---

## Files changed

- `src/specialties/registry.py` — `infectious_disease` fallback precedence
- `rct_extractor/integrations/_common.py` — `PCT_TYPES` log-RR conversion
- `src/specialties/pneumonia.py` — `bactera?emia/-emic`
- `src/specialties/malaria_arm_data.py` — median+IQR log-normal flag
- `src/specialties/diabetes.py`, `hypertension.py`, `maternal_neonatal.py`,
  `typhoid.py` — `[ae]` → `a?e` spelling fixes
- `rct_extractor/cli.py` — human-format `--output` no longer empty
- `tests/test_integrations.py`, `test_pneumonia.py`, `test_malaria_arm_data.py`,
  `test_hepatitis.py`, `test_cli_packaging.py` — 13 new regression tests
