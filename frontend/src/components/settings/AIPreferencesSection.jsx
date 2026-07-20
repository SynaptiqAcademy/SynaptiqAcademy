import React from "react";
import { Bot, PenTool, Zap, BrainCircuit } from "lucide-react";
import { SettingsGrid } from "./SettingsGrid";
import { PreferenceCard } from "./PreferenceCard";
import { PreferenceRow } from "./PreferenceRow";

const APPLIED_CAPTION = "Honored by Synaptiq AI features as they roll out";

export function AIPreferencesSection({ prefs, setPref }) {
  return (
    <SettingsGrid>
      <PreferenceCard icon={Bot} title="AI Provider & Model">
        <PreferenceRow
          label="Preferred AI Provider"
          control="select"
          value={prefs.aiProvider}
          options={[{ value: "anthropic", label: "Anthropic (Claude)" }, { value: "openai", label: "OpenAI" }, { value: "auto", label: "Best available" }]}
          onChange={(v) => setPref("aiProvider", v, "Preferred AI Provider")}
          caption={APPLIED_CAPTION}
        />
        <PreferenceRow
          label="Preferred AI Model"
          control="select"
          value={prefs.aiModel}
          options={[{ value: "fast", label: "Fast" }, { value: "balanced", label: "Balanced" }, { value: "advanced", label: "Most capable" }]}
          onChange={(v) => setPref("aiModel", v, "Preferred AI Model")}
          caption={APPLIED_CAPTION}
        />
      </PreferenceCard>

      <PreferenceCard icon={PenTool} title="Writing Defaults">
        <PreferenceRow
          label="Default Writing Style"
          control="select"
          value={prefs.defaultWritingStyle}
          options={[{ value: "academic", label: "Academic" }, { value: "concise", label: "Concise" }, { value: "narrative", label: "Narrative" }]}
          onChange={(v) => setPref("defaultWritingStyle", v, "Default Writing Style")}
        />
        <PreferenceRow
          label="Default Citation Style"
          control="select"
          value={prefs.defaultCitationStyle}
          options={[{ value: "apa", label: "APA" }, { value: "mla", label: "MLA" }, { value: "chicago", label: "Chicago" }, { value: "ieee", label: "IEEE" }, { value: "vancouver", label: "Vancouver" }]}
          onChange={(v) => setPref("defaultCitationStyle", v, "Default Citation Style")}
        />
        <PreferenceRow
          label="Academic Tone"
          control="select"
          value={prefs.academicTone}
          options={[{ value: "formal", label: "Formal" }, { value: "balanced", label: "Balanced" }, { value: "approachable", label: "Approachable" }]}
          onChange={(v) => setPref("academicTone", v, "Academic Tone")}
        />
      </PreferenceCard>

      <PreferenceCard icon={Zap} title="Automation">
        <PreferenceRow label="Auto Summaries" value={prefs.autoSummaries} onChange={(v) => setPref("autoSummaries", v, "Auto Summaries")} />
        <PreferenceRow label="Auto Suggestions" value={prefs.autoSuggestions} onChange={(v) => setPref("autoSuggestions", v, "Auto Suggestions")} />
        <PreferenceRow label="Auto Save" value={prefs.autoSave} onChange={(v) => setPref("autoSave", v, "Auto Save")} />
        <PreferenceRow label="Streaming Responses" value={prefs.streamingResponses} onChange={(v) => setPref("streamingResponses", v, "Streaming Responses")} />
      </PreferenceCard>

      <PreferenceCard icon={BrainCircuit} title="Context & Memory">
        <PreferenceRow
          label="Smart Context"
          hint="Let AI features use your active project/workspace as context"
          value={prefs.smartContext}
          onChange={(v) => setPref("smartContext", v, "Smart Context")}
        />
        <PreferenceRow
          label="AI Memory"
          hint="Allow AI features to remember preferences across sessions"
          value={prefs.aiMemory}
          onChange={(v) => setPref("aiMemory", v, "AI Memory")}
        />
      </PreferenceCard>
    </SettingsGrid>
  );
}

export default AIPreferencesSection;
