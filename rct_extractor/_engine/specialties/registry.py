"""
Specialty Registry - Central registry for all specialty patterns and endpoints.
"""

from typing import Dict, List, Tuple, Optional, Callable
import re

from .cardiology import (
    CARDIOLOGY_ENDPOINTS,
    HEART_FAILURE_PATTERNS,
    ACS_PATTERNS,
    AF_PATTERNS,
    VALVE_PATTERNS,
    detect_cardiology_subspecialty,
    normalize_cardiology_endpoint
)

from .oncology import (
    ONCOLOGY_ENDPOINTS,
    BREAST_CANCER_PATTERNS,
    LUNG_CANCER_PATTERNS,
    GI_ONCOLOGY_PATTERNS,
    detect_oncology_subspecialty,
    normalize_oncology_endpoint
)

from .malaria import (
    MALARIA_ENDPOINTS,
    TREATMENT_PATTERNS as MALARIA_TREATMENT_PATTERNS,
    PREVENTION_PATTERNS as MALARIA_PREVENTION_PATTERNS,
    SEVERE_PATTERNS as MALARIA_SEVERE_PATTERNS,
    TRANSMISSION_PATTERNS as MALARIA_TRANSMISSION_PATTERNS,
    detect_malaria_subspecialty,
    normalize_malaria_endpoint
)

from .hiv import (
    HIV_ENDPOINTS,
    TREATMENT_PATTERNS as HIV_TREATMENT_PATTERNS,
    PREVENTION_PATTERNS as HIV_PREVENTION_PATTERNS,
    PMTCT_PATTERNS as HIV_PMTCT_PATTERNS,
    COINFECTION_PATTERNS as HIV_COINFECTION_PATTERNS,
    detect_hiv_subspecialty,
    normalize_hiv_endpoint
)

from .typhoid import (
    TYPHOID_ENDPOINTS,
    TREATMENT_PATTERNS as TYPHOID_TREATMENT_PATTERNS,
    VACCINE_PATTERNS as TYPHOID_VACCINE_PATTERNS,
    RESISTANCE_PATTERNS as TYPHOID_RESISTANCE_PATTERNS,
    COMPLICATIONS_PATTERNS as TYPHOID_COMPLICATIONS_PATTERNS,
    detect_typhoid_subspecialty,
    normalize_typhoid_endpoint
)

from .schistosomiasis import (
    SCHISTOSOMIASIS_ENDPOINTS,
    TREATMENT_PATTERNS as SCHISTO_TREATMENT_PATTERNS,
    PREVENTION_PATTERNS as SCHISTO_PREVENTION_PATTERNS,
    MORBIDITY_PATTERNS as SCHISTO_MORBIDITY_PATTERNS,
    VACCINE_PATTERNS as SCHISTO_VACCINE_PATTERNS,
    detect_schistosomiasis_subspecialty,
    normalize_schistosomiasis_endpoint
)

from .sickle_cell import (
    SICKLE_CELL_ENDPOINTS,
    DISEASE_MODIFYING_PATTERNS as SCD_DISEASE_MODIFYING_PATTERNS,
    ACUTE_PAIN_PATTERNS as SCD_ACUTE_PAIN_PATTERNS,
    PREVENTION_PATTERNS as SCD_PREVENTION_PATTERNS,
    TRANSFUSION_PATTERNS as SCD_TRANSFUSION_PATTERNS,
    detect_sickle_cell_subspecialty,
    normalize_sickle_cell_endpoint
)

from .cholera import (
    CHOLERA_ENDPOINTS,
    TREATMENT_PATTERNS as CHOLERA_TREATMENT_PATTERNS,
    REHYDRATION_PATTERNS as CHOLERA_REHYDRATION_PATTERNS,
    VACCINE_PATTERNS as CHOLERA_VACCINE_PATTERNS,
    SEVERE_PATTERNS as CHOLERA_SEVERE_PATTERNS,
    detect_cholera_subspecialty,
    normalize_cholera_endpoint
)

from .maternal_neonatal import (
    MATERNAL_NEONATAL_ENDPOINTS,
    MATERNAL_PATTERNS as MNH_MATERNAL_PATTERNS,
    HYPERTENSIVE_PATTERNS as MNH_HYPERTENSIVE_PATTERNS,
    NEONATAL_PATTERNS as MNH_NEONATAL_PATTERNS,
    PRETERM_PATTERNS as MNH_PRETERM_PATTERNS,
    detect_maternal_neonatal_subspecialty,
    normalize_maternal_neonatal_endpoint
)

from .tuberculosis import (
    TUBERCULOSIS_ENDPOINTS,
    TREATMENT_PATTERNS as TB_TREATMENT_PATTERNS,
    DRUG_RESISTANT_PATTERNS as TB_DRUG_RESISTANT_PATTERNS,
    PREVENTION_PATTERNS as TB_PREVENTION_PATTERNS,
    LATENT_PATTERNS as TB_LATENT_PATTERNS,
    detect_tuberculosis_subspecialty,
    normalize_tuberculosis_endpoint
)

from .hepatitis import (
    HEPATITIS_ENDPOINTS,
    TREATMENT_PATTERNS as HEPATITIS_TREATMENT_PATTERNS,
    PREVENTION_PATTERNS as HEPATITIS_PREVENTION_PATTERNS,
    PMTCT_PATTERNS as HEPATITIS_PMTCT_PATTERNS,
    OUTCOMES_PATTERNS as HEPATITIS_OUTCOMES_PATTERNS,
    detect_hepatitis_subspecialty,
    normalize_hepatitis_endpoint
)

