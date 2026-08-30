from pydantic import BaseModel, Field

class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)
    category: str | None = Field(default=None, max_length=120)
    categories: list[str] | None = None
    document_ids: list[str] | None = None

class SearchResult(BaseModel):
    score: float
    passage_id: str
    document_id: str
    text: str
    title: str
    category: str | None = None
    source: str | None = None

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
    source: str | None = None
