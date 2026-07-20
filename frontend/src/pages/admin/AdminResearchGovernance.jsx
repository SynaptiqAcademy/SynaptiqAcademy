import React, { useState, useCallback, useEffect } from "react";
import { FlaskConical, FileText, Users, AlertTriangle, RefreshCw, TrendingUp } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

function useAOS(path, params = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const query = new URLSearchParams(params).toString();
  const fetch = useCallback(() => {
    setLoading(true);
    api.get(`/admin/aos/${path}${query ? "?" + query : ""}`)
      .then((r) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [path, query]);
  useEffect(() => { fetch(); }, [fetch]);
  return { data, loading, refetch: fetch };
}

function ScoreGauge({ score, label }) {
  const color = score >= 70 ? "text-green-400" : score >= 40 ? "text-yellow-400" : "text-red-400";
  const bar   = score >= 70 ? "bg-green-500" : score >= 40 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="bg-[#0F2847] border border-[#1a3050] p-4">
      <div className={`text-3xl font-bold ${color}`}>{score}</div>
      <div className="text-xs text-slate-400 mb-2">{label}</div>
      <div className="h-1.5 bg-[#1a3050] rounded-full overflow-hidden">
        <div className={`h-full ${bar} transition-all`} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

function StalledTable({ title, icon: Icon, items = [], fields }) {
  if (items.length === 0) return null;
  return (
    <div className="bg-[#0F2847] border border-[#1a3050]">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[#1a3050]">
        <Icon size={14} className="text-yellow-400" />
        <span className="text-sm font-semibold text-white">{title}</span>
        <span className="text-xs text-slate-500">({items.length})</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs text-slate-300">
          <thead className="text-slate-500 border-b border-[#1a3050]">
            <tr>
              {fields.map((f) => (
                <th key={f.key} className="text-left px-3 py-2 font-medium">{f.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.slice(0, 10).map((item, i) => (
              <tr key={i} className="border-t border-[#1a3050] hover:bg-[#1a3050]/40">
                {fields.map((f) => (
                  <td key={f.key} className="px-3 py-2 text-slate-300">
                    {f.format ? f.format(item[f.key], item) : (item[f.key] || "—")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function AdminResearchGovernance() {
  const [staleDays, setStaleDays] = useState(30);
  const { data: overview, loading: ovLoading, refetch: refOv } = useAOS("research/overview");
  const { data: stalled, loading: stLoading, refetch: refStalled } = useAOS("research/stalled", { days: staleDays });
  const { data: health, loading: hlLoading, refetch: refHealth } = useAOS("research/health");

  const refetchAll = () => { refOv(); refStalled(); refHealth(); };
  const loading = ovLoading || stLoading || hlLoading;

  const ov = overview || {};
  const h  = health || {};
  const s  = stalled || {};

  return (
    <AdministrationLayout
      title="Research Governance Center"
      subtitle="Platform-wide research health and stalled entity detection"
      actions={
        <div className="flex items-center gap-2">
          <select
            value={staleDays}
            onChange={(e) => setStaleDays(Number(e.target.value))}
            className="text-xs bg-[#0F2847] border border-[#1a3050] text-slate-300 px-2 py-1.5"
          >
            <option value={14}>14 days stale</option>
            <option value={30}>30 days stale</option>
            <option value={60}>60 days stale</option>
            <option value={90}>90 days stale</option>
          </select>
          <button onClick={refetchAll} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      }
    >

      {/* Health Score */}
      {!hlLoading && h.overall_score !== undefined && (
        <div className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Research Health</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <ScoreGauge score={h.overall_score} label="Overall Score" />
            <ScoreGauge score={h.components?.publication}  label="Publications" />
            <ScoreGauge score={h.components?.activity_30d} label="Activity (30d)" />
            <ScoreGauge score={h.components?.manuscripts}  label="Manuscripts" />
            <ScoreGauge score={h.components?.projects}     label="Projects" />
            <ScoreGauge score={h.components?.grants}       label="Grants" />
          </div>
          {h.recommendations?.length > 0 && (
            <div className="bg-yellow-900/20 border border-yellow-700/40 p-3 space-y-1">
              {h.recommendations.map((r, i) => r && (
                <div key={i} className="flex items-start gap-2 text-xs text-yellow-300">
                  <AlertTriangle size={12} className="flex-shrink-0 mt-0.5" />
                  {r}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Overview KPIs */}
      {!ovLoading && (
        <div className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Platform Overview</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { icon: FileText,    label: "Publications",    value: ov.publications?.total, sub: `+${ov.publications?.new_30d ?? 0} this month`, color: "text-blue-400" },
              { icon: FileText,    label: "Manuscripts",     value: ov.manuscripts?.total, sub: `${ov.manuscripts?.active ?? 0} active`,          color: "text-purple-400" },
              { icon: FlaskConical,label: "Projects",        value: ov.projects?.total,    sub: `${ov.projects?.active ?? 0} active`,             color: "text-green-400" },
              { icon: Users,       label: "Collaborations",  value: ov.collaborations?.total, sub: "",                                            color: "text-yellow-400" },
              { icon: TrendingUp,  label: "Grant Links",     value: ov.grants?.links,      sub: "",                                               color: "text-blue-400" },
              { icon: TrendingUp,  label: "Grant Apps",      value: ov.grants?.applications, sub: `${ov.grants?.total ?? 0} total`,               color: "text-purple-400" },
            ].map(({ icon: Icon, label, value, sub, color }) => (
              <div key={label} className="bg-[#0F2847] border border-[#1a3050] p-3 flex gap-3 items-start">
                <Icon size={16} className={`${color} flex-shrink-0 mt-0.5`} />
                <div>
                  <div className="text-xl font-bold text-white">{value?.toLocaleString() ?? "—"}</div>
                  <div className="text-xs text-slate-400">{label}</div>
                  {sub && <div className="text-[10px] text-slate-500">{sub}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stalled Entities */}
      {!stLoading && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
              Stalled Entities (no update in {staleDays} days)
            </h2>
            {s.totals && (
              <span className="text-xs text-yellow-400">
                {(s.totals.stalled_projects || 0) + (s.totals.inactive_manuscripts || 0) + (s.totals.dormant_collabs || 0)} issues detected
              </span>
            )}
          </div>

          <StalledTable
            title="Stalled Projects"
            icon={FlaskConical}
            items={s.stalled_projects || []}
            fields={[
              { key: "title",       label: "Title" },
              { key: "updated_at",  label: "Last Updated", format: (v) => (v || "").slice(0, 10) },
              { key: "owner_id",    label: "Owner ID",     format: (v) => v?.slice(-8) || "—" },
            ]}
          />

          <StalledTable
            title="Inactive Manuscripts"
            icon={FileText}
            items={s.inactive_manuscripts || []}
            fields={[
              { key: "title",      label: "Title" },
              { key: "status",     label: "Status" },
              { key: "updated_at", label: "Last Updated", format: (v) => (v || "").slice(0, 10) },
            ]}
          />

          <StalledTable
            title="Dormant Collaborations"
            icon={Users}
            items={s.dormant_collaborations || []}
            fields={[
              { key: "title",      label: "Title" },
              { key: "updated_at", label: "Last Updated", format: (v) => (v || "").slice(0, 10) },
              { key: "owner_id",   label: "Owner ID",     format: (v) => v?.slice(-8) || "—" },
            ]}
          />

          <StalledTable
            title="Expired Funding Opportunities"
            icon={AlertTriangle}
            items={s.expired_funding || []}
            fields={[
              { key: "title",    label: "Title" },
              { key: "funder",   label: "Funder" },
              { key: "deadline", label: "Deadline", format: (v) => (v || "").slice(0, 10) },
            ]}
          />

          {s.stalled_projects?.length === 0 && s.inactive_manuscripts?.length === 0 &&
           s.dormant_collaborations?.length === 0 && s.expired_funding?.length === 0 && (
            <div className="bg-green-900/20 border border-green-700/40 p-4 text-center text-green-400 text-sm">
              No stalled entities detected. Research platform is healthy.
            </div>
          )}
        </div>
      )}
    </AdministrationLayout>
  );
}
