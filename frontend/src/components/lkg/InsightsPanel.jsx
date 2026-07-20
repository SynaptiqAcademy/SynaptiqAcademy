import React, { useState, useEffect } from "react";
import { Brain, TrendingUp, RefreshCw, AlertCircle, Database } from "lucide-react";
import { getMyInsights, getPlatformInsights, discoverTopics } from "../../services/lkgEngine";

function InsightCard({ insight }) {
  return (
    <div className="p-3 rounded-lg border border-slate-100 hover:border-blue-100 hover:bg-blue-50/20 transition-colors">
      <p className="text-[12px] text-slate-700 leading-snug">{insight.text}</p>
      <p className="text-[10px] text-slate-400 mt-1">{insight.source || "Synaptiq LKG"}</p>
    </div>
  );
}

function EmergingTopicRow({ topic }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-slate-50 last:border-0">
      <span className="text-[12px] text-slate-700 truncate">{topic.label || topic.topic_id}</span>
      <div className="flex items-center gap-2 flex-shrink-0">
        <span className="text-[10px] text-slate-400">{topic.total} links</span>
        {topic.growth_rate > 0 && (
          <span className="text-[10px] text-emerald-600 font-medium">+{(topic.growth_rate * 100).toFixed(0)}%</span>
        )}
      </div>
    </div>
  );
}

export default function InsightsPanel() {
  const [myInsights,     setMyInsights]     = useState(null);
  const [platformData,   setPlatformData]   = useState(null);
  const [emergingTopics, setEmergingTopics] = useState([]);
  const [loading,        setLoading]        = useState(false);
  const [error,          setError]          = useState(null);
  const [tab,            setTab]            = useState("personal");

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [myRes, platRes, topicRes] = await Promise.all([
        getMyInsights().catch(() => null),
        getPlatformInsights().catch(() => null),
        discoverTopics().catch(() => null),
      ]);
      setMyInsights(myRes?.data || null);
      setPlatformData(platRes?.data || null);
      setEmergingTopics(topicRes?.data?.emerging_topics || []);
    } catch (err) {
      setError("Failed to load graph insights");
    } finally {
      setLoading(false);
    }
  }

  const insights = tab === "personal"
    ? (myInsights?.insights || [])
    : [];

  return (
    <div className="flex flex-col h-full bg-white border-r border-slate-200">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <Brain size={14} className="text-blue-600" />
          <span className="text-[12px] font-bold text-slate-700 uppercase tracking-widest">Graph Insights</span>
        </div>
        <button onClick={load} disabled={loading}
          className="p-1 text-slate-400 hover:text-slate-600 transition-colors">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-100">
        {[{ id: "personal", label: "My Network" }, { id: "platform", label: "Platform" }].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 py-2 text-[11px] font-medium transition-colors ${
              tab === t.id
                ? "text-blue-600 border-b-2 border-blue-600"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {loading && (
          <div className="text-center py-8 text-[11px] text-slate-400">Analyzing graph…</div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 rounded-lg border border-red-100">
            <AlertCircle size={13} className="text-red-400 flex-shrink-0" />
            <p className="text-[11px] text-red-600">{error}</p>
          </div>
        )}

        {/* Personal tab */}
        {!loading && !error && tab === "personal" && (
          <>
            {insights.length === 0 && myInsights && (
              <div className="text-center py-6 text-[11px] text-slate-400">
                {myInsights.insights?.[0]?.text || "No insights yet. Complete your profile to appear in the graph."}
              </div>
            )}
            {insights.map((ins, i) => <InsightCard key={i} insight={ins} />)}
            {myInsights?.evidence?.length > 0 && (
              <div className="mt-2 pt-3 border-t border-slate-100">
                <div className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5">
                  <Database size={9} />
                  Evidence sources
                </div>
                {myInsights.evidence.map((ev, i) => (
                  <p key={i} className="text-[10px] text-slate-500 mb-0.5">• {ev}</p>
                ))}
                <p className="text-[9px] text-slate-400 italic mt-1">{myInsights.policy_note}</p>
              </div>
            )}
          </>
        )}

        {/* Platform tab */}
        {!loading && !error && tab === "platform" && (
          <>
            {/* Graph size */}
            {platformData?.graph_size && (
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Graph Size</p>
                <div className="flex gap-4">
                  <div>
                    <p className="text-lg font-bold text-slate-800">{(platformData.graph_size.nodes || 0).toLocaleString()}</p>
                    <p className="text-[10px] text-slate-400">nodes</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold text-slate-800">{(platformData.graph_size.edges || 0).toLocaleString()}</p>
                    <p className="text-[10px] text-slate-400">edges</p>
                  </div>
                </div>
              </div>
            )}

            {/* Emerging topics */}
            {emergingTopics.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 mb-2">
                  <TrendingUp size={11} className="text-emerald-500" />
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Emerging Topics</p>
                </div>
                {emergingTopics.slice(0, 8).map((t, i) => <EmergingTopicRow key={i} topic={t} />)}
              </div>
            )}

            {/* Collab density */}
            {platformData?.collaboration && (
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Collaboration</p>
                <p className="text-sm font-semibold text-slate-700">{platformData.collaboration.interpretation}</p>
                <p className="text-[10px] text-slate-400 mt-0.5">
                  {(platformData.collaboration.collaboration_edges || 0)} edges across {(platformData.collaboration.researcher_nodes || 0)} researchers
                </p>
                <p className="text-[9px] text-slate-400 italic mt-1">{platformData.collaboration.source}</p>
              </div>
            )}

            <p className="text-[9px] text-slate-400 text-center">All figures from Synaptiq LKG database queries</p>
          </>
        )}
      </div>
    </div>
  );
}
