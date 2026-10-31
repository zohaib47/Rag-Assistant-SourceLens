import os
os.environ["SQLALCHEMY_WARN_20"] = "1"
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"
import hashlib
import re
from functools import lru_cache
from dotenv import load_dotenv
from sqlalchemy import create_engine
from langchain_postgres import PGVector
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

CONNECTION_STRING = os.getenv("SUPABASE_DB_URL")
COLLECTION_NAME = "repo_repo_rag_vectors"  # default; purane code ke sath compatible


@lru_cache(maxsize=1)
def get_embeddings():
    """
    Returns local HuggingFace embeddings with optimized batch size for faster inference.
    """
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        encode_kwargs={"batch_size": 64}  # Speed boost: processes multiple chunks at once
    )


@lru_cache(maxsize=1)
def get_engine():
    """
    Ek hi database engine poori app ke liye. Har call par naya engine banane se
    Supabase ke connections khatam ho jate hain.
    """
    if not CONNECTION_STRING:
        raise ValueError("SUPABASE_DB_URL .env file mein nahi mili!")
    return create_engine(CONNECTION_STRING, pool_pre_ping=True)


def make_collection_name(source: str, user_id: str = "") -> str:
    """
    Har repo (aur chahein to har user) ke liye alag collection ka naam.
    """
    slug = re.sub(r"[^a-z0-9]+", "_", source.lower()).strip("_")[-30:]
    digest = hashlib.sha1(f"{user_id}|{source}".encode("utf-8")).hexdigest()[:10]
    return f"repo_{digest}_{slug}"


def create_vector_store(chunks, collection_name: str = COLLECTION_NAME, replace: bool = True):
    """
    Stores chunks in Supabase pgvector.
    """
    embeddings = get_embeddings()

    vector_store = PGVector.from_documents(
        documents=chunks,
        embedding=embeddings,
        connection=get_engine(),
        collection_name=collection_name,
        use_jsonb=True,
        pre_delete_collection=replace,
        # batch_size removed because PGVector doesn't take it in __init__
    )
    print(f"Successfully stored {len(chunks)} chunks in Supabase pgvector ({collection_name}).")
    return vector_store


def load_vector_store(collection_name: str = COLLECTION_NAME):
    """
    Loads the existing vector store from Supabase pgvector.
    """
    if not CONNECTION_STRING:
        return None

    try:
        return PGVector(
            connection=get_engine(),
            embeddings=get_embeddings(),
            collection_name=collection_name,
            use_jsonb=True,
        )
    except Exception as e:
        print(f"Error loading vector store from Supabase: {e}")
        return None