import React, { useState, useEffect, useCallback } from "react";
import { AIWorkspaceLayout } from "@/layouts";
import {
  User, Brain, Target, Activity, Network, Lightbulb, Heart,
  Clock, Settings, RefreshCw, Database, ChevronDown, ChevronUp,
  AlertCircle, CheckCircle, Info, Eye, EyeOff, Zap
} from "lucide-react";
import ResearchHealth  from "../components/twin/ResearchHealth";
import GoalTracker     from "../components/twin/GoalTracker";
import TwinTimeline    from "../components/twin/TwinTimeline";
import {
  getMyTwin, syncTwin, getProfile, getWorkingStyle, getHealth,
  getTimeline, getRecommendations, listGoals, updatePrivacy, resetPreferences,
} from "../services/twinEngine";

// ── Tabs ─────────────────────────────────────────────────────────────────────

const TABS = [
  { id: "overview",     label: "Overview",         icon: Brain },
  { id: "identity",     label: "Research Identity",icon: User },
  { id: "expertise",    label: "Expertise",         icon: Zap },
  { id: "goals",        label: "Goals",             icon: Target },
  { id: "activity",     label: "Activity",          icon: Activity },
  { id: "health",       label: "Research Health",   icon: Heart },
  { id: "recommendations", label: "Recommendations", icon: Lightbulb },
  { id: "timeline",     label: "Timeline",          icon: Clock },
  { id: "settings",     label: "Settings",          icon: Settings },
];

// ── Helper components ────────────────────────────────────────────────────────

const CONF_STYLE = {
  high:         { color: "#047857", bg: "#F0FDF4", label: "Strong evidence" },
  medium:       { color: "#B45309", bg: "#FFFBEB", label: "Partial evidence" },
  low:          { color: "#6B7280", bg: "#F9FAFB", label: "Limited evidence" },
  insufficient: { color: "#6B7280", bg: "#F9FAFB", label: "Insufficient data" },
};

function ConfBadge({ confidence }) {
  const s = CONF_STYLE[confidence] || CONF_STYLE.low;
  return (
    <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold" style={{ color: s.color, background: s.bg }}>
      {s.label}
    </span>
  );
}

function EvidenceBlock({ evidence = [], policy_note }) {
  const [open, setOpen] = useState(false);
  if (!evidence.length && !policy_note) return null;
  return (
    <div className="mt-2 border-t border-slate-100 pt-2">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-600"
      >
        <Database size={9} />
        Evidence sources
        {open ? <ChevronUp size={9} /> : <ChevronDown size={9} />}
      </button>
      {open && (
        <div className="mt-1.5 space-y-1">
          {evidence.map((ev, i) => (
            <p key={i} className="text-[10px] text-slate-500">
              <span className="font-medium">{ev.source}:</span> {ev.detail}
            </p>
          ))}
          {policy_note && <p className="text-[9px] text-slate-400 italic">{policy_note}</p>}
        </div>
      )}
    </div>
  );
}

function Section({ title, children, className = "" }) {
  return (
    <div className={`bg-white rounded-xl border border-slate-200 p-5 ${className}`}>
      {title && <h3 className="text-[11px] font-bold text-slate-500 uppercase tracking-widest mb-4">{title}</h3>}
      {children}
    </div>
  );
}

// ── Overview tab ─────────────────────────────────────────────────────────────

