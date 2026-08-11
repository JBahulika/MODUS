"use client";

import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const SAMPLE_QUERIES = [
  "AI transformation opportunities for a mid-size retail bank in operations",
  "Enterprise AI opportunities in order-to-cash for a CPG company",
  "How should a hospital system approach AI automation in clinical admin?",
];

type Source = { id?: string; title?: string; url?: string; rank?: number };
type Claim = { id?: string; text?: string; source_ids?: string[] };
type Recommendation = {
  title?: string;
  priority?: string;
  rationale?: string;
  supporting_findings?: string[];
  sources?: Source[];
  confidence?: string;
  roles?: string[];
};

type Report = {
  query?: string;
  subject?: string;
  overall_confidence?: string;
  confidence_score?: number;
  executive_summary?: string;
  one_pager?: {
    headline?: string;
    three_moves?: string[];
    watchouts?: string[];
  };
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
  claims?: Claim[];
  conflicts?: string[];
  confidence_notes?: string[];
  sources?: Source[];
  agent_contributions?: Array<{ agent?: string; summary?: string }>;
  eval?: Record<string, unknown>;
  what_if_assessment?: string;
  what_if?: string;
};

type ProgressEvent = { step: string; message: string; status?: string };
type UploadedDoc = { id: string; filename: string; chars: number };

const STEP_LABELS: Record<string, string> = {
  queued: "Queued",
  planning: "Planning",
  company: "Company",
  industry: "Industry",
  news: "News",
  competitors: "Competitors",
  opportunity: "Opportunities",
  risk: "Risk",
  documents: "Documents",
  what_if: "Scenario",
  summarizing: "Synthesis",
  done: "Done",
  error: "Error",
  completed: "Done",
  failed: "Failed",
};

const ROLES = [
  { id: "all", label: "All roles" },
  { id: "coo", label: "COO" },
  { id: "risk", label: "Risk" },
  { id: "transformation", label: "Transformation" },
] as const;

