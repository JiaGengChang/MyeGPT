import os
from dotenv import load_dotenv
import re
import uuid
import psycopg
import pandas as pd
from langchain.tools import StructuredTool
from langchain_experimental.tools import PythonAstREPLTool
from langchain_community.utilities import SQLDatabase
from langchain_community.tools import QuerySQLDatabaseTool

from vectorstore import connect_store

filedir = os.path.dirname(os.path.abspath(__file__))

gene_annot = pd.read_csv(f'{filedir}/../refdata/gene_annotation.tsv', sep='\t', dtype={'Chromosome/scaffold name':'str'})

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
    name="convert_gene_name_to_accession",
    description="Convert a gene name to its corresponding GENCODE accession aka Ensembl Gene stable ID (e.g. from NSD2 to ENSG00000109685). Returns an error message if the gene name is not found or if it is not a gene name."
)

def gene_metadata(gene_id: str):
    if not gene_id.startswith("ENSG"):
        return f"Error: '{gene_id}' does not appear to be a valid Gene stable ID."
    gene_info = gene_annot[gene_annot['Gene stable ID'] == gene_id]
    if not gene_info.empty:
        info_dict = gene_info.iloc[0].to_dict()
        return f"Gene Metadata for {gene_id}:\n" + "\n".join([f"{key}: {value}" for key, value in info_dict.items()])
    else:
        return f"Error: '{gene_id}' not found in the gene annotation database."
    
gene_metadata_tool = StructuredTool.from_function(
    func=gene_metadata,
    name="get_gene_metadata",
    description="Retrieve the metadata for a given GENCODE accession aka Ensembl Gene stable ID (e.g. ENSG00000109685). Returns an error message if the gene ID is not found or invalid. The fields returned are: Chromosome/scaffold name, Gene start (bp), Gene end (bp), Strand, Gene description, Gene name, Gene type"
)

def execute_sql_query_with_python(query: str):
    conn = psycopg.connect(os.environ.get("COMMPASS_DSN"))
    with conn.cursor() as curs:
        curs.execute(re.sub(r'LIMIT \d+', '', query, flags=re.IGNORECASE))
        result = curs.fetchall()
        df = pd.DataFrame(result, columns=[desc[0] for desc in curs.description])
        conn.close()
    if not df.empty:
        result_csv_filename = f"result/result_{uuid.uuid4().hex[:8]}.csv"
        df.to_csv(result_csv_filename, index=False)
        return f"Query results saved to output file {result_csv_filename}."
    else:
        return "Query returned no results. No output file created."

python_execute_sql_query_tool = StructuredTool.from_function(
    func=execute_sql_query_with_python,
    name="execute_full_sql_query_with_python",
    description="Executes the full SQL query using python without the trial-run LIMIT clause and saves the results to disk. Useful for downstream analysis for visualization etc."
)

# python tool to do basic tasks like string manipulation and arithmetic
python_repl_tool = PythonAstREPLTool()

# create a QUERY SQL tool
db_uri = os.environ.get("COMMPASS_DB_URI")
db = SQLDatabase.from_uri(db_uri)
langchain_query_sql_tool = QuerySQLDatabaseTool(db=db)

# similarity search against our vector store
def document_search(query: str, k:int = 1):
    # establish connection to postgres vector store
    store = connect_store()
    results = store.similarity_search(query, k=k)
    if results:
        return f"""The top {k} table(s) with the best match:
        <div class="scrollable lightaccent codeblock">{[doc.page_content for doc in results]}</div>
        """
    else:
        return "No tables with relevant fields found"

# tool to search for relevant database documents
document_search_tool = StructuredTool.from_function(
    func=document_search,
    name="document_search",
    description="Returns the reference manual of top K tables most relevant to the query. The query should only involve one subject, such as survival data, gene expression data, or copy number data - do not mix multiple concepts at once."
)

def generate_graph_filepath() -> str:
    plot_file_path = f"graph/graph_{uuid.uuid4().hex[:8]}.png"
    return plot_file_path

generate_graph_filepath_tool = StructuredTool.from_function(
    func=generate_graph_filepath,
    name="generate_graph_filepath",
    description="Generates a unique file path to save the plot image in PNG format."
)

