from fastapi import APIRouter, HTTPException, Request
from src.indexing.options import ReindexRequest

router = APIRouter(prefix="/reindex", tags=["Réindexation"])


@router.get("")
def status(request: Request):
    return request.app.state.reindex.snapshot()


@router.post("", status_code=202)
def start(parameters: ReindexRequest, request: Request):
    try:
        return request.app.state.reindex.start(parameters)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/cancel")
def cancel(request: Request):
    try:
        return request.app.state.reindex.cancel()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


async def document_mutation(request: Request):
    manager = getattr(request.app.state, "reindex", None)
    if manager is None:
        yield
        return
    guard = manager.mutation()
    try:
        guard.__enter__()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    try:
        yield
    finally:
        guard.__exit__(None, None, None)
