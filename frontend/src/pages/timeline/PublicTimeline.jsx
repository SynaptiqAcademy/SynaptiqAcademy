import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Globe, Activity, CalendarDays, Trophy, BookOpen, GraduationCap, DollarSign, Users, FileCheck, ShieldCheck, Award, Eye, Sparkles } from "lucide-react";
import { NAVY, WARM, BRD, EMERALD, TEXT_SECONDARY, WHITE } from "../../lib/tokens";
import { ResearchLayout } from "@/layouts";

const API = "/api/timeline";

const CATEGORY_META = {
  research:      { label: "Research",      icon: BookOpen,    color: "#0369A1" },
  teaching:      { label: "Teaching",      icon: GraduationCap, color: "#7C3AED" },
  grant:         { label: "Grants",        icon: DollarSign,  color: "#059669" },
  collaboration: { label: "Collaboration", icon: Users,       color: "#0F2847" },
  review:        { label: "Review",        icon: FileCheck,   color: "#D97706" },
  verification:  { label: "Verification",  icon: ShieldCheck, color: "#059669" },
  recognition:   { label: "Recognition",   icon: Award,       color: "#D97706" },
  community:     { label: "Community",     icon: Eye,         color: "#0369A1" },
  ai:            { label: "AI",            icon: Sparkles,    color: "#7C3AED" },
};

export default function PublicTimeline() {
  const { userId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!userId) return;
    fetch(`${API}/public/${userId}?limit=50`, { credentials: "include" })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(d => { setData(d); setLoading(false); })
      .catch(() => { setError(true); setLoading(false); });
  }, [userId]);

  if (loading) {
    return (
      <ResearchLayout title="Public Timeline" icon={<Globe size={18} />}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: 80, color: TEXT_SECONDARY }}>
          Loading timeline…
        </div>
      </ResearchLayout>
    );
  }

  if (error || !data) {
    return (
      <ResearchLayout title="Public Timeline" icon={<Globe size={18} />}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 8, padding: 80 }}>
          <Globe size={36} color={BRD} />
          <p style={{ color: NAVY, fontWeight: 600 }}>Timeline not found</p>
          <p style={{ color: TEXT_SECONDARY, fontSize: 13 }}>This timeline is private or does not exist.</p>
        </div>
      </ResearchLayout>
    );
  }

  const { events = [], stats = {} } = data;

  // Group by year
  const grouped = {};
  for (const ev of events) {
    const year = ev.occurred_at ? new Date(ev.occurred_at).getFullYear() : "Unknown";
    if (!grouped[year]) grouped[year] = [];
    grouped[year].push(ev);
  }
  const years = Object.keys(grouped).sort((a, b) => b - a);

  return (
    <ResearchLayout title="Research Activity Timeline" subtitle="Public Academic Timeline" icon={<Globe size={18} />}>
      <div style={{ maxWidth: 760, margin: "0 auto" }}>

        {/* Public header */}
        <div style={{ background: `linear-gradient(135deg, ${NAVY} 0%, #1e4080 100%)`,
          borderRadius: 14, padding: "28px 32px", color: WHITE, marginBottom: 28,
          boxShadow: "0 8px 32px rgba(15,40,71,.2)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
            <Globe size={16} color="rgba(255,255,255,.7)" />
            <span style={{ fontSize: 12, opacity: 0.7 }}>Public Academic Timeline</span>
          </div>
          <h1 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 16px" }}>
            Research Activity Timeline
          </h1>
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
            {[
              { label: "Total Events",  value: stats.total_events || 0,   icon: Activity },
              { label: "Milestones",    value: stats.milestone_count || 0, icon: Trophy },
              { label: "Categories",    value: Object.values(stats.category_breakdown || {}).filter(v => v > 0).length, icon: CalendarDays },
            ].map(s => {
              const Icon = s.icon;
              return (
                <div key={s.label} style={{ textAlign: "center" }}>
                  <Icon size={14} color="rgba(255,255,255,.6)" style={{ marginBottom: 2 }} />
                  <div style={{ fontSize: 22, fontWeight: 700 }}>{s.value}</div>
                  <div style={{ fontSize: 11, opacity: 0.65 }}>{s.label}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Events */}
        {events.length === 0 ? (
          <div style={{ background: WHITE, border: `1px solid ${BRD}`, borderRadius: 12,
            padding: 60, textAlign: "center" }}>
            <Activity size={32} color={BRD} style={{ display: "block", margin: "0 auto 12px" }} />
            <p style={{ color: TEXT_SECONDARY, fontSize: 14 }}>No public events to display.</p>
          </div>
        ) : (
          years.map(year => (
            <div key={year} style={{ marginBottom: 28 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
                <span style={{ fontSize: 14, fontWeight: 700, color: NAVY }}>{year}</span>
                <div style={{ flex: 1, height: 1, background: BRD }} />
                <span style={{ fontSize: 12, color: TEXT_SECONDARY }}>{grouped[year].length} events</span>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {grouped[year].map(ev => {
                  const meta = CATEGORY_META[ev.category] || CATEGORY_META.research;
                  const Icon = meta.icon;
                  return (
                    <div key={ev._id} style={{
                      background: WHITE, border: `1px solid ${BRD}`,
                      borderLeft: `4px solid ${meta.color}`,
                      borderRadius: 9, padding: "14px 18px",
                    }}>
                      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                        <div style={{
                          width: 30, height: 30, borderRadius: 7,
                          background: meta.color + "14",
                          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                        }}>
                          <Icon size={14} color={meta.color} />
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
                            <span style={{
                              background: meta.color + "14", color: meta.color,
                              border: `1px solid ${meta.color}28`,
                              borderRadius: 5, padding: "1px 8px", fontSize: 11, fontWeight: 600,
                            }}>{ev.label}</span>
                            {ev.is_milestone && (
                              <span style={{ fontSize: 11, color: "#D97706", fontWeight: 600 }}>★ Milestone</span>
                            )}
                            <span style={{ fontSize: 11, color: TEXT_SECONDARY, marginLeft: "auto" }}>
                              {ev.occurred_at ? new Date(ev.occurred_at).toLocaleDateString("en-GB", {
                                day: "numeric", month: "short", year: "numeric",
                              }) : "—"}
                            </span>
                          </div>
                          <div style={{ fontWeight: 600, color: NAVY, fontSize: 14 }}>{ev.title}</div>
                          {ev.description && (
                            <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 4 }}>{ev.description}</div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}

        <div style={{ textAlign: "center", marginTop: 32, fontSize: 12, color: TEXT_SECONDARY }}>
          Powered by Synaptiq Academic OS
        </div>
      </div>
    </ResearchLayout>
  );
}
