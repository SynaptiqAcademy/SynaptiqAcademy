import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Brain, Command, Zap, Target, CheckSquare, Trophy, TrendingUp,
  ArrowRight, RefreshCw, Star, Sparkles,
  BookMarked, GraduationCap, Calendar,
} from "lucide-react";
import { NAVY, WARM, BRD, ACCENT, EMERALD, WHITE, TEXT_SECONDARY } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";
import { SIE_NAV_ITEMS } from "@/lib/navItems";
import { Card, Badge, Tag, Button, Input, Callout, StatCard, StatGrid, Spinner, H4 } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

const QUICK_COMMANDS = [
  "Help me publish two Q1 papers this year",
  "Build a grant strategy for Horizon Europe",
  "Prepare me for promotion to associate professor",
  "Generate my research plan for the next 6 months",
  "Find collaboration opportunities in my field",
  "Improve my citation impact",
  "Analyse my academic weaknesses",
  "Create my publication roadmap",
];

const NAV_ITEMS = [
  { to: "/sie/goals",        label: "Goals",         icon: Target,        color: ACCENT },
  { to: "/sie/planning",     label: "Roadmaps",      icon: BookMarked,    color: "#8b5cf6" },
  { to: "/sie/missions",     label: "Missions",      icon: CheckSquare,   color: EMERALD },
  { to: "/sie/career",       label: "Career",        icon: GraduationCap, color: "#f59e0b" },
  { to: "/sie/daily",        label: "Today",         icon: Calendar,      color: "#0ea5e9" },
  { to: "/sie/grants",       label: "Grants",        icon: Trophy,        color: "#ec4899" },
  { to: "/sie/recommendations", label: "AI Recs",   icon: Sparkles,      color: ACCENT },
  { to: "/sie/progress",     label: "Progress",      icon: TrendingUp,    color: EMERALD },
];

function InsightBadge({ insight }) {
  return (
    <Callout variant={insight.level} style={{ marginBottom: 6, padding: "8px 12px" }}>
      <span style={{ fontSize: 13 }}>{insight.text}</span>
    </Callout>
  );
}

