import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Navigate, Link } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { useAuth } from "../contexts/AuthContext";
import { ProfileLayout } from "@/layouts";
import { Avatar } from "@/components/ds/Avatar";
import {
  MessageSquare, UserPlus, ExternalLink, Edit, Sparkles,
  BarChart2, CheckCircle2, Circle, Copy, Share2, Download,
  BookOpen, Briefcase, GraduationCap, DollarSign, User,
  RefreshCw, Loader2, Plus, X,
  MapPin, Building2, Link2, Search, FileText, Users2,
  ArrowRight, BrainCircuit, Layers, FolderOpen, Microscope,
  Award, Star, Globe2, FlaskConical, Tag, ChevronDown, Users,
  Shield, Bookmark, BarChart, Lightbulb, Code2, PenLine,
} from "lucide-react";
import { toast } from "sonner";
import ReputationBadge from "../components/marketplace/ReputationBadge";
import ReputationCard from "../components/reputation/ReputationCard";
import OrcidBadge from "../components/orcid/OrcidBadge";
import InviteModal from "../components/marketplace/InviteModal";
import { ACCENT, NAVY, WARM } from "@/lib/tokens";
import { SkeletonPage, SkeletonCard } from "@/components/ds/LoadingState";
import { EmptyState } from "@/components/ds/EmptyState";
import {
  USER_TYPE_LABELS, PRIMARY_DOMAIN_LABELS,
  USER_TYPE_OPTIONS, PRIMARY_DOMAIN_OPTIONS,
} from "../lib/userTypes";

// ─── Brand tokens ─────────────────────────────────────────────────────────────
const BORDER = "#E4E8EF";

// ─── Constants (preserved from original) ─────────────────────────────────────
const RESEARCH_AREAS = [
  "Artificial Intelligence", "Healthcare", "Management", "Economics",
  "Education", "Public Health", "Cybersecurity", "Engineering", "Psychology",
  "Sociology", "Political Science", "Environmental Science", "History",
  "Communication", "Law", "Philosophy", "Mathematics", "Physics", "Chemistry",
  "Biology", "Medicine", "Business", "Finance", "Accounting", "Marketing",
];
const TEACHING_AREAS_OPTS = [
  "Mathematics", "Economics", "Management", "Computer Science", "Medicine",
  "Engineering", "Psychology", "Education", "Sciences", "Humanities", "Law", "Business",
];
const PROFESSIONAL_EXPERTISE_OPTS = [
  "Artificial Intelligence", "Cybersecurity", "Public Health", "Project Management",
  "Innovation", "Data Science", "Finance", "Strategy", "Operations", "R&D",
  "Product Development", "Sustainability",
];
const METHODS_OPTS = [
  "Quantitative", "Qualitative", "Mixed Methods", "Systematic Review", "Meta-Analysis",
  "Case Study", "Survey", "Ethnography", "Grounded Theory", "Experimental",
  "Quasi-Experimental", "Longitudinal", "Cross-Sectional", "SEM", "PLS-SEM",
  "Regression", "Structural Equation Modelling", "Discourse Analysis", "Content Analysis",
  "Action Research", "Design Science",
];
const SOFTWARE_OPTS = [
  "SPSS", "R", "Python", "Stata", "SAS", "MATLAB", "NVivo", "Atlas.ti",
  "MAXQDA", "Excel", "Tableau", "Power BI", "Gephi", "VOSviewer", "LaTeX",
];
const SKILLS_OPTS = [
  "Data Analysis", "Literature Review", "Grant Writing", "Statistics",
  "Methodology", "Writing", "Editing", "Supervision", "Project Management",
  "Science Communication", "Open Science", "Peer Review",
];
const CONTRIBUTE_OPTS = [
  "Writing", "Statistics", "Methodology", "Data Analysis",
  "Literature Review", "Grant Writing", "Supervision", "Peer Review",
];
const LOOKING_OPTS = [
  "Co-authors", "Statisticians", "AI Researchers", "Healthcare Experts",
  "Economists", "Engineers", "Supervisors", "Funding Partners", "Industry Partners",
];
const CAREER_STAGES = [
  { value: "phd_student",   label: "PhD Student" },
  { value: "postdoc",       label: "Postdoctoral Researcher" },
  { value: "early_career",  label: "Early Career Researcher" },
  { value: "mid_career",    label: "Mid-Career Researcher" },
  { value: "senior",        label: "Senior Researcher" },
  { value: "professor",     label: "Professor" },
  { value: "emeritus",      label: "Professor Emeritus" },
  { value: "industry",      label: "Industry Researcher" },
];
const AVAILABILITY_OPTIONS = ["Available", "Limited Availability", "Not Currently Available"];

// ─── Helpers ──────────────────────────────────────────────────────────────────
function extractOrcidId(orcid) {
  if (!orcid) return null;
  if (typeof orcid === "object") return orcid.orcid_id || null;
  if (typeof orcid === "string") return orcid;
  return null;
}

const AREA_PALETTE = ["#0891B2","#7C3AED","#059669","#D97706","#EA580C","#8A1538","#374151","#0F2847"];

const PUB_TYPE_LABELS = {
  "journal-article": "Journal Article",
  "conference-paper": "Conference Paper",
  "book-chapter": "Book Chapter",
  "book": "Book",
  "preprint": "Preprint",
  "thesis": "Thesis",
  "review": "Review",
};

