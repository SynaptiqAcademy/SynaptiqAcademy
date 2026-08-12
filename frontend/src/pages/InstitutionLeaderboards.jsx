import { useState, useEffect, useCallback } from "react";
import api from "../lib/api";
import { NAVY, WARM } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import {
  Building2, Users, Globe, TrendingUp,
} from "lucide-react";
import { Card, NavTabs, ErrorState, EmptyState, DataTable, SkeletonTable } from "@/components/ds";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(val, fallback = "—") {
  if (val == null || val === "") return fallback;
  return val;
}

function fmtNum(val) {
  if (val == null) return "—";
  return Number(val).toLocaleString();
}

function pct(val, max) {
  if (!max) return 0;
  return Math.min(100, Math.round((val / max) * 100));
}

function iisColor(score) {
  if (score >= 7500) return "#D97706";
  if (score >= 5000) return "#7C3AED";
  if (score >= 2500) return "#0891B2";
  return "#94A3B8";
}

function iisLabel(score) {
  if (score >= 7500) return "Distinguished";
  if (score >= 5000) return "Premier";
  if (score >= 2500) return "Established";
  return "Emerging";
}

// ── Rank medal ────────────────────────────────────────────────────────────────

function RankMedal({ rank }) {
  if (rank === 1) return <span className="font-bold text-amber-500 text-sm w-7 text-center">1</span>;
  if (rank === 2) return <span className="font-bold text-slate-400 text-sm w-7 text-center">2</span>;
  if (rank === 3) return <span className="font-bold text-amber-700 text-sm w-7 text-center">3</span>;
  return <span className="font-mono text-xs text-slate-400 w-7 text-center">{rank}</span>;
}

// ── Leaderboard row ───────────────────────────────────────────────────────────

function LeaderboardRow({ rank, name, sub, score, scoreSub, max = 10000, color, extra }) {
  const p = pct(score || 0, max);
  const c = color || iisColor(score);

  return (
    <div className="py-3 border-b border-slate-100 last:border-0">
      <div className="flex items-center gap-3">
        <RankMedal rank={rank} />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-slate-900 truncate">{fmt(name)}</div>
          {sub && <div className="text-xs text-slate-500 truncate">{sub}</div>}
        </div>
        <div className="text-right flex-shrink-0">
          <div className="font-mono text-sm font-semibold" style={{ color: c }}>
            {fmtNum(score)}
          </div>
          {scoreSub && <div className="text-[10px] text-slate-400">{scoreSub}</div>}
        </div>
        {extra && <div className="flex-shrink-0 text-right">{extra}</div>}
      </div>
      <div className="ml-10 mt-2 h-1.5 bg-slate-100 overflow-hidden">
        <div
          className="h-full transition-all duration-700"
          style={{ width: `${p}%`, backgroundColor: c }}
        />
      </div>
    </div>
  );
}

// ── Bar chart (div-based, horizontal) ────────────────────────────────────────

