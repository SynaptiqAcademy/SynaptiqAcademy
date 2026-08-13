import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { Star, ShieldCheck, Tags } from "lucide-react";
import { NAVY, ACCENT, EMERALD } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Badge, Tag, TagGroup, MiniBar, Button, StatusDot, H1, H2, Caption, LoadingOverlay, ErrorState } from "@/components/ds";
import { fetchApi } from "@/lib/api";

const API = "/api/acad-market";

// ── Right rail — rating breakdown + specialties, real data already fetched ────
// for this provider (converted from the previous hand-built two-column grid) ──
function ProviderProfileSidebar({ summary, p, userId }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {summary && summary.count > 0 && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
            <Star size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Rating Breakdown</div>
          </div>
          <div style={{ fontFamily: "Georgia, serif", fontSize: 28, fontWeight: 700, color: "#0f172a" }}>{summary.overall}</div>
          <div style={{ display: "flex", gap: 2, margin: "4px 0 10px" }}>
            {[1, 2, 3, 4, 5].map((s) => <Star key={s} size={13} style={{ color: "#F59E0B" }} fill={s <= Math.round(summary.overall) ? "#F59E0B" : "none"} />)}
          </div>
          {Object.entries(summary.dimensions || {}).map(([dim, val]) => (
            <div key={dim} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <span style={{ fontSize: 11, color: "#64748B", textTransform: "capitalize" }}>{dim}</span>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <MiniBar value={val} max={5} color={ACCENT} style={{ width: 70 }} />
                <span style={{ fontSize: 11, fontWeight: 700, color: "#0f172a" }}>{val}</span>
              </div>
            </div>
          ))}
        </Card>
      )}

      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
          <Tags size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Specialties</div>
        </div>
        <TagGroup>
          {(p?.categories || []).map((c) => (
            <Tag key={c} size="sm">{c.replace(/_/g, " ")}</Tag>
          ))}
        </TagGroup>
        {p?.availability && (
          <div style={{ marginTop: 12, fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}>
            <StatusDot color={p.availability === "available" ? EMERALD : "#475569"} size={7} />
            <span style={{ fontWeight: 700, color: p.availability === "available" ? EMERALD : "#475569" }}>
              {p.availability === "available" ? "Available now" : "Busy"}
            </span>
          </div>
        )}
        <Link to={`/academic-marketplace/services?provider=${userId}`}>
          <Button as="span" size="sm" style={{ width: "100%", marginTop: 12 }}>
            View Services
          </Button>
        </Link>
      </Card>
    </div>
  );
}

export default function ProviderProfile() {
  const { id: userId } = useParams();
  const [portfolio, setPortfolio] = useState(null);
  const [ratings, setRatings] = useState({ results: [], total: 0 });
  const [summary, setSummary] = useState(null);
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchApi(`${API}/providers/${userId}/portfolio`).then(r => r.json()),
      fetchApi(`${API}/ratings/providers/${userId}?limit=5`).then(r => r.json()),
      fetchApi(`${API}/ratings/providers/${userId}/summary`).then(r => r.json()),
      fetchApi(`${API}/services?provider_user_id=${userId}&limit=6`).then(r => r.json()),
    ]).then(([port, rat, sum, svcs]) => {
      setPortfolio(port);
      setRatings(rat);
      setSummary(sum);
      setServices(svcs.results || []);
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
    <ResearchLayout
      title={p?.display_name || "Provider Profile"}
      subtitle={p?.headline}
      sidebar={<ProviderProfileSidebar summary={summary} p={p} userId={userId} />}
    >
        <div className="mb-2">
          <Link to="/academic-marketplace/providers" className="text-crimson-600 text-[13px] no-underline">← Back to Providers</Link>
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

        {/* Portfolio */}
        {portfolio.portfolio_items?.length > 0 && (
          <Card padding="lg" className="mb-5">
            <H2 className="mb-4" style={{ fontSize: "1.125rem" }}>Portfolio</H2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
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
    </ResearchLayout>
  );
}
