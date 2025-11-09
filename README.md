# SHL Assessment Recommendation System

An intelligent recommendation system that helps hiring managers and recruiters find the right SHL assessments for their roles. The system uses natural language queries or job descriptions to recommend relevant assessments from SHL's product catalog.

## Architecture

This project uses a modular architecture with the following components:

- **FastAPI Application** - RESTful API for recommendations
- **ChromaDB** - Vector database for semantic search
- **Sentence Transformers** - Embedding generation for semantic similarity
- **Web Scraper** - Crawls SHL assessment data from the product catalog
- **CLI Tools** - Command-line interface for data management

## Quick Start

### Prerequisites

- **Python 3.12**
- **uv** - Fast Python package installer and resolver ([Install uv](https://github.com/astral-sh/uv))


### Installation with uv

1. **Clone the repository**:
   ```powershell
   git clone [<repository-url>](https://github.com/Vansh41104/AI-Recomendation-Engine.git)
   cd AI-Recomendation-Engine
   ```

2. **Install dependencies with uv**:
   ```powershell
   uv sync
   ```

3. **Running the server and Scraper**:
   ```powershell
   uv run python -m app.main
   uv run run.py scrape --dataset "dataset/Gen_AI Dataset.csv"
   ```


## Setup Pipeline

### Step 1: Scrape Assessment Data

Scrape SHL assessments from the product catalog:

```powershell
uv run run.py scrape --dataset "dataset/Gen_AI Dataset.csv" --output "data/shl_assessments.csv"
```
### Step 2: Build Embeddings

Generate vector embeddings for semantic search:

```powershell
uv run run.py build-embeddings --csv-path "data/shl_assessments.csv"
```

### Step 3: Start the API Server

```powershell
uv run run.py serve
```


## API Endpoints

### 1. Health Check Endpoint

**GET** `/health`

Verifies the API is running.

**Response:**
```json
{
  "status": "healthy"
}
```


### 2. Assessment Recommendation Endpoint

**POST** `/api/recommend`

Accepts a job description or natural language query and returns recommended relevant assessments (minimum 1, maximum 10).

**Request Body:**
```json
{
  "query": "I am hiring for Java developers who can also collaborate effectively with my business teams."
}
```

**Response:**
```json
{
  "recommended_assessments": [
    {
      "url": "https://www.shl.com/solutions/products/product-catalog/assessment-name/",
      "name": "Assessment Name",
      "adaptive_support": "Yes",
      "description": "Detailed description of the assessment",
      "duration": "45 minutes",
      "remote_support": "Yes",
      "test_type": ["K", "P"]
    }
  ]
}
```

## Batch Processing

Generate predictions for multiple queries at once:

```powershell
uv run scripts/batch_query.py --input dataset/test.csv --output dataset/vansh_bhatnagar.csv
```

The output CSV will be in the format required for submission:
```csv
Query,Assessment_url
Query 1,Recommendation 1 (URL)
Query 1,Recommendation 2 (URL)
Query 1,Recommendation 3 (URL)
...
```

## CLI Commands

The project includes a CLI tool for common operations:

```powershell
# Start API server
uv run run.py serve 

# Scrape assessments
uv run run.py scrape

# Build embeddings
uv run run.py build-embeddings 

# Check API health
uv run run.py health 

# Get collection statistics
uv run run.py stats 

# Search assessments
uv run run.py search "your query" 
```

## Project Structure

```
SHL-Recomendation-Engine/
├── app/
│   ├── main.py
│   ├── services/
│   │   ├── chroma_service.py   
│   │   ├── embedding_service.py
│   │   └── scraper_service.py  
│   ├── shared/
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── parser.py
│   │   └── utils.py 
│   └── static/
│       ├── index.html
│       ├── script.js
│       └── style.css
├── chroma_db/
│   └── chroma.sqlite3
├── data/
│   ├── shl_assessments.csv
│   └── shl_embeddings_payload.json
├── dataset/
│   ├── Gen_AI Dataset.csv 
│   ├── test.csv           
│   └── vansh_bhatnagar.csv
├── scripts/
│   └── batch_query.py
├── test/             
│   ├── api.py
│   ├── embeddings_builder.py
│   └── scraper.py
├── run.py        
├── pyproject.toml
├── uv.lock       
└── README.md
```

## Configuration

The application uses environment variables for configuration. All variables have sensible defaults and can be overridden using system environment variables:

| Variable | Description | Default |
| --- | --- | --- |
| `CHROMA_COLLECTION_NAME` | ChromaDB collection name | `shl_assessments` |
| `CHROMA_PERSIST_DIR` | ChromaDB storage directory | `chroma_db` |
| `SENTENCE_TRANSFORMER_MODEL` | Embedding model name | `all-MiniLM-L6-v2` |
| `GATEWAY_HOST` | API server host | `0.0.0.0` |
| `GATEWAY_PORT` | API server port | `8000` |


## How It Works

1. **Data Collection**: Web scraper crawls SHL assessment pages and extracts metadata
2. **Embedding Generation**: Assessment descriptions are converted to vector embeddings using Sentence Transformers
3. **Vector Storage**: Embeddings are stored in ChromaDB for fast similarity search
4. **Query Processing**: User queries are converted to embeddings
5. **Semantic Search**: ChromaDB finds the most similar assessments using cosine similarity
6. **Ranking & Filtering**: Results are ranked and filtered to ensure balance across test types
7. **Response**: Top 5-10 recommendations are returned with metadata

