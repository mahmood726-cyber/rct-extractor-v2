"""
Gestational Diabetes (GDM) Subspecialty Patterns and Endpoints

Built for the same meta-analysis workflow as the maternal-neonatal, endometriosis
and other women's-health profiles. Gestational diabetes is the most common
medical complication of pregnancy and its RCTs (metformin vs insulin vs glyburide
vs diet, treatment-target and screening-strategy trials) report a distinct
maternal-and-neonatal glycaemic endpoint vocabulary that NEITHER the general
diabetes profile (type 1/2, cardiorenal) NOR the maternal-neonatal profile covers
on its own (no macrosomia / LGA / neonatal-hypoglycaemia endpoints there).

Subspecialties:
- Glycemic (maternal glycaemic control / treatment): treatment-target attainment,
  fasting and postprandial plasma glucose, HbA1c, need for insulin / additional
  pharmacotherapy. Interventions: metformin, glyburide/glibenclamide, insulin,
  medical nutrition therapy / diet, lifestyle.
- Maternal (maternal pregnancy outcomes): pre-eclampsia, gestational
  hypertension, caesarean section, induction of labour, gestational weight gain,
  birth trauma / perineal injury.
- Neonatal (neonatal outcomes): macrosomia, large-for-gestational-age (LGA),
  neonatal hypoglycaemia, birth weight, NICU admission, shoulder dystocia,
  neonatal hyperbilirubinaemia, respiratory distress, small-for-gestational-age.
- Screening (diagnosis / strategy): GDM diagnosis rate, oral glucose tolerance
  test (OGTT), one-step vs two-step screening, IADPSG vs alternative criteria.

Effect measures follow what these trials report: binary (macrosomia, LGA,
neonatal hypoglycaemia, pre-eclampsia, caesarean, insulin requirement, NICU,
shoulder dystocia, GDM diagnosis) -> RR/OR/RD; continuous (fasting/postprandial
glucose, HbA1c, birth weight, gestational weight gain) -> MD/SMD.
"""
from typing import Dict, List, Tuple, Optional
import re

# ============================================================
# GESTATIONAL DIABETES ENDPOINTS
# ============================================================

