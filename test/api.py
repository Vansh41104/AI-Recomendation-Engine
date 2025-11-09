import os
from typing import Any, Dict, List
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction


CHROMA_COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION_NAME", "shl_assessments")
CHROMA_PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", "chroma_db")
SENTENCE_TRANSFORMER_MODEL = os.environ.get("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")
GATEWAY_HOST = os.environ.get("GATEWAY_HOST", "0.0.0.0")
GATEWAY_PORT = int(os.environ.get("GATEWAY_PORT", "8000"))


class RecommendRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Natural language query")


class RecommendationItem(BaseModel):
    url: str = Field(..., description="Valid URL to the assessment resource")
    name: str = Field(..., description="Name of the assessment")
    adaptive_support: str = Field(..., description="Either 'Yes' or 'No' indicating if the assessment supports adaptive testing")
    description: str = Field(..., description="Detailed description of the assessment")
    duration: str = Field(..., description="Duration of the assessment in minutes")
    remote_support: str = Field(..., description="Either 'Yes' or 'No' indicating if the assessment can be taken remotely")
    test_type: List[str] = Field(..., description="Categories or types of the assessment")


class RecommendResponse(BaseModel):
    recommended_assessments: List[RecommendationItem]


def initialize_chroma_client() -> chromadb.api.ClientAPI:
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return client


def get_chroma_collection(client: chromadb.api.ClientAPI):
    embedding_function = SentenceTransformerEmbeddingFunction(
        model_name=SENTENCE_TRANSFORMER_MODEL
    )
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"source": "shl-assessments"},
        embedding_function=embedding_function,
    )
    return collection, embedding_function


def search_chroma(collection, query: str, top_k: int = 5) -> Dict[str, Any]:
    try:
        results = collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        documents = results.get("documents", [[]])[0]
        
        return {
            "ids": ids,
            "distances": distances,
            "metadatas": metadatas,
            "documents": documents,
        }
    except Exception as e:
        raise


def create_api_app():
    app = FastAPI(
        title="Recommendation Engine",
        description="API for Recommendation Engine",
        version="1.0.0"
    )
    static_dir = Path(__file__).parent.parent / "app" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    client = initialize_chroma_client()
    collection, embedding_function = get_chroma_collection(client)

    @app.get("/")
    async def root():
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Recommendation Engine API"}

    @app.get("/health")
    def health_check() -> Dict[str, str]:
        return {"status": "healthy"}

    @app.post("/api/recommend", response_model=RecommendResponse)
    async def recommend(request: RecommendRequest) -> RecommendResponse:
        try:
            top_k = 10
            search_results = search_chroma(collection, request.query, top_k)
            
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

    return app


def run_api_server(host: str = None, port: int = None):
    import uvicorn
    app = create_api_app()
    host = host or GATEWAY_HOST or "0.0.0.0"
    port = port or GATEWAY_PORT or 8000
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_api_server()
