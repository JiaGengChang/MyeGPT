import os
import pandas as pd
from langchain.chat_models import init_chat_model
from langchain.tools import StructuredTool
from langchain_experimental.tools import PythonAstREPLTool
from langchain_community.utilities import SQLDatabase
from langchain_community.tools import QuerySQLDatabaseTool
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent
import matplotlib
import json
matplotlib.use('Agg') # non-interactive backend

from dbdesc import db_description
from prompt import latent_system_message

COMMPASS_DB_URI = f'postgresql+psycopg2://{os.environ.get("DB_USER")}:{os.environ.get("DB_PASSWORD")}@{os.environ.get("DB_HOST")}:5432/commpass'
db = SQLDatabase.from_uri(COMMPASS_DB_URI)

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

def save_query_results_to_json(results, file_path: str):
    """
    Save SQL query results (list of dicts or DataFrame) to a JSON file.
    """
    if isinstance(results, pd.DataFrame):
        data = results.to_dict(orient="records")
    else:
        data = results
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    return f"Query results saved to {file_path}"

save_query_results_tool = StructuredTool.from_function(
    func=save_query_results_to_json,
    name="save_query_results_to_json",
    description="Save SQL query results from `query_sql_tool` to a JSON file at the specified file path."
)

# python tool to do basic tasks like string manipulation and arithmetic
repl_tool = PythonAstREPLTool()

# create a QUERY SQL tool
query_sql_tool = QuerySQLDatabaseTool(db=db)

# Create runnable graph
graph = create_react_agent(
    model=init_chat_model(os.environ.get("MODEL")),
    tools=[convert_gene_tool, query_sql_tool, repl_tool],
    checkpointer=InMemorySaver()
)

# Create a system message for the agent
# dynamic variables will be filled in later

def query_agent(user_input: str, graph_url: str):
    
    system_message = SystemMessage(content=latent_system_message.format(
        commpass_db_uri=COMMPASS_DB_URI,
        db_description=db_description,
        dialect=db.dialect,
        graph_url=graph_url,
    ))

    user_message = HumanMessage(content=user_input)
    
    config = {"configurable": {"thread_id": "thread-001"}, "recursion_limit": 25}

    full_response = ""
    for step in graph.stream({"messages": [system_message, user_message]}, config, stream_mode="values"):
        if step["messages"]:
            step["messages"][-1].pretty_print()
        if step["messages"] and isinstance(step["messages"][-1], AIMessage):
            chunk = step["messages"][-1].content
            full_response += chunk
    return full_response