export default function HomePage() {
  const [query, setQuery] = useState(SAMPLE_QUERIES[0]);
  const [whatIf, setWhatIf] = useState("");
  const [docs, setDocs] = useState<UploadedDoc[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState("idle");
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [openRec, setOpenRec] = useState<number | null>(0);
  const [viewMode, setViewMode] = useState<"brief" | "full">("brief");
  const [role, setRole] = useState<(typeof ROLES)[number]["id"]>("all");
  const [activeClaim, setActiveClaim] = useState<string | null>(null);

  const busy = loading && status !== "completed" && status !== "failed";
  const activeStep = events.length ? events[events.length - 1].step : status;

  useEffect(() => {
    if (!jobId || status === "completed" || status === "failed") {
      return;
    }
    const source = new EventSource(`${API_URL}/research/${jobId}/events`);
    const handle = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as ProgressEvent;
        setEvents((prev) => [...prev, data]);
        if (data.status) setStatus(data.status);
        if (data.step === "done" || data.step === "completed") {
          setStatus("completed");
          source.close();
          void fetchReport(jobId).catch((err) => {
            setLoading(false);
            setError(err instanceof Error ? err.message : "Could not load the brief");
          });
        }
        if (data.step === "error" || data.step === "failed") {
          setStatus("failed");
          setError(data.message);
          source.close();
          setLoading(false);
        }
      } catch {
        /* ignore */
      }
    };
    Object.keys(STEP_LABELS).forEach((name) =>
      source.addEventListener(name, handle as EventListener)
    );
    source.addEventListener("pdf_error", handle as EventListener);
    source.addEventListener("message", handle as EventListener);
    return () => source.close();
  }, [jobId, status]);

  async function fetchReport(id: string) {
    const res = await fetch(`${API_URL}/research/${id}`);
    if (!res.ok) throw new Error("Failed to load report");
    const data = await res.json();
    setReport(data.report);
    setStatus(data.status || "completed");
    setLoading(false);
    setOpenRec(0);
    setViewMode("brief");
  }

  async function onUpload(file: File | null) {
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    const res = await fetch(`${API_URL}/upload`, { method: "POST", body });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      setError(detail.detail || "Upload failed");
      return;
    }
    const data = await res.json();
    setDocs((prev) => [...prev, data]);
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
        body: JSON.stringify({
          query: query.trim(),
          use_cache: false,
          document_ids: docs.map((d) => d.id),
          what_if: whatIf.trim(),
        }),
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

  const filteredRecs = useMemo(() => {
    const recs = report?.recommendations || [];
    if (role === "all") return recs;
    return recs.filter((r) => (r.roles || []).includes(role));
  }, [report, role]);

  const sourceMap = useMemo(() => {
    const map = new Map<string, Source>();
    for (const s of report?.sources || []) {
      if (s.id) map.set(s.id, s);
    }
    return map;
  }, [report]);

  return (
    <main className="shell">
      <aside className="rail">
        <p className="eyebrow">Enterprise research</p>
        <h1>Enterprise AI Research Agent</h1>
        <p className="rail-copy">
          Type a transformation question. The system researches it, checks
          risks, and returns a short brief with sources.
        </p>

        <div className="help">
          <button type="button" className="help-btn" aria-describedby="how-help">
            How this works
            <span className="tip" id="how-help" role="tooltip">
              You give it a business question about AI or transformation.
              Different agents look up company context, industry trends, news,
              competitors, and opportunities. Then it writes a brief with
              recommendations and the sources behind them.
              <br />
              <br />
              Best inputs: a company or industry + the process you care about.
              Example: “AI opportunities in loan operations for a mid-size
              retail bank.” You can also upload a short internal note and add a
              what-if like “budget is frozen for a year.”
            </span>
          </button>
        </div>

        <div className="walk">
          <p>Flow</p>
          <ol>
            <li>You ask a question</li>
            <li>Agents gather evidence</li>
            <li>Risk check runs</li>
            <li>You get a brief with sources</li>
          </ol>
        </div>

        <div className="walk">
          <p>What to enter</p>
          <ul>
            <li>Company or industry</li>
            <li>Process or function to improve</li>
            <li>Optional: a document or what-if</li>
          </ul>
        </div>
      </aside>

      <section className="stage">
        <header className="hero-card">
          <div>
            <p className="brand-mark">Research a transformation question</p>
            <p className="lede">
              Pick an example below or type your own, then run research.
            </p>
          </div>
        </header>

        <form className="composer" onSubmit={onSubmit}>
          <label htmlFor="query">Query</label>
          <textarea
            id="query"
            rows={3}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={busy}
            required
            placeholder="Company or industry + the process you want to improve"
          />
          <div className="chips">
            {SAMPLE_QUERIES.map((sample) => (
              <button
                key={sample}
                type="button"
                className="chip"
                disabled={busy}
                onClick={() => setQuery(sample)}
              >
                {sample}
              </button>
            ))}
          </div>

          <div className="grid-2">
            <div>
              <label htmlFor="whatif">What would change if…</label>
              <input
                id="whatif"
                value={whatIf}
                onChange={(e) => setWhatIf(e.target.value)}
                placeholder="Optional, e.g. hiring freeze for 12 months"
                disabled={busy}
              />
            </div>
            <div>
              <label htmlFor="docs">Internal docs</label>
              <input
                id="docs"
                type="file"
                accept=".pdf,.txt,.md,.docx"
                disabled={busy}
                onChange={(e) => onUpload(e.target.files?.[0] || null)}
              />
              {docs.length > 0 && (
                <ul className="doc-list">
                  {docs.map((d) => (
                    <li key={d.id}>
                      {d.filename} · {d.chars} chars
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <button type="submit" className="primary" disabled={busy}>
            {busy ? "Researching…" : "Run research"}
          </button>
        </form>

        {(loading || events.length > 0) && (
          <div className="panel">
            <div className="panel-head">
              <h2>Agent timeline</h2>
              <span className="pill">{STEP_LABELS[activeStep] || activeStep}</span>
            </div>
            <div className="timeline">
              {events.map((ev, idx) => (
                <div key={`${ev.step}-${idx}`} className="timeline-item">
                  <span className="dot" />
                  <div>
                    <strong>{STEP_LABELS[ev.step] || ev.step}</strong>
                    <p>{ev.message}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="panel error">
            <h2>Something failed</h2>
            <p>{error}</p>
          </div>
        )}

        {report && (
          <div className="report">
            <div className="report-top">
              <div>
                <p className="eyebrow">Brief</p>
                <h2>{report.subject || report.query}</h2>
              </div>
              <div className="report-actions">
                <div className="seg">
                  <button
                    type="button"
                    className={viewMode === "brief" ? "on" : ""}
                    onClick={() => setViewMode("brief")}
                  >
                    1-page
                  </button>
                  <button
                    type="button"
                    className={viewMode === "full" ? "on" : ""}
                    onClick={() => setViewMode("full")}
                  >
                    Full
                  </button>
                </div>
                {jobId && (
                  <a
                    className="primary linkish"
                    href={`${API_URL}/research/${jobId}/pdf`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    PDF
                  </a>
                )}
              </div>
            </div>

            <div className="metrics">
              <Metric
                label="Confidence"
                value={`${report.overall_confidence || "medium"} · ${Math.round(
                  (report.confidence_score || 0.6) * 100
                )}%`}
              />
              <Metric
                label="Sources"
                value={String(report.eval?.sources_count ?? report.sources?.length ?? 0)}
              />
              <Metric label="Claims linked" value={String(report.eval?.claims_linked ?? 0)} />
              <Metric
                label="Competitors"
                value={String(report.eval?.named_competitors ?? report.competitors?.length ?? 0)}
              />
            </div>

            {viewMode === "brief" ? (
              <div className="one-pager">
                <h3>{report.one_pager?.headline || "Executive brief"}</h3>
                <p>{report.executive_summary}</p>
                <div className="two-col">
                  <div>
                    <h4>Three moves</h4>
                    <ul>
                      {(report.one_pager?.three_moves || []).map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4>Watchouts</h4>
                    <ul>
                      {(report.one_pager?.watchouts || []).map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            ) : (
              <>
                <Block title="Executive summary">
                  <p>{report.executive_summary}</p>
                </Block>
                <Block title="Context">
                  <p>{report.context?.company_or_subject_summary}</p>
                  {report.context?.industry && (
                    <p>
                      <strong>Industry:</strong> {report.context.industry}
                    </p>
                  )}
                  <p>{report.context?.operating_notes}</p>
                </Block>
              </>
            )}

            {(report.what_if_assessment || report.what_if) && (
              <Block title="What-if assessment">
                <p>{report.what_if_assessment || `Scenario: ${report.what_if}`}</p>
              </Block>
            )}

            <Block title="Evidence claims">
              <div className="claims">
                {(report.claims || []).map((claim) => (
                  <button
                    key={claim.id}
                    type="button"
                    className={`claim ${activeClaim === claim.id ? "on" : ""}`}
                    onClick={() =>
                      setActiveClaim(activeClaim === claim.id ? null : claim.id || null)
                    }
                  >
                    <span>{claim.text}</span>
                    <em>
                      {(claim.source_ids || [])
                        .map((id) => sourceMap.get(id)?.title || id)
                        .filter(Boolean)
                        .slice(0, 2)
                        .join(" · ") || "source"}
                    </em>
                  </button>
                ))}
              </div>
              {activeClaim && (
                <div className="claim-sources">
                  {(report.claims?.find((c) => c.id === activeClaim)?.source_ids || []).map(
                    (id) => {
                      const src = sourceMap.get(id);
                      if (!src) return null;
                      return src.url ? (
                        <a key={id} href={src.url} target="_blank" rel="noreferrer">
                          {src.title || src.url}
                        </a>
                      ) : (
                        <span key={id}>{src.title}</span>
                      );
                    }
                  )}
                </div>
              )}
            </Block>

            <div className="role-bar">
              <span>Recommendations for</span>
              <div className="seg">
                {ROLES.map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    className={role === r.id ? "on" : ""}
                    onClick={() => setRole(r.id)}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="recs">
              {filteredRecs.map((rec, idx) => {
                const open = openRec === idx;
                return (
                  <div key={idx} className={`rec ${open ? "open" : ""}`}>
                    <button
                      type="button"
                      className="rec-head"
                      onClick={() => setOpenRec(open ? null : idx)}
                    >
                      <span>
                        <strong>{rec.title}</strong>
                        <em>
                          {rec.priority} priority · {rec.confidence} confidence
                        </em>
                      </span>
                      <span>{open ? "−" : "+"}</span>
                    </button>
                    {open && (
                      <div className="rec-body">
                        <p>
                          <strong>Why:</strong> {rec.rationale}
                        </p>
                        <ul>
                          {(rec.supporting_findings || []).map((f, i) => (
                            <li key={i}>{f}</li>
                          ))}
                        </ul>
                        <div className="source-row">
                          {(rec.sources || []).map((s, i) =>
                            s.url ? (
                              <a key={i} href={s.url} target="_blank" rel="noreferrer">
                                {s.title || s.url}
                              </a>
                            ) : (
                              <span key={i}>{s.title}</span>
                            )
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {viewMode === "full" && (
              <>
                <Block title="Industry signals">
                  <List items={report.industry_signals?.trends} />
                  <List items={report.industry_signals?.pressures} />
                </Block>
                <Block title="Named competitors">
                  <div className="cards">
                    {(report.competitors || []).map((c, idx) => (
                      <div key={idx} className="mini">
                        <h4>{String(c.name || "")}</h4>
                        <p>{String(c.why || "")}</p>
                      </div>
                    ))}
                  </div>
                </Block>
                <Block title="Opportunities">
                  <div className="cards">
                    {(report.ai_opportunities || []).map((o, idx) => (
                      <div key={idx} className="mini">
                        <h4>{String(o.title || "")}</h4>
                        <p>{String(o.expected_impact || o.why_now || "")}</p>
                      </div>
                    ))}
                  </div>
                </Block>
                <Block title="Risks">
                  <ul className="risk-list">
                    {(report.risks || []).map((risk, idx) =>
                      typeof risk === "string" ? (
                        <li key={idx}>{risk}</li>
                      ) : (
                        <li key={idx}>
                          <strong>
                            {String(risk.title || "")} · {String(risk.severity || "")}
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
                </Block>
              </>
            )}

            <Block title="Agent contributions">
              <div className="contrib">
                {(report.agent_contributions || []).map((a, idx) => (
                  <div key={idx}>
                    <strong>{a.agent}</strong>
                    <p>{a.summary}</p>
                  </div>
                ))}
              </div>
            </Block>

            <Block title="Top sources">
              <ol className="sources">
                {(report.sources || []).slice(0, 12).map((s, idx) => (
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
              </ol>
            </Block>
          </div>
        )}
      </section>

      <style jsx>{`
        .shell {
          position: relative;
          z-index: 1;
          display: grid;
          grid-template-columns: minmax(260px, 320px) 1fr;
          gap: 1.25rem;
          max-width: 1200px;
          margin: 0 auto;
          padding: 1.5rem;
          animation: riseIn 0.55s ease both;
        }

        .rail,
        .hero-card,
        .composer,
        .panel,
        .report,
        .one-pager {
          background: rgba(255, 250, 242, 0.88);
          border: 1px solid var(--line);
          box-shadow: var(--shadow);
        }

        .rail {
          border-radius: 22px;
          padding: 1.25rem;
          position: sticky;
          top: 1rem;
          align-self: start;
        }

        .rail h1,
        .report h2,
        .brand-mark,
        .one-pager h3,
        .mini h4 {
          font-family: var(--font-display);
          letter-spacing: -0.03em;
        }

        .rail h1 {
          margin: 0.2rem 0 0.7rem;
          font-size: 1.7rem;
          line-height: 1.1;
        }

        .rail-copy,
        .lede,
        .timeline p,
        .rec-body p,
        .mini p {
          color: var(--ink-soft);
          line-height: 1.5;
        }

        .eyebrow {
          margin: 0;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          font-size: 0.72rem;
          font-weight: 700;
          color: var(--accent-2);
        }

        .help {
          margin-top: 1rem;
        }

        .help-btn {
          position: relative;
          border: 1px solid var(--line);
          background: #fff;
          border-radius: 999px;
          padding: 0.55rem 0.9rem;
          font-weight: 600;
          cursor: help;
        }

        .tip {
          display: none;
          position: absolute;
          left: 0;
          top: calc(100% + 0.55rem);
          width: min(280px, 70vw);
          padding: 0.85rem 0.9rem;
          border-radius: 14px;
          background: #1c1914;
          color: #f7f1e6;
          font-size: 0.86rem;
          font-weight: 400;
          line-height: 1.45;
          z-index: 20;
          box-shadow: var(--shadow);
          text-align: left;
        }

        .help-btn:hover .tip,
        .help-btn:focus .tip {
          display: block;
        }

        .walk {
          margin-top: 1.1rem;
          padding-top: 1rem;
          border-top: 1px solid var(--line);
        }

        .walk p {
          margin: 0;
          font-weight: 700;
        }

        .walk ol,
        .walk ul,
        .doc-list,
        .sources,
        .risk-list,
        .rec-body ul {
          margin: 0.4rem 0 0;
          padding-left: 1.1rem;
          color: var(--ink-soft);
        }

        .report-actions,
        .role-bar,
        .claim-sources,
        .source-row {
          display: flex;
          gap: 0.65rem;
        }

        .grid-2,
        .two-col,
        .cards,
        .contrib,
        .metrics {
          display: grid;
          gap: 0.85rem;
        }

        .grid-2,
        .two-col {
          grid-template-columns: 1fr 1fr;
        }

        .metrics {
          grid-template-columns: repeat(4, 1fr);
          margin: 1rem 0;
        }

        .cards,
        .contrib {
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        }

        input,
        textarea {
          width: 100%;
          border: 1px solid var(--line);
          background: #fff;
          border-radius: 12px;
          padding: 0.8rem 0.9rem;
        }

        button,
        .linkish {
          border: none;
          border-radius: 999px;
          cursor: pointer;
        }

        .primary,
        .linkish {
          background: var(--accent);
          color: #f6fff9;
          font-weight: 700;
          padding: 0.8rem 1.15rem;
          text-decoration: none;
          display: inline-flex;
          align-items: center;
          justify-content: center;
        }

        .ghost,
        .chip,
        .seg button,
        .rec-head,
        .claim {
          background: transparent;
          color: var(--ink);
        }

        .ghost,
        .chip {
          border: 1px solid var(--line);
          border-radius: 999px;
          padding: 0.55rem 0.9rem;
        }

        .stage {
          display: grid;
          gap: 1rem;
        }

        .hero-card,
        .composer,
        .panel,
        .report {
          border-radius: 22px;
          padding: 1.2rem 1.25rem;
        }

        .hero-card {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          align-items: start;
        }

        .brand-mark {
          margin: 0;
          font-size: clamp(1.5rem, 3vw, 2.1rem);
          line-height: 1.15;
        }

        .chips {
          display: flex;
          flex-wrap: wrap;
          gap: 0.45rem;
          margin: 0.7rem 0 1rem;
        }

        .chip {
          text-align: left;
          font-size: 0.82rem;
          max-width: 100%;
        }

        label {
          display: block;
          margin: 0.7rem 0 0.35rem;
          font-size: 0.8rem;
          font-weight: 700;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          color: var(--ink-soft);
        }

        .panel-head,
        .report-top {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          align-items: center;
        }

        .pill {
          background: var(--accent-soft);
          color: var(--accent);
          border-radius: 999px;
          padding: 0.3rem 0.7rem;
          font-size: 0.75rem;
          font-weight: 700;
          text-transform: uppercase;
        }

        .timeline {
          display: grid;
          gap: 0.75rem;
          margin-top: 0.9rem;
        }

        .timeline-item {
          display: grid;
          grid-template-columns: 12px 1fr;
          gap: 0.7rem;
        }

        .dot {
          width: 10px;
          height: 10px;
          margin-top: 0.4rem;
          border-radius: 50%;
          background: var(--accent);
          animation: pulseDot 1.4s ease infinite;
        }

        .one-pager,
        .block {
          border-radius: 18px;
          padding: 1rem 1.05rem;
          margin-top: 0.85rem;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.55);
        }

        .seg {
          display: inline-flex;
          padding: 0.2rem;
          border-radius: 999px;
          border: 1px solid var(--line);
          background: #fff;
        }

        .seg button {
          border-radius: 999px;
          padding: 0.4rem 0.75rem;
          font-weight: 600;
        }

        .seg button.on,
        .claim.on {
          background: var(--accent);
          color: #f4fff8;
        }

        .role-bar {
          align-items: center;
          justify-content: space-between;
          margin: 1rem 0 0.6rem;
          color: var(--ink-soft);
        }

        .recs {
          display: grid;
          gap: 0.55rem;
        }

        .rec {
          border: 1px solid var(--line);
          border-radius: 14px;
          background: #fff;
          overflow: hidden;
        }

        .rec-head {
          width: 100%;
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          text-align: left;
          padding: 0.85rem 1rem;
        }

        .rec-head em,
        .claim em {
          display: block;
          margin-top: 0.2rem;
          color: var(--ink-soft);
          font-style: normal;
          font-size: 0.85rem;
        }

        .rec-body {
          padding: 0 1rem 1rem;
          border-top: 1px solid var(--line);
        }

        .claims {
          display: grid;
          gap: 0.5rem;
        }

        .claim {
          text-align: left;
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 0.8rem 0.9rem;
          background: #fff;
        }

        .claim-sources,
        .source-row {
          flex-wrap: wrap;
          margin-top: 0.7rem;
        }

        .mini {
          border: 1px solid var(--line);
          border-radius: 12px;
          padding: 0.8rem;
          background: #fff;
        }

        .error {
          border-color: rgba(143, 45, 45, 0.3);
        }

        @media (max-width: 920px) {
          .shell {
            grid-template-columns: 1fr;
          }

          .rail {
            position: static;
          }

          .hero-card,
          .report-top,
          .role-bar {
            flex-direction: column;
            align-items: stretch;
          }

          .grid-2,
          .two-col,
          .metrics {
            grid-template-columns: 1fr 1fr;
          }
        }

        @media (max-width: 640px) {
          .grid-2,
          .two-col,
          .metrics {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Block({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="block">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function List({ items }: { items?: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <ul>
      {items.map((item, idx) => (
        <li key={idx}>{item}</li>
      ))}
    </ul>
  );
}
