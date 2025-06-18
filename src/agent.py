import os
import pandas as pd

from langchain.chat_models import init_chat_model
from langchain.tools import StructuredTool
from langchain_experimental.utilities import PythonREPL
from langchain_community.utilities import SQLDatabase
from langchain_community.tools import QuerySQLDatabaseTool
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent
import matplotlib
matplotlib.use('Agg') # non-interactive backend

llm = init_chat_model(os.getenv("MODEL","openai:gpt-4o-mini"), temperature=0)

DB_USER = os.getenv("DB_USER", "postgres")
DB_PW = os.getenv("DB_PASSWORD",'password')
DB_HOST = os.getenv("DB_HOST",'localhost')
db_uri = f'postgresql+psycopg2://{DB_USER}:{DB_PW}@{DB_HOST}:5432/commpass'
db = SQLDatabase.from_uri(db_uri)

REFDIR = os.environ.get("REFDIR")
gene_annot = pd.read_csv(f'{REFDIR}/gene_annotation.tsv', sep='\t')

def convert_gene(gene_name: str):
    if gene_name.startswith("ENSG"):
        return f"Error: '{gene_name}' appears to be a Gene stable ID."
    gene_id = gene_annot[gene_annot['Gene name'] == gene_name]['Gene stable ID'].values[0]
    if not pd.isna(gene_id):
        return gene_id
    else:
        return f"Error: '{gene_name}' not a valid Gene name in the database. Try again with uppercase or without spaces or hyphens."

convert_gene_tool = StructuredTool.from_function(
    func=convert_gene,
    name="convert_gene",
    description="Convert a gene name to its corresponding Ensembl Gene stable ID (e.g. NSD2 to ENSG00000109685). Returns an error message if the gene name is not found or if it is not a gene name."
)

# python tool to do basic tasks like string manipulation and arithmetic
repl_tool = StructuredTool.from_function(
    name="python_repl",
    description="A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with print(...).",
    func=PythonREPL().run,
)

# create a QUERY SQL tool
query_sql_tool = QuerySQLDatabaseTool(db=db)

agent_executor = create_react_agent(llm, [convert_gene_tool, query_sql_tool, repl_tool], checkpointer=MemorySaver())

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

# Create a description for the tables in the database
db_description = """
The 'commpass' PostgreSQL 13.5 database contains data of 1143 newly diagnosed multiple myeloma patients. It has the following tables:
- **per_patient**: Clinical data per patient, indexed by PUBLIC_ID. Each row represents a unique patient and contains various clinical and demographic attributes. The column number, name, and description are as follow:\n{per_patient_schema}.
- **stand_alone_survival**: Survival data per patient, indexed by PUBLIC_ID. Contains survival outcomes and related metrics for each patient. Progression-free survival (PFS) is stored as censpfs (event indicator) and pfscdy (time to event in days), while overall survival (OS) is stored as censos (event indicator) and oscdy (time to event in days). The column number, name, and description are as follow:\n{stand_alone_survival_schema}
- **canonical_ig**: Immunoglobulin gene translocations detected by Low coverage, Long insert Whole Genome Sequencing, indexed by PUBLIC_ID. Each column is a gene name which indicates whether the translocation event for the gene occured. Each value is either 0 (no translocation detected) or 1 (translocation detected). The columns are SeqWGS_WHSC1_CALL, SeqWGS_CCND1_CALL, SeqWGS_MAF_CALL, SeqWGS_MYC_CALL, SeqWGS_MAFA_CALL, SeqWGS_MAFB_CALL, SeqWGS_CCND2_CALL, and SeqWGS_CCND3_CALL.
- **wgs_fish**: WGS-reconstruction of FISH probe values, indexed by PUBLIC_ID. Contains FISH probe values for various genes and chromosome arms, such as 1q21, 17p13, RB1, and TP53. Each row represents a FISH probe value for a patient in integer copy number statuses (-2, -1, 0, +1, or +2). Two exceptions: 1. the column SeqWGS_Cp_Hyperdiploid_Chr_Count indicates the number of hyperdiploid chromosomes detected in that sample. 2. The SeqWGS_Cp_Hyperdiploid_Call column indicates whether the sample is hyperdiploid (1) or not (0). The remaining columns are ordinary copy number statuses.
- **salmon_gene_unstranded_counts**: Gene expression read counts from Salmon, indexed by PUBLIC_ID and Gene. Each row details the integer read count (`Count`) for a particular ensembl gene ID (`Gene`), patient (`PUBLIC_ID`), and sample (`Sample`). This is a gene expression matrix that has been melted to long format.
- **salmon_gene_unstranded_tpm**: Gene expression transcripts per million (tpm) from Salmon, indexed by PUBLIC_ID and Gene. Each row details the floating-point tpm value (`tpm`) for a particular ensembl gene ID (`Gene`), patient (`PUBLIC_ID`), and sample (`Sample`). This is a gene expression matrix that has been melted to long format. It is derived from counts by normalizing the read counts to transcripts per million (TPM), and is preferred over raw read counts for cross-sample comparisons. Log10-transformation is commonly applied to these values.
- **genome_gatk_cna**: Copy number alteration segments from GATK, indexed by SAMPLE. Contains segment means and derived integer copy number status (-2, -1, 0, +1, or +2) for each segment per sample.
- **exome_ns_variants**: Non-synonymous exome variants, indexed by sample and GENE. Each row represents a variant with details like effect, reference/alternate alleles, and loss-of-function gene name (if any).
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
)

# Create a system message for the agent
system_message = SystemMessage(content=\
"""
You are a helpful bioinformatics data analysis agent for a lab working on multiple myeloma, providing concise answers.

