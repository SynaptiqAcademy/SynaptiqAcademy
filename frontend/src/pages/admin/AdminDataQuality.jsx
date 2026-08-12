/* eslint-disable */
import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, CheckCircle, Wrench } from "lucide-react";
import api from "@/lib/api";
import { EMERALD, AMBER, CRIMSON, INFO } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Button, Card, Badge, MiniBar, Alert } from "@/components/ds";

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

function scoreColor(score) {
  return score >= 80 ? EMERALD : score >= 55 ? AMBER : CRIMSON;
}

function ScoreMeter({ label, score, description }) {
  const color = scoreColor(score ?? 0);
  return (
    <Card padding="lg">
      <div className="flex items-end gap-2 mb-1">
        <span className="text-3xl font-bold" style={{ color }}>{score ?? 0}</span>
        <span className="text-slate-400 text-xs mb-1">/100</span>
      </div>
      <div className="text-xs text-slate-700 mb-1.5">{label}</div>
      <MiniBar value={score ?? 0} max={100} height={4} className="mb-1.5" />
      {description && <div className="text-[10px] text-slate-400">{description}</div>}
    </Card>
  );
}

const SEVERITY_VARIANT = { high: "danger", medium: "warning", low: "info" };
const SEVERITY_ACCENT = { high: CRIMSON, medium: AMBER, low: INFO };

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
        <Button variant="ghost" size="icon" onClick={refetchAll} aria-label="Refresh">
          <RefreshCw size={14} className={(sL || iL) ? "animate-spin" : ""} />
        </Button>
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
        <Card padding="lg">
          <div className="text-xs text-slate-500 font-medium mb-3">User Profile Completeness Breakdown</div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {Object.entries(s.completeness).map(([key, pct]) => (
              <div key={key}>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-slate-500 capitalize">{key.replace("with_", "")}</span>
                  <span style={{ color: scoreColor(pct) }}>{pct}%</span>
                </div>
                <MiniBar value={pct} max={100} height={4} />
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Issues */}
      <div>
        <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
          Detected Issues {issueList.length > 0 && <span style={{ color: AMBER }}>({issueList.length})</span>}
        </div>
        <div className="space-y-2">
          {issueList.map((issue, i) => (
            <Card key={i} padding="sm" accent={SEVERITY_ACCENT[issue.severity] || SEVERITY_ACCENT.low}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <Badge variant={SEVERITY_VARIANT[issue.severity] || "info"} size="sm">{issue.severity}</Badge>
                    <span className="text-xs font-semibold text-slate-800">{issue.label}</span>
                    <span className="text-xs text-slate-600">({issue.count.toLocaleString()})</span>
                    {issue.pct && <span className="text-[10px] text-slate-400">{issue.pct}% of users</span>}
                  </div>
                  <div className="text-[10px] text-slate-500">{issue.action}</div>
                </div>
              </div>
            </Card>
          ))}
          {!iL && issueList.length === 0 && (
            <div className="flex items-center gap-2 text-sm" style={{ color: EMERALD }}>
              <CheckCircle size={16} />
              No data quality issues detected
            </div>
          )}
        </div>
      </div>

      {/* Remediation */}
      <Card padding="lg">
        <div className="flex items-center gap-2 mb-3">
          <Wrench size={14} style={{ color: INFO }} />
          <span className="text-sm font-semibold text-slate-800">Auto-Remediation</span>
        </div>
        <div className="space-y-2">
          {[
            { action: "set_default_name", label: "Set default name for users with no name" },
            { action: "verify_emails_batch", label: "Queue verification emails for unverified accounts" },
          ].map(({ action, label }) => (
            <div key={action} className="flex items-center justify-between gap-4 text-xs">
              <span className="text-slate-600">{label}</span>
              <div className="flex gap-2 flex-shrink-0">
                <Button variant="ghost" size="sm" onClick={() => remediate(action, true)} disabled={remediating}>
                  Dry Run
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => { if (window.confirm(`Run "${label}" for real?`)) remediate(action, false); }}
                  disabled={remediating}
                >
                  Apply
                </Button>
              </div>
            </div>
          ))}
        </div>
        {remedResp && <Alert variant="info" className="mt-3">{remedResp}</Alert>}
      </Card>
    </AdministrationLayout>
  );
}
