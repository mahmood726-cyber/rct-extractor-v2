# Independent re-verification of the self-reported specialties (2026-06-13)

**Extractor under test:** `master` HEAD `c21d33c` of `rct-extractor-v2` (92
specialties registered), scored with
`rct_extractor.extract(text, specialty=<sp>)` on the **full real-PDF body**
(`pdf_raw` surface via the repo `PDFParser`).
**Branch:** `reverify-catalogue-2026-06-13` (master extractor code untouched).

## Why this run exists

The catalogue's per-specialty ≥95% real-PDF accuracy was, for several recently
merged waves, **self-reported by the build branch and never independently
re-run on master**. The prior independent sweep (`docs/PDF_REVERIFY_30.md`,
2026-06-11) covered the 30 onc-/cardiometab-/npg- specialties. This run closes
the remaining self-reported gap:

1. **Factory G (7):** cataract, allergic_conjunctivitis, chronic_rhinosinusitis,
   otitis_media, obstructive_sleep_apnea, alcohol_use_disorder, insomnia
   — merged "code-complete, self-reported ≥95%, not independently verified".
2. **glioma** (branch-measured 93%) and **myelodysplastic_syndrome / MDS**
   (branch-measured 96% with the core fix) — re-confirmed on master.
3. **Spot sample** of Factory F oncology/heme and the ccs/wru ("D/E") waves.

## Method (identical to PDF_REVERIFY_30, non-circular, re-acquired)

Same four-step harness as the 2026-06-11 sweep, re-run from scratch:

1. **Re-acquired corpora** from the specialty's **own committed corpus `*_TERM`**
   (`scripts/<sp>/build_<sp>_corpus.py`, AST-parsed verbatim) via EuropePMC
   open-access search.
2. **Gold re-harvested verbatim from each abstract** by the independent regex
   harvester with the **verbatim-substring anti-fabrication guard** — the
   extractor never produces gold.
3. **RCT-only scoping** via the harvester's **independent** design-marker filter
   (per-effect 220-char window + paper-level non-RCT guard); flagged tuples are
   excluded from scoring, never counted as misses.
4. **Scored on the full real-PDF body.** `correct` = right effect **type** AND
   point AND **both** CI bounds within tolerance (point 0.02 abs/rel; CI 0.03).
   The gate is `correct / in-scope gold`.

### One infrastructure change, fully disclosed (truth-first)

The PDF *mirror* changed, **nothing else**. As of 2026-06-13 the two PDF routes
the prior sweep used are both unavailable on this host: the EuropePMC rendered-PDF
endpoint returns HTTP 500, and NCBI retired the `oa_package` FTP tree (oa.fcgi
now advertises dead paths). The **same real PMC-OA PDFs** were fetched from the
**AWS Open Data mirror** (`pmc-oa-opendata` S3 bucket,
`PMC<id>.<ver>/PMC<id>.<ver>.pdf`, `%PDF` magic verified). The corpus query, the
gold source (abstract), the scoping filter, and the scoring surface (full PDF
body) are unchanged. Script: `scripts/pdf_eval/acquire_via_s3.py`.

## TL;DR

- **22 self-reported specialties re-measured from scratch on master; 21 confirm
  ≥95% real-PDF accuracy, overall 1993/2015 = 98.91%.**
- **The one shortfall is `glioma` at 93.1%** — a genuine (small) HR-pattern gap,
  exactly matching its own branch-measured 93%. It was never truly ≥95% and
  should not carry a ≥95% badge.
- All 7 **Factory G** specialties confirm (97.9–100%); **MDS** confirms at 99.3%.
- **Scope exclusions are legitimate, not gamed** (zero genuine-RCT effects
  excluded across all 22, manually spot-confirmed) **but they are load-bearing**:
  the broad `randomized` corpus query is heavily contaminated with
  cohort/Mendelian-randomization/meta-analysis papers, so for some specialties the
  in-scope denominator is a minority of harvested tuples. The ≥95% gate is a
  **recall** measure on RCT-effect tuples; it does **not** measure precision (the
  extractor still fires on non-RCT papers).
- **Catalogue status after this run: 52 / 92 specialties independently
  re-verified** by this harness (30 prior + 22 here); **38 / 92 remain
  self-reported / branch-measured.**

## Headline result (primary targets)