from .meningitis import (
    MENINGITIS_ENDPOINTS,
    TREATMENT_PATTERNS as MENINGITIS_TREATMENT_PATTERNS,
    VACCINE_PATTERNS as MENINGITIS_VACCINE_PATTERNS,
    MORTALITY_PATTERNS as MENINGITIS_MORTALITY_PATTERNS,
    SEQUELAE_PATTERNS as MENINGITIS_SEQUELAE_PATTERNS,
    detect_meningitis_subspecialty,
    normalize_meningitis_endpoint
)

from .pneumonia import (
    PNEUMONIA_ENDPOINTS,
    TREATMENT_PATTERNS as PNEUMONIA_TREATMENT_PATTERNS,
    VACCINE_PATTERNS as PNEUMONIA_VACCINE_PATTERNS,
    MORTALITY_PATTERNS as PNEUMONIA_MORTALITY_PATTERNS,
    SEVERE_PATTERNS as PNEUMONIA_SEVERE_PATTERNS,
    detect_pneumonia_subspecialty,
    normalize_pneumonia_endpoint
)

from .diarrhoeal import (
    DIARRHOEAL_ENDPOINTS,
    REHYDRATION_PATTERNS as DIARRHOEAL_REHYDRATION_PATTERNS,
    ROTAVIRUS_PATTERNS as DIARRHOEAL_ROTAVIRUS_PATTERNS,
    TREATMENT_PATTERNS as DIARRHOEAL_TREATMENT_PATTERNS,
    MORTALITY_DURATION_PATTERNS as DIARRHOEAL_MORTALITY_DURATION_PATTERNS,
    detect_diarrhoeal_subspecialty,
    normalize_diarrhoeal_endpoint
)

from .malnutrition import (
    MALNUTRITION_ENDPOINTS,
    THERAPEUTIC_FEEDING_PATTERNS as MALN_THERAPEUTIC_FEEDING_PATTERNS,
    MICRONUTRIENT_PATTERNS as MALN_MICRONUTRIENT_PATTERNS,
    MORTALITY_PATTERNS as MALN_MORTALITY_PATTERNS,
    RECOVERY_GROWTH_PATTERNS as MALN_RECOVERY_GROWTH_PATTERNS,
    detect_malnutrition_subspecialty,
    normalize_malnutrition_endpoint
)

from .helminths import (
    HELMINTHS_ENDPOINTS,
    TREATMENT_PATTERNS as HELMINTHS_TREATMENT_PATTERNS,
    MASS_DEWORMING_PATTERNS as HELMINTHS_MASS_DEWORMING_PATTERNS,
    NUTRITION_PATTERNS as HELMINTHS_NUTRITION_PATTERNS,
    REINFECTION_PATTERNS as HELMINTHS_REINFECTION_PATTERNS,
    detect_helminths_subspecialty,
    normalize_helminths_endpoint
)

from .hypertension import (
    HYPERTENSION_ENDPOINTS,
    BP_LOWERING_PATTERNS as HTN_BP_LOWERING_PATTERNS,
    CV_EVENTS_PATTERNS as HTN_CV_EVENTS_PATTERNS,
    BP_REDUCTION_PATTERNS as HTN_BP_REDUCTION_PATTERNS,
    ADHERENCE_PATTERNS as HTN_ADHERENCE_PATTERNS,
    detect_hypertension_subspecialty,
    normalize_hypertension_endpoint
)

from .cervical_cancer import (
    CERVICAL_CANCER_ENDPOINTS,
    VACCINE_PATTERNS as CC_VACCINE_PATTERNS,
    SCREENING_PATTERNS as CC_SCREENING_PATTERNS,
    TREATMENT_PATTERNS as CC_TREATMENT_PATTERNS,
    MORTALITY_PATTERNS as CC_MORTALITY_PATTERNS,
    detect_cervical_cancer_subspecialty,
    normalize_cervical_cancer_endpoint
)

from .diabetes import (
    DIABETES_ENDPOINTS,
    GLYCEMIC_PATTERNS as DIABETES_GLYCEMIC_PATTERNS,
    CARDIORENAL_PATTERNS as DIABETES_CARDIORENAL_PATTERNS,
    HYPOGLYCEMIA_PATTERNS as DIABETES_HYPOGLYCEMIA_PATTERNS,
    COMPLICATIONS_PATTERNS as DIABETES_COMPLICATIONS_PATTERNS,
    detect_diabetes_subspecialty,
    normalize_diabetes_endpoint
)

from .dyslipidaemia import (
    DYSLIPIDAEMIA_ENDPOINTS,
    LIPID_LOWERING_PATTERNS as DLD_LIPID_LOWERING_PATTERNS,
    LDL_TARGET_PATTERNS as DLD_LDL_TARGET_PATTERNS,
    CV_EVENTS_PATTERNS as DLD_CV_EVENTS_PATTERNS,
    SAFETY_PATTERNS as DLD_SAFETY_PATTERNS,
    detect_dyslipidaemia_subspecialty,
    normalize_dyslipidaemia_endpoint
)


# ============================================================
# SPECIALTY REGISTRY
# ============================================================

