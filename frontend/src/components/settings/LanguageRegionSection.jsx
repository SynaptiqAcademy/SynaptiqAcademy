import React from "react";
import { Globe2, CalendarClock, Clock, Hash } from "lucide-react";
import { SettingsGrid } from "./SettingsGrid";
import { PreferenceCard } from "./PreferenceCard";
import { PreferenceRow } from "./PreferenceRow";
import { TEXT_MUTED } from "@/lib/tokens";

function formatPreviewDate(dateFormat) {
  const now = new Date();
  const d = String(now.getDate()).padStart(2, "0");
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const y = now.getFullYear();
  if (dateFormat === "MM/DD/YYYY") return `${m}/${d}/${y}`;
  if (dateFormat === "YYYY-MM-DD") return `${y}-${m}-${d}`;
  return `${d}/${m}/${y}`;
}

function formatPreviewTime(timeFormat) {
  const now = new Date();
  return timeFormat === "12h"
    ? now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true })
    : now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
}

function Preview({ children }) {
  return <div style={{ fontSize: 11, color: TEXT_MUTED, fontFamily: "monospace" }}>Preview: {children}</div>;
}

export function LanguageRegionSection({ prefs, setPref }) {
  return (
    <SettingsGrid>
      <PreferenceCard icon={Globe2} title="Language" description="Interface translation is on our roadmap">
        <PreferenceRow
          label="Language"
          control="select"
          value={prefs.language}
          options={[
            { value: "en", label: "English" },
            { value: "es", label: "Español" },
            { value: "fr", label: "Français" },
            { value: "de", label: "Deutsch" },
            { value: "pt", label: "Português" },
          ]}
          onChange={(v) => setPref("language", v, "Language")}
          caption={prefs.language !== "en" ? "UI translation coming soon — English shown for now" : undefined}
        />
      </PreferenceCard>

      <PreferenceCard icon={CalendarClock} title="Date & Time Format">
        <PreferenceRow
          label="Date Format"
          control="select"
          value={prefs.dateFormat}
          options={[
            { value: "DD/MM/YYYY", label: "DD/MM/YYYY" },
            { value: "MM/DD/YYYY", label: "MM/DD/YYYY" },
            { value: "YYYY-MM-DD", label: "YYYY-MM-DD" },
          ]}
          onChange={(v) => setPref("dateFormat", v, "Date Format")}
        />
        <Preview>{formatPreviewDate(prefs.dateFormat)}</Preview>
        <PreferenceRow
          label="Time Format"
          control="select"
          value={prefs.timeFormat}
          options={[{ value: "24h", label: "24-hour" }, { value: "12h", label: "12-hour" }]}
          onChange={(v) => setPref("timeFormat", v, "Time Format")}
        />
        <Preview>{formatPreviewTime(prefs.timeFormat)}</Preview>
      </PreferenceCard>

      <PreferenceCard icon={Clock} title="Timezone">
        <PreferenceRow
          label="Timezone"
          hint={prefs.timezone}
          control="select"
          value={prefs.timezone}
          options={Intl.supportedValuesOf ? Intl.supportedValuesOf("timeZone").slice(0, 300).map((tz) => ({ value: tz, label: tz })) : [{ value: prefs.timezone, label: prefs.timezone }]}
          onChange={(v) => setPref("timezone", v, "Timezone")}
        />
      </PreferenceCard>

      <PreferenceCard icon={Hash} title="Regional Format">
        <PreferenceRow
          label="Week Start Day"
          control="select"
          value={prefs.weekStartDay}
          options={[{ value: "sunday", label: "Sunday" }, { value: "monday", label: "Monday" }]}
          onChange={(v) => setPref("weekStartDay", v, "Week Start Day")}
        />
        <PreferenceRow
          label="Number Format"
          control="select"
          value={prefs.numberFormat}
          options={[{ value: "1,234.56", label: "1,234.56" }, { value: "1.234,56", label: "1.234,56" }, { value: "1 234,56", label: "1 234,56" }]}
          onChange={(v) => setPref("numberFormat", v, "Number Format")}
        />
      </PreferenceCard>
    </SettingsGrid>
  );
}

export default LanguageRegionSection;
