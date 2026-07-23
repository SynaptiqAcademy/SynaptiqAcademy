/**
 * Force-directed graph explorer — canvas-based, no external graph library.
 * Uses a simple spring-repulsion simulation (Hooke + Coulomb approximation).
 * Renders nodes as circles, edges as lines, labels on hover / selected.
 */
import React, { useRef, useEffect, useCallback, useState } from "react";
import { getSubgraph, getMySubgraph } from "../../services/lkgEngine";

const NODE_COLORS = {
  researcher:       "#3B82F6",
  publication:      "#10B981",
  institution:      "#8B5CF6",
  topic:            "#F59E0B",
  journal:          "#EF4444",
  project:          "#14B8A6",
  manuscript:       "#6366F1",
  funding_program:  "#F97316",
  dataset:          "#06B6D4",
  conference:       "#EC4899",
  lesson:           "#84CC16",
  default:          "#6B7280",
};

const NODE_RADIUS = {
  researcher:  14,
  publication: 11,
  institution: 16,
  topic:       9,
  default:     10,
};

// ── Simulation ─────────────────────────────────────────────────────────────

function buildSimulation(nodes, edges) {
  const nodeMap = Object.fromEntries(nodes.map(n => [n.node_id, n]));
  const positions = {};
  nodes.forEach((n, i) => {
    const angle = (i / nodes.length) * 2 * Math.PI;
    const r = 120 + Math.random() * 80;
    positions[n.node_id] = { x: 300 + r * Math.cos(angle), y: 300 + r * Math.sin(angle), vx: 0, vy: 0 };
  });

  function tick(alpha = 0.3) {
    const k  = 60;   // ideal spring length
    const kc = 3000; // repulsion constant

    // Repulsion
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = positions[nodes[i].node_id];
        const b = positions[nodes[j].node_id];
        const dx = b.x - a.x || 0.01;
        const dy = b.y - a.y || 0.01;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = kc / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        a.vx -= fx; a.vy -= fy;
        b.vx += fx; b.vy += fy;
      }
    }

    // Attraction (spring)
    edges.forEach(e => {
      const a = positions[e.from_id];
      const b = positions[e.to_id];
      if (!a || !b) return;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = (dist - k) * 0.03;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      a.vx += fx; a.vy += fy;
      b.vx -= fx; b.vy -= fy;
    });

    // Gravity toward center
    nodes.forEach(n => {
      const p = positions[n.node_id];
      p.vx += (300 - p.x) * 0.005;
      p.vy += (300 - p.y) * 0.005;
      // Damping
      p.vx *= 0.8;
      p.vy *= 0.8;
      p.x  += p.vx * alpha;
      p.y  += p.vy * alpha;
    });

    return positions;
  }

  return { positions, tick };
}

// ── Component ──────────────────────────────────────────────────────────────

