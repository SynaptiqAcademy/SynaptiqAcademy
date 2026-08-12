/**
 * Synaptiq Layout Primitives — Central Export
 *
 * Every page must use exactly one layout from this module.
 * Pages provide content into named slots; they MUST NOT override structure.
 *
 * ResearchLayout is the single canonical layout for every page under
 * Academic Network, Research, Teaching, Publishing, Funding, and AI
 * Workspace — those 6 sections render an identical shell (same aside
 * width/side, same hero treatment). AIWorkspaceLayout and DiscoveryLayout
 * were retired into it (pass `navItems` for the old AIWorkspaceLayout
 * auto-nav behavior).
 *
 * Usage:
 *   import { ResearchLayout } from "@/layouts";
 */

export { ResearchLayout }       from "./ResearchLayout";
export { DashboardLayout }      from "./DashboardLayout";
export { AnalyticsLayout }      from "./AnalyticsLayout";
export { AdministrationLayout } from "./AdministrationLayout";
export { SettingsLayout }       from "./SettingsLayout";
export { ProfileLayout }        from "./ProfileLayout";
export { InstitutionLayout }    from "./InstitutionLayout";
export { WorkspaceLayout }      from "./WorkspaceLayout";
export { ArtifactLayout }       from "./ArtifactLayout";
