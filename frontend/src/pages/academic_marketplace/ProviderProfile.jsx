import React, { useState, useEffect } from "react";
import { Star, ShieldCheck } from "lucide-react";
import { ACCENT, EMERALD } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Badge, Tag, TagGroup, MiniBar, Button, StatusDot, H1, H2, H3, Caption, LoadingOverlay, ErrorState } from "@/components/ds";

const API = "/api/acad-market";

export default function ProviderProfile() {
  const userId = window.location.pathname.split("/").pop();
  const [portfolio, setPortfolio] = useState(null);
  const [ratings, setRatings] = useState({ results: [], total: 0 });
  const [summary, setSummary] = useState(null);
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/providers/${userId}/portfolio`).then(r => r.json()),
      fetch(`${API}/ratings/providers/${userId}?limit=5`).then(r => r.json()),
      fetch(`${API}/ratings/providers/${userId}/summary`).then(r => r.json()),
      fetch(`${API}/services?limit=6`).then(r => r.json()),
    ]).then(([port, rat, sum, svcs]) => {
      setPortfolio(port);
      setRatings(rat);
      setSummary(sum);
      const filtered = (svcs.results || []).filter(s => s.provider_user_id === userId);
      setServices(filtered);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [userId]);

  if (loading) return <LoadingOverlay text="Loading..." />;
  if (!portfolio || portfolio.error) return <ErrorState type="not_found" message="Provider not found." />;

  const p = portfolio.provider;

  const verLabel = (lvl) => {
    if (lvl >= 5) return { label: "Elite", color: "#7C3AED" };
    if (lvl >= 4) return { label: "Expert Verified", color: EMERALD };
    if (lvl >= 3) return { label: "Institution Verified", color: ACCENT };
    if (lvl >= 2) return { label: "ID Verified", color: "#0891B2" };
    return null;
  };
  const ver = verLabel(p?.verification_level);

  return (
    <ResearchLayout title={p?.display_name || "Provider Profile"} subtitle={p?.headline}>
        <div className="mb-2">
          <a href="/academic-marketplace/providers" className="text-crimson-600 text-[13px] no-underline">← Back to Providers</a>
        </div>

        {/* Header */}
        <Card padding="xl" className="mb-5">
          <div className="flex gap-5 items-start">
            <div className="w-[72px] h-[72px] rounded-full flex items-center justify-center shrink-0" style={{ background: ACCENT + "22" }}>
              <span className="text-[28px] font-bold text-crimson-600">{(p?.display_name || "?")[0]}</span>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 flex-wrap mb-1.5">
                <H1 as="h1" style={{ fontSize: "1.375rem" }}>{p?.display_name}</H1>
                {ver && (
                  <Badge color={ver.color}>
                    <ShieldCheck size={11} /> {ver.label}
                  </Badge>
                )}
              </div>
              <div className="text-slate-600 text-[15px] mb-2.5">{p?.headline}</div>
              <div className="flex gap-5 flex-wrap">
                <div className="flex items-center gap-1">
                  <Star size={14} className="text-amber-500" fill="#F59E0B" />
                  <span className="font-semibold text-navy-700">{p?.average_rating?.toFixed(1)}</span>
                  <Caption>({p?.rating_count} reviews)</Caption>
                </div>
                <Caption>{p?.completed_orders} orders completed</Caption>
                <Caption>{p?.success_rate?.toFixed(0)}% success rate</Caption>
                {p?.country && <Caption>{p.country}</Caption>}
              </div>
            </div>
          </div>
          {p?.bio && (
            <div className="mt-4 pt-4 border-t border-hairline text-slate-600 leading-relaxed">
              {p.bio}
            </div>
          )}
        </Card>

        <div className="grid grid-cols-[1fr_320px] gap-5">
          <div>
            {/* Portfolio */}
            {portfolio.portfolio_items?.length > 0 && (
              <Card padding="lg" className="mb-5">
                <H2 className="mb-4" style={{ fontSize: "1.125rem" }}>Portfolio</H2>
                <div className="grid grid-cols-2 gap-3">
                  {portfolio.portfolio_items.map((item, i) => (
                    <div key={i} className="border border-hairline rounded-md p-4">
                      <div className="text-sm font-semibold text-navy-700 mb-1.5">{item.title}</div>
                      <div className="text-[13px] text-slate-600 leading-normal">{item.description?.slice(0, 100)}</div>
                      {item.link && (
                        <a href={item.link} target="_blank" rel="noreferrer" className="text-xs text-crimson-600 no-underline mt-2 block">View →</a>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Reviews */}
            {ratings.results?.length > 0 && (
              <Card padding="lg" className="mb-5">
                <H2 className="mb-4" style={{ fontSize: "1.125rem" }}>Reviews</H2>
                {ratings.results.map((r, i) => (
                  <div
                    key={i}
                    className={`mb-4 pb-4 ${i < ratings.results.length - 1 ? "border-b border-hairline" : ""}`}
                  >
                    <div className="flex items-center gap-2 mb-1.5">
                      <div className="flex gap-0.5">
                        {[1,2,3,4,5].map(s => <Star key={s} size={12} className="text-amber-500" fill={s <= r.overall ? "#F59E0B" : "none"} />)}
                      </div>
                      <span className="text-[13px] font-semibold text-navy-700">{r.buyer_name || "Verified Buyer"}</span>
                    </div>
                    <p className="text-sm text-slate-600 leading-relaxed m-0">{r.review_text}</p>
                    {r.provider_response && (
                      <div className="bg-[#F4F6FA] rounded-md p-2.5 mt-2 text-[13px] text-slate-600">
                        <strong className="text-navy-700">Provider response: </strong>{r.provider_response}
                      </div>
                    )}
                  </div>
                ))}
              </Card>
            )}
          </div>

          {/* Sidebar */}
          <div>
            {summary && summary.count > 0 && (
              <Card padding="md" className="mb-4">
                <H3 className="mb-3">Rating Breakdown</H3>
                <div className="text-4xl font-extrabold text-navy-700 mb-1">{summary.overall}</div>
                <div className="flex gap-0.5 mb-3">
                  {[1,2,3,4,5].map(s => <Star key={s} size={14} className="text-amber-500" fill={s <= Math.round(summary.overall) ? "#F59E0B" : "none"} />)}
                </div>
                {Object.entries(summary.dimensions || {}).map(([dim, val]) => (
                  <div key={dim} className="flex justify-between items-center mb-2">
                    <Caption className="capitalize">{dim}</Caption>
                    <div className="flex items-center gap-1.5">
                      <MiniBar value={val} max={5} color={ACCENT} style={{ width: 80 }} />
                      <span className="text-xs font-semibold text-navy-700">{val}</span>
                    </div>
                  </div>
                ))}
              </Card>
            )}

            <Card padding="md">
              <H3 className="mb-3">Specialties</H3>
              <TagGroup>
                {(p?.categories || []).map(c => (
                  <Tag key={c} size="sm">
                    {c.replace(/_/g, " ")}
                  </Tag>
                ))}
              </TagGroup>
              {p?.availability && (
                <div className="mt-4 text-sm flex items-center gap-1.5">
                  <StatusDot color={p.availability === "available" ? EMERALD : "#475569"} size={7} />
                  <span className="font-semibold" style={{ color: p.availability === "available" ? EMERALD : "#475569" }}>
                    {p.availability === "available" ? "Available now" : "Busy"}
                  </span>
                </div>
              )}
              <Button as="a" href={`/academic-marketplace/services?provider=${userId}`} className="w-full mt-4">
                View Services
              </Button>
            </Card>
          </div>
        </div>
    </ResearchLayout>
  );
}