function HBarChart({ items = [], nameKey = "name", scoreKey = "score", max = 10000, colorFn }) {
  const maxVal = Math.max(...items.map((i) => i[scoreKey] || 0), max, 1);
  return (
    <div className="space-y-2 mt-4">
      {items.slice(0, 20).map((item, idx) => {
        const val = item[scoreKey] || 0;
        const p = pct(val, maxVal);
        const c = colorFn ? colorFn(val) : iisColor(val);
        return (
          <div key={idx}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-700 truncate max-w-[55%]">{item[nameKey]}</span>
              <span className="font-mono text-xs text-slate-500">{fmtNum(val)}</span>
            </div>
            <div className="h-2 bg-slate-100 overflow-hidden">
              <div
                className="h-full transition-all duration-700"
                style={{ width: `${p}%`, backgroundColor: c }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Country aggregation ───────────────────────────────────────────────────────

function aggregateByCountry(institutions = [], researchers = []) {
  const map = {};

  for (const inst of institutions) {
    const country = inst.country || "Unknown";
    if (!map[country]) map[country] = { country, institutions: 0, researchers: 0, iis_scores: [] };
    map[country].institutions += 1;
    if (inst.iis_score != null) map[country].iis_scores.push(inst.iis_score);
  }

  for (const r of researchers) {
    const country = r.country || r.institution_country || "Unknown";
    if (!map[country]) map[country] = { country, institutions: 0, researchers: 0, iis_scores: [] };
    map[country].researchers += 1;
  }

  return Object.values(map)
    .map((c) => ({
      ...c,
      avg_iis: c.iis_scores.length
        ? Math.round(c.iis_scores.reduce((a, b) => a + b, 0) / c.iis_scores.length)
        : 0,
    }))
    .sort((a, b) => b.avg_iis - a.avg_iis);
}

// ── Main component ────────────────────────────────────────────────────────────

const TABS = [
  { key: "institutions", label: "Institutions", icon: Building2 },
  { key: "researchers", label: "Researchers", icon: Users },
  { key: "countries", label: "Countries", icon: Globe },
];

export default function InstitutionLeaderboards() {
  const [activeTab, setActiveTab] = useState("institutions");
  const [leaderboard, setLeaderboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchLeaderboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get("/institution-hub/leaderboards");
      setLeaderboard(res.data);
    } catch (e) {
      setError(e?.response?.data?.message || "Failed to load leaderboards.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLeaderboard();
  }, [fetchLeaderboard]);

  const institutions = leaderboard?.institutions || [];
  const researchers = leaderboard?.researchers || [];
  const countries = aggregateByCountry(institutions, researchers);

  const maxIis = Math.max(...institutions.map((i) => i.iis_score || i.impact_score || 0), 1);
  const maxSis = Math.max(...researchers.map((r) => r.sis_score || r.impact_score || 0), 1);
  const maxAvgIis = Math.max(...countries.map((c) => c.avg_iis || 0), 1);

  const rankedCountries = countries.map((c, i) => ({ ...c, rank: i + 1 }));

  const countryColumns = [
    { key: "rank", label: "Rank", width: 48, render: (v) => <RankMedal rank={v} /> },
    { key: "country", label: "Country", render: (v) => <span className="text-sm font-medium text-slate-900">{v}</span> },
    { key: "institutions", label: "Institutions", render: (v) => fmtNum(v) },
    { key: "researchers", label: "Researchers", render: (v) => fmtNum(v) },
    {
      key: "avg_iis", label: "Avg IIS",
      render: (v) => (
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold" style={{ color: iisColor(v) }}>{fmtNum(v)}</span>
          <div className="flex-1 h-1.5 bg-slate-100 overflow-hidden min-w-12 max-w-24">
            <div className="h-full transition-all duration-700" style={{ width: `${pct(v, maxAvgIis)}%`, backgroundColor: iisColor(v) }} />
          </div>
        </div>
      ),
    },
  ];

  return (
    <InstitutionLayout
      title="Leaderboards"
      subtitle="Global rankings for institutions, researchers, and countries on the Synaptiq platform."
    >
      {/* Tab bar */}
      <div className="bg-white sticky top-0 z-10 mb-6">
        <NavTabs
          variant="underline"
          active={activeTab}
          onChange={setActiveTab}
          tabs={TABS.map((t) => ({ id: t.key, label: t.label, icon: t.icon }))}
        />
      </div>

        {loading ? (
          <SkeletonTable rows={10} cols={4} />
        ) : error ? (
          <ErrorState message={error} onRetry={fetchLeaderboard} />
        ) : (
          <>
            {/* ── Institutions tab ── */}
            {activeTab === "institutions" && (
              <div className="space-y-6">
                <Card padding="lg">
                  <div className="flex items-center gap-2 mb-1">
                    <Building2 size={14} strokeWidth={1.5} className="text-slate-400" />
                    <h2 className="text-sm font-semibold text-slate-900">Top Institutions by Impact Score</h2>
                  </div>
                  <p className="text-xs text-slate-500 mb-4">
                    Ranked by Institution Impact Score (IIS), a composite of publication volume, citations, grant success, and member reputation.
                  </p>
                  {institutions.length === 0 ? (
                    <EmptyState icon={<Building2 />} title="No institutions ranked yet." />
                  ) : (
                    <>
                      <div>
                        {institutions.map((inst, idx) => {
                          const score = inst.iis_score || inst.impact_score || 0;
                          return (
                            <LeaderboardRow
                              key={inst._id || idx}
                              rank={idx + 1}
                              name={inst.name}
                              sub={[inst.type, inst.country].filter(Boolean).join(" · ")}
                              score={score}
                              scoreSub={iisLabel(score)}
                              max={maxIis}
                              extra={
                                inst.member_count != null ? (
                                  <span className="text-[10px] text-slate-400">{fmtNum(inst.member_count)} members</span>
                                ) : null
                              }
                            />
                          );
                        })}
                      </div>

                      {institutions.length > 3 && (
                        <div className="mt-8 pt-6 border-t border-slate-100">
                          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-4">
                            Score Chart — Top {Math.min(20, institutions.length)}
                          </h3>
                          <HBarChart
                            items={institutions}
                            nameKey="name"
                            scoreKey="iis_score"
                            max={maxIis}
                            colorFn={iisColor}
                          />
                        </div>
                      )}
                    </>
                  )}
                </Card>
              </div>
            )}

            {/* ── Researchers tab ── */}
            {activeTab === "researchers" && (
              <div className="space-y-6">
                <Card padding="lg">
                  <div className="flex items-center gap-2 mb-1">
                    <TrendingUp size={14} strokeWidth={1.5} className="text-slate-400" />
                    <h2 className="text-sm font-semibold text-slate-900">Top Researchers Globally</h2>
                  </div>
                  <p className="text-xs text-slate-500 mb-4">
                    Ranked by Scholar Impact Score (SIS) reflecting publications, citations, h-index, collaborations, and teaching.
                  </p>
                  {researchers.length === 0 ? (
                    <EmptyState icon={<Users />} title="No researcher rankings available." />
                  ) : (
                    <>
                      <div>
                        {researchers.map((r, idx) => {
                          const score = r.sis_score || r.impact_score || 0;
                          return (
                            <LeaderboardRow
                              key={r._id || idx}
                              rank={idx + 1}
                              name={r.name || r.display_name}
                              sub={r.institution_name || r.institution}
                              score={score}
                              scoreSub="SIS"
                              max={maxSis}
                              color="#7C3AED"
                              extra={
                                r.h_index != null ? (
                                  <span className="text-[10px] text-slate-400">h-index {r.h_index}</span>
                                ) : null
                              }
                            />
                          );
                        })}
                      </div>

                      {researchers.length > 3 && (
                        <div className="mt-8 pt-6 border-t border-slate-100">
                          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-4">
                            Score Chart — Top {Math.min(20, researchers.length)}
                          </h3>
                          <HBarChart
                            items={researchers}
                            nameKey="name"
                            scoreKey="sis_score"
                            max={maxSis}
                            colorFn={() => "#7C3AED"}
                          />
                        </div>
                      )}
                    </>
                  )}
                </Card>
              </div>
            )}

            {/* ── Countries tab ── */}
            {activeTab === "countries" && (
              <div className="space-y-6">
                <Card padding="lg">
                  <div className="flex items-center gap-2 mb-1">
                    <Globe size={14} strokeWidth={1.5} className="text-slate-400" />
                    <h2 className="text-sm font-semibold text-slate-900">Country Rankings</h2>
                  </div>
                  <p className="text-xs text-slate-500 mb-4">
                    Countries aggregated by average Institution Impact Score. Hover bars for scores.
                  </p>
                  {countries.length === 0 ? (
                    <EmptyState icon={<Globe />} title="No country data available." />
                  ) : (
                    <>
                      <DataTable columns={countryColumns} rows={rankedCountries} />

                      {countries.length > 3 && (
                        <div className="mt-8 pt-6 border-t border-slate-100">
                          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-4">
                            Avg IIS by Country — Top {Math.min(20, countries.length)}
                          </h3>
                          <HBarChart
                            items={countries}
                            nameKey="country"
                            scoreKey="avg_iis"
                            max={maxAvgIis}
                            colorFn={iisColor}
                          />
                        </div>
                      )}
                    </>
                  )}
                </Card>
              </div>
            )}
          </>
        )}
    </InstitutionLayout>
  );
}