def display_plot_html(file_path: str) -> str:
    if not os.path.exists(file_path):
        return f"Error: Path for PNG file {file_path} does not exist. Rename the newly generated PNG to {file_path}, or re-generate and save to {file_path}."
    else:
        html = f"""
        <div class=image-container>
            <img src={file_path} width=100% height=auto>
            <div class=links-container>
                <a href={file_path} download>Download</a>
                <a href={file_path} target=_blank rel=noopener noreferrer>New tab</a>
            </div>
        </div>
        """
        return html.replace('\n', '')

# tool to plot image
display_plot_tool = StructuredTool.from_function(
    func=display_plot_html,
    name="display_plot_html",
    description="Display the plot image saved at the given file path as HTML output. Arguments: file_path (str). If file path does not exist, an error message is returned. Thus, the plot must first be saved as file_path before this plot tool is called."
)

def _max_overlapping_segment(gene_stable_id: str):
    import os
    import psycopg
    import pandas as pd
    # disable SettingWithCopyWarning
    pd.options.mode.chained_assignment = None  # default='warn'

    global gene_annot

    gene_of_interest_annot = gene_annot[gene_annot['Gene stable ID'] == gene_stable_id].iloc[0]

    gc = 'chr' + str(gene_of_interest_annot['Chromosome/scaffold name'])
    gs = int(gene_of_interest_annot['Gene start (bp)'])
    ge = int(gene_of_interest_annot['Gene end (bp)'])

    # sort by overlap length between probe and gene
    #  PROBE =====1    |     =====2 |  =====3         |           ====4  |     ===5       |  ==========6
    #  GENES   =====1  |  =====2    |          ====3  |  =====4          |  ===========5. |.    ====6
    conn = psycopg.connect(os.environ.get("COMMPASS_DSN"))
    with conn.cursor() as curs:
        curs.execute('SELECT * FROM genome_gatk_cna WHERE chromosome = %s', (gc,))
        result = curs.fetchall()
        cn_chrom = pd.DataFrame(result, columns=[desc[0] for desc in curs.description])
        curs.execute('SELECT * FROM genome_gatk_cna WHERE chromosome = %s AND start_pos < %s AND end_pos > %s AND end_pos < %s', (gc,gs,gs,ge))
        result = curs.fetchall()
        df_case1 = pd.DataFrame(result, columns=[desc[0] for desc in curs.description])
        curs.execute('SELECT * FROM genome_gatk_cna WHERE chromosome = %s AND start_pos > %s AND start_pos < %s AND end_pos > %s', (gc,gs,ge,ge))
        result = curs.fetchall()
        df_case2 = pd.DataFrame(result, columns=[desc[0] for desc in curs.description])
        curs.execute('SELECT * FROM genome_gatk_cna WHERE chromosome = %s AND end_pos < %s', (gc,gs))
        result = curs.fetchall()
        df_case3 = pd.DataFrame(result, columns=[desc[0] for desc in curs.description])
        curs.execute('SELECT * FROM genome_gatk_cna WHERE chromosome = %s AND start_pos > %s', (gc,ge))
        result = curs.fetchall()
        df_case4 = pd.DataFrame(result, columns=[desc[0] for desc in curs.description])        
        curs.execute('SELECT * FROM genome_gatk_cna WHERE chromosome = %s AND start_pos > %s AND end_pos < %s', (gc,gs,ge))
        result = curs.fetchall()
        df_case5 = pd.DataFrame(result, columns=[desc[0] for desc in curs.description])
        curs.execute('SELECT * FROM genome_gatk_cna WHERE chromosome = %s AND start_pos < %s AND end_pos > %s', (gc,gs,ge))
        result = curs.fetchall()
        df_case6 = pd.DataFrame(result, columns=[desc[0] for desc in curs.description])
        conn.close()

        # cases 1 to 6 should be all inclusive
        assert len(df_case1) + len(df_case2) + len(df_case3) + len(df_case4) + len(df_case5) + len(df_case6) == len(cn_chrom)

        # calculate overlap lengths
        df_case1.loc[:,'overlap_len'] = df_case1['end_pos'] - gs + 1
        df_case2.loc[:,'overlap_len'] = ge - df_case2['start_pos'] + 1
        df_case5.loc[:,'overlap_len'] = df_case5['end_pos'] - df_case5['start_pos'] + 1
        df_case6.loc[:,'overlap_len'] = ge - gs + 1

        df_overlaps = pd.concat([df for df in [df_case1, df_case2, df_case5, df_case6] if len(df)], ignore_index=True)
        # in case of a tie between overlap lengths, choose the one with higher Num_Probes value
        df_max_overlaps_max_probes = df_overlaps.groupby('sample').apply(lambda x: x.sort_values(by=['overlap_len','num_probes'], ascending=False).head(n=1),include_groups=False)
        ans_df = df_max_overlaps_max_probes.reset_index()
        ans_df.loc[:, 'public_id'] = ans_df['sample'].str.extract(r'(MMRF_[0-9]+)_')[0]
        assert not ans_df[ans_df.index.duplicated()].any().any()
        # drop level_1 column generated by groupby apply
        ans_df = ans_df.set_index(['public_id']).drop(columns=['level_1'])
        return ans_df

