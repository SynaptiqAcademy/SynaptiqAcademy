import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { ExternalLink, Coins, Globe, Calendar, Bookmark, BookmarkCheck, FilePlus, CheckCircle2 } from "lucide-react";
import { SkeletonCard } from "@/components/ds/LoadingState";
import { Badge } from "@/components/ds/Badge";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Tag, TagGroup } from "@/components/ds/Tag";

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
            <Badge variant="default">{g.funding_type}</Badge>
          )}
          {fmtAmount(g.funding_amount) && (
            <Badge variant="success">{fmtAmount(g.funding_amount)}</Badge>
          )}
          {g.source && (
            <Badge variant="neutral">Source: {g.source}</Badge>
          )}
        </div>
        <h1 className="font-serif text-5xl text-slate-900 mt-2 leading-tight">{g.title}</h1>
        <div className="mt-2 text-sm text-slate-500">{g.sponsor}</div>

        <div className="mt-4 flex items-center gap-3 flex-wrap">
          <Button
            onClick={toggleSave}
            variant="outline"
            size="sm"
          >
            {saved ? <BookmarkCheck size={12} strokeWidth={1.5} /> : <Bookmark size={12} strokeWidth={1.5} />}
            {saved ? "Saved" : "Save"}
          </Button>

          <Button
            onClick={startApplication}
            disabled={applying}
            variant={hasApplication ? "outline" : "primary"}
            size="sm"
            className={hasApplication ? "!border-emerald-600 !text-emerald-700 hover:!bg-emerald-50" : ""}
          >
            {hasApplication ? (
              <><CheckCircle2 size={12} strokeWidth={1.5} /> Open application ({g.user_application.status})</>
            ) : (
              <><FilePlus size={12} strokeWidth={1.5} /> {applying ? "Creating…" : "Start application"}</>
            )}
          </Button>
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
            <TagGroup gap={8}>
              {(g.research_areas || []).map((s, i) => (
                <Tag key={i}>{s}</Tag>
              ))}
            </TagGroup>
            {(!g.research_areas || g.research_areas.length === 0) && <span className="text-sm text-slate-500">—</span>}
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
              <TagGroup gap={6}>
                {g.keywords.map((k, i) => (
                  <Tag key={i} size="sm" className="font-mono">{k}</Tag>
                ))}
              </TagGroup>
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
          <Card padding="lg" className="space-y-3 text-sm">
            <div className="overline">Key facts</div>
            <div className="flex items-center justify-between"><span className="text-slate-500">Sponsor</span><span className="text-slate-900 text-right max-w-[60%] leading-snug">{g.sponsor || "—"}</span></div>
            {g.program && <div className="flex items-center justify-between"><span className="text-slate-500">Program</span><span className="text-slate-900 text-right">{g.program}</span></div>}
            {g.country && <div className="flex items-center justify-between"><span className="text-slate-500">Country</span><span className="text-slate-900 flex items-center gap-1"><Globe size={11} />{g.country}</span></div>}
            {g.open_date && <div className="flex items-center justify-between"><span className="text-slate-500">Opens</span><span className="text-slate-900 font-mono">{g.open_date}</span></div>}
            {g.deadline && <div className="flex items-center justify-between"><span className="text-slate-500">Deadline</span><span className="text-slate-900 font-mono flex items-center gap-1"><Calendar size={11} />{g.deadline}</span></div>}
            {fmtAmount(g.funding_amount) && <div className="flex items-center justify-between"><span className="text-slate-500">Amount</span><span className="text-emerald-700 font-medium">{fmtAmount(g.funding_amount)}</span></div>}
            {g.status && <div className="flex items-center justify-between"><span className="text-slate-500">Status</span><span className="text-slate-900">{g.status}</span></div>}
          </Card>

          {/* Matching hints */}
          {g.match_score != null && (
            <Card padding="md" className="border-emerald-200 bg-emerald-50/60">
              <div className="overline text-emerald-700 mb-1">Match score: {g.match_score}</div>
              <div className="text-xs text-emerald-700">{g.match_reason}</div>
              {g.eligibility_estimate && (
                <div className="text-xs text-emerald-600 font-mono mt-1">Eligibility: {g.eligibility_estimate}</div>
              )}
            </Card>
          )}
        </aside>
      </div>
    </div>
  );
}
