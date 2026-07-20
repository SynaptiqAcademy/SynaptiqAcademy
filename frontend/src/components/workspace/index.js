/**
 * Synaptiq Workspace Layout System
 *
 * Import from this module in every top-level page.
 * No page may define its own layout — use these components instead.
 *
 * Usage:
 *   import {
 *     WorkspaceLayout,
 *     PageSummary,
 *     PageToolbar,
 *     PageSection,
 *     PageSidebar, SidebarCard,
 *     AIAssistant,
 *     EmptyState,
 *     WorkspaceSkeleton,
 *   } from "@/components/workspace";
 *
 * Visual rhythm enforced by WorkspaceLayout:
 *   1. PageHeader   — title · subtitle · actions
 *   2. PageSummary  — one contextual card
 *   3. PageToolbar  — filter · search · view controls
 *   4. Content grid — PageContent (flex-1) + PageSidebar (288px)
 *   5. PageFooter   — 40px bottom spacing
 */

// ── Structural slots ───────────────────────────────────────────────────────
export { PageHeader }                             from "./PageHeader";
export { PageSummary, StatPill }                  from "./PageSummary";
export { PageToolbar, SearchInput, ViewToggle,
         FilterButton, SortSelect, TabFilter }    from "./PageToolbar";
export { PageContent }                            from "./PageContent";
export { PageSidebar, SidebarCard,
         SidebarDivider }                         from "./PageSidebar";
export { PageSection }                            from "./PageSection";
export { PageFooter }                             from "./PageFooter";

// ── Utility components ─────────────────────────────────────────────────────
export { AIAssistant }                            from "./AIAssistant";
export { EmptyState }                             from "./EmptyState";
export { WorkspaceSkeleton, Skeleton,
         SkeletonText, SkeletonCard }             from "./Skeleton";
