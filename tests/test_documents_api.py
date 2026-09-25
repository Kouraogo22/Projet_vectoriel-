from types import SimpleNamespace
import asyncio

from fastapi import FastAPI
import httpx

from api.routes import documents


def request(app: FastAPI, method: str, url: str, **kwargs) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(send())


class FakeStore:
    def __init__(self, source, storage_kind="original"):
        self.source = source
        self.storage_kind = storage_kind
        self.deleted = []

    def get_document_content(self, document_id):
        if document_id != "known":
            return None
        return {
            "document_id": document_id,
            "title": "Document",
            "category": "Test",
            "source": str(self.source),
            "original_filename": self.source.name,
            "storage_kind": self.storage_kind,
            "content": "contenu",
            "chunks_indexed": 1,
        }

    def delete_document(self, document_id):
        self.deleted.append(document_id)


def test_delete_document_removes_index_and_managed_file(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    stored = upload_dir / "document.txt"
    stored.write_text("contenu", encoding="utf-8")
    monkeypatch.setattr(documents, "UPLOAD_DIR", upload_dir)

    app = FastAPI()
    app.state.store = FakeStore(stored)
    app.include_router(documents.router)
    response = request(app, "DELETE", "/documents/known")

    assert response.status_code == 204
    assert app.state.store.deleted == ["known"]
    assert not stored.exists()


def test_upload_limit_is_enforced(tmp_path, monkeypatch):
    monkeypatch.setattr(documents, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(documents, "settings", SimpleNamespace(max_upload_size_mb=0))
    app = FastAPI()
    app.state.retriever = object()
    app.include_router(documents.router)

    response = request(
        app,
        "POST",
        "/documents",
        files={"file": ("document.txt", b"contenu", "text/plain")},
    )

    assert response.status_code == 400
    assert "limite" in response.json()["detail"]


def test_reconstructed_text_is_not_presented_as_original(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    stored = upload_dir / "reconstructed.txt"
    stored.write_text("contenu", encoding="utf-8")
    monkeypatch.setattr(documents, "UPLOAD_DIR", upload_dir)
    app = FastAPI()
    app.state.store = FakeStore(stored, storage_kind="reconstructed")
    app.include_router(documents.router)

    content = request(app, "GET", "/documents/known/content")
    download = request(app, "GET", "/documents/known/download")

    assert content.json()["original_available"] is False
    assert content.json()["original_is_reconstructed"] is True
    assert download.status_code == 404
