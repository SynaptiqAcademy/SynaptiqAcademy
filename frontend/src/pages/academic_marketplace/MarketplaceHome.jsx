import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ShoppingBag, Star, TrendingUp, Zap, ChevronRight, Award } from "lucide-react";
import { NAVY, ACCENT, EMERALD } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Grid, SearchBar, Button, H2, Caption } from "@/components/ds";
import { fetchApi } from "@/lib/api";

// ── Right rail — top trending service + top featured expert, real data ────────
// already fetched by this page (never a new request just for the sidebar) ─────
function MarketplaceHomeSidebar({ trending, featured }) {
  const topTrending = trending?.[0];
  const topFeatured = featured?.[0];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {topTrending && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <TrendingUp size={14} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Trending Now</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {trending.slice(0, 3).map((svc) => (
              <Link key={svc.id} to={`/academic-marketplace/services/${svc.id}`} style={{ textDecoration: "none" }}>
                <div style={{ fontSize: 12.5, fontWeight: 600, color: "#0f172a", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{svc.title}</div>
                <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 1 }}>
                  <Star size={9} style={{ color: "#F59E0B" }} fill="#F59E0B" />
                  <span style={{ fontSize: 11, color: "#94A3B8" }}>{svc.average_rating?.toFixed(1) || "New"}</span>
                  {svc.recent_orders > 0 && (
                    <span style={{ fontSize: 11, color: EMERALD }}>· {svc.recent_orders} recent orders</span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </Card>
      )}

      {topFeatured && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
            <Award size={14} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Featured Expert</div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
            <div className="w-9 h-9 rounded-full flex items-center justify-center shrink-0" style={{ background: ACCENT + "22" }}>
              <span className="text-sm font-bold text-crimson-600">{(topFeatured.display_name || "?")[0]}</span>
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", fontFamily: "Georgia, serif" }}>{topFeatured.display_name}</div>
              <div style={{ fontSize: 11, color: "#64748B", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{topFeatured.headline}</div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 8 }}>
            <Star size={10} style={{ color: "#F59E0B" }} fill="#F59E0B" />
            <span style={{ fontSize: 11, color: "#64748B" }}>{topFeatured.average_rating?.toFixed(1)} ({topFeatured.completed_orders} orders)</span>
          </div>
          <Link to={`/academic-marketplace/providers/${topFeatured.user_id}`}>
            <Button as="span" size="sm" variant="ghost" style={{ width: "100%", marginTop: 10 }}>
              View profile
            </Button>
          </Link>
        </Card>
      )}
    </div>
  );
}

const API = "/api/acad-market";

export default function MarketplaceHome() {
  const navigate = useNavigate();
  const [featured, setFeatured] = useState([]);
  const [trending, setTrending] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchApi(`${API}/featured-providers`).then(r => r.json()),
      fetchApi(`${API}/trending`).then(r => r.json()),
    ]).then(([fp, tr]) => {
      setFeatured(fp || []);
      setTrending(Array.isArray(tr) ? tr : []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const categories = [
    { key: "statistical_analysis", label: "Statistical Analysis", color: ACCENT },
    { key: "systematic_review", label: "Systematic Review", color: EMERALD },
    { key: "scientific_writing", label: "Scientific Writing", color: "#7C3AED" },
    { key: "grant_writing", label: "Grant Writing", color: "#DB2777" },
    { key: "programming", label: "Research Software", color: "#0891B2" },
    { key: "peer_review", label: "Peer Review", color: "#D97706" },
    { key: "data_visualization", label: "Data Visualization", color: "#059669" },
    { key: "research_consulting", label: "Research Consulting", color: NAVY },
  ];

  const runSearch = () => navigate(`/academic-marketplace/services?q=${encodeURIComponent(search)}`);

  return (
    <ResearchLayout
      title="Academic Services Marketplace"
      subtitle="Connect with verified academic experts. Every service is transparent, every transaction is traceable."
      sidebar={!loading && (featured.length > 0 || trending.length > 0) ? <MarketplaceHomeSidebar trending={trending} featured={featured} /> : undefined}
    >

        {/* Search */}
        <div className="text-center mb-12">
          <div className="flex gap-2 max-w-[600px] mx-auto items-center">
            <SearchBar
              value={search}
              onChange={setSearch}
              onKeyDown={e => e.key === "Enter" && runSearch()}
              placeholder="Search statistical analysis, peer review, grant writing..."
              size="lg"
              className="flex-1"
            />
            <Button onClick={runSearch}>Search</Button>
          </div>
        </div>

        {/* Categories */}
        <div className="mb-12">
          <H2 className="mb-5">Browse by Category</H2>
          <Grid cols={4} gap="sm">
            {categories.map(cat => (
              <Card key={cat.key} to={`/academic-marketplace/services?category=${cat.key}`} padding="md">
                <div className="flex items-center gap-3">
                  <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: cat.color }} />
                  <span className="text-navy-700 text-sm font-medium">{cat.label}</span>
                  <ChevronRight size={14} className="text-slate-500 ml-auto" />
                </div>
              </Card>
            ))}
          </Grid>
        </div>

        {/* Trending Services */}
        {trending.length > 0 && (
          <div className="mb-12">
            <div className="flex items-center justify-between mb-5">
              <H2 className="m-0">
                <TrendingUp size={18} className="mr-2 align-middle inline" />
                Trending Services
              </H2>
              <Link to="/academic-marketplace/services" className="text-crimson-600 text-sm font-medium no-underline">View all →</Link>
            </div>
            <Grid cols={3} gap="md">
              {trending.slice(0, 6).map(svc => (
                <Card key={svc.id} to={`/academic-marketplace/services/${svc.id}`} padding="lg">
                  <div className="text-xs text-crimson-600 font-semibold uppercase mb-2">
                    {svc.category?.replace(/_/g, " ")}
                  </div>
                  <div className="text-[15px] font-semibold text-navy-700 mb-2">{svc.title}</div>
                  <div className="flex items-center gap-2">
                    <Star size={13} className="text-amber-500" fill="#F59E0B" />
                    <Caption>{svc.average_rating?.toFixed(1) || "New"}</Caption>
                    {svc.recent_orders > 0 && (
                      <span className="text-xs text-emerald-600 ml-auto">
                        {svc.recent_orders} recent orders
                      </span>
                    )}
                  </div>
                </Card>
              ))}
            </Grid>
          </div>
        )}

        {/* Featured Providers */}
        {featured.length > 0 && (
          <div className="mb-12">
            <div className="flex items-center justify-between mb-5">
              <H2 className="m-0">
                <Award size={18} className="mr-2 align-middle inline" />
                Featured Experts
              </H2>
              <Link to="/academic-marketplace/providers" className="text-crimson-600 text-sm font-medium no-underline">View all →</Link>
            </div>
            <Grid cols={4} gap="md">
              {featured.map(p => (
                <Card key={p.user_id} to={`/academic-marketplace/providers/${p.user_id}`} padding="lg">
                  <div className="text-center">
                    <div className="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3" style={{ background: ACCENT + "22" }}>
                      <span className="text-xl font-bold text-crimson-600">{(p.display_name || "?")[0]}</span>
                    </div>
                    <div className="text-sm font-semibold text-navy-700 mb-1">{p.display_name}</div>
                    <Caption className="mb-2">{p.headline?.slice(0, 50)}</Caption>
                    <div className="flex justify-center items-center gap-1">
                      <Star size={12} className="text-amber-500" fill="#F59E0B" />
                      <Caption>{p.average_rating?.toFixed(1)}</Caption>
                      <Caption>({p.completed_orders} orders)</Caption>
                    </div>
                  </div>
                </Card>
              ))}
            </Grid>
          </div>
        )}

        {/* Quick actions */}
        <Grid cols={2} gap="md">
          <Card to="/academic-marketplace/provider/setup" padding="xl" style={{ background: NAVY, color: "#fff" }}>
            <Zap size={24} className="mb-3" />
            <div className="text-lg font-bold mb-1">Become a Provider</div>
            <div className="text-sm opacity-80">Offer your expertise to the academic community</div>
          </Card>
          <Card to="/academic-marketplace/orders" padding="xl">
            <ShoppingBag size={24} className="mb-3 text-navy-700" />
            <div className="text-lg font-bold mb-1 text-navy-700">My Orders</div>
            <Caption>Track and manage your service orders</Caption>
          </Card>
        </Grid>
    </ResearchLayout>
  );
}
