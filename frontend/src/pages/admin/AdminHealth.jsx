import React, { useState, useCallback, useEffect } from "react";
import { CheckCircle, XCircle, Server, Link, AlertTriangle, RefreshCw } from "lucide-react";
import api from "@/lib/api";
import { EMERALD, AMBER, CRIMSON, INFO, VIOLET } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Button, Card, StatCard, StatGrid, StatusDot, MiniBar, DataTable, Badge } from "@/components/ds";

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

function IntegrationRow({ name, config }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
      <div className="flex items-center gap-2">
        <StatusDot color={config.configured ? EMERALD : CRIMSON} size={8} />
        <span className="text-sm text-slate-700 capitalize">{name.replace(/_/g, " ")}</span>
      </div>
      <span className="text-xs px-2 py-0.5" style={{ color: config.configured ? EMERALD : CRIMSON }}>
        {config.status}
      </span>
    </div>
  );
}

function scoreColorFor(val) {
  return val >= 70 ? EMERALD : val >= 40 ? AMBER : CRIMSON;
}

export default function AdminHealth() {
  const { data: infra,  loading: iLoad,  refetch: refInfra }    = useAOS("health/infrastructure");
  const { data: integ,  loading: igLoad, refetch: refInteg }    = useAOS("health/integrations");
  const { data: incidents, loading: incLoad, refetch: refInc }  = useAOS("health/incidents");
  const { data: prReady, loading: prLoad }                      = useAOS("platform-audit/scores");

  const loading = iLoad || igLoad || incLoad || prLoad;
  const refetchAll = () => { refInfra(); refInteg(); refInc(); };

  const inf = infra || {};
  const ig  = integ || {};
  const score = prReady?.overall_score;

  const incidentColumns = [
    {
      key: "severity", label: "Severity",
      render: (v) => (
        <Badge
          size="sm"
          variant={v === "critical" ? "danger" : v === "high" ? "warning" : "neutral"}
        >
          {v}
        </Badge>
      ),
    },
    { key: "category", label: "Category" },
    { key: "message", label: "Message", maxWidth: 320 },
    { key: "frequency", label: "Frequency" },
    { key: "created_at", label: "Date", render: (v) => (v || "").slice(0, 10) },
    {
      key: "resolved", label: "Resolved",
      render: (v) => v
        ? <CheckCircle size={12} style={{ color: EMERALD }} />
        : <XCircle size={12} style={{ color: CRIMSON }} />,
    },
  ];

  return (
    <AdministrationLayout
      title="Platform Health Center"
      subtitle="Infrastructure, integrations, and incident monitoring"
      actions={
        <Button variant="hero" size="icon" onClick={refetchAll} aria-label="Refresh">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </Button>
      }
    >

      {/* Summary row */}
      <StatGrid cols={4}>
        <StatCard
          label="Database"
          value={inf.database?.ok ? "Healthy" : "Error"}
          icon={inf.database?.ok ? <CheckCircle style={{ color: EMERALD }} /> : <XCircle style={{ color: CRIMSON }} />}
        />
        <StatCard label="App Uptime" value={`${Math.round(inf.app_uptime_hours || 0)}h`} />
        <StatCard
          label="Platform Score"
          value={score ?? "—"}
          sub={prReady?.audited_at ? prReady.audited_at.slice(0, 10) : undefined}
        />
        <StatCard label="Errors (24h)" value={inf.errors_24h ?? 0} />
      </StatGrid>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Infrastructure */}
        {!iLoad && (
          <Card padding="lg">
            <div className="flex items-center gap-2 mb-3">
              <Server size={14} style={{ color: INFO }} />
              <div className="text-sm font-semibold text-slate-800">Infrastructure</div>
            </div>
            <div className="space-y-2 text-xs">
              {[
                ["Python Version",    inf.python_version],
                ["Platform",         inf.platform],
                ["DB Collections",   inf.database?.collections],
                ["DB Connections",   inf.database?.stats?.connections_current],
                ["DB Uptime",        inf.database?.stats?.uptime_seconds ? `${Math.round(inf.database.stats.uptime_seconds / 3600)}h` : "—"],
                ["App Uptime",       `${inf.app_uptime_hours}h`],
                ["Errors 24h",       inf.errors_24h],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between border-b border-slate-100 pb-1.5">
                  <span className="text-slate-500">{label}</span>
                  <span className="text-slate-800">{value ?? "—"}</span>
                </div>
              ))}
              {inf.database?.stats?.ops_per_second && (
                <div>
                  <div className="text-slate-400 mt-2 mb-1">Database Ops/s</div>
                  {Object.entries(inf.database.stats.ops_per_second).map(([op, count]) => (
                    <div key={op} className="flex justify-between text-[10px] py-0.5">
                      <span className="text-slate-400">{op}</span>
                      <span className="text-slate-600">{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Card>
        )}

        {/* Integrations */}
        {!igLoad && (
          <Card padding="lg">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Link size={14} style={{ color: VIOLET }} />
                <div className="text-sm font-semibold text-slate-800">Integrations</div>
              </div>
              <div className="text-xs text-slate-400">
                {ig.configured}/{ig.total} configured · Score: {ig.health_score}
              </div>
            </div>
            <div>
              {Object.entries(ig.integrations || {}).map(([name, config]) => (
                <IntegrationRow key={name} name={name} config={config} />
              ))}
            </div>
            <div className="mt-3 flex items-center gap-2">
              <StatusDot color={ig.db_reachable ? EMERALD : CRIMSON} size={8} />
              <span className="text-xs text-slate-500">Database reachable: {ig.db_reachable ? "Yes" : "No"}</span>
            </div>
          </Card>
        )}
      </div>

      {/* Audit scores detail */}
      {prReady?.scores && (
        <Card padding="lg">
          <div className="text-sm font-semibold text-slate-800 mb-3">Platform Audit Scores</div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.entries(prReady.scores).map(([key, val]) => (
              <div key={key}>
                <div className="text-xl font-bold" style={{ color: scoreColorFor(val) }}>{val}</div>
                <div className="text-[10px] text-slate-400 mb-1">{key.replace(/_/g, " ")}</div>
                <MiniBar value={val} max={100} height={6} />
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Incidents */}
      {!incLoad && (
        <Card padding="none">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-100">
            <AlertTriangle size={14} style={{ color: AMBER }} />
            <div className="text-sm font-semibold text-slate-800">Recent Incidents</div>
            <span className="text-xs text-slate-400">({(incidents?.items || []).length})</span>
          </div>
          {(incidents?.items || []).length === 0 ? (
            <div className="p-6 text-center text-slate-500 text-sm flex items-center justify-center gap-2">
              <CheckCircle size={14} style={{ color: EMERALD }} />
              No incidents recorded
            </div>
          ) : (
            <DataTable columns={incidentColumns} rows={(incidents.items || []).slice(0, 20)} />
          )}
        </Card>
      )}
    </AdministrationLayout>
  );
}
