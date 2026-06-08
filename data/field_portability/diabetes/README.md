# Type 2 Diabetes (T2DM) RCT Extraction — Test Results

The diabetes extractor (`src/specialties/diabetes.py` + `diabetes_arm_data.py`,
registered in the specialty registry) reuses the shared effect-augmenter and
arm-data engine with type-2-diabetes endpoints and glucose-lowering drug-class arm
labels. Type 2 diabetes is a rising Africa-priority NCD; its trials are
**continuous-heavy** (HbA1c change is the dominant estimand) and dominated by large
cardiovascular / renal outcome trials (CVOTs).

- **glycemic** — HbA1c reduction (continuous), fasting plasma glucose, HbA1c-target
  attainment (<7%), body-weight change, time-in-range (metformin / SGLT2 inhibitors
  empagliflozin-dapagliflozin-canagliflozin / GLP-1 RAs liraglutide-semaglutide-
  dulaglutide / dual GIP-GLP-1 tirzepatide / DPP-4 inhibitors / sulfonylureas /
  thiazolidinediones / insulin arms).
- **cardiorenal** — 3-point MACE, cardiovascular death, myocardial infarction,
  stroke, hospitalisation for heart failure, all-cause mortality; renal composite,
  end-stage kidney disease, eGFR slope, urine albumin-to-creatinine ratio (UACR,
  log-normal).
- **hypoglycemia** — severe, documented symptomatic, and nocturnal hypoglycaemia.
- **complications** — diabetic retinopathy, nephropathy, peripheral neuropathy,
  lower-limb amputation, diabetic ketoacidosis.

## Tested on real data (2026-06-08)

Corpus from PubMed: **1,498 type-2-diabetes RCTs / 923 OA PMCIDs / 214 NCT /
1,470 abstracts** (retmax 1,500). T2DM is a very large field, so this is a
recent-1,500 slice of the search term, not the full PubMed RCT count.

| Check | Result | Notes |
|---|---|---|
| **Published T2D meta-analyses** (silver gold) | **92.4%** (318/344) | point+CI agreement across 120 T2D MAs; all-CI numbers 77.8% (424) |
| **Effect internal-consistency** | **98.6%** | of 214 abstract effects (Altman-Bland / midpoint checks), 250-abstract slice |
| **Arm-level proportion consistency** | **100.0%** | reported % == 100·events/total (22 proportions) |
| **Subspecialty routing** | glycemic 146 / general 66 / cardiorenal 13 / complications 5 / hypoglycemia 4 | of a 250-abstract slice detected as diabetes |
| **Effect-type mix** | MD 61 / HR 53 / OR 37 / SMD 29 / RR 28 | MD (HbA1c/weight/eGFR) leads — the field is continuous-heavy |
| **AACT external gold** | dense (CVOTs) | unlike typhoid/malaria, T2DM pharma CVOTs (EMPA-REG, CANVAS, DECLARE, LEADER…) post numeric results on ClinicalTrials.gov; `build_aact_diabetes_gold.py` is ready — run with an AACT snapshot |
| **Abstract→PDF cross-check** | tooling ready | `download_diabetes_pdfs.py` (923 OA PMCIDs) + `cross_check.py`; identical to HIV/malaria — run when downloading the full-text set |

### Honest findings
- Diabetes RCTs are **continuous-heavy**: HbA1c change (MD/SMD) is the primary
  estimand, so the continuous path (mean±SD, Wan IQR→SD) is exercised more than
  2×2 tables — abstract 2×2 yield is low and *expected* to be (10 tables across the
  250-abstract slice; most n/N tables live in full text). 51 continuous rows were
  recovered from the slice.
- **UACR is pooled log-normally** (use GMR, not raw MD) — flagged automatically by
  the arm-data engine, mirroring typhoid's anti-Vi titre handling.
- The **7.6% of published-MA estimates we miss** are dominated by *off-topic
  association ORs* (fracture / dementia / respiratory-disease risk in diabetics)
  surfaced by the broad T2D-MA search, plus a few **general** core format gaps
  (inline-defined `(SMD) = …`, effect label separated from its value by an
  intervening clause) — not diabetes-specific mis-reads. These are shared-core
  formats; fixing them belongs in `malaria_effects.py` as a strict-superset change
  validated across all specialties, not in the diabetes profile.
- **CVOT routing**: the diabetes keyword set is weighted with drug-class names so
  cardiovascular-outcome-trial abstracts (heavy in "cardiovascular death", "heart
  failure") route to **diabetes/cardiorenal**, not cardiology.

Tooling: `scripts/diabetes/` (build_diabetes_corpus, download_diabetes_pdfs,
validate_diabetes, validate_diabetes_ma, analyze_diabetes_ma_misses,
build_aact_diabetes_gold, cross_check).
