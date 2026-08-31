from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from api.models import DocumentContent, DocumentResponse, DocumentSummary

router = APIRouter(prefix="/documents", tags=["Documents"])
ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"


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
    stored_path = None
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        stored_path = UPLOAD_DIR / f"{uuid4().hex}_{original_filename}"
        stored_path.write_bytes(await file.read())
        display_title = title or Path(original_filename).stem
        document_id, chunks = request.app.state.retriever.index_document(
            stored_path,
            display_title,
            category,
            source=stored_path,
            original_filename=original_filename,
        )
        return DocumentResponse(document_id=document_id, title=display_title, chunks_indexed=chunks)
    except (ValueError, OSError) as exc:
        if stored_path:
            stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        if stored_path:
            stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail=f"Indexation indisponible : {exc}") from exc

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
    document["original_available"] = bool((path := managed_upload_path(document.get("source"))) and path.is_file())
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
    file_path = managed_upload_path(document.get("source"))
    if file_path is None or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Le fichier original n'est pas disponible.")
    return FileResponse(path=file_path, filename=document["original_filename"])

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, request: Request) -> None:
    try:
        request.app.state.store.delete_document(document_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Suppression impossible : {exc}") from exc
