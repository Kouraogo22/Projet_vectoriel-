from typing import Annotated
from pydantic import BaseModel, Field

CategoryValue = Annotated[str, Field(min_length=1, max_length=120)]
DocumentIdValue = Annotated[str, Field(min_length=1, max_length=200)]

class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)
    category: str | None = Field(default=None, max_length=120)
    categories: list[CategoryValue] | None = Field(default=None, max_length=50)
    document_ids: list[DocumentIdValue] | None = Field(default=None, max_length=100)

class SearchResult(BaseModel):
    score: float
    passage_id: str
    document_id: str
    text: str
    title: str
    category: str | None = None

class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]

class DocumentResponse(BaseModel):
    document_id: str
    title: str
    chunks_indexed: int

class DocumentSummary(BaseModel):
    document_id: str
    title: str
    category: str | None = None


class DocumentContent(DocumentSummary):
    """Contenu reconstitué à partir des passages indexés d'un document."""

    content: str
    chunks_indexed: int
    original_filename: str
    original_available: bool
    original_is_reconstructed: bool = False
