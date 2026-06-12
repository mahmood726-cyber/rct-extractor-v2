"""
Specialty Registry - Central registry for all specialty patterns and endpoints.
"""

from typing import Dict, List, Tuple, Optional, Callable
import re

from .ards import (
    ARDS_ENDPOINTS,
    VENTILATION_PATTERNS as ARDS_VENTILATION_PATTERNS,
    PHARMACOTHERAPY_PATTERNS as ARDS_PHARMACOTHERAPY_PATTERNS,
    RESCUE_PATTERNS as ARDS_RESCUE_PATTERNS,
    SUPPORTIVE_PATTERNS as ARDS_SUPPORTIVE_PATTERNS,
    detect_ards_subspecialty,
    normalize_ards_endpoint
)
from .perioperative import (
    PERIOPERATIVE_ENDPOINTS,
    ANAESTHETIC_TECHNIQUE_PATTERNS as PERIOP_ANAESTHETIC_TECHNIQUE_PATTERNS,
    PONV_PATTERNS as PERIOP_PONV_PATTERNS,
    ORGAN_PROTECTION_PATTERNS as PERIOP_ORGAN_PROTECTION_PATTERNS,
    RECOVERY_PATTERNS as PERIOP_RECOVERY_PATTERNS,
    detect_perioperative_subspecialty,
    normalize_perioperative_endpoint
)
from .chronic_pain import (
    CHRONIC_PAIN_ENDPOINTS,
    PHARMACOLOGICAL_PATTERNS as CP_PHARMACOLOGICAL_PATTERNS,
    INTERVENTIONAL_PATTERNS as CP_INTERVENTIONAL_PATTERNS,
    NEUROPATHIC_PATTERNS as CP_NEUROPATHIC_PATTERNS,
    BEHAVIOURAL_PATTERNS as CP_BEHAVIOURAL_PATTERNS,
    detect_chronic_pain_subspecialty,
    normalize_chronic_pain_endpoint
)
from .postoperative_pain import (
    POSTOPERATIVE_PAIN_ENDPOINTS,
    REGIONAL_ANALGESIA_PATTERNS as POP_REGIONAL_ANALGESIA_PATTERNS,
    MULTIMODAL_PATTERNS as POP_MULTIMODAL_PATTERNS,
    OPIOID_PATTERNS as POP_OPIOID_PATTERNS,
    CHRONIC_POSTSURGICAL_PATTERNS as POP_CHRONIC_POSTSURGICAL_PATTERNS,
    detect_postoperative_pain_subspecialty,
    normalize_postoperative_pain_endpoint
)
from .anaemia import (
    ANAEMIA_ENDPOINTS,
    IRON_THERAPY_PATTERNS as ANAEMIA_IRON_THERAPY_PATTERNS,
    ESA_PATTERNS as ANAEMIA_ESA_PATTERNS,
    NUTRITIONAL_PATTERNS as ANAEMIA_NUTRITIONAL_PATTERNS,
    TRANSFUSION_ANAEMIA_PATTERNS as ANAEMIA_TRANSFUSION_PATTERNS,
    detect_anaemia_subspecialty,
    normalize_anaemia_endpoint
)
from .itp import (
    ITP_ENDPOINTS,
    FIRST_LINE_PATTERNS as ITP_FIRST_LINE_PATTERNS,
    TPO_RA_PATTERNS as ITP_TPO_RA_PATTERNS,
    SECOND_LINE_PATTERNS as ITP_SECOND_LINE_PATTERNS,
    PAEDIATRIC_PATTERNS as ITP_PAEDIATRIC_PATTERNS,
    detect_itp_subspecialty,
    normalize_itp_endpoint
)
from .transfusion import (
    TRANSFUSION_ENDPOINTS,
    THRESHOLD_PATTERNS as TX_THRESHOLD_PATTERNS,
    PLATELET_PLASMA_PATTERNS as TX_PLATELET_PLASMA_PATTERNS,
    MASSIVE_PATTERNS as TX_MASSIVE_PATTERNS,
    PROCESSING_PATTERNS as TX_PROCESSING_PATTERNS,
    detect_transfusion_subspecialty,
    normalize_transfusion_endpoint
)
from .allergic_rhinitis import (
    ALLERGIC_RHINITIS_ENDPOINTS,
    PHARMACOTHERAPY_PATTERNS as AR_PHARMACOTHERAPY_PATTERNS,
    IMMUNOTHERAPY_PATTERNS as AR_IMMUNOTHERAPY_PATTERNS,
    BIOLOGICS_PATTERNS as AR_BIOLOGICS_PATTERNS,
    ENVIRONMENTAL_PATTERNS as AR_ENVIRONMENTAL_PATTERNS,
    detect_allergic_rhinitis_subspecialty,
    normalize_allergic_rhinitis_endpoint
)
from .urticaria import (
    URTICARIA_ENDPOINTS,
    ANTIHISTAMINE_PATTERNS as URT_ANTIHISTAMINE_PATTERNS,
    BIOLOGIC_PATTERNS as URT_BIOLOGIC_PATTERNS,
    ANAPHYLAXIS_PATTERNS as URT_ANAPHYLAXIS_PATTERNS,
    OTHER_PATTERNS as URT_OTHER_PATTERNS,
    detect_urticaria_subspecialty,
    normalize_urticaria_endpoint
)
from .orthopaedic import (
    ORTHOPAEDIC_ENDPOINTS,
    FRACTURE_FIXATION_PATTERNS as ORTHO_FRACTURE_FIXATION_PATTERNS,
    ARTHROPLASTY_PATTERNS as ORTHO_ARTHROPLASTY_PATTERNS,
    HEALING_PATTERNS as ORTHO_HEALING_PATTERNS,
    FUNCTIONAL_PATTERNS as ORTHO_FUNCTIONAL_PATTERNS,
    detect_orthopaedic_subspecialty,
    normalize_orthopaedic_endpoint
)
from .low_back_pain import (
    LOW_BACK_PAIN_ENDPOINTS,
    PHARMACOLOGICAL_PATTERNS as LBP_PHARMACOLOGICAL_PATTERNS,
    INTERVENTIONAL_PATTERNS as LBP_INTERVENTIONAL_PATTERNS,
    PHYSICAL_PATTERNS as LBP_PHYSICAL_PATTERNS,
    PSYCHOLOGICAL_PATTERNS as LBP_PSYCHOLOGICAL_PATTERNS,
    detect_low_back_pain_subspecialty,
    normalize_low_back_pain_endpoint
)
from .wound_healing import (
    WOUND_HEALING_ENDPOINTS,
    BURNS_PATTERNS as WH_BURNS_PATTERNS,
    CHRONIC_WOUNDS_PATTERNS as WH_CHRONIC_WOUNDS_PATTERNS,
    SURGICAL_WOUNDS_PATTERNS as WH_SURGICAL_WOUNDS_PATTERNS,
    ADJUNCTS_PATTERNS as WH_ADJUNCTS_PATTERNS,
    detect_wound_healing_subspecialty,
    normalize_wound_healing_endpoint
)

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

