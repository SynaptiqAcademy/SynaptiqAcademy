import React, { useState, useCallback, useEffect } from "react";
import { Search, AlertTriangle, CheckCircle, Play, Clock, RefreshCw } from "lucide-react";
import api from "@/lib/api";
import { NAVY, EMERALD, AMBER, CRIMSON } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Card, Button, Badge, EmptyState, Spinner } from "@/components/ds";

function useAOS(path) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetch = useCallback(() => {
    setLoading(true);
    api.get(`/admin/aos/${path}`)
      .then((r) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [path]);
  useEffect(() => { fetch(); }, [fetch]);
  return { data, loading, refetch: fetch };
}

const SCORE_LABELS = {
  platform_health:  "Platform Health",
  security:         "Security",
  performance:      "Performance",
  academic_quality: "Academic Quality",
  ux:               "UX & Onboarding",
};

function scoreColor(score) {
  return score >= 70 ? EMERALD : score >= 40 ? AMBER : CRIMSON;
}

function ScoreMeter({ label, score }) {
  const color = scoreColor(score);
  return (
    <Card padding="md">
      <div className="flex items-end justify-between mb-2">
        <div className="text-xs text-slate-500">{label}</div>
        <div className="text-2xl font-bold" style={{ color }}>{score}</div>
      </div>
      <div className="h-2 rounded-full overflow-hidden bg-slate-100">
        <div className="h-full transition-all" style={{ width: `${score}%`, background: color }} />
      </div>
    </Card>
  );
}

const SEVERITY_BADGE = {
  critical: "danger",
  high:     "warning",
  medium:   "warning",
  low:      "info",
};

const SEVERITY_ACCENT = {
  critical: CRIMSON,
  high:     "#f97316",
  medium:   AMBER,
  low:      "#3B82F6",
};

export default function AdminPlatformAuditor() {
  const { data: report, loading, refetch } = useAOS("platform-audit/report");
  const [running, setRunning] = useState(false);
  const [runMsg, setRunMsg] = useState("");

  const runAudit = async () => {
    setRunning(true);
    setRunMsg("");
    try {
      await api.post("/admin/aos/platform-audit/run");
      setRunMsg("Audit complete");
      refetch();
    } catch (e) {
      setRunMsg(e?.response?.data?.detail || "Audit failed");
    } finally {
      setRunning(false);
    }
  };

  const r = report || {};
  const overallColor = scoreColor(r.overall_score || 0);

  return (
    <AdministrationLayout
      title="Platform Auditor"
      subtitle="Automated scoring across Health, Security, Performance, Academic Quality, and UX"
      actions={
        <div className="flex items-center gap-2">
          {runMsg && <span className="text-xs text-slate-500">{runMsg}</span>}
          <Button variant="hero" size="sm" onClick={runAudit} loading={running}>
            <Play size={12} />
            {running ? "Running Audit..." : "Run Audit"}
          </Button>
          <Button variant="hero" size="icon" onClick={refetch} aria-label="Refresh">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </Button>
        </div>
      }
    >
      {loading ? (
        <div className="flex items-center justify-center gap-2 py-12 text-slate-500">
          <Spinner size={18} /> Loading audit report...
        </div>
      ) : r.message ? (
        <EmptyState
          icon={<Search />}
          title={r.message}
          action={
            <Button variant="primary" onClick={runAudit} loading={running}>
              <Play size={14} />
              {running ? "Running..." : "Run First Audit"}
            </Button>
          }
        />
      ) : (
        <div className="flex flex-col gap-6">
          {/* Overall Score */}
          <Card accent={overallColor} padding="xl">
            <div className="flex items-center gap-6">
              <div className="text-6xl font-bold" style={{ color: overallColor }}>
                {r.overall_score}
              </div>
              <div>
                <div className="font-semibold text-lg text-slate-800">Overall Platform Score</div>
                <div className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                  <Clock size={11} />
                  Last audited: {(r.audited_at || "").slice(0, 19)}
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  {(r.issue_count || 0)} issue{r.issue_count !== 1 ? "s" : ""} detected
                </div>
              </div>
            </div>
          </Card>

          {/* Score breakdown */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.entries(r.scores || {}).map(([key, score]) => (
              <ScoreMeter key={key} label={SCORE_LABELS[key] || key} score={score} />
            ))}
          </div>

          {/* Issues */}
          {(r.issues || []).length > 0 && (
            <div className="flex flex-col gap-3">
              <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
                Issues ({r.issues.length})
              </h2>
              {r.issues.map((issue, i) => (
                <Card key={i} accent={SEVERITY_ACCENT[issue.severity] || "#94a3b8"} padding="sm">
                  <div className="flex items-start gap-3">
                    <AlertTriangle size={14} className="flex-shrink-0 mt-0.5 text-slate-400" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge variant={SEVERITY_BADGE[issue.severity] || "neutral"} size="sm">{issue.severity}</Badge>
                        <span className="text-xs font-medium text-slate-700">{issue.area?.toUpperCase()}</span>
                      </div>
                      <div className="text-xs text-slate-600 mt-1">{issue.message}</div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {(r.issues || []).length === 0 && (
            <Card accent={EMERALD} padding="sm">
              <div className="flex items-center gap-2 text-sm text-emerald-700">
                <CheckCircle size={14} />
                No issues detected. Platform is healthy.
              </div>
            </Card>
          )}

          {/* Metrics detail */}
          {r.metrics && (
            <Card padding="md">
              <div className="text-sm font-semibold text-slate-800 mb-3">Audit Metrics</div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(r.metrics).map(([key, value]) => (
                  <div key={key}>
                    <div className="text-[10px] text-slate-500 mb-1">{key.replace(/_/g, " ")}</div>
                    <div className="text-sm text-slate-800">
                      {typeof value === "boolean" ? (value ? "Yes" : "No") : String(value)}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}
    </AdministrationLayout>
  );
}
