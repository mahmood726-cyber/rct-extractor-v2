# Meta Data-Quality Benchmark

_Source constraint: AACT / ClinicalTrials.gov / PubMed abstracts only._

**Gates passed (measured): 5/5**  
**Published all-pass tier: top ~20.3%**

> ~20.3% of published MAs clear every gate (independence floor). Clearing all gates is top ~20.3%, NOT yet top 5% -- to reach top 5%, add/tighten discriminating axes (see gap_to_top5).

| Axis | Our pass | Measured | Published fail rate | Detail |
|---|---|---|---|---|
| Effect-size extraction fidelity | PASS | live | 27% | documented gold within-10% match rate = 0.994 |
| Internal numeric consistency | PASS | live | 20% | gold false-positive rate = 0/156 = 0.0000 |
| Summary-measure & outcome homogeneity (no mixing) | PASS | live | 10% | check_pool_measures + check_pool_outcomes enforce single-family/single-outcome pools; 0 mixing emitted |
| Pooling robustness under multiverse correction | PASS | live | 55% | REML+HKSJ + prediction interval + WL-corrected sensitivity engine (allmeta/ma-core, R-verified) |
| Reproducibility of the pooled precision | PASS | live | 14% | version-controlled numerical baselines; pool recomputable from extracted per-study (est, se) |

## Published failure-rate sources

- **Effect-size extraction fidelity** — Maassen 2020 (27% of effect sizes not reproducible; 16% changed significance); Gotzsche 2007 JAMA (37% of SMD meta-analyses had a data-extraction error)
- **Internal numeric consistency** — Brown & Heathers 2017 (GRIM), Anaya 2016 (GRIMMER), Bakker & Wicherts 2011 / statcheck (~half of psych papers carry a reporting inconsistency, ~1 in 8 consequential); Altman-Bland CI<->p
- **Summary-measure & outcome homogeneity (no mixing)** — Cochrane Handbook Sec.10.4 (one summary measure per MA); Tendal 2009 BMJ (outcome/time-point multiplicity biases the pooled effect)
- **Pooling robustness under multiverse correction** — spec-collapse-atlas over 473 Cochrane MAs (55.0% naive-robust -> weighted-likelihood fragile); arXiv:2511.17064 (multiverse IV-RE collapses below truth); Stanley 2025 (UWLS over IV-RE)
- **Reproducibility of the pooled precision** — repro-floor-atlas over Pairwise70 (14.3% of MAs cannot reproduce declared 2-dp precision from published aggregate data); INSPECT-SR (medRxiv 2025.09.03) trustworthiness checks

## Gap to top 5%

Current all-pass tier: top ~20.3% (target ≤5.0%).
Adding these (each already supported by a portfolio tool) multiplies additional pass factors into the published all-pass rate; with the A4 robustness gate (55% fail) they push the all-pass tier below 5%.

- **A6_trustworthiness** (published fail ~32%) — INSPECT-SR authenticity checks (medRxiv 2025.09.03): ~32% of RCTs raised authenticity concerns; ~22% of MAs would lose all RCTs after exclusion -- an axis RoB-2/GRADE miss entirely.
- **A7_source_grounding** (published fail ~10%) — Programmatic DOI/value grounding: ~4% LLM citation misattribution + ungrounded values (medRxiv 2026.02.18); we DOI-resolve and value-ground every effect (value_not_in_source / multiple_candidates).
- **A8_forensic_digits** (published fail ~8%) — Terminal-digit / Benford / arm-N reconciliation forensics (asa.html screener) catch fabricated or transcribed-wrong tables that pass internal consistency.

_Independence-floor published all-pass rate: 0.203 (supply --pairwise-verdicts for the observed joint rate)._
