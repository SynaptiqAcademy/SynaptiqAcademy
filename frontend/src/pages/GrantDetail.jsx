import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { ExternalLink, Coins, Globe, Calendar, Bookmark, BookmarkCheck, FilePlus, CheckCircle2 } from "lucide-react";
import { NAVY } from "@/lib/tokens";
import { SkeletonCard } from "@/components/ds/LoadingState";

const fmtAmount = (fa) => {
  if (!fa || !fa.amount) return null;
  const a = parseFloat(fa.amount);
  const cur = fa.currency || "";
  if (a >= 1_000_000) return `${(a / 1_000_000).toFixed(1)}M ${cur}`.trim();
  if (a >= 1_000) return `${(a / 1_000).toFixed(0)}K ${cur}`.trim();
  return `${a} ${cur}`.trim();
};

export default function GrantDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [g, setG] = useState(null);
  const [saved, setSaved] = useState(false);
  const [applying, setApplying] = useState(false);

  useEffect(() => {
    api.get(`/grants/${id}`)
      .then((r) => {
        setG(r.data);
        setSaved(r.data.is_saved || false);
      })
      .catch(() => setG({ error: true }));
  }, [id]);

  const toggleSave = async () => {
    try {
      if (saved) { await api.post(`/grants/${id}/unsave`); setSaved(false); }
      else { await api.post(`/grants/${id}/save`); setSaved(true); }
    } catch {}
  };

  const startApplication = async () => {
    // If user already has an application, go there
    if (g?.user_application?.id) {
      navigate(`/grant-applications/${g.user_application.id}`);
      return;
    }
    setApplying(true);
    try {
      const { data } = await api.post("/grant-applications", { grant_id: id });
      toast.success("Application workspace created");
      navigate(`/grant-applications/${data.id}`);
    } catch (e) {
      const msg = e?.response?.data?.detail;
      if (msg?.includes("already have")) {
        toast.info("Redirecting to your existing application…");
        // Try to fetch it
        const apps = await api.get(`/grant-applications?grant_id=${id}`).catch(() => ({ data: [] }));
        const existing = (apps.data || []).find((a) => !["withdrawn", "closed"].includes(a.status));
        if (existing) navigate(`/grant-applications/${existing.id}`);
      } else {
        toast.error(msg || "Failed to start application");
      }
    } finally {
      setApplying(false);
    }
  };

  if (!g) return <div className="p-6"><SkeletonCard rows={4} /></div>;
  if (g.error) return <div className="text-sm text-slate-500">Grant not found. <Link to="/grants" className="underline">Back</Link></div>;

  const hasApplication = !!g.user_application;

  return (
    <div className="space-y-8">
      <Link to="/grants" className="text-sm text-slate-500 hover:text-slate-900">← All grants</Link>

      <header className="border-b border-slate-200 pb-6">
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          <Coins size={16} strokeWidth={1.5} className="text-[#0F2847]" />
          {g.funding_type && (
            <span className="overline border border-[#0F2847]/20 bg-[#0F2847]/5 text-[#0F2847] px-2 py-0.5">{g.funding_type}</span>
          )}
          {fmtAmount(g.funding_amount) && (
            <span className="overline border border-emerald-300 bg-emerald-50 text-emerald-700 px-2 py-0.5">{fmtAmount(g.funding_amount)}</span>
          )}
          {g.source && (
            <span className="overline border border-slate-200 bg-slate-50 text-slate-600 px-2 py-0.5">
              Source: {g.source}
            </span>
          )}
        </div>
        <h1 className="font-serif text-5xl text-slate-900 mt-2 leading-tight">{g.title}</h1>
        <div className="mt-2 text-sm text-slate-500">{g.sponsor}</div>

        <div className="mt-4 flex items-center gap-3 flex-wrap">
          <button
            onClick={toggleSave}
            className="inline-flex items-center gap-2 text-xs border border-[#0F2847] text-[#0F2847] px-3 py-1.5 hover:bg-[#0F2847] hover:text-white transition-colors"
          >
            {saved ? <BookmarkCheck size={12} strokeWidth={1.5} /> : <Bookmark size={12} strokeWidth={1.5} />}
            {saved ? "Saved" : "Save"}
          </button>

          <button
            onClick={startApplication}
            disabled={applying}
            className={`inline-flex items-center gap-2 text-xs px-4 py-1.5 transition-colors disabled:opacity-50 ${
              hasApplication
                ? "border border-emerald-600 text-emerald-700 hover:bg-emerald-50"
                : "bg-[#0F2847] text-white hover:bg-slate-800"
            }`}
          >
            {hasApplication ? (
              <><CheckCircle2 size={12} strokeWidth={1.5} /> Open application ({g.user_application.status})</>
            ) : (
              <><FilePlus size={12} strokeWidth={1.5} /> {applying ? "Creating…" : "Start application"}</>
            )}
          </button>
        </div>
      </header>

      <div className="grid lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8 space-y-8">
          {g.abstract_text && (
            <section>
              <h2 className="overline mb-3">Abstract</h2>
              <p className="text-slate-700 leading-relaxed whitespace-pre-wrap">{g.abstract_text}</p>
            </section>
          )}
          {g.summary && (
            <section>
              <h2 className="overline mb-3">Summary</h2>
              <p className="text-slate-700 leading-relaxed">{g.summary}</p>
            </section>
          )}
          <section className="border-t border-slate-200 pt-6">
            <h2 className="overline mb-3">Research areas</h2>
            <div className="flex flex-wrap gap-2">
              {(g.research_areas || []).map((s, i) => (
                <span key={i} className="text-sm px-3 py-1 border border-slate-300 text-slate-700">{s}</span>
              ))}
              {(!g.research_areas || g.research_areas.length === 0) && <span className="text-sm text-slate-500">—</span>}
            </div>
          </section>
          {g.eligibility && (
            <section className="border-t border-slate-200 pt-6">
              <h2 className="overline mb-3">Eligibility</h2>
              <p className="text-slate-700 whitespace-pre-wrap">{g.eligibility}</p>
            </section>
          )}
          {(g.keywords || []).length > 0 && (
            <section className="border-t border-slate-200 pt-6">
              <h2 className="overline mb-3">Keywords</h2>
              <div className="flex flex-wrap gap-1.5">
                {g.keywords.map((k, i) => (
                  <span key={i} className="text-xs font-mono px-2 py-0.5 border border-slate-200 text-slate-600">{k}</span>
                ))}
              </div>
            </section>
          )}
          {g.url && (
            <section className="border-t border-slate-200 pt-6">
              <a href={g.url} target="_blank" rel="noreferrer"
                 className="inline-flex items-center gap-2 text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">
                Visit official source <ExternalLink size={14} strokeWidth={1.5} />
              </a>
            </section>
          )}
        </div>

        <aside className="lg:col-span-4 space-y-4">
          <div className="border border-slate-200 bg-white p-6 space-y-3 text-sm">
            <div className="overline">Key facts</div>
            <div className="flex items-center justify-between"><span className="text-slate-500">Sponsor</span><span className="text-slate-900 text-right max-w-[60%] leading-snug">{g.sponsor || "—"}</span></div>
            {g.program && <div className="flex items-center justify-between"><span className="text-slate-500">Program</span><span className="text-slate-900 text-right">{g.program}</span></div>}
            {g.country && <div className="flex items-center justify-between"><span className="text-slate-500">Country</span><span className="text-slate-900 flex items-center gap-1"><Globe size={11} />{g.country}</span></div>}
            {g.open_date && <div className="flex items-center justify-between"><span className="text-slate-500">Opens</span><span className="text-slate-900 font-mono">{g.open_date}</span></div>}
            {g.deadline && <div className="flex items-center justify-between"><span className="text-slate-500">Deadline</span><span className="text-slate-900 font-mono flex items-center gap-1"><Calendar size={11} />{g.deadline}</span></div>}
            {fmtAmount(g.funding_amount) && <div className="flex items-center justify-between"><span className="text-slate-500">Amount</span><span className="text-emerald-700 font-medium">{fmtAmount(g.funding_amount)}</span></div>}
            {g.status && <div className="flex items-center justify-between"><span className="text-slate-500">Status</span><span className="text-slate-900">{g.status}</span></div>}
          </div>

          {/* Matching hints */}
          {g.match_score != null && (
            <div className="border border-emerald-200 bg-emerald-50/60 p-4">
              <div className="overline text-emerald-700 mb-1">Match score: {g.match_score}</div>
              <div className="text-xs text-emerald-700">{g.match_reason}</div>
              {g.eligibility_estimate && (
                <div className="text-xs text-emerald-600 font-mono mt-1">Eligibility: {g.eligibility_estimate}</div>
              )}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
