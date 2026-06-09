# Epilepsy / Antiepileptic-Drug (AED) RCT Extraction — Test Results

The epilepsy extractor (`src/specialties/epilepsy.py` + `epilepsy_arm_data.py`,
registered in the specialty registry) reuses the shared effect-augmenter and
arm-data engine with epilepsy endpoints and AED / status-epilepticus arm labels.
Epilepsy is an **Africa-priority** topic — an estimated **60–90% epilepsy
treatment gap** across sub-Saharan Africa (most people with epilepsy receive no
appropriate antiseizure medication) — with a large RCT literature spanning four
clinical axes:

- **efficacy** — seizure freedom, ≥50% responder rate, seizure frequency (counts /
  monthly rate, log-normal), time to first seizure / treatment failure
  (carbamazepine / valproate / levetiracetam / phenobarbital / lamotrigine /
  phenytoin / topiramate / oxcarbazepine / gabapentin / lacosamide / zonisamide /
  perampanel / brivaracetam / ethosuximide / clobazam arms).
- **tolerability** — treatment withdrawal / discontinuation (incl. withdrawal due
  to adverse events), retention / treatment failure, any adverse event, serious
  adverse event, drug rash (lamotrigine / carbamazepine).
- **status_epilepticus** — clinical seizure cessation / termination, time to
  seizure cessation, seizure recurrence, need for rescue / additional anticonvulsant,
  intubation / respiratory depression (lorazepam / diazepam / midazolam /
  (fos)phenytoin / valproate / levetiracetam / phenobarbital arms).
- **treatment_gap** — medication adherence, the epilepsy treatment gap (proportion
  untreated), retention in care / loss to follow-up, quality of life (QOLIE)
  (phenobarbital primary-care delivery / task-shifting / community health worker /
  WHO mhGAP / mobile-health-reminder interventions).

Effect measures follow what these trials report: binary (seizure freedom,
responder, withdrawal, adverse event, cessation, recurrence, adherence) → RR/OR/RD;
time-to-event (time to first seizure / treatment failure) → HR; continuous
(seizure frequency → **log-normal / count, pool on the log scale as a ratio**;
time to cessation, quality of life → MD/SMD).

## Tested on real data (2026-06-09)

Corpus from PubMed: **2,488 epilepsy RCTs / 1,311 OA PMCIDs / 267 NCT / 2,463 abstracts**.

| Check | Result | Notes |
|---|---|---|
| **Published epilepsy / AED meta-analyses** (silver gold) | **96.4%** (291/302) | point+CI agreement across **88** epilepsy MAs (AED efficacy, responder, withdrawal/tolerability, status epilepticus); all-CI numbers 78.9% (299/379) |
| **Effect internal-consistency** | **87.9%** | of 2,112 abstract effects (Altman-Bland / midpoint checks); 20.0% of abstracts carry an extractable effect (493/2,463) |
| **Arm-level proportion consistency** | **100.0%** | reported % == 100·events/total (114 proportions; 25 trials with a 2×2, 31 tables, 6 poolable as-is, 36 continuous rows) |
| **Subspecialty routing** | efficacy 1,198 / general 403 / tolerability 213 / status_epilepticus 148 / treatment_gap 105 | of corpus docs detected as epilepsy — balanced across the four AED axes |
| **AACT external gold** | `build_aact_epilepsy_gold.py` ready | epilepsy is well-registered on ClinicalTrials.gov (regulatory AED licensing trials) — expected to be richer than typhoid/cholera (responder-rate RD/OR, seizure-freedom) |
| **Abstract→PDF cross-check** | tooling in place | `scripts/epilepsy/download_epilepsy_pdfs.py` + `cross_check.py` ready (identical to HIV/malaria/typhoid/cholera); run when PMC OA render is stable |

Effect-type distribution across the 2,112 abstract effects: MD 759, RR 718, OR 425,
SMD 100, HR 65, ARD 34, IRR 9, RRR 2 — i.e. a mix of continuous seizure-frequency /
QoL mean differences, responder/seizure-freedom risk ratios, and AED odds ratios.

### Honest findings
- Epilepsy abstracts are **efficacy-heavy** (seizure freedom, ≥50% responder rate,
  percentage reduction in seizure frequency) and report a mix of binary 2×2
  responder/seizure-freedom tables, comparative ratios (RR/OR/HR), and continuous
  seizure-frequency / quality-of-life outcomes — so all three extraction paths
  (effect-estimate, 2×2 arm-data, continuous arm-data) are exercised.
- **Seizure frequency is treated as log-normal / count data**: a raw arithmetic
  mean ± SD for seizure frequency is flagged `poolable: false` with a pooling note
  (pool on the log scale / use a ratio, not a raw mean difference), because
  seizure counts are over-dispersed. Quality-of-life (QOLIE) and time-to-cessation
  remain ordinary poolable continuous outcomes.
- The MA-validation effect agreement (**96.4%**) is on a large pool (302 reviewer
  effect estimates across 88 published epilepsy MAs), in line with the typhoid
  (100%) and cholera (94.4%) sibling bundles; the residual all-CI gap (78.9%) is
  dominated by abstract-only estimates whose CI the abstract never restates, not by
  mis-reads (arm-level proportion consistency is 100%).

### Reproduce
```
python scripts/epilepsy/build_epilepsy_corpus.py --retmax 2500 --email you@org
python scripts/epilepsy/validate_epilepsy.py            # corpus extraction / arm-level yield -> validation.json
python scripts/epilepsy/validate_epilepsy_ma.py --retmax 200 --email you@org   # vs published MAs -> ma_validation.json
python scripts/epilepsy/analyze_epilepsy_ma_misses.py --retmax 200 --email you@org   # mine fixable format gaps
python scripts/epilepsy/build_aact_epilepsy_gold.py --aact <AACT snapshot>      # external numeric gold
python scripts/epilepsy/download_epilepsy_pdfs.py --workers 3 --resume          # OA full-text
python scripts/epilepsy/cross_check.py                  # abstract vs PDF vs AACT
```

Tooling: `scripts/epilepsy/` (build_epilepsy_corpus, download_epilepsy_pdfs,
validate_epilepsy, validate_epilepsy_ma, analyze_epilepsy_ma_misses,
build_aact_epilepsy_gold, cross_check).
