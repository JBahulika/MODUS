"use client";

import { FormEvent, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const SAMPLE_QUERIES = [
  "AI transformation opportunities for a mid-size retail bank in operations",
  "Enterprise AI opportunities in order-to-cash for a CPG company",
  "How should a hospital system approach AI automation in clinical admin?",
];

type ProgressEvent = {
  step: string;
  message: string;
  status?: string;
};

type Source = { title?: string; url?: string };

type Recommendation = {
  title?: string;
  priority?: string;
  rationale?: string;
  supporting_findings?: string[];
  sources?: Source[];
  confidence?: string;
};

type Report = {
  query?: string;
  subject?: string;
  executive_summary?: string;
  context?: {
    industry?: string;
    company_or_subject_summary?: string;
    operating_notes?: string;
  };
  industry_signals?: {
    trends?: string[];
    ai_adoption_patterns?: string[];
    pressures?: string[];
  };
  recent_news?: Array<Record<string, unknown>>;
  competitors?: Array<Record<string, unknown>>;
  ai_opportunities?: Array<Record<string, unknown>>;
  risks?: Array<Record<string, unknown> | string>;
  recommendations?: Recommendation[];
  conflicts?: string[];
  confidence_notes?: string[];
  sources?: Source[];
};

const STEP_LABELS: Record<string, string> = {
  queued: "Queued",
  planning: "Planning",
  company: "Company context",
  industry: "Industry signals",
  news: "News",
  competitors: "Competitors",
  opportunity: "AI opportunities",
  risk: "Risk check",
  summarizing: "Synthesizing",
  done: "Done",
  error: "Error",
  completed: "Completed",
  failed: "Failed",
};

export default function HomePage() {
  const [query, setQuery] = useState(SAMPLE_QUERIES[0]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [openRec, setOpenRec] = useState<number | null>(0);

  const activeStep = events.length ? events[events.length - 1].step : status;
  const busy = loading && status !== "completed" && status !== "failed";

  useEffect(() => {
    if (!jobId || status === "completed" || status === "failed") return;

    const source = new EventSource(`${API_URL}/research/${jobId}/events`);

    const handle = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as ProgressEvent;
        setEvents((prev) => [...prev, data]);
        if (data.status) setStatus(data.status);
        if (data.step === "done" || data.step === "completed") {
          setStatus("completed");
          source.close();
          void fetchReport(jobId);
        }
        if (data.step === "error" || data.step === "failed") {
          setStatus("failed");
          setError(data.message);
          source.close();
          setLoading(false);
        }
      } catch {
        /* ignore malformed chunks */
      }
    };

    [
      "queued",
      "planning",
      "company",
      "industry",
      "news",
      "competitors",
      "opportunity",
      "risk",
      "summarizing",
      "done",
      "error",
      "completed",
      "failed",
      "pdf_error",
      "message",
    ].forEach((name) => source.addEventListener(name, handle as EventListener));

    return () => source.close();
  }, [jobId, status]);

  async function fetchReport(id: string) {
    const res = await fetch(`${API_URL}/research/${id}`);
    if (!res.ok) throw new Error("Failed to load report");
    const data = await res.json();
    setReport(data.report);
    setStatus(data.status);
    setLoading(false);
    setOpenRec(0);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setReport(null);
    setEvents([]);
    setLoading(true);
    setStatus("queued");
    setOpenRec(null);

    try {
      const res = await fetch(`${API_URL}/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim(), use_cache: false }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || "Failed to start research");
      }
      const data = await res.json();
      setJobId(data.job_id);
      setStatus(data.status);
      if (data.cached || data.status === "completed") {
        await fetchReport(data.job_id);
      }
    } catch (err) {
      setLoading(false);
      setStatus("failed");
      setError(err instanceof Error ? err.message : "Request failed");
    }
  }

  return (
    <main className="page">
      <header className="hero">
        <p className="brand">Enterprise AI Research Agent</p>
        <h1>Research a transformation question.</h1>
        <p className="lede">
          Specialist agents gather company context, industry signals, news,
          competitors, and AI opportunities, then return a brief with sources
          and clear recommendation rationales.
        </p>

        <form className="search" onSubmit={onSubmit}>
          <label htmlFor="query">Research query</label>
          <div className="row">
            <input
              id="query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. AI opportunities for retail banking operations"
              disabled={busy}
              required
            />
            <button type="submit" disabled={busy}>
              {busy ? "Researching…" : "Research"}
            </button>
          </div>
          <div className="samples">
            {SAMPLE_QUERIES.map((sample) => (
              <button
                key={sample}
                type="button"
                className="sample"
                disabled={busy}
                onClick={() => setQuery(sample)}
              >
                {sample}
              </button>
            ))}
          </div>
        </form>
      </header>

      {(loading || events.length > 0) && (
        <section className="panel progress" aria-live="polite">
          <div className="panel-head">
            <h2>Status</h2>
            <span className={`pill ${status}`}>
              {STEP_LABELS[activeStep] || activeStep}
            </span>
          </div>
          <ol>
            {events.map((ev, idx) => (
              <li key={`${ev.step}-${idx}`}>
                <span className="dot" />
                <div>
                  <strong>{STEP_LABELS[ev.step] || ev.step}</strong>
                  <p>{ev.message}</p>
                </div>
              </li>
            ))}
          </ol>
          {busy && <div className="bar" />}
        </section>
      )}

      {error && (
        <section className="panel error">
          <h2>Error</h2>
          <p>{error}</p>
        </section>
      )}

      {report && (
        <section className="report">
          <div className="report-head">
            <div>
              <p className="eyebrow">Brief</p>
              <h2>{report.subject || report.query || query}</h2>
            </div>
            {jobId && (
              <a
                className="download"
                href={`${API_URL}/research/${jobId}/pdf`}
                target="_blank"
                rel="noreferrer"
              >
                Download PDF
              </a>
            )}
          </div>

          <article className="block">
            <h3>Executive summary</h3>
            <p>{report.executive_summary || "—"}</p>
          </article>

          <article className="block">
            <h3>Context</h3>
            <p>{report.context?.company_or_subject_summary || "—"}</p>
            {report.context?.industry ? (
              <p>
                <strong>Industry:</strong> {report.context.industry}
              </p>
            ) : null}
            {report.context?.operating_notes ? (
              <p>{report.context.operating_notes}</p>
            ) : null}
          </article>

          <article className="block">
            <h3>Industry signals</h3>
            <BulletList title="Trends" items={report.industry_signals?.trends} />
            <BulletList
              title="AI adoption"
              items={report.industry_signals?.ai_adoption_patterns}
            />
            <BulletList
              title="Pressures"
              items={report.industry_signals?.pressures}
            />
          </article>

          <article className="block">
            <h3>Recent news</h3>
            <ul className="news">
              {(report.recent_news || []).map((item, idx) => (
                <li key={idx}>
                  <strong>{String(item.headline || "Untitled")}</strong>
                  <p>{String(item.summary || "")}</p>
                  {item.url ? (
                    <a href={String(item.url)} target="_blank" rel="noreferrer">
                      Source
                    </a>
                  ) : null}
                </li>
              ))}
            </ul>
          </article>

          <article className="block">
            <h3>Competitors</h3>
            <div className="grid">
              {(report.competitors || []).map((c, idx) => (
                <div key={idx} className="comp">
                  <h4>{String(c.name || "Competitor")}</h4>
                  <p>{String(c.why || "")}</p>
                  <BulletList
                    items={(c.ai_or_transformation_moves as string[]) || []}
                  />
                </div>
              ))}
            </div>
          </article>

          <article className="block">
            <h3>AI opportunities</h3>
            <div className="grid">
              {(report.ai_opportunities || []).map((opp, idx) => (
                <div key={idx} className="comp">
                  <h4>{String(opp.title || "Opportunity")}</h4>
                  <p>
                    <strong>{String(opp.process_or_function || "")}</strong>
                    {opp.complexity ? ` · ${String(opp.complexity)} complexity` : ""}
                  </p>
                  <p>{String(opp.why_now || "")}</p>
                  <p>{String(opp.expected_impact || "")}</p>
                </div>
              ))}
            </div>
          </article>

          <article className="block">
            <h3>Risks</h3>
            <ul className="news">
              {(report.risks || []).map((risk, idx) =>
                typeof risk === "string" ? (
                  <li key={idx}>{risk}</li>
                ) : (
                  <li key={idx}>
                    <strong>
                      {String(risk.title || "Risk")}
                      {risk.severity ? ` · ${String(risk.severity)}` : ""}
                    </strong>
                    <p>{String(risk.detail || "")}</p>
                    {risk.mitigation ? (
                      <p>
                        <em>Mitigation:</em> {String(risk.mitigation)}
                      </p>
                    ) : null}
                  </li>
                )
              )}
            </ul>
          </article>

          <article className="block">
            <h3>Recommendations</h3>
            <p className="hint">
              Open a recommendation to see why it was made and which sources
              support it.
            </p>
            <div className="recs">
              {(report.recommendations || []).map((rec, idx) => {
                const open = openRec === idx;
                return (
                  <div key={idx} className={`rec ${open ? "open" : ""}`}>
                    <button
                      type="button"
                      className="rec-head"
                      onClick={() => setOpenRec(open ? null : idx)}
                    >
                      <span>
                        <strong>{rec.title || "Recommendation"}</strong>
                        <em>
                          {rec.priority || "medium"} priority ·{" "}
                          {rec.confidence || "medium"} confidence
                        </em>
                      </span>
                      <span className="chev">{open ? "−" : "+"}</span>
                    </button>
                    {open && (
                      <div className="rec-body">
                        <p>
                          <strong>Why:</strong> {rec.rationale || "—"}
                        </p>
                        <BulletList
                          title="Supporting findings"
                          items={rec.supporting_findings}
                        />
                        <ul className="sources">
                          {(rec.sources || []).map((s, sidx) => (
                            <li key={sidx}>
                              {s.url ? (
                                <a href={s.url} target="_blank" rel="noreferrer">
                                  {s.title || s.url}
                                </a>
                              ) : (
                                s.title
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </article>

          {(report.confidence_notes?.length || report.conflicts?.length) ? (
            <article className="block">
              <h3>Confidence & conflicts</h3>
              <BulletList items={report.confidence_notes} />
              <BulletList items={report.conflicts} />
            </article>
          ) : null}

          <article className="block">
            <h3>Sources</h3>
            <ul className="sources">
              {(report.sources || []).map((s, idx) => (
                <li key={idx}>
                  {s.url ? (
                    <a href={s.url} target="_blank" rel="noreferrer">
                      {s.title || s.url}
                    </a>
                  ) : (
                    s.title
                  )}
                </li>
              ))}
            </ul>
          </article>
        </section>
      )}

      <style jsx>{`
        .page {
          position: relative;
          z-index: 1;
          max-width: 920px;
          margin: 0 auto;
          padding: 2.5rem 1.25rem 4rem;
        }

        .hero {
          animation: riseIn 0.7s ease both;
          padding: 1.5rem 0 2rem;
        }

        .brand {
          margin: 0 0 0.75rem;
          font-family: var(--font-display);
          font-size: clamp(1.8rem, 4.5vw, 2.7rem);
          font-weight: 700;
          letter-spacing: -0.03em;
          color: var(--ink);
          line-height: 1.05;
        }

        h1 {
          margin: 0;
          max-width: 18ch;
          font-family: var(--font-display);
          font-size: clamp(1.35rem, 3vw, 2rem);
          font-weight: 500;
          line-height: 1.2;
          color: var(--ink-soft);
        }

        .lede {
          margin: 1rem 0 0;
          max-width: 58ch;
          color: var(--ink-soft);
          font-size: 1.05rem;
          line-height: 1.55;
        }

        .search {
          margin-top: 1.75rem;
        }

        .search label {
          display: block;
          margin-bottom: 0.4rem;
          font-size: 0.85rem;
          font-weight: 600;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          color: var(--ink-soft);
        }

        .row {
          display: flex;
          gap: 0.65rem;
          flex-wrap: wrap;
        }

        input {
          flex: 1;
          min-width: 220px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.72);
          border-radius: 10px;
          padding: 0.9rem 1rem;
          outline: none;
        }

        input:focus {
          border-color: var(--accent);
          box-shadow: 0 0 0 3px rgba(15, 76, 92, 0.15);
        }

        button,
        .download {
          border: none;
          border-radius: 10px;
          background: var(--accent);
          color: #f7fffc;
          font-weight: 700;
          padding: 0.9rem 1.25rem;
          cursor: pointer;
          text-decoration: none;
          display: inline-flex;
          align-items: center;
        }

        button:disabled {
          opacity: 0.7;
          cursor: wait;
        }

        .samples {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-top: 0.85rem;
        }

        .sample {
          background: transparent;
          color: var(--ink-soft);
          border: 1px solid var(--line);
          font-weight: 600;
          font-size: 0.82rem;
          padding: 0.45rem 0.7rem;
          text-align: left;
        }

        .panel,
        .report {
          margin-top: 1.25rem;
          animation: riseIn 0.55s ease both;
        }

        .panel {
          border: 1px solid var(--line);
          background: var(--paper);
          border-radius: 16px;
          padding: 1.1rem 1.2rem;
          box-shadow: var(--shadow);
        }

        .panel-head,
        .report-head {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 1rem;
        }

        .panel h2,
        .report-head h2,
        .block h3 {
          margin: 0;
          font-family: var(--font-display);
          font-weight: 700;
        }

        .eyebrow {
          margin: 0 0 0.25rem;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          font-size: 0.75rem;
          color: var(--ink-soft);
          font-weight: 700;
        }

        .pill {
          font-size: 0.78rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          padding: 0.35rem 0.65rem;
          border-radius: 999px;
          background: rgba(15, 76, 92, 0.12);
          color: var(--accent);
        }

        .pill.failed,
        .pill.error {
          background: rgba(159, 18, 57, 0.12);
          color: var(--danger);
        }

        .progress ol {
          list-style: none;
          margin: 1rem 0 0;
          padding: 0;
          display: grid;
          gap: 0.75rem;
        }

        .progress li {
          display: grid;
          grid-template-columns: 14px 1fr;
          gap: 0.75rem;
        }

        .dot {
          width: 10px;
          height: 10px;
          margin-top: 0.35rem;
          border-radius: 50%;
          background: var(--accent);
          animation: pulseDot 1.4s ease infinite;
        }

        .progress p {
          margin: 0.15rem 0 0;
          color: var(--ink-soft);
        }

        .bar {
          margin-top: 1rem;
          height: 4px;
          border-radius: 999px;
          background: linear-gradient(
            90deg,
            transparent,
            var(--accent),
            transparent
          );
          background-size: 200% 100%;
          animation: pulseDot 1.2s linear infinite;
        }

        .error {
          border-color: rgba(159, 18, 57, 0.25);
        }

        .block {
          margin-top: 1rem;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.62);
          border-radius: 16px;
          padding: 1.15rem 1.2rem;
        }

        .block p,
        .block li {
          color: var(--ink-soft);
          line-height: 1.55;
        }

        .hint {
          margin-top: 0.4rem;
          font-size: 0.95rem;
        }

        .news,
        .sources {
          list-style: none;
          padding: 0;
          margin: 0.75rem 0 0;
          display: grid;
          gap: 0.85rem;
        }

        .grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 0.85rem;
          margin-top: 0.85rem;
        }

        .comp {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 0.85rem;
          background: rgba(255, 255, 255, 0.55);
        }

        .comp h4 {
          margin: 0 0 0.35rem;
          font-family: var(--font-display);
        }

        .recs {
          display: grid;
          gap: 0.65rem;
          margin-top: 0.85rem;
        }

        .rec {
          border: 1px solid var(--line);
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.55);
          overflow: hidden;
        }

        .rec-head {
          width: 100%;
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          background: transparent;
          color: var(--ink);
          text-align: left;
          padding: 0.9rem 1rem;
          border-radius: 0;
        }

        .rec-head em {
          display: block;
          margin-top: 0.2rem;
          font-style: normal;
          color: var(--ink-soft);
          font-size: 0.85rem;
        }

        .chev {
          font-size: 1.2rem;
          color: var(--accent);
        }

        .rec-body {
          padding: 0 1rem 1rem;
          border-top: 1px solid var(--line);
        }
      `}</style>
    </main>
  );
}

function BulletList({
  title,
  items,
}: {
  title?: string;
  items?: string[] | null;
}) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      {title ? <h4 style={{ marginBottom: "0.35rem" }}>{title}</h4> : null}
      <ul>
        {items.map((item, idx) => (
          <li key={idx}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
