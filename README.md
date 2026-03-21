# my-fin-agent

`my-fin-agent` is a lightweight full-stack financial Q&A application built with FastAPI, React, and OpenAI. It supports two kinds of questions through one chat interface:

- Market questions: live price, trend, technical indicator, financial statement, and news queries for specific tickers
- Knowledge questions: conceptual finance questions answered from externally retrieved reference material

The current knowledge path does not use ChromaDB or a local vector store. Knowledge answers are generated from externally retrieved sources, currently centered on Wikipedia.

## Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                      Frontend (React)                       │
│  - Chat interface                                           │
│  - Markdown / LaTeX rendering                               │
│  - Calls POST /api/query                                    │
└───────────────────────────────┬──────────────────────────────┘
                                │ HTTP / JSON
┌───────────────────────────────▼──────────────────────────────┐
│                      Backend (FastAPI)                      │
│  - /api/query                                               │
│  - /api/health                                              │
│  - /api/providers                                           │
└───────────────────────────────┬──────────────────────────────┘
                                │
                     ┌──────────▼──────────┐
                     │   Query Router      │
                     │   OpenAI intent     │
                     └───────┬───────┬─────┘
                             │       │
                    market   │       │ knowledge
                             │       │
        ┌────────────────────▼─┐   ┌─▼────────────────────────┐
        │ Market Agent         │   │ Knowledge Agent           │
        │ OpenAI + tool calls  │   │ External retrieval        │
        │ 5 tools, parallel    │   │ Wikipedia search          │
        │                      │   │ OpenAI grounded answer    │
        └───────┬──────────────┘   └──────────┬───────────────┘
                │                             │
     ┌──────────▼──────────┐         ┌────────▼───────────────┐
     │ Market Data Sources │         │ Knowledge Sources      │
     │ - yfinance          │         │ - Wikipedia            │
     │ - Finnhub (optional)│         │ - Public web refs      │
     └─────────────────────┘         └────────────────────────┘
```

## Tech Stack

### Frontend

- React 19
- TypeScript
- Vite
- Tailwind CSS
- `react-markdown` + KaTeX

### Backend

- FastAPI
- Pydantic
- Uvicorn

### Intelligence Layer

- OpenAI chat completions for:
  - query routing
  - market response generation
  - knowledge response generation
- OpenAI tool use for market-data workflows

### Data Sources

- `yfinance` for core market data
- `Finnhub` as an optional enrichment source
- Wikipedia API for external knowledge retrieval

## How It Works

### Market Queries

The router classifies a question as `market` when it asks for live or ticker-specific information such as:

- current price
- performance over a time range
- technical indicators
- financial statements
- catalyst/news questions

The market agent can call:

- `get_stock_price`
- `get_price_history`
- `get_technical_indicators`
- `get_financial_statements`
- `search_news`

It returns a structured answer split into:

- `## DATA`
- `## ANALYSIS`

### Knowledge Queries

The router classifies a question as `knowledge` when it is conceptual, such as:

- “What is quantitative easing?”
- “How does RSI work?”
- “What is the difference between revenue and net income?”

The knowledge flow is:

1. Extract search terms from the user’s question with the LLM
2. Search Wikipedia in the preferred language
3. Fall back to English Wikipedia if needed
4. Build a grounded answer from retrieved excerpts
5. Return the answer with source labels and URLs

## API

### Endpoints

- `GET /`
- `GET /api/health`
- `GET /api/providers`
- `POST /api/query`

### Example Request

```json
{
  "query": "How has Tesla performed this year?"
}
```

### Example Response

```json
{
  "answer": "...",
  "data_section": "...",
  "analysis_section": "...",
  "sources": ["Yahoo Finance (yfinance)"],
  "query_type": "market",
  "ticker": "TSLA",
  "latency_ms": 2140.8,
  "source_type": null
}
```

## Configuration

Backend environment variables are documented in [`backend/.env.example`](./backend/.env.example).

### Backend Variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | Yes | Required for routing and answer generation |
| `OPENAI_MODEL` | No | Defaults to `gpt-5.4` |
| `FINNHUB_API_KEY` | No | Enables Finnhub news and financial enrichment |
| `ALPHA_VANTAGE_API_KEY` | No | Reserved optional provider slot |
| `ALLOWED_ORIGINS` | No | Comma-separated list of frontend origins allowed by CORS |

### Frontend Variables

Frontend build-time variables are documented in [`frontend/.env.example`](./frontend/.env.example).

| Variable | Required | Purpose |
| --- | --- | --- |
| `VITE_API_URL` | No in local dev, Yes in deployment | Base URL for the backend API |

## Local Development

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# edit .env and set OPENAI_API_KEY
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Optional local frontend config:

```bash
VITE_API_URL=http://127.0.0.1:8000
```

If `VITE_API_URL` is not set, the frontend falls back to `http://localhost:8000` in development.

### Helper Scripts

From the repo root:

```bash
./start.sh
./stop.sh
./restart.sh
```

Defaults:

- backend: `127.0.0.1:8000`
- frontend: `127.0.0.1:5173`
- logs: `.run/`

## Deploying to Render

The repo includes [`render.yaml`](./render.yaml) for a simple two-service deployment:

- one Render Web Service for the backend
- one Render Static Site for the frontend

### Recommended Deployment Method

Use a Render Blueprint:

1. Push the repo to GitHub
2. In Render, click `New` -> `Blueprint`
3. Select this repository
4. Use the root `render.yaml`
5. Review services and create the Blueprint

### Backend Web Service Settings

- Service Type: `Web Service`
- Root Directory: `backend`
- Runtime: `Python`
- Build Command: `pip install -e .`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/api/health`

Recommended environment variables:

- `OPENAI_API_KEY=<required>`
- `OPENAI_MODEL=gpt-5.4`
- `FINNHUB_API_KEY=<optional>`
- `ALPHA_VANTAGE_API_KEY=<optional>`
- `ALLOWED_ORIGINS=https://<your-frontend>.onrender.com`

If you also want local frontend access against the deployed backend:

- `ALLOWED_ORIGINS=https://<your-frontend>.onrender.com,http://localhost:5173,http://127.0.0.1:5173`

### Frontend Static Site Settings

- Service Type: `Static Site`
- Root Directory: `frontend`
- Build Command: `npm ci && npm run build`
- Publish Directory: `dist`

Required environment variable:

- `VITE_API_URL=https://<your-backend>.onrender.com`

### Post-Deploy Verification

1. Open `https://<backend>.onrender.com/api/health`
2. Open `https://<backend>.onrender.com/api/providers`
3. Load the frontend
4. Run one market query and one knowledge query
5. If browser requests fail, verify:
   - `VITE_API_URL` points to the backend
   - `ALLOWED_ORIGINS` includes the frontend domain

## Testing

### Backend

```bash
cd backend
source .venv/bin/activate
pytest
```

### Frontend

```bash
cd frontend
npm run lint
npm run build
```

## Project Structure

```text
backend/
  agents/
  api/
  market/
  rag/
  tests/
  config.py
  main.py
  pyproject.toml

frontend/
  public/
  src/
  package.json
  vite.config.ts

render.yaml
README.md
start.sh
stop.sh
restart.sh
```

## Notes

- The backend no longer depends on ChromaDB.
- Knowledge answers are only as good as the external retrieved context.
- Wikipedia-backed answers are useful for general finance concepts, but they are not a substitute for authoritative regulatory or legal sources.
