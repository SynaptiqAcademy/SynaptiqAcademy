import React, { useState, useEffect, useRef, useCallback } from "react";
import { BrainCircuit, Send, Loader2, Clock, ChevronDown, ChevronUp } from "lucide-react";
import { NAVY, WARM, BRD, ACCENT, WHITE, TEXT_SECONDARY } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import { Button, Card, NavTabs, Textarea, Tag, EmptyState } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

const SUGGESTED = [
  "What is our overall institutional health status?",
  "Which departments need additional funding support?",
  "Which researchers are candidates for promotion?",
  "What are our biggest institutional risks right now?",
  "How can we improve our international collaboration?",
  "What is our grant success rate and how can we improve it?",
  "Which research areas are our strongest?",
  "How is our publication quality trending?",
];

// Custom chat-bubble shape (asymmetric corner + tail) has no equivalent in
// the ds/ library (Card is a rectangular container) — left hand-rolled.
function MessageBubble({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div style={{
      display: "flex", justifyContent: isUser ? "flex-end" : "flex-start",
      marginBottom: 14, gap: 10,
    }}>
      {!isUser && (
        <div style={{ width: 32, height: 32, borderRadius: "50%", background: `${ACCENT}20`, flexShrink: 0,
          display: "flex", alignItems: "center", justifyContent: "center" }}>
          <BrainCircuit size={16} color={ACCENT} />
        </div>
      )}
      <div style={{
        maxWidth: "72%",
        background: isUser ? NAVY : WHITE,
        color: isUser ? WHITE : NAVY,
        border: isUser ? "none" : `1px solid ${BRD}`,
        borderRadius: isUser ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
        padding: "12px 16px", fontSize: 13, lineHeight: 1.6,
        whiteSpace: "pre-wrap",
      }}>
        {msg.text}
      </div>
    </div>
  );
}

function HistoryItem({ item }) {
  const [open, setOpen] = useState(false);
  return (
    <Card padding="none" className="mb-2 overflow-hidden">
      <button onClick={() => setOpen(v => !v)} style={{
        width: "100%", padding: "10px 14px", display: "flex", justifyContent: "space-between",
        alignItems: "center", background: "none", border: "none", cursor: "pointer",
      }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: NAVY, textAlign: "left", flex: 1 }}>{item.query}</span>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>{new Date(item.created_at).toLocaleDateString()}</span>
          {open ? <ChevronUp size={13} color={TEXT_SECONDARY} /> : <ChevronDown size={13} color={TEXT_SECONDARY} />}
        </div>
      </button>
      {open && (
        <div style={{ padding: "0 14px 12px", fontSize: 13, color: "#334155", lineHeight: 1.6, borderTop: `1px solid ${BRD}` }}>
          <div style={{ paddingTop: 10, whiteSpace: "pre-wrap" }}>{item.response}</div>
        </div>
      )}
    </Card>
  );
}

export default function AIExecutiveAssistant() {
  const [messages, setMessages] = useState([
    { role: "assistant", text: "Hello. I'm the Synaptiq AI Executive Assistant. I can answer questions about your institution's health, faculty, publications, grants, collaborations, risks, and strategic priorities.\n\nHow can I help you today?" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [tab, setTab] = useState("chat");
  const bottomRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const loadHistory = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/iip/assistant/history`, { headers: authH() });
      if (r.ok) setHistory(await r.json());
    } catch (_) {}
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  const send = async (query) => {
    if (!query.trim() || loading) return;
    const q = query.trim();
    setInput("");
    setMessages(m => [...m, { role: "user", text: q }]);
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/iip/assistant/query`, {
        method: "POST",
        headers: { ...authH(), "Content-Type": "application/json" },
        body: JSON.stringify({ query: q }),
      });
      if (r.ok) {
        const d = await r.json();
        setMessages(m => [...m, { role: "assistant", text: d.response }]);
        loadHistory();
      } else {
        setMessages(m => [...m, { role: "assistant", text: "I couldn't process that request. Please try again." }]);
      }
    } catch (_) {
      setMessages(m => [...m, { role: "assistant", text: "Connection error. Please check your network and try again." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <InstitutionLayout
      title="AI Executive Assistant"
      subtitle="Ask strategic questions about your institution. Powered by real institutional data."
    >
      <div style={{ marginBottom: 16 }}>
        <NavTabs
          variant="pill"
          active={tab}
          onChange={setTab}
          tabs={[
            { id: "chat", label: "Chat" },
            { id: "history", label: "History", count: history.length, icon: Clock },
          ]}
        />
      </div>

      {tab === "chat" && (
        <>
          {/* Suggestions */}
          {messages.length <= 1 && (
            <div style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 12, color: TEXT_SECONDARY, marginBottom: 8 }}>Suggested questions:</p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {SUGGESTED.map((s, i) => (
                  <Tag key={i} onClick={() => send(s)}>{s}</Tag>
                ))}
              </div>
            </div>
          )}

          {/* Messages — custom scrollable transcript panel, no ds/ equivalent for a
              tinted chat-history well; left hand-rolled. */}
          <div style={{
            background: WARM, borderRadius: 12, padding: 20, minHeight: 300, maxHeight: 500,
            overflowY: "auto", marginBottom: 16,
          }}>
            {messages.map((m, i) => <MessageBubble key={i} msg={m} />)}
            {loading && (
              <div style={{ display: "flex", alignItems: "center", gap: 10, opacity: 0.7 }}>
                <div style={{ width: 32, height: 32, borderRadius: "50%", background: `${ACCENT}20`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <BrainCircuit size={16} color={ACCENT} />
                </div>
                <div style={{ background: WHITE, border: `1px solid ${BRD}`, borderRadius: "16px 16px 16px 4px", padding: "12px 16px" }}>
                  <Loader2 size={16} color={ACCENT} style={{ animation: "spin 1s linear infinite" }} />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div style={{ display: "flex", gap: 8 }}>
            <Textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
              placeholder="Ask a strategic question about your institution..."
              rows={2}
              resize={false}
              wrapperClassName="flex-1"
            />
            <Button
              variant="primary"
              size="icon"
              onClick={() => send(input)}
              disabled={loading || !input.trim()}
            >
              <Send size={18} />
            </Button>
          </div>
          <p style={{ fontSize: 11, color: TEXT_SECONDARY, marginTop: 6 }}>
            Press Enter to send · Shift+Enter for new line
          </p>
        </>
      )}

      {tab === "history" && (
        <div>
          {history.length === 0
            ? <EmptyState title="No conversation history yet." />
            : history.map((item, i) => <HistoryItem key={i} item={item} />)
          }
        </div>
      )}
    </InstitutionLayout>
  );
}
