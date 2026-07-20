/* eslint-disable */
import React, { useEffect, useRef, useState, useCallback } from "react";
import { Search, ZoomIn, ZoomOut, Maximize2, Info, Network } from "lucide-react";
import { NAVY, WARM, BRD, ACCENT, TEXT_SECONDARY, WHITE } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Button, Input, FormSelect, Badge, EmptyState } from "@/components/ds";

const API = (p) => `/api/akg${p}`;

const TYPE_COLORS = {
  researcher: "#3b82f6", educator: "#7c3aed", student: "#06b6d4",
  institution: "#d97706", topic: "#059669", research_area: "#10b981",
  grant: "#f59e0b", community: "#ec4899", marketplace_service: "#8b5cf6",
  funding_agency: "#ef4444", country: "#6b7280", default: ACCENT,
};

function useForceLayout(nodes, edges) {
  const [positions, setPositions] = useState({});

  useEffect(() => {
    if (!nodes.length) return;
    const W = 800, H = 560;
    const pos = {};
    nodes.forEach((n, i) => {
      const angle = (i / nodes.length) * 2 * Math.PI;
      const r = Math.min(W, H) * 0.35;
      pos[n.entity_id] = {
        x: W / 2 + r * Math.cos(angle) + (Math.random() - 0.5) * 30,
        y: H / 2 + r * Math.sin(angle) + (Math.random() - 0.5) * 30,
      };
    });

    let p = { ...pos };
    for (let iter = 0; iter < 80; iter++) {
      const delta = {};
      nodes.forEach(n => { delta[n.entity_id] = { x: 0, y: 0 }; });

      // Repulsion
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i].entity_id, b = nodes[j].entity_id;
          const dx = (p[a]?.x || 0) - (p[b]?.x || 0);
          const dy = (p[a]?.y || 0) - (p[b]?.y || 0);
          const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
          const force = 2000 / (dist * dist);
          delta[a].x += (dx / dist) * force;
          delta[a].y += (dy / dist) * force;
          delta[b].x -= (dx / dist) * force;
          delta[b].y -= (dy / dist) * force;
        }
      }

      // Attraction along edges
      edges.forEach(e => {
        const a = e.from_id, b = e.to_id;
        if (!p[a] || !p[b]) return;
        const dx = p[b].x - p[a].x, dy = p[b].y - p[a].y;
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
        const force = dist * 0.03;
        delta[a].x += (dx / dist) * force;
        delta[a].y += (dy / dist) * force;
        delta[b].x -= (dx / dist) * force;
        delta[b].y -= (dy / dist) * force;
      });

      nodes.forEach(n => {
        const id = n.entity_id;
        if (!p[id]) return;
        const damping = 0.85;
        p = { ...p, [id]: {
          x: Math.max(30, Math.min(W - 30, p[id].x + delta[id].x * damping)),
          y: Math.max(30, Math.min(H - 30, p[id].y + delta[id].y * damping)),
        }};
      });
    }
    setPositions(p);
  }, [nodes, edges]);

  return positions;
}

