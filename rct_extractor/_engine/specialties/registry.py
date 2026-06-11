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

from .respiratory import (
    RESPIRATORY_ENDPOINTS,
    COPD_PATTERNS as RESP_COPD_PATTERNS,
    ASTHMA_PATTERNS as RESP_ASTHMA_PATTERNS,
    ILD_PATTERNS as RESP_ILD_PATTERNS,
    GENERAL_PATTERNS as RESP_GENERAL_PATTERNS,
    detect_respiratory_subspecialty,
    normalize_respiratory_endpoint
)

from .stroke import (
    STROKE_ENDPOINTS,
    ACUTE_ISCHEMIC_PATTERNS as STROKE_ACUTE_ISCHEMIC_PATTERNS,
    HEMORRHAGIC_PATTERNS as STROKE_HEMORRHAGIC_PATTERNS,
    SECONDARY_PREVENTION_PATTERNS as STROKE_SECONDARY_PREVENTION_PATTERNS,
    RECOVERY_PATTERNS as STROKE_RECOVERY_PATTERNS,
    detect_stroke_subspecialty,
    normalize_stroke_endpoint
)

from .nephrology import (
    NEPHROLOGY_ENDPOINTS,
    CKD_PATTERNS as NEPHRO_CKD_PATTERNS,
    DIALYSIS_PATTERNS as NEPHRO_DIALYSIS_PATTERNS,
    AKI_PATTERNS as NEPHRO_AKI_PATTERNS,
    GLOMERULAR_PATTERNS as NEPHRO_GLOMERULAR_PATTERNS,
    detect_nephrology_subspecialty,
    normalize_nephrology_endpoint
)

from .psychiatry import (
    PSYCHIATRY_ENDPOINTS,
    DEPRESSION_PATTERNS as PSYCH_DEPRESSION_PATTERNS,
    ANXIETY_PATTERNS as PSYCH_ANXIETY_PATTERNS,
    BIPOLAR_PATTERNS as PSYCH_BIPOLAR_PATTERNS,
    PSYCHOSIS_PATTERNS as PSYCH_PSYCHOSIS_PATTERNS,
    detect_psychiatry_subspecialty,
    normalize_psychiatry_endpoint
)

from .rheumatology import (
    RHEUMATOLOGY_ENDPOINTS,
    RA_PATTERNS as RHEUM_RA_PATTERNS,
    PSA_PATTERNS as RHEUM_PSA_PATTERNS,
    AXSPA_PATTERNS as RHEUM_AXSPA_PATTERNS,
    GOUT_PATTERNS as RHEUM_GOUT_PATTERNS,
    SLE_PATTERNS as RHEUM_SLE_PATTERNS,
    detect_rheumatology_subspecialty,
    normalize_rheumatology_endpoint
)

from .gastroenterology import (
    GASTROENTEROLOGY_ENDPOINTS,
    IBD_PATTERNS as GI_IBD_PATTERNS,
    HPYLORI_PATTERNS as GI_HPYLORI_PATTERNS,
    GERD_PATTERNS as GI_GERD_PATTERNS,
    MASH_PATTERNS as GI_MASH_PATTERNS,
    detect_gastroenterology_subspecialty,
    normalize_gastroenterology_endpoint
)

from .dermatology import (
    DERMATOLOGY_ENDPOINTS,
    PSORIASIS_PATTERNS as DERM_PSORIASIS_PATTERNS,
    ATOPIC_DERMATITIS_PATTERNS as DERM_ATOPIC_DERMATITIS_PATTERNS,
    ACNE_PATTERNS as DERM_ACNE_PATTERNS,
    HIDRADENITIS_PATTERNS as DERM_HIDRADENITIS_PATTERNS,
    detect_dermatology_subspecialty,
    normalize_dermatology_endpoint
)

from .ophthalmology import (
    OPHTHALMOLOGY_ENDPOINTS,
    AMD_PATTERNS as OPHTH_AMD_PATTERNS,
    DME_PATTERNS as OPHTH_DME_PATTERNS,
    GLAUCOMA_PATTERNS as OPHTH_GLAUCOMA_PATTERNS,
    DRY_EYE_PATTERNS as OPHTH_DRY_EYE_PATTERNS,
    detect_ophthalmology_subspecialty,
    normalize_ophthalmology_endpoint
)

