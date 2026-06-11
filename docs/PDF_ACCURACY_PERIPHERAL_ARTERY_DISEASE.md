# Real-PDF Accuracy — peripheral artery disease (PAD) specialty

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold harvested by
> the repo's independent regex (`build_gold_from_abstracts.harvest_effects`,
> verbatim-substring guard) from each article's abstract; the extractor scored on
> the **full PDF body**. Corpus + abstracts sourced from EuropePMC (NCBI eutils
> was DNS-unreachable here) with the default RCT-only publication-type filter; see
> the dyslipidaemia / VTE reports for full rationale.

## Dataset

- **45 real PMC-OA PAD RCT articles**, **148 gold effect tuples**
  (HR 122 / OR 13 / RR 10 / IRR 3). Gold in `data/pdf_eval/gold_peripheral_artery_disease.jsonl`.

## Results

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 148 | 145 (98%) | 1 (1%) | 2 (1%) |
| **pdf_raw** | **148** | **145 (98%)** | **2 (1%)** | **1 (1%)** |
| pdf_pp | 148 | 145 (98%) | 2 (1%) | 1 (1%) |

**pdf_raw = 98% correct — above the 95% bar.** Among matched pairs: type 99%,
CI bounds 99%/99%.

## Honest residuals (pdf_raw) — not generalizable pattern gaps

All three come from a single paper, `PMC9346972`, reporting multivariable
risk-factor ORs with an idiosyncratic `adj-OR` token and per-unit annotations
(`adj-OR [per 10 years]: 1.67`, `adj-OR [per 5 kg/m2]: 1.15`). These are
adjusted regression coefficients from one trial's secondary analysis, not the
canonical `OR`/`aOR` form; the per-unit bracket between the token and value is
the obstacle. A single paper's house style — not worth a shared-core change at
98%. No core-extractor change was made; nothing overfit.

## Subspecialties

limb_outcomes (MALE, amputation, amputation-free survival, acute limb ischaemia,
limb salvage), revascularisation (primary patency, TLR/TVR, restenosis),
medical_therapy (MACE/MI/stroke/CV+all-cause death, major bleeding), functional
(maximal / pain-free walking distance, ankle-brachial index — continuous MD/SMD).

## Reproduce

```bash
python scripts/pdf_eval/acquire_and_gold_epmc.py --specialty peripheral_artery_disease \
  --query '("peripheral artery disease" OR "peripheral arterial disease" OR \
    "intermittent claudication" OR "critical limb ischemia" OR "critical limb ischaemia" OR \
    "chronic limb-threatening ischemia" OR cilostazol OR femoropopliteal OR "ankle-brachial")' \
  --max-search 2500 --max-download 60 --target 45 --workers 8 \
  --out data/pdf_eval/gold_peripheral_artery_disease.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_peripheral_artery_disease.jsonl \
  --out data/pdf_eval/eval_peripheral_artery_disease.json --preprocess
```
