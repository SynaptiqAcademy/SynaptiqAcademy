/**
 * navigation.js V5 — Research OS Navigation Architecture
 *
 * Philosophy:
 *   Top Navigation  → "What do I need today?"        (Home / Inbox / Messages / Meetings)
 *   Left Sidebar    → "What tools do I have?"        (8 functional groups)
 *   Avatar Menu     → "Who am I / account settings?" (in TopBar, not here)
 *
 * Sections (8): research · publishing · funding · teaching · network · institution · ai · profile
 *
 * Home/Inbox/Messages/Meetings are now PRIMARY TOP NAV — not sidebar sections.
 * They remain accessible via ⌘K (getAllPages) and via their existing routes.
 *
 * V2 API (Sidebar, MobileDrawer):
 *   NAV_SECTIONS, getOrderedSections(), findSectionForPath(), findSubGroupForPath()
 *
 * V1 backward-compat (CommandPalette, WorkflowLauncher):
 *   CORE_ITEMS, WORKSPACE_ITEMS, AI_TOOLS, DISCOVER_GROUP, DISCOVER_FLAT,
 *   COLLAB_ITEMS, MESSAGES_ITEM, PUBS_ITEMS, IMPACT_ITEMS, INSTITUTION_ITEMS,
 *   TEACHING_ITEMS, ALL_* route sets, TOOL_PREFIXES, getAllPages(), QUICK_ACTIONS
 */

import {
  BrainCircuit, LayoutDashboard, Bell, MessageSquare,
  FlaskConical, FolderOpen, LayoutGrid,
  BookMarked, Target, BarChart2, Microscope, AlignLeft, PenLine, Lightbulb, Activity,
  BookOpen, CalendarDays, BadgeDollarSign, Coins, Users, UserCheck, Trophy,
  Building2, School, Sparkles, ShoppingBag,
  Users2, Network, Inbox, Mail,
  FileText, ClipboardCheck, Layers, ClipboardList, Archive,
  TrendingUp, BarChart3, Link2, Eye, Award, Shield, ShieldCheck,
  GraduationCap, PenTool, CheckSquare, Briefcase, Folder,
  User, Settings, CreditCard, Fingerprint, BadgeCheck, FileSearch, History,
  AlertTriangle, Globe, ShieldAlert,
  Brain, Zap, Star, Rocket, Command, Compass, Cpu, Sun,
  Handshake, Radio, Bookmark, Network as NetworkIcon,
  Store, Receipt, Package, Tag, DollarSign,
  GitBranch, Waypoints, Map, Search, RefreshCw, Bot,
  House,
} from "lucide-react";
import { TID } from "../lib/testIds";

// ─── V2: Section definitions ──────────────────────────────────────────────────

