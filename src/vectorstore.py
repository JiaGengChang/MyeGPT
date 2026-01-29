import os 
from langchain_postgres import PGEngine, PGVectorStore

# load user modules
from variables import COMMPASS_DB_URI,EMBEDDINGS_MODEL_PROVIDER,EMBEDDINGS_TABLE_SUFFIX

def create_embedding_service(model_provider):
    # create embedding service
    if model_provider=='mistral':
        from langchain_mistralai import MistralAIEmbeddings
        embedding_service = MistralAIEmbeddings(model="mistral-embed") # embedding dim 1024
    elif model_provider=='openai':
        from langchain_openai.embeddings import OpenAIEmbeddings
        embedding_service = OpenAIEmbeddings(model="text-embedding-3-large") # 3072
    elif model_provider=='gemini':
        from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
        embedding_service = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001") # 3072
    elif model_provider=='amazon':
        from langchain_aws.embeddings import BedrockEmbeddings
        embedding_service = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1",region_name="us-east-1") # 1024
    else:
        raise ValueError(f"Unsupported model provider: {model_provider}")
    return embedding_service

# create pgengine connection pool manager
pg_engine = PGEngine.from_connection_string(COMMPASS_DB_URI)

# embeddings provider
# embeddings = MistralAIEmbeddings(model="mistral-embed")
embeddings = create_embedding_service(EMBEDDINGS_MODEL_PROVIDER)
# set env var for embedding model id (prefer 'model', fallback to 'model_id')
try:
    os.environ["EMBEDDINGS_MODEL_ID"] = embeddings.model
except AttributeError:
    os.environ["EMBEDDINGS_MODEL_ID"] = embeddings.model_id

# create connection to vector store
def connect_store():
    store = PGVectorStore.create_sync(
        engine=pg_engine,
        table_name=EMBEDDINGS_MODEL_PROVIDER+EMBEDDINGS_TABLE_SUFFIX,
        schema_name="document_embeddings",
        embedding_service=embeddings,
    )
    return store