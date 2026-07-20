import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../lib/api";
import { ExternalLink, BookOpen, Globe, FileText } from "lucide-react";
import { NAVY } from "@/lib/tokens";
import { SkeletonCard } from "@/components/ds/LoadingState";

function Metric({ label, value, sub }) {
  return (
    <div className="flex items-baseline justify-between py-2 border-b border-slate-100 last:border-b-0">
      <div>
        <div className="text-sm text-slate-600">{label}</div>
        {sub && <div className="text-xs text-slate-400 font-mono">{sub}</div>}
      </div>
      <span className="font-serif text-2xl text-slate-900">{value ?? "—"}</span>
    </div>
  );
}

function ProvenanceBadge({ source }) {
  const labels = { openalex: "OpenAlex", doaj: "DOAJ", crossref: "Crossref", seed: "Curated seed" };
  return (
    <span className="overline border border-slate-200 bg-slate-50 text-slate-600 px-2 py-0.5">
      Data: {labels[source] || source}
    </span>
  );
}

export default function JournalDetail() {
  const { id } = useParams();
  const [j, setJ] = useState(null);

  useEffect(() => { api.get(`/journals/${id}`).then((r) => setJ(r.data)).catch(() => setJ({error: true})); }, [id]);

  if (!j) return <div className="p-6"><SkeletonCard rows={4} /></div>;
  if (j.error) return <div className="text-sm text-slate-500">Journal not found. <Link to="/journals" className="underline">Back to discovery</Link></div>;

  const xid = j.external_ids || {};
  const oaLabel = j.open_access ? (j.oa_status || "Open access") : "Subscription / hybrid";

  return (
    <div className="space-y-8">
      <Link to="/journals" className="text-sm text-slate-500 hover:text-slate-900">← All journals</Link>

      <header className="border-b border-slate-200 pb-6">
        <div className="flex items-center gap-2 mb-2">
          <BookOpen size={16} strokeWidth={1.5} className="text-[#0F2847]" />
          <div className="overline text-[#0F2847]">{j.publisher || "Publisher unknown"}</div>
          <ProvenanceBadge source={j.source} />
          {j.quartile && (
            <span className="overline border border-[#0F2847]/20 bg-[#0F2847]/5 text-[#0F2847] px-2 py-0.5">{j.quartile}</span>
          )}
          {j.open_access && (
            <span className="overline border border-emerald-300 bg-emerald-50 text-emerald-700 px-2 py-0.5">{oaLabel}</span>
          )}
        </div>
        <h1 className="font-serif text-5xl text-slate-900 mt-2 leading-tight">{j.title}</h1>
        <div className="mt-3 text-sm text-slate-500 flex flex-wrap gap-3">
          {xid.issn_l && <span>ISSN-L: <span className="font-mono text-slate-700">{xid.issn_l}</span></span>}
          {xid.issns && xid.issns.length > 0 && (
            <span>ISSN: <span className="font-mono text-slate-700">{xid.issns.join(", ")}</span></span>
          )}
          {j.country && <span><Globe size={11} className="inline" /> {j.country}</span>}
        </div>
      </header>

      <div className="grid lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8 space-y-8">
          <section>
            <h2 className="overline mb-3">Subject coverage</h2>
            {(j.subjects && j.subjects.length > 0) ? (
              <div className="flex flex-wrap gap-2">
                {j.subjects.map((s, i) => (
                  <span key={i} className="text-sm px-3 py-1 border border-slate-300 text-slate-700">{s}</span>
                ))}
              </div>
            ) : <div className="text-sm text-slate-500">No subjects indexed for this journal yet.</div>}
          </section>

          {j.scope_keywords && j.scope_keywords.length > 0 && (
            <section className="border-t border-slate-200 pt-6">
              <h2 className="overline mb-3">Topics covered</h2>
              <div className="flex flex-wrap gap-2">
                {j.scope_keywords.map((t, i) => (
                  <span key={i} className="text-xs font-mono px-2 py-1 bg-slate-100 text-slate-700">{t}</span>
                ))}
              </div>
            </section>
          )}

          <section className="border-t border-slate-200 pt-6 grid sm:grid-cols-2 gap-4 text-sm">
            <div className="border-l-2 border-[#0F2847] pl-3">
              <div className="overline">APC</div>
              <div className="text-slate-900 mt-1">{j.apc_usd ? `${j.apc_usd.toLocaleString()} USD` : (j.open_access ? "Diamond OA / no APC" : "Subscription model")}</div>
            </div>
            <div className="border-l-2 border-[#0F2847] pl-3">
              <div className="overline">Open access</div>
              <div className="text-slate-900 mt-1">{oaLabel}</div>
            </div>
            <div className="border-l-2 border-[#0F2847] pl-3">
              <div className="overline">Review time</div>
              <div className="text-slate-900 mt-1">{j.review_time_weeks ? `${j.review_time_weeks} weeks (avg)` : "Not published"}</div>
            </div>
            <div className="border-l-2 border-[#0F2847] pl-3">
              <div className="overline">Acceptance rate</div>
              <div className="text-slate-900 mt-1">{j.acceptance_rate ? `${j.acceptance_rate}%` : "Not published"}</div>
            </div>
          </section>

          {(j.homepage_url || j.submission_url) && (
            <section className="border-t border-slate-200 pt-6 flex flex-wrap gap-4">
              {j.homepage_url && (
                <a href={j.homepage_url} target="_blank" rel="noreferrer"
                   className="inline-flex items-center gap-2 text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">
                  Visit homepage <ExternalLink size={14} strokeWidth={1.5} />
                </a>
              )}
              {j.submission_url && (
                <a href={j.submission_url} target="_blank" rel="noreferrer"
                   className="inline-flex items-center gap-2 text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">
                  Submission guidelines <ExternalLink size={14} strokeWidth={1.5} />
                </a>
              )}
            </section>
          )}
        </div>

        <aside className="lg:col-span-4 space-y-6">
          <div className="border border-slate-200 bg-white p-6">
            <div className="overline mb-4">Impact metrics</div>
            <Metric label="Works published" value={(j.works_count || 0).toLocaleString()} />
            <Metric label="Total citations" value={(j.cited_by_count || 0).toLocaleString()} />
            <Metric label="h-index" value={j.h_index || "—"} />
            <Metric label="2-year citedness" value={j.mean_citedness_2yr?.toFixed(2) ?? "—"} sub="OpenAlex" />
            <Metric label="Popularity score" value={j.popularity_score?.toFixed(1) ?? "—"} sub="synthetic" />
          </div>
          {j.quartile_source === "openalex_estimate" && (
            <div className="text-[11px] text-slate-500 leading-relaxed">
              Quartile is an OpenAlex-derived estimate from 2-year mean citedness. Scimago / JCR back-fills available where licensing permits.
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
