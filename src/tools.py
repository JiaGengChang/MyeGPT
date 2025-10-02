import os
import re
import uuid
import psycopg
import pandas as pd
from langchain.tools import StructuredTool
from langchain_experimental.tools import PythonAstREPLTool
from langchain_community.utilities import SQLDatabase
from langchain_community.tools import QuerySQLDatabaseTool

from vectorstore import connect_store

__all__ = ['convert_gene_tool', 'document_search_tool', 'langchain_query_sql_tool', 'python_repl_tool', 'python_execute_sql_query_tool']

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
        return f"""The top {k} table(s) with best match:
        {[doc.page_content for doc in results]}
        """
    else:
        return "No tables with relevant fields found"

# tool to search for relevant database documents
document_search_tool = StructuredTool.from_function(
    func=document_search,
    name="document_search",
    description="Returns the reference manual of top K tables most relevant to the query. The query should only involve one subject, such as survival data, gene expression data, or copy number data - do not mix multiple concepts at once."
)