# Anaphylaxis / Chronic Urticaria RCT Extraction

The urticaria/anaphylaxis extractor
(`rct_extractor/_engine/specialties/urticaria.py` + `urticaria_arm_data.py`,
registered in the specialty registry) reuses the shared effect-augmenter and the
arm-data engine (`malaria_arm_data`) with urticaria endpoints and antihistamine /
biologic arm labels — the same one-core-engine / per-topic-profile design as the
tuberculosis and ARDS profiles.

## Subspecialties & endpoints

| Subspecialty | Endpoints |
|---|---|
| **antihistamine** (H1-antihistamine, updosing for CSU) | UAS7, itch severity (ISS7), hives severity (HSS7), angioedema, DLQI, complete response / well-controlled |
| **biologic** (omalizumab, ligelizumab, BTK inhibitors) | UAS7, complete response (UAS7=0), well-controlled, urticaria control test (UCT), ISS7, DLQI, adverse events |
| **anaphylaxis** (epinephrine, food/venom) | anaphylaxis recurrence / biphasic reaction, symptom resolution, adverse events |
| **other** (ciclosporin, chronic inducible urticaria) | UAS7, complete response, UCT, critical temperature threshold, DLQI |

**Arm labels** cover biologics (omalizumab, ligelizumab, dupilumab, remibrutinib,
fenebrutinib, barzolvolimab), antihistamines (cetirizine, bilastine, fexofenadine,
rupatadine, updosed), ciclosporin, epinephrine and placebo / standard-care
controls. Binary response / well-controlled / recurrence outcomes become 2×2
tables; symptom scores (UAS7, ISS7, HSS7, UCT, DLQI) are extracted as per-arm
mean+SD (Wan IQR→SD).

## Real-PDF accuracy (non-circular harness)

Gold is harvested **verbatim from each paper's own abstract** by the independent
regex in `scripts/pdf_eval/build_gold_from_abstracts.py` (substring
anti-fabrication guard) and scored on the **full PDF body**, so the measurement
is not circular. PMC-OA PDFs were acquired via
`scripts/pdf_eval/acquire_specialty_gold_corpus.py` using the RCT query in
`scripts/urticaria/build_urticaria_corpus.py`.

**Measured: 99/102 in-scope gold tuples correct = 97% on the full-PDF surface**
(32 PMC-OA papers, 102 gold tuples). The 3 imperfect tuples came from two papers
using a comma-separated parenthetical CI format (`RR = 0.68, 95% CI (0.50,
0.92)`) and an integer-bound rate ratio — a generic parser edge case, not a
urticaria-specific gap. No gold value was hardcoded or overfit; the engine was
untouched.

```
python scripts/urticaria/build_urticaria_corpus.py --retmax 1000
python scripts/pdf_eval/acquire_specialty_gold_corpus.py --specialty urticaria --target 32
python scripts/pdf_eval/build_gold_from_abstracts.py --specialty urticaria --out data/pdf_eval/gold_urticaria.jsonl
python scripts/pdf_eval/run_pdf_eval.py --gold data/pdf_eval/gold_urticaria.jsonl --out data/pdf_eval/eval_urticaria.json
```
