# Meta-analysis data errors: what the literature finds, and what we check

Goal: extracted data more trustworthy than the median published meta-analysis,
**within our data limits** (AACT / ClinicalTrials.gov structured fields +
PubMed abstracts — no full-text tables, no figures, no supplements).

This is achievable not because our raw extraction is super-human, but because we
attach an **auditable internal-consistency verdict** to every number and refuse
to silently mix incompatible estimates. Most published meta-analyses carry no
such machine-checkable trail, and empirical audits keep finding the same errors.

## How often published meta-analyses are wrong

| Source | Finding |
|---|---|
| Gøtzsche et al. 2007 (*JAMA*) | Data-extraction errors affecting the SMD in **37%** of reviews examined. |
| Maassen et al. 2020 (*…effect sizes*) | ~**27%** of effect sizes not reproducible; ~**16%** of errors changed statistical significance. |
| Ford et al. 2010; Tendal et al. 2009 (*BMJ*) | Outcome / time-point **multiplicity** ("vibration of effects") routinely biases the pooled estimate. |
| Lakens; Higgins (Cochrane Handbook Ch.6) | **SD↔SE confusion** is the dominant continuous-outcome error. |
| Our own audit (156 abstracts) | Internally-consistent extractions can **still be wrong** (3 gold-misses flagged by 0 numeric checks) → consistency ≠ correctness. |

**Therefore:** published meta-analyses are a *comparator for triangulation, not
an oracle.* They use different trial sets, data sources, and methods, and carry
their own human errors. When our value disagrees with a published pool, that is
a **bidirectional "investigate"** signal — sometimes they are wrong — never an
automatic correction of our number.

## The canonical error taxonomy → our guard

| # | Known error pattern | Where it bites | Our check (flag) |
|---|---|---|---|
| 1 | **SD reported as SE** (or vice versa) | Continuous | `dispersion_se_sd_mismatch` — SE from the effect CI vs SE pooled from arm SDs disagree by >2.5×/<0.4× |
| 2 | **SMD / MD miscomputed** (wrong pooled SD, sign, Cohen vs Hedges) | Continuous | `smd_recompute_mismatch`, `md_recompute_mismatch` (orientation-tolerant) |
| 3 | **Median/IQR treated as mean/SD** (skew) | Continuous | GRIM/GRIMMER granularity (`grim_inconsistent`, `grimmer_inconsistent`) on integer scales |
| 4 | **Summary-measure mixing** (MD pooled with OR/HR; OR with RR) | Pooling | `check_pool_measures` → `mixed_continuous_and_binary` (hard), `mixed_summary_measure`, `mixed_effect_subtype`; bus `_diagnostics` |
| 5 | **Outcome mixing** — different outcomes/constructs pooled as one (all-cause vs CV mortality; composite vs component) | Pooling | `check_pool_outcomes` → `mixed_outcome`; bus `_diagnostics.outcome_homogeneity` |
| 6 | **Time-point multiplicity** — 12-wk pooled with 52-wk | Pooling | `check_pool_outcomes` → `mixed_timepoint` |
| 7 | **Diagnostic 2×2 incoherence** — Se/Sp/N imply non-integer cells; Se/Sp/PPV violate Bayes | DTA | `dta_cells_noninteger`, `dta_2x2_mismatch`, `dta_bayes_mismatch` |
| 8 | **Disconnected / no-loop network** treated as analysable | NMA | kit `nma-consistency.classifyNetwork` → DISCONNECTED / TREE refusal (union-find + Euler loops) |
| 9 | **Unit-of-analysis** — multi-arm shared-control double counting | NMA | shared-control covariance in multi-outcome-nma; node-split gated on real loops |
| 10 | **Negated-count trap** — "Not randomised 1,807" read as N | Counts | `events_exceed_n`, `arm_n_*` (hard) |
| 11 | **Misread digit / reversed CI / significance flip** | All | `point_outside_ci`, `point_grossly_off_centre`, `swapped_ci_bounds` repair, `gross_sig_inconsistency` |
| 12 | **Wrong estimand / ungrounded value / multiplicity of candidates** | All | `value_not_in_source`, `multiple_candidates`, `multiple_effect_types`, effect ordering |

## Maximum methodologically-valid pooling

Detecting an invalid mix is only half the job; we also want to pool **as many
trials as legitimately possible**. `outcome_grouping.partition_valid_pools`
splits a candidate set into the *largest* sub-pools that share
`(canonical outcome, measure family, follow-up bucket)`, so the caller pools the
biggest valid group and reports the remainder rather than either (a) fragmenting
needlessly or (b) combining across an outcome/measure/time boundary.

## Triangulation against real publications

`tests/test_triangulation_published.py` checks the extractor against verbatim
PubMed abstracts, asserting we reproduce each trial's **own** published estimate
(oracle-free — the trial states its number, so no pooling-method ambiguity) and
that the value is internally consistent. STEP 1 (Wilding 2021, *NEJM*; PMID
33567185) anchors the continuous case: we reproduce the −12.4-pp body-weight
treatment difference (95% CI −13.4 to −11.5) exactly, with zero false flags.

This validates against the **trial**, not a pooled meta-analytic value — because
a published meta-analysis may use a different trial set / data source / model and
carries its own human error. When our number disagrees with a *published pool*,
that is an investigate-both-sides signal, never an automatic correction.

## Known limitations (pinned regression targets)

- **ARD vs MD for "percentage points"** — a continuous %-change mean difference
  ("treatment difference of −12.4 percentage points" for body-weight % change) is
  currently typed `ARD` (a binary risk difference). The value/CI are correct; only
  the family label is. A safe fix needs ARD↔MD disambiguation plus cross-type
  de-duplication (naively widening the MD pattern double-extracts the span). Pinned
  as an `xfail` in the triangulation test.

## Design rule that keeps this honest

Every guard above is held to **zero false positives on the 156-record gold set**
(`test_gold_set_zero_false_positives`). Pool-level guards only assert a mix
between **confidently-recognised, different** outcomes/measures; an unrecognised
phrase never triggers a flag. The flags are *surfaced for review*, not used to
silently delete data — because the cost of a false "this is wrong" is a human
ignoring a true one next time.
