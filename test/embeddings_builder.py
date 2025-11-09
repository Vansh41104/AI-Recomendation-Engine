import json
import re
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import pandas as pd
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import os


CHROMA_COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION_NAME", "shl_assessments")
CHROMA_PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", "chroma_db")
SENTENCE_TRANSFORMER_MODEL = os.environ.get("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")


@dataclass
class EmbeddingRecord:
    id: str
    url: str
    description: str
    duration: str
    adaptive_support: bool
    remote_support: bool
    test_type: List[str]

    def to_document(self) -> str:
        bullet_types = ", ".join(self.test_type)
        return (
            f"URL: {self.url}\n"
            f"Duration: {self.duration or 'Unspecified'}\n"
            f"Adaptive Support: {'Yes' if self.adaptive_support else 'No'}\n"
            f"Remote Support: {'Yes' if self.remote_support else 'No'}\n"
            f"Test Types: {bullet_types or 'Unspecified'}\n"
            f"Description: {self.description}"
        )

    def to_metadata(self) -> dict:
        metadata = asdict(self)
        metadata.pop("id")
        if isinstance(metadata.get("test_type"), list):
            metadata["test_type"] = ", ".join(metadata["test_type"])
        return metadata


def slugify(value: str) -> str:
    safe = (
        value.lower()
        .replace("https://", "")
        .replace("http://", "")
        .replace("/", "-")
        .replace("_", "-")
    )
    safe = re.sub(r"[^a-z0-9-]", "", safe)
    safe = re_collapse_hyphens(safe)

    hash_suffix = hashlib.md5(value.encode()).hexdigest()[:8]
    
    if len(safe) > 48:
        return f"{safe[:48]}-{hash_suffix}"
    else:
        return f"{safe}-{hash_suffix}"


def re_collapse_hyphens(value: str) -> str:
    result = []
    previous_hyphen = False
    for char in value:
        if char == "-":
            if not previous_hyphen:
                result.append(char)
            previous_hyphen = True
        else:
            previous_hyphen = False
            result.append(char)
    return "".join(result).strip("-")


def parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    try:
        import pandas as pd
        if pd.isna(value):
            return False
    except ImportError:
        pass
    normalized = str(value).strip().lower()
    return normalized in {"true", "1", "yes", "y"}


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


def persist_payload(records: List[EmbeddingRecord], output_path: Path) -> None:
    payload = [asdict(record) for record in records]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def upsert_into_chroma(
    collection_name: str,
    persist_dir: str,
    records: List[EmbeddingRecord]
) -> None:
    client = chromadb.PersistentClient(path=persist_dir)
    embedding_func = SentenceTransformerEmbeddingFunction(
        model_name=SENTENCE_TRANSFORMER_MODEL
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
    csv_path: str, 
    collection_name: Optional[str] = None, 
    persist_dir: Optional[str] = None
) -> Dict[str, Any]:
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    collection_name = collection_name or CHROMA_COLLECTION_NAME
    persist_dir = persist_dir or CHROMA_PERSIST_DIR
    
    try:
        records = load_assessments(csv_file)
        
        if not records:
            return {
                "records_processed": 0,
                "collection_name": collection_name,
                "message": "No records loaded from CSV"
            }
        
        payload_path = Path("data/shl_embeddings_payload.json")
        persist_payload(records, payload_path)
        
        upsert_into_chroma(collection_name, persist_dir, records)
        
        return {
            "records_processed": len(records),
            "collection_name": collection_name,
            "message": f"Successfully built and loaded {len(records)} embeddings"
        }
    
    except ValueError as e:
        raise
    except Exception as e:
        raise


def get_collection_stats(
    collection_name: str = None, 
    persist_dir: str = None
) -> Dict[str, Any]:
    collection_name = collection_name or CHROMA_COLLECTION_NAME
    persist_dir = persist_dir or CHROMA_PERSIST_DIR
    
    try:
        client = chromadb.PersistentClient(path=persist_dir)
        embedding_func = SentenceTransformerEmbeddingFunction(
            model_name=SENTENCE_TRANSFORMER_MODEL
        )
        coll = client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_func,
        )
        
        count = coll.count()
        
        return {
            "collection_name": collection_name,
            "count": count,
            "model": SENTENCE_TRANSFORMER_MODEL,
            "persist_dir": persist_dir,
        }
    
    except Exception as e:
        raise


if __name__ == "__main__":
    csv_path = "data/shl_assessments.csv"
    
    result = build_embeddings(csv_path)
    print(f"Embedding result: {result}")
    
    stats = get_collection_stats()
    print(f"Collection stats: {stats}")
