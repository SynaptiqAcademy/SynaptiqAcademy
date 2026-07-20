/**
 * Today.jsx — Personalized Research Day (Phase XXIX).
 *
 * Adaptive landing page that reorganizes itself around each user's activity:
 *  - Continue Working  → last visited pages from localStorage
 *  - Dynamic Quick Actions → reranked by tool usage frequency
 *  - Mode Banner       → detected from recent activity (writing / grant / teaching…)
 *  - Weekly Insights   → behavioral analysis surfaced as actionable tips
 *  - Deadlines + Feed  → live data from /discover/feed
 */

import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { DashboardLayout } from "@/layouts";
import { useAuth }           from "../contexts/AuthContext";
import api                   from "../lib/api";
import { getDashboardMode }  from "../lib/dashboardConfig";
import { QUICK_ACTIONS }     from "../config/navigation";
import { getRecentPages }    from "../hooks/useRecentPages";
import {
  rankActions, inferMode, generateInsights, getTopPaths,
} from "../hooks/useUserMemory";
import DeadlinesWidget       from "../components/ai/DeadlinesWidget";
import ReputationWidget      from "../components/reputation/ReputationWidget";
import AiBriefing            from "../components/proactive/AiBriefing";
import { ACCENT, NAVY, WARM } from "@/lib/tokens";
import {
  ArrowRight, BrainCircuit, Calendar, Coins, Sparkles, Clock,
  TrendingUp, Zap, Target, Activity, BookMarked, BarChart2,
  FileText, Users, BadgeDollarSign, Lightbulb, Sun,
  FolderOpen, GraduationCap, BookOpen, ClipboardCheck, Award,
  Microscope, AlignLeft, BarChart3, Brain, Waypoints,
  ChevronRight, FlaskConical, LayoutGrid,
} from "lucide-react";

// ─── Brand tokens ─────────────────────────────────────────────────────────────

const NAVY2  = "#0a1d38";
const BORDER = "#E4E8EF";

// ─── Working mode config ──────────────────────────────────────────────────────

const MODE_CONFIG = {
  writing:  { label: "Writing Mode",         color: "#1D4ED8", bg: "#EFF6FF", icon: FileText },
  grant:    { label: "Grant Mode",            color: "#B45309", bg: "#FFFBEB", icon: BadgeDollarSign },
  teaching: { label: "Teaching Mode",         color: "#047857", bg: "#F0FDF4", icon: GraduationCap },
  admin:    { label: "Administration Mode",   color: "#7C3AED", bg: "#F5F3FF", icon: LayoutGrid },
  review:   { label: "Review Mode",           color: "#DC2626", bg: "#FEF2F2", icon: Microscope },
  research: { label: "Research Mode",         color: "#0F2847", bg: "#F8FAFC", icon: FlaskConical },
};

// ─── Mode-specific spotlight tools ───────────────────────────────────────────

