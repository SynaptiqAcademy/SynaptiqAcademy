/**
 * Copilot — Multi-Agent Research Copilot page (Phase XXXI).
 *
 * Route: /copilot
 *
 * Architecture:
 *   Left column:  chat-style input + conversation history
 *   Right panel:  live orchestration map + per-agent cards
 *
 * Users describe their research goal in plain language.
 * The orchestrator selects the right workflow, runs agents in parallel,
 * and delivers a unified response with full evidence provenance.
 */
import React, { useState, useRef, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Send, Sparkles, RefreshCw, ChevronDown, ChevronUp,
  Users, BookOpen, FileText, BadgeDollarSign, BarChart2,
  CheckCircle, Lightbulb, Search, Info, Database,
} from "lucide-react";
import { streamExecute, getWorkflows } from "../services/copilotEngine";
import AgentCard from "../components/copilot/AgentCard";
import OrchestrationMap from "../components/copilot/OrchestrationMap";
import { NAVY, ACCENT, WARM } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";

// ── Constants ──────────────────────────────────────────────────────────────────

const BORDER = "#E4E8EF";
const SESSION_KEY = "sq_copilot_session";

// Starter prompts shown before first message
const STARTERS = [
  { icon: FileText,        text: "Help me publish this paper",           workflow: "publish_paper" },
  { icon: BadgeDollarSign, text: "Find grant funding for my research",    workflow: "funding_discovery" },
  { icon: Search,          text: "Conduct a literature review",           workflow: "literature_review" },
  { icon: CheckCircle,     text: "Simulate peer review of my manuscript", workflow: "peer_review_sim" },
  { icon: Users,           text: "Find research collaborators",           workflow: "collaboration_search" },
  { icon: BarChart2,       text: "Advise on research methodology",        workflow: "methodology_design" },
];

// ── Sub-components ─────────────────────────────────────────────────────────────

