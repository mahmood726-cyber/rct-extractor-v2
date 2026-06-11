# Real-PDF Accuracy — dyslipidaemia / lipid-lowering specialty

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`. Gold values are
> harvested by the repo's independent regex (`build_gold_from_abstracts.harvest_effects`,
> verbatim-substring anti-fabrication guard) from each article's abstract; the
> extractor is then scored on the **full PDF body** — a different, messier surface.

## Provenance note (honest)

The canonical pipeline fetches search results + abstracts from NCBI E-utilities
(`eutils.ncbi.nlm.nih.gov`). In this build environment that host was unreachable
at the DNS level (`getaddrinfo failed`) while EuropePMC resolved normally. The
gold for this specialty was therefore sourced via
`scripts/pdf_eval/acquire_and_gold_epmc.py`, which:

- searches **EuropePMC** (OA, in-EPMC, has-PDF, English) instead of eutils;
- takes the article's abstract from the EuropePMC `core` record (real, author-written
  publisher prose), HTML-stripped with the same normalisation as the XML path;
- harvests gold with the **identical** `harvest_effects` regex + verbatim guard;
- downloads the real PMC-OA rendered PDF with the repo's own `download_pmc_pdf`
  (EuropePMC render → PMC OA tgz fallback, `%PDF`-verified);
- the extractor is then scored on the full PDF body by `run_pdf_eval.py`.

The only substantive change from the eutils path is the *source of the abstract
text* (EuropePMC vs eutils db=pmc) — both are the same article's own abstract.

## Dataset

- **45 real PMC Open-Access lipid-lowering RCT articles**, **169 gold effect tuples**
  (OR 83 / RR 37 / HR 49). Each identified by PMID + PMCID; every gold tuple stores
  the verbatim abstract quote it came from. PDFs are gitignored (re-fetchable);
  gold in `data/pdf_eval/gold_dyslipidaemia.jsonl`.

## Results

Match tolerances: point ±0.02 abs or 2% rel; CI bounds ±0.03 abs or 3% rel.
`correct` = effect type + point + both CI bounds all within tolerance.

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 169 | 159 (94%) | 1 (1%) | 9 (5%) |
| **pdf_raw** | **169** | **166 (98%)** | **1 (1%)** | **2 (1%)** |
| pdf_pp | 169 | 165 (98%) | 1 (1%) | 3 (2%) |

**pdf_raw (the full-PDF surface a user actually gets) = 98% correct — above the
95% bar.** Among matched pairs: effect type 99%, CI bounds 100%/100%.

## Honest residuals (pdf_raw) — not generalizable pattern gaps

All three residual sentences parse correctly **in isolation** (verified), so none
is a missing pattern; each is a paper-/PDF-body-specific artefact:

- `PMC12684614` point_only — gold `aOR 1.01 [0.83–1.24]`; the paper reports a
  near-identical `aHR 1.02 [0.82–1.26]` in the adjacent clause and the scorer
  matched the HR (same point within tolerance, different type). Both are the same
  null result.
- `PMC10956955` ×2 missed — `OR: 0.68; 95% CI: 0.45, 1.03` and
  `OR: 1.31; 95% CI: 0.98, 1.76`. These exact strings DO extract correctly in
  isolation (confirmed); the miss is specific to how this PDF's body renders the
  surrounding text, not a comma-separated-CI-bound gap.

Forcing these would mean special-casing PMCIDs (benchmark gaming). 98% is the
honest, non-overfit number. No change was made to the shared core extractor.

## Reproduce

```bash
python scripts/pdf_eval/acquire_and_gold_epmc.py --specialty dyslipidaemia \
  --query '(statin OR dyslipidemia OR dyslipidaemia OR hypercholesterolemia OR \
    hypercholesterolaemia OR "LDL cholesterol" OR ezetimibe OR evolocumab OR \
    alirocumab OR inclisiran OR "lipid lowering") AND (randomized OR randomised)' \
  --max-search 1500 --max-download 60 --target 45 --workers 8 \
  --out data/pdf_eval/gold_dyslipidaemia.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_dyslipidaemia.jsonl \
  --out data/pdf_eval/eval_dyslipidaemia.json --preprocess
```
