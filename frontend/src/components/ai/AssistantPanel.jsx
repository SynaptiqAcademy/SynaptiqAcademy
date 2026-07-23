/**
 * AssistantPanel — embeddable Research Copilot drawer.
 *
 * Slides in from the right edge with a chat thread, quick-action chips, and
 * credit-aware send button. Used inside WorkspaceDetail, ProjectDetail, and
 * ManuscriptDetail. Powered by /api/assistant/*.
 *
 * Props:
 *   open, onClose
 *   entityKind: "workspace" | "project" | "manuscript"
 *   entityId
 *   entityTitle (string for header)
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import api from "../../lib/api";
import { toast } from "sonner";
import { useAuth } from "../../contexts/AuthContext";
import { NAVY } from "@/lib/tokens";
import {
  Sparkles, X, Send, Loader2, Trash2, History, Plus,
  BookOpen, Lightbulb, Beaker, HelpCircle, Pencil, BadgeCheck,
  CalendarDays, Coins, MessageSquareReply,
} from "lucide-react";

const ASSISTANT_COST = 2;

const QUICK_ACTIONS_BY_KIND = {
  workspace: [
    { cap: "literature_synthesis",      label: "Summarize Literature",      icon: BookOpen, prompt: "Summarize the most relevant literature themes for this workspace’s research scope." },
    { cap: "research_question_generation", label: "Identify Research Gaps", icon: Lightbulb, prompt: "Based on the workspace context, identify 3-5 open research gaps and explain why they matter." },
    { cap: "methodology_assistance",    label: "Suggest Methodology",       icon: Beaker, prompt: "Propose a rigorous methodology covering data, instruments, analysis, and validity threats." },
    { cap: "research_question_generation", label: "Generate Research Questions", icon: HelpCircle, prompt: "Generate 3-5 sharp research questions aligned with the workspace context." },
  ],
  project: [
    { cap: "literature_synthesis",      label: "Summarize Literature",      icon: BookOpen, prompt: "Synthesize the most relevant literature for this project." },
    { cap: "research_question_generation", label: "Identify Research Gaps", icon: Lightbulb, prompt: "Identify 3-5 unanswered questions in this domain." },
    { cap: "methodology_assistance",    label: "Suggest Methodology",       icon: Beaker, prompt: "Propose a methodology with measurable steps for this project." },
    { cap: "research_question_generation", label: "Generate Research Questions", icon: HelpCircle, prompt: "Generate 3-5 research questions for this project." },
  ],
  manuscript: [
    { cap: "freeform",                  label: "Improve Abstract",          icon: Pencil, prompt: "Rewrite the abstract for clarity, impact, and precision. Show the original and the improved version." },
    { cap: "literature_synthesis",      label: "Summarize Literature",      icon: BookOpen, prompt: "Synthesize the literature relevant to this manuscript into 4-6 themes." },
    { cap: "research_question_generation", label: "Identify Research Gaps", icon: Lightbulb, prompt: "Identify 3-5 research gaps this manuscript could fill or speak to." },
    { cap: "methodology_assistance",    label: "Suggest Methodology",       icon: Beaker, prompt: "Critique and refine the methodology section. Suggest improvements." },
    { cap: "journal_explanation",       label: "Explain Journal Match",     icon: BookOpen, prompt: "Explain why the current target journal is (or isn't) a strong fit for this manuscript." },
    { cap: "conference_explanation",    label: "Explain Conference Match",  icon: CalendarDays, prompt: "Suggest 2-3 conferences that fit this manuscript and explain why." },
    { cap: "grant_explanation",         label: "Explain Grant Match",       icon: Coins, prompt: "Suggest 2-3 grants that could fund follow-up work from this manuscript." },
    { cap: "reviewer_response_drafting", label: "Draft Reviewer Response",  icon: MessageSquareReply, prompt: "Draft a polite, point-by-point response to typical reviewer concerns about this paper." },
  ],
};

export default function AssistantPanel({ open, onClose, entityKind, entityId, entityTitle }) {
  const { refreshMe } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [capability, setCapability] = useState("freeform");
  const [busy, setBusy] = useState(false);
  const [creating, setCreating] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [balance, setBalance] = useState(null);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  const quickActions = useMemo(() => QUICK_ACTIONS_BY_KIND[entityKind] || [], [entityKind]);

  const loadCredits = useCallback(async () => {
    try { const { data } = await api.get("/credits/balance"); setBalance(data); } catch {}
  }, []);

  const loadSessions = useCallback(async () => {
    if (!open) return;
    try {
      const { data } = await api.get(`/assistant/sessions?entity_kind=${entityKind}&entity_id=${entityId}`);
      setSessions(data || []);
      if ((data || []).length > 0 && !sessionId) {
        setSessionId(data[0].id);
      }
    } catch (e) { /* ignore */ }
  }, [open, entityKind, entityId, sessionId]);

  const loadMessages = useCallback(async (sid) => {
    if (!sid) { setMessages([]); return; }
    try {
      const { data } = await api.get(`/assistant/sessions/${sid}/messages`);
      setMessages(data.messages || []);
    } catch (e) { setMessages([]); }
  }, []);

  const newSession = useCallback(async (title) => {
    setCreating(true);
    try {
      const { data } = await api.post("/assistant/sessions", {
        entity_kind: entityKind, entity_id: entityId, title: title || undefined,
      });
      setSessions((s) => [data, ...s]);
      setSessionId(data.id);
      setMessages([]);
      setShowHistory(false);
      return data.id;
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to start session");
      return null;
    } finally { setCreating(false); }
  }, [entityKind, entityId]);

  const ensureSession = useCallback(async () => {
    if (sessionId) return sessionId;
    return await newSession();
  }, [sessionId, newSession]);

  const send = useCallback(async (text, cap) => {
    const body = (text || "").trim();
    if (!body || busy) return;
    if (balance && balance.balance < ASSISTANT_COST) {
      toast.error("Out of Research Credits. Upgrade plan or wait for monthly reset.");
      return;
    }
    setBusy(true);
    const sid = await ensureSession();
    if (!sid) { setBusy(false); return; }
    // Optimistic user message
    const userMsg = { id: `tmp-${Date.now()}`, role: "user", text: body, capability: cap || "freeform", created_at: new Date().toISOString() };
    setMessages((m) => [...m, userMsg]);
    setDraft("");
    try {
      const { data } = await api.post(`/assistant/sessions/${sid}/messages`, { text: body, capability: cap || capability || "freeform" });
      setMessages((m) => [...m, { id: data.id, role: "assistant", text: data.text, credits_consumed: data.credits_consumed, latency_ms: data.latency_ms, created_at: new Date().toISOString() }]);
      loadCredits();
      refreshMe?.();
    } catch (e) {
      // Roll back optimistic message on hard error
      const status = e?.response?.status;
      const detail = e?.response?.data?.detail || "Failed";
      toast.error(detail);
      if (status === 402) {
        // user out of credits — keep their message but show no reply
      } else {
        setMessages((m) => m.filter((x) => x.id !== userMsg.id));
        setDraft(body);
      }
    } finally { setBusy(false); }
  }, [busy, balance, ensureSession, capability, loadCredits, refreshMe]);

  const deleteSession = useCallback(async (sid) => {
    if (!confirm("Delete this conversation? This cannot be undone.")) return;
    try {
      await api.delete(`/assistant/sessions/${sid}`);
      setSessions((s) => s.filter((x) => x.id !== sid));
      if (sessionId === sid) {
        setSessionId(null);
        setMessages([]);
      }
    } catch (e) { toast.error("Failed"); }
  }, [sessionId]);

  useEffect(() => { if (open) { loadSessions(); loadCredits(); } }, [open, loadSessions, loadCredits]);
  useEffect(() => { loadMessages(sessionId); }, [sessionId, loadMessages]);
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages.length, busy]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex" data-testid="assistant-panel" onClick={onClose}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-slate-900/40" />
      {/* Drawer */}
      <div
        className="ml-auto relative w-full max-w-2xl h-full bg-white border-l border-slate-200 flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="border-b border-slate-200 px-5 py-4 flex items-start justify-between gap-3 bg-white">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Sparkles size={14} strokeWidth={1.5} className="text-[#0F2847]" />
              <div className="overline text-[#0F2847]">Research Copilot</div>
              {balance && (
                <span className="text-[10px] font-mono text-slate-500 ml-auto" data-testid="assistant-balance">
                  {balance.balance} / {balance.monthly_allowance} credits
                </span>
              )}
            </div>
            <h3 className="font-serif text-lg text-slate-900 mt-1 truncate">{entityTitle || `${entityKind} chat`}</h3>
            <div className="text-[11px] font-mono text-slate-500 mt-0.5 capitalize">{entityKind} context · {ASSISTANT_COST} credits / message</div>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <button
              data-testid="assistant-history-toggle"
              onClick={() => setShowHistory((s) => !s)}
              className="text-slate-500 hover:text-slate-900 p-1.5 border border-slate-200 hover:border-slate-400"
              title="Conversation history"
            >
              <History size={13} strokeWidth={1.5} />
            </button>
            <button
              data-testid="assistant-new-session"
              onClick={() => newSession()}
              disabled={creating}
              className="text-slate-500 hover:text-slate-900 p-1.5 border border-slate-200 hover:border-slate-400"
              title="New conversation"
            >
              <Plus size={13} strokeWidth={1.5} />
            </button>
            <button
              data-testid="assistant-close"
              onClick={onClose}
              className="text-slate-400 hover:text-slate-900 p-1.5"
              title="Close"
            >
              <X size={16} strokeWidth={1.5} />
            </button>
          </div>
        </div>

        {/* History dropdown */}
        {showHistory && (
          <div className="border-b border-slate-200 bg-slate-50 max-h-48 overflow-y-auto">
            {sessions.length === 0 && (
              <div className="text-xs text-slate-500 px-4 py-3">No previous conversations on this {entityKind}.</div>
            )}
            {sessions.map((s) => (
              <div
                key={s.id}
                className={`flex items-center gap-2 px-4 py-2 border-b border-slate-100 text-xs hover:bg-white cursor-pointer ${sessionId === s.id ? "bg-white" : ""}`}
                onClick={() => { setSessionId(s.id); setShowHistory(false); }}
                data-testid={`assistant-session-${s.id}`}
              >
                <span className="text-slate-700 truncate flex-1">{s.title}</span>
                <span className="text-[10px] font-mono text-slate-400">{s.messages_count || 0} msgs</span>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteSession(s.id); }}
                  className="text-slate-400 hover:text-red-600 p-1"
                  title="Delete"
                >
                  <Trash2 size={11} strokeWidth={1.5} />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-4 bg-slate-50/40">
          {messages.length === 0 && (
            <div className="text-center pt-10 pb-6">
              <div className="inline-flex w-14 h-14 items-center justify-center bg-[#0F2847]/5 border border-[#0F2847]/20 mx-auto">
                <Sparkles size={20} strokeWidth={1.5} className="text-[#0F2847]" />
              </div>
              <p className="font-serif text-lg text-slate-900 mt-4">How can I help with your research?</p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">Grounded in your {entityKind} context. Try a quick action below or write your own prompt.</p>
            </div>
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} msg={m} />
          ))}
          {busy && (
            <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
              <Loader2 size={12} className="animate-spin text-[#0F2847]" />
              Thinking…
            </div>
          )}
        </div>

        {/* Quick actions */}
        <div className="border-t border-slate-200 bg-white px-4 py-3">
          <div className="flex items-center justify-between mb-2">
            <div className="overline">Quick actions</div>
            <div className="text-[10px] font-mono text-slate-400">{ASSISTANT_COST} credits each</div>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {quickActions.map((a, i) => {
              const Icon = a.icon;
              return (
                <button
                  key={i}
                  data-testid={`assistant-quick-${a.cap}-${i}`}
                  onClick={() => send(a.prompt, a.cap)}
                  disabled={busy}
                  className="inline-flex items-center gap-1.5 text-[11px] border border-slate-300 px-2.5 py-1 hover:border-[#0F2847] hover:text-[#0F2847] disabled:opacity-50"
                >
                  <Icon size={11} strokeWidth={1.5} />
                  {a.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Composer */}
        <div className="border-t border-slate-200 bg-white px-4 py-3">
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              data-testid="assistant-input"
              rows={2}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(draft, capability); }
              }}
              placeholder={`Ask the copilot anything about this ${entityKind}…`}
              className="flex-1 px-3 py-2 border border-slate-300 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847] resize-none"
            />
            <button
              data-testid="assistant-send"
              onClick={() => send(draft, capability)}
              disabled={busy || !draft.trim()}
              className="bg-[#0F2847] text-white px-4 py-2 text-sm hover:bg-slate-800 disabled:opacity-50 inline-flex items-center gap-1.5"
              title={`Send (${ASSISTANT_COST} credits)`}
            >
              {busy ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} strokeWidth={1.5} />}
              Send
            </button>
          </div>
          <div className="flex items-center justify-between mt-1.5">
            <div className="text-[10px] font-mono text-slate-400">
              {balance ? `Balance: ${balance.balance} credits` : ""}
            </div>
            <div className="text-[10px] font-mono text-slate-400">Cost on send: {ASSISTANT_COST}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[88%] ${isUser ? "" : "border-l-2 border-[#0F2847] pl-3"}`}>
        {!isUser && (
          <div className="flex items-center gap-1.5 mb-1">
            <Sparkles size={10} strokeWidth={1.5} className="text-[#0F2847]" />
            <span className="overline text-[#0F2847]">Copilot</span>
            {msg.credits_consumed != null && (
              <span className="text-[10px] font-mono text-slate-400">· {typeof msg.credits_consumed === "number" ? msg.credits_consumed : (msg.credits_consumed?.consumed ?? 0)} credits · {((msg.latency_ms || 0) / 1000).toFixed(1)}s</span>
            )}
          </div>
        )}
        <div
          className={
            isUser
              ? "bg-[#0F2847] text-white px-4 py-2.5 text-sm whitespace-pre-wrap leading-relaxed"
              : "bg-white border border-slate-200 px-4 py-3 text-sm text-slate-800 whitespace-pre-wrap leading-relaxed font-serif"
          }
        >
          {msg.text}
        </div>
        {msg.capability && msg.capability !== "freeform" && isUser && (
          <div className="text-[10px] font-mono text-slate-400 mt-1 text-right">
            {msg.capability.replaceAll("_", " ")}
          </div>
        )}
      </div>
    </div>
  );
}
