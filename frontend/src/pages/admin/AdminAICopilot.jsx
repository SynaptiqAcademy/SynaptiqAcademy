import React, { useState, useCallback, useEffect, useRef } from "react";
import { RefreshCw, Send, Cpu, FileText, ChevronDown, ChevronRight } from "lucide-react";
import api from "@/lib/api";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

function useX(path, params = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const query = new URLSearchParams(params).toString();
  const load = useCallback(() => {
    setLoading(true);
    api.get(`/admin/x/${path}${query ? "?" + query : ""}`)
      .then(r => setData(r.data)).catch(() => setData(null)).finally(() => setLoading(false));
  }, [path, query]);
  useEffect(() => { load(); }, [load]);
  return { data, loading, refetch: load };
}

function BriefingRow({ brief, onView }) {
  return (
    <tr className="border-t border-[#1a3050] hover:bg-[#1a3050]/30 cursor-pointer" onClick={() => onView(brief)}>
      <td className="px-3 py-2">
        <span className={`text-[10px] px-2 py-0.5 border ${
          brief.kind === "daily" ? "text-blue-400 border-blue-700"
          : brief.kind === "weekly" ? "text-purple-400 border-purple-700"
          : brief.kind === "monthly" ? "text-green-400 border-green-700"
          : "text-slate-400 border-slate-700"
        }`}>{brief.kind?.toUpperCase()}</span>
      </td>
      <td className="px-3 py-2 text-xs text-slate-300">{(brief.created_at || "").slice(0, 16).replace("T", " ")}</td>
      <td className="px-3 py-2 text-xs text-slate-500">{brief.generated_by || "—"}</td>
      <td className="px-3 py-2"><ChevronRight size={12} className="text-slate-500" /></td>
    </tr>
  );
}

