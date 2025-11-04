import hashlib
from pathlib import Path
from typing import Optional
from utils.logger import get_logger

# Use enhanced logger
logger = get_logger("file_hash")


class FileHashService:
    """Service for calculating file hashes to detect duplicate uploads"""

    @staticmethod
    def calculate_file_hash(file_path: str, algorithm: str = "sha256") -> Optional[str]:
        """
        Calculate hash of a file

        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use (md5, sha1, sha256)

        Returns:
            Hexadecimal hash string or None if error
        """
        try:
            hash_obj = hashlib.new(algorithm)

            # Read file in chunks to handle large files
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    hash_obj.update(chunk)

            file_hash = hash_obj.hexdigest()
            logger.debug(f"Calculated hash: algorithm={algorithm}, file_path={file_path}, hash_value={file_hash[:16]}")
            return file_hash

        except Exception as e:
            logger.error(f"Failed to calculate hash: file_path={file_path}, error={str(e)}")
            return None

    @staticmethod
    def calculate_content_hash(content: bytes, algorithm: str = "sha256") -> str:
        """
        Calculate hash of content bytes

        Args:
            content: File content as bytes
            algorithm: Hash algorithm to use

        Returns:
            Hexadecimal hash string
        """
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(content)
        return hash_obj.hexdigest()


file_hash_service = FileHashService()
