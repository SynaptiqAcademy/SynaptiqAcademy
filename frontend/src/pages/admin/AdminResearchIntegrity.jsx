import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, ShieldCheck, AlertTriangle, Search } from "lucide-react";
import api from "@/lib/api";
import { NAVY, EMERALD, AMBER, CRIMSON } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Card, Button, Alert, DataTable } from "@/components/ds";

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
  return score >= 70 ? EMERALD : score >= 45 ? AMBER : CRIMSON;
}

function ScoreDial({ score, label, sub }) {
  const color = scoreColor(score ?? 0);
  return (
    <Card padding="md">
      <div className="text-3xl font-bold" style={{ color }}>{score ?? 0}</div>
      <div className="text-xs text-slate-800 font-medium mt-0.5">{label}</div>
      {sub && <div className="text-[10px] text-slate-500 mb-2">{sub}</div>}
      <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
        <div className="h-full" style={{ width: `${score ?? 0}%`, background: color }} />
      </div>
    </Card>
  );
}

const SEVERITY_ACCENT = {
  high:   CRIMSON,
  medium: AMBER,
  low:    "#3B82F6",
};

const SEVERITY_TEXT = {
  high:   "text-red-700",
  medium: "text-amber-700",
  low:    "text-blue-700",
};

export default function AdminResearchIntegrity() {
  const { data: scores,  loading: sL, refetch: refScores  } = useX("research-integrity/scores");
  const { data: dups,    loading: dL, refetch: refDups    } = useX("research-integrity/duplicates");
  const { data: anomaly, loading: aL, refetch: refAnomaly } = useX("research-integrity/anomalies");
  const { data: recs,    loading: rL, refetch: refRecs    } = useX("research-integrity/recommendations");
  const refetchAll = () => { refScores(); refDups(); refAnomaly(); refRecs(); };
  const loading = sL || dL || aL || rL;

  const s = scores || {};
  const anomalies = anomaly?.anomalies || [];
  const dupMs = dups?.duplicate_manuscripts || [];
  const dupDois = dups?.duplicate_dois || [];
  const recommendations = recs?.recommendations || [];

  const dupMsColumns = [
    { key: "norm_title", label: "Normalized Title", maxWidth: 240, render: (v) => <span className="text-amber-700 truncate block">{v}</span> },
    { key: "count", label: "Count", align: "right", render: (v) => <span className="text-red-600">{v}</span> },
  ];

  const dupDoisColumns = [
    { key: "doi", label: "DOI", maxWidth: 240, render: (v) => <span className="font-mono text-red-700 truncate block">{v}</span> },
    { key: "count", label: "Duplicates", align: "right", render: (v) => <span className="text-red-600">{v}</span> },
  ];

  return (
    <AdministrationLayout
      title="Research Integrity Center"
      subtitle="Duplicate detection, anomaly analysis, ORCID coverage, manuscript health"
      actions={
        <Button variant="hero" size="icon" onClick={refetchAll} aria-label="Refresh">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </Button>
      }
    >
      <div className="flex flex-col gap-6">
        {/* Score dials */}
        <div>
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">Integrity Scores</div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <ScoreDial score={s.overall_integrity_score} label="Overall" sub="Composite across all dimensions" />
            <ScoreDial score={s.manuscript_integrity_score} label="Manuscripts" sub="Published, active, not withdrawn" />
            <ScoreDial score={s.publication_integrity_score} label="Publications" sub="With citations / total" />
            <ScoreDial score={s.orcid_integrity_score} label="ORCID Coverage" sub="Users with verified ORCID" />
            <ScoreDial score={s.collaboration_integrity_score} label="Collaborations" sub="Active / total" />
          </div>
        </div>

        {/* Raw stats */}
        {s.raw && (
          <Card padding="md">
            <div className="text-xs text-slate-500 font-medium mb-3">Platform Research Stats</div>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 text-xs">
              {[
                ["Total Manuscripts", s.raw.total_manuscripts],
                ["Published", s.raw.published],
                ["In Review", s.raw.in_review],
                ["Withdrawn", s.raw.withdrawn],
                ["Total Publications", s.raw.total_publications],
                ["Cited Pubs", s.raw.cited_publications],
                ["ORCID Users", s.raw.orcid_users],
                ["Total Users", s.raw.total_users],
              ].map(([label, val]) => (
                <div key={label}>
                  <div className="text-lg font-bold text-slate-900">{(val || 0).toLocaleString()}</div>
                  <div className="text-[10px] text-slate-500">{label}</div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Anomalies */}
        {anomalies.length > 0 && (
          <div>
            <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
              Anomalies Detected ({anomalies.length})
            </div>
            <div className="space-y-2">
              {anomalies.map((a, i) => (
                <Card key={i} accent={SEVERITY_ACCENT[a.severity] || SEVERITY_ACCENT.low} padding="sm" className={`text-xs ${SEVERITY_TEXT[a.severity] || SEVERITY_TEXT.low}`}>
                  <div className="font-medium uppercase text-[10px] mb-0.5">{a.type?.replace(/_/g, " ")}</div>
                  {a.message}
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-semibold uppercase tracking-widest text-slate-500">Recommendations</div>
            {recommendations.map((r, i) => (
              <Card key={i} accent={SEVERITY_ACCENT[r.priority] || SEVERITY_ACCENT.low} padding="sm" className={`text-xs ${SEVERITY_TEXT[r.priority] || SEVERITY_TEXT.low}`}>
                <span className="font-medium uppercase text-[10px] mr-2">{r.area}</span>
                {r.description}
              </Card>
            ))}
          </div>
        )}

        {/* Duplicates */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card padding="none">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-200">
              <Search size={14} className="text-amber-500" />
              <span className="text-sm font-semibold text-slate-800">Duplicate Manuscript Titles</span>
              {dups && <span className="text-xs text-amber-600">({dups.total_ms_duplicates ?? 0})</span>}
            </div>
            <div className="max-h-60 overflow-y-auto">
              <DataTable
                columns={dupMsColumns}
                rows={dupMs.slice(0, 10)}
                loading={dL}
                emptyNode={<div className="px-3 py-4 text-center text-emerald-600 text-xs">No duplicate titles detected</div>}
              />
            </div>
          </Card>

          <Card padding="none">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-200">
              <AlertTriangle size={14} className="text-red-500" />
              <span className="text-sm font-semibold text-slate-800">Duplicate DOIs</span>
              {dups && <span className="text-xs text-red-600">({dups.total_doi_duplicates ?? 0})</span>}
            </div>
            <div className="max-h-60 overflow-y-auto">
              <DataTable
                columns={dupDoisColumns}
                rows={dupDois.slice(0, 10)}
                loading={dL}
                emptyNode={<div className="px-3 py-4 text-center text-emerald-600 text-xs">No duplicate DOIs detected</div>}
              />
            </div>
          </Card>
        </div>

        {anomalies.length === 0 && dupMs.length === 0 && dupDois.length === 0 && !loading && (
          <Alert variant="success" icon={ShieldCheck}>
            Research integrity is healthy — no anomalies or duplicates detected
          </Alert>
        )}
      </div>
    </AdministrationLayout>
  );
}
