import React from "react";
import { BookMarked, Save, SpellCheck, Users } from "lucide-react";
import { SettingsGrid } from "./SettingsGrid";
import { PreferenceCard } from "./PreferenceCard";
import { PreferenceRow } from "./PreferenceRow";

const NO_EDITOR_CAPTION = "Applied once Synaptiq's manuscript editor adopts this setting";

export function EditorSection({ prefs, setPref }) {
  return (
    <SettingsGrid>
      <PreferenceCard icon={BookMarked} title="Markdown & Citations">
        <PreferenceRow
          label="Markdown Toolbar"
          hint="Show formatting toolbar in markdown fields"
          value={prefs.markdownToolbar}
          onChange={(v) => setPref("markdownToolbar", v, "Markdown Toolbar")}
        />
        <PreferenceRow
          label="Citation Style"
          control="select"
          value={prefs.citationStyle}
          options={[{ value: "apa", label: "APA" }, { value: "mla", label: "MLA" }, { value: "chicago", label: "Chicago" }, { value: "ieee", label: "IEEE" }, { value: "vancouver", label: "Vancouver" }]}
          onChange={(v) => setPref("citationStyle", v, "Citation Style")}
          caption={NO_EDITOR_CAPTION}
        />
        <PreferenceRow
          label="Reference Manager"
          control="select"
          value={prefs.referenceManager}
          options={[{ value: "none", label: "None" }, { value: "zotero", label: "Zotero" }, { value: "mendeley", label: "Mendeley" }, { value: "endnote", label: "EndNote" }]}
          onChange={(v) => setPref("referenceManager", v, "Reference Manager")}
          caption="No reference-manager integration exists yet — this stores your preference for when one ships"
        />
      </PreferenceCard>

      <PreferenceCard icon={Save} title="Autosave">
        <PreferenceRow
          label="Autosave Interval"
          control="select"
          value={String(prefs.autosaveInterval)}
          options={[{ value: "30", label: "Every 30 seconds" }, { value: "60", label: "Every minute" }, { value: "300", label: "Every 5 minutes" }]}
          onChange={(v) => setPref("autosaveInterval", Number(v), "Autosave Interval")}
        />
      </PreferenceCard>

      <PreferenceCard icon={SpellCheck} title="Proofing">
        <PreferenceRow label="Spell Checking" value={prefs.spellChecking} onChange={(v) => setPref("spellChecking", v, "Spell Checking")} caption={NO_EDITOR_CAPTION} />
        <PreferenceRow label="Grammar Checking" value={prefs.grammarChecking} onChange={(v) => setPref("grammarChecking", v, "Grammar Checking")} caption={NO_EDITOR_CAPTION} />
      </PreferenceCard>

      <PreferenceCard icon={Users} title="Collaboration">
        <PreferenceRow label="Track Changes" value={prefs.trackChanges} onChange={(v) => setPref("trackChanges", v, "Track Changes")} caption={NO_EDITOR_CAPTION} />
        <PreferenceRow
          label="Comment Behaviour"
          control="select"
          value={prefs.commentBehavior}
          options={[{ value: "inline", label: "Inline" }, { value: "sidebar", label: "Sidebar" }]}
          onChange={(v) => setPref("commentBehavior", v, "Comment Behaviour")}
          caption={NO_EDITOR_CAPTION}
        />
      </PreferenceCard>
    </SettingsGrid>
  );
}

export default EditorSection;
