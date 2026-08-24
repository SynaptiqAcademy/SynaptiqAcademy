/* eslint-disable */
import React, { useState, useCallback, useEffect } from "react";
import { Database, HardDrive, AlertTriangle, CheckCircle, RefreshCw, Activity, Trash2 } from "lucide-react";
import api from "@/lib/api";
import { EMERALD, AMBER, CRIMSON, INFO, VIOLET } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Button, Card, StatCard, StatGrid, DataTable, Alert } from "@/components/ds";

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

function scoreColor(s) {
  return s >= 80 ? EMERALD : s >= 50 ? AMBER : CRIMSON;
}

function DangerZone() {
  const [accounts, setAccounts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [confirmText, setConfirmText] = useState("");
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const loadPreview = useCallback(() => {
    setLoading(true);
    setResult(null);
    setError("");
    api.get("/admin/platform-reset/preview")
      .then((r) => setAccounts(r.data))
      .catch(() => setError("Could not load account preview."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadPreview(); }, [loadPreview]);

  const canExecute = confirmText === "RESET" && !executing && (accounts?.count || 0) > 0;

  const execute = () => {
    if (!canExecute) return;
    setExecuting(true);
    setError("");
    api.post("/admin/platform-reset/execute", { confirm: "RESET" })
      .then((r) => { setResult(r.data); setConfirmText(""); loadPreview(); })
      .catch((e) => setError(e?.response?.data?.detail || "Reset failed."))
      .finally(() => setExecuting(false));
  };

  const accountColumns = [
    { key: "email", label: "Email" },
    { key: "full_name", label: "Name" },
    { key: "role", label: "Role" },
    { key: "plan_code", label: "Plan" },
    { key: "created_at", label: "Created", render: (v) => (v || "").slice(0, 10) },
  ];

  return (
    <Card padding="lg" accent={CRIMSON} className="bg-red-50/40 border-red-200">
      <div className="flex items-center gap-2 mb-1">
        <Trash2 size={16} style={{ color: CRIMSON }} />
        <div className="text-sm font-semibold text-slate-800">Danger Zone — Reset to Zero</div>
      </div>
      <p className="text-xs text-slate-600 mb-3">
        Permanently deletes every account except the protected super-admin, and every piece of
        data those accounts own (projects, workspaces, manuscripts, messages, credits, sessions,
        and everything else). Intended for the pre-launch testing period, before billing is live.
        This cannot be undone.
      </p>

      {result && (
        <div className="mb-3"><Alert variant="success">Deleted {result.deleted_users} account(s). The platform is now clean.</Alert></div>
      )}
      {error && (
        <div className="mb-3"><Alert variant="error">{error}</Alert></div>
      )}

      {!loading && (accounts?.count || 0) === 0 && !result && (
        <div className="flex items-center gap-2 text-sm" style={{ color: EMERALD }}>
          <CheckCircle size={14} />
          No accounts to delete — only the protected super-admin exists.
        </div>
      )}

      {!loading && (accounts?.count || 0) > 0 && (
        <>
          <div className="text-xs font-medium text-slate-700 mb-2">
            {accounts.count} account(s) will be permanently deleted:
          </div>
          <div className="overflow-y-auto max-h-64 mb-3">
            <DataTable columns={accountColumns} rows={accounts.accounts} stickyHeader />
          </div>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder='Type "RESET" to confirm'
              className="border border-red-300 rounded-md px-3 py-1.5 text-sm flex-1 max-w-xs"
            />
            <Button variant="danger" onClick={execute} disabled={!canExecute}>
              {executing ? "Deleting…" : "Delete all non-admin accounts"}
            </Button>
            <Button variant="outline" size="sm" onClick={loadPreview}>Refresh list</Button>
          </div>
        </>
      )}
    </Card>
  );
}

export default function AdminDatabaseOps() {
  const { data: overview, loading: ovLoad, refetch: refOv } = useAOS("db/overview");
  const { data: integrity, loading: intLoad, refetch: refInt } = useAOS("db/integrity");
  const { data: health, loading: hlLoad, refetch: refHl } = useAOS("db/health");

  const loading = ovLoad || intLoad || hlLoad;
  const refetchAll = () => { refOv(); refInt(); refHl(); };

  const ov  = overview   || {};
  const int = integrity  || {};
  const h   = health     || {};

  const collectionColumns = [
    { key: "collection", label: "Collection", render: (v) => <span className="font-mono">{v}</span> },
    {
      key: "count", label: "Documents", align: "right",
      render: (v) => v < 0 ? "error" : v.toLocaleString(),
    },
  ];

  return (
    <AdministrationLayout
      title="Database Operations Center"
      subtitle="MongoDB cluster health, collection stats, and integrity"
      actions={
        <Button variant="hero" size="icon" onClick={refetchAll} aria-label="Refresh">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </Button>
      }
    >

      {/* DB Health */}
      {!hlLoad && (
        <StatGrid cols={4}>
          <StatCard
            label="Database Status"
            value={h.ok ? "Connected" : "Disconnected"}
            icon={h.ok ? <CheckCircle style={{ color: EMERALD }} /> : <AlertTriangle style={{ color: CRIMSON }} />}
          />
          <StatCard label="Health Score" value={h.health_score ?? "—"} />
          <StatCard label="Ping Latency" value={`${h.latency_ms ?? "—"} ms`} />
          <StatCard
            label="Active Connections"
            value={h.server_info?.connections ?? "—"}
            sub={h.server_info?.version ? `MongoDB ${h.server_info.version}` : undefined}
          />
        </StatGrid>
      )}

      {/* Storage */}
      {!ovLoad && !ov.error && (
        <StatGrid cols={4}>
          <StatCard label="Storage" value={`${ov.storage_size_mb} MB`} icon={<HardDrive style={{ color: INFO }} />} />
          <StatCard label="Data Size" value={`${ov.data_size_mb} MB`} icon={<Database style={{ color: VIOLET }} />} />
          <StatCard label="Collections" value={ov.total_collections} icon={<Activity style={{ color: EMERALD }} />} />
          <StatCard
            label="Indexes"
            value={ov.total_indexes}
            sub={`${ov.index_size_mb} MB index size`}
            icon={<Activity style={{ color: AMBER }} />}
          />
        </StatGrid>
      )}

      {/* Integrity */}
      {!intLoad && (
        <Card padding="lg">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-semibold text-slate-800">Data Integrity</div>
            <div className="flex items-center gap-2">
              <div className="text-2xl font-bold" style={{ color: scoreColor(int.integrity_score || 0) }}>
                {int.integrity_score ?? "—"}
              </div>
              <div className="text-xs text-slate-400">/ 100</div>
            </div>
          </div>
          <div className="text-[10px] text-slate-400 mb-3">Scanned at {(int.scanned_at || "").slice(0, 19)}</div>
          {(int.issues || []).length === 0 ? (
            <div className="flex items-center gap-2 text-sm" style={{ color: EMERALD }}>
              <CheckCircle size={14} />
              No integrity issues detected
            </div>
          ) : (
            <div className="space-y-2">
              {(int.issues || []).map((issue, i) => (
                <Card key={i} padding="sm" accent={AMBER} className="bg-amber-50">
                  <div className="flex items-start gap-3">
                    <AlertTriangle size={12} style={{ color: AMBER }} className="flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="text-xs text-slate-800">{issue.type?.replace(/_/g, " ")}: {issue.count} records</div>
                      <div className="text-[10px] text-slate-500">{issue.action}</div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Collection list */}
      {!ovLoad && (ov.collections || []).length > 0 && (
        <div>
          <div className="text-sm font-semibold text-slate-800 mb-2">Collections ({ov.total_collections})</div>
          <div className="overflow-y-auto max-h-96">
            <DataTable columns={collectionColumns} rows={ov.collections || []} stickyHeader />
          </div>
        </div>
      )}

      <DangerZone />
    </AdministrationLayout>
  );
}
