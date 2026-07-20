/* eslint-disable */
/**
 * FirstExperience — first-visit guided setup shown instead of the normal
 * dashboard. Renders inside AppShell (sidebar remains visible) but replaces
 * all dashboard content until the user completes all 5 steps or skips.
 *
 * Rules (per spec):
 * - No gradients, no glassmorphism, no neon, no heavy shadows.
 * - Animations: 150–250ms, fade/scale/slide only.
 * - Reuses existing design tokens and real API endpoints only.
 * - Does not modify any backend logic, routing, or business rules.
 */
import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { toast } from "sonner";
import { NAVY, ACCENT, WARM, BRDX, WHITE } from "@/lib/tokens";
import {
  CheckCircle2, Circle, ChevronRight, ArrowRight,
  Link2, BookOpen, FlaskConical, FolderOpen, BrainCircuit,
  X, Sparkles,
} from "lucide-react";

// ─── Design constants ─────────────────────────────────────────────────────────

const BRD = BRDX || "#E4E8EF";
const MUTED   = "#94A3B8";
const TEXT     = "#0F172A";
const TEXT2    = "#475569";
const EMERALD  = "#059669";

// ─── Step definitions ─────────────────────────────────────────────────────────

const STEP_ICON = [Link2, BookOpen, FlaskConical, FolderOpen, BrainCircuit];

const STEPS = [
  {
    title: "Connect ORCID",
    desc: "Link your ORCID iD to import your academic identity. Your publications, h-index, and citations will be calculated from it.",
    time: "30 sec",
  },
  {
    title: "Import Publications",
    desc: "Bring your research portfolio into Synaptiq. Once imported, AI tools have context for every recommendation.",
    time: "1 min",
    to: "/manuscripts",
  },
  {
    title: "Set Research Interests",
    desc: "Choose your primary research domains. Every AI recommendation, collaboration match, and funding alert is shaped by this.",
    time: "30 sec",
  },
  {
    title: "Create a Workspace",
    desc: "Your first workspace organises manuscripts, collaborators, and AI tools around a single project.",
    time: "1 min",
    to: "/workspaces",
  },
  {
    title: "Generate Your Digital Twin",
    desc: "Your Academic Twin simulates your research trajectory, predicts high-impact directions, and benchmarks you against your field.",
    time: "2 min",
    to: "/twin",
  },
];

const RESEARCH_DOMAINS = [
  "Artificial Intelligence", "Machine Learning", "Data Science", "Computer Science",
  "Biomedical Sciences", "Medicine", "Public Health", "Biology", "Chemistry",
  "Physics", "Mathematics", "Statistics", "Engineering", "Environmental Science",
  "Economics", "Psychology", "Sociology", "Political Science", "Education",
  "History", "Philosophy", "Linguistics", "Law", "Architecture",
];

// ─── Component ────────────────────────────────────────────────────────────────

