# Real-PDF Accuracy — pulmonary-hypertension (PAH) specialty

> Same non-circular methodology as `docs/PDF_ACCURACY_EVAL.md`: gold harvested by
> the repo's independent regex (`build_gold_from_abstracts.harvest_effects`,
> verbatim guard) from each article's abstract; scored on the **full PDF body**.
> Corpus + abstracts from EuropePMC (eutils DNS-unreachable here), RCT-only filter.

## Scope + sample-size note (disclosed)

The gold harvester captures only **ratio** effects (OR/RR/HR/IRR) stated with a
95% CI. Pulmonary-hypertension RCTs are **continuous-outcome dominated** — their
primary endpoints are 6-minute walk distance, pulmonary vascular resistance and
mean PAP (mean differences), which are NOT ratio effects and so are out of the
gold harvester's scope. The gold set is therefore the subset of PH trials that
report a ratio endpoint with CI (mostly time-to-clinical-worsening HRs and event
ORs/RRs): **19 papers / 26 gold tuples** — small but in-scope and traceable. The
specialty's continuous 6MWD/PVR/mPAP/NT-proBNP endpoints are fully supported by
the arm-level extractor (unit-tested) but are simply not part of this
ratio-based gold measurement.

## Results

| surface | gold | correct | point_only | missed |
|---|---|---|---|---|
| abstract | 26 | 25 (96%) | 0 | 1 (4%) |
| **pdf_raw** | **26** | **26 (100%)** | **0** | **0** |
| pdf_pp | 26 | 26 (100%) | 0 | 0 |

**pdf_raw = 26/26 = 100% correct — above the 95% bar** (type 100%, CI 100%/100%).
(The single abstract-surface miss does not affect the full-PDF result, which is
the reported metric.)

## Subspecialties

functional (6-minute walk distance, WHO functional class, Borg dyspnoea),
hemodynamics (PVR, mean PAP, cardiac index — continuous), clinical_worsening
(time to clinical worsening, PH hospitalisation, all-cause mortality), biomarker
(NT-proBNP/BNP — continuous). Arm labels: PDE5 inhibitors (sildenafil, tadalafil),
endothelin-receptor antagonists (bosentan, ambrisentan, macitentan),
prostacyclin-pathway (epoprostenol, treprostinil, iloprost, selexipag),
riociguat, sotatercept.

No core-extractor change was needed; nothing overfit.

## Reproduce

```bash
python scripts/pdf_eval/acquire_and_gold_epmc.py --specialty pulmonary_hypertension \
  --query '(TITLE:"pulmonary arterial hypertension" OR ABSTRACT:"pulmonary arterial hypertension" OR \
    TITLE:"pulmonary hypertension" OR ABSTRACT:"pulmonary hypertension" OR bosentan OR macitentan OR \
    ambrisentan OR riociguat OR selexipag OR treprostinil OR epoprostenol OR sotatercept)' \
  --max-search 3500 --max-download 65 --target 50 --workers 8 \
  --out data/pdf_eval/gold_pulmonary_hypertension.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_pulmonary_hypertension.jsonl \
  --out data/pdf_eval/eval_pulmonary_hypertension.json --preprocess
```