export default function ResearchCommandCenter() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [command, setCommand] = useState("");
  const [cmdLoading, setCmdLoading] = useState(false);
  const [cmdResult, setCmdResult] = useState(null);
  const navigate = useNavigate();
  const cmdRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/sie/overview`, { headers: authH() });
      if (r.ok) setOverview(await r.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const runCommand = async (cmd) => {
    const q = (cmd || command).trim();
    if (!q) return;
    setCmdLoading(true);
    setCmdResult(null);
    setCommand(q);
    try {
      const r = await fetch(`${API}/api/sie/command`, {
        method: "POST",
        headers: { ...authH(), "Content-Type": "application/json" },
        body: JSON.stringify({ command: q }),
      });
      if (r.ok) setCmdResult(await r.json());
    } catch (_) {}
    setCmdLoading(false);
  };

  const ctx = overview?.context;
  const insights = overview?.insights || [];

  return (
    <AIWorkspaceLayout
      title="Synaptiq Intelligence Engine"
      subtitle={ctx ? `Welcome, ${ctx.user?.name || "Researcher"}. Your AI research partner is active.` : "Your AI academic operating system."}
      navItems={SIE_NAV_ITEMS}
    >
      {/* AI Command input */}
      <div style={{ marginBottom: 20, display: "flex", gap: 8, padding: "14px 16px", background: WHITE, border: `1px solid ${BRD}` }}>
        <Input
          value={command}
          onChange={e => setCommand(e.target.value)}
          onKeyDown={e => e.key === "Enter" && runCommand()}
          placeholder="Tell the AI what you want to achieve…"
          prefix={<Command size={16} color={ACCENT} />}
          wrapperClassName="flex-1"
        />
        <Button onClick={() => runCommand()} loading={cmdLoading} disabled={cmdLoading || !command.trim()} style={{ flexShrink: 0 }}>
          {!cmdLoading && <Zap size={14} />}
          Execute
        </Button>
      </div>

      {/* Quick commands */}
      {!cmdResult && (
        <div style={{ marginBottom: 20 }}>
          <p style={{ fontSize: 12, color: TEXT_SECONDARY, marginBottom: 8 }}>Try an AI command:</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {QUICK_COMMANDS.map((q, i) => (
              <Tag key={i} onClick={() => { setCommand(q); runCommand(q); }}>{q}</Tag>
            ))}
          </div>
        </div>
      )}

      {/* Command result */}
      {cmdResult && (
        <Card padding="xl" style={{ border: `2px solid ${ACCENT}`, marginBottom: 24 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <Brain size={16} color={ACCENT} />
            <H4>{cmdResult.title}</H4>
          </div>
          <p style={{ margin: "0 0 14px", fontSize: 13, color: "#334155" }}>{cmdResult.summary}</p>
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 12, color: TEXT_SECONDARY, fontWeight: 600, marginBottom: 6 }}>ACTION STEPS</div>
            {(cmdResult.action_steps || []).map((step, i) => (
              <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                {/* Numbered step avatar: no ds/ primitive for a numbered
                    circle, left hand-rolled */}
                <span style={{ width: 20, height: 20, borderRadius: "50%", background: `${ACCENT}20`, color: ACCENT, fontWeight: 800, fontSize: 11, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{i + 1}</span>
                <span style={{ fontSize: 13, color: "#334155" }}>{step}</span>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {(cmdResult.modules_invoked || []).map((m, i) => (
              <Badge key={i} color={ACCENT}>{m}</Badge>
            ))}
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
            {cmdResult.primary_action_url && (
              <Button onClick={() => navigate(cmdResult.primary_action_url)}>
                Open in Synaptiq <ArrowRight size={13} />
              </Button>
            )}
            <Button variant="ghost" onClick={() => { setCmdResult(null); setCommand(""); }}>
              New Command
            </Button>
          </div>
        </Card>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 20 }}>
        <div>
          {/* Stats */}
          {ctx && (
            <div style={{ marginBottom: 20 }}>
              <StatGrid cols={4}>
                <StatCard label="Publications" value={ctx.research?.total_publications ?? 0} />
                <StatCard label="Grants Approved" value={ctx.grants?.approved ?? 0} />
                <StatCard label="Active Goals" value={ctx.sie?.active_goals ?? 0} />
                <StatCard label="Pending Missions" value={ctx.sie?.pending_missions ?? 0} />
              </StatGrid>
            </div>
          )}

          {/* Platform insights */}
          {insights.length > 0 && (
            <Card padding="lg" style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
                <Sparkles size={15} color={ACCENT} />
                <H4>AI Insights</H4>
              </div>
              {insights.map((ins, i) => <InsightBadge key={i} insight={ins} />)}
            </Card>
          )}

          {/* Navigation grid */}
          <Card padding="lg">
            <H4 style={{ marginBottom: 14 }}>Intelligence Modules</H4>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
              {NAV_ITEMS.map(({ to, label, icon: Icon, color }) => (
                <Card
                  key={to}
                  onClick={() => navigate(to)}
                  padding="md"
                  style={{ background: WARM, display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}
                  onMouseOver={e => e.currentTarget.style.background = `${color}10`}
                  onMouseOut={e => e.currentTarget.style.background = WARM}
                >
                  <Icon size={20} color={color} />
                  <span style={{ fontSize: 12, fontWeight: 700, color: NAVY }}>{label}</span>
                </Card>
              ))}
            </div>
          </Card>
        </div>

        {/* Right column */}
        <div>
          {loading ? (
            <div style={{ display: "flex", justifyContent: "center", padding: 40 }}>
              <Spinner size={24} color={ACCENT} />
            </div>
          ) : (
            <>
              <Card padding="lg" style={{ marginBottom: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
                  <Star size={14} color="#f59e0b" />
                  <H4>Platform Summary</H4>
                </div>
                {/* Compact label/value summary rows: kept hand-rolled —
                    ds/ListItem's built-in padding (12px+ per row) would
                    triple the height of this deliberately dense 4px-row list */}
                {ctx && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {[
                      { label: "Institution", value: ctx.user?.institution || "Not set" },
                      { label: "Integrity Score", value: `${ctx.integrity?.score ?? 0}/100 (${ctx.integrity?.grade ?? "N/A"})` },
                      { label: "Grant Success", value: `${ctx.grants?.success_rate_pct ?? 0}%` },
                      { label: "Collaborations", value: ctx.research?.total_collaborations ?? 0 },
                      { label: "AI Memory", value: ctx.sie?.memory_configured ? "Configured" : "Not configured" },
                    ].map(({ label, value }) => (
                      <div key={label} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, padding: "4px 0", borderBottom: `1px solid ${BRD}` }}>
                        <span style={{ color: TEXT_SECONDARY }}>{label}</span>
                        <span style={{ fontWeight: 600, color: NAVY }}>{value}</span>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              <Button
                onClick={() => navigate("/sie/daily")}
                className="w-full"
                style={{ background: `linear-gradient(135deg, ${EMERALD}, #059669)` }}
              >
                <Calendar size={16} /> View Today's Agenda
              </Button>
              <Button variant="ghost" onClick={load} className="w-full" style={{ marginTop: 8 }}>
                <RefreshCw size={13} /> Refresh
              </Button>
            </>
          )}
        </div>
      </div>
    </AIWorkspaceLayout>
  );
}