export const NAV_SECTIONS = {

  // ── Research ──────────────────────────────────────────────────────────────
  // Everything a researcher needs to do research work.
  // AI writing tools live here, not in "AI Workspace" (which is the orchestration layer).
  research: {
    id: "research",
    label: "Research",
    icon: FlaskConical,
    items: [
      // ── Research Tools (visible) ──
      {
        _type: "subgroup",
        id: "research-tools",
        label: "AI Tools",
        icon: Brain,
        items: [
          { to: "/literature-review",       label: "Literature Review",    icon: BookMarked,   testid: TID.navLiteratureReview },
          { to: "/research-gap-finder",     label: "Research Gaps",        icon: Target,       testid: TID.navResearchGapFinder },
          { to: "/research-design-advisor", label: "Study Design",         icon: FlaskConical, testid: TID.navResearchDesignAdvisor },
          { to: "/statistical-review",      label: "Statistical Analysis", icon: BarChart2,    testid: TID.navStatisticalReview },
          { to: "/ai/rewrite",              label: "AI Rewriting",         icon: PenLine,      testid: null },
          { to: "/ai/abstract",             label: "Abstract Generator",   icon: AlignLeft,    testid: null },
          { to: "/recommendations",         label: "Recommendations",      icon: Lightbulb,    testid: null },
        ],
      },
      // ── Research Workspace (visible) ──
      {
        _type: "subgroup",
        id: "research-workspace",
        label: "Workspace",
        icon: FolderOpen,
        items: [
          { to: "/research-hub", label: "Command Center",    icon: Command,    testid: null, exact: true },
          { to: "/projects",     label: "Research Projects", icon: FolderOpen, testid: TID.navProjects, exact: true },
          { to: "/workspaces",   label: "Workspaces",        icon: LayoutGrid, testid: TID.navWorkspaces },
          { to: "/repository",   label: "Repository",        icon: Archive,    testid: TID.navRepository },
          { to: "/timeline",     label: "Timeline",          icon: Activity,   testid: null, exact: true },
        ],
      },
      // ── Hidden: SIE (Research Planner), AKG, advanced tools ──
      {
        _type: "subgroup",
        id: "research-planner",
        label: "Research Planner",
        icon: Brain,
        sidebarHidden: true,
        items: [
          { to: "/sie",                 label: "Command Center",      icon: Command,       testid: null, exact: true },
          { to: "/sie/goals",           label: "Research Goals",      icon: Target,        testid: null },
          { to: "/sie/missions",        label: "Research Missions",   icon: CheckSquare,   testid: null },
          { to: "/sie/planning",        label: "Research Roadmaps",   icon: BookMarked,    testid: null },
          { to: "/sie/publications",    label: "Publication Roadmap", icon: FileText,      testid: null },
          { to: "/sie/career",          label: "Career Planner",      icon: GraduationCap, testid: null },
          { to: "/sie/daily",           label: "Daily Agenda",        icon: CalendarDays,  testid: null },
          { to: "/sie/weekly",          label: "Weekly Planner",      icon: BarChart2,     testid: null },
          { to: "/sie/memory",          label: "AI Memory",           icon: Brain,         testid: null },
          { to: "/sie/recommendations", label: "Recommendations",     icon: Sparkles,      testid: null },
          { to: "/sie/automations",     label: "Automation Center",   icon: Zap,           testid: null },
          { to: "/sie/progress",        label: "Research Progress",   icon: TrendingUp,    testid: null },
          { to: "/sie/grants",          label: "Grant Planner",       icon: Trophy,        testid: null },
          { to: "/sie/settings",        label: "SIE Settings",        icon: Settings,      testid: null },
        ],
      },
      {
        _type: "subgroup",
        id: "knowledge-search",
        label: "Knowledge Search",
        icon: Waypoints,
        sidebarHidden: true,
        items: [
          { to: "/akg",                 label: "Knowledge Home",      icon: Waypoints,  testid: null, exact: true },
          { to: "/akg/search",          label: "Semantic Search",     icon: Search,     testid: null },
          { to: "/akg/trends",          label: "Trend Discovery",     icon: TrendingUp, testid: null },
          { to: "/akg/recommendations", label: "Research Connections",icon: Lightbulb,  testid: null },
          { to: "/akg/reasoning",       label: "AI Reasoning",        icon: Brain,      testid: null },
        ],
      },
      {
        _type: "subgroup",
        id: "advanced-research",
        label: "Advanced Tools",
        icon: Cpu,
        expertOnly: true,
        sidebarHidden: true,
        items: [
          { to: "/akg/explorer",        label: "Graph Explorer",      icon: Map,        testid: null },
          { to: "/akg/analytics",       label: "Graph Analytics",     icon: BarChart2,  testid: null },
          { to: "/akg/sync",            label: "Graph Sync",          icon: RefreshCw,  testid: null },
          { to: "/akg/admin",           label: "Graph Admin",         icon: Shield,     testid: null },
          { to: "/integrity",           label: "Integrity Report",    icon: Microscope, testid: null },
          { to: "/timeline/analytics",  label: "Activity Analytics",  icon: BarChart3,  testid: null },
          { to: "/manuscript-review",   label: "Manuscript Review",   icon: Microscope, testid: TID.navAIManuscriptReview },
        ],
      },
      // Standalone hidden items
      { to: "/research-hub", label: "Research Hub",     icon: Command,   testid: null, exact: true, sidebarHidden: true },
      { to: "/search",       label: "Search",           icon: Search,    testid: null, exact: true, sidebarHidden: true },
      { to: "/copilot",      label: "Copilot",          icon: Sparkles,  testid: null, exact: true, sidebarHidden: true },
    ],
    routes: [
      "/research-hub", "/projects", "/workspaces", "/repository", "/timeline",
      // AI Tools (explicitly here so /ai/rewrite doesn't match the "ai" section)
      "/ai/rewrite", "/ai/abstract",
      "/literature-review", "/research-gap-finder", "/research-design-advisor",
      "/statistical-review", "/recommendations",
      // SIE
      "/sie", "/sie/goals", "/sie/missions", "/sie/planning", "/sie/publications",
      "/sie/grants", "/sie/career", "/sie/daily", "/sie/weekly", "/sie/memory",
      "/sie/recommendations", "/sie/automations", "/sie/progress", "/sie/settings",
      // AKG
      "/akg", "/akg/search", "/akg/trends", "/akg/recommendations", "/akg/reasoning",
      "/akg/explorer", "/akg/analytics", "/akg/entity", "/akg/sync", "/akg/admin",
      // Other research tools
      "/integrity", "/timeline/analytics", "/manuscript-review",
      "/search", "/copilot",
    ],
  },

  // ── Publishing ────────────────────────────────────────────────────────────
  publishing: {
    id: "publishing",
    label: "Publishing",
    icon: FileText,
    items: [
      { to: "/manuscripts",        label: "Manuscripts",          icon: FileText,       testid: TID.navManuscripts },
      { to: "/reviews",            label: "Reviews",              icon: ClipboardCheck, testid: TID.navReviews },
      { to: "/publication-hub",    label: "Publication Hub",      icon: Layers,         testid: TID.navPublicationHub },
      { to: "/journals",           label: "Journals",             icon: BookOpen,       testid: TID.navJournals },
      { to: "/conferences",        label: "Conferences",          icon: CalendarDays,   testid: TID.navConferences },
      { to: "/grant-applications", label: "Applications",         icon: ClipboardList,  testid: null },
      { to: "/citation-monitoring",label: "Citation Monitoring",  icon: Eye,            testid: TID.navCitationMonitoring },
      // Impact subgroup
      {
        _type: "subgroup",
        id: "pub-impact",
        label: "Impact",
        icon: TrendingUp,
        items: [
          { to: "/research-impact",  label: "Research Impact", icon: Activity,  testid: TID.navResearchImpact },
          { to: "/impact-dashboard", label: "Impact Dashboard",icon: TrendingUp, testid: null },
          { to: "/citations",        label: "Citations",       icon: Link2,      testid: TID.navCitations },
          { to: "/analytics",        label: "Analytics",       icon: BarChart3,  testid: TID.navAnalytics },
          { to: "/leaderboards",     label: "Leaderboards",    icon: Trophy,     testid: null },
          { to: "/reputation",       label: "Reputation",      icon: Award,      testid: null },
          { to: "/verification",     label: "Verification",    icon: ShieldCheck,testid: null },
        ],
      },
    ],
    routes: [
      "/manuscripts", "/reviews", "/publication-hub", "/journals", "/conferences",
      "/grant-applications", "/citation-monitoring",
      "/research-impact", "/impact-dashboard", "/citations", "/analytics",
      "/leaderboards", "/reputation", "/verification",
    ],
  },

  // ── Funding ───────────────────────────────────────────────────────────────
  funding: {
    id: "funding",
    label: "Funding",
    icon: BadgeDollarSign,
    items: [
      { to: "/grants",                  label: "Grants",                 icon: BadgeDollarSign, testid: TID.navGrants },
      { to: "/funding",                 label: "Funding Opportunities",  icon: Coins,           testid: TID.navFunding },
      { to: "/grant-collaboration-hub", label: "Grant AI",               icon: BrainCircuit,    testid: null },
      { to: "/grant-applications",      label: "Grant Applications",     icon: ClipboardList,   testid: null, sidebarHidden: true },
    ],
    routes: ["/grants", "/funding", "/grant-applications", "/grant-collaboration-hub"],
  },

  // ── Teaching ──────────────────────────────────────────────────────────────
  teaching: {
    id: "teaching",
    label: "Teaching",
    icon: GraduationCap,
    items: [
      { to: "/teaching",                    label: "Courses",             icon: GraduationCap, testid: null, exact: true },
      { to: "/teaching/lesson-planner",     label: "Lesson Planner",     icon: PenTool,       testid: null },
      { to: "/teaching/assessment-builder", label: "Assessment Builder", icon: CheckSquare,   testid: null },
      { to: "/teaching/workspaces",         label: "Teaching Workspace", icon: Folder,        testid: null },
      { to: "/teaching/analytics",          label: "Teaching Analytics", icon: BarChart3,     testid: null },
      { to: "/teaching/portfolio",          label: "Portfolio",          icon: Briefcase,     testid: null, sidebarHidden: true },
      { to: "/faculty",                     label: "Faculty Profiles",   icon: Users,         testid: null, sidebarHidden: true },
      {
        _type: "subgroup",
        id: "teaching-integration",
        label: "Research & Institution",
        icon: Network,
        sidebarHidden: true,
        items: [
          { to: "/workspaces",              label: "Research Workspaces", icon: LayoutGrid, testid: null },
          { to: "/projects",                label: "Research Projects",   icon: FolderOpen, testid: null },
          { to: "/network/teaching",        label: "Teaching Networks",   icon: Users,      testid: null },
          { to: "/institution-hub",         label: "Institution Hub",     icon: Building2,  testid: null },
          { to: "/institution/departments", label: "Departments",         icon: School,     testid: null },
        ],
      },
    ],
    routes: [
      "/teaching", "/teaching/lesson-planner", "/teaching/assessment-builder",
      "/teaching/portfolio", "/teaching/workspaces", "/teaching/analytics", "/faculty",
    ],
  },

  // ── Academic Network ──────────────────────────────────────────────────────
  network: {
    id: "network",
    label: "Academic Network",
    icon: Users2,
    items: [
      // Visible
      { to: "/researchers",            label: "Researchers",          icon: Users,         testid: null, exact: true },
      { to: "/collaborations",         label: "Collaborations",       icon: Users2,        testid: TID.navCollaborations },
      { to: "/reviewer-marketplace",   label: "Reviewer Marketplace", icon: UserCheck,     testid: null },
      // Messages and Meetings live only in the global TopBar (see file header) — not duplicated here.
      // Hidden — accessible via ⌘K and direct URL
      { to: "/network",                label: "Network",              icon: NetworkIcon,   testid: TID.navNetwork, exact: true, sidebarHidden: true },
      { to: "/collaboration-requests", label: "Requests",             icon: Inbox,         testid: TID.navCollabRequests, sidebarHidden: true },
      { to: "/invitations",            label: "Invitations",          icon: Mail,          testid: null, sidebarHidden: true },
      { to: "/teams",                  label: "Research Teams",       icon: Users2,        testid: null, exact: true, sidebarHidden: true },
      { to: "/feed",                   label: "Research Feed",        icon: Radio,         testid: null, exact: true, sidebarHidden: true },
      { to: "/expertise",              label: "Expertise",            icon: Sparkles,      testid: TID.navExpertise, sidebarHidden: true },
      {
        _type: "subgroup",
        id: "network-discover",
        label: "Discover",
        icon: Compass,
        sidebarHidden: true,
        items: [
          { to: "/network/people",        label: "Researchers",        icon: Users,      testid: null },
          { to: "/network/institutions",  label: "Institutions",       icon: Building2,  testid: null },
          { to: "/network/groups",        label: "Research Groups",    icon: Layers,     testid: null },
          { to: "/network/teaching",      label: "Teaching Networks",  icon: BookOpen,   testid: null },
          { to: "/network/communities",   label: "Communities",        icon: MessageSquare, testid: null },
          { to: "/network/collaborations",label: "Open Collaborations",icon: Handshake,  testid: null },
          { to: "/network/grant-teams",   label: "Grant Teams",        icon: Trophy,     testid: null },
          { to: "/network/industry",      label: "Industry Partners",  icon: Briefcase,  testid: null },
          { to: "/network/mentorship",    label: "Mentorship",         icon: UserCheck,  testid: null },
          { to: "/network/projects",      label: "Projects",           icon: FolderOpen, testid: null },
          { to: "/network/conferences",   label: "Events",             icon: CalendarDays, testid: null },
          { to: "/network/saved",         label: "Saved",              icon: Bookmark,   testid: null },
        ],
      },
      {
        _type: "subgroup",
        id: "network-intelligence",
        label: "Intelligence",
        icon: BarChart3,
        sidebarHidden: true,
        items: [
          { to: "/network/activity",        label: "Activity Center",    icon: Radio,      testid: null },
          { to: "/network/analytics",       label: "Network Analytics",  icon: TrendingUp, testid: null },
          { to: "/network/recommendations", label: "AI Recommendations", icon: Lightbulb,  testid: null },
          { to: "/network/settings",        label: "Network Settings",   icon: Settings,   testid: null },
        ],
      },
      {
        _type: "subgroup",
        id: "services",
        label: "Services",
        icon: Store,
        sidebarHidden: true,
        items: [
          { to: "/academic-marketplace",                 label: "Marketplace Home",    icon: Store,       testid: null, exact: true },
          { to: "/academic-marketplace/services",        label: "Browse Services",     icon: Tag,         testid: null },
          { to: "/academic-marketplace/providers",       label: "Find Experts",        icon: Users,       testid: null },
          { to: "/academic-marketplace/recommendations", label: "Recommended",         icon: Sparkles,    testid: null },
          { to: "/academic-marketplace/orders",          label: "My Orders",           icon: Package,     testid: null },
          { to: "/academic-marketplace/dashboard",       label: "Provider Dashboard",  icon: Briefcase,   testid: null },
          { to: "/academic-marketplace/services/create", label: "Create Service",      icon: Zap,         testid: null },
          { to: "/academic-marketplace/provider/setup",  label: "Provider Profile",    icon: UserCheck,   testid: null },
          { to: "/academic-marketplace/wallet",          label: "Wallet",              icon: DollarSign,  testid: null },
          { to: "/academic-marketplace/disputes",        label: "Dispute Center",      icon: ShieldAlert, testid: null },
          { to: "/academic-marketplace/admin",           label: "Admin Center",        icon: BarChart3,   testid: null },
          { to: "/marketplace",                          label: "Marketplace",         icon: ShoppingBag, testid: TID.navMarketplace },
          { to: "/institutions",                         label: "Institutions",        icon: Building2,   testid: TID.navInstitutions },
        ],
      },
    ],
    routes: [
      "/network", "/teams", "/teams/create", "/feed", "/collaborations", "/collaboration-requests",
      "/invitations", "/researchers", "/expertise",
      "/reviewer-marketplace", "/marketplace", "/institutions",
      // Network sub-pages
      "/network/people", "/network/institutions", "/network/groups", "/network/teaching",
      "/network/communities", "/network/collaborations", "/network/grant-teams",
      "/network/industry", "/network/mentorship", "/network/projects", "/network/conferences",
      "/network/saved", "/network/activity", "/network/analytics",
      "/network/recommendations", "/network/settings",
      // Marketplace
      "/academic-marketplace", "/academic-marketplace/services", "/academic-marketplace/services/create",
      "/academic-marketplace/providers", "/academic-marketplace/recommendations",
      "/academic-marketplace/orders", "/academic-marketplace/dashboard",
      "/academic-marketplace/provider/setup", "/academic-marketplace/wallet",
      "/academic-marketplace/disputes", "/academic-marketplace/admin",
    ],
  },

  // ── Institution ───────────────────────────────────────────────────────────
  institution: {
    id: "institution",
    label: "Institution",
    icon: Building2,
    items: [
      { to: "/institution-hub",              label: "Institution Dashboard", icon: Building2,     testid: null },
      { to: "/institution-platform/faculty", label: "Faculty",               icon: Users,         testid: null },
      { to: "/institution/departments",      label: "Departments",           icon: School,        testid: TID.navDepartments },
      { to: "/institution/analytics",        label: "Analytics",             icon: BarChart3,     testid: null },
      { to: "/institution-platform",         label: "Administration",        icon: LayoutDashboard, testid: null, exact: true },
      { to: "/institution-leaderboards",     label: "Rankings",              icon: Trophy,        testid: null, sidebarHidden: true },
      {
        _type: "subgroup",
        id: "institution-intel",
        label: "Executive Intelligence",
        icon: LayoutDashboard,
        expertOnly: true,
        sidebarHidden: true,
        items: [
          { to: "/institution-platform/health",         label: "Institution Health",       icon: Activity,       testid: null },
          { to: "/institution-platform/departments",    label: "Department Intelligence",  icon: LayoutGrid,     testid: null },
          { to: "/institution-platform/publications",   label: "Publication Intelligence", icon: FileText,       testid: null },
          { to: "/institution-platform/grants",         label: "Grant Intelligence",       icon: Coins,          testid: null },
          { to: "/institution-platform/collaborations", label: "Collaboration Intel",      icon: Globe,          testid: null },
          { to: "/institution-platform/financial",      label: "Financial Intelligence",   icon: TrendingUp,     testid: null },
          { to: "/institution-platform/risks",          label: "Risk Intelligence",        icon: ShieldAlert,    testid: null },
          { to: "/institution-platform/forecasts",      label: "Forecast Center",          icon: BarChart2,      testid: null },
          { to: "/institution-platform/benchmarks",     label: "Benchmark Center",         icon: Target,         testid: null },
          { to: "/institution-platform/reports",        label: "Institution Reports",      icon: ClipboardList,  testid: null },
          { to: "/institution-platform/assistant",      label: "AI Executive Assistant",   icon: BrainCircuit,   testid: null },
          { to: "/institution-platform/strategic",      label: "Strategic Planning",       icon: AlertTriangle,  testid: null },
        ],
      },
    ],
    routes: [
      "/institution-hub", "/institution-leaderboards", "/institution/analytics", "/institution/departments",
      "/institution-platform", "/institution-platform/health", "/institution-platform/faculty",
      "/institution-platform/departments", "/institution-platform/publications",
      "/institution-platform/grants", "/institution-platform/collaborations",
      "/institution-platform/financial", "/institution-platform/risks",
      "/institution-platform/forecasts", "/institution-platform/benchmarks",
      "/institution-platform/reports", "/institution-platform/assistant",
      "/institution-platform/strategic",
    ],
  },

  // ── AI Workspace ──────────────────────────────────────────────────────────
  // Orchestration layer — NOT the writing/research AI tools (those are in Research).
  ai: {
    id: "ai",
    label: "AI Workspace",
    icon: BrainCircuit,
    items: [
      { to: "/ai",          label: "AI Assistant",  icon: BrainCircuit, testid: null, exact: true, accent: true },
      { to: "/ai-suite",    label: "AI Suite",      icon: Sparkles,     testid: null, exact: true },
      { to: "/ai-usage",    label: "AI Usage",      icon: Activity,     testid: TID.navAIUsage },
      { to: "/ai-credits",  label: "Credits",       icon: Coins,        testid: null },
      { to: "/twin",        label: "Academic Twin", icon: Cpu,          testid: null },
      { to: "/copilot",         label: "Research Copilot",     icon: Sparkles,     testid: null, exact: true, sidebarHidden: true },
      { to: "/agent-workforce", label: "Agent Workforce",      icon: Bot,          testid: null, exact: true, sidebarHidden: true },
      { to: "/collaboration-intelligence", label: "Collaboration AI", icon: BrainCircuit, testid: TID.navCollaborationIntelligence, sidebarHidden: true },
      { to: "/living-graph",    label: "Knowledge Graph",      icon: NetworkIcon,  testid: null, sidebarHidden: true },
      { to: "/today",           label: "Today",                icon: Sun,          testid: null, exact: true, sidebarHidden: true },
    ],
    routes: [
      // NOTE: /ai/rewrite and /ai/abstract are in research.routes — they match research first
      "/ai", "/ai-suite", "/ai-credits", "/ai-usage",
      "/copilot", "/agent-workforce", "/collaboration-intelligence",
      "/twin", "/living-graph", "/today",
      "/recommendations",
    ],
  },

  // ── Account ───────────────────────────────────────────────────────────────
  // Identity (Academic Passport) and Settings do NOT appear in the sidebar —
  // both live only in the Avatar dropdown (single entry point).
  profile: {
    id: "profile",
    label: "Account",
    icon: User,
    items: [
      // Hidden — accessible via ⌘K and the avatar menu (single entry point)
      { to: "/academic-passport",      label: "Academic Passport", icon: Fingerprint, testid: null, sidebarHidden: true },
      { to: "/settings",               label: "Settings",   icon: Settings,   testid: TID.navSettings, exact: true, sidebarHidden: true },
      { to: "/settings/billing",       label: "Billing",    icon: CreditCard, testid: null, sidebarHidden: true },
      { to: "/settings/security",      label: "Security & Privacy", icon: ShieldCheck, testid: null, sidebarHidden: true },
      { to: "/recommendation-center",  label: "AI Advisor", icon: Sparkles,   testid: null, sidebarHidden: true },
      {
        _type: "subgroup",
        id: "trust",
        label: "Trust & Verification",
        icon: ShieldCheck,
        sidebarHidden: true,
        items: [
          { to: "/trust",                  label: "Trust Overview",        icon: ShieldCheck,     testid: null, exact: true },
          { to: "/trust/my-verifications", label: "My Verifications",      icon: BadgeCheck,      testid: null },
          { to: "/trust/requests",         label: "Verification Requests", icon: FileSearch,      testid: null },
          { to: "/trust/score",            label: "Trust Score",           icon: Shield,          testid: null },
          { to: "/trust/integrity",        label: "Integrity Report",      icon: Award,           testid: null },
          { to: "/trust/institution",      label: "Institution Verify",    icon: Building2,       testid: null },
          { to: "/trust/publications",     label: "Publications Verify",   icon: FileText,        testid: null },
          { to: "/trust/reviewer",         label: "Reviewer Verify",       icon: UserCheck,       testid: null },
          { to: "/trust/grants",           label: "Grant Holder Verify",   icon: BadgeDollarSign, testid: null },
          { to: "/trust/history",          label: "Verification History",  icon: History,         testid: null },
          { to: "/trust/settings",         label: "Trust Settings",        icon: Settings,        testid: null },
        ],
      },
    ],
    routes: [
      // Note: /academic-passport is intentionally NOT listed here — it's a
      // flagship top-level page (reached only via the avatar menu), so it
      // shows no "Account >" breadcrumb prefix, same as Settings.
      "/recommendation-center", "/profile", "/settings", "/settings/billing", "/settings/security",
      "/trust", "/trust/my-verifications", "/trust/requests", "/trust/passport",
      "/trust/score", "/trust/integrity", "/trust/institution", "/trust/publications",
      "/trust/reviewer", "/trust/grants", "/trust/history", "/trust/settings",
    ],
  },
};

