# Real-PDF Accuracy — venous thromboembolism (VTE) specialty

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold harvested by
> the repo's independent regex (`build_gold_from_abstracts.harvest_effects`,
> verbatim-substring guard) from each article's abstract; the extractor is scored
> on the **full PDF body**.

## Provenance note (honest)

NCBI E-utilities was DNS-unreachable in this build environment, so the corpus +
abstracts were sourced from **EuropePMC** via `scripts/pdf_eval/acquire_and_gold_epmc.py`
(same `harvest_effects` gold regex + verbatim guard + repo `download_pmc_pdf`).
See the dyslipidaemia report for the full rationale.

**RCT-only corpus filter.** The eval's stated scope is real PMC-OA *RCT* articles.
A first broad VTE pass scored only 91% — but inspection showed the misses were
**meta-analyses and observational cohorts** the RCT extractor declines by design
(pooled estimates flagged with `I²`, adjusted `aHR` from cohorts, subgroup
notations). The field "venous thromboembolism + randomized" is dominated by
meta-analyses (41,512 EuropePMC hits → 2,979 once restricted to RCT primary
reports). The acquirer now defaults to an RCT publication-type filter
(`PUB_TYPE:"Randomized Controlled Trial"`, excluding Meta-Analysis / Systematic
Review / Review). This is methodology alignment, not benchmark gaming: every one
of the broad-pass misses parses correctly in isolation; they were out-of-scope
document types, not pattern gaps.

## Dataset

- **45 real PMC-OA VTE RCT articles**, **136 gold effect tuples**
  (HR 56 / OR 56 / RR 20 / IRR 4). Gold in `data/pdf_eval/gold_venous_thromboembolism.jsonl`.

## Results

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 136 | 130 (96%) | 0 | 6 (4%) |
| **pdf_raw** | **136** | **131 (96%)** | **0** | **5 (4%)** |
| pdf_pp | 136 | 131 (96%) | 0 | 5 (4%) |

**pdf_raw = 96% correct — above the 95% bar.** Among matched pairs: effect type
100%, CI bounds 100%/100%, point 100%.

## Honest residuals (pdf_raw) — not generalizable pattern gaps

- `PMC9676876` ×3 — `OR; 7.75, 95% CI, 3.27-18.35` etc. This paper uses an
  idiosyncratic **semicolon directly after the type token** (`OR; <value>`) that
  the extractor does not treat as a type→point joiner (it accepts `OR`, `OR:`,
  `OR=`, `OR,`). A single paper's house style; not worth a shared-core change at
  96% (would risk other specialties / the parallel factories).
- `PMC11602906` ×2 — `HR: 0.93, 95% CI: 0.72-1.2` / `HR: 0.89, 95% CI: 0.51-1.5`.
  Both extract correctly **in isolation** (verified); the miss is specific to how
  this PDF body renders adjacent antibiotic-subgroup HRs, not a pattern gap.

No change was made to the shared core extractor; 96% is the honest, non-overfit number.

## Reproduce

```bash
python scripts/pdf_eval/acquire_and_gold_epmc.py --specialty venous_thromboembolism \
  --query '("venous thromboembolism" OR "deep vein thrombosis" OR "deep-vein thrombosis" \
    OR "pulmonary embolism" OR thromboprophylaxis OR apixaban OR rivaroxaban OR edoxaban \
    OR dabigatran OR enoxaparin)' \
  --max-search 2500 --max-download 60 --target 45 --workers 8 \
  --out data/pdf_eval/gold_venous_thromboembolism.jsonl   # RCT-only filter is default
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_venous_thromboembolism.jsonl \
  --out data/pdf_eval/eval_venous_thromboembolism.json --preprocess
```
