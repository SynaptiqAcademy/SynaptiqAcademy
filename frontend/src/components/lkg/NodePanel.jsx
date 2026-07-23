import React, { useState, useEffect, useCallback } from "react";
import { X, ExternalLink, Clock, GitBranch, Layers } from "lucide-react";
import { getNodeEdges, getNodeTimeline } from "../../services/lkgEngine";

const TYPE_COLOR = {
  researcher: "#3B82F6",
  publication: "#10B981",
  institution: "#8B5CF6",
  topic: "#F59E0B",
  journal: "#EF4444",
  project: "#14B8A6",
  manuscript: "#6366F1",
  funding_program: "#F97316",
  dataset: "#06B6D4",
  conference: "#EC4899",
  lesson: "#84CC16",
  default: "#6B7280",
};

const STATUS_BADGE = {
  verified:  { color: "#047857", bg: "#F0FDF4", label: "Verified" },
  inferred:  { color: "#B45309", bg: "#FFFBEB", label: "Inferred" },
  predicted: { color: "#6B7280", bg: "#F9FAFB", label: "Predicted" },
};

function Badge({ status }) {
  const s = STATUS_BADGE[status] || STATUS_BADGE.verified;
  return (
    <span
      className="text-[10px] px-1.5 py-0.5 rounded font-semibold"
      style={{ color: s.color, background: s.bg }}
    >
      {s.label}
    </span>
  );
}

