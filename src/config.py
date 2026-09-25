"""Configuration centralisée de l'application."""
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key: str | None = os.getenv("QDRANT_API_KEY") or None
    collection_name: str = os.getenv("COLLECTION_NAME", "documents_semantiques")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "120"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "20"))
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))

settings = Settings()
