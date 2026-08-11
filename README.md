# Enterprise AI Research Agent

Transformation research agent for the MODUS Enterprise AI Build Challenge.

Type a research question. Specialist agents gather company context, industry signals, news, competitor AI moves, and opportunity areas. A risk check runs next, then a synthesizer produces a brief with recommendations, rationales, sources, and PDF export.

## Stack

| Layer | Choice |
|-------|--------|
| UI | Next.js 14 |
| API | FastAPI + SSE |
| Orchestration | LangGraph |
| LLM | Google Gemini |
| Search | Tavily → DuckDuckGo → Wikipedia |
| News | NewsAPI with search fallback |
| Storage | SQLite jobs/reports, Redis optional cache |
| Export | ReportLab PDF |

## Architecture

```text
User query → Next.js
              → FastAPI job + SSE
                 → LangGraph
                    Planner
                      → Company | Industry | News   (parallel)
                      → Competitors | Opportunities (parallel)
                      → Risk / Governance
                      → Synthesizer
                 → SQLite + optional Redis + PDF
```

## Setup

### 1. Backend

```bash
cd P27_MODUS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # if needed
# set GOOGLE_API_KEY (required)
# optional: TAVILY_API_KEY, NEWS_API_KEY, REDIS_URL
chmod +x run_api.sh
./run_api.sh
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs

Optional Redis:

```bash
docker compose up -d
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

UI: http://localhost:3000

## Sample queries

- AI transformation opportunities for a mid-size retail bank in operations
- Enterprise AI opportunities in order-to-cash for a CPG company
- How should a hospital system approach AI automation in clinical admin?

## What gets stored

Permanent: research jobs, final report JSON, event log, PDFs  
Generated on demand: agent working notes, live search results, recommendations for a new query

## Interview talking points

- Reliability: tools gather evidence first; sources stay on findings; thin evidence is called out
- Explainability: each recommendation has rationale, supporting findings, and source links
- Extensibility: new agents/tools plug into the graph without rewriting the app
- Scale: move heavy work to a worker queue, SQLite → Postgres, keep Redis for cache/queue

## MODUS form answers Q37–Q46

See the challenge plan answers, or use this short map:

| Question | Answer in this build |
|----------|----------------------|
| 37 Architecture | Next.js → FastAPI → LangGraph multi-agent → SQLite/Redis → PDF |
| 38 Flow | Query → job/SSE → planner → specialist agents → risk → synthesizer → brief |
| 39 Components | UI, API, orchestrator, agents, tools, store, cache, PDF |
| 40 Persist vs generate | Jobs/reports/events/PDFs stored; intermediate research generated live |
| 41 Databases | SQLite now; Redis cache; Postgres + vectors later at scale |
| 42 Extensibility | Modular agents/tools + shared JSON contracts |
| 43 Scale | Workers, Postgres, rate limits, async UI |
| 44 Reliability | Tool-first evidence, sources, conflict/confidence notes |
| 45 Explain recommendations | Rationale + supporting findings + source links in UI |
| 46 New data without code change | Connector/config based inputs; core loop stays plan → gather → synthesize |
