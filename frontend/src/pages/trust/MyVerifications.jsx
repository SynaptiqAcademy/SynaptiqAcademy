/* eslint-disable */
import React, { useEffect, useState } from "react";
import { RefreshCw, CheckCircle2, Clock, XCircle } from "lucide-react";
import { NAVY, BRD, EMERALD, ACCENT, TEXT_SECONDARY } from "../../lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Badge, Button, FilterChip, EmptyState, LoadingOverlay } from "@/components/ds";

const API = "/api/trust";

const STATUS_CONFIG = {
  verified:  { icon: CheckCircle2, color: EMERALD,  label: "Verified" },
  pending:   { icon: Clock,        color: "#D97706", label: "Pending" },
  failed:    { icon: XCircle,      color: ACCENT,    label: "Failed" },
  rejected:  { icon: XCircle,      color: ACCENT,    label: "Rejected" },
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const Icon = cfg.icon;
  return (
    <Badge color={cfg.color}>
      <Icon size={12} /> {cfg.label}
    </Badge>
  );
}

// Kept hand-rolled: the exact 80/50-threshold EMERALD/amber/crimson color
// logic here doesn't match ds/Progress.jsx's ProgressBar `colorByValue`
// thresholds (80/100, amber/crimson/emerald-only-at-100), so mapping to it
// would silently change which color shows at a given confidence value.
function ConfidenceBar({ value = 0 }) {
  const color = value >= 80 ? EMERALD : value >= 50 ? "#D97706" : ACCENT;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 4, background: BRD, borderRadius: 2 }}>
        <div style={{ width: `${value}%`, height: "100%", background: color, borderRadius: 2,
          transition: "width .5s ease" }} />
      </div>
      <span style={{ fontSize: 12, color: TEXT_SECONDARY, minWidth: 30 }}>{value}%</span>
    </div>
  );
}

export default function MyVerifications() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState({});
  const [types, setTypes] = useState([]);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    Promise.all([
      fetch(API + "/verifications", { credentials: "include" }).then(r => r.json()),
      fetch(API + "/verifications/types", { credentials: "include" }).then(r => r.json()),
    ]).then(([v, t]) => {
      setItems(v || []);
      setTypes(t || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const runAuto = async (vType) => {
    setRunning(p => ({ ...p, [vType]: true }));
    const r = await fetch(API + "/verifications/run", {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ verification_type: vType, payload: {} }),
    });
    if (r.ok) {
      const updated = await r.json();
      setItems(prev => {
        const idx = prev.findIndex(x => x.verification_type === vType);
        if (idx >= 0) { const arr = [...prev]; arr[idx] = updated; return arr; }
        return [updated, ...prev];
      });
    }
    setRunning(p => ({ ...p, [vType]: false }));
  };

  const verifiedSet = new Set(items.map(i => i.verification_type));
  const filtered = filter === "all" ? items : items.filter(i => i.status === filter);

  return (
    <ResearchLayout
      title="My Verifications"
      subtitle={`${items.filter(x => x.status === "verified").length} of ${types.length} types verified`}
      actions={
        <div style={{ display: "flex", gap: 8 }}>
          {["all", "verified", "pending", "failed"].map(f => (
            <FilterChip
              key={f}
              label={f.charAt(0).toUpperCase() + f.slice(1)}
              active={filter === f}
              onClick={() => setFilter(f)}
            />
          ))}
        </div>
      }
    >
      <div style={{ maxWidth: 900, margin: "0 auto" }}>

        {loading ? (
          <LoadingOverlay text="Loading…" />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {filtered.map(v => (
              <Card key={v._id || v.verification_type} padding="md">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                  <div style={{ fontWeight: 600, color: NAVY, fontSize: 14 }}>{v.label}</div>
                  <StatusBadge status={v.status} />
                </div>
                <ConfidenceBar value={v.confidence || 0} />
                {v.notes && (
                  <p style={{ fontSize: 12, color: TEXT_SECONDARY, margin: "8px 0 0" }}>{v.notes}</p>
                )}
                {v.expires_at && (
                  <p style={{ fontSize: 11, color: TEXT_SECONDARY, margin: "4px 0 0" }}>
                    Expires: {new Date(v.expires_at).toLocaleDateString()}
                  </p>
                )}
              </Card>
            ))}

            {filtered.length === 0 && (
              <EmptyState title="No verifications found for this filter." />
            )}

            {/* Available to run */}
            {filter === "all" && types.filter(t => !verifiedSet.has(t.id)).length > 0 && (
              <Card padding="md" style={{ marginTop: 8 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 12 }}>
                  Available Verifications
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {types.filter(t => !verifiedSet.has(t.id)).slice(0, 10).map(t => (
                    <div key={t.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                      padding: "8px 0", borderBottom: `1px solid ${BRD}` }}>
                      <span style={{ fontSize: 13, color: NAVY }}>{t.label}</span>
                      <Button size="sm" onClick={() => runAuto(t.id)} disabled={running[t.id]}>
                        <RefreshCw size={12} style={{ animation: running[t.id] ? "spin 1s linear infinite" : "none" }} />
                        {running[t.id] ? "Running…" : "Run Check"}
                      </Button>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        )}
      </div>
    </ResearchLayout>
  );
}
