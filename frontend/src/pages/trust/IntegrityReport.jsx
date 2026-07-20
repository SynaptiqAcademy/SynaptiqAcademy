/* eslint-disable */
import React, { useEffect, useState } from "react";
import { RefreshCw, AlertTriangle, CheckCircle2, XCircle, ShieldAlert } from "lucide-react";
import { NAVY, BRD, EMERALD, ACCENT, TEXT_SECONDARY } from "../../lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Button, Badge, Callout, LoadingOverlay } from "@/components/ds";

const API = "/api/trust";

const LEVEL_COLORS = {
  Excellent:    EMERALD,
  Good:         "#0369A1",
  Fair:         "#D97706",
  "Under Review": ACCENT,
};

const SEVERITY_CONFIG = {
  high:   { color: ACCENT,   icon: XCircle },
  medium: { color: "#D97706",icon: AlertTriangle },
  low:    { color: "#0369A1",icon: ShieldAlert },
};

export default function IntegrityReport() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = (refresh = false) => {
    setRefreshing(true);
    fetch(API + "/integrity" + (refresh ? "?refresh=true" : ""), { credentials: "include" })
      .then(r => r.ok ? r.json() : null)
      .then(d => setReport(d))
      .finally(() => { setLoading(false); setRefreshing(false); });
  };

  useEffect(() => { load(); }, []);

  const levelColor = LEVEL_COLORS[report?.level] || ACCENT;

  return (
    <ResearchLayout
      title="Integrity Report"
      subtitle="Academic integrity analysis — retractions, duplicates, flags"
      actions={
        <Button variant="outline" onClick={() => load(true)} disabled={refreshing}>
          <RefreshCw size={14} style={{ animation: refreshing ? "spin 1s linear infinite" : "none" }} />
          Regenerate
        </Button>
      }
    >
      <div style={{ maxWidth: 800, margin: "0 auto" }}>

        {loading ? (
          <LoadingOverlay text="Analysing integrity…" />
        ) : (
          <>
            {/* Score hero */}
            <Card padding="xl" style={{ marginBottom: 20, display: "flex", alignItems: "center", gap: 28 }}>
              <div style={{
                width: 100, height: 100, borderRadius: "50%",
                border: `6px solid ${levelColor}`,
                display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                flexShrink: 0,
              }}>
                <div style={{ fontSize: 30, fontWeight: 800, color: levelColor }}>{report?.score || 0}</div>
                <div style={{ fontSize: 10, color: TEXT_SECONDARY }}>/100</div>
              </div>
              <div>
                <Badge color={levelColor} style={{ marginBottom: 8 }}>
                  {report?.level}
                </Badge>
                <p style={{ color: TEXT_SECONDARY, fontSize: 13, margin: "8px 0 6px" }}>{report?.level_note}</p>
                <p style={{ color: TEXT_SECONDARY, fontSize: 12, margin: 0 }}>
                  {report?.publications_checked || 0} publications • {report?.dois_checked || 0} DOIs checked
                </p>
              </div>
            </Card>

            {/* Flags */}
            {report?.flags?.length > 0 && (
              <Card padding="lg" style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 12 }}>
                  Flags ({report.flags.length})
                </div>
                {report.flags.map((f, i) => {
                  const cfg = SEVERITY_CONFIG[f.severity] || SEVERITY_CONFIG.low;
                  const Icon = cfg.icon;
                  return (
                    <div key={i} style={{
                      display: "flex", gap: 12, padding: "10px 0",
                      borderBottom: i < report.flags.length - 1 ? `1px solid ${BRD}` : "none",
                    }}>
                      <Icon size={16} color={cfg.color} style={{ flexShrink: 0, marginTop: 2 }} />
                      <div>
                        <div style={{ fontSize: 13, color: NAVY, marginBottom: 2 }}>{f.description}</div>
                        <div style={{ fontSize: 11, color: TEXT_SECONDARY }}>
                          Severity: <strong style={{ color: cfg.color }}>{f.severity}</strong>
                          {f.raised_at ? " · " + new Date(f.raised_at).toLocaleDateString() : ""}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </Card>
            )}

            {/* Positive signals */}
            {report?.positive_signals?.length > 0 && (
              <Callout variant="success" title="Positive Signals">
                {report.positive_signals.map((s, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8,
                    fontSize: 13, color: NAVY, padding: "4px 0" }}>
                    <CheckCircle2 size={14} color={EMERALD} style={{ flexShrink: 0, marginTop: 2 }} />
                    {s}
                  </div>
                ))}
              </Callout>
            )}
          </>
        )}
      </div>
    </ResearchLayout>
  );
}
