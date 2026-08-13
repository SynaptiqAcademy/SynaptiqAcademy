import React, { useState, useEffect, useCallback } from "react";
import { Star, Package, Tag as TagIcon } from "lucide-react";
import { NAVY, ACCENT, EMERALD } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Grid, SearchBar, FormSelect, Button, EmptyState, LoadingOverlay, Caption, Tag, TagGroup } from "@/components/ds";
import { fetchApi } from "@/lib/api";

const API = "/api/acad-market";

const SORT_OPTIONS = [
  { value: "rating", label: "Top Rated" },
  { value: "popular", label: "Most Popular" },
  { value: "newest", label: "Newest" },
  { value: "price_asc", label: "Price: Low to High" },
];

// ── Right rail — fetched categories as quick filters + the top-rated result ────
// on the current page; no data invented, nothing fetched just for the rail ────
function ServiceBrowseSidebar({ categories, category, onSelectCategory, results }) {
  const topRated = results.length > 0
    ? results.reduce((best, s) => (s.average_rating || 0) > (best.average_rating || 0) ? s : best, results[0])
    : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {categories.length > 0 && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <TagIcon size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Categories</div>
          </div>
          <TagGroup gap={6}>
            {categories.map((c) => (
              <Tag
                key={c}
                size="sm"
                variant={category === c ? "active" : "default"}
                onClick={() => onSelectCategory(category === c ? "" : c)}
              >
                {c.replace(/_/g, " ")}
              </Tag>
            ))}
          </TagGroup>
        </Card>
      )}

      {topRated && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <Star size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Top Rated on This Page</div>
          </div>
          <a href={`/academic-marketplace/services/${topRated.id}`} style={{ textDecoration: "none" }}>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: "#0f172a" }}>{topRated.title}</div>
          </a>
          <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 4 }}>
            <Star size={10} style={{ color: "#F59E0B" }} fill="#F59E0B" />
            <span style={{ fontSize: 11, color: "#64748B" }}>
              {topRated.average_rating > 0 ? topRated.average_rating.toFixed(1) : "New"} ({topRated.rating_count})
            </span>
          </div>
        </Card>
      )}
    </div>
  );
}

export default function ServiceBrowse() {
  const params = new URLSearchParams(window.location.search);
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState(params.get("q") || "");
  const [category, setCategory] = useState(params.get("category") || "");
  const [sort, setSort] = useState("rating");
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    fetchApi(`${API}/services/categories`).then(r => r.json()).then(d => setCategories(d.categories || []));
  }, []);

  const fetchServices = useCallback(() => {
    setLoading(true);
    const qs = new URLSearchParams({ page, sort });
    if (q) qs.set("q", q);
    if (category) qs.set("category", category);
    fetchApi(`${API}/services?${qs}`).then(r => r.json()).then(d => {
      setResults(d.results || []);
      setTotal(d.total || 0);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [q, category, sort, page]);

  useEffect(() => { fetchServices(); }, [fetchServices]);

  return (
    <ResearchLayout
      title="Browse Services"
      subtitle={`${total} services available`}
      sidebar={!loading ? (
        <ServiceBrowseSidebar
          categories={categories}
          category={category}
          onSelectCategory={(c) => { setCategory(c); setPage(1); }}
          results={results}
        />
      ) : undefined}
    >

        {/* Filters */}
        <div className="flex gap-3 mb-6 flex-wrap items-center">
          <SearchBar
            value={q}
            onChange={val => { setQ(val); setPage(1); }}
            placeholder="Search services..."
            className="flex-1"
            style={{ minWidth: 240 }}
          />
          <FormSelect value={category} onChange={e => { setCategory(e.target.value); setPage(1); }} wrapperClassName="w-auto" className="w-auto">
            <option value="">All Categories</option>
            {categories.map(c => <option key={c} value={c}>{c.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}</option>)}
          </FormSelect>
          <FormSelect value={sort} onChange={e => setSort(e.target.value)} wrapperClassName="w-auto" className="w-auto">
            {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </FormSelect>
        </div>

        {loading ? (
          <LoadingOverlay text="Loading services..." />
        ) : results.length === 0 ? (
          <EmptyState icon={<Package />} title="No services found" description="Try adjusting your filters" />
        ) : (
          <Grid cols={3} gap="md">
            {results.map(svc => (
              <Card key={svc.id} to={`/academic-marketplace/services/${svc.id}`} padding="lg">
                <div className="flex items-center gap-2 mb-2.5">
                  <TagIcon size={13} className="text-crimson-600" />
                  <span className="text-xs text-crimson-600 font-semibold uppercase">
                    {svc.category?.replace(/_/g, " ")}
                  </span>
                </div>
                <div className="text-[15px] font-bold text-navy-700 mb-2 leading-snug">{svc.title}</div>
                <div className="text-[13px] text-slate-600 mb-3 leading-normal">
                  {svc.description?.slice(0, 100)}{svc.description?.length > 100 ? "…" : ""}
                </div>
                {svc.packages?.[0] && (
                  <div className="text-sm font-semibold text-emerald-600 mb-2">
                    From ${svc.packages[0].price}
                  </div>
                )}
                <div className="flex items-center gap-2 justify-between">
                  <div className="flex items-center gap-1">
                    <Star size={13} className="text-amber-500" fill={svc.average_rating > 0 ? "#F59E0B" : "none"} />
                    <Caption>
                      {svc.average_rating > 0 ? svc.average_rating.toFixed(1) : "New"} ({svc.rating_count})
                    </Caption>
                  </div>
                  <Caption>{svc.order_count} orders</Caption>
                </div>
                {svc.provider && (
                  <div className="mt-3 pt-3 border-t border-hairline text-xs text-slate-600">
                    By {svc.provider.display_name}
                    {svc.provider.verification_level >= 3 && (
                      <span className="text-emerald-600 ml-1.5">✓ Verified</span>
                    )}
                  </div>
                )}
              </Card>
            ))}
          </Grid>
        )}

        {total > 20 && (
          <div className="flex justify-center gap-2 mt-6 items-center">
            <Button variant="ghost" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
              Previous
            </Button>
            <Caption>Page {page}</Caption>
            <Button variant="ghost" onClick={() => setPage(p => p + 1)} disabled={results.length < 20}>
              Next
            </Button>
          </div>
        )}
    </ResearchLayout>
  );
}
