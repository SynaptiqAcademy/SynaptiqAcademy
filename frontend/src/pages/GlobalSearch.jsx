/* eslint-disable */
/**
 * GlobalSearch — Unified cross-platform search.
 *
 * Searches live database content (not just navigation pages) using:
 *   GET /api/lkg/search?q={query}             → Knowledge Graph semantic search
 *   GET /api/network/people?q={query}         → Researcher search
 *   GET /api/network/groups?q={query}         → Teams / research groups
 *   GET /api/projects?q={query}               → Research projects
 *   GET /api/grants?q={query}                 → Grant opportunities
 *   GET /api/journals?q={query}               → Journals
 *
 * Results are grouped by entity type with direct deep-links.
 * Complements CommandPalette (⌘K) which searches navigation pages.
 */
import React, { useEffect, useRef, useState, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api from "../lib/api";
import {
  Search, User, FileText, FolderOpen, Building2, Users, Coins,
  BookOpen, Sparkles, ArrowRight, ChevronRight, X, Loader2,
  GraduationCap, Globe, Target, BrainCircuit,
} from "lucide-react";
import { ResearchLayout } from "@/layouts";

// ─── Entity type → route resolver ────────────────────────────────────────────
function resolveRoute(result) {
  const { type, id, slug } = result;
  switch (type) {
    case "researcher":
    case "user":        return slug ? `/researcher/${slug}` : `/faculty/${id}`;
    case "publication": return `/repository/${id}`;
    case "project":     return `/projects/${id}`;
    case "institution": return `/institution-hub/${id}`;
    case "group":
    case "team":        return `/teams/${id}`;
    case "workspace":   return `/workspaces/${id}`;
    case "grant":       return `/grants/${id}`;
    case "journal":     return `/journals/${id}`;
    case "conference":  return `/conferences/${id}`;
    case "manuscript":  return `/manuscripts/${id}`;
    case "lesson":      return `/teaching/lessons/${id}`;
    case "assessment":  return `/teaching/assessments/${id}`;
    default:            return null;
  }
}

// ─── Type → display config ────────────────────────────────────────────────────
const TYPE_CONFIG = {
  researcher:   { label: "Researchers",    icon: User,        color: "#7C3AED", plural: "Researchers"    },
  user:         { label: "Researchers",    icon: User,        color: "#7C3AED", plural: "Researchers"    },
  publication:  { label: "Publications",   icon: FileText,    color: "#0891B2", plural: "Publications"   },
  project:      { label: "Projects",       icon: FolderOpen,  color: "#059669", plural: "Projects"       },
  institution:  { label: "Institutions",   icon: Building2,   color: "#374151", plural: "Institutions"   },
  group:        { label: "Teams",          icon: Users,       color: "#D97706", plural: "Teams"          },
  team:         { label: "Teams",          icon: Users,       color: "#D97706", plural: "Teams"          },
  workspace:    { label: "Workspaces",     icon: FolderOpen,  color: "#2563EB", plural: "Workspaces"     },
  grant:        { label: "Grants",         icon: Coins,       color: "#059669", plural: "Grants"         },
  journal:      { label: "Journals",       icon: BookOpen,    color: "#9333EA", plural: "Journals"       },
  conference:   { label: "Conferences",    icon: Globe,       color: "#EA580C", plural: "Conferences"    },
  manuscript:   { label: "Manuscripts",    icon: FileText,    color: "#0891B2", plural: "Manuscripts"    },
  lesson:       { label: "Lessons",        icon: GraduationCap, color: "#0891B2", plural: "Lessons"     },
  assessment:   { label: "Assessments",    icon: Target,      color: "#8B5CF6", plural: "Assessments"   },
  topic:        { label: "Research Topics",icon: BrainCircuit,color: "#64748B", plural: "Topics"        },
};

const SECTION_ORDER = [
  "researcher", "user", "project", "publication", "manuscript",
  "group", "team", "institution", "workspace",
  "grant", "journal", "conference", "lesson", "assessment", "topic",
];

function getConfig(type) {
  return TYPE_CONFIG[type] || { label: type, icon: Sparkles, color: "#64748B" };
}

// ─── Quick search suggestions ─────────────────────────────────────────────────
const QUICK_LINKS = [
  { label: "Find Researchers",  to: "/researchers",  icon: User       },
  { label: "Browse Projects",   to: "/projects",     icon: FolderOpen },
  { label: "Find Teams",        to: "/teams",        icon: Users      },
  { label: "Browse Grants",     to: "/grants",       icon: Coins      },
  { label: "Browse Journals",   to: "/journals",     icon: BookOpen   },
  { label: "Institution Hub",   to: "/institution-hub", icon: Building2 },
];

// ─── Result item ──────────────────────────────────────────────────────────────
function ResultItem({ result }) {
  const cfg = getConfig(result.type);
  const Icon = cfg.icon;
  const to = resolveRoute(result);

  const label = result.label || result.name || result.title || "Untitled";
  const sub   = result.institution || result.discipline || result.year || result.type;

  if (!to) return null;

  return (
    <Link
      to={to}
      className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50 transition-colors group"
    >
      <div
        className="w-7 h-7 shrink-0 flex items-center justify-center"
        style={{ background: cfg.color + "15" }}
      >
        <Icon size={13} strokeWidth={1.5} style={{ color: cfg.color }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-slate-900 truncate group-hover:text-[#0F2847] transition-colors">
          {label}
        </div>
        {sub && (
          <div className="text-xs text-slate-500 mt-0.5 truncate">{sub}</div>
        )}
      </div>
      <ChevronRight size={12} strokeWidth={1.5} className="text-slate-300 shrink-0" />
    </Link>
  );
}

// ─── Result group ─────────────────────────────────────────────────────────────
function ResultGroup({ type, results }) {
  const cfg = getConfig(type);
  const Icon = cfg.icon;
  return (
    <section className="border border-slate-200 bg-white overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
        <Icon size={13} strokeWidth={1.5} style={{ color: cfg.color }} />
        <span className="overline">{cfg.plural || cfg.label}</span>
        <span className="text-[10px] font-mono text-slate-400 ml-1">{results.length}</span>
      </div>
      <div className="divide-y divide-slate-50">
        {results.slice(0, 5).map((r, i) => (
          <ResultItem key={r.id || i} result={r} />
        ))}
        {results.length > 5 && (
          <div className="px-4 py-2 text-xs text-slate-400 font-mono">
            +{results.length - 5} more — refine your search to narrow results
          </div>
        )}
      </div>
    </section>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function GlobalSearch() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQ = searchParams.get("q") || "";

  const [query, setQuery]     = useState(initialQ);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const inputRef              = useRef(null);
  const debounceRef           = useRef(null);

  // Auto-focus on mount
  useEffect(() => { inputRef.current?.focus(); }, []);

  const doSearch = useCallback(async (q) => {
    if (!q || q.trim().length < 2) {
      setResults(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);

    try {
      // Primary: LKG semantic search (covers researchers, publications, institutions, etc.)
      const [lkgRes, peopleRes, groupsRes, projectsRes, grantsRes, journalsRes] = await Promise.allSettled([
        api.get(`/lkg/search?q=${encodeURIComponent(q)}&limit=40`),
        api.get(`/network/people?q=${encodeURIComponent(q)}&limit=10`),
        api.get(`/network/groups?q=${encodeURIComponent(q)}&limit=10`),
        api.get(`/projects?q=${encodeURIComponent(q)}&limit=10`),
        api.get(`/grants?q=${encodeURIComponent(q)}&limit=10`),
        api.get(`/journals?q=${encodeURIComponent(q)}&limit=10`),
      ]);

      // Merge results, deduplicate by id
      const seen = new Set();
      const merged = [];

      const addResults = (items, typeOverride) => {
        (items || []).forEach((r) => {
          const id = r.id || r._id;
          if (!id || seen.has(id)) return;
          seen.add(id);
          merged.push({ ...r, id, type: typeOverride || r.type || r.entity_type || "unknown" });
        });
      };

      // LKG semantic results (highest quality)
      if (lkgRes.status === "fulfilled") {
        addResults(lkgRes.value.data?.results || [], null);
      }

      // People search
      if (peopleRes.status === "fulfilled") {
        const people = peopleRes.value.data?.items || peopleRes.value.data || [];
        addResults(people.map((p) => ({
          ...p,
          label: p.full_name || p.label,
          type: "researcher",
        })), null);
      }

      // Groups/Teams
      if (groupsRes.status === "fulfilled") {
        const groups = groupsRes.value.data?.items || groupsRes.value.data || [];
        addResults(groups.map((g) => ({ ...g, label: g.name || g.label, type: "group" })), null);
      }

      // Projects
      if (projectsRes.status === "fulfilled") {
        const projects = projectsRes.value.data?.items || projectsRes.value.data || [];
        addResults(projects.map((p) => ({
          ...p,
          label: p.name || p.title || p.label,
          type: "project",
        })), null);
      }

      // Grants
      if (grantsRes.status === "fulfilled") {
        const grants = grantsRes.value.data?.items || grantsRes.value.data || [];
        addResults(grants.map((g) => ({
          ...g,
          label: g.title || g.name || g.label,
          type: "grant",
        })), null);
      }

      // Journals
      if (journalsRes.status === "fulfilled") {
        const journals = journalsRes.value.data?.items || journalsRes.value.data || [];
        addResults(journals.map((j) => ({
          ...j,
          label: j.name || j.title || j.label,
          type: "journal",
        })), null);
      }

      setResults(merged);
    } catch (e) {
      setError("Search is temporarily unavailable. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleChange = (e) => {
    const val = e.target.value;
    setQuery(val);
    setSearchParams(val ? { q: val } : {}, { replace: true });

    clearTimeout(debounceRef.current);
    if (val.trim().length < 2) {
      setResults(null);
      return;
    }
    debounceRef.current = setTimeout(() => doSearch(val), 350);
  };

  const clearSearch = () => {
    setQuery("");
    setResults(null);
    setSearchParams({}, { replace: true });
    inputRef.current?.focus();
  };

  // Run search on initial load if query param present
  useEffect(() => {
    if (initialQ.length >= 2) doSearch(initialQ);
  }, []); // eslint-disable-line

  // Group results by type in canonical order
  const grouped = {};
  (results || []).forEach((r) => {
    const t = r.type || "unknown";
    if (!grouped[t]) grouped[t] = [];
    grouped[t].push(r);
  });

  const orderedTypes = [
    ...SECTION_ORDER.filter((t) => grouped[t]),
    ...Object.keys(grouped).filter((t) => !SECTION_ORDER.includes(t)),
  ];

  const totalResults = (results || []).length;

  return (
    <ResearchLayout
      title="Search"
      subtitle="Search across researchers, projects, teams, publications, grants, journals, and institutions."
      icon={Search}
    >
      {/* Search input */}
      <div className="relative mb-6">
        <Search
          size={16}
          strokeWidth={1.5}
          className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
        />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleChange}
          placeholder="Search researchers, projects, teams, publications, grants…"
          className="w-full pl-11 pr-10 py-3.5 border border-slate-300 text-sm bg-white focus:outline-none focus:border-[#0F2847] transition-colors"
          data-testid="global-search-input"
          autoComplete="off"
        />
        {query && (
          <button
            onClick={clearSearch}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700"
            aria-label="Clear search"
          >
            <X size={14} strokeWidth={1.5} />
          </button>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center gap-2 text-sm text-slate-500 py-8 justify-center">
          <Loader2 size={16} className="animate-spin" />
          Searching…
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {/* Results */}
      {!loading && results !== null && !error && (
        <>
          {totalResults === 0 ? (
            <div className="text-center py-16">
              <Search size={28} strokeWidth={1.5} className="text-slate-200 mx-auto mb-3" />
              <div className="text-slate-900 font-medium">No results for "{query}"</div>
              <div className="text-sm text-slate-500 mt-1">Try a different search term or browse by category below.</div>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {QUICK_LINKS.map(({ label, to, icon: Icon }) => (
                  <Link
                    key={to}
                    to={to}
                    className="inline-flex items-center gap-1.5 text-xs border border-slate-200 bg-white px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847] transition-colors"
                  >
                    <Icon size={11} strokeWidth={1.5} />
                    {label}
                  </Link>
                ))}
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-4">
                <div className="text-sm text-slate-600">
                  <span className="font-medium text-slate-900">{totalResults}</span> results for <span className="font-medium text-slate-900">"{query}"</span>
                </div>
                <div className="text-xs text-slate-400 font-mono">
                  {orderedTypes.length} categories
                </div>
              </div>
              <div className="space-y-4">
                {orderedTypes.map((type) => (
                  <ResultGroup key={type} type={type} results={grouped[type]} />
                ))}
              </div>
            </>
          )}
        </>
      )}

      {/* Empty state / quick links */}
      {!loading && results === null && !query && (
        <div className="space-y-6">
          <div>
            <div className="overline mb-3">Browse by category</div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {QUICK_LINKS.map(({ label, to, icon: Icon }) => (
                <Link
                  key={to}
                  to={to}
                  className="border border-slate-200 bg-white p-4 hover:border-[#0F2847] transition-colors group flex items-center gap-3"
                >
                  <Icon size={15} strokeWidth={1.5} className="text-[#0F2847] shrink-0" />
                  <span className="text-sm text-slate-900 group-hover:text-[#0F2847] transition-colors">{label}</span>
                  <ArrowRight size={12} strokeWidth={1.5} className="ml-auto text-slate-300 group-hover:text-[#0F2847] transition-colors" />
                </Link>
              ))}
            </div>
          </div>
          <div className="border border-slate-200 bg-slate-50 p-4">
            <div className="text-xs text-slate-500 font-mono">
              Tip: Use <kbd className="bg-white border border-slate-200 px-1 py-0.5 text-[10px]">⌘K</kbd> to quickly navigate to any page in the platform.
              Global Search finds actual research content — researchers, publications, projects, and more.
            </div>
          </div>
        </div>
      )}
    </ResearchLayout>
  );
}