from .oesophageal_cancer import (
    OESOPHAGEAL_CANCER_ENDPOINTS,
    DEFINITIVE_PATTERNS as OE_DEFINITIVE_PATTERNS,
    ADJUVANT_PATTERNS as OE_ADJUVANT_PATTERNS,
    ADVANCED_PATTERNS as OE_ADVANCED_PATTERNS,
    MORTALITY_PATTERNS as OE_MORTALITY_PATTERNS,
    detect_oesophageal_cancer_subspecialty,
    normalize_oesophageal_cancer_endpoint
from .prostate_cancer import (
    PROSTATE_CANCER_ENDPOINTS,
    SYSTEMIC_PATTERNS as PC_SYSTEMIC_PATTERNS,
    LOCALIZED_PATTERNS as PC_LOCALIZED_PATTERNS,
    HORMONAL_PATTERNS as PC_HORMONAL_PATTERNS,
    MORTALITY_PATTERNS as PC_MORTALITY_PATTERNS,
    detect_prostate_cancer_subspecialty,
    normalize_prostate_cancer_endpoint
from .ovarian_cancer import (
    OVARIAN_CANCER_ENDPOINTS,
    SYSTEMIC_PATTERNS as OC_SYSTEMIC_PATTERNS,
    MAINTENANCE_PATTERNS as OC_MAINTENANCE_PATTERNS,
    SURGICAL_PATTERNS as OC_SURGICAL_PATTERNS,
    MORTALITY_PATTERNS as OC_MORTALITY_PATTERNS,
    detect_ovarian_cancer_subspecialty,
    normalize_ovarian_cancer_endpoint
from .pancreatic_cancer import (
    PANCREATIC_CANCER_ENDPOINTS,
    SYSTEMIC_PATTERNS as PA_SYSTEMIC_PATTERNS,
    ADJUVANT_PATTERNS as PA_ADJUVANT_PATTERNS,
    LOCALLY_ADVANCED_PATTERNS as PA_LOCALLY_ADVANCED_PATTERNS,
    MORTALITY_PATTERNS as PA_MORTALITY_PATTERNS,
    detect_pancreatic_cancer_subspecialty,
    normalize_pancreatic_cancer_endpoint
from .gastric_cancer import (
    GASTRIC_CANCER_ENDPOINTS,
    SYSTEMIC_PATTERNS as GC_SYSTEMIC_PATTERNS,
    PERIOPERATIVE_PATTERNS as GC_PERIOPERATIVE_PATTERNS,
    SURGICAL_PATTERNS as GC_SURGICAL_PATTERNS,
    MORTALITY_PATTERNS as GC_MORTALITY_PATTERNS,
    detect_gastric_cancer_subspecialty,
    normalize_gastric_cancer_endpoint
from .hepatocellular_carcinoma import (
    HEPATOCELLULAR_CARCINOMA_ENDPOINTS,
    SYSTEMIC_PATTERNS as HCC_SYSTEMIC_PATTERNS,
    LOCOREGIONAL_PATTERNS as HCC_LOCOREGIONAL_PATTERNS,
    CURATIVE_PATTERNS as HCC_CURATIVE_PATTERNS,
    MORTALITY_PATTERNS as HCC_MORTALITY_PATTERNS,
    detect_hepatocellular_carcinoma_subspecialty,
    normalize_hepatocellular_carcinoma_endpoint
from .melanoma import (
    MELANOMA_ENDPOINTS,
    SYSTEMIC_PATTERNS as MEL_SYSTEMIC_PATTERNS,
    ADJUVANT_PATTERNS as MEL_ADJUVANT_PATTERNS,
    NEOADJUVANT_PATTERNS as MEL_NEOADJUVANT_PATTERNS,
    MORTALITY_PATTERNS as MEL_MORTALITY_PATTERNS,
    detect_melanoma_subspecialty,
    normalize_melanoma_endpoint
from .leukaemia import (
    LEUKAEMIA_ENDPOINTS,
    AML_PATTERNS as LK_AML_PATTERNS,
    ALL_PATTERNS as LK_ALL_PATTERNS,
    CLL_PATTERNS as LK_CLL_PATTERNS,
    CML_PATTERNS as LK_CML_PATTERNS,
    detect_leukaemia_subspecialty,
    normalize_leukaemia_endpoint
from .lymphoma import (
    LYMPHOMA_ENDPOINTS,
    HODGKIN_PATTERNS as LY_HODGKIN_PATTERNS,
    AGGRESSIVE_PATTERNS as LY_AGGRESSIVE_PATTERNS,
    INDOLENT_PATTERNS as LY_INDOLENT_PATTERNS,
    MORTALITY_PATTERNS as LY_MORTALITY_PATTERNS,
    detect_lymphoma_subspecialty,
    normalize_lymphoma_endpoint
from .head_neck_cancer import (
    HEAD_NECK_CANCER_ENDPOINTS,
    DEFINITIVE_PATTERNS as HN_DEFINITIVE_PATTERNS,
    RECURRENT_METASTATIC_PATTERNS as HN_RECURRENT_METASTATIC_PATTERNS,
    NASOPHARYNGEAL_PATTERNS as HN_NASOPHARYNGEAL_PATTERNS,
    MORTALITY_PATTERNS as HN_MORTALITY_PATTERNS,
    detect_head_neck_cancer_subspecialty,
    normalize_head_neck_cancer_endpoint
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
    'oesophageal_cancer': {
        'subspecialties': ['definitive', 'adjuvant', 'advanced', 'mortality'],
        'detection_function': detect_oesophageal_cancer_subspecialty,
        'normalizer': normalize_oesophageal_cancer_endpoint,
        'endpoints': OESOPHAGEAL_CANCER_ENDPOINTS,
        'patterns': {
            'definitive': OE_DEFINITIVE_PATTERNS,
            'adjuvant': OE_ADJUVANT_PATTERNS,
            'advanced': OE_ADVANCED_PATTERNS,
            'mortality': OE_MORTALITY_PATTERNS
    'prostate_cancer': {
        'subspecialties': ['systemic', 'localized', 'hormonal', 'mortality'],
        'detection_function': detect_prostate_cancer_subspecialty,
        'normalizer': normalize_prostate_cancer_endpoint,
        'endpoints': PROSTATE_CANCER_ENDPOINTS,
        'patterns': {
            'systemic': PC_SYSTEMIC_PATTERNS,
            'localized': PC_LOCALIZED_PATTERNS,
            'hormonal': PC_HORMONAL_PATTERNS,
            'mortality': PC_MORTALITY_PATTERNS
    'ovarian_cancer': {
        'subspecialties': ['systemic', 'maintenance', 'surgical', 'mortality'],
        'detection_function': detect_ovarian_cancer_subspecialty,
        'normalizer': normalize_ovarian_cancer_endpoint,
        'endpoints': OVARIAN_CANCER_ENDPOINTS,
        'patterns': {
            'systemic': OC_SYSTEMIC_PATTERNS,
            'maintenance': OC_MAINTENANCE_PATTERNS,
            'surgical': OC_SURGICAL_PATTERNS,
            'mortality': OC_MORTALITY_PATTERNS
    'pancreatic_cancer': {
        'subspecialties': ['systemic', 'adjuvant', 'locally_advanced', 'mortality'],
        'detection_function': detect_pancreatic_cancer_subspecialty,
        'normalizer': normalize_pancreatic_cancer_endpoint,
        'endpoints': PANCREATIC_CANCER_ENDPOINTS,
        'patterns': {
            'systemic': PA_SYSTEMIC_PATTERNS,
            'adjuvant': PA_ADJUVANT_PATTERNS,
            'locally_advanced': PA_LOCALLY_ADVANCED_PATTERNS,
            'mortality': PA_MORTALITY_PATTERNS
    'gastric_cancer': {
        'subspecialties': ['systemic', 'perioperative', 'surgical', 'mortality'],
        'detection_function': detect_gastric_cancer_subspecialty,
        'normalizer': normalize_gastric_cancer_endpoint,
        'endpoints': GASTRIC_CANCER_ENDPOINTS,
        'patterns': {
            'systemic': GC_SYSTEMIC_PATTERNS,
            'perioperative': GC_PERIOPERATIVE_PATTERNS,
            'surgical': GC_SURGICAL_PATTERNS,
            'mortality': GC_MORTALITY_PATTERNS
    'hepatocellular_carcinoma': {
        'subspecialties': ['systemic', 'locoregional', 'curative', 'mortality'],
        'detection_function': detect_hepatocellular_carcinoma_subspecialty,
        'normalizer': normalize_hepatocellular_carcinoma_endpoint,
        'endpoints': HEPATOCELLULAR_CARCINOMA_ENDPOINTS,
        'patterns': {
            'systemic': HCC_SYSTEMIC_PATTERNS,
            'locoregional': HCC_LOCOREGIONAL_PATTERNS,
            'curative': HCC_CURATIVE_PATTERNS,
            'mortality': HCC_MORTALITY_PATTERNS
    'melanoma': {
        'subspecialties': ['systemic', 'adjuvant', 'neoadjuvant', 'mortality'],
        'detection_function': detect_melanoma_subspecialty,
        'normalizer': normalize_melanoma_endpoint,
        'endpoints': MELANOMA_ENDPOINTS,
        'patterns': {
            'systemic': MEL_SYSTEMIC_PATTERNS,
            'adjuvant': MEL_ADJUVANT_PATTERNS,
            'neoadjuvant': MEL_NEOADJUVANT_PATTERNS,
            'mortality': MEL_MORTALITY_PATTERNS
    'leukaemia': {
        'subspecialties': ['aml', 'all', 'cll', 'cml'],
        'detection_function': detect_leukaemia_subspecialty,
        'normalizer': normalize_leukaemia_endpoint,
        'endpoints': LEUKAEMIA_ENDPOINTS,
        'patterns': {
            'aml': LK_AML_PATTERNS,
            'all': LK_ALL_PATTERNS,
            'cll': LK_CLL_PATTERNS,
            'cml': LK_CML_PATTERNS
    'lymphoma': {
        'subspecialties': ['hodgkin', 'aggressive', 'indolent', 'mortality'],
        'detection_function': detect_lymphoma_subspecialty,
        'normalizer': normalize_lymphoma_endpoint,
        'endpoints': LYMPHOMA_ENDPOINTS,
        'patterns': {
            'hodgkin': LY_HODGKIN_PATTERNS,
            'aggressive': LY_AGGRESSIVE_PATTERNS,
            'indolent': LY_INDOLENT_PATTERNS,
            'mortality': LY_MORTALITY_PATTERNS
    'head_neck_cancer': {
        'subspecialties': ['definitive', 'recurrent_metastatic', 'nasopharyngeal', 'mortality'],
        'detection_function': detect_head_neck_cancer_subspecialty,
        'normalizer': normalize_head_neck_cancer_endpoint,
        'endpoints': HEAD_NECK_CANCER_ENDPOINTS,
        'patterns': {
            'definitive': HN_DEFINITIVE_PATTERNS,
            'recurrent_metastatic': HN_RECURRENT_METASTATIC_PATTERNS,
            'nasopharyngeal': HN_NASOPHARYNGEAL_PATTERNS,
            'mortality': HN_MORTALITY_PATTERNS
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
    'neurology': {
        'subspecialties': ['alzheimers', 'ms', 'parkinsons', 'stroke'],
        'endpoints': {
            'CDR_SB': {'aliases': ['cdr-sb', 'clinical dementia rating', 'cdr sum of boxes']},
            'DISABILITY_PROGRESSION': {'aliases': ['disability progression', 'edss progression']},
            'ANNUALIZED_RELAPSE_RATE': {'aliases': ['annualized relapse rate', 'arr', 'relapse rate']},
            'BRAIN_ATROPHY': {'aliases': ['brain atrophy', 'brain volume loss']}
        }
    },
    'rheumatology': {
        'subspecialties': ['ra', 'psa', 'axspa', 'gout', 'sle'],
        'detection_function': detect_rheumatology_subspecialty,
        'normalizer': normalize_rheumatology_endpoint,
        'endpoints': RHEUMATOLOGY_ENDPOINTS,
        'patterns': {
            'ra': RHEUM_RA_PATTERNS,
            'psa': RHEUM_PSA_PATTERNS,
            'axspa': RHEUM_AXSPA_PATTERNS,
            'gout': RHEUM_GOUT_PATTERNS,
            'sle': RHEUM_SLE_PATTERNS
        }
    },
    'gastroenterology': {
        'subspecialties': ['ibd', 'hpylori', 'gerd', 'mash'],
        'detection_function': detect_gastroenterology_subspecialty,
        'normalizer': normalize_gastroenterology_endpoint,
        'endpoints': GASTROENTEROLOGY_ENDPOINTS,
        'patterns': {
            'ibd': GI_IBD_PATTERNS,
            'hpylori': GI_HPYLORI_PATTERNS,
            'gerd': GI_GERD_PATTERNS,
            'mash': GI_MASH_PATTERNS
        }
    },
    'dermatology': {
        'subspecialties': ['psoriasis', 'atopic_dermatitis', 'acne', 'hidradenitis'],
        'detection_function': detect_dermatology_subspecialty,
        'normalizer': normalize_dermatology_endpoint,
        'endpoints': DERMATOLOGY_ENDPOINTS,
        'patterns': {
            'psoriasis': DERM_PSORIASIS_PATTERNS,
            'atopic_dermatitis': DERM_ATOPIC_DERMATITIS_PATTERNS,
            'acne': DERM_ACNE_PATTERNS,
            'hidradenitis': DERM_HIDRADENITIS_PATTERNS
        }
    },
    'ophthalmology': {
        'subspecialties': ['amd', 'dme', 'glaucoma', 'dry_eye'],
        'detection_function': detect_ophthalmology_subspecialty,
        'normalizer': normalize_ophthalmology_endpoint,
        'endpoints': OPHTHALMOLOGY_ENDPOINTS,
        'patterns': {
            'amd': OPHTH_AMD_PATTERNS,
            'dme': OPHTH_DME_PATTERNS,
            'glaucoma': OPHTH_GLAUCOMA_PATTERNS,
            'dry_eye': OPHTH_DRY_EYE_PATTERNS
        }
    },
    'respiratory': {
        'subspecialties': ['copd', 'asthma', 'ild', 'general_respiratory'],
        'detection_function': detect_respiratory_subspecialty,
        'normalizer': normalize_respiratory_endpoint,
        'endpoints': RESPIRATORY_ENDPOINTS,
        'patterns': {
            'copd': RESP_COPD_PATTERNS,
            'asthma': RESP_ASTHMA_PATTERNS,
            'ild': RESP_ILD_PATTERNS,
            'general_respiratory': RESP_GENERAL_PATTERNS
        }
    },
    'stroke': {
        'subspecialties': ['acute_ischemic', 'hemorrhagic', 'secondary_prevention', 'recovery'],
        'detection_function': detect_stroke_subspecialty,
        'normalizer': normalize_stroke_endpoint,
        'endpoints': STROKE_ENDPOINTS,
        'patterns': {
            'acute_ischemic': STROKE_ACUTE_ISCHEMIC_PATTERNS,
            'hemorrhagic': STROKE_HEMORRHAGIC_PATTERNS,
            'secondary_prevention': STROKE_SECONDARY_PREVENTION_PATTERNS,
            'recovery': STROKE_RECOVERY_PATTERNS
        }
    },
    'nephrology': {
        'subspecialties': ['ckd', 'dialysis', 'aki', 'glomerular'],
        'detection_function': detect_nephrology_subspecialty,
        'normalizer': normalize_nephrology_endpoint,
        'endpoints': NEPHROLOGY_ENDPOINTS,
        'patterns': {
            'ckd': NEPHRO_CKD_PATTERNS,
            'dialysis': NEPHRO_DIALYSIS_PATTERNS,
            'aki': NEPHRO_AKI_PATTERNS,
            'glomerular': NEPHRO_GLOMERULAR_PATTERNS
        }
    },
    'psychiatry': {
        'subspecialties': ['depression', 'anxiety', 'bipolar', 'psychosis'],
        'detection_function': detect_psychiatry_subspecialty,
        'normalizer': normalize_psychiatry_endpoint,
        'endpoints': PSYCHIATRY_ENDPOINTS,
        'patterns': {
            'depression': PSYCH_DEPRESSION_PATTERNS,
            'anxiety': PSYCH_ANXIETY_PATTERNS,
            'bipolar': PSYCH_BIPOLAR_PATTERNS,
            'psychosis': PSYCH_PSYCHOSIS_PATTERNS
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
        'oesophageal_cancer': [
            r'(?:o?esophageal|esophageal)\s+(?:cancer|carcinoma|squamous|adenocarcinoma)',
            r'\boescc\b|\bescc\b(?=.{0,40}(?:o?esophag|esophag))',
            r'(?:o?esophagectomy|esophagectomy)', r'\bcross\s+(?:trial|regimen)\b',
            r'neoadjuvant\s+chemoradi', r'carboplatin[- ,/]+paclitaxel',
            r'barrett', r'checkmate[- ]?577',
            r'(?:advanced|metastatic|recurrent)\s+(?:o?esophageal|esophageal)'
        'prostate_cancer': [
            r'prostate\s+cancer', r'prostate\s+carcinoma', r'prostatic\s+(?:carcinoma|adenocarcinoma)',
            r'castrat(?:ion|e)[- ]?resistant\s+prostate', r'\bm?crpc\b', r'\bm?hspc\b', r'\bnmcrpc\b',
            r'prostate[- ]specific\s+antigen|\bpsa\b', r'\bgleason\b',
            r'radical\s+prostatectomy', r'biochemical\s+(?:recurrence|failure|relapse)',
            r'androgen[- ]deprivation', r'\bpsma\b',
            r'abiraterone|enzalutamide|apalutamide|darolutamide',
            r'leuprolide|goserelin|degarelix|relugolix|triptorelin',
            r'radiographic\s+progression[- ]?free', r'metastasis[- ]?free\s+survival'
        'ovarian_cancer': [
            r'ovarian\s+cancer', r'ovarian\s+carcinoma', r'epithelial\s+ovarian',
            r'fallopian\s+tube\s+(?:cancer|carcinoma)', r'primary\s+peritoneal',
            r'ca[- ]?125', r'cytoreduction|cytoreductive', r'debulking',
            r'platinum[- ](?:sensitive|resistant|refractory)',
            r'olaparib|niraparib|rucaparib', r'\bbrca\b|homologous\s+recombination\s+deficien|\bhrd\b',
            r'carboplatin', r'figo\s+stage', r'primary\s+debulking|interval\s+debulking'
        'pancreatic_cancer': [
            r'pancreatic\s+cancer', r'pancreatic\s+(?:adeno)?carcinoma',
            r'pancreatic\s+ductal\s+adenocarcinoma|\bpdac\b', r'\blapc\b',
            r'folfirinox', r'gemcitabine', r'nab[- ]?paclitaxel',
            r'ca\s?19[-. ]?9', r'pancreaticoduodenectomy|whipple',
            r'borderline\s+resectable', r'resected\s+pancreatic',
            r'locally\s+advanced\s+pancreatic', r'nalirifox', r'metastatic\s+pancreatic'
        'gastric_cancer': [
            r'gastric\s+cancer', r'stomach\s+cancer', r'gastric\s+(?:adeno)?carcinoma',
            r'gastro[- ]?(?:o)?esophageal\s+junction|\bgej\b', r'gastrectomy',
            r'\bflot\b', r'd[12]\s+(?:lymphadenectomy|dissection)',
            r'ramucirumab', r'trastuzumab\s+deruxtecan',
            r'resectable\s+gastric|metastatic\s+gastric|advanced\s+gastric',
            r'perioperative\s+chemotherapy', r'her2[- ]?(?:positive|\+)\s+gastric'
        'hepatocellular_carcinoma': [
            r'hepatocellular\s+carcinoma', r'\bhcc\b', r'liver\s+cancer',
            r'sorafenib|lenvatinib|regorafenib|cabozantinib',
            r'atezolizumab|durvalumab|tremelimumab',
            r'\bbclc\b', r'child[- ]?pugh',
            r'transarterial\s+(?:chemoembolization|radioembolization)|\btace\b|\btare\b',
            r'alpha[- ]?fetoprotein|\bafp\b', r'radiofrequency\s+ablation|\brfa\b',
            r'unresectable\s+(?:hepatocellular|hcc)|advanced\s+(?:hepatocellular|hcc)',
            r'milan\s+criteria', r'hepatectomy|liver\s+resection'
        'melanoma': [
            r'\bmelanoma\b', r'cutaneous\s+melanoma', r'metastatic\s+melanoma',
            r'acral\s+(?:lentiginous\s+)?melanoma|uveal\s+melanoma',
            r'braf\s+v?600|braf[- ]?(?:mutant|mutation|positive)',
            r'ipilimumab|nivolumab|pembrolizumab|relatlimab',
            r'dabrafenib|trametinib|encorafenib|binimetinib|vemurafenib|cobimetinib',
            r'\bbreslow\b', r'sentinel[- ]node', r'resected\s+(?:stage\s+(?:iii|iv)\s+)?melanoma'
        'leukaemia': [
            r'leuk(?:a)?emia', r'acute\s+myeloid|acute\s+lymph(?:o)?blastic',
            r'chronic\s+lymphocytic|chronic\s+myeloid',
            r'\baml\b|\ball\b(?=.{0,40}leuk)|\bcll\b|\bcml\b',
            r'bcr[- ]?abl', r'\bflt3\b|\bnpm1\b',
            r'imatinib|dasatinib|nilotinib|ponatinib|bosutinib|asciminib',
            r'ibrutinib|acalabrutinib|venetoclax', r'blinatumomab|inotuzumab',
            r'complete\s+remission', r'(?:measurable|minimal)\s+residual\s+disease',
            r'major\s+molecular\s+response', r'cytarabine'
        'lymphoma': [
            r'lymphoma', r'hodgkin', r'non[- ]?hodgkin',
            r'diffuse\s+large\s+b[- ]?cell|\bdlbcl\b', r'follicular\s+lymphoma',
            r'mantle[- ]cell|marginal[- ]zone', r'\br[- ]?chop\b',
            r'brentuximab|polatuzumab|\babvd\b|\bbeacopp\b',
            r'rituximab|obinutuzumab|bendamustine',
            r'reed[- ]sternberg', r'axicabtagene|tisagenlecleucel|lisocabtagene'
        'head_neck_cancer': [
            r'head\s+and\s+neck\s+(?:cancer|squamous|carcinoma)|\bhnscc\b',
            r'nasopharyngeal\s+(?:carcinoma|cancer)|\bnpc\b',
            r'oropharyngeal|laryngeal\s+cancer|hypopharyngeal|oral\s+cavity\s+cancer',
            r'chemoradi(?:o|ation)therapy|concurrent\s+chemoradi',
            r'cetuximab', r'\btpf\b', r'locoregional\s+control',
            r'gemcitabine[- ,/]+cisplatin', r'epstein[- ]barr', r'\bextreme\b'
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
        'stroke': [
            r'\bstroke\b', r'ischa?emic\s+stroke', r'acute\s+ischa?emic\s+stroke',
            r'ha?emorrhagic\s+stroke', r'\bnihss\b', r'nih\s+stroke\s+scale',
            r'modified\s+rankin', r'rankin\s+scale',
            r'thrombectomy', r'endovascular\s+(?:therapy|treatment|thrombectomy)', r'\bevt\b',
            r'thrombolysis|thrombolytic', r'alteplase', r'tenecteplase', r'\btpa\b|\btnk\b',
            r'intracerebral\s+ha?emorrhage', r'ha?ematoma\s+(?:expansion|growth)',
            r'\btici\b', r'recanali[sz]ation',
            r'large\s+vessel\s+occlusion|\blvo\b',
            r'recurrent\s+stroke|stroke\s+recurrence',
            r'transient\s+ischa?emic\s+attack|\btia\b',
            r'fugl[- ]meyer', r'barthel\s+index',
            r'stroke\s+rehabilitation|neurorehabilitation', r'secondary\s+stroke\s+prevention'
        ],
        'nephrology': [
            r'chronic\s+kidney\s+disease', r'\bckd\b',
            r'end[- ]stage\s+(?:kidney|renal)\s+disease', r'\beskd\b', r'\besrd\b',
            r'\begfr\b', r'estimated\s+glomerular\s+filtration\s+rate',
            r'\bdialysis\b', r'h?emodialysis', r'peritoneal\s+dialysis',
            r'albuminuria', r'\buacr\b', r'proteinuria', r'\bupcr\b',
            r'nephropathy', r'glomerulonephritis', r'iga\s+nephropathy',
            r'nephrotic', r'nephritis', r'kidney\s+failure', r'\bkdigo\b',
            r'acute\s+kidney\s+injury|\baki\b', r'renal\s+replacement\s+therapy|\brrt\b',
            r'doubling\s+of\s+serum\s+creatinine',
            r'composite\s+(?:kidney|renal)\s+(?:outcome|endpoint)',
            r'membranous\s+nephropathy', r'lupus\s+nephritis', r'\bfsgs\b',
            r'kt/v', r'vascular\s+access'
        ],
        'psychiatry': [
            r'major\s+depressive\s+disorder|\bmdd\b',
            r'\bdepression\b|depressive\s+(?:disorder|episode|symptoms?)',
            r'antidepressant', r'treatment[- ]resistant\s+depression|\btrd\b',
            r'schizophrenia|schizoaffective',
            r'\bpsychosis\b|psychotic\s+(?:disorder|symptoms?|episode|relapse)',
            r'antipsychotic', r'\bbipolar\b', r'\bmania\b|\bmanic\b', r'mood\s+stabili[sz]er',
            r'generali[sz]ed\s+anxiety\s+disorder|anxiety\s+disorder',
            r'\bmadrs\b|montgomery[- ]asberg',
            r'hamilton\s+depression|hamilton\s+rating\s+scale\s+for\s+depression|\bham-?d\b|\bhdrs\b',
            r'hamilton\s+anxiety|\bham-?a\b',
            r'\bpanss\b|positive\s+and\s+negative\s+syndrome\s+scale',
            r'\bymrs\b|young\s+mania\s+rating\s+scale',
            r'\bphq-?9\b', r'\bgad-?7\b', r'\bssri\b|\bsnri\b',
            r'esketamine|zuranolone|brexanolone|vortioxetine|cariprazine|lurasidone|lumateperone|brexpiprazole'
        ],
        'neurology': [
            r'alzheimer', r'dementia', r'multiple\s+sclerosis', r'\bms\b',
            r'parkinson', r'stroke', r'neurological', r'cognitive', r'relapse'
        ],
        'rheumatology': [
            r'rheumatoid\s+arthritis', r'psoriatic\s+arthritis',
            r'ankylosing\s+spondylitis', r'axial\s+spondyloarthritis', r'spondyloarthritis',
            r'systemic\s+lupus\s+erythematosus', r'\blupus\b', r'\bgout\b', r'gouty',
            r'\bacr\s?(?:20|50|70)\b|acr[- ]?(?:20|50|70)', r'\bdas28\b',
            r'\basas\s?(?:20|40)\b|asas[- ]?(?:20|40)', r'\bbasdai\b', r'\basdas\b',
            r'\bsledai\b', r'\bsri[- ]?4\b', r'\bbicla\b',
            r'serum\s+urate', r'urate[- ]lowering', r'\bdmard\b|csdmard',
            r'minimal\s+disease\s+activity'
        ],
        'gastroenterology': [
            r'ulcerative\s+colitis', r"crohn'?s?\s+disease|crohn\s+disease",
            r'inflammatory\s+bowel\s+disease|\bibd\b',
            r'mayo\s+(?:clinic\s+)?score', r'\bcdai\b',
            r'mucosal\s+healing', r'endoscopic\s+(?:remission|improvement|healing)',
            r'steroid[- ]free\s+remission|corticosteroid[- ]free\s+remission',
            r'helicobacter\s+pylori|\bh\.?\s*pylori\b', r'eradication\s+rate',
            r'erosive\s+(?:o?esophagitis|reflux)',
            r'gastro[- ]?o?esophageal\s+reflux|\bgerd\b|\bgord\b',
            r'nonalcoholic\s+steatohepatitis|non[- ]alcoholic\s+steatohepatitis|\bnash\b',
            r'metabolic\s+dysfunction[- ]associated\s+steatohepatitis|\bmash\b',
            r'nonalcoholic\s+fatty\s+liver(?:\s+disease)?|non[- ]alcoholic\s+fatty\s+liver|\bnafld\b|\bmafld\b|\bmasld\b',
            r'mri[- ]?pdff'
        ],
        'dermatology': [
            r'plaque\s+psoriasis', r'\bpsoriasis\b', r'psoriasis\s+vulgaris',
            r'\bpasi\b', r'psoriasis\s+area\s+and\s+severity\s+index',
            r'atopic\s+dermatitis', r'\beczema\b', r'atopic\s+eczema',
            r'\beasi\b', r'easi\s*\d', r'eczema\s+area\s+and\s+severity\s+index',
            r'\bscorad\b', r'viga[- ]ad', r'pruritus\s+nrs', r'itch\s+nrs',
            r'peak\s+pruritus', r'acne\s+vulgaris', r'\bacne\b',
            r'hidradenitis\s+suppurativa', r'\bhiscr\b', r'hi-scr'
        ],
        'ophthalmology': [
            r'age[- ]related\s+macular\s+degeneration', r'\bamd\b|\bnamd\b|\bwamd\b',
            r'neovascular', r'choroidal\s+neovascular\w*|\bcnv\b',
            r'anti[- ]vegf', r'intravitreal',
            r'ranibizumab|aflibercept|bevacizumab|brolucizumab|faricimab|pegcetacoplan|avacincaptad',
            r'best[- ]corrected\s+visual\s+acuity|\bbcva\b', r'visual\s+acuity',
            r'etdrs\s+letters', r'central\s+(?:retinal|subfield|macular)\s+thickness',
            r'\boct\b|optical\s+coherence\s+tomography',
            r'diabetic\s+macular\s+(?:edema|oedema)|\bdme\b|\bdmo\b', r'diabetic\s+retinopathy',
            r'intraocular\s+pressure|\biop\b', r'glaucoma', r'ocular\s+hypertension',
            r'visual\s+field', r'open[- ]angle',
            r'latanoprost|bimatoprost|travoprost|timolol|brinzolamide|dorzolamide|brimonidine|netarsudil',
            r'dry\s+eye(?:\s+disease)?|\bded\b', r'ocular\s+surface', r'\bosdi\b',
            r'corneal\s+(?:fluorescein\s+)?staining', r'schirmer', r'\bocular\b', r'\bcorneal?\b',
            r'cyclosporine|lifitegrast|varenicline\s+nasal'
        ],
        'respiratory': [
            r'chronic\s+obstructive\s+pulmonary\s+disease', r'\bcopd\b', r'\baecopd\b',
            r'\basthma\b', r'asthmatic', r'pulmonary\s+fibrosis', r'\bipf\b',
            r'interstitial\s+lung\s+disease', r'\bild\b', r'emphysema',
            r'exacerbation', r'\bfev1?\b', r'\bfvc\b', r'forced\s+(?:expiratory|vital)',
            r'broncho', r'inhale[dr]?', r'\bsgrq\b', r'\bacq\b', r'\bfeno\b',
            r'tiotropium|umeclidinium|salmeterol|formoterol|budesonide|fluticasone',
            r'mepolizumab|benralizumab|dupilumab|omalizumab|tezepelumab',
            r'nintedanib|pirfenidone'
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
    elif best_specialty == 'oesophageal_cancer':
        subspecialty, conf = detect_oesophageal_cancer_subspecialty(text)
    elif best_specialty == 'prostate_cancer':
        subspecialty, conf = detect_prostate_cancer_subspecialty(text)
    elif best_specialty == 'ovarian_cancer':
        subspecialty, conf = detect_ovarian_cancer_subspecialty(text)
    elif best_specialty == 'pancreatic_cancer':
        subspecialty, conf = detect_pancreatic_cancer_subspecialty(text)
    elif best_specialty == 'gastric_cancer':
        subspecialty, conf = detect_gastric_cancer_subspecialty(text)
    elif best_specialty == 'hepatocellular_carcinoma':
        subspecialty, conf = detect_hepatocellular_carcinoma_subspecialty(text)
    elif best_specialty == 'melanoma':
        subspecialty, conf = detect_melanoma_subspecialty(text)
    elif best_specialty == 'leukaemia':
        subspecialty, conf = detect_leukaemia_subspecialty(text)
    elif best_specialty == 'lymphoma':
        subspecialty, conf = detect_lymphoma_subspecialty(text)
    elif best_specialty == 'head_neck_cancer':
        subspecialty, conf = detect_head_neck_cancer_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'diabetes':
        subspecialty, conf = detect_diabetes_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'respiratory':
        subspecialty, conf = detect_respiratory_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'stroke':
        subspecialty, conf = detect_stroke_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'nephrology':
        subspecialty, conf = detect_nephrology_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'psychiatry':
        subspecialty, conf = detect_psychiatry_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'rheumatology':
        subspecialty, conf = detect_rheumatology_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'gastroenterology':
        subspecialty, conf = detect_gastroenterology_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'dermatology':
        subspecialty, conf = detect_dermatology_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'ophthalmology':
        subspecialty, conf = detect_ophthalmology_subspecialty(text)
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
