import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Network, GitBranch, Users, Lightbulb, ExternalLink } from "lucide-react";
import { NAVY, BRD, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Button, Badge, NavTabs, EmptyState } from "@/components/ds";

const API = (p) => `/api/akg${p}`;

const TYPE_COLORS = {
  researcher: "#3b82f6", educator: "#7c3aed", institution: "#d97706",
  topic: "#059669", grant: "#f59e0b", community: "#ec4899",
  marketplace_service: "#8b5cf6", default: ACCENT,
};

const RelCard = ({ r, onExplore }) => {
  const dir = r.direction || "out";
  const otherEntity = r.other_entity;
  return (
    <Card padding="sm" style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <div>
        <Badge variant={dir === "in" ? "info" : "success"}>{dir === "in" ? "← IN" : "→ OUT"}</Badge>
      </div>
      <div style={{ fontSize: 12, fontWeight: 600, color: NAVY, minWidth: 140 }}>{r.rel_type?.replace(/_/g, " ")}</div>
      <div style={{ flex: 1 }}>
        <span style={{ fontSize: 13, color: NAVY }}>{otherEntity?.label || r.to_id || r.from_id}</span>
        {otherEntity?.entity_type && (
          <span style={{ marginLeft: 8, fontSize: 11, color: TEXT_SECONDARY }}>({otherEntity.entity_type})</span>
        )}
      </div>
      {otherEntity?.entity_id && (
        <Button variant="outline" size="sm" onClick={() => onExplore(otherEntity.entity_id)}>
          View
        </Button>
      )}
    </Card>
  );
};

export default function EntityDetail() {
  const { entityId } = useParams();
  const nav = useNavigate();
  const [entity, setEntity] = useState(null);
  const [rels, setRels] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [tab, setTab] = useState("overview");

  useEffect(() => {
    if (!entityId) return;
    Promise.all([
      fetch(API(`/entities/${entityId}`)).then(r => r.json()),
      fetch(API(`/relationships/${entityId}?direction=both`)).then(r => r.json()),
      fetch(API(`/inference/related/${entityId}`)).then(r => r.json()).catch(() => []),
    ]).then(([e, r, s]) => {
      setEntity(e.error ? null : e);
      setRels(Array.isArray(r) ? r : []);
      setSuggestions(Array.isArray(s) ? s : []);
    });
  }, [entityId]);

  if (!entity) return (
    <EmptyState icon={<Network />} title="Entity not found or not yet synced." size="lg" />
  );

  const color = TYPE_COLORS[entity.entity_type] || TYPE_COLORS.default;
  const props = entity.properties || {};

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "relationships", label: `Relationships (${rels.length})` },
    { id: "related", label: `Related (${suggestions.length})` },
  ];

  return (
    <ResearchLayout>
      <div style={{ maxWidth: 1100 }}>
      <Card padding="xl" className="mb-5">
        <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
          <div style={{ width: 52, height: 52, borderRadius: 12, background: color + "20", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Network size={24} color={color} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: NAVY, marginBottom: 4 }}>{entity.label}</div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              <Badge color={color}>{entity.entity_type?.replace(/_/g, " ")}</Badge>
              {props.institution && <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>{props.institution}</span>}
              {props.country && <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>{props.country}</span>}
            </div>
          </div>
          <Button variant="outline" onClick={() => nav(`/akg/explorer?id=${entityId}`)}>
            <Network size={14} /> Explore in Graph
          </Button>
        </div>
      </Card>

      <div className="mb-5">
        <NavTabs tabs={tabs} active={tab} onChange={setTab} variant="pill" />
      </div>

      {tab === "overview" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <Card padding="lg">
            <h3 style={{ fontSize: 14, fontWeight: 700, color: NAVY, marginBottom: 16 }}>Properties</h3>
            {Object.entries(props).filter(([k, v]) => v && k !== "description" && !Array.isArray(v)).map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: `1px solid ${BRD}` }}>
                <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>{k.replace(/_/g, " ")}</span>
                <span style={{ fontSize: 12, color: NAVY, fontWeight: 500 }}>{String(v).substring(0, 60)}</span>
              </div>
            ))}
          </Card>
          <Card padding="lg">
            {props.description && (
              <>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: NAVY, marginBottom: 10 }}>Description</h3>
                <p style={{ fontSize: 13, color: TEXT_SECONDARY, lineHeight: 1.6 }}>{props.description}</p>
              </>
            )}
            {(props.research_interests?.length > 0 || props.expertise?.length > 0) && (
              <>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: NAVY, marginBottom: 10, marginTop: 16 }}>Interests & Expertise</h3>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {[...(props.research_interests || []), ...(props.expertise || [])].map((item, i) => (
                    <Badge key={i} variant="neutral">{item}</Badge>
                  ))}
                </div>
              </>
            )}
          </Card>
        </div>
      )}

      {tab === "relationships" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {rels.length === 0 ? (
            <EmptyState title="No relationships found." />
          ) : rels.map((r, i) => (
            <RelCard key={i} r={r} onExplore={(id) => nav(`/akg/entity/${id}`)} />
          ))}
        </div>
      )}

      {tab === "related" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
          {suggestions.length === 0 ? (
            <div style={{ gridColumn: "1/-1" }}>
              <EmptyState title="No related entities found." />
            </div>
          ) : suggestions.map((s, i) => {
            const c = TYPE_COLORS[s.entity_type] || TYPE_COLORS.default;
            return (
              <Card key={i} onClick={() => nav(`/akg/entity/${s.entity_id}`)}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, color: NAVY }}>{s.label}</span>
                  <Badge color={c}>{s.entity_type}</Badge>
                </div>
                {s.reason && <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{s.reason}</div>}
                {s.score !== undefined && <div style={{ fontSize: 11, color: TEXT_SECONDARY, marginTop: 4 }}>Match: {(s.score * 100).toFixed(0)}%</div>}
              </Card>
            );
          })}
        </div>
      )}
      </div>
    </ResearchLayout>
  );
}
