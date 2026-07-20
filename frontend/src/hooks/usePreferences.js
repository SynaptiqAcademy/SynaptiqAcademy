import { useCallback, useEffect, useState } from "react";
import { applyPreferenceEffects } from "@/lib/applyPreferenceEffects";

/**
 * usePreferences — client-only Application Preferences store.
 *
 * No backend endpoint exists for generic UI preferences (confirmed: PATCH
 * /users/me is strictly academic-profile data). Follows the same convention
 * already established in this codebase for client-only state (Sidebar.jsx's
 * sq_sidebar_collapsed / sq_expert_mode, Messages.jsx's "zero backend
 * surface" pattern): a single sq_-prefixed localStorage key, lazy useState
 * init, try/catch writes.
 */

const STORAGE_KEY = "sq_app_preferences";
const LOG_KEY = "sq_app_preferences_log";
const MAX_LOG = 8;

export const DEFAULT_PREFERENCES = {
  // General
  defaultLandingPage: "discover",       // discover | notifications | today | last_visited
  startupBehavior: "continue",          // continue | always_home
  defaultDashboardView: "home",         // home | today
  showRecentActivity: true,
  searchResultsPerPage: 20,
  searchIncludeArchived: false,
  searchSuggestions: true,
  highlightMatches: true,

  // Appearance
  theme: "light",                       // light | dark | system (dark/system not yet rendered)
  accentColor: "navy",                  // navy | emerald | amber | crimson (previewed within Settings only)
  density: "comfortable",               // comfortable | compact
  sidebarCollapsed: false,              // mirrors the real sq_sidebar_collapsed key
  animationsEnabled: true,
  reducedMotion: false,                 // real: toggles data-reduced-motion on <html>
  cardStyle: "bordered",                // bordered | elevated
  fontSize: "medium",                   // small | medium | large — real: sets root font-size

  // Language & Region
  language: "en",
  dateFormat: "DD/MM/YYYY",
  timeFormat: "24h",
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  weekStartDay: "monday",
  numberFormat: "1,234.56",

  // AI Preferences
  aiProvider: "anthropic",
  aiModel: "balanced",
  defaultWritingStyle: "academic",
  defaultCitationStyle: "apa",
  academicTone: "formal",
  autoSummaries: true,
  autoSuggestions: true,
  autoSave: true,
  streamingResponses: true,
  smartContext: true,
  aiMemory: true,

  // Workspace
  defaultWorkspaceId: "",
  defaultProjectId: "",
  defaultResearchArea: "",
  defaultMeetingType: "Research Meeting",
  defaultMeetingReminder: 15,
  defaultDocumentVisibility: "private",
  defaultRepositoryVisibility: "private",

  // Editor
  markdownToolbar: true,
  citationStyle: "apa",
  referenceManager: "none",             // none | zotero | mendeley | endnote
  autosaveInterval: 60,                 // seconds
  spellChecking: true,
  grammarChecking: true,
  trackChanges: false,
  commentBehavior: "inline",            // inline | sidebar

  // Keyboard
  gKeyShortcutsEnabled: true,

  // Accessibility
  highContrast: false,
  keyboardNavigation: true,
  screenReaderMode: false,
  largeCursor: false,
  focusIndicators: true,

  // Labs
  experimentalFeatures: false,
  betaAiFeatures: false,
  previewComponents: false,
  developerOptions: false,
};

const SECTION_KEYS = {
  general: ["defaultLandingPage", "startupBehavior", "defaultDashboardView", "showRecentActivity", "searchResultsPerPage", "searchIncludeArchived", "searchSuggestions", "highlightMatches"],
  appearance: ["theme", "accentColor", "density", "sidebarCollapsed", "animationsEnabled", "reducedMotion", "cardStyle", "fontSize"],
  languageRegion: ["language", "dateFormat", "timeFormat", "timezone", "weekStartDay", "numberFormat"],
  ai: ["aiProvider", "aiModel", "defaultWritingStyle", "defaultCitationStyle", "academicTone", "autoSummaries", "autoSuggestions", "autoSave", "streamingResponses", "smartContext", "aiMemory"],
  workspace: ["defaultWorkspaceId", "defaultProjectId", "defaultResearchArea", "defaultMeetingType", "defaultMeetingReminder", "defaultDocumentVisibility", "defaultRepositoryVisibility"],
  editor: ["markdownToolbar", "citationStyle", "referenceManager", "autosaveInterval", "spellChecking", "grammarChecking", "trackChanges", "commentBehavior"],
  keyboard: ["gKeyShortcutsEnabled"],
  accessibility: ["highContrast", "keyboardNavigation", "screenReaderMode", "largeCursor", "focusIndicators"],
  labs: ["experimentalFeatures", "betaAiFeatures", "previewComponents", "developerOptions"],
};

export function loadPrefs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? { ...DEFAULT_PREFERENCES, ...JSON.parse(raw) } : { ...DEFAULT_PREFERENCES };
  } catch {
    return { ...DEFAULT_PREFERENCES };
  }
}

function loadLog() {
  try {
    return JSON.parse(localStorage.getItem(LOG_KEY) || "[]");
  } catch {
    return [];
  }
}

function persist(prefs) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)); } catch {}
}

function persistLog(log) {
  try { localStorage.setItem(LOG_KEY, JSON.stringify(log)); } catch {}
}

export function usePreferences() {
  const [prefs, setPrefs] = useState(loadPrefs);
  const [recentChanges, setRecentChanges] = useState(loadLog);

  const setPref = useCallback((key, value, label) => {
    setPrefs((prev) => {
      const next = { ...prev, [key]: value };
      persist(next);
      return next;
    });
    setRecentChanges((prev) => {
      const entry = { key, label: label || key, at: new Date().toISOString() };
      const next = [entry, ...prev.filter((e) => e.key !== key)].slice(0, MAX_LOG);
      persistLog(next);
      return next;
    });
  }, []);

  const resetSection = useCallback((sectionId) => {
    const keys = SECTION_KEYS[sectionId] || [];
    setPrefs((prev) => {
      const next = { ...prev };
      keys.forEach((k) => { next[k] = DEFAULT_PREFERENCES[k]; });
      persist(next);
      return next;
    });
  }, []);

  const resetAll = useCallback(() => {
    setPrefs({ ...DEFAULT_PREFERENCES });
    persist({ ...DEFAULT_PREFERENCES });
    setRecentChanges([]);
    persistLog([]);
  }, []);

  // Apply the subset of preferences with a real DOM effect whenever they change.
  useEffect(() => {
    applyPreferenceEffects(prefs);
  }, [prefs.reducedMotion, prefs.focusIndicators, prefs.highContrast, prefs.fontSize]); // eslint-disable-line react-hooks/exhaustive-deps

  return { prefs, setPref, resetSection, resetAll, recentChanges };
}

export default usePreferences;
