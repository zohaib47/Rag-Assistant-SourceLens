import os
import logging
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

IGNORE_DIRS = {
    "node_modules", ".git", "venv", "__pycache__", "dist", "build", ".next", "vector_db"
}

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".md", ".html", ".css"
}
PDF_EXTENSION = ".pdf"

SKIP_FILES = {"package-lock.json", "yarn.lock"}


def _read_text_file(file_path: str) -> str:
    """UTF-8 se parhta hai, fail ho to latin-1 par fallback."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1", errors="ignore") as f:
            return f.read()


def _read_pdf(file_path: str, relative_path: str, file_ext: str) -> list:
    """Har PDF page ko alag Document banata hai (page number metadata ke sath)."""
    from pypdf import PdfReader

    docs = []
    reader = PdfReader(file_path)
    for page_no, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            docs.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": f"{relative_path} (page {page_no})",
                        "file_extension": file_ext,
                        "page": page_no,
                    },
                )
            )
    if not docs:
        logger.warning(f"{relative_path}: koi text nahi mila (shayad scanned PDF hai).")
    return docs


def load_codebase(root_dir: str) -> list:
    """Folder se code files aur PDFs parh kar Document list return karta hai."""
    documents = []

    if not os.path.exists(root_dir):
        logger.error(f"Directory '{root_dir}' does not exist.")
        return documents

    logger.info(f"Scanning directory: {root_dir}")

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]

        for file in filenames:
            if file in SKIP_FILES:
                continue

            file_ext = os.path.splitext(file)[1].lower()
            if file_ext not in CODE_EXTENSIONS and file_ext != PDF_EXTENSION:
                continue

            file_path = os.path.join(dirpath, file)
            relative_path = os.path.relpath(file_path, root_dir)

            try:
                if file_ext == PDF_EXTENSION:
                    documents.extend(_read_pdf(file_path, relative_path, file_ext))
                else:
                    content = _read_text_file(file_path)
                    if content.strip():
                        documents.append(
                            Document(
                                page_content=content,
                                metadata={
                                    "source": relative_path,
                                    "file_extension": file_ext,
                                },
                            )
                        )
            except Exception as e:
                logger.warning(f"Skipping {file_path}: {e}")

    logger.info(f"Loaded {len(documents)} documents from '{root_dir}'.")
    return documents