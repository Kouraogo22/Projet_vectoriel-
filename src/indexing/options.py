from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.config import settings


class IndexOptions(BaseModel):
    """Paramètres enregistrés avec chaque génération de l'index."""
    model_config = ConfigDict(extra="forbid")
    chunk_size: int = Field(default=settings.chunk_size, ge=1, le=10000)
    chunk_overlap: int = Field(default=settings.chunk_overlap, ge=0, le=9999)
    embedding_model: str = Field(default=settings.embedding_model, min_length=1, max_length=200,
                                 pattern=r"^[\w.-]+/[\w.-]+$")
    normalize_embeddings: bool = True
    batch_size: int = Field(default=32, ge=1, le=256)
    upload_batch_size: int = Field(default=128, ge=1, le=1024)
    device: Literal["cpu", "cuda", "mps"] = "cpu"
    max_seq_length: int | None = Field(default=None, ge=8, le=32768)
    clean_text: bool = True
    distance: Literal["Cosine", "Dot", "Euclid", "Manhattan"] = "Cosine"
    on_disk: bool = False
    hnsw_m: int = Field(default=16, ge=0, le=128)
    ef_construct: int = Field(default=100, ge=4, le=1024)
    full_scan_threshold: int = Field(default=10000, ge=0, le=1000000)
    indexing_threshold: int = Field(default=10000, ge=0, le=1000000)

    @model_validator(mode="after")
    def validate_overlap(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Le chevauchement doit être inférieur à la taille des passages.")
        return self


class ReindexRequest(IndexOptions):
    source_mode: Literal["originals_preferred", "indexed_text"] = "originals_preferred"
    allow_reconstructed: bool = True
    collection_prefix: str = Field(default="documents_reindex", min_length=1, max_length=60,
                                   pattern=r"^[a-zA-Z0-9_-]+$")
