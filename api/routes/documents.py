from pathlib import Path
from tempfile import NamedTemporaryFile
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from api.models import DocumentResponse, DocumentSummary

router = APIRouter(prefix="/documents", tags=["Documents"])
ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def add_document(request: Request, file: UploadFile = File(...), title: str | None = Form(None), category: str | None = Form(None)) -> DocumentResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Formats acceptés : PDF, DOCX, TXT ou MD.")
    temporary_path = None
    try:
        with NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
            temporary.write(await file.read())
            temporary_path = Path(temporary.name)
        display_title = title or Path(file.filename or "document").stem
        document_id, chunks = request.app.state.retriever.index_document(temporary_path, display_title, category)
        return DocumentResponse(document_id=document_id, title=display_title, chunks_indexed=chunks)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Indexation indisponible : {exc}") from exc
    finally:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)

@router.get("", response_model=list[DocumentSummary])
def list_documents(request: Request) -> list[DocumentSummary]:
    try:
        return [DocumentSummary(**document) for document in request.app.state.store.list_documents()]
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Base vectorielle indisponible : {exc}") from exc

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, request: Request) -> None:
    try:
        request.app.state.store.delete_document(document_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Suppression impossible : {exc}") from exc