export default function NodePanel({ node, onClose, onNavigate }) {
  const [edges, setEdges]       = useState([]);
  const [timeline, setTimeline] = useState(null);
  const [tab, setTab]           = useState("edges");
  const [loading, setLoading]   = useState(false);

  const loadEdges = useCallback(async () => {
    if (!node) return;
    setLoading(true);
    try {
      const res = await getNodeEdges(node.node_id, "both");
      setEdges(res.data?.edges || []);
    } catch {
      setEdges([]);
    } finally {
      setLoading(false);
    }
  }, [node]);

  const loadTimeline = useCallback(async () => {
    if (!node || timeline) return;
    setLoading(true);
    try {
      const res = await getNodeTimeline(node.node_id);
      setTimeline(res.data);
    } catch {
      setTimeline({ timeline: [] });
    } finally {
      setLoading(false);
    }
  }, [node, timeline]);

  useEffect(() => {
    if (!node) return;
    setEdges([]);
    setTimeline(null);
    setTab("edges");
    loadEdges();
  }, [node, loadEdges]);

  if (!node) return null;

  const color = TYPE_COLOR[node.type] || TYPE_COLOR.default;
  const meta  = node.metadata || {};

  return (
    <aside className="flex flex-col h-full w-80 bg-white border-l border-slate-200 shadow-xl z-20 overflow-hidden">
      {/* Header */}
      <div className="flex items-start gap-3 p-4 border-b border-slate-100" style={{ borderLeftColor: color, borderLeftWidth: 4 }}>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span
              className="text-[10px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-widest"
              style={{ color, background: `${color}18` }}
            >
              {node.type?.replace(/_/g, " ")}
            </span>
            <Badge status={node.confidence === "high" ? "verified" : "inferred"} />
          </div>
          <h2 className="font-semibold text-slate-800 text-sm leading-snug line-clamp-3">{node.label}</h2>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 mt-0.5 flex-shrink-0">
          <X size={16} />
        </button>
      </div>

      {/* Metadata */}
      <div className="px-4 py-3 border-b border-slate-100 space-y-1">
        {meta.institution && (
          <p className="text-[11px] text-slate-500">
            <span className="font-medium text-slate-600">Institution: </span>{meta.institution}
          </p>
        )}
        {meta.orcid && (
          <p className="text-[11px] text-slate-500">
            <span className="font-medium text-slate-600">ORCID: </span>
            <a href={`https://orcid.org/${meta.orcid}`} target="_blank" rel="noreferrer"
              className="text-blue-600 hover:underline inline-flex items-center gap-0.5">
              {meta.orcid} <ExternalLink size={9} />
            </a>
          </p>
        )}
        {meta.doi && (
          <p className="text-[11px] text-slate-500">
            <span className="font-medium text-slate-600">DOI: </span>
            <a href={`https://doi.org/${meta.doi}`} target="_blank" rel="noreferrer"
              className="text-blue-600 hover:underline inline-flex items-center gap-0.5">
              {meta.doi} <ExternalLink size={9} />
            </a>
          </p>
        )}
        {meta.year && (
          <p className="text-[11px] text-slate-500">
            <span className="font-medium text-slate-600">Year: </span>{meta.year}
          </p>
        )}
        {meta.status && (
          <p className="text-[11px] text-slate-500">
            <span className="font-medium text-slate-600">Status: </span>{meta.status}
          </p>
        )}
        <p className="text-[10px] text-slate-400 mt-1">
          Source: {node.source || "Synaptiq platform"}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-100">
        {[
          { id: "edges",    icon: GitBranch, label: "Connections" },
          { id: "timeline", icon: Clock,     label: "Timeline" },
          { id: "explore",  icon: Layers,    label: "Explore" },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => { setTab(t.id); if (t.id === "timeline") loadTimeline(); }}
            className={`flex-1 flex items-center justify-center gap-1 py-2.5 text-[11px] font-medium transition-colors ${
              tab === t.id
                ? "text-blue-600 border-b-2 border-blue-600 bg-blue-50/50"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            <t.icon size={11} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="p-4 text-center text-[11px] text-slate-400">Loading…</div>
        )}

        {/* Edges tab */}
        {!loading && tab === "edges" && (
          <div className="p-3 space-y-1.5">
            {edges.length === 0 && (
              <p className="text-[11px] text-slate-400 text-center py-6">No connections recorded yet</p>
            )}
            {edges.map((e, i) => {
              const other = e.from_id === node.node_id ? e.to_id : e.from_id;
              const dir   = e.from_id === node.node_id ? "→" : "←";
              return (
                <button
                  key={i}
                  onClick={() => onNavigate?.(other)}
                  className="w-full text-left p-2 rounded-md border border-slate-100 hover:border-blue-200 hover:bg-blue-50/30 transition-colors"
                >
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="text-[10px] font-bold text-blue-600 uppercase tracking-widest">{e.type}</span>
                    <span className="text-[10px] text-slate-400">{dir}</span>
                  </div>
                  <p className="text-[11px] text-slate-600 truncate">{other}</p>
                  <Badge status={e.status || "verified"} />
                </button>
              );
            })}
          </div>
        )}

        {/* Timeline tab */}
        {!loading && tab === "timeline" && (
          <div className="p-3">
            {(!timeline || !timeline.timeline?.length) && (
              <p className="text-[11px] text-slate-400 text-center py-6">No timeline events</p>
            )}
            {timeline?.timeline?.map((yr, i) => (
              <div key={i} className="mb-4">
                <div className="text-[11px] font-bold text-slate-500 mb-1.5">{yr.year}</div>
                {yr.events?.slice(0, 5).map((ev, j) => (
                  <div key={j} className="pl-3 border-l-2 border-slate-200 mb-1.5">
                    <p className="text-[11px] font-medium text-slate-700">{ev.type}</p>
                    <p className="text-[10px] text-slate-400 truncate">{ev.other_node}</p>
                  </div>
                ))}
                {yr.events?.length > 5 && (
                  <p className="text-[10px] text-slate-400 pl-3">+{yr.events.length - 5} more</p>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Explore tab */}
        {!loading && tab === "explore" && (
          <div className="p-3 space-y-2">
            <button
              onClick={() => onNavigate?.(node.node_id)}
              className="w-full text-left p-3 rounded-md bg-blue-50 hover:bg-blue-100 transition-colors"
            >
              <p className="text-[11px] font-semibold text-blue-700">Expand in graph</p>
              <p className="text-[10px] text-blue-500">Load 2-degree subgraph around this node</p>
            </button>
            <div className="text-[10px] text-slate-400 p-2">
              Node ID: <span className="font-mono break-all">{node.node_id}</span>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
