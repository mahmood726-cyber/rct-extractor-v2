# Immune Thrombocytopenia (ITP) RCT Extraction

The ITP extractor (`rct_extractor/_engine/specialties/itp.py` + `itp_arm_data.py`,
registered in the specialty registry) reuses the shared effect-augmenter and the
arm-data engine (`malaria_arm_data`) with ITP endpoints and immunotherapy /
TPO-RA arm labels — the same one-core-engine / per-topic-profile design as the
tuberculosis and ARDS profiles.

## Subspecialties & endpoints

| Subspecialty | Endpoints |
|---|---|
| **first_line** (corticosteroids, IVIG, anti-D) | platelet response (>=30/>=50 ×10⁹/L), complete response, time to response, bleeding, platelet count |
| **tpo_ra** (eltrombopag, romiplostim, avatrombopag) | durable / sustained platelet response, overall response, rescue therapy, platelet count, bleeding, thromboembolic events |
| **second_line** (rituximab, fostamatinib, splenectomy, FcRn inhibitors) | relapse / loss of response, splenectomy avoidance, durable / complete response, bleeding |
| **paediatric** (childhood / chronic ITP) | platelet response, complete response, bleeding score, time to response, progression to chronic ITP |

**Arm labels** cover TPO-RAs (eltrombopag, romiplostim, avatrombopag,
hetrombopag), immunomodulators (rituximab, fostamatinib, efgartigimod,
mycophenolate), first-line agents (high-dose dexamethasone, prednisone, IVIG,
anti-D), splenectomy and placebo / standard-of-care controls. Binary response /
bleeding / relapse outcomes become 2×2 tables; platelet count (log-normal) and
time to response are extracted as per-arm mean+SD (Wan IQR→SD).

## Real-PDF accuracy (non-circular harness)

Gold is harvested **verbatim from each paper's own abstract** by the independent
regex in `scripts/pdf_eval/build_gold_from_abstracts.py` (substring
anti-fabrication guard) and scored on the **full PDF body**, so the measurement
is not circular. PMC-OA PDFs were acquired via
`scripts/pdf_eval/acquire_specialty_gold_corpus.py` using the RCT query in
`scripts/itp/build_itp_corpus.py`.

**Measured: 138/138 in-scope gold tuples correct = 100% on the full-PDF surface**
(32 PMC-OA papers, 142 gold tuples — a rich ratio-measure pool, 4 out-of-scope
non-randomised tuples excluded). No gold value was hardcoded or overfit; the
engine was untouched.

```
python scripts/itp/build_itp_corpus.py --retmax 1000
python scripts/pdf_eval/acquire_specialty_gold_corpus.py --specialty itp --target 32
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty itp --out data/pdf_eval/gold_itp.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_itp.jsonl --out data/pdf_eval/eval_itp.json
```
