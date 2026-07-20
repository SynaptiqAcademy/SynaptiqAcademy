/**
 * Marketplace — people-first discovery.
 *
 * Premium SYNAPTIQ surface: role chips, deterministic search, AI rerank with
 * credit-aware button. Powered by /api/marketplace/{search,rerank,reverse,analytics}.
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { useAuth } from "../contexts/AuthContext";
import MatchCard from "../components/marketplace/MatchCard";
import InviteModal from "../components/marketplace/InviteModal";
import ReputationBadge from "../components/marketplace/ReputationBadge";
import { NAVY } from "@/lib/tokens";
import { DiscoveryLayout } from "@/layouts";
import {
  Sparkles, Search, SlidersHorizontal, Loader2, Compass, TrendingUp,
  Users, BookOpen, BarChart3, Mail, Award, ArrowRight, X,
} from "lucide-react";
import { Spinner } from "@/components/ds/LoadingState";
import EmptyState from "@/components/ds/EmptyState";

const ROLES = [
  { value: "co_author",       label: "Co-authors",        Icon: Users },
  { value: "statistician",    label: "Statisticians",     Icon: BarChart3 },
  { value: "methodology",     label: "Methodologists",    Icon: Compass },
  { value: "reviewer",        label: "Reviewers",         Icon: BookOpen },
  { value: "ai_specialist",   label: "AI specialists",    Icon: Sparkles },
  { value: "data_scientist",  label: "Data scientists",   Icon: TrendingUp },
  { value: "editor",          label: "Editors",           Icon: BookOpen },
  { value: "sme",             label: "Subject experts",   Icon: Award },
];

const RERANK_COST = 5;

export default function Marketplace() {
  const { user, refreshMe } = useAuth();
  const [role, setRole] = useState(null);
  const [q, setQ] = useState("");
  const [availability, setAvailability] = useState("");
  const [country, setCountry] = useState("");
  const [institution, setInstitution] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [reranked, setReranked] = useState(false);
  const [reranking, setReranking] = useState(false);
  const [inviting, setInviting] = useState(null);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const [reverse, setReverse] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const debounceRef = useRef(null);

  const fetchResults = async () => {
    setLoading(true); setReranked(false);
    try {
      const { data } = await api.post("/marketplace/search", {
        role, q: q || undefined, availability: availability || undefined,
        country: country || undefined, institution: institution || undefined,
        limit: 50,
      });
      setResults(data.results || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Search failed");
    } finally { setLoading(false); }
  };

  useEffect(() => {
    // Debounce text search; instant on filter changes.
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(fetchResults, q ? 350 : 0);
    return () => clearTimeout(debounceRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role, q, availability, country, institution]);

  useEffect(() => {
    api.get("/marketplace/reverse").then(({ data }) => setReverse(data)).catch(() => {});
    api.get("/marketplace/analytics").then(({ data }) => setAnalytics(data)).catch(() => {});
  }, []);

  const rerank = async () => {
    if (!results.length) return;
    if ((user?.credits_balance ?? 0) < RERANK_COST) {
      toast.error(`AI rerank costs ${RERANK_COST} credits; balance too low.`);
      return;
    }
    setReranking(true);
    try {
      const { data } = await api.post("/marketplace/rerank", {
        candidates: results, role, top_n: 10,
        context: q ? `Searching for: ${q}` : null,
      });
      setResults(data.rankings || []);
      setReranked(true);
      toast.success(`AI reranked top ${data.rankings?.length || 0} (−${data.credits_consumed} credits)`);
      refreshMe?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Rerank failed");
    } finally { setReranking(false); }
  };

  const onMessage = (m) => {
    // Open chat with user (navigates to messages)
    window.location.href = `/messages?to=${m.user.id}`;
  };

  const activeFilters = [availability, country, institution].filter(Boolean).length;

  return (
    <DiscoveryLayout
      title="Find collaborators"
      subtitle="People-first discovery across the network. Search by expertise, then use AI to surface the best fits with explanations."
      actions={
        <div className="flex flex-col items-end gap-2">
          <Link to="/expertise" className="text-xs inline-flex items-center gap-1.5 border border-slate-300 px-3 py-2 hover:border-[#0F2847]" data-testid="open-expertise-requests">
            Expertise requests <ArrowRight size={11} strokeWidth={1.5} />
          </Link>
          <Link to="/invitations" className="text-xs inline-flex items-center gap-1.5 border border-slate-300 px-3 py-2 hover:border-[#0F2847]" data-testid="open-invitations">
            <Mail size={11} strokeWidth={1.5} /> My invitations
          </Link>
        </div>
      }
    >
    <div className="space-y-8">
      {/* Role chips */}
      <div className="flex flex-wrap gap-1.5" data-testid="marketplace-role-chips">
        <button
          onClick={() => setRole(null)}
          data-testid="role-chip-any"
          className={`text-xs px-3 py-1.5 border transition-colors ${role === null ? "border-[#0F2847] bg-[#0F2847] text-white" : "border-slate-300 text-slate-700 hover:border-[#0F2847]"}`}
        >
          Any expertise
        </button>
        {ROLES.map(({ value, label, Icon }) => (
          <button
            key={value}
            data-testid={`role-chip-${value}`}
            onClick={() => setRole(value === role ? null : value)}
            className={`text-xs px-3 py-1.5 border inline-flex items-center gap-1.5 transition-colors ${role === value ? "border-[#0F2847] bg-[#0F2847] text-white" : "border-slate-300 text-slate-700 hover:border-[#0F2847]"}`}
          >
            <Icon size={11} strokeWidth={1.5} />
            {label}
          </button>
        ))}
      </div>

      {/* Search + actions row */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[260px]">
          <Search size={13} strokeWidth={1.5} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            data-testid="marketplace-search-input"
            value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Search by keyword, name, institution, skill…"
            className="w-full pl-9 pr-3 py-2 border border-slate-300 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
          />
        </div>
        <button
          data-testid="marketplace-filters-toggle"
          onClick={() => setFiltersOpen((f) => !f)}
          className="inline-flex items-center gap-1.5 text-xs border border-slate-300 px-3 py-2 hover:border-[#0F2847]"
        >
          <SlidersHorizontal size={11} strokeWidth={1.5} />
          Filters{activeFilters > 0 ? ` · ${activeFilters}` : ""}
        </button>
        <button
          data-testid="marketplace-rerank-btn"
          onClick={rerank}
          disabled={reranking || !results.length}
          className="inline-flex items-center gap-1.5 text-xs bg-gradient-to-r from-[#0F2847] to-[#1E3A5F] text-white px-3 py-2 hover:from-[#0a1f3a] hover:to-[#0F2847] disabled:opacity-50"
        >
          {reranking ? <Loader2 size={11} className="animate-spin" /> : <Sparkles size={11} strokeWidth={1.5} />}
          Rerank with AI ({RERANK_COST} credits)
        </button>
      </div>

      {filtersOpen && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 border border-slate-200 bg-white p-4">
          <div>
            <div className="overline mb-1">Availability</div>
            <select data-testid="filter-availability" value={availability} onChange={(e) => setAvailability(e.target.value)} className="w-full px-2 py-1.5 border border-slate-300 text-sm">
              <option value="">Any</option>
              <option value="available">Available</option>
              <option value="selective">Selective</option>
              <option value="not_available">Not available</option>
            </select>
          </div>
          <div>
            <div className="overline mb-1">Country</div>
            <input data-testid="filter-country" value={country} onChange={(e) => setCountry(e.target.value)} placeholder="e.g. Germany" className="w-full px-2 py-1.5 border border-slate-300 text-sm" />
          </div>
          <div>
            <div className="overline mb-1">Institution</div>
            <input data-testid="filter-institution" value={institution} onChange={(e) => setInstitution(e.target.value)} placeholder="e.g. ETH" className="w-full px-2 py-1.5 border border-slate-300 text-sm" />
          </div>
        </div>
      )}

      {/* Layout: results + side widgets */}
      <div className="grid lg:grid-cols-[1fr_320px] gap-6">
        {/* Results */}
        <main className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="overline">
              {loading ? "Searching…" : `${results.length} match${results.length === 1 ? "" : "es"}`}
              {reranked && <span className="ml-2 text-amber-700"> · AI reranked</span>}
            </div>
            {results.length > 0 && (
              <Link to="/ai-usage" className="text-[10px] font-mono text-slate-400 hover:text-[#0F2847]">
                Track AI spend ↗
              </Link>
            )}
          </div>
          {loading && (
            <div className="flex items-center gap-2 py-4">
              <Spinner size={14} />
              <span className="text-sm text-slate-500">Loading matches…</span>
            </div>
          )}
          {!loading && results.length === 0 && (
            <EmptyState
              icon={<Users />}
              title="No matches yet"
              description="Try a broader role or clear filters."
              size="md"
              dashed={true}
            />
          )}
          {!loading && results.map((m) => (
            <MatchCard
              key={m.user.id + (reranked ? "-r" : "")}
              match={m}
              onInvite={() => setInviting(m)}
              onMessage={onMessage}
            />
          ))}
        </main>

        {/* Sidebar — reverse matches + analytics */}
        <aside className="space-y-5">
          <SidebarReverse reverse={reverse} />
          <SidebarAnalytics analytics={analytics} />
          <SidebarReputation />
        </aside>
      </div>

      {inviting && (
        <InviteModal
          target={inviting}
          onClose={() => setInviting(null)}
          defaultKind="collaboration"
        />
      )}
    </div>
    </DiscoveryLayout>
  );
}

