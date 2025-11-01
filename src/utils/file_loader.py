from pathlib import Path
from typing import Callable, Dict, Optional

from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyMuPDFLoader,
    TextLoader,
    UnstructuredCSVLoader,
    UnstructuredExcelLoader,
    UnstructuredPowerPointLoader,
)

from settings.logger import get_logger

logger = get_logger(__name__)


class FileLoader:
    """A class to handle loading and extracting content from various file types."""

    LANGCHAIN_LOADERS: Dict[str, Callable[[str], object]] = {
        ".pdf": lambda fp: PyMuPDFLoader(fp),
        ".docx": lambda fp: Docx2txtLoader(fp),
        ".csv": lambda fp: UnstructuredCSVLoader(fp),
        ".xls": lambda fp: UnstructuredExcelLoader(fp),
        ".xlsx": lambda fp: UnstructuredExcelLoader(fp),
        ".txt": lambda fp: TextLoader(fp, encoding="utf-8"),
        ".ppt": lambda fp: UnstructuredPowerPointLoader(fp),
        ".pptx": lambda fp: UnstructuredPowerPointLoader(fp),
    }

    DOCLING_FORMATS = [".pdf", ".docx", ".xlsx", ".pptx", ".csv", ".png", ".jpeg"]

    def __init__(self, file_path: str, content_path: str, client: str = "langchain"):
        """
        Initialize FileLoader with file paths and client type.

        Args:
            file_path: Path to the source file
            content_path: Path where extracted content will be saved
            client: Type of loader client ('langchain' or 'docling')
        """
        self.file_path = Path(file_path)
        self.content_path = Path(content_path)
        self.client = client.lower()

        if self.client not in ["langchain", "docling"]:
            logger.warning(f"Invalid client type: {client}. Defaulting to langchain.")
            self.client = "langchain"

    def extract_from_file(self) -> Optional[list]:
        """
        Extract content from file and append to content_path.

        Returns:
            List of extracted documents or None if extraction fails
        """
        try:
            file_ext = self._get_file_ext()
            loader = self._get_loader(file_ext)

            if not loader:
                logger.warning(
                    f"No loader found for extension {file_ext}. Skipping file..."
                )
                return None

            documents = loader(self.file_path.as_posix()).load()
            self._append_to_content(documents)
            return documents

        except Exception as e:
            logger.error(f"Error extracting content from {self.file_path}: {str(e)}")
            return None

    def _get_loader(self, file_ext: str) -> Optional[Callable]:
        """Get appropriate loader based on client type and file extension."""
        if file_ext in [".png", ".jpeg"] or (
            self.client == "docling" and file_ext in self.DOCLING_FORMATS
        ):
            from langchain_docling import DoclingLoader
            from langchain_docling.loader import ExportType

            return lambda fp: DoclingLoader(fp, export_type=ExportType.MARKDOWN)

        logger.warning(
            "Format not supported by DocLing or wrong client chosen. Falling back to LangChain."
        )
        return self.LANGCHAIN_LOADERS.get(file_ext)

    def _append_to_content(self, documents: list) -> None:
        """Append extracted content to the specified content file."""
        try:
            with open(self.content_path, "a", encoding="utf-8") as f:
                for doc in documents:
                    f.write(doc.page_content + "\n")
        except IOError as e:
            logger.error(f"Error writing to content file {self.content_path}: {str(e)}")
            raise

    def _get_file_ext(self) -> str:
        """Get file extension from file_path."""
        return self.file_path.suffix.lower()

    @property
    def supported_formats(self):
        return {
            "docling": self.DOCLING_FORMATS,
            "langchain": list(self.LANGCHAIN_LOADERS.keys()),
        }