def max_overlapping_segment(gene_stable_id: str):
    ans_df = _max_overlapping_segment(gene_stable_id)
    # index [public_id] 
    # MMRF_1016	
    # values [sample	chromosome	start_pos	end_pos	num_probes	segment_mean	visit	segment_copy_number_status	overlap_len]
    # MMRF_1016_1_BM_CD138pos	chr1	149053976	155975058	700	0.499688	1	1	46319
    csv_path = f'result/gene_level_copy_number_{gene_stable_id}.csv'
    ans_df.to_csv(csv_path)
    return f"Result saved to {csv_path}"
    
gene_level_copy_number_tool = StructuredTool.from_function(
    func=max_overlapping_segment,
    name="get_gene_level_copy_number_data",
    description="Retrieve the gene-level copy number data for a given GENCODE accession aka Ensembl Gene stable ID. Returns the path to a csv file of a pandas dataframe with index as public_id, columns as sample, chromosome, start_pos, end_pos, num_probes, segment_mean, visit, segment_copy_number_status, and overlap_len. The variables related to copy number are 1. segment_mean, which is the log2 fold-change of the probe, and 2. segment_copy_number_status, which is the categorical copy number status (-2, -1, 0, +1, or +2). Example input: ENSG00000143621, example output: public_id=MMRF_1016, sample=MMRF_1016_1_BM_CD138pos, chromosome=chr1, start_pos=149053976, end_pos=155975058, num_probes=700, segment_mean=0.499688, visit=1, segment_copy_number_status=1, overlap_len=46319."
)

def get_cox_regression_base_data(endpoint='os'):
    # input: endpoint: 'os' or 'pfs' 
    # output: None except printed statement
    # behavior: 
    # saves a template dataset for Cox PH regression analysis to result/cox_dataset_template_{endpoint}.csv
    # this csv file contains PUBLIC ID, survival time, censoring status, age, ISS (I, II, III), and gender (Male, Female)
    # ... which are the common covariates used in Cox PH regression with variable of interest
    # create the datase only if not already exists
    if not os.path.exists(f'result/cox_dataset_template_{endpoint}.csv'):
        conn = psycopg.connect(os.environ.get("COMMPASS_DSN"))
        with conn.cursor() as curs:
            if endpoint == 'os':
                curs.execute(f'SELECT PUBLIC_ID, oscdy, censos FROM stand_alone_survival WHERE censos is not null')
            elif endpoint == 'pfs':
                curs.execute(f'SELECT PUBLIC_ID, pfscdy, censpfs FROM stand_alone_survival WHERE censpfs is not null')
            else:
                raise ValueError('endpoint must be either \"os\" or \"pfs\"')
            result = curs.fetchall()
            df_surv = pd.DataFrame(result, columns=['PUBLIC_ID', endpoint+'cdy', 'cens'+endpoint])
            curs.execute('SELECT PUBLIC_ID, D_PT_age, D_PT_gender, D_PT_iss FROM per_patient')
            result = curs.fetchall()
            df_clin = pd.DataFrame(result, columns=['PUBLIC_ID', 'D_PT_age', 'D_PT_gender', 'D_PT_iss'])
            df_clin['D_PT_gender'] = df_clin['D_PT_gender'].map({1: 'Male',2: 'Female'})
            df_clin['D_PT_iss'] = df_clin['D_PT_iss'].map({1: 'I',2: 'II', 3: 'III'})
            df_clin['D_PT_gender'] = df_clin['D_PT_gender'].astype(pd.CategoricalDtype())
            df_clin['D_PT_iss'] = df_clin['D_PT_iss'].astype(pd.CategoricalDtype())
            df_cph_template = df_surv.merge(df_clin, on='PUBLIC_ID')
            df_cph_template.to_csv(f'result/cox_ph_covariates_{endpoint}.csv', index=False)

    # Already pre-generated to save
    return f'Saved template dataset containing PUBLIC ID, {endpoint}, age, ISS, gender columns to result/cox_ph_covariates_{endpoint}.csv'