function SidebarReverse({ reverse }) {
  if (!reverse) return <SectionLoading title="Looking for you" />;
  const exp = reverse.expertise_requests || [];
  const inv = reverse.invitations || [];
  return (
    <div className="border border-slate-200 bg-white p-4" data-testid="reverse-matches">
      <div className="flex items-center gap-2 mb-3">
        <TrendingUp size={12} strokeWidth={1.5} className="text-[#0F2847]" />
        <div className="overline">Looking for you</div>
      </div>
      {exp.length === 0 && inv.length === 0 && (
        <div className="text-xs text-slate-500">No matching requests right now. Set your expertise tags to surface more opportunities.</div>
      )}
      {inv.length > 0 && (
        <div className="mb-3">
          <div className="text-[10px] font-mono text-slate-400 mb-1">Invitations to you</div>
          {inv.slice(0, 3).map((r) => (
            <Link key={r.id} to={`/expertise/${r.id}`} className="block py-1.5 border-b border-slate-100 text-xs hover:text-[#0F2847]">
              <span className="overline text-amber-700 mr-1">{r.kind}</span> {r.title}
            </Link>
          ))}
        </div>
      )}
      {exp.length > 0 && (
        <div>
          <div className="text-[10px] font-mono text-slate-400 mb-1">Open requests matching you</div>
          {exp.slice(0, 5).map((r) => (
            <Link key={r.id} to={`/expertise/${r.id}`} className="block py-1.5 border-b border-slate-100 text-xs hover:text-[#0F2847]">
              <span className="overline text-[#0F2847] mr-1">{r.kind}</span> {r.title}
            </Link>
          ))}
        </div>
      )}
      <Link to="/expertise" className="text-[11px] font-mono text-[#0F2847] hover:underline mt-3 inline-block">
        See all expertise requests →
      </Link>
    </div>
  );
}

