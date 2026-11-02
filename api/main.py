from fastapi import FastAPI, HTTPException, Response
from contextlib import asynccontextmanager
import fcntl
from starlette.concurrency import run_in_threadpool
from api.routes import documents, search, reindex
from pathlib import Path
from src.indexing.jobs import ReindexManager
from src.config import settings
from src.database import VectorStore
from src.embeddings import EmbeddingEncoder
from src.search import SemanticRetriever

@asynccontextmanager
async def lifespan(app):
    state_dir = Path(__file__).resolve().parents[1] / "data" / "index_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    with (state_dir / "worker.lock").open("a") as guard:
        try:
            fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("La réindexation nécessite un seul processus API par dossier index_state.") from exc
        app.state.reindex = ReindexManager(app, state_dir, documents.UPLOAD_DIR)
        try:
            yield
        finally:
            app.state.reindex.cancel_event.set()
            if app.state.reindex.thread:
                await run_in_threadpool(app.state.reindex.thread.join)
            fcntl.flock(guard, fcntl.LOCK_UN)


app = FastAPI(title="API de recherche sémantique", version="1.1.0", lifespan=lifespan)
app.state.store = VectorStore(settings.qdrant_url, settings.qdrant_api_key, settings.collection_name)
app.state.retriever = SemanticRetriever(app.state.store, EmbeddingEncoder(settings.embedding_model))


@app.get("/", tags=["Santé"])
def home() -> dict[str, str]:
    return {"message": "API de recherche sémantique opérationnelle"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Évite une erreur 404 lorsque le navigateur demande l'icône du site."""
    return Response(status_code=204)


@app.get("/health", tags=["Santé"])
def health() -> dict[str, str]:
    try:
        collection_exists = app.state.store.client.collection_exists(app.state.store.collection_name)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="La base vectorielle est indisponible.") from exc
    return {
        "status": "ok",
        "collection": app.state.store.collection_name,
        "collection_status": "available" if collection_exists else "not_created",
    }

app.include_router(search.router)
app.include_router(documents.router)

app.include_router(reindex.router)
