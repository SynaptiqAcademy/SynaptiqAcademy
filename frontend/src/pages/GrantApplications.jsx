import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { BRD, BRDH, NAVY, WARM } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import {
  Coins, Plus, Target, Users, BarChart2,
  ChevronRight, CheckCircle2, XCircle,
  AlertCircle, Archive, ClipboardCheck,
  Calendar,
} from "lucide-react";
import { EmptyState } from "@/components/ds/EmptyState";
import { SkeletonPage } from "@/components/ds/LoadingState";
import { FilterChip } from "@/components/ds/SearchBar";
import { Badge as DsBadge } from "@/components/ds/Badge";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";

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
  return <DsBadge color={s.color}>{s.label}</DsBadge>;
}

// ─── Right rail — deadlines, status mix, and PI/team split from apps already loaded ─
function GrantApplicationsSidebar({ apps }) {
  const upcoming = apps
    .filter((a) => a.grant?.deadline && new Date(a.grant.deadline) >= new Date(new Date().toDateString()))
    .sort((a, b) => new Date(a.grant.deadline) - new Date(b.grant.deadline))
    .slice(0, 4);

  const statusCounts = {};
  apps.forEach((a) => { if (a.status) statusCounts[a.status] = (statusCounts[a.status] || 0) + 1; });
  const topStatuses = Object.entries(statusCounts).sort((a, b) => b[1] - a[1]).slice(0, 4);

  const piCount = apps.filter((a) => a.is_pi).length;
  const teamCount = apps.length - piCount;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Calendar size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Upcoming Deadlines</div>
        </div>
        {upcoming.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {upcoming.map((a) => (
              <Link key={a.id} to={`/grant-applications/${a.id}`} style={{ textDecoration: "none" }}>
                <div style={{ fontSize: 12.5, fontWeight: 600, color: "#0f172a", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {a.grant?.title || a.grant_title || "Untitled Grant"}
                </div>
                <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 1 }}>{a.grant.deadline}</div>
              </Link>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>
            No upcoming deadlines among your applications.
          </p>
        )}
      </Card>

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <BarChart2 size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>By Status</div>
        </div>
        {topStatuses.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {topStatuses.map(([s, count]) => (
              <div key={s} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontSize: 12, color: "#374151" }}>{STATUS[s]?.label || s}</span>
                <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a", fontFamily: "monospace" }}>{count}</span>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: 12, color: "#94A3B8", margin: 0, lineHeight: 1.5 }}>No applications yet.</p>
        )}
      </Card>

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
          <Users size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Your Role</div>
        </div>
        <div style={{ display: "flex", gap: 20 }}>
          <div>
            <div style={{ fontFamily: "Georgia, serif", fontSize: 22, fontWeight: 700, color: "#0f172a" }}>{piCount}</div>
            <div style={{ fontSize: 10, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.05em" }}>As PI</div>
          </div>
          <div>
            <div style={{ fontFamily: "Georgia, serif", fontSize: 22, fontWeight: 700, color: "#0f172a" }}>{teamCount}</div>
            <div style={{ fontSize: 10, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.05em" }}>As Team Member</div>
          </div>
        </div>
      </Card>
    </div>
  );
}

// ─── Application card ─────────────────────────────────────────────────────────
function ApplicationCard({ app }) {
  const budget = fmtBudget(app.requested_budget, app.currency);

  return (
    <Card to={`/grant-applications/${app.id}`} padding="lg">
      <div style={{ display: "flex", alignItems: "flex-start", gap: 20, justifyContent: "space-between" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: NAVY, marginBottom: 6 }}>
            {app.agency_name || "Grant Application"}
          </div>
          <h3 style={{
            fontSize: 16, fontWeight: 600, color: "#0F172A",
            margin: 0, lineHeight: 1.4, fontFamily: "Georgia, serif",
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
              <DsBadge color="#7C3AED">Team Member</DsBadge>
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
          <ChevronRight size={14} strokeWidth={1.5} style={{ color: "#E2E8F0" }} />
        </div>
      </div>
    </Card>
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
      <Button as={Link} to="/grants" variant="hero" size="sm">
        <Coins size={12} strokeWidth={1.5} /> Browse Grants
      </Button>
      <Button as={Link} to="/grant-collaboration-hub" variant="hero" size="sm">
        <Users size={12} strokeWidth={1.5} /> Grant Hub
      </Button>
    </div>
  );

  return (
    <ResearchLayout
      title="Grant Applications"
      subtitle="Track every application from discovery to award. Develop proposals, manage teams, plan budgets, and monitor deliverables."
      nav={<LifecycleNav current="/grant-applications" />}
      actions={grantActions}
      stats={!loading && analytics ? [
        { label: "Total Applications", value: analytics.total_applications ?? 0 },
        { label: "Active",             value: analytics.active_applications ?? 0 },
        { label: "Funded",             value: analytics.funded ?? 0 },
        { label: "Success Rate",       value: analytics.success_rate != null ? `${analytics.success_rate}%` : "—" },
      ] : undefined}
      sidebar={!loading && apps.length > 0 ? <GrantApplicationsSidebar apps={apps} /> : undefined}
    >
      <div style={{ paddingBottom: 64 }}>
        {loading ? (
          <SkeletonPage />
        ) : (
          <>
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
                    <Button as={Link} to="/grants" variant="primary" size="md">
                      <Coins size={13} strokeWidth={1.5} /> Browse Funding
                    </Button>
                    <Button as={Link} to="/funding" variant="outline" size="md">
                      Funding Sources
                    </Button>
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
                  <Button variant="link" size="sm" onClick={() => setFilterStatus("")}>
                    Clear filter
                  </Button>
                }
                size="sm"
              />
            )}

          </>
        )}
      </div>
    </ResearchLayout>
  );
}