function SidebarAnalytics({ analytics }) {
  if (!analytics) return <SectionLoading title="Your network impact" />;
  const stats = [
    { label: "Invitations sent",     value: analytics.invitations_sent },
    { label: "Acceptances",          value: analytics.invitations_accepted },
    { label: "Reviews completed",    value: analytics.reviews_completed },
    { label: "Requests fulfilled",   value: analytics.expertise_requests_fulfilled },
  ];
  const rate = Math.round((analytics.collaboration_success_rate || 0) * 100);
  return (
    <div className="border border-slate-200 bg-white p-4" data-testid="marketplace-analytics">
      <div className="flex items-center gap-2 mb-3">
        <BarChart3 size={12} strokeWidth={1.5} className="text-[#0F2847]" />
        <div className="overline">Your network impact</div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {stats.map((s) => (
          <div key={s.label}>
            <div className="font-serif text-2xl text-slate-900">{s.value || 0}</div>
            <div className="text-[10px] font-mono text-slate-500">{s.label}</div>
          </div>
        ))}
      </div>
      <div className="mt-3">
        <div className="flex items-center justify-between text-[11px] font-mono">
          <span>Collaboration success</span>
          <span className="text-[#0F2847]">{rate}%</span>
        </div>
        <div className="h-1 bg-slate-100 mt-1 relative overflow-hidden">
          <div className="absolute inset-y-0 left-0 bg-[#0F2847]" style={{ width: `${rate}%` }} />
        </div>
      </div>
    </div>
  );
}

function SidebarReputation() {
  const [rep, setRep] = useState(null);
  const [syncing, setSyncing] = useState(false);
  useEffect(() => {
    api.get("/reputation/me").then(({ data }) => setRep(data)).catch(() => {});
  }, []);
  const syncOA = async () => {
    setSyncing(true);
    try {
      const { data } = await api.post("/reputation/sync-openalex");
      setRep(data.reputation);
      toast.success(`Synced OpenAlex: ${data.openalex?.works_count} works, ${data.openalex?.citations} citations`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "OpenAlex sync failed");
    } finally { setSyncing(false); }
  };
  if (!rep) return <SectionLoading title="Your reputation" />;
  return (
    <div className="border border-slate-200 bg-white p-4" data-testid="sidebar-reputation">
      <div className="flex items-center gap-2 mb-3">
        <Award size={12} strokeWidth={1.5} className="text-[#0F2847]" />
        <div className="overline">Your reputation</div>
      </div>
      <ReputationBadge reputation={rep} />
      <button
        data-testid="sync-openalex-btn"
        onClick={syncOA}
        disabled={syncing}
        className="mt-3 w-full text-[11px] inline-flex items-center justify-center gap-1.5 border border-slate-300 px-2 py-1.5 hover:border-[#0F2847]"
      >
        {syncing ? <Loader2 size={11} className="animate-spin" /> : <Sparkles size={11} strokeWidth={1.5} />}
        Sync OpenAlex citations
      </button>
      <div className="text-[10px] font-mono text-slate-400 mt-2">Add your ORCID in Settings for a precise match.</div>
    </div>
  );
}

function SectionLoading({ title }) {
  return (
    <div className="border border-slate-200 bg-white p-4">
      <div className="overline mb-3">{title}</div>
      <div className="flex items-center gap-2">
        <Spinner size={12} />
        <span className="text-xs text-slate-400">Loading…</span>
      </div>
    </div>
  );
}
