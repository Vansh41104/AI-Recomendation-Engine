from typing import Any, Dict, List
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from app.shared.config import settings
from app.shared.models import (
    RecommendRequest,
    RecommendResponse,
)
from app.services.chroma_service import ChromaService
from app.services.scraper_service import ScraperService

app = FastAPI(
    title="Recommendation Engine",
    description="API for Recommendation Engine",
    version="1.0.0"
)
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

chroma_service = ChromaService()
scraper_service = ScraperService()

@app.get("/")
async def root():
    index_file = static_dir / "index.html"
    return FileResponse(index_file)

@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "healthy"}


@app.post("/api/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest) -> RecommendResponse:
    try:
        top_k = 10
        search_results = chroma_service.search(request.query, top_k)
        
        ids = search_results.get("ids", [])
        metadatas = search_results.get("metadatas", [])
        
        if not ids:
            raise HTTPException(status_code=404, detail="No recommendations found")

        recommended_assessments = []
        
        for idx in range(len(ids)):
            metadata = metadatas[idx]
            
            url = metadata.get('url', '')
            name = url.split('/')[-2].replace('-', ' ').title() if url else "Assessment"
            
            adaptive_support = "Yes" if metadata.get('adaptive_support') else "No"
            remote_support = "Yes" if metadata.get('remote_support') else "No"
            
            test_type_raw = metadata.get('test_type', '')
            if isinstance(test_type_raw, str):
                test_types = [t.strip() for t in test_type_raw.replace(';', ',').split(',') if t.strip()]
            elif isinstance(test_type_raw, list):
                test_types = test_type_raw
            else:
                test_types = []
            
            recommendation = {
                "url": url,
                "name": name,
                "adaptive_support": adaptive_support,
                "description": metadata.get('description', ''),
                "duration": metadata.get('duration', ''),
                "remote_support": remote_support,
                "test_type": test_types
            }
            recommended_assessments.append(recommendation)
        
        return RecommendResponse(
            recommended_assessments=recommended_assessments
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


@app.on_event("shutdown")
def shutdown_event():
    scraper_service.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.GATEWAY_HOST or "0.0.0.0",
        port=settings.GATEWAY_PORT or 8000
    )
