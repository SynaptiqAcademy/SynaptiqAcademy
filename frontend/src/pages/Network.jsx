/* eslint-disable */
import React, { useCallback, useEffect, useState } from "react";
import { DiscoveryLayout } from "@/layouts";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import {
  Search, Users, UserPlus, Bookmark, BookmarkCheck, MessageSquare,
  Filter, X, CheckCircle, ChevronDown, ChevronUp, ExternalLink,
  GraduationCap, Microscope, BarChart2, Globe2, Sparkles,
  Building2, Target, ArrowRight, BrainCircuit, MapPin,
  Activity, BookOpen, FlaskConical, Star,
} from "lucide-react";
import { Avatar } from "@/components/ds/Avatar";
import { USER_TYPE_OPTIONS, userTypeLabel } from "../lib/userTypes";
import { SkeletonCard } from "@/components/ds/LoadingState";
import EmptyState from "@/components/ds/EmptyState";
import { Spinner } from "@/components/ds/LoadingState";
import { useAuth } from "../contexts/AuthContext";
import { getDashboardMode } from "../lib/dashboardConfig";
import ReputationLevel from "../components/reputation/ReputationLevel";
import { useReputationBatch } from "../hooks/useReputation";
import InviteModal from "../components/marketplace/InviteModal";
import { toast } from "sonner";
import { ACCENT, NAVY, WARM } from "@/lib/tokens";

// ─── Brand tokens ─────────────────────────────────────────────────────────────
const BORDER = "#E4E8EF";

// ─── Constants ────────────────────────────────────────────────────────────────
const AREAS = [
  "Artificial Intelligence", "Healthcare", "Management", "Economics", "Education",
  "Public Health", "Cybersecurity", "Engineering", "Psychology", "Biology",
  "Physics", "Chemistry", "Mathematics", "Computer Science", "Neuroscience",
  "Environmental Science", "Political Science", "Sociology", "Law", "History",
];
const AVAIL  = ["", "Available", "Limited Availability", "Not Currently Available"];
const USER_TYPES = [{ value: "", label: "All types" }, ...USER_TYPE_OPTIONS];
const COMMON_METHODS = [
  "Qualitative", "Quantitative", "Mixed Methods", "Systematic Review",
  "Meta-Analysis", "RCT", "Survey", "Ethnography", "Case Study",
  "Machine Learning", "Statistical Modeling", "Longitudinal Study",
];
const COMMON_SKILLS = [
  "Python", "R", "SPSS", "MATLAB", "NVivo", "Stata", "ATLAS.ti", "SAS",
  "Tableau", "Power BI", "Excel", "QGIS", "MAXQDA",
];

const MODE_HEADER = {
  research: { title: "Research Network",     sub: "Discover collaborators, experts and institutions across your research domain." },
  teaching: { title: "Academic Network",     sub: "Connect with educators, faculty and trainers across institutions worldwide." },
  hybrid:   { title: "Academic Network",     sub: "Connect with researchers, educators and professionals across disciplines." },
};
const MODE_SUGGESTED_TYPES = {
  research: ["phd_candidate", "postdoctoral_researcher", "researcher", "university_faculty"],
  teaching: ["educator", "trainer", "university_faculty"],
  hybrid:   ["researcher", "educator", "university_faculty", "industry_professional"],
};

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

// ─── ORCID badge ──────────────────────────────────────────────────────────────
function OrcidBadge({ orcid }) {
  const id = orcid?.orcid_id || orcid;
  if (!id) return null;
  return (
    <a
      href={`https://orcid.org/${id}`}
      target="_blank"
      rel="noopener noreferrer"
      onClick={(e) => e.stopPropagation()}
      title={`ORCID: ${id}`}
      style={{ display: "inline-flex", alignItems: "center", gap: 2, fontSize: 10, fontFamily: "monospace", fontWeight: 700, color: "#a6ce39", border: "1px solid #a6ce3940", padding: "2px 6px", textDecoration: "none" }}
    >
      iD
    </a>
  );
}

// ─── Match score badge ────────────────────────────────────────────────────────
function MatchBadge({ score }) {
  if (!score || score <= 0) return null;
  const color = score >= 60 ? { text: "#059669", bg: "#F0FDF4", border: "#A7F3D0" }
              : score >= 30 ? { text: "#0891B2", bg: "#F0F9FF", border: "#BAE6FD" }
              :               { text: "#94A3B8", bg: WARM,      border: BORDER };
  return (
    <span style={{ fontSize: 10, fontFamily: "monospace", color: color.text, background: color.bg, border: `1px solid ${color.border}`, padding: "2px 6px", fontWeight: 600 }}>
      {score}% match
    </span>
  );
}

