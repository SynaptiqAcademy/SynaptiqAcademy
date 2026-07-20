/* eslint-disable */
import React, { useEffect, useState } from "react";
import { RefreshCw, CheckCircle, AlertCircle, Clock, Database } from "lucide-react";
import { NAVY, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { Card, Button, EmptyState, LoadingOverlay } from "@/components/ds";

const API = (p) => `/api/akg${p}`;

const SOURCES = ["users", "institutions", "projects", "grants", "marketplace_services", "communities"];

const StatusRow = ({ log }) => {
  const isError = log.synced?.toString().startsWith("error");
  return (
    <Card padding="sm" style={{ display: "flex", alignItems: "center", gap: 14 }}>
      {isError
        ? <AlertCircle size={16} color="#dc2626" />
        : <CheckCircle size={16} color="#059669" />}
      <div style={{ minWidth: 130, fontSize: 13, fontWeight: 500, color: NAVY }}>{log.source}</div>
      <div style={{ flex: 1, fontSize: 13, color: isError ? "#dc2626" : TEXT_SECONDARY }}>
        {isError ? log.synced : `${log.synced} records synced`}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: TEXT_SECONDARY }}>
        <Clock size={12} />
        {log.at ? new Date(log.at).toLocaleString() : "—"}
      </div>
    </Card>
  );
};

export default function SyncCenter() {
  const [logs, setLogs]     = useState([]);
  const [syncing, setSyncing] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadStatus = async () => {
    const data = await fetch(API("/sync/status")).then(r => r.json()).catch(() => []);
    setLogs(Array.isArray(data) ? data : []);
    setLoading(false);
  };

  useEffect(() => { loadStatus(); }, []);

  const triggerSync = async () => {
    setSyncing(true);
    await fetch(API("/sync/trigger"), { method: "POST" });
    setTimeout(async () => {
      await loadStatus();
      setSyncing(false);
    }, 2500);
  };

  const lastSyncBySource = {};
  for (const log of logs) {
    if (!lastSyncBySource[log.source]) lastSyncBySource[log.source] = log;
  }

  return (
    <AdministrationLayout
      title="Sync Center"
      subtitle="Monitor and control knowledge graph synchronization from existing platform collections."
      icon={<Database size={22} color={ACCENT} />}
      actions={
        <Button variant="primary" onClick={triggerSync} disabled={syncing} loading={syncing}>
          {!syncing && <RefreshCw size={16} />}
          {syncing ? "Syncing…" : "Run Full Sync"}
        </Button>
      }
    >

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14, marginBottom: 28 }}>
        {SOURCES.map(source => {
          const log = lastSyncBySource[source];
          const hasData = log && !log.synced?.toString().startsWith("error");
          return (
            <Card key={source}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: NAVY }}>{source.replace(/_/g, " ")}</span>
                {hasData ? <CheckCircle size={14} color="#059669" /> : <AlertCircle size={14} color={log ? "#dc2626" : TEXT_SECONDARY} />}
              </div>
              <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>
                {log ? (hasData ? `${log.synced} records` : "Error") : "Not synced yet"}
              </div>
              {log?.at && (
                <div style={{ fontSize: 11, color: TEXT_SECONDARY, marginTop: 4 }}>
                  Last: {new Date(log.at).toLocaleDateString()}
                </div>
              )}
            </Card>
          );
        })}
      </div>

      <Card padding="lg">
        <h2 style={{ fontSize: 15, fontWeight: 700, color: NAVY, marginBottom: 16 }}>Sync History (last 50)</h2>
        {loading ? (
          <LoadingOverlay text="Loading…" />
        ) : logs.length === 0 ? (
          <EmptyState icon={<Database />} title="No sync history yet. Run your first sync above." size="lg" />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {logs.map((log, i) => <StatusRow key={i} log={log} />)}
          </div>
        )}
      </Card>
    </AdministrationLayout>
  );
}
