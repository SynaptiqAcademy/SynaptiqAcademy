import React, { useState } from "react";
import { Settings as SettingsIcon, Search, Clock } from "lucide-react";
import { SettingsGrid } from "./SettingsGrid";
import { PreferenceCard } from "./PreferenceCard";
import { PreferenceRow } from "./PreferenceRow";
import { Button } from "@/components/ds/Button";
import { List, ListItem } from "@/components/ds/List";
import { Caption, Meta } from "@/components/ds/Typography";

const LANDING_OPTIONS = [
  { value: "discover", label: "Home" },
  { value: "notifications", label: "Inbox" },
  { value: "today", label: "Today" },
  { value: "last_visited", label: "Last visited page" },
];

const RESULTS_PER_PAGE_OPTIONS = [
  { value: 10, label: "10" },
  { value: 20, label: "20" },
  { value: 50, label: "50" },
  { value: 100, label: "100" },
];

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

export function GeneralSection({ prefs, setPref, recentChanges = [] }) {
  const [expanded, setExpanded] = useState(false);
  const visibleChanges = expanded ? recentChanges : recentChanges.slice(0, 5);

  return (
    <SettingsGrid>
      <PreferenceCard
        icon={SettingsIcon}
        title="Application Preferences"
        description="Control the general behaviour of Synaptiq when you start and navigate the platform."
      >
        <PreferenceRow
          label="Default landing page"
          hint="Where you land after signing in"
          control="select"
          value={prefs.defaultLandingPage}
          options={LANDING_OPTIONS}
          onChange={(v) => setPref("defaultLandingPage", v, "Default Landing Page")}
        />
        <PreferenceRow
          label="Default dashboard view"
          hint="The view shown on your dashboard"
          control="select"
          value={prefs.defaultDashboardView}
          options={[
            { value: "home", label: "Home" },
            { value: "today", label: "Today" },
          ]}
          onChange={(v) => setPref("defaultDashboardView", v, "Default Dashboard View")}
        />
        <PreferenceRow
          label="Startup behaviour"
          hint="What happens when you open Synaptiq"
          control="select"
          value={prefs.startupBehavior}
          options={[
            { value: "continue", label: "Continue where I left off" },
            { value: "always_home", label: "Always show Home" },
          ]}
          onChange={(v) => setPref("startupBehavior", v, "Startup Behaviour")}
        />
        <PreferenceRow
          label="Show recent activity"
          hint="Display recent activity on Home"
          value={prefs.showRecentActivity}
          onChange={(v) => setPref("showRecentActivity", v, "Show Recent Activity")}
        />
      </PreferenceCard>

      <PreferenceCard
        icon={Search}
        title="Search Preferences"
        description="Customize how search works across Synaptiq."
      >
        <PreferenceRow
          label="Search results per page"
          hint="Number of results displayed"
          control="select"
          value={prefs.searchResultsPerPage}
          options={RESULTS_PER_PAGE_OPTIONS}
          onChange={(v) => setPref("searchResultsPerPage", Number(v), "Search Results Per Page")}
        />
        <PreferenceRow
          label="Include archived items"
          hint="Show archived projects, manuscripts and workspaces"
          caption="Applied as search surfaces adopt this preference"
          value={prefs.searchIncludeArchived}
          onChange={(v) => setPref("searchIncludeArchived", v, "Include Archived Items")}
        />
        <PreferenceRow
          label="Search suggestions"
          hint="Show AI powered search suggestions"
          caption="Applied as search surfaces adopt this preference"
          value={prefs.searchSuggestions}
          onChange={(v) => setPref("searchSuggestions", v, "Search Suggestions")}
        />
        <PreferenceRow
          label="Highlight matches"
          hint="Highlight search terms in results"
          caption="Applied as search surfaces adopt this preference"
          value={prefs.highlightMatches}
          onChange={(v) => setPref("highlightMatches", v, "Highlight Matches")}
        />
      </PreferenceCard>

      <PreferenceCard
        icon={Clock}
        title="Recent Changes"
        description="A log of your latest settings updates."
      >
        {recentChanges.length === 0 ? (
          <Caption>No changes yet this session.</Caption>
        ) : (
          <>
            <List border={false} radius={0} style={{ background: "transparent" }}>
              {visibleChanges.map((c) => (
                <ListItem
                  key={c.key + c.at}
                  compact
                  title={c.label}
                  trailing={<Meta style={{ flexShrink: 0 }}>{timeAgo(c.at)}</Meta>}
                  style={{ padding: "6px 0" }}
                />
              ))}
            </List>
            {recentChanges.length > 5 && (
              <Button
                variant="link"
                size="sm"
                onClick={() => setExpanded((e) => !e)}
                style={{ marginTop: 2, alignSelf: "flex-start" }}
              >
                {expanded ? "Show less" : "View all changes →"}
              </Button>
            )}
          </>
        )}
      </PreferenceCard>
    </SettingsGrid>
  );
}

export default GeneralSection;
