# Real-PDF Accuracy — Schizophrenia (`schizophrenia`)

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold harvested by
> the extractor-INDEPENDENT `build_gold_from_abstracts.harvest_effects` (verbatim
> guard) over each abstract; the shipped extractor is scored on the full PDF body.
> EuropePMC-sourced (NCBI `eutils` DNS-blocked on host) via
> `scripts/pdf_eval/acquire_epmc_gold.py`; source swapped only. Non-RCT papers
> (review / meta-analysis / Mendelian randomization / observational / retrospective
> / real-world / propensity) are excluded by `_looks_non_rct` so the gold is RCT-only.

## Dataset

- **22 real PMC Open-Access schizophrenia RCT articles**, **43 gold effect tuples**
  (explicit ratio + 95% CI in the abstract).
- Gold: `data/pdf_eval/gold_schizophrenia.jsonl`. PDFs gitignored.

## Results (match tol: point ±0.02/2%, CI ±0.03/3%)

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 43 | 43 (100%) | 0 | 0 |
| pdf_raw  | 43 | **43 (100%)** | 0 | 0 |
| pdf_pp   | 43 | 43 (100%) | 0 | 0 |

**Real-PDF accuracy = 100% (43/43) ≥ 95% target.** No remaining gaps.

The effect-tuple extraction is the shared core (`enhanced_extractor_v3.py`); the
`schizophrenia` module adds endpoint vocabulary (PANSS total/positive/negative,
CGI, ≥30%/≥50% PANSS response, relapse, rehospitalization, all-cause
discontinuation, cognition/MCCB, weight gain, EPS/akathisia), subspecialty routing
(acute / maintenance / negative-cognitive / safety), and antipsychotic arm labels.