const MODE_SPOTLIGHT = {
  writing: [
    { label: "Manuscripts",         to: "/manuscripts",        icon: FileText,    desc: "Continue writing your current manuscript." },
    { label: "Journal Finder",      to: "/journals",           icon: BookMarked,  desc: "Find the right journal for your paper." },
    { label: "Manuscript Review",   to: "/manuscript-review",  icon: Microscope,  desc: "Get AI feedback before submission." },
    { label: "Abstract Generator",  to: "/ai/abstract",        icon: AlignLeft,   desc: "Generate a structured abstract." },
    { label: "AI Rewriting",        to: "/ai/rewrite",         icon: Sparkles,    desc: "Improve clarity and flow." },
    { label: "Publication Hub",     to: "/publication-hub",    icon: BookOpen,    desc: "Track your submission pipeline." },
  ],
  grant: [
    { label: "Grant Discovery",     to: "/grants",             icon: BadgeDollarSign, desc: "Find open calls matching your profile." },
    { label: "My Applications",     to: "/grant-applications", icon: ClipboardCheck,  desc: "Track your active applications." },
    { label: "Grant Teams",         to: "/grant-collaboration-hub", icon: Users,   desc: "Find collaborators for consortium grants." },
    { label: "Funding Sources",     to: "/funding",            icon: Coins,       desc: "Explore funding opportunities." },
    { label: "Research Goals",      to: "/sie/goals",          icon: Target,      desc: "Align your goals with funding priorities." },
    { label: "Collaboration AI",    to: "/collaboration-intelligence", icon: BrainCircuit, desc: "AI-matched co-investigators." },
  ],
  teaching: [
    { label: "Lesson Planner",      to: "/teaching/lesson-planner",   icon: BookOpen,     desc: "Build structured lesson plans." },
    { label: "Assessment Builder",  to: "/teaching/assessment-builder", icon: ClipboardCheck, desc: "Design assessments and rubrics." },
    { label: "Teaching Workspaces", to: "/teaching/workspaces",        icon: FolderOpen,   desc: "AI teaching assistant inside every course." },
    { label: "Teaching Portfolio",  to: "/teaching/portfolio",         icon: Award,        desc: "Document your teaching philosophy." },
    { label: "Teaching Hub",        to: "/teaching",                   icon: GraduationCap,desc: "Your full teaching dashboard." },
    { label: "Teaching Analytics",  to: "/teaching/analytics",         icon: BarChart2,    desc: "Track engagement and outcomes." },
  ],
  research: [
    { label: "Literature Review",   to: "/literature-review",  icon: BookMarked,  desc: "AI synthesis across hundreds of papers." },
    { label: "Research Gaps",       to: "/research-gap-finder", icon: Target,     desc: "Find unanswered questions in your field." },
    { label: "Statistical Review",  to: "/statistical-review", icon: BarChart2,   desc: "AI review of your methods and data." },
    { label: "Research Impact",     to: "/research-impact",    icon: Activity,    desc: "Your h-index, citations, and influence." },
    { label: "Projects",            to: "/projects",           icon: FolderOpen,  desc: "Your active research projects." },
    { label: "Collaboration AI",    to: "/collaboration-intelligence", icon: Users, desc: "AI-matched collaborator suggestions." },
  ],
  admin: [
    { label: "Institution Hub",     to: "/institution-hub",    icon: LayoutGrid,  desc: "Institution overview and governance." },
    { label: "Institution Health",  to: "/institution-platform/health", icon: Activity, desc: "Real-time institution health metrics." },
    { label: "Faculty Intelligence", to: "/institution-platform/faculty", icon: Users, desc: "Faculty performance and activity." },
    { label: "Grant Intelligence",  to: "/institution-platform/grants", icon: BadgeDollarSign, desc: "Institution-wide funding overview." },
    { label: "Forecast Center",     to: "/institution-platform/forecast", icon: TrendingUp, desc: "Research output and revenue forecasts." },
    { label: "Institution Reports", to: "/institution-platform/reports", icon: FileText, desc: "Exportable executive reports." },
  ],
  review: [
    { label: "Manuscript Review",   to: "/manuscript-review",   icon: Microscope,  desc: "AI-structured manuscript feedback." },
    { label: "Reviewer Marketplace", to: "/reviewer-marketplace", icon: Users,     desc: "Find peer reviewers for your paper." },
    { label: "My Reviews",          to: "/reviews",              icon: ClipboardCheck, desc: "Track your review requests." },
    { label: "Citation Monitoring", to: "/citation-monitoring",  icon: TrendingUp,  desc: "Track citations of your published work." },
    { label: "Research Impact",     to: "/research-impact",      icon: Activity,    desc: "Citation metrics and h-index." },
    { label: "Integrity Report",    to: "/integrity",            icon: Microscope,  desc: "Academic integrity analysis." },
  ],
};

