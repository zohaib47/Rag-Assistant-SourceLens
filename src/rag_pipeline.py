import os
from dotenv import load_dotenv
from src.vectorstore import load_vector_store
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_groq import ChatGroq

load_dotenv()

def format_docs(docs):
    """
    Retrieved documents ko un ke file path (metadata) ke sath format karta hai 
    taake LLM ko pata ho ke kaunsa content kis file ka hai.
    """
    formatted = []
    for doc in docs:
        source = doc.metadata.get("source", "Unknown File")
        formatted.append(f"--- File Path: {source} ---\n{doc.page_content}\n")
    return "\n".join(formatted)

def get_rag_chain():
    """
    Sets up the complete RAG pipeline connecting Supabase pgvector retriever, 
    custom formatting, file-aware system prompt, and Groq LLM.
    """
    # 1. Vector store load karein (Supabase pgvector se)
    vector_store = load_vector_store()
    if not vector_store:
        raise ValueError("Vector database nahi mila! Pehle files ya repository load aur index karein.")
    
    # 2. Retriever banayein (Top 4 most relevant chunks uthayega)
    retriever = vector_store.as_retriever(search_kwargs={"k": 4})
    
    # 3. Groq LLM initialize karein (.env se model name aur key uthayega)
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY .env file mein nahi mili!")
        
    model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        
    llm = ChatGroq(
        model=model_name,
        api_key=api_key,
        temperature=0.1  # Low temperature taake model accurate aur factual answers de
    )
    
    # 4. File & Codebase Q&A ke liye File-Aware Expert System Prompt
    template = """You are an expert AI Software Engineer and Document Assistant. 
Your task is to answer the user's technical question or document query accurately using ONLY the provided context snippets.
Always examine the file path or file name from the context metadata and mention the exact file name in your answer.
If the answer is NOT present in the provided context files, state clearly mentioning the specific file name(s): 
"Yeh maloomat di gayi file(s) mein mojood nahi hain."

Context (Snippets with File Paths):
{context}

User Question: {question}

Answer with clear explanation and exact file references:"""

    prompt = ChatPromptTemplate.from_template(template)
    
    # 5. LangChain Expression Language (LCEL) chain banayein
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain, retriever

if __name__ == "__main__":
    # Testing the pipeline
    try:
        chain, _ = get_rag_chain()
        test_query = "What is the main content of this file?"
        print(f"\nRunning test query: '{test_query}'\n")
        response = chain.invoke(test_query)
        print("--- AI Response ---")
        print(response)
    except Exception as e:
        print(f"Error: {e}")