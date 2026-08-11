# Enterprise AI Research Agent

An enterprise transformation research system. Submit a research question and receive a structured brief covering company context, industry signals, competitor AI moves, opportunity areas, risks, and recommendations with sources.

## What it does

1. Accepts a free-text transformation research query
2. Plans the research scope
3. Runs specialist agents in parallel for company context, industry signals, and news
4. Follows with competitor analysis and AI opportunity mapping
5. Applies a risk and governance pass
6. Synthesizes a decision-ready brief with recommendation rationales and citations
7. Streams progress live and exports a PDF

## Architecture

```text
Next.js UI
  → FastAPI (job create, SSE progress, report, PDF)
     → LangGraph orchestrator
        Planner
          → Company | Industry | News
          → Competitors | AI Opportunities
          → Risk / Governance
          → Synthesizer
     → SQLite (jobs, events, reports)
     → Redis optional cache
     → PDF export
```

### Major components

| Component | Role |
|-----------|------|
| Next.js frontend | Query input, live progress, brief view, recommendation detail, PDF download |
| FastAPI API | Job lifecycle, SSE events, report retrieval, PDF serving |
| LangGraph workflow | Orchestrates planning, parallel research, risk check, and synthesis |
| Research agents | Company, industry, news, competitors, opportunities, risk, synthesizer |
| Tool adapters | Web search, news lookup, LLM structured JSON |
| SQLite store | Durable jobs, event log, final report JSON |
| Redis cache | Short-lived completed brief cache (optional) |
| PDF module | ReportLab export of the final brief |

## Information flow

User submits a query → API creates a job and streams progress → planner defines scope → specialist agents gather evidence through tools and return structured findings with sources → risk agent reviews conflicts and confidence → synthesizer merges everything into one brief with recommendations, each carrying rationale, supporting findings, and source links → UI loads the completed report and optional PDF.

## Data model

**Stored permanently**
- Research jobs and status
- Final report JSON
- Progress event log
- Generated PDF files

**Generated when required**
- Agent intermediate notes
- Live search and news results
- Recommendations for a new query
- SSE progress stream

## Reliability and explainability

- Agents gather evidence through tools before writing findings
- Important points retain source URLs
- Thin or conflicting evidence is surfaced in confidence notes and conflicts
- Each recommendation includes rationale, supporting findings, source links, and confidence

## Extensibility

Agents and tools are separate modules with shared JSON contracts. The orchestrator only wires nodes and state. Adding a new specialist (for example a regulatory agent or an internal docs connector) means adding a module and graph edge, not redesigning the application. New datasets can be introduced through connectors and configuration while the core loop stays the same: plan → gather evidence → structure findings → synthesize.

## Scale considerations

The MVP runs research jobs inside the API process with SQLite. For much larger volume, the intended path is:
- Move heavy work to a worker queue
- Replace SQLite with Postgres
- Keep Redis for cache and queue backing
- Add rate limiting for external APIs
- Keep the UI async with progress tracking

## Tech stack

| Layer | Choice |
|-------|--------|
| UI | Next.js 14 |
| API | FastAPI + SSE |
| Orchestration | LangGraph |
| LLM | Google Gemini |
| Search | Tavily → DuckDuckGo → Wikipedia |
| News | NewsAPI with search fallback |
| Storage | SQLite, Redis optional |
| Export | ReportLab PDF |

## Setup

### Backend

```bash
cd P27_MODUS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set GOOGLE_API_KEY
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

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

UI: http://localhost:3000

## Example queries

- AI transformation opportunities for a mid-size retail bank in operations
- Enterprise AI opportunities in order-to-cash for a CPG company
- How should a hospital system approach AI automation in clinical admin?

## Project structure

```text
app/
  agents/       # planner, company, industry, news, competitor, opportunity, risk, synthesizer
  api/          # REST + SSE routes
  tools/        # LLM, search, news
  memory/       # SQLite + Redis cache
  workflows/    # LangGraph orchestration
  pdf/          # PDF export
frontend/       # Next.js UI
data/           # local SQLite (gitignored)
reports/        # generated PDFs (gitignored)
```
