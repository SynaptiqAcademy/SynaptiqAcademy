/* eslint-disable */
import React, { useState } from "react";
import { Brain, GitBranch, Users, Zap, ChevronRight } from "lucide-react";
import { NAVY, WARM, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Button, Tag, Input, Badge, InlineError, EmptyState } from "@/components/ds";

const API = (p) => `/api/akg${p}`;

const QUERY_TYPES = [
  { id: "collaborators", label: "Collaborator Suggestions", icon: Users, description: "FOAF + keyword overlap to suggest researchers you should collaborate with", color: "#3b82f6" },
  { id: "related",       label: "Related Entities",         icon: GitBranch, description: "Find entities most semantically similar to a given entity", color: "#7c3aed" },
  { id: "gaps",          label: "Expertise Gaps",           icon: Zap, description: "Identify knowledge areas your network has but you lack", color: "#d97706" },
  { id: "partners",      label: "Grant Partners",           icon: Brain, description: "Find researchers who complement your grant application profile", color: "#059669" },
  { id: "path",          label: "Shortest Path",            icon: ChevronRight, description: "Find the shortest path between two entities in the graph", color: "#dc2626" },
];

const ResultCard = ({ item }) => (
  <Card>
    <div style={{ fontWeight: 600, color: NAVY, marginBottom: 4 }}>{item.label || item.entity_id || JSON.stringify(item).substring(0, 60)}</div>
    {item.reason && <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{item.reason}</div>}
    {item.score !== undefined && <div style={{ fontSize: 11, color: ACCENT, marginTop: 4 }}>Score: {typeof item.score === "number" ? (item.score * 100).toFixed(1) + "%" : item.score}</div>}
    {item.gap_terms && (
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 8 }}>
        {item.gap_terms.slice(0, 6).map((t, i) => (
          <Badge key={i} color="#d97706">{t}</Badge>
        ))}
      </div>
    )}
  </Card>
);

export default function AIReasoning() {
  const [activeQuery, setActiveQuery] = useState("collaborators");
  const [entityId, setEntityId] = useState("");
  const [entityIdB, setEntityIdB] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    if (!entityId.trim()) { setError("Entity ID is required"); return; }
    setLoading(true);
    setError("");
    setResults(null);
    try {
      let url;
      if (activeQuery === "collaborators") url = API(`/inference/collaborators/${entityId}`);
      else if (activeQuery === "related")  url = API(`/inference/related/${entityId}`);
      else if (activeQuery === "gaps")     url = API(`/inference/expertise-gaps/${entityId}`);
      else if (activeQuery === "partners") url = API(`/inference/grant-partners/${entityId}`);
      else if (activeQuery === "path") {
        if (!entityIdB.trim()) { setError("Target entity ID is required for path query"); setLoading(false); return; }
        const data = await fetch(API("/path"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ from_id: entityId, to_id: entityIdB }) }).then(r => r.json());
        setResults(data);
        setLoading(false);
        return;
      }
      const data = await fetch(url).then(r => r.json());
      setResults(data);
    } catch {
      setError("Request failed. Check the entity ID.");
    }
    setLoading(false);
  };

  const meta = QUERY_TYPES.find(q => q.id === activeQuery) || {};
  const Icon = meta.icon || Brain;

  return (
    <ResearchLayout
      title="AI Reasoning"
      subtitle="Graph-based reasoning over entities and relationships. Pure rule-based intelligence — no LLM."
      icon={<Brain size={22} color={ACCENT} />}
    >

      <div style={{ display: "flex", gap: 12, marginBottom: 28, flexWrap: "wrap" }}>
        {QUERY_TYPES.map(q => {
          const QI = q.icon;
          const active = activeQuery === q.id;
          return (
            <Tag
              key={q.id}
              onClick={() => { setActiveQuery(q.id); setResults(null); }}
              color={active ? q.color : undefined}
              size="lg"
            >
              <QI size={14} /> {q.label}
            </Tag>
          );
        })}
      </div>

      <Card padding="lg" className="mb-6">
        <Card.Header>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Icon size={18} color={meta.color || ACCENT} />
            <h2 style={{ fontSize: 16, fontWeight: 700, color: NAVY, margin: 0 }}>{meta.label}</h2>
          </div>
          <p style={{ fontSize: 13, color: TEXT_SECONDARY, margin: "8px 0 0" }}>{meta.description}</p>
        </Card.Header>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Input
            label={activeQuery === "path" ? "Source Entity ID" : "Entity ID"}
            value={entityId}
            onChange={e => setEntityId(e.target.value)}
            placeholder="e.g. user:64a1b2c3d4e5f6 or MD5 hash"
            hint={<>Tip: Use <code style={{ background: WARM, padding: "1px 4px", borderRadius: 3 }}>/api/akg/me/entity</code> to find your own entity ID.</>}
          />

          {activeQuery === "path" && (
            <Input
              label="Target Entity ID"
              value={entityIdB}
              onChange={e => setEntityIdB(e.target.value)}
              placeholder="Target entity ID"
            />
          )}

          <InlineError>{error}</InlineError>

          <Button variant="primary" onClick={run} disabled={loading} loading={loading} className="self-start">
            {loading ? "Reasoning…" : "Run Query"}
          </Button>
        </div>
      </Card>

      {results !== null && (
        <div>
          <div style={{ fontSize: 13, color: TEXT_SECONDARY, marginBottom: 12 }}>
            {Array.isArray(results) ? `${results.length} results` : "Result"}
          </div>
          {Array.isArray(results) ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
              {results.length === 0 ? (
                <div style={{ gridColumn: "1/-1" }}>
                  <EmptyState title="No results found." description="Try a different entity." />
                </div>
              ) : results.map((item, i) => <ResultCard key={i} item={item} />)}
            </div>
          ) : (
            <Card padding="lg">
              <pre style={{ fontSize: 12, color: NAVY, overflowX: "auto", margin: 0 }}>{JSON.stringify(results, null, 2)}</pre>
            </Card>
          )}
        </div>
      )}
    </ResearchLayout>
  );
}
