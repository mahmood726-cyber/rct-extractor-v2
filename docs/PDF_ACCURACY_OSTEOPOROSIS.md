# Real-PDF Accuracy — osteoporosis specialty

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold harvested by
> the repo's independent regex (`build_gold_from_abstracts.harvest_effects`,
> verbatim guard) from each article's abstract; scored on the **full PDF body**.
> Corpus + abstracts from EuropePMC (eutils DNS-unreachable here), RCT-only filter.

## Dataset

- **45 real PMC-OA osteoporosis RCT articles**, **133 gold effect tuples**.
  Gold in `data/pdf_eval/gold_osteoporosis.jsonl`.

## Results

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 133 | 133 (100%) | 0 | 0 |
| **pdf_raw** | **133** | **129 (97%)** | **0** | **4 (3%)** |
| pdf_pp | 133 | 129 (97%) | 0 | 4 (3%) |

**pdf_raw = 97% correct — above the 95% bar** (type 100%, CI 100%/100%; abstract
surface is a clean 100%).

## Generalizable core fix re-applied (v6.6)

The first pass scored 89%, with ~10 point-only cases all from the U+00BC `¼`-for-`=`
glyph in the **CI-keyword** position (`95% CI ¼ 0.07 to 16.62`), seen across
several osteoporosis PDFs (`PMC7853161` ×5, `PMC8346694`, `PMC10697786` ×4). This
is the same value-independent font repair introduced for obesity (extend the
documented `¼`→`=` repair to the CI-keyword position). Re-applied here it lifted
pdf_raw 89%→97% with the full suite green. (It is a core-extractor change; the
coordinator will dedupe it against the obesity branch's identical fix on merge.)

## Honest residuals (pdf_raw) — not generalizable pattern gaps

- `PMC8346694` missed — a SECOND hazard ratio (`hazard ratio = 0.59, 95% CI =
  0.37 to 0.93`) adjacent to the paper's first HR (now extracted); proximity.
- `PMC12589805` / `PMC12179999` / `PMC4742634` missed — `HR 0.08, 95% CI 0.01,
  0.96`, `OR 1.9; 95%CI 1.1-3.1`, `HR was 1.31 (95% CI 0.80-2.15)`. Each parses
  correctly in isolation; the miss is specific to the surrounding PDF-body text.

No further core change; nothing overfit.

## Subspecialties

fracture (vertebral / non-vertebral / hip / clinical / any), bmd (lumbar-spine /
total-hip / femoral-neck BMD — continuous), bone_turnover (CTX, P1NP — continuous),
safety (ONJ, atypical femoral fracture, hypocalcaemia). Arm labels cover
bisphosphonates, denosumab, teriparatide/abaloparatide, romosozumab, SERMs,
strontium ranelate, calcium/vitamin D, hormone therapy.

## Reproduce

```bash
python scripts/pdf_eval/acquire_and_gold_epmc.py --specialty osteoporosis \
  --query '(osteoporosis OR "bone mineral density" OR "vertebral fracture" OR \
    "fragility fracture" OR bisphosphonate OR alendronate OR risedronate OR zoledronic OR \
    denosumab OR teriparatide OR romosozumab OR raloxifene)' \
  --max-search 2500 --max-download 60 --target 45 --workers 8 --out data/pdf_eval/gold_osteoporosis.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_osteoporosis.jsonl \
  --out data/pdf_eval/eval_osteoporosis.json --preprocess
```
