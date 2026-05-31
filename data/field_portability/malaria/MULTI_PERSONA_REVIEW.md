# Malaria Extractor — Multi-Persona Review (2026-05-31)

Four independent expert reviewers examined the live code (biostatistician,
Cochrane meta-analyst, tropical-medicine/malaria clinician, SWE red-team). Every
red-team finding was empirically reproduced. Findings below, by severity, with
the persona(s) that raised each.

## P0 — produces semantically WRONG, validation-passing data

| # | Finding | Where | Raised by | Status |
|---|---------|-------|-----------|--------|
| P0-1 | `_tag_endpoint` returns first endpoint in list order, not nearest → `8/150` near "ACPR aside, anaemia in 8 of 150" tagged ACPR not ANAEMIA | `malaria_arm_data.py` `_tag_endpoint` | red-team | FIXED |
| P0-2 | `_BARE_RATIO_RE` matches vital signs: "respiratory rate RR, 18; 95% CI 16-20" → RR=18 (point-in-CI guard doesn't catch it) | `malaria_effects.py` `_BARE_RATIO_RE` | red-team, clinician | FIXED |
| P0-3 | Case-insensitive 2-letter drug abbrevs: `\bAL\b` (re.I) matches "et **al**." → false arm label | `malaria_arm_data.py` `_ARM_PATTERNS` | clinician | FIXED |
| P0-4 | `n of N` matches "page 8 of 150", "8 of 12 sites" → fake proportion | `malaria_arm_data.py` `_PROP_PATTERNS` | red-team | FIXED |
| P0-5 | `RRR` in `RATIO_TYPES` but emitted as a percentage (null=0, not ratio null=1) → wrong significance verdict for every vaccine-efficacy/RRR estimate | `internal_consistency.py` | biostatistician | FIXED |
| P0-6 | `gross_sig_inconsistency` hard-drops correct extractions (CI-includes-1 but p<0.05 is common: different model/rounding) | `internal_consistency.py` | red-team | FIXED |
| P0-7 | PCR-corrected and PCR-uncorrected ACPR collapsed into one endpoint → can pair mismatched denominators | `malaria.py`, `malaria_arm_data.py` | meta-analyst, clinician | FIXED |
| P0-8 | P. vivax RELAPSE missing → radical-cure (primaquine/tafenoquine) recurrences misrouted to recrudescence/reinfection | `malaria.py` | clinician | FIXED |

## P1 — systematic bias / silent loss

- **Double-counting**: same effect in abstract + results + forest-plot row emitted 2-3× (span-overlap dedup only) → inflated weight, false-narrow CI. (meta-analyst, red-team)
- **Multi-arm (>2) trials**: `pair_2x2` emits only the first pair, drops the comparator (e.g. placebo); shared-control comparisons are also correlated (τ²/2). (meta-analyst, red-team)
- **Continuous outcomes unsupported**: no per-arm mean+SD+N extractor → clearance-time/Hb meta-analyses lose most trials; PCT is log-normal (needs GMR). (meta-analyst)
- **No ITT vs per-protocol denominator tag** → mixed denominators across the pool. (meta-analyst)
- **Char-offset drift** after `normalize_text` ligature expansion (offsets index normalized frame, not the input). (red-team)
- **Efficacy %** has no plausibility guard in the standalone augmenter path (accepts 560%, -5%). (red-team)
- **95% CI hardcoded** (z=1.96): non-inferiority malaria trials report 90%/97.5% CIs → SE mis-scaled in the p-derivation. (biostatistician)
- **Missing clinical vocabulary**: Kelch13/K13 resistance markers, parasite reduction ratio (PRR), IPTp maternal outcomes (placental malaria, low birth weight, maternal anaemia, preterm), G6PD haemolysis (primaquine/tafenoquine safety). (clinician)
- **Missing arm labels**: tafenoquine, atovaquone-proguanil, mefloquine, arterolane-PPQ, pyronaridine-PPQ, SP-AQ, rectal artesunate. (clinician)

## P2 — refinement / honesty

- README headline metrics are self-consistency/recovery, not certified correctness; add a "what these do NOT cover" box (arm labels, PCR status, denominators, dedup). (meta-analyst)
- `needs_review` is opt-in and coarse; add a `poolable_ready()` accessor that withholds unverified rows. (meta-analyst)
- `MALARIA_INFECTION` vs `PREVALENCE` share the `parasite prevalence` alias (non-deterministic winner). (clinician)
- Severe-malaria components (acidosis, hypoglycaemia, AKI, coma score) are context-only, not endpoints. (clinician)
- `recurrent parasitaemia` → TREATMENT_FAILURE is PCR-uncorrected and over-broad. (clinician)

## Confirmed correct (not rubber-stamped)
Altman-Bland SE/z/P + inverse; geometric-vs-arithmetic midpoint split; mid_tol/gross_mid_tol values; `pct == 100·n/N` check + guards; aRR→RR vs MD ordering (no mislabel in the augmenter); no ReDoS (bounded lazy quantifiers).

## Disposition
**All 8 P0s fixed**, plus the P1 block. Round 1 (commit 4ce2d40): P0-1..P0-6.
Round 2 ("next block"): P0-7 PCR-status separation, P0-8 vivax relapse + 12 new
clinical endpoints (K13, PRR, IPTp maternal, haemolysis, severe components),
cross-mention dedup, multi-arm flagging, ITT/PP tagging, poolable_ready(),
continuous per-arm mean+SD/median+IQR extraction, the [ae] spelling bug, the
efficacy-% guard, and the README honesty box. Full suite: 880 passed, 0 failures.

STILL OPEN (low impact, documented): char-offset drift after ligature
normalization (source_text stays internally consistent); the hardcoded 95% z
for the rare 90%/97.5% non-inferiority CIs (now only adds a review flag, never
drops, since gross_sig is soft). Both are candidates for a future pass.