export default function FirstExperience({ user, steps, progress, completedCount, markStep, markStepSilent, isComplete, onComplete }) {
  const navigate = useNavigate();
  const firstName = user?.first_name || user?.full_name?.split(" ")[0] || "Researcher";

  // Active inline step: 0 = ORCID inline, 2 = chips inline, null = none
  const [activeInline, setActiveInline] = useState(null);

  // ORCID inline state
  const [orcidValue, setOrcidValue]   = useState(user?.orcid || "");
  const [orcidSaving, setOrcidSaving] = useState(false);

  // Research interests inline state
  const [selected, setSelected] = useState(new Set(user?.research_areas || []));
  const [areasSaving, setAreasSaving] = useState(false);

  // Completion glow state
  const [celebrating, setCelebrating] = useState(false);

  // Auto-detect pre-filled steps from user profile (once on mount)
  useEffect(() => {
    if (user?.orcid) markStepSilent(0);
    if (user?.research_areas?.length > 0) markStepSilent(2);
  }, []); // intentionally empty — run once on mount

  // Trigger completion animation then hand off to parent
  useEffect(() => {
    if (isComplete && !celebrating) {
      setCelebrating(true);
      const t = setTimeout(() => onComplete?.(), 1400);
      return () => clearTimeout(t);
    }
  }, [isComplete, celebrating, onComplete]);

  // ── Handlers ──────────────────────────────────────────────────────────────

  const saveOrcid = async () => {
    const clean = orcidValue.trim();
    setOrcidSaving(true);
    try {
      await api.patch("/users/me", { orcid: clean });
      markStep(0);
      setActiveInline(null);
      toast.success("ORCID saved.");
    } catch {
      toast.error("Could not save ORCID. Try again.");
    } finally {
      setOrcidSaving(false);
    }
  };

  const skipOrcid = () => { markStep(0); setActiveInline(null); };

  const saveAreas = async () => {
    const areas = [...selected];
    setAreasSaving(true);
    try {
      await api.patch("/users/me", { research_areas: areas });
      markStep(2);
      setActiveInline(null);
      toast.success("Research interests saved.");
    } catch {
      toast.error("Could not save interests. Try again.");
    } finally {
      setAreasSaving(false);
    }
  };

  const skipAreas = () => { markStep(2); setActiveInline(null); };

  const handleNavStep = (index, to) => {
    markStep(index);
    setTimeout(() => navigate(to), 120);
  };

  const skipAll = () => {
    [0, 1, 2, 3, 4].forEach((i) => !steps[i] && markStep(i));
  };

  const toggleDomain = (d) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(d) ? next.delete(d) : next.add(d);
      return next;
    });
  };

  // First incomplete step index (for highlighting)
  const activeStep = steps.findIndex((done) => !done);

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div
      style={{
        minHeight: "calc(100vh - 64px)",
        background: WHITE,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "56px 24px 80px",
        transition: "opacity 0.35s ease",
        opacity: celebrating ? 0 : 1,
      }}
      aria-label="First-time setup"
    >
      <div style={{ width: "100%", maxWidth: 600 }}>

        {/* ── Progress bar ──────────────────────────────────────────────── */}
        <div style={{ marginBottom: 48 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
            <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: MUTED }}>
              Platform Setup
            </span>
            <span style={{ fontSize: 11, fontFamily: "monospace", color: MUTED }}>
              {completedCount} / 5 steps
            </span>
          </div>
          <div style={{ height: 3, background: BRD, width: "100%", overflow: "hidden" }}>
            <div
              style={{
                height: "100%",
                width: `${progress}%`,
                background: progress === 100 ? EMERALD : NAVY,
                transition: "width 0.45s cubic-bezier(0.4, 0, 0.2, 1)",
              }}
            />
          </div>
        </div>

        {/* ── Welcome heading ───────────────────────────────────────────── */}
        <div style={{ marginBottom: 48 }}>
          <h1
            style={{
              fontSize: 30,
              fontWeight: 700,
              color: TEXT,
              margin: "0 0 10px",
              letterSpacing: "-0.035em",
              lineHeight: 1.15,
            }}
          >
            {isComplete ? "Setup complete." : `Welcome, ${firstName}.`}
          </h1>
          <p style={{ fontSize: 15, color: TEXT2, margin: 0, lineHeight: 1.6 }}>
            {isComplete
              ? "Your Research Operating System is ready. Opening your dashboard…"
              : "Set up your Research Operating System in a few steps. This takes around three minutes."}
          </p>
        </div>

        {/* ── Step list ─────────────────────────────────────────────────── */}
        <div
          style={{ display: "flex", flexDirection: "column", gap: 10 }}
          role="list"
          aria-label="Setup steps"
        >
          {STEPS.map((step, i) => {
            const done  = steps[i];
            const isAct = !done && i === activeStep;
            const Icon  = STEP_ICON[i];

            return (
              <div
                key={i}
                role="listitem"
                style={{
                  border: `1px solid ${isAct ? NAVY + "30" : BRD}`,
                  background: done ? WARM : WHITE,
                  padding: 20,
                  transition: "border-color 0.2s, background 0.2s, opacity 0.2s",
                  opacity: !done && !isAct ? 0.55 : 1,
                }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
                  {/* Step indicator */}
                  <div
                    style={{
                      width: 28,
                      height: 28,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      marginTop: 1,
                    }}
                    aria-hidden="true"
                  >
                    {done ? (
                      <CheckCircle2 size={20} strokeWidth={1.5} style={{ color: EMERALD }} />
                    ) : (
                      <div
                        style={{
                          width: 20,
                          height: 20,
                          borderRadius: "50%",
                          border: `1.5px solid ${isAct ? NAVY : BRD}`,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <span style={{ fontSize: 10, fontWeight: 700, color: isAct ? NAVY : MUTED }}>{i + 1}</span>
                      </div>
                    )}
                  </div>

                  {/* Content */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8, marginBottom: done ? 0 : 4 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                        <Icon size={13} strokeWidth={1.5} style={{ color: done ? EMERALD : isAct ? NAVY : MUTED, flexShrink: 0 }} />
                        <span style={{ fontSize: 14, fontWeight: 600, color: done ? "#475569" : TEXT, letterSpacing: "-0.01em" }}>
                          {step.title}
                        </span>
                        {done && (
                          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: EMERALD }}>
                            Done
                          </span>
                        )}
                      </div>
                      {!done && (
                        <span style={{ fontSize: 11, color: MUTED, flexShrink: 0, fontFamily: "monospace" }}>
                          {step.time}
                        </span>
                      )}
                    </div>

                    {!done && (
                      <p style={{ fontSize: 13, color: TEXT2, margin: "6px 0 0", lineHeight: 1.6 }}>
                        {step.desc}
                      </p>
                    )}

                    {/* Inline: ORCID (step 0) */}
                    {!done && i === 0 && (
                      <div
                        style={{
                          marginTop: 14,
                          overflow: "hidden",
                          maxHeight: activeInline === 0 ? 160 : 0,
                          transition: "max-height 0.25s ease",
                        }}
                      >
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                          <input
                            type="text"
                            value={orcidValue}
                            onChange={(e) => setOrcidValue(e.target.value)}
                            placeholder="0000-0000-0000-0000"
                            aria-label="ORCID iD"
                            style={{
                              flex: 1,
                              minWidth: 180,
                              border: `1px solid ${BRD}`,
                              padding: "7px 10px",
                              fontSize: 13,
                              color: TEXT,
                              outline: "none",
                              fontFamily: "monospace",
                              background: WHITE,
                            }}
                            onKeyDown={(e) => e.key === "Enter" && saveOrcid()}
                          />
                          <button
                            onClick={saveOrcid}
                            disabled={orcidSaving || !orcidValue.trim()}
                            style={{
                              background: NAVY,
                              color: "white",
                              border: "none",
                              padding: "7px 16px",
                              fontSize: 12,
                              fontWeight: 600,
                              cursor: orcidSaving || !orcidValue.trim() ? "not-allowed" : "pointer",
                              opacity: orcidSaving || !orcidValue.trim() ? 0.55 : 1,
                              transition: "opacity 0.15s",
                            }}
                          >
                            {orcidSaving ? "Saving…" : "Save"}
                          </button>
                          <button
                            onClick={skipOrcid}
                            style={{ background: "transparent", border: `1px solid ${BRD}`, padding: "7px 12px", fontSize: 12, color: TEXT2, cursor: "pointer" }}
                          >
                            Skip
                          </button>
                        </div>
                        <p style={{ fontSize: 11, color: MUTED, margin: "8px 0 0", lineHeight: 1.5 }}>
                          Find your ORCID iD at{" "}
                          <a href="https://orcid.org" target="_blank" rel="noopener noreferrer" style={{ color: NAVY, textDecoration: "none", borderBottom: "1px solid " + BRD }}>orcid.org</a>.
                          You can also link it later in Settings.
                        </p>
                      </div>
                    )}

                    {/* Inline: Research Interests (step 2) */}
                    {!done && i === 2 && (
                      <div
                        style={{
                          marginTop: 14,
                          overflow: "hidden",
                          maxHeight: activeInline === 2 ? 340 : 0,
                          transition: "max-height 0.25s ease",
                        }}
                      >
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
                          {RESEARCH_DOMAINS.map((d) => {
                            const on = selected.has(d);
                            return (
                              <button
                                key={d}
                                onClick={() => toggleDomain(d)}
                                style={{
                                  fontSize: 12,
                                  padding: "5px 11px",
                                  border: `1px solid ${on ? NAVY : BRD}`,
                                  background: on ? NAVY : WHITE,
                                  color: on ? "white" : TEXT2,
                                  cursor: "pointer",
                                  transition: "background 0.15s, border-color 0.15s, color 0.15s",
                                }}
                                aria-pressed={on}
                              >
                                {d}
                              </button>
                            );
                          })}
                        </div>
                        <div style={{ display: "flex", gap: 8 }}>
                          <button
                            onClick={saveAreas}
                            disabled={areasSaving || selected.size === 0}
                            style={{
                              background: NAVY,
                              color: "white",
                              border: "none",
                              padding: "7px 16px",
                              fontSize: 12,
                              fontWeight: 600,
                              cursor: areasSaving || selected.size === 0 ? "not-allowed" : "pointer",
                              opacity: areasSaving || selected.size === 0 ? 0.55 : 1,
                              transition: "opacity 0.15s",
                            }}
                          >
                            {areasSaving ? "Saving…" : `Save (${selected.size} selected)`}
                          </button>
                          <button
                            onClick={skipAreas}
                            style={{ background: "transparent", border: `1px solid ${BRD}`, padding: "7px 12px", fontSize: 12, color: TEXT2, cursor: "pointer" }}
                          >
                            Skip
                          </button>
                        </div>
                      </div>
                    )}

                    {/* CTAs for non-done steps */}
                    {!done && (
                      <div style={{ marginTop: 14, display: "flex", gap: 8, flexWrap: "wrap" }}>
                        {/* Step 0: inline toggle */}
                        {i === 0 && activeInline !== 0 && (
                          <button
                            onClick={() => setActiveInline(0)}
                            style={primaryBtn}
                            aria-expanded={activeInline === 0}
                          >
                            Enter ORCID iD
                            <ChevronRight size={12} strokeWidth={2} />
                          </button>
                        )}
                        {i === 0 && activeInline === 0 && (
                          <button
                            onClick={() => setActiveInline(null)}
                            style={ghostBtn}
                          >
                            <X size={11} strokeWidth={1.5} /> Close
                          </button>
                        )}

                        {/* Step 2: inline toggle */}
                        {i === 2 && activeInline !== 2 && (
                          <button
                            onClick={() => setActiveInline(2)}
                            style={primaryBtn}
                            aria-expanded={activeInline === 2}
                          >
                            Select domains
                            <ChevronRight size={12} strokeWidth={2} />
                          </button>
                        )}
                        {i === 2 && activeInline === 2 && (
                          <button
                            onClick={() => setActiveInline(null)}
                            style={ghostBtn}
                          >
                            <X size={11} strokeWidth={1.5} /> Close
                          </button>
                        )}

                        {/* Steps 1, 3, 4: navigate */}
                        {step.to && (
                          <button
                            onClick={() => handleNavStep(i, step.to)}
                            style={primaryBtn}
                          >
                            {i === 1 ? "Go to Publications" : i === 3 ? "Create Workspace" : "Generate Digital Twin"}
                            <ArrowRight size={12} strokeWidth={2} />
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* ── Skip all ──────────────────────────────────────────────────── */}
        {!isComplete && (
          <div style={{ marginTop: 32, textAlign: "center" }}>
            <button
              onClick={skipAll}
              style={{
                background: "transparent",
                border: "none",
                fontSize: 12,
                color: MUTED,
                cursor: "pointer",
                textDecoration: "underline",
                textDecorationStyle: "dotted",
                textUnderlineOffset: 3,
              }}
            >
              Skip setup and explore the platform
            </button>
          </div>
        )}

      </div>
    </div>
  );
}

// ─── Style helpers ────────────────────────────────────────────────────────────

const primaryBtn = {
  display: "inline-flex",
  alignItems: "center",
  gap: 5,
  background: NAVY,
  color: "white",
  border: "none",
  padding: "7px 14px",
  fontSize: 12,
  fontWeight: 600,
  cursor: "pointer",
  letterSpacing: "-0.01em",
  transition: "opacity 0.15s",
};

const ghostBtn = {
  display: "inline-flex",
  alignItems: "center",
  gap: 5,
  background: "transparent",
  color: "#64748B",
  border: `1px solid ${BRDX || "#E4E8EF"}`,
  padding: "6px 12px",
  fontSize: 12,
  cursor: "pointer",
  transition: "border-color 0.15s, color 0.15s",
};
