import os
import ftplib

# Helper function to read text file through an FTP connection
def readlines_ftp(handle:ftplib.FTP, filename: str) -> str:
    data = []
    handle.retrlines(f'RETR {filename}', data.append)
    return '\n'.join(data)

# Connect to FTP server and retrieve per_visit_schema
with ftplib.FTP() as ftp:
    ftp.connect(os.environ.get("FTP_HOST"))
    ftp.login(os.environ.get("FTP_USERNAME"), os.environ.get("FTP_PASSWORD"))
    ftp.cwd('schema')

    latent_db_description = readlines_ftp(ftp, 'latent_db_description.txt')
    
    # Retrieve per_visit_schema
    per_visit_schema = readlines_ftp(ftp, 'MMRF_CoMMpass_IA22_PER_PATIENT_VISIT.tsv')

    # Retrieve per_patient_schema
    per_patient_schema = readlines_ftp(ftp, 'MMRF_CoMMpass_IA22_PER_PATIENT.tsv')

    # Retrieve stand_alone_survival_schema
    stand_alone_survival_schema = readlines_ftp(ftp, 'MMRF_CoMMpass_IA22_STAND_ALONE_SURVIVAL.tsv')

    # Retrieve stand_alone_treatment_regiment_schema
    stand_alone_treatment_regiment_schema = readlines_ftp(ftp, 'MMRF_CoMMpass_IA22_STAND_ALONE_TREATMENT_REGIMEN.tsv')

    # Retrieve stand_alone_trtresp_schema
    stand_alone_trtresp_schema = readlines_ftp(ftp, 'MMRF_CoMMpass_IA22_STAND_ALONE_TRTRESP.tsv')

    # Retrieve exome_ns_variants_schema
    exome_ns_variants_schema = readlines_ftp(ftp, 'MMRF_CoMMpass_IA22_exome_vcfmerger2_IGV_All_Canonical_NS_Variants.txt')

    # Retrieve chromothripsis_schema
    chromothripsis_schema = readlines_ftp(ftp, 'chromoth_categorical_df_pval0.05.tsv')

    # Retrieve gep_scores_schema
    gep_scores_schema = readlines_ftp(ftp, 'commpass_gep_risk_scores.csv')

    # Retrieve mutsig_sbs_schema
    mutsig_sbs_schema = readlines_ftp(ftp, 'mutsig_sbs_schema.tsv')

# Create a description for the tables in the database
db_description = latent_db_description.format(
    per_patient_schema=per_patient_schema,
    per_visit_schema=per_visit_schema,
    stand_alone_survival_schema=stand_alone_survival_schema,
    stand_alone_treatment_regiment_schema=stand_alone_treatment_regiment_schema,
    stand_alone_trtresp_schema=stand_alone_trtresp_schema,
    exome_ns_variants_schema=exome_ns_variants_schema,
    chromothripsis_schema=chromothripsis_schema,
    gep_scores_schema=gep_scores_schema,
    mutsig_sbs_schema=mutsig_sbs_schema
)