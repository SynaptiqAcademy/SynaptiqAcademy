import React, { useState, useEffect, useCallback } from "react";
import {
  Shield, AlertTriangle, CheckCircle, XCircle, RefreshCw,
  ChevronDown, ChevronUp, ExternalLink, Info, Loader2,
  User, BookOpen, Quote, DollarSign, Activity,
} from "lucide-react";
import { NAVY, WARM, BRD, ACCENT, EMERALD, WHITE, TEXT_SECONDARY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";

const API = process.env.REACT_APP_API_URL || "";
const token = () => localStorage.getItem("token");
const authH = () => ({ Authorization: `Bearer ${token()}` });

const GRADE_COLOR = {
  "A+": "#059669", A: "#059669", B: "#0ea5e9", C: "#f59e0b", D: "#f97316", F: "#dc2626",
};

const LEVEL_COLOR = {
  critical: "#dc2626", high: "#f97316", medium: "#f59e0b", low: "#6b7280",
};

const FACTOR_LABELS = {
  identity: "Identity",
  publications: "Publications",
  citations: "Citations",
  grants: "Grants",
  collaboration: "Collaboration",
  metadata: "Metadata",
  verification_coverage: "Verification",
  profile_consistency: "Consistency",
  institution: "Institution",
  activity: "Activity",
};

function ScoreRing({ score, grade }) {
  const radius = 54;
  const circ = 2 * Math.PI * radius;
  const progress = ((score || 0) / 100) * circ;
  const color = GRADE_COLOR[grade] || ACCENT;
  return (
    <div style={{ position: "relative", width: 140, height: 140 }}>
      <svg width={140} height={140} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={70} cy={70} r={radius} fill="none" stroke={`${color}22`} strokeWidth={10} />
        <circle
          cx={70} cy={70} r={radius} fill="none"
          stroke={color} strokeWidth={10}
          strokeDasharray={`${progress} ${circ}`}
          strokeLinecap="round"
          style={{ transition: "stroke-dasharray 0.8s ease" }}
        />
      </svg>
      <div style={{
        position: "absolute", inset: 0, display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
      }}>
        <span style={{ fontSize: 28, fontWeight: 800, color: NAVY, lineHeight: 1 }}>{score ?? "—"}</span>
        <span style={{ fontSize: 14, fontWeight: 700, color }}>Grade {grade || "—"}</span>
      </div>
    </div>
  );
}

function RiskFlag({ flag, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const color = LEVEL_COLOR[flag.level] || "#6b7280";
  return (
    <div style={{
      border: `1px solid ${color}33`,
      borderLeft: `4px solid ${color}`,
      borderRadius: 8, marginBottom: 8, background: WHITE,
      overflow: "hidden",
    }}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          width: "100%", padding: "10px 14px", display: "flex",
          alignItems: "center", gap: 10, background: "none", border: "none",
          cursor: "pointer", textAlign: "left",
        }}
      >
        <span style={{
          fontSize: 11, fontWeight: 700, textTransform: "uppercase",
          letterSpacing: "0.05em", color, minWidth: 64,
        }}>{flag.level}</span>
        <span style={{ flex: 1, fontWeight: 600, fontSize: 14, color: NAVY }}>{flag.title}</span>
        <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>{flag.confidence}%</span>
        {open ? <ChevronUp size={14} color={TEXT_SECONDARY} /> : <ChevronDown size={14} color={TEXT_SECONDARY} />}
      </button>
      {open && (
        <div style={{ padding: "0 14px 12px 14px" }}>
          <p style={{ fontSize: 13, color: "#334155", margin: "0 0 8px" }}>{flag.description}</p>
          <div style={{
            background: `${color}10`, borderRadius: 6, padding: "8px 12px",
            fontSize: 13, color: "#334155",
          }}>
            <strong>Action:</strong> {flag.action}
          </div>
        </div>
      )}
    </div>
  );
}

function FactorBar({ label, value, weight }) {
  const pct = Math.round(value || 0);
  const barColor = pct >= 70 ? EMERALD : pct >= 50 ? "#f59e0b" : ACCENT;
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
        <span style={{ fontSize: 13, color: NAVY, fontWeight: 500 }}>{label}</span>
        <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>
          {pct}/100 <span style={{ opacity: 0.6 }}>({(weight * 100).toFixed(0)}%)</span>
        </span>
      </div>
      <div style={{ height: 6, background: `${NAVY}12`, borderRadius: 99 }}>
        <div style={{
          height: "100%", borderRadius: 99, background: barColor,
          width: `${pct}%`, transition: "width 0.6s ease",
        }} />
      </div>
    </div>
  );
}

function Section({ title, icon: Icon, children }) {
  return (
    <div style={{
      background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12,
      padding: 20, marginBottom: 16,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
        <Icon size={16} color={ACCENT} />
        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: NAVY }}>{title}</h3>
      </div>
      {children}
    </div>
  );
}

