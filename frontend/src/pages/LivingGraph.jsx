import React, { useState, useCallback } from "react";
import { AIWorkspaceLayout } from "@/layouts";
import { Network, Search, TrendingUp, Users, BookOpen, Lightbulb } from "lucide-react";
import GraphCanvas from "../components/lkg/GraphCanvas";
import NodePanel from "../components/lkg/NodePanel";
import InsightsPanel from "../components/lkg/InsightsPanel";
import { searchGraph } from "../services/lkgEngine";

const NAV_TABS = [
  { id: "explorer",   label: "Explorer",   icon: Network },
  { id: "insights",   label: "Insights",   icon: Lightbulb },
  { id: "discovery",  label: "Discovery",  icon: TrendingUp },
];

function SearchBar({ onResult }) {
  const [query,   setQuery]   = useState("");
  const [results, setResults] = useState([]);
  const [open,    setOpen]    = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSearch(e) {
    const q = e.target.value;
    setQuery(q);
    if (q.length < 2) { setResults([]); setOpen(false); return; }
    setLoading(true);
    try {
      const res = await searchGraph(q, null, 10);
      setResults(res.data?.results || []);
      setOpen(true);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative w-full max-w-sm">
      <div className="relative">
        <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          value={query}
          onChange={handleSearch}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder="Search the knowledge graph…"
          className="w-full pl-8 pr-3 py-2 text-[12px] rounded-lg border border-slate-200 bg-white placeholder-slate-400 focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-200"
        />
        {loading && (
          <div className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 border-blue-400 border-t-transparent animate-spin" />
        )}
      </div>
      {open && results.length > 0 && (
        <div className="absolute top-full mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg z-50 overflow-hidden">
          {results.map((r, i) => (
            <button
              key={i}
              onMouseDown={() => { onResult?.(r); setOpen(false); setQuery(""); }}
              className="w-full text-left px-3 py-2 hover:bg-blue-50 border-b border-slate-50 last:border-0 transition-colors"
            >
              <div className="flex items-center gap-2">
                <span
                  className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wide text-white"
                  style={{ background: { researcher: "#3B82F6", publication: "#10B981", topic: "#F59E0B", institution: "#8B5CF6" }[r.type] || "#6B7280" }}
                >
                  {r.type?.replace(/_/g, " ")}
                </span>
                <span className="text-[12px] text-slate-700 truncate">{r.label}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function DiscoveryPanel() {
  const [section, setSection] = useState("collaborators");
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(false);

  async function load(sec) {
    setSection(sec);
    setData(null);
    setLoading(true);
    try {
      const { discoverCollaborators, discoverTopics, discoverFunding } = await import("../services/lkgEngine");
      const fn = { collaborators: discoverCollaborators, topics: discoverTopics, funding: discoverFunding }[sec];
      const res = await fn();
      setData(res.data);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="px-4 py-3 border-b border-slate-100">
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Discovery Engine</p>
        <div className="flex gap-1.5">
          {[
            { id: "collaborators", icon: Users,     label: "Collaborators" },
            { id: "topics",        icon: TrendingUp, label: "Topics" },
            { id: "funding",       icon: BookOpen,   label: "Funding" },
          ].map(s => (
            <button
              key={s.id}
              onClick={() => load(s.id)}
              className={`flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium transition-colors ${
                section === s.id ? "bg-blue-100 text-blue-700" : "bg-slate-50 text-slate-600 hover:bg-slate-100"
              }`}
            >
              <s.icon size={11} />
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {!data && !loading && (
          <div className="text-center py-8 text-[11px] text-slate-400">
            Select a discovery category above
          </div>
        )}
        {loading && (
          <div className="text-center py-8 text-[11px] text-slate-400">Analyzing graph…</div>
        )}

        {/* Collaborators */}
        {!loading && data && section === "collaborators" && (
          <>
            <p className="text-[10px] text-slate-400 mb-3">{data.status_note}</p>
            {(data.discoveries || []).length === 0 && (
              <p className="text-[11px] text-slate-400 text-center py-4">No potential collaborators found yet</p>
            )}
            {(data.discoveries || []).slice(0, 8).map((d, i) => (
              <div key={i} className="p-3 rounded-lg border border-slate-100 mb-2">
                <p className="text-[12px] font-medium text-slate-700">{d.other_researcher?.label || "Unknown researcher"}</p>
                {d.via_collaborator && (
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    via {d.via_collaborator.label}
                  </p>
                )}
                <p className="text-[10px] text-amber-600 mt-1">Inferred — not a confirmed connection</p>
              </div>
            ))}
          </>
        )}

        {/* Emerging Topics */}
        {!loading && data && section === "topics" && (
          <>
            {(data.emerging_topics || []).length === 0 && (
              <p className="text-[11px] text-slate-400 text-center py-4">No topic trend data yet</p>
            )}
            {(data.emerging_topics || []).slice(0, 10).map((t, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-slate-50 last:border-0">
                <span className="text-[12px] text-slate-700">{t.label || t.topic_id}</span>
                <div className="flex gap-2 items-center">
                  <span className="text-[10px] text-slate-400">{t.total} links</span>
                  {t.growth_rate > 0 && (
                    <span className="text-[10px] font-medium text-emerald-600">
                      +{(t.growth_rate * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              </div>
            ))}
          </>
        )}

        {/* Funding */}
        {!loading && data && section === "funding" && (
          <>
            {data.message && (
              <p className="text-[11px] text-slate-500 text-center py-4">{data.message}</p>
            )}
            {(data.opportunities || []).map((o, i) => (
              <div key={i} className="p-3 rounded-lg border border-slate-100 mb-2">
                <p className="text-[12px] font-medium text-slate-700">{o.label}</p>
                {o.metadata?.funder && <p className="text-[10px] text-slate-400">{o.metadata.funder}</p>}
                {o.metadata?.deadline && <p className="text-[10px] text-orange-500">Deadline: {o.metadata.deadline}</p>}
              </div>
            ))}
            {data.source && (
              <p className="text-[9px] text-slate-400 mt-3">{data.source}</p>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default function LivingGraph() {
  const [activeTab,     setActiveTab]     = useState("explorer");
  const [selectedNode,  setSelectedNode]  = useState(null);
  const [rootNodeId,    setRootNodeId]    = useState(null);

  const handleNodeSelect = useCallback((node) => setSelectedNode(node), []);
  const handleSearchResult = useCallback((node) => {
    setRootNodeId(node.node_id);
    setSelectedNode(node);
    setActiveTab("explorer");
  }, []);

  return (
    <AIWorkspaceLayout
      title="Living Knowledge Graph"
      subtitle="Explore your academic knowledge network and discover connections"
      actions={<SearchBar onResult={handleSearchResult} />}
    >
      <div className="flex gap-2 mb-4 flex-wrap">
        {NAV_TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-medium transition-colors ${
              activeTab === t.id
                ? "bg-blue-100 text-blue-700"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <t.icon size={12} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden" style={{ margin: "-24px", marginTop: 0, height: "calc(100vh - 200px)" }}>
        {/* Left: Insights panel (always visible on explorer) */}
        {activeTab === "insights" && (
          <div className="w-80 flex-shrink-0 overflow-hidden border-r border-slate-200">
            <InsightsPanel />
          </div>
        )}

        {/* Center: Graph canvas or Discovery */}
        <div className="flex-1 overflow-hidden relative">
          {activeTab === "explorer" && (
            <GraphCanvas
              rootNodeId={rootNodeId}
              selectedNodeId={selectedNode?.node_id}
              onNodeSelect={handleNodeSelect}
            />
          )}
          {activeTab === "insights" && (
            <div className="flex items-center justify-center h-full text-[12px] text-slate-400">
              Select a tab on the left panel to explore insights
            </div>
          )}
          {activeTab === "discovery" && (
            <div className="h-full overflow-hidden">
              <DiscoveryPanel />
            </div>
          )}
        </div>

        {/* Right: Node detail panel (explorer only) */}
        {activeTab === "explorer" && selectedNode && (
          <NodePanel
            node={selectedNode}
            onClose={() => setSelectedNode(null)}
            onNavigate={(nodeId) => {
              setRootNodeId(nodeId);
              setSelectedNode(null);
            }}
          />
        )}
      </div>
    </AIWorkspaceLayout>
  );
}
