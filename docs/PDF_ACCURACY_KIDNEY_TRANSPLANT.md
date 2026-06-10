# Real-PDF Accuracy — kidney-transplant specialty

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold harvested by
> the repo's independent regex (`build_gold_from_abstracts.harvest_effects`,
> verbatim guard) from each article's abstract; scored on the **full PDF body**.
> Corpus + abstracts from EuropePMC (eutils DNS-unreachable here), RCT-only filter.

## Corpus scope (disclosed) + sample-size note

The query requires a transplant term in the **title/abstract**
(`TITLE:"kidney transplant" OR ABSTRACT:"kidney transplant" OR … renal allograft …`),
not anywhere in full text. Without this restriction EuropePMC also returned
CKD / SGLT2 trials (e.g. CREDENCE) and stroke/AF meta-analyses that merely mention
"kidney transplant" in their exclusion criteria — out-of-scope papers whose pooled
or percentage effects the RCT extractor correctly declines, and which dragged a
broad-query pass down to 91%.

**Supply is genuinely limited**: even at `--max-search 6000`, only **21**
kidney-transplant RCTs state an explicit effect estimate **with a 95% CI in the
abstract** (most report rejection / graft-survival as raw per-arm proportions, not
adjusted ratios + CI). The gold set is therefore 21 papers / **32 gold tuples** —
small but in-scope and fully traceable (cf. typhoid's 28 in the main report).

## Results

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 32 | 32 (100%) | 0 | 0 |
| **pdf_raw** | **32** | **31 (97%)** | **0** | **1 (3%)** |
| pdf_pp | 32 | 31 (97%) | 0 | 1 (3%) |

**pdf_raw = 97% correct — above the 95% bar**; the abstract surface is a clean
100% (the extractor handles every in-scope pattern).

## Generalizable core fix this pass (v6.6 — Y-glyph dash)

The first body-surface miss, `PMC4240460` `HR, 4.56; 95% CI, 2.15Y9.71`, was a font
that renders the en-dash between CI bounds as the letter **`Y`** (`2.15Y9.71` →
`2.15–9.71`). Added a value-independent repair that rewrites `Y` to an en-dash
**only when it sits directly between a decimal lower bound and a numeric upper
bound** (`(\d+\.\d+)\s*[Yy]\s*(\d+(?:\.\d+)?)`), so ordinary prose / gene symbols
are never touched. Generalizable to any PDF with this font corruption; full suite
stayed green.

## Honest residual (pdf_raw) — not a pattern gap

- `PMC6830819` missed — `odds ratio 1.14; 95% confidence interval 0.53–2.40`: in
  this PDF an author email/affiliation block is spliced **between** the "odds
  ratio" token and its value (`…email: …snuh.org).  1.14; 95% CI …`), so the type
  cannot be linked to the estimate. The sentence parses correctly in isolation;
  it is a PDF reading-order artifact, not a pattern gap. (1/32 = 3%.)

No overfitting; the only core change is the value-independent Y-glyph repair.

## Subspecialties

rejection (biopsy-proven acute / antibody-mediated), graft (loss / failure /
survival, delayed graft function), function (eGFR, serum creatinine — continuous),
complications (patient survival, CMV / BK infection, NODAT, PTLD). Arm labels:
tacrolimus, ciclosporin, mycophenolate, azathioprine, sirolimus/everolimus,
belatacept, basiliximab, ATG, corticosteroids. Routes away from the general
`nephrology` specialty (shared eGFR/creatinine vocabulary) via a dedicated test.

## Reproduce

```bash
python scripts/pdf_eval/acquire_and_gold_epmc.py --specialty kidney_transplant \
  --query '(TITLE:"kidney transplant" OR ABSTRACT:"kidney transplant" OR \
    TITLE:"kidney transplantation" OR ABSTRACT:"kidney transplantation" OR \
    TITLE:"renal transplant" OR ABSTRACT:"renal transplant" OR \
    TITLE:"renal transplantation" OR ABSTRACT:"renal transplantation" OR \
    TITLE:"renal allograft" OR ABSTRACT:"renal allograft" OR \
    TITLE:"kidney allograft" OR ABSTRACT:"kidney allograft")' \
  --max-search 6000 --max-download 70 --target 60 --workers 8 \
  --out data/pdf_eval/gold_kidney_transplant.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_kidney_transplant.jsonl \
  --out data/pdf_eval/eval_kidney_transplant.json --preprocess
```
