import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import asdict
import pandas as pd
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.shared.config import settings
from app.shared.models import EmbeddingRecord
from app.shared.utils import slugify, parse_bool


class EmbeddingService:
    
    @staticmethod
    def load_assessments(csv_path: Path) -> List[EmbeddingRecord]:
        df = pd.read_csv(csv_path)
        required_columns = {
            "url",
            "adaptive_support",
            "description",
            "duration",
            "remote_support",
            "test_type",
        }
        missing = required_columns - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns in CSV: {missing}")

        records: List[EmbeddingRecord] = []
        for _, row in df.iterrows():
            test_types = row["test_type"]
            
            if isinstance(test_types, str):
                try:
                    parsed = json.loads(test_types)
                    if isinstance(parsed, list):
                        test_types = parsed
                    else:
                        test_types = [value.strip() for value in str(test_types).split(",") if value.strip()]
                except json.JSONDecodeError:
                    cleaned = str(test_types).strip()
                    if cleaned.startswith("[") and cleaned.endswith("]"):
                        inner = cleaned[1:-1]
                        split_values = [
                            part.strip().strip("'\"")
                            for part in inner.split(",")
                            if part.strip().strip("'\"")
                        ]
                        test_types = split_values
                    else:
                        test_types = [value.strip() for value in cleaned.split(",") if value.strip()]
            elif pd.isna(test_types):
                test_types = []

            record = EmbeddingRecord(
                id=slugify(str(row["url"])),
                url=str(row["url"]),
                description=str(row["description"] or ""),
                duration=str(row["duration"] or ""),
                adaptive_support=parse_bool(row.get("adaptive_support")),
                remote_support=parse_bool(row.get("remote_support")),
                test_type=list(test_types) if isinstance(test_types, list) else [str(test_types)],
            )
            records.append(record)
        
        return records
    
    @staticmethod
    def persist_payload(records: List[EmbeddingRecord], output_path: Path) -> None:
        payload = [asdict(record) for record in records]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    
    @staticmethod
    def upsert_into_chroma(
        collection_name: str,
        persist_dir: str,
        records: List[EmbeddingRecord]
    ) -> None:
        client = chromadb.PersistentClient(path=persist_dir)
        embedding_func = SentenceTransformerEmbeddingFunction(
            model_name=settings.SENTENCE_TRANSFORMER_MODEL
        )
        coll = client.get_or_create_collection(
            name=collection_name,
            metadata={"source": "shl-assessments"},
            embedding_function=embedding_func,
        )

        ids = [record.id for record in records]
        documents = [record.to_document() for record in records]
        metadatas = [record.to_metadata() for record in records]

        if not ids:
            return

        coll.upsert(ids=ids, documents=documents, metadatas=metadatas)
    
    def build_embeddings(
        self, 
        csv_path: str, 
        collection_name: Optional[str] = None, 
        persist_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        csv_file = Path(csv_path)
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        
        try:
            records = self.load_assessments(csv_file)
            
            if not records:
                return {
                    "records_processed": 0,
                    "collection_name": collection_name,
                    "message": "No records loaded from CSV"
                }
            
            payload_path = Path("data/shl_embeddings_payload.json")
            self.persist_payload(records, payload_path)
            
            self.upsert_into_chroma(collection_name, persist_dir, records)
            
            return {
                "records_processed": len(records),
                "collection_name": collection_name,
                "message": f"Successfully built and loaded {len(records)} embeddings"
            }
        
        except ValueError as e:
            raise
        except Exception as e:
            raise
