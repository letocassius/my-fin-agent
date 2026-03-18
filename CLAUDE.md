# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Status

This is a **greenfield project**. No application code exists yet — only this requirements file. The sections below describe the intended architecture to guide implementation.

---

## Intended Architecture

```
frontend/          # React SPA (Vite + TypeScript)
backend/           # Python FastAPI service
  api/             # Route handlers
  agents/          # LLM agent logic (query routing, tool use)
  rag/             # RAG pipeline: chunking, embedding, vector search
  market/          # External market data API clients
  knowledge_base/  # Source documents for RAG
```

**Data flow:**
1. User query → frontend → `POST /api/query`
2. Backend router classifies query: **market** (price/trend) vs **knowledge** (conceptual)
3. Market queries → external API (Yahoo Finance / Alpha Vantage) → LLM formats structured answer
4. Knowledge queries → vector similarity search → retrieved chunks → LLM generates grounded answer
5. Response includes explicit separation of objective data vs analytical commentary

---

## Dev Commands (once implemented)

```bash
# Backend
cd backend
pip install -e ".[dev]"
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev        # dev server on :5173
npm run build
npm run lint

# Tests
cd backend && pytest
cd frontend && npm test
```

---

## Key Implementation Decisions

**Query routing:** The LLM agent should classify intent first (market data vs financial knowledge) before dispatching to the appropriate handler. Ambiguous queries (e.g., "What is BABA's P/E ratio?") should hit market data.

**Market data:** Use `yfinance` (no API key required) as the primary source. Alpha Vantage as fallback if real-time quotes are needed.

**RAG pipeline:** Embed with `text-embedding-3-small` (OpenAI) or equivalent. Store vectors in ChromaDB (local, no infra needed). Chunk financial documents at ~500 tokens with 50-token overlap.

**LLM integration:** Use an OpenAI chat model with structured tool use for the agent. The agent should have tools: `get_stock_price`, `get_price_history`, `search_news`, `retrieve_knowledge`.

**Answer structure:** Every market answer must include a clearly labeled data section (price, change %, dates) and a separate analysis section. Never blend facts with interpretation without labeling.

---

## Project Requirements Summary

### Functional

- Asset Q&A: real-time prices, % change over periods, trend classification, factor analysis
- Knowledge Q&A: conceptual finance questions answered via RAG (not free-form generation)
- Query routing: market queries → external API; knowledge queries → vector retrieval

### Mandatory Components

| Component | Choice |
|---|---|
| Frontend | React + TypeScript (Vite) |
| Backend | FastAPI (Python) |
| LLM | OpenAI API |
| Vector Store | ChromaDB |
| Market Data | yfinance + Alpha Vantage |

### Evaluation Priorities

- Depth and correctness over feature quantity
- Professional, data-driven responses over conversational fluency
- Sound architecture over visual polish

---

## Financial Asset QA System — Full Requirements

---

### Project Goal

Design and implement a full-stack, LLM-powered financial asset question-answering system. Vibe coding is an acceptable development approach.

#### Core Capabilities

1. Asset price and movement analysis *(primary focus)*
2. Financial knowledge Q&A *(RAG-based)*
3. Structured, professional, data-driven answer generation

#### Assessment Focus

This project is evaluated on:

- Frontend engineering skill
- Backend architecture design
- LLM integration
- Data integration and accuracy control
- Overall system design thinking

---

### Functional Requirements

#### 1. Asset Q&A

The system must handle queries such as:

- What is Alibaba's current stock price?
- How has BABA performed over the last 7 days?
- Why did Alibaba surge on January 15th?
- What is Tesla's recent price trend?

**System capabilities:**

- Fetch real-time or recent price data
- Compute price change percentages (e.g., 7-day, 30-day)
- Produce structured trend summaries (uptrend / downtrend / sideways)
- Analyze potential driving factors (earnings, macro events, news, etc.)

**Answer quality requirements:**

- Data must be clearly presented
- Structure must be clear and logical
- Distinguish explicitly between *objective data* and *analytical commentary*
- Minimize hallucination — use an appropriate Agent framework

> Predicting future price movements is **not** required.

---

#### 2. Financial Knowledge Q&A

The system must handle queries such as:

- What is a P/E ratio?
- What is the difference between revenue and net income?
- What is the summary of a company's most recent quarterly earnings report?

**Implementation requirements:**

- Build a small financial knowledge base
- Implement document chunking and vectorization
- Support vector retrieval
- Generate answers grounded in Web Search retrieval

> Responses must **not** rely solely on free-form model generation. Integration of existing skills/tools is permitted.

---

#### 3. Market Data Integration *(required for asset Q&A)*

Asset-related questions must be answered by calling **external market data APIs** — not by querying the knowledge base.

Recommended sources (non-exhaustive):

- Yahoo Finance
- Alpha Vantage
- Other equivalent market data providers

**The system must implement basic query routing:**

| Query Type | Handler |
|---|---|
| Market / price queries | External market API |
| Knowledge / conceptual queries | RAG retrieval |

---

### Technical Requirements

Tech stack is flexible, but the following components are **mandatory**:

| Component | Requirement |
|---|---|
| Web Frontend | Interactive UI |
| Backend | REST or equivalent API service |
| LLM Integration | Structured prompt + agent framework |
| Vector Retrieval | Chunking, embedding, and similarity search |

---

### Deliverables

#### 0. Runnable GitHub Repository

A fully functional, runnable project hosted on GitHub.

#### 1. README

Must include:

- System architecture diagram
- Tech stack rationale
- Prompt design approach
- Data source documentation
- Reflections on optimization and extensibility

#### 2. 3-Minute Demo Video

Must cover:

- System overview
- Asset Q&A walkthrough
- RAG walkthrough
- Architecture explanation

---

### Evaluation Criteria

| Dimension | Description |
|---|---|
| System Architecture | Clarity, modularity, and scalability of the overall design |
| Asset Q&A Quality | Professionalism and factual accuracy of answers |
| RAG Implementation | Quality of retrieval pipeline and answer grounding |
| Data Integration | Reliability and correctness of external data ingestion |
| Frontend Engineering | Usability, structure, and code quality of the UI |
| Code Quality | Readability, organization, and maintainability |

---

### Evaluation Philosophy

We prioritize:

- **Clarity of design thinking** over feature quantity
- **Sound engineering structure** over visual polish
- **Professional, data-driven responses** over conversational fluency
- **Appropriate use of LLM capabilities** over raw model calls

> Feature bloat and flashy UI are explicitly **not** valued. Depth and correctness are.
