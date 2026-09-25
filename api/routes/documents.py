from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from api.models import DocumentContent, DocumentResponse, DocumentSummary
from src.config import settings

router = APIRouter(prefix="/documents", tags=["Documents"])
ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"
UPLOAD_CHUNK_SIZE = 1024 * 1024


def managed_upload_path(source: str | None) -> Path | None:
    """N'autorise le téléchargement que des fichiers conservés dans data/uploads."""
    if not source:
        return None
    candidate = Path(source).resolve()
    try:
        candidate.relative_to(UPLOAD_DIR.resolve())
    except ValueError:
        return None
    return candidate

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def add_document(request: Request, file: UploadFile = File(...), title: str | None = Form(None), category: str | None = Form(None)) -> DocumentResponse:
    original_filename = Path(file.filename or "document").name
    suffix = Path(original_filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Formats acceptés : PDF, DOCX, TXT ou MD.")
    if title and len(title.strip()) > 240:
        raise HTTPException(status_code=400, detail="Le titre ne doit pas dépasser 240 caractères.")
    if category and len(category.strip()) > 120:
        raise HTTPException(status_code=400, detail="La catégorie ne doit pas dépasser 120 caractères.")
    stored_path = None
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        safe_filename = original_filename[-180:]
        stored_path = UPLOAD_DIR / f"{uuid4().hex}_{safe_filename}"
        written = 0
        with stored_path.open("wb") as destination:
            while chunk := await file.read(UPLOAD_CHUNK_SIZE):
                written += len(chunk)
                if written > settings.max_upload_size_mb * 1024 * 1024:
                    raise ValueError(
                        f"Le fichier dépasse la limite de {settings.max_upload_size_mb} Mo."
                    )
                destination.write(chunk)
        if written == 0:
            raise ValueError("Le fichier transmis est vide.")
        display_title = title.strip() if title and title.strip() else Path(original_filename).stem
        normalized_category = category.strip() if category and category.strip() else None
        document_id, chunks = await run_in_threadpool(
            request.app.state.retriever.index_document,
            stored_path,
            display_title,
            normalized_category,
            stored_path,
            original_filename,
        )
        return DocumentResponse(document_id=document_id, title=display_title, chunks_indexed=chunks)
    except (ValueError, OSError) as exc:
        if stored_path:
            stored_path.unlink(missing_ok=True)
        detail = str(exc) if isinstance(exc, ValueError) else "Le fichier n'a pas pu être enregistré."
        raise HTTPException(status_code=400, detail=detail) from exc
    except Exception as exc:
        if stored_path:
            stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail="L'indexation est temporairement indisponible.") from exc

@router.get("", response_model=list[DocumentSummary])
def list_documents(request: Request) -> list[DocumentSummary]:
    try:
        return [DocumentSummary(**document) for document in request.app.state.store.list_documents()]
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Base vectorielle indisponible : {exc}") from exc


@router.get("/{document_id}/content", response_model=DocumentContent)
def get_document_content(document_id: str, request: Request) -> DocumentContent:
    """Retourne le texte d'un document, reconstitué depuis ses passages indexés."""
    try:
        document = request.app.state.store.get_document_content(document_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Lecture du document impossible : {exc}") from exc
    if document is None:
        raise HTTPException(status_code=404, detail="Document introuvable dans la base vectorielle.")
    path = managed_upload_path(document.get("source"))
    document["original_is_reconstructed"] = document.get("storage_kind") == "reconstructed"
    document["original_available"] = bool(
        path and path.is_file() and not document["original_is_reconstructed"]
    )
    return DocumentContent(**document)


@router.get("/{document_id}/download")
def download_original(document_id: str, request: Request) -> FileResponse:
    """Télécharge le fichier original lorsqu'il est conservé dans le stockage local."""
    try:
        document = request.app.state.store.get_document_content(document_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Lecture du document impossible : {exc}") from exc
    if document is None:
        raise HTTPException(status_code=404, detail="Document introuvable dans la base vectorielle.")
    if document.get("storage_kind") == "reconstructed":
        raise HTTPException(status_code=404, detail="Le fichier original n'est pas disponible.")
    file_path = managed_upload_path(document.get("source"))
    if file_path is None or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Le fichier original n'est pas disponible.")
    return FileResponse(path=file_path, filename=document["original_filename"])

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, request: Request) -> None:
    file_path = None
    pending_path = None
    try:
        document = request.app.state.store.get_document_content(document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document introuvable dans la base vectorielle.")
        file_path = managed_upload_path(document.get("source"))
        if file_path and file_path.is_file():
            pending_path = file_path.with_name(f".{file_path.name}.{uuid4().hex}.deleting")
            file_path.replace(pending_path)
        request.app.state.store.delete_document(document_id)
        if pending_path:
            pending_path.unlink(missing_ok=True)
    except HTTPException:
        raise
    except Exception as exc:
        if pending_path and pending_path.exists() and file_path is not None:
            pending_path.replace(file_path)
        raise HTTPException(status_code=503, detail="La suppression est temporairement indisponible.") from exc
