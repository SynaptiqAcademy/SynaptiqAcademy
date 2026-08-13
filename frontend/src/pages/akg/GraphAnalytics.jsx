/* eslint-disable */
import React, { useEffect, useState } from "react";
import { Network, Users, Layers } from "lucide-react";
import { NAVY, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, NavTabs, ProgressBar, EmptyState } from "@/components/ds";
import { fetchApi } from "@/lib/api";

const API = (p) => `/api/akg${p}`;

export default function GraphAnalytics() {
  const [overview, setOverview] = useState(null);
  const [centrality, setCentrality] = useState([]);
  const [influence, setInfluence] = useState([]);
  const [communities, setCommunities] = useState([]);
  const [tab, setTab] = useState("centrality");

  useEffect(() => {
    Promise.all([
      fetchApi(API("/analytics/overview")).then(r => r.json()),
      fetchApi(API("/analytics/centrality?top_n=15")).then(r => r.json()),
      fetchApi(API("/analytics/influence?top_n=15")).then(r => r.json()),
      fetchApi(API("/analytics/communities")).then(r => r.json()),
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
    <ResearchLayout
      title="Graph Analytics"
      subtitle="Network-level analytics: centrality, influence, and community structure."
      stats={overview ? [
        { label: "Total Entities", value: overview.total_entities?.toLocaleString() ?? 0 },
        { label: "Relationships",  value: overview.total_relationships?.toLocaleString() ?? 0 },
        { label: "Avg Degree",     value: overview.avg_degree ?? "—" },
        { label: "Collaboration",  value: overview.collaboration_density?.density_label ?? "—" },
      ] : undefined}
      sidebar={(centrality.length > 0 || influence.length > 0 || communities.length > 0)
        ? <GraphAnalyticsSidebar centrality={centrality} influence={influence} communities={communities} />
        : undefined}
    >

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
    </ResearchLayout>
  );
}

// ── Right rail — real data already loaded by this page, never fabricated ──────
function GraphAnalyticsSidebar({ centrality, influence, communities }) {
  const topNode = centrality[0];
  const topInfluencer = influence[0];
  const largestCommunity = communities.length
    ? communities.reduce((a, b) => (b.size > a.size ? b : a), communities[0])
    : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Network size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Most Connected Node</div>
        </div>
        {topNode ? (
          <>
            <div style={{ fontFamily: "Georgia, serif", fontSize: 17, color: NAVY }}>{topNode.label}</div>
            <div style={{ fontSize: 12, color: "#64748B" }}>
              Degree {topNode.degree} (in {topNode.in_degree} / out {topNode.out_degree})
            </div>
          </>
        ) : (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>No centrality data yet.</p>
        )}
      </Card>

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Users size={13} style={{ color: ACCENT }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Most Influential Node</div>
        </div>
        {topInfluencer ? (
          <>
            <div style={{ fontFamily: "Georgia, serif", fontSize: 17, color: NAVY }}>{topInfluencer.label}</div>
            <div style={{ fontSize: 12, color: "#64748B" }}>
              {topInfluencer.entity_type?.replace(/_/g, " ")} · score {topInfluencer.influence_score}
            </div>
          </>
        ) : (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>No influence data yet.</p>
        )}
      </Card>

      {largestCommunity && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <Layers size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Largest Community</div>
          </div>
          <div style={{ fontFamily: "Georgia, serif", fontSize: 26, color: NAVY }}>{largestCommunity.size}</div>
          <div style={{ fontSize: 12, color: "#64748B" }}>members detected via label propagation</div>
        </Card>
      )}
    </div>
  );
}
