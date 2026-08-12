import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../lib/api";
import { ExternalLink, BookOpen, Globe, FileText } from "lucide-react";
import { SkeletonCard } from "@/components/ds/LoadingState";
import { Badge } from "@/components/ds/Badge";
import { Card } from "@/components/ds/Card";
import { Tag, TagGroup } from "@/components/ds/Tag";
import { ResearchLayout } from "@/layouts";

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
  return <Badge variant="neutral">Data: {labels[source] || source}</Badge>;
}

export default function JournalDetail() {
  const { id } = useParams();
  const [j, setJ] = useState(null);

  useEffect(() => { api.get(`/journals/${id}`).then((r) => setJ(r.data)).catch(() => setJ({error: true})); }, [id]);

  if (!j) return <ResearchLayout title="Journal"><SkeletonCard rows={4} /></ResearchLayout>;
  if (j.error) return (
    <ResearchLayout title="Journal not found">
      <div className="text-sm text-slate-500">Journal not found. <Link to="/journals" className="underline">Back to discovery</Link></div>
    </ResearchLayout>
  );

  const xid = j.external_ids || {};
  const oaLabel = j.open_access ? (j.oa_status || "Open access") : "Subscription / hybrid";

  return (
    <ResearchLayout title={j.title}>
      <div className="space-y-8">
        <Link to="/journals" className="text-sm text-slate-500 hover:text-slate-900">← All journals</Link>

        {/* Meta bar */}
        <div className="flex items-center gap-2 flex-wrap pb-6 border-b border-slate-200">
          <BookOpen size={16} strokeWidth={1.5} className="text-[#0F2847]" />
          <div className="overline text-[#0F2847]">{j.publisher || "Publisher unknown"}</div>
          <ProvenanceBadge source={j.source} />
          {j.quartile && (
            <Badge variant="default">{j.quartile}</Badge>
          )}
          {j.open_access && (
            <Badge variant="success">{oaLabel}</Badge>
          )}
          {(xid.issn_l || (xid.issns && xid.issns.length > 0) || j.country) && (
            <div className="w-full mt-2 text-sm text-slate-500 flex flex-wrap gap-3">
              {xid.issn_l && <span>ISSN-L: <span className="font-mono text-slate-700">{xid.issn_l}</span></span>}
              {xid.issns && xid.issns.length > 0 && (
                <span>ISSN: <span className="font-mono text-slate-700">{xid.issns.join(", ")}</span></span>
              )}
              {j.country && <span><Globe size={11} className="inline" /> {j.country}</span>}
            </div>
          )}
        </div>

      <div className="grid lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8 space-y-8">
          <section>
            <h2 className="overline mb-3">Subject coverage</h2>
            {(j.subjects && j.subjects.length > 0) ? (
              <TagGroup gap={8}>
                {j.subjects.map((s, i) => (
                  <Tag key={i}>{s}</Tag>
                ))}
              </TagGroup>
            ) : <div className="text-sm text-slate-500">No subjects indexed for this journal yet.</div>}
          </section>

          {j.scope_keywords && j.scope_keywords.length > 0 && (
            <section className="border-t border-slate-200 pt-6">
              <h2 className="overline mb-3">Topics covered</h2>
              <TagGroup gap={6}>
                {j.scope_keywords.map((t, i) => (
                  <Tag key={i} size="sm" className="font-mono">{t}</Tag>
                ))}
              </TagGroup>
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
          <Card padding="lg">
            <div className="overline mb-4">Impact metrics</div>
            <Metric label="Works published" value={(j.works_count || 0).toLocaleString()} />
            <Metric label="Total citations" value={(j.cited_by_count || 0).toLocaleString()} />
            <Metric label="h-index" value={j.h_index || "—"} />
            <Metric label="2-year citedness" value={j.mean_citedness_2yr?.toFixed(2) ?? "—"} sub="OpenAlex" />
            <Metric label="Popularity score" value={j.popularity_score?.toFixed(1) ?? "—"} sub="synthetic" />
          </Card>
          {j.quartile_source === "openalex_estimate" && (
            <div className="text-[11px] text-slate-500 leading-relaxed">
              Quartile is an OpenAlex-derived estimate from 2-year mean citedness. Scimago / JCR back-fills available where licensing permits.
            </div>
          )}
        </aside>
      </div>
      </div>
    </ResearchLayout>
  );
}
