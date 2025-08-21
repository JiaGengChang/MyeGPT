import os
from fastapi import FastAPI
import pandas as pd
from langchain_aws import ChatBedrockConverse
from langchain.tools import StructuredTool
from langchain_experimental.tools import PythonAstREPLTool
from langchain_community.utilities import SQLDatabase
from langchain_community.tools import QuerySQLDatabaseTool
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent
import uuid
import psycopg
import matplotlib
matplotlib.use('Agg') # non-interactive backend

from vectorstore import connect_store

gene_annot = pd.read_csv(f'../refdata/gene_annotation.tsv', sep='\t')

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
def execute_query_python(query: str):
    conn = psycopg.connect(dsn=os.environ.get("COMMPASS_DSN"))
    with conn.cursor() as curs:
        curs.execute(query.replace("LIMIT 100","")) # forcefully remove LIMIT 100 clause
        result = curs.fetchall()
        df = pd.DataFrame(result, columns=[desc[0] for desc in curs.description])
        conn.close()
    if not df.empty:
        result_csv_filename = f"result/result_{uuid.uuid4().hex[:8]}.csv"
        df.to_csv(result_csv_filename, index=False)
        return f"Query results saved to output file {result_csv_filename}."
    else:
        return "Query returned no results. No output file created."

python_query_sql_tool = StructuredTool.from_function(
    func=execute_query_python,
    name="execute_query_with_python",
    description="Executes the full SQL query using python without the LIMIT 100 clause and saves the results to disk. Useful for downstream analysis for visualization etc."
)

# python tool to do basic tasks like string manipulation and arithmetic
python_repl_tool = PythonAstREPLTool()

# create a QUERY SQL tool
db_uri = os.environ.get("COMMPASS_DB_URI")
db = SQLDatabase.from_uri(db_uri)
langchain_query_sql_tool = QuerySQLDatabaseTool(db=db)

# similarity search against our vector store
def document_search(query: str):
    # establish connection to postgres vector store
    store = connect_store()
    results = store.similarity_search(query,k=1)
    if results:
        return f"""Table with best match:
        {[doc.page_content for doc in results]}
        """
    else:
        return "No tables with relevant fields found"

# tool to search for relevant database documents
document_search_tool = StructuredTool.from_function(
    func=document_search,
    name="document_search",
    description="Search for database tables that are relevant to the query. Returns the reference manual of top 3 tables relevant to the query. The query should only include one subject, such as survival data, gene  expression data, or copy number data - do not mix multiple concepts at once."
)

# initialize the chat model
llm = ChatBedrockConverse(
    model_id=os.environ.get("MODEL_ID"),
    temperature=0.,
)

# Create runnable graph
graph = create_react_agent(
    model=llm,
    tools=[document_search_tool, convert_gene_tool, langchain_query_sql_tool, python_repl_tool, python_query_sql_tool],
    checkpointer=InMemorySaver(),
    store=connect_store(),
)

# Create a system message for the agent
# dynamic variables will be filled in at the start of each session
# removed db description
def create_system_message() -> str:
    with open('prompt.txt', 'r') as f:
        latent_system_message = f.read()
    system_message = latent_system_message.format(
        dialect=db.dialect,
        commpass_db_uri=db_uri
    )
    return system_message

system_message = None
config = {"configurable": {"thread_id": "thread-001"}}

async def send_init_prompt(app:FastAPI):
    global system_message
    global graph
    global config
    system_message = create_system_message()
    init_response = await graph.ainvoke({"messages" :[system_message]}, config)

    # Store the init response for injection into HTML
    app.state.init_response = init_response["messages"][-1].content
    
    # Open the gate for queries
    app.state.init_prompt_done.set()

def query_agent(user_input: str):
    global graph
    global config
    graph_png_filename = f"graph/graph_{uuid.uuid4().hex[:8]}.png"
    preamble = SystemMessage(f"""
                             If a graph is created, save it as {graph_png_filename} and display with `<img src={graph_png_filename} max-width=100% height=auto>`.
                             """)
    user_message = HumanMessage(content=user_input)
    
    for step in graph.stream({"messages": [preamble, user_message]}, config, stream_mode="values"):
        if step["messages"]:
            step["messages"][-1].pretty_print()
            if isinstance(step["messages"][-1], AIMessage):
                chunk = step["messages"][-1].content
                if isinstance(chunk, list):
                    chunk = chunk[0]
                if isinstance(chunk, dict) and "text" in chunk:
                    chunk = chunk["text"][:-1]
                yield chunk