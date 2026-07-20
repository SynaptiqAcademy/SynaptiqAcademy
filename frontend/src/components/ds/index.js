/**
 * Synaptiq Design System — Central Export
 *
 * This is the ONE component library for the product. Every page imports
 * from here — no page builds its own badge, stat tile, table, or modal.
 * Tokens (color/spacing/radius/shadow/motion/icon scale) live in
 * `@/lib/tokens` and `src/index.css`'s `:root` custom properties — those
 * two files are the single source of truth this library is built on.
 *
 *   import { Button, Card, Badge, StatCard, ContextPanel } from "@/components/ds";
 *
 * Toast notifications are the one exception to "import from here": use
 * `import { toast } from "sonner"` directly (mounted once in App.js).
 *
 * Categories:
 *   Primitives         Button, Card, Badge, Avatar, AvatarGroup, Tag, TagGroup, Skeleton
 *   Layout             PageLayout, Section, Grid
 *   Typography         Display, H1-H4, Body*, Caption, Label, Meta, Text
 *   Forms              Input, Textarea, FormSelect, FormField, FormGroup, FormRow,
 *                      Checkbox, Radio, Switch, RadioGroup, CheckboxGroup
 *   Feedback           Alert, Banner, Callout, InlineError, Tooltip, ProgressBar, ProgressRing
 *   Navigation         NavTabs, Breadcrumb, Dropdown
 *   Data display       DataTable, Pagination, StatCard, StatGrid
 *   Lists              List, ListItem, ListSeparator, ListHeader, ListFooter
 *   Notifications      NotificationItem
 *   Search & filters   SearchBar, FilterBar, FilterChip
 *   States             EmptyState, ErrorState, Skeleton*, Spinner, LoadingOverlay
 *   Overlays           Modal, Dialog, Drawer
 *   Charts             Sparkline, SparkArea, MiniBar, BarChart, DonutChart, LineChart, ChartLegend
 *   Cards              WorkspaceCard, ResearchCard, PublicationCard, PersonCard,
 *                      Timeline, TimelineItem, StatusDot
 *                      GrantCard, ConferenceCard, JournalCard, ResearcherCard, InstitutionCard
 *   AI                 AIResponsePanel, EvidencePanel, EvidenceItem, CitationInline, VerificationBadge
 *   Operating-system   ContextPanel, SmartActionsBar, RelatedEntityPanel (entity-detail pages)
 */

// ── Primitives ────────────────────────────────────────────────────────────────
export { Button }                          from "./Button";
export { Card }                            from "./Card";
export { Badge }                           from "./Badge";
export { Input }                           from "./Input";
export { Textarea }                        from "./Textarea";
export { FormSelect }                      from "./FormSelect";
export { Skeleton }                        from "./Skeleton";
export { Avatar }                          from "./Avatar";
export { AvatarGroup }                     from "./AvatarGroup";
export { Tag, TagGroup }                   from "./Tag";

// ── Universal layout ──────────────────────────────────────────────────────────
export { PageLayout }                      from "./PageLayout";
export { Section }                         from "./Section";
export { Grid }                            from "./Grid";

// ── Typography scale ──────────────────────────────────────────────────────────
export {
  Display, H1, H2, H3, H4,
  SectionLabel as TypeSectionLabel,
  BodyLarge, Body, BodySmall,
  Caption, Label, Meta,
  Text,
}                                          from "./Typography";

// ── Separators ────────────────────────────────────────────────────────────────
export { Separator, SectionDivider }       from "./Separator";

// ── Forms ─────────────────────────────────────────────────────────────────────
export {
  FormField,
  FormGroup,
  FormRow,
  Checkbox,
  Radio,
  Switch,
  RadioGroup,
  CheckboxGroup,
}                                          from "./Form";

// ── Feedback: Alert ───────────────────────────────────────────────────────────
export { Alert, Banner, Callout, InlineError } from "./Alert";

// ── Feedback: Toast ───────────────────────────────────────────────────────────
// Toast notifications are handled by `sonner` (mounted once in App.js as
// <Toaster/>) — import { toast } from "sonner" directly. There is
// deliberately no ds/ toast component: a second, unmounted toast system
// used to live here and was pure dead code (nothing ever wraps children in
// a provider for it), so it has been removed rather than kept as a trap.

