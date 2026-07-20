import React, { useMemo, useState } from "react";
import {
  SlidersHorizontal, Palette, Globe2, Sparkles, Layers, PenTool,
  Keyboard, Accessibility, FlaskConical, Search, X, ShieldCheck, CloudCog,
} from "lucide-react";
import { Card } from "@/components/ds/Card";
import { NAVY, BRD, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY, WHITE } from "@/lib/tokens";

export const CATEGORIES = [
  { id: "general", label: "General", icon: SlidersHorizontal },
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "languageRegion", label: "Language & Region", icon: Globe2 },
  { id: "ai", label: "AI Preferences", icon: Sparkles },
  { id: "workspace", label: "Workspace", icon: Layers },
  { id: "editor", label: "Editor", icon: PenTool },
  { id: "keyboard", label: "Keyboard Shortcuts", icon: Keyboard },
  { id: "accessibility", label: "Accessibility", icon: Accessibility },
  { id: "labs", label: "Labs", icon: FlaskConical },
  { id: "privacy", label: "Privacy", icon: ShieldCheck },
];

// Flat searchable index — mirrors the real preference labels rendered in
// each category so instant search actually finds what's on the page.
const SEARCH_INDEX = [
  { label: "Default Landing Page", categoryId: "general" },
  { label: "Startup Behaviour", categoryId: "general" },
  { label: "Default Dashboard View", categoryId: "general" },
  { label: "Show Recent Activity", categoryId: "general" },
  { label: "Search Results Per Page", categoryId: "general" },
  { label: "Include Archived Items", categoryId: "general" },
  { label: "Search Suggestions", categoryId: "general" },
  { label: "Highlight Matches", categoryId: "general" },
  { label: "Theme", categoryId: "appearance" },
  { label: "Accent Color", categoryId: "appearance" },
  { label: "Density / Compact Mode", categoryId: "appearance" },
  { label: "Sidebar Behaviour", categoryId: "appearance" },
  { label: "Animations", categoryId: "appearance" },
  { label: "Reduced Motion", categoryId: "appearance" },
  { label: "Card Style", categoryId: "appearance" },
  { label: "Font Size", categoryId: "appearance" },
  { label: "Language", categoryId: "languageRegion" },
  { label: "Date Format", categoryId: "languageRegion" },
  { label: "Time Format", categoryId: "languageRegion" },
  { label: "Timezone", categoryId: "languageRegion" },
  { label: "Week Start Day", categoryId: "languageRegion" },
  { label: "Number Format", categoryId: "languageRegion" },
  { label: "Preferred AI Provider", categoryId: "ai" },
  { label: "Preferred AI Model", categoryId: "ai" },
  { label: "Default Writing Style", categoryId: "ai" },
  { label: "Default Citation Style", categoryId: "ai" },
  { label: "Academic Tone", categoryId: "ai" },
  { label: "Auto Summaries", categoryId: "ai" },
  { label: "Auto Suggestions", categoryId: "ai" },
  { label: "Auto Save", categoryId: "ai" },
  { label: "Streaming Responses", categoryId: "ai" },
  { label: "Smart Context", categoryId: "ai" },
  { label: "AI Memory", categoryId: "ai" },
  { label: "Default Workspace", categoryId: "workspace" },
  { label: "Default Project", categoryId: "workspace" },
  { label: "Default Research Area", categoryId: "workspace" },
  { label: "Meeting Defaults", categoryId: "workspace" },
  { label: "Document Visibility", categoryId: "workspace" },
  { label: "Repository Visibility", categoryId: "workspace" },
  { label: "Markdown Toolbar", categoryId: "editor" },
  { label: "Citation Style", categoryId: "editor" },
  { label: "Reference Manager", categoryId: "editor" },
  { label: "Autosave Interval", categoryId: "editor" },
  { label: "Spell Checking", categoryId: "editor" },
  { label: "Grammar Checking", categoryId: "editor" },
  { label: "Track Changes", categoryId: "editor" },
  { label: "Comment Behaviour", categoryId: "editor" },
  { label: "Navigation Shortcuts", categoryId: "keyboard" },
  { label: "Command Palette", categoryId: "keyboard" },
  { label: "Quick Actions", categoryId: "keyboard" },
  { label: "High Contrast", categoryId: "accessibility" },
  { label: "Focus Indicators", categoryId: "accessibility" },
  { label: "Large Cursor", categoryId: "accessibility" },
  { label: "Keyboard Navigation", categoryId: "accessibility" },
  { label: "Screen Reader Mode", categoryId: "accessibility" },
  { label: "Experimental Features", categoryId: "labs" },
  { label: "Beta AI Features", categoryId: "labs" },
  { label: "Preview Components", categoryId: "labs" },
  { label: "Developer Options", categoryId: "labs" },
  { label: "Cookie Consent", categoryId: "privacy" },
  { label: "Manage Cookie Preferences", categoryId: "privacy" },
  { label: "Reset Cookie Preferences", categoryId: "privacy" },
];

