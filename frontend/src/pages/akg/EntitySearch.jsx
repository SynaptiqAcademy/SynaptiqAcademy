/* eslint-disable */
import React, { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Filter, ExternalLink } from "lucide-react";
import { NAVY, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { DiscoveryLayout } from "@/layouts";
import { Card, Button, Badge, Tag, SearchBar, EmptyState, LoadingOverlay } from "@/components/ds";

const API = (p) => `/api/akg${p}`;

const ENTITY_TYPE_OPTIONS = [
  "researcher", "educator", "student", "institution", "topic",
  "research_area", "grant", "community", "marketplace_service",
  "funding_agency", "method", "software", "journal", "conference",
];

const TYPE_BADGE_COLORS = {
  researcher: "#3b82f6", educator: "#7c3aed", institution: "#d97706",
  topic: "#059669", grant: "#f59e0b", community: "#ec4899",
  marketplace_service: "#8b5cf6", default: ACCENT,
};

export default function EntitySearch() {
  const nav = useNavigate();
  const [query, setQuery] = useState("");
  const [selectedTypes, setSelectedTypes] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const toggleType = (t) => setSelectedTypes(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]);

  const search = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const typeParam = selectedTypes.length ? `&entity_types=${selectedTypes.join(",")}` : "";
      const data = await fetch(API(`/entities/search?q=${encodeURIComponent(query)}&limit=30${typeParam}`)).then(r => r.json());
      setResults(Array.isArray(data) ? data : []);
    } finally {
      setLoading(false);
    }
  }, [query, selectedTypes]);

  const handleKeyDown = (e) => { if (e.key === "Enter") search(); };

  return (
    <DiscoveryLayout
      title="Semantic Entity Search"
      subtitle="TF-IDF cosine similarity search across all knowledge graph entities. No LLM — pure rule-based intelligence."
    >

      <Card padding="lg" className="mb-6">
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          <div style={{ flex: 1 }}>
            <SearchBar
              value={query}
              onChange={setQuery}
              onKeyDown={handleKeyDown}
              placeholder="Search by label, description, keywords, expertise…"
              size="lg"
            />
          </div>
          <Button variant="primary" size="lg" onClick={search}>
            Search
          </Button>
        </div>

        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
            <Filter size={14} color={TEXT_SECONDARY} />
            <span style={{ fontSize: 12, color: TEXT_SECONDARY, fontWeight: 600 }}>Filter by entity type:</span>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {ENTITY_TYPE_OPTIONS.map(t => {
              const active = selectedTypes.includes(t);
              const color = TYPE_BADGE_COLORS[t] || TYPE_BADGE_COLORS.default;
              return (
                <Tag key={t} onClick={() => toggleType(t)} color={active ? color : undefined}>
                  {t.replace(/_/g, " ")}
                </Tag>
              );
            })}
          </div>
        </div>
      </Card>

      {loading && <LoadingOverlay text="Searching…" />}

      {!loading && searched && results.length === 0 && (
        <EmptyState icon={<Search />} title={`No entities found for "${query}"`} size="lg" />
      )}

      {!loading && results.length > 0 && (
        <div>
          <div style={{ fontSize: 13, color: TEXT_SECONDARY, marginBottom: 12 }}>{results.length} results</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {results.map(r => {
              const color = TYPE_BADGE_COLORS[r.entity_type] || TYPE_BADGE_COLORS.default;
              return (
                <Card key={r.entity_id} style={{ display: "flex", alignItems: "center", gap: 16 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, color: NAVY }}>{r.label}</span>
                      <Badge color={color}>{r.entity_type?.replace(/_/g, " ")}</Badge>
                    </div>
                    {r.properties?.description && (
                      <p style={{ fontSize: 12, color: TEXT_SECONDARY, margin: 0, lineHeight: 1.5 }}>{r.properties.description.substring(0, 140)}{r.properties.description.length > 140 ? "…" : ""}</p>
                    )}
                    {r.score !== undefined && (
                      <div style={{ fontSize: 11, color: TEXT_SECONDARY, marginTop: 4 }}>Relevance: {(r.score * 100).toFixed(0)}%</div>
                    )}
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => nav(`/akg/entity/${r.entity_id}`)}>
                    <ExternalLink size={14} color={ACCENT} />
                  </Button>
                </Card>
              );
            })}
          </div>
        </div>
      )}
    </DiscoveryLayout>
  );
}
