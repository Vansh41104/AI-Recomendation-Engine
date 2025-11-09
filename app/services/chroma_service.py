from typing import Any, Dict
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.shared.config import settings


class ChromaService:
    
    def __init__(self):
        self.client = self.initialize_client()
        self.collection, self.embedding_function = self.get_collection()
    
    def initialize_client(self) -> chromadb.api.ClientAPI:
        client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        return client
    
    def get_collection(self):
        embedding_function = SentenceTransformerEmbeddingFunction(
            model_name=settings.SENTENCE_TRANSFORMER_MODEL
        )
        collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"source": "shl-assessments"},
            embedding_function=embedding_function,
        )
        return collection, embedding_function
    
    def search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        try:
            results = self.collection.query(
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
    
    def get_collection_stats(
        self, 
        collection_name: str = None, 
        persist_dir: str = None
    ) -> Dict[str, Any]:
        collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        
        try:
            client = chromadb.PersistentClient(path=persist_dir)
            embedding_func = SentenceTransformerEmbeddingFunction(
                model_name=settings.SENTENCE_TRANSFORMER_MODEL
            )
            coll = client.get_or_create_collection(
                name=collection_name,
                embedding_function=embedding_func,
            )
            
            count = coll.count()
            
            return {
                "collection_name": collection_name,
                "count": count,
                "model": settings.SENTENCE_TRANSFORMER_MODEL,
                "persist_dir": persist_dir,
            }
        
        except Exception as e:
            raise
