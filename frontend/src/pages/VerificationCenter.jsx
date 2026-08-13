import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ResearchLayout } from "@/layouts";
import { AI_NAV_ITEMS } from "@/lib/navItems";
import {
  Shield, Star, Award, CheckCircle, Circle, RefreshCw,
  ArrowUp, ArrowDown, FileText, ChevronRight,
  BookOpen, Users, Briefcase, GraduationCap, BarChart2,
  Clock, AlertCircle, Loader,
} from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { WARM } from "@/lib/tokens";
import {
  Card, Button, NavTabs, EmptyState, Badge, Input, FormSelect, Textarea,
  Alert, Callout, List, ListItem, SkeletonCard as DsSkeletonCard,
} from "@/components/ds";

// ── Research Intelligence Nav ─────────────────────────────────────────────────

const INTEL_NAV = [
  { to: "/analytics",           label: "Analytics"    },
  { to: "/research-impact",     label: "Impact"       },
  { to: "/impact-dashboard",    label: "Dashboard"    },
  { to: "/citations",           label: "Citations"    },
  { to: "/citation-monitoring", label: "Monitoring"   },
  { to: "/reputation",          label: "Reputation"   },
  { to: "/verification",        label: "Verification" },
];

function IntelNav({ current }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
      {INTEL_NAV.map((s, i) => {
        const isCur = s.to === current;
        return (
          <React.Fragment key={s.to}>
            {i > 0 && <ChevronRight size={10} strokeWidth={1.5} style={{ color: "#94A3B8", flexShrink: 0 }} />}
            <Link to={s.to} style={{ fontSize: 11, fontWeight: isCur ? 700 : 400, color: isCur ? "#0F2847" : "#94A3B8", padding: "3px 7px", background: isCur ? "rgba(15,40,71,0.07)" : "transparent", borderRadius: 3, textDecoration: "none", whiteSpace: "nowrap" }}>
              {s.label}
            </Link>
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

const LEVEL_NAMES = {
  0: "Unverified",
  1: "Email Verified",
  2: "Identity Verified",
  3: "ORCID Verified",
  4: "Institution Verified",
  5: "Researcher Verified",
  6: "Expert Verified",
  7: "Trusted Researcher",
  8: "Distinguished Scholar",
};

const LEVEL_ACCENT = {
  0: "#94A3B8",
  1: "#3B82F6",
  2: "#3B82F6",
  3: "#6366F1",
  4: "#8B5CF6",
  5: "#7C3AED",
  6: "#D97706",
  7: "#059669",
  8: "#B45309",
};

const STATUS_FLAGS = [
  { key: "email_verified",       label: "Email"       },
  { key: "orcid_verified",       label: "ORCID"       },
  { key: "institution_verified", label: "Institution" },
  { key: "researcher_verified",  label: "Researcher"  },
  { key: "reviewer_verified",    label: "Reviewer"    },
  { key: "mentor_verified",      label: "Mentor"      },
  { key: "expert_verified",      label: "Expert"      },
  { key: "grant_verified",       label: "Grant"       },
  { key: "teaching_verified",    label: "Teaching"    },
];

const EVIDENCE_TYPES = [
  { value: "employment_letter",    label: "Employment Letter" },
  { value: "institution_document", label: "Institution Document" },
  { value: "certificate",          label: "Certificate" },
  { value: "academic_credential",  label: "Academic Credential" },
  { value: "research_contract",    label: "Research Contract" },
  { value: "grant_document",       label: "Grant Document" },
  { value: "reviewer_invitation",  label: "Reviewer Invitation" },
  { value: "teaching_document",    label: "Teaching Document" },
  { value: "publication_record",   label: "Publication Record" },
  { value: "orcid_export",         label: "ORCID Export" },
  { value: "custom",               label: "Custom / Other" },
];

const SCORE_COMPONENTS = [
  { key: "email_verified",       label: "Email Verified",        max: 50  },
  { key: "orcid_verified",       label: "ORCID Verified",        max: 100 },
  { key: "institution_verified", label: "Institution Verified",  max: 100 },
  { key: "publications",         label: "Publications",          max: 150 },
  { key: "citations",            label: "Citations",             max: 100 },
  { key: "h_index",              label: "H-Index",               max: 100 },
  { key: "reputation",           label: "Reputation Score",      max: 150 },
  { key: "reviews",              label: "Peer Reviews",          max: 100 },
  { key: "collaborations",       label: "Collaborations",        max: 75  },
  { key: "teaching",             label: "Teaching Activity",     max: 50  },
  { key: "projects",             label: "Projects",              max: 25  },
];

const ROADMAP = {
  0: [{ text: "Verify your email address to reach Level 1", icon: CheckCircle, cta: "Go to Settings", href: "/settings" }],
  1: [
    { text: "Connect your ORCID iD to verify your identity", icon: Shield, cta: "Connect ORCID", tab: "overview" },
    { text: "Add your institution affiliation to verify identity", icon: Briefcase, cta: "Add Institution", href: "/academic-passport" },
  ],
  2: [
    { text: "Link your ORCID to reach Level 3 (ORCID Verified)", icon: Shield, cta: "Connect ORCID", tab: "overview" },
    { text: "Submit institution documents as evidence", icon: FileText, cta: "Submit Evidence", tab: "evidence" },
  ],
  3: [
    { text: "Add your institution affiliation to reach Level 4", icon: Briefcase, cta: "Update Profile", href: "/academic-passport" },
    { text: "Submit institution document as supporting evidence", icon: FileText, cta: "Submit Evidence", tab: "evidence" },
  ],
  4: [
    { text: "Add at least one publication to reach Level 5", icon: BookOpen, cta: "Add Publications", href: "/publications" },
    { text: "Submit academic credentials as evidence", icon: Award, cta: "Submit Evidence", tab: "evidence" },
  ],
  5: [
    { text: "Add 5 or more publications to reach Level 6", icon: BookOpen, cta: "Add Publications", href: "/publications" },
    { text: "Receive a peer review to strengthen your profile", icon: Star, cta: "View Reviews", href: "/academic-passport" },
    { text: "Submit publication records as evidence", icon: FileText, cta: "Submit Evidence", tab: "evidence" },
  ],
  6: [
    { text: "Build a high reputation score (500+) to reach Level 7", icon: BarChart2, cta: "View Reputation", href: "/reputation" },
    { text: "Establish 3+ active research collaborations", icon: Users, cta: "Find Collaborators", href: "/grants" },
    { text: "Earn additional verification badges", icon: Award, cta: "View Badges", tab: "overview" },
  ],
  7: [
    { text: "Reach 10+ publications for Distinguished Scholar", icon: BookOpen, cta: "Add Publications", href: "/publications" },
    { text: "Complete 5+ peer reviews", icon: Star, cta: "View Reviews", href: "/academic-passport" },
    { text: "Achieve 3+ teaching engagements and secure grants", icon: GraduationCap, cta: "Teaching Hub", href: "/teaching" },
  ],
  8: [{ text: "Maximum verification achieved — Distinguished Scholar", icon: Award, cta: null, href: null }],
};

// ── Utilities ─────────────────────────────────────────────────────────────────

function formatLabel(str) {
  return str.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

function BadgeIcon({ type }) {
  if (!type) return <Award className="w-5 h-5" />;
  const t = type.toLowerCase();
  if (t.includes("orcid") || t.includes("verified")) return <CheckCircle className="w-5 h-5" />;
  if (t.includes("expert") || t.includes("distinguished")) return <Star className="w-5 h-5" />;
  if (t.includes("trust") || t.includes("shield")) return <Shield className="w-5 h-5" />;
  return <Award className="w-5 h-5" />;
}

function historyIconBg(type) {
  if (!type) return "bg-slate-100 text-slate-500";
  const t = type.toLowerCase();
  if (t.includes("level_up") || t.includes("upgrade")) return "bg-emerald-100 text-emerald-600";
  if (t.includes("level_down") || t.includes("downgrade")) return "bg-red-100 text-red-500";
  if (t.includes("badge")) return "bg-blue-100 text-blue-600";
  if (t.includes("evidence")) return "bg-amber-100 text-amber-600";
  return "bg-slate-100 text-slate-500";
}

function HistoryIcon({ type }) {
  if (!type) return <FileText className="w-4 h-4" />;
  const t = type.toLowerCase();
  if (t.includes("level_up") || t.includes("upgrade")) return <ArrowUp className="w-4 h-4" />;
  if (t.includes("level_down") || t.includes("downgrade")) return <ArrowDown className="w-4 h-4" />;
  if (t.includes("badge")) return <CheckCircle className="w-4 h-4" />;
  if (t.includes("evidence")) return <FileText className="w-4 h-4" />;
  return <FileText className="w-4 h-4" />;
}

// ── Primitives ────────────────────────────────────────────────────────────────

function SectionHeader({ label, action }) {
  return (
    <div className="flex items-center justify-between mb-5">
      <h2 className="overline">{label}</h2>
      {action}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function VerificationCenter() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [profile, setProfile]           = useState(null);
  const [badges, setBadges]             = useState([]);
  const [breakdown, setBreakdown]       = useState(null);
  const [history, setHistory]           = useState([]);
  const [evidence, setEvidence]         = useState([]);
  const [loading, setLoading]           = useState(true);
  const [activeTab, setActiveTab]       = useState("overview");
  const [computing, setComputing]       = useState(false);
  const [orcidForm, setOrcidForm]       = useState({ orcid: "", submitting: false, msg: "" });
  const [evidenceForm, setEvidenceForm] = useState({
    evidence_type: "employment_letter",
    description:   "",
    submitting:    false,
    msg:           "",
  });

  useEffect(() => {
    const load = async () => {
      try {
        const [profileRes, badgesRes] = await Promise.all([
          api.get("/verification/me"),
          api.get("/verification/me/badges"),
        ]);
        setProfile(profileRes.data);
        setBadges(badgesRes.data || []);
      } catch {}
      setLoading(false);
    };
    load();
  }, []);

  const recompute = async () => {
    setComputing(true);
    try {
      const res = await api.post("/verification/me/compute");
      setProfile(res.data);
      const badgesRes = await api.get("/verification/me/badges");
      setBadges(badgesRes.data || []);
    } catch {}
    setComputing(false);
  };

  const loadBreakdown = async () => {
    try {
      const res = await api.get("/verification/me/trust-breakdown");
      setBreakdown(res.data);
    } catch {}
  };

  const loadHistory = async () => {
    try {
      const res = await api.get("/verification/me/history");
      setHistory(res.data || []);
    } catch {}
  };

  const loadEvidence = async () => {
    try {
      const res = await api.get("/verification/me/evidence");
      setEvidence(res.data || []);
    } catch {}
  };

  const switchTab = (tab) => {
    setActiveTab(tab);
    if (tab === "trust"    && !breakdown)            loadBreakdown();
    if (tab === "history"  && history.length === 0)  loadHistory();
    if (tab === "evidence" && evidence.length === 0) loadEvidence();
  };

  const submitOrcid = async (e) => {
    e.preventDefault();
    setOrcidForm((f) => ({ ...f, submitting: true, msg: "" }));
    try {
      await api.post("/verification/me/orcid", { orcid: orcidForm.orcid });
      setOrcidForm((f) => ({ ...f, submitting: false, msg: "ORCID submitted for verification." }));
      const profileRes = await api.get("/verification/me");
      setProfile(profileRes.data);
    } catch (err) {
      const msg = err?.response?.data?.detail || "Failed to submit ORCID.";
      setOrcidForm((f) => ({ ...f, submitting: false, msg }));
    }
  };

  const submitEvidence = async (e) => {
    e.preventDefault();
    setEvidenceForm((f) => ({ ...f, submitting: true, msg: "" }));
    try {
      await api.post("/verification/me/evidence", {
        evidence_type: evidenceForm.evidence_type,
        description:   evidenceForm.description,
      });
      setEvidenceForm((f) => ({ ...f, submitting: false, msg: "Evidence submitted. Pending review.", description: "" }));
      loadEvidence();
    } catch (err) {
      const msg = err?.response?.data?.detail || "Failed to submit evidence.";
      setEvidenceForm((f) => ({ ...f, submitting: false, msg }));
    }
  };

  // ── Loading ───────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <ResearchLayout
        navItems={AI_NAV_ITEMS}
        title="Verification Center"
        subtitle="Your academic identity, trust score, and verification status"
      >
        <div className="space-y-5">
          <DsSkeletonCard rows={5} />
          <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-3">
            {Array.from({ length: 9 }).map((_, i) => <div key={i} className="border border-slate-200 bg-slate-100 h-20 animate-pulse" />)}
          </div>
          {[1, 2].map((i) => <DsSkeletonCard key={i} rows={4} />)}
        </div>
      </ResearchLayout>
    );
  }

  const score        = profile?.verification_score ?? 0;
  const level        = profile?.verification_level ?? 0;
  const levelName    = LEVEL_NAMES[level] || "Unverified";
  const accent       = LEVEL_ACCENT[level] || "#94A3B8";
  const roadmapSteps = ROADMAP[level] || ROADMAP[0];

  // ── Tab: Overview ─────────────────────────────────────────────────────────

  const renderOverview = () => (
    <div className="space-y-8">

      <section>
        <SectionHeader label={`Verification Badges${badges.length > 0 ? ` (${badges.length})` : ""}`} />
        {badges.length === 0 ? (
          <EmptyState
            icon={<Award />}
            title="No badges yet"
            description="Complete verification steps below to earn badges that confirm your academic identity."
          />
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-4">
            {badges.map((badge, i) => (
              <Card key={badge._id || i} padding="md" className="flex flex-col items-center gap-2 text-center">
                <div className="w-10 h-10 border border-slate-200 flex items-center justify-center text-[#0F2847]">
                  <BadgeIcon type={badge.badge_type} />
                </div>
                <span className="text-xs font-semibold text-slate-800 leading-tight">{formatLabel(badge.badge_type || "Badge")}</span>
                {badge.awarded_at && <span className="text-[10px] text-slate-400 font-mono">{formatDate(badge.awarded_at)}</span>}
              </Card>
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionHeader label="What's Next" />
        <Card padding="lg">
          <p className="text-sm text-slate-500 mb-5">Steps to advance your verification level</p>
          {level === 8 ? (
            <Alert variant="warning" icon={Award}>
              Maximum verification achieved — Distinguished Scholar
            </Alert>
          ) : (
            <div className="space-y-3">
              {roadmapSteps.map((step, i) => {
                const Icon = step.icon;
                return (
                  <div key={i} className="flex items-center gap-4 border border-slate-100 bg-slate-50 p-4">
                    <div className="w-8 h-8 border border-slate-200 bg-white flex items-center justify-center text-[#0F2847] flex-shrink-0">
                      <Icon className="w-4 h-4" />
                    </div>
                    <p className="flex-1 text-sm text-slate-700">{step.text}</p>
                    {step.cta && (
                      step.tab ? (
                        <Button variant="link" onClick={() => switchTab(step.tab)} className="flex-shrink-0">
                          {step.cta} <ChevronRight className="w-3.5 h-3.5" />
                        </Button>
                      ) : (
                        <Button as={Link} to={step.href} variant="link" className="flex-shrink-0">
                          {step.cta} <ChevronRight className="w-3.5 h-3.5" />
                        </Button>
                      )
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </section>

      <section>
        <SectionHeader label="ORCID Verification" />
        <Card padding="xl">
          <p className="text-xs text-slate-500 mb-5">
            Link your ORCID iD to verify your researcher identity and connect your publications automatically.
          </p>
          {profile?.orcid_verified ? (
            <Alert variant="success" icon={CheckCircle}>
              ORCID Connected
              {profile?.orcid_id && <span className="font-mono ml-1">({profile.orcid_id})</span>}
            </Alert>
          ) : (
            <form onSubmit={submitOrcid} className="space-y-4">
              <Input
                label="ORCID iD"
                type="text"
                value={orcidForm.orcid}
                onChange={(e) => setOrcidForm((f) => ({ ...f, orcid: e.target.value }))}
                placeholder="0000-0000-0000-0000"
                className="font-mono"
                hint="Format: 0000-0000-0000-0000"
                required
              />
              <Button type="submit" disabled={orcidForm.submitting} loading={orcidForm.submitting}>
                {orcidForm.submitting ? "Submitting…" : "Connect ORCID"}
              </Button>
              {orcidForm.msg && (
                <p className="text-sm text-slate-600 bg-slate-50 border border-slate-200 px-4 py-2.5">{orcidForm.msg}</p>
              )}
            </form>
          )}
        </Card>
      </section>

    </div>
  );

  // ── Tab: Trust Score ──────────────────────────────────────────────────────

  const renderTrust = () => (
    <div className="space-y-6">
      {!breakdown ? (
        <Card padding="xl" className="flex flex-col items-center gap-3">
          <Loader className="w-7 h-7 animate-spin text-[#0F2847]" />
          <p className="text-slate-500 text-sm">Loading trust breakdown…</p>
        </Card>
      ) : (
        <>
          <section>
            <SectionHeader label="Score Breakdown" />
            <Card padding="lg" className="space-y-4">
              {SCORE_COMPONENTS.map(({ key, label, max }) => {
                const components = breakdown?.components || {};
                const earned = components[key] ?? 0;
                const pct    = max > 0 ? Math.min((earned / max) * 100, 100) : 0;
                const full    = earned >= max;
                const partial = earned > 0 && earned < max;
                const barColor = full ? "#059669" : partial ? "#D97706" : "#E2E8F0";
                return (
                  <div key={key}>
                    <div className="flex items-center gap-3 mb-1.5">
                      {full    ? <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                      : partial ? <AlertCircle className="w-4 h-4 text-amber-500 flex-shrink-0" />
                               : <Circle className="w-4 h-4 text-slate-300 flex-shrink-0" />}
                      <span className="flex-1 text-sm text-slate-700">{label}</span>
                      <span className={`text-xs font-semibold tabular-nums font-mono ${full ? "text-emerald-600" : partial ? "text-amber-600" : "text-slate-400"}`}>
                        {earned} / {max}
                      </span>
                    </div>
                    <div className="ml-7 h-1.5 bg-slate-100 overflow-hidden">
                      <div className="h-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: barColor }} />
                    </div>
                  </div>
                );
              })}
            </Card>
          </section>

          {breakdown?.next_level_requirements && (
            <section>
              <SectionHeader label="Next Level Requirements" />
              <Callout variant="info">
                {typeof breakdown.next_level_requirements === "string" ? (
                  <p>{breakdown.next_level_requirements}</p>
                ) : Array.isArray(breakdown.next_level_requirements) ? (
                  <ul className="space-y-2">
                    {breakdown.next_level_requirements.map((req, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <ChevronRight className="w-4 h-4 mt-0.5 flex-shrink-0" /> {req}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="space-y-2">
                    {Object.entries(breakdown.next_level_requirements).map(([k, v]) => (
                      <div key={k} className="flex items-center gap-2">
                        <ChevronRight className="w-4 h-4 flex-shrink-0" />
                        <span className="font-semibold">{formatLabel(k)}:</span> {String(v)}
                      </div>
                    ))}
                  </div>
                )}
              </Callout>
            </section>
          )}

          {breakdown?.tier_distribution && (
            <section>
              <SectionHeader label="Score Distribution by Tier" />
              <div className="grid sm:grid-cols-3 lg:grid-cols-5 gap-3">
                {Object.entries(breakdown.tier_distribution).map(([tier, pts]) => (
                  <Card key={tier} padding="md" className="text-center">
                    <div className="font-serif text-3xl text-[#0F2847]">{pts}</div>
                    <div className="overline mt-1">{formatLabel(tier)}</div>
                  </Card>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );

  // ── Tab: Evidence ─────────────────────────────────────────────────────────

  const renderEvidence = () => (
    <div className="space-y-6">
      <section>
        <SectionHeader label="Submit Evidence" />
        <Card padding="xl">
          <p className="text-xs text-slate-500 mb-5">
            Provide documentation to support your verification. Evidence is reviewed by the platform team.
          </p>
          <form onSubmit={submitEvidence} className="space-y-4">
            <FormSelect
              label="Evidence Type"
              value={evidenceForm.evidence_type}
              onChange={(e) => setEvidenceForm((f) => ({ ...f, evidence_type: e.target.value }))}
            >
              {EVIDENCE_TYPES.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </FormSelect>
            <Textarea
              label="Description *"
              value={evidenceForm.description}
              onChange={(e) => setEvidenceForm((f) => ({ ...f, description: e.target.value }))}
              placeholder="Describe the evidence you are submitting and why it supports your verification…"
              rows={4}
              required
            />
            <Button type="submit" disabled={evidenceForm.submitting} loading={evidenceForm.submitting}>
              {evidenceForm.submitting ? "Submitting…" : "Submit Evidence"}
            </Button>
            {evidenceForm.msg && (
              <Alert variant={
                evidenceForm.msg.toLowerCase().includes("fail") || evidenceForm.msg.toLowerCase().includes("error")
                  ? "error" : "success"
              }>
                {evidenceForm.msg}
              </Alert>
            )}
          </form>
        </Card>
      </section>

      <section>
        <SectionHeader label="Submitted Evidence" />
        {evidence.length === 0 ? (
          <EmptyState
            icon={<FileText />}
            title="No evidence submitted"
            description="Submit documents above to strengthen your verification profile."
          />
        ) : (
          <div className="space-y-3">
            {evidence.map((item, i) => {
              const statusVariant = {
                pending:  "warning",
                approved: "success",
                rejected: "danger",
              }[item.status] || "warning";
              const statusLabel = {
                pending: "Pending", approved: "Approved", rejected: "Rejected",
              }[item.status] || "Pending";
              return (
                <Card key={item._id || i} padding="lg" className="flex items-start gap-4">
                  <Badge variant={statusVariant} className="flex-shrink-0">{statusLabel}</Badge>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                      {formatLabel(item.evidence_type || "Evidence")}
                    </p>
                    <p className="text-sm text-slate-700 line-clamp-2">{item.description}</p>
                  </div>
                  <div className="flex-shrink-0 text-xs text-slate-400 font-mono whitespace-nowrap">
                    {formatDate(item.submitted_at || item.created_at)}
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );

  // ── Tab: History ──────────────────────────────────────────────────────────

  const renderHistory = () => (
    <div>
      <SectionHeader label="Verification History" />
      {history.length === 0 ? (
        <EmptyState
          icon={<Clock />}
          title="No history yet"
          description={'Click "Recompute Status" above to start tracking your verification history.'}
        />
      ) : (
        <List>
          {history.map((event, i) => {
            const iconBg = historyIconBg(event.event_type);
            return (
              <ListItem
                key={event._id || i}
                leading={
                  <div className={`w-8 h-8 flex items-center justify-center flex-shrink-0 ${iconBg}`}>
                    <HistoryIcon type={event.event_type} />
                  </div>
                }
                title={formatLabel(event.event_type || "Event")}
                subtitle={event.details && (typeof event.details === "string" ? event.details : JSON.stringify(event.details))}
                trailing={
                  <div className="text-xs text-slate-400 font-mono whitespace-nowrap">
                    {formatDate(event.created_at || event.timestamp)}
                  </div>
                }
              />
            );
          })}
        </List>
      )}
    </div>
  );

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <ResearchLayout
      navItems={AI_NAV_ITEMS}
      title="Verification Center"
      subtitle="Your academic identity, trust score, and verification status — evidence-based credentials for the research community."
      actions={
        <Button onClick={recompute} disabled={computing} loading={computing} variant="hero">
          {!computing && <RefreshCw className="w-4 h-4" />}
          {computing ? "Recomputing…" : "Recompute Status"}
        </Button>
      }
    >
      <div className="space-y-10">

        {/* ── Trust Score Hero ── */}
        <Card padding="lg" className="border-[#0F2847]">
          <div className="flex flex-col md:flex-row md:items-center gap-8">
            <div className="flex-shrink-0 text-center md:text-left">
              <div className="overline text-[#0F2847] mb-2">Trust Score</div>
              <div className="font-serif text-6xl text-[#0F2847] tracking-tight leading-none">{score}</div>
              <div className="text-xs text-slate-400 mt-1 font-mono">/1000</div>
            </div>
            <div className="flex-1">
              <div className="flex flex-wrap items-center gap-2 mb-4">
                <Badge size="md" color={accent} className="text-sm font-semibold">
                  <Shield className="w-3.5 h-3.5" />
                  Level {level} — {levelName}
                </Badge>
              </div>
              <div className="h-2 bg-slate-100 overflow-hidden">
                <div
                  className="h-full transition-all duration-700"
                  style={{ width: `${Math.min((score / 1000) * 100, 100)}%`, backgroundColor: accent }}
                />
              </div>
              <div className="flex justify-between text-xs text-slate-400 mt-1.5 font-mono">
                <span>0</span><span>250</span><span>500</span><span>750</span><span>1000</span>
              </div>
            </div>
          </div>
        </Card>

        {/* ── Verification Status Flags ── */}
        <section>
          <SectionHeader label="Verification Status" />
          <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-9 gap-3">
            {STATUS_FLAGS.map(({ key, label }) => {
              const verified = profile?.[key] === true;
              return (
                <Card
                  key={key}
                  padding="sm"
                  className={`flex flex-col items-center gap-2 text-center transition-all ${
                    verified ? "border-emerald-300 bg-emerald-50" : ""
                  }`}
                >
                  {verified
                    ? <CheckCircle className="w-5 h-5 text-emerald-500" />
                    : <Circle className="w-5 h-5 text-slate-300" />}
                  <span className="text-xs font-medium text-slate-700 leading-tight">{label}</span>
                  <span className={`text-[10px] font-semibold uppercase tracking-wide ${verified ? "text-emerald-700" : "text-slate-400"}`}>
                    {verified ? "✓" : "—"}
                  </span>
                </Card>
              );
            })}
          </div>
        </section>

        {/* ── Tab Bar ── */}
        <NavTabs
          variant="underline"
          active={activeTab}
          onChange={switchTab}
          tabs={[
            { id: "overview", label: "Overview"    },
            { id: "trust",    label: "Trust Score" },
            { id: "evidence", label: "Evidence"    },
            { id: "history",  label: "History"     },
          ]}
        />

        {/* ── Tab Content ── */}
        <div>
          {activeTab === "overview" && renderOverview()}
          {activeTab === "trust"    && renderTrust()}
          {activeTab === "evidence" && renderEvidence()}
          {activeTab === "history"  && renderHistory()}
        </div>

      </div>
    </ResearchLayout>
  );
}
