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
import "./home.css";

import WelcomeHeader     from "./WelcomeHeader";
import MyWork            from "./MyWork";
import AICommandCenter   from "./AICommandCenter";
import Activity          from "./Activity";
import QuickActions      from "./QuickActions";
import KpiCards          from "./KpiCards";
import Upcoming          from "./Upcoming";
import Recommendations   from "./Recommendations";
import PersonalProgress  from "./PersonalProgress";
import Learning          from "./Learning";

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

  // Home is a research command centre: who you are and what to ask first,
  // then the work in progress, then what needs attention. It uses the same
  // page header, surfaces and buttons as every other page.
  return (
    <div data-testid={TID.discoverFeed} className="hm" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
    <ResearchLayout noPad>
      <div className="hm-top">
        <WelcomeHeader user={user} />
        <AICommandCenter aiConvs={aiConvs} navigate={navigate} />
      </div>

      <div className="hm-body">
        <KpiCards kpi={kpi} feed={feed} manuscripts={manuscripts} workspaces={workspaces} billing={billing} />

        <div className="hm-grid">
          <div className="hm-main">
            <MyWork manuscripts={manuscripts} workspaces={workspaces} />
            <Activity feed={feed} manuscripts={manuscripts} />
            <Recommendations feed={feed} />
          </div>
          <aside className="hm-aside" aria-label="Needs attention and shortcuts">
            <Upcoming deadlines={deadlines} />
            <QuickActions onOpenLauncher={() => setLauncherOpen(true)} />
            <PersonalProgress />
            <Learning />
          </aside>
        </div>
      </div>

      <WorkflowLauncher open={launcherOpen} onClose={() => setLauncherOpen(false)} />
    </ResearchLayout>
    </div>
  );
}
