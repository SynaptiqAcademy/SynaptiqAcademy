import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { BRD, BRDH, NAVY, WARM } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import {
  Coins, Plus, Target, Users, Clock, BarChart2,
  ChevronRight, ArrowRight, CheckCircle2, XCircle,
  AlertCircle, FileText, Archive, Layers, ClipboardCheck,
  Calendar, TrendingUp,
} from "lucide-react";
import { EmptyState } from "@/components/ds/EmptyState";
import { SkeletonPage } from "@/components/ds/LoadingState";
import { FilterChip } from "@/components/ds/SearchBar";

// ─── Brand tokens ─────────────────────────────────────────────────────────────
const EMRL  = "#059669";

// ─── Status system ────────────────────────────────────────────────────────────
const STATUS = {
  draft:                 { label: "Draft",             color: "#64748B", bg: "#F8FAFC", border: "#CBD5E1" },
  in_preparation:        { label: "In Preparation",    color: "#0369A1", bg: "#EFF6FF", border: "#BAE6FD" },
  internal_review:       { label: "Internal Review",   color: "#B45309", bg: "#FFFBEB", border: "#FCD34D" },
  ready_for_submission:  { label: "Ready to Submit",   color: "#0891B2", bg: "#ECFEFF", border: "#67E8F9" },
  submitted:             { label: "Submitted",         color: "#4338CA", bg: "#EEF2FF", border: "#A5B4FC" },
  eligible:              { label: "Eligible",          color: "#0F766E", bg: "#F0FDFA", border: "#99F6E4" },
  under_evaluation:      { label: "Under Evaluation",  color: "#B45309", bg: "#FFFBEB", border: "#FCD34D" },
  funded:                { label: "Funded",            color: EMRL,      bg: "#ECFDF5", border: "#6EE7B7" },
  rejected:              { label: "Rejected",          color: "#DC2626", bg: "#FEF2F2", border: "#FCA5A5" },
  closed:                { label: "Closed",            color: "#94A3B8", bg: "#F8FAFC", border: "#CBD5E1" },
  withdrawn:             { label: "Withdrawn",         color: "#94A3B8", bg: "#F8FAFC", border: "#CBD5E1" },
};

const PRIORITY_STATUSES = ["internal_review","ready_for_submission","under_evaluation"];

