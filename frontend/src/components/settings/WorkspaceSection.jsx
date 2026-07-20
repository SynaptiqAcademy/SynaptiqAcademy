import React, { useEffect, useState } from "react";
import { Layers, Microscope, CalendarDays, Archive } from "lucide-react";
import { SettingsGrid } from "./SettingsGrid";
import { PreferenceCard } from "./PreferenceCard";
import { PreferenceRow } from "./PreferenceRow";
import { useAuth } from "@/contexts/AuthContext";
import api from "@/lib/api";

const MEETING_TYPES = [
  "Research Meeting", "PhD Supervision", "Project Meeting", "Grant Meeting",
  "Peer Review Meeting", "Institution Meeting", "Conference Preparation",
  "Journal Submission Meeting",
];

export function WorkspaceSection({ prefs, setPref }) {
  const { user } = useAuth();
  const [workspaces, setWorkspaces] = useState([]);
  const [projects, setProjects] = useState([]);

  useEffect(() => {
    api.get("/workspaces").then((r) => setWorkspaces(r.data || [])).catch(() => {});
    api.get("/projects").then((r) => setProjects(r.data || [])).catch(() => {});
  }, []);

  const researchAreas = user?.research_areas || [];

  return (
    <SettingsGrid>
      <PreferenceCard icon={Layers} title="Default Workspace & Project" description="Pre-selected when you create new items">
        <PreferenceRow
          label="Default Workspace"
          control="select"
          value={prefs.defaultWorkspaceId}
          options={[{ value: "", label: "None" }, ...workspaces.map((w) => ({ value: w.id, label: w.name }))]}
          onChange={(v) => setPref("defaultWorkspaceId", v, "Default Workspace")}
        />
        <PreferenceRow
          label="Default Project"
          control="select"
          value={prefs.defaultProjectId}
          options={[{ value: "", label: "None" }, ...projects.map((p) => ({ value: p.id, label: p.title || p.name }))]}
          onChange={(v) => setPref("defaultProjectId", v, "Default Project")}
        />
      </PreferenceCard>

      <PreferenceCard icon={Microscope} title="Default Research Area" description="From your Academic Passport research areas">
        <PreferenceRow
          label="Research Area"
          control="select"
          value={prefs.defaultResearchArea}
          options={[{ value: "", label: "None" }, ...researchAreas.map((a) => ({ value: a, label: a }))]}
          onChange={(v) => setPref("defaultResearchArea", v, "Default Research Area")}
          hint={researchAreas.length === 0 ? "Add research areas in Academic Passport to populate this" : undefined}
        />
      </PreferenceCard>

      <PreferenceCard icon={CalendarDays} title="Meeting Defaults">
        <PreferenceRow
          label="Default Meeting Type"
          control="select"
          value={prefs.defaultMeetingType}
          options={MEETING_TYPES.map((t) => ({ value: t, label: t }))}
          onChange={(v) => setPref("defaultMeetingType", v, "Default Meeting Type")}
        />
        <PreferenceRow
          label="Default Reminder"
          control="select"
          value={String(prefs.defaultMeetingReminder)}
          options={[5, 10, 15, 30, 60].map((m) => ({ value: String(m), label: `${m} minutes before` }))}
          onChange={(v) => setPref("defaultMeetingReminder", Number(v), "Default Meeting Reminder")}
        />
      </PreferenceCard>

      <PreferenceCard icon={Archive} title="Document & Repository Defaults" description="Visibility applied when you don't choose one explicitly">
        <PreferenceRow
          label="Document Visibility"
          control="select"
          value={prefs.defaultDocumentVisibility}
          options={[{ value: "private", label: "Private" }, { value: "public", label: "Public" }]}
          onChange={(v) => setPref("defaultDocumentVisibility", v, "Document Visibility")}
        />
        <PreferenceRow
          label="Repository Visibility"
          control="select"
          value={prefs.defaultRepositoryVisibility}
          options={[{ value: "private", label: "Private" }, { value: "public", label: "Public" }]}
          onChange={(v) => setPref("defaultRepositoryVisibility", v, "Repository Visibility")}
        />
      </PreferenceCard>
    </SettingsGrid>
  );
}

export default WorkspaceSection;