export default function GraphExplorer() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [detail, setDetail] = useState(null);
  const [depth, setDepth] = useState(2);
  const positions = useForceLayout(graph.nodes, graph.edges);
  const svgRef = useRef(null);
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });

  useEffect(() => {
    if (query.length < 2) { setSuggestions([]); return; }
    const t = setTimeout(() => {
      fetch(API(`/entities/suggestions?prefix=${encodeURIComponent(query)}&limit=6`))
        .then(r => r.json()).then(data => setSuggestions(Array.isArray(data) ? data : [])).catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  const loadGraph = useCallback(async (entityId) => {
    const data = await fetch(API(`/traverse/${entityId}?depth=${depth}`)).then(r => r.json()).catch(() => ({}));
    setGraph({ nodes: data.nodes || [], edges: data.edges || [] });
    setSelected(entityId);
  }, [depth]);

  const showDetail = async (entityId) => {
    const data = await fetch(API(`/entities/${entityId}`)).then(r => r.json()).catch(() => null);
    setDetail(data);
  };

  const handleSuggestionClick = (s) => {
    setQuery(s.label || s);
    setSuggestions([]);
    const id = s.entity_id || s;
    loadGraph(id);
    showDetail(id);
  };

  const zoom = (dir) => setTransform(t => ({ ...t, scale: Math.max(0.3, Math.min(2.5, t.scale + dir * 0.2)) }));

  const W = 800, H = 560;

  return (
    <ResearchLayout
      title="Graph Explorer"
      subtitle="Search an entity and explore its knowledge graph neighborhood."
    >

      <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
        <div style={{ position: "relative", flex: 1 }}>
          <Input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search entity by name…"
            prefix={<Search size={16} />}
          />
          {/* Live autocomplete suggestion list — anchored under the search input as the
              user types. Left hand-rolled: Dropdown expects a toggleable trigger button,
              not a debounced network-driven autocomplete list, so it is not a clean fit. */}
          {suggestions.length > 0 && (
            <div style={{ position: "absolute", top: "100%", left: 0, right: 0, background: WHITE, border: `1px solid ${BRD}`, borderRadius: 8, zIndex: 100, boxShadow: "0 4px 16px rgba(0,0,0,0.1)" }}>
              {suggestions.map((s, i) => (
                <div key={i} onClick={() => handleSuggestionClick(s)}
                  style={{ padding: "10px 14px", cursor: "pointer", fontSize: 13, borderBottom: i < suggestions.length - 1 ? `1px solid ${BRD}` : "none" }}
                  onMouseEnter={e => e.currentTarget.style.background = WARM}
                  onMouseLeave={e => e.currentTarget.style.background = WHITE}>
                  <span style={{ fontWeight: 500, color: NAVY }}>{typeof s === "object" ? s.label : s}</span>
                  {s.entity_type && <span style={{ marginLeft: 8, fontSize: 11, color: TEXT_SECONDARY }}>{s.entity_type}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
        <FormSelect
          value={depth}
          onChange={e => { setDepth(+e.target.value); if (selected) loadGraph(selected); }}
        >
          <option value={1}>Depth 1</option>
          <option value={2}>Depth 2</option>
          <option value={3}>Depth 3</option>
        </FormSelect>
        <Button variant="ghost" size="icon" onClick={() => zoom(1)}><ZoomIn size={16} /></Button>
        <Button variant="ghost" size="icon" onClick={() => zoom(-1)}><ZoomOut size={16} /></Button>
        <Button variant="ghost" size="icon" onClick={() => setTransform({ x: 0, y: 0, scale: 1 })}><Maximize2 size={16} /></Button>
      </div>

      <div style={{ display: "flex", gap: 16 }}>
        <Card padding="none" className="flex-1" style={{ overflow: "hidden" }}>
          {graph.nodes.length === 0 ? (
            <div style={{ height: H }}>
              <EmptyState icon={<Network />} title="Search for an entity to explore its graph neighborhood" size="lg" dashed={false} className="h-full flex flex-col items-center justify-center" />
            </div>
          ) : (
            // Force-directed graph render — untouched, this is the core visualization
            // (physics layout comes from useForceLayout above); only its wrapping
            // container was converted to Card.
            <svg width={W} height={H} style={{ display: "block" }}>
              <g transform={`translate(${transform.x},${transform.y}) scale(${transform.scale})`}>
                {graph.edges.map((e, i) => {
                  const a = positions[e.from_id], b = positions[e.to_id];
                  if (!a || !b) return null;
                  return (
                    <g key={i}>
                      <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={BRD} strokeWidth={1.5} />
                      <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2} textAnchor="middle" fontSize={9} fill={TEXT_SECONDARY}>{e.rel_type?.replace(/_/g, " ")}</text>
                    </g>
                  );
                })}
                {graph.nodes.map(n => {
                  const pos = positions[n.entity_id];
                  if (!pos) return null;
                  const color = TYPE_COLORS[n.entity_type] || TYPE_COLORS.default;
                  const isCenter = n.entity_id === selected;
                  return (
                    <g key={n.entity_id} onClick={() => showDetail(n.entity_id)} style={{ cursor: "pointer" }}>
                      <circle cx={pos.x} cy={pos.y} r={isCenter ? 18 : 12} fill={color} opacity={0.9}
                        stroke={isCenter ? NAVY : "none"} strokeWidth={isCenter ? 2 : 0} />
                      <text x={pos.x} y={pos.y + (isCenter ? 28 : 22)} textAnchor="middle" fontSize={10} fill={NAVY} fontWeight={isCenter ? 700 : 400}>
                        {(n.label || "").substring(0, 18)}
                      </text>
                    </g>
                  );
                })}
              </g>
            </svg>
          )}
        </Card>

        {detail && (
          <Card style={{ width: 280 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <Info size={16} color={ACCENT} />
              <span style={{ fontWeight: 700, color: NAVY }}>Entity Detail</span>
            </div>
            <div style={{ fontSize: 16, fontWeight: 700, color: NAVY, marginBottom: 4 }}>{detail.label}</div>
            <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginBottom: 12 }}>
              <Badge color={TYPE_COLORS[detail.entity_type] || ACCENT}>{detail.entity_type?.replace(/_/g, " ")}</Badge>
            </div>
            {detail.properties?.description && (
              <p style={{ fontSize: 12, color: TEXT_SECONDARY, lineHeight: 1.6, marginBottom: 12 }}>{detail.properties.description}</p>
            )}
            {detail.properties?.institution && (
              <div style={{ fontSize: 12, marginBottom: 6 }}><span style={{ color: TEXT_SECONDARY }}>Institution: </span>{detail.properties.institution}</div>
            )}
            {detail.properties?.country && (
              <div style={{ fontSize: 12 }}><span style={{ color: TEXT_SECONDARY }}>Country: </span>{detail.properties.country}</div>
            )}
          </Card>
        )}
      </div>
    </ResearchLayout>
  );
}
