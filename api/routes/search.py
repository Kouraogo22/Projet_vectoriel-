from fastapi import APIRouter, HTTPException, Request
from api.models import SearchRequest, SearchResponse, SearchResult

router = APIRouter(prefix="/search", tags=["Recherche"])

@router.post("", response_model=SearchResponse)
def search(request: SearchRequest, app_request: Request) -> SearchResponse:
    try:
        results = app_request.app.state.retriever.search(
            request.query,
            request.limit,
            category=request.category,
            categories=request.categories,
            document_ids=request.document_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Recherche indisponible : {exc}") from exc
    return SearchResponse(query=request.query, results=[SearchResult(**result) for result in results])
