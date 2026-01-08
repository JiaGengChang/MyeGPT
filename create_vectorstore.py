# Creates a PostgresQL Vector Store for retrieval using memory
# each table of the CoMMpass DB has its own metadata document
# as it will only load the relevant tables descriptions when it decides it needs to
# more cost effective alternative to loading in the large static prompt at the start of every session 
import os
from dotenv import load_dotenv
assert load_dotenv(os.path.join(os.path.dirname(__file__),'src','.env')), "Failed to load .env file"
from langchain_postgres import PGEngine, PGVectorStore
import uuid
from langchain_core.documents import Document
from argparse import ArgumentParser
from src.vectorstore import create_embedding_service

# parameters
SCHEMA_NAME = "document_embeddings" # previously was commpass_schema
parser = ArgumentParser()
parser.add_argument('--model_provider', type=str, required=True, choices=['mistral','openai','gemini','amazon'], help='Embedding model provider to use.')
# vector length: mistral-embed: 1024, amazon titan text embed v1: 1536, openai text-embed-large: 3072, gemini-embedding-001
parser.add_argument('--vector_size', type=int, required=True, help='Dimension of the embedding vectors.') 
args = parser.parse_args()
TABLE_NAME = args.model_provider
VECTOR_SIZE = args.vector_size

def main():
    docsdir = os.path.join(os.path.dirname(__file__), 'docs')
    docs = []
    for file in os.listdir(docsdir):
        print(f"Found document file: {file}")
        with open(os.path.join(docsdir, file), "r", encoding="utf-8") as f:
            content = f.read()
            print(f"Content preview: {content[:50]}...")
            docs.append(Document(id=uuid.uuid3(uuid.NAMESPACE_URL, file).__str__(), page_content=content))

    # Create an embedding class instance
    embeddings = create_embedding_service(args.model_provider)

    CONNECTION_STRING = os.environ.get("COMMPASS_DB_URI")

    # Create an SQLAlchemy Async Engine
    pg_engine = PGEngine.from_connection_string(CONNECTION_STRING)
    
    # Initialize empty table
    pg_engine.init_vectorstore_table(
        table_name=TABLE_NAME,
        schema_name=SCHEMA_NAME,
        vector_size=VECTOR_SIZE,
        overwrite_existing=True,
    )
    # create connection to vector store
    store = PGVectorStore.create_sync(
        engine=pg_engine,
        table_name=TABLE_NAME,
        schema_name=SCHEMA_NAME,
        embedding_service=embeddings,
    )
    # add our database manual
    store.add_documents(docs)

if __name__ == "__main__":
    main()