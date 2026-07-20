/* eslint-disable */
import React, { useEffect, useState } from "react";
import { Network, Search, TrendingUp, BarChart2, Lightbulb, RefreshCw, Layers, Users, GitBranch } from "lucide-react";
import { NAVY, WARM, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Button, StatGrid, StatCard } from "@/components/ds";

const API = (p) => `/api/akg${p}`;

const QuickLink = ({ to, icon: Icon, label, description, color }) => (
  <Card to={to}>
    <div style={{ width: 40, height: 40, borderRadius: 10, background: color + "18", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 12 }}>
      <Icon size={20} color={color} />
    </div>
    <div style={{ fontWeight: 600, color: NAVY, marginBottom: 4 }}>{label}</div>
    <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{description}</div>
  </Card>
);

export default function KnowledgeGraphHome() {
  const [overview, setOverview] = useState(null);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    fetch(API("/analytics/overview")).then(r => r.json()).then(setOverview).catch(() => {});
  }, []);

  const triggerSync = async () => {
    setSyncing(true);
    await fetch(API("/sync/trigger"), { method: "POST" });
    setTimeout(() => setSyncing(false), 2000);
  };

  return (
    <ResearchLayout
      title="Academic Knowledge Graph"
      subtitle="The semantic intelligence layer powering every AI capability across Synaptiq."
      icon={<Network size={24} color={ACCENT} />}
      actions={
        <Button variant="primary" onClick={triggerSync} disabled={syncing} loading={syncing}>
          {!syncing && <RefreshCw size={16} />}
          {syncing ? "Syncing…" : "Sync Now"}
        </Button>
      }
    >

      <StatGrid cols={4} className="mb-8">
        <StatCard label="Total Entities" value={overview?.total_entities?.toLocaleString()} icon={<Layers />} />
        <StatCard label="Relationships" value={overview?.total_relationships?.toLocaleString()} icon={<GitBranch />} />
        <StatCard label="Avg Degree" value={overview?.avg_degree} icon={<Network />} />
        <StatCard label="Collab Density" value={overview?.collaboration_density?.density_label} icon={<Users />} />
      </StatGrid>

      <h2 style={{ fontSize: 16, fontWeight: 700, color: NAVY, marginBottom: 16 }}>Explore the Graph</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 32 }}>
        <QuickLink to="/akg/explorer"         icon={Network}      label="Graph Explorer"        description="Interactive visualization of entities and relationships"  color={ACCENT} />
        <QuickLink to="/akg/search"           icon={Search}       label="Semantic Search"       description="TF-IDF powered search across all graph entities"          color="#7c3aed" />
        <QuickLink to="/akg/trends"           icon={TrendingUp}   label="Trend Discovery"       description="Emerging topics, hot research areas, growth signals"       color="#059669" />
        <QuickLink to="/akg/analytics"        icon={BarChart2}    label="Graph Analytics"       description="Centrality, influence, community detection"               color="#d97706" />
        <QuickLink to="/akg/recommendations"  icon={Lightbulb}    label="Recommendations"       description="Graph-powered personalized academic recommendations"       color="#dc2626" />
        <QuickLink to="/akg/sync"             icon={RefreshCw}    label="Sync Center"           description="Monitor and control knowledge graph synchronization"       color="#0891b2" />
      </div>

      {overview?.entities_by_type && (
        <Card padding="lg">
          <h2 style={{ fontSize: 15, fontWeight: 700, color: NAVY, marginBottom: 16 }}>Entity Distribution</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
            {Object.entries(overview.entities_by_type).slice(0, 12).map(([type, count]) => (
              <div key={type} style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: WARM, borderRadius: 8 }}>
                <span style={{ fontSize: 13, color: NAVY, fontWeight: 500 }}>{type.replace(/_/g, " ")}</span>
                <span style={{ fontSize: 13, color: TEXT_SECONDARY, fontWeight: 600 }}>{count}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </ResearchLayout>
  );
}
