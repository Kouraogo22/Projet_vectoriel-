from fastapi import FastAPI
from api.routes import documents, search
from src.config import settings
from src.database import VectorStore
from src.embeddings import EmbeddingEncoder
from src.search import SemanticRetriever

app = FastAPI(title="API de recherche sémantique", version="1.0.0")
app.state.store = VectorStore(settings.qdrant_url, settings.qdrant_api_key, settings.collection_name)
app.state.retriever = SemanticRetriever(app.state.store, EmbeddingEncoder(settings.embedding_model))

@app.get("/", tags=["Santé"])
def home() -> dict[str, str]:
    return {"message": "API de recherche sémantique opérationnelle"}

@app.get("/health", tags=["Santé"])
def health() -> dict[str, str]:
    return {"status": "ok", "collection": settings.collection_name}

app.include_router(search.router)
app.include_router(documents.router)