cox_regression_base_data_tool = StructuredTool.from_function(
    func=get_cox_regression_base_data,
    name="get_cox_regression_base_data",
    description="""
    Retrieve a template dataset for Cox PH regression analysis for a given endpoint ('os' or 'pfs'). Returns the path to a csv file containing PUBLIC ID, survival time, censoring status, age, ISS, and gender columns. 
    Example input: os
    Example output: result/cox_ph_covariates_os.csv
    Use scenario: When the user requests for survival regression of their feature of interest alongside common covariates like age, sex, and ISS, call this function to obtain the table for age, sex, ISS, and the right-censored survival data. You can then merge their feature(s) of interest with this table."""
)

def uni_cox_expr_log2tpm(endpoint:str) -> None:
    # input: endpoint: 'os' or 'pfs' 
    # output: None except printed statement
    # behavior: returns the path to the pre-computed Cox PH regression results
    endpoint = endpoint.lower()
    if endpoint not in ['os','pfs']:
        raise ValueError('endpoint must be either \"os\" or \"pfs\"')
    result_file = 'result/cox_ph_os_56294_genes.csv' if endpoint == 'os' else 'result/cox_ph_pfs_56317_genes.csv'
    if not os.path.exists(result_file):
        raise FileNotFoundError(f'Gene-wise Cox PH regression results for endpoint {endpoint} not found.')
    print(f'Path to gene-wise CoxPH summary statistics for {endpoint} endpoint: {result_file}')

coxph_stats_log2tpm_expr_tool = StructuredTool.from_function(
    func=uni_cox_expr_log2tpm,
    name="gene_expr_coxph_statistics",
    description="""
    Retrieve the path to pre-computed Cox PH regression results for a given endpoint ('os' or 'pfs'). 
    Returns the path to a csv file containing columns gene, coef, exp(coef), se(coef), z, p, lower95, upper95, n, q, neglog10q
    The analysis performed is Cox PH regression based on z-score of log2 (tpm+1) expression values of all genes.
    Age, sex, and ISS are used as covariates, besides the gene of interest.
    Samples are first-visit, bone marrow plasma cell in nature (visit ID = 1, tissue type BM, CD138pos).
    Example input: os
    Example output: Path to gene-wise CoxPH summary statistics for os endpoint: __path__to_result__file__
    Note: some genes do not have regression values, CoxPH only around 56,000 out of 60,000 genes in GRCh38.
    Suitable for: User wants to filter a long list of genes down to those relevant to survival outcomes.
    Suitable for: User wants to measure whether upregulation or downregulation of a gene is associated with better or worse survival outcomes -> look at whether hazard ratio is >1 or <1.
    Not suitable for: User wants to measure the effect of their gene of interest on survival while adjusting for other covariates apart from age, sex, and ISS -> Suggest using cox_regression_base_data_tool to get the base dataset and then merge their feature(s) of interest for CoxPH regression.
    Not suitable for: analysis on certain subpopulations, as summary statistics are based on the entire cohort.
    """
)

def mad_expr_log2tpm():
    # input: none
    # output: None except printed statement
    # behavior: returns the path to the pre-computed median and MAD of log2(tpm+1) expression values
    result_file = 'result/gene_log2tpm_mad.csv'
    if not os.path.exists(result_file):
        raise FileNotFoundError('Pre-computed gene MAD results not found.')
    print(f'Path to gene-wise median and MAD of log2(tpm+1) expression values: {result_file}')

mad_log2tpm_expr_tool = StructuredTool.from_function(
    func=mad_expr_log2tpm,
    name="gene_expr_mad_values",
    description="""
    Retrieve the path to pre-computed median and median absolute deviation (MAD) of log2(tpm+1)-transformed gene expression.
    Returns the path to a csv file containing columns Ensembl gene ID, median log2(tpm+1), and MAD log2(tpm+1).
    This contains all GrCh38 genes with expression data.
    Suitable for: User wants to filter or order genes based on expression variability across the cohort.
    Suitable for: User wants to check if a subpopulation has higher or lower expression compared to the cohort median.
    Not suitable for: evaluating differential expression between conditions. This is cohort-wide summary statistics.
    Not suitable for: retrieving median or MAD of certain subpopulations. Values here are based on the entire cohort.
    """
)