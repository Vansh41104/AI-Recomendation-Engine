import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.chroma_service import ChromaService

DEFAULT_INPUT_FILE = "dataset/test.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch SHL recommendation queries")
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT_FILE,
        help="Path to input CSV containing a 'query' column",
    )
    parser.add_argument(
        "--output",
        default="output_recommendations.csv",
        help="Output CSV path",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=1,
        help="Number of recommendations to request for each query",
    )
    return parser.parse_args()


def load_queries(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")
    df = pd.read_csv(path)
    
    query_col = None
    for col in df.columns:
        if col.lower() == "query":
            query_col = col
            break
    
    if query_col is None:
        raise ValueError("Input CSV must contain a 'Query' column")
    
    queries = [str(value).strip() for value in df[query_col].dropna().tolist() if str(value).strip()]
    if not queries:
        raise ValueError("No queries found in input file")
    return queries


def fetch_recommendations(chroma_service: ChromaService, query: str, top_k: int) -> List[Dict[str, Any]]:
    try:
        search_results = chroma_service.search(query, top_k)
        
        ids = search_results.get("ids", [])
        distances = search_results.get("distances", [])
        metadatas = search_results.get("metadatas", [])
        
        if not ids:
            return []
        
        recommendations = []
        
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
                "test_type": test_types,
                "distance": distances[idx] if idx < len(distances) else None
            }
            recommendations.append(recommendation)
        
        return recommendations[:top_k]
    
    except Exception as e:
        return []


def write_output(path: Path, queries: List[str], recommendations: List[List[Dict[str, Any]]], top_k: int) -> None:
    rows = []
    for query, recs in zip(queries, recommendations):
        if recs:
            rec = recs[0]
            row = {
                "Query": query,
                "Assessment_url": rec.get("url", "")
            }
            rows.append(row)
        else:
            rows.append({
                "Query": query,
                "Assessment_url": ""
            })
    
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    print(f"Results written to: {path}")


def process_queries(chroma_service: ChromaService, queries: List[str], top_k: int) -> List[List[Dict[str, Any]]]:
    all_recommendations: List[List[Dict[str, Any]]] = []
    
    for query in queries:
        recs = fetch_recommendations(chroma_service, query, top_k)
        all_recommendations.append(recs)
    
    return all_recommendations


def main() -> None:
    args = parse_args()

    project_root = Path(__file__).parent.parent
    input_path = Path(args.input) if Path(args.input).is_absolute() else project_root / args.input
    output_path = Path(args.output) if Path(args.output).is_absolute() else project_root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    queries = load_queries(input_path)
    chroma_service = ChromaService()
    all_recommendations = process_queries(chroma_service, queries, args.top_k)
    write_output(output_path, queries, all_recommendations, args.top_k)


if __name__ == "__main__":
    main()
