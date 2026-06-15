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

`tests/test_triangulation_published.py` (extractor) and the NMA case in the kit's
`test_advanced_engines.py` check against verbatim PubMed abstracts / real network
topologies, asserting we reproduce each trial's **own** published estimate
(oracle-free — the trial states its number, so no pooling-method ambiguity) and
that the value is internally consistent. Anchors:

- **Continuous (MD)** — STEP 1 (Wilding 2021, *NEJM*; PMID 33567185): reproduces the
  −12.4-pp body-weight treatment difference (95% CI −13.4 to −11.5) exactly, zero
  false flags; also drove the ARD→MD fix below.
- **Continuous (SMD)** — Yan 2015 (PMID 25812710) "SMD=-0.50, 95% CI: -0.97 to -0.03"
  and Schuch 2016 (*Braz J Psychiatry*; PMID 27611903) "SMD = -0.90 [95%CI -0.29 to
  -1.51]". Fixed: (a) no-paren / bracket "SMD … to …" forms now extract a single
  clean SMD (was: missing CI + a duplicate generic-MD twin — now suppressed via
  `_suppress_md_twin_of_smd`); (b) the **reversed CI** Schuch prints (more-negative
  bound second) is repaired at extraction (`CI_REVERSED_REPAIRED`) instead of being
  dropped as CI-inconsistent.
- **DTA (no-CI)** — Elli 2022 (*Diagn Microbiol Infect Dis*; PMID 35216863): the
  combined "sensitivity and specificity … were 34.2% and 92.3%" no-CI form (which
  abstracts use constantly) was previously unextracted; now parsed, and the reported
  PLR 4.4 / NLR 0.71 are checked against Se/Sp (PLR=Se/(1−Sp)=4.44, NLR=(1−Se)/Sp=0.713).
- **DTA (decimal CI)** — Zheng 2023 (*PLoS One*; PMID 36812225): the decimal form
  "sensitivity, 0.76 (95% confidence interval [CI], 0.75 to 0.77)" — comma after the
  name, spelled-out CI, "to" separator — matched no pattern; now extracted (Se 0.76
  [0.75, 0.77], Sp 0.77 [0.75, 0.78]).
- **Dose-response** — Greenwood 2014 (*Br J Nutr*; PMID 24932880): the per-increment
  trend "RR 1.20/330 ml per d (95% CI 1.12, 1.29)" put the dose BETWEEN the estimate
  and its CI, defeating the contiguous effect pattern; a dose-unit-anchored per-unit
  pattern (kept trap-safe by the pt∈CI plausibility gate) now extracts RR 1.20 per
  330 ml.
- **Dose-response (MA-summary prose)** — Crippa 2014 (*Am J Epidemiol*; PMID 25156996):
  categorical risk reductions "for 4 cups/day … (16%, 95% CI: 13, 18)" are converted
  to an RR on the ratio scale (RR=1−pct/100=0.84, CI bounds flipped → 0.82–0.87), tied
  to the dose category. Requires a "risk reduction" cue scoped to the sentence (sign +
  low FP); both the 4-cup and 3-cup data points extract.
- **NMA** — the warfarin-anchored DOAC atrial-fibrillation network (ARISTOTLE,
  ROCKET-AF, RE-LY, ENGAGE-AF; no DOAC-vs-DOAC RCT) is correctly classified a STAR:
  connected but no closed loop, so consistency cannot be tested.

This validates against the **trial**, not a pooled meta-analytic value — because
a published meta-analysis may use a different trial set / data source / model and
carries its own human error. When our number disagrees with a *published pool*,
that is an investigate-both-sides signal, never an automatic correction.

## Resolved via triangulation

- **ARD vs MD for "percentage points"** — a continuous %-change mean difference
  ("treatment difference of −12.4 percentage points" for body-weight % change) was
  typed `ARD` (a binary risk difference). Fixed by a context-gated reclassification
  pass (`_reclassify_ard_as_md_when_continuous`): an `ARD` whose local context
  carries a continuous mean-change cue (mean change / change from baseline /
  change in body weight·BP·HbA1c·score·level …) **and** no binary cue (risk
  difference / absolute risk / rate of / incidence / proportion / NNT) is relabelled
  `MD`. It relabels in place (no new extraction → no twin). A true risk difference
  stays `ARD`. Pinned by `test_ard_vs_md_disambiguation`.

## Design rule that keeps this honest

Every guard above is held to **zero false positives on the 156-record gold set**
(`test_gold_set_zero_false_positives`). Pool-level guards only assert a mix
between **confidently-recognised, different** outcomes/measures; an unrecognised
phrase never triggers a flag. The flags are *surfaced for review*, not used to
silently delete data — because the cost of a false "this is wrong" is a human
ignoring a true one next time.
