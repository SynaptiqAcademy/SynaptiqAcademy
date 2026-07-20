import React, { useState, useCallback, useEffect } from "react";
import { RefreshCw, ShieldCheck, AlertTriangle, Search } from "lucide-react";
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

function ScoreDial({ score, label, sub }) {
  const color = score >= 70 ? "text-green-400" : score >= 45 ? "text-yellow-400" : "text-red-400";
  const bar   = score >= 70 ? "bg-green-500" : score >= 45 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="bg-[#0F2847] border border-[#1a3050] p-4">
      <div className={`text-3xl font-bold ${color}`}>{score ?? 0}</div>
      <div className="text-xs text-white font-medium mt-0.5">{label}</div>
      {sub && <div className="text-[10px] text-slate-500 mb-2">{sub}</div>}
      <div className="h-1 bg-[#1a3050] rounded-full overflow-hidden">
        <div className={`h-full ${bar}`} style={{ width: `${score ?? 0}%` }} />
      </div>
    </div>
  );
}

const SEVERITY_STYLE = {
  high:   "border-l-red-500 bg-red-900/20 text-red-300",
  medium: "border-l-yellow-500 bg-yellow-900/20 text-yellow-300",
  low:    "border-l-blue-500 bg-blue-900/20 text-blue-300",
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

  return (
    <AdministrationLayout
      title="Research Integrity Center"
      subtitle="Duplicate detection, anomaly analysis, ORCID coverage, manuscript health"
      actions={
        <button onClick={refetchAll} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      }
    >

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
        <div className="bg-[#0F2847] border border-[#1a3050] p-4">
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
                <div className="text-lg font-bold text-white">{(val || 0).toLocaleString()}</div>
                <div className="text-[10px] text-slate-500">{label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Anomalies */}
      {anomalies.length > 0 && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
            Anomalies Detected ({anomalies.length})
          </div>
          <div className="space-y-2">
            {anomalies.map((a, i) => (
              <div key={i} className={`border-l-2 p-3 text-xs ${SEVERITY_STYLE[a.severity] || SEVERITY_STYLE.low}`}>
                <div className="font-medium uppercase text-[10px] mb-0.5">{a.type?.replace(/_/g, " ")}</div>
                {a.message}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-500">Recommendations</div>
          {recommendations.map((r, i) => (
            <div key={i} className={`border-l-2 p-3 text-xs ${SEVERITY_STYLE[r.priority] || SEVERITY_STYLE.low}`}>
              <span className="font-medium uppercase text-[10px] mr-2">{r.area}</span>
              {r.description}
            </div>
          ))}
        </div>
      )}

      {/* Duplicates */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-[#0F2847] border border-[#1a3050]">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-[#1a3050]">
            <Search size={14} className="text-yellow-400" />
            <span className="text-sm font-semibold text-white">Duplicate Manuscript Titles</span>
            {dups && <span className="text-xs text-yellow-400">({dups.total_ms_duplicates ?? 0})</span>}
          </div>
          <div className="overflow-y-auto max-h-60">
            <table className="w-full text-xs text-slate-300">
              <thead className="text-slate-500 border-b border-[#1a3050]">
                <tr>
                  <th className="text-left px-3 py-2 font-medium">Normalized Title</th>
                  <th className="text-right px-3 py-2 font-medium">Count</th>
                </tr>
              </thead>
              <tbody>
                {dupMs.slice(0, 10).map((d, i) => (
                  <tr key={i} className="border-t border-[#1a3050] hover:bg-[#1a3050]/30">
                    <td className="px-3 py-2 text-yellow-300 max-w-[240px] truncate">{d.norm_title}</td>
                    <td className="px-3 py-2 text-right text-red-400">{d.count}</td>
                  </tr>
                ))}
                {!dL && dupMs.length === 0 && (
                  <tr><td colSpan={2} className="px-3 py-4 text-center text-green-400">No duplicate titles detected</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-[#0F2847] border border-[#1a3050]">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-[#1a3050]">
            <AlertTriangle size={14} className="text-red-400" />
            <span className="text-sm font-semibold text-white">Duplicate DOIs</span>
            {dups && <span className="text-xs text-red-400">({dups.total_doi_duplicates ?? 0})</span>}
          </div>
          <div className="overflow-y-auto max-h-60">
            <table className="w-full text-xs text-slate-300">
              <thead className="text-slate-500 border-b border-[#1a3050]">
                <tr>
                  <th className="text-left px-3 py-2 font-medium">DOI</th>
                  <th className="text-right px-3 py-2 font-medium">Duplicates</th>
                </tr>
              </thead>
              <tbody>
                {dupDois.slice(0, 10).map((d, i) => (
                  <tr key={i} className="border-t border-[#1a3050] hover:bg-[#1a3050]/30">
                    <td className="px-3 py-2 font-mono text-red-300 max-w-[240px] truncate">{d.doi}</td>
                    <td className="px-3 py-2 text-right text-red-400">{d.count}</td>
                  </tr>
                ))}
                {!dL && dupDois.length === 0 && (
                  <tr><td colSpan={2} className="px-3 py-4 text-center text-green-400">No duplicate DOIs detected</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {anomalies.length === 0 && dupMs.length === 0 && dupDois.length === 0 && !loading && (
        <div className="flex items-center gap-2 text-green-400 text-sm">
          <ShieldCheck size={16} />
          Research integrity is healthy — no anomalies or duplicates detected
        </div>
      )}
    </AdministrationLayout>
  );
}