const INSIGHT_ICON_MAP = {
  brain:    BrainCircuit,
  trending: TrendingUp,
  star:     Sparkles,
  arrow:    ArrowRight,
  activity: Activity,
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getGreeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

function formatDate() {
  return new Date().toLocaleDateString("en-GB", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  });
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Today() {
  const { user }         = useAuth();
  const [feed, setFeed]  = useState(null);
  const [recent,  setRecent]   = useState([]);
  const [actions, setActions]  = useState([]);
  const [mode,    setMode]     = useState("research");
  const [insights,setInsights] = useState([]);

  const dashboardMode = getDashboardMode(user);

  useEffect(() => {
    api.get("/discover/feed").then((r) => setFeed(r.data)).catch(() => setFeed({}));

    const pages = getRecentPages().slice(0, 4);
    setRecent(pages);

    const top = getTopPaths(8);
    const detected = inferMode(top);
    setMode(detected);
    setInsights(generateInsights());
    setActions(rankActions(QUICK_ACTIONS).slice(0, 6));
  }, []);

  const firstName  = user?.full_name?.split(" ")[0] || "Researcher";
  const modeConfig = MODE_CONFIG[mode] || MODE_CONFIG.research;
  const spotlight  = MODE_SPOTLIGHT[mode] || MODE_SPOTLIGHT.research;

  if (!feed) return <TodaySkeleton />;

  return (
    <DashboardLayout
      greeting={
        <TodayHeader
          firstName={firstName}
          user={user}
          modeConfig={modeConfig}
          dashboardMode={dashboardMode}
        />
      }
      banner={<AiBriefing />}
    >
      {/* ── CONTINUE WORKING ─────────────────────────────────────────────── */}
      {recent.length > 0 && <ContinueWorking pages={recent} />}

      {/* ── DYNAMIC QUICK ACTIONS ────────────────────────────────────────── */}
      <QuickActionsGrid actions={actions} />

      {/* ── MAIN GRID ────────────────────────────────────────────────────── */}
      <div className="grid gap-7 mt-7 items-start lg:grid-cols-[1fr_300px]">

        {/* Left column */}
        <div className="flex flex-col gap-8">

          {/* Weekly Insights */}
          {insights.length > 0 && <InsightsPanel insights={insights} />}

          {/* Deadlines */}
          <SectionBlock label="Upcoming Deadlines" icon={Calendar}>
            <DeadlinesWidget limit={5} />
          </SectionBlock>

          {/* Mode-specific tools */}
          <ModeSpotlight modeConfig={modeConfig} items={spotlight} />
        </div>

        {/* Right panel */}
        <aside className="flex flex-col gap-6">
          <AIEntryCard />

          {feed.grants?.length > 0 && (
            <PanelBlock title="Funding Calls" icon={Coins}>
              <div className="flex flex-col gap-3">
                {feed.grants.slice(0, 3).map((g) => (
                  <div key={g.id} style={{ borderLeft: `2px solid ${NAVY}`, paddingLeft: 12 }}>
                    <div className="text-[13px] font-medium text-slate-900 leading-snug">{g.title}</div>
                    <div className="text-[11px] text-slate-400 mt-1">{g.amount} · Deadline {g.deadline}</div>
                  </div>
                ))}
              </div>
            </PanelBlock>
          )}

          {feed.conferences?.length > 0 && (
            <PanelBlock title="Upcoming Conferences" icon={Calendar}>
              <div className="flex flex-col gap-3">
                {feed.conferences.slice(0, 3).map((c) => (
                  <div key={c.id} style={{ borderLeft: `2px solid ${BORDER}`, paddingLeft: 12 }}>
                    <div className="text-[13px] font-medium text-slate-900 leading-snug">{c.name}</div>
                    <div className="text-[11px] text-slate-400 mt-1">{c.location} · {c.date}</div>
                  </div>
                ))}
              </div>
            </PanelBlock>
          )}

          <ReputationWidget />
        </aside>
      </div>
    </DashboardLayout>
  );
}

// ─── Today Header ─────────────────────────────────────────────────────────────

function TodayHeader({ firstName, user, modeConfig, dashboardMode }) {
  const ModeIcon = modeConfig.icon;

  const subLabel =
    dashboardMode === "teaching" ? "Education Operating System" :
    dashboardMode === "hybrid"   ? "Research & Education OS" :
    "Research Operating System";

  return (
    <div style={{ background: NAVY, margin: "-24px -24px 28px", padding: "36px 28px 24px" }}>
      <div className="flex items-end justify-between gap-4 flex-wrap">
        {/* Greeting */}
        <div>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.38)", letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 600, marginBottom: 8 }}>
            {formatDate()}
          </div>
          <h1 style={{ fontSize: 25, fontWeight: 700, color: "white", margin: "0 0 5px", letterSpacing: "-0.03em", lineHeight: 1.15 }}>
            {getGreeting()}, {firstName}.
          </h1>
          <div style={{ fontSize: 13, color: "rgba(255,255,255,0.42)", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span>{subLabel}</span>
            {user?.institution && (
              <>
                <span style={{ color: "rgba(255,255,255,0.18)" }}>·</span>
                <span>{user.institution}</span>
              </>
            )}
          </div>
        </div>

        {/* Status strip */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Mode badge */}
          <div
            className="flex items-center gap-1.5 text-[11px] font-semibold px-3 py-1.5"
            style={{ background: modeConfig.color + "22", color: modeConfig.color, border: `1px solid ${modeConfig.color}44` }}
          >
            <ModeIcon size={10} strokeWidth={2} />
            {modeConfig.label}
          </div>

          {/* Credits */}
          {user?.credits_remaining != null && (
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "rgba(255,255,255,0.6)", border: "1px solid rgba(255,255,255,0.12)", padding: "5px 12px" }}>
              <Zap size={11} strokeWidth={1.5} style={{ color: "#FCD34D" }} />
              <span style={{ fontFamily: "monospace", fontWeight: 600 }}>{user.credits_remaining}</span>
              <span style={{ color: "rgba(255,255,255,0.3)" }}>credits</span>
            </div>
          )}

          {/* AI CTA */}
          <Link
            to="/ai"
            style={{ display: "inline-flex", alignItems: "center", gap: 7, background: ACCENT, color: "white", padding: "8px 14px", fontSize: 12, fontWeight: 600, textDecoration: "none" }}
          >
            <BrainCircuit size={12} strokeWidth={1.5} />
            Synaptiq AI
            <ArrowRight size={11} strokeWidth={2} />
          </Link>
        </div>
      </div>
    </div>
  );
}