// ─── V2: Ordered sections by dashboard mode ───────────────────────────────────

// Note: "profile" is intentionally excluded from every ordered list below —
// Academic Passport and Settings are reachable only via the avatar menu
// (TopBar.jsx AVATAR_SECTIONS) and ⌘K, not the sidebar accordion. The
// NAV_SECTIONS.profile object itself stays defined for routing/breadcrumb/search.
const SECTION_ORDERS = {
  research: ["research", "publishing", "funding", "network", "institution", "teaching", "ai"],
  teaching: ["teaching", "research", "publishing", "funding", "network", "institution", "ai"],
  hybrid:   ["network", "research", "teaching", "publishing", "funding", "institution", "ai"],
};

export function getOrderedSections(dashboardMode, showInstitution = false) {
  const order = SECTION_ORDERS[dashboardMode] || SECTION_ORDERS.research;
  return order
    .filter((id) => id !== "institution" || showInstitution)
    .map((id) => NAV_SECTIONS[id]);
}

// ─── V2: Path → section / subgroup detection ──────────────────────────────────

export function findSectionForPath(pathname) {
  for (const [id, section] of Object.entries(NAV_SECTIONS)) {
    const matches = section.routes.some(
      (r) => pathname === r || pathname.startsWith(r + "/")
    );
    if (matches) return id;
  }
  return null;
}

