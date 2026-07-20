/* eslint-disable */
import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, AlertTriangle, CheckCircle, Wrench } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

function useX(path, params = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const query = new URLSearchParams(params).toString();
  const load = useCallback(() => {
    setLoading(true);
    api.get(`/admin/x/${path}${query ? "?" + query : ""}`)
      .then(r => setData(r.data)).catch(() => setData(null)).finally(() => setLoading(false));
  }, [path, query]);
  useEffect(() => { load(); }, [load]);
  return { data, loading, refetch: load };
}

function ScoreMeter({ label, score, description }) {
  const color = score >= 80 ? "bg-green-500" : score >= 55 ? "bg-yellow-500" : "bg-red-500";
  const textColor = score >= 80 ? "text-green-400" : score >= 55 ? "text-yellow-400" : "text-red-400";
  return (
    <div className="bg-[#0F2847] border border-[#1a3050] p-4">
      <div className="flex items-end gap-2 mb-1">
        <span className={`text-3xl font-bold ${textColor}`}>{score ?? 0}</span>
        <span className="text-slate-500 text-xs mb-1">/100</span>
      </div>
      <div className="text-xs text-white mb-1">{label}</div>
      <div className="h-1 bg-[#1a3050] rounded-full overflow-hidden mb-1.5">
        <div className={`h-full ${color} transition-all`} style={{ width: `${score ?? 0}%` }} />
      </div>
      {description && <div className="text-[10px] text-slate-500">{description}</div>}
    </div>
  );
}

const SEVERITY_STYLE = {
  high:   "border-l-red-500 bg-red-900/20 text-red-300",
  medium: "border-l-yellow-500 bg-yellow-900/20 text-yellow-300",
  low:    "border-l-blue-500 bg-blue-900/20 text-blue-300",
};

export default function AdminDataQuality() {
  const { data: scores, loading: sL, refetch: refScores } = useX("data-quality/scores");
  const { data: issues, loading: iL, refetch: refIssues } = useX("data-quality/issues");
  const [remedResp, setRemedResp] = useState("");
  const [remediating, setRemediating] = useState(false);
  const refetchAll = () => { refScores(); refIssues(); };

  const s = scores || {};
  const issueList = issues?.issues || [];

  const remediate = async (action, dryRun = true) => {
    setRemediating(true); setRemedResp("");
    try {
      const r = await api.post(`/admin/x/data-quality/remediate?action=${action}&dry_run=${dryRun}`);
      setRemedResp(r.data.result);
      setTimeout(() => { setRemedResp(""); if (!dryRun) refetchAll(); }, 4000);
    } catch (e) { setRemedResp(e?.response?.data?.detail || "Error"); }
    finally { setRemediating(false); }
  };

  return (
    <AdministrationLayout
      title="Data Governance Center"
      subtitle="Completeness, accuracy, and consistency scoring with automated remediation"
      actions={
        <button onClick={refetchAll} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
          <RefreshCw size={14} className={(sL || iL) ? "animate-spin" : ""} />
        </button>
      }
    >

      {/* Score meters */}
      <div>
        <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Data Quality Scores</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <ScoreMeter label="Overall Quality" score={s.overall_quality_score} description="Weighted composite across all dimensions" />
          <ScoreMeter label="Completeness" score={s.completeness_score} description="Profile fields, ORCID, institution, role" />
          <ScoreMeter label="Accuracy" score={s.accuracy_score} description="Duplicate detection, missing emails" />
          <ScoreMeter label="Consistency" score={s.consistency_score} description="Email verification rate" />
        </div>
      </div>

      {/* Completeness detail */}
      {s.completeness && (
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
          <div className="text-xs text-slate-500 font-medium mb-3">User Profile Completeness Breakdown</div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {Object.entries(s.completeness).map(([key, pct]) => (
              <div key={key}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-slate-400 capitalize">{key.replace("with_", "")}</span>
                  <span className={pct >= 80 ? "text-green-400" : pct >= 50 ? "text-yellow-400" : "text-red-400"}>{pct}%</span>
                </div>
                <div className="h-1 bg-[#1a3050] rounded-full overflow-hidden">
                  <div className={`h-full ${pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-yellow-500" : "bg-red-500"}`}
                    style={{ width: `${pct}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Issues */}
      <div>
        <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
          Detected Issues {issueList.length > 0 && <span className="text-yellow-400">({issueList.length})</span>}
        </div>
        <div className="space-y-2">
          {issueList.map((issue, i) => (
            <div key={i} className={`border-l-2 p-3 flex items-start justify-between gap-4 ${SEVERITY_STYLE[issue.severity] || SEVERITY_STYLE.low}`}>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-[10px] font-medium uppercase">{issue.severity}</span>
                  <span className="text-xs font-semibold">{issue.label}</span>
                  <span className="text-xs">({issue.count.toLocaleString()})</span>
                  {issue.pct && <span className="text-[10px] text-slate-500">{issue.pct}% of users</span>}
                </div>
                <div className="text-[10px] text-slate-400">{issue.action}</div>
              </div>
            </div>
          ))}
          {!iL && issueList.length === 0 && (
            <div className="flex items-center gap-2 text-green-400 text-sm">
              <CheckCircle size={16} />
              No data quality issues detected
            </div>
          )}
        </div>
      </div>

      {/* Remediation */}
      <div className="bg-[#0F2847] border border-[#1a3050] p-4">
        <div className="flex items-center gap-2 mb-3">
          <Wrench size={14} className="text-blue-400" />
          <span className="text-sm font-semibold text-white">Auto-Remediation</span>
        </div>
        <div className="space-y-2">
          {[
            { action: "set_default_name", label: "Set default name for users with no name" },
            { action: "verify_emails_batch", label: "Queue verification emails for unverified accounts" },
          ].map(({ action, label }) => (
            <div key={action} className="flex items-center justify-between gap-4 text-xs">
              <span className="text-slate-300">{label}</span>
              <div className="flex gap-2 flex-shrink-0">
                <button onClick={() => remediate(action, true)} disabled={remediating}
                  className="text-[10px] text-slate-400 border border-[#1a3050] px-2 py-1 hover:text-white disabled:opacity-50">
                  Dry Run
                </button>
                <button onClick={() => { if (window.confirm(`Run "${label}" for real?`)) remediate(action, false); }}
                  disabled={remediating}
                  className="text-[10px] bg-blue-700 hover:bg-blue-600 text-white px-2 py-1 disabled:opacity-50">
                  Apply
                </button>
              </div>
            </div>
          ))}
        </div>
        {remedResp && <div className="mt-3 text-xs text-slate-300 bg-[#0B1C35] border border-[#1a3050] p-2">{remedResp}</div>}
      </div>
    </AdministrationLayout>
  );
}
