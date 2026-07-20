import React, { useState, useEffect, useCallback } from "react";
import { Star, ShieldCheck, Users } from "lucide-react";
import { ACCENT, EMERALD } from "@/lib/tokens";
import { DiscoveryLayout } from "@/layouts";
import { Card, Grid, Badge, Tag, TagGroup, SearchBar, FormSelect, Button, EmptyState, LoadingOverlay } from "@/components/ds";

const API = "/api/acad-market";

export default function ProviderBrowse() {
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [minRating, setMinRating] = useState("");
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    fetch(`${API}/services/categories`).then(r => r.json()).then(d => setCategories(d.categories || []));
  }, []);

  const fetchProviders = useCallback(() => {
    setLoading(true);
    const qs = new URLSearchParams({ page });
    if (q) qs.set("q", q);
    if (category) qs.set("category", category);
    if (minRating) qs.set("min_rating", minRating);
    fetch(`${API}/providers/search?${qs}`).then(r => r.json()).then(d => {
      setResults(d.results || []);
      setTotal(d.total || 0);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [q, category, minRating, page]);

  useEffect(() => { fetchProviders(); }, [fetchProviders]);

  const verLabel = (lvl) => {
    if (lvl >= 5) return { label: "Elite", color: "#7C3AED" };
    if (lvl >= 4) return { label: "Expert", color: EMERALD };
    if (lvl >= 3) return { label: "Institution", color: ACCENT };
    if (lvl >= 2) return { label: "ID Verified", color: "#0891B2" };
    return null;
  };

  return (
    <DiscoveryLayout title="Find Experts" subtitle={`${total} verified academic professionals`}>

        <div className="flex gap-3 mb-6 flex-wrap items-center">
          <SearchBar
            value={q}
            onChange={val => { setQ(val); setPage(1); }}
            placeholder="Search experts..."
            className="flex-1"
            style={{ minWidth: 240 }}
          />
          <FormSelect value={category} onChange={e => { setCategory(e.target.value); setPage(1); }} wrapperClassName="w-auto" className="w-auto">
            <option value="">All Specialties</option>
            {categories.map(c => <option key={c} value={c}>{c.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}</option>)}
          </FormSelect>
          <FormSelect value={minRating} onChange={e => { setMinRating(e.target.value); setPage(1); }} wrapperClassName="w-auto" className="w-auto">
            <option value="">Any Rating</option>
            <option value="4.5">4.5+ Stars</option>
            <option value="4.0">4.0+ Stars</option>
            <option value="3.5">3.5+ Stars</option>
          </FormSelect>
        </div>

        {loading ? (
          <LoadingOverlay text="Loading providers..." />
        ) : results.length === 0 ? (
          <EmptyState icon={<Users />} title="No providers found" />
        ) : (
          <Grid cols={3} gap="md">
            {results.map(p => {
              const ver = verLabel(p.verification_level);
              return (
                <Card key={p.user_id} to={`/academic-marketplace/providers/${p.user_id}`} padding="lg">
                  <div className="flex items-start gap-3 mb-3">
                    <div className="w-11 h-11 rounded-full flex items-center justify-center shrink-0" style={{ background: ACCENT + "22" }}>
                      <span className="text-lg font-bold text-crimson-600">{(p.display_name || "?")[0]}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[15px] font-bold text-navy-700 mb-0.5">{p.display_name}</div>
                      <div className="text-xs text-slate-600 overflow-hidden text-ellipsis whitespace-nowrap">{p.headline}</div>
                    </div>
                  </div>
                  {ver && (
                    <Badge color={ver.color} className="mb-2.5">
                      <ShieldCheck size={10} /> {ver.label}
                    </Badge>
                  )}
                  <div className="text-[13px] text-slate-600 mb-3 leading-normal">
                    {p.bio?.slice(0, 80)}{p.bio?.length > 80 ? "…" : ""}
                  </div>
                  <div className="flex justify-between text-[13px]">
                    <div className="flex items-center gap-1">
                      <Star size={13} className="text-amber-500" fill={p.average_rating > 0 ? "#F59E0B" : "none"} />
                      <span className="text-navy-700 font-semibold">{p.average_rating?.toFixed(1) || "New"}</span>
                      <span className="text-slate-600">({p.rating_count})</span>
                    </div>
                    <span className="text-slate-600">{p.completed_orders} completed</span>
                  </div>
                  {p.categories?.length > 0 && (
                    <TagGroup className="mt-2.5">
                      {p.categories.slice(0, 3).map(c => (
                        <Tag key={c} size="sm">
                          {c.replace(/_/g, " ")}
                        </Tag>
                      ))}
                    </TagGroup>
                  )}
                </Card>
              );
            })}
          </Grid>
        )}

        {total > 20 && (
          <div className="flex justify-center gap-2 mt-6">
            <Button variant="ghost" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
              Previous
            </Button>
            <Button variant="ghost" onClick={() => setPage(p => p + 1)} disabled={results.length < 20}>
              Next
            </Button>
          </div>
        )}
    </DiscoveryLayout>
  );
}