export function findSubGroupForPath(sectionId, pathname) {
  const section = NAV_SECTIONS[sectionId];
  if (!section) return null;
  for (const item of section.items) {
    if (item._type === "subgroup") {
      const found = item.items.some(
        (sub) => pathname === sub.to || pathname.startsWith(sub.to + "/")
      );
      if (found) return item.id;
    }
  }
  return null;
}

// ─── V1: Backward-compat exports (CommandPalette, WorkflowLauncher) ───────────

export const CORE_ITEMS = [
  { to: "/ai",            label: "Synaptiq AI",  icon: BrainCircuit,    testid: null,                 accent: true, exact: false, group: "Platform" },
  { to: "/discover",      label: "Home",         icon: House,           testid: TID.navDiscover,      exact: true,               group: "Platform" },
  { to: "/notifications", label: "Inbox",        icon: Bell,            testid: TID.navNotifications, exact: true,               group: "Platform" },
];

export const WORKSPACE_ITEMS = [
  { to: "/projects",   label: "Projects",   icon: FolderOpen, testid: TID.navProjects,   exact: true,  group: "Research" },
  { to: "/workspaces", label: "Workspaces", icon: LayoutGrid, testid: TID.navWorkspaces, exact: false, group: "Research" },
];

export const AI_TOOLS = [
  { to: "/literature-review",          label: "Literature Review",    icon: BookMarked,   testid: TID.navLiteratureReview,          group: "Research AI" },
  { to: "/research-gap-finder",        label: "Research Gaps",        icon: Target,       testid: TID.navResearchGapFinder,         group: "Research AI" },
  { to: "/research-design-advisor",    label: "Study Design",         icon: FlaskConical, testid: TID.navResearchDesignAdvisor,     group: "Research AI" },
  { to: "/statistical-review",         label: "Statistical Analysis", icon: BarChart2,    testid: TID.navStatisticalReview,         group: "Research AI" },
  { to: "/manuscript-review",          label: "Manuscript Review",    icon: Microscope,   testid: TID.navAIManuscriptReview,        group: "Research AI" },
  { to: "/ai/abstract",                label: "Abstract Generator",   icon: AlignLeft,    testid: null,                             group: "Research AI" },
  { to: "/ai/rewrite",                 label: "AI Rewriting",         icon: PenLine,      testid: null,                             group: "Research AI" },
  { to: "/collaboration-intelligence", label: "Collaboration AI",     icon: BrainCircuit, testid: TID.navCollaborationIntelligence, group: "Research AI" },
  { to: "/recommendations",            label: "Recommendations",      icon: Lightbulb,    testid: null,                             group: "Research AI" },
  { to: "/ai-usage",                   label: "AI Usage",             icon: Activity,     testid: TID.navAIUsage,                   group: "Research AI" },
];

