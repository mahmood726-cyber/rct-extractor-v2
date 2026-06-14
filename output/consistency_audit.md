# Internal-consistency audit — `validation_dataset.jsonl`

Run of the all-specialty consistency screen over a real abstract batch.

## Coverage

- Records processed: **156**
- Effects extracted: **167** (checkable: 166)
- Flagged: **0** (0.0%) · repaired (reversed-CI): 0 · needs-review: 0 · hard failures: 0

## Flags by code

- (none — every extraction was internally consistent)

## Gold cross-check (primary effect vs gold point estimate)

- Gold-comparable records: **156**
- Extracted within 10% of gold: **153** (98.1%)
- Extracted off by >10%: **3** (of which the consistency screen flagged 0)

> **Finding:** internal consistency ≠ correctness. The gold-misses below are each *internally consistent* (point inside its CI, etc.) but grab the wrong estimand / comparison / unit — so the consistency screen cannot catch them. These need source-grounding + multi-candidate-disambiguation checks (next increment).

### Gold-miss extractions (the actionable errors)

- **INPULSIS**: gold Mean Difference `109.9` → extracted HR `0.64` · flags=[]
  - _INPULSIS: Nintedanib reduced annual FVC decline in IPF (-113.6 vs -223.5 ml/year; difference 109.9 ml/year; 95% CI, 75.9-144.0; P<0.001). Ti_
- **RA-BEAM**: gold Odds Ratio `3.0` → extracted OR `1.4` · flags=[]
  - _RA-BEAM: Baricitinib showed superior ACR20 response vs placebo at week 12 (70% vs 40%; OR 3.0, 95% CI 2.3-4.0). vs adalimumab: OR 1.4 (1.0-1_
- **4S-NNT**: gold Relative Risk Reduction `0.3` → extracted RRR `30.0` · flags=[]
  - _4S: Simvastatin in CHD patients. Total mortality RRR 30% (95% CI 21-38%). NNT 30 over 5.4 years to prevent one death. Landmark statin surviv_

## Sample flagged / errored extractions