// ─── Main Component ───────────────────────────────────────────────────────────
export default function Profile() {
  const { userId } = useParams();
  const { user: me, refreshMe } = useAuth();
  const navigate = useNavigate();
  const isMe = !userId || userId === me?.id;
  const targetId = userId || me?.id;
  const [profile, setProfile] = useState(isMe ? me : null);
  const [editing, setEditing] = useState(false);
  const [reputation, setReputation] = useState(null);
  const [inviting, setInviting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [teachingStats, setTeachingStats] = useState(null);
  const [completion, setCompletion] = useState(null);
  const [pubs, setPubs] = useState(null);
  const [pubsLoading, setPubsLoading] = useState(false);
  const [pubQuery, setPubQuery] = useState("");

  const loadProfile = useCallback(async () => {
    if (!targetId) return;
    if (isMe) {
      setProfile(me);
    } else {
      const r = await api.get(`/users/${targetId}`).catch(() => null);
      if (r) setProfile(r.data);
    }
  }, [targetId, isMe, me]);

  const loadPubs = useCallback(async (q = "") => {
    setPubsLoading(true);
    try {
      const params = { limit: 50 };
      if (q) params.q = q;
      const r = await api.get(`/users/${targetId}/publications`, { params });
      setPubs(r.data);
    } catch (_) {
      setPubs({ results: [], total: 0 });
    } finally {
      setPubsLoading(false);
    }
  }, [targetId]);

  useEffect(() => {
    loadProfile();
    if (targetId) {
      api.get(`/reputation/${targetId}`).then((r) => setReputation(r.data)).catch(() => {});
      loadPubs();
    }
    if (isMe) {
      api.get("/teaching-analytics/overview", { params: { period: "30d" } })
        .then((r) => setTeachingStats(r.data)).catch(() => {});
      api.get("/users/me/profile-completion")
        .then((r) => setCompletion(r.data)).catch(() => {});
    }
  }, [targetId, me, isMe, loadProfile, loadPubs]);

  const handleSyncOpenAlex = async () => {
    setSyncing(true);
    try {
      const { data } = await api.post("/reputation/sync-openalex");
      setReputation(data.reputation);
      toast.success("OpenAlex citations synced.");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "OpenAlex sync failed.");
    } finally {
      setSyncing(false);
    }
  };

  const connect = async () => {
    try {
      await api.post(`/users/${targetId}/connect`);
      toast.success("Connection request sent");
      refreshMe();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to connect");
    }
  };

  // Academic Passport is now the single flagship identity page for viewing
  // your own profile — /profile and /profile/<your-id> both redirect there.
  // Viewing another researcher's profile (isMe === false) is unaffected.
  // (Placed after all hooks above to keep hook call order stable across renders.)
  if (isMe) {
    return <Navigate to="/academic-passport" replace />;
  }

  if (!profile) {
    return <div className="p-6"><SkeletonPage /></div>;
  }

  if (editing && isMe) {
    return (
      <EditProfile
        profile={profile}
        onClose={async () => {
          setEditing(false);
          await refreshMe();
          loadProfile();
          api.get("/users/me/profile-completion").then((r) => setCompletion(r.data)).catch(() => {});
        }}
      />
    );
  }

  const orcidId = extractOrcidId(profile.orcid);

  const hIndex    = reputation?.publication?.h_index ?? profile.h_index ?? 0;
  const citations = reputation?.publication?.external_citations ?? 0;
  const pubCount  = profile.publications_count ?? 0;
  const connCount = profile.connections_count ?? 0;

  const profileStats = (
    <>
      {[
        { label: "Publications", value: pubCount > 0 ? pubCount : "—" },
        { label: "Citations",    value: citations > 0 ? citations.toLocaleString() : "—" },
        { label: "h-index",     value: hIndex > 0 ? hIndex : "—" },
        { label: "Connections", value: connCount > 0 ? connCount : "—" },
      ].map(({ label, value }) => (
        <span key={label} style={{ fontSize: 12, color: "#64748B" }}>
          <strong style={{ fontWeight: 700, color: "#0f172a", fontFamily: "monospace", marginRight: 4 }}>{value}</strong>
          {label}
        </span>
      ))}
    </>
  );

  const heroBtnBase = {
    display: "inline-flex", alignItems: "center", gap: 6,
    padding: "7px 14px", fontSize: 12, fontWeight: 600,
    cursor: "pointer", border: "1px solid #E4E8EF",
    background: "white", color: "#0F2847",
  };

  const profileActions = isMe ? (
    <>
      <button
        data-testid={TID.profileEditBtn}
        onClick={() => setEditing(true)}
        style={{ ...heroBtnBase, background: "#0F2847", color: "white", border: "none" }}
      >
        <Edit size={12} strokeWidth={1.5} /> Edit Profile
      </button>
      <button onClick={() => {
        const profileUrl = `${window.location.origin}/profile/${profile.id}`;
        if (navigator.share) {
          navigator.share({ title: profile.full_name, url: profileUrl }).catch(() => {});
        } else {
          navigator.clipboard.writeText(profileUrl).then(() => toast.success("Profile URL copied"));
        }
      }} style={heroBtnBase}>
        <Share2 size={12} strokeWidth={1.5} /> Share
      </button>
    </>
  ) : (
    <>
      <button
        data-testid={TID.profileMessageBtn}
        onClick={() => navigate(`/messages/${profile.id}`)}
        style={{ ...heroBtnBase, background: "#0F2847", color: "white", border: "none" }}
      >
        <MessageSquare size={12} strokeWidth={1.5} /> Message
      </button>
      <button data-testid={TID.profileConnectBtn} onClick={connect} style={heroBtnBase}>
        <UserPlus size={12} strokeWidth={1.5} /> Connect
      </button>
      <button data-testid="profile-invite-btn" onClick={() => setInviting(true)} style={heroBtnBase}>
        <Sparkles size={12} strokeWidth={1.5} /> Invite
      </button>
    </>
  );

  const profileNav = <ProfileNav profile={profile} pubs={pubs} />;

  const profileSidebar = (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {isMe && completion && <CompletionWidget completion={completion} />}
      <ReputationCard
        reputation={reputation}
        isMe={isMe}
        onSyncOpenAlex={handleSyncOpenAlex}
        syncing={syncing}
      />
      {isMe && teachingStats && <TeachingStatsWidget stats={teachingStats} />}
      {isMe && <QuickActionsWidget profile={profile} />}
    </div>
  );

  return (
    <>
      <ProfileLayout
        name={profile.full_name}
        title={profile.academic_role}
        institution={profile.institution}
        avatar={profile.avatar_url}
        verified={!!orcidId}
        stats={profileStats}
        actions={profileActions}
        nav={profileNav}
        sidebar={profileSidebar}
      >
        <AboutSection profile={profile} isMe={isMe} />

        <PublicationsSection
          pubs={pubs}
          loading={pubsLoading}
          isMe={isMe}
          query={pubQuery}
          onQuery={(q) => { setPubQuery(q); loadPubs(q); }}
          onRefresh={() => loadPubs(pubQuery)}
        />

        <CVSection
          educations={profile.orcid_educations || []}
          employments={profile.orcid_employments || []}
          isMe={isMe}
        />

        {((profile.orcid_fundings || []).length > 0 || isMe) && (
          <FundingSection fundings={profile.orcid_fundings || []} isMe={isMe} />
        )}

        <SkillsSection profile={profile} />

        <IdentifiersSection profile={profile} orcidId={orcidId} />

        <AchievementsSection profile={profile} pubs={pubs} />
      </ProfileLayout>

      {inviting && !isMe && (
        <InviteModal
          target={{ user: profile }}
          onClose={() => setInviting(false)}
          defaultKind="collaboration"
        />
      )}
    </>
  );
}