export const DISCOVER_GROUP = [
  { to: "/journals",             label: "Journals",             icon: BookOpen,        testid: TID.navJournals,    group: "Publishing" },
  { to: "/conferences",          label: "Conferences",          icon: CalendarDays,    testid: TID.navConferences, group: "Publishing" },
  { to: "/grants",               label: "Grants",               icon: BadgeDollarSign, testid: TID.navGrants,      group: "Funding" },
  { to: "/funding",              label: "Funding",              icon: Coins,           testid: TID.navFunding,     group: "Funding" },
  { to: "/researchers",          label: "Researchers",          icon: Users,           testid: null,               group: "Network" },
  { to: "/reviewer-marketplace", label: "Reviewer Marketplace", icon: UserCheck,       testid: null,               group: "Network" },
  { to: "/leaderboards",         label: "Leaderboards",         icon: Trophy,          testid: null,               group: "Publishing" },
];

export const DISCOVER_FLAT = [
  { to: "/institutions",            label: "Institutions", icon: Building2,   testid: TID.navInstitutions, group: "Network" },
  { to: "/institution/departments", label: "Departments",  icon: School,      testid: TID.navDepartments,  group: "Institution" },
  { to: "/expertise",               label: "Expertise",    icon: Sparkles,    testid: TID.navExpertise,    group: "Network" },
  { to: "/marketplace",             label: "Marketplace",  icon: ShoppingBag, testid: TID.navMarketplace,  group: "Network" },
];