export default function IntegrityCenter() {
  const [report, setReport]   = useState(null);
  const [status, setStatus]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [err, setErr]         = useState(null);

  const loadStatus = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/integrity/status`, { headers: authH() });
      if (r.ok) setStatus(await r.json());
    } catch (_) {}
  }, []);

  const loadReport = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/integrity/report`, { headers: authH() });
      if (r.ok) {
        const d = await r.json();
        if (d.status !== "not_started" && d.status !== "pending" && d.status !== "running") {
          setReport(d);
        }
      }
    } catch (_) {}
  }, []);

  useEffect(() => {
    (async () => {
      setLoading(true);
      await Promise.all([loadReport(), loadStatus()]);
      setLoading(false);
    })();
  }, [loadReport, loadStatus]);

  // Poll while running
  useEffect(() => {
    if (status?.status !== "running" && status?.status !== "pending") return;
    const iv = setInterval(async () => {
      await loadStatus();
      await loadReport();
    }, 4000);
    return () => clearInterval(iv);
  }, [status, loadStatus, loadReport]);

  const handleAnalyze = async (force = false) => {
    setRunning(true);
    setErr(null);
    try {
      const r = await fetch(`${API}/api/integrity/analyze`, {
        method: "POST",
        headers: { ...authH(), "Content-Type": "application/json" },
        body: JSON.stringify({ force_refresh: force }),
      });
      const d = await r.json();
      setStatus(d);
    } catch (e) {
      setErr("Failed to trigger analysis. Please try again.");
    } finally {
      setRunning(false);
    }
  };

  const isAnalyzing = status?.status === "running" || status?.status === "pending";

  if (loading) {
    return (
      <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Loader2 size={32} color={ACCENT} style={{ animation: "spin 1s linear infinite" }} />
      </div>
    );
  }

  return (
    <ResearchLayout
      title="Integrity Engine"
      subtitle="Academic integrity analysis across identity, publications, citations, and grants"
      actions={
        <button
          onClick={() => handleAnalyze(!report)}
          disabled={running || isAnalyzing}
          style={{
            background: running || isAnalyzing ? NAVY : WHITE,
            color: running || isAnalyzing ? WHITE : NAVY,
            border: `1px solid ${NAVY}`, borderRadius: 8, padding: "8px 18px",
            fontWeight: 700, fontSize: 13, cursor: running || isAnalyzing ? "not-allowed" : "pointer",
            display: "flex", alignItems: "center", gap: 6, opacity: running || isAnalyzing ? 0.6 : 1,
          }}
        >
          {running || isAnalyzing
            ? <><Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> Analyzing…</>
            : <><RefreshCw size={14} /> {report ? "Re-Analyze" : "Run Analysis"}</>}
        </button>
      }
    >
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "0 4px" }}>

      {err && (
        <div style={{ background: "#fee2e2", border: "1px solid #fca5a5", borderRadius: 8,
          padding: "12px 16px", color: "#991b1b", marginBottom: 16, fontSize: 14 }}>
          {err}
        </div>
      )}

      {isAnalyzing && (
        <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 8,
          padding: "12px 16px", color: "#1e40af", marginBottom: 16, fontSize: 14,
          display: "flex", alignItems: "center", gap: 8 }}>
          <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
          Analysis in progress — verifying identity, publications, citations, and grants with external providers…
        </div>
      )}

      {!report && !isAnalyzing && (
        <div style={{
          background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12, padding: 40,
          textAlign: "center",
        }}>
          <Shield size={40} color={`${NAVY}40`} style={{ marginBottom: 12 }} />
          <h3 style={{ margin: "0 0 8px", color: NAVY, fontSize: 16, fontWeight: 700 }}>
            No Integrity Report Yet
          </h3>
          <p style={{ margin: "0 0 20px", color: TEXT_SECONDARY, fontSize: 14 }}>
            Run an analysis to verify your identity, publications, citations, and grants against 7 external providers.
          </p>
          <button
            onClick={() => handleAnalyze(false)}
            disabled={running}
            style={{
              background: NAVY, color: WHITE, border: "none", borderRadius: 8,
              padding: "10px 24px", fontWeight: 700, fontSize: 14, cursor: "pointer",
            }}
          >
            Run First Analysis
          </button>
        </div>
      )}

      {report && (
        <>
          {/* Score + Grade */}
          <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 24, marginBottom: 24 }}>
            <div style={{
              background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12,
              padding: 24, display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
            }}>
              <ScoreRing score={report.integrity_score} grade={report.grade} />
              <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>
                Integrity Score
              </span>
              <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>
                {report.generated_at ? new Date(report.generated_at).toLocaleDateString() : ""}
              </span>
            </div>
            <Section title="Score Breakdown" icon={Activity}>
              {Object.entries(report.score_factors || {}).map(([k, v]) => (
                <FactorBar
                  key={k}
                  label={FACTOR_LABELS[k] || k}
                  value={v}
                  weight={(report.score_weights || {})[k] || 0}
                />
              ))}
            </Section>
          </div>

          {/* Risk Flags */}
          {(report.risk_flags || []).length > 0 && (
            <Section title={`Risk Flags (${report.risk_flags.length})`} icon={AlertTriangle}>
              <div style={{ display: "flex", gap: 12, marginBottom: 12 }}>
                {report.critical_risks > 0 && (
                  <span style={{ fontSize: 12, fontWeight: 700, color: "#dc2626",
                    background: "#fee2e2", padding: "2px 8px", borderRadius: 99 }}>
                    {report.critical_risks} Critical
                  </span>
                )}
                {report.high_risks > 0 && (
                  <span style={{ fontSize: 12, fontWeight: 700, color: "#f97316",
                    background: "#ffedd5", padding: "2px 8px", borderRadius: 99 }}>
                    {report.high_risks} High
                  </span>
                )}
              </div>
              {(report.risk_flags || [])
                .sort((a, b) => {
                  const order = { critical: 0, high: 1, medium: 2, low: 3 };
                  return (order[a.level] ?? 4) - (order[b.level] ?? 4);
                })
                .map((f, i) => (
                  <RiskFlag key={f.key || i} flag={f} defaultOpen={f.level === "critical"} />
                ))}
            </Section>
          )}

          {report.risk_flags?.length === 0 && (
            <div style={{
              background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 12,
              padding: "16px 20px", display: "flex", alignItems: "center", gap: 10, marginBottom: 16,
              color: "#166534",
            }}>
              <CheckCircle size={18} color={EMERALD} />
              <span style={{ fontWeight: 600, fontSize: 14 }}>No risk flags detected — your integrity profile looks clean.</span>
            </div>
          )}

          {/* Domain summaries */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            {/* Identity */}
            <Section title="Identity Analysis" icon={User}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                <span style={{ fontSize: 22, fontWeight: 800, color: NAVY }}>
                  {report.identity?.score ?? "—"}
                  <span style={{ fontSize: 14, color: TEXT_SECONDARY, fontWeight: 500 }}>/100</span>
                </span>
              </div>
              {(report.identity?.checks || []).slice(0, 5).map((c, i) => (
                <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 6 }}>
                  {c.passed
                    ? <CheckCircle size={14} color={EMERALD} style={{ marginTop: 2, flexShrink: 0 }} />
                    : <XCircle size={14} color={ACCENT} style={{ marginTop: 2, flexShrink: 0 }} />}
                  <span style={{ fontSize: 12, color: "#334155" }}>
                    {c.check.replace(/_/g, " ")}
                    {c.issue ? ` — ${c.issue}` : ""}
                  </span>
                </div>
              ))}
            </Section>

            {/* Publications */}
            <Section title="Publication Analysis" icon={BookOpen}>
              <div style={{ display: "flex", gap: 16, marginBottom: 12 }}>
                {[
                  { label: "Total", val: report.publications?.total ?? 0 },
                  { label: "Verified", val: report.publications?.verified ?? 0, good: true },
                  { label: "Retracted", val: report.publications?.retracted_count ?? 0, bad: true },
                ].map(({ label, val, good, bad }) => (
                  <div key={label} style={{ textAlign: "center" }}>
                    <div style={{
                      fontSize: 20, fontWeight: 800,
                      color: bad && val > 0 ? ACCENT : good ? EMERALD : NAVY,
                    }}>{val}</div>
                    <div style={{ fontSize: 11, color: TEXT_SECONDARY }}>{label}</div>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>
                Score: <strong style={{ color: NAVY }}>{report.publications?.score ?? "—"}/100</strong>
              </div>
            </Section>

            {/* Citations */}
            <Section title="Citation Analysis" icon={Quote}>
              <div style={{ display: "flex", gap: 16, marginBottom: 12 }}>
                {[
                  { label: "Total", val: report.citations?.total_citations ?? 0 },
                  { label: "Avg/Pub", val: report.citations?.average_per_pub ?? 0 },
                  { label: "Velocity", val: report.citations?.velocity ?? "stable" },
                ].map(({ label, val }) => (
                  <div key={label} style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 18, fontWeight: 800, color: NAVY }}>{val}</div>
                    <div style={{ fontSize: 11, color: TEXT_SECONDARY }}>{label}</div>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>
                Score: <strong style={{ color: NAVY }}>{report.citations?.score ?? "—"}/100</strong>
              </div>
            </Section>

            {/* Grants */}
            <Section title="Grant Analysis" icon={DollarSign}>
              <div style={{ display: "flex", gap: 16, marginBottom: 12 }}>
                {[
                  { label: "Total", val: report.grants?.total ?? 0 },
                  { label: "Complete", val: report.grants?.complete ?? 0, good: true },
                  { label: "Recognized", val: report.grants?.funder_recognized ?? 0, good: true },
                ].map(({ label, val, good }) => (
                  <div key={label} style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 18, fontWeight: 800, color: good ? EMERALD : NAVY }}>{val}</div>
                    <div style={{ fontSize: 11, color: TEXT_SECONDARY }}>{label}</div>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>
                Score: <strong style={{ color: NAVY }}>{report.grants?.score ?? "—"}/100</strong>
              </div>
            </Section>
          </div>
        </>
      )}
    </div>
    </ResearchLayout>
  );
}
