import logging
import os
import shutil
import yaml
import gc
from langchain.docstore.document import Document
from langchain.embeddings import HuggingFaceInstructEmbeddings, HuggingFaceEmbeddings, HuggingFaceBgeEmbeddings
from langchain.vectorstores import Chroma
from chromadb.config import Settings
from document_processor import load_documents, split_documents
import torch
from utilities import validate_symbolic_links

ROOT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
SOURCE_DIRECTORY = f"{ROOT_DIRECTORY}/Docs_for_DB"
PERSIST_DIRECTORY = f"{ROOT_DIRECTORY}/Vector_DB"
INGEST_THREADS = os.cpu_count() or 8

CHROMA_SETTINGS = Settings(
    chroma_db_impl="duckdb+parquet", persist_directory=PERSIST_DIRECTORY, anonymized_telemetry=False
)

def main():
    with open(os.path.join(ROOT_DIRECTORY, "config.yaml"), 'r') as stream:
        config_data = yaml.safe_load(stream)
        EMBEDDING_MODEL_NAME = config_data.get("EMBEDDING_MODEL_NAME", "")
        COMPUTE_DEVICE = config_data.get("COMPUTE_DEVICE", "cpu")

    logging.info(f"Loading documents from {SOURCE_DIRECTORY}")
    documents = load_documents(SOURCE_DIRECTORY)
    texts = split_documents(documents)
    
    #  validate symbolic links before creating the database.
    validate_symbolic_links(SOURCE_DIRECTORY)
    
    logging.info(f"Loaded {len(documents)} documents from {SOURCE_DIRECTORY}")
    logging.info(f"Split into {len(texts)} chunks of text")
    
    embeddings = get_embeddings(EMBEDDING_MODEL_NAME, COMPUTE_DEVICE)
    
    if os.path.exists(PERSIST_DIRECTORY):
        shutil.rmtree(PERSIST_DIRECTORY)
        os.makedirs(PERSIST_DIRECTORY)
    
    db = Chroma.from_documents(
        texts,
        embeddings,
        persist_directory=PERSIST_DIRECTORY,
        client_settings=CHROMA_SETTINGS,
    )
    db.persist()
    
    print("Vector database has been created.")
    
    embeddings = None
    del embeddings
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

def get_embeddings(EMBEDDING_MODEL_NAME, COMPUTE_DEVICE):
    if "instructor" in EMBEDDING_MODEL_NAME:
        return HuggingFaceInstructEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={"device": COMPUTE_DEVICE},
            embed_instruction="Represent the document for retrievel:",
            query_instruction="Represent the question for retrieving supporting documents:"
        )
    elif "bge" in EMBEDDING_MODEL_NAME and "large-en-v1.5" not in EMBEDDING_MODEL_NAME:
        return HuggingFaceBgeEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={"device": COMPUTE_DEVICE},
            query_instruction="Represent this sentence for searching relevant passages:"
        )
    else:
        return HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={"device": COMPUTE_DEVICE},
        )

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s", level=logging.INFO
    )
    main()
