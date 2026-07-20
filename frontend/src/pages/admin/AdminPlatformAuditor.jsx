import React, { useState, useCallback, useEffect } from "react";
import { Search, RefreshCw, AlertTriangle, CheckCircle, Play, Clock } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";

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

function ScoreMeter({ label, score }) {
  const color = score >= 70 ? "bg-green-500 text-green-400" : score >= 40 ? "bg-yellow-500 text-yellow-400" : "bg-red-500 text-red-400";
  const [barColor, textColor] = color.split(" ");
  return (
    <div className="bg-[#0F2847] border border-[#1a3050] p-4">
      <div className="flex items-end justify-between mb-2">
        <div className="text-xs text-slate-400">{label}</div>
        <div className={`text-2xl font-bold ${textColor}`}>{score}</div>
      </div>
      <div className="h-2 bg-[#1a3050] rounded-full overflow-hidden">
        <div className={`h-full ${barColor} transition-all`} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

const SEVERITY_COLORS = {
  critical: "border-red-700 bg-red-900/20 text-red-400",
  high:     "border-orange-700 bg-orange-900/20 text-orange-400",
  medium:   "border-yellow-700 bg-yellow-900/20 text-yellow-400",
  low:      "border-blue-700 bg-blue-900/20 text-blue-400",
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
  const overallColor = (r.overall_score || 0) >= 70
    ? "text-green-400 border-green-700"
    : (r.overall_score || 0) >= 40
    ? "text-yellow-400 border-yellow-700"
    : "text-red-400 border-red-700";

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Platform Auditor</h1>
          <p className="text-sm text-slate-400 mt-0.5">Automated scoring across Health, Security, Performance, Academic Quality, and UX</p>
        </div>
        <div className="flex items-center gap-2">
          {runMsg && <span className="text-xs text-slate-400">{runMsg}</span>}
          <button
            onClick={runAudit}
            disabled={running}
            className="flex items-center gap-1.5 text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-3 py-1.5 transition-colors"
          >
            <Play size={12} />
            {running ? "Running Audit..." : "Run Audit"}
          </button>
          <button onClick={refetch} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-slate-500">Loading audit report...</div>
      ) : r.message ? (
        <div className="bg-[#0F2847] border border-[#1a3050] p-8 text-center">
          <Search size={32} className="text-slate-500 mx-auto mb-3" />
          <div className="text-slate-400 mb-4">{r.message}</div>
          <button
            onClick={runAudit}
            disabled={running}
            className="inline-flex items-center gap-1.5 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-4 py-2"
          >
            <Play size={14} />
            {running ? "Running..." : "Run First Audit"}
          </button>
        </div>
      ) : (
        <>
          {/* Overall Score */}
          <div className={`bg-[#0F2847] border-2 ${overallColor.split(" ")[1]} p-6 flex items-center gap-6`}>
            <div className={`text-6xl font-bold ${overallColor.split(" ")[0]}`}>
              {r.overall_score}
            </div>
            <div>
              <div className="text-white font-semibold text-lg">Overall Platform Score</div>
              <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                <Clock size={11} />
                Last audited: {(r.audited_at || "").slice(0, 19)}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                {(r.issue_count || 0)} issue{r.issue_count !== 1 ? "s" : ""} detected
              </div>
            </div>
          </div>

          {/* Score breakdown */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.entries(r.scores || {}).map(([key, score]) => (
              <ScoreMeter key={key} label={SCORE_LABELS[key] || key} score={score} />
            ))}
          </div>

          {/* Issues */}
          {(r.issues || []).length > 0 && (
            <div className="space-y-3">
              <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
                Issues ({r.issues.length})
              </h2>
              {r.issues.map((issue, i) => {
                const cls = SEVERITY_COLORS[issue.severity] || "border-slate-700 bg-slate-800/20 text-slate-400";
                return (
                  <div key={i} className={`border p-3 flex items-start gap-3 ${cls}`}>
                    <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="text-xs font-medium">
                        [{issue.severity}] {issue.area?.toUpperCase()}
                      </div>
                      <div className="text-xs text-slate-300 mt-0.5">{issue.message}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {(r.issues || []).length === 0 && (
            <div className="flex items-center gap-2 text-green-400 text-sm bg-green-900/20 border border-green-700/40 p-3">
              <CheckCircle size={14} />
              No issues detected. Platform is healthy.
            </div>
          )}

          {/* Metrics detail */}
          {r.metrics && (
            <div className="bg-[#0F2847] border border-[#1a3050] p-4">
              <div className="text-sm font-semibold text-white mb-3">Audit Metrics</div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(r.metrics).map(([key, value]) => (
                  <div key={key}>
                    <div className="text-[10px] text-slate-500 mb-1">{key.replace(/_/g, " ")}</div>
                    <div className="text-sm text-white">
                      {typeof value === "boolean" ? (value ? "Yes" : "No") : String(value)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
