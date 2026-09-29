/**
 * Academic Passport — the flagship, single identity experience.
 *
 * P1 Phase 7C4.1: full experience/visual redesign. Six primary sections
 * (Overview/Research/Teaching/Reputation/Portfolio/Analytics) now sit
 * behind a compact horizontal PassportNav (replacing the old fixed-width
 * vertical sidebar-inside-a-sidebar), under a premium
 * PassportCredentialHeader (replacing the old PassportHero, which repeated
 * a 7-counter analytics ribbon on every tab). The old permanently-visible
 * right rail (Completion/Trust Health/Verification/Next Steps/AI Insights/
 * Recent Activity/Platform Tip stacked on every tab) is gone — each piece
 * now lives once, in its natural place in the Overview/Reputation/
 * Analytics narrative, so every tab's content gets full width. Every panel
 * still reuses an existing endpoint — no new backend.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { AnimatePresence, motion } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import api from "@/lib/api";
import { connectOrcid, isOrcidAuthenticated } from "@/lib/orcid";

import { PassportNav, TABS } from "@/components/passport/PassportNav";
import { PassportCredentialHeader } from "@/components/passport/PassportCredentialHeader";
import { usePassportActions } from "@/components/passport/QuickActionsBar";
import { EditIdentityModal } from "@/components/passport/EditIdentityModal";
import { SkeletonPage } from "@/components/ds/LoadingState";

import { OverviewTab } from "@/components/passport/tabs/OverviewTab";
import { ResearchTab } from "@/components/passport/tabs/ResearchTab";
import { TeachingTab } from "@/components/passport/tabs/TeachingTab";
import { ReputationTab } from "@/components/passport/tabs/ReputationTab";
import { PortfolioTab } from "@/components/passport/tabs/PortfolioTab";
import { AnalyticsTab } from "@/components/passport/tabs/AnalyticsTab";

// Backward-compat: old anchor-based deep links (e.g. from other pages'
// "View all X" cards, or bookmarked #hashes) still land on the right tab.
const HASH_TO_TAB = {
  academic_identity: "overview",
  research_interests: "overview",
  biography: "overview",
  research_impact: "research",
  publications_panel: "research",
  research_integrations: "research",
  research_reputation: "reputation",
  trust_verification: "overview",
  achievements: "reputation",
  public_portfolio: "portfolio",
  academic_timeline: "portfolio",
};

// Several hashes above land on the same tab section — this maps each one to
// the actual DOM id to scroll to once that tab's content has mounted, so
// "View all X" links from other pages/cards land the user ON the relevant
// section, not just on the right tab with no further feedback (P1 Phase
// 7C4.3 §13/§18 — several of these were previously dead in that sense).
const HASH_TO_ANCHOR_ID = {
  academic_identity: "academic_identity",
  research_interests: "academic_identity",
  biography: "academic_identity",
  research_impact: "research_impact",
  publications_panel: "publications_panel",
  research_integrations: "research-integrations-section",
  trust_verification: "trust_verification",
};

const ORCID_ERROR_MESSAGES = {
  cancelled: "You cancelled the ORCID sign-in.",
  already_linked_to_other_account: "This ORCID iD is already linked to a different SYNAPTIQ account.",
};

export default function AcademicPassport() {
  const { user: me, refreshMe } = useAuth();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [passport, setPassport] = useState(null);
  const [reputation, setReputation] = useState(null);
  const [teachingStats, setTeachingStats] = useState(null);
  const [completion, setCompletion] = useState(null);
  const [pubs, setPubs] = useState(null);
  const [pubsLoading, setPubsLoading] = useState(false);
  const [pubQuery, setPubQuery] = useState("");
  const [projects, setProjects] = useState([]);
  const [projectsTotal, setProjectsTotal] = useState(0);
  const [grantsTotal, setGrantsTotal] = useState(0);
  const [collaborations, setCollaborations] = useState([]);
  const [impact, setImpact] = useState(null);
  const [verification, setVerification] = useState(null);
  const [researchRank, setResearchRank] = useState(null);
  const [repAnalytics, setRepAnalytics] = useState(null);
  const [recentEvents, setRecentEvents] = useState([]);
  const [trustBadges, setTrustBadges] = useState([]);
  const [badgeCatalogue, setBadgeCatalogue] = useState([]);
  const [publicProfile, setPublicProfile] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [editOpen, setEditOpen] = useState(false);

  const initialTab = useMemo(() => {
    const h = location.hash?.replace("#", "");
    return HASH_TO_TAB[h] || (TABS.some((t) => t.id === h) ? h : "overview");
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const [activeTab, setActiveTab] = useState(initialTab);

  const loadPubs = useCallback(async (q = "") => {
    if (!me?.id) return;
    setPubsLoading(true);
    try {
      const params = { limit: 50 };
      if (q) params.q = q;
      const r = await api.get(`/users/${me.id}/publications`, { params });
      setPubs(r.data);
    } catch {
      setPubs({ results: [], total: 0 });
    } finally {
      setPubsLoading(false);
    }
  }, [me?.id]);

  useEffect(() => {
    if (!me?.id) return;
    api.get("/trust/passport").then((r) => setPassport(r.data)).catch(() => {});
    api.get(`/reputation/${me.id}`).then((r) => setReputation(r.data)).catch(() => {});
    api.get("/teaching-analytics/overview", { params: { period: "30d" } }).then((r) => setTeachingStats(r.data)).catch(() => {});
    api.get("/users/me/profile-completion").then((r) => setCompletion(r.data)).catch(() => {});
    api.get("/projects").then((r) => {
      const list = (r.data || []).filter((p) => p.status !== "archived");
      setProjectsTotal(list.length);
      setProjects(list.slice(0, 5));
    }).catch(() => {});
    api.get("/grants").then((r) => setGrantsTotal((r.data || []).length)).catch(() => {});
    api.get("/collaborations/mine").then((r) => setCollaborations((r.data?.active || []).slice(0, 5))).catch(() => {});
    api.get("/research-impact/dashboard", { silentGate: true }).then((r) => setImpact(r.data)).catch(() => {});
    api.get("/verification/me", { silentGate: true }).then((r) => setVerification(r.data)).catch(() => {});
    api.get("/reputation/research/me", { silentGate: true }).then((r) => setResearchRank(r.data)).catch(() => {});
    api.get("/reputation/analytics/me", { silentGate: true }).then((r) => setRepAnalytics(r.data)).catch(() => {});
    api.get("/reputation/events/me", { params: { limit: 5 }, silentGate: true }).then((r) => setRecentEvents(r.data || [])).catch(() => {});
    api.get("/trust/badges", { silentGate: true }).then((r) => setTrustBadges(r.data || [])).catch(() => {});
    api.get("/trust/badges/catalogue", { silentGate: true }).then((r) => setBadgeCatalogue(r.data || [])).catch(() => {});
    api.get("/profiles/me", { silentGate: true }).then((r) => setPublicProfile(r.data)).catch(() => {});
    loadPubs();
  }, [me?.id, loadPubs]);

  // The real, existing public profile URL (ResearcherProfile.jsx's
  // /researcher/:slug route) — used for Share/Export/Preview everywhere in
  // the Passport. Every account has a slug from its first GET /profiles/me
  // (auto-generated, see get_or_create_profile), so this is reliably
  // available, unlike the trust passport's own public_url (no matching
  // frontend route — see usePassportActions).
  const refreshPublicProfile = useCallback(() => {
    api.get("/profiles/me", { silentGate: true }).then((r) => setPublicProfile(r.data)).catch(() => {});
  }, []);

  const handleSyncOpenAlex = async () => {
    setSyncing(true);
    try {
      const { data } = await api.post("/reputation/sync-openalex");
      setReputation(data.reputation);
    } finally {
      setSyncing(false);
    }
  };

  // Re-fetches only the canonical data a Passport mutation can affect — no
  // window.location.reload() anywhere (P1 Phase 7C4.3 §19). Identity edits
  // affect completion + verification (via refreshMe, which updates `me`);
  // ORCID connect/sync additionally affects the trust passport and the
  // publications list.
  const refreshVerificationAndCompletion = useCallback(() => {
    api.get("/users/me/profile-completion").then((r) => setCompletion(r.data)).catch(() => {});
    api.get("/verification/me", { silentGate: true }).then((r) => setVerification(r.data)).catch(() => {});
  }, []);

  const refreshAfterIdentityChange = useCallback(async () => {
    await refreshMe();
    refreshVerificationAndCompletion();
  }, [refreshMe, refreshVerificationAndCompletion]);

  const refreshAfterOrcidChange = useCallback(async () => {
    await refreshMe();
    refreshVerificationAndCompletion();
    api.get("/trust/passport").then((r) => setPassport(r.data)).catch(() => {});
    loadPubs(pubQuery);
  }, [refreshMe, refreshVerificationAndCompletion, loadPubs, pubQuery]);

  const [orcidSyncing, setOrcidSyncing] = useState(false);
  const orcidActionInFlight = useRef(false);

  // Connect ORCID directly from the Passport (P1 Phase 7C4.3 §2): reuses the
  // exact OAuth flow OrcidSettings.jsx has always used, just told to return
  // to /academic-passport instead of the now ORCID-content-free /settings.
  // Guards against double-clicks firing two full-page OAuth redirects.
  const handleConnectOrcid = useCallback(() => {
    if (orcidActionInFlight.current) return;
    orcidActionInFlight.current = true;
    connectOrcid("/academic-passport")
      .catch(() => { toast.error("Could not start the ORCID connection"); orcidActionInFlight.current = false; });
  }, []);

  const handleSyncOrcid = useCallback(async () => {
    if (orcidActionInFlight.current) return;
    orcidActionInFlight.current = true;
    setOrcidSyncing(true);
    try {
      const { data } = await api.post("/orcid/sync");
      const imported = data.publications_imported ?? data.imported ?? 0;
      toast.success(`ORCID synced — ${imported} publication${imported === 1 ? "" : "s"} imported`);
      await refreshAfterOrcidChange();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "ORCID sync failed");
    } finally {
      setOrcidSyncing(false);
      orcidActionInFlight.current = false;
    }
  }, [refreshAfterOrcidChange]);

  // Lands here after a successful/failed direct ORCID connect (backend now
  // redirects back to /academic-passport instead of /settings). Mirrors
  // OrcidSettings.jsx's own query-param handling so the toast + state
  // refresh happen wherever the connection was actually initiated from.
  useEffect(() => {
    const orcidError = searchParams.get("orcid_error");
    const orcidConnected = searchParams.get("orcid") === "connected";
    if (orcidError) {
      toast.error(ORCID_ERROR_MESSAGES[orcidError] || "ORCID sign-in failed. Please try again.");
      setSearchParams((p) => { p.delete("orcid_error"); return p; }, { replace: true });
    } else if (orcidConnected) {
      toast.success("ORCID connected");
      setSearchParams((p) => { p.delete("orcid"); return p; }, { replace: true });
      refreshAfterOrcidChange();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Supports plain <Link to="/academic-passport#some_section"> from child
  // cards (e.g. "View all publications") without a full page reload — maps
  // the old anchor onto its new tab, then scrolls to the actual section
  // once that tab's (AnimatePresence-animated) content has mounted.
  useEffect(() => {
    const h = location.hash?.replace("#", "");
    if (!h) return;
    const tab = HASH_TO_TAB[h] || (TABS.some((t) => t.id === h) ? h : null);
    if (tab) setActiveTab(tab);

    const anchorId = HASH_TO_ANCHOR_ID[h];
    if (!anchorId) return;
    let attempts = 0;
    const tryScroll = () => {
      const el = document.getElementById(anchorId);
      if (el) { el.scrollIntoView({ behavior: "smooth", block: "start" }); return; }
      if (attempts++ < 10) setTimeout(tryScroll, 50);
    };
    setTimeout(tryScroll, 50);
  }, [location.hash]);

  // usePassportActions has no internal hooks of its own (it's a plain
  // function despite the `use` naming convention), but the linter's
  // rules-of-hooks check doesn't know that — called unconditionally, before
  // the early return below, to satisfy it regardless.
  const publicUrl = publicProfile?.slug ? `${window.location.origin}/researcher/${publicProfile.slug}` : null;
  const { exportCV, downloadPassport, shareProfile } = usePassportActions({ profile: me, passport, publicUrl });

  if (!me) {
    return <div className="p-6"><SkeletonPage /></div>;
  }

  const pubsTotal = pubs?.total ?? me.publications_count ?? 0;
  const orcidConnected = isOrcidAuthenticated(me.orcid);

  const tabProps = {
    overview:   <OverviewTab
                  profile={me} verification={verification} completion={completion}
                  pubsTotal={pubsTotal} recentEvents={recentEvents}
                  onEdit={() => setEditOpen(true)} onGoToTab={setActiveTab}
                  onConnectOrcid={handleConnectOrcid} onSyncOrcid={handleSyncOrcid} orcidConnected={orcidConnected}
                  orcidBusy={orcidSyncing}
                />,
    research:   <ResearchTab
                  profile={me} impact={impact} researchRank={researchRank}
                  pubs={pubs} pubsLoading={pubsLoading} pubQuery={pubQuery}
                  onQuery={(q) => { setPubQuery(q); loadPubs(q); }}
                  onRefresh={() => loadPubs(pubQuery)}
                  onSynced={refreshAfterOrcidChange}
                  projects={projects} collaborations={collaborations}
                  onEdit={() => setEditOpen(true)}
                />,
    teaching:   <TeachingTab teachingStats={teachingStats} />,
    reputation: <ReputationTab
                  profile={me} onEditIdentity={() => setEditOpen(true)} passport={passport}
                  repAnalytics={repAnalytics} researchRank={researchRank}
                  onSyncOpenAlex={handleSyncOpenAlex} syncing={syncing}
                  pubCount={pubsTotal} trustBadges={trustBadges} badgeCatalogue={badgeCatalogue}
                />,
    portfolio:  <PortfolioTab
                  profile={me}
                  employments={me.orcid_employments || []}
                  educations={me.orcid_educations || []}
                  pubs={pubs}
                  exportCV={exportCV} downloadPassport={downloadPassport} shareProfile={shareProfile}
                  publicUrl={publicUrl}
                  onSlugChanged={refreshPublicProfile}
                />,
    analytics:  <AnalyticsTab reputation={reputation} teachingStats={teachingStats} />,
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <PassportCredentialHeader
        profile={me}
        passport={passport}
        verification={verification}
        completion={completion}
        onEdit={() => setEditOpen(true)}
        onShare={shareProfile}
        onExport={downloadPassport}
      />

      <PassportNav activeTab={activeTab} onTabChange={setActiveTab} />

      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
        >
          {tabProps[activeTab]}
        </motion.div>
      </AnimatePresence>

      <EditIdentityModal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        profile={me}
        onSaved={refreshAfterIdentityChange}
      />
    </div>
  );
}