export const COLLAB_ITEMS = [
  { to: "/network",                 label: "Network",        icon: NetworkIcon, testid: TID.navNetwork,        group: "Network" },
  { to: "/collaborations",          label: "Collaborations", icon: Users,       testid: TID.navCollaborations, group: "Network" },
  { to: "/collaboration-requests",  label: "Requests",       icon: Inbox,       testid: TID.navCollabRequests, group: "Network" },
  { to: "/invitations",             label: "Invitations",    icon: Mail,        testid: null,                  group: "Network" },
  { to: "/grant-collaboration-hub", label: "Grant Hub",      icon: Users2,      testid: null,                  group: "Funding" },
];

export const MESSAGES_ITEM = {
  to: "/messages", label: "Messages", icon: MessageSquare, testid: TID.navMessages, group: "Platform",
};

export const PUBS_ITEMS = [
  { to: "/manuscripts",        label: "Manuscripts",        icon: FileText,       testid: TID.navManuscripts,    group: "Publishing" },
  { to: "/reviews",            label: "Reviews",            icon: ClipboardCheck, testid: TID.navReviews,        group: "Publishing" },
  { to: "/publication-hub",    label: "Publication Hub",    icon: Layers,         testid: TID.navPublicationHub, group: "Publishing" },
  { to: "/grant-applications", label: "Grant Applications", icon: ClipboardList,  testid: null,                  group: "Funding" },
  { to: "/repository",         label: "Repository",         icon: Archive,        testid: TID.navRepository,     group: "Research" },
];