// ── Feedback: Tooltip ─────────────────────────────────────────────────────────
export { Tooltip }                         from "./Tooltip";

// ── Feedback: Progress ────────────────────────────────────────────────────────
export { ProgressBar, ProgressRing }       from "./Progress";

// ── Feedback: Toggle (legacy) ─────────────────────────────────────────────────
export { Toggle }                          from "./Toggle";

// ── Navigation ────────────────────────────────────────────────────────────────
export { NavTabs }                         from "./NavTabs";
export { Breadcrumb }                      from "./Breadcrumb";
export { Dropdown, DropdownItem, DropdownSeparator, DropdownLabel, DropdownGroup } from "./Dropdown";

// ── Data display ──────────────────────────────────────────────────────────────
export { DataTable, Pagination }           from "./DataTable";
export { StatCard, StatGrid }              from "./StatCard";

// ── Lists ─────────────────────────────────────────────────────────────────────
export { List, ListItem, ListSeparator, ListHeader, ListFooter } from "./List";

// ── Notifications ─────────────────────────────────────────────────────────────
// The one canonical single-notification row — for the Inbox, a bell dropdown,
// an admin activity feed, or any future notification-like list.
export { NotificationItem }                from "./NotificationItem";

// ── App shell navigation ──────────────────────────────────────────────────────
// The one canonical Sidebar — variant="app" (default, full research/teaching
// OS sidebar) or variant="admin" (Admin OS sidebar).
export { Sidebar }                         from "./Sidebar";
// The one canonical TopNav — variant="app" (default) or variant="admin".
export { TopNav }                          from "./TopNav";
// The one shell content wrapper — breadcrumb + page container + footer.
// Used by both AppShell and AdminShell around their routed content.
export { ContentFrame }                    from "./ContentFrame";
// The one shell footer — rendered only by ContentFrame, never per-page.
export { Footer }                          from "./Footer";

// ── Search & filters ──────────────────────────────────────────────────────────
export { SearchBar, FilterBar, FilterChip } from "./SearchBar";

// ── States ────────────────────────────────────────────────────────────────────
export { EmptyState }                      from "./EmptyState";
export { ErrorState }                      from "./ErrorState";
export {
  SkeletonLine,
  SkeletonCard,
  SkeletonTable,
  SkeletonPage,
  Spinner,
  LoadingOverlay,
}                                          from "./LoadingState";

// ── Modals & overlays ─────────────────────────────────────────────────────────
export { Modal, Dialog }                   from "./Modal";
export { Drawer }                          from "./Drawer";

// ── Operating-system patterns (Admin OS Phase 2) ─────────────────────────────
export { ContextPanel }                    from "./ContextPanel";
export { SmartActionsBar }                 from "./SmartActionsBar";
export { RelatedEntityPanel }              from "./RelatedEntityPanel";

// ── Charts ────────────────────────────────────────────────────────────────────
export {
  Sparkline,
  SparkArea,
  MiniBar,
  BarChart,
  DonutChart,
  LineChart,
  ChartLegend,
}                                          from "./Chart";

// ── Content cards ─────────────────────────────────────────────────────────────
// Metric cards live in StatCard.jsx (the one canonical implementation) — a
// MetricCard used to live here too and has been consolidated into StatCard.
export {
  WorkspaceCard,
  ResearchCard,
  PublicationCard,
  PersonCard,
  Timeline,
  TimelineItem,
  StatusDot,
}                                          from "./PremiumCards";

// ── Domain / entity cards ─────────────────────────────────────────────────────
export {
  GrantCard,
  ConferenceCard,
  JournalCard,
  ResearcherCard,
  InstitutionCard,
}                                          from "./EntityCards";

// ── AI components ─────────────────────────────────────────────────────────────
export {
  AIResponsePanel,
  EvidencePanel,
  EvidenceItem,
  CitationInline,
  VerificationBadge,
}                                          from "./AIComponents";
