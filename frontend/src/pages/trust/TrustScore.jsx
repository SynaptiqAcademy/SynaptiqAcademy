/* eslint-disable */
import React, { useEffect, useState } from "react";
import { RefreshCw, ChevronDown, ChevronUp } from "lucide-react";
import { NAVY, BRD, EMERALD, ACCENT, TEXT_SECONDARY } from "../../lib/tokens";
import { AnalyticsLayout } from "@/layouts";
import { Card, Button, Badge, LoadingOverlay } from "@/components/ds";

const API = "/api/trust";

const LEVEL_COLORS = {
  Unverified:   ACCENT,
  Basic:        "#D97706",
  Established:  "#0369A1",
  Trusted:      EMERALD,
  Distinguished:"#7C3AED",
};

// Kept hand-rolled: this is a composite accordion-header row (label + inline
// progress bar + score/weight column + chevron, full-width, left-aligned)
// rather than a plain labeled button. ds/Button.jsx's fixed height scale and
// centered-content BASE class would collapse this three-part flexible layout,
// so the <button> shell stays hand-rolled while everything it contains keeps
// its exact toggle logic.
function FactorRow({ id, factor }) {
  const [open, setOpen] = useState(false);
  const contribution = (factor.score * factor.weight) / 100;
  const color = factor.score >= 80 ? EMERALD : factor.score >= 50 ? "#0369A1" : factor.score >= 20 ? "#D97706" : ACCENT;

  return (
    <div style={{ borderBottom: `1px solid ${BRD}` }}>
      <button onClick={() => setOpen(!open)}
        style={{ width: "100%", display: "flex", alignItems: "center", gap: 12,
          padding: "12px 0", background: "none", border: "none", cursor: "pointer", textAlign: "left" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 4 }}>{factor.label}</div>
          <div style={{ height: 6, background: BRD, borderRadius: 3 }}>
            <div style={{ width: `${factor.score}%`, height: "100%", background: color,
              borderRadius: 3, transition: "width .5s ease" }} />
          </div>
        </div>
        <div style={{ textAlign: "right", minWidth: 80 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color }}>
            {Math.round(factor.score)}
            <span style={{ fontSize: 11, color: TEXT_SECONDARY, fontWeight: 400 }}>/100</span>
          </div>
          <div style={{ fontSize: 11, color: TEXT_SECONDARY }}>
            ×{factor.weight}% = +{contribution.toFixed(1)}
          </div>
        </div>
        {open ? <ChevronUp size={16} color={TEXT_SECONDARY} /> : <ChevronDown size={16} color={TEXT_SECONDARY} />}
      </button>
      {open && (
        <div style={{ paddingBottom: 12, paddingLeft: 2 }}>
          {factor.value !== undefined && (
            <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginBottom: 4 }}>
              Value: <strong>{factor.value}</strong>
            </div>
          )}
          {factor.reasons?.map((r, i) => (
            <div key={i} style={{ fontSize: 12, color: TEXT_SECONDARY, marginBottom: 2 }}>• {r}</div>
          ))}
          {factor.recommendation && (
            <div style={{ fontSize: 12, color: "#0369A1", marginTop: 6,
              background: "#0369A114", borderRadius: 6, padding: "6px 10px" }}>
              💡 {factor.recommendation}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function TrustScore() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = (refresh = false) => {
    setRefreshing(true);
    fetch(API + "/score" + (refresh ? "?refresh=true" : ""), { credentials: "include" })
      .then(r => r.ok ? r.json() : null)
      .then(d => setData(d))
      .finally(() => { setLoading(false); setRefreshing(false); });
  };

  useEffect(() => { load(); }, []);

  const levelColor = LEVEL_COLORS[data?.level] || ACCENT;

  return (
    <AnalyticsLayout
      title="Trust Score"
      subtitle="14-factor weighted breakdown of your academic trust"
      actions={
        <Button variant="outline" onClick={() => load(true)} disabled={refreshing}>
          <RefreshCw size={14} style={{ animation: refreshing ? "spin 1s linear infinite" : "none" }} />
          Recalculate
        </Button>
      }
    >
      <div style={{ maxWidth: 800, margin: "0 auto" }}>

        {loading ? (
          <LoadingOverlay text="Computing trust score…" />
        ) : (
          <>
            {/* Score hero */}
            <Card padding="xl" style={{ marginBottom: 20, display: "flex", alignItems: "center", gap: 28 }}>
              <div style={{
                width: 110, height: 110, borderRadius: "50%",
                border: `6px solid ${levelColor}`,
                display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                flexShrink: 0,
              }}>
                <div style={{ fontSize: 34, fontWeight: 800, color: levelColor, lineHeight: 1 }}>
                  {data?.score || 0}
                </div>
                <div style={{ fontSize: 10, color: TEXT_SECONDARY }}>/ 100</div>
              </div>
              <div>
                <Badge color={levelColor} style={{ marginBottom: 8 }}>
                  {data?.level}
                </Badge>
                <p style={{ color: TEXT_SECONDARY, fontSize: 13, margin: "8px 0 8px" }}>
                  {data?.level_advice}
                </p>
                <p style={{ color: TEXT_SECONDARY, fontSize: 12, margin: 0 }}>
                  Computed: {data?.computed_at ? new Date(data.computed_at).toLocaleString() : "—"}
                </p>
              </div>
            </Card>

            {/* Factor breakdown */}
            <Card padding="lg">
              <div style={{ fontSize: 13, fontWeight: 600, color: NAVY, marginBottom: 4 }}>
                Score Breakdown
              </div>
              <p style={{ fontSize: 12, color: TEXT_SECONDARY, margin: "0 0 16px" }}>
                Each factor's contribution = raw score × weight. Click to expand details.
              </p>
              {data?.factors && Object.entries(data.factors).map(([id, factor]) => (
                <FactorRow key={id} id={id} factor={factor} />
              ))}
            </Card>
          </>
        )}
      </div>
    </AnalyticsLayout>
  );
}
