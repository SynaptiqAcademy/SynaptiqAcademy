/* eslint-disable */
import React, { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, Minus, Building2, Users, RefreshCw } from "lucide-react";
import { NAVY, WARM, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { DiscoveryLayout } from "@/layouts";
import { Card, Button, Badge, ProgressBar, EmptyState, LoadingOverlay } from "@/components/ds";

const API = (p) => `/api/akg${p}`;

const TREND_COLORS = { emerging: "#059669", stable: "#d97706", declining: "#dc2626" };
const TREND_ICONS  = { emerging: TrendingUp, stable: Minus, declining: TrendingDown };

export default function TrendDiscovery() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [windowDays, setWindowDays] = useState(30);

  const loadReport = async () => {
    setLoading(true);
    const data = await fetch(API("/trends")).then(r => r.json()).catch(() => ({}));
    setReport(data);
    setLoading(false);
  };

  useEffect(() => { loadReport(); }, []);

  if (loading) return <LoadingOverlay text="Loading trend data…" />;

  const emerging = report?.emerging_topics || [];
  const hotAreas = report?.hot_research_areas || [];
  const instGrowth = report?.institutional_growth || [];
  const collabTrend = report?.collaboration_trends?.monthly || [];

  const maxCollab = Math.max(...collabTrend.map(m => m.collaborations), 1);

  return (
    <DiscoveryLayout
      title="Trend Discovery"
      subtitle="Emerging topics, growth signals, and declining research areas — powered by the knowledge graph."
      actions={
        <Button variant="outline" onClick={loadReport}>
          <RefreshCw size={14} /> Refresh
        </Button>
      }
    >

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
        <Card padding="lg">
          <h2 style={{ fontSize: 16, fontWeight: 700, color: NAVY, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
            <TrendingUp size={18} color="#059669" /> Emerging Topics
          </h2>
          {emerging.length === 0 ? (
            <EmptyState title="No trend data yet — sync the graph first." />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {emerging.map((t, i) => {
                const color = TREND_COLORS[t.trend] || "#6b7280";
                const Icon = TREND_ICONS[t.trend] || Minus;
                return (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 14px", background: WARM, borderRadius: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 500, flex: 1, color: NAVY }}>{t.label}</span>
                    <div style={{ display: "flex", alignItems: "center", gap: 4, color }}>
                      <Icon size={14} />
                      <span style={{ fontSize: 12, fontWeight: 600 }}>{t.growth_rate > 0 ? "+" : ""}{t.growth_rate}%</span>
                    </div>
                    <Badge color={color}>{t.trend}</Badge>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        <Card padding="lg">
          <h2 style={{ fontSize: 16, fontWeight: 700, color: NAVY, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
            <TrendingUp size={18} color={ACCENT} /> Hot Research Areas
          </h2>
          {hotAreas.length === 0 ? (
            <EmptyState title="No data yet." />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {hotAreas.map((a, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{ fontSize: 13, color: NAVY, flex: 1, fontWeight: 500 }}>{a.area}</span>
                  <div style={{ width: 100 }}>
                    <ProgressBar value={a.new_connections} max={hotAreas[0]?.new_connections || 1} showValue={false} />
                  </div>
                  <span style={{ fontSize: 12, color: TEXT_SECONDARY, minWidth: 40, textAlign: "right" }}>{a.new_connections}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <Card padding="lg">
          <h2 style={{ fontSize: 16, fontWeight: 700, color: NAVY, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
            <Building2 size={18} color="#d97706" /> Institutional Growth
          </h2>
          {instGrowth.length === 0 ? (
            <EmptyState title="No data yet." />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {instGrowth.slice(0, 8).map((inst, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 12px", background: WARM, borderRadius: 8 }}>
                  <span style={{ fontSize: 13, color: NAVY, flex: 1 }}>{inst.label}</span>
                  <span style={{ fontSize: 12, color: "#d97706", fontWeight: 600 }}>+{inst.new_affiliations} researchers</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card padding="lg">
          <h2 style={{ fontSize: 16, fontWeight: 700, color: NAVY, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
            <Users size={18} color="#7c3aed" /> Collaboration Trends
          </h2>
          {collabTrend.length === 0 ? (
            <EmptyState title="No collaboration data yet." />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {collabTrend.map((m, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{ fontSize: 12, color: TEXT_SECONDARY, minWidth: 60 }}>{m.month}</span>
                  <div style={{ flex: 1 }}>
                    <ProgressBar value={m.collaborations} max={maxCollab} showValue={false} />
                  </div>
                  <span style={{ fontSize: 12, color: NAVY, fontWeight: 600, minWidth: 30, textAlign: "right" }}>{m.collaborations}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </DiscoveryLayout>
  );
}
