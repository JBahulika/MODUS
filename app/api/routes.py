"""FastAPI routes for research jobs, SSE progress, and PDF download."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.memory import redis_cache, sqlite_store
from app.pdf.generator import generate_pdf
from app.workflows.langgraph_workflow import run_research

router = APIRouter()


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    use_cache: bool = True


class ResearchStartResponse(BaseModel):
    job_id: str
    query: str
    status: str
    cached: bool = False


def _is_cacheable_report(report: dict[str, Any]) -> bool:
    summary = str(report.get("executive_summary") or "")
    if not summary.strip():
        return False
    lowered = summary.lower()
    if any(
        token in lowered
        for token in (
            "quota exceeded",
            "resource_exhausted",
            "429",
            "unable to structure",
            "incomplete synthesis",
        )
    ):
        return False

    has_recs = bool(report.get("recommendations"))
    has_opps = bool(report.get("ai_opportunities"))
    context = report.get("context") or {}
    has_context = bool(context.get("company_or_subject_summary") or context.get("industry"))
    if not has_recs and not has_opps and not has_context:
        return False
    return True


def _run_job(job_id: str, query: str) -> None:
    sqlite_store.update_job_status(job_id, "running")

    def on_progress(step: str, message: str) -> None:
        sqlite_store.add_event(job_id, step, message)

    try:
        result = run_research(query=query, job_id=job_id, on_progress=on_progress)
        report = result.get("report") or {}
        report["job_id"] = job_id
        report["errors"] = result.get("errors") or []
        sqlite_store.save_report(job_id, report)
        if _is_cacheable_report(report):
            redis_cache.cache_set(redis_cache.query_cache_key(query), report, ttl=3600)
        else:
            redis_cache.cache_delete(redis_cache.query_cache_key(query))
        try:
            generate_pdf(report, job_id)
        except Exception as pdf_exc:
            sqlite_store.add_event(job_id, "pdf_error", f"PDF generation failed: {pdf_exc}")
        sqlite_store.add_event(job_id, "done", "Brief ready.")
    except Exception as exc:
        sqlite_store.update_job_status(job_id, "failed", error=str(exc))
        sqlite_store.add_event(job_id, "error", str(exc))


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/research", response_model=ResearchStartResponse)
def start_research(
    body: ResearchRequest,
    background_tasks: BackgroundTasks,
) -> ResearchStartResponse:
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Research query is required")

    if body.use_cache:
        cached = redis_cache.cache_get(redis_cache.query_cache_key(query))
        if isinstance(cached, dict) and _is_cacheable_report(cached):
            job_id = str(uuid.uuid4())
            sqlite_store.create_job(job_id, query)
            sqlite_store.save_report(job_id, cached)
            sqlite_store.add_event(job_id, "done", "Returned cached brief.")
            try:
                generate_pdf(cached, job_id)
            except Exception:
                pass
            return ResearchStartResponse(
                job_id=job_id,
                query=query,
                status="completed",
                cached=True,
            )

    job_id = str(uuid.uuid4())
    sqlite_store.create_job(job_id, query)
    sqlite_store.add_event(job_id, "queued", f"Queued research: {query}")
    background_tasks.add_task(_run_job, job_id, query)
    return ResearchStartResponse(
        job_id=job_id,
        query=query,
        status="queued",
        cached=False,
    )


@router.get("/research")
def list_research(limit: int = 20) -> list[dict[str, Any]]:
    return sqlite_store.list_jobs(limit=limit)


@router.get("/research/{job_id}")
def get_research(job_id: str) -> dict[str, Any]:
    job = sqlite_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/research/{job_id}/events")
async def research_events(job_id: str) -> EventSourceResponse:
    job = sqlite_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        last_id = 0
        idle_rounds = 0
        while True:
            events = sqlite_store.get_events(job_id, after_id=last_id)
            current = sqlite_store.get_job(job_id)
            for event in events:
                last_id = event["id"]
                idle_rounds = 0
                yield {
                    "event": event["step"],
                    "data": json.dumps(
                        {
                            "step": event["step"],
                            "message": event["message"],
                            "created_at": event["created_at"],
                            "status": current["status"] if current else "unknown",
                        }
                    ),
                }
                if event["step"] in {"done", "error"}:
                    return

            status = current["status"] if current else "failed"
            if status in {"completed", "failed"} and not events:
                idle_rounds += 1
                if idle_rounds >= 2:
                    yield {
                        "event": status,
                        "data": json.dumps(
                            {
                                "step": status,
                                "message": f"Job {status}",
                                "status": status,
                            }
                        ),
                    }
                    return

            await asyncio.sleep(0.6)

    return EventSourceResponse(event_generator())


@router.get("/research/{job_id}/pdf")
def download_pdf(job_id: str) -> FileResponse:
    job = sqlite_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed" or not job.get("report"):
        raise HTTPException(status_code=409, detail="Report not ready")

    from app.config import get_settings

    path = get_settings().reports_path / f"{job_id}.pdf"
    if not path.exists():
        try:
            path = generate_pdf(job["report"], job_id)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"PDF failed: {exc}") from exc

    safe_name = (job.get("query") or "research")[:40].replace(" ", "_")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{safe_name}_enterprise_brief.pdf",
    )
