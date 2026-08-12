/* eslint-disable */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { useFirstExperience } from "@/hooks/useFirstExperience";
import { ResearchLayout } from "@/layouts";
import FirstExperience from "@/components/onboarding/FirstExperience";
import { WorkspaceSkeleton } from "@/components/workspace";
import WorkflowLauncher from "@/components/layout/WorkflowLauncher";
import { TID } from "@/lib/testIds";
import api from "@/lib/api";
import { WARM, NAVY, NAVY2, NAVY_LIGHT } from "@/lib/tokens";

import WelcomeHeader     from "./WelcomeHeader";
import MyWork            from "./MyWork";
import AICommandCenter   from "./AICommandCenter";
import Activity          from "./Activity";
import Analytics         from "./Analytics";
import QuickActions      from "./QuickActions";
import KpiCards          from "./KpiCards";
import Upcoming          from "./Upcoming";
import Recommendations   from "./Recommendations";
import PersonalProgress  from "./PersonalProgress";
import Learning          from "./Learning";
import FooterSummary     from "./FooterSummary";

export default function Home() {
  const { user }   = useAuth();
  const navigate   = useNavigate();

  // ── Core Domain Data Contracts (Preserved flawlessly) ──────────────────────
  const [feed,        setFeed]        = useState(null);
  const [manuscripts, setManuscripts] = useState([]);
  const [workspaces,  setWorkspaces]  = useState([]);
  const [impact,      setImpact]      = useState(null);

  // ── Secondary Metadata Stream (Preserved flawlessly) ────────────────────────
  const [billing,     setBilling]     = useState(null);
  const [aiConvs,     setAiConvs]     = useState([]);
  const [deadlines,   setDeadlines]   = useState([]);
  const [notifCount,  setNotifCount]  = useState(0);

  const [launcherOpen, setLauncherOpen] = useState(false);

  const fex = useFirstExperience(user?.id);
  const [fexVisible, setFexVisible] = useState(!fex.isComplete);

  useEffect(() => {
    Promise.all([
      api.get("/discover/feed").catch(() => ({ data: {} })),
      api.get("/manuscripts").catch(() => ({ data: [] })),
      api.get("/workspaces").catch(() => ({ data: [] })),
      api.get("/research-impact/dashboard").catch(() => ({ data: null })),
    ]).then(([feedRes, msRes, wsRes, impRes]) => {
      setFeed(feedRes.data || {});
      setManuscripts((Array.isArray(msRes.data) ? msRes.data : []).slice(0, 8));
      setWorkspaces((Array.isArray(wsRes.data) ? wsRes.data : []).slice(0, 8));
      setImpact(impRes.data);
    });

    api.get("/billing/subscription").then(r => setBilling(r.data)).catch(() => {});
    api.get("/ai-os/conversations").then(r => setAiConvs((r.data?.conversations || r.data || []).slice(0, 3))).catch(() => {});
    api.get("/deadlines/mine", { params: { limit: 5 } }).then(r => setDeadlines(r.data?.items || [])).catch(() => {});
    api.get("/notifications").then(r => {
      const d = r.data;
      setNotifCount(Array.isArray(d) ? d.filter(n => !n.read).length : (d?.unread_count || 0));
    }).catch(() => {});
  }, []);

  // AUTH-BUG parity fix: this bell count used to be a one-time fetch, so it
  // silently drifted from the TopNav bell on the very same page (which
  // updates live off the same WebSocket event). Listen for the identical
  // "synaptiq:notification" event MobileTopBar/MobileBottomNav already use.
  useEffect(() => {
    const handler = () => setNotifCount(n => n + 1);
    window.addEventListener("synaptiq:notification", handler);
    return () => window.removeEventListener("synaptiq:notification", handler);
  }, []);

  if (fexVisible) {
    return (
      <ResearchLayout>
        <FirstExperience
          user={user}
          steps={fex.steps}
          progress={fex.progress}
          completedCount={fex.completedCount}
          markStep={fex.markStep}
          markStepSilent={fex.markStepSilent}
          isComplete={fex.isComplete}
          onComplete={() => setFexVisible(false)}
        />
      </ResearchLayout>
    );
  }

  if (!feed) return <WorkspaceSkeleton rows={8} />;

  const kpi = impact?.kpi;

  const hero = (
    <section
      className="relative overflow-hidden"
      style={{
        margin:     "-24px 0 0",
        background: `radial-gradient(1100px 520px at 15% -10%, ${NAVY_LIGHT} 0%, transparent 60%), linear-gradient(165deg, ${NAVY2} 0%, ${NAVY} 100%)`,
      }}
    >
      {/* ambient dot-grid texture */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          opacity: 0.05,
          backgroundImage: "radial-gradient(circle, #ffffff 1px, transparent 1px)",
          backgroundSize: "26px 26px",
        }}
        aria-hidden="true"
      />

      <div className="relative max-w-[1180px] mx-auto px-6 md:px-10 pt-7 pb-14">
        <WelcomeHeader user={user} billing={billing} notifCount={notifCount} navigate={navigate} />
        <AICommandCenter aiConvs={aiConvs} credits={billing?.credits} navigate={navigate} />
        <Analytics kpi={kpi} feed={feed} manuscripts={manuscripts} workspaces={workspaces} />
      </div>
    </section>
  );

  return (
    <div data-testid={TID.discoverFeed} style={{ background: WARM, flex: 1, display: "flex", flexDirection: "column" }}>
    <ResearchLayout customHero={hero} noPad>

      {/* ══════════════════════════════════════════════════════════════════
          THE SURFACE — where the actual work lives.
          ══════════════════════════════════════════════════════════════ */}
      <div className="max-w-[1180px] mx-auto px-1 md:px-2 pt-16 pb-16 space-y-16">

        <div className="sq-fade-up">
          <QuickActions onOpenLauncher={() => setLauncherOpen(true)} />
        </div>

        <div className="sq-fade-up sq-delay-1">
          <KpiCards kpi={kpi} feed={feed} manuscripts={manuscripts} workspaces={workspaces} billing={billing} />
        </div>

        <div className="sq-fade-up sq-delay-1">
          <MyWork manuscripts={manuscripts} workspaces={workspaces} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_300px] gap-x-14 gap-y-16 items-start sq-fade-up sq-delay-2">
          <div className="flex flex-col gap-16 min-w-0">
            <Activity feed={feed} manuscripts={manuscripts} />
            <Recommendations feed={feed} />
          </div>
          <div className="flex flex-col gap-12">
            <Upcoming deadlines={deadlines} />
            <PersonalProgress />
            <Learning />
          </div>
        </div>

      </div>

      {/* ══════════════════════════════════════════════════════════════════
          THE STATUS BAR — a quiet dark strip mirroring the deck above.
          ══════════════════════════════════════════════════════════════ */}
      <div className="max-w-[1180px] mx-auto px-1 md:px-2 pb-10">
        <footer style={{ background: NAVY2, borderRadius: 16 }} className="px-6 py-4">
          <FooterSummary billing={billing} />
        </footer>
      </div>

      <WorkflowLauncher open={launcherOpen} onClose={() => setLauncherOpen(false)} />

    </ResearchLayout>
    </div>
  );
}