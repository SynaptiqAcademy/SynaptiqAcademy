/* eslint-disable */
import React, { useEffect, useState } from "react";
import { BarChart2, Network, Users, Layers, Activity } from "lucide-react";
import { NAVY, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { AnalyticsLayout } from "@/layouts";
import { Card, NavTabs, StatGrid, StatCard, ProgressBar, EmptyState } from "@/components/ds";

const API = (p) => `/api/akg${p}`;

export default function GraphAnalytics() {
  const [overview, setOverview] = useState(null);
  const [centrality, setCentrality] = useState([]);
  const [influence, setInfluence] = useState([]);
  const [communities, setCommunities] = useState([]);
  const [tab, setTab] = useState("centrality");

  useEffect(() => {
    Promise.all([
      fetch(API("/analytics/overview")).then(r => r.json()),
      fetch(API("/analytics/centrality?top_n=15")).then(r => r.json()),
      fetch(API("/analytics/influence?top_n=15")).then(r => r.json()),
      fetch(API("/analytics/communities")).then(r => r.json()),
    ]).then(([ov, cent, inf, comm]) => {
      setOverview(ov);
      setCentrality(Array.isArray(cent) ? cent : []);
      setInfluence(Array.isArray(inf) ? inf : []);
      setCommunities(Array.isArray(comm) ? comm : []);
    }).catch(() => {});
  }, []);

  const tabs = [
    { id: "centrality", label: "Degree Centrality" },
    { id: "influence",  label: "Influence Score" },
    { id: "communities", label: "Communities" },
  ];

  const maxDegree    = Math.max(...centrality.map(n => n.degree || 0), 1);
  const maxInfluence = Math.max(...influence.map(n => n.influence_score || 0), 1);

  return (
    <AnalyticsLayout
      title="Graph Analytics"
      subtitle="Network-level analytics: centrality, influence, and community structure."
    >

      {overview && (
        <StatGrid cols={4} className="mb-7">
          <StatCard label="Total Entities"    value={overview.total_entities?.toLocaleString()}      icon={<Layers />} />
          <StatCard label="Relationships"     value={overview.total_relationships?.toLocaleString()} icon={<Network />} />
          <StatCard label="Avg Degree"        value={overview.avg_degree}                            icon={<Activity />} />
          <StatCard label="Collaboration"     value={overview.collaboration_density?.density_label}  icon={<Users />} />
        </StatGrid>
      )}

      <div className="mb-5">
        <NavTabs tabs={tabs} active={tab} onChange={setTab} variant="pill" />
      </div>

      {tab === "centrality" && (
        <Card padding="lg">
          <h2 style={{ fontSize: 15, fontWeight: 700, color: NAVY, marginBottom: 16 }}>Most Connected Nodes</h2>
          {centrality.length === 0 ? (
            <EmptyState title="No data yet — sync the graph first." />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {centrality.map((n, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <span style={{ fontSize: 13, color: TEXT_SECONDARY, minWidth: 20, textAlign: "right" }}>#{i + 1}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: NAVY, marginBottom: 2 }}>{n.label}</div>
                    <ProgressBar value={n.degree} max={maxDegree} showValue={false} />
                  </div>
                  <div style={{ minWidth: 100, textAlign: "right", fontSize: 12, color: TEXT_SECONDARY }}>
                    in: {n.in_degree} | out: {n.out_degree}
                  </div>
                  <span style={{ fontSize: 12, fontWeight: 700, color: ACCENT, minWidth: 30, textAlign: "right" }}>{n.degree}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {tab === "influence" && (
        <Card padding="lg">
          <h2 style={{ fontSize: 15, fontWeight: 700, color: NAVY, marginBottom: 16 }}>Most Influential Nodes (In-Degree)</h2>
          {influence.length === 0 ? (
            <EmptyState title="No data yet." />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {influence.map((n, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <span style={{ fontSize: 13, color: TEXT_SECONDARY, minWidth: 20, textAlign: "right" }}>#{i + 1}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: NAVY, marginBottom: 2 }}>{n.label}</div>
                    <ProgressBar value={n.influence_score} max={maxInfluence} showValue={false} />
                  </div>
                  <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>{n.entity_type?.replace(/_/g, " ")}</span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: "#7c3aed", minWidth: 30, textAlign: "right" }}>{n.influence_score}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {tab === "communities" && (
        <Card padding="lg">
          <h2 style={{ fontSize: 15, fontWeight: 700, color: NAVY, marginBottom: 16 }}>Detected Communities (Label Propagation)</h2>
          {communities.length === 0 ? (
            <EmptyState title="No communities detected yet." />
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
              {communities.map((c, i) => (
                <Card key={i} padding="sm">
                  <div style={{ fontSize: 13, fontWeight: 700, color: NAVY, marginBottom: 6 }}>Community #{i + 1}</div>
                  <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginBottom: 8 }}>{c.size} members</div>
                  {c.member_ids?.slice(0, 3).map((id, j) => (
                    <div key={j} style={{ fontSize: 11, color: TEXT_SECONDARY, padding: "2px 0" }}>{id.substring(0, 30)}…</div>
                  ))}
                </Card>
              ))}
            </div>
          )}
        </Card>
      )}
    </AnalyticsLayout>
  );
}