SPECIALTY_REGISTRY = {
    'cardiology': {
        'subspecialties': ['heart_failure', 'acs', 'af', 'valve'],
        'detection_function': detect_cardiology_subspecialty,
        'normalizer': normalize_cardiology_endpoint,
        'endpoints': CARDIOLOGY_ENDPOINTS,
        'patterns': {
            'heart_failure': HEART_FAILURE_PATTERNS,
            'acs': ACS_PATTERNS,
            'af': AF_PATTERNS,
            'valve': VALVE_PATTERNS
        }
    },
    'oncology': {
        'subspecialties': ['breast', 'lung', 'gi', 'gu', 'heme'],
        'detection_function': detect_oncology_subspecialty,
        'normalizer': normalize_oncology_endpoint,
        'endpoints': ONCOLOGY_ENDPOINTS,
        'patterns': {
            'breast': BREAST_CANCER_PATTERNS,
            'lung': LUNG_CANCER_PATTERNS,
            'gi': GI_ONCOLOGY_PATTERNS
        }
    },
    'malaria': {
        'subspecialties': ['treatment', 'prevention', 'severe', 'transmission'],
        'detection_function': detect_malaria_subspecialty,
        'normalizer': normalize_malaria_endpoint,
        'endpoints': MALARIA_ENDPOINTS,
        'patterns': {
            'treatment': MALARIA_TREATMENT_PATTERNS,
            'prevention': MALARIA_PREVENTION_PATTERNS,
            'severe': MALARIA_SEVERE_PATTERNS,
            'transmission': MALARIA_TRANSMISSION_PATTERNS
        }
    },
    'hiv': {
        'subspecialties': ['treatment', 'prevention', 'pmtct', 'coinfection'],
        'detection_function': detect_hiv_subspecialty,
        'normalizer': normalize_hiv_endpoint,
        'endpoints': HIV_ENDPOINTS,
        'patterns': {
            'treatment': HIV_TREATMENT_PATTERNS,
            'prevention': HIV_PREVENTION_PATTERNS,
            'pmtct': HIV_PMTCT_PATTERNS,
            'coinfection': HIV_COINFECTION_PATTERNS
        }
    },
    'typhoid': {
        'subspecialties': ['treatment', 'vaccine', 'resistance', 'complications'],
        'detection_function': detect_typhoid_subspecialty,
        'normalizer': normalize_typhoid_endpoint,
        'endpoints': TYPHOID_ENDPOINTS,
        'patterns': {
            'treatment': TYPHOID_TREATMENT_PATTERNS,
            'vaccine': TYPHOID_VACCINE_PATTERNS,
            'resistance': TYPHOID_RESISTANCE_PATTERNS,
            'complications': TYPHOID_COMPLICATIONS_PATTERNS
        }
    },
    'schistosomiasis': {
        'subspecialties': ['treatment', 'prevention', 'morbidity', 'vaccine'],
        'detection_function': detect_schistosomiasis_subspecialty,
        'normalizer': normalize_schistosomiasis_endpoint,
        'endpoints': SCHISTOSOMIASIS_ENDPOINTS,
        'patterns': {
            'treatment': SCHISTO_TREATMENT_PATTERNS,
            'prevention': SCHISTO_PREVENTION_PATTERNS,
            'morbidity': SCHISTO_MORBIDITY_PATTERNS,
            'vaccine': SCHISTO_VACCINE_PATTERNS
        }
    },
    'sickle_cell': {
        'subspecialties': ['disease_modifying', 'acute_pain', 'prevention', 'transfusion'],
        'detection_function': detect_sickle_cell_subspecialty,
        'normalizer': normalize_sickle_cell_endpoint,
        'endpoints': SICKLE_CELL_ENDPOINTS,
        'patterns': {
            'disease_modifying': SCD_DISEASE_MODIFYING_PATTERNS,
            'acute_pain': SCD_ACUTE_PAIN_PATTERNS,
            'prevention': SCD_PREVENTION_PATTERNS,
            'transfusion': SCD_TRANSFUSION_PATTERNS
        }
    },
    'cholera': {
        'subspecialties': ['treatment', 'rehydration', 'vaccine', 'severe'],
        'detection_function': detect_cholera_subspecialty,
        'normalizer': normalize_cholera_endpoint,
        'endpoints': CHOLERA_ENDPOINTS,
        'patterns': {
            'treatment': CHOLERA_TREATMENT_PATTERNS,
            'rehydration': CHOLERA_REHYDRATION_PATTERNS,
            'vaccine': CHOLERA_VACCINE_PATTERNS,
            'severe': CHOLERA_SEVERE_PATTERNS
        }
    },
    'maternal_neonatal': {
        'subspecialties': ['maternal', 'hypertensive', 'neonatal', 'preterm'],
        'detection_function': detect_maternal_neonatal_subspecialty,
        'normalizer': normalize_maternal_neonatal_endpoint,
        'endpoints': MATERNAL_NEONATAL_ENDPOINTS,
        'patterns': {
            'maternal': MNH_MATERNAL_PATTERNS,
            'hypertensive': MNH_HYPERTENSIVE_PATTERNS,
            'neonatal': MNH_NEONATAL_PATTERNS,
            'preterm': MNH_PRETERM_PATTERNS
        }
    },
    'tuberculosis': {
        'subspecialties': ['treatment', 'drug_resistant', 'prevention', 'latent'],
        'detection_function': detect_tuberculosis_subspecialty,
        'normalizer': normalize_tuberculosis_endpoint,
        'endpoints': TUBERCULOSIS_ENDPOINTS,
        'patterns': {
            'treatment': TB_TREATMENT_PATTERNS,
            'drug_resistant': TB_DRUG_RESISTANT_PATTERNS,
            'prevention': TB_PREVENTION_PATTERNS,
            'latent': TB_LATENT_PATTERNS
        }
    },
    'hepatitis': {
        'subspecialties': ['treatment', 'prevention', 'pmtct', 'outcomes'],
        'detection_function': detect_hepatitis_subspecialty,
        'normalizer': normalize_hepatitis_endpoint,
        'endpoints': HEPATITIS_ENDPOINTS,
        'patterns': {
            'treatment': HEPATITIS_TREATMENT_PATTERNS,
            'prevention': HEPATITIS_PREVENTION_PATTERNS,
            'pmtct': HEPATITIS_PMTCT_PATTERNS,
            'outcomes': HEPATITIS_OUTCOMES_PATTERNS
        }
    },
    'meningitis': {
        'subspecialties': ['treatment', 'vaccine', 'mortality', 'sequelae'],
        'detection_function': detect_meningitis_subspecialty,
        'normalizer': normalize_meningitis_endpoint,
        'endpoints': MENINGITIS_ENDPOINTS,
        'patterns': {
            'treatment': MENINGITIS_TREATMENT_PATTERNS,
            'vaccine': MENINGITIS_VACCINE_PATTERNS,
            'mortality': MENINGITIS_MORTALITY_PATTERNS,
            'sequelae': MENINGITIS_SEQUELAE_PATTERNS
        }
    },
    'pneumonia': {
        'subspecialties': ['treatment', 'vaccine', 'mortality', 'severe'],
        'detection_function': detect_pneumonia_subspecialty,
        'normalizer': normalize_pneumonia_endpoint,
        'endpoints': PNEUMONIA_ENDPOINTS,
        'patterns': {
            'treatment': PNEUMONIA_TREATMENT_PATTERNS,
            'vaccine': PNEUMONIA_VACCINE_PATTERNS,
            'mortality': PNEUMONIA_MORTALITY_PATTERNS,
            'severe': PNEUMONIA_SEVERE_PATTERNS
        }
    },
    'diarrhoeal': {
        'subspecialties': ['rehydration', 'rotavirus', 'treatment', 'mortality_duration'],
        'detection_function': detect_diarrhoeal_subspecialty,
        'normalizer': normalize_diarrhoeal_endpoint,
        'endpoints': DIARRHOEAL_ENDPOINTS,
        'patterns': {
            'rehydration': DIARRHOEAL_REHYDRATION_PATTERNS,
            'rotavirus': DIARRHOEAL_ROTAVIRUS_PATTERNS,
            'treatment': DIARRHOEAL_TREATMENT_PATTERNS,
            'mortality_duration': DIARRHOEAL_MORTALITY_DURATION_PATTERNS
        }
    },
    'malnutrition': {
        'subspecialties': ['therapeutic_feeding', 'micronutrient', 'mortality', 'recovery_growth'],
        'detection_function': detect_malnutrition_subspecialty,
        'normalizer': normalize_malnutrition_endpoint,
        'endpoints': MALNUTRITION_ENDPOINTS,
        'patterns': {
            'therapeutic_feeding': MALN_THERAPEUTIC_FEEDING_PATTERNS,
            'micronutrient': MALN_MICRONUTRIENT_PATTERNS,
            'mortality': MALN_MORTALITY_PATTERNS,
            'recovery_growth': MALN_RECOVERY_GROWTH_PATTERNS
        }
    },
    'helminths': {
        'subspecialties': ['treatment', 'mass_deworming', 'nutrition', 'reinfection'],
        'detection_function': detect_helminths_subspecialty,
        'normalizer': normalize_helminths_endpoint,
        'endpoints': HELMINTHS_ENDPOINTS,
        'patterns': {
            'treatment': HELMINTHS_TREATMENT_PATTERNS,
            'mass_deworming': HELMINTHS_MASS_DEWORMING_PATTERNS,
            'nutrition': HELMINTHS_NUTRITION_PATTERNS,
            'reinfection': HELMINTHS_REINFECTION_PATTERNS
        }
    },
    'hypertension': {
        'subspecialties': ['bp_lowering', 'cv_events', 'bp_reduction', 'adherence'],
        'detection_function': detect_hypertension_subspecialty,
        'normalizer': normalize_hypertension_endpoint,
        'endpoints': HYPERTENSION_ENDPOINTS,
        'patterns': {
            'bp_lowering': HTN_BP_LOWERING_PATTERNS,
            'cv_events': HTN_CV_EVENTS_PATTERNS,
            'bp_reduction': HTN_BP_REDUCTION_PATTERNS,
            'adherence': HTN_ADHERENCE_PATTERNS
        }
    },
    'cervical_cancer': {
        'subspecialties': ['vaccine', 'screening', 'treatment', 'mortality'],
        'detection_function': detect_cervical_cancer_subspecialty,
        'normalizer': normalize_cervical_cancer_endpoint,
        'endpoints': CERVICAL_CANCER_ENDPOINTS,
        'patterns': {
            'vaccine': CC_VACCINE_PATTERNS,
            'screening': CC_SCREENING_PATTERNS,
            'treatment': CC_TREATMENT_PATTERNS,
            'mortality': CC_MORTALITY_PATTERNS
        }
    },
    'infectious_disease': {
        'subspecialties': ['covid', 'hepatitis', 'bacterial'],
        'endpoints': {
            'MORTALITY': {'aliases': ['mortality', 'death', 'all-cause mortality']},
            'HOSPITALIZATION': {'aliases': ['hospitalization', 'hospital admission']},
            'RECOVERY': {'aliases': ['recovery', 'clinical recovery', 'time to recovery']},
            'VIROLOGIC_RESPONSE': {'aliases': ['virologic response', 'viral suppression', 'undetectable']}
        }
    },
    'diabetes': {
        'subspecialties': ['glycemic', 'cardiorenal', 'hypoglycemia', 'complications'],
        'detection_function': detect_diabetes_subspecialty,
        'normalizer': normalize_diabetes_endpoint,
        'endpoints': DIABETES_ENDPOINTS,
        'patterns': {
            'glycemic': DIABETES_GLYCEMIC_PATTERNS,
            'cardiorenal': DIABETES_CARDIORENAL_PATTERNS,
            'hypoglycemia': DIABETES_HYPOGLYCEMIA_PATTERNS,
            'complications': DIABETES_COMPLICATIONS_PATTERNS
        }
    },
    'dyslipidaemia': {
        'subspecialties': ['lipid_lowering', 'ldl_target', 'cv_events', 'safety'],
        'detection_function': detect_dyslipidaemia_subspecialty,
        'normalizer': normalize_dyslipidaemia_endpoint,
        'endpoints': DYSLIPIDAEMIA_ENDPOINTS,
        'patterns': {
            'lipid_lowering': DLD_LIPID_LOWERING_PATTERNS,
            'ldl_target': DLD_LDL_TARGET_PATTERNS,
            'cv_events': DLD_CV_EVENTS_PATTERNS,
            'safety': DLD_SAFETY_PATTERNS
        }
    },
    'neurology': {
        'subspecialties': ['alzheimers', 'ms', 'parkinsons', 'stroke'],
        'endpoints': {
            'CDR_SB': {'aliases': ['cdr-sb', 'clinical dementia rating', 'cdr sum of boxes']},
            'DISABILITY_PROGRESSION': {'aliases': ['disability progression', 'edss progression']},
            'ANNUALIZED_RELAPSE_RATE': {'aliases': ['annualized relapse rate', 'arr', 'relapse rate']},
            'BRAIN_ATROPHY': {'aliases': ['brain atrophy', 'brain volume loss']}
        }
    },
    'autoimmune': {
        'subspecialties': ['ra', 'sle', 'psoriasis', 'ibd'],
        'endpoints': {
            'ACR20': {'aliases': ['acr20', 'acr 20', 'acr20 response']},
            'ACR50': {'aliases': ['acr50', 'acr 50']},
            'ACR70': {'aliases': ['acr70', 'acr 70']},
            'PASI90': {'aliases': ['pasi90', 'pasi 90', '90% improvement in pasi']},
            'SRI': {'aliases': ['sri', 'sle responder index']}
        }
    },
    'respiratory': {
        'subspecialties': ['copd', 'asthma', 'ipf'],
        'endpoints': {
            'EXACERBATION': {'aliases': ['exacerbation', 'acute exacerbation', 'copd exacerbation']},
            'FEV1': {'aliases': ['fev1', 'forced expiratory volume']},
            'FVC': {'aliases': ['fvc', 'forced vital capacity']},
            'FVC_DECLINE': {'aliases': ['fvc decline', 'annual fvc decline', 'rate of fvc decline']}
        }
    }
}


