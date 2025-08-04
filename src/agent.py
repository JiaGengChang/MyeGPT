import os
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
import matplotlib
matplotlib.use('Agg') # non-interactive backend

from dbdesc import db_description
from prompt import latent_system_message

db_uri = os.environ.get("COMMPASS_DB_URI")
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
repl_tool = PythonAstREPLTool()

# create a QUERY SQL tool
query_sql_tool = QuerySQLDatabaseTool(db=db)

# initialize the chat model
llm = ChatBedrockConverse(
    model_id=os.environ.get("MODEL_ID"),
    temperature=0.,
)

# Create runnable graph
graph = create_react_agent(
    model=llm,
    tools=[convert_gene_tool, query_sql_tool, repl_tool],
    checkpointer=InMemorySaver()
)

# Create a system message for the agent
# dynamic variables will be filled in at the start of each session

def create_system_message():
    system_message = latent_system_message.format(
        db_description=db_description,
        dialect=db.dialect,
        commpass_db_uri=db_uri
    )
    return system_message

system_message = None
config = {"configurable": {"thread_id": "thread-001"}, "recursion_limit": 50}

def start_session():
    global system_message
    global graph
    global config
    system_message = create_system_message()
    graph.invoke({"messages" :[system_message]}, config)

def query_agent(user_input: str):
    global system_message
    global graph
    global config
    if not system_message:
        start_session()
    graph_png_filename = f"graph/graph_{uuid.uuid4().hex[:8]}.png"
    preamble = SystemMessage(f'If a graph is generated, save it as {graph_png_filename} and display it with <img>.')
    user_message = HumanMessage(content=user_input)
    full_response = ""
    for step in graph.stream({"messages": [preamble, user_message]}, config, stream_mode="values"):
        if step["messages"]:
            step["messages"][-1].pretty_print()
        if step["messages"] and isinstance(step["messages"][-1], AIMessage):
            chunk = step["messages"][-1].content
            if isinstance(chunk, str):
                full_response += chunk
            elif isinstance(chunk, dict) and "text" in chunk:
                full_response += chunk["text"]
            elif isinstance(chunk, list) and "text" in chunk[0]:
                full_response += chunk[0]["text"]
        
    return full_response