from .endometriosis import (
    ENDOMETRIOSIS_ENDPOINTS,
    PAIN_PATTERNS as ENDO_PAIN_PATTERNS,
    MEDICAL_PATTERNS as ENDO_MEDICAL_PATTERNS,
    SURGICAL_PATTERNS as ENDO_SURGICAL_PATTERNS,
    FERTILITY_PATTERNS as ENDO_FERTILITY_PATTERNS,
    detect_endometriosis_subspecialty,
    normalize_endometriosis_endpoint
)
from .menopause_hrt import (
    MENOPAUSE_HRT_ENDPOINTS,
    VASOMOTOR_PATTERNS as MHT_VASOMOTOR_PATTERNS,
    GENITOURINARY_PATTERNS as MHT_GENITOURINARY_PATTERNS,
    BONE_PATTERNS as MHT_BONE_PATTERNS,
    SAFETY_PATTERNS as MHT_SAFETY_PATTERNS,
    detect_menopause_hrt_subspecialty,
    normalize_menopause_hrt_endpoint
)
from .infertility_ivf import (
    INFERTILITY_IVF_ENDPOINTS,
    STIMULATION_PATTERNS as IVF_STIMULATION_PATTERNS,
    LAB_PATTERNS as IVF_LAB_PATTERNS,
    TRANSFER_PATTERNS as IVF_TRANSFER_PATTERNS,
    OVULATION_PATTERNS as IVF_OVULATION_PATTERNS,
    detect_infertility_ivf_subspecialty,
    normalize_infertility_ivf_endpoint
)
from .gestational_diabetes import (
    GESTATIONAL_DIABETES_ENDPOINTS,
    GLYCEMIC_PATTERNS as GDM_GLYCEMIC_PATTERNS,
    MATERNAL_PATTERNS as GDM_MATERNAL_PATTERNS,
    NEONATAL_PATTERNS as GDM_NEONATAL_PATTERNS,
    SCREENING_PATTERNS as GDM_SCREENING_PATTERNS,
    detect_gestational_diabetes_subspecialty,
    normalize_gestational_diabetes_endpoint
)
from .uterine_fibroids import (
    UTERINE_FIBROIDS_ENDPOINTS,
    BLEEDING_PATTERNS as UF_BLEEDING_PATTERNS,
    VOLUME_PATTERNS as UF_VOLUME_PATTERNS,
    PROCEDURAL_PATTERNS as UF_PROCEDURAL_PATTERNS,
    QOL_PATTERNS as UF_QOL_PATTERNS,
    detect_uterine_fibroids_subspecialty,
    normalize_uterine_fibroids_endpoint
)
from .benign_prostatic_hyperplasia import (
    BENIGN_PROSTATIC_HYPERPLASIA_ENDPOINTS,
    SYMPTOMS_PATTERNS as BPH_SYMPTOMS_PATTERNS,
    FLOW_PATTERNS as BPH_FLOW_PATTERNS,
    PROGRESSION_PATTERNS as BPH_PROGRESSION_PATTERNS,
    SEXUAL_PATTERNS as BPH_SEXUAL_PATTERNS,
    detect_benign_prostatic_hyperplasia_subspecialty,
    normalize_benign_prostatic_hyperplasia_endpoint
)
from .erectile_dysfunction import (
    ERECTILE_DYSFUNCTION_ENDPOINTS,
    PHARMACOLOGIC_PATTERNS as ED_PHARMACOLOGIC_PATTERNS,
    SHOCKWAVE_PATTERNS as ED_SHOCKWAVE_PATTERNS,
    DEVICE_PATTERNS as ED_DEVICE_PATTERNS,
    SAFETY_PATTERNS as ED_SAFETY_PATTERNS,
    detect_erectile_dysfunction_subspecialty,
    normalize_erectile_dysfunction_endpoint
)
from .urinary_incontinence import (
    URINARY_INCONTINENCE_ENDPOINTS,
    OAB_PATTERNS as UI_OAB_PATTERNS,
    SUI_PATTERNS as UI_SUI_PATTERNS,
    PROCEDURAL_PATTERNS as UI_PROCEDURAL_PATTERNS,
    QOL_PATTERNS as UI_QOL_PATTERNS,
    detect_urinary_incontinence_subspecialty,
    normalize_urinary_incontinence_endpoint
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

from .osteoporosis import (
    OSTEOPOROSIS_ENDPOINTS,
    FRACTURE_PATTERNS as OST_FRACTURE_PATTERNS,
    BMD_PATTERNS as OST_BMD_PATTERNS,
    BONE_TURNOVER_PATTERNS as OST_BONE_TURNOVER_PATTERNS,
    SAFETY_PATTERNS as OST_SAFETY_PATTERNS,
    detect_osteoporosis_subspecialty,
    normalize_osteoporosis_endpoint
)

from .kidney_transplant import (
    KIDNEY_TRANSPLANT_ENDPOINTS,
    REJECTION_PATTERNS as KT_REJECTION_PATTERNS,
    GRAFT_PATTERNS as KT_GRAFT_PATTERNS,
    FUNCTION_PATTERNS as KT_FUNCTION_PATTERNS,
    COMPLICATIONS_PATTERNS as KT_COMPLICATIONS_PATTERNS,
    detect_kidney_transplant_subspecialty,
    normalize_kidney_transplant_endpoint
)

from .pulmonary_hypertension import (
    PULMONARY_HYPERTENSION_ENDPOINTS,
    FUNCTIONAL_PATTERNS as PH_FUNCTIONAL_PATTERNS,
    HEMODYNAMICS_PATTERNS as PH_HEMODYNAMICS_PATTERNS,
    CLINICAL_WORSENING_PATTERNS as PH_CLINICAL_WORSENING_PATTERNS,
    BIOMARKER_PATTERNS as PH_BIOMARKER_PATTERNS,
    detect_pulmonary_hypertension_subspecialty,
    normalize_pulmonary_hypertension_endpoint
)

from .pcos import (
    PCOS_ENDPOINTS,
    REPRODUCTIVE_PATTERNS as PCOS_REPRODUCTIVE_PATTERNS,
    METABOLIC_PATTERNS as PCOS_METABOLIC_PATTERNS,
    ANDROGEN_PATTERNS as PCOS_ANDROGEN_PATTERNS,
    SAFETY_PATTERNS as PCOS_SAFETY_PATTERNS,
    detect_pcos_subspecialty,
    normalize_pcos_endpoint
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
)

from .prostate_cancer import (
    PROSTATE_CANCER_ENDPOINTS,
    SYSTEMIC_PATTERNS as PC_SYSTEMIC_PATTERNS,
    LOCALIZED_PATTERNS as PC_LOCALIZED_PATTERNS,
    HORMONAL_PATTERNS as PC_HORMONAL_PATTERNS,
    MORTALITY_PATTERNS as PC_MORTALITY_PATTERNS,
    detect_prostate_cancer_subspecialty,
    normalize_prostate_cancer_endpoint
)

from .ovarian_cancer import (
    OVARIAN_CANCER_ENDPOINTS,
    SYSTEMIC_PATTERNS as OC_SYSTEMIC_PATTERNS,
    MAINTENANCE_PATTERNS as OC_MAINTENANCE_PATTERNS,
    SURGICAL_PATTERNS as OC_SURGICAL_PATTERNS,
    MORTALITY_PATTERNS as OC_MORTALITY_PATTERNS,
    detect_ovarian_cancer_subspecialty,
    normalize_ovarian_cancer_endpoint
)

from .pancreatic_cancer import (
    PANCREATIC_CANCER_ENDPOINTS,
    SYSTEMIC_PATTERNS as PA_SYSTEMIC_PATTERNS,
    ADJUVANT_PATTERNS as PA_ADJUVANT_PATTERNS,
    LOCALLY_ADVANCED_PATTERNS as PA_LOCALLY_ADVANCED_PATTERNS,
    MORTALITY_PATTERNS as PA_MORTALITY_PATTERNS,
    detect_pancreatic_cancer_subspecialty,
    normalize_pancreatic_cancer_endpoint
)

from .gastric_cancer import (
    GASTRIC_CANCER_ENDPOINTS,
    SYSTEMIC_PATTERNS as GC_SYSTEMIC_PATTERNS,
    PERIOPERATIVE_PATTERNS as GC_PERIOPERATIVE_PATTERNS,
    SURGICAL_PATTERNS as GC_SURGICAL_PATTERNS,
    MORTALITY_PATTERNS as GC_MORTALITY_PATTERNS,
    detect_gastric_cancer_subspecialty,
    normalize_gastric_cancer_endpoint
)

from .hepatocellular_carcinoma import (
    HEPATOCELLULAR_CARCINOMA_ENDPOINTS,
    SYSTEMIC_PATTERNS as HCC_SYSTEMIC_PATTERNS,
    LOCOREGIONAL_PATTERNS as HCC_LOCOREGIONAL_PATTERNS,
    CURATIVE_PATTERNS as HCC_CURATIVE_PATTERNS,
    MORTALITY_PATTERNS as HCC_MORTALITY_PATTERNS,
    detect_hepatocellular_carcinoma_subspecialty,
    normalize_hepatocellular_carcinoma_endpoint
)

from .melanoma import (
    MELANOMA_ENDPOINTS,
    SYSTEMIC_PATTERNS as MEL_SYSTEMIC_PATTERNS,
    ADJUVANT_PATTERNS as MEL_ADJUVANT_PATTERNS,
    NEOADJUVANT_PATTERNS as MEL_NEOADJUVANT_PATTERNS,
    MORTALITY_PATTERNS as MEL_MORTALITY_PATTERNS,
    detect_melanoma_subspecialty,
    normalize_melanoma_endpoint
)

from .leukaemia import (
    LEUKAEMIA_ENDPOINTS,
    AML_PATTERNS as LK_AML_PATTERNS,
    ALL_PATTERNS as LK_ALL_PATTERNS,
    CLL_PATTERNS as LK_CLL_PATTERNS,
    CML_PATTERNS as LK_CML_PATTERNS,
    detect_leukaemia_subspecialty,
    normalize_leukaemia_endpoint
)

from .lymphoma import (
    LYMPHOMA_ENDPOINTS,
    HODGKIN_PATTERNS as LY_HODGKIN_PATTERNS,
    AGGRESSIVE_PATTERNS as LY_AGGRESSIVE_PATTERNS,
    INDOLENT_PATTERNS as LY_INDOLENT_PATTERNS,
    MORTALITY_PATTERNS as LY_MORTALITY_PATTERNS,
    detect_lymphoma_subspecialty,
    normalize_lymphoma_endpoint
)

from .multiple_myeloma import (
    MULTIPLE_MYELOMA_ENDPOINTS,
    NEWLY_DIAGNOSED_PATTERNS as MM_NEWLY_DIAGNOSED_PATTERNS,
    RELAPSED_REFRACTORY_PATTERNS as MM_RELAPSED_REFRACTORY_PATTERNS,
    RESPONSE_PATTERNS as MM_RESPONSE_PATTERNS,
    MORTALITY_PATTERNS as MM_MORTALITY_PATTERNS,
    detect_multiple_myeloma_subspecialty,
    normalize_multiple_myeloma_endpoint
)

from .head_neck_cancer import (
    HEAD_NECK_CANCER_ENDPOINTS,
    DEFINITIVE_PATTERNS as HN_DEFINITIVE_PATTERNS,
    RECURRENT_METASTATIC_PATTERNS as HN_RECURRENT_METASTATIC_PATTERNS,
    NASOPHARYNGEAL_PATTERNS as HN_NASOPHARYNGEAL_PATTERNS,
    MORTALITY_PATTERNS as HN_MORTALITY_PATTERNS,
    detect_head_neck_cancer_subspecialty,
    normalize_head_neck_cancer_endpoint
)

from .bladder_cancer import (
    BLADDER_CANCER_ENDPOINTS,
    NMIBC_PATTERNS as BL_NMIBC_PATTERNS,
    MIBC_PATTERNS as BL_MIBC_PATTERNS,
    ADVANCED_PATTERNS as BL_ADVANCED_PATTERNS,
    MORTALITY_PATTERNS as BL_MORTALITY_PATTERNS,
    detect_bladder_cancer_subspecialty,
    normalize_bladder_cancer_endpoint
)

from .renal_cell_carcinoma import (
    RENAL_CELL_CARCINOMA_ENDPOINTS,
    ADVANCED_PATTERNS as RCC_ADVANCED_PATTERNS,
    ADJUVANT_PATTERNS as RCC_ADJUVANT_PATTERNS,
    SUBSEQUENT_LINE_PATTERNS as RCC_SUBSEQUENT_LINE_PATTERNS,
    MORTALITY_PATTERNS as RCC_MORTALITY_PATTERNS,
    detect_renal_cell_carcinoma_subspecialty,
    normalize_renal_cell_carcinoma_endpoint
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

from .venous_thromboembolism import (
    VTE_ENDPOINTS,
    TREATMENT_PATTERNS as VTE_TREATMENT_PATTERNS,
    PREVENTION_PATTERNS as VTE_PREVENTION_PATTERNS,
    BLEEDING_PATTERNS as VTE_BLEEDING_PATTERNS,
    MORTALITY_PATTERNS as VTE_MORTALITY_PATTERNS,
    detect_venous_thromboembolism_subspecialty,
    normalize_venous_thromboembolism_endpoint
)

from .peripheral_artery_disease import (
    PAD_ENDPOINTS,
    LIMB_OUTCOMES_PATTERNS as PAD_LIMB_OUTCOMES_PATTERNS,
    REVASCULARISATION_PATTERNS as PAD_REVASCULARISATION_PATTERNS,
    MEDICAL_THERAPY_PATTERNS as PAD_MEDICAL_THERAPY_PATTERNS,
    FUNCTIONAL_PATTERNS as PAD_FUNCTIONAL_PATTERNS,
    detect_peripheral_artery_disease_subspecialty,
    normalize_peripheral_artery_disease_endpoint
)

from .obesity import (
    OBESITY_ENDPOINTS,
    WEIGHT_LOSS_PATTERNS as OB_WEIGHT_LOSS_PATTERNS,
    BODY_COMPOSITION_PATTERNS as OB_BODY_COMPOSITION_PATTERNS,
    CARDIOMETABOLIC_PATTERNS as OB_CARDIOMETABOLIC_PATTERNS,
    SAFETY_PATTERNS as OB_SAFETY_PATTERNS,
    detect_obesity_subspecialty,
    normalize_obesity_endpoint
)

from .thyroid import (
    THYROID_ENDPOINTS,
    HYPOTHYROIDISM_PATTERNS as THY_HYPOTHYROIDISM_PATTERNS,
    HYPERTHYROIDISM_PATTERNS as THY_HYPERTHYROIDISM_PATTERNS,
    THYROID_FUNCTION_PATTERNS as THY_THYROID_FUNCTION_PATTERNS,
    OUTCOMES_PATTERNS as THY_OUTCOMES_PATTERNS,
    detect_thyroid_subspecialty,
    normalize_thyroid_endpoint
)

from .parkinsons import (
    PARKINSONS_ENDPOINTS,
    TREATMENT_PATTERNS as PD_MOTOR_PATTERNS,
    DRUG_RESISTANT_PATTERNS as PD_DEVICE_PATTERNS,
    PREVENTION_PATTERNS as PD_NONMOTOR_PATTERNS,
    LATENT_PATTERNS as PD_NEUROPROTECTION_PATTERNS,
    detect_parkinsons_subspecialty,
    normalize_parkinsons_endpoint
)

from .alzheimers import (
    ALZHEIMERS_ENDPOINTS,
    TREATMENT_PATTERNS as AD_SYMPTOMATIC_PATTERNS,
    DRUG_RESISTANT_PATTERNS as AD_DMT_PATTERNS,
    PREVENTION_PATTERNS as AD_NEUROPSYCH_PATTERNS,
    LATENT_PATTERNS as AD_PREVENTION_MCI_PATTERNS,
    detect_alzheimers_subspecialty,
    normalize_alzheimers_endpoint
)

from .multiple_sclerosis import (
    MULTIPLE_SCLEROSIS_ENDPOINTS,
    TREATMENT_PATTERNS as MS_RELAPSING_PATTERNS,
    DRUG_RESISTANT_PATTERNS as MS_PROGRESSIVE_PATTERNS,
    PREVENTION_PATTERNS as MS_SYMPTOMATIC_PATTERNS,
    LATENT_PATTERNS as MS_ACUTE_RELAPSE_PATTERNS,
    detect_multiple_sclerosis_subspecialty,
    normalize_multiple_sclerosis_endpoint
)

from .migraine import (
    MIGRAINE_ENDPOINTS,
    TREATMENT_PATTERNS as MIGRAINE_ACUTE_PATTERNS,
    DRUG_RESISTANT_PATTERNS as MIGRAINE_PREVENTIVE_PATTERNS,
    PREVENTION_PATTERNS as MIGRAINE_CHRONIC_PATTERNS,
    LATENT_PATTERNS as MIGRAINE_DEVICE_PATTERNS,
    detect_migraine_subspecialty,
    normalize_migraine_endpoint
)

from .schizophrenia import (
    SCHIZOPHRENIA_ENDPOINTS,
    TREATMENT_PATTERNS as SCZ_ACUTE_PATTERNS,
    DRUG_RESISTANT_PATTERNS as SCZ_MAINTENANCE_PATTERNS,
    PREVENTION_PATTERNS as SCZ_NEGCOG_PATTERNS,
    LATENT_PATTERNS as SCZ_SAFETY_PATTERNS,
    detect_schizophrenia_subspecialty,
    normalize_schizophrenia_endpoint
)

from .cirrhosis import (
    CIRRHOSIS_ENDPOINTS,
    TREATMENT_PATTERNS as CIRR_PORTAL_HTN_PATTERNS,
    DRUG_RESISTANT_PATTERNS as CIRR_DECOMPENSATION_PATTERNS,
    PREVENTION_PATTERNS as CIRR_ENCEPHALOPATHY_PATTERNS,
    LATENT_PATTERNS as CIRR_PROGRESSION_PATTERNS,
    detect_cirrhosis_subspecialty,
    normalize_cirrhosis_endpoint
)

from .osteoarthritis import (
    OSTEOARTHRITIS_ENDPOINTS,
    TREATMENT_PATTERNS as OA_PHARM_PATTERNS,
    DRUG_RESISTANT_PATTERNS as OA_INTRAARTICULAR_PATTERNS,
    PREVENTION_PATTERNS as OA_STRUCTURAL_PATTERNS,
    LATENT_PATTERNS as OA_NONPHARM_PATTERNS,
    detect_osteoarthritis_subspecialty,
    normalize_osteoarthritis_endpoint
)

from .covid19 import (
    COVID19_ENDPOINTS,
    TREATMENT_PATTERNS as COV_ANTIVIRAL_PATTERNS,
    DRUG_RESISTANT_PATTERNS as COV_IMMUNO_PATTERNS,
    PREVENTION_PATTERNS as COV_PROPHYLAXIS_PATTERNS,
    LATENT_PATTERNS as COV_SEVERE_PATTERNS,
    detect_covid19_subspecialty,
    normalize_covid19_endpoint
)

from .sepsis import (
    SEPSIS_ENDPOINTS,
    TREATMENT_PATTERNS as SEP_HEMO_PATTERNS,
    DRUG_RESISTANT_PATTERNS as SEP_ADJUNCTIVE_PATTERNS,
    PREVENTION_PATTERNS as SEP_ANTIMICROBIAL_PATTERNS,
    LATENT_PATTERNS as SEP_ORGAN_PATTERNS,
    detect_sepsis_subspecialty,
    normalize_sepsis_endpoint
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
    'ards': {
        'subspecialties': ['ventilation', 'pharmacotherapy', 'rescue', 'supportive'],
        'detection_function': detect_ards_subspecialty,
        'normalizer': normalize_ards_endpoint,
        'endpoints': ARDS_ENDPOINTS,
        'patterns': {
            'ventilation': ARDS_VENTILATION_PATTERNS,
            'pharmacotherapy': ARDS_PHARMACOTHERAPY_PATTERNS,
            'rescue': ARDS_RESCUE_PATTERNS,
            'supportive': ARDS_SUPPORTIVE_PATTERNS
        }
    },
    'perioperative': {
        'subspecialties': ['anaesthetic_technique', 'ponv', 'organ_protection', 'recovery'],
        'detection_function': detect_perioperative_subspecialty,
        'normalizer': normalize_perioperative_endpoint,
        'endpoints': PERIOPERATIVE_ENDPOINTS,
        'patterns': {
            'anaesthetic_technique': PERIOP_ANAESTHETIC_TECHNIQUE_PATTERNS,
            'ponv': PERIOP_PONV_PATTERNS,
            'organ_protection': PERIOP_ORGAN_PROTECTION_PATTERNS,
            'recovery': PERIOP_RECOVERY_PATTERNS
        }
    },
    'chronic_pain': {
        'subspecialties': ['pharmacological', 'interventional', 'neuropathic', 'behavioural'],
        'detection_function': detect_chronic_pain_subspecialty,
        'normalizer': normalize_chronic_pain_endpoint,
        'endpoints': CHRONIC_PAIN_ENDPOINTS,
        'patterns': {
            'pharmacological': CP_PHARMACOLOGICAL_PATTERNS,
            'interventional': CP_INTERVENTIONAL_PATTERNS,
            'neuropathic': CP_NEUROPATHIC_PATTERNS,
            'behavioural': CP_BEHAVIOURAL_PATTERNS
        }
    },
    'postoperative_pain': {
        'subspecialties': ['regional_analgesia', 'multimodal', 'opioid', 'chronic_postsurgical'],
        'detection_function': detect_postoperative_pain_subspecialty,
        'normalizer': normalize_postoperative_pain_endpoint,
        'endpoints': POSTOPERATIVE_PAIN_ENDPOINTS,
        'patterns': {
            'regional_analgesia': POP_REGIONAL_ANALGESIA_PATTERNS,
            'multimodal': POP_MULTIMODAL_PATTERNS,
            'opioid': POP_OPIOID_PATTERNS,
            'chronic_postsurgical': POP_CHRONIC_POSTSURGICAL_PATTERNS
        }
    },
    'anaemia': {
        'subspecialties': ['iron_therapy', 'esa', 'nutritional', 'transfusion_anaemia'],
        'detection_function': detect_anaemia_subspecialty,
        'normalizer': normalize_anaemia_endpoint,
        'endpoints': ANAEMIA_ENDPOINTS,
        'patterns': {
            'iron_therapy': ANAEMIA_IRON_THERAPY_PATTERNS,
            'esa': ANAEMIA_ESA_PATTERNS,
            'nutritional': ANAEMIA_NUTRITIONAL_PATTERNS,
            'transfusion_anaemia': ANAEMIA_TRANSFUSION_PATTERNS
        }
    },
    'itp': {
        'subspecialties': ['first_line', 'tpo_ra', 'second_line', 'paediatric'],
        'detection_function': detect_itp_subspecialty,
        'normalizer': normalize_itp_endpoint,
        'endpoints': ITP_ENDPOINTS,
        'patterns': {
            'first_line': ITP_FIRST_LINE_PATTERNS,
            'tpo_ra': ITP_TPO_RA_PATTERNS,
            'second_line': ITP_SECOND_LINE_PATTERNS,
            'paediatric': ITP_PAEDIATRIC_PATTERNS
        }
    },
    'transfusion': {
        'subspecialties': ['threshold', 'platelet_plasma', 'massive', 'processing'],
        'detection_function': detect_transfusion_subspecialty,
        'normalizer': normalize_transfusion_endpoint,
        'endpoints': TRANSFUSION_ENDPOINTS,
        'patterns': {
            'threshold': TX_THRESHOLD_PATTERNS,
            'platelet_plasma': TX_PLATELET_PLASMA_PATTERNS,
            'massive': TX_MASSIVE_PATTERNS,
            'processing': TX_PROCESSING_PATTERNS
        }
    },
    'allergic_rhinitis': {
        'subspecialties': ['pharmacotherapy', 'immunotherapy', 'biologics', 'environmental'],
        'detection_function': detect_allergic_rhinitis_subspecialty,
        'normalizer': normalize_allergic_rhinitis_endpoint,
        'endpoints': ALLERGIC_RHINITIS_ENDPOINTS,
        'patterns': {
            'pharmacotherapy': AR_PHARMACOTHERAPY_PATTERNS,
            'immunotherapy': AR_IMMUNOTHERAPY_PATTERNS,
            'biologics': AR_BIOLOGICS_PATTERNS,
            'environmental': AR_ENVIRONMENTAL_PATTERNS
        }
    },
    'urticaria': {
        'subspecialties': ['antihistamine', 'biologic', 'anaphylaxis', 'other'],
        'detection_function': detect_urticaria_subspecialty,
        'normalizer': normalize_urticaria_endpoint,
        'endpoints': URTICARIA_ENDPOINTS,
        'patterns': {
            'antihistamine': URT_ANTIHISTAMINE_PATTERNS,
            'biologic': URT_BIOLOGIC_PATTERNS,
            'anaphylaxis': URT_ANAPHYLAXIS_PATTERNS,
            'other': URT_OTHER_PATTERNS
        }
    },
    'orthopaedic': {
        'subspecialties': ['fracture_fixation', 'arthroplasty', 'healing', 'functional'],
        'detection_function': detect_orthopaedic_subspecialty,
        'normalizer': normalize_orthopaedic_endpoint,
        'endpoints': ORTHOPAEDIC_ENDPOINTS,
        'patterns': {
            'fracture_fixation': ORTHO_FRACTURE_FIXATION_PATTERNS,
            'arthroplasty': ORTHO_ARTHROPLASTY_PATTERNS,
            'healing': ORTHO_HEALING_PATTERNS,
            'functional': ORTHO_FUNCTIONAL_PATTERNS
        }
    },
    'low_back_pain': {
        'subspecialties': ['pharmacological', 'interventional', 'physical', 'psychological'],
        'detection_function': detect_low_back_pain_subspecialty,
        'normalizer': normalize_low_back_pain_endpoint,
        'endpoints': LOW_BACK_PAIN_ENDPOINTS,
        'patterns': {
            'pharmacological': LBP_PHARMACOLOGICAL_PATTERNS,
            'interventional': LBP_INTERVENTIONAL_PATTERNS,
            'physical': LBP_PHYSICAL_PATTERNS,
            'psychological': LBP_PSYCHOLOGICAL_PATTERNS
        }
    },
    'wound_healing': {
        'subspecialties': ['burns', 'chronic_wounds', 'surgical_wounds', 'adjuncts'],
        'detection_function': detect_wound_healing_subspecialty,
        'normalizer': normalize_wound_healing_endpoint,
        'endpoints': WOUND_HEALING_ENDPOINTS,
        'patterns': {
            'burns': WH_BURNS_PATTERNS,
            'chronic_wounds': WH_CHRONIC_WOUNDS_PATTERNS,
            'surgical_wounds': WH_SURGICAL_WOUNDS_PATTERNS,
            'adjuncts': WH_ADJUNCTS_PATTERNS
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
        }
    },
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
        }
    },
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
        }
    },
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
        }
    },
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
        }
    },
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
        }
    },
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
        }
    },
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
        }
    },
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
        }
    },
    'multiple_myeloma': {
        'subspecialties': ['newly_diagnosed', 'relapsed_refractory', 'response', 'mortality'],
        'detection_function': detect_multiple_myeloma_subspecialty,
        'normalizer': normalize_multiple_myeloma_endpoint,
        'endpoints': MULTIPLE_MYELOMA_ENDPOINTS,
        'patterns': {
            'newly_diagnosed': MM_NEWLY_DIAGNOSED_PATTERNS,
            'relapsed_refractory': MM_RELAPSED_REFRACTORY_PATTERNS,
            'response': MM_RESPONSE_PATTERNS,
            'mortality': MM_MORTALITY_PATTERNS
        }
    },
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
    'bladder_cancer': {
        'subspecialties': ['nmibc', 'mibc', 'advanced', 'mortality'],
        'detection_function': detect_bladder_cancer_subspecialty,
        'normalizer': normalize_bladder_cancer_endpoint,
        'endpoints': BLADDER_CANCER_ENDPOINTS,
        'patterns': {
            'nmibc': BL_NMIBC_PATTERNS,
            'mibc': BL_MIBC_PATTERNS,
            'advanced': BL_ADVANCED_PATTERNS,
            'mortality': BL_MORTALITY_PATTERNS
        }
    },
    'renal_cell_carcinoma': {
        'subspecialties': ['advanced', 'adjuvant', 'subsequent_line', 'mortality'],
        'detection_function': detect_renal_cell_carcinoma_subspecialty,
        'normalizer': normalize_renal_cell_carcinoma_endpoint,
        'endpoints': RENAL_CELL_CARCINOMA_ENDPOINTS,
        'patterns': {
            'advanced': RCC_ADVANCED_PATTERNS,
            'adjuvant': RCC_ADJUVANT_PATTERNS,
            'subsequent_line': RCC_SUBSEQUENT_LINE_PATTERNS,
            'mortality': RCC_MORTALITY_PATTERNS
        }
    },
    'endometriosis': {
        'subspecialties': ['pain', 'medical', 'surgical', 'fertility'],
        'detection_function': detect_endometriosis_subspecialty,
        'normalizer': normalize_endometriosis_endpoint,
        'endpoints': ENDOMETRIOSIS_ENDPOINTS,
        'patterns': {
            'pain': ENDO_PAIN_PATTERNS,
            'medical': ENDO_MEDICAL_PATTERNS,
            'surgical': ENDO_SURGICAL_PATTERNS,
            'fertility': ENDO_FERTILITY_PATTERNS
        }
    },
    'menopause_hrt': {
        'subspecialties': ['vasomotor', 'genitourinary', 'bone', 'safety'],
        'detection_function': detect_menopause_hrt_subspecialty,
        'normalizer': normalize_menopause_hrt_endpoint,
        'endpoints': MENOPAUSE_HRT_ENDPOINTS,
        'patterns': {
            'vasomotor': MHT_VASOMOTOR_PATTERNS,
            'genitourinary': MHT_GENITOURINARY_PATTERNS,
            'bone': MHT_BONE_PATTERNS,
            'safety': MHT_SAFETY_PATTERNS
        }
    },
    'infertility_ivf': {
        'subspecialties': ['stimulation', 'lab', 'transfer', 'ovulation'],
        'detection_function': detect_infertility_ivf_subspecialty,
        'normalizer': normalize_infertility_ivf_endpoint,
        'endpoints': INFERTILITY_IVF_ENDPOINTS,
        'patterns': {
            'stimulation': IVF_STIMULATION_PATTERNS,
            'lab': IVF_LAB_PATTERNS,
            'transfer': IVF_TRANSFER_PATTERNS,
            'ovulation': IVF_OVULATION_PATTERNS
        }
    },
    'gestational_diabetes': {
        'subspecialties': ['glycemic', 'maternal', 'neonatal', 'screening'],
        'detection_function': detect_gestational_diabetes_subspecialty,
        'normalizer': normalize_gestational_diabetes_endpoint,
        'endpoints': GESTATIONAL_DIABETES_ENDPOINTS,
        'patterns': {
            'glycemic': GDM_GLYCEMIC_PATTERNS,
            'maternal': GDM_MATERNAL_PATTERNS,
            'neonatal': GDM_NEONATAL_PATTERNS,
            'screening': GDM_SCREENING_PATTERNS
        }
    },
    'uterine_fibroids': {
        'subspecialties': ['bleeding', 'volume', 'procedural', 'qol'],
        'detection_function': detect_uterine_fibroids_subspecialty,
        'normalizer': normalize_uterine_fibroids_endpoint,
        'endpoints': UTERINE_FIBROIDS_ENDPOINTS,
        'patterns': {
            'bleeding': UF_BLEEDING_PATTERNS,
            'volume': UF_VOLUME_PATTERNS,
            'procedural': UF_PROCEDURAL_PATTERNS,
            'qol': UF_QOL_PATTERNS
        }
    },
    'benign_prostatic_hyperplasia': {
        'subspecialties': ['symptoms', 'flow', 'progression', 'sexual'],
        'detection_function': detect_benign_prostatic_hyperplasia_subspecialty,
        'normalizer': normalize_benign_prostatic_hyperplasia_endpoint,
        'endpoints': BENIGN_PROSTATIC_HYPERPLASIA_ENDPOINTS,
        'patterns': {
            'symptoms': BPH_SYMPTOMS_PATTERNS,
            'flow': BPH_FLOW_PATTERNS,
            'progression': BPH_PROGRESSION_PATTERNS,
            'sexual': BPH_SEXUAL_PATTERNS
        }
    },
    'erectile_dysfunction': {
        'subspecialties': ['pharmacologic', 'shockwave', 'device', 'safety'],
        'detection_function': detect_erectile_dysfunction_subspecialty,
        'normalizer': normalize_erectile_dysfunction_endpoint,
        'endpoints': ERECTILE_DYSFUNCTION_ENDPOINTS,
        'patterns': {
            'pharmacologic': ED_PHARMACOLOGIC_PATTERNS,
            'shockwave': ED_SHOCKWAVE_PATTERNS,
            'device': ED_DEVICE_PATTERNS,
            'safety': ED_SAFETY_PATTERNS
        }
    },
    'urinary_incontinence': {
        'subspecialties': ['oab', 'sui', 'procedural', 'qol'],
        'detection_function': detect_urinary_incontinence_subspecialty,
        'normalizer': normalize_urinary_incontinence_endpoint,
        'endpoints': URINARY_INCONTINENCE_ENDPOINTS,
        'patterns': {
            'oab': UI_OAB_PATTERNS,
            'sui': UI_SUI_PATTERNS,
            'procedural': UI_PROCEDURAL_PATTERNS,
            'qol': UI_QOL_PATTERNS
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
    'venous_thromboembolism': {
        'subspecialties': ['treatment', 'prevention', 'bleeding', 'mortality'],
        'detection_function': detect_venous_thromboembolism_subspecialty,
        'normalizer': normalize_venous_thromboembolism_endpoint,
        'endpoints': VTE_ENDPOINTS,
        'patterns': {
            'treatment': VTE_TREATMENT_PATTERNS,
            'prevention': VTE_PREVENTION_PATTERNS,
            'bleeding': VTE_BLEEDING_PATTERNS,
            'mortality': VTE_MORTALITY_PATTERNS
        }
    },
    'peripheral_artery_disease': {
        'subspecialties': ['limb_outcomes', 'revascularisation', 'medical_therapy', 'functional'],
        'detection_function': detect_peripheral_artery_disease_subspecialty,
        'normalizer': normalize_peripheral_artery_disease_endpoint,
        'endpoints': PAD_ENDPOINTS,
        'patterns': {
            'limb_outcomes': PAD_LIMB_OUTCOMES_PATTERNS,
            'revascularisation': PAD_REVASCULARISATION_PATTERNS,
            'medical_therapy': PAD_MEDICAL_THERAPY_PATTERNS,
            'functional': PAD_FUNCTIONAL_PATTERNS
        }
    },
    'obesity': {
        'subspecialties': ['weight_loss', 'body_composition', 'cardiometabolic', 'safety'],
        'detection_function': detect_obesity_subspecialty,
        'normalizer': normalize_obesity_endpoint,
        'endpoints': OBESITY_ENDPOINTS,
        'patterns': {
            'weight_loss': OB_WEIGHT_LOSS_PATTERNS,
            'body_composition': OB_BODY_COMPOSITION_PATTERNS,
            'cardiometabolic': OB_CARDIOMETABOLIC_PATTERNS,
            'safety': OB_SAFETY_PATTERNS
        }
    },
    'thyroid': {
        'subspecialties': ['hypothyroidism', 'hyperthyroidism', 'thyroid_function', 'outcomes'],
        'detection_function': detect_thyroid_subspecialty,
        'normalizer': normalize_thyroid_endpoint,
        'endpoints': THYROID_ENDPOINTS,
        'patterns': {
            'hypothyroidism': THY_HYPOTHYROIDISM_PATTERNS,
            'hyperthyroidism': THY_HYPERTHYROIDISM_PATTERNS,
            'thyroid_function': THY_THYROID_FUNCTION_PATTERNS,
            'outcomes': THY_OUTCOMES_PATTERNS
        }
    },
    'osteoporosis': {
        'subspecialties': ['fracture', 'bmd', 'bone_turnover', 'safety'],
        'detection_function': detect_osteoporosis_subspecialty,
        'normalizer': normalize_osteoporosis_endpoint,
        'endpoints': OSTEOPOROSIS_ENDPOINTS,
        'patterns': {
            'fracture': OST_FRACTURE_PATTERNS,
            'bmd': OST_BMD_PATTERNS,
            'bone_turnover': OST_BONE_TURNOVER_PATTERNS,
            'safety': OST_SAFETY_PATTERNS
        }
    },
    'kidney_transplant': {
        'subspecialties': ['rejection', 'graft', 'function', 'complications'],
        'detection_function': detect_kidney_transplant_subspecialty,
        'normalizer': normalize_kidney_transplant_endpoint,
        'endpoints': KIDNEY_TRANSPLANT_ENDPOINTS,
        'patterns': {
            'rejection': KT_REJECTION_PATTERNS,
            'graft': KT_GRAFT_PATTERNS,
            'function': KT_FUNCTION_PATTERNS,
            'complications': KT_COMPLICATIONS_PATTERNS
        }
    },
    'pulmonary_hypertension': {
        'subspecialties': ['functional', 'hemodynamics', 'clinical_worsening', 'biomarker'],
        'detection_function': detect_pulmonary_hypertension_subspecialty,
        'normalizer': normalize_pulmonary_hypertension_endpoint,
        'endpoints': PULMONARY_HYPERTENSION_ENDPOINTS,
        'patterns': {
            'functional': PH_FUNCTIONAL_PATTERNS,
            'hemodynamics': PH_HEMODYNAMICS_PATTERNS,
            'clinical_worsening': PH_CLINICAL_WORSENING_PATTERNS,
            'biomarker': PH_BIOMARKER_PATTERNS
        }
    },
    'pcos': {
        'subspecialties': ['reproductive', 'metabolic', 'androgen', 'safety'],
        'detection_function': detect_pcos_subspecialty,
        'normalizer': normalize_pcos_endpoint,
        'endpoints': PCOS_ENDPOINTS,
        'patterns': {
            'reproductive': PCOS_REPRODUCTIVE_PATTERNS,
            'metabolic': PCOS_METABOLIC_PATTERNS,
            'androgen': PCOS_ANDROGEN_PATTERNS,
            'safety': PCOS_SAFETY_PATTERNS
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
    'cirrhosis': {
        'subspecialties': ['portal_hypertension', 'decompensation', 'encephalopathy', 'progression'],
        'detection_function': detect_cirrhosis_subspecialty,
        'normalizer': normalize_cirrhosis_endpoint,
        'endpoints': CIRRHOSIS_ENDPOINTS,
        'patterns': {
            'portal_hypertension': CIRR_PORTAL_HTN_PATTERNS,
            'decompensation': CIRR_DECOMPENSATION_PATTERNS,
            'encephalopathy': CIRR_ENCEPHALOPATHY_PATTERNS,
            'progression': CIRR_PROGRESSION_PATTERNS
        }
    },
    'osteoarthritis': {
        'subspecialties': ['pharmacologic', 'intraarticular', 'structural', 'nonpharm'],
        'detection_function': detect_osteoarthritis_subspecialty,
        'normalizer': normalize_osteoarthritis_endpoint,
        'endpoints': OSTEOARTHRITIS_ENDPOINTS,
        'patterns': {
            'pharmacologic': OA_PHARM_PATTERNS,
            'intraarticular': OA_INTRAARTICULAR_PATTERNS,
            'structural': OA_STRUCTURAL_PATTERNS,
            'nonpharm': OA_NONPHARM_PATTERNS
        }
    },
    'covid19': {
        'subspecialties': ['antiviral', 'immunomodulator', 'prophylaxis_vaccine', 'severe_supportive'],
        'detection_function': detect_covid19_subspecialty,
        'normalizer': normalize_covid19_endpoint,
        'endpoints': COVID19_ENDPOINTS,
        'patterns': {
            'antiviral': COV_ANTIVIRAL_PATTERNS,
            'immunomodulator': COV_IMMUNO_PATTERNS,
            'prophylaxis_vaccine': COV_PROPHYLAXIS_PATTERNS,
            'severe_supportive': COV_SEVERE_PATTERNS
        }
    },
    'sepsis': {
        'subspecialties': ['hemodynamic', 'adjunctive', 'antimicrobial_source', 'organ_support'],
        'detection_function': detect_sepsis_subspecialty,
        'normalizer': normalize_sepsis_endpoint,
        'endpoints': SEPSIS_ENDPOINTS,
        'patterns': {
            'hemodynamic': SEP_HEMO_PATTERNS,
            'adjunctive': SEP_ADJUNCTIVE_PATTERNS,
            'antimicrobial_source': SEP_ANTIMICROBIAL_PATTERNS,
            'organ_support': SEP_ORGAN_PATTERNS
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
    },
    'parkinsons': {
        'subspecialties': ['motor', 'device_advanced', 'nonmotor', 'neuroprotection'],
        'detection_function': detect_parkinsons_subspecialty,
        'normalizer': normalize_parkinsons_endpoint,
        'endpoints': PARKINSONS_ENDPOINTS,
        'patterns': {
            'motor': PD_MOTOR_PATTERNS,
            'device_advanced': PD_DEVICE_PATTERNS,
            'nonmotor': PD_NONMOTOR_PATTERNS,
            'neuroprotection': PD_NEUROPROTECTION_PATTERNS
        }
    },
    'alzheimers': {
        'subspecialties': ['symptomatic', 'disease_modifying', 'neuropsychiatric', 'prevention_mci'],
        'detection_function': detect_alzheimers_subspecialty,
        'normalizer': normalize_alzheimers_endpoint,
        'endpoints': ALZHEIMERS_ENDPOINTS,
        'patterns': {
            'symptomatic': AD_SYMPTOMATIC_PATTERNS,
            'disease_modifying': AD_DMT_PATTERNS,
            'neuropsychiatric': AD_NEUROPSYCH_PATTERNS,
            'prevention_mci': AD_PREVENTION_MCI_PATTERNS
        }
    },
    'multiple_sclerosis': {
        'subspecialties': ['relapsing', 'progressive', 'symptomatic', 'acute_relapse'],
        'detection_function': detect_multiple_sclerosis_subspecialty,
        'normalizer': normalize_multiple_sclerosis_endpoint,
        'endpoints': MULTIPLE_SCLEROSIS_ENDPOINTS,
        'patterns': {
            'relapsing': MS_RELAPSING_PATTERNS,
            'progressive': MS_PROGRESSIVE_PATTERNS,
            'symptomatic': MS_SYMPTOMATIC_PATTERNS,
            'acute_relapse': MS_ACUTE_RELAPSE_PATTERNS
        }
    },
    'migraine': {
        'subspecialties': ['acute', 'preventive', 'chronic', 'device_neuromod'],
        'detection_function': detect_migraine_subspecialty,
        'normalizer': normalize_migraine_endpoint,
        'endpoints': MIGRAINE_ENDPOINTS,
        'patterns': {
            'acute': MIGRAINE_ACUTE_PATTERNS,
            'preventive': MIGRAINE_PREVENTIVE_PATTERNS,
            'chronic': MIGRAINE_CHRONIC_PATTERNS,
            'device_neuromod': MIGRAINE_DEVICE_PATTERNS
        }
    },
    'schizophrenia': {
        'subspecialties': ['acute', 'maintenance', 'negative_cognitive', 'safety'],
        'detection_function': detect_schizophrenia_subspecialty,
        'normalizer': normalize_schizophrenia_endpoint,
        'endpoints': SCHIZOPHRENIA_ENDPOINTS,
        'patterns': {
            'acute': SCZ_ACUTE_PATTERNS,
            'maintenance': SCZ_MAINTENANCE_PATTERNS,
            'negative_cognitive': SCZ_NEGCOG_PATTERNS,
            'safety': SCZ_SAFETY_PATTERNS
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
_FALLBACK_SPECIALTIES = {'infectious_disease', 'neurology'}


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
        'ards': [
            r'\bards\b', r'acute\s+respiratory\s+distress\s+syndrome',
            r'acute\s+(?:hypox(?:ae|e)mic\s+)?respiratory\s+failure',
            r'ventilator[- ]free\s+days', r'lung[- ]protective\s+ventilation',
            r'low\s+tidal\s+volume', r'prone\s+position(?:ing)?|proning',
            r'pao2\s*[:/]\s*fio2|p/f\s+ratio', r'berlin\s+definition',
            r'higher\s+peep|positive\s+end[- ]expiratory\s+pressure',
            r'veno[- ]venous\s+ecmo|\bvv[- ]?ecmo\b',
            r'refractory\s+hypox(?:ae|e)mia', r'recruitment\s+man(?:o?eu|eu)vre',
            r'high[- ]flow\s+nasal\s+(?:oxygen|cannula)|\bhfnc\b|\bhfno\b'
        ],
        'perioperative': [
            r'perioperative', r'postoperative', r'intraoperative',
            r'an(?:ae|e)sthesia', r'an(?:ae|e)sthetic', r'an(?:ae|e)sthesiolog',
            r'postoperative\s+nausea\s+and\s+vomiting|\bponv\b',
            r'regional\s+an(?:ae|e)sthesia|neuraxial|spinal\s+an(?:ae|e)sthesia',
            r'general\s+an(?:ae|e)sthesia', r'peripheral\s+nerve\s+block',
            r'total\s+intravenous\s+an(?:ae|e)sthesia|\btiva\b',
            r'postoperative\s+delirium', r'postoperative\s+complications?',
            r'surgical[- ]site\s+infection', r'enhanced\s+recovery\s+after\s+surgery|\beras\b',
            r'undergoing\s+(?:elective\s+)?surgery', r'non[- ]cardiac\s+surgery',
            r'myocardial\s+injury\s+after\s+non[- ]cardiac\s+surgery|\bmins\b'
        ],
        'chronic_pain': [
            r'chronic\s+pain', r'neuropathic\s+pain', r'painful\s+(?:diabetic\s+)?neuropathy',
            r'post[- ]?herpetic\s+neuralgia', r'trigeminal\s+neuralgia',
            r'fibromyalgia', r'pain\s+intensity', r'\bnrs\s+pain\b|pain\s+nrs',
            r'pregabalin|gabapentin', r'duloxetine', r'spinal\s+cord\s+stimulation',
            r'radiofrequency\s+(?:ablation|denervation)', r'epidural\s+steroid',
            r'>=?\s*(?:30|50)%\s+(?:pain\s+)?reduction', r'analgesic\s+(?:efficacy|effect)',
            r'central\s+sensiti[sz]ation', r'allodynia|hyperalgesia',
            r'brief\s+pain\s+inventory'
        ],
        'postoperative_pain': [
            r'postoperative\s+pain', r'post[- ]?operative\s+analgesia',
            r'acute\s+post[- ]?surgical\s+pain', r'chronic\s+post[- ]?surgical\s+pain',
            r'(?:morphine|opioid)\s+consumption', r'rescue\s+analgesi\w+',
            r'patient[- ]controlled\s+analgesia|\bpca\b', r'multimodal\s+analgesia',
            r'transversus\s+abdominis\s+plane|\btap\s+block\b', r'erector\s+spinae\s+block',
            r'time\s+to\s+first\s+(?:rescue|analgesi)', r'opioid[- ]sparing',
            r'pain\s+(?:score|at\s+rest|on\s+movement)\s+(?:after|following)\s+surgery',
            r'wound\s+infiltration', r'preemptive\s+analgesia|pre[- ]emptive\s+analgesia'
        ],
        'anaemia': [
            r'iron[- ]deficiency\s+an(?:ae|e)mia|\bida\b', r'\ban(?:ae|e)mia\b', r'an(?:ae|e)mic',
            r'intravenous\s+iron|\biv\s+iron\b|oral\s+iron|ferrous\s+(?:sulfate|sulphate|fumarate)',
            r'ferric\s+carboxymaltose|iron\s+sucrose|ferric\s+derisomaltose|\bfcm\b',
            r'erythropoiesis[- ]stimulating\s+agent|\besa\b|erythropoietin|epoetin|darbepoetin',
            r'roxadustat|daprodustat|vadadustat|hif[- ]?ph',
            r'h(?:ae|e)moglobin\s+(?:response|change|increase|target)', r'serum\s+ferritin|ferritin',
            r'transferrin\s+saturation|\btsat\b', r'iron[- ]folic\s+acid|iron\s+and\s+folic\s+acid',
            r'red[- ](?:blood[- ])?cell\s+transfusion|transfusion\s+(?:requirement|avoidance)'
        ],
        'itp': [
            r'immune\s+thrombocytopenia|immune\s+thrombocytopenic\s+purpura|\bitp\b',
            r'thrombocytopenic\s+purpura', r'thrombopoietin\s+receptor\s+agonist|\btpo[- ]?ra\b',
            r'eltrombopag|romiplostim|avatrombopag|hetrombopag|fostamatinib',
            r'platelet\s+response', r'platelet\s+count\s+(?:>=|of\s+at\s+least)\s*\d+',
            r'durable\s+(?:platelet\s+)?response', r'rituximab\s+for\s+(?:itp|immune)',
            r'high[- ]dose\s+dexamethasone', r'anti[- ]d\s+immunoglobulin',
            r'newly\s+diagnosed\s+(?:itp|immune\s+thrombocytopenia)'
        ],
        'transfusion': [
            r'restrictive\s+(?:vs\.?\s+liberal\s+)?(?:transfusion|strategy|threshold)',
            r'liberal\s+(?:transfusion|strategy|threshold)', r'transfusion\s+threshold',
            r'transfusion\s+strategy', r'red[- ](?:blood[- ])?cell\s+transfusion',
            r'h(?:ae|e)moglobin\s+(?:trigger|threshold)', r'platelet\s+transfusion',
            r'fresh\s+frozen\s+plasma|\bffp\b', r'massive\s+transfusion',
            r'prophylactic\s+platelet', r'whole\s+blood\s+(?:transfusion|resuscitation)',
            r'patient\s+blood\s+management', r'units\s+(?:of\s+(?:blood|red\s+cells)|transfused)',
            r'(?:1\s*:\s*1\s*:\s*1|fixed[- ]ratio)\s+(?:transfusion|resuscitation)?'
        ],
        'allergic_rhinitis': [
            r'allergic\s+rhinitis', r'rhinoconjunctivitis', r'hay\s+fever',
            r'seasonal\s+allergic\s+rhinitis|\bsar\b', r'perennial\s+allergic\s+rhinitis',
            r'total\s+nasal\s+symptom\s+score|\btnss\b',
            r'combined\s+symptom(?:[- ]and)?[- ]medication\s+score|\bcsms\b',
            r'allergen\s+immunotherapy|sublingual\s+immunotherapy|\bslit\b',
            r'intranasal\s+corticosteroid', r'rhinoconjunctivitis\s+quality\s+of\s+life|\brqlq\b',
            r'grass\s+pollen|house\s+dust\s+mite\s+allerg|ragweed',
            r'nasal\s+congestion\s+score', r'azelastine|montelukast\s+for\s+rhinitis'
        ],
        'urticaria': [
            r'chronic\s+spontaneous\s+urticaria|\bcsu\b', r'chronic\s+idiopathic\s+urticaria|\bciu\b',
            r'chronic\s+urticaria', r'chronic\s+inducible\s+urticaria|\bcindu\b',
            r'urticaria\s+activity\s+score|\buas7\b', r'urticaria\s+control\s+test|\buct\b',
            r'\banaphylaxis\b|anaphylactic', r'(?:adrenaline|epinephrine)\s+auto[- ]?injector',
            r'omalizumab|ligelizumab|remibrutinib', r'itch\s+severity\s+score|\biss7\b',
            r'angioedema', r'biphasic\s+reaction', r'hives', r'wheal\s+and\s+flare'
        ],
        'orthopaedic': [
            r'(?:internal|external)\s+fixation', r'open\s+reduction|\borif\b',
            r'intramedullary\s+nail', r'locking\s+plate|plate\s+fixation',
            r'(?:total\s+)?(?:hip|knee|shoulder)\s+(?:arthroplasty|replacement)|\btha\b|\btka\b|\btkr\b|\bthr\b',
            r'hemiarthroplasty', r'non[- ]?union|delayed\s+union|time\s+to\s+union',
            r'(?:distal\s+radius|ankle|tibial?|clavicle|proximal\s+humerus|femoral\s+neck|hip)\s+fracture',
            r'harris\s+hip\s+score|oxford\s+(?:hip|knee)\s+score|womac|dash\s+score|constant\s+score',
            r'reoperation|revision\s+(?:surgery|arthroplasty)',
            r'acl\s+reconstruction|rotator\s+cuff\s+repair',
            r'operative\s+(?:vs\.?\s+)?(?:non[- ]?operative|conservative)',
            r'periprosthetic\s+joint\s+infection|\bpji\b'
        ],
        'low_back_pain': [
            r'low\s+back\s+pain', r'chronic\s+low\s+back\s+pain', r'acute\s+low\s+back\s+pain',
            r'\blumbago\b', r'sciatica', r'lumbar\s+radiculopathy',
            r'oswestry\s+disability(?:\s+index)?|\bodi\b', r'roland[- ]morris|\brmdq\b|\brdq\b',
            r'(?:lumbar\s+)?disc\s+herniation', r'spinal\s+manipulation\s+for\s+(?:back|low)',
            r'epidural\s+steroid\s+injection', r'back[- ]specific\s+function',
            r'non[- ]specific\s+(?:low\s+)?back\s+pain', r'quebec\s+back\s+pain'
        ],
        'wound_healing': [
            r'wound\s+healing', r'\bburn\b|burns|burn\s+(?:wound|injury)|thermal\s+injury',
            r'diabetic\s+foot\s+ulcer|\bdfu\b', r'venous\s+leg\s+ulcer|\bvlu\b',
            r'pressure\s+(?:ulcer|injury|sore)', r'chronic\s+wound|non[- ]healing\s+(?:wound|ulcer)',
            r'negative[- ]pressure\s+wound\s+therapy|\bnpwt\b',
            r'complete\s+(?:wound\s+)?(?:healing|closure)', r'time\s+to\s+(?:wound\s+)?healing',
            r'wound\s+(?:area\s+reduction|dehiscence)', r'skin\s+graft|split[- ]thickness',
            r'skin\s+substitute|dermal\s+(?:template|matrix)', r're[- ]?epitheliali[sz]ation',
            r'leg\s+ulcer\s+healing'
        ],
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
        'uterine_fibroids': [
            r'uterine\s+fibroids?', r'uterine\s+leiomyoma(?:ta)?', r'leiomyoma(?:ta)?',
            r'\bmyoma(?:ta)?\b', r'\bfibroids?\b', r'heavy\s+menstrual\s+bleeding',
            r'menstrual\s+blood\s+loss', r'ulipristal', r'relugolix',
            r'uterine\s+artery\s+emboli[sz]ation|\buae\b', r'myomectomy',
            r'fibroid\s+volume', r'ufs[- ]qol',
            r'(?:mr[- ]?guided\s+)?focused\s+ultrasound|mrgfus'
        ],
        'benign_prostatic_hyperplasia': [
            r'benign\s+prostatic\s+(?:hyperplasia|obstruction|enlargement)',
            r'\bbph\b', r'lower\s+urinary\s+tract\s+symptoms?|\bluts\b',
            r'international\s+prostate\s+symptom\s+score|\bipss\b',
            r'tamsulosin|alfuzosin|silodosin|doxazosin|terazosin',
            r'finasteride|dutasteride', r'transurethral\s+resection|\bturp\b',
            r'maximum\s+(?:urinary\s+)?flow\s+rate|\bqmax\b',
            r'prostatic\s+urethral\s+lift|urolift|holep|greenlight|rezum',
            r'5[- ]?alpha[- ]?reductase'
        ],
        'erectile_dysfunction': [
            r'erectile\s+dysfunction', r'erectile\s+function', r'\bimpotence\b',
            r'international\s+index\s+of\s+erectile\s+function|\biief\b',
            r'sildenafil|tadalafil|vardenafil|avanafil|udenafil',
            r'phosphodiesterase[- ]?5|pde[- ]?5\s+inhibitor',
            r'sexual\s+encounter\s+profile|\bsep\s?[23]\b',
            r'erection\s+hardness', r'penile\s+(?:prosthesis|implant)',
            r'intracavernosal', r'vacuum\s+erection\s+device',
            r'low[- ]intensity\s+(?:extracorporeal\s+)?shock'
        ],
        'urinary_incontinence': [
            r'overactive\s+bladder|\boab\b', r'urinary\s+incontinence',
            r'urgency\s+urinary\s+incontinence|\buui\b', r'urge\s+incontinence',
            r'stress\s+urinary\s+incontinence', r'urinary\s+urgency',
            r'mirabegron|vibegron',
            r'solifenacin|tolterodine|fesoterodine|oxybutynin|darifenacin|trospium',
            r'antimuscarinic', r'detrusor\s+overactivity',
            r'midurethral\s+sling|sacral\s+neuromodulation',
            r'percutaneous\s+tibial\s+nerve|\bptns\b', r'micturition\s+frequency'
        ],
        'oesophageal_cancer': [
            r'(?:o?esophageal|esophageal)\s+(?:cancer|carcinoma|squamous|adenocarcinoma)',
            r'\boescc\b|\bescc\b(?=.{0,40}(?:o?esophag|esophag))',
            r'(?:o?esophagectomy|esophagectomy)', r'\bcross\s+(?:trial|regimen)\b',
            r'neoadjuvant\s+chemoradi', r'carboplatin[- ,/]+paclitaxel',
            r'barrett', r'checkmate[- ]?577',
            r'(?:advanced|metastatic|recurrent)\s+(?:o?esophageal|esophageal)'
        ],
        'prostate_cancer': [
            r'prostate\s+cancer', r'prostate\s+carcinoma', r'prostatic\s+(?:carcinoma|adenocarcinoma)',
            r'castrat(?:ion|e)[- ]?resistant\s+prostate', r'\bm?crpc\b', r'\bm?hspc\b', r'\bnmcrpc\b',
            r'prostate[- ]specific\s+antigen|\bpsa\b', r'\bgleason\b',
            r'radical\s+prostatectomy', r'biochemical\s+(?:recurrence|failure|relapse)',
            r'androgen[- ]deprivation', r'\bpsma\b',
            r'abiraterone|enzalutamide|apalutamide|darolutamide',
            r'leuprolide|goserelin|degarelix|relugolix|triptorelin',
            r'radiographic\s+progression[- ]?free', r'metastasis[- ]?free\s+survival'
        ],
        'ovarian_cancer': [
            r'ovarian\s+cancer', r'ovarian\s+carcinoma', r'epithelial\s+ovarian',
            r'fallopian\s+tube\s+(?:cancer|carcinoma)', r'primary\s+peritoneal',
            r'ca[- ]?125', r'cytoreduction|cytoreductive', r'debulking',
            r'platinum[- ](?:sensitive|resistant|refractory)',
            r'olaparib|niraparib|rucaparib', r'\bbrca\b|homologous\s+recombination\s+deficien|\bhrd\b',
            r'carboplatin', r'figo\s+stage', r'primary\s+debulking|interval\s+debulking'
        ],
        'pancreatic_cancer': [
            r'pancreatic\s+cancer', r'pancreatic\s+(?:adeno)?carcinoma',
            r'pancreatic\s+ductal\s+adenocarcinoma|\bpdac\b', r'\blapc\b',
            r'folfirinox', r'gemcitabine', r'nab[- ]?paclitaxel',
            r'ca\s?19[-. ]?9', r'pancreaticoduodenectomy|whipple',
            r'borderline\s+resectable', r'resected\s+pancreatic',
            r'locally\s+advanced\s+pancreatic', r'nalirifox', r'metastatic\s+pancreatic'
        ],
        'gastric_cancer': [
            r'gastric\s+cancer', r'stomach\s+cancer', r'gastric\s+(?:adeno)?carcinoma',
            r'gastro[- ]?(?:o)?esophageal\s+junction|\bgej\b', r'gastrectomy',
            r'\bflot\b', r'd[12]\s+(?:lymphadenectomy|dissection)',
            r'ramucirumab', r'trastuzumab\s+deruxtecan',
            r'resectable\s+gastric|metastatic\s+gastric|advanced\s+gastric',
            r'perioperative\s+chemotherapy', r'her2[- ]?(?:positive|\+)\s+gastric'
        ],
        'hepatocellular_carcinoma': [
            r'hepatocellular\s+carcinoma', r'\bhcc\b', r'liver\s+cancer',
            r'sorafenib|lenvatinib|regorafenib|cabozantinib',
            r'atezolizumab|durvalumab|tremelimumab',
            r'\bbclc\b', r'child[- ]?pugh',
            r'transarterial\s+(?:chemoembolization|radioembolization)|\btace\b|\btare\b',
            r'alpha[- ]?fetoprotein|\bafp\b', r'radiofrequency\s+ablation|\brfa\b',
            r'unresectable\s+(?:hepatocellular|hcc)|advanced\s+(?:hepatocellular|hcc)',
            r'milan\s+criteria', r'hepatectomy|liver\s+resection'
        ],
        'melanoma': [
            r'\bmelanoma\b', r'cutaneous\s+melanoma', r'metastatic\s+melanoma',
            r'acral\s+(?:lentiginous\s+)?melanoma|uveal\s+melanoma',
            r'braf\s+v?600|braf[- ]?(?:mutant|mutation|positive)',
            r'ipilimumab|nivolumab|pembrolizumab|relatlimab',
            r'dabrafenib|trametinib|encorafenib|binimetinib|vemurafenib|cobimetinib',
            r'\bbreslow\b', r'sentinel[- ]node', r'resected\s+(?:stage\s+(?:iii|iv)\s+)?melanoma'
        ],
        'leukaemia': [
            r'leuk(?:a)?emia', r'acute\s+myeloid|acute\s+lymph(?:o)?blastic',
            r'chronic\s+lymphocytic|chronic\s+myeloid',
            r'\baml\b|\ball\b(?=.{0,40}leuk)|\bcll\b|\bcml\b',
            r'bcr[- ]?abl', r'\bflt3\b|\bnpm1\b',
            r'imatinib|dasatinib|nilotinib|ponatinib|bosutinib|asciminib',
            r'ibrutinib|acalabrutinib|venetoclax', r'blinatumomab|inotuzumab',
            r'complete\s+remission', r'(?:measurable|minimal)\s+residual\s+disease',
            r'major\s+molecular\s+response', r'cytarabine'
        ],
        'lymphoma': [
            r'lymphoma', r'hodgkin', r'non[- ]?hodgkin',
            r'diffuse\s+large\s+b[- ]?cell|\bdlbcl\b', r'follicular\s+lymphoma',
            r'mantle[- ]cell|marginal[- ]zone', r'\br[- ]?chop\b',
            r'brentuximab|polatuzumab|\babvd\b|\bbeacopp\b',
            r'rituximab|obinutuzumab|bendamustine',
            r'reed[- ]sternberg', r'axicabtagene|tisagenlecleucel|lisocabtagene'
        ],
        'multiple_myeloma': [
            r'multiple\s+myeloma', r'\bmyeloma\b', r'\bndmm\b|\brrmm\b',
            r'plasma[- ]cell\s+(?:neoplasm|disorder|dyscrasia)', r'm[- ]protein|paraprotein',
            r'bortezomib|carfilzomib|ixazomib', r'lenalidomide|pomalidomide|thalidomide',
            r'daratumumab|isatuximab', r'elotuzumab|belantamab|selinexor',
            r'\bvrd\b|\bkrd\b|\bd[- ]?vrd\b|\bvmp\b',
            r'idecabtagene|ciltacabtagene|teclistamab|talquetamab|elranatamab',
            r'autologous\s+stem[- ]cell\s+transplant', r'imwg', r'\bbcma\b'
        ],
        'head_neck_cancer': [
            r'head\s+and\s+neck\s+(?:cancer|squamous|carcinoma)|\bhnscc\b',
            r'nasopharyngeal\s+(?:carcinoma|cancer)|\bnpc\b',
            r'oropharyngeal|laryngeal\s+cancer|hypopharyngeal|oral\s+cavity\s+cancer',
            r'chemoradi(?:o|ation)therapy|concurrent\s+chemoradi',
            r'cetuximab', r'\btpf\b', r'locoregional\s+control',
            r'gemcitabine[- ,/]+cisplatin', r'epstein[- ]barr', r'\bextreme\b'
        ],
        'bladder_cancer': [
            r'bladder\s+cancer', r'urothelial\s+(?:carcinoma|cancer)',
            r'non[- ]?muscle[- ]?invasive\s+bladder|\bnmibc\b',
            r'muscle[- ]?invasive\s+bladder|\bmibc\b',
            r'intravesical', r'bacillus\s+calmette[- ]gu[ée]rin|\bbcg\b(?=.{0,40}bladder)',
            r'radical\s+cystectomy', r'enfortumab|avelumab\s+maintenance',
            r'transurethral\s+resection|\bturbt\b', r'metastatic\s+urothelial'
        ],
        'renal_cell_carcinoma': [
            r'renal\s+cell\s+(?:carcinoma|cancer)|\brcc\b|\bmrcc\b',
            r'clear[- ]cell\s+renal', r'kidney\s+cancer',
            r'sunitinib|pazopanib|cabozantinib|axitinib|tivozanib|lenvatinib',
            r'ipilimumab|nivolumab|pembrolizumab', r'\bimdc\b', r'nephrectomy',
            r'metastatic\s+renal', r'\bvhl\b|von\s+hippel[- ]lindau', r'belzutifan'
        ],
        'endometriosis': [
            r'endometriosis', r'endometrioma', r'adenomyosis',
            r'deep\s+infiltrating\s+endometriosis', r'endometriosis[- ]associated\s+pain',
            r'dienogest', r'elagolix', r'relugolix', r'linzagolix',
            r'rasrm|rafs|revised\s+american\s+fertility',
            r'ectopic\s+endometrial', r'peritoneal\s+endometriosis',
            r'\bb\s*&\s*b\s+score\b|biberoglu[- ]behrman'
        ],
        'menopause_hrt': [
            # NB: r'menopaus(?:e|al)' already matches the substring in
            # "postmenopausal"/"perimenopausal", so listing those separately would
            # double-count one demographic word and let it outrank a specific
            # specialty (e.g. an oncology breast-cancer trial that merely says
            # "postmenopausal"). Keep the single base pattern.
            r'menopaus(?:e|al)', r'climacteric',
            r'hot\s+flush(?:es)?|hot\s+flash(?:es)?', r'vasomotor\s+symptom',
            r'hormone\s+(?:replacement\s+)?therapy', r'\bhrt\b', r'\bmht\b',
            r'vulvovaginal\s+atrophy', r'genitourinary\s+syndrome\s+of\s+menopause',
            r'fezolinetant|elinzanetant', r'tibolone', r'ospemifene', r'prasterone',
            r'conjugated\s+equine\s+(?:o?estrogen)', r'night\s+sweats?'
        ],
        'infertility_ivf': [
            r'in[- ]vitro\s+fertili[sz]ation', r'\bivf\b', r'\bicsi\b',
            r'intracytoplasmic\s+sperm\s+injection', r'assisted\s+reproducti\w+',
            r'embryo\s+transfer', r'ovarian\s+stimulation',
            r'controlled\s+ovarian\s+(?:hyper)?stimulation',
            r'oocytes?\s+retrieved|oocyte\s+yield', r'ovarian\s+hyperstimulation\s+syndrome',
            r'\bohss\b', r'clinical\s+pregnancy\s+rate', r'blastocyst',
            r'gn?rh\s+antagonist|gn?rh\s+agonist', r'follitropin|gonadotro?ph?in',
            r'frozen[- ](?:thawed\s+)?embryo|\bfet\b', r'intrauterine\s+insemination|\biui\b',
            r'subfertil(?:e|ity)', r'\binfertilit(?:y|ies)\b', r'ovulation\s+induction',
            r'anovulat(?:ion|ory)', r'clomi(?:phene|fene)', r'fertili[sz]ation\s+rate',
            r'(?:clinical|ongoing)\s+pregnancy', r'mature\s+oocyte|mii\s+oocyte'
        ],
        'gestational_diabetes': [
            r'gestational\s+diabetes(?:\s+mellitus)?', r'\bgdm\b',
            r'hyperglyca?emia\s+in\s+pregnancy', r'diabetes\s+in\s+pregnancy',
            r'glucose\s+intolerance\s+in\s+pregnancy', r'macrosomia',
            r'large[- ]for[- ]gestational[- ]age|\blga\b',
            r'neonatal\s+hypoglyca?emia',
            r'oral\s+glucose\s+tolerance\s+test|\bogtt\b', r'\biadpsg\b',
            r'glyburide|glibenclamide', r'(?:one|two)[- ]step\s+screening',
            r'shoulder\s+dystocia', r'birth\s*weight', r'gestational\s+weight\s+gain',
            r'need\s+for\s+insulin|insulin\s+requirement',
            r'fasting\s+(?:plasma\s+)?glucose', r'postprandial\s+glucose'
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
        'osteoporosis': [
            r'osteoporo(?:sis|tic)', r'osteopenia', r'bone\s+mineral\s+density|\bbmd\b',
            r'vertebral\s+fracture', r'non[- ]?vertebral\s+fracture', r'hip\s+fracture',
            r'fragility\s+fracture', r'osteoporotic\s+fracture',
            r'bisphosphonate|alendronate|risedronate|ibandronate|zoledronic',
            r'denosumab', r'teriparatide|abaloparatide', r'romosozumab',
            r'raloxifene|bazedoxifene', r'strontium\s+ranelate',
            r't[- ]score', r'\bfrax\b', r'bone[- ]turnover\s+marker',
            r'postmenopausal\s+(?:women\s+)?(?:with\s+)?osteoporosis',
            r'femoral\s+neck|lumbar\s+spine\s+(?:bmd|bone)',
        ],
        'kidney_transplant': [
            r'kidney\s+transplant\w*', r'renal\s+transplant\w*', r'renal\s+allograft',
            r'kidney\s+allograft', r'\ballograft\b', r'graft\s+(?:loss|failure|survival)',
            r'(?:biopsy[- ]proven\s+)?acute\s+rejection', r'antibody[- ]mediated\s+rejection',
            r'delayed\s+graft\s+function', r'transplant\s+recipients?',
            r'tacrolimus|ciclosporin|cyclosporine', r'mycophenolate|belatacept',
            r'basiliximab|anti[- ]thymocyte\s+globulin|thymoglobulin', r'sirolimus|everolimus',
            r'living[- ](?:donor|related)\s+(?:kidney|renal)|deceased[- ]donor',
            r'immunosuppress(?:ion|ive)\s+(?:regimen|therapy)',
        ],
        'pulmonary_hypertension': [
            r'pulmonary\s+(?:arterial\s+)?hypertension', r'\bpah\b',
            r'pulmonary\s+vascular\s+resistance|\bpvr\b',
            r'mean\s+pulmonary\s+arter(?:ial|y)\s+pressure|\bmpap\b',
            r'6[- ]min(?:ute)?\s+walk|six[- ]min(?:ute)?\s+walk|\b6mwd\b|\b6mwt\b',
            r'who\s+functional\s+class', r'right\s+heart\s+catheter',
            r'bosentan|ambrisentan|macitentan', r'epoprostenol|treprostinil|iloprost|selexipag|beraprost',
            r'riociguat', r'sotatercept', r'endothelin\s+receptor\s+antagonist',
            r'sildenafil|tadalafil', r'time\s+to\s+clinical\s+worsening',
            r'pulmonary\s+arteriopathy|chronic\s+thromboembolic\s+pulmonary',
        ],
        'pcos': [
            r'polycystic\s+ovar(?:y|ian)\s+syndrome', r'\bpcos\b', r'polycystic\s+ovar(?:y|ian|ies)',
            r'anovulat(?:ion|ory)', r'ovulation\s+induction', r'oligo[- ]?ovulation',
            r'letrozole', r'clomi(?:phene|fene)', r'hyperandrogenism|hyperandrogen(?:a|ae)mia',
            r'hirsutism|ferriman[- ]gallwey', r'oligomenorrh(?:o)?ea|amenorrh(?:o)?ea',
            r'rotterdam\s+criteria', r'free\s+androgen\s+index',
            r'sex\s+hormone[- ]binding\s+globulin', r'ovarian\s+drilling',
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
            # schizophrenia / schizoaffective + PANSS are now owned by the dedicated
            # 'schizophrenia' specialty (more specific); psychiatry keeps mood,
            # anxiety and bipolar. 'psychosis'/'antipsychotic' stay here because they
            # also arise in mood disorders (e.g. bipolar with psychotic features).
            r'\bpsychosis\b|psychotic\s+(?:disorder|symptoms?|episode|relapse)',
            r'antipsychotic', r'\bbipolar\b', r'\bmania\b|\bmanic\b', r'mood\s+stabili[sz]er',
            r'generali[sz]ed\s+anxiety\s+disorder|anxiety\s+disorder',
            r'\bmadrs\b|montgomery[- ]asberg',
            r'hamilton\s+depression|hamilton\s+rating\s+scale\s+for\s+depression|\bham-?d\b|\bhdrs\b',
            r'hamilton\s+anxiety|\bham-?a\b',
            r'\bymrs\b|young\s+mania\s+rating\s+scale',
            r'\bphq-?9\b', r'\bgad-?7\b', r'\bssri\b|\bsnri\b',
            r'esketamine|zuranolone|brexanolone|vortioxetine|cariprazine|lurasidone|lumateperone|brexpiprazole'
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
        'venous_thromboembolism': [
            # VTE-specific anchors only. Generic anticoagulation terms (the oral
            # DOAC drug names, "anticoagulation", "major bleeding", "DOAC/NOAC",
            # "vitamin-K antagonist") were deliberately removed from *detection*:
            # they are shared verbatim with atrial-fibrillation / ACS trials and
            # caused VTE to steal AF anticoagulation studies (which route to
            # cardiology). Real VTE reports always carry the thrombosis/embolism
            # vocabulary below, so detection stays strong; extraction is forced-
            # specialty in the eval and is unaffected by this trim.
            r'venous\s+thromboembolism', r'\bvte\b', r'thromboprophylaxis',
            r'deep[- ]vein\s+thrombosis', r'\bdvt\b', r'pulmonary\s+embolism',
            r'recurrent\s+(?:venous\s+thromboembolism|vte|thrombosis)',
            r'thromboembolic',
            r'enoxaparin|dalteparin|tinzaparin|nadroparin|fondaparinux',
            r'low[- ]molecular[- ]weight\s+heparin|unfractionated\s+heparin',
            r'post[- ]?thrombotic\s+syndrome',
        ],
        'peripheral_artery_disease': [
            r'peripheral\s+arter(?:y|ial)\s+disease', r'\bpad\b', r'\bpaod\b',
            r'intermittent\s+claudication', r'\bclaudication\b',
            r'critical\s+limb\s+isch[ae]mia|chronic\s+limb[- ]threatening\s+isch[ae]mia',
            r'\bclti\b|\bcli\b', r'acute\s+limb\s+isch[ae]mia',
            r'ankle[- ]brachial\s+(?:index|pressure)', r'\babi\b|\babpi\b',
            r'major\s+adverse\s+limb\s+events?', r'amputation[- ]free\s+survival',
            r'limb\s+salvage', r'femoropopliteal|infrainguinal|infrapopliteal',
            r'(?:maxim(?:al|um)|pain[- ]free|absolute)\s+(?:walking|claudication)\s+'
            r'(?:distance|time)',
            r'target[- ](?:lesion|vessel)\s+revascular[is]ation', r'primary\s+patency',
            r'cilostazol|naftidrofuryl|pentoxifylline',
            r'drug[- ]coated\s+balloon|drug[- ]eluting\s+stent',
            r'lower[- ](?:limb|extremity)\s+(?:revascular[is]ation|isch[ae]mia|arter)',
        ],
        'obesity': [
            r'\bobesity\b', r'\boverweight\b', r'body\s+weight', r'weight\s+loss',
            r'weight\s+reduction', r'weight\s+management', r'anti[- ]obesity',
            r'body\s+mass\s+index|\bbmi\b', r'waist\s+circumference', r'adiposity',
            r'bariatric|sleeve\s+gastrectomy|gastric\s+bypass',
            r'(?:>=?|at\s+least\s+)\s*\d+\s*%\s+weight\s+loss',
            r'percent(?:age)?\s+(?:body\s+)?weight', r'fat\s+mass',
            r'semaglutide|liraglutide|tirzepatide|retatrutide|cagrilintide',
            r'orlistat|phentermine|naltrexone[\/ -]?bupropion|setmelanotide|lorcaserin',
        ],
        'thyroid': [
            r'\bthyroid\b', r'hypothyroid(?:ism)?', r'hyperthyroid(?:ism)?',
            r'thyrotoxicosis', r'levothyroxine|l[- ]?thyroxine|\blt4\b|liothyronine',
            r'thyroid[- ]stimulating\s+hormone|\btsh\b',
            r'free\s+(?:thyroxine|t4|triiodothyronine|t3)|\bft4\b|\bft3\b',
            r'methimazole|carbimazole|thiamazole|propylthiouracil|\bptu\b|antithyroid',
            r"graves[’']?\s+disease|graves\s+disease",
            r'radioactive\s+iodine|radioiodine', r'thyroidectomy',
            r'thyroiditis', r'euthyroid', r'goit(?:re|er)',
            r'thyroid\s+peroxidase\s+antibod|\btpoab?\b',
            r'thyroid\s+(?:function|hormone|eye\s+disease)|orbitopathy|ophthalmopathy',
            r'subclinical\s+(?:hypo|hyper)?thyroid',
        ],
        'parkinsons': [
            r'parkinson', r'\bupdrs\b|mds[- ]?updrs', r'levodopa|l[- ]?dopa',
            r'dopamine\s+agonist|dopaminergic',
            r'pramipexole|ropinirole|rotigotine|rasagiline|selegiline|safinamide',
            r'entacapone|opicapone|amantadine|istradefylline|pimavanserin',
            r'dyskinesia', r'\boff[- ]time\b|on\s+time\s+without',
            r'deep\s+brain\s+stimulation|\bdbs\b|subthalamic',
            r'levodopa[- ]carbidopa\s+intestinal\s+gel|\blcig\b',
            r'pdq[- ]?39', r'bradykinesia|motor\s+fluctuations'
        ],
        'alzheimers': [
            r'alzheimer', r'\bdementia\b', r'adas[- ]?cog', r'cdr[- ]?s[ob]b|cdr\s+sum',
            r'mild\s+cognitive\s+impairment|\bmci\b',
            r'donepezil|rivastigmine|galantamine|memantine|cholinesterase',
            r'lecanemab|aducanumab|donanemab|gantenerumab|solanezumab',
            r'anti[- ]amyloid|amyloid\s+pet|centiloid|\baria\b',
            r'\bnpi\b|neuropsychiatric\s+inventory|\bcmai\b|\bmmse\b'
        ],
        'multiple_sclerosis': [
            r'multiple\\s+sclerosis',
            r'\\brrms\\b|\\bspms\\b|\\bppms\\b',
            r'relapsing[- ]remitting',
            r'annuali[sz]ed\\s+relapse\\s+rate|\\barr\\b',
            r'\\bedss\\b|expanded\\s+disability',
            r'gadolinium[- ]enhancing|new\\s+(?:or\\s+(?:newly\\s+)?enlarging\\s+)?t2',
            r'ocrelizumab|ofatumumab|natalizumab|fingolimod|ozanimod|siponimod|glatiramer|teriflunomide|dimethyl\\s+fumarate|cladribine|interferon\\s+beta',
            r'\\bneda\\b|confirmed\\s+disability\\s+progression',
        ],
        'migraine': [
            r'migraine',
            r'\\btriptan|sumatriptan|rizatriptan|eletriptan|zolmitriptan',
            r'ubrogepant|rimegepant|zavegepant|atogepant|gepant|lasmiditan',
            r'erenumab|fremanezumab|galcanezumab|eptinezumab|anti[- ]cgrp|calcitonin\\s+gene',
            r'monthly\\s+migraine\\s+days|\\bmmd\\b|monthly\\s+headache\\s+days|\\bmhd\\b',
            r'2[- ]h(?:our|r)?\\s+pain\\s+(?:freedom|relief)|most\\s+bothersome\\s+symptom',
            r'chronic\\s+migraine|episodic\\s+migraine|onabotulinumtoxin',
            r'headache\\s+days|50\\s*%\\s+responder|midas|hit[- ]?6',
        ],
        'schizophrenia': [
            r'schizophreni|schizoaffective',
            r'\\bpanss\\b|positive\\s+and\\s+negative\\s+syndrome',
            r'antipsychotic|risperidone|olanzapine|quetiapine|aripiprazole|paliperidone|lurasidone|cariprazine|brexpiprazole|clozapine|haloperidol',
            r'\\bcgi[- ]?[si]?\\b|clinical\\s+global\\s+impression',
            r'long[- ]acting\\s+injectable|\\blai\\b|relapse\\s+prevention',
            r'negative\\s+symptoms?|treatment[- ]resistant\\s+schizophreni',
            r'psychosis|psychotic\\s+(?:symptoms|disorder|episode)',
            r'xanomeline|karxt|extrapyramidal|akathisia',
        ],
        'cirrhosis': [
            r'cirrhosis|cirrhotic',
            r'variceal\s+(?:bleed|haemorrhage|hemorrhage)|o?esophageal\s+varices|portal\s+hypertension',
            r'hepatic\s+encephalopathy|rifaximin|lactulose',
            r'hepatorenal\s+syndrome|hrs[- ]?aki?|terlipressin',
            r'refractory\s+ascites|ascites|spontaneous\s+bacterial\s+peritonitis|sbp',
            r'acute[- ]on[- ]chronic\s+liver\s+failure|aclf|transplant[- ]free\s+survival',
            r'meld|child[- ]pugh|decompensated|hvpg',
            r'carvedilol|nadolol|paracentesis|tips',
        ],
        'osteoarthritis': [
            r'osteoarthritis|\boa\b|knee\s+oa|hip\s+oa|degenerative\s+joint',
            r'\bwomac\b|western\s+ontario',
            r'intra[- ]?articular|hyaluron(?:ic|ate)|viscosupplement',
            r'omeract[- ]oarsi|oarsi\s+responder|joint[- ]space\s+width|\bjsw\b',
            r'total\s+(?:knee|hip|joint)\s+(?:replacement|arthroplasty)|\bkoos\b',
            r'naproxen|celecoxib|diclofenac|duloxetine|tanezumab',
            r'sprifermin|lorecivivint|cartilage\s+(?:thickness|volume)',
            r'pain\s+vas|visual\s+analog(?:ue)?\s+scale',
        ],
        'covid19': [
            r'covid|sars[- ]?cov[- ]?2|coronavirus\s+disease|2019[- ]ncov',
            r'nirmatrelvir|paxlovid|molnupiravir|remdesivir|ensitrelvir',
            r'hospitali[sz]ation\s+or\s+death|time\s+to\s+(?:sustained\s+)?recovery',
            r'dexamethasone\s+covid|tocilizumab|sarilumab|baricitinib',
            r'who\s+clinical\s+(?:progression|ordinal)|mechanical\s+ventilation',
            r'vaccine\s+efficacy|symptomatic\s+covid|breakthrough\s+infection',
            r'convalescent\s+plasma|casirivimab|sotrovimab|tixagevimab',
            r'viral\s+clearance|sars[- ]cov[- ]2\s+rna',
        ],
        'sepsis': [
            r'\bsepsis\b|septic\s+shock|septica?emia|sepsis[- ]associated',
            r'norepinephrine|noradrenaline|vasopressin|angiotensin\s+ii|vasopressor',
            r'\bsofa\b|sequential\s+organ\s+failure|apache\s+ii',
            r'hydrocortisone\s+(?:in\s+)?(?:sepsis|septic)|fludrocortisone|metabolic\s+resuscitation',
            r'vasopressor[- ]free\s+days|shock\s+reversal|organ[- ]support[- ]free',
            r'procalcitonin[- ]guided|source\s+control|early\s+goal[- ]directed',
            r'28[- ]day\s+mortality|90[- ]day\s+mortality',
            r'renal\s+replacement\s+therapy\s+(?:in\s+)?(?:sepsis|septic|aki)|sepsis[- ]associated\s+aki',
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
    elif best_specialty == 'ards':
        subspecialty, conf = detect_ards_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'perioperative':
        subspecialty, conf = detect_perioperative_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'chronic_pain':
        subspecialty, conf = detect_chronic_pain_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'postoperative_pain':
        subspecialty, conf = detect_postoperative_pain_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'anaemia':
        subspecialty, conf = detect_anaemia_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'itp':
        subspecialty, conf = detect_itp_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'transfusion':
        subspecialty, conf = detect_transfusion_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'allergic_rhinitis':
        subspecialty, conf = detect_allergic_rhinitis_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'urticaria':
        subspecialty, conf = detect_urticaria_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'orthopaedic':
        subspecialty, conf = detect_orthopaedic_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'low_back_pain':
        subspecialty, conf = detect_low_back_pain_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'wound_healing':
        subspecialty, conf = detect_wound_healing_subspecialty(text)
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
    elif best_specialty == 'uterine_fibroids':
        subspecialty, conf = detect_uterine_fibroids_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'benign_prostatic_hyperplasia':
        subspecialty, conf = detect_benign_prostatic_hyperplasia_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'erectile_dysfunction':
        subspecialty, conf = detect_erectile_dysfunction_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'urinary_incontinence':
        subspecialty, conf = detect_urinary_incontinence_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'oesophageal_cancer':
        subspecialty, conf = detect_oesophageal_cancer_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'prostate_cancer':
        subspecialty, conf = detect_prostate_cancer_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'ovarian_cancer':
        subspecialty, conf = detect_ovarian_cancer_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'pancreatic_cancer':
        subspecialty, conf = detect_pancreatic_cancer_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'gastric_cancer':
        subspecialty, conf = detect_gastric_cancer_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'hepatocellular_carcinoma':
        subspecialty, conf = detect_hepatocellular_carcinoma_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'melanoma':
        subspecialty, conf = detect_melanoma_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'leukaemia':
        subspecialty, conf = detect_leukaemia_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'lymphoma':
        subspecialty, conf = detect_lymphoma_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'multiple_myeloma':
        subspecialty, conf = detect_multiple_myeloma_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'head_neck_cancer':
        subspecialty, conf = detect_head_neck_cancer_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'bladder_cancer':
        subspecialty, conf = detect_bladder_cancer_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'renal_cell_carcinoma':
        subspecialty, conf = detect_renal_cell_carcinoma_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'endometriosis':
        subspecialty, conf = detect_endometriosis_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'menopause_hrt':
        subspecialty, conf = detect_menopause_hrt_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'infertility_ivf':
        subspecialty, conf = detect_infertility_ivf_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'gestational_diabetes':
        subspecialty, conf = detect_gestational_diabetes_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'diabetes':
        subspecialty, conf = detect_diabetes_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'osteoporosis':
        subspecialty, conf = detect_osteoporosis_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'kidney_transplant':
        subspecialty, conf = detect_kidney_transplant_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'pulmonary_hypertension':
        subspecialty, conf = detect_pulmonary_hypertension_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'pcos':
        subspecialty, conf = detect_pcos_subspecialty(text)
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
    elif best_specialty == 'dyslipidaemia':
        subspecialty, conf = detect_dyslipidaemia_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'venous_thromboembolism':
        subspecialty, conf = detect_venous_thromboembolism_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'peripheral_artery_disease':
        subspecialty, conf = detect_peripheral_artery_disease_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'obesity':
        subspecialty, conf = detect_obesity_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'thyroid':
        subspecialty, conf = detect_thyroid_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'parkinsons':
        subspecialty, conf = detect_parkinsons_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'alzheimers':
        subspecialty, conf = detect_alzheimers_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'multiple_sclerosis':
        subspecialty, conf = detect_multiple_sclerosis_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'migraine':
        subspecialty, conf = detect_migraine_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'schizophrenia':
        subspecialty, conf = detect_schizophrenia_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'cirrhosis':
        subspecialty, conf = detect_cirrhosis_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'osteoarthritis':
        subspecialty, conf = detect_osteoarthritis_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'covid19':
        subspecialty, conf = detect_covid19_subspecialty(text)
        confidence = max(confidence, conf)
    elif best_specialty == 'sepsis':
        subspecialty, conf = detect_sepsis_subspecialty(text)
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