# ============================================================
# REGISTRY FUNCTIONS
# ============================================================

# Generic catch-all buckets that lack a detection_function / normalizer /
# arm-level extractor. They must never outrank a specific specialty (see
# detect_specialty). `infectious_disease` is the one with bare-word keywords;
# the others are kept here too so a future generic keyword can't silently steal
# routing from a specific specialty.
_FALLBACK_SPECIALTIES = {'infectious_disease'}


def detect_specialty(text: str) -> Tuple[str, str, float]:
    """
    Detect therapeutic specialty and subspecialty from text.

    Returns:
        Tuple of (specialty, subspecialty, confidence)
    """
    text_lower = text.lower()

    specialty_scores = {}

    # Keywords for each specialty
    specialty_keywords = {
        'cardiology': [
            r'heart\s+failure', r'myocardial\s+infarction', r'atrial\s+fibrillation',
            r'coronary', r'cardiovascular', r'cardiac', r'lvef', r'ejection\s+fraction',
            r'arrhythmia', r'hypertension', r'valve', r'tavr', r'pci'
        ],
        'oncology': [
            r'cancer', r'tumor', r'carcinoma', r'adenocarcinoma', r'melanoma',
            r'chemotherapy', r'immunotherapy', r'progression[- ]?free', r'pfs',
            r'response\s+rate', r'her2', r'egfr', r'pd[- ]?l1', r'checkpoint'
        ],
        'malaria': [
            r'malaria', r'plasmodium', r'falciparum', r'vivax',
            r'antimalarial', r'artemisinin', r'\bacpr\b', r'parasit(?:ae|e)mia',
            r'parasite\s+clearance', r'recrudescen', r'gametocyt',
            r'artemether[- ]?lumefantrine', r'dihydroartemisinin',
            r'sulfadoxine[- ]?pyrimethamine', r'rts,?\s?s', r'\bsmc\b',
            r'chemoprevention'
        ],
        'hiv': [
            r'\bhiv\b', r'\baids\b', r'antiretroviral', r'\bart\b', r'\bhaart\b',
            r'viral\s+(?:load\s+)?suppression', r'virologic', r'\bcd4\b',
            r'pre[- ]?exposure\s+prophylaxis', r'\bprep\b', r'dolutegravir',
            r'tenofovir|emtricitabine', r'mother[- ]to[- ]child\s+transmission',
            r'efavirenz', r'undetectable'
        ],
        'typhoid': [
            r'typhoid', r'enteric\s+fever', r'paratyphoid', r'paratyphi',
            r'salmonella\s+typhi', r'\bs\.?\s*typhi\b', r'typhoid\s+conjugate\s+vaccine',
            r'\btcv\b', r'\bty21a\b', r'vi\s+polysaccharide', r'anti[- ]vi',
            r'fever\s+clearance\s+time', r'widal'
        ],
        'schistosomiasis': [
            r'schistosom', r'bilharzia', r'praziquantel', r'\bpzq\b',
            r's\.?\s*(?:mansoni|haematobium|hematobium|japonicum|mekongi|intercalatum)',
            r'kato[- ]?katz', r'egg\s+reduction\s+rate', r'eggs\s+per\s+gram',
            r'cercaria(?:e)?', r'miracidia', r'oxamniquine', r'sh28gst|bilhvax',
            r'periportal\s+fibrosis'
        ],
        'sickle_cell': [
            r'sickle\s+cell', r'\bscd\b', r'sickle\s+cell\s+(?:disease|ana?emia)',
            r'\bhbss\b', r'\bhbsc\b', r'ha?emoglobin\s+s\b', r'\bsickle\b',
            r'vaso[- ]?occlusive', r'hydroxyurea|hydroxycarbamide', r'voxelotor',
            r'crizanlizumab', r'acute\s+chest\s+syndrome', r'fetal\s+ha?emoglobin|\bhbf\b'
        ],
        'cholera': [
            r'cholera', r'vibrio\s+cholerae', r'v\.?\s*cholerae',
            r'oral\s+cholera\s+vaccine', r'\bocv\b', r'vibriocidal',
            r'dukoral|shanchol|euvichol|hillchol', r'el\s+tor',
            r'cholera\s+toxin', r'ogawa|inaba', r'rice[- ]based\s+ors',
            r'watery\s+diarrh(?:oea|ea)'
        ],
        'maternal_neonatal': [
            r'maternal\s+(?:mortalit|death|sepsis|morbidit)',
            r'postpartum\s+ha?emorrhage', r'\bpph\b', r'pre[- ]?eclampsia',
            r'eclampsia', r'eclamptic', r'magnesium\s+sul(?:f|ph)ate',
            r'gestational\s+(?:age|hypertension|diabetes)',
            r'neonatal\s+(?:mortalit|death|sepsis|encephalopathy)',
            r'stillbirth', r'perinatal\s+(?:mortalit|death)',
            r'preterm\s+(?:birth|delivery|labou?r)', r'premature\s+(?:birth|delivery)',
            r'low\s+birth\s?weight', r'\blbw\b', r'birth\s?weight',
            r'birth\s+asphyxia', r'\bapgar\b', r'caesarean|cesarean',
            r'oxytocin', r'misoprostol', r'carbetocin', r'tranexamic\s+acid',
            r'antenatal\s+cortico?steroids?', r'kangaroo\s+mother\s+care',
            r'\bneonate', r'\bnewborn\b', r'obstetric', r'intrapartum'
        ],
        'tuberculosis': [
            r'tuberculosis', r'\btb\b', r'mycobacterium\s+tuberculosis',
            r'pulmonary\s+tuberculosis', r'\bmdr[- ]?tb\b|\brr[- ]?tb\b|\bxdr[- ]?tb\b',
            r'sputum\s+culture', r'culture\s+conversion', r'smear[- ]positive',
            r'rifampic?in', r'isoniazid', r'rifapentine', r'pyrazinamide',
            r'bedaquiline', r'pretomanid|delamanid', r'\bhrze\b|\bbpalm?\b',
            r'latent\s+(?:tb|tuberculosis)|\bltbi\b', r'anti[- ]tuberculosis',
            r'tb\s+preventive\s+(?:therapy|treatment)|\btpt\b', r'\bbcg\b'
        ],
        'hepatitis': [
            r'hepatitis\s+[bc]\b', r'\bhbv\b', r'\bhcv\b', r'chronic\s+hepatitis',
            r'\bhbsag\b', r'\bhbeag\b', r'hbv\s+dna', r'sustained\s+virologic\w*\s+response',
            r'\bsvr\b', r'sofosbuvir|ledipasvir|velpatasvir|glecaprevir|daclatasvir',
            r'entecavir|tenofovir\s+(?:disoproxil|alafenamide)|telbivudine',
            r'hepatocellular\s+carcinoma', r'cirrhosis', r'direct[- ]acting\s+antiviral',
            r'anti[- ]?hbs', r'liver\s+stiffness'
        ],
        'meningitis': [
            r'meningitis', r'meningococc', r'neisseria\s+meningitidis',
            r'pneumococcal\s+meningitis', r'h[ae]mophilus\s+influenzae',
            r'\bhib\b', r'menafrivac', r'\bmena[- ]?tt\b', r'\bmenacwy\b',
            r'4cmenb', r'cerebrospinal\s+fluid', r'\bcsf\b', r'lumbar\s+puncture',
            r'serum\s+bactericidal|\bsba\b', r'meningitis\s+belt'
        ],
        'pneumonia': [
            r'pneumonia', r'pneumococc', r'streptococcus\s+pneumoniae',
            r's\.?\s*pneumoniae', r'community[- ]acquired\s+pneumonia|\bcap\b',
            r'pneumococcal\s+conjugate\s+vaccine|\bpcv\s*\d*\b', r'\bppsv\s*\d*\b',
            r'\bhib\b|haemophilus\s+influenzae', r'invasive\s+pneumococcal\s+disease|\bipd\b',
            r'lower\s+respiratory\s+(?:tract\s+)?infection|\blrti\b',
            r'acute\s+respiratory\s+infection', r'radiolog(?:ically|ic)[- ]confirmed\s+pneumonia',
            r'chest\s+indrawing', r'fast\s+breathing', r'bronchopneumonia',
            r'nasopharyngeal\s+(?:carriage|colon[is]ation)', r'empyema'
        ],
        'diarrhoeal': [
            r'diarrho?eal?', r'rotavirus', r'gastroenteritis', r'oral\s+rehydration',
            r'\bors\b', r'zinc', r'rotarix|rotateq|rotavac|rotasiil',
            r'dysentery', r'shigell', r'dehydration', r'stool\s+(?:output|frequency)',
            r'acute\s+(?:watery\s+)?diarrho?ea', r'racecadotril',
            r'reduced[- ]osmolarity', r'persistent\s+diarrho?ea'
        ],
        'malnutrition': [
            r'malnutrition', r'undernutrition', r'severe\s+acute\s+malnutrition',
            r'moderate\s+acute\s+malnutrition', r'kwashiorkor', r'marasmus',
            r'ready[- ]to[- ]use\s+therapeutic\s+food', r'\brutf\b', r'\brusf\b',
            r'mid[- ]upper\s+arm\s+circumference', r'\bmuac\b', r'weight[- ]for[- ]height',
            r'\bwhz\b', r'\bstunting\b', r'\bwasting\b', r'\bcmam\b',
            r'therapeutic\s+feeding', r'nutritional\s+rehabilitation',
            r'supplementary\s+feeding', r'\bf-?75\b', r'\bf-?100\b'
        ],
        'helminths': [
            r'soil[- ]transmitted\s+helminth', r'\bsth\b', r'geohelminth',
            r'helminth', r'\bdeworming\b|de[- ]worming', r'anthelmin(?:t|th)ic',
            r'ascaris|ascariasis', r'trichuris|trichuriasis|whipworm',
            r'hookworm|necator|ancylostoma', r'strongyloides|strongyloidiasis',
            r'roundworm|intestinal\s+worm', r'albendazole', r'mebendazole',
            r'pyrantel', r'levamisole', r'tribendimidine', r'oxantel',
            r'egg\s+reduction\s+rate', r'eggs\s+per\s+gram', r'kato[- ]?katz'
        ],
        'hypertension': [
            r'hypertension', r'hypertensive', r'blood[- ]pressure', r'antihypertensive',
            r'systolic|diastolic', r'mm\s?hg', r'\bsbp\b|\bdbp\b',
            r'ambulatory\s+blood[- ]pressure',
            r'blood[- ]pressure[- ](?:control|lowering|reduction|target|goal)',
            r'ace\s+inhibitor|angiotensin[- ]converting[- ]enzyme\s+inhibitor',
            r'angiotensin[- ]receptor\s+blocker|\barb\b',
            r'calcium[- ]channel\s+blocker|\bccb\b', r'thiazide',
            r'amlodipine|hydrochlorothiazide|chlort(?:h)?alidone|indapamide|atenolol',
        ],
        'cervical_cancer': [
            r'cervical\s+cancer', r'cervical\s+carcinoma', r'cervical\s+intraepithelial',
            r'\bcin\s?[123]\b', r'cin\s?2\+|cin\s?3\+', r'\bhpv\b', r'human\s+papillomavirus',
            r'cervical\s+(?:dysplasia|lesion|precancer)', r'\bhsil\b|\blsil\b',
            r'visual\s+inspection\s+with\s+acetic\s+acid|\bvia\b', r'\bvili\b',
            r'cervical\s+screening', r'pap\s+smear|cervical\s+cytology',
            r'gardasil|cervarix|cecolin|walrinvax', r'colposcopy',
            r'\bleep\b|\blletz\b|cryotherapy|thermal\s+ablation|coni[sz]ation',
            r'high[- ]grade\s+squamous\s+intraepithelial', r'persistent\s+hpv',
            r'quadrivalent|bivalent|nonavalent'
        ],
        'infectious_disease': [
            r'covid', r'sars[- ]?cov',
            r'viral', r'bacterial', r'antiviral', r'antibiotic', r'infection'
        ],
        'diabetes': [
            r'diabetes', r'diabetic', r'type\s+2\s+diabetes|\bt2dm\b',
            r'hba1c', r'glycated\s+ha?emoglobin', r'fasting\s+plasma\s+glucose',
            r'glucose', r'insulin', r'glyca?emic', r'hypoglyca?emia',
            r'sglt[- ]?2', r'\w*gliflozin', r'glp[- ]?1', r'\w*glutide', r'tirzepatide',
            r'\w*gliptin', r'dpp[- ]?4', r'metformin', r'sulfonylurea|sulphonylurea',
            r'pioglitazone|rosiglitazone', r'obesity', r'weight\s+loss'
        ],
        'dyslipidaemia': [
            r'dyslipid(?:emia|aemia)', r'hyperlipid(?:emia|aemia)',
            r'hypercholesterol(?:emia|aemia)', r'\bldl[- ]?c?\b',
            r'ldl\s+cholesterol', r'low[- ]density\s+lipoprotein',
            r'hdl\s+cholesterol|high[- ]density\s+lipoprotein', r'non[- ]hdl',
            r'triglycerid', r'total\s+cholesterol', r'lipid[- ]lowering',
            r'cholesterol[- ]lowering', r'lipid\s+profile',
            r'apolipoprotein\s+b|\bapob\b', r'lipoprotein\s*\(a\)|\blp\(a\)',
            r'\bstatin\b', r'atorvastatin|rosuvastatin|simvastatin|pravastatin',
            r'lovastatin|pitavastatin|fluvastatin', r'ezetimibe',
            r'pcsk9|evolocumab|alirocumab|inclisiran', r'bempedoic\s+acid',
            r'fenofibrate|gemfibrozil|\bfibrate\b',
            r'icosapent\s+ethyl', r'colesevelam|cholestyramine',
        ],
        'neurology': [
            r'alzheimer', r'dementia', r'multiple\s+sclerosis', r'\bms\b',
            r'parkinson', r'stroke', r'neurological', r'cognitive', r'relapse'
        ],
        'autoimmune': [
            r'rheumatoid\s+arthritis', r'lupus', r'psoriasis', r'psoriatic',
            r'inflammatory\s+bowel', r'crohn', r'colitis', r'acr\d{2}', r'pasi'
        ],
        'respiratory': [
            r'copd', r'asthma', r'pulmonary\s+fibrosis', r'ipf',
            r'exacerbation', r'fev1', r'fvc', r'broncho', r'inhale'
        ]
    }

    for specialty, keywords in specialty_keywords.items():
        score = sum(1 for kw in keywords if re.search(kw, text_lower))
        specialty_scores[specialty] = score

    best_specialty = max(specialty_scores, key=specialty_scores.get)
    best_score = specialty_scores[best_specialty]

    if best_score == 0:
        return ('unknown', None, 0.0)

    # `infectious_disease` is a deliberate catch-all whose keywords (viral,
    # bacterial, infection, antibiotic, antiviral) are intentionally broad and
    # co-occur with EVERY specific infectious-disease specialty (hepatitis,
    # typhoid, TB, cholera, pneumonia, meningitis, ...). Left alone, those bare
    # words let it outscore a specific specialty on a borderline abstract and
    # route it to a bucket with no detection/normalizer/arm-level extractor --
    # i.e. lose all specialty-specific extraction. So treat it as a fallback:
    # it only wins when NO specific specialty matched at all.
    if best_specialty in _FALLBACK_SPECIALTIES:
        specific = {s: sc for s, sc in specialty_scores.items()
                    if s not in _FALLBACK_SPECIALTIES and sc > 0}
        if specific:
            best_specialty = max(specific, key=specific.get)
            best_score = specialty_scores[best_specialty]

    # Detect subspecialty
    subspecialty = None
    confidence = min(best_score / 5, 1.0)

    if best_specialty == 'cardiology':
        subspecialty, conf = detect_cardiology_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'oncology':
        subspecialty, _, conf = detect_oncology_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'malaria':
        subspecialty, conf = detect_malaria_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'hiv':
        subspecialty, conf = detect_hiv_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'typhoid':
        subspecialty, conf = detect_typhoid_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'schistosomiasis':
        subspecialty, conf = detect_schistosomiasis_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'sickle_cell':
        subspecialty, conf = detect_sickle_cell_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'cholera':
        subspecialty, conf = detect_cholera_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'maternal_neonatal':
        subspecialty, conf = detect_maternal_neonatal_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'tuberculosis':
        subspecialty, conf = detect_tuberculosis_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'hepatitis':
        subspecialty, conf = detect_hepatitis_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'meningitis':
        subspecialty, conf = detect_meningitis_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'pneumonia':
        subspecialty, conf = detect_pneumonia_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'diarrhoeal':
        subspecialty, conf = detect_diarrhoeal_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'malnutrition':
        subspecialty, conf = detect_malnutrition_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'helminths':
        subspecialty, conf = detect_helminths_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'hypertension':
        subspecialty, conf = detect_hypertension_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'cervical_cancer':
        subspecialty, conf = detect_cervical_cancer_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'diabetes':
        subspecialty, conf = detect_diabetes_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'dyslipidaemia':
        subspecialty, conf = detect_dyslipidaemia_subspecialty(text)
        confidence = max(confidence, conf)

    return (best_specialty, subspecialty, confidence)


