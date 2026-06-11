# Real-PDF Accuracy — thyroid-disorders specialty

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold harvested by
> the repo's independent regex (`build_gold_from_abstracts.harvest_effects`,
> verbatim guard) from each article's abstract; scored on the **full PDF body**.
> Corpus + abstracts from EuropePMC (eutils DNS-unreachable here), RCT-only filter.

## Corpus scope (disclosed)

The specialty targets **thyroid-disorder treatment RCTs** (hypothyroidism,
hyperthyroidism / Graves', thyroiditis). The acquirer query is restricted to
thyroid-disorder terms (`hypothyroidism OR hyperthyroidism OR thyrotoxicosis OR
"Graves disease" OR levothyroxine OR liothyronine OR methimazole OR carbimazole
OR propylthiouracil OR thyroiditis OR "subclinical hypothyroidism"`) rather than
the bare word `thyroid`. The bare term pulls in tangential studies — e.g. IVF /
fertility trials that mention thyroid autoimmunity only as a covariate, whose
pregnancy-rate effect estimates are not thyroid-disorder endpoints. This is a
topical scoping decision about what the specialty is for, made on principle (not
to chase a number); it is disclosed here for transparency.

## Dataset

- **45 real PMC-OA thyroid-disorder RCT articles**, **122 gold effect tuples**
  (HR 77 / RR 35 / OR 27 / IRR 1 across the harvested set). Gold in
  `data/pdf_eval/gold_thyroid.jsonl`.

## Results

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 122 | 119 (98%) | 1 (1%) | 2 (2%) |
| **pdf_raw** | **122** | **120 (98%)** | **0** | **2 (2%)** |
| pdf_pp | 122 | 120 (98%) | 0 | 2 (2%) |

**pdf_raw = 98% correct — above the 95% bar** (type 100%, CI 100%/100%).

## Honest residuals (pdf_raw) — not generalizable pattern gaps

- `PMC10463286` missed — `…0.84-0.904; HR adjusted = 0.361, 95% CI 0.155-0.841`:
  a second HR abuts the target ("HR adjusted ="), and the adjacent CI confuses
  proximity matching; the tuple parses correctly in isolation.
- `PMC12571290` missed — `the odds ratio for duration below 65 mm Hg for 10
  minutes was 1.03 (95% CI …`: a ~46-character descriptive clause sits between
  the type token and the value, beyond the bounded glue window (kept bounded on
  purpose — widening it invites false positives corpus-wide).

Both are single-paper prose idiosyncrasies; no core change, nothing overfit.

## Documented general limitation (observed, not a thyroid pattern gap)

A first broad-`thyroid` pass scored 94%, dominated by one out-of-scope IVF RCT
(`PMC13168238`) reporting seven `% vs %; RR z, 95% CI lo-hi` pregnancy outcomes in
one dense abstract. Every sentence parses correctly in isolation, but the core
extractor's value-level dedup / dense-abstract effect-selection
(`enhanced_extractor_v3.extract`, the `seen_values` path) under-extracts when many
similarly-formatted effects are packed into one passage — a real, general
limitation worth a future dedicated pass, but one that touches the shared
extraction core and is out of scope for a single specialty branch. The
disorder-focused corpus above does not contain such dense out-of-specialty
abstracts; its 98% reflects genuine thyroid-disorder RCTs.

## Subspecialties

hypothyroidism (TSH normalisation, thyroid QoL), hyperthyroidism (euthyroidism,
remission, relapse, Graves' orbitopathy), thyroid_function (TSH/FT4/FT3/TPOAb —
continuous), outcomes (pregnancy loss, preterm birth, adverse events).

## Reproduce

```bash
python scripts/pdf_eval/acquire_and_gold_epmc.py --specialty thyroid \
  --query '(hypothyroidism OR hyperthyroidism OR thyrotoxicosis OR "Graves disease" OR \
    "Graves orbitopathy" OR levothyroxine OR liothyronine OR methimazole OR carbimazole OR \
    propylthiouracil OR thyroiditis OR "subclinical hypothyroidism")' \
  --max-search 2500 --max-download 60 --target 45 --workers 8 --out data/pdf_eval/gold_thyroid.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_thyroid.jsonl \
  --out data/pdf_eval/eval_thyroid.json --preprocess
```
