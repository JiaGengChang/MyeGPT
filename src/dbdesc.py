import os

# Read the schema files of the clinical tables
SCHEMADIR = os.environ.get("SCHEMADIR")
with open(f"{SCHEMADIR}/MMRF_CoMMpass_IA22_PER_PATIENT_VISIT.tsv", "r") as f:
    per_visit_schema = f.read()
with open(f"{SCHEMADIR}/MMRF_CoMMpass_IA22_PER_PATIENT.tsv", "r") as f:
    per_patient_schema = f.read()
with open(f"{SCHEMADIR}/MMRF_CoMMpass_IA22_STAND_ALONE_SURVIVAL.tsv", "r") as f:
    stand_alone_survival_schema = f.read()
with open(f"{SCHEMADIR}/MMRF_CoMMpass_IA22_STAND_ALONE_TREATMENT_REGIMEN.tsv", "r") as f:
    stand_alone_treatment_regiment_schema = f.read()
with open(f"{SCHEMADIR}/MMRF_CoMMpass_IA22_STAND_ALONE_TRTRESP.tsv", "r") as f:
    stand_alone_trtresp_schema = f.read()
with open(f"{SCHEMADIR}/MMRF_CoMMpass_IA22_exome_vcfmerger2_IGV_All_Canonical_NS_Variants.txt", "r") as f:
    exome_ns_variants_schema = f.read()
with open(f"{SCHEMADIR}/chromoth_categorical_df_pval0.05.tsv","r") as f:
    chromothripsis_schema = f.read()
with open(f"{SCHEMADIR}/commpass_gep_risk_scores.csv","r") as f:
    gep_scores_schema = f.read()
with open(f"{SCHEMADIR}/mutsig_sbs_schema.tsv","r") as f:
    mutsig_sbs_schema = f.read()    

# Create a description for the tables in the database
db_description = """
The 'commpass' PostgreSQL 13.5 database contains data of 1143 newly diagnosed multiple myeloma patients. It has the following tables:
- **per_patient**: Clinical data per patient, indexed by PUBLIC_ID. Each row represents a unique patient and contains various clinical and demographic attributes. The column number, name, and description are as follow:\n{per_patient_schema}.
- **stand_alone_survival**: Survival data per patient, indexed by PUBLIC_ID. Contains survival outcomes and related metrics for each patient. Progression-free survival (PFS) is stored as censpfs (event indicator) and pfscdy (time to event in days), while overall survival (OS) is stored as censos (event indicator) and oscdy (time to event in days). The column number, name, and description are as follow:\n{stand_alone_survival_schema}
- **canonical_ig**: Immunoglobulin gene translocations detected by Low coverage, Long insert Whole Genome Sequencing, indexed by PUBLIC_ID. Each column is a gene name which indicates whether the translocation event for the gene occured. Each value is either 0 (no translocation detected) or 1 (translocation detected). The columns are SeqWGS_WHSC1_CALL, SeqWGS_CCND1_CALL, SeqWGS_MAF_CALL, SeqWGS_MYC_CALL, SeqWGS_MAFA_CALL, SeqWGS_MAFB_CALL, SeqWGS_CCND2_CALL, and SeqWGS_CCND3_CALL.
- **wgs_fish**: WGS-reconstruction of FISH probe values, indexed by PUBLIC_ID. Contains FISH probe values for various genes and chromosome arms, such as 1q21, 17p13, RB1, and TP53. Rows starting with SeqWGS_Cp represents a FISH probe value for a patient in integer copy number statuses (-2, -1, 0, +1, or +2), with 2 exceptions: 1. SeqWGS_Cp_Hyperdiploid_Chr_Count indicates the number of hyperdiploid chromosomes detected in that sample. 2. SeqWGS_Cp_Hyperdiploid_Call column indicates whether the sample is hyperdiploid (1) or not (0). The remaining columns are ordinary copy number statuses. Rows starting with SeqWGS_SegmentMean represent the mean log ratio of the probe values.
- **salmon_gene_unstranded_counts**: Gene expression read counts from Salmon, indexed by PUBLIC_ID and Gene. Each row details the integer read count (`Count`) for a particular ensembl gene ID (`Gene`), patient (`PUBLIC_ID`), and sample (`Sample`). This is a gene expression matrix that has been melted to long format.
- **salmon_gene_unstranded_tpm**: Gene expression transcripts per million (tpm) from Salmon, indexed by PUBLIC_ID and Gene. Each row details the floating-point tpm value (`tpm`) for a particular ensembl gene ID (`Gene`), patient (`PUBLIC_ID`), and sample (`Sample`). This is a gene expression matrix that has been melted to long format. It is derived from counts by normalizing the read counts to transcripts per million (TPM), and is preferred over raw read counts for cross-sample comparisons. Log10-transformation is commonly applied to these values.
- **genome_gatk_cna**: Copy number alteration segments from GATK, indexed by SAMPLE. The Segment_Mean column indicates raw mean log ratios of each probe, and Segment_Copy_Number column indicates the derived integer copy number status (-2, -1, 0, +1, or +2) for the probe.
- **exome_ns_variants**: Non-synonymous exome variants, indexed by Ensemble stable ID "GENEID" and patient identifier "PUBLIC_ID". The column number, name, and description are as follow:\n{exome_ns_variants_schema}
- **chromothripsis**: Occurrence of chromothripsis events indexed by PUBLIC_ID. Events were detected using ShatterSeek algorithm run on copy number and structural variation data. The column number, name, and description are as follow:\n{chromothripsis_schema}
- **gep_scores**: Gene expression profiling risk scores, also known as GEP risk indices or GEP signatures, indexed by PUBLIC_ID. The column number, name, and description are as follow:\n {gep_scores_schema}
- **mutsig_sbs**: Mutational signatures for Single Base Substitutions (SBS), indexed by PUBLIC_ID. Signatures were extracted using SigProfiler. The column number, name, and description are as follow:\n{mutsig_sbs_schema}
- **per_visit**: Clinical data per patient visit, indexed by PUBLIC_ID. Each row represents a visit for a patient, with visit-specific clinical details. The column number, name, and description are as follow:\n{per_visit_schema}
- **stand_alone_trtresp**: Treatment response data per patient, indexed by PUBLIC_ID. Contains information about patient responses to treatments. The column number, name, and description are as follow:\n{stand_alone_trtresp_schema}
- **stand_alone_treatment_regimen**: Treatment regimen data per patient, indexed by PUBLIC_ID. Each row details the treatment regiment administered to a patient in that step of treatment. The column number, name, and description are as follow:\n{stand_alone_treatment_regiment_schema}
- **gene_annotation**: Gene annotation reference, indexed by Gene stable ID and Gene name. Contains gene metadata such as ensembl IDs and names.
All tables are based on CoMMpass Interim Analysis 22 (IA22), except for `canonical_ig` which is based on IA16 and `gene annotation` table which comes from Ensembl. The actual data can be obtained from https://research.themmrf.org/.
""".format(
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