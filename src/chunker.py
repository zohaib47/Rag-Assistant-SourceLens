import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

LANGUAGE_MAP = {
    ".py": Language.PYTHON,
    ".js": Language.JS,
    ".jsx": Language.JS,
    ".ts": Language.TS,
    ".tsx": Language.TS,
    ".html": Language.HTML,
    ".md": Language.MARKDOWN,
}


def _get_splitter(file_ext: str, chunk_size: int, chunk_overlap: int):
    """File type ke hisab se splitter: code ko functions/classes par, baqi ko paragraphs par todta hai."""
    language = LANGUAGE_MAP.get(file_ext)
    if language:
        # Code files ke liye standard size rakhein taake logic intact rahay
        return RecursiveCharacterTextSplitter.from_language(
            language=language, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
    
    # PDF, Excel, ya baqi documents ke liye chunk_size bara rakhein taake chunks kam banein aur speed fast ho
    doc_chunk_size = max(chunk_size, 1500)  # Minimum 1500 size for documents
    return RecursiveCharacterTextSplitter(
        chunk_size=doc_chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def split_code_documents(documents: list, chunk_size: int = 1000, chunk_overlap: int = 200) -> list:
    """Documents ko chhote chunks mein todta hai (code structure ka khayal rakhte hue)."""
    chunked = []
    splitters = {}  # har extension ka splitter sirf ek baar banta hai

    for doc in documents:
        ext = doc.metadata.get("file_extension", "")
        if ext not in splitters:
            splitters[ext] = _get_splitter(ext, chunk_size, chunk_overlap)
        chunked.extend(splitters[ext].split_documents([doc]))

    logger.info(f"Split {len(documents)} documents into {len(chunked)} chunks.")
    return chunked