function MessageBubble({ role, content, agentOutputs = [], plan, showAgents, onToggleAgents }) {
  if (role === "user") {
    return (
      <div className="flex justify-end mb-5">
        <div
          className="max-w-[75%] px-4 py-3 text-[13px] text-white leading-relaxed"
          style={{ background: NAVY }}
        >
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="mb-6">
      {/* Agent attribution header */}
      {plan && (
        <div className="flex items-center gap-2 mb-2">
          <Sparkles size={10} strokeWidth={1.5} style={{ color: NAVY }} />
          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
            Research Copilot · {agentOutputs.length} agent{agentOutputs.length !== 1 ? "s" : ""}
          </span>
          {agentOutputs.length > 0 && (
            <button
              onClick={onToggleAgents}
              className="ml-auto flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-600 transition-colors"
            >
              {showAgents ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
              {showAgents ? "Hide" : "Show"} agent details
            </button>
          )}
        </div>
      )}

      {/* Main response */}
      <div
        className="px-5 py-4 text-[13px] text-slate-700 leading-relaxed border border-slate-200 bg-white whitespace-pre-wrap"
      >
        {content}
      </div>

      {/* Agent detail cards (expandable) */}
      {showAgents && agentOutputs.length > 0 && (
        <div className="mt-2 flex flex-col gap-2">
          {agentOutputs.map((o, i) => (
            <AgentCard key={i} output={o} />
          ))}
        </div>
      )}
    </div>
  );
}

function RunningAgents({ statuses, plan }) {
  const running = Object.entries(statuses).filter(([, s]) => s === "running").map(([n]) => n);
  if (!running.length || !plan) return null;
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className="w-1.5 h-1.5 bg-blue-500 animate-pulse rounded-full" />
      <span className="text-[11px] text-slate-500">
        {running.join(", ")} agent{running.length !== 1 ? "s" : ""} working…
      </span>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function Copilot() {
  const [messages,       setMessages]       = useState([]);
  const [input,          setInput]          = useState("");
  const [running,        setRunning]        = useState(false);
  const [sessionId,      setSessionId]      = useState(() => localStorage.getItem(SESSION_KEY) || null);
  const [agentStatuses,  setAgentStatuses]  = useState({});
  const [currentPlan,    setCurrentPlan]    = useState(null);
  const [showAgentMap,   setShowAgentMap]   = useState(true);
  const [showAgentCards, setShowAgentCards] = useState({});   // messageIdx → bool
  const [workflows,      setWorkflows]      = useState([]);
  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  useEffect(() => {
    getWorkflows().then(d => setWorkflows(d?.workflows || []));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(async (text) => {
    const trimmed = text.trim();
    if (!trimmed || running) return;

    setInput("");
    setRunning(true);
    setAgentStatuses({});
    setCurrentPlan(null);

    // Append user message
    const userMsg = { role: "user", content: trimmed };
    setMessages(prev => [...prev, userMsg]);

    // Placeholder for assistant response being built
    const assistantIdx = messages.length + 1;
    let   accumulatedOutputs = [];
    let   planData           = null;
    let   finalData          = null;

    // Update assistant message in-place as events arrive
    const updateAssistant = (patch) => {
      setMessages(prev => {
        const next = [...prev];
        const existing = next[assistantIdx];
        if (!existing) {
          next[assistantIdx] = { role: "assistant", content: "", agentOutputs: [], plan: null, ...patch };
        } else {
          next[assistantIdx] = { ...existing, ...patch };
        }
        return next;
      });
    };

    await streamExecute(trimmed, sessionId, {
      onPlan: (plan) => {
        planData = plan;
        setCurrentPlan(plan);
        // Mark all agents as waiting
        const initial = {};
        (plan.stages || []).flat().forEach(a => { initial[a] = "waiting"; });
        setAgentStatuses(initial);
        updateAssistant({ plan, content: "", agentOutputs: [] });

        // Persist session ID
        if (plan.session_id && plan.session_id !== sessionId) {
          setSessionId(plan.session_id);
          localStorage.setItem(SESSION_KEY, plan.session_id);
        }
      },

      onStageStart: ({ agents }) => {
        setAgentStatuses(prev => {
          const next = { ...prev };
          agents.forEach(a => { next[a] = "running"; });
          return next;
        });
      },

      onAgentOutput: (output) => {
        accumulatedOutputs = [...accumulatedOutputs, output];
        setAgentStatuses(prev => ({ ...prev, [output.agent]: output.status }));
        updateAssistant({ agentOutputs: accumulatedOutputs });
      },

      onFinal: (data) => {
        finalData = data;
        updateAssistant({
          content:      data.response || "No response generated.",
          agentOutputs: data.agent_outputs || accumulatedOutputs,
          plan:         planData,
          meta:         {
            workflow:         data.workflow_id,
            qualityScore:     data.quality_score,
            agentsUsed:       data.agents_used,
            evidenceSources:  data.evidence_sources,
          },
        });
        setRunning(false);
      },

      onError: (err) => {
        updateAssistant({ content: `An error occurred: ${err.message || "Unknown error"}`, agentOutputs: [] });
        setRunning(false);
      },

      onDone: () => {
        if (!finalData) setRunning(false);
      },
    });
  }, [running, sessionId, messages.length]);

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleStarter = (text) => {
    setInput(text);
    sendMessage(text);
  };

  const newSession = () => {
    localStorage.removeItem(SESSION_KEY);
    setSessionId(null);
    setMessages([]);
    setCurrentPlan(null);
    setAgentStatuses({});
    inputRef.current?.focus();
  };

  const isEmpty = messages.length === 0;

  return (
    <AIWorkspaceLayout
      title="Research Copilot"
      subtitle="Describe your research goal. A team of specialized AI agents will collaborate to help you."
      actions={
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAgentMap(v => !v)}
            className="flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1.5 border border-slate-200 text-slate-500 hover:text-slate-800 transition-colors"
          >
            <BarChart2 size={10} strokeWidth={1.5} />
            {showAgentMap ? "Hide" : "Show"} agent map
          </button>
          {!isEmpty && (
            <button
              onClick={newSession}
              className="flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1.5 border border-slate-200 text-slate-500 hover:text-slate-800 transition-colors"
            >
              <RefreshCw size={10} strokeWidth={1.5} />
              New session
            </button>
          )}
        </div>
      }
    >

      <div className="flex-1 flex gap-6 min-h-0 items-start">
        {/* ── Left: conversation ────────────────────────────────────── */}
        <div className="flex-1 flex flex-col min-w-0" style={{ minHeight: "500px" }}>

          {/* Empty state / starters */}
          {isEmpty && (
            <div className="flex-1 flex flex-col items-center justify-center py-10">
              <div className="w-12 h-12 flex items-center justify-center mb-4" style={{ background: NAVY }}>
                <Sparkles size={18} strokeWidth={1.5} className="text-white" />
              </div>
              <h2 className="text-[16px] font-semibold text-slate-800 mb-1">What would you like to work on?</h2>
              <p className="text-[13px] text-slate-400 mb-6 text-center max-w-md">
                Describe any research task. The copilot will coordinate the right specialists automatically.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                {STARTERS.map(({ icon: Icon, text }) => (
                  <button
                    key={text}
                    onClick={() => handleStarter(text)}
                    className="flex items-center gap-2.5 px-4 py-3 border border-slate-200 bg-white text-left hover:border-slate-400 hover:bg-slate-50 transition-all text-[12px] text-slate-600 font-medium"
                  >
                    <Icon size={12} strokeWidth={1.5} style={{ color: NAVY, flexShrink: 0 }} />
                    {text}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Messages */}
          {!isEmpty && (
            <div className="flex-1 overflow-y-auto pb-4 pr-1">
              {messages.map((msg, i) => (
                <MessageBubble
                  key={i}
                  role={msg.role}
                  content={msg.content || ""}
                  agentOutputs={msg.agentOutputs || []}
                  plan={msg.plan}
                  showAgents={!!showAgentCards[i]}
                  onToggleAgents={() => setShowAgentCards(prev => ({ ...prev, [i]: !prev[i] }))}
                />
              ))}

              {running && (
                <div className="mb-4">
                  <RunningAgents statuses={agentStatuses} plan={currentPlan} />
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          )}

          {/* Input area */}
          <form onSubmit={handleSubmit} className="mt-4 flex gap-2 items-end">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage(input);
                  }
                }}
                placeholder="Describe your research goal… (e.g. Help me publish this paper)"
                rows={3}
                disabled={running}
                className="w-full resize-none border border-slate-300 px-4 py-3 text-[13px] text-slate-800 placeholder-slate-400 focus:outline-none focus:border-slate-500 transition-colors disabled:bg-slate-50 disabled:text-slate-400"
              />
              <div className="absolute bottom-2 right-2 text-[10px] text-slate-300">Shift+Enter for newline</div>
            </div>
            <button
              type="submit"
              disabled={running || !input.trim()}
              className="flex items-center gap-2 px-4 py-3 text-[13px] font-semibold text-white transition-colors disabled:opacity-40"
              style={{ background: running ? "#64748B" : NAVY }}
            >
              {running
                ? <RefreshCw size={13} strokeWidth={1.5} className="animate-spin" />
                : <Send size={13} strokeWidth={1.5} />
              }
              {running ? "Working…" : "Send"}
            </button>
          </form>

          <p className="text-[10px] text-slate-400 mt-2">
            All recommendations are sourced from verified platform data. No statistics are fabricated.
          </p>
        </div>

        {/* ── Right: agent map + cards ──────────────────────────────── */}
        {showAgentMap && (
          <aside
            className="w-[300px] shrink-0 flex flex-col gap-4"
            style={{ position: "sticky", top: "80px", maxHeight: "80vh", overflowY: "auto" }}
          >
            {/* Orchestration map */}
            {currentPlan ? (
              <div className="border border-slate-200 bg-white px-4 py-3">
                <OrchestrationMap plan={currentPlan} statuses={agentStatuses} />
              </div>
            ) : (
              <div className="border border-dashed border-slate-200 px-4 py-5 text-center">
                <BarChart2 size={20} strokeWidth={1} className="text-slate-200 mx-auto mb-2" />
                <p className="text-[11px] text-slate-400 m-0">Agent orchestration map appears here</p>
              </div>
            )}

            {/* Agent status cards */}
            {Object.keys(agentStatuses).length > 0 && (
              <div className="flex flex-col gap-1.5">
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 px-1">
                  Active agents
                </div>
                {Object.entries(agentStatuses).map(([name, status]) => (
                  <AgentCard
                    key={name}
                    output={{
                      agent:   name,
                      status,
                      content: "",
                      evidence: [],
                      limitations: [],
                      confidence: "not_applicable",
                      confidence_basis: "",
                    }}
                    compact
                  />
                ))}
              </div>
            )}

            {/* Workflow shortcuts */}
            {!running && workflows.length > 0 && (
              <div className="border border-slate-200 bg-white px-4 py-3">
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                  Quick workflows
                </div>
                {workflows.slice(0, 6).map(wf => (
                  <button
                    key={wf.id}
                    onClick={() => handleStarter(wf.phrases?.[0] || wf.label)}
                    className="w-full text-left text-[11px] text-slate-500 hover:text-slate-900 py-1 border-b border-slate-50 last:border-0 transition-colors"
                  >
                    {wf.label.split(":")[0]}
                  </button>
                ))}
              </div>
            )}

            {/* Evidence policy note */}
            <div className="flex items-start gap-2 px-3 py-2.5 border border-slate-100 bg-slate-50">
              <Info size={10} strokeWidth={1.5} className="text-slate-400 shrink-0 mt-0.5" />
              <p className="text-[10px] text-slate-400 m-0 leading-relaxed">
                All agents follow the Academic Reliability Policy. Every recommendation traces to verified evidence. No statistics are fabricated.
              </p>
            </div>
          </aside>
        )}
      </div>
    </AIWorkspaceLayout>
  );
}