export const IMPACT_ITEMS = [
  { to: "/research-impact",     label: "Research Impact",     icon: Activity,   testid: TID.navResearchImpact,     group: "Publishing" },
  { to: "/impact-dashboard",    label: "Impact Dashboard",    icon: TrendingUp, testid: null,                      group: "Publishing" },
  { to: "/citations",           label: "Citations",           icon: Link2,      testid: TID.navCitations,          group: "Publishing" },
  { to: "/citation-monitoring", label: "Citation Monitoring", icon: Eye,        testid: TID.navCitationMonitoring, group: "Publishing" },
  { to: "/analytics",           label: "Analytics",           icon: BarChart3,  testid: TID.navAnalytics,          group: "Publishing" },
  { to: "/reputation",          label: "Reputation",          icon: Award,      testid: null,                      group: "Publishing" },
  { to: "/verification",        label: "Verification",        icon: Shield,     testid: null,                      group: "Publishing" },
];

export const INSTITUTION_ITEMS = [
  { to: "/institution-hub",          label: "Institution Hub",       icon: Building2, testid: null, group: "Institution" },
  { to: "/institution-leaderboards", label: "Institution Rankings",  icon: Trophy,    testid: null, group: "Institution" },
  { to: "/institution/analytics",    label: "Institution Analytics", icon: BarChart3, testid: null, group: "Institution" },
];

export const TEACHING_ITEMS = [
  { to: "/teaching",                    label: "Teaching Hub",       icon: GraduationCap, testid: null, exact: true,  group: "Teaching" },
  { to: "/teaching/lesson-planner",     label: "Lesson Planner",    icon: PenTool,       testid: null, exact: false, group: "Teaching" },
  { to: "/teaching/assessment-builder", label: "Assessment Builder",icon: CheckSquare,   testid: null, exact: false, group: "Teaching" },
  { to: "/teaching/portfolio",          label: "Teaching Portfolio", icon: Briefcase,     testid: null, exact: false, group: "Teaching" },
  { to: "/teaching/workspaces",         label: "Teaching Spaces",   icon: Folder,        testid: null, exact: false, group: "Teaching" },
  { to: "/teaching/analytics",          label: "Teaching Analytics",icon: BarChart3,     testid: null, exact: false, group: "Teaching" },
];

// V1 derived route sets
export const ALL_WORKSPACE_ROUTES   = WORKSPACE_ITEMS.map((i) => i.to);
export const ALL_AI_ROUTES          = [...AI_TOOLS.map((i) => i.to), "/ai"];
export const ALL_DISCOVER_ROUTES    = [...DISCOVER_GROUP, ...DISCOVER_FLAT].map((i) => i.to);
export const ALL_COLLAB_ROUTES      = [...COLLAB_ITEMS, MESSAGES_ITEM].map((i) => i.to);
export const ALL_PUBS_ROUTES        = PUBS_ITEMS.map((i) => i.to);
export const ALL_IMPACT_ROUTES      = IMPACT_ITEMS.map((i) => i.to);
export const ALL_INSTITUTION_ROUTES = INSTITUTION_ITEMS.map((i) => i.to);
export const ALL_TEACHING_ROUTES    = TEACHING_ITEMS.map((i) => i.to);

