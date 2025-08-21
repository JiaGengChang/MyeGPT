import os 
from langchain_postgres import PGEngine, PGVectorStore
from langchain_aws import BedrockEmbeddings

# do not change, set in create_vectorstore.py
TABLE_NAME = "vectorstore"  
SCHEMA_NAME = "commpass_schema"

# create pgengine connection pool manager
pg_engine = PGEngine.from_connection_string(os.environ.get("COMMPASS_DB_URI"))

# embeddings provider
# us-east-1 has the best availability
embeddings = BedrockEmbeddings(model_id=os.environ.get("EMBEDDING_MODEL_ID"), region_name='us-east-1')

# create connection to vector store
def connect_store():
    store = PGVectorStore.create_sync(
        engine=pg_engine,
        table_name=TABLE_NAME,
        schema_name=SCHEMA_NAME,
        embedding_service=embeddings,
    )
    return store