// ─── Continue Working ─────────────────────────────────────────────────────────

function ContinueWorking({ pages }) {
  return (
    <section className="mb-6">
      <div className="flex items-center gap-2 mb-3">
        <Clock size={11} strokeWidth={1.5} className="text-slate-400" />
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94A3B8" }}>
          Continue Working
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {pages.map((page) => {
          const Icon = page.icon || ChevronRight;
          return (
            <Link
              key={page.to}
              to={page.to}
              className="flex items-center gap-2 border border-slate-200 bg-white px-3 py-2 text-[13px] font-medium text-slate-700 hover:border-slate-300 hover:text-slate-900 hover:shadow-sm transition-all duration-100"
            >
              <Icon size={12} strokeWidth={1.5} className="text-slate-400 shrink-0" />
              <span>{page.label}</span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

// ─── Dynamic Quick Actions grid ───────────────────────────────────────────────

function QuickActionsGrid({ actions }) {
  if (!actions?.length) return null;
  return (
    <section className="mb-2">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Zap size={11} strokeWidth={1.5} className="text-slate-400" />
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94A3B8" }}>
            Quick Actions
          </span>
        </div>
        <span style={{ fontSize: 10, color: "#CBD5E1" }}>sorted by your usage</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 7 }}>
        {actions.map((action) => {
          const Icon = action.icon || ChevronRight;
          return (
            <Link
              key={action.to}
              to={action.to}
              className="flex items-center gap-2 border border-slate-200 bg-white px-3 py-2.5 text-[13px] font-medium text-slate-600 hover:border-slate-300 hover:text-slate-900 hover:shadow-sm transition-all duration-100"
            >
              <Icon size={13} strokeWidth={1.5} className="text-slate-400 shrink-0" />
              <span className="truncate">{action.label}</span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

// ─── Weekly Insights panel ────────────────────────────────────────────────────

function InsightsPanel({ insights }) {
  return (
    <section>
      <div className="flex items-center gap-2 pb-3 mb-4" style={{ borderBottom: `1px solid ${BORDER}` }}>
        <Lightbulb size={12} strokeWidth={1.5} style={{ color: NAVY }} />
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#64748B" }}>
          This Week's Insights
        </span>
      </div>
      <div className="flex flex-col gap-3">
        {insights.map((insight) => {
          const Icon = INSIGHT_ICON_MAP[insight.icon] || Lightbulb;
          return (
            <div
              key={insight.id}
              className="flex items-start gap-3 p-3 border border-slate-100 bg-white"
            >
              <div className="w-7 h-7 flex items-center justify-center bg-slate-50 shrink-0 mt-0.5">
                <Icon size={12} strokeWidth={1.5} className="text-slate-500" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[13px] text-slate-700 leading-relaxed m-0">
                  {insight.text}
                </p>
                {insight.to && (
                  <Link
                    to={insight.to}
                    className="inline-flex items-center gap-1 text-[11px] font-medium mt-1.5 transition-colors"
                    style={{ color: NAVY }}
                  >
                    Go there
                    <ArrowRight size={9} strokeWidth={2} />
                  </Link>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ─── Mode-specific spotlight ──────────────────────────────────────────────────

function ModeSpotlight({ modeConfig, items }) {
  return (
    <section>
      <div className="flex items-center gap-2 pb-3 mb-4" style={{ borderBottom: `1px solid ${BORDER}` }}>
        <div className="w-2 h-2 rounded-full shrink-0" style={{ background: modeConfig.color }} />
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#64748B" }}>
          {modeConfig.label} — Suggested Tools
        </span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className="flex flex-col gap-2 border border-slate-200 bg-white p-4 no-underline hover:border-slate-300 hover:shadow-sm transition-all duration-100"
            >
              <Icon size={14} strokeWidth={1.5} style={{ color: NAVY }} />
              <div className="text-[13px] font-semibold text-slate-800 leading-snug">{item.label}</div>
              <p className="text-[11px] text-slate-500 leading-relaxed m-0">{item.desc}</p>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

// ─── AI Entry Card ────────────────────────────────────────────────────────────

function AIEntryCard() {
  const AI_LINKS = [
    { label: "Literature Review",     to: "/literature-review",  credit: 20 },
    { label: "Manuscript Review",     to: "/manuscript-review",  credit: 20 },
    { label: "Research Gap Finder",   to: "/research-gap-finder", credit: 10 },
    { label: "Statistical Analysis",  to: "/statistical-review", credit: 25 },
    { label: "Generate Abstract",     to: "/ai/abstract",        credit: 5  },
    { label: "AI Rewriting",          to: "/ai/rewrite",         credit: 2  },
  ];
  return (
    <div style={{ background: NAVY, overflow: "hidden" }}>
      <div style={{ padding: "18px 18px 12px" }}>
        <div className="flex items-center gap-2 mb-2">
          <BrainCircuit size={12} strokeWidth={1.5} style={{ color: "rgba(255,255,255,0.45)" }} />
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.35)" }}>
            Synaptiq AI
          </span>
        </div>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: "white", margin: "0 0 3px", letterSpacing: "-0.01em" }}>
          Your research partner
        </h3>
        <p style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", lineHeight: 1.55, margin: 0 }}>
          Powered by Claude. Review papers, synthesize literature, analyze citations.
        </p>
      </div>
      <div style={{ padding: "2px 10px 10px" }}>
        {AI_LINKS.map(({ label, to, credit }) => (
          <Link
            key={to}
            to={to}
            className="flex items-center justify-between py-1.5 px-2 text-[12px] no-underline transition-all duration-100"
            style={{ color: "rgba(255,255,255,0.5)" }}
            onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.06)"; e.currentTarget.style.color = "white"; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "rgba(255,255,255,0.5)"; }}
          >
            <span>{label}</span>
            <span style={{ fontSize: 10, fontFamily: "monospace", color: "rgba(255,255,255,0.22)" }}>{credit} cr</span>
          </Link>
        ))}
        <div style={{ borderTop: "1px solid rgba(255,255,255,0.07)", marginTop: 6, paddingTop: 6 }}>
          <Link
            to="/ai"
            className="flex items-center justify-between p-2 text-[12px] font-semibold text-white no-underline transition-all duration-150"
            style={{ background: ACCENT }}
            onMouseEnter={(e) => e.currentTarget.style.background = "#a01a42"}
            onMouseLeave={(e) => e.currentTarget.style.background = ACCENT}
          >
            Open Synaptiq AI
            <ArrowRight size={12} strokeWidth={2} />
          </Link>
        </div>
      </div>
    </div>
  );
}

// ─── Section block ────────────────────────────────────────────────────────────

function SectionBlock({ label, icon: Icon, children }) {
  return (
    <section>
      <div className="flex items-center gap-2 pb-3 mb-4" style={{ borderBottom: `1px solid ${BORDER}` }}>
        {Icon && <Icon size={12} strokeWidth={1.5} style={{ color: NAVY }} />}
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#64748B" }}>
          {label}
        </span>
      </div>
      {children}
    </section>
  );
}

// ─── Panel Block ──────────────────────────────────────────────────────────────

function PanelBlock({ title, icon: Icon, children }) {
  return (
    <div>
      <div className="flex items-center gap-2 pb-3 mb-3" style={{ borderBottom: `1px solid ${BORDER}` }}>
        {Icon && <Icon size={11} strokeWidth={1.5} style={{ color: NAVY }} />}
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#64748B" }}>
          {title}
        </span>
      </div>
      {children}
    </div>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function TodaySkeleton() {
  return (
    <div>
      <style>{`@keyframes sk-pulse{0%,100%{opacity:1}50%{opacity:.45}}`}</style>
      <div style={{ background: "#E2E8F0", height: 132, margin: "-24px -24px 28px", animation: "sk-pulse 1.6s ease-in-out infinite" }} />
      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        {[1,2,3,4].map(i => <div key={i} style={{ background: "#E2E8F0", height: 36, width: 130, animation: "sk-pulse 1.6s ease-in-out infinite" }} />)}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6,1fr)", gap: 7, marginBottom: 28 }}>
        {[1,2,3,4,5,6].map(i => <div key={i} style={{ background: "#E2E8F0", height: 38, animation: "sk-pulse 1.6s ease-in-out infinite" }} />)}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 28 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {[80,120,200].map(h => <div key={h} style={{ background: "#E2E8F0", height: h, animation: "sk-pulse 1.6s ease-in-out infinite" }} />)}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {[180,110].map(h => <div key={h} style={{ background: "#E2E8F0", height: h, animation: "sk-pulse 1.6s ease-in-out infinite" }} />)}
        </div>
      </div>
    </div>
  );
}
