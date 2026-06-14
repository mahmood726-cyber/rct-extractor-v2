# Internal-consistency audit — `validation_dataset.jsonl`

Run of the all-specialty consistency screen over a real abstract batch.

## Coverage

- Records processed: **156**
- Effects extracted: **167** (checkable: 166)
- Flagged: **18** (10.8%) · repaired (reversed-CI): 0 · needs-review: 18 · hard failures: 0

## Flags by code

- `multiple_effect_types`: 16
- `multiple_candidates`: 2

## Gold cross-check (primary effect vs gold point estimate)

- Gold-comparable records: **156**
- Extracted within 10% of gold: **155** (99.4%)
- Extracted off by >10%: **1** (of which the consistency screen flagged 0)

> **Finding:** internal consistency ≠ correctness. The gold-misses below are each *internally consistent* (point inside its CI, etc.) but grab the wrong estimand / comparison / unit — so the consistency screen cannot catch them. These need source-grounding + multi-candidate-disambiguation checks (next increment).

### Gold-miss extractions (the actionable errors)

- **4S-NNT**: gold Relative Risk Reduction `0.3` → extracted RRR `30.0` · flags=[]
  - _4S: Simvastatin in CHD patients. Total mortality RRR 30% (95% CI 21-38%). NNT 30 over 5.4 years to prevent one death. Landmark statin surviv_

## Sample flagged / errored extractions

- {"id": 25, "trial": "ACTT-1", "type": "IRR", "es": 1.32, "ci": [1.12, 1.55], "flags": ["multiple_effect_types"], "score": 1.0}
- {"id": 25, "trial": "ACTT-1", "type": "RR", "es": 1.32, "ci": [null, null], "flags": ["multiple_effect_types"], "score": 1.0}
- {"id": 26, "trial": "RECOVERY Dexamethasone", "type": "IRR", "es": 0.83, "ci": [0.75, 0.93], "flags": ["multiple_effect_types"], "score": 1.0}
- {"id": 26, "trial": "RECOVERY Dexamethasone", "type": "RR", "es": 0.83, "ci": [0.75, 0.93], "flags": ["multiple_effect_types"], "score": 1.0}
- {"id": 27, "trial": "SOLIDARITY", "type": "IRR", "es": 0.91, "ci": [0.79, 1.05], "flags": ["multiple_effect_types"], "score": 1.0}
- {"id": 27, "trial": "SOLIDARITY", "type": "RR", "es": 0.91, "ci": [0.79, 1.05], "flags": ["multiple_effect_types"], "score": 1.0}
- {"id": 30, "trial": "INPULSIS", "type": "MD", "es": 109.9, "ci": [75.9, 144.0], "flags": ["multiple_effect_types"], "score": 1.0}
- {"id": 30, "trial": "INPULSIS", "type": "HR", "es": 0.64, "ci": [0.39, 1.05], "flags": ["multiple_effect_types"], "score": 1.0}
- {"id": 32, "trial": "RA-BEAM", "type": "OR", "es": 3.0, "ci": [2.3, 4.0], "flags": ["multiple_candidates"], "score": 1.0}
- {"id": 32, "trial": "RA-BEAM", "type": "OR", "es": 1.4, "ci": [1.0, 1.8], "flags": ["multiple_candidates"], "score": 1.0}
- {"id": 97, "trial": "IMPACT (COPD)", "type": "IRR", "es": 0.75, "ci": [0.7, 0.81], "flags": ["multiple_effect_types"], "score": 1.0}
- {"id": 97, "trial": "IMPACT (COPD)", "type": "RR", "es": 0.75, "ci": [0.7, 0.81], "flags": ["multiple_effect_types"], "score": 1.0}
