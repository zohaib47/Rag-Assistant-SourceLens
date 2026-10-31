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
EXCEL_EXTENSIONS = {".xlsx", ".xlsm", ".xls"}

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


def _read_excel(file_path: str, relative_path: str, file_ext: str) -> list:
    """Read workbook sheets into text documents with row and column labels."""
    if file_ext == ".xls":
        import xlrd

        workbook = xlrd.open_workbook(file_path, on_demand=True)
        try:
            sheets = []
            for sheet in workbook.sheets():
                rows = [
                    [sheet.cell_value(row, col) for col in range(sheet.ncols)]
                    for row in range(sheet.nrows)
                ]
                sheets.append((sheet.name, rows))
        finally:
            workbook.release_resources()
    else:
        from openpyxl import load_workbook

        workbook = load_workbook(file_path, read_only=True, data_only=True)
        try:
            sheets = [
                (sheet.title, [list(row) for row in sheet.iter_rows(values_only=True)])
                for sheet in workbook.worksheets
            ]
        finally:
            workbook.close()

    documents = []
    for sheet_name, rows in sheets:
        non_empty_rows = [
            (row_number, row)
            for row_number, row in enumerate(rows, start=1)
            if any(value is not None and str(value).strip() for value in row)
        ]
        if not non_empty_rows:
            continue

        header_row_number, header_row = non_empty_rows[0]
        headers = [
            str(value).strip() if value is not None and str(value).strip()
            else f"Column {column_number}"
            for column_number, value in enumerate(header_row, start=1)
        ]
        lines = [f"Worksheet: {sheet_name}", "Columns: " + " | ".join(headers)]

        for row_number, row in non_empty_rows[1:]:
            cells = []
            for column_number, value in enumerate(row):
                if value is None or not str(value).strip():
                    continue
                header = headers[column_number] if column_number < len(headers) else f"Column {column_number + 1}"
                cells.append(f"{header}: {value}")
            if cells:
                lines.append(f"Row {row_number}: " + " | ".join(cells))

        if len(non_empty_rows) == 1:
            lines.append(
                f"Row {header_row_number}: "
                + " | ".join(
                    f"{headers[index]}: {value}"
                    for index, value in enumerate(header_row)
                    if value is not None and str(value).strip()
                )
            )

        documents.append(
            Document(
                page_content="\n".join(lines),
                metadata={
                    "source": f"{relative_path} (sheet: {sheet_name})",
                    "file_extension": file_ext,
                    "sheet": sheet_name,
                },
            )
        )
    return documents


def load_file(file_path: str, source_name: str | None = None) -> list:
    """Load one supported code, PDF, or Excel file into source-tagged documents."""
    file_name = os.path.basename(file_path)
    if file_name in SKIP_FILES:
        return []

    file_ext = os.path.splitext(file_name)[1].lower()
    if (
        file_ext not in CODE_EXTENSIONS
        and file_ext != PDF_EXTENSION
        and file_ext not in EXCEL_EXTENSIONS
    ):
        return []

    source_name = source_name or file_name
    if file_ext == PDF_EXTENSION:
        return _read_pdf(file_path, source_name, file_ext)
    if file_ext in EXCEL_EXTENSIONS:
        return _read_excel(file_path, source_name, file_ext)

    content = _read_text_file(file_path)
    if not content.strip():
        return []
    return [
        Document(
            page_content=content,
            metadata={"source": source_name, "file_extension": file_ext},
        )
    ]


def load_codebase(root_dir: str) -> list:
    """Load supported code, PDF, and Excel files from a folder."""
    documents = []

    if not os.path.exists(root_dir):
        logger.error(f"Directory '{root_dir}' does not exist.")
        return documents

    logger.info(f"Scanning directory: {root_dir}")

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]

        for file in filenames:
            file_path = os.path.join(dirpath, file)
            relative_path = os.path.relpath(file_path, root_dir)
            try:
                documents.extend(load_file(file_path, relative_path))
            except Exception as error:
                logger.warning("Skipping %s: %s", file_path, error)

    logger.info(f"Loaded {len(documents)} documents from '{root_dir}'.")
    return documents