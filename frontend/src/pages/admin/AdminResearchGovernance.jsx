import React, { useState, useCallback, useEffect } from "react";
import { FlaskConical, FileText, Users, AlertTriangle, RefreshCw, TrendingUp } from "lucide-react";
import api from "@/lib/api";
import { NAVY, EMERALD, AMBER, CRIMSON } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import {
  Card, Button, FormSelect, Alert, StatCard, StatGrid, DataTable,
} from "@/components/ds";

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

function scoreColor(score) {
  return score >= 70 ? EMERALD : score >= 40 ? AMBER : CRIMSON;
}

function ScoreGauge({ score, label }) {
  const color = scoreColor(score);
  return (
    <Card padding="md">
      <div className="text-3xl font-bold" style={{ color }}>{score}</div>
      <div className="text-xs text-slate-500 mb-2">{label}</div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className="h-full transition-all" style={{ width: `${score}%`, background: color }} />
      </div>
    </Card>
  );
}

function StalledTable({ title, icon: Icon, items = [], fields }) {
  if (items.length === 0) return null;
  const columns = fields.map((f) => ({
    key: f.key,
    label: f.label,
    render: (v, row) => (f.format ? f.format(v, row) : (v || "—")),
  }));
  return (
    <Card padding="none">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-200">
        <Icon size={14} className="text-amber-500" />
        <span className="text-sm font-semibold text-slate-800">{title}</span>
        <span className="text-xs text-slate-400">({items.length})</span>
      </div>
      <DataTable columns={columns} rows={items.slice(0, 10)} />
    </Card>
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
          <FormSelect
            value={staleDays}
            onChange={(e) => setStaleDays(Number(e.target.value))}
            wrapperClassName="!mb-0"
            size="sm"
          >
            <option value={14}>14 days stale</option>
            <option value={30}>30 days stale</option>
            <option value={60}>60 days stale</option>
            <option value={90}>90 days stale</option>
          </FormSelect>
          <Button variant="ghost" size="icon" onClick={refetchAll} aria-label="Refresh">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-6">
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
              <Alert variant="warning">
                <div className="space-y-1">
                  {h.recommendations.map((r, i) => r && (
                    <div key={i} className="flex items-start gap-2 text-xs">
                      <AlertTriangle size={12} className="flex-shrink-0 mt-0.5" />
                      {r}
                    </div>
                  ))}
                </div>
              </Alert>
            )}
          </div>
        )}

        {/* Overview KPIs */}
        {!ovLoading && (
          <div className="space-y-3">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Platform Overview</h2>
            <StatGrid cols={6}>
              <StatCard icon={<FileText />} label="Publications" value={ov.publications?.total?.toLocaleString() ?? "—"} sub={`+${ov.publications?.new_30d ?? 0} this month`} />
              <StatCard icon={<FileText />} label="Manuscripts" value={ov.manuscripts?.total?.toLocaleString() ?? "—"} sub={`${ov.manuscripts?.active ?? 0} active`} />
              <StatCard icon={<FlaskConical />} label="Projects" value={ov.projects?.total?.toLocaleString() ?? "—"} sub={`${ov.projects?.active ?? 0} active`} />
              <StatCard icon={<Users />} label="Collaborations" value={ov.collaborations?.total?.toLocaleString() ?? "—"} />
              <StatCard icon={<TrendingUp />} label="Grant Links" value={ov.grants?.links?.toLocaleString() ?? "—"} />
              <StatCard icon={<TrendingUp />} label="Grant Apps" value={ov.grants?.applications?.toLocaleString() ?? "—"} sub={`${ov.grants?.total ?? 0} total`} />
            </StatGrid>
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
                <span className="text-xs text-amber-600">
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
              <Alert variant="success">
                No stalled entities detected. Research platform is healthy.
              </Alert>
            )}
          </div>
        )}
      </div>
    </AdministrationLayout>
  );
}