def get_specialty_patterns(specialty: str, subspecialty: str = None) -> Dict:
    """Get patterns for a specific specialty/subspecialty."""
    spec_info = SPECIALTY_REGISTRY.get(specialty, {})

    if subspecialty and 'patterns' in spec_info:
        return spec_info['patterns'].get(subspecialty, {})

    return spec_info.get('patterns', {})


def get_endpoint_normalizer(specialty: str) -> Optional[Callable]:
    """Get the endpoint normalizer function for a specialty."""
    spec_info = SPECIALTY_REGISTRY.get(specialty, {})
    return spec_info.get('normalizer')


def normalize_endpoint_by_specialty(
    endpoint: str,
    specialty: str = None,
    subspecialty: str = None
) -> str:
    """
    Normalize endpoint using specialty-specific rules.

    Falls back to generic normalization if no specialty match.
    """
    if specialty:
        normalizer = get_endpoint_normalizer(specialty)
        if normalizer:
            return normalizer(endpoint, subspecialty)

    # Generic normalization
    endpoint_lower = endpoint.lower()

    generic_mappings = {
        'PRIMARY_OUTCOME': ['primary', 'primary outcome', 'primary endpoint'],
        'SECONDARY_OUTCOME': ['secondary', 'secondary outcome'],
        'MORTALITY': ['death', 'mortality', 'survival'],
        'COMPOSITE': ['composite', 'combined']
    }

    for canonical, aliases in generic_mappings.items():
        for alias in aliases:
            if alias in endpoint_lower:
                return canonical

    return endpoint.upper()


def get_all_endpoints(specialty: str = None) -> Dict:
    """Get all endpoints, optionally filtered by specialty."""
    if specialty:
        spec_info = SPECIALTY_REGISTRY.get(specialty, {})
        return spec_info.get('endpoints', {})

    # Return all endpoints
    all_endpoints = {}
    for spec_name, spec_info in SPECIALTY_REGISTRY.items():
        endpoints = spec_info.get('endpoints', {})
        all_endpoints.update(endpoints)

    return all_endpoints
