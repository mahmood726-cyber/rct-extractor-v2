# Real-PDF Accuracy — Sepsis / septic shock (`sepsis`)

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold harvested by
> the extractor-INDEPENDENT `build_gold_from_abstracts.harvest_effects` (verbatim
> guard) over each abstract; the shipped extractor is scored on the full PDF body.
> EuropePMC-sourced (NCBI `eutils` DNS-blocked on host); non-RCT papers excluded by
> `_looks_non_rct`.

## Routing note

Sepsis was previously unrouted (the generic `infectious_disease` bucket keys on
"infection"/"bacterial" but is a fallback). The dedicated `sepsis` specialty wins;
a regression test asserts a sepsis abstract routes to `sepsis` over the ID fallback.

## Dataset

- **22 real PMC Open-Access sepsis / septic-shock RCT articles**, **45 gold effect
  tuples** (explicit ratio + 95% CI in the abstract).
- Gold: `data/pdf_eval/gold_sepsis.jsonl`. PDFs gitignored.

## Results (match tol: point ±0.02/2%, CI ±0.03/3%)

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 45 | 45 (100%) | 0 | 0 |
| pdf_raw  | 45 | **45 (100%)** | 0 | 0 |
| pdf_pp   | 45 | 45 (100%) | 0 | 0 |

**Real-PDF accuracy = 100% (45/45) ≥ 95% target.** No remaining gaps.

The effect-tuple extraction is the shared core (`enhanced_extractor_v3.py`); the
`sepsis` module adds endpoint vocabulary (28-/90-day mortality, shock reversal,
vasopressor-/ventilator-/organ-support-free days, new RRT / sepsis-associated AKI,
SOFA, antibiotic duration), subspecialty routing (hemodynamic / adjunctive /
antimicrobial-source / organ-support), British/American spelling
(`septica?emia`, `ha?emodynamic`), and arm-level labels (norepinephrine,
vasopressin, angiotensin II, hydrocortisone, vitamin C, balanced crystalloid).
