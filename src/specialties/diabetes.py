"""
Type 2 Diabetes (T2DM) Subspecialty Patterns and Endpoints

Built for the same African-student meta-analysis workflow as the malaria, HIV and
typhoid profiles. Type 2 diabetes is a rising Africa-priority NCD; its RCTs report
a distinct endpoint vocabulary (glycaemic control, cardiovascular/renal outcome
trials, hypoglycaemia safety) the generic effect-size engine does not recognise on
its own.

Subspecialties:
- Glycaemic (glucose-lowering efficacy): HbA1c reduction (continuous), fasting
  plasma glucose, HbA1c target attainment (<7%), body-weight change, time-in-range.
  Drug classes: metformin, SGLT2 inhibitors (empagliflozin, dapagliflozin,
  canagliflozin, ertugliflozin), GLP-1 receptor agonists (liraglutide, semaglutide,
  dulaglutide, exenatide), the dual GIP/GLP-1 agonist tirzepatide, DPP-4 inhibitors
  (sitagliptin, linagliptin), sulfonylureas, thiazolidinediones, insulin.
- Cardiorenal (CVOT / kidney outcomes): MACE (3-point major adverse cardiovascular
  events), cardiovascular death, myocardial infarction, stroke, hospitalisation for
  heart failure, all-cause mortality; renal composite, end-stage kidney disease,
  eGFR slope, urine albumin-to-creatinine ratio (UACR, log-normal).
- Hypoglycaemia (safety): severe hypoglycaemia, documented symptomatic
  hypoglycaemia, nocturnal hypoglycaemia.
- Complications (microvascular / acute): diabetic retinopathy, nephropathy
  progression, peripheral neuropathy, lower-limb amputation, diabetic ketoacidosis.

Effect measures follow what these trials report: binary (target attainment, MACE,
HF hospitalisation, ESKD, hypoglycaemia, retinopathy) -> RR/OR/HR/RD; continuous
(HbA1c change, FPG, body weight, eGFR slope, time-in-range) -> MD/SMD; UACR ->
GMR (log-normal, pool on the log scale).
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# DIABETES ENDPOINTS
# ============================================================

DIABETES_ENDPOINTS = {
    # --- Glycaemic efficacy ---
    'HBA1C_REDUCTION': {
        'aliases': ['hba1c', 'haemoglobin a1c', 'hemoglobin a1c', 'glycated haemoglobin',
                    'glycated hemoglobin', 'glycosylated haemoglobin', 'glycosylated hemoglobin',
                    'change in hba1c', 'hba1c reduction', 'hba1c change', 'a1c reduction',
                    'glycaemic control', 'glycemic control'],
        'subspecialty': 'glycemic',
        'measure_types': ['MD', 'SMD']
    },
    'FASTING_PLASMA_GLUCOSE': {
        'aliases': ['fasting plasma glucose', 'fasting blood glucose', 'fpg',
                    'fasting glucose', 'change in fasting plasma glucose'],
        'subspecialty': 'glycemic',
        'measure_types': ['MD', 'SMD']
    },
    'HBA1C_TARGET': {
        'aliases': ['hba1c target', 'hba1c <7%', 'hba1c below 7', 'glycaemic target',
                    'glycemic target', 'target hba1c attainment', 'hba1c goal',
                    'achieved hba1c', 'hba1c <7.0%'],
        'subspecialty': 'glycemic',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'BODY_WEIGHT': {
        'aliases': ['body weight', 'weight change', 'weight loss', 'weight reduction',
                    'change in body weight', 'body-weight change'],
        'subspecialty': 'glycemic',
        'measure_types': ['MD', 'SMD']
    },
    'TIME_IN_RANGE': {
        'aliases': ['time in range', 'time-in-range', 'tir', 'glucose time in range'],
        'subspecialty': 'glycemic',
        'measure_types': ['MD', 'SMD']
    },

    # --- Cardiorenal (CVOT / kidney) ---
    'MACE': {
        'aliases': ['mace', 'major adverse cardiovascular events',
                    'major adverse cardiovascular event', '3-point mace', 'three-point mace',
                    'composite cardiovascular outcome', 'cardiovascular composite',
                    'major adverse cardiac events'],
        'subspecialty': 'cardiorenal',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'CV_DEATH': {
        'aliases': ['cardiovascular death', 'cardiovascular mortality', 'cv death',
                    'death from cardiovascular causes', 'cardiovascular-related death'],
        'subspecialty': 'cardiorenal',
        'measure_types': ['HR', 'RR']
    },
    'MYOCARDIAL_INFARCTION': {
        'aliases': ['myocardial infarction', 'nonfatal myocardial infarction',
                    'non-fatal myocardial infarction', 'heart attack', 'nonfatal mi'],
        'subspecialty': 'cardiorenal',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'STROKE': {
        'aliases': ['stroke', 'nonfatal stroke', 'non-fatal stroke', 'ischaemic stroke',
                    'ischemic stroke', 'cerebrovascular event'],
        'subspecialty': 'cardiorenal',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'HF_HOSPITALIZATION': {
        'aliases': ['hospitalization for heart failure', 'hospitalisation for heart failure',
                    'heart failure hospitalization', 'heart failure hospitalisation',
                    'hhf', 'hospitalized for heart failure', 'worsening heart failure'],
        'subspecialty': 'cardiorenal',
        'measure_types': ['HR', 'RR']
    },
    'ALL_CAUSE_MORTALITY': {
        'aliases': ['all-cause mortality', 'all cause mortality', 'death from any cause',
                    'total mortality', 'overall mortality'],
        'subspecialty': 'cardiorenal',
        'measure_types': ['HR', 'RR', 'OR']
    },
    'RENAL_COMPOSITE': {
        'aliases': ['renal composite', 'kidney composite', 'composite kidney outcome',
                    'composite renal outcome', 'kidney disease progression',
                    'ckd progression', 'composite renal endpoint'],
        'subspecialty': 'cardiorenal',
        'measure_types': ['HR', 'RR']
    },
    'ESKD': {
        'aliases': ['end-stage kidney disease', 'end stage kidney disease',
                    'end-stage renal disease', 'end stage renal disease', 'eskd', 'esrd',
                    'kidney failure', 'chronic dialysis', 'sustained dialysis',
                    'renal replacement therapy', 'doubling of serum creatinine'],
        'subspecialty': 'cardiorenal',
        'measure_types': ['HR', 'RR']
    },
    'EGFR_SLOPE': {
        'aliases': ['egfr slope', 'egfr decline', 'rate of egfr decline',
                    'estimated gfr slope', 'annual egfr change', 'chronic egfr slope',
                    'total egfr slope'],
        'subspecialty': 'cardiorenal',
        'measure_types': ['MD', 'SMD']
    },
    'UACR': {
        'aliases': ['uacr', 'urine albumin-to-creatinine ratio',
                    'urinary albumin-to-creatinine ratio', 'urine albumin to creatinine ratio',
                    'albumin-to-creatinine ratio', 'albumin creatinine ratio',
                    'urinary albumin creatinine ratio'],
        'subspecialty': 'cardiorenal',
        'measure_types': ['GMR', 'MD', 'SMD']
    },
    'ALBUMINURIA': {
        'aliases': ['albuminuria', 'new-onset macroalbuminuria', 'macroalbuminuria',
                    'progression to macroalbuminuria', 'new macroalbuminuria',
                    'microalbuminuria'],
        'subspecialty': 'cardiorenal',
        'measure_types': ['RR', 'OR', 'HR']
    },

    # --- Hypoglycaemia (safety) ---
    'SEVERE_HYPOGLYCEMIA': {
        'aliases': ['severe hypoglycaemia', 'severe hypoglycemia',
                    'severe hypoglycaemic event', 'severe hypoglycemic event',
                    'level 3 hypoglycaemia', 'level 3 hypoglycemia'],
        'subspecialty': 'hypoglycemia',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'DOCUMENTED_HYPOGLYCEMIA': {
        'aliases': ['documented symptomatic hypoglycaemia', 'documented symptomatic hypoglycemia',
                    'confirmed hypoglycaemia', 'confirmed hypoglycemia',
                    'symptomatic hypoglycaemia', 'symptomatic hypoglycemia',
                    'level 2 hypoglycaemia', 'level 2 hypoglycemia',
                    'overall hypoglycaemia', 'overall hypoglycemia'],
        'subspecialty': 'hypoglycemia',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'NOCTURNAL_HYPOGLYCEMIA': {
        'aliases': ['nocturnal hypoglycaemia', 'nocturnal hypoglycemia',
                    'night-time hypoglycaemia', 'nighttime hypoglycemia'],
        'subspecialty': 'hypoglycemia',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Complications (microvascular / acute) ---
    'RETINOPATHY': {
        'aliases': ['diabetic retinopathy', 'retinopathy', 'retinopathy progression',
                    'worsening retinopathy', 'sight-threatening retinopathy'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'NEPHROPATHY': {
        'aliases': ['diabetic nephropathy', 'nephropathy', 'nephropathy progression',
                    'incident nephropathy', 'diabetic kidney disease'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'NEUROPATHY': {
        'aliases': ['diabetic neuropathy', 'peripheral neuropathy', 'neuropathy',
                    'distal symmetric polyneuropathy'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'AMPUTATION': {
        'aliases': ['amputation', 'lower-limb amputation', 'lower limb amputation',
                    'minor amputation', 'major amputation', 'foot amputation'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR', 'HR']
    },
    'DKA': {
        'aliases': ['diabetic ketoacidosis', 'ketoacidosis', 'dka'],
        'subspecialty': 'complications',
        'measure_types': ['RR', 'OR']
    },
}


# ============================================================
# GLYCAEMIC PATTERNS (glucose-lowering efficacy)
# ============================================================

GLYCEMIC_PATTERNS = {
    'detection_keywords': [
        r'metformin', r'\w*gliflozin\b', r'sglt[- ]?2\s+inhibitor',
        r'\w*glutide\b', r'glp[- ]?1\s+receptor\s+agonist', r'tirzepatide',
        r'\w*gliptin\b', r'dpp[- ]?4\s+inhibitor', r'sulfonylurea|sulphonylurea',
        r'glimepiride|gliclazide|glibenclamide|glyburide|glipizide',
        r'pioglitazone|rosiglitazone|thiazolidinedione',
        r'insulin\s+(?:glargine|degludec|detemir|aspart|lispro)|basal\s+insulin',
        r'hba1c|glycated\s+ha?emoglobin|glycosylated\s+ha?emoglobin',
        r'fasting\s+plasma\s+glucose|fasting\s+blood\s+glucose',
        r'glyca?emic\s+control', r'time[- ]in[- ]range',
    ],
    'endpoint_patterns': [
        (r'hba1c|ha?emoglobin\s+a1c|glyc(?:at|osylat)ed\s+ha?emoglobin|'
         r'glyca?emic\s+control|\ba1c\b', 'HBA1C_REDUCTION'),
        (r'fasting\s+(?:plasma|blood)\s+glucose|fasting\s+glucose|\bfpg\b',
         'FASTING_PLASMA_GLUCOSE'),
        (r'hba1c\s+(?:target|goal|<\s*7)|glyca?emic\s+target|hba1c\s+attainment|'
         r'achieved\s+hba1c|target\s+hba1c', 'HBA1C_TARGET'),
        (r'body[- ]?weight|weight\s+(?:change|loss|reduction)', 'BODY_WEIGHT'),
        (r'time[- ]in[- ]range|\btir\b', 'TIME_IN_RANGE'),
    ],
    'context_patterns': [
        r'change\s+from\s+baseline', r'treatment\s+difference|placebo[- ]adjusted',
        r'week\s+(?:24|26|52|104)', r'least[- ]squares\s+mean|ls\s+mean',
    ]
}


# ============================================================
# CARDIORENAL PATTERNS (CVOT / kidney outcomes)
# ============================================================

CARDIORENAL_PATTERNS = {
    'detection_keywords': [
        r'major\s+adverse\s+cardiovascular\s+events?|\bmace\b',
        r'cardiovascular\s+(?:death|mortality|outcome)',
        r'hospitali[sz]ation\s+for\s+heart\s+failure|\bhhf\b',
        r'myocardial\s+infarction', r'nonfatal\s+stroke|non[- ]fatal\s+stroke',
        r'renal\s+composite|kidney\s+composite|composite\s+(?:renal|kidney)\s+outcome',
        r'end[- ]stage\s+(?:kidney|renal)\s+disease|\beskd\b|\besrd\b',
        r'egfr\s+slope|egfr\s+decline', r'albumin[- ](?:to[- ])?creatinine\s+ratio|\buacr\b',
        r'doubling\s+of\s+serum\s+creatinine', r'cardiovascular\s+outcome\s+trial|\bcvot\b',
    ],
    'endpoint_patterns': [
        (r'major\s+adverse\s+cardiovascular\s+events?|\bmace\b|3[- ]point\s+mace|'
         r'composite\s+cardiovascular\s+outcome', 'MACE'),
        (r'cardiovascular\s+(?:death|mortality)|death\s+from\s+cardiovascular\s+causes|'
         r'\bcv\s+death\b', 'CV_DEATH'),
        (r'(?:non[- ]?fatal\s+)?myocardial\s+infarction|heart\s+attack', 'MYOCARDIAL_INFARCTION'),
        (r'(?:non[- ]?fatal\s+|ischa?emic\s+)?stroke|cerebrovascular\s+event', 'STROKE'),
        (r'hospitali[sz]ation\s+for\s+heart\s+failure|heart\s+failure\s+hospitali[sz]ation|'
         r'\bhhf\b|worsening\s+heart\s+failure', 'HF_HOSPITALIZATION'),
        (r'all[- ]cause\s+mortality|death\s+from\s+any\s+cause|total\s+mortality',
         'ALL_CAUSE_MORTALITY'),
        (r'renal\s+composite|kidney\s+composite|composite\s+(?:renal|kidney)\s+(?:outcome|endpoint)|'
         r'ckd\s+progression|kidney\s+disease\s+progression', 'RENAL_COMPOSITE'),
        (r'end[- ]stage\s+(?:kidney|renal)\s+disease|\beskd\b|\besrd\b|kidney\s+failure|'
         r'(?:sustained|chronic)\s+dialysis|doubling\s+of\s+serum\s+creatinine', 'ESKD'),
        (r'egfr\s+slope|egfr\s+decline|rate\s+of\s+egfr|estimated\s+gfr\s+slope', 'EGFR_SLOPE'),
        (r'(?:urin(?:e|ary)\s+)?albumin[- ](?:to[- ])?creatinine\s+ratio|\buacr\b', 'UACR'),
        (r'macroalbuminuria|albuminuria', 'ALBUMINURIA'),
    ],
    'context_patterns': [
        r'per\s+(?:100|1000)\s+(?:patient|person)[- ]years', r'hazard\s+ratio|\bhr\b',
        r'time[- ]to[- ]event', r'cardiovascular\s+safety',
    ]
}


# ============================================================
# HYPOGLYCAEMIA PATTERNS (safety)
# ============================================================

HYPOGLYCEMIA_PATTERNS = {
    'detection_keywords': [
        r'severe\s+hypoglyca?emia', r'documented\s+symptomatic\s+hypoglyca?emia',
        r'confirmed\s+hypoglyca?emia', r'symptomatic\s+hypoglyca?emia',
        r'nocturnal\s+hypoglyca?emia', r'hypoglyca?emic\s+event',
        r'level\s+[23]\s+hypoglyca?emia', r'\bhypoglyca?emia\b',
    ],
    'endpoint_patterns': [
        (r'severe\s+hypoglyca?emia|severe\s+hypoglyca?emic\s+event|level\s+3\s+hypoglyca?emia',
         'SEVERE_HYPOGLYCEMIA'),
        (r'documented\s+symptomatic\s+hypoglyca?emia|confirmed\s+hypoglyca?emia|'
         r'symptomatic\s+hypoglyca?emia|level\s+2\s+hypoglyca?emia|overall\s+hypoglyca?emia',
         'DOCUMENTED_HYPOGLYCEMIA'),
        (r'nocturnal\s+hypoglyca?emia|night[- ]?time\s+hypoglyca?emia', 'NOCTURNAL_HYPOGLYCEMIA'),
    ],
    'context_patterns': [
        r'events?\s+per\s+(?:patient|person)[- ]year', r'glucose\s+<\s*54\s*mg',
        r'requiring\s+(?:assistance|third[- ]party)', r'blood\s+glucose\s+\d',
    ]
}


# ============================================================
# COMPLICATIONS PATTERNS (microvascular / acute)
# ============================================================

COMPLICATIONS_PATTERNS = {
    'detection_keywords': [
        r'diabetic\s+retinopathy|retinopathy\s+progression',
        r'diabetic\s+nephropathy|diabetic\s+kidney\s+disease',
        r'(?:diabetic|peripheral)\s+neuropathy',
        r'lower[- ]limb\s+amputation|foot\s+amputation',
        r'diabetic\s+ketoacidosis|\bdka\b',
    ],
    'endpoint_patterns': [
        (r'diabetic\s+retinopathy|retinopathy(?:\s+progression)?|sight[- ]threatening\s+retinopathy',
         'RETINOPATHY'),
        (r'diabetic\s+nephropathy|nephropathy(?:\s+progression)?|diabetic\s+kidney\s+disease',
         'NEPHROPATHY'),
        (r'(?:diabetic|peripheral|distal\s+symmetric)\s+(?:poly)?neuropathy|\bneuropathy\b',
         'NEUROPATHY'),
        (r'(?:lower[- ]limb|foot|minor|major)?\s*amputation', 'AMPUTATION'),
        (r'diabetic\s+ketoacidosis|ketoacidosis|\bdka\b', 'DKA'),
    ],
    'context_patterns': [
        r'microvascular', r'fundus\s+photograph', r'monofilament',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_diabetes_subspecialty(text: str) -> Tuple[str, float]:
    """Detect type-2 diabetes trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: glycemic, cardiorenal, hypoglycemia, complications, general_diabetes."""
    text_lower = text.lower()
    scores = {'glycemic': 0, 'cardiorenal': 0, 'hypoglycemia': 0, 'complications': 0}
    for kw in GLYCEMIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['glycemic'] += 1
    for kw in CARDIORENAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['cardiorenal'] += 1
    for kw in HYPOGLYCEMIA_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['hypoglycemia'] += 1
    for kw in COMPLICATIONS_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['complications'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_diabetes', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_diabetes_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'glycemic': GLYCEMIC_PATTERNS['endpoint_patterns'],
        'cardiorenal': CARDIORENAL_PATTERNS['endpoint_patterns'],
        'hypoglycemia': HYPOGLYCEMIA_PATTERNS['endpoint_patterns'],
        'complications': COMPLICATIONS_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_diabetes_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical diabetes endpoint, preferring the LONGEST matching
    alias so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in DIABETES_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
