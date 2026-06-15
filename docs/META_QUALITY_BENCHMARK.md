# How we benchmark data quality against published meta-analyses

Goal: prove the pipeline's data quality is in the top tier of published
meta-analyses, **within our source limit** (AACT / ClinicalTrials.gov / PubMed
abstracts — no full-text tables/figures/supplements), with maximum
methodologically-valid pooling. The benchmark is deliberately built so the
claim is *earned and falsifiable*, not asserted.

## The method: a composite gate vs the real published-MA distribution

"Data quality" isn't one number. The empirical literature decomposes published-MA
failure into distinct error modes, each with a **reported base rate**. We define
one GATE per mode, score our pipeline's pass on each from real metrics, then
estimate the fraction of published MAs that clear **every** gate. Our percentile
is how exclusive that all-pass set is.

| Gate | Published fail rate | Source | Our mechanism |
|---|---|---|---|
| A1 Extraction fidelity | 27% | Maassen 2020 (27% effect sizes unreproducible, 16% sig-flips); Gøtzsche 2007 JAMA (37% of SMD MAs) | gold within-10% match + type accuracy (`evaluate_real_rct_metrics`) |
| A2 Internal consistency | 20% | Brown&Heathers 2017 GRIM, Anaya 2016 GRIMMER, Bakker&Wicherts/statcheck, Altman-Bland | `check_consistency` (point-in-CI, SD↔SE, 2×2/Bayes/LR, GRIM/GRIMMER, reversed-CI repair); **gold FP = 0** |
| A3 Measure/outcome homogeneity | 10% | Cochrane §10.4; Tendal 2009 BMJ (multiplicity) | `check_pool_measures` + `check_pool_outcomes`; `partition_valid_pools` (max-valid pooling) |
| A4 Pooling robustness | 55% | spec-collapse-atlas (473 Cochrane MAs, 55% naive-robust→WL-fragile); arXiv:2511.17064; Stanley 2025 | REML+HKSJ + prediction interval + WL-corrected sensitivity |
| A5 Reproducibility | 14.3% | repro-floor-atlas (Pairwise70); INSPECT-SR (medRxiv 2025.09.03) | version-controlled numerical baselines; pool recomputable from the (est, se) bus |

Implementation: `rct_extractor/_engine/benchmark/meta_quality_index.py` (pure,
tested) + `scripts/meta_quality_benchmark.py` (wires real artifacts). Reuses the
existing stack mapped in the portfolio: `evaluate_real_rct_metrics`,
`consistency_audit`, the 127-trial cardiology author-meta linked benchmark
(`evaluate_cardiology_linked_benchmark`), and the Pairwise70 atlases
(spec-collapse / fragility / repro-floor).

## Honesty rails (so "top 5%" can't be gamed)

1. **Computed, not asserted.** Every axis pass comes from a real number; an axis
   with no evidence is reported *unmeasured* and blocks the percentile claim.
2. **Independence is an optimistic floor.** The published all-pass rate is first
   the product of per-axis pass rates (independence). Real failures are positively
   correlated (bad MAs fail several axes), which *raises* the joint pass rate — so
   the true tier is at least the independence floor; supply per-MA Pairwise70 gate
   verdicts (`--pairwise-verdicts`) for the observed rate, and we report the larger
   (less self-flattering) figure.
3. **Source constraint stated** on every run.

## The 8 gates and 3 extra axes

Beyond A1–A5, three further axes are now first-class gates (each measured live on
the gold set): **A6 Trustworthiness** (INSPECT-SR, ≈32% of RCTs raise concerns;
proxy = A7∧A8 clean), **A7 Source grounding** (`value_not_in_source` /
`multiple_candidates`; ≈4% LLM-misattribution baseline), **A8 Forensic digits**
(GRIM/GRIMMER/Benford/terminal-digit/arm-N reconciliation).

## Observed Pairwise70 rate (not just the literature floor)

`scripts/build_pairwise_gate_verdicts.py` reads spec-collapse-atlas'
`corpus_results.json` (473 Cochrane MAs) and emits a per-MA A4 verdict
(`A4 pass = not false_robust`). The benchmark then uses a **hybrid** published rate:
the real corpus marginal for the covered axis (A4: **260/473 = 55.0% false-robust**,
confirming the literature 0.55) × the literature pass rate for the uncovered axes,
capturing real cross-axis correlation once ≥2 axes have per-MA verdicts.

## What the benchmark currently says (run it)

```
python scripts/build_pairwise_gate_verdicts.py
python scripts/meta_quality_benchmark.py --pairwise-verdicts data/pairwise_gate_verdicts.jsonl
```

- We clear **all 8 measured gates** (internal-consistency FP **0/156**, forensic FP
  **0/156**, grounding FP **1/156** — live).
- Composite all-pass tier: **top ~11%** of published MAs (hybrid = independence here,
  since the real A4 marginal equals the literature 0.55).
- Honest gap: reaching ≤5% as a composite would need **~4 more** independent gates
  (~20% marginal fail each), and failure-correlation works *against* this. So a
  blanket "top 5%" is **not supported** by these axes. The defensible claims are
  **(a) composite top ~11%** and **(b) per-axis standings** — e.g. on pooling
  robustness we are better than the **55%** of MAs that are false-robust, and on
  internal consistency our gold false-positive rate is **0**. The runner prints all
  of this; it never claims a number it hasn't computed.

## Maximum methodologically-valid pooling

A3 is paired with `partition_valid_pools`: split the available trials into the
*largest* sub-pools valid to combine (outcome × measure-family × follow-up bucket),
so we pool as many trials as legitimately possible without crossing a boundary —
the constructive complement to the mixing guard.
