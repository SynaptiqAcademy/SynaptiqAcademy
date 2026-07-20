import React, { useState, useEffect, useCallback } from "react";
import { Star, Package, Tag as TagIcon } from "lucide-react";
import { ACCENT, EMERALD } from "@/lib/tokens";
import { DiscoveryLayout } from "@/layouts";
import { Card, Grid, SearchBar, FormSelect, Button, EmptyState, LoadingOverlay, Caption } from "@/components/ds";

const API = "/api/acad-market";

const SORT_OPTIONS = [
  { value: "rating", label: "Top Rated" },
  { value: "popular", label: "Most Popular" },
  { value: "newest", label: "Newest" },
  { value: "price_asc", label: "Price: Low to High" },
];

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
    fetch(`${API}/services/categories`).then(r => r.json()).then(d => setCategories(d.categories || []));
  }, []);

  const fetchServices = useCallback(() => {
    setLoading(true);
    const qs = new URLSearchParams({ page, sort });
    if (q) qs.set("q", q);
    if (category) qs.set("category", category);
    fetch(`${API}/services?${qs}`).then(r => r.json()).then(d => {
      setResults(d.results || []);
      setTotal(d.total || 0);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [q, category, sort, page]);

  useEffect(() => { fetchServices(); }, [fetchServices]);

  return (
    <DiscoveryLayout title="Browse Services" subtitle={`${total} services available`}>

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
    </DiscoveryLayout>
  );
}
