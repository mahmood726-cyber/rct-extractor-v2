# Real-PDF Accuracy — Cirrhosis / decompensated liver disease (`cirrhosis`)

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold harvested by
> the extractor-INDEPENDENT `build_gold_from_abstracts.harvest_effects` (verbatim
> guard) over each abstract; the shipped extractor is scored on the full PDF body.
> EuropePMC-sourced (NCBI `eutils` DNS-blocked on host) via
> `scripts/pdf_eval/acquire_epmc_gold.py`; source swapped only. Non-RCT papers
> (review / meta-analysis / Mendelian randomization / cohort / observational /
> retrospective / real-world / propensity) excluded by `_looks_non_rct`, so the
> gold is RCT-only — important here because the cirrhosis literature is rich in
> observational cohorts.

## Routing note

A decompensated-cirrhosis abstract previously routed to `hepatitis` (whose only
cirrhosis signal is the bare keyword). The `cirrhosis` specialty's specific
vocabulary (variceal bleeding, ascites, hepatic encephalopathy, hepatorenal
syndrome, SBP, MELD, HVPG, terlipressin, …) outscores it; a regression test
asserts `cirrhosis` wins while a hepatitis-C SVR abstract still routes to
`hepatitis`.

## Dataset

- **22 real PMC Open-Access cirrhosis RCT articles**, **53 gold effect tuples**
  (explicit ratio + 95% CI in the abstract).
- Gold: `data/pdf_eval/gold_cirrhosis.jsonl`. PDFs gitignored.

## Results (match tol: point ±0.02/2%, CI ±0.03/3%)

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 53 | 53 (100%) | 0 | 0 |
| pdf_raw  | 53 | **53 (100%)** | 0 | 0 |
| pdf_pp   | 53 | 53 (100%) | 0 | 0 |

**Real-PDF accuracy = 100% (53/53) ≥ 95% target.** No remaining gaps.

The effect-tuple extraction is the shared core (`enhanced_extractor_v3.py`); the
`cirrhosis` module adds endpoint vocabulary (variceal bleeding/rebleeding, HVPG,
ascites control, HRS reversal, SBP, HE recurrence/reversal, ACLF, transplant-free
survival, MELD), subspecialty routing (portal-hypertension / decompensation /
encephalopathy / progression), British/American spelling (`ha?emorrhage`,
`o?esophageal`), and arm-level labels (NSBBs, terlipressin, albumin, rifaximin,
lactulose, TIPS, band ligation).
