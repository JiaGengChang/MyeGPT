# Creates a PostgresQL Vector Store for retrieval using memory
# each table of the CoMMpass DB has its own metadata document
# as it will only load the relevant tables descriptions when it decides it needs to
# more cost effective alternative to loading in the large static prompt at the start of every session 
import os
from dotenv import load_dotenv
from langchain_aws import BedrockEmbeddings
from langchain_postgres import PGEngine, PGVectorStore
# from sqlalchemy.ext.asyncio import create_async_engine

import uuid
from langchain_core.documents import Document

# parameters
TABLE_NAME = "vectorstore" # string
SCHEMA_NAME = "commpass_schema" # string
VECTOR_SIZE = 1024  # int

def main():
    assert load_dotenv('src/.env')
    # Load the various documents

    with open("docs/overview.txt", "r", encoding="utf-8") as f:
        overview_content = f.read()

    with open("docs/canonical_ig.txt", "r", encoding="utf-8") as f:
        canonical_content = f.read()

    with open("docs/chromothripsis.txt", "r", encoding="utf-8") as f:
        chromothripsis_content = f.read()

    with open("docs/exome_ns_variants.txt", "r", encoding="utf-8") as f:
        exome_ns_variants_content = f.read()

    with open("docs/gatk_baf.txt", "r", encoding="utf-8") as f:
        gatk_baf_content = f.read()

    with open("docs/gene_annotation.txt", "r", encoding="utf-8") as f:
        gene_annotation_content = f.read()

    with open("docs/genome_gatk_cna.txt", "r", encoding="utf-8") as f:
        genome_gatk_cna_content = f.read()

    with open("docs/gep_scores.txt", "r", encoding="utf-8") as f:
        gep_scores_content = f.read()

    with open("docs/mutsig_sbs.txt", "r", encoding="utf-8") as f:
        mutsig_sbs_content = f.read()

    with open("docs/per_patient.txt", "r", encoding="utf-8") as f:
        per_patient_content = f.read()

    with open("docs/per_visit.txt", "r", encoding="utf-8") as f:
        per_visit_content = f.read()

    with open("docs/salmon_gene_unstranded_counts.txt", "r", encoding="utf-8") as f:
        salmon_gene_unstranded_counts_content = f.read()

    with open("docs/salmon_gene_unstranded_tpm.txt", "r", encoding="utf-8") as f:
        salmon_gene_unstranded_tpm_content = f.read()

    with open("docs/stand_alone_survival.txt", "r", encoding="utf-8") as f:
        stand_alone_survival_content = f.read()

    with open("docs/stand_alone_treatment_regimen.txt", "r", encoding="utf-8") as f:
        stand_alone_treatment_regimen_content = f.read()

    with open("docs/stand_alone_trtresp.txt", "r", encoding="utf-8") as f:
        stand_alone_trtresp_content = f.read()

    with open("docs/wgs_fish.txt", "r", encoding="utf-8") as f:
        wgs_fish_content = f.read()


    docs = [
        Document(
            id=str(uuid.uuid4()),
            page_content=overview_content,
            metadata={"category": "parent", "data modality": "N/A"},
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=canonical_content,
            metadata={"category": "child", "data modality": "Canonical Ig translocations"},
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=chromothripsis_content,
            metadata={"category": "child", "data modality": "Chromothripsis"},
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=exome_ns_variants_content,
            metadata={"category": "child", "data modality": "Exome Non-Synonymous Variants"},
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=gatk_baf_content,
            metadata={"category": "child", "data modality": "B-allele frequencies"},
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=gene_annotation_content,
            metadata={"category": "child", "data modality": "Reference Gene Annotation"},
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=genome_gatk_cna_content,
            metadata={"category": "child", "data modality": "Genome GATK Copy number alterations"},
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=gep_scores_content,
            metadata={"category": "child", "data modality": "GEP risk Scores"},
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=mutsig_sbs_content,
            metadata={"category": "child", "data modality": "SBS mutational signatures"},
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=per_patient_content,
            metadata={"category": "child", "data modality": "Patient-level Clinical/Demographic Data"},
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=per_visit_content,
            metadata={"category": "child", "data modality": "Patient Visit-level Clinical/Demographic Data"},
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=salmon_gene_unstranded_counts_content,
            metadata={"category": "child", "data modality": "Gene-level Unstranded Counts"},
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=salmon_gene_unstranded_tpm_content,
            metadata={"category": "child", "data modality": "Gene-level Unstranded TPM (transcripts per million)"},
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=stand_alone_survival_content,
            metadata={"category": "child", "data modality": "Patient Survival Data"},
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=stand_alone_treatment_regimen_content,
            metadata={"category": "child", "data modality": "Patient Treatment Regimen Data"},
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=stand_alone_trtresp_content,
            metadata={"category": "child", "data modality": "Patient Treatment Response Data"},
        ),
        Document(
            id=str(uuid.uuid4()),
            page_content=wgs_fish_content,
            metadata={"category": "child", "data modality": "Whole Genome Sequencing FISH Data"},
        ),
    ]

    # Create an embedding class instance
    embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0", region_name="us-east-1")

    # from langchain_openai import OpenAIEmbeddings
    # embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

    # create pgengine connection pool
    # CONNECTION_STRING = (
    #     f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}"
    #     f":{POSTGRES_PORT}/{POSTGRES_DB}"
    # )
    CONNECTION_STRING = os.environ.get("COMMPASS_DB_URI")

    # Create an SQLAlchemy Async Engine
    # engine = create_async_engine(CONNECTION_STRING)
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