| metric | value |
|---|---|
| primary specialties re-verified | **9** (7 Factory G + glioma + MDS) |
| ≥95% on `pdf_raw` | **8 / 9** |
| overall `pdf_raw` correct | **729 / 737 = 98.91%** |
| only specialty below 95% | **glioma (93.1%)** — matches its branch-measured 93% |

## Per-specialty re-verified accuracy (`pdf_raw`, master `c21d33c`)

| specialty | papers | in-scope gold | correct | point_only | missed | out-of-scope | pdf_raw % | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|:--|
| allergic_conjunctivitis | 41 | 61 | 61 | 0 | 0 | 67 | **100.0%** | ✅ CONFIRM |
| cataract | 41 | 58 | 58 | 0 | 0 | 76 | **100.0%** | ✅ CONFIRM |
| chronic_rhinosinusitis | 39 | 46 | 46 | 0 | 0 | 90 | **100.0%** | ✅ CONFIRM |
| insomnia | 40 | 65 | 65 | 0 | 0 | 38 | **100.0%** | ✅ CONFIRM |
| obstructive_sleep_apnea | 40 | 84 | 84 | 0 | 0 | 70 | **100.0%** | ✅ CONFIRM |
| myelodysplastic_syndrome | 40 | 145 | 144 | 0 | 1 | 30 | **99.3%** | ✅ CONFIRM |
| otitis_media | 40 | 125 | 124 | 0 | 1 | 72 | **99.2%** | ✅ CONFIRM |
| alcohol_use_disorder | 41 | 95 | 93 | 1 | 1 | 82 | **97.9%** | ✅ CONFIRM |
| **glioma** | 40 | 58 | 54 | 0 | 4 | 6 | **93.1%** | ⚠️ **BELOW 95%** |

