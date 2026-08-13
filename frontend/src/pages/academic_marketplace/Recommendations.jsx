import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Lightbulb, Star, RefreshCw, X, TrendingUp } from "lucide-react";
import { Card, Grid, Button, H2, Caption, LoadingOverlay } from "@/components/ds";
import { ResearchLayout } from "@/layouts";
import { fetchApi } from "@/lib/api";

const API = "/api/acad-market";

export default function Recommendations() {
  const [recs, setRecs] = useState([]);
  const [trending, setTrending] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [catFilter, setCatFilter] = useState("");

  const load = (cat) => {
    setLoading(true);
    const qs = cat ? `?category=${cat}` : "";
    Promise.all([
      fetchApi(`${API}/recommendations${qs}`).then(r => r.json()),
      fetchApi(`${API}/trending`).then(r => r.json()),
    ]).then(([r, t]) => {
      setRecs(Array.isArray(r) ? r : []);
      setTrending(Array.isArray(t) ? t : []);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => { load(catFilter); }, [catFilter]);

  const refresh = async () => {
    setRefreshing(true);
    await fetchApi(`${API}/recommendations/refresh`, { method: "POST" });
    load(catFilter);
    setRefreshing(false);
  };

  const dismiss = async (serviceId) => {
    await fetchApi(`${API}/recommendations/${serviceId}`, { method: "DELETE" });
    setRecs(prev => prev.filter(r => r.service_id !== serviceId));
  };

  return (
    <ResearchLayout
      title="Recommended for You"
      subtitle="Algorithmic matches based on your research profile"
      icon={<Lightbulb size={15} strokeWidth={1.5} style={{ color: "#0F2847" }} />}
      actions={
        <Button variant="ghost" onClick={refresh} disabled={refreshing}>
          <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
          Refresh
        </Button>
      }
    >
        {loading ? (
          <LoadingOverlay text="Generating recommendations..." />
        ) : (
          <>
            {recs.length > 0 && (
              <div className="mb-10">
                <Grid cols={3} gap="md">
                  {recs.map(r => (
                    <Card key={r.service_id} padding="lg" className="relative">
                      <button onClick={() => dismiss(r.service_id)}
                        aria-label="Dismiss recommendation"
                        className="absolute top-3 right-3 bg-transparent border-none cursor-pointer text-slate-600 p-1">
                        <X size={14} />
                      </button>
                      <div className="text-xs text-crimson-600 font-semibold uppercase mb-1.5">
                        {r.category?.replace(/_/g, " ")}
                      </div>
                      <Link to={`/academic-marketplace/services/${r.service_id}`}
                        className="text-[15px] font-bold text-navy-700 no-underline block mb-2">
                        {r.title}
                      </Link>
                      <div className="flex items-center gap-1 mb-2.5">
                        <Star size={13} className="text-amber-500" fill={r.average_rating > 0 ? "#F59E0B" : "none"} />
                        <Caption>{r.average_rating?.toFixed(1) || "New"} ({r.rating_count})</Caption>
                      </div>
                      <div className="bg-[#F4F6FA] rounded-md px-2.5 py-1.5 text-xs text-slate-600 leading-snug">
                        <strong className="text-navy-700">Why: </strong>{r.reason}
                      </div>
                    </Card>
                  ))}
                </Grid>
              </div>
            )}

            {trending.length > 0 && (
              <div>
                <H2 className="mb-4">
                  <TrendingUp size={18} className="mr-2 align-middle inline" />
                  Trending This Month
                </H2>
                <Grid cols={3} gap="sm">
                  {trending.map(svc => (
                    <Card key={svc.id} to={`/academic-marketplace/services/${svc.id}`} padding="md">
                      <div className="text-xs text-crimson-600 font-semibold uppercase mb-1.5">
                        {svc.category?.replace(/_/g, " ")}
                      </div>
                      <div className="text-sm font-bold text-navy-700 mb-1.5">{svc.title}</div>
                      <div className="flex justify-between text-xs text-slate-600">
                        <span>{svc.recent_orders} orders this month</span>
                        <span className="flex items-center gap-0.5">
                          <Star size={11} className="text-amber-500" fill={svc.average_rating > 0 ? "#F59E0B" : "none"} />
                          {svc.average_rating?.toFixed(1) || "New"}
                        </span>
                      </div>
                    </Card>
                  ))}
                </Grid>
              </div>
            )}
          </>
        )}
    </ResearchLayout>
  );
}