GESTATIONAL_DIABETES_ENDPOINTS = {
    # --- Glycemic (maternal glycaemic control / treatment) ---
    'GLYCEMIC_TARGET': {
        'aliases': ['glycemic target', 'glycaemic target', 'target attainment',
                    'glycemic control', 'glycaemic control', 'treatment target',
                    'glucose target achieved', 'within-target glucose'],
        'subspecialty': 'glycemic',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'FASTING_GLUCOSE': {
        'aliases': ['fasting plasma glucose', 'fasting glucose', 'fasting blood glucose',
                    'mean fasting glucose', 'fpg'],
        'subspecialty': 'glycemic',
        'measure_types': ['MD', 'SMD']
    },
    'POSTPRANDIAL_GLUCOSE': {
        'aliases': ['postprandial glucose', 'post-prandial glucose', '2-hour glucose',
                    'postprandial blood glucose', '1-hour postprandial',
                    'post-meal glucose', '2-h plasma glucose'],
        'subspecialty': 'glycemic',
        'measure_types': ['MD', 'SMD']
    },
    'HBA1C': {
        'aliases': ['hba1c', 'glycated haemoglobin', 'glycated hemoglobin',
                    'glycosylated haemoglobin', 'glycosylated hemoglobin',
                    'hemoglobin a1c', 'haemoglobin a1c'],
        'subspecialty': 'glycemic',
        'measure_types': ['MD', 'SMD']
    },
    'INSULIN_REQUIREMENT': {
        'aliases': ['need for insulin', 'insulin requirement', 'requirement for insulin',
                    'additional insulin', 'supplemental insulin', 'insulin therapy',
                    'progression to insulin', 'rescue insulin', 'failure of treatment'],
        'subspecialty': 'glycemic',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Maternal (maternal pregnancy outcomes) ---
    'PRE_ECLAMPSIA': {
        'aliases': ['pre-eclampsia', 'preeclampsia', 'pre eclampsia',
                    'pregnancy-induced hypertension', 'hypertensive disorder of pregnancy'],
        'subspecialty': 'maternal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'GESTATIONAL_HYPERTENSION': {
        'aliases': ['gestational hypertension', 'pregnancy hypertension',
                    'hypertensive disorders of pregnancy'],
        'subspecialty': 'maternal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'CAESAREAN': {
        'aliases': ['caesarean section', 'cesarean section', 'caesarean delivery',
                    'cesarean delivery', 'c-section', 'caesarean', 'cesarean'],
        'subspecialty': 'maternal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'INDUCTION_LABOUR': {
        'aliases': ['induction of labour', 'induction of labor', 'labour induction',
                    'labor induction', 'induced labour', 'induced labor'],
        'subspecialty': 'maternal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'GESTATIONAL_WEIGHT_GAIN': {
        'aliases': ['gestational weight gain', 'maternal weight gain',
                    'weight gain in pregnancy', 'pregnancy weight gain'],
        'subspecialty': 'maternal',
        'measure_types': ['MD', 'SMD']
    },

    # --- Neonatal (neonatal outcomes) ---
    'MACROSOMIA': {
        'aliases': ['macrosomia', 'fetal macrosomia', 'foetal macrosomia',
                    'birth weight >4000', 'birthweight over 4000',
                    'birth weight greater than 4000', 'macrosomic infant'],
        'subspecialty': 'neonatal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'LARGE_FOR_GESTATIONAL_AGE': {
        'aliases': ['large for gestational age', 'large-for-gestational-age', 'lga',
                    'large for gestational-age infant', 'birth weight above the 90th'],
        'subspecialty': 'neonatal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'NEONATAL_HYPOGLYCAEMIA': {
        'aliases': ['neonatal hypoglycaemia', 'neonatal hypoglycemia',
                    'newborn hypoglycaemia', 'newborn hypoglycemia',
                    'infant hypoglycaemia', 'infant hypoglycemia'],
        'subspecialty': 'neonatal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'BIRTH_WEIGHT': {
        'aliases': ['birth weight', 'birthweight', 'mean birth weight',
                    'neonatal birth weight', 'infant birth weight'],
        'subspecialty': 'neonatal',
        'measure_types': ['MD', 'SMD']
    },
    'NICU_ADMISSION': {
        'aliases': ['nicu admission', 'admission to nicu', 'neonatal intensive care',
                    'admission to neonatal intensive care', 'special care nursery',
                    'neonatal unit admission'],
        'subspecialty': 'neonatal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'SHOULDER_DYSTOCIA': {
        'aliases': ['shoulder dystocia', 'birth trauma', 'birth injury',
                    'brachial plexus injury'],
        'subspecialty': 'neonatal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'NEONATAL_HYPERBILIRUBINAEMIA': {
        'aliases': ['hyperbilirubinaemia', 'hyperbilirubinemia', 'neonatal jaundice',
                    'jaundice requiring phototherapy', 'phototherapy'],
        'subspecialty': 'neonatal',
        'measure_types': ['RR', 'OR', 'RD']
    },
    'RESPIRATORY_DISTRESS': {
        'aliases': ['respiratory distress syndrome', 'neonatal respiratory distress',
                    'respiratory distress', 'rds', 'transient tachypnoea',
                    'transient tachypnea'],
        'subspecialty': 'neonatal',
        'measure_types': ['RR', 'OR', 'RD']
    },

    # --- Screening (diagnosis / strategy) ---
    'GDM_DIAGNOSIS': {
        'aliases': ['gdm diagnosis', 'diagnosis of gestational diabetes',
                    'incidence of gestational diabetes', 'gdm incidence',
                    'gestational diabetes diagnosis', 'detection of gdm',
                    'gdm prevalence'],
        'subspecialty': 'screening',
        'measure_types': ['RR', 'OR', 'RD']
    },
}


# ============================================================
# GLYCEMIC PATTERNS
# ============================================================

GLYCEMIC_PATTERNS = {
    'detection_keywords': [
        r'glyca?emic\s+(?:control|target)', r'fasting\s+(?:plasma\s+)?glucose',
        r'postprandial\s+glucose|post[- ]prandial', r'hba1c|glycated\s+h[ae]moglobin',
        r'metformin', r'glyburide|glibenclamide', r'\binsulin\b',
        r'medical\s+nutrition\s+therapy|dietary\s+(?:therapy|intervention)',
        r'need\s+for\s+insulin|insulin\s+requirement', r'self[- ]monitoring\s+of\s+blood\s+glucose',
    ],
    'endpoint_patterns': [
        (r'glyca?emic\s+target|target\s+attainment|glyca?emic\s+control|'
         r'treatment\s+target|glucose\s+target', 'GLYCEMIC_TARGET'),
        (r'fasting\s+(?:plasma\s+|blood\s+)?glucose|\bfpg\b', 'FASTING_GLUCOSE'),
        (r'(?:postprandial|post[- ]prandial|post[- ]meal)\s+(?:blood\s+)?glucose|'
         r'(?:1|2)[- ]h(?:our)?\s+(?:postprandial\s+|plasma\s+)?glucose', 'POSTPRANDIAL_GLUCOSE'),
        (r'hba1c|glyc(?:ated|osylated)\s+h[ae]moglobin|h[ae]moglobin\s+a1c', 'HBA1C'),
        (r'need\s+for\s+insulin|insulin\s+requirement|requirement\s+for\s+insulin|'
         r'additional\s+insulin|progression\s+to\s+insulin|rescue\s+insulin|'
         r'failure\s+of\s+(?:diet|treatment)', 'INSULIN_REQUIREMENT'),
    ],
    'context_patterns': [
        r'mg\/dl|mmol\/l', r'change\s+from\s+baseline', r'per\s+protocol',
    ]
}


# ============================================================
# MATERNAL PATTERNS
# ============================================================

MATERNAL_PATTERNS = {
    'detection_keywords': [
        r'pre[- ]?eclampsia', r'gestational\s+hypertension', r'caesarean|cesarean',
        r'induction\s+of\s+lab(?:ou)?r', r'gestational\s+weight\s+gain|maternal\s+weight\s+gain',
        r'hypertensive\s+disorder',
    ],
    'endpoint_patterns': [
        (r'pre[- ]?eclampsia', 'PRE_ECLAMPSIA'),
        (r'gestational\s+hypertension|pregnancy[- ]induced\s+hypertension|'
         r'hypertensive\s+disorders?\s+of\s+pregnancy', 'GESTATIONAL_HYPERTENSION'),
        (r'caesarean(?:\s+(?:section|delivery))?|cesarean(?:\s+(?:section|delivery))?|'
         r'c[- ]section', 'CAESAREAN'),
        (r'induction\s+of\s+lab(?:ou)?r|lab(?:ou)?r\s+induction|induced\s+lab(?:ou)?r',
         'INDUCTION_LABOUR'),
        (r'gestational\s+weight\s+gain|maternal\s+weight\s+gain|weight\s+gain\s+in\s+pregnancy',
         'GESTATIONAL_WEIGHT_GAIN'),
    ],
    'context_patterns': [
        r'\d+\s+weeks(?:\'|\s+of)?\s+gestation', r'per\s+protocol',
    ]
}


# ============================================================
# NEONATAL PATTERNS
# ============================================================

NEONATAL_PATTERNS = {
    'detection_keywords': [
        r'macrosomia', r'large[- ]for[- ]gestational[- ]age|\blga\b',
        r'neonatal\s+hypoglyca?emia', r'birth\s*weight', r'nicu\s+admission|neonatal\s+intensive\s+care',
        r'shoulder\s+dystocia', r'hyperbilirubina?emia|neonatal\s+jaundice|phototherapy',
        r'respiratory\s+distress', r'small[- ]for[- ]gestational[- ]age',
    ],
    'endpoint_patterns': [
        (r'macrosomi[ac]|birth\s*weight\s*(?:>|greater\s+than|over|above)\s*4000', 'MACROSOMIA'),
        (r'large[- ]for[- ]gestational[- ]age|\blga\b|birth\s*weight\s+above\s+the\s+90th',
         'LARGE_FOR_GESTATIONAL_AGE'),
        (r'neonatal\s+hypoglyca?emia|newborn\s+hypoglyca?emia|infant\s+hypoglyca?emia',
         'NEONATAL_HYPOGLYCAEMIA'),
        (r'birth\s*weight|birthweight', 'BIRTH_WEIGHT'),
        (r'nicu\s+admission|admission\s+to\s+(?:the\s+)?(?:nicu|neonatal\s+intensive\s+care)|'
         r'special\s+care\s+nursery|neonatal\s+unit\s+admission', 'NICU_ADMISSION'),
        (r'shoulder\s+dystocia|birth\s+(?:trauma|injury)|brachial\s+plexus', 'SHOULDER_DYSTOCIA'),
        (r'hyperbilirubina?emia|neonatal\s+jaundice|jaundice\s+requiring\s+phototherapy|'
         r'\bphototherapy\b', 'NEONATAL_HYPERBILIRUBINAEMIA'),
        (r'respiratory\s+distress(?:\s+syndrome)?|\brds\b|transient\s+tachypn(?:o)?ea',
         'RESPIRATORY_DISTRESS'),
    ],
    'context_patterns': [
        r'\bgrams?\b|\bkg\b', r'>\s*4000\s*g|>\s*4\s*kg', r'90th\s+(?:centile|percentile)',
    ]
}


# ============================================================
# SCREENING PATTERNS
# ============================================================

SCREENING_PATTERNS = {
    'detection_keywords': [
        r'oral\s+glucose\s+tolerance\s+test|\bogtt\b', r'one[- ]step|two[- ]step',
        r'iadpsg', r'screening\s+for\s+gestational\s+diabetes',
        r'diagnosis\s+of\s+gestational\s+diabetes', r'gdm\s+(?:diagnosis|incidence|prevalence)',
    ],
    'endpoint_patterns': [
        (r'(?:gdm|gestational\s+diabetes)\s+(?:diagnosis|incidence|prevalence)|'
         r'diagnosis\s+of\s+gestational\s+diabetes|incidence\s+of\s+gestational\s+diabetes|'
         r'detection\s+of\s+gdm', 'GDM_DIAGNOSIS'),
    ],
    'context_patterns': [
        r'75[- ]g\s+ogtt|100[- ]g\s+ogtt', r'24[- ]28\s+weeks',
    ]
}


# ============================================================
# SUBSPECIALTY DETECTION
# ============================================================

def detect_gestational_diabetes_subspecialty(text: str) -> Tuple[str, float]:
    """Detect GDM trial subspecialty. Returns (subspecialty, confidence).
    Subspecialties: glycemic, maternal, neonatal, screening, general_gdm."""
    text_lower = text.lower()
    scores = {'glycemic': 0, 'maternal': 0, 'neonatal': 0, 'screening': 0}
    for kw in GLYCEMIC_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['glycemic'] += 1
    for kw in MATERNAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['maternal'] += 1
    for kw in NEONATAL_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['neonatal'] += 1
    for kw in SCREENING_PATTERNS['detection_keywords']:
        if re.search(kw, text_lower):
            scores['screening'] += 1

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return ('general_gdm', 0.5)
    return (best, scores[best] / total if total else 0.5)


def get_gestational_diabetes_endpoint_patterns(subspecialty: str) -> List[Tuple[str, str]]:
    return {
        'glycemic': GLYCEMIC_PATTERNS['endpoint_patterns'],
        'maternal': MATERNAL_PATTERNS['endpoint_patterns'],
        'neonatal': NEONATAL_PATTERNS['endpoint_patterns'],
        'screening': SCREENING_PATTERNS['endpoint_patterns'],
    }.get(subspecialty, [])


def normalize_gestational_diabetes_endpoint(endpoint: str, subspecialty: str = None) -> str:
    """Normalize to canonical GDM endpoint, preferring the LONGEST matching alias
    so specific endpoints win over generic substrings."""
    endpoint_lower = endpoint.lower()
    best, best_len = None, 0
    for canonical, info in GESTATIONAL_DIABETES_ENDPOINTS.items():
        for alias in info['aliases']:
            if alias in endpoint_lower and len(alias) > best_len:
                best, best_len = canonical, len(alias)
    return best if best else endpoint.upper()
