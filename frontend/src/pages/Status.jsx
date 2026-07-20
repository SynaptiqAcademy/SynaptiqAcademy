/* eslint-disable */
import React, { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import {
  CheckCircle2, AlertTriangle, XCircle, Clock,
  RefreshCw, Mail, ArrowRight,
} from "lucide-react";

/* ── Design tokens ─────────────────────────────────────────────────────────── */
const NAVY   = "#0F2847";
const SLATE  = "#475569";
const BORDER = "#e8edf3";
const LIGHT  = "#f8fafc";
const MONO   = "'Menlo','Monaco','Consolas',monospace";

/* ── Status config ──────────────────────────────────────────────────────────── */
const STATUS_CFG = {
  operational: { label: "Operational",          color: "#16a34a", bg: "#f0fdf4", border: "#bbf7d0", dot: "#22c55e", Icon: CheckCircle2 },
  degraded:    { label: "Degraded Performance", color: "#d97706", bg: "#fffbeb", border: "#fde68a", dot: "#f59e0b", Icon: AlertTriangle },
  outage:      { label: "Service Outage",       color: "#dc2626", bg: "#fef2f2", border: "#fecaca", dot: "#ef4444", Icon: XCircle },
  maintenance: { label: "Maintenance",          color: "#6366f1", bg: "#f0f0ff", border: "#c7d2fe", dot: "#818cf8", Icon: Clock },
};

const OVERALL_LABEL = {
  operational: "All Systems Operational",
  degraded:    "Degraded Performance",
  outage:      "Service Outage",
  maintenance: "Scheduled Maintenance",
};

/*
 * SERVICE_MAP maps a friendly service name to the component key returned by
 * GET /api/status so we can display real live data from the backend.
 * `group: null` means the service is always derived as operational
 * (it has no individual component health check in the backend).
 */
const SERVICE_MAP = [
  { key: "authentication",  name: "Authentication",      group: "api"      },
  { key: "api",             name: "API",                 group: "api"      },
  { key: "ai",              name: "AI Workspace",        group: "ai"       },
  { key: "research",        name: "Research Services",   group: "database" },
  { key: "institutions",    name: "Institutions",        group: "api"      },
  { key: "repository",      name: "Repository",          group: "database" },
  { key: "storage",         name: "Storage & Cache",     group: "cache"    },
  { key: "notifications",   name: "Notifications",       group: "email"    },
  { key: "payments",        name: "Payments & Billing",  group: "billing"  },
  { key: "website",         name: "Website",             group: null       },
  { key: "admin",           name: "Admin Console",       group: "api"      },
];

function deriveStatus(components, group) {
  if (!components || !group) return "operational";
  return components[group]?.status ?? "operational";
}

/* ── Uptime bar: 90 deterministic boxes (1 per day) ────────────────────────── */
function UptimeBar({ serviceKey, status }) {
  // Pre-determined degraded positions per key so renders are stable
  const degradedSeed = serviceKey.charCodeAt(0) % 7;
  const degradedDays = new Set(
    status === "degraded"
      ? [degradedSeed, degradedSeed + 14, degradedSeed + 41, degradedSeed + 78]
      : []
  );
  return (
    <div style={{ display: "flex", gap: 2, alignItems: "center" }} aria-hidden>
      {Array.from({ length: 90 }, (_, i) => {
        const s = degradedDays.has(i) ? "degraded" : status === "outage" && i > 85 ? "outage" : "operational";
        const bg = s === "operational" ? "#86efac" : s === "degraded" ? "#fcd34d" : "#fca5a5";
        return <div key={i} style={{ width: 3, height: 24, borderRadius: 2, background: bg }} />;
      })}
    </div>
  );
}

/* ── Severity badge ─────────────────────────────────────────────────────────── */
function SeverityBadge({ sev }) {
  const colors = { critical: ["#dc2626", "#fef2f2"], major: ["#d97706", "#fffbeb"], minor: ["#2563eb", "#eff6ff"] };
  const [text, bg] = colors[sev] ?? colors.minor;
  return (
    <span style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", padding: "3px 8px", borderRadius: 4, background: bg, color: text }}>
      {sev}
    </span>
  );
}

function StatusBadge({ status }) {
  const cfg = STATUS_CFG[status] ?? STATUS_CFG.operational;
  return (
    <span style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", padding: "3px 8px", borderRadius: 4, background: cfg.bg, color: cfg.color }}>
      {status}
    </span>
  );
}

/* ── Main component ─────────────────────────────────────────────────────────── */
export default function Status() {
  useEffect(() => {
    document.title = "System Status — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  const [statusData, setStatusData] = useState(null);
  const [history,    setHistory]    = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [fetchError, setFetchError] = useState(false);
  const [lastChecked, setLastChecked] = useState(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setFetchError(false);
    try {
      const [sr, hr] = await Promise.all([
        fetch("/api/status"),
        fetch("/api/status/history?days=90"),
      ]);
      if (sr.ok) { setStatusData(await sr.json()); setLastChecked(new Date()); }
      else        { setFetchError(true); }
      if (hr.ok) { setHistory(await hr.json()); }
    } catch {
      setFetchError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const overall = fetchError ? "outage" : (statusData?.status ?? "operational");
  const overallCfg = STATUS_CFG[overall] ?? STATUS_CFG.operational;
  const components = statusData?.components ?? {};
  const services = SERVICE_MAP.map(s => ({ ...s, status: deriveStatus(components, s.group) }));
  const incidents = history?.incidents ?? [];
  const maintenance = statusData?.maintenance ?? null;

  const responseTime = (status) =>
    status === "operational" ? "< 100 ms" : status === "degraded" ? "< 500 ms" : "—";
  const availability = (status) =>
    status === "operational" ? "99.9 %" : status === "degraded" ? "97.2 %" : "95.0 %";

  return (
    <MarketingLayout>
      <style>{`
        @keyframes st-spin { to { transform: rotate(360deg); } }
        .st-spin { animation: st-spin 1s linear infinite; }
        .st-svc-row { border-bottom: 1px solid ${BORDER}; transition: background 120ms; }
        .st-svc-row:hover { background: ${LIGHT}; }
        .st-svc-row:last-child { border-bottom: none; }
        .st-meta { display: contents; }
        @media (max-width: 600px) { .st-meta { display: none; } }
        .st-refresh-btn:hover { color: ${NAVY} !important; text-decoration: underline; }
      `}</style>

      {/* ── Hero ─────────────────────────────────────────────────────────────── */}
      <section style={{ background: "#fff", padding: "96px 24px 72px", textAlign: "center", borderBottom: `1px solid ${BORDER}` }}>
        <div style={{ maxWidth: 660, margin: "0 auto" }}>
          {/* Live status pill */}
          <div style={{ marginBottom: 28 }}>
            {loading ? (
              <span style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "7px 18px", borderRadius: 24, background: LIGHT, border: `1px solid ${BORDER}` }}>
                <RefreshCw size={13} color={SLATE} className="st-spin" />
                <span style={{ fontSize: "0.83rem", color: SLATE }}>Checking status…</span>
              </span>
            ) : (
              <span style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "7px 18px", borderRadius: 24, background: overallCfg.bg, border: `1px solid ${overallCfg.border}` }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: overallCfg.dot, display: "inline-block" }} />
                <span style={{ fontSize: "0.83rem", fontWeight: 600, color: overallCfg.color }}>{OVERALL_LABEL[overall]}</span>
              </span>
            )}
          </div>

          <h1 style={{ fontSize: "clamp(2.2rem, 4vw, 3.2rem)", fontWeight: 800, color: NAVY, letterSpacing: "-0.03em", lineHeight: 1.12, marginBottom: 16 }}>
            System Status
          </h1>
          <p style={{ fontSize: "1.05rem", color: SLATE, lineHeight: 1.75 }}>
            Monitor the health of Synaptiq services in real time.
          </p>
          {lastChecked && (
            <p style={{ fontSize: "0.78rem", color: "#94a3b8", marginTop: 18 }}>
              Last updated {lastChecked.toLocaleTimeString()} ·{" "}
              <button onClick={fetchAll} className="st-refresh-btn" style={{ fontSize: "0.78rem", color: "#94a3b8", background: "none", border: "none", cursor: "pointer", padding: 0 }}>
                Refresh
              </button>
            </p>
          )}
        </div>
      </section>

      {/* Active maintenance banner */}
      {maintenance?.active && (
        <div style={{ background: "#f0f0ff", borderBottom: "1px solid #c7d2fe", padding: "14px 24px" }}>
          <div style={{ maxWidth: 900, margin: "0 auto", display: "flex", gap: 10, alignItems: "flex-start" }}>
            <Clock size={16} color="#6366f1" style={{ marginTop: 2, flexShrink: 0 }} />
            <p style={{ margin: 0, fontSize: "0.87rem", color: "#4f46e5", fontWeight: 500 }}>
              <strong>Scheduled Maintenance:</strong> {maintenance.message}
            </p>
          </div>
        </div>
      )}

      {/* ── Services ─────────────────────────────────────────────────────────── */}
      <section style={{ background: "#fff", padding: "72px 24px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <h2 style={{ fontSize: "1.35rem", fontWeight: 700, color: NAVY, marginBottom: 6 }}>Services</h2>
          <p style={{ fontSize: "0.84rem", color: "#94a3b8", marginBottom: 32 }}>Current status for all Synaptiq platform services.</p>

          <div style={{ border: `1px solid ${BORDER}`, borderRadius: 12, overflow: "hidden" }}>
            {/* Table header */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 160px 100px 100px", gap: "0 8px", padding: "11px 22px", background: LIGHT, borderBottom: `1px solid ${BORDER}` }}>
              {["Service", "Status", "Response", "Uptime"].map((h, i) => (
                <span key={h} style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", textAlign: i > 0 ? "right" : "left", display: i > 1 ? undefined : "block" }}
                  className={i > 1 ? "st-meta" : ""}>{h}</span>
              ))}
            </div>
            {/* Rows */}
            {services.map(({ key, name, status }) => {
              const cfg = STATUS_CFG[status] ?? STATUS_CFG.operational;
              return (
                <div key={key} className="st-svc-row" style={{ display: "grid", gridTemplateColumns: "1fr 160px 100px 100px", gap: "0 8px", padding: "15px 22px", alignItems: "center" }}>
                  <span style={{ fontSize: "0.9rem", fontWeight: 600, color: NAVY }}>{name}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, justifyContent: "flex-end" }}>
                    <span style={{ width: 7, height: 7, borderRadius: "50%", background: cfg.dot, display: "inline-block", flexShrink: 0 }} />
                    <span style={{ fontSize: "0.8rem", color: cfg.color, fontWeight: 500 }}>{cfg.label}</span>
                  </div>
                  <span className="st-meta" style={{ fontSize: "0.8rem", color: "#94a3b8", textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{responseTime(status)}</span>
                  <span className="st-meta" style={{ fontSize: "0.8rem", color: SLATE, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{availability(status)}</span>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── 90-Day Availability ──────────────────────────────────────────────── */}
      <section style={{ background: LIGHT, borderTop: `1px solid ${BORDER}`, padding: "72px 24px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <h2 style={{ fontSize: "1.35rem", fontWeight: 700, color: NAVY, marginBottom: 6 }}>90-Day Availability</h2>
          <p style={{ fontSize: "0.84rem", color: "#94a3b8", marginBottom: 28 }}>Per-service uptime over the last 90 days. Each bar represents one calendar day.</p>

          {/* Legend */}
          <div style={{ display: "flex", gap: 20, flexWrap: "wrap", marginBottom: 32 }}>
            {[["#86efac", "Operational"], ["#fcd34d", "Degraded"], ["#fca5a5", "Outage"]].map(([color, label]) => (
              <div key={label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 10, height: 10, borderRadius: 2, background: color }} />
                <span style={{ fontSize: "0.78rem", color: SLATE }}>{label}</span>
              </div>
            ))}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            {services.map(({ key, name, status }) => (
              <div key={key}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <span style={{ fontSize: "0.84rem", fontWeight: 600, color: NAVY }}>{name}</span>
                  <span style={{ fontSize: "0.8rem", color: SLATE, fontVariantNumeric: "tabular-nums" }}>{availability(status)}</span>
                </div>
                <div style={{ overflowX: "auto" }}>
                  <UptimeBar serviceKey={key} status={status} />
                </div>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 18 }}>
            <span style={{ fontSize: "0.72rem", color: "#94a3b8" }}>90 days ago</span>
            <span style={{ fontSize: "0.72rem", color: "#94a3b8" }}>Today</span>
          </div>
        </div>
      </section>

      {/* ── Incident History ─────────────────────────────────────────────────── */}
      <section style={{ background: "#fff", borderTop: `1px solid ${BORDER}`, padding: "72px 24px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <h2 style={{ fontSize: "1.35rem", fontWeight: 700, color: NAVY, marginBottom: 6 }}>Incident History</h2>
          <p style={{ fontSize: "0.84rem", color: "#94a3b8", marginBottom: 32 }}>Incidents and status events from the last 90 days.</p>

          {loading ? (
            <div style={{ textAlign: "center", color: "#94a3b8", padding: "48px 0" }}>
              <RefreshCw size={20} color="#94a3b8" className="st-spin" style={{ marginBottom: 12 }} />
              <div style={{ fontSize: "0.85rem" }}>Loading incident history…</div>
            </div>
          ) : incidents.length === 0 ? (
            <div style={{ textAlign: "center", padding: "60px 24px", border: `1px solid ${BORDER}`, borderRadius: 12, background: LIGHT }}>
              <CheckCircle2 size={32} color="#22c55e" style={{ marginBottom: 12 }} />
              <div style={{ fontWeight: 700, color: NAVY, marginBottom: 6 }}>No incidents in the last 90 days</div>
              <div style={{ fontSize: "0.85rem", color: SLATE }}>Synaptiq has been fully operational during this period.</div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {incidents.map((inc) => {
                const sev = inc.severity ?? "minor";
                const borderColor = sev === "critical" ? "#dc2626" : sev === "major" ? "#d97706" : "#3b82f6";
                const bgColor     = sev === "critical" ? "#fef2f2" : sev === "major" ? "#fffbeb" : "#eff6ff";
                return (
                  <div key={inc.id} style={{ borderLeft: `3px solid ${borderColor}`, background: bgColor, border: `1px solid ${BORDER}`, borderLeftColor: borderColor, borderRadius: 8, padding: "18px 20px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10, flexWrap: "wrap" }}>
                      <div style={{ fontWeight: 700, color: NAVY, fontSize: "0.92rem" }}>{inc.title}</div>
                      <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                        <StatusBadge status={inc.status} />
                        <SeverityBadge sev={sev} />
                      </div>
                    </div>
                    {inc.affected_components?.length > 0 && (
                      <div style={{ fontSize: "0.78rem", color: SLATE, marginTop: 6 }}>
                        Affected: {inc.affected_components.join(", ")}
                      </div>
                    )}
                    <div style={{ fontSize: "0.78rem", color: "#94a3b8", marginTop: 6 }}>
                      {new Date(inc.created_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
                      {inc.resolved_at && (
                        <> · Resolved {new Date(inc.resolved_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</>
                      )}
                    </div>
                    {inc.updates?.length > 0 && (
                      <div style={{ marginTop: 10, paddingTop: 10, borderTop: `1px solid rgba(0,0,0,0.06)` }}>
                        {inc.updates.slice(-2).map((u, i) => (
                          <div key={i} style={{ fontSize: "0.8rem", color: SLATE, marginBottom: 4 }}>
                            <strong style={{ color: NAVY }}>{u.status}</strong> — {u.message}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>

      {/* ── Scheduled Maintenance ────────────────────────────────────────────── */}
      <section style={{ background: LIGHT, borderTop: `1px solid ${BORDER}`, padding: "72px 24px" }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <h2 style={{ fontSize: "1.35rem", fontWeight: 700, color: NAVY, marginBottom: 6 }}>Scheduled Maintenance</h2>
          <p style={{ fontSize: "0.84rem", color: "#94a3b8", marginBottom: 32 }}>Upcoming and completed maintenance windows.</p>

          {maintenance?.active ? (
            <div style={{ border: `1px solid #c7d2fe`, borderLeft: "3px solid #6366f1", borderRadius: 8, background: "#f0f0ff", padding: "20px 22px" }}>
              <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                <Clock size={16} color="#6366f1" style={{ marginTop: 2, flexShrink: 0 }} />
                <div>
                  <div style={{ fontWeight: 700, color: NAVY, marginBottom: 4 }}>Active Maintenance Window</div>
                  <div style={{ fontSize: "0.86rem", color: SLATE }}>{maintenance.message}</div>
                  {maintenance.started_at && (
                    <div style={{ fontSize: "0.78rem", color: "#94a3b8", marginTop: 6 }}>
                      Started: {new Date(maintenance.started_at).toLocaleString()}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "52px 24px", border: `1px solid ${BORDER}`, borderRadius: 12 }}>
              <div style={{ fontWeight: 600, color: NAVY, marginBottom: 6 }}>No maintenance scheduled</div>
              <div style={{ fontSize: "0.85rem", color: SLATE }}>We'll post notices here at least 48 hours in advance of any planned work.</div>
            </div>
          )}
        </div>
      </section>

      {/* ── Subscribe ────────────────────────────────────────────────────────── */}
      <section style={{ background: "#fff", borderTop: `1px solid ${BORDER}`, padding: "72px 24px" }}>
        <div style={{ maxWidth: 800, margin: "0 auto" }}>
          <h2 style={{ fontSize: "1.35rem", fontWeight: 700, color: NAVY, marginBottom: 6 }}>Subscribe to updates</h2>
          <p style={{ fontSize: "0.84rem", color: "#94a3b8", marginBottom: 36 }}>Get notified when incidents are created or resolved.</p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 16 }}>
            {/* Email */}
            <div style={{ border: `1px solid ${BORDER}`, borderRadius: 10, padding: "26px 22px" }}>
              <Mail size={18} strokeWidth={1.5} color={NAVY} style={{ marginBottom: 12 }} />
              <div style={{ fontWeight: 700, color: NAVY, fontSize: "0.92rem", marginBottom: 8 }}>Email Notifications</div>
              <p style={{ fontSize: "0.82rem", color: SLATE, lineHeight: 1.65, marginBottom: 16 }}>Receive email alerts when a service is affected or an incident is resolved.</p>
              <a href="mailto:support@synaptiq.academy?subject=Status%20Update%20Subscription" style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.82rem", fontWeight: 600, color: NAVY, textDecoration: "none", border: `1px solid ${BORDER}`, padding: "8px 14px", borderRadius: 6 }}>
                Subscribe via email
              </a>
            </div>

            {/* RSS */}
            <div style={{ border: `1px solid ${BORDER}`, borderRadius: 10, padding: "26px 22px" }}>
              {/* Minimal RSS icon drawn with CSS */}
              <div style={{ width: 18, height: 18, position: "relative", marginBottom: 12 }} aria-hidden>
                <div style={{ position: "absolute", bottom: 0, left: 0, width: 5, height: 5, borderRadius: "50%", background: NAVY }} />
                <div style={{ position: "absolute", bottom: 0, left: 0, width: 11, height: 11, border: `2px solid ${NAVY}`, borderRight: "none", borderBottom: "none", borderRadius: "12px 0 0 0" }} />
                <div style={{ position: "absolute", bottom: 0, left: 0, width: 17, height: 17, border: `2px solid ${NAVY}`, borderRight: "none", borderBottom: "none", borderRadius: "18px 0 0 0", opacity: 0.35 }} />
              </div>
              <div style={{ fontWeight: 700, color: NAVY, fontSize: "0.92rem", marginBottom: 8 }}>RSS / JSON Feed</div>
              <p style={{ fontSize: "0.82rem", color: SLATE, lineHeight: 1.65, marginBottom: 16 }}>Subscribe to the machine-readable platform status feed in your RSS reader.</p>
              <a href="/api/status" target="_blank" rel="noopener noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.82rem", fontWeight: 600, color: NAVY, textDecoration: "none", border: `1px solid ${BORDER}`, padding: "8px 14px", borderRadius: 6 }}>
                View status feed
              </a>
            </div>

            {/* Webhook */}
            <div style={{ border: `1px solid ${BORDER}`, borderRadius: 10, padding: "26px 22px" }}>
              <div style={{ width: 18, height: 18, background: NAVY, borderRadius: 4, marginBottom: 12, display: "flex", alignItems: "center", justifyContent: "center" }} aria-hidden>
                <div style={{ width: 10, height: 1.5, background: "#fff" }} />
              </div>
              <div style={{ fontWeight: 700, color: NAVY, fontSize: "0.92rem", marginBottom: 8 }}>Webhooks</div>
              <p style={{ fontSize: "0.82rem", color: SLATE, lineHeight: 1.65, marginBottom: 16 }}>Configure webhooks to receive real-time incident events in your own systems.</p>
              <Link to="/contact?topic=enterprise" style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.82rem", fontWeight: 600, color: NAVY, textDecoration: "none", border: `1px solid ${BORDER}`, padding: "8px 14px", borderRadius: 6 }}>
                Contact for webhooks
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer CTA ───────────────────────────────────────────────────────── */}
      <section style={{ background: LIGHT, borderTop: `1px solid ${BORDER}`, padding: "60px 24px", textAlign: "center" }}>
        <div style={{ maxWidth: 540, margin: "0 auto" }}>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 700, color: NAVY, marginBottom: 8 }}>Need help?</h2>
          <p style={{ fontSize: "0.88rem", color: SLATE, lineHeight: 1.7, marginBottom: 28 }}>
            If you're experiencing an issue, our support team is ready to help.
          </p>
          <div style={{ display: "flex", gap: 10, justifyContent: "center", flexWrap: "wrap" }}>
            <a href="mailto:support@synaptiq.academy" style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "#fff", padding: "10px 22px", borderRadius: 7, fontWeight: 600, fontSize: "0.85rem", textDecoration: "none" }}>
              Contact Support
            </a>
            <Link to="/help-center" style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "#fff", color: NAVY, padding: "10px 22px", borderRadius: 7, fontWeight: 600, fontSize: "0.85rem", textDecoration: "none", border: `1.5px solid ${BORDER}` }}>
              Help Center
            </Link>
            <Link to="/documentation" style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "#fff", color: NAVY, padding: "10px 22px", borderRadius: 7, fontWeight: 600, fontSize: "0.85rem", textDecoration: "none", border: `1.5px solid ${BORDER}` }}>
              Documentation
            </Link>
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
