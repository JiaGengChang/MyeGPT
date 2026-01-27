import os
import re
import uuid
import psycopg
import pandas as pd
from typing import Optional
from langchain.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun

from vectorstore import connect_store

filedir = os.path.dirname(os.path.abspath(__file__))

gene_annot = pd.read_csv(f'{filedir}/../refdata/gene_annotation.tsv', sep='\t', dtype={'Chromosome/scaffold name':'str'})

class ConvertGeneTool(BaseTool):
    name:str = "convert_gene_name_to_accession"
    description: str = (
        "Convert a gene name to its corresponding GENCODE accession"
        "aka Ensembl Gene stable ID (e.g. from NSD2 to ENSG00000109685)."
        "Returns an error message if the gene name is not found"
        "or if it is not a gene name." 
        "This tool is not suitable for handling multiple genes at once" 
        "Run SQL query on the `gene_annotation` table instead for converting multiple genes."
    )
    gene_annot: pd.DataFrame = gene_annot

    def _convert_gene(self, gene_name: str):
        if gene_name.startswith("ENSG"):
            return f"Error: '{gene_name}' appears to be a Gene stable ID."
        gene_id = self.gene_annot[self.gene_annot['Gene name'] == gene_name]['Gene stable ID'].values[0]
        if not pd.isna(gene_id):
            return gene_id
        else:
            return f"Error: '{gene_name}' not a valid Gene name in the database. Try again with uppercase or without spaces or hyphens."

    def _run(
            self,
            query: str,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        """Use the tool."""
        return self._convert_gene(query)


class GeneMetadataTool(BaseTool):
    name: str = "get_gene_metadata"
    description: str = (
        "Retrieve the metadata for a given GENCODE accession aka Ensembl Gene stable ID (e.g. ENSG00000109685). "
        "Returns an error message if the gene ID is not found or invalid. "
        "The fields returned are: "
        "Chromosome/scaffold name, Gene start (bp), Gene end (bp), Strand, Gene description, Gene name, Gene type"
        "This tool is not suitable for handling multiple genes at once" 
        "Use SQL query tool on the `hgnc_nomenclature` table instead for converting multiple genes."        
    )
    gene_annot: pd.DataFrame = gene_annot

    def _get_metadata(self, gene_id: str):
        if not gene_id.startswith("ENSG"):
            return f"Error: '{gene_id}' does not appear to be a valid Gene stable ID."
        gene_info = self.gene_annot[self.gene_annot['Gene stable ID'] == gene_id]
        if not gene_info.empty:
            info_dict = gene_info.iloc[0].to_dict()
            return f"Gene Metadata for {gene_id}:\n" + "\n".join([f"{key}: {value}" for key, value in info_dict.items()])
        else:
            return f"Error: '{gene_id}' not found in the gene annotation database. Try again with uppercase or without spaces or hyphens."

    def _run(
            self,
            query: str,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        """Use the tool."""
        return self._get_metadata(query)

class PythonSQLTool(BaseTool):
    name: str = "execute_full_sql_query_with_python"
    description:str = (
        "Executes the full SQL query using python without the trial-run LIMIT clause"
        "and saves the results to disk. Run this after the query has been tested using the QuerySQLDatabaseTool."
        "Can take some time to run especially when querying the `expr` table"
        "because the `expr` table has 60,000+ rows and 1000+ columns."
        "Useful for extracting full results, compared to QuerySQLDatabaseTool which is just a trial run."
    )

    def _execute_sql_query_with_python(self, query: str):
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
        
    def _run(
            self,
            query: str,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ):
        """Use the tool."""
        return self._execute_sql_query_with_python(query)


# similarity search against our vector store
class DocumentSearchTool(BaseTool):
    name: str = "document_search"
    description: str = (
        "Returns the reference manual of top K tables most relevant to the query. "
        "The query should only involve one term, such as survival data, gene expression data, "
        "or copy number data - do not mix multiple concepts at once."
        "Each term should have 3 words at maximum"
        "If there are multiple terms to search, call this tool multiple times, one for each term"
    )
    
    def _run(
        self,
        query: str,
        k: int = 1,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        k = max(1, min(k, 3))  # constrain k between 1 and 3
        store = connect_store()
        results = store.similarity_search(query, k=k)
        if results:
            return f"The top {k} table(s) with the best match: <div class=\"scrollable lightaccent codeblock\">{[doc.page_content for doc in results]}</div>"
        else:
            return "No tables with relevant fields found"



class GenerateGraphFilepathTool(BaseTool):
    name: str = "generate_graph_filepath"
    description: str = (
        "Generates a unique file path to save the plot image in PNG format."
        "No arguments required."
        "Returns a file path string like 'graph/graph_ab12cd34.png'."
    )
    
    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        plot_file_path = f"graph/graph_{uuid.uuid4().hex[:8]}.png"
        return plot_file_path



class DisplayPlotTool(BaseTool):
    name: str = "display_plot_html"
    description: str = (
        "Display the plot image saved at the given file path as HTML output. "
        "Arguments: file_path (str). If file path does not exist, an error message is returned. "
        "Thus, the plot must first be saved as file_path before this plot tool is called."
    )
    
    def _run(
        self,
        file_path: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
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


class GeneCopyNumberTool(BaseTool):
    name: str = "get_gene_level_copy_number_data"
    description: str = (
        "Retrieve the gene-level copy number data for a given GENCODE accession aka Ensembl Gene stable ID. "
        "Returns the path to a saved CSV file containing copy number data with index as public_id. "
        "Columns include: sample, chromosome, start_pos, end_pos, num_probes, segment_mean, visit, "
        "segment_copy_number_status, and overlap_len. "
        "segment_mean is the log2 fold-change of the probe. "
        "segment_copy_number_status is the categorical copy number status (-2, -1, 0, +1, or +2). "
        "Example input: ENSG00000143621"
        "Example output: public_id=MMRF_1016, sample=MMRF_1016_1_BM_CD138pos, chromosome=chr1, start_pos=149053976, end_pos=155975058, num_probes=700, segment_mean=0.499688, visit=1, segment_copy_number_status=1, overlap_len=46319."
    )

    def _max_overlapping_segment(self, gene_stable_id: str):
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
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        ans_df = self._max_overlapping_segment(query)
        csv_path = f'result/gene_level_copy_number_{query}.csv'
        ans_df.to_csv(csv_path)
        return f"Result saved to {csv_path}"


class CoxRegressionBaseDataTool(BaseTool):
    name: str = "get_cox_regression_base_data"
    description: str = (
        "Retrieve a template dataset for Cox PH regression analysis for a given endpoint ('os' or 'pfs'). "
        "Returns the path to a csv file containing PUBLIC ID, survival time, censoring status, age, ISS, and gender columns. "
        "Column names for endpoint os are PUBLIC_ID,oscdy,censos,D_PT_age,D_PT_gender_Male,D_PT_iss_II,D_PT_iss_III"
        "Column names for endpoint pfs are PUBLIC_ID,pfscdy,censpfs,D_PT_age,D_PT_gender_Male,D_PT_iss_II,D_PT_iss_III"
        "Example input: os "
        "Example output: result/cox_ph_covariates_os.csv "
        "Use scenario: When the user requests for survival regression of their feature of interest alongside common covariates like age, sex, and ISS, "
        "call this function to obtain the table for age, sex, ISS, and the right-censored survival data. "
        "You can then merge their feature(s) of interest with this table."
    )

    def _get_cox_regression_base_data(self, endpoint='os'):
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
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        return self._get_cox_regression_base_data(query)

class CoxPHStatsLog2TPMExprTool(BaseTool):
    name: str = "gene_expr_coxph_statistics"
    description: str = (
        "Retrieve the path to pre-computed Cox PH regression results for a given endpoint ('os' or 'pfs'). "
        "Returns the path to a csv file containing columns gene, coef, exp(coef), se(coef), z, p, lower95, upper95, n, q, neglog10q. "
        "Column names are `Gene`,`coef`,`exp(coef)`,`se(coef)`,`coef lower 95%`,`coef upper 95%`,`exp(coef) lower 95%`,`exp(coef) upper 95%`,`cmp to`,`z`,`p`,`-log2(p)` respectively. "
        "The analysis performed is Cox PH regression based on z-score of log2 (tpm+1) expression values of all genes. "
        "Age, sex, and ISS are used as covariates, besides the gene of interest. "
        "Samples are first-visit, bone marrow plasma cell in nature (visit ID = 1, tissue type BM, CD138pos). "
        "Example input: os "
        "Example output: Path to gene-wise CoxPH summary statistics for os endpoint: result/__path__to__results__.csv "
        "Note: some genes do not have regression values, CoxPH only around 56,000 out of 60,000 genes in GRCh38. "
        "Suitable for: User wants to filter a long list of genes down to those relevant to survival outcomes. "
        "Suitable for: User wants to measure whether upregulation or downregulation of a gene is associated with better or worse survival outcomes -> look at whether hazard ratio is >1 or <1. "
        "Not suitable for: User wants to measure the effect of their gene of interest on survival while adjusting for other covariates apart from age, sex, and ISS -> Suggest using get_cox_regression_base_data to get the base dataset and then merge their feature(s) of interest for CoxPH regression. "
        "Not suitable for: analysis on certain subpopulations, as summary statistics are based on the entire cohort."
    )
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        endpoint = query.lower()
        if endpoint not in ['os', 'pfs']:
            return "Error: endpoint must be either 'os' or 'pfs'"
        result_file = 'result/cox_ph_os_56294_genes.csv' if endpoint == 'os' else 'result/cox_ph_pfs_56317_genes.csv'
        if not os.path.exists(result_file):
            return f'Error: Gene-wise Cox PH regression results for endpoint {endpoint} not found.'
        return f'Path to gene-wise CoxPH summary statistics for {endpoint} endpoint: {result_file}'

class MADLog2TPMExprTool(BaseTool):
    name: str = "gene_expr_mad_values"
    description: str = (
        "Retrieve the path to pre-computed median and median absolute deviation (MAD) of log2(tpm+1)-transformed gene expression. "
        "Returns the path to a csv file containing columns Ensembl gene ID, median log2(tpm+1), and MAD log2(tpm+1). "
        "Column names are gene, median_log2, mad_log2 respectively. "
        "This contains all GrCh38 genes with expression data. "
        "Suitable for: User wants to filter or order genes based on expression variability across the cohort. "
        "Suitable for: User wants to check if a subpopulation has higher or lower expression compared to the cohort median. "
        "Not suitable for: evaluating differential expression between conditions. This is cohort-wide summary statistics. "
        "Not suitable for: retrieving median or MAD of certain subpopulations. Values here are based on the entire cohort."
    )
    
    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        result_file = 'result/gene_log2tpm_mad.csv'
        if not os.path.exists(result_file):
            return 'Error: Pre-computed gene MAD results not found.'
        return f'Path to gene-wise median and MAD of log2(tpm+1) expression values: {result_file}'
    

__all__ = [
    "ConvertGeneTool", 
    "GeneMetadataTool", 
    "MADLog2TPMExprTool", 
    "PythonSQLTool", 
    "DocumentSearchTool", 
    "GenerateGraphFilepathTool", 
    "DisplayPlotTool", 
    "GeneCopyNumberTool", 
    "CoxRegressionBaseDataTool", 
    "CoxPHStatsLog2TPMExprTool"
    ]