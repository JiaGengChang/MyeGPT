import os 
from langchain_postgres import PGEngine, PGVectorStore
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_aws.embeddings import BedrockEmbeddings
from langchain_mistralai import MistralAIEmbeddings

# do not change, set in create_vectorstore.py
SCHEMA_NAME = "document_embeddings"
TABLE_NAME = os.environ.get("EMBEDDINGS_MODEL_PROVIDER")

# create pgengine connection pool manager
pg_engine = PGEngine.from_connection_string(os.environ.get("COMMPASS_DB_URI"))

# embeddings provider
embeddings = MistralAIEmbeddings(model="mistral-embed")

# create connection to vector store
def connect_store():
    store = PGVectorStore.create_sync(
        engine=pg_engine,
        table_name=TABLE_NAME,
        schema_name=SCHEMA_NAME,
        embedding_service=embeddings,
    )
    return store

def create_embedding_service(model_provider):

    # create embedding service
    if model_provider=='mistral':
        embedding_service = MistralAIEmbeddings(model="mistral-embed") # embedding dim 1024
    elif model_provider=='openai':
        embedding_service = OpenAIEmbeddings(model="text-embedding-3-large") # 3072
    elif model_provider=='amazon':
        embedding_service = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1",region_name="us-east-1") # 1024
    else:
        raise ValueError(f"Unsupported model provider: {model_provider}")
    
    return embedding_service