function HighlightText({ text, query }) {
  if (!query) return <>{text}</>;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return <>{text}</>;
  return (
    <>
      {text.slice(0, idx)}
      <span style={{ color: NAVY, fontWeight: 700 }}>{text.slice(idx, idx + query.length)}</span>
      {text.slice(idx + query.length)}
    </>
  );
}

export function SettingsNav({ activeCategory, onSelect }) {
  const [query, setQuery] = useState("");

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return null;
    return SEARCH_INDEX.filter((i) => i.label.toLowerCase().includes(q));
  }, [query]);

  return (
    <div className="w-full lg:w-[200px] lg:sticky lg:top-6" style={{ flexShrink: 0, alignSelf: "flex-start" }}>
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: TEXT_MUTED, letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Settings
        </div>
        <div style={{ fontSize: 13, fontWeight: 600, color: TEXT_SECONDARY, marginTop: 2 }}>
          Application Preferences
        </div>
      </div>

      <div style={{ position: "relative", marginBottom: 14 }}>
        <Search size={13} style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)", color: TEXT_MUTED }} />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Escape") setQuery(""); }}
          placeholder="Search settings…"
          style={{ width: "100%", height: 32, padding: "0 40px 0 28px", border: `1px solid ${BRD}`, borderRadius: 6, fontSize: 12, outline: "none", boxSizing: "border-box" }}
        />
        {query ? (
          <button onClick={() => setQuery("")} aria-label="Clear search" style={{ position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)", background: "none", border: "none", cursor: "pointer", color: TEXT_MUTED, display: "flex" }}>
            <X size={12} />
          </button>
        ) : (
          <span style={{
            position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)",
            fontSize: 10, fontFamily: "monospace", color: TEXT_MUTED, border: `1px solid ${BRD}`,
            borderRadius: 4, padding: "1px 5px", pointerEvents: "none",
          }}>
            ⌘/
          </span>
        )}
      </div>

      {results !== null ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {results.length === 0 ? (
            <div style={{ fontSize: 12, color: TEXT_MUTED, padding: "8px 4px" }}>No matches for "{query}"</div>
          ) : (
            results.map((r) => {
              const cat = CATEGORIES.find((c) => c.id === r.categoryId);
              return (
                <button
                  key={r.label}
                  onClick={() => { onSelect(r.categoryId); setQuery(""); }}
                  style={{
                    display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 1, width: "100%",
                    padding: "7px 10px", border: "none", background: "transparent", cursor: "pointer", textAlign: "left", borderRadius: 6,
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#F8FAFC")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <span style={{ fontSize: 12.5, color: TEXT_PRIMARY }}><HighlightText text={r.label} query={query} /></span>
                  <span style={{ fontSize: 10, color: TEXT_MUTED }}>{cat?.label}</span>
                </button>
              );
            })
          )}
        </div>
      ) : (
        <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {CATEGORIES.map(({ id, label, icon: Icon }) => {
            const active = activeCategory === id;
            return (
              <button
                key={id}
                onClick={() => onSelect(id)}
                style={{
                  display: "flex", alignItems: "center", gap: 9, width: "100%", padding: "8px 10px",
                  border: "none", borderRadius: 7, cursor: "pointer", textAlign: "left",
                  background: active ? NAVY : "transparent",
                  color: active ? WHITE : TEXT_PRIMARY,
                  fontWeight: active ? 600 : 400,
                  transition: "background 100ms",
                }}
                onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = "#F8FAFC"; }}
                onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = "transparent"; }}
              >
                <Icon size={14} style={{ flexShrink: 0, color: active ? WHITE : TEXT_MUTED }} />
                <span style={{ fontSize: 12.5 }}>{label}</span>
              </button>
            );
          })}
        </nav>
      )}

      <Card padding="lg" style={{ marginTop: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 8 }}>
          <CloudCog size={14} style={{ color: NAVY }} />
          <div style={{ fontSize: 12.5, fontWeight: 700, color: TEXT_PRIMARY }}>Settings Sync</div>
        </div>
        <p style={{ fontSize: 12, color: TEXT_MUTED, lineHeight: 1.6, margin: 0 }}>
          Your preferences are saved securely in this browser.
        </p>
        <button
          onClick={() => onSelect("privacy")}
          style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12, fontWeight: 600, color: NAVY, background: "none", border: "none", padding: 0, marginTop: 10, cursor: "pointer" }}
        >
          Learn more →
        </button>
      </Card>
    </div>
  );
}

export default SettingsNav;