const fmtBudget = (amount, currency = "EUR") => {
  if (!amount) return null;
  const n = parseFloat(amount);
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M ${currency}`;
  if (n >= 1_000)     return `${(n / 1_000).toFixed(0)}K ${currency}`;
  return `${n} ${currency}`;
};

// ─── Lifecycle nav ────────────────────────────────────────────────────────────
function LifecycleNav({ current }) {
  const steps = [
    { to: "/manuscripts",        label: "Writing"      },
    { to: "/reviews",            label: "Peer Review"  },
    { to: "/publication-hub",    label: "Publishing"   },
    { to: "/repository",         label: "Archive"      },
    { to: "/grant-applications", label: "Applications" },
  ];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
      {steps.map((s, i) => {
        const isCur = s.to === current;
        return (
          <React.Fragment key={s.to}>
            {i > 0 && <ChevronRight size={10} strokeWidth={1.5} style={{ color: "#CBD5E1", flexShrink: 0 }} />}
            <Link
              to={s.to}
              style={{
                fontSize: 11, fontWeight: isCur ? 700 : 400,
                color: isCur ? NAVY : "#94A3B8",
                padding: "3px 7px",
                background: isCur ? "rgba(15,40,71,0.07)" : "transparent",
                borderRadius: 3, textDecoration: "none", whiteSpace: "nowrap",
              }}
            >
              {s.label}
            </Link>
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─── Status badge ─────────────────────────────────────────────────────────────
function Badge({ status }) {
  const s = STATUS[status] || { label: status || "—", color: "#64748B", bg: "#F8FAFC", border: "#CBD5E1" };
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase",
      padding: "3px 8px", background: s.bg, color: s.color, border: `1px solid ${s.border}`,
      whiteSpace: "nowrap",
    }}>
      {s.label}
    </span>
  );
}

// ─── Analytics panel ──────────────────────────────────────────────────────────
function AnalyticsPanel({ data }) {
  if (!data) return null;
  const items = [
    { label: "Total Applications", value: data.total_applications ?? 0, icon: Target,    accent: NAVY    },
    { label: "Active",             value: data.active_applications ?? 0, icon: Clock,    accent: "#4338CA" },
    { label: "Funded",             value: data.funded ?? 0,              icon: Coins,    accent: EMRL    },
    { label: "Success Rate",       value: data.success_rate != null ? `${data.success_rate}%` : "—", icon: TrendingUp, accent: data.success_rate > 0 ? EMRL : "#94A3B8" },
  ];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 28 }}>
      {items.map(({ label, value, icon: Icon, accent }) => (
        <div key={label} style={{ background: "#fff", border: `1px solid ${BRD}`, padding: "16px 20px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
            <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94A3B8" }}>{label}</span>
            <Icon size={13} strokeWidth={1.5} style={{ color: accent }} />
          </div>
          <span style={{ fontSize: 26, fontWeight: 700, color: "#0F172A", fontFamily: "Georgia, serif", letterSpacing: "-0.02em", lineHeight: 1 }}>
            {value}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Application card ─────────────────────────────────────────────────────────
function ApplicationCard({ app }) {
  const [hov, setHov] = useState(false);
  const budget = fmtBudget(app.requested_budget, app.currency);

  return (
    <Link
      to={`/grant-applications/${app.id}`}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: "block", textDecoration: "none",
        background: "#fff",
        border: `1px solid ${hov ? BRDH : BRD}`,
        padding: "20px 24px",
        boxShadow: hov ? "0 4px 20px rgba(15,23,42,0.09)" : "none",
        transition: "border-color 150ms, box-shadow 150ms",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 20, justifyContent: "space-between" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: NAVY, marginBottom: 6 }}>
            {app.agency_name || "Grant Application"}
          </div>
          <h3 style={{
            fontSize: 16, fontWeight: 600, color: hov ? NAVY : "#0F172A",
            margin: 0, lineHeight: 1.4, fontFamily: "Georgia, serif",
            transition: "color 150ms",
          }}>
            {app.grant?.title || app.grant_title || "Untitled Grant"}
          </h3>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 10, flexWrap: "wrap" }}>
            {app.grant?.deadline && (
              <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, fontFamily: "monospace", color: "#94A3B8" }}>
                <Calendar size={10} strokeWidth={1.5} />
                Deadline: {app.grant.deadline}
              </span>
            )}
            {budget && (
              <span style={{ fontSize: 11, fontWeight: 600, color: EMRL, fontFamily: "monospace" }}>
                {budget}
              </span>
            )}
            {app.consortium_name && (
              <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, fontFamily: "monospace", color: "#64748B" }}>
                <Users size={10} strokeWidth={1.5} />
                {app.consortium_name}
              </span>
            )}
            {!app.is_pi && (
              <span style={{ fontSize: 10, fontWeight: 600, color: "#7C3AED", background: "#F5F3FF", border: "1px solid #C4B5FD", padding: "2px 6px" }}>
                Team Member
              </span>
            )}
            {app.updated_at && (
              <span style={{ fontSize: 10, fontFamily: "monospace", color: "#CBD5E1" }}>
                {new Date(app.updated_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
              </span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8, flexShrink: 0 }}>
          <Badge status={app.status} />
          <ChevronRight size={14} strokeWidth={1.5} style={{ color: hov ? NAVY : "#E2E8F0", transition: "color 150ms" }} />
        </div>
      </div>
    </Link>
  );
}

// ─── Skeleton ────────────────────────────────────────────────────────────────
function Skeleton() {
  return (
    <>
      <style>{`@keyframes rl-pulse{0%,100%{opacity:.45}50%{opacity:.2}}.rl-sk{background:#E2E8F0;animation:rl-pulse 1.8s ease-in-out infinite}`}</style>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 28 }}>
        {[1,2,3,4].map((i) => <div key={i} className="rl-sk" style={{ height: 80 }} />)}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {[1,2,3].map((i) => <div key={i} className="rl-sk" style={{ height: 90 }} />)}
      </div>
    </>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function GrantApplications() {
  const [apps, setApps]         = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [loading, setLoading]   = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [a, an] = await Promise.all([
        api.get("/grant-applications"),
        api.get("/grant-applications/analytics"),
      ]);
      setApps(a.data || []);
      setAnalytics(an.data);
    } catch { setApps([]); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const filtered = filterStatus ? apps.filter((a) => a.status === filterStatus) : apps;
  const activeStatuses = [...new Set(apps.map((a) => a.status).filter(Boolean))];

  const priority = filtered.filter((a) => PRIORITY_STATUSES.includes(a.status));
  const rest     = filtered.filter((a) => !PRIORITY_STATUSES.includes(a.status));

  const grantActions = (
    <div style={{ display: "flex", gap: 8 }}>
      <Link to="/grants" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", textDecoration: "none", padding: "8px 14px", border: `1px solid ${BRD}`, background: "#fff" }}>
        <Coins size={12} strokeWidth={1.5} /> Browse Grants
      </Link>
      <Link to="/grant-collaboration-hub" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", textDecoration: "none", padding: "8px 14px", border: `1px solid ${BRD}`, background: "#fff" }}>
        <Users size={12} strokeWidth={1.5} /> Grant Hub
      </Link>
    </div>
  );

  return (
    <ResearchLayout
      title="Grant Applications"
      subtitle="Track every application from discovery to award. Develop proposals, manage teams, plan budgets, and monitor deliverables."
      nav={<LifecycleNav current="/grant-applications" />}
      actions={grantActions}
    >
      <div style={{ paddingBottom: 64 }}>
        {loading ? (
          <SkeletonPage />
        ) : (
          <>
            {/* Analytics */}
            <AnalyticsPanel data={analytics} />

            {/* Filters */}
            {apps.length > 2 && (
              <div style={{ display: "flex", gap: 6, marginBottom: 24, flexWrap: "wrap" }}>
                <FilterChip
                  label="All"
                  active={!filterStatus}
                  onClick={() => setFilterStatus("")}
                />
                {activeStatuses.map((s) => (
                  <FilterChip
                    key={s}
                    label={(STATUS[s]?.label) || s}
                    active={filterStatus === s}
                    onClick={() => setFilterStatus(filterStatus === s ? "" : s)}
                  />
                ))}
              </div>
            )}

            {/* Priority applications */}
            {priority.length > 0 && (
              <div style={{ marginBottom: 28 }}>
                <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#B45309", marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
                  <AlertCircle size={11} strokeWidth={2} /> Action Required
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {priority.map((a) => <ApplicationCard key={a.id} app={a} />)}
                </div>
              </div>
            )}

            {/* All applications */}
            {rest.length > 0 && (
              <div>
                {priority.length > 0 && (
                  <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 12 }}>
                    All Applications
                  </div>
                )}
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {rest.map((a) => <ApplicationCard key={a.id} app={a} />)}
                </div>
              </div>
            )}

            {/* Empty states */}
            {filtered.length === 0 && apps.length === 0 && (
              <EmptyState
                icon={<Coins />}
                title="No grant applications yet"
                description='Discover funding opportunities that match your research profile. Click "Start Application" on any grant to open your proposal workspace.'
                action={
                  <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
                    <Link to="/grants" style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "#fff", textDecoration: "none", padding: "10px 18px", fontSize: 13, fontWeight: 600 }}>
                      <Coins size={13} strokeWidth={1.5} /> Browse Funding
                    </Link>
                    <Link to="/funding" style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "#fff", color: NAVY, textDecoration: "none", padding: "10px 18px", fontSize: 13, fontWeight: 600, border: `1px solid ${BRD}` }}>
                      Funding Sources
                    </Link>
                  </div>
                }
                size="lg"
                dashed={false}
              />
            )}
            {filtered.length === 0 && apps.length > 0 && (
              <EmptyState
                icon={<Target />}
                title="No applications match this filter"
                action={
                  <button onClick={() => setFilterStatus("")} style={{ fontSize: 12, color: NAVY, background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}>
                    Clear filter
                  </button>
                }
                size="sm"
              />
            )}

            {/* Lifecycle footer */}
            {apps.length > 0 && (
              <div style={{ marginTop: 48, paddingTop: 24, borderTop: `1px solid ${BRD}`, display: "flex", gap: 16, flexWrap: "wrap" }}>
                {[
                  { to: "/grants",             label: "Browse Grants",    icon: Coins },
                  { to: "/funding",            label: "Funding Sources",  icon: Target },
                  { to: "/manuscripts",        label: "Manuscripts",      icon: FileText },
                  { to: "/publication-hub",    label: "Publication Hub",  icon: Layers },
                  { to: "/repository",         label: "Repository",       icon: Archive },
                ].map(({ to, label, icon: Icon }) => (
                  <Link key={to} to={to} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", textDecoration: "none" }}>
                    <Icon size={12} strokeWidth={1.5} /> {label}
                    <ArrowRight size={10} strokeWidth={1.5} />
                  </Link>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </ResearchLayout>
  );
}