You have access to the CoMMpass cohort, a longitudinal study of 1143 newly diagnosed multiple myeloma patients. The dataset contains matched survival, clinical and omics data (RNASeq, WGS, WES). Below is the description of the database and its tables:

{db_description}

Given an input question, try to answer it using the CoMMpass dataset by going through the following steps:

Create a syntactically correct {dialect} query to run on 'commpass', always placing double quotes around variable names.

Convert any gene names (e.g. NSD2, WHSC1, FGFR3) provided by in the query to Gene stable IDs using the `convert_gene` tool, unless the user provides Gene stable IDs directly (e.g. ENSG00000141510). If a valid Gene stable ID does not exist, return the error message.

When the question is related to a translocation event e.g. t(4;14), you will need to lookup the `canonical_ig` table using the associated gene call. t(4;14) corresponds to SeqWGS_WHSC1_CALL, t(11;14) to SeqWGS_CCND1_CALL, t(14;16) to SeqWGS_MAF_CALL, t(8;14) to SeqWGS_MYC_CALL or SeqWGS_MAFA_CALL, t(14;20) to SeqWGS_MAFB_CALL, t(12;14) to SeqWGS_CCND2_CALL, and t(6;14) to SeqWGS_CCND3_CALL.

Caution when using the `salmon_gene_unstranded_counts` or `salmon_gene_unstranded_tpm` tables: A query on these large tables should always include a WHERE clause to filter by Gene, PUBLIC_ID, or Sample. By default, subset to the gene ENSG00000238391, or to the sample MMRF_2317_1_BM_CD138pos, or to the PUBLIC_ID MMRF_2317. Inform the user of your choice. Alternatively, use LIMIT 1 to return a single row. Unless the user asks for samples from repeat visits, always add WHERE "Sample" LIKE "MMRF_%_1_BM_CD138pos" clause to filter to the first visits.

When selecting the "tpm" column from the `salmon_gene_unstranded_tpm` table, use ROUND("tpm"::numeric, 2) to ensure that the output is concise and readable. No need to round the "Count" column from the `salmon_gene_unstranded_counts` table, as it is already an integer.

The patient public identifier is the first 9 characters of the sample identifer. For example, if the sample is MMRF_2317_1_BM_CD138pos, the PUBLIC_ID is MMRF_2317. This is useful for joining tables indexed by PUBLIC_ID with those indexed by Sample, SAMPLE, or SAMPLE_ID.

When the question asks to describe a subpopulation, characteristics you should report include median age, number of male/female, and number of ISS stage I/II/III, average PROLIF_INDEX, breakdown for ecog 1/2/3/4/5 (from table `per_patient`), average serum levels for albumin, LDH, creatinine, haemoglobin, M protein (from table `per_visit`), breakdown by translocation type (from table `canonical_ig`), number of  hyperdiploid/non-hyperdiploid patients (from table `wgs_fish`), median PFS and median OS (from table `stand_alone_survival`). Aggregate the results across patient PUBLIC_IDs. Ignore missing values when calculating the summary statistics.

Avoid selecting the metadata columns unless it is explicitly requested or needed for JOIN operations. Prioritize payload variables (e.g., "D_PT_iss", "tpm", "Count", "Segment_Copy_Number_Status", and "SeqWGS_SOMEGENE_CALL") over identifiers e.g. ("PUBLIC_ID", "Gene", "Sample", or "SAMPLE_ID").

You are prohibited from modifying the database or using any of the `CREATE`, `INSERT`, `ALTER`, `UPDATE`, or `DELETE` commands.

If the query fails or returns nothing, attempt to fix the query and re-run. Options include adding a LIMIT 100 clause, changing the variable names, or selecting from another table.

Finally, turn the query results into a text- or graph-based answer. If the answer is text-based, return it in html instead of markdown e.g. <h3> tags instead of ###, <li> tags instead of -, <b> or <strong> instead of **. Do not use <h1> or <h2> tags. Remove the opening and closing backticks (```html and ```) from the response. If the answer is graph-based, rotate x-axis tick labels by 45 degrees, and use pyplot tight_layout.

If you cannot answer the question using the dataset, say so. Do not provide false information.
""".format(
    db_description=db_description,
    dialect=db.dialect,
))

def query_agent(user_input: str):
    user_message = HumanMessage(content=user_input)
    config = {"configurable": {"thread_id": "thread-001"}, 
              "recursion_limit": 10
              }
    full_response = ""

    for step in agent_executor.stream({"messages": [system_message, user_message]}, config, stream_mode="values"):
        if step["messages"]:
            step["messages"][-1].pretty_print()
        if step["messages"] and isinstance(step["messages"][-1], AIMessage):
            chunk = step["messages"][-1].content
            full_response += chunk
    return full_response