// ─── Researcher Card (premium redesign) ───────────────────────────────────────
function ResearcherCard({ u, repScore, savedIds, onSaveToggle, onInvite, currentUserId }) {
  const isSelf   = u.id === currentUserId;
  const isSaved  = savedIds.has(u.id);
  const [saveBusy, setSaveBusy] = useState(false);
  const [hovered, setHovered]   = useState(false);

  const handleSave = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setSaveBusy(true);
    try {
      if (isSaved) {
        await api.delete(`/researchers/saved/${u.id}`);
        toast.success("Removed from saved");
      } else {
        await api.post(`/researchers/saved/${u.id}`);
        toast.success("Researcher saved");
      }
      onSaveToggle(u.id, !isSaved);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed");
    } finally {
      setSaveBusy(false);
    }
  };

  const areaColor = (a) => {
    const idx = AREAS.indexOf(a);
    const hues = ["#0891B2","#7C3AED","#059669","#D97706","#EA580C","#0891B2","#8A1538","#374151"];
    return hues[idx % hues.length] || NAVY;
  };

  const areas = (u.research_areas || []).length > 0 ? u.research_areas : (u.teaching_areas || []);

  return (
    <div
      style={{ display: "flex", flexDirection: "column", border: `1px solid ${hovered ? NAVY + "50" : BORDER}`, background: "white", transition: "border-color 0.15s, box-shadow 0.15s, transform 0.12s", transform: hovered ? "translateY(-2px)" : "none", boxShadow: hovered ? "0 4px 20px rgba(15,40,71,0.1)" : "none" }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <Link to={`/profile/${u.id}`} style={{ display: "block", padding: "18px 18px 14px", textDecoration: "none" }}>

        {/* Avatar row */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 14 }}>
          <div style={{ position: "relative", flexShrink: 0 }}>
            <Avatar url={u.avatar_url} name={u.full_name} size={48} />
            {u.availability === "Available" && (
              <span style={{ position: "absolute", bottom: -1, right: -1, width: 11, height: 11, borderRadius: "50%", background: "#10B981", border: "2px solid white" }} title="Available for collaboration" />
            )}
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#0f172a", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", letterSpacing: "-0.01em" }}>
              {u.full_name}
            </div>
            <div style={{ fontSize: 11, color: "#64748B", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginTop: 2 }}>
              {userTypeLabel(u, "Researcher")}
            </div>
            {u.institution && (
              <div style={{ display: "flex", alignItems: "center", gap: 3, fontSize: 11, color: "#94A3B8", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                <Building2 size={9} strokeWidth={1.5} style={{ flexShrink: 0 }} />
                {u.institution}
              </div>
            )}
            {u.country && (
              <div style={{ display: "flex", alignItems: "center", gap: 3, fontSize: 10, color: "#CBD5E1", marginTop: 1 }}>
                <MapPin size={9} strokeWidth={1.5} style={{ flexShrink: 0 }} />
                {u.country}
              </div>
            )}
          </div>
        </div>

        {/* Research areas */}
        {areas.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 12 }}>
            {areas.slice(0, 3).map((a) => {
              const c = areaColor(a);
              return (
                <span key={a} style={{ fontSize: 10, padding: "2px 7px", color: c, background: c + "12", border: `1px solid ${c}30`, fontWeight: 500 }}>
                  {a}
                </span>
              );
            })}
            {areas.length > 3 && (
              <span style={{ fontSize: 10, padding: "2px 7px", color: "#94A3B8", background: WARM, border: `1px solid ${BORDER}` }}>
                +{areas.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Metrics row */}
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6, paddingTop: 10, borderTop: `1px solid ${BORDER}` }}>
          <ReputationLevel reputation={repScore} variant="chip" />
          {u.orcid?.orcid_id && <OrcidBadge orcid={u.orcid} />}
          {u.match_score > 0 && <MatchBadge score={u.match_score} />}
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
            {u.h_index > 0 && (
              <span style={{ fontSize: 11, color: "#94A3B8", fontFamily: "monospace" }}>
                h <strong style={{ color: "#374151" }}>{u.h_index}</strong>
              </span>
            )}
            {u.publications_count > 0 && (
              <span style={{ fontSize: 11, color: "#94A3B8", fontFamily: "monospace" }}>
                <strong style={{ color: "#374151" }}>{u.publications_count}</strong> pub
              </span>
            )}
          </div>
        </div>
      </Link>

      {/* Actions row */}
      {!isSelf && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "10px 18px 14px", borderTop: `1px solid ${BORDER}` }}>
          <button
            onClick={handleSave}
            disabled={saveBusy}
            style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, padding: "5px 10px", border: `1px solid ${isSaved ? NAVY + "40" : BORDER}`, background: isSaved ? WARM : "white", color: isSaved ? NAVY : "#64748B", cursor: "pointer", transition: "all 0.15s", opacity: saveBusy ? 0.5 : 1 }}
            title={isSaved ? "Remove from saved" : "Save researcher"}
          >
            {isSaved ? <BookmarkCheck size={11} strokeWidth={1.5} /> : <Bookmark size={11} strokeWidth={1.5} />}
            {isSaved ? "Saved" : "Save"}
          </button>
          <Link
            to={`/messages/${u.id}`}
            style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, padding: "5px 10px", border: `1px solid ${BORDER}`, color: "#64748B", textDecoration: "none", transition: "border-color 0.15s" }}
            onClick={(e) => e.stopPropagation()}
          >
            <MessageSquare size={11} strokeWidth={1.5} />
            Message
          </Link>
          <button
            onClick={(e) => { e.preventDefault(); onInvite(u); }}
            style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 4, fontSize: 11, padding: "5px 10px", border: `1px solid ${BORDER}`, background: "white", color: "#64748B", cursor: "pointer", transition: "all 0.15s" }}
            title="Invite to collaborate"
          >
            <UserPlus size={11} strokeWidth={1.5} />
            Invite
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Discover Section ─────────────────────────────────────────────────────────
function DiscoverSection({ title, icon: Icon, accent, researchers, savedIds, onSaveToggle, onInvite, currentUserId, repMap }) {
  if (!researchers || researchers.length === 0) return null;
  const color = accent || NAVY;
  return (
    <section>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, paddingBottom: 12, borderBottom: `1px solid ${BORDER}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {Icon && (
            <div style={{ width: 26, height: 26, background: color + "15", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Icon size={12} strokeWidth={1.5} style={{ color }} />
            </div>
          )}
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8" }}>
              {title}
            </div>
          </div>
        </div>
        <span style={{ fontSize: 10, fontFamily: "monospace", color: "#CBD5E1" }}>
          {researchers.length} researcher{researchers.length !== 1 ? "s" : ""}
        </span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
        {researchers.slice(0, 6).map((u) => (
          <ResearcherCard
            key={u.id}
            u={u}
            repScore={repMap?.[u.id]}
            savedIds={savedIds}
            onSaveToggle={onSaveToggle}
            onInvite={onInvite}
            currentUserId={currentUserId}
          />
        ))}
      </div>
    </section>
  );
}

// ─── Main Network Page ────────────────────────────────────────────────────────
export default function Network() {
  const { user } = useAuth();
  const dashboardMode = getDashboardMode(user);
  const header = MODE_HEADER[dashboardMode] || MODE_HEADER.research;
  const suggestedTypes = MODE_SUGGESTED_TYPES[dashboardMode] || [];

  const [activeTab, setActiveTab]       = useState("hub");
  const [hubData, setHubData]           = useState(null);
  const [hubLoading, setHubLoading]     = useState(true);
  const [users, setUsers]               = useState([]);
  const [savedUsers, setSavedUsers]     = useState([]);
  const [sections, setSections]         = useState(null);
  const [savedIds, setSavedIds]         = useState(new Set());
  const [loading, setLoading]           = useState(true);
  const [inviting, setInviting]         = useState(null);
  const [nextCursor, setNextCursor]     = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Search params
  const [q, setQ]                       = useState("");
  const [area, setArea]                 = useState("");
  const [avail, setAvail]               = useState("");
  const [userType, setUserType]         = useState("");
  const [country, setCountry]           = useState("");
  const [method, setMethod]             = useState("");
  const [softwareSkill, setSoftwareSkill] = useState("");
  const [minHIndex, setMinHIndex]       = useState(0);
  const [hasOrcid, setHasOrcid]         = useState(false);
  const [hasOpenalex, setHasOpenalex]   = useState(false);
  const [forCollab, setForCollab]       = useState(false);
  const [forReviewing, setForReviewing] = useState(false);
  const [forConsulting, setForConsulting] = useState(false);
  const [forSupervision, setForSupervision] = useState(false);

  const userIds = users.map((u) => u.id);
  const { data: repMap } = useReputationBatch(userIds);

  useEffect(() => {
    api.get("/researchers/saved/ids").then((r) => {
      setSavedIds(new Set(r.data.ids || []));
    }).catch(() => {});
  }, []);

  const load = useCallback(async (reset = true) => {
    setLoading(true);
    const params = {};
    if (q)              params.q = q;
    if (area)           params.research_area = area;
    if (avail)          params.availability = avail;
    if (userType)       params.user_type = userType;
    if (country)        params.country = country;
    if (method)         params.method = method;
    if (softwareSkill)  params.software_skill = softwareSkill;
    if (minHIndex > 0)  params.min_h_index = minHIndex;
    if (hasOrcid)       params.has_orcid = true;
    if (hasOpenalex)    params.has_openalex = true;
    if (forCollab)      params.available_for_collaboration = true;
    if (forReviewing)   params.available_for_reviewing = true;
    if (forConsulting)  params.available_for_consulting = true;
    if (forSupervision) params.available_for_supervision = true;
    if (!reset && nextCursor) params.cursor = nextCursor;
    params.limit = 30;
    try {
      const { data } = await api.get("/users", { params });
      const items = Array.isArray(data) ? data : (data.items || []);
      setUsers((prev) => reset ? items : [...prev, ...items]);
      setNextCursor(Array.isArray(data) ? null : (data.next_cursor || null));
    } catch {
      toast.error("Failed to load researchers");
    } finally {
      setLoading(false);
    }
  }, [q, area, avail, userType, country, method, softwareSkill, minHIndex, hasOrcid, hasOpenalex, forCollab, forReviewing, forConsulting, forSupervision, nextCursor]);

  useEffect(() => { load(true); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (activeTab === "hub" && !hubData) {
      setHubLoading(true);
      Promise.all([
        api.get("/researchers/discover/sections").catch(() => ({ data: {} })),
        api.get("/network/collaborations", { params: { limit: 6 } }).catch(() => ({ data: [] })),
        api.get("/network/groups", { params: { limit: 6 } }).catch(() => ({ data: [] })),
        api.get("/network/activity", { params: { limit: 8 } }).catch(() => ({ data: [] })),
        api.get("/network/stats").catch(() => ({ data: {} })),
      ]).then(([secRes, collabRes, groupsRes, actRes, statsRes]) => {
        const collabs = Array.isArray(collabRes.data) ? collabRes.data : (collabRes.data?.items || []);
        const groups  = Array.isArray(groupsRes.data)  ? groupsRes.data  : (groupsRes.data?.items || groupsRes.data?.groups || []);
        const feed    = Array.isArray(actRes.data)     ? actRes.data     : (actRes.data?.items || []);
        setHubData({ sections: secRes.data, collabs, groups, feed, stats: statsRes.data });
      }).finally(() => setHubLoading(false));
    }
  }, [activeTab, hubData]);

  useEffect(() => {
    if (activeTab === "discover" && !sections) {
      api.get("/researchers/discover/sections").then((r) => setSections(r.data)).catch(() => setSections({}));
    }
  }, [activeTab, sections]);

  useEffect(() => {
    if (activeTab === "saved") {
      api.get("/researchers/saved").then((r) => setSavedUsers(r.data.items || [])).catch(() => setSavedUsers([]));
    }
  }, [activeTab]);

  const handleSaveToggle = (userId, nowSaved) => {
    setSavedIds((prev) => {
      const next = new Set(prev);
      if (nowSaved) next.add(userId); else next.delete(userId);
      return next;
    });
    if (activeTab === "saved" && !nowSaved) {
      setSavedUsers((prev) => prev.filter((u) => u.id !== userId));
    }
  };

  const clearFilters = () => {
    setQ(""); setArea(""); setAvail(""); setUserType(""); setCountry("");
    setMethod(""); setSoftwareSkill(""); setMinHIndex(0);
    setHasOrcid(false); setHasOpenalex(false);
    setForCollab(false); setForReviewing(false); setForConsulting(false); setForSupervision(false);
  };

  const activeFilterCount = [area, avail, userType, country, method, softwareSkill].filter(Boolean).length
    + [hasOrcid, hasOpenalex, forCollab, forReviewing, forConsulting, forSupervision].filter(Boolean).length
    + (minHIndex > 0 ? 1 : 0);

  const firstName = user?.full_name?.split(" ")[0] || "Researcher";

  return (
    <DiscoveryLayout title={header.title} subtitle={header.sub}>
    <div>
      {/* ── COMMAND HEADER ───────────────────────────────────────────────── */}
      <div style={{ background: NAVY, margin: "-24px -24px 0", padding: "36px 28px 28px" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          <div>
            <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 600, marginBottom: 8 }}>
              {getGreeting()}, {firstName}
            </div>
            <h1 style={{ fontSize: 26, fontWeight: 700, color: "white", margin: "0 0 6px", letterSpacing: "-0.03em", lineHeight: 1.15 }}>
              {header.title}
            </h1>
            <p style={{ fontSize: 13, color: "rgba(255,255,255,0.45)", margin: 0, maxWidth: 480 }}>
              {header.sub}
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            {savedIds.size > 0 && (
              <button
                onClick={() => setActiveTab("saved")}
                style={{ display: "inline-flex", alignItems: "center", gap: 6, border: "1px solid rgba(255,255,255,0.18)", color: "rgba(255,255,255,0.7)", padding: "7px 14px", fontSize: 12, fontWeight: 500, background: "transparent", cursor: "pointer" }}
              >
                <BookmarkCheck size={12} strokeWidth={1.5} />
                Saved ({savedIds.size})
              </button>
            )}
            <button
              onClick={() => setActiveTab("discover")}
              style={{ display: "inline-flex", alignItems: "center", gap: 6, background: ACCENT, color: "white", border: "none", padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
              onMouseEnter={(e) => e.currentTarget.style.background = "#a01a42"}
              onMouseLeave={(e) => e.currentTarget.style.background = ACCENT}
            >
              <Sparkles size={13} strokeWidth={1.5} />
              Discover Researchers
            </button>
          </div>
        </div>
      </div>

      {/* ── TAB NAVIGATION ───────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: 0, borderBottom: `1px solid ${BORDER}`, background: "white", marginBottom: 24 }}>
        {[
          { key: "hub",      label: "Community Hub", icon: Activity,     sub: "Network overview" },
          { key: "search",   label: "Search",        icon: Search,       sub: "Find by name, area or keyword" },
          { key: "discover", label: "Discover",       icon: Sparkles,     sub: "Curated recommendations" },
          { key: "saved",    label: "Saved",          icon: BookmarkCheck, sub: savedIds.size > 0 ? `${savedIds.size} saved` : "Your shortlist" },
        ].map((t) => {
          const active = activeTab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 2, padding: "14px 20px", borderBottom: `2px solid ${active ? NAVY : "transparent"}`, background: "transparent", cursor: "pointer", transition: "border-color 0.15s", borderTop: "none", borderLeft: "none", borderRight: "none", minWidth: 140 }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <t.icon size={13} strokeWidth={1.5} style={{ color: active ? NAVY : "#94A3B8" }} />
                <span style={{ fontSize: 13, fontWeight: active ? 700 : 500, color: active ? NAVY : "#64748B" }}>{t.label}</span>
                {t.key === "saved" && savedIds.size > 0 && (
                  <span style={{ fontSize: 10, fontFamily: "monospace", background: NAVY, color: "white", padding: "1px 6px", fontWeight: 600 }}>{savedIds.size}</span>
                )}
              </div>
              <span style={{ fontSize: 10, color: "#CBD5E1" }}>{t.sub}</span>
            </button>
          );
        })}
      </div>

      {/* ══ COMMUNITY HUB TAB ══════════════════════════════════════════════ */}
      {activeTab === "hub" && (
        <div>
          {hubLoading ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
              {[1,2,3,4,5,6].map((i) => <SkeletonCard key={i} rows={4} />)}
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 36 }}>

              {/* Stats strip */}
              {hubData?.stats && Object.keys(hubData.stats).length > 0 && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 1, background: BORDER }}>
                  {[
                    { label: "Researchers",   value: hubData.stats.total_users     || hubData.stats.researchers || "—" },
                    { label: "Teams",         value: hubData.stats.total_groups     || hubData.stats.groups || "—" },
                    { label: "Collaborations",value: hubData.stats.total_collabs    || hubData.stats.collaborations || "—" },
                    { label: "Institutions",  value: hubData.stats.total_institutions || hubData.stats.institutions || "—" },
                  ].map(({ label, value }) => (
                    <div key={label} style={{ background: "white", padding: "18px 20px", textAlign: "center" }}>
                      <div style={{ fontSize: 22, fontWeight: 700, color: NAVY, letterSpacing: "-0.03em", fontFamily: "monospace" }}>{value}</div>
                      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8", marginTop: 4 }}>{label}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Recommended Researchers */}
              <DiscoverSection
                title="Recommended for you"
                icon={Sparkles}
                accent={ACCENT}
                researchers={hubData?.sections?.recommended || []}
                savedIds={savedIds}
                onSaveToggle={handleSaveToggle}
                onInvite={setInviting}
                currentUserId={user?.id}
                repMap={repMap}
              />

              {/* Available Collaborators */}
              <DiscoverSection
                title="Open to collaboration"
                icon={Users}
                accent={NAVY}
                researchers={hubData?.sections?.available_collaborators || []}
                savedIds={savedIds}
                onSaveToggle={handleSaveToggle}
                onInvite={setInviting}
                currentUserId={user?.id}
                repMap={repMap}
              />

              {/* Top Scholars */}
              <DiscoverSection
                title="Top scholars"
                icon={Star}
                accent="#D97706"
                researchers={hubData?.sections?.top_scholars || []}
                savedIds={savedIds}
                onSaveToggle={handleSaveToggle}
                onInvite={setInviting}
                currentUserId={user?.id}
                repMap={repMap}
              />

              {/* Open Collaboration Requests */}
              {hubData?.collabs?.length > 0 && (
                <section>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, paddingBottom: 12, borderBottom: `1px solid ${BORDER}` }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ width: 26, height: 26, background: "#059669" + "15", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <Target size={12} strokeWidth={1.5} style={{ color: "#059669" }} />
                      </div>
                      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8" }}>Open Collaboration Requests</div>
                    </div>
                    <Link to="/network/collaborations" style={{ fontSize: 12, color: NAVY, textDecoration: "none", fontWeight: 600, display: "flex", alignItems: "center", gap: 4 }}>
                      View all <ArrowRight size={11} strokeWidth={2} />
                    </Link>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
                    {hubData.collabs.slice(0, 4).map((c) => (
                      <div key={c._id || c.id} style={{ border: `1px solid ${BORDER}`, background: "white", padding: 16 }}>
                        <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", marginBottom: 4 }}>{c.title}</div>
                        <div style={{ fontSize: 11, color: "#64748B", marginBottom: 8, lineHeight: 1.5 }}>{c.type} · {c.discipline}</div>
                        {c.description && (
                          <div style={{ fontSize: 12, color: "#94A3B8", lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden", marginBottom: 10 }}>{c.description}</div>
                        )}
                        <Link to={`/network/collaborations`} style={{ fontSize: 11, color: NAVY, fontWeight: 600, textDecoration: "none", display: "flex", alignItems: "center", gap: 4 }}>
                          Apply <ArrowRight size={10} strokeWidth={2} />
                        </Link>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Popular Research Teams */}
              {hubData?.groups?.length > 0 && (
                <section>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, paddingBottom: 12, borderBottom: `1px solid ${BORDER}` }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ width: 26, height: 26, background: "#7C3AED" + "15", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <BrainCircuit size={12} strokeWidth={1.5} style={{ color: "#7C3AED" }} />
                      </div>
                      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8" }}>Popular Research Teams</div>
                    </div>
                    <Link to="/teams" style={{ fontSize: 12, color: NAVY, textDecoration: "none", fontWeight: 600, display: "flex", alignItems: "center", gap: 4 }}>
                      View all <ArrowRight size={11} strokeWidth={2} />
                    </Link>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
                    {hubData.groups.slice(0, 6).map((g) => (
                      <Link key={g._id || g.id} to={`/teams/${g._id || g.id}`} style={{ border: `1px solid ${BORDER}`, background: "white", padding: 16, textDecoration: "none", display: "block", transition: "border-color 0.12s" }}
                        onMouseEnter={(e) => e.currentTarget.style.borderColor = NAVY + "50"}
                        onMouseLeave={(e) => e.currentTarget.style.borderColor = BORDER}
                      >
                        <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 6 }}>{g.type?.replace(/_/g, " ") || "Team"}</div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", marginBottom: 4 }}>{g.name}</div>
                        {g.discipline && <div style={{ fontSize: 11, color: "#64748B" }}>{g.discipline}</div>}
                        <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 8, display: "flex", alignItems: "center", gap: 4 }}>
                          <Users size={10} strokeWidth={1.5} />
                          {g.member_count ?? 0} members
                        </div>
                      </Link>
                    ))}
                  </div>
                </section>
              )}

              {/* International Researchers */}
              <DiscoverSection
                title="International researchers"
                icon={Globe2}
                accent="#0891B2"
                researchers={hubData?.sections?.international_matches || []}
                savedIds={savedIds}
                onSaveToggle={handleSaveToggle}
                onInvite={setInviting}
                currentUserId={user?.id}
                repMap={repMap}
              />

              {/* Available Reviewers */}
              <DiscoverSection
                title="Available for reviewing"
                icon={CheckCircle}
                accent="#059669"
                researchers={hubData?.sections?.available_reviewers || []}
                savedIds={savedIds}
                onSaveToggle={handleSaveToggle}
                onInvite={setInviting}
                currentUserId={user?.id}
                repMap={repMap}
              />

              {/* Research Feed preview */}
              {hubData?.feed?.length > 0 && (
                <section>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, paddingBottom: 12, borderBottom: `1px solid ${BORDER}` }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ width: 26, height: 26, background: "#374151" + "15", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <Activity size={12} strokeWidth={1.5} style={{ color: "#374151" }} />
                      </div>
                      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8" }}>Recent Activity</div>
                    </div>
                    <Link to="/feed" style={{ fontSize: 12, color: NAVY, textDecoration: "none", fontWeight: 600, display: "flex", alignItems: "center", gap: 4 }}>
                      Research Feed <ArrowRight size={11} strokeWidth={2} />
                    </Link>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {hubData.feed.slice(0, 5).map((item, i) => {
                      const actor = item.actor || item.user || {};
                      return (
                        <div key={item._id || item.id || i} style={{ display: "flex", alignItems: "flex-start", gap: 12, padding: "12px 16px", background: "white", border: `1px solid ${BORDER}` }}>
                          <Avatar url={actor.avatar_url} name={actor.full_name || actor.name || "?"} size={28} />
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <span style={{ fontSize: 13, fontWeight: 600, color: "#0f172a" }}>{actor.full_name || actor.name || "Researcher"}</span>
                            {" "}<span style={{ fontSize: 12, color: "#64748B" }}>{item.content || item.type?.replace(/_/g, " ")}</span>
                            {item.title && <div style={{ fontSize: 12, color: "#374151", marginTop: 4, fontWeight: 500 }}>{item.title}</div>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}

              {/* Empty state */}
              {!hubData?.sections?.recommended?.length && !hubData?.collabs?.length && !hubData?.groups?.length && (
                <EmptyState
                  icon={<GraduationCap />}
                  title="Complete your profile to unlock the community"
                  description="Synaptiq matches researchers based on your research areas, methodology and institution. Add these to your profile to unlock curated recommendations."
                  action={<Link to="/profile-setup" style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "white", padding: "9px 20px", fontSize: 13, fontWeight: 600, textDecoration: "none" }}>Complete your profile<ArrowRight size={12} strokeWidth={2} /></Link>}
                  size="md"
                  dashed={true}
                />
              )}

            </div>
          )}
        </div>
      )}

      {/* ══ SEARCH TAB ══════════════════════════════════════════════════════ */}
      {activeTab === "search" && (
        <div>
          {/* Quick type chips */}
          {suggestedTypes.length > 0 && !userType && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center", marginBottom: 16 }}>
              <span style={{ fontSize: 11, color: "#94A3B8" }}>Quick filter:</span>
              {suggestedTypes.map((t) => {
                const opt = USER_TYPE_OPTIONS.find((o) => o.value === t);
                if (!opt) return null;
                return (
                  <button
                    key={t}
                    onClick={() => { setUserType(t); load(true); }}
                    style={{ fontSize: 11, border: `1px solid ${BORDER}`, padding: "4px 12px", color: "#475569", background: "white", cursor: "pointer" }}
                    onMouseEnter={(e) => e.currentTarget.style.borderColor = NAVY + "60"}
                    onMouseLeave={(e) => e.currentTarget.style.borderColor = BORDER}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          )}

          {/* Main search bar */}
          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <div style={{ position: "relative", flex: 1 }}>
              <Search size={13} strokeWidth={1.5} style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: "#94A3B8" }} />
              <input
                data-testid={TID.networkSearch}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") load(true); }}
                placeholder="Name, institution, research area, keyword, ORCID…"
                style={{ width: "100%", paddingLeft: 34, paddingRight: 12, paddingTop: 9, paddingBottom: 9, border: `1px solid ${BORDER}`, fontSize: 13, color: "#374151", outline: "none", boxSizing: "border-box" }}
                onFocus={(e) => e.currentTarget.style.borderColor = NAVY + "70"}
                onBlur={(e) => e.currentTarget.style.borderColor = BORDER}
              />
            </div>
            <button
              onClick={() => load(true)}
              style={{ background: NAVY, color: "white", border: "none", padding: "9px 18px", fontSize: 13, fontWeight: 600, cursor: "pointer", flexShrink: 0 }}
            >
              Search
            </button>
            <button
              onClick={() => setShowAdvanced((v) => !v)}
              style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, border: `1px solid ${showAdvanced ? NAVY : BORDER}`, padding: "9px 14px", color: showAdvanced ? NAVY : "#64748B", background: showAdvanced ? WARM : "white", cursor: "pointer" }}
            >
              <Filter size={12} strokeWidth={1.5} />
              Filters
              {activeFilterCount > 0 && (
                <span style={{ fontSize: 10, fontFamily: "monospace", background: NAVY, color: "white", padding: "1px 5px", fontWeight: 700 }}>{activeFilterCount}</span>
              )}
              {showAdvanced ? <ChevronUp size={11} strokeWidth={1.5} /> : <ChevronDown size={11} strokeWidth={1.5} />}
            </button>
          </div>

          {/* Advanced filter panel */}
          {showAdvanced && (
            <div style={{ border: `1px solid ${BORDER}`, background: WARM, padding: 20, marginBottom: 20 }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 14 }}>
                {[
                  { label: "Research area", el: <select value={area} onChange={(e) => setArea(e.target.value)} style={selStyle}><option value="">Any area</option>{AREAS.map((a) => <option key={a}>{a}</option>)}</select> },
                  { label: "Country", el: <input value={country} onChange={(e) => setCountry(e.target.value)} placeholder="e.g. United Kingdom" style={inpStyle} /> },
                  { label: "Researcher type", el: <select value={userType} onChange={(e) => setUserType(e.target.value)} style={selStyle}>{USER_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}</select> },
                  { label: "Availability", el: <select value={avail} onChange={(e) => setAvail(e.target.value)} style={selStyle}><option value="">Any</option>{AVAIL.filter(Boolean).map((a) => <option key={a}>{a}</option>)}</select> },
                  { label: "Methodology", el: <select value={method} onChange={(e) => setMethod(e.target.value)} style={selStyle}><option value="">Any method</option>{COMMON_METHODS.map((m) => <option key={m}>{m}</option>)}</select> },
                  { label: "Software / tool", el: <select value={softwareSkill} onChange={(e) => setSoftwareSkill(e.target.value)} style={selStyle}><option value="">Any tool</option>{COMMON_SKILLS.map((s) => <option key={s}>{s}</option>)}</select> },
                  { label: "Min h-index", el: <input type="number" min={0} max={200} value={minHIndex || ""} onChange={(e) => setMinHIndex(Number(e.target.value) || 0)} placeholder="0" style={inpStyle} /> },
                ].map(({ label, el }) => (
                  <div key={label}>
                    <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 5 }}>{label}</div>
                    {el}
                  </div>
                ))}
              </div>

              {/* Boolean toggles */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
                {[
                  { label: "ORCID verified",          state: hasOrcid,       set: setHasOrcid },
                  { label: "OpenAlex synced",         state: hasOpenalex,    set: setHasOpenalex },
                  { label: "Open to collaborate",     state: forCollab,      set: setForCollab },
                  { label: "Available for reviewing", state: forReviewing,   set: setForReviewing },
                  { label: "Available for consulting",state: forConsulting,  set: setForConsulting },
                  { label: "Available for supervision",state:forSupervision, set: setForSupervision },
                ].map(({ label, state, set }) => (
                  <button
                    key={label}
                    onClick={() => set((v) => !v)}
                    style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, border: `1px solid ${state ? NAVY : BORDER}`, padding: "5px 12px", background: state ? WARM : "white", color: state ? NAVY : "#64748B", cursor: "pointer", transition: "all 0.15s", fontWeight: state ? 600 : 400 }}
                  >
                    {state && <CheckCircle size={10} strokeWidth={2} />}
                    {label}
                  </button>
                ))}
              </div>

              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={() => load(true)} style={{ fontSize: 12, background: NAVY, color: "white", border: "none", padding: "7px 16px", cursor: "pointer", fontWeight: 600 }}>
                  Apply filters
                </button>
                {activeFilterCount > 0 && (
                  <button onClick={() => { clearFilters(); }} style={{ fontSize: 12, color: "#64748B", border: `1px solid ${BORDER}`, background: "white", padding: "7px 14px", cursor: "pointer" }}>
                    Clear all ({activeFilterCount})
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Active filter badges */}
          {activeFilterCount > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 14 }}>
              {[
                area && { key: "area", label: area, clear: () => setArea("") },
                country && { key: "country", label: country, clear: () => setCountry("") },
                userType && { key: "type", label: USER_TYPES.find((t) => t.value === userType)?.label || userType, clear: () => setUserType("") },
                avail && { key: "avail", label: avail, clear: () => setAvail("") },
                method && { key: "method", label: method, clear: () => setMethod("") },
                softwareSkill && { key: "skill", label: softwareSkill, clear: () => setSoftwareSkill("") },
                minHIndex > 0 && { key: "h", label: `h-index ≥ ${minHIndex}`, clear: () => setMinHIndex(0) },
                hasOrcid && { key: "orcid", label: "ORCID verified", clear: () => setHasOrcid(false) },
                forCollab && { key: "collab", label: "Open to collaborate", clear: () => setForCollab(false) },
                forReviewing && { key: "review", label: "Available for reviewing", clear: () => setForReviewing(false) },
              ].filter(Boolean).map((f) => (
                <span key={f.key} style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, background: WARM, border: `1px solid ${BORDER}`, padding: "3px 8px", color: "#374151" }}>
                  {f.label}
                  <button onClick={f.clear} style={{ background: "none", border: "none", cursor: "pointer", color: "#94A3B8", padding: 0, lineHeight: 1 }}>
                    <X size={10} strokeWidth={2} />
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Results */}
          <div data-testid={TID.networkList}>
            {loading && users.length === 0 && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
                {[1,2,3,4,5,6].map((i) => <SkeletonCard key={i} rows={4} />)}
              </div>
            )}

            {!loading && users.length === 0 && (
              <NetworkEmptyState hasFilters={!!(q || activeFilterCount > 0)} onClear={() => { clearFilters(); setQ(""); load(true); }} />
            )}

            {users.length > 0 && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
                {users.map((u) => (
                  <ResearcherCard
                    key={u.id}
                    u={u}
                    repScore={repMap?.[u.id]}
                    savedIds={savedIds}
                    onSaveToggle={handleSaveToggle}
                    onInvite={setInviting}
                    currentUserId={user?.id}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Load more */}
          {nextCursor && !loading && (
            <div style={{ display: "flex", justifyContent: "center", marginTop: 28 }}>
              <button
                onClick={() => load(false)}
                style={{ fontSize: 13, color: NAVY, border: `1px solid ${NAVY}40`, padding: "10px 28px", background: "white", cursor: "pointer" }}
              >
                Load more researchers
              </button>
            </div>
          )}
          {loading && users.length > 0 && (
            <div style={{ textAlign: "center", padding: "16px" }}>
              <Spinner size={14} />
            </div>
          )}
        </div>
      )}

      {/* ══ DISCOVER TAB ════════════════════════════════════════════════════ */}
      {activeTab === "discover" && (
        <div>
          {!sections && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
              {[1,2,3,4,5,6].map((i) => <SkeletonCard key={i} rows={4} />)}
            </div>
          )}

          {sections && (
            <div style={{ display: "flex", flexDirection: "column", gap: 36 }}>
              {[
                { key: "recommended",            title: "Recommended for you",      icon: Sparkles,     accent: ACCENT },
                { key: "methodology_experts",     title: "Methodology experts",      icon: BarChart2,    accent: "#7C3AED" },
                { key: "institutional_matches",   title: "At your institution",      icon: GraduationCap,accent: "#059669" },
                { key: "international_matches",   title: "International researchers",icon: Globe2,       accent: "#0891B2" },
                { key: "top_scholars",            title: "Top scholars",             icon: Star,         accent: "#D97706" },
                { key: "available_collaborators", title: "Open to collaboration",    icon: Users,        accent: NAVY },
                { key: "available_reviewers",     title: "Available for reviewing",  icon: CheckCircle,  accent: "#059669" },
              ].map(({ key, title, icon, accent }) => (
                <DiscoverSection
                  key={key}
                  title={title}
                  icon={icon}
                  accent={accent}
                  researchers={sections[key]}
                  savedIds={savedIds}
                  onSaveToggle={handleSaveToggle}
                  onInvite={setInviting}
                  currentUserId={user?.id}
                  repMap={repMap}
                />
              ))}

              {!sections.recommended?.length && !sections.available_collaborators?.length && (
                <EmptyState
                  icon={<GraduationCap />}
                  title="Complete your profile for recommendations"
                  description="Synaptiq matches researchers based on your research areas, methodology and institution. Add these to your profile to unlock curated recommendations."
                  action={<Link to="/academic-passport" style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "white", padding: "9px 20px", fontSize: 13, fontWeight: 600, textDecoration: "none" }}>Complete your profile<ArrowRight size={12} strokeWidth={2} /></Link>}
                  size="md"
                  dashed={true}
                />
              )}
            </div>
          )}
        </div>
      )}

      {/* ══ SAVED TAB ═══════════════════════════════════════════════════════ */}
      {activeTab === "saved" && (
        <div>
          {savedUsers.length === 0 ? (
            <EmptyState
              icon={<Bookmark />}
              title="No saved researchers yet"
              description="Save researchers to build your personal academic shortlist. Use the bookmark icon on any researcher card."
              action={<button onClick={() => setActiveTab("search")} style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "white", border: "none", padding: "9px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>Browse researchers<ArrowRight size={12} strokeWidth={2} /></button>}
              size="md"
              dashed={true}
            />
          ) : (
            <>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 16 }}>
                {savedIds.size} saved researcher{savedIds.size !== 1 ? "s" : ""}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
                {savedUsers.map((u) => (
                  <ResearcherCard
                    key={u.id}
                    u={u}
                    repScore={repMap?.[u.id]}
                    savedIds={savedIds}
                    onSaveToggle={(uid, nowSaved) => {
                      handleSaveToggle(uid, nowSaved);
                      if (!nowSaved) setSavedUsers((prev) => prev.filter((r) => r.id !== uid));
                    }}
                    onInvite={setInviting}
                    currentUserId={user?.id}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* Invite modal */}
      {inviting && (
        <InviteModal
          target={inviting}
          onClose={() => setInviting(null)}
          defaultKind="collaboration"
        />
      )}

    </div>
    </DiscoveryLayout>
  );
}

// ─── Filter input styles ──────────────────────────────────────────────────────
const selStyle = {
  width: "100%", padding: "7px 10px", border: `1px solid ${BORDER}`,
  background: "white", fontSize: 12, color: "#374151", outline: "none",
};
const inpStyle = {
  width: "100%", padding: "7px 10px", border: `1px solid ${BORDER}`,
  fontSize: 12, color: "#374151", outline: "none", boxSizing: "border-box",
};

// ─── Empty State ──────────────────────────────────────────────────────────────
function NetworkEmptyState({ hasFilters, onClear }) {
  return (
    <EmptyState
      icon={<Users />}
      title={hasFilters ? "No researchers match your filters" : "No researchers found"}
      description={
        hasFilters
          ? "Try broadening your search or clearing some filters to discover more researchers."
          : "Complete your profile so other researchers can find and connect with you."
      }
      action={
        hasFilters ? (
          <button
            onClick={onClear}
            style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "white", border: "none", padding: "9px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
          >
            <X size={12} strokeWidth={2} />
            Clear filters
          </button>
        ) : (
          <Link
            to="/academic-passport"
            style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: "white", padding: "9px 20px", fontSize: 13, fontWeight: 600, textDecoration: "none" }}
          >
            Complete your profile
            <ArrowRight size={12} strokeWidth={2} />
          </Link>
        )
      }
      size="md"
      dashed={true}
    />
  );
}
