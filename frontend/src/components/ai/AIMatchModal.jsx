/**
 * AI Match modal — used for journal, conference, grant, and reviewer matching.
 *
 * Props:
 *   open, onClose
 *   kind: "journal" | "conference" | "grant" | "reviewer"
 *   manuscriptId (or for grants: optional)
 *   creditCost: number   (for label)
 *
 * On open, fires POST /api/matching/<kind> with the manuscript id, shows a
 * skeleton while waiting, then renders ranked cards with score + rationale +
 * concerns + per-kind action buttons.
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../../lib/api";
import { toast } from "sonner";
import { userTypeLabel } from "../../lib/userTypes";
import { NAVY } from "@/lib/tokens";
import {
  Sparkles, X, BookOpen, CalendarDays, Coins, UserPlus, ExternalLink,
  ShieldAlert, Loader2, Plus,
} from "lucide-react";

const KIND_META = {
  journal:    { label: "AI Journal Match",    endpoint: "/matching/journal",    cost: 10, icon: BookOpen },
  conference: { label: "AI Conference Match", endpoint: "/matching/conference", cost: 5,  icon: CalendarDays },
  grant:      { label: "AI Grant Match",      endpoint: "/matching/grant",      cost: 10, icon: Coins },
  reviewer:   { label: "AI Reviewer Match",   endpoint: "/matching/reviewer",   cost: 10, icon: UserPlus },
};

function ScoreRing({ score }) {
  const c = 2 * Math.PI * 18;
  const off = c - (Math.max(0, Math.min(100, score)) / 100) * c;
  const tone = score >= 80 ? "#15803d" : score >= 60 ? "#0F2847" : score >= 40 ? "#b45309" : "#6b7280";
  return (
    <div className="relative h-12 w-12">
      <svg viewBox="0 0 40 40" className="-rotate-90 h-12 w-12">
        <circle cx="20" cy="20" r="18" stroke="#E2E8F0" strokeWidth="3" fill="none"/>
        <circle cx="20" cy="20" r="18" stroke={tone} strokeWidth="3" fill="none" strokeDasharray={c} strokeDashoffset={off} strokeLinecap="round"/>
      </svg>
      <div className="absolute inset-0 flex items-center justify-center text-xs font-serif text-slate-900">{score}</div>
    </div>
  );
}

function JournalCard({ r, manuscriptId }) {
  const j = r.journal;
  const add = async () => {
    try {
      await api.post("/publication-hub/submissions", { manuscript_id: manuscriptId, venue_kind: "journal", venue_id: j.id, stage: "selected" });
      toast.success("Added to Publication Hub");
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };
  return (
    <div className="border border-slate-200 bg-white p-4">
      <div className="flex items-start gap-4">
        <ScoreRing score={r.score} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            {j.quartile && <span className="overline border border-[#0F2847]/20 bg-[#0F2847]/5 text-[#0F2847] px-1.5 py-0.5">{j.quartile}</span>}
            {j.open_access && <span className="overline border border-emerald-200 bg-emerald-50 text-emerald-700 px-1.5 py-0.5">OA</span>}
            {j.apc_usd != null && <span className="text-[10px] font-mono text-slate-500">APC ${j.apc_usd?.toLocaleString?.() || j.apc_usd}</span>}
          </div>
          <Link to={`/journals/${j.id}`} className="font-serif text-lg text-slate-900 hover:text-[#0F2847]">{j.title}</Link>
          <div className="text-xs text-slate-500 mt-0.5">{j.publisher}</div>
          <p className="text-xs text-slate-700 mt-2 leading-relaxed">{r.rationale}</p>
          {r.concerns && <p className="text-xs text-amber-700 mt-1"><ShieldAlert size={10} className="inline mr-1" strokeWidth={1.5}/> {r.concerns}</p>}
        </div>
      </div>
      <div className="mt-3 flex items-center justify-end gap-2">
        <Link to={`/journals/${j.id}`} className="text-xs text-slate-500 hover:underline">View profile</Link>
        <button onClick={add} className="text-xs bg-[#0F2847] text-white px-3 py-1 hover:bg-slate-800 inline-flex items-center gap-1">
          <Plus size={11} strokeWidth={1.5}/> Add to Pub Hub
        </button>
      </div>
    </div>
  );
}

function ConferenceCard({ r, manuscriptId }) {
  const c = r.conference;
  const add = async () => {
    try {
      await api.post("/publication-hub/submissions", { manuscript_id: manuscriptId, venue_kind: "conference", venue_id: c.id, stage: "selected" });
      toast.success("Added to Publication Hub");
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };
  return (
    <div className="border border-slate-200 bg-white p-4">
      <div className="flex items-start gap-4">
        <ScoreRing score={r.score} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            {c.acronym && <span className="overline border border-[#0F2847]/20 bg-[#0F2847]/5 text-[#0F2847] px-1.5 py-0.5">{c.acronym}</span>}
            {c.rank && <span className="overline border border-purple-200 bg-purple-50 text-purple-700 px-1.5 py-0.5">CORE {c.rank}</span>}
            {c.submission_deadline && <span className="text-[10px] font-mono text-amber-700">Due {c.submission_deadline}</span>}
          </div>
          <Link to={`/conferences/${c.id}`} className="font-serif text-lg text-slate-900 hover:text-[#0F2847]">{c.name}</Link>
          {c.location && <div className="text-xs text-slate-500 mt-0.5">{c.location}</div>}
          <p className="text-xs text-slate-700 mt-2 leading-relaxed">{r.rationale}</p>
          {r.concerns && <p className="text-xs text-amber-700 mt-1"><ShieldAlert size={10} className="inline mr-1" strokeWidth={1.5}/> {r.concerns}</p>}
        </div>
      </div>
      <div className="mt-3 flex items-center justify-end gap-2">
        <Link to={`/conferences/${c.id}`} className="text-xs text-slate-500 hover:underline">View</Link>
        <button onClick={add} className="text-xs bg-[#0F2847] text-white px-3 py-1 hover:bg-slate-800 inline-flex items-center gap-1">
          <Plus size={11} strokeWidth={1.5}/> Add to Pub Hub
        </button>
      </div>
    </div>
  );
}

function GrantCard({ r }) {
  const g = r.grant;
  const fa = g.funding_amount || {};
  const save = async () => {
    try { await api.post(`/grants/${g.id}/save`); toast.success("Grant saved"); }
    catch (e) { toast.error("Failed"); }
  };
  return (
    <div className="border border-slate-200 bg-white p-4">
      <div className="flex items-start gap-4">
        <ScoreRing score={r.score} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            {g.funding_type && <span className="overline border border-[#0F2847]/20 bg-[#0F2847]/5 text-[#0F2847] px-1.5 py-0.5">{g.funding_type}</span>}
            {fa.amount && <span className="overline border border-emerald-200 bg-emerald-50 text-emerald-700 px-1.5 py-0.5">{(fa.amount/1000).toFixed(0)}K {fa.currency}</span>}
            {r.eligibility_match && <span className={`overline border px-1.5 py-0.5 ${r.eligibility_match==='high'?'border-emerald-300 bg-emerald-50 text-emerald-700':r.eligibility_match==='low'?'border-red-300 bg-red-50 text-red-700':'border-amber-300 bg-amber-50 text-amber-700'}`}>elig: {r.eligibility_match}</span>}
            {g.deadline && <span className="text-[10px] font-mono text-amber-700">Due {g.deadline}</span>}
          </div>
          <Link to={`/grants/${g.id}`} className="font-serif text-lg text-slate-900 hover:text-[#0F2847]">{g.title}</Link>
          <div className="text-xs text-slate-500 mt-0.5">{g.sponsor}</div>
          <p className="text-xs text-slate-700 mt-2 leading-relaxed">{r.rationale}</p>
          {r.concerns && <p className="text-xs text-amber-700 mt-1"><ShieldAlert size={10} className="inline mr-1" strokeWidth={1.5}/> {r.concerns}</p>}
        </div>
      </div>
      <div className="mt-3 flex items-center justify-end gap-2">
        <Link to={`/grants/${g.id}`} className="text-xs text-slate-500 hover:underline">View</Link>
        <button onClick={save} className="text-xs bg-[#0F2847] text-white px-3 py-1 hover:bg-slate-800 inline-flex items-center gap-1">
          <Plus size={11} strokeWidth={1.5}/> Save
        </button>
      </div>
    </div>
  );
}

function ReviewerCard({ r, manuscriptId }) {
  const u = r.reviewer;
  const invite = async () => {
    try {
      await api.post(`/manuscripts/${manuscriptId}/review-requests`, { reviewer_id: u.id, note: "Suggested by AI match" });
      toast.success("Review requested");
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };
  return (
    <div className="border border-slate-200 bg-white p-4">
      <div className="flex items-start gap-4">
        <ScoreRing score={r.score} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            {r.collaboration_risk === "high" && <span className="overline border border-red-300 bg-red-50 text-red-700 px-1.5 py-0.5">Prior collab</span>}
            {(r.expertise_areas || []).slice(0, 3).map((a, i) => (
              <span key={i} className="text-[10px] font-mono text-slate-600 border border-slate-200 px-1.5 py-0.5">{a}</span>
            ))}
          </div>
          <Link to={`/profile/${u.id}`} className="font-serif text-lg text-slate-900 hover:text-[#0F2847]">{u.full_name}</Link>
          <div className="text-xs text-slate-500 mt-0.5">
            {[userTypeLabel(u), u.institution].filter(Boolean).join(" · ")}
          </div>
          <div className="text-[11px] text-slate-500 mt-1 font-mono">{u.publications_count || 0} pubs {u.h_index ? `· h=${u.h_index}` : ""}</div>
          <p className="text-xs text-slate-700 mt-2 leading-relaxed">{r.rationale}</p>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-end gap-2">
        <button onClick={invite} className="text-xs bg-[#0F2847] text-white px-3 py-1 hover:bg-slate-800 inline-flex items-center gap-1">
          <UserPlus size={11} strokeWidth={1.5}/> Request review
        </button>
      </div>
    </div>
  );
}

export default function AIMatchModal({ open, onClose, kind, manuscriptId, projectId, query }) {
  const meta = KIND_META[kind];
  const Icon = meta?.icon || Sparkles;
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true); setError(null); setData(null);
    const body = kind === "grant"
      ? { manuscript_id: manuscriptId, project_id: projectId, query, top_n: 6 }
      : { manuscript_id: manuscriptId, top_n: 6 };
    api.post(meta.endpoint, body)
      .then(({ data }) => setData(data))
      .catch((e) => setError(e?.response?.data?.detail || "Match failed"))
      .finally(() => setLoading(false));
  }, [open, kind]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 flex items-start justify-center pt-12 px-4 overflow-y-auto" onClick={onClose}>
      <div role="dialog" aria-modal="true" data-testid="ai-match-modal" className="bg-slate-50 w-full max-w-3xl border border-slate-200 mb-16" onClick={(e) => e.stopPropagation()}>
        <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Icon size={18} strokeWidth={1.5} className="text-[#0F2847]"/>
            <div>
              <div className="overline text-[#0F2847]">SYNAPTIQ AI · {meta.cost} credits</div>
              <h3 className="font-serif text-xl text-slate-900">{meta.label}</h3>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-900"><X size={18} strokeWidth={1.5}/></button>
        </div>
        <div className="p-5 space-y-3">
          {loading && (
            <div className="flex flex-col items-center gap-3 py-16 text-slate-500 text-sm">
              <Loader2 size={20} className="animate-spin text-[#0F2847]"/>
              Analysing the manuscript and ranking candidates…
            </div>
          )}
          {error && (
            <div className="border border-red-200 bg-red-50 text-red-800 p-4 text-sm">{error}</div>
          )}
          {data && (
            <>
              <div className="text-xs text-slate-500 font-mono">
                {data.credits_consumed} credits · {(data.latency_ms / 1000).toFixed(1)}s · {data.recommendations.length} recommendations
              </div>
              {data.recommendations.length === 0 && <div className="text-sm text-slate-500">No matches found.</div>}
              {kind === "journal" && data.recommendations.map((r) => <JournalCard key={r.journal.id} r={r} manuscriptId={manuscriptId}/>)}
              {kind === "conference" && data.recommendations.map((r) => <ConferenceCard key={r.conference.id} r={r} manuscriptId={manuscriptId}/>)}
              {kind === "grant" && data.recommendations.map((r) => <GrantCard key={r.grant.id} r={r}/>)}
              {kind === "reviewer" && data.recommendations.map((r) => <ReviewerCard key={r.reviewer.id} r={r} manuscriptId={manuscriptId}/>)}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