export default function GraphCanvas({ rootNodeId, onNodeSelect, selectedNodeId }) {
  const canvasRef   = useRef(null);
  const simRef      = useRef(null);
  const rafRef      = useRef(null);
  const offsetRef   = useRef({ x: 0, y: 0, scale: 1 });
  const dragRef     = useRef(null);
  const [graphData, setGraphData]   = useState({ nodes: [], edges: [] });
  const [loading,   setLoading]     = useState(false);
  const [hovered,   setHovered]     = useState(null);

  // Load subgraph
  useEffect(() => {
    setLoading(true);
    const fn = rootNodeId
      ? () => getSubgraph(rootNodeId, 2)
      : () => getMySubgraph(2);

    fn()
      .then(res => {
        const data = res.data || {};
        setGraphData({ nodes: data.nodes || [], edges: data.edges || [] });
      })
      .catch(() => setGraphData({ nodes: [], edges: [] }))
      .finally(() => setLoading(false));
  }, [rootNodeId]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !simRef.current) return;
    const ctx  = canvas.getContext("2d");
    const pos  = simRef.current.positions;
    const { x: ox, y: oy, scale } = offsetRef.current;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.translate(ox, oy);
    ctx.scale(scale, scale);

    // Draw edges
    graphData.edges.forEach(e => {
      const a = pos[e.from_id];
      const b = pos[e.to_id];
      if (!a || !b) return;
      const isInferred = e.status === "inferred";
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = isInferred ? "#CBD5E1" : "#94A3B8";
      ctx.lineWidth   = isInferred ? 0.5 : 1;
      ctx.setLineDash(isInferred ? [3, 3] : []);
      ctx.stroke();
      ctx.setLineDash([]);
    });

    // Draw nodes
    graphData.nodes.forEach(n => {
      const p = pos[n.node_id];
      if (!p) return;
      const r     = (NODE_RADIUS[n.type] || NODE_RADIUS.default);
      const color = NODE_COLORS[n.type] || NODE_COLORS.default;
      const isSel = n.node_id === selectedNodeId;
      const isHov = n.node_id === hovered;

      // Glow for selected
      if (isSel) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, r + 4, 0, 2 * Math.PI);
        ctx.fillStyle = `${color}33`;
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, 2 * Math.PI);
      ctx.fillStyle   = isSel ? color : isHov ? `${color}CC` : `${color}99`;
      ctx.strokeStyle = color;
      ctx.lineWidth   = isSel || isHov ? 2 : 1;
      ctx.fill();
      ctx.stroke();

      // Label on hover or selection
      if (isHov || isSel) {
        const label = (n.label || n.node_id).substring(0, 30);
        ctx.font      = `bold ${isSel ? 10 : 9}px -apple-system, sans-serif`;
        ctx.fillStyle = "#1E293B";
        const tw = ctx.measureText(label).width;
        ctx.fillStyle = "rgba(255,255,255,0.9)";
        ctx.fillRect(p.x + r + 2, p.y - 8, tw + 6, 14);
        ctx.fillStyle = "#1E293B";
        ctx.fillText(label, p.x + r + 5, p.y + 2);
      }
    });

    ctx.restore();
  }, [graphData, selectedNodeId, hovered]);

  // Build simulation when data changes
  useEffect(() => {
    if (!graphData.nodes.length) return;
    simRef.current = buildSimulation(graphData.nodes, graphData.edges);

    let ticks = 0;
    function animate() {
      if (!simRef.current) return;
      simRef.current.tick(ticks < 80 ? 0.4 : 0.1);
      ticks++;
      draw();
      rafRef.current = requestAnimationFrame(animate);
    }
    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, [graphData, draw]);

  // Mouse handlers
  function getNodeAt(canvasX, canvasY) {
    const { x: ox, y: oy, scale } = offsetRef.current;
    const wx = (canvasX - ox) / scale;
    const wy = (canvasY - oy) / scale;
    const pos = simRef.current?.positions || {};
    for (const n of graphData.nodes) {
      const p = pos[n.node_id];
      if (!p) continue;
      const r = NODE_RADIUS[n.type] || NODE_RADIUS.default;
      if (Math.sqrt((wx - p.x) ** 2 + (wy - p.y) ** 2) <= r + 2) return n;
    }
    return null;
  }

  function onMouseMove(e) {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const node = getNodeAt(e.clientX - rect.left, e.clientY - rect.top);
    setHovered(node?.node_id || null);
    if (dragRef.current) {
      offsetRef.current.x += e.movementX;
      offsetRef.current.y += e.movementY;
    }
  }

  function onClick(e) {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const node = getNodeAt(e.clientX - rect.left, e.clientY - rect.top);
    if (node) onNodeSelect?.(node);
  }

  function onWheel(e) {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    offsetRef.current.scale = Math.min(3, Math.max(0.2, offsetRef.current.scale * factor));
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-[12px] text-slate-400">
        Loading knowledge graph…
      </div>
    );
  }

  if (!graphData.nodes.length) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3">
        <p className="text-[13px] text-slate-500 font-medium">No graph data yet</p>
        <p className="text-[11px] text-slate-400 text-center max-w-xs">
          Complete your profile and run ORCID sync to appear in the Living Knowledge Graph.
          An admin can also trigger platform ingestion from the admin panel.
        </p>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full select-none">
      <canvas
        ref={canvasRef}
        width={900}
        height={600}
        className="w-full h-full cursor-grab active:cursor-grabbing"
        onMouseMove={onMouseMove}
        onMouseDown={() => { dragRef.current = true; }}
        onMouseUp={()   => { dragRef.current = false; }}
        onMouseLeave={() => { dragRef.current = false; setHovered(null); }}
        onClick={onClick}
        onWheel={onWheel}
      />
      {/* Legend */}
      <div className="absolute bottom-3 left-3 bg-white/90 backdrop-blur-sm border border-slate-200 rounded-lg p-2 shadow-sm">
        <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Node types</p>
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
          {Object.entries(NODE_COLORS).filter(([k]) => k !== "default").slice(0, 8).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
              <span className="text-[9px] text-slate-500">{type.replace(/_/g, " ")}</span>
            </div>
          ))}
        </div>
      </div>
      {/* Node count */}
      <div className="absolute top-3 right-3 bg-white/90 backdrop-blur-sm border border-slate-200 rounded-md px-2 py-1 text-[10px] text-slate-500">
        {graphData.nodes.length} nodes · {graphData.edges.length} edges
      </div>
    </div>
  );
}
