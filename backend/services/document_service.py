"""
Document Service for Lumina IQ RAG Backend.

Handles PDF extraction and preprocessing using LlamaIndex.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib
from llama_index.core import SimpleDirectoryReader, Document
from llama_index.readers.file import PDFReader
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("document_service")


class DocumentService:
    """Service for document extraction and preprocessing using LlamaIndex."""

    def __init__(self):
        self.pdf_reader = PDFReader()
        self.is_initialized = False

    def initialize(self) -> None:
        """Initialize document service."""
        try:
            logger.info("Initializing document service")

            # Ensure books directory exists
            books_dir = Path(settings.BOOKS_DIR)
            books_dir.mkdir(parents=True, exist_ok=True)

            self.is_initialized = True
            logger.info(f"Document service initialized successfully - books_dir: {str(books_dir)}")

        except Exception as e:
            logger.error(f"Failed to initialize document service: {str(e)} - error_type: {type(e).__name__}")
            self.is_initialized = False
            raise

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file for deduplication."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    async def extract_from_pdf(
        self, file_path: Path, extract_metadata: bool = True
    ) -> List[Document]:
        """Extract text and metadata from PDF using LlamaIndex."""
        if not self.is_initialized:
            raise RuntimeError("Document service not initialized")

        try:
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"Extracting content from PDF - file_path: {str(file_path)}, file_size_mb: {file_size_mb:.2f}")

            # Check if file is large and should use specialized handling
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            use_llamaindex_for_large = (
                settings.LLAMAINDEX_USE_FOR_LARGE_PDFS
                and file_size_mb > settings.LLAMAINDEX_LARGE_PDF_THRESHOLD_MB
            )

            if use_llamaindex_for_large:
                logger.info(f"Using LlamaIndex for large PDF processing - file_size_mb: {file_size_mb:.2f}")

            # Extract using LlamaIndex PDFReader
            documents = self.pdf_reader.load_data(file=file_path)

            # Compute file hash for deduplication
            file_hash = self._compute_file_hash(file_path)

            # Enrich documents with metadata
            for i, doc in enumerate(documents):
                doc.metadata.update(
                    {
                        "file_name": file_path.name,
                        "file_path": str(file_path),
                        "file_hash": file_hash,
                        "file_size_bytes": file_path.stat().st_size,
                        "page_number": i + 1,
                        "total_pages": len(documents),
                        "source": "pdf",
                    }
                )

            logger.info(f"Successfully extracted content from PDF - file_name: {file_path.name}, page_count: {len(documents)}, file_hash: {file_hash[:8]}")

            return documents

        except Exception as e:
            logger.error(f"Failed to extract content from PDF: {str(e)} - error_type: {type(e).__name__}, file_path: {str(file_path)}")
            raise

    async def extract_from_directory(
        self, directory_path: Path, file_pattern: str = "*.pdf"
    ) -> List[Document]:
        """Extract content from all PDFs in a directory."""
        if not self.is_initialized:
            raise RuntimeError("Document service not initialized")

        try:
            logger.info(f"Extracting content from directory - directory: {str(directory_path)}, pattern: {file_pattern}")

            # Use SimpleDirectoryReader for batch processing
            reader = SimpleDirectoryReader(
                input_dir=str(directory_path),
                required_exts=[".pdf"],
                recursive=False,
            )

            documents = reader.load_data()

            # Enrich with file hashes
            for doc in documents:
                if "file_path" in doc.metadata:
                    file_path = Path(doc.metadata["file_path"])
                    if file_path.exists():
                        file_hash = self._compute_file_hash(file_path)
                        doc.metadata["file_hash"] = file_hash

            logger.info(f"Successfully extracted content from directory - document_count: {len(documents)}, directory: {str(directory_path)}")

            return documents

        except Exception as e:
            logger.error(f"Failed to extract content from directory: {str(e)} - error_type: {type(e).__name__}, directory: {str(directory_path)}")
            raise

    async def validate_document(self, file_path: Path) -> Dict[str, Any]:
        """Validate document before processing."""
        try:
            if not file_path.exists():
                return {"valid": False, "error": "File does not exist"}

            if not file_path.is_file():
                return {"valid": False, "error": "Path is not a file"}

            if file_path.suffix.lower() != ".pdf":
                return {"valid": False, "error": "File is not a PDF"}

            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb == 0:
                return {"valid": False, "error": "File is empty"}

            # Compute file hash
            file_hash = self._compute_file_hash(file_path)

            return {
                "valid": True,
                "file_name": file_path.name,
                "file_size_mb": round(file_size_mb, 2),
                "file_hash": file_hash,
            }

        except Exception as e:
            logger.error(f"Failed to validate document: {str(e)} - error_type: {type(e).__name__}, file_path: {str(file_path)}")
            return {"valid": False, "error": str(e)}

    async def get_document_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from document without full processing."""
        try:
            validation = await self.validate_document(file_path)
            if not validation["valid"]:
                return validation

            # Quick metadata extraction
            documents = await self.extract_from_pdf(file_path, extract_metadata=True)

            return {
                "valid": True,
                "file_name": file_path.name,
                "file_size_mb": validation["file_size_mb"],
                "file_hash": validation["file_hash"],
                "page_count": len(documents),
                "total_characters": sum(len(doc.text) for doc in documents),
            }

        except Exception as e:
            logger.error(f"Failed to get document metadata: {str(e)} - error_type: {type(e).__name__}, file_path: {str(file_path)}")
            return {"valid": False, "error": str(e)}


# Global singleton instance
document_service = DocumentService()
