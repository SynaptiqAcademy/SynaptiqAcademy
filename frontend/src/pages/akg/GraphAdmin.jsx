/* eslint-disable */
import React, { useEffect, useState } from "react";
import { Shield, RefreshCw, Layers, Trash2, Activity } from "lucide-react";
import { NAVY, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Card, Button, Input, Alert, List, ListItem, DataTable, EmptyState } from "@/components/ds";
import { fetchApi } from "@/lib/api";
import { confirmDialog } from "@/lib/confirm";

const API = (p) => `/api/admin/akg${p}`;

export default function GraphAdmin() {
  const [stats, setStats]   = useState(null);
  const [audit, setAudit]   = useState([]);
  const [syncing, setSyncing] = useState(false);
  const [deleteId, setDeleteId] = useState("");
  const [deleteMsg, setDeleteMsg] = useState("");

  useEffect(() => {
    Promise.all([
      fetchApi(API("/stats")).then(r => r.json()),
      fetchApi(API("/audit?limit=30")).then(r => r.json()),
    ]).then(([s, a]) => {
      setStats(s.error ? null : s);
      setAudit(Array.isArray(a) ? a : []);
    }).catch(() => {});
  }, []);

  const runSync = async () => {
    setSyncing(true);
    await fetchApi(API("/sync/full"), { method: "POST" });
    setTimeout(() => setSyncing(false), 2000);
  };

  const deleteEntity = async () => {
    if (!deleteId.trim()) return;
    if (!(await confirmDialog({
      title: `Permanently delete entity "${deleteId.trim()}"?`,
      description: "This removes the entity and all its relationships from the graph. This cannot be undone.",
      danger: true,
    }))) return;
    const res = await fetchApi(API(`/entity/${deleteId}`), { method: "DELETE" }).then(r => r.json()).catch(() => ({}));
    setDeleteMsg(res.deleted ? "Entity deleted." : (res.error || "Failed to delete."));
    setDeleteId("");
  };

  const auditColumns = [
    { key: "at", label: "Time", render: (v) => v ? new Date(v).toLocaleString() : "—" },
    { key: "user_id", label: "User ID", render: (v) => <span style={{ fontFamily: "monospace", color: NAVY }}>{v?.substring(0, 16)}…</span> },
    { key: "action", label: "Action", render: (v) => <span style={{ color: ACCENT, fontWeight: 500 }}>{v}</span> },
    { key: "target", label: "Target" },
  ];

  return (
    <AdministrationLayout
      title="Graph Administration"
      subtitle="Admin-only controls for the Academic Knowledge Graph."
      icon={<Shield size={22} color="#dc2626" />}
      stats={stats ? [
        { label: "Total Entities", value: stats.total_entities?.toLocaleString() ?? 0 },
        { label: "Relationships",  value: stats.total_relationships?.toLocaleString() ?? 0 },
        { label: "Avg Degree",     value: stats.avg_degree ?? "—" },
        { label: "Collab Density", value: stats.collaboration_density?.density_label ?? "—" },
      ] : undefined}
      sidebar={(stats?.entities_by_type || audit.length > 0) ? <GraphAdminSidebar stats={stats} audit={audit} /> : undefined}
      actions={
        <Button variant="danger" onClick={runSync} disabled={syncing} loading={syncing}>
          {!syncing && <RefreshCw size={16} />}
          {syncing ? "Syncing…" : "Force Full Sync"}
        </Button>
      }
    >

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>
        {stats?.entities_by_type && (
          <Card padding="lg">
            <h2 style={{ fontSize: 15, fontWeight: 700, color: NAVY, marginBottom: 16 }}>Entities by Type</h2>
            <List>
              {Object.entries(stats.entities_by_type).slice(0, 12).map(([type, count]) => (
                <ListItem
                  key={type}
                  compact
                  title={type.replace(/_/g, " ")}
                  trailing={<span style={{ fontSize: 12, color: TEXT_SECONDARY, fontWeight: 600 }}>{count}</span>}
                />
              ))}
            </List>
          </Card>
        )}

        <Card padding="lg">
          <h2 style={{ fontSize: 15, fontWeight: 700, color: NAVY, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
            <Trash2 size={16} color="#dc2626" /> Delete Entity
          </h2>
          <p style={{ fontSize: 12, color: TEXT_SECONDARY, marginBottom: 14 }}>Permanently remove an entity and all its relationships from the graph.</p>
          <Input
            value={deleteId}
            onChange={e => setDeleteId(e.target.value)}
            placeholder="Entity ID to delete"
            wrapperClassName="mb-2.5"
          />
          <Button variant="danger" size="sm" onClick={deleteEntity}>
            Delete Entity
          </Button>
          {deleteMsg && (
            <div className="mt-2.5">
              <Alert variant={deleteMsg.includes("deleted") ? "success" : "error"}>{deleteMsg}</Alert>
            </div>
          )}
        </Card>
      </div>

      <Card padding="lg">
        <h2 style={{ fontSize: 15, fontWeight: 700, color: NAVY, marginBottom: 16 }}>Audit Log (last 30)</h2>
        <DataTable
          columns={auditColumns}
          rows={audit}
          emptyNode={<EmptyState title="No audit entries yet." dashed={false} />}
        />
      </Card>
    </AdministrationLayout>
  );
}

// ── Right rail — real data already loaded by this page, never fabricated ──────
function GraphAdminSidebar({ stats, audit }) {
  const topType = stats?.entities_by_type
    ? Object.entries(stats.entities_by_type).sort((a, b) => b[1] - a[1])[0]
    : null;
  const recentAudit = (audit || []).slice(0, 4);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Layers size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Most Common Entity Type</div>
        </div>
        {topType ? (
          <>
            <div style={{ fontFamily: "Georgia, serif", fontSize: 26, color: NAVY }}>{topType[1].toLocaleString()}</div>
            <div style={{ fontSize: 12, color: "#64748B" }}>{topType[0].replace(/_/g, " ")} entities</div>
          </>
        ) : (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>No entity data yet.</p>
        )}
      </Card>

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Activity size={13} style={{ color: ACCENT }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Recent Admin Activity</div>
        </div>
        {recentAudit.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {recentAudit.map((a, i) => (
              <div key={i} style={{ fontSize: 12, color: "#374151" }}>
                <span style={{ fontWeight: 600, color: NAVY }}>{a.action}</span>
                {a.target && <span style={{ color: "#64748B" }}> · {a.target}</span>}
              </div>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>No audit entries yet.</p>
        )}
      </Card>
    </div>
  );
}
