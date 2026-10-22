"""Application configuration loaded from environment variables."""

import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from the backend directory
_backend_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(_backend_dir / ".env")


class Settings:
    """Central configuration for the application."""

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    MAX_ROWS: int = int(os.getenv("MAX_ROWS", "1000000"))
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", tempfile.gettempdir())
    ALLOWED_EXTENSIONS: list[str] = [".csv"]
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    def __repr__(self) -> str:
        masked_key = (
            f"{self.GEMINI_API_KEY[:4]}...{self.GEMINI_API_KEY[-4:]}"
            if len(self.GEMINI_API_KEY) > 8
            else ("***" if self.GEMINI_API_KEY else "<not set>")
        )
        return (
            f"Settings(GEMINI_API_KEY={masked_key}, "
            f"MAX_FILE_SIZE_MB={self.MAX_FILE_SIZE_MB}, "
            f"MAX_ROWS={self.MAX_ROWS}, "
            f"UPLOAD_DIR={self.UPLOAD_DIR})"
        )


settings = Settings()