// ─── Hero Header ──────────────────────────────────────────────────────────────
function ProfileHero({ profile, isMe, orcidId, reputation, onEdit, onConnect, onInvite, onMessage }) {
  const hIndex    = reputation?.publication?.h_index ?? profile.h_index ?? 0;
  const citations = reputation?.publication?.external_citations ?? 0;
  const pubCount  = profile.publications_count ?? 0;
  const connCount = profile.connections_count ?? 0;

  const availColor = {
    "Available":                 "#059669",
    "Limited Availability":      "#D97706",
    "Not Currently Available":   "#DC2626",
  }[profile.availability] ?? "#94A3B8";

  const careerLabel = CAREER_STAGES.find((s) => s.value === profile.career_stage)?.label;

  const profileUrl = `${window.location.origin}/profile/${profile.id}`;
  const share = async () => {
    if (navigator.share) {
      try { await navigator.share({ title: profile.full_name, url: profileUrl }); } catch (_) {}
    } else {
      navigator.clipboard.writeText(profileUrl).then(() => toast.success("Profile URL copied"));
    }
  };

  const downloadCV = async () => {
    try {
      const { data } = await api.get("/users/me/cv");
      const lines = [
        `CURRICULUM VITAE`,
        `Generated: ${new Date(data.generated_at).toLocaleDateString()}`,
        "",
        `━━━ IDENTITY ━━━`,
        `Name: ${data.identity.full_name}`,
        data.identity.academic_role ? `Title: ${data.identity.academic_role}` : "",
        `Institution: ${data.identity.institution}`,
        data.identity.department ? `Department: ${data.identity.department}` : "",
        [data.identity.city, data.identity.country].filter(Boolean).join(", "),
        data.identity.email ? `Email: ${data.identity.email}` : "",
        data.identity.orcid_id ? `ORCID: https://orcid.org/${data.identity.orcid_id}` : "",
        data.identity.website ? `Website: ${data.identity.website}` : "",
        "",
        `━━━ METRICS ━━━`,
        `h-index: ${data.metrics.h_index}`,
        `Total Citations: ${data.metrics.total_citations}`,
        `Publications: ${data.metrics.publications_count}`,
        "",
      ];
      if (data.research.research_keywords.length > 0) {
        lines.push(`━━━ RESEARCH KEYWORDS ━━━`);
        lines.push(data.research.research_keywords.join(", "));
        lines.push("");
      }
      if (data.employment.length > 0) {
        lines.push(`━━━ EMPLOYMENT ━━━`);
        data.employment.forEach((e) => {
          lines.push(`${e.role || "Position"} — ${e.institution}`);
          if (e.department) lines.push(`  ${e.department}`);
          if (e.start_year) lines.push(`  ${e.start_year} – ${e.end_year || "present"}`);
          lines.push("");
        });
      }
      if (data.education.length > 0) {
        lines.push(`━━━ EDUCATION ━━━`);
        data.education.forEach((e) => {
          lines.push(`${e.role || "Degree"} — ${e.institution}`);
          if (e.department) lines.push(`  ${e.department}`);
          if (e.start_year) lines.push(`  ${e.start_year} – ${e.end_year || "present"}`);
          lines.push("");
        });
      }
      if (data.publications.length > 0) {
        lines.push(`━━━ PUBLICATIONS ━━━`);
        data.publications.forEach((p, i) => {
          const doi   = p.doi ? ` https://doi.org/${p.doi}` : "";
          const cites = p.citations > 0 ? ` [${p.citations} citations]` : "";
          lines.push(`${i + 1}. ${p.title} (${p.year || "n.d."})${cites}`);
          if (p.journal) lines.push(`   ${p.journal}${doi}`);
        });
      }
      const blob = new Blob([lines.filter((l) => l !== undefined).join("\n")], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(profile.full_name || "cv").replace(/\s+/g, "_")}_CV.txt`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("CV downloaded");
    } catch (_) {
      toast.error("CV download failed");
    }
  };

  const heroBtnBase = {
    display: "inline-flex", alignItems: "center", gap: 6,
    padding: "8px 16px", fontSize: 12, fontWeight: 600,
    cursor: "pointer", border: "1px solid rgba(255,255,255,0.25)",
    background: "rgba(255,255,255,0.12)", color: "white",
    transition: "background 0.12s",
  };

  return (
    <div style={{ margin: "-24px -24px 0", background: NAVY }}>
      {/* Main hero */}
      <div style={{ padding: "36px 32px 28px" }}>
        <div style={{ display: "flex", gap: 24, alignItems: "flex-start", flexWrap: "wrap" }}>

          {/* Avatar */}
          <div style={{ flexShrink: 0 }}>
            <div style={{ width: 100, height: 100, border: "3px solid rgba(255,255,255,0.2)", overflow: "hidden", background: "rgba(255,255,255,0.08)" }}>
              <Avatar url={profile.avatar_url} name={profile.full_name} size={100} />
            </div>
          </div>

          {/* Identity */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {/* Eyebrow chips */}
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8, flexWrap: "wrap" }}>
              {profile.user_type && (
                <span style={{ fontSize: 10, fontWeight: 700, color: "rgba(255,255,255,0.45)", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                  {USER_TYPE_LABELS[profile.user_type]}
                </span>
              )}
              {careerLabel && (
                <span style={{ fontSize: 10, padding: "2px 8px", background: "rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.7)", border: "1px solid rgba(255,255,255,0.18)", letterSpacing: "0.04em" }}>
                  {careerLabel}
                </span>
              )}
              {profile.primary_domain && (
                <span style={{ fontSize: 10, padding: "2px 8px", background: "rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.7)", border: "1px solid rgba(255,255,255,0.18)" }}>
                  {PRIMARY_DOMAIN_LABELS[profile.primary_domain]}
                </span>
              )}
              {profile.availability && (
                <span style={{ fontSize: 10, padding: "2px 8px", background: availColor + "28", color: availColor, border: `1px solid ${availColor}50` }}>
                  ● {profile.availability}
                </span>
              )}
            </div>

            {/* Name + ORCID + Reputation */}
            <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", marginBottom: 4 }}>
              <h1 style={{ fontSize: 30, fontWeight: 700, color: "white", margin: 0, letterSpacing: "-0.03em", lineHeight: 1.1 }}>
                {profile.full_name}
              </h1>
              {orcidId && <OrcidBadge orcidId={orcidId} size="lg" testId="profile-orcid-badge" />}
              {reputation && (
                <span style={{ display: "inline-flex" }}>
                  <ReputationBadge reputation={reputation} testId="profile-reputation" />
                </span>
              )}
            </div>

            {/* Title */}
            {profile.academic_role && (
              <div style={{ fontSize: 14, color: "rgba(255,255,255,0.65)", marginBottom: 8 }}>
                {profile.academic_role}
              </div>
            )}

            {/* Institution + Location */}
            <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap", marginBottom: 12 }}>
              {profile.institution && (
                <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 13, color: "rgba(255,255,255,0.65)" }}>
                  <Building2 size={12} strokeWidth={1.5} />
                  {profile.institution}
                  {profile.department && (
                    <span style={{ color: "rgba(255,255,255,0.35)" }}>· {profile.department}</span>
                  )}
                </span>
              )}
              {(profile.city || profile.country) && (
                <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: "rgba(255,255,255,0.45)" }}>
                  <MapPin size={10} strokeWidth={1.5} />
                  {[profile.city, profile.country].filter(Boolean).join(", ")}
                </span>
              )}
            </div>

            {/* Biography excerpt */}
            {profile.biography && (
              <p style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", lineHeight: 1.65, margin: "0 0 14px", maxWidth: 560 }}>
                {profile.biography.length > 220 ? profile.biography.slice(0, 220) + "…" : profile.biography}
              </p>
            )}

            {/* Research area chips */}
            {(profile.research_areas || []).length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                {profile.research_areas.slice(0, 7).map((area, i) => {
                  const c = AREA_PALETTE[i % AREA_PALETTE.length];
                  return (
                    <span key={area} style={{ fontSize: 11, padding: "3px 9px", background: c + "28", color: c === NAVY ? "rgba(255,255,255,0.7)" : c, border: `1px solid ${c}50` }}>
                      {area}
                    </span>
                  );
                })}
              </div>
            )}
          </div>

          {/* CTA column */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6, flexShrink: 0, minWidth: 148 }}>
            {isMe ? (
              <>
                <button
                  data-testid={TID.profileEditBtn}
                  onClick={onEdit}
                  style={{ ...heroBtnBase, background: "rgba(255,255,255,0.18)", border: "1px solid rgba(255,255,255,0.35)" }}
                  onMouseEnter={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.26)"}
                  onMouseLeave={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.18)"}
                >
                  <Edit size={12} strokeWidth={1.5} /> Edit Profile
                </button>
                <button
                  onClick={share}
                  style={heroBtnBase}
                  onMouseEnter={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.2)"}
                  onMouseLeave={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.12)"}
                >
                  <Share2 size={12} strokeWidth={1.5} /> Share Profile
                </button>
                <button
                  onClick={downloadCV}
                  style={heroBtnBase}
                  onMouseEnter={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.2)"}
                  onMouseLeave={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.12)"}
                >
                  <Download size={12} strokeWidth={1.5} /> Download CV
                </button>
              </>
            ) : (
              <>
                <button
                  data-testid={TID.profileMessageBtn}
                  onClick={onMessage}
                  style={{ ...heroBtnBase, background: "rgba(255,255,255,0.18)", border: "1px solid rgba(255,255,255,0.35)" }}
                  onMouseEnter={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.26)"}
                  onMouseLeave={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.18)"}
                >
                  <MessageSquare size={12} strokeWidth={1.5} /> Message
                </button>
                <button
                  data-testid={TID.profileConnectBtn}
                  onClick={onConnect}
                  style={heroBtnBase}
                  onMouseEnter={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.2)"}
                  onMouseLeave={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.12)"}
                >
                  <UserPlus size={12} strokeWidth={1.5} /> Connect
                </button>
                <button
                  data-testid="profile-invite-btn"
                  onClick={onInvite}
                  style={heroBtnBase}
                  onMouseEnter={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.2)"}
                  onMouseLeave={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.12)"}
                >
                  <Sparkles size={12} strokeWidth={1.5} /> Invite to collaborate
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Stats ribbon */}
      <div style={{ background: "rgba(0,0,0,0.25)", borderTop: "1px solid rgba(255,255,255,0.08)", display: "grid", gridTemplateColumns: "repeat(4, 1fr)" }}>
        {[
          { label: "Publications",  value: pubCount > 0 ? pubCount : "—",                          note: "on record" },
          { label: "Citations",     value: citations > 0 ? citations.toLocaleString() : "—",        note: "from OpenAlex" },
          { label: "h-index",       value: hIndex > 0 ? hIndex : "—",                              note: "impact" },
          { label: "Connections",   value: connCount > 0 ? connCount : "—",                        note: "researchers" },
        ].map(({ label, value, note }, i) => (
          <div key={label} style={{ padding: "14px 20px", borderLeft: i > 0 ? "1px solid rgba(255,255,255,0.07)" : "none" }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: "white", fontFamily: "monospace", lineHeight: 1 }}>{value}</div>
            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", textTransform: "uppercase", letterSpacing: "0.08em", marginTop: 4 }}>{label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Section Nav ──────────────────────────────────────────────────────────────
function ProfileNav({ profile, pubs }) {
  const hasPubs   = (pubs?.total ?? profile.publications_count ?? 0) > 0;
  const hasCV     = (profile.orcid_educations || []).length > 0 || (profile.orcid_employments || []).length > 0;
  const hasSkills = (profile.methods || []).length > 0 || (profile.software_skills || []).length > 0 || (profile.skills || []).length > 0;

  const navItems = [
    { href: "#about",       label: "About",         show: true },
    { href: "#publications", label: `Publications${pubs?.total > 0 ? ` (${pubs.total})` : ""}`, show: true },
    { href: "#experience",  label: "Experience",    show: hasCV },
    { href: "#skills",      label: "Skills & Expertise", show: hasSkills },
    { href: "#identifiers", label: "Academic IDs",  show: true },
    { href: "#achievements",label: "Achievements",  show: true },
  ];

  return (
    <nav style={{ display: "flex", gap: 0, borderBottom: `1px solid ${BORDER}`, marginBottom: 28, overflowX: "auto" }}>
      {navItems.filter((n) => n.show).map(({ href, label }) => (
        <a
          key={href}
          href={href}
          style={{ display: "block", padding: "10px 14px", fontSize: 11, fontWeight: 600, color: "#64748B", textDecoration: "none", whiteSpace: "nowrap", borderBottom: "2px solid transparent", letterSpacing: "0.02em", textTransform: "uppercase", transition: "color 0.12s" }}
          onMouseEnter={(e) => { e.currentTarget.style.color = NAVY; e.currentTarget.style.borderBottomColor = NAVY; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = "#64748B"; e.currentTarget.style.borderBottomColor = "transparent"; }}
        >
          {label}
        </a>
      ))}
    </nav>
  );
}

// ─── Section container ────────────────────────────────────────────────────────
function Section({ id, title, icon: Icon, color = NAVY, children, actions }) {
  return (
    <section id={id} style={{ marginBottom: 36, scrollMarginTop: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18, paddingBottom: 12, borderBottom: `2px solid ${BORDER}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 28, height: 28, background: color + "15", border: `1px solid ${color}30`, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Icon size={13} strokeWidth={1.5} style={{ color }} />
          </div>
          <h2 style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", margin: 0, letterSpacing: "-0.01em", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            {title}
          </h2>
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

// ─── About Section ────────────────────────────────────────────────────────────
function AboutSection({ profile, isMe }) {
  const allMethods = [
    ...(profile.methods || []),
    ...(profile.methodological_expertise || []),
  ].filter((v, i, a) => a.indexOf(v) === i);

  const hasAbout = profile.biography || (profile.research_areas || []).length > 0 ||
    (profile.research_interests || []).length > 0 || (profile.research_keywords || []).length > 0 ||
    allMethods.length > 0 || (profile.teaching_areas || []).length > 0 ||
    profile.available_for_collaboration || profile.available_for_supervision ||
    profile.available_for_reviewing || profile.available_for_consulting ||
    (profile.can_contribute || []).length > 0 || (profile.looking_for || []).length > 0;

  if (!hasAbout && !isMe) return null;

  return (
    <Section id="about" title="About" icon={User}>
      {/* Biography */}
      {profile.biography ? (
        <div style={{ fontSize: 14, color: "#374151", lineHeight: 1.8, marginBottom: 20, padding: "18px 20px", background: WARM, borderLeft: `3px solid ${NAVY}` }}>
          {profile.biography}
        </div>
      ) : isMe ? (
        <div style={{ padding: "16px 20px", border: `1px dashed ${BORDER}`, marginBottom: 20, display: "flex", alignItems: "center", gap: 10 }}>
          <PenLine size={14} strokeWidth={1.5} style={{ color: "#CBD5E1" }} />
          <span style={{ fontSize: 13, color: "#94A3B8" }}>No biography yet. </span>
          <span style={{ fontSize: 13, color: NAVY, cursor: "pointer", textDecoration: "underline" }}>Add one to improve your profile visibility.</span>
        </div>
      ) : null}

      {/* Research Areas */}
      {(profile.research_areas || []).length > 0 && (
        <div style={{ marginBottom: 18 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Research Areas</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {profile.research_areas.map((area, i) => {
              const c = AREA_PALETTE[i % AREA_PALETTE.length];
              return (
                <span key={area} style={{ fontSize: 12, padding: "4px 11px", background: c + "12", color: c, border: `1px solid ${c}35`, fontWeight: 500 }}>
                  {area}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Research Keywords */}
      {(profile.research_keywords || []).length > 0 && (
        <div style={{ marginBottom: 18 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Research Keywords</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
            {profile.research_keywords.map((k) => (
              <span key={k} style={{ fontSize: 11, padding: "3px 9px", background: NAVY + "08", color: NAVY, border: `1px solid ${NAVY}25` }}>
                {k}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Research Interests */}
      {(profile.research_interests || []).length > 0 && (
        <div style={{ marginBottom: 18 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Research Interests</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
            {profile.research_interests.map((r) => (
              <span key={r} style={{ fontSize: 11, padding: "3px 9px", background: "#F8FAFC", color: "#475569", border: `1px solid ${BORDER}` }}>
                {r}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Availability + Open To */}
      {(profile.available_for_collaboration || profile.available_for_supervision ||
        profile.available_for_reviewing || profile.available_for_consulting ||
        (profile.can_contribute || []).length > 0 || (profile.looking_for || []).length > 0) && (
        <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: 16, marginTop: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            {/* Open to */}
            {(profile.available_for_collaboration || profile.available_for_supervision ||
              profile.available_for_reviewing || profile.available_for_consulting) && (
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Open to</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                  {profile.available_for_collaboration && <OpenBadge label="Collaboration" />}
                  {profile.available_for_supervision   && <OpenBadge label="Supervision" />}
                  {profile.available_for_reviewing     && <OpenBadge label="Peer Review" />}
                  {profile.available_for_consulting    && <OpenBadge label="Consulting" />}
                </div>
              </div>
            )}

            {/* Can contribute */}
            {(profile.can_contribute || []).length > 0 && (
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Can contribute</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                  {profile.can_contribute.map((c) => (
                    <span key={c} style={{ fontSize: 11, padding: "3px 9px", background: "#EFF6FF", color: NAVY, border: `1px solid ${BORDER}` }}>{c}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Looking for */}
            {(profile.looking_for || []).length > 0 && (
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>Looking for</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                  {profile.looking_for.map((c) => (
                    <span key={c} style={{ fontSize: 11, padding: "3px 9px", background: "#FFFBEB", color: "#92400E", border: `1px solid #FDE68A` }}>{c}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {!hasAbout && isMe && (
        <div style={{ textAlign: "center", padding: "32px 24px", color: "#94A3B8", fontSize: 13 }}>
          Complete your profile to improve your research visibility and attract collaborators.
        </div>
      )}
    </Section>
  );
}

function OpenBadge({ label }) {
  return (
    <span style={{ fontSize: 11, padding: "3px 10px", background: "#F0FDF4", color: "#059669", border: "1px solid #A7F3D0", display: "flex", alignItems: "center", gap: 4, fontWeight: 500 }}>
      <CheckCircle2 size={9} strokeWidth={2} /> {label}
    </span>
  );
}

// ─── Publications Section ─────────────────────────────────────────────────────
function PublicationsSection({ pubs, loading, isMe, query, onQuery, onRefresh }) {
  const [importingOrcid, setImportingOrcid] = useState(false);

  const importOrcid = async () => {
    setImportingOrcid(true);
    try {
      const { data } = await api.post("/orcid/sync");
      const imported = data.publications_imported ?? data.imported ?? 0;
      toast.success(`ORCID synced — ${imported} publications imported`);
      onRefresh();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "ORCID sync failed");
    } finally {
      setImportingOrcid(false);
    }
  };

  const sectionActions = isMe && (
    <button
      onClick={importOrcid}
      disabled={importingOrcid}
      style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, fontWeight: 500, color: "#64748B", background: "white", border: `1px solid ${BORDER}`, padding: "5px 11px", cursor: "pointer" }}
    >
      {importingOrcid ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} strokeWidth={1.5} />}
      Sync ORCID
    </button>
  );

  return (
    <Section id="publications" title="Publications" icon={BookOpen} color="#0891B2" actions={sectionActions}>
      {/* Search */}
      <div style={{ position: "relative", marginBottom: 16 }}>
        <Search size={12} strokeWidth={1.5} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "#94A3B8" }} />
        <input
          type="search"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="Search publications by title, journal, keyword…"
          style={{ width: "100%", paddingLeft: 30, paddingRight: 12, paddingTop: 8, paddingBottom: 8, border: `1px solid ${BORDER}`, fontSize: 12, color: "#374151", outline: "none", boxSizing: "border-box" }}
          onFocus={(e) => e.currentTarget.style.borderColor = NAVY + "60"}
          onBlur={(e)  => e.currentTarget.style.borderColor = BORDER}
        />
      </div>

      {loading && <SkeletonCard rows={3} />}

      {!loading && (!pubs || pubs.results.length === 0) && (
        <EmptyState
          icon={<BookOpen />}
          title={query ? "No publications match your search." : "No publications on record."}
          description={isMe && !query ? "Connect ORCID in Settings to automatically import your publications." : undefined}
          dashed
        />
      )}

      {!loading && pubs && pubs.results.length > 0 && (
        <div>
          {pubs.total > pubs.results.length && (
            <div style={{ fontSize: 11, color: "#94A3B8", fontFamily: "monospace", marginBottom: 12 }}>
              Showing {pubs.results.length} of {pubs.total} publications
            </div>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {pubs.results.map((pub) => (
              <PublicationCard key={pub.id} pub={pub} />
            ))}
          </div>
        </div>
      )}
    </Section>
  );
}

function PublicationCard({ pub }) {
  const [expanded, setExpanded] = useState(false);
  const [hov, setHov] = useState(false);
  const typeLabel = PUB_TYPE_LABELS[pub.type] || pub.type || "Publication";
  const decade = pub.year ? Math.floor(pub.year / 10) * 10 : null;
  const isRecent = decade >= 2020;

  return (
    <div
      onClick={() => setExpanded((v) => !v)}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: "flex", gap: 14, alignItems: "flex-start", padding: "14px 16px",
        border: `1px solid ${hov ? "#CBD5E1" : BORDER}`,
        background: hov ? WARM : "white",
        cursor: "pointer", transition: "all 0.12s",
        borderLeft: `3px solid ${isRecent ? "#0891B2" : BORDER}`,
      }}
    >
      {/* Year badge */}
      <div style={{ flexShrink: 0, minWidth: 48, textAlign: "center" }}>
        {pub.year && (
          <div style={{ fontSize: 14, fontWeight: 700, fontFamily: "monospace", color: isRecent ? "#0891B2" : "#94A3B8" }}>
            {pub.year}
          </div>
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "#0f172a", lineHeight: 1.45, marginBottom: 4 }}>
          {pub.title}
        </div>
        {(pub.authors || []).length > 0 && (
          <div style={{ fontSize: 11, color: "#64748B", marginBottom: 4 }}>
            {pub.authors.slice(0, 5).join(", ")}{pub.authors.length > 5 ? ` +${pub.authors.length - 5}` : ""}
          </div>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap", marginBottom: expanded ? 8 : 0 }}>
          {pub.journal && (
            <span style={{ fontSize: 11, color: "#475569", fontStyle: "italic" }}>{pub.journal}</span>
          )}
          <span style={{ fontSize: 10, padding: "1px 6px", background: "#EFF6FF", color: NAVY, border: `1px solid ${BORDER}`, textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>
            {typeLabel}
          </span>
          {pub.open_access && (
            <span style={{ fontSize: 10, padding: "1px 6px", background: "#F0FDF4", color: "#059669", border: "1px solid #A7F3D0", fontWeight: 600 }}>
              Open Access
            </span>
          )}
        </div>

        {expanded && pub.abstract && (
          <p style={{ fontSize: 12, color: "#64748B", lineHeight: 1.65, margin: "8px 0", borderTop: `1px solid ${BORDER}`, paddingTop: 8 }}>
            {pub.abstract}
          </p>
        )}
        {expanded && (pub.concepts || []).length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 6 }}>
            {pub.concepts.slice(0, 8).map((c) => (
              <span key={c.display_name || c} style={{ fontSize: 10, padding: "1px 6px", background: "#F0FDF4", color: "#059669" }}>
                {c.display_name || c}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Right: citations + DOI */}
      <div style={{ flexShrink: 0, textAlign: "right", display: "flex", flexDirection: "column", gap: 4, alignItems: "flex-end" }}>
        {pub.citations > 0 && (
          <div style={{ fontSize: 13, fontWeight: 700, fontFamily: "monospace", color: "#0f172a" }}>
            {pub.citations}
            <span style={{ fontSize: 10, fontWeight: 400, color: "#94A3B8", marginLeft: 3 }}>cites</span>
          </div>
        )}
        {pub.doi && (
          <a
            href={`https://doi.org/${pub.doi}`}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 10, color: "#0891B2", textDecoration: "none", fontWeight: 600 }}
          >
            DOI <ExternalLink size={9} strokeWidth={1.5} />
          </a>
        )}
        <ChevronDown size={12} strokeWidth={1.5} style={{ color: "#CBD5E1", transform: expanded ? "rotate(180deg)" : "none", transition: "transform 0.15s", marginTop: 4 }} />
      </div>
    </div>
  );
}

// ─── CV Section ───────────────────────────────────────────────────────────────
function CVSection({ educations, employments, isMe }) {
  const hasData = educations.length > 0 || employments.length > 0;
  if (!hasData && !isMe) return null;

  return (
    <Section id="experience" title="Education & Employment" icon={Briefcase} color="#7C3AED">
      {!hasData ? (
        <EmptyState
          icon={<GraduationCap />}
          title="No education or employment records"
          description="Connect ORCID in Settings to import your education and employment history."
          dashed
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
          {employments.length > 0 && (
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 14 }}>
                Employment
              </div>
              <TimelineList records={employments} type="employment" />
            </div>
          )}
          {educations.length > 0 && (
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 14 }}>
                Education
              </div>
              <TimelineList records={educations} type="education" />
            </div>
          )}
        </div>
      )}
    </Section>
  );
}

function TimelineList({ records, type }) {
  return (
    <div style={{ position: "relative" }}>
      <div style={{ position: "absolute", left: 10, top: 12, bottom: 12, width: 1, background: BORDER }} />
      <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
        {records.map((r, i) => {
          const startY = r.start_year || "";
          const endY   = r.end_year || "present";
          const yearRange = startY ? `${startY} – ${endY}` : "";
          const isCurrent = !r.end_year;
          return (
            <div key={i} style={{ display: "flex", gap: 18, paddingLeft: 0, paddingBottom: 20 }}>
              {/* Dot */}
              <div style={{ flexShrink: 0, width: 20, paddingTop: 2 }}>
                <div style={{ width: 8, height: 8, background: isCurrent ? "#7C3AED" : BORDER, border: `2px solid ${isCurrent ? "#7C3AED" : "#CBD5E1"}`, marginLeft: 6, marginTop: 4 }} />
              </div>
              {/* Content */}
              <div style={{ flex: 1, paddingBottom: 8, borderBottom: i < records.length - 1 ? `1px solid ${BORDER}` : "none" }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#0f172a" }}>
                  {type === "education" ? (r.role || "Degree") : (r.role || "Position")}
                </div>
                <div style={{ fontSize: 12, color: "#374151", marginTop: 1 }}>{r.institution}</div>
                {r.department && (
                  <div style={{ fontSize: 11, color: "#64748B" }}>{r.department}</div>
                )}
                <div style={{ display: "flex", gap: 10, marginTop: 4, alignItems: "center" }}>
                  {yearRange && (
                    <span style={{ fontSize: 10, fontFamily: "monospace", color: isCurrent ? "#7C3AED" : "#94A3B8", fontWeight: isCurrent ? 600 : 400 }}>
                      {yearRange}
                    </span>
                  )}
                  {(r.city || r.country) && (
                    <span style={{ fontSize: 10, color: "#CBD5E1", display: "flex", alignItems: "center", gap: 3 }}>
                      <MapPin size={9} strokeWidth={1.5} />
                      {[r.city, r.country].filter(Boolean).join(", ")}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Funding Section ──────────────────────────────────────────────────────────
function FundingSection({ fundings, isMe }) {
  return (
    <Section id="funding" title="Research Funding" icon={DollarSign} color="#059669">
      {fundings.length === 0 ? (
        <EmptyState
          icon={<DollarSign />}
          title={isMe ? "No funding records yet." : "No funding records."}
          description={isMe ? "Connect ORCID and sync to import your funding history." : undefined}
          dashed
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {fundings.map((f, i) => (
            <div key={i} style={{ padding: "14px 16px", border: `1px solid ${BORDER}`, background: "white" }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#0f172a", marginBottom: 4 }}>
                {f.title || "Funding award"}
              </div>
              {f.organization && (
                <div style={{ fontSize: 12, color: "#374151" }}>{f.organization}</div>
              )}
              <div style={{ display: "flex", gap: 10, marginTop: 6 }}>
                {f.type && (
                  <span style={{ fontSize: 10, padding: "1px 6px", background: "#F0FDF4", color: "#059669", border: "1px solid #A7F3D0", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>
                    {f.type}
                  </span>
                )}
                {(f.start_year || f.end_year) && (
                  <span style={{ fontSize: 10, fontFamily: "monospace", color: "#94A3B8" }}>
                    {f.start_year || "?"} – {f.end_year || "present"}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Section>
  );
}

// ─── Skills Section ───────────────────────────────────────────────────────────
function SkillsSection({ profile }) {
  const allMethods = [
    ...(profile.methods || []),
    ...(profile.methodological_expertise || []),
  ].filter((v, i, a) => a.indexOf(v) === i);

  const allSkills = [...(profile.skills || [])].filter(Boolean);
  const software  = [...(profile.software_skills || [])].filter(Boolean);
  const expertise = [...(profile.professional_expertise || [])].filter(Boolean);
  const teaching  = [...(profile.teaching_areas || [])].filter(Boolean);

  const hasAny = allMethods.length > 0 || allSkills.length > 0 || software.length > 0 ||
    expertise.length > 0 || teaching.length > 0;
  if (!hasAny) return null;

  const SkillGroup = ({ label, items, chipColor, chipBg, chipBorder }) => {
    if (!items || items.length === 0) return null;
    return (
      <div style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>{label}</div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
          {items.map((item) => (
            <span key={item} style={{ fontSize: 12, padding: "4px 11px", background: chipBg, color: chipColor, border: `1px solid ${chipBorder}`, fontWeight: 500 }}>
              {item}
            </span>
          ))}
        </div>
      </div>
    );
  };

  return (
    <Section id="skills" title="Skills & Expertise" icon={BarChart2} color="#7C3AED">
      <SkillGroup label="Research Methods"      items={allMethods} chipColor="#0891B2" chipBg="#EFF9FF"  chipBorder="#BAE6FD" />
      <SkillGroup label="Software & Tools"      items={software}   chipColor="#D97706" chipBg="#FFFBEB"  chipBorder="#FDE68A" />
      <SkillGroup label="Academic Skills"       items={allSkills}  chipColor="#059669" chipBg="#F0FDF4"  chipBorder="#A7F3D0" />
      <SkillGroup label="Professional Expertise" items={expertise} chipColor="#7C3AED" chipBg="#FAF5FF"  chipBorder="#DDD6FE" />
      <SkillGroup label="Teaching Areas"        items={teaching}   chipColor={NAVY}    chipBg="#EFF6FF"  chipBorder={BORDER}  />
    </Section>
  );
}

// ─── Identifiers Section ──────────────────────────────────────────────────────
function IdentifiersSection({ profile, orcidId }) {
  const ids = [
    { label: "ORCID",          value: orcidId,               href: orcidId ? `https://orcid.org/${orcidId}` : null,                                   color: "#059669" },
    { label: "Google Scholar", value: profile.google_scholar, href: profile.google_scholar ? `https://scholar.google.com/citations?user=${profile.google_scholar}` : null, color: "#0891B2" },
    { label: "ResearchGate",   value: profile.researchgate,  href: profile.researchgate ? `https://www.researchgate.net/profile/${profile.researchgate}` : null,           color: "#0891B2" },
    { label: "Scopus",         value: profile.scopus_id,     href: profile.scopus_id ? `https://www.scopus.com/authid/detail.uri?authorId=${profile.scopus_id}` : null,   color: "#D97706" },
    { label: "OpenAlex",       value: profile.openalex_author_id ? profile.openalex_author_id.split("/").pop() : null,
      href: profile.openalex_author_id ? (profile.openalex_profile_url || `https://openalex.org/authors/${profile.openalex_author_id.split("/").pop()}`) : null,         color: "#7C3AED" },
    { label: "LinkedIn",       value: profile.linkedin,      href: profile.linkedin ? `https://www.linkedin.com/in/${profile.linkedin}` : null,                            color: "#0891B2" },
    { label: "Website",        value: profile.website,       href: profile.website,                                                                                        color: NAVY },
  ].filter((id) => id.value);

  if (ids.length === 0) return null;

  return (
    <Section id="identifiers" title="Academic Identifiers" icon={Globe2} color="#059669">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 10 }}>
        {ids.map(({ label, value, href, color }) => (
          <a
            key={label}
            href={href || "#"}
            target={href ? "_blank" : "_self"}
            rel="noreferrer"
            style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 14px", border: `1px solid ${BORDER}`, background: WARM, textDecoration: "none", transition: "all 0.12s" }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = color + "50"; e.currentTarget.style.background = "white"; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.background = WARM; }}
          >
            <div style={{ width: 28, height: 28, background: color + "15", border: `1px solid ${color}30`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <Link2 size={12} strokeWidth={1.5} style={{ color }} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.07em" }}>{label}</div>
              <div style={{ fontSize: 11, color: "#374151", fontFamily: "monospace", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {typeof value === "string" && value.length > 22 ? value.slice(0, 22) + "…" : value}
              </div>
            </div>
            {href && <ExternalLink size={11} strokeWidth={1.5} style={{ color: "#CBD5E1", flexShrink: 0 }} />}
          </a>
        ))}
      </div>
    </Section>
  );
}

// ─── Achievements Section ─────────────────────────────────────────────────────
function AchievementsSection({ profile, pubs }) {
  const orcidId = extractOrcidId(profile.orcid);
  const pubCount = pubs?.total ?? profile.publications_count ?? 0;

  const badges = [
    orcidId && { icon: Shield, label: "ORCID Connected", desc: "Verified researcher identity", color: "#059669", bg: "#F0FDF4" },
    profile.biography?.trim() && { icon: PenLine, label: "Researcher Profile", desc: "Biography added", color: "#0891B2", bg: "#F0F9FF" },
    pubCount > 0 && { icon: BookOpen, label: "Publications Imported", desc: `${pubCount} publication${pubCount !== 1 ? "s" : ""} on record`, color: NAVY, bg: "#EFF6FF" },
    (profile.research_areas || []).length > 0 && { icon: FlaskConical, label: "Research Areas Defined", desc: `${profile.research_areas.length} area${profile.research_areas.length !== 1 ? "s" : ""}`, color: "#7C3AED", bg: "#FAF5FF" },
    (profile.research_keywords || []).length > 0 && { icon: Tag, label: "Keywords Set", desc: `${profile.research_keywords.length} keywords`, color: "#D97706", bg: "#FFFBEB" },
    profile.available_for_collaboration && { icon: Users2, label: "Open to Collaboration", desc: "Accepting collaborators", color: "#059669", bg: "#F0FDF4" },
    profile.available_for_reviewing && { icon: CheckCircle2, label: "Open Reviewer", desc: "Available for peer review", color: "#0891B2", bg: "#F0F9FF" },
    (profile.teaching_areas || []).length > 0 && { icon: GraduationCap, label: "Teaching Profile", desc: `${profile.teaching_areas.length} teaching area${profile.teaching_areas.length !== 1 ? "s" : ""}`, color: "#D97706", bg: "#FFFBEB" },
    (profile.methods || []).length >= 3 && { icon: Microscope, label: "Methods Expert", desc: `${profile.methods.length} methods listed`, color: "#7C3AED", bg: "#FAF5FF" },
    (profile.connections_count ?? 0) > 0 && { icon: Users, label: "Network Builder", desc: `${profile.connections_count} connection${profile.connections_count !== 1 ? "s" : ""}`, color: NAVY, bg: "#EFF6FF" },
    (profile.google_scholar || profile.researchgate || profile.scopus_id) && { icon: Link2, label: "Academic IDs Linked", desc: "External profiles connected", color: "#059669", bg: "#F0FDF4" },
    (profile.software_skills || []).length > 0 && { icon: Code2, label: "Software Skills", desc: `${profile.software_skills.length} tool${profile.software_skills.length !== 1 ? "s" : ""}`, color: "#0891B2", bg: "#F0F9FF" },
  ].filter(Boolean);

  if (badges.length === 0) return null;

  return (
    <Section id="achievements" title="Profile Achievements" icon={Award} color="#D97706">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 10 }}>
        {badges.map(({ icon: Icon, label, desc, color, bg }) => (
          <div key={label} style={{ padding: "14px", background: bg, border: `1px solid ${color}25`, display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ width: 28, height: 28, background: color + "20", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Icon size={13} strokeWidth={1.5} style={{ color }} />
            </div>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#0f172a" }}>{label}</div>
              <div style={{ fontSize: 10, color: "#94A3B8", marginTop: 2 }}>{desc}</div>
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}

// ─── Sidebar Widgets ──────────────────────────────────────────────────────────

function CompletionWidget({ completion }) {
  const pct = completion.percentage;
  const barColor = pct >= 80 ? "#059669" : pct >= 50 ? "#D97706" : ACCENT;
  return (
    <div style={{ border: `1px solid ${BORDER}`, background: "white" }} data-testid="profile-completion-widget">
      <div style={{ padding: "14px 16px 10px", borderBottom: `1px solid ${BORDER}` }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8" }}>Profile Strength</div>
          <span style={{ fontSize: 18, fontWeight: 700, fontFamily: "monospace", color: barColor }}>{pct}%</span>
        </div>
        <div style={{ height: 4, background: "#E2E8F0", marginTop: 8 }}>
          <div style={{ height: "100%", background: barColor, width: `${pct}%`, transition: "width 0.6s ease" }} />
        </div>
      </div>
      <div style={{ padding: "10px 14px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {completion.items.map((item) => (
            <div key={item.key} style={{ display: "flex", alignItems: "center", gap: 7 }}>
              {item.earned
                ? <CheckCircle2 size={12} strokeWidth={1.5} style={{ color: "#059669", flexShrink: 0 }} />
                : <Circle size={12} strokeWidth={1.5} style={{ color: "#CBD5E1", flexShrink: 0 }} />}
              <span style={{ flex: 1, fontSize: 11, color: item.earned ? "#374151" : "#94A3B8" }}>{item.label}</span>
              {item.earned
                ? <span style={{ fontSize: 10, fontFamily: "monospace", color: "#059669" }}>+{item.points}</span>
                : <Link to={item.action} style={{ fontSize: 10, color: NAVY, textDecoration: "none" }}>{item.action_label}</Link>
              }
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function TeachingStatsWidget({ stats }) {
  return (
    <div style={{ border: `1px solid ${BORDER}`, background: "white" }}>
      <div style={{ padding: "14px 16px 10px", borderBottom: `1px solid ${BORDER}`, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <BarChart2 size={12} strokeWidth={1.5} style={{ color: NAVY }} />
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8" }}>Teaching (30d)</span>
        </div>
        <Link to="/teaching/analytics" style={{ fontSize: 10, color: "#94A3B8", textDecoration: "none" }}>Analytics →</Link>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, background: BORDER }}>
        {[
          { label: "Lessons",      value: stats.period_counts?.lessons },
          { label: "Assessments",  value: stats.period_counts?.assessments },
          { label: "AI Sessions",  value: stats.period_counts?.ai_sessions },
          { label: "Teaching Rep", value: stats.reputation?.teaching_score },
        ].map(({ label, value }) => (
          <div key={label} style={{ background: "white", padding: "10px 12px" }}>
            <div style={{ fontSize: 20, fontWeight: 700, fontFamily: "monospace", color: "#0f172a" }}>{value ?? 0}</div>
            <div style={{ fontSize: 10, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.07em", marginTop: 1 }}>{label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function QuickActionsWidget({ profile }) {
  const profileUrl = `${window.location.origin}/profile/${profile.id}`;
  const share = async () => {
    if (navigator.share) {
      try { await navigator.share({ title: profile.full_name, url: profileUrl }); } catch (_) {}
    } else {
      navigator.clipboard.writeText(profileUrl).then(() => toast.success("Profile URL copied"));
    }
  };

  const links = [
    { label: "Open ORCID Settings",    to: "/settings",          icon: RefreshCw },
    { label: "Manage Publications",     to: "/publications",       icon: BookOpen },
    { label: "View My Projects",        to: "/projects",           icon: FolderOpen },
    { label: "Open Workspaces",         to: "/workspaces",         icon: Layers },
    { label: "Launch Synaptiq AI",      to: "/ai",                 icon: BrainCircuit },
    { label: "Find Collaborators",      to: "/network",            icon: Users2 },
  ];

  return (
    <div style={{ border: `1px solid ${BORDER}`, background: "white" }}>
      <div style={{ padding: "14px 16px 10px", borderBottom: `1px solid ${BORDER}` }}>
        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8" }}>Quick Actions</div>
      </div>
      <div style={{ padding: "8px 10px", display: "flex", flexDirection: "column", gap: 2 }}>
        <button
          onClick={share}
          style={{ display: "flex", alignItems: "center", gap: 7, padding: "6px 8px", fontSize: 11, color: "#374151", background: WARM, border: `1px solid ${BORDER}`, cursor: "pointer", textAlign: "left", marginBottom: 4 }}
        >
          <Share2 size={11} strokeWidth={1.5} /> Share Profile
        </button>
        {links.map(({ label, to, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            style={{ display: "flex", alignItems: "center", gap: 7, padding: "6px 8px", fontSize: 11, color: "#64748B", textDecoration: "none", border: "1px solid transparent", transition: "all 0.12s" }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.background = WARM; e.currentTarget.style.color = NAVY; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = "transparent"; e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "#64748B"; }}
          >
            <Icon size={11} strokeWidth={1.5} />
            {label}
          </Link>
        ))}
      </div>
    </div>
  );
}

// ─── Edit Profile ─────────────────────────────────────────────────────────────

function EditProfile({ profile, onClose }) {
  const orcidId = profile.orcid && typeof profile.orcid === "object"
    ? profile.orcid.orcid_id
    : (typeof profile.orcid === "string" ? profile.orcid : null);

  const [f, setF] = useState({
    full_name:              profile.full_name || "",
    institution:            profile.institution || "",
    department:             profile.department || "",
    country:                profile.country || "",
    city:                   profile.city || "",
    career_stage:           profile.career_stage || "",
    user_type:              profile.user_type || "",
    primary_domain:         profile.primary_domain || "",
    academic_role:          profile.academic_role || "",
    biography:              profile.biography || "",
    google_scholar:         profile.google_scholar || "",
    researchgate:           profile.researchgate || "",
    scopus_id:              profile.scopus_id || "",
    linkedin:               profile.linkedin || "",
    website:                profile.website || "",
    avatar_url:             profile.avatar_url || "",
    research_areas:         profile.research_areas || [],
    research_interests:     profile.research_interests || [],
    research_keywords:      profile.research_keywords || [],
    methods:                profile.methods || [],
    software_skills:        profile.software_skills || [],
    teaching_areas:         profile.teaching_areas || [],
    professional_expertise: profile.professional_expertise || [],
    skills:                 profile.skills || [],
    can_contribute:         profile.can_contribute || [],
    looking_for:            profile.looking_for || [],
    availability:           profile.availability || "Available",
    available_for_collaboration: profile.available_for_collaboration ?? true,
    available_for_supervision:   profile.available_for_supervision ?? false,
    available_for_reviewing:     profile.available_for_reviewing ?? false,
    available_for_consulting:    profile.available_for_consulting ?? false,
  });
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [keywordInput, setKeywordInput] = useState("");

  const update = (key, val) => { setF((prev) => ({ ...prev, [key]: val })); setDirty(true); };
  const toggle = (key, v) => {
    const set = new Set(f[key]);
    set.has(v) ? set.delete(v) : set.add(v);
    update(key, Array.from(set));
  };

  const addKeyword = (e) => {
    if ((e.key === "Enter" || e.key === ",") && keywordInput.trim()) {
      e.preventDefault();
      const kw = keywordInput.trim().replace(/,$/, "");
      if (kw && !f.research_keywords.includes(kw)) {
        update("research_keywords", [...f.research_keywords, kw]);
      }
      setKeywordInput("");
    }
  };
  const removeKeyword = (kw) => update("research_keywords", f.research_keywords.filter((k) => k !== kw));

  const save = async () => {
    if (f.avatar_url && !f.avatar_url.startsWith("http")) {
      toast.error("Avatar URL must start with http:// or https://");
      return;
    }
    if (f.website && !f.website.startsWith("http")) {
      toast.error("Website URL must start with http:// or https://");
      return;
    }
    setSaving(true);
    try {
      await api.patch("/users/me", f);
      toast.success("Profile saved");
      setDirty(false);
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-8 pb-16">
      <div>
        <div className="overline">Edit · Academic identity</div>
        <h1 className="font-serif text-4xl text-slate-900 mt-2">Update your profile</h1>
        {dirty && (
          <div className="mt-2 text-xs text-amber-600 font-mono">Unsaved changes</div>
        )}
      </div>

      {/* ORCID read-only notice */}
      {orcidId && (
        <div className="border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800 flex items-center gap-2">
          <CheckCircle2 size={12} strokeWidth={1.5} />
          ORCID {orcidId} connected.{" "}
          <Link to="/settings" className="underline">Manage in Settings</Link>.
        </div>
      )}
      {!orcidId && (
        <div className="border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 flex items-center gap-2">
          Connect your ORCID in <Link to="/settings" className="underline">Settings</Link> to automatically import publications, education, and employment.
        </div>
      )}

      {/* Identity */}
      <section>
        <h2 className="overline mb-4">Identity</h2>
        <div className="grid sm:grid-cols-2 gap-5">
          <FieldInput label="Full name" value={f.full_name} onChange={(v) => update("full_name", v)} />
          <FieldInput label="Job title" value={f.academic_role} onChange={(v) => update("academic_role", v)} placeholder="e.g. Associate Professor" />
          <FieldInput label="Institution" value={f.institution} onChange={(v) => update("institution", v)} />
          <FieldInput label="Department" value={f.department} onChange={(v) => update("department", v)} />
          <FieldInput label="City" value={f.city} onChange={(v) => update("city", v)} />
          <FieldInput label="Country" value={f.country} onChange={(v) => update("country", v)} />
          <FieldSelect
            label="Platform category"
            value={f.user_type}
            onChange={(v) => update("user_type", v)}
            options={USER_TYPE_OPTIONS}
          />
          <FieldSelect
            label="Primary focus"
            value={f.primary_domain}
            onChange={(v) => update("primary_domain", v)}
            options={PRIMARY_DOMAIN_OPTIONS}
          />
          <FieldSelect
            label="Career stage"
            value={f.career_stage}
            onChange={(v) => update("career_stage", v)}
            options={CAREER_STAGES}
          />
          <FieldInput label="Avatar URL" value={f.avatar_url} onChange={(v) => update("avatar_url", v)} placeholder="https://" />
        </div>
        <div className="mt-5">
          <label className="overline block mb-2">Biography</label>
          <textarea
            rows={4}
            value={f.biography}
            onChange={(e) => update("biography", e.target.value)}
            placeholder="Describe your research background, interests, and goals…"
            className="w-full px-3 py-2 border border-slate-300 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
          />
          <div className="text-xs text-slate-400 mt-1">{f.biography.length} chars</div>
        </div>
      </section>

      {/* Academic identifiers */}
      <section className="border-t border-slate-200 pt-8">
        <h2 className="overline mb-4">Academic identifiers</h2>
        <div className="grid sm:grid-cols-2 gap-5">
          <FieldInput label="Google Scholar ID" value={f.google_scholar} onChange={(v) => update("google_scholar", v)} placeholder="e.g. abcde123" />
          <FieldInput label="ResearchGate username" value={f.researchgate} onChange={(v) => update("researchgate", v)} placeholder="e.g. Jane-Smith-42" />
          <FieldInput label="Scopus Author ID" value={f.scopus_id} onChange={(v) => update("scopus_id", v)} placeholder="e.g. 12345678900" />
          <FieldInput label="LinkedIn username" value={f.linkedin} onChange={(v) => update("linkedin", v)} placeholder="e.g. janesmith" />
          <FieldInput label="Personal website" value={f.website} onChange={(v) => update("website", v)} placeholder="https://" />
        </div>
      </section>

      {/* Research profile */}
      <section className="border-t border-slate-200 pt-8">
        <h2 className="overline mb-4">Research profile</h2>

        {/* Keywords — tag input */}
        <div className="mb-5">
          <label className="overline block mb-2">Research keywords</label>
          <div className="flex flex-wrap gap-1.5 mb-2 min-h-[2rem]">
            {f.research_keywords.map((kw) => (
              <span key={kw} className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-[#0F2847]/5 border border-[#0F2847]/20 text-[#0F2847]">
                {kw}
                <button type="button" onClick={() => removeKeyword(kw)} className="hover:text-red-600">
                  <X size={10} strokeWidth={2} />
                </button>
              </span>
            ))}
          </div>
          <input
            type="text"
            value={keywordInput}
            onChange={(e) => setKeywordInput(e.target.value)}
            onKeyDown={addKeyword}
            placeholder="Type keyword and press Enter…"
            className="w-full px-3 py-2 border border-slate-300 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
          />
          <div className="text-[10px] text-slate-400 mt-1">Press Enter or comma to add each keyword</div>
        </div>

        <ChipBlock
          label="Research areas"
          options={RESEARCH_AREAS}
          selected={f.research_areas}
          onToggle={(v) => toggle("research_areas", v)}
          allowCustom
          onCustomAdd={(v) => { if (!f.research_areas.includes(v)) update("research_areas", [...f.research_areas, v]); }}
        />
        <ChipBlock
          label="Research methods"
          options={METHODS_OPTS}
          selected={f.methods}
          onToggle={(v) => toggle("methods", v)}
        />
        <ChipBlock
          label="Software &amp; tools"
          options={SOFTWARE_OPTS}
          selected={f.software_skills}
          onToggle={(v) => toggle("software_skills", v)}
          allowCustom
          onCustomAdd={(v) => { if (!f.software_skills.includes(v)) update("software_skills", [...f.software_skills, v]); }}
        />
        <ChipBlock
          label="Skills"
          options={SKILLS_OPTS}
          selected={f.skills}
          onToggle={(v) => toggle("skills", v)}
          allowCustom
          onCustomAdd={(v) => { if (!f.skills.includes(v)) update("skills", [...f.skills, v]); }}
        />
      </section>

      {/* Teaching / domain */}
      {(f.primary_domain === "teaching" || f.primary_domain === "both") && (
        <section className="border-t border-slate-200 pt-8">
          <h2 className="overline mb-4">Teaching</h2>
          <ChipBlock
            label="Teaching areas"
            options={TEACHING_AREAS_OPTS}
            selected={f.teaching_areas}
            onToggle={(v) => toggle("teaching_areas", v)}
          />
        </section>
      )}
      {(f.primary_domain === "research" || f.primary_domain === "both" || !f.primary_domain) && (
        <section className="border-t border-slate-200 pt-8">
          <h2 className="overline mb-4">Professional expertise</h2>
          <ChipBlock
            options={PROFESSIONAL_EXPERTISE_OPTS}
            selected={f.professional_expertise}
            onToggle={(v) => toggle("professional_expertise", v)}
          />
        </section>
      )}

      {/* Collaboration */}
      <section className="border-t border-slate-200 pt-8">
        <h2 className="overline mb-4">Collaboration &amp; availability</h2>
        <div className="mb-5">
          <label className="overline block mb-2">Status</label>
          <select
            value={f.availability}
            onChange={(e) => update("availability", e.target.value)}
            className="px-3 py-2 border border-slate-300 bg-white text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
          >
            {AVAILABILITY_OPTIONS.map((o) => <option key={o}>{o}</option>)}
          </select>
        </div>
        <div className="mb-5">
          <div className="overline mb-3">Open to</div>
          <div className="space-y-2">
            {[
              { key: "available_for_collaboration", label: "Collaboration" },
              { key: "available_for_supervision",   label: "PhD / Masters Supervision" },
              { key: "available_for_reviewing",     label: "Peer Review" },
              { key: "available_for_consulting",    label: "Consulting" },
            ].map(({ key, label }) => (
              <label key={key} className="flex items-center gap-3 cursor-pointer text-sm">
                <input
                  type="checkbox"
                  checked={f[key]}
                  onChange={(e) => update(key, e.target.checked)}
                  className="accent-[#0F2847]"
                />
                <span className="text-slate-700">{label}</span>
              </label>
            ))}
          </div>
        </div>
        <ChipBlock
          label="Can contribute"
          options={CONTRIBUTE_OPTS}
          selected={f.can_contribute}
          onToggle={(v) => toggle("can_contribute", v)}
        />
        <ChipBlock
          label="Looking for"
          options={LOOKING_OPTS}
          selected={f.looking_for}
          onToggle={(v) => toggle("looking_for", v)}
          allowCustom
          onCustomAdd={(v) => { if (!f.looking_for.includes(v)) update("looking_for", [...f.looking_for, v]); }}
        />
      </section>

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-slate-200 sticky bottom-0 bg-white py-4">
        <button
          onClick={save}
          disabled={saving}
          className="bg-[#0F2847] text-white px-6 py-3 text-sm hover:bg-slate-800 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save changes"}
        </button>
        <button
          onClick={() => {
            if (dirty && !window.confirm("Discard unsaved changes?")) return;
            onClose();
          }}
          className="border border-slate-300 px-6 py-3 text-sm hover:bg-slate-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ─── Form primitives ──────────────────────────────────────────────────────────

function FieldInput({ label, value, onChange, type = "text", placeholder }) {
  return (
    <div>
      <label className="overline block mb-2">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2 border border-slate-300 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
      />
    </div>
  );
}

function FieldSelect({ label, value, onChange, options }) {
  return (
    <div>
      <label className="overline block mb-2">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-slate-300 bg-white text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
      >
        <option value="">Select…</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

function ChipBlock({ label, options, selected, onToggle, allowCustom, onCustomAdd }) {
  const [customInput, setCustomInput] = useState("");
  const addCustom = (e) => {
    e.preventDefault();
    const v = customInput.trim();
    if (v && onCustomAdd) { onCustomAdd(v); setCustomInput(""); }
  };
  return (
    <div className="mt-5">
      {label && <label className="overline block mb-2" dangerouslySetInnerHTML={{ __html: label }} />}
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button
            key={o}
            type="button"
            onClick={() => onToggle(o)}
            className={`px-3 py-1.5 text-xs border ${
              selected.includes(o)
                ? "bg-[#0F2847] text-white border-[#0F2847]"
                : "bg-white text-slate-700 border-slate-300 hover:border-slate-500"
            }`}
          >
            {o}
          </button>
        ))}
        {/* Show custom items not in options list */}
        {selected.filter((s) => !options.includes(s)).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onToggle(s)}
            className="px-3 py-1.5 text-xs border bg-[#0F2847] text-white border-[#0F2847]"
          >
            {s}
          </button>
        ))}
      </div>
      {allowCustom && (
        <form onSubmit={addCustom} className="flex gap-2 mt-2">
          <input
            type="text"
            value={customInput}
            onChange={(e) => setCustomInput(e.target.value)}
            placeholder="Add custom…"
            className="px-2 py-1 text-xs border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
          />
          <button type="submit" className="px-2 py-1 text-xs border border-slate-300 hover:bg-slate-50">
            <Plus size={10} strokeWidth={2} />
          </button>
        </form>
      )}
    </div>
  );
}
