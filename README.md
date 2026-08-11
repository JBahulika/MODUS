# Enterprise AI Research Agent

Ask a transformation question. Specialist agents research company context, industry signals, news, competitors, and opportunities, then return a brief with recommendations and sources.

## How to run

```bash
# backend
cd P27_MODUS
source .venv/bin/activate
pip install -r requirements.txt
./run_api.sh

# frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

Use **Load sample brief** for an instant example, or type your own question and click **Run research**.

## What to enter

- A company or industry
- The process or function you care about
- Optional: a short internal document and a what-if scenario

Example: `AI transformation opportunities for a mid-size retail bank in operations`

## Architecture

```text
Next.js UI
  → FastAPI (jobs, SSE, uploads, demo, PDF)
     → LangGraph
        Planner
          → Company | Industry | News
          → Competitors | Opportunities
          → Risk check
          → Synthesizer
     → SQLite + optional Redis + PDF
```
