/* eslint-disable */
/**
 * AISuite — Research AI Suite gateway.
 *
 * Positions AI as a premium enhancement layer that researchers reach AFTER
 * they have built their profile, joined the community, created workspaces,
 * and started publications. Never presents AI as the starting point.
 *
 * Pulls real data from:
 *   GET /api/billing/subscription  → credit balance
 *   GET /api/ai/usage              → recent sessions + consumption
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import {
  BrainCircuit, BookMarked, Target, FlaskConical, BarChart2, Microscope,
  PenLine, AlignLeft, Sparkles, Users, TrendingUp, Coins, Activity,
  ChevronRight, ArrowRight, Bot, Cpu, Lightbulb, Clock, Info,
} from "lucide-react";
import { Spinner } from "@/components/ds/LoadingState";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Tag } from "@/components/ds/Tag";
import { Alert } from "@/components/ds/Alert";
import { StatCard } from "@/components/ds/StatCard";
import { AIWorkspaceLayout } from "@/layouts";

// ─── Credit costs (mirrors plans_catalogue.py CREDIT_COSTS) ─────────────────
const CREDIT_COST = {
  "/literature-review":       20,
  "/research-gap-finder":     10,
  "/research-design-advisor": 10,
  "/ai":                       2,
  "/ai/rewrite":               2,
  "/ai/abstract":              5,
  "/manuscript-review":       20,
  "/statistical-review":      25,
  "/collaboration-intelligence": 15,
  "/copilot":                  3,
  "/agent-workforce":          8,
  "/twin":                     0,
  "/recommendations":          0,
  "/research-impact":          0,
};

const CREDIT_UNIT = {
  "/literature-review":       "per review",
  "/research-gap-finder":     "per analysis",
  "/research-design-advisor": "per session",
  "/ai":                      "per message",
  "/ai/rewrite":              "per rewrite",
  "/ai/abstract":             "per abstract",
  "/manuscript-review":       "per review",
  "/statistical-review":      "per analysis",
  "/collaboration-intelligence": "per analysis",
  "/copilot":                 "per message",
  "/agent-workforce":         "per workflow",
  "/twin":                    "free",
  "/recommendations":         "free",
  "/research-impact":         "free",
};

// ─── AI Tool Categories ──────────────────────────────────────────────────────
const CATEGORIES = [
  {
    id: "preparation",
    label: "Research Preparation",
    description: "Understand the landscape before you write.",
    icon: FlaskConical,
    color: "#7C3AED",
    bg: "#FAF5FF",
    tools: [
      {
        to: "/literature-review",
        label: "Literature Review",
        icon: BookMarked,
        purpose: "AI synthesis of hundreds of papers into a structured review.",
        bestTime: "Before drafting — to map the field and identify gaps.",
        input: "Research topic or list of papers",
      },
      {
        to: "/research-gap-finder",
        label: "Research Gap Finder",
        icon: Target,
        purpose: "Identifies unanswered questions and underexplored angles in your field.",
        bestTime: "At the ideation stage — to select a novel research direction.",
        input: "Research area or existing paper abstract",
      },
      {
        to: "/research-design-advisor",
        label: "Study Design Advisor",
        icon: FlaskConical,
        purpose: "Recommends research design, methodology, and sampling strategies.",
        bestTime: "Before data collection — to validate your methodological approach.",
        input: "Research question and discipline context",
      },
    ],
  },
  {
    id: "writing",
    label: "Writing & Enhancement",
    description: "Improve academic writing quality and clarity.",
    icon: PenLine,
    color: "#2563EB",
    bg: "#EFF6FF",
    tools: [
      {
        to: "/ai",
        label: "AI Research Assistant",
        icon: BrainCircuit,
        purpose: "Context-aware academic assistant for any research question.",
        bestTime: "Any stage — for instant expert guidance on your work.",
        input: "Natural language question about your research",
      },
      {
        to: "/ai/rewrite",
        label: "Academic Rewriting",
        icon: PenLine,
        purpose: "Elevates academic writing to publication-ready standard.",
        bestTime: "After drafting — to polish tone, clarity, and academic register.",
        input: "Section of your manuscript",
      },
      {
        to: "/ai/abstract",
        label: "Abstract Generator",
        icon: AlignLeft,
        purpose: "Generates a structured, concise abstract from your full text.",
        bestTime: "After completing your manuscript — before journal submission.",
        input: "Full manuscript or key sections",
      },
    ],
  },
  {
    id: "review",
    label: "Review & Validation",
    description: "Validate methodology and prepare for peer review.",
    icon: Microscope,
    color: "#0891B2",
    bg: "#F0F9FF",
    tools: [
      {
        to: "/manuscript-review",
        label: "Manuscript Review",
        icon: Microscope,
        purpose: "Simulates peer review with structured feedback on all sections.",
        bestTime: "Before submission — to identify weaknesses reviewers will flag.",
        input: "Full manuscript (abstract + sections)",
      },
      {
        to: "/statistical-review",
        label: "Statistical Analysis",
        icon: BarChart2,
        purpose: "Reviews statistical methods, assumptions, and reporting standards.",
        bestTime: "After analysis — to ensure statistical rigor before review.",
        input: "Methods section and statistical outputs",
      },
    ],
  },
  {
    id: "collaboration",
    label: "Collaboration Intelligence",
    description: "Find the right partners and work smarter together.",
    icon: Users,
    color: "#D97706",
    bg: "#FFFBEB",
    tools: [
      {
        to: "/collaboration-intelligence",
        label: "Collaboration AI",
        icon: Users,
        purpose: "AI-powered matching with optimal collaborators based on 9 dimensions.",
        bestTime: "When forming a research team or seeking co-authors.",
        input: "Your research profile and project goals",
      },
      {
        to: "/copilot",
        label: "Research Copilot",
        icon: Sparkles,
        purpose: "Multi-engine AI team covering literature, writing, review, and funding.",
        bestTime: "Any stage — for orchestrated multi-step research assistance.",
        input: "Complex research objective or project description",
      },
      {
        to: "/agent-workforce",
        label: "Research Agents",
        icon: Bot,
        purpose: "Autonomous AI agents that execute complete research workflows.",
        bestTime: "For delegating systematic, multi-step research tasks.",
        input: "Research mission statement and parameters",
      },
    ],
  },
  {
    id: "impact",
    label: "Impact & Strategy",
    description: "Maximize the reach and impact of your research.",
    icon: TrendingUp,
    color: "#059669",
    bg: "#F0FDF4",
    tools: [
      {
        to: "/recommendations",
        label: "AI Recommendations",
        icon: Lightbulb,
        purpose: "Personalized research opportunities ranked by relevance and impact.",
        bestTime: "Ongoing — for staying aligned with high-impact opportunities.",
        input: "Your research profile (automatic)",
      },
      {
        to: "/research-impact",
        label: "Research Impact",
        icon: Activity,
        purpose: "Tracks your Synaptiq Impact Score, h-index, and benchmarks.",
        bestTime: "Periodically — to monitor research productivity and standing.",
        input: "Your publication record (automatic)",
      },
      {
        to: "/twin",
        label: "Research Twin",
        icon: Cpu,
        purpose: "Digital twin of your academic identity with goals and simulation.",
        bestTime: "For long-term strategic planning and career scenario modeling.",
        input: "Your complete academic profile (automatic)",
      },
    ],
  },
];

// ─── Recommended workflow stages ─────────────────────────────────────────────
const WORKFLOW_STEPS = [
  { label: "Build Profile",         to: "/profile-setup",   done: true,  color: "#059669" },
  { label: "Join Community",        to: "/network",          done: true,  color: "#059669" },
  { label: "Create Team",           to: "/teams",            done: true,  color: "#059669" },
  { label: "Open Workspace",        to: "/workspaces",       done: true,  color: "#059669" },
  { label: "Start Document",        to: "/manuscripts",      done: true,  color: "#059669" },
  { label: "AI Enhancement",        to: "/ai-suite",         done: false, color: "#0F2847", current: true },
];

// ─── Tool card ────────────────────────────────────────────────────────────────
function ToolCard({ tool }) {
  const Icon = tool.icon;
  const cost = CREDIT_COST[tool.to];
  const unit = CREDIT_UNIT[tool.to];
  return (
    <Card to={tool.to} padding="lg" className="group hover:border-[#0F2847]">
      <div className="flex items-start justify-between gap-2 mb-3">
        <Icon size={18} strokeWidth={1.5} className="text-[#0F2847] mt-0.5 shrink-0" />
        <Badge variant={cost === 0 ? "success" : "neutral"} size="sm" className="shrink-0">
          {cost === 0 ? "Free" : `${cost} credits ${unit}`}
        </Badge>
      </div>
      <div className="font-serif text-base text-slate-900 group-hover:text-[#0F2847] transition-colors mb-2">
        {tool.label}
      </div>
      <p className="text-xs text-slate-600 leading-relaxed mb-3">{tool.purpose}</p>
      <div className="text-[10px] font-mono text-slate-400 border-t border-slate-100 pt-2 flex items-center gap-1">
        <Clock size={9} strokeWidth={1.5} />
        {tool.bestTime}
      </div>
      <div className="mt-2 flex items-center gap-1 text-xs text-[#0F2847] opacity-0 group-hover:opacity-100 transition-opacity">
        Launch tool <ArrowRight size={11} strokeWidth={1.5} />
      </div>
    </Card>
  );
}

// ─── Credit balance widget ────────────────────────────────────────────────────
function CreditWidget({ balance, loading }) {
  return (
    <Card padding="lg" style={{ background: "#0F2847", borderColor: "#0F2847", color: "#fff" }}>
      <div className="flex items-center justify-between gap-6">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-slate-400">Research Credits</div>
          <div className="font-serif text-4xl mt-1 flex items-center">
            {loading ? <Spinner size={24} color="#ffffff" /> : (balance ?? 0).toLocaleString()}
          </div>
          <div className="text-xs text-slate-400 mt-1">available for AI tools</div>
        </div>
        <div className="flex flex-col gap-2 items-end">
          <Link
            to="/ai-credits"
            className="text-xs border border-white/30 text-white px-3 py-1.5 hover:bg-white/10 inline-flex items-center gap-1"
          >
            <Coins size={11} strokeWidth={1.5} />
            Manage credits
          </Link>
          <Link
            to="/settings/billing"
            className="text-xs text-slate-400 hover:text-white px-3 py-1.5 inline-flex items-center gap-1"
          >
            Purchase credits <ChevronRight size={10} strokeWidth={1.5} />
          </Link>
        </div>
      </div>
    </Card>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function AISuite() {
  const { user } = useAuth();
  const [balance, setBalance]   = useState(null);
  const [usage, setUsage]       = useState(null);
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/billing/subscription").catch(() => ({ data: null })),
      api.get("/ai/usage").catch(() => ({ data: null })),
    ]).then(([sub, u]) => {
      setBalance(sub.data?.credits?.balance ?? 0);
      setUsage(u.data);
    }).finally(() => setLoading(false));
  }, []);

  const recentActivity = (usage?.last_30d || [])
    .filter((d) => d.credits > 0)
    .slice(-7);

  const totalUsed30d = (usage?.last_30d || []).reduce((s, d) => s + (d.credits || 0), 0);

  const firstName = user?.full_name?.split(" ")[0] || "there";

  return (
    <AIWorkspaceLayout
      title="Research AI Suite"
      subtitle="AI tools designed to enhance existing research work — not replace it."
    >
      <div className="space-y-10">

        {/* ── Educational header ───────────────────────────────────────── */}
        <div className="grid lg:grid-cols-3 gap-5">
          <Card padding="lg" className="lg:col-span-2">
            <div className="overline flex items-center gap-2 mb-3">
              <Info size={12} strokeWidth={1.5} className="text-[#0F2847]" />
              How AI Suite works
            </div>
            <h2 className="font-serif text-2xl text-slate-900 mb-3">
              Your research is ready for AI enhancement
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed mb-5 max-w-2xl">
              AI Suite is a professional assistant layer — it improves, validates, and accelerates research that already exists.
              Every tool works best when applied to real work: a manuscript in progress, an active workspace, or a specific research question.
              AI never generates complete papers from scratch.
            </p>
            {/* Workflow arrow strip */}
            <div className="flex items-center gap-1 flex-wrap">
              {WORKFLOW_STEPS.map((step, i) => (
                <React.Fragment key={step.label}>
                  <Link to={step.to} style={{ textDecoration: "none" }}>
                    <Tag
                      variant={step.current || step.done ? "active" : "default"}
                      color={step.current ? "#0F2847" : step.done ? "#059669" : undefined}
                    >
                      {step.label}
                    </Tag>
                  </Link>
                  {i < WORKFLOW_STEPS.length - 1 && (
                    <ArrowRight size={10} strokeWidth={1.5} className="text-slate-300 shrink-0" />
                  )}
                </React.Fragment>
              ))}
            </div>
          </Card>

          {/* Credit widget */}
          <div>
            <CreditWidget balance={balance} loading={loading} />
            {totalUsed30d > 0 && (
              <StatCard
                className="mt-3"
                label="Last 30 days"
                value={totalUsed30d}
                sub="credits consumed — view analytics"
                to="/ai-usage"
              />
            )}
          </div>
        </div>

        {/* ── Quick-launch from workspace recommendation ────────────────── */}
        <Alert variant="warning" icon={Sparkles} title="Launch AI directly from your Workspace">
          <p className="leading-relaxed">
            Open any workspace, go to the <strong>AI Enhancement</strong> tab, and get tool recommendations
            matched to your document's current stage.
          </p>
          <Link to="/workspaces" className="mt-2 inline-flex items-center gap-1 text-xs border-b border-current hover:opacity-70">
            Go to Workspaces <ArrowRight size={10} strokeWidth={1.5} />
          </Link>
        </Alert>

        {/* ── Tool categories ───────────────────────────────────────────── */}
        {CATEGORIES.map((cat) => {
          const CatIcon = cat.icon;
          return (
            <section key={cat.id}>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-7 h-7 flex items-center justify-center" style={{ background: cat.bg }}>
                  <CatIcon size={14} strokeWidth={1.5} style={{ color: cat.color }} />
                </div>
                <div>
                  <div className="font-serif text-lg text-slate-900">{cat.label}</div>
                  <div className="text-xs text-slate-500">{cat.description}</div>
                </div>
              </div>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {cat.tools.map((tool) => (
                  <ToolCard key={tool.to} tool={tool} />
                ))}
              </div>
            </section>
          );
        })}

        {/* ── Quick navigation ──────────────────────────────────────────── */}
        <section>
          <div className="overline mb-3">Quick access</div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              { to: "/ai-credits",  label: "AI Credits",       icon: Coins,     desc: "Balance, packages, purchase" },
              { to: "/ai-usage",    label: "AI Analytics",     icon: Activity,  desc: "Usage trends, most used tools" },
              { to: "/copilot",     label: "Research Copilot", icon: Sparkles,  desc: "Multi-agent AI orchestration" },
              { to: "/workspaces",  label: "Research Workspaces", icon: FlaskConical, desc: "Launch AI from your documents" },
            ].map(({ to, label, icon: Icon, desc }) => (
              <Card key={to} to={to} padding="md" className="group hover:border-[#0F2847]">
                <div className="flex items-start gap-3">
                  <Icon size={15} strokeWidth={1.5} className="text-[#0F2847] mt-0.5 shrink-0" />
                  <div>
                    <div className="text-sm font-medium text-slate-900 group-hover:text-[#0F2847] transition-colors">{label}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{desc}</div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </section>

      </div>
    </AIWorkspaceLayout>
  );
}
