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
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import api from "@/lib/api";

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

export default function AcademicPassport() {
  const { user: me, refreshMe } = useAuth();
  const location = useLocation();
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
    loadPubs();
  }, [me?.id, loadPubs]);

  const handleSyncOpenAlex = async () => {
    setSyncing(true);
    try {
      const { data } = await api.post("/reputation/sync-openalex");
      setReputation(data.reputation);
    } finally {
      setSyncing(false);
    }
  };

  // Supports plain <Link to="/academic-passport#some_section"> from child
  // cards (e.g. "View all publications") without a full page reload — maps
  // the old anchor onto its new tab.
  useEffect(() => {
    const h = location.hash?.replace("#", "");
    if (!h) return;
    const tab = HASH_TO_TAB[h] || (TABS.some((t) => t.id === h) ? h : null);
    if (tab) setActiveTab(tab);
  }, [location.hash]);

  const { exportCV, downloadPassport, shareProfile } = usePassportActions({ profile: me, passport });

  if (!me) {
    return <div className="p-6"><SkeletonPage /></div>;
  }

  const pubsTotal = pubs?.total ?? me.publications_count ?? 0;
  const publicUrl = passport?.public_url ? window.location.origin + passport.public_url : null;

  const tabProps = {
    overview:   <OverviewTab
                  profile={me} verification={verification} completion={completion}
                  pubsTotal={pubsTotal} recentEvents={recentEvents}
                  onEdit={() => setEditOpen(true)} onGoToTab={setActiveTab}
                />,
    research:   <ResearchTab
                  profile={me} impact={impact} researchRank={researchRank}
                  pubs={pubs} pubsLoading={pubsLoading} pubQuery={pubQuery}
                  onQuery={(q) => { setPubQuery(q); loadPubs(q); }}
                  onRefresh={() => loadPubs(pubQuery)}
                  projects={projects} collaborations={collaborations}
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
        onSaved={refreshMe}
      />
    </div>
  );
}