function BriefingModal({ brief, onClose }) {
  return (
    <div className="fixed inset-0 bg-black/70 flex items-start justify-center z-50 p-4 pt-12 overflow-y-auto">
      <div className="bg-[#0B1C35] border border-[#1a3050] w-full max-w-2xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1a3050]">
          <div className="flex items-center gap-2">
            <Cpu size={16} className="text-blue-400" />
            <span className="text-sm font-semibold text-white capitalize">{brief.kind} Briefing</span>
            <span className="text-xs text-slate-500">{(brief.created_at || "").slice(0, 10)}</span>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl">×</button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <div className="text-[10px] text-slate-500 font-medium mb-2">AI NARRATIVE</div>
            <div className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed bg-[#080f1f] border border-[#1a3050] p-4">
              {brief.briefing}
            </div>
          </div>
          {brief.context && (
            <details>
              <summary className="text-[10px] text-slate-500 cursor-pointer hover:text-slate-300">Show Platform Context Used</summary>
              <div className="mt-2 text-[10px] text-slate-400 font-mono whitespace-pre bg-[#080f1f] border border-[#1a3050] p-3 overflow-x-auto">
                {brief.context}
              </div>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}

export default function AdminAICopilot() {
  const { data: briefings, loading: bL, refetch: refBriefings } = useX("copilot/briefings", { limit: 20 });
  const [generating, setGenerating] = useState(false);
  const [genKind, setGenKind] = useState("daily");
  const [genResult, setGenResult] = useState(null);
  const [viewBrief, setViewBrief] = useState(null);

  // Chat
  const [messages, setMessages] = useState([]);
  const [inputVal, setInputVal] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatRef = useRef(null);

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [messages]);

  const generateBrief = async () => {
    setGenerating(true); setGenResult(null);
    try {
      const r = await api.post(`/admin/x/copilot/brief?kind=${genKind}`);
      setGenResult(r.data);
      refBriefings();
    } catch (e) {
      setGenResult({ briefing: e?.response?.data?.detail || "Generation failed", kind: genKind });
    } finally { setGenerating(false); }
  };

  const sendMessage = async () => {
    if (!inputVal.trim() || chatLoading) return;
    const question = inputVal.trim();
    setInputVal("");
    setMessages(prev => [...prev, { role: "user", content: question }]);
    setChatLoading(true);
    try {
      const r = await api.post("/admin/x/copilot/query", { message: question, kind: "query" });
      setMessages(prev => [...prev, { role: "assistant", content: r.data.answer }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: "assistant", content: "Error: " + (e?.response?.data?.detail || "Request failed") }]);
    } finally { setChatLoading(false); }
  };

  const items = briefings?.items || [];

  return (
    <AdministrationLayout
      title="Executive AI Copilot"
      subtitle="Anthropic-powered daily briefings, reports, and AI platform assistant"
      actions={
        <button onClick={refBriefings} className="p-1.5 bg-[#0F2847] border border-[#1a3050] text-slate-400 hover:text-white">
          <RefreshCw size={14} className={bL ? "animate-spin" : ""} />
        </button>
      }
    >

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Generate briefing */}
        <div className="space-y-4">
          <div className="bg-[#0F2847] border border-[#1a3050] p-5">
            <div className="flex items-center gap-2 mb-4">
              <Cpu size={16} className="text-blue-400" />
              <span className="text-sm font-semibold text-white">Generate AI Briefing</span>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-[10px] text-slate-500 mb-1">Briefing Type</label>
                <select value={genKind} onChange={e => setGenKind(e.target.value)}
                  className="w-full text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 px-2 py-1.5">
                  <option value="daily">Daily Briefing</option>
                  <option value="weekly">Weekly Summary</option>
                  <option value="monthly">Monthly Executive Report</option>
                </select>
              </div>
              <button onClick={generateBrief} disabled={generating}
                className="w-full flex items-center justify-center gap-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white py-2">
                <Cpu size={14} className={generating ? "animate-pulse" : ""} />
                {generating ? "Generating with Claude AI..." : `Generate ${genKind} briefing`}
              </button>
            </div>
          </div>

          {genResult && (
            <div className="bg-[#0F2847] border border-blue-700/40 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Cpu size={12} className="text-blue-400" />
                <span className="text-xs font-semibold text-blue-400 uppercase">{genResult.kind} Briefing — Generated</span>
              </div>
              <div className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed max-h-64 overflow-y-auto">
                {genResult.briefing}
              </div>
            </div>
          )}

          {/* Past briefings */}
          <div className="bg-[#0F2847] border border-[#1a3050]">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-[#1a3050]">
              <FileText size={13} className="text-slate-400" />
              <span className="text-sm font-semibold text-white">Past Briefings</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-slate-300">
                <thead className="text-slate-500 border-b border-[#1a3050]">
                  <tr>
                    <th className="text-left px-3 py-2 font-medium">Kind</th>
                    <th className="text-left px-3 py-2 font-medium">Generated</th>
                    <th className="text-left px-3 py-2 font-medium">By</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {bL && <tr><td colSpan={4} className="px-3 py-4 text-center text-slate-500">Loading...</td></tr>}
                  {!bL && items.map(b => <BriefingRow key={b.id} brief={b} onView={setViewBrief} />)}
                  {!bL && items.length === 0 && (
                    <tr><td colSpan={4} className="px-3 py-6 text-center text-slate-500">No briefings yet — generate your first one</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* AI Chat */}
        <div className="bg-[#0F2847] border border-[#1a3050] flex flex-col" style={{ minHeight: 480 }}>
          <div className="flex items-center gap-2 px-4 py-3 border-b border-[#1a3050]">
            <Cpu size={14} className="text-blue-400" />
            <span className="text-sm font-semibold text-white">Ask the Platform AI</span>
            <span className="text-[10px] text-slate-500">Powered by Claude</span>
          </div>

          {/* Messages */}
          <div ref={chatRef} className="flex-1 overflow-y-auto p-4 space-y-3" style={{ maxHeight: 320 }}>
            {messages.length === 0 && (
              <div className="text-xs text-slate-500 text-center py-8">
                Ask anything about the platform — growth trends, at-risk users, infrastructure, revenue...
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`text-xs ${m.role === "user" ? "text-right" : "text-left"}`}>
                <div className={`inline-block max-w-[80%] p-3 ${
                  m.role === "user"
                    ? "bg-blue-600/20 border border-blue-700/40 text-blue-200"
                    : "bg-[#0B1C35] border border-[#1a3050] text-slate-300"
                }`}>
                  <div className="whitespace-pre-wrap">{m.content}</div>
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="text-left">
                <div className="inline-block bg-[#0B1C35] border border-[#1a3050] p-3 text-xs text-slate-400">
                  <span className="animate-pulse">Claude is thinking...</span>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="p-3 border-t border-[#1a3050]">
            <div className="flex gap-2">
              <input
                value={inputVal}
                onChange={e => setInputVal(e.target.value)}
                onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendMessage()}
                placeholder="Ask about platform health, users, revenue..."
                className="flex-1 text-xs bg-[#0B1C35] border border-[#1a3050] text-slate-300 placeholder-slate-600 px-3 py-2"
              />
              <button onClick={sendMessage} disabled={chatLoading || !inputVal.trim()}
                className="px-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white">
                <Send size={13} />
              </button>
            </div>
            <div className="text-[10px] text-slate-600 mt-1.5">Press Enter to send • Queries are saved to briefing history</div>
          </div>
        </div>
      </div>

      {viewBrief && <BriefingModal brief={viewBrief} onClose={() => setViewBrief(null)} />}
    </AdministrationLayout>
  );
}
