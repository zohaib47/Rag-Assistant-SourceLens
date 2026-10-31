import os
import logging
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_groq import ChatGroq
from src.vectorstore import load_vector_store

load_dotenv()
logger = logging.getLogger(__name__)

NOT_FOUND_MESSAGE = "ℹ️ This information could not be found in the indexed files."
TOP_K = int(os.getenv("RAG_TOP_K", "8"))

PROMPT_TEMPLATE = """You are an expert AI Software Engineer and Document Assistant.
Answer the user's question using ONLY the context snippets below.

Rules:
1. Use only facts that are written in the context. Never use outside knowledge and never guess.
2. If the answer is not in the context, reply with exactly this sentence and nothing else:
{not_found}
3. Mention the exact file name for every fact. If the snippet header shows a page number, cite that page. Cite a page only for text that really appears in that snippet.
4. If the question is wrong about something (for example it assumes a feature or number that the context contradicts), say so politely and give the correct information from the context.
5. If a snippet gives information that applies to the whole product line or document (for example a general warranty table that does not name a model), apply it to the model or item asked about and say it is stated generally.
6. If the question mentions a model, item or name that does not exist in the context, say it is not in the files.
7. Format: short, clear markdown. For tables use only plain text in cells. Never use HTML tags such as <br>; use separate rows or bullet lists instead.

Context (snippets with file paths):
{context}

Question: {question}

Answer:"""


def format_docs(docs):
    """Retrieved chunks ko file path (aur page/sheet) ke sath format karta hai."""
    formatted = []
    for doc in docs:
        source = doc.metadata.get("source", "Unknown File")
        formatted.append(f"--- File Path: {source} ---\n{doc.page_content}\n")
    return "\n".join(formatted)


def get_rag_chain(collection_name: str | None = None):
    """
    RAG pipeline: Supabase pgvector retriever + strict prompt + Groq LLM.
    Returns (chain, retriever). chain.invoke(question) ek string return karta hai.
    """
    vector_store = (
        load_vector_store(collection_name) if collection_name else load_vector_store()
    )
    if not vector_store:
        raise ValueError("Vector database not found. Please index your files first.")

    retriever = vector_store.as_retriever(search_kwargs={"k": TOP_K})

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env")

    model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    llm = ChatGroq(model=model_name, api_key=api_key, temperature=0.1)

    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    answer_chain = prompt | llm | StrOutputParser()

    def answer(question: str) -> str:
        docs = retriever.invoke(question)
        logger.info(
            "Retrieved %d chunks for question %r: %s",
            len(docs), question, [d.metadata.get("source") for d in docs],
        )
        if not docs:
            return NOT_FOUND_MESSAGE
        return answer_chain.invoke(
            {
                "context": format_docs(docs),
                "question": question,
                "not_found": NOT_FOUND_MESSAGE,
            }
        )

    return RunnableLambda(answer), retriever


if __name__ == "__main__":
    try:
        chain, _ = get_rag_chain()
        test_query = "What is the main content of this file?"
        print(f"\nRunning test query: '{test_query}'\n")
        print("--- AI Response ---")
        print(chain.invoke(test_query))
    except Exception as e:
        print(f"Error: {e}")