**All 7 Factory G specialties independently confirm ≥95%** (97.9–100%). The
self-reported numbers held. **MDS confirms at 99.3%** (branch reported 96% "with
the core fix"; master is higher). **glioma is genuinely 93.1%** — its branch
already measured 93%; it was never truly ≥95% and this run does not paper over
that.

### glioma — honest cause of the 93.1% (4 misses)

| PMCID | gold tuple | cause |
|---|---|---|
| PMC11266256 | OR **349.9** (247.6–494.4) | **gold over-inclusion** — an implausible biomarker odds ratio, not a treatment arm comparison; the extractor correctly declined it |
| PMC12833535 | HR 1.21 (0.88–1.65) | genuine gap — "hazard ratio:1.21 **favoring placebo,** 95% CI…"; the interjected clause breaks the point→CI proximity |
| PMC12573252 | HR 1.22 (0.73–2.04) | genuine gap — short-form "HR 1.22; 95% CI 0.73-2.04" lost in the PDF text layer |
| PMC4678179 | HR 1.04 (0.69–1.58) | genuine gap — standard HR phrasing missed |

Removing only the implausible gold artifact, glioma is **54/57 = 94.7%** — still
below 95%. The shortfall is a real (small) HR-pattern gap, **not** corpus
contamination or over-aggressive exclusion. **glioma is the one specialty in this
set that should not carry a ≥95% badge.**

The other three single misses (otitis_media 1, MDS 1, alcohol 2) are: a non-standard
"OR **to** 1.67" construction, a standard HR lost in the PDF text layer, and two
pooled ORs from a statin **meta-analysis** paper (PMC12934547) that the paper-level
guard did not flag — i.e. mostly contamination, not extractor gaps.

## (B) Scope-exclusion audit — are exclusions "doing too much work"?

This is the load-bearing question for the catalogue's honesty, and the answer is
**two-sided**:

| specialty | in-scope | oos | as-is % | stress % (if NOTHING excluded) | oos-on-RCT |
|---|---:|---:|---:|---:|---:|
| chronic_rhinosinusitis | 46 | 90 | 100.0% | **33.8%** | 0 |
| cataract | 58 | 76 | 100.0% | **43.3%** | 0 |
| allergic_conjunctivitis | 61 | 67 | 100.0% | **47.7%** | 0 |
| obstructive_sleep_apnea | 84 | 70 | 100.0% | 54.5% | 0 |
| otitis_media | 125 | 72 | 99.2% | 62.9% | 0 |
| insomnia | 65 | 38 | 100.0% | 63.1% | 0 |
| alcohol_use_disorder | 95 | 82 | 97.9% | 52.5% | 0 |
| myelodysplastic_syndrome | 145 | 30 | 99.3% | 82.3% | 0 |
| glioma | 58 | 6 | 93.1% | 84.4% | 0 |

**The exclusions ARE load-bearing** — for the ENT/eye specialties the in-scope
denominator is a *minority* of harvested tuples (chronic_rhinosinusitis excludes
90 of 136). If you scored every harvested effect, those specialties would read
34–48%. **But the exclusions are legitimate, not gamed:**

- **`oos-on-RCT = 0` everywhere** — not a single excluded tuple comes from a
  genuine-RCT abstract. Every exclusion is a paper the *independent* abstract
  design-marker filter identified as non-RCT.
- **Manually confirmed** (chronic_rhinosinusitis, the worst case): the 90 excluded
  tuples are nationwide **cohort** studies, **systematic reviews / meta-analyses**,
  cross-sectional studies, and — repeatedly — **Mendelian randomization** papers.
  "Mendelian **randomization**" is a systematic false match for the broad
  `randomized` full-text corpus query; it is correctly excluded.
- The high out-of-scope ratio is therefore **corpus contamination from the broad
  query**, not the filter wrongly removing RCT effects to flatter the score.

### The honest limitation the headline does NOT capture (precision)

The ≥95% gate is **recall** of abstract-stated, in-scope RCT effects recovered
from the PDF body. It is **not** precision. On papers that are *entirely*
out-of-scope (every tuple flagged non-RCT), the extractor still emits **8–18
effect tuples per paper** (e.g. allergic_conjunctivitis: 306 extractions across 21
fully-non-RCT papers). The extractor does **not** wholesale-decline non-RCT papers
— it pulls every effect+CI it can pattern-match, including Mendelian-randomization
causal estimates and meta-analysis forest-plot pools. So on a contaminated corpus
the extractor's *precision* would be much lower than its recall. The catalogue's
≥95% claim is specifically a recall claim on RCT-effect tuples, and that claim is
verified; readers should not read it as "the extractor only ever fires on RCT
arm-comparison effects."

## Spot-check sample (Factory F oncology/heme + ccs/wru "D/E" waves)

To confirm the catalogue holds beyond the primary targets, 13 further
recently-merged specialties were re-acquired and scored by the identical harness.

| metric | value |
|---|---|
| spot-check specialties | **13** |
| ≥95% on `pdf_raw` | **13 / 13** |
| overall `pdf_raw` correct | **1264 / 1278 = 98.90%** |

| specialty | papers | in-scope gold | correct | point_only | missed | out-of-scope | pdf_raw % | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|:--|
| anaemia | 40 | 132 | 132 | 0 | 0 | 50 | **100.0%** | ✅ |
| ards | 40 | 88 | 88 | 0 | 0 | 86 | **100.0%** | ✅ |
| endometrial_cancer | 40 | 90 | 90 | 0 | 0 | 114 | **100.0%** | ✅ |
| endometriosis | 40 | 82 | 82 | 0 | 0 | 106 | **100.0%** | ✅ |
| gestational_diabetes | 40 | 73 | 73 | 0 | 0 | 131 | **100.0%** | ✅ |
| itp | 40 | 109 | 109 | 0 | 0 | 67 | **100.0%** | ✅ |
| multiple_myeloma | 40 | 137 | 137 | 0 | 0 | 39 | **100.0%** | ✅ |
| testicular_cancer | 40 | 100 | 100 | 0 | 0 | 64 | **100.0%** | ✅ |
| wound_healing | 40 | 97 | 96 | 1 | 0 | 50 | **99.0%** | ✅ |
| thyroid_cancer | 40 | 106 | 103 | 0 | 3 | 78 | **97.2%** | ✅ |
| erectile_dysfunction | 40 | 59 | 57 | 2 | 0 | 101 | **96.6%** | ✅ |
| influenza | 40 | 114 | 110 | 0 | 4 | 63 | **96.5%** | ✅ |
| sarcoma | 40 | 91 | 87 | 1 | 3 | 52 | **95.6%** | ✅ |

Same picture as the primary set: every spot-check specialty clears the gate; the
handful of misses classify as meta-analysis / observational contamination
(`thyroid_cancer` 3× non-RCT, `influenza` 3× mixed/MA, `sarcoma` 3× mixed/MA),
not extractor pattern gaps; and `oos-on-RCT = 0` for all 13 (exclusions
legitimate, load-bearing on the contaminated corpora — `gestational_diabetes`
and `erectile_dysfunction` stress-test to ~36%).

## Combined result (this run)

| | papers | in-scope gold | correct | ≥95% | overall |
|---|---:|---:|---:|---:|---:|
| primary (9) | 362 | 737 | 729 | 8/9 | 98.91% |
| spot-check (13) | 520 | 1278 | 1264 | 13/13 | 98.90% |
| **total (22)** | **882** | **2015** | **1993** | **21/22** | **98.91%** |

## Catalogue-wide: how much is now independently verified?

`master` registers **92 specialties.** Counting only specialties whose real-PDF
≥95% has been **re-run from scratch by this non-circular abstract-gold harness**
(not trusted from a branch eval JSON):

| status | count | specialties |
|---|---:|---|
| **Independently re-verified — abstract-gold real-PDF harness** | **52 / 92** | 30 in `PDF_REVERIFY_30.md` (2026-06-11) + 22 here |
| └ of which **confirm ≥95%** | **46** | (this run 21/22; prior sweep 25/30) |
| └ **measured below 95%** | **6** | `glioma` (93.1%, genuine gap) + 5 prior (`renal_cell_carcinoma`, `kidney_transplant`, `pulmonary_hypertension`, `cirrhosis`, `alzheimers` — attributed to corpus contamination, extractor behaving correctly) |
| **Foundational template (validated separately)** | **2** | `hiv`, `malaria` |
| **Still self-reported / branch-measured only** | **38 / 92** | see list below |

**The 38 not independently re-run by this harness** (some have *other* validation
— e.g. `sickle_cell` 97.8% and `typhoid` 100% published-MA agreement — but were
not put through this abstract-gold real-PDF harness):

> allergic_rhinitis, benign_prostatic_hyperplasia, cardiology, cervical_cancer,
> cholera, chronic_pain, dermatology, diabetes, diarrhoeal, gastroenterology,
> helminths, hepatitis, hypertension, infertility_ivf, low_back_pain,
> malnutrition, maternal_neonatal, meningitis, menopause_hrt, nephrology,
> oncology, ophthalmology, orthopaedic, perioperative, pneumonia,
> postoperative_pain, psychiatry, respiratory, rheumatology, schistosomiasis,
> sickle_cell, stroke, transfusion, tuberculosis, typhoid, urinary_incontinence,
> urticaria, uterine_fibroids

## Honest overall statement

After this run, **57% of the 92-specialty catalogue (52/92) has been
independently re-verified on the real PDF body by the repo's own non-circular
harness, and 46 of those clear ≥95%.** Across the **22 self-reported specialties
this run targeted, 21 confirm ≥95% (overall 98.91%)** — the self-reported numbers
held up almost everywhere. **The single genuine exception is `glioma` (93.1%)**,
which was already branch-measured at 93% and should be relabelled accordingly.

The verification is **trustworthy on its own terms** — gold is harvested verbatim
from abstracts by an independent regex, scored on the messy full PDF text, and the
scope filter excludes only genuinely non-RCT tuples (zero genuine-RCT effects
removed, manually confirmed). **The one caveat a reader must hold:** the ≥95%
figure is **recall of RCT-effect tuples on a scope-filtered subset**, and because
the broad corpus query admits many non-RCT papers, that subset can be a minority
of what was harvested. The number is honest about what it measures; it is not a
precision guarantee, and `38/92` of the catalogue still rests on self-reported
branch evals that this run did not touch.

## Artifacts

Tags: `primary9` (the 9 primary targets), `spotcheck` (the 13 spot-check
specialties). `RUN_META.txt` records the exact master/branch commits + date.

- `data/pdf_eval/reverify/gold_<sp>.jsonl` — per-specialty re-harvested gold (22).
- `data/pdf_eval/reverify/eval_{primary9,spotcheck}.json` — per-paper scoring.
- `data/pdf_eval/reverify/summary_{primary9,spotcheck}.json` — per-specialty table.
- `data/pdf_eval/reverify/scope_{primary9,spotcheck}.json` — scope audit + miss buckets.
- `scripts/pdf_eval/acquire_via_s3.py` — AWS S3 OA-mirror corpus acquisition.
- `scripts/pdf_eval/reverify_targets.sh`, `reverify_score.sh`,
  `reverify_aggregate_targets.py`, `reverify_scope_audit.py` — parameterized harness.