function OverviewTab({ twin, profile, ws, recs }) {
  const activity = twin?.activity_summary || {};
  const domains  = profile?.profile?.research_domains?.slice(0, 5) || [];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Activity summary */}
      <Section title="Activity Summary">
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: "Manuscripts",    value: activity.manuscripts_count ?? 0 },
            { label: "Projects",       value: activity.projects_count ?? 0 },
            { label: "Collaborations", value: activity.collaborations_count ?? 0 },
            { label: "Grants",         value: activity.grants_count ?? 0 },
            { label: "ORCID Pubs",     value: activity.orcid_publications ?? 0 },
            { label: "Teaching",       value: activity.teaching_lessons ?? 0 },
          ].map(({ label, value }) => (
            <div key={label} className="text-center p-3 bg-slate-50 rounded-lg">
              <p className="text-xl font-bold text-slate-800">{value}</p>
              <p className="text-[10px] text-slate-400 mt-0.5">{label}</p>
            </div>
          ))}
        </div>
        {activity.last_computed && (
          <p className="text-[10px] text-slate-400 mt-3 text-center">
            Last updated: {new Date(activity.last_computed).toLocaleDateString()}
          </p>
        )}
        <p className="text-[10px] text-slate-400 mt-1 text-center">From Synaptiq platform database</p>
      </Section>

      {/* Research domains */}
      <Section title="Top Research Domains">
        {domains.length === 0 ? (
          <p className="text-[11px] text-slate-400">No domains identified yet. Sync your twin to analyze your manuscripts and projects.</p>
        ) : (
          <div className="space-y-2">
            {domains.map((d, i) => (
              <div key={i} className="flex items-center justify-between">
                <span className="text-[12px] text-slate-700 capitalize">{d.domain}</span>
                <ConfBadge confidence={d.confidence} />
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Working style */}
      <Section title="Working Style Observations">
        {(!ws?.observations?.length) ? (
          <p className="text-[11px] text-slate-400">No patterns identified yet.</p>
        ) : (
          <div className="space-y-2">
            {ws.observations.slice(0, 4).map((o, i) => (
              <div key={i} className="flex items-start gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 flex-shrink-0" />
                <p className="text-[12px] text-slate-600">{o.pattern}</p>
              </div>
            ))}
            {ws.methodology && <p className="text-[9px] text-slate-400 italic mt-2">{ws.methodology}</p>}
          </div>
        )}
      </Section>

      {/* Top recommendations */}
      <Section title="Top Recommendations">
        {(!recs?.recommendations?.length) ? (
          <p className="text-[11px] text-slate-400">No recommendations yet. Sync your twin to generate personalized guidance.</p>
        ) : (
          <div className="space-y-2">
            {recs.recommendations.slice(0, 3).map((r, i) => (
              <div key={i} className="p-2.5 rounded-lg border border-slate-100">
                <p className="text-[12px] font-medium text-slate-700">{r.title}</p>
                <p className="text-[10px] text-slate-400 mt-0.5">{r.why}</p>
                <ConfBadge confidence={r.confidence} />
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}

// ── Identity tab ──────────────────────────────────────────────────────────────

function IdentityTab({ profile }) {
  const p = profile?.profile || {};
  return (
    <div className="space-y-4">
      <Section title="Research Identity">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Career Stage</p>
            <p className="text-[13px] font-semibold text-slate-700 capitalize">{p.career_stage?.replace(/_/g, " ") || "Unknown"}</p>
            {p.career_stage_evidence?.length > 0 && (
              <EvidenceBlock evidence={p.career_stage_evidence} />
            )}
          </div>
          <div>
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Research Character</p>
            <p className="text-[13px] text-slate-600">{p.interdisciplinary_activity?.assessment || "Insufficient data"}</p>
            {p.interdisciplinary_activity?.methodology && (
              <p className="text-[10px] text-slate-400 mt-1">{p.interdisciplinary_activity.methodology}</p>
            )}
          </div>
        </div>
      </Section>

      <Section title="Research Domains">
        {(!p.research_domains?.length) ? (
          <p className="text-[11px] text-slate-400">No domains identified. Sync your twin to analyze manuscripts and projects.</p>
        ) : (
          <div className="space-y-3">
            {p.research_domains.map((d, i) => (
              <div key={i} className="border-b border-slate-50 pb-3 last:border-0">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[12px] font-semibold text-slate-700 capitalize">{d.domain}</span>
                  <ConfBadge confidence={d.confidence} />
                </div>
                <p className="text-[10px] text-slate-400">{d.evidence_count} verified data point(s)</p>
                <EvidenceBlock evidence={d.evidence} />
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Emerging Interests">
        {(!p.emerging_interests?.length) ? (
          <p className="text-[11px] text-slate-400">No emerging interests detected yet.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {p.emerging_interests.map((d, i) => (
              <span key={i} className="text-[11px] px-2.5 py-1 bg-amber-50 text-amber-700 border border-amber-100 rounded-full capitalize">
                {d.domain}
              </span>
            ))}
          </div>
        )}
        <p className="text-[9px] text-slate-400 mt-3">Emerging interests have fewer than 3 verified evidence points. They may become established domains as activity increases.</p>
      </Section>
    </div>
  );
}

// ── Expertise tab ─────────────────────────────────────────────────────────────

function ExpertiseTab({ profile }) {
  const p = profile?.profile || {};
  const methods = p.methodological_expertise || [];
  return (
    <div className="space-y-4">
      <Section title="Methodological Expertise">
        {methods.length === 0 ? (
          <p className="text-[11px] text-slate-400">No methodological expertise detected. Add more manuscripts with abstracts and keywords to improve detection.</p>
        ) : (
          <div className="space-y-2">
            {methods.map((m, i) => (
              <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-slate-50">
                <div className="flex-1">
                  <p className="text-[12px] font-medium text-slate-700 capitalize">{m.method}</p>
                  <p className="text-[10px] text-slate-400">{m.evidence?.[0]?.detail || ""}</p>
                </div>
                <ConfBadge confidence={m.confidence} />
              </div>
            ))}
          </div>
        )}
        <p className="text-[10px] text-slate-400 mt-3 italic">
          Derived from manuscript abstracts and keywords only. Not an assessment of methodological skill.
        </p>
      </Section>

      <Section title="Publication Themes">
        {(!p.publication_themes?.length) ? (
          <p className="text-[11px] text-slate-400">No publication themes identified yet.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {p.publication_themes.map((t, i) => (
              <span key={i} className="text-[11px] px-2.5 py-1 bg-blue-50 text-blue-700 border border-blue-100 rounded-full capitalize">
                {t.domain}
              </span>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}

// ── Activity tab ──────────────────────────────────────────────────────────────

function ActivityTab({ twin }) {
  const a = twin?.activity_summary || {};
  const ai = twin?.ai_context || {};
  return (
    <div className="space-y-4">
      <Section title="Platform Activity Summary">
        <div className="space-y-2 text-[12px] text-slate-600">
          <p><span className="font-medium">{a.manuscripts_count ?? 0}</span> manuscript(s) on Synaptiq</p>
          <p><span className="font-medium">{a.projects_count ?? 0}</span> research project(s)</p>
          <p><span className="font-medium">{a.collaborations_count ?? 0}</span> accepted collaboration(s)</p>
          <p><span className="font-medium">{a.grants_count ?? 0}</span> grant application(s)</p>
          <p><span className="font-medium">{a.orcid_publications ?? 0}</span> ORCID-linked publication(s)</p>
          <p><span className="font-medium">{a.teaching_lessons ?? 0}</span> teaching lesson(s)</p>
        </div>
        <p className="text-[10px] text-slate-400 mt-3">All counts from Synaptiq platform database. Sync twin to update.</p>
      </Section>

      <Section title="AI Interaction Patterns">
        {(!ai.accepted_suggestion_types?.length && !ai.rejected_suggestion_types?.length) ? (
          <p className="text-[11px] text-slate-400">No AI interaction patterns recorded yet.</p>
        ) : (
          <div className="space-y-2">
            {ai.accepted_suggestion_types?.slice(0, 5).map((t, i) => (
              <div key={i} className="flex items-center gap-2">
                <CheckCircle size={12} className="text-emerald-500" />
                <span className="text-[11px] text-slate-600">{t}</span>
              </div>
            ))}
          </div>
        )}
        <p className="text-[9px] text-slate-400 mt-2 italic">You can reset these preferences in Settings.</p>
      </Section>
    </div>
  );
}

// ── Recommendations tab ───────────────────────────────────────────────────────

function RecommendationsTab({ recs, loading }) {
  if (loading) return <div className="text-center py-12 text-[11px] text-slate-400">Generating…</div>;
  if (!recs) return null;
  if (recs.disabled) return (
    <div className="text-center py-12 text-[11px] text-slate-500">
      {recs.note}
    </div>
  );

  return (
    <div className="space-y-3">
      <p className="text-[11px] text-slate-500">{recs.policy_note}</p>
      {(recs.recommendations || []).map((r, i) => (
        <div key={i} className={`border rounded-xl p-4 ${r.urgent ? "border-orange-200 bg-orange-50/30" : "border-slate-200"}`}>
          <div className="flex items-start justify-between gap-2 mb-2">
            <p className="text-[13px] font-semibold text-slate-800">{r.title}</p>
            <ConfBadge confidence={r.confidence} />
          </div>
          <p className="text-[11px] text-slate-600 mb-2">{r.why}</p>
          <EvidenceBlock evidence={r.evidence} />
          <p className="text-[10px] text-slate-400 mt-2">{r.confidence_basis}</p>
        </div>
      ))}
      {(!recs.recommendations?.length) && (
        <p className="text-center text-[11px] text-slate-400 py-8">No recommendations yet. Sync your twin to generate personalized guidance.</p>
      )}
    </div>
  );
}

// ── Settings tab ──────────────────────────────────────────────────────────────

function SettingsTab({ twin, onRefresh }) {
  const privacy = twin?.privacy || {};
  const [saving,    setSaving]    = useState(false);
  const [resetting, setResetting] = useState(false);
  const [msg,       setMsg]       = useState("");

  async function handlePrivacy(field, value) {
    setSaving(true);
    try {
      await updatePrivacy({ [field]: value });
      setMsg("Saved.");
      onRefresh?.();
    } catch { setMsg("Error saving."); }
    finally { setSaving(false); setTimeout(() => setMsg(""), 2000); }
  }

  async function handleReset() {
    if (!window.confirm("Reset all learned preferences? This cannot be undone.")) return;
    setResetting(true);
    try {
      await resetPreferences();
      setMsg("Preferences reset.");
      onRefresh?.();
    } catch { setMsg("Error resetting."); }
    finally { setResetting(false); setTimeout(() => setMsg(""), 3000); }
  }

  return (
    <div className="space-y-4">
      <Section title="Privacy Settings">
        <div className="space-y-4">
          <label className="flex items-center justify-between cursor-pointer">
            <div>
              <p className="text-[12px] font-medium text-slate-700">Personalization enabled</p>
              <p className="text-[10px] text-slate-400">Allow the Twin to learn from your activity and generate recommendations</p>
            </div>
            <input
              type="checkbox"
              checked={privacy.personalization_enabled ?? true}
              onChange={e => handlePrivacy("personalization_enabled", e.target.checked)}
              className="w-4 h-4 accent-blue-600"
            />
          </label>
          <label className="flex items-center justify-between cursor-pointer">
            <div>
              <p className="text-[12px] font-medium text-slate-700">Share with institution</p>
              <p className="text-[10px] text-slate-400">Allow institution administrators to view your Twin data (disabled by default)</p>
            </div>
            <input
              type="checkbox"
              checked={privacy.share_with_institution ?? false}
              onChange={e => handlePrivacy("share_with_institution", e.target.checked)}
              className="w-4 h-4 accent-blue-600"
            />
          </label>
          {msg && <p className="text-[11px] text-blue-600">{msg}</p>}
        </div>
      </Section>

      <Section title="Data Control">
        <div className="space-y-3">
          <div>
            <p className="text-[12px] font-medium text-slate-700 mb-1">Reset learned preferences</p>
            <p className="text-[10px] text-slate-400 mb-2">Clears working style observations, AI interaction patterns, and user corrections. The twin can relearn from your activity.</p>
            <button
              onClick={handleReset}
              disabled={resetting}
              className="px-3 py-1.5 bg-red-50 text-red-600 text-[11px] font-medium rounded-lg border border-red-200 hover:bg-red-100 transition-colors disabled:opacity-50"
            >
              {resetting ? "Resetting…" : "Reset preferences"}
            </button>
          </div>
          <div className="pt-3 border-t border-slate-100">
            <p className="text-[10px] text-slate-400">
              The Digital Research Twin is private by default. Only you can see this data unless you explicitly enable institution sharing above.
              GDPR compliance: you may reset or export your Twin data at any time.
            </p>
          </div>
        </div>
      </Section>

      <Section title="Excluded Items">
        <p className="text-[11px] text-slate-600 mb-2">
          {privacy.excluded_manuscript_ids?.length ?? 0} manuscript(s) excluded ·{" "}
          {privacy.excluded_project_ids?.length ?? 0} project(s) excluded
        </p>
        <p className="text-[10px] text-slate-400">
          To exclude an item, use the "Exclude from Twin" option in the manuscript or project view.
          Excluded items are not used in domain analysis or working style learning.
        </p>
      </Section>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function DigitalTwin() {
  const [activeTab, setActiveTab] = useState("overview");
  const [twin,      setTwin]      = useState(null);
  const [profile,   setProfile]   = useState(null);
  const [ws,        setWs]        = useState(null);
  const [health,    setHealth]    = useState(null);
  const [timeline,  setTimeline]  = useState(null);
  const [recs,      setRecs]      = useState(null);
  const [goals,     setGoals]     = useState(null);
  const [loading,   setLoading]   = useState({});
  const [syncing,   setSyncing]   = useState(false);
  const [syncMsg,   setSyncMsg]   = useState("");

  const setLoad = (key, val) => setLoading(l => ({ ...l, [key]: val }));

  const loadTab = useCallback(async (tab) => {
    if (tab === "overview") {
      setLoad("overview", true);
      const [t, p, w, r] = await Promise.all([
        getMyTwin().catch(() => null),
        getProfile().catch(() => null),
        getWorkingStyle().catch(() => null),
        getRecommendations().catch(() => null),
      ]);
      setTwin(t?.data);
      setProfile(p?.data);
      setWs(w?.data);
      setRecs(r?.data);
      setLoad("overview", false);
    } else if (tab === "identity" || tab === "expertise") {
      if (!profile) {
        setLoad("profile", true);
        const p = await getProfile().catch(() => null);
        setProfile(p?.data);
        setLoad("profile", false);
      }
    } else if (tab === "health") {
      setLoad("health", true);
      const h = await getHealth().catch(() => null);
      setHealth(h?.data);
      setLoad("health", false);
    } else if (tab === "timeline") {
      setLoad("timeline", true);
      const t = await getTimeline().catch(() => null);
      setTimeline(t?.data);
      setLoad("timeline", false);
    } else if (tab === "recommendations") {
      setLoad("recs", true);
      const r = await getRecommendations().catch(() => null);
      setRecs(r?.data);
      setLoad("recs", false);
    } else if (tab === "goals") {
      setLoad("goals", true);
      const g = await listGoals().catch(() => null);
      setGoals(g?.data);
      setLoad("goals", false);
    } else if (tab === "activity") {
      if (!twin) {
        setLoad("twin", true);
        const t = await getMyTwin().catch(() => null);
        setTwin(t?.data);
        setLoad("twin", false);
      }
    } else if (tab === "settings") {
      if (!twin) {
        setLoad("twin", true);
        const t = await getMyTwin().catch(() => null);
        setTwin(t?.data);
        setLoad("twin", false);
      }
    }
  }, [profile, twin]);

  useEffect(() => { loadTab(activeTab); }, [activeTab]);

  async function handleSync() {
    setSyncing(true);
    setSyncMsg("");
    try {
      const res = await syncTwin();
      setSyncMsg(`Synced at ${new Date(res.data.synced_at).toLocaleTimeString()}`);
      // Reload current tab
      setTwin(null); setProfile(null); setWs(null); setHealth(null);
      setTimeline(null); setRecs(null); setGoals(null);
      await loadTab(activeTab);
    } catch {
      setSyncMsg("Sync failed — try again");
    } finally {
      setSyncing(false);
      setTimeout(() => setSyncMsg(""), 4000);
    }
  }

  async function handleGoalsRefresh() {
    setLoad("goals", true);
    const g = await listGoals().catch(() => null);
    setGoals(g?.data);
    setLoad("goals", false);
  }

  async function handleSettingsRefresh() {
    const t = await getMyTwin().catch(() => null);
    setTwin(t?.data);
  }

  const isLoading = Object.values(loading).some(Boolean);

  return (
    <AIWorkspaceLayout
      title="Digital Research Twin"
      subtitle="Your evolving academic intelligence layer — derived from verified platform activity only"
      actions={
        <div className="flex items-center gap-3">
          {syncMsg && <p className="text-[11px] text-blue-600">{syncMsg}</p>}
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-[11px] font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={12} className={syncing ? "animate-spin" : ""} />
            {syncing ? "Syncing…" : "Sync Twin"}
          </button>
        </div>
      }
    >
      <div className="flex flex-1 overflow-hidden" style={{ margin: "-24px", height: "calc(100% + 48px)" }}>
        {/* Sidebar tabs */}
        <nav className="w-52 bg-white border-r border-slate-200 flex-shrink-0 overflow-y-auto">
          <div className="py-2">
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`w-full flex items-center gap-2.5 px-4 py-2.5 text-left text-[12px] font-medium transition-colors ${
                  activeTab === t.id
                    ? "bg-blue-50 text-blue-700 border-r-2 border-blue-600"
                    : "text-slate-600 hover:bg-slate-50"
                }`}
              >
                <t.icon size={14} />
                {t.label}
              </button>
            ))}
          </div>
        </nav>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-6">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="w-5 h-5 rounded-full border-2 border-blue-400 border-t-transparent animate-spin" />
            </div>
          )}

          {!isLoading && (
            <>
              {activeTab === "overview"     && <OverviewTab twin={twin} profile={profile} ws={ws} recs={recs} />}
              {activeTab === "identity"     && <IdentityTab profile={profile} />}
              {activeTab === "expertise"    && <ExpertiseTab profile={profile} />}
              {activeTab === "goals"        && <GoalTracker goals={goals} loading={loading.goals} onRefresh={handleGoalsRefresh} />}
              {activeTab === "activity"     && <ActivityTab twin={twin} />}
              {activeTab === "health"       && <ResearchHealth health={health} loading={loading.health} />}
              {activeTab === "recommendations" && <RecommendationsTab recs={recs} loading={loading.recs} />}
              {activeTab === "timeline"     && <TwinTimeline timeline={timeline} loading={loading.timeline} />}
              {activeTab === "settings"     && <SettingsTab twin={twin} onRefresh={handleSettingsRefresh} />}
            </>
          )}
        </main>
      </div>
    </AIWorkspaceLayout>
  );
}