// TOOL_PREFIXES: all routes that aren't top-nav primary destinations.
// Used by MobileBottomNav to detect "More" tab active state.
export const TOOL_PREFIXES = [
  ...NAV_SECTIONS.research.routes,
  ...NAV_SECTIONS.publishing.routes,
  ...NAV_SECTIONS.funding.routes,
  ...NAV_SECTIONS.teaching.routes,
  ...NAV_SECTIONS.network.routes,
  ...NAV_SECTIONS.institution.routes,
  ...NAV_SECTIONS.ai.routes,
];

// ─── getAllPages — flat list for CommandPalette search ─────────────────────────

const _SECTION_GROUPS = {
  research:    "Research",
  publishing:  "Publishing",
  funding:     "Funding",
  teaching:    "Teaching",
  network:     "Network",
  institution: "Institution",
  ai:          "AI Workspace",
  profile:     "Account",
};

// Also include the top-nav primary destinations so they're searchable via ⌘K
const TOP_NAV_PAGES = [
  { label: "Home",     to: "/discover",      group: "Platform", icon: House },
  { label: "Inbox",    to: "/notifications", group: "Platform", icon: Bell },
  { label: "Messages", to: "/messages",      group: "Platform", icon: MessageSquare },
  { label: "Meetings", to: "/meetings",      group: "Platform", icon: CalendarDays },
];

export function getAllPages() {
  const raw = [...TOP_NAV_PAGES];

  for (const [id, section] of Object.entries(NAV_SECTIONS)) {
    const defaultGroup = _SECTION_GROUPS[id] || section.label;

    for (const item of section.items) {
      if (item._type === "subgroup") {
        const group = defaultGroup;
        item.items.forEach((sub) =>
          raw.push({ label: sub.label, to: sub.to, group, icon: sub.icon })
        );
      } else if (item.to) {
        raw.push({ label: item.label, to: item.to, group: defaultGroup, icon: item.icon });
      }
    }
  }

  const seen = new Set();
  return raw.filter((p) => {
    if (seen.has(p.to)) return false;
    seen.add(p.to);
    return true;
  });
}

// ─── Quick Action Workflows (WorkflowLauncher) ────────────────────────────────

export const QUICK_ACTIONS = [
  {
    label: "Research Copilot",
    to: "/copilot",
    icon: Sparkles,
    description: "Multi-agent AI team: literature, writing, review, funding, and more",
    category: "AI",
  },
  {
    label: "Living Knowledge Graph",
    to: "/living-graph",
    icon: NetworkIcon,
    description: "Explore your research network, discover collaborators, and find emerging topics",
    category: "AI",
  },
  {
    label: "Digital Research Twin",
    to: "/twin",
    icon: Brain,
    description: "Your evolving academic identity, goals, research health, and personalized recommendations",
    category: "AI",
  },
  {
    label: "Agent Workforce",
    to: "/agent-workforce",
    icon: Bot,
    description: "Delegate complete research workflows to specialized AI agents",
    category: "AI",
  },
  {
    label: "Write a Manuscript",
    to: "/manuscripts",
    icon: FileText,
    description: "Start writing or continue a research paper",
    category: "Research",
  },
  {
    label: "Start Research Project",
    to: "/projects",
    icon: FolderOpen,
    description: "Create a new research project workspace",
    category: "Research",
  },
  {
    label: "Find Collaborators",
    to: "/collaboration-intelligence",
    icon: Users,
    description: "AI-matched co-author and partner suggestions",
    category: "Research",
  },
  {
    label: "Apply for Funding",
    to: "/grants",
    icon: BadgeDollarSign,
    description: "Discover grants and funding opportunities",
    category: "Funding",
  },
  {
    label: "Generate Literature Review",
    to: "/literature-review",
    icon: BookMarked,
    description: "AI synthesis across hundreds of papers",
    category: "AI",
  },
  {
    label: "Analyze Dataset",
    to: "/statistical-review",
    icon: BarChart2,
    description: "AI review of your statistical methods and data",
    category: "AI",
  },
  {
    label: "Create Teaching Material",
    to: "/teaching/lesson-planner",
    icon: GraduationCap,
    description: "Build lesson plans and assessments with AI",
    category: "Teaching",
  },
  {
    label: "Review Manuscript",
    to: "/manuscript-review",
    icon: Microscope,
    description: "Get structured AI feedback before submission",
    category: "AI",
  },
  {
    label: "Find Research Gaps",
    to: "/research-gap-finder",
    icon: Target,
    description: "Identify unanswered questions in your field",
    category: "Research",
  },
  {
    label: "Generate Research Plan",
    to: "/sie/goals",
    icon: Brain,
    description: "AI-powered research roadmap and goal setting",
    category: "Planning",
  },
  {
    label: "Import Publications",
    to: "/repository",
    icon: Archive,
    description: "Import and manage your publication records",
    category: "Research",
  },
  {
    label: "Generate Abstract",
    to: "/ai/abstract",
    icon: AlignLeft,
    description: "AI-generated abstract from your manuscript",
    category: "AI",
  },
];
