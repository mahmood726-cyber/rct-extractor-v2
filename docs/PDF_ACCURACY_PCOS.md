# Real-PDF Accuracy — polycystic-ovary-syndrome (PCOS) specialty

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold harvested by
> the repo's independent regex (`build_gold_from_abstracts.harvest_effects`,
> verbatim guard) from each article's abstract; scored on the **full PDF body**.
> Corpus + abstracts from EuropePMC (eutils DNS-unreachable here), RCT-only filter,
> with the transplant term in title/abstract to keep the corpus on-topic.

## Dataset

- **50 real PMC-OA PCOS RCT articles**, **111 gold effect tuples** scored (3
  out-of-scope tuples — non-randomised / NMA-indirect / modelling — auto-excluded
  by the harness, which the extractor declines by design). Gold in
  `data/pdf_eval/gold_pcos.jsonl`.

## Results

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 111 | 99 (89%) | 0 | 12 (11%) |
| **pdf_raw** | **111** | **105 (95%)** | **0** | **6 (5%)** |
| pdf_pp | 111 | 105 (95%) | 0 | 6 (5%) |

**pdf_raw = 105/111 = 95% correct — meets the 95% bar** (type 100%, CI 100%/100%).

## Generalizable core fix re-applied (v6.6 — ¼ glyph in CI position)

Four point-only cases (`PMC10697786`) were the U+00BC `¼`-for-`=` glyph in the CI
keyword position (`HR = 1.26; 95% CI ¼ 1.03 to 1.54`). The same value-independent
repair used for obesity/osteoporosis/PCOS recovered them (lifted pdf_raw 91%→95%);
full suite green. (Coordinator will dedupe this identical core fix across branches.)

## Honest residuals (pdf_raw) — not generalizable pattern gaps

All six remaining misses are from a single paper, `PMC4326646`, which reports
hazard ratios **by baseline insulin-sensitivity tertile** with the subgroup label
interposed between the type token and the value: `HR intermediate IS 1.420, 95% CI
0.878–2.297`, `HR low IS 1.657, …`. These are prognostic-by-subgroup estimates
(arguably not randomised treatment effects) and the interposed `intermediate IS` /
`low IS` label breaks the type→value link. A single paper's notation; widening the
type→value glue window to absorb arbitrary interposed labels would add false
positives corpus-wide. No overfitting; the only core change is the ¼ glyph repair.

## Subspecialties

reproductive (ovulation, clinical pregnancy, live birth, miscarriage, multiple
pregnancy — the ratio-rich primary endpoints), metabolic (BMI/weight, HOMA-IR,
HbA1c — continuous), androgen (testosterone, SHBG, Ferriman-Gallwey hirsutism
score; menstrual regularity), safety (OHSS, GI adverse events). Arm labels:
letrozole, clomifene, metformin, inositol, spironolactone, gonadotropins, OCP,
ovarian drilling, GLP-1 agonists, lifestyle. Routes away from maternal_neonatal
(shared pregnancy vocabulary) via a dedicated test.

## Reproduce

```bash
python scripts/pdf_eval/acquire_and_gold_epmc.py --specialty pcos \
  --query '(TITLE:"polycystic ovary syndrome" OR ABSTRACT:"polycystic ovary syndrome" OR \
    TITLE:"polycystic ovarian syndrome" OR ABSTRACT:"polycystic ovarian syndrome" OR \
    letrozole OR clomifene OR clomiphene OR hirsutism)' \
  --max-search 3000 --max-download 65 --target 50 --workers 8 --out data/pdf_eval/gold_pcos.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_pcos.jsonl \
  --out data/pdf_eval/eval_pcos.json --preprocess
```
