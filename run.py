import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional
import uvicorn
from app.shared.config import settings


def serve(args):
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


def build_embeddings(args):
    from app.services.embedding_service import EmbeddingService
    
    csv_path_obj = Path(args.csv_path)
    if not csv_path_obj.exists():
        print(f"CSV file not found: {args.csv_path}")
        sys.exit(1)
    
    try:
        embedding_service = EmbeddingService()
        result = embedding_service.build_embeddings(
            csv_path=args.csv_path,
            collection_name=args.collection_name,
            persist_dir=args.persist_dir
        )
        print(f"Embeddings built: {result['records_processed']} records")
    except Exception as e:
        print(f"Failed to build embeddings: {str(e)}")
        sys.exit(1)


def scrape(args):
    from app.services.scraper_service import ScraperService
    
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Dataset file not found: {args.dataset}")
        sys.exit(1)
    
    try:
        scraper_service = ScraperService()
        result = scraper_service.scrape_and_save_from_dataset(
            dataset_path=str(dataset_path),
            limit=args.limit,
            output_path=args.output
        )
        
        if result.get("saved"):
            print(f"Scraped {result['count']} assessments to {result['path']}")
    except Exception as e:
        print(f"Failed to scrape: {str(e)}")
        sys.exit(1)


def health(args):
    import httpx
    
    url = f"http://{args.host}:{args.port}/health"
    
    async def check_health():
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    print(f"Status: {data.get('status')}")
                else:
                    print(f"ERROR (status {response.status_code})")
            except Exception as e:
                print(f"UNAVAILABLE: {str(e)}")
    
    asyncio.run(check_health())


def stats(args):
    from app.services.chroma_service import ChromaService
    
    try:
        chroma_service = ChromaService()
        result = chroma_service.get_collection_stats(args.collection_name, args.persist_dir)
        print(f"Collection: {result['collection_name']}, Count: {result['count']}")
    except Exception as e:
        print(f"Failed to get stats: {str(e)}")
        sys.exit(1)


def search(args):
    from app.services.chroma_service import ChromaService
    
    try:
        chroma_service = ChromaService()
        results = chroma_service.search(args.query, args.top_k)
        
        for i, (doc_id, distance, metadata, document) in enumerate(zip(
            results['ids'], 
            results['distances'], 
            results['metadatas'],
            results['documents']
        ), 1):
            print(f"Result #{i} (Score: {distance:.4f})")
            print(f"URL: {metadata.get('url')}")
            print(f"Duration: {metadata.get('duration')}")
            print(f"Test Type: {metadata.get('test_type')}")
            print()
    except Exception as e:
        print(f"Search failed: {str(e)}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="SHL Recommendation Engine CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True
    
    serve_parser = subparsers.add_parser('serve')
    serve_parser.add_argument('--host', default='0.0.0.0')
    serve_parser.add_argument('--port', type=int, default=8000)
    serve_parser.add_argument('--reload', action='store_true')
    serve_parser.set_defaults(func=serve)
    
    build_parser = subparsers.add_parser('build-embeddings')
    build_parser.add_argument('--csv-path', default='data/shl_assessments.csv')
    build_parser.add_argument('--collection-name', default=None)
    build_parser.add_argument('--persist-dir', default=None)
    build_parser.set_defaults(func=build_embeddings)
    
    scrape_parser = subparsers.add_parser('scrape')
    scrape_parser.add_argument('--dataset', default='dataset/Gen_AI Dataset.csv')
    scrape_parser.add_argument('--output', default='data/shl_assessments.csv')
    scrape_parser.add_argument('--limit', type=int, default=None)
    scrape_parser.set_defaults(func=scrape)

    health_parser = subparsers.add_parser('health')
    health_parser.add_argument('--host', default='localhost')
    health_parser.add_argument('--port', type=int, default=8000)
    health_parser.set_defaults(func=health)

    stats_parser = subparsers.add_parser('stats')
    stats_parser.add_argument('--collection-name', default=None)
    stats_parser.add_argument('--persist-dir', default=None)
    stats_parser.set_defaults(func=stats)

    search_parser = subparsers.add_parser('search')
    search_parser.add_argument('query')
    search_parser.add_argument('--top-k', type=int, default=5)
    search_parser.set_defaults(func=search)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
