import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { AnalyticsLayout } from "@/layouts";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { ACCENT, EMERALD, NAVY } from "@/lib/tokens";
import {
  Users, FileText, BookOpen, TrendingUp, Award, FolderOpen, Target,
  BarChart3, RefreshCw, AlertCircle, CheckCircle2, ChevronLeft,
  Building2, Globe, Zap, Activity, DollarSign, Star, Clock,
  ArrowUpRight, Settings, Download, PlusCircle,
} from "lucide-react";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(val, fallback = "—") {
  if (val == null || val === "") return fallback;
  return val;
}

function fmtNum(val) {
  if (val == null) return "—";
  return Number(val).toLocaleString();
}

function fmtPct(val) {
  if (val == null) return "—";
  return (Number(val) * 100).toFixed(1) + "%";
}

function fmtPctRaw(val) {
  if (val == null) return "—";
  const n = Number(val);
  if (n <= 1) return (n * 100).toFixed(1) + "%";
  return n.toFixed(1) + "%";
}

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function barW(val, max) {
  if (!max || val == null) return "0%";
  return Math.min(100, Math.round((Number(val) / Number(max)) * 100)) + "%";
}

function percentileColor(p) {
  if (p == null) return "text-slate-500";
  if (p > 75) return "text-emerald-600";
  if (p > 50) return "text-blue-600";
  if (p > 25) return "text-amber-600";
  return "text-red-600";
}

function percentileBg(p) {
  if (p == null) return "bg-slate-100";
  if (p > 75) return "bg-emerald-100 border-emerald-200";
  if (p > 50) return "bg-blue-100 border-blue-200";
  if (p > 25) return "bg-amber-100 border-amber-200";
  return "bg-red-100 border-red-200";
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function Skeleton({ h = "h-4", w = "w-full", className = "" }) {
  return <div className={`${h} ${w} bg-slate-200 animate-pulse rounded ${className}`} />;
}

function CardSkeleton() {
  return (
    <div className="bg-white border border-slate-200 rounded-md p-5 animate-pulse space-y-3">
      <Skeleton h="h-3" w="w-1/3" />
      <Skeleton h="h-7" w="w-1/2" />
      <Skeleton h="h-3" />
    </div>
  );
}

function TabSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="grid grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => <CardSkeleton key={i} />)}
      </div>
      <div className="bg-white border border-slate-200 rounded-md p-6 space-y-4">
        {[...Array(5)].map((_, i) => <Skeleton key={i} h="h-4" w={`w-${["full","4/5","3/4","2/3","1/2"][i]}`} />)}
      </div>
    </div>
  );
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function Toast({ message, type = "success", onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [onClose]);

  const colors =
    type === "success"
      ? "bg-emerald-50 border-emerald-200 text-emerald-800"
      : "bg-red-50 border-red-200 text-red-800";

  return (
    <div className={`fixed bottom-6 right-6 z-50 border px-4 py-3 text-sm shadow-lg rounded-lg max-w-xs ${colors}`}>
      <div className="flex items-center gap-2">
        {type === "success" ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
        <span>{message}</span>
        <button onClick={onClose} className="ml-auto opacity-60 hover:opacity-100 text-lg leading-none">&times;</button>
      </div>
    </div>
  );
}

// ── Section heading ───────────────────────────────────────────────────────────

function SectionHeading({ title, subtitle }) {
  return (
    <div className="mb-4">
      <h3 className="text-base font-semibold text-slate-800">{title}</h3>
      {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
    </div>
  );
}

// ── KPI Card ──────────────────────────────────────────────────────────────────

function KpiCard({ label, value, icon: Icon, accent = "#0F2847", suffix = "" }) {
  return (
    <div className="bg-white border border-slate-200 rounded-md p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">{label}</p>
          <p className="text-2xl font-bold text-slate-900">
            {value != null ? fmtNum(value) : "—"}
            {suffix && <span className="text-base font-semibold text-slate-600 ml-0.5">{suffix}</span>}
          </p>
        </div>
        {Icon && (
          <div className="p-2 rounded-lg" style={{ backgroundColor: accent + "18" }}>
            <Icon size={18} style={{ color: accent }} />
          </div>
        )}
      </div>
    </div>
  );
}

// ── Horizontal Bar ────────────────────────────────────────────────────────────

function HBar({ value, max, color = "#0F2847", height = "h-2" }) {
  const w = max ? Math.min(100, Math.round((Number(value || 0) / Number(max)) * 100)) : 0;
  return (
    <div className={`w-full bg-slate-100 rounded-full ${height}`}>
      <div className={`${height} rounded-full transition-all duration-500`} style={{ width: `${w}%`, backgroundColor: color }} />
    </div>
  );
}

// ── Progress Bar with label ───────────────────────────────────────────────────

function LabeledBar({ label, value, max, color = "#0F2847", showValue = true, valueSuffix = "" }) {
  const w = max ? Math.min(100, Math.round((Number(value || 0) / Number(max)) * 100)) : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-slate-600">
        <span className="font-medium truncate max-w-xs">{label}</span>
        {showValue && <span className="ml-2 shrink-0">{fmtNum(value)}{valueSuffix}</span>}
      </div>
      <div className="w-full bg-slate-100 rounded-full h-1.5">
        <div className="h-1.5 rounded-full transition-all duration-500" style={{ width: `${w}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

// ── SVG Ring ──────────────────────────────────────────────────────────────────

function Ring({ value, max = 100, color = "#0F2847", size = 96 }) {
  const r = 38;
  const circ = 2 * Math.PI * r;
  const pct = max ? Math.min(1, Number(value || 0) / Number(max)) : 0;
  const offset = circ * (1 - pct);
  return (
    <svg width={size} height={size} viewBox="0 0 96 96">
      <circle cx="48" cy="48" r={r} fill="none" stroke="#E2E8F0" strokeWidth="8" />
      <circle
        cx="48" cy="48" r={r} fill="none"
        stroke={color} strokeWidth="8"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 48 48)"
      />
      <text x="48" y="52" textAnchor="middle" fontSize="14" fontWeight="700" fill="#1E293B">
        {Math.round(pct * 100)}%
      </text>
    </svg>
  );
}

// ── EXECUTIVE TAB ─────────────────────────────────────────────────────────────

function ExecutiveTab({ kpis, tabData }) {
  const snapshot = tabData?.snapshot;

  const pubTrends = snapshot?.publication_trends ?? kpis?.publication_trends ?? [];
  const maxPubs = pubTrends.length ? Math.max(...pubTrends.map(y => y.count || 0), 1) : 1;

  const researchOutput = snapshot?.research_output ?? kpis?.research_output ?? null;
  const collabScore = snapshot?.collaboration_score ?? kpis?.collaboration_score ?? null;
  const grantSuccessDim = snapshot?.grant_success ?? kpis?.grant_success_rate ?? null;
  const dimMax = 100;

  return (
    <div className="space-y-8">
      {/* KPI Row 1 */}
      <div>
        <SectionHeading title="Core Metrics" subtitle="Institution-wide research performance indicators" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard label="Total Members" value={kpis?.total_members} icon={Users} />
          <KpiCard label="Active Researchers" value={kpis?.active_researchers} icon={Activity} accent="#0891B2" />
          <KpiCard label="Total Publications" value={kpis?.total_publications} icon={FileText} accent="#7C3AED" />
          <KpiCard label="Total Citations" value={kpis?.total_citations} icon={BookOpen} accent="#D97706" />
        </div>
      </div>

      {/* KPI Row 2 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="H-Index Composite" value={kpis?.h_index_composite} icon={Award} accent="#8A1538" />
        <KpiCard label="Total Projects" value={kpis?.total_projects} icon={FolderOpen} accent="#059669" />
        <KpiCard
          label="Grant Success Rate"
          value={kpis?.grant_success_rate != null ? (Number(kpis.grant_success_rate) <= 1 ? (Number(kpis.grant_success_rate) * 100).toFixed(1) : Number(kpis.grant_success_rate).toFixed(1)) : null}
          icon={Target}
          accent="#0F2847"
          suffix="%"
        />
        <KpiCard label="Avg Impact Score" value={kpis?.avg_impact_score != null ? Number(kpis.avg_impact_score).toFixed(2) : null} icon={BarChart3} accent="#DC2626" />
      </div>

      {/* Impact Score + Dimension Bars */}
      {(snapshot?.institution_impact || kpis?.institution_impact) && (
        <div className="bg-white border border-slate-200 rounded-md p-6">
          <SectionHeading title="Institution Impact Score" subtitle="Composite IIS across all research dimensions" />
          <div className="flex flex-col md:flex-row items-start gap-8">
            <div className="text-center shrink-0">
              <div className="text-5xl font-black" style={{ color: "#0F2847" }}>
                {fmtNum(snapshot?.institution_impact ?? kpis?.institution_impact)}
              </div>
              <div className="text-xs text-slate-500 mt-1 uppercase tracking-widest">IIS Score</div>
            </div>
            <div className="flex-1 space-y-4 w-full">
              {researchOutput != null && (
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-600 font-medium">Research Output</span>
                    <span className="text-slate-800 font-semibold">{Number(researchOutput).toFixed(1)}</span>
                  </div>
                  <HBar value={researchOutput} max={dimMax} color="#0F2847" height="h-2.5" />
                </div>
              )}
              {collabScore != null && (
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-600 font-medium">Collaboration Score</span>
                    <span className="text-slate-800 font-semibold">{Number(collabScore).toFixed(1)}</span>
                  </div>
                  <HBar value={collabScore} max={dimMax} color="#0891B2" height="h-2.5" />
                </div>
              )}
              {grantSuccessDim != null && (
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-600 font-medium">Grant Success</span>
                    <span className="text-slate-800 font-semibold">
                      {(Number(grantSuccessDim) <= 1 ? (Number(grantSuccessDim) * 100).toFixed(1) : Number(grantSuccessDim).toFixed(1))}%
                    </span>
                  </div>
                  <HBar
                    value={Number(grantSuccessDim) <= 1 ? Number(grantSuccessDim) * 100 : Number(grantSuccessDim)}
                    max={100}
                    color="#8A1538"
                    height="h-2.5"
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Quick Metrics */}
      <div className="bg-white border border-slate-200 rounded-md p-6">
        <SectionHeading title="Quick Metrics" />
        <div className="space-y-5">
          {kpis?.grant_success_rate != null && (
            <div>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="text-slate-600 font-medium">Grant Success Rate</span>
                <span className="font-semibold text-slate-800">
                  {(Number(kpis.grant_success_rate) <= 1 ? (Number(kpis.grant_success_rate) * 100).toFixed(1) : Number(kpis.grant_success_rate).toFixed(1))}%
                </span>
              </div>
              <HBar
                value={Number(kpis.grant_success_rate) <= 1 ? Number(kpis.grant_success_rate) * 100 : Number(kpis.grant_success_rate)}
                max={100}
                color="#059669"
              />
            </div>
          )}
          {kpis?.avg_reputation != null && (
            <div>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="text-slate-600 font-medium">Average Researcher Reputation</span>
                <span className="font-semibold text-slate-800">{Number(kpis.avg_reputation).toFixed(1)} / 100</span>
              </div>
              <HBar value={kpis.avg_reputation} max={100} color="#7C3AED" />
            </div>
          )}
          {kpis?.top_h_index != null && (
            <div className="flex items-center justify-between py-2 border-t border-slate-100">
              <span className="text-sm text-slate-600 font-medium">Top H-Index</span>
              <span className="text-2xl font-bold" style={{ color: "#8A1538" }}>{fmtNum(kpis.top_h_index)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Publication Trends Mini Chart */}
      {pubTrends.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-md p-6">
          <SectionHeading title="Publication Trends" subtitle="Annual output over time" />
          <div className="flex items-end gap-2 h-28">
            {pubTrends.slice(-3).map((yr, i) => {
              const h = maxPubs ? Math.max(6, Math.round((Number(yr.count || 0) / maxPubs) * 96)) : 6;
              return (
                <div key={i} className="flex flex-col items-center gap-1 flex-1">
                  <span className="text-xs font-semibold text-slate-700">{fmtNum(yr.count)}</span>
                  <div className="w-full rounded-t" style={{ height: `${h}px`, backgroundColor: "#0F2847" }} />
                  <span className="text-xs text-slate-500">{yr.year}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ── PERFORMANCE TAB ───────────────────────────────────────────────────────────

function PerformanceTab({ tabData }) {
  const perf = tabData?.performance ?? {};
  const pubsByYear = perf?.publications_by_year ?? [];
  const topAreas = perf?.top_research_areas ?? [];

  const maxPubs = pubsByYear.length ? Math.max(...pubsByYear.map(y => Number(y.publications || 0)), 1) : 1;
  const maxCites = pubsByYear.length ? Math.max(...pubsByYear.map(y => Number(y.citations || 0)), 1) : 1;
  const maxArea = topAreas.length ? Math.max(...topAreas.map(a => Number(a.count || 0)), 1) : 1;

  return (
    <div className="space-y-8">
      {/* Stat cards row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-md p-5">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">Avg Citations / Paper</p>
          <p className="text-2xl font-bold text-slate-900">{perf?.avg_citations_per_paper != null ? Number(perf.avg_citations_per_paper).toFixed(2) : "—"}</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-md p-5">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">Publication Velocity</p>
          <p className="text-2xl font-bold text-slate-900">{perf?.publication_velocity != null ? `${Number(perf.publication_velocity).toFixed(1)}/yr` : "—"}</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-md p-5">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">International Rate</p>
          <p className="text-2xl font-bold text-slate-900">{perf?.international_rate != null ? fmtPctRaw(perf.international_rate) : "—"}</p>
        </div>
      </div>

      {/* Publications by Year chart */}
      {pubsByYear.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-md p-6">
          <SectionHeading title="Publications & Citations by Year" subtitle="Last 8 years of research output" />
          <div className="space-y-3">
            {pubsByYear.slice(-8).map((yr, i) => (
              <div key={i} className="grid grid-cols-[3rem_1fr_1fr] items-center gap-3">
                <span className="text-xs font-semibold text-slate-600 text-right">{yr.year}</span>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <div
                      className="h-4 rounded-sm transition-all duration-500 min-w-[4px]"
                      style={{ width: barW(yr.publications, maxPubs), backgroundColor: "#0F2847" }}
                    />
                    <span className="text-xs text-slate-600 whitespace-nowrap">{fmtNum(yr.publications)} pubs</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div
                      className="h-4 rounded-sm transition-all duration-500 min-w-[4px]"
                      style={{ width: barW(yr.citations, maxCites), backgroundColor: "#D97706" }}
                    />
                    <span className="text-xs text-slate-500 whitespace-nowrap">{fmtNum(yr.citations)} cites</span>
                  </div>
                </div>
                <div /> {/* spacer */}
              </div>
            ))}
          </div>
          <div className="flex items-center gap-6 mt-4 pt-4 border-t border-slate-100">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: "#0F2847" }} />
              <span className="text-xs text-slate-500">Publications</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: "#D97706" }} />
              <span className="text-xs text-slate-500">Citations</span>
            </div>
          </div>
        </div>
      )}

      {/* Research Area Distribution */}
      {topAreas.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-md p-6">
          <SectionHeading title="Research Area Distribution" subtitle="Top 10 research domains" />
          <div className="space-y-3">
            {topAreas.slice(0, 10).map((area, i) => (
              <LabeledBar
                key={i}
                label={fmt(area.area ?? area.name ?? area._id)}
                value={area.count}
                max={maxArea}
                color="#7C3AED"
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── RESEARCHERS TAB ───────────────────────────────────────────────────────────

function ResearchersTab({ tabData }) {
  const top = tabData?.researchers_top ?? [];
  const growing = tabData?.researchers_growing ?? [];

  function initials(name) {
    if (!name) return "??";
    return name.split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase();
  }

  const maxSis = top.length ? Math.max(...top.map(r => Number(r.sis_total || 0)), 1) : 1;

  return (
    <div className="space-y-8">
      {/* Top Researchers */}
      <div>
        <SectionHeading title="Top Researchers" subtitle="Ranked by research impact score" />
        {top.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-md p-8 text-center text-slate-500 text-sm">No researcher data available</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {top.map((r, i) => {
              const slug = r.slug ?? r.public_slug ?? null;
              const inner = (
                <div className="bg-white border border-slate-200 rounded-md p-5 flex gap-4 items-start hover:shadow-md transition-shadow">
                  <div className="text-slate-400 font-bold text-sm w-5 shrink-0 pt-1">#{i + 1}</div>
                  <div className="w-10 h-10 rounded-full shrink-0 flex items-center justify-center text-white text-sm font-bold" style={{ backgroundColor: "#0F2847" }}>
                    {initials(r.full_name)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-semibold text-slate-800 truncate">{fmt(r.full_name)}</p>
                      {r.h_index != null && (
                        <span className="shrink-0 text-xs font-bold px-2 py-0.5 rounded-full" style={{ backgroundColor: "#8A153818", color: "#8A1538" }}>
                          h={r.h_index}
                        </span>
                      )}
                    </div>
                    {r.institution && <p className="text-xs text-slate-500 mt-0.5 truncate">{r.institution}</p>}
                    {r.sis_total != null && (
                      <div className="mt-2">
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-slate-500">SIS Score</span>
                          <span className="font-medium text-slate-700">{fmtNum(r.sis_total)}</span>
                        </div>
                        <HBar value={r.sis_total} max={maxSis} color="#0F2847" />
                      </div>
                    )}
                  </div>
                </div>
              );
              return slug ? (
                <Link key={i} to={`/researcher/${slug}`}>{inner}</Link>
              ) : (
                <div key={i}>{inner}</div>
              );
            })}
          </div>
        )}
      </div>

      {/* Fastest Growing */}
      {growing.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-md p-6">
          <SectionHeading title="Fastest Growing Researchers" subtitle="Year-over-year publication momentum" />
          <div className="divide-y divide-slate-100">
            {growing.map((r, i) => (
              <div key={i} className="py-3 flex items-center gap-4">
                <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0" style={{ backgroundColor: "#059669" }}>
                  {initials(r.full_name)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-800 truncate">{fmt(r.full_name)}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {r.prev_year_pubs != null && r.current_year_pubs != null
                      ? `${r.prev_year_pubs} → ${r.current_year_pubs} publications`
                      : ""}
                  </p>
                </div>
                {r.growth_rate != null && (
                  <div className="flex items-center gap-1 text-emerald-600 font-semibold text-sm">
                    <ArrowUpRight size={14} />
                    {fmtPctRaw(r.growth_rate)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── DEPARTMENTS TAB ───────────────────────────────────────────────────────────

function DepartmentsTab({ tabData }) {
  const depts = tabData?.departments ?? [];

  const sorted = [...depts].sort((a, b) => Number(b.publications || 0) - Number(a.publications || 0));
  const maxPubs = sorted.length ? Math.max(...sorted.map(d => Number(d.publications || 0)), 1) : 1;
  const maxCites = sorted.length ? Math.max(...sorted.map(d => Number(d.citations || 0)), 1) : 1;
  const totalPubs = sorted.reduce((s, d) => s + Number(d.publications || 0), 0);

  return (
    <div className="space-y-8">
      {/* Comparison Table */}
      <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h3 className="text-base font-semibold text-slate-800">Department Comparison</h3>
          <p className="text-xs text-slate-500 mt-0.5">Sorted by publications descending</p>
        </div>
        {sorted.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-sm">No department data available</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                <tr>
                  <th className="text-left px-6 py-3">Department</th>
                  <th className="text-right px-4 py-3">Members</th>
                  <th className="text-right px-4 py-3">Publications</th>
                  <th className="text-right px-4 py-3">Citations</th>
                  <th className="text-right px-4 py-3">Grants</th>
                  <th className="text-right px-6 py-3">Avg Impact</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sorted.map((d, i) => (
                  <tr key={i} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-3 font-medium text-slate-800">{fmt(d.name ?? d.department)}</td>
                    <td className="px-4 py-3 text-right text-slate-600">{fmtNum(d.members)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16 bg-slate-100 rounded-full h-1.5 shrink-0">
                          <div className="h-1.5 rounded-full" style={{ width: barW(d.publications, maxPubs), backgroundColor: "#0F2847" }} />
                        </div>
                        <span className="text-slate-700 font-medium w-12 text-right">{fmtNum(d.publications)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16 bg-slate-100 rounded-full h-1.5 shrink-0">
                          <div className="h-1.5 rounded-full" style={{ width: barW(d.citations, maxCites), backgroundColor: "#D97706" }} />
                        </div>
                        <span className="text-slate-700 font-medium w-16 text-right">{fmtNum(d.citations)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-slate-600">{fmtNum(d.grants)}</td>
                    <td className="px-6 py-3 text-right text-slate-600">{d.avg_impact != null ? Number(d.avg_impact).toFixed(2) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Department share of total publications */}
      {sorted.length > 0 && totalPubs > 0 && (
        <div className="bg-white border border-slate-200 rounded-md p-6">
          <SectionHeading title="Publication Share by Department" subtitle="Each department's contribution to total output" />
          <div className="space-y-3">
            {sorted.map((d, i) => (
              <LabeledBar
                key={i}
                label={fmt(d.name ?? d.department)}
                value={d.publications}
                max={totalPubs}
                color={["#0F2847", "#0891B2", "#7C3AED", "#059669", "#D97706", "#DC2626", "#8A1538"][i % 7]}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── GRANTS TAB ────────────────────────────────────────────────────────────────

function GrantsTab({ tabData }) {
  const gperf = tabData?.grants_performance ?? {};
  const gtrends = tabData?.grants_trends ?? [];
  const bySource = gperf?.funding_by_source ?? [];

  const maxApps = gtrends.length ? Math.max(...gtrends.map(y => Number(y.applications || 0)), 1) : 1;
  const maxAwarded = gtrends.length ? Math.max(...gtrends.map(y => Number(y.awarded || 0)), 1) : 1;
  const combinedMax = Math.max(maxApps, maxAwarded);
  const maxSourceAmt = bySource.length ? Math.max(...bySource.map(s => Number(s.amount || s.total || 0)), 1) : 1;

  return (
    <div className="space-y-8">
      {/* Grant KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <KpiCard label="Total Applications" value={gperf?.total_applications} icon={FileText} />
        <KpiCard label="Awarded" value={gperf?.total_awarded} icon={CheckCircle2} accent="#059669" />
        <KpiCard
          label="Success Rate"
          value={gperf?.success_rate != null ? (Number(gperf.success_rate) <= 1 ? (Number(gperf.success_rate) * 100).toFixed(1) : Number(gperf.success_rate).toFixed(1)) : null}
          icon={Target}
          accent="#8A1538"
          suffix="%"
        />
        <KpiCard label="Total Funding" value={gperf?.total_funding_secured} icon={DollarSign} accent="#D97706" />
        <KpiCard label="Avg Grant Size" value={gperf?.avg_grant_size} icon={BarChart3} accent="#7C3AED" />
      </div>

      {/* Funding by Year */}
      {gtrends.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-md p-6">
          <SectionHeading title="Funding Pipeline by Year" subtitle="Applications vs. awarded grants" />
          <div className="space-y-4">
            {gtrends.map((yr, i) => (
              <div key={i} className="grid grid-cols-[3.5rem_1fr] items-center gap-3">
                <span className="text-xs font-semibold text-slate-600 text-right">{yr.year}</span>
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <div className="h-4 rounded-sm min-w-[4px] transition-all duration-500"
                      style={{ width: barW(yr.applications, combinedMax), backgroundColor: "#94A3B8" }} />
                    <span className="text-xs text-slate-500">{fmtNum(yr.applications)} apps</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-4 rounded-sm min-w-[4px] transition-all duration-500"
                      style={{ width: barW(yr.awarded, combinedMax), backgroundColor: "#059669" }} />
                    <span className="text-xs text-slate-600 font-medium">{fmtNum(yr.awarded)} awarded</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-6 mt-4 pt-4 border-t border-slate-100">
            <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-slate-400" /><span className="text-xs text-slate-500">Applications</span></div>
            <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-emerald-600" /><span className="text-xs text-slate-500">Awarded</span></div>
          </div>
        </div>
      )}

      {/* Funding by Source */}
      {bySource.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-md p-6">
          <SectionHeading title="Top Funding Sources" />
          <div className="space-y-3">
            {bySource.map((s, i) => (
              <div key={i} className="space-y-1">
                <div className="flex justify-between text-xs text-slate-600">
                  <span className="font-medium truncate max-w-xs">{fmt(s.source ?? s.name)}</span>
                  <span className="ml-2 shrink-0">
                    {fmtNum(s.count ?? s.grants)} grants
                    {s.amount != null ? ` · $${fmtNum(s.amount)}` : s.total != null ? ` · $${fmtNum(s.total)}` : ""}
                  </span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-1.5">
                  <div className="h-1.5 rounded-full" style={{ width: barW(s.amount ?? s.total ?? 0, maxSourceAmt), backgroundColor: "#D97706" }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── COLLABORATIONS TAB ────────────────────────────────────────────────────────

function CollaborationsTab({ tabData }) {
  const data = tabData?.collaborations ?? {};
  const total = data?.total ?? 0;
  const byStatus = data?.by_status ?? data?.status_breakdown ?? {};

  const statusEntries = Object.entries(byStatus);
  const maxStatus = statusEntries.length ? Math.max(...statusEntries.map(([, v]) => Number(v)), 1) : 1;

  const intlCount = data?.international_count ?? 0;
  const intlPct = total > 0 ? Math.round((intlCount / total) * 100) : 0;

  const statusColors = {
    open: "#0891B2",
    active: "#059669",
    completed: "#7C3AED",
    closed: "#94A3B8",
    pending: "#D97706",
  };

  return (
    <div className="space-y-8">
      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Total Collaborations" value={data?.total} icon={Users} />
        <KpiCard label="Internal" value={data?.internal_count} icon={Building2} accent="#0891B2" />
        <KpiCard label="International" value={data?.international_count} icon={Globe} accent="#7C3AED" />
        <KpiCard label="Unique Partners" value={data?.unique_partners} icon={Star} accent="#D97706" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* By Status */}
        {statusEntries.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-md p-6">
            <SectionHeading title="By Status" />
            <div className="space-y-3">
              {statusEntries.map(([status, count], i) => (
                <LabeledBar
                  key={i}
                  label={status.charAt(0).toUpperCase() + status.slice(1)}
                  value={count}
                  max={maxStatus}
                  color={statusColors[status] ?? "#0F2847"}
                />
              ))}
            </div>
          </div>
        )}

        {/* International Ring */}
        {total > 0 && (
          <div className="bg-white border border-slate-200 rounded-md p-6 flex flex-col items-center justify-center">
            <SectionHeading title="International Reach" subtitle="Share of cross-border collaborations" />
            <Ring value={intlPct} max={100} color="#7C3AED" size={120} />
            <p className="text-sm text-slate-600 mt-3 text-center">
              <span className="font-semibold text-slate-800">{fmtNum(intlCount)}</span> of {fmtNum(total)} collaborations are international
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// ── BENCHMARKS TAB ────────────────────────────────────────────────────────────

function BenchmarksTab({ tabData }) {
  const bench = tabData?.benchmarks ?? {};
  const percentiles = bench?.percentiles ?? {};
  const topInst = bench?.top_institutions ?? [];
  const strengths = bench?.strengths ?? [];
  const improvements = bench?.improvement_areas ?? bench?.areas_for_improvement ?? [];

  const pCards = [
    { key: "publications", label: "Publications" },
    { key: "citations", label: "Citations" },
    { key: "grants", label: "Grants" },
    { key: "impact", label: "Impact Score" },
  ].filter(c => percentiles[c.key] != null);

  return (
    <div className="space-y-8">
      {/* Percentile Cards */}
      {pCards.length > 0 && (
        <div>
          <SectionHeading title="Peer Percentile Ranking" subtitle="How your institution compares to peers globally" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {pCards.map((c, i) => {
              const p = Math.round(Number(percentiles[c.key]));
              return (
                <div key={i} className={`border rounded-md p-5 ${percentileBg(p)}`}>
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">{c.label}</p>
                  <p className={`text-3xl font-black ${percentileColor(p)}`}>{p}<span className="text-base font-semibold">th</span></p>
                  <p className="text-xs text-slate-600 mt-1">Outperforms {p}% of peers</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Peer Comparison Table */}
      {topInst.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100">
            <h3 className="text-base font-semibold text-slate-800">Peer Institutions</h3>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wide">
              <tr>
                <th className="text-left px-6 py-3">Institution</th>
                <th className="text-left px-4 py-3">Country</th>
                <th className="text-right px-4 py-3">IIS Score</th>
                <th className="text-right px-6 py-3">Rank</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {topInst.map((inst, i) => (
                <tr key={i} className="hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-3 font-medium text-slate-800">{fmt(inst.name ?? inst.institution_name)}</td>
                  <td className="px-4 py-3 text-slate-600">{fmt(inst.country)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-slate-800">{fmtNum(inst.iis_total)}</td>
                  <td className="px-6 py-3 text-right text-slate-600">#{fmtNum(inst.rank)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Strengths / Improvements */}
      {(strengths.length > 0 || improvements.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {strengths.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-md p-6">
              <SectionHeading title="Strengths" />
              <div className="flex flex-wrap gap-2">
                {strengths.map((s, i) => (
                  <span key={i} className="px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
          {improvements.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-md p-6">
              <SectionHeading title="Areas for Improvement" />
              <div className="flex flex-wrap gap-2">
                {improvements.map((s, i) => (
                  <span key={i} className="px-3 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── FORECASTS TAB ─────────────────────────────────────────────────────────────

function ForecastsTab({ id, tabData, user, onReload }) {
  const [generating, setGenerating] = useState(false);
  const [toast, setToast] = useState(null);
  const forecasts = tabData?.forecasts ?? {};

  const forecastKeys = [
    { key: "publications_forecast", label: "Publications Forecast", color: "#0F2847" },
    { key: "citations_forecast", label: "Citations Forecast", color: "#D97706" },
    { key: "funding_forecast", label: "Funding Forecast", color: "#059669" },
  ];

  async function handleGenerate() {
    setGenerating(true);
    try {
      await api.post(`/institution-analytics/${id}/forecasts/generate`);
      setToast({ message: "Forecast generation initiated", type: "success" });
      await onReload();
    } catch (e) {
      setToast({ message: e?.response?.data?.error ?? "Generation failed", type: "error" });
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="space-y-8">
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      {forecastKeys.map(({ key, label, color }) => {
        const fc = forecasts[key];
        if (!fc) return null;
        const years = fc.years ?? fc.predictions ?? [];
        const maxVal = years.length ? Math.max(...years.map(y => Number(y.predicted ?? y.value ?? 0)), 1) : 1;

        return (
          <div key={key} className="bg-white border border-slate-200 rounded-md p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-base font-semibold text-slate-800">{label}</h3>
                {fc.generated_at && (
                  <p className="text-xs text-slate-500 mt-0.5">Generated {formatDate(fc.generated_at)}</p>
                )}
              </div>
            </div>

            {years.length > 0 ? (
              <div className="space-y-3">
                {years.map((yr, i) => {
                  const val = yr.predicted ?? yr.value ?? 0;
                  const lo = yr.low_confidence ?? yr.low ?? null;
                  const hi = yr.high_confidence ?? yr.high ?? null;
                  const barPct = maxVal ? Math.min(100, Math.round((Number(val) / maxVal) * 100)) : 0;
                  return (
                    <div key={i} className="grid grid-cols-[3.5rem_1fr_auto] items-center gap-3">
                      <span className="text-xs font-semibold text-slate-600 text-right">{yr.year}</span>
                      <div className="relative h-6 bg-slate-100 rounded-sm overflow-hidden">
                        <div className="h-full rounded-sm transition-all duration-500" style={{ width: `${barPct}%`, backgroundColor: color + "CC" }} />
                        {lo != null && hi != null && (
                          <div
                            className="absolute top-0 h-full opacity-30"
                            style={{
                              left: `${Math.round((Number(lo) / maxVal) * 100)}%`,
                              width: `${Math.round(((Number(hi) - Number(lo)) / maxVal) * 100)}%`,
                              backgroundColor: color,
                            }}
                          />
                        )}
                      </div>
                      <div className="text-right text-xs">
                        <span className="font-semibold text-slate-800">{fmtNum(val)}</span>
                        {lo != null && hi != null && (
                          <span className="text-slate-400 ml-1">({fmtNum(lo)}–{fmtNum(hi)})</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No forecast data available for this metric.</p>
            )}
          </div>
        );
      })}

      {Object.keys(forecasts).length === 0 && (
        <div className="bg-white border border-slate-200 rounded-md p-10 text-center">
          <Zap size={32} className="mx-auto text-slate-300 mb-3" />
          <p className="text-slate-600 font-medium">No forecasts generated yet</p>
          <p className="text-slate-400 text-sm mt-1">Generate your first research forecast below</p>
        </div>
      )}

      <div className="flex justify-end">
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white rounded-lg disabled:opacity-60 transition-opacity"
          style={{ backgroundColor: "#0F2847" }}
        >
          <Zap size={15} />
          {generating ? "Generating…" : "Generate New Forecast"}
        </button>
      </div>
    </div>
  );
}

// ── REPORTS TAB ───────────────────────────────────────────────────────────────

function ReportsTab({ id, tabData, onReload }) {
  const [toast, setToast] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [form, setForm] = useState({ report_type: "executive", title: "" });
  const reports = tabData?.reports ?? [];

  const typeColors = {
    executive: "bg-blue-100 text-blue-700 border-blue-200",
    research: "bg-purple-100 text-purple-700 border-purple-200",
    funding: "bg-emerald-100 text-emerald-700 border-emerald-200",
    accreditation: "bg-amber-100 text-amber-700 border-amber-200",
  };

  const statusColors = {
    ready: "bg-emerald-100 text-emerald-700",
    generating: "bg-amber-100 text-amber-700",
    failed: "bg-red-100 text-red-700",
    pending: "bg-slate-100 text-slate-600",
  };

  async function handleGenerate(e) {
    e.preventDefault();
    if (!form.title.trim()) return;
    setGenerating(true);
    try {
      await api.post(`/institution-analytics/${id}/reports/generate`, form);
      setToast({ message: "Report generation started", type: "success" });
      setForm(f => ({ ...f, title: "" }));
      await onReload();
    } catch (err) {
      setToast({ message: err?.response?.data?.error ?? "Failed to generate report", type: "error" });
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="space-y-8">
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      {/* Report List */}
      <div className="bg-white border border-slate-200 rounded-md overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h3 className="text-base font-semibold text-slate-800">Generated Reports</h3>
        </div>
        {reports.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-sm">No reports generated yet. Use the form below to create your first report.</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {reports.map((r, i) => (
              <div key={i} className="px-6 py-4 flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${typeColors[r.report_type] ?? "bg-slate-100 text-slate-600 border-slate-200"}`}>
                      {fmt(r.report_type)}
                    </span>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded ${statusColors[r.status] ?? "bg-slate-100 text-slate-600"}`}>
                      {fmt(r.status)}
                    </span>
                  </div>
                  <p className="font-medium text-slate-800 mt-1 truncate">{fmt(r.title)}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{formatDate(r.created_at)}</p>
                </div>
                <button
                  onClick={() => setToast({ message: "Export coming soon", type: "success" })}
                  className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50 transition-colors shrink-0"
                >
                  <Download size={13} /> Download
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Generate Form */}
      <div className="bg-white border border-slate-200 rounded-md p-6">
        <SectionHeading title="Generate New Report" subtitle="Create a structured institutional report" />
        <form onSubmit={handleGenerate} className="space-y-4 max-w-lg">
          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1.5">Report Type</label>
            <select
              value={form.report_type}
              onChange={e => setForm(f => ({ ...f, report_type: e.target.value }))}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="executive">Executive Summary</option>
              <option value="research">Research Output</option>
              <option value="funding">Funding & Grants</option>
              <option value="accreditation">Accreditation Report</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1.5">Report Title</label>
            <input
              type="text"
              value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              placeholder="e.g. Annual Research Performance Review 2026"
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            type="submit"
            disabled={generating || !form.title.trim()}
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white rounded-lg disabled:opacity-60 transition-opacity"
            style={{ backgroundColor: "#0F2847" }}
          >
            <PlusCircle size={15} />
            {generating ? "Generating…" : "Generate Report"}
          </button>
        </form>
      </div>
    </div>
  );
}

// ── SETTINGS TAB ──────────────────────────────────────────────────────────────

function SettingsTab({ id }) {
  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded-md p-6">
        <SectionHeading title="Analytics Settings" subtitle="Configure data collection and reporting preferences" />
        <div className="space-y-4">
          <div className="py-3 border-b border-slate-100 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-800">Analytics Center</p>
              <p className="text-xs text-slate-500 mt-0.5">Institution ID: {id}</p>
            </div>
            <Link
              to={`/institution-hub/${id}`}
              className="text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors flex items-center gap-1.5"
            >
              <Building2 size={13} /> Institution Hub
            </Link>
          </div>
          <div className="py-3 border-b border-slate-100 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-800">Admin Console</p>
              <p className="text-xs text-slate-500 mt-0.5">Manage members, settings, and permissions</p>
            </div>
            <Link
              to={`/institution-admin/${id}`}
              className="text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors flex items-center gap-1.5"
            >
              <Settings size={13} /> Admin Console
            </Link>
          </div>
          <div className="py-3 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-800">Leaderboards</p>
              <p className="text-xs text-slate-500 mt-0.5">View institutional rankings and comparisons</p>
            </div>
            <Link
              to={`/institution-leaderboards/${id}`}
              className="text-xs font-medium px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors flex items-center gap-1.5"
            >
              <Trophy size={13} /> Leaderboards
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

// We need Trophy in the import — adding it via a helper since it's not imported
function Trophy({ size = 16, className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
      <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
      <path d="M4 22h16" />
      <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" />
      <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" />
      <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
    </svg>
  );
}

// ── MAIN COMPONENT ────────────────────────────────────────────────────────────

const TABS = [
  { id: "executive", label: "Executive" },
  { id: "performance", label: "Performance" },
  { id: "researchers", label: "Researchers" },
  { id: "departments", label: "Departments" },
  { id: "grants", label: "Grants" },
  { id: "collaborations", label: "Collaborations" },
  { id: "benchmarks", label: "Benchmarks" },
  { id: "forecasts", label: "Forecasts" },
  { id: "reports", label: "Reports" },
  { id: "settings", label: "Settings" },
];

export default function InstitutionAnalyticsCenter() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState("executive");
  const [kpis, setKpis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [kpiError, setKpiError] = useState(null);
  const [tabData, setTabData] = useState({});
  const [tabLoading, setTabLoading] = useState({});
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState(null);
  const loadedTabs = useRef(new Set());

  // ── Load KPIs on mount ──────────────────────────────────────────────────────

  const loadKpis = useCallback(async () => {
    try {
      const res = await api.get(`/institution-analytics/${id}/kpis`);
      setKpis(res.data);
    } catch (e) {
      setKpiError(e?.response?.data?.error ?? "Failed to load KPIs");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadKpis();
  }, [loadKpis]);

  // ── Lazy tab loader ─────────────────────────────────────────────────────────

  const loadTab = useCallback(async (tab, force = false) => {
    if (!force && loadedTabs.current.has(tab)) return;
    loadedTabs.current.add(tab);
    setTabLoading(prev => ({ ...prev, [tab]: true }));

    try {
      let updates = {};

      if (tab === "executive") {
        const snapshotRes = await api.get(`/institution-analytics/${id}/snapshot`);
        updates.snapshot = snapshotRes.data;
      }

      if (tab === "performance") {
        const [perfRes, trendsRes] = await Promise.allSettled([
          api.get(`/institution-analytics/${id}/performance`),
          api.get(`/institution-analytics/${id}/performance/trends`),
        ]);
        updates.performance = {
          ...(perfRes.status === "fulfilled" ? perfRes.value.data : {}),
          ...(trendsRes.status === "fulfilled" ? trendsRes.value.data : {}),
        };
      }

      if (tab === "researchers") {
        const [topRes, growRes] = await Promise.allSettled([
          api.get(`/institution-analytics/${id}/researchers/top`),
          api.get(`/institution-analytics/${id}/researchers/fastest-growing`),
        ]);
        updates.researchers_top = topRes.status === "fulfilled" ? (topRes.value.data?.researchers ?? topRes.value.data) : [];
        updates.researchers_growing = growRes.status === "fulfilled" ? (growRes.value.data?.researchers ?? growRes.value.data) : [];
      }

      if (tab === "departments") {
        const res = await api.get(`/institution-analytics/${id}/departments`);
        updates.departments = res.data?.departments ?? res.data ?? [];
      }

      if (tab === "grants") {
        const [perfRes, trendsRes] = await Promise.allSettled([
          api.get(`/institution-analytics/${id}/grants/performance`),
          api.get(`/institution-analytics/${id}/grants/trends`),
        ]);
        updates.grants_performance = perfRes.status === "fulfilled" ? perfRes.value.data : {};
        updates.grants_trends = trendsRes.status === "fulfilled" ? (trendsRes.value.data?.trends ?? trendsRes.value.data ?? []) : [];
      }

      if (tab === "collaborations") {
        const res = await api.get(`/institution-analytics/${id}/collaborations/analytics`);
        updates.collaborations = res.data;
      }

      if (tab === "benchmarks") {
        const res = await api.get(`/institution-analytics/${id}/benchmarks`);
        updates.benchmarks = res.data;
      }

      if (tab === "forecasts") {
        const res = await api.get(`/institution-analytics/${id}/forecasts`);
        updates.forecasts = res.data;
      }

      if (tab === "reports") {
        const res = await api.get(`/institution-analytics/${id}/reports`);
        updates.reports = res.data?.reports ?? res.data ?? [];
      }

      setTabData(prev => ({ ...prev, ...updates }));
    } catch (e) {
      // Tab load errors are non-fatal; data will be empty
    } finally {
      setTabLoading(prev => ({ ...prev, [tab]: false }));
    }
  }, [id]);

  // ── Activate tab ────────────────────────────────────────────────────────────

  function activateTab(tab) {
    setActiveTab(tab);
    loadTab(tab);
  }

  useEffect(() => {
    // Load executive tab data on first render (kpis already being fetched separately)
    loadTab("executive");
  }, [loadTab]);

  // ── Refresh KPIs ────────────────────────────────────────────────────────────

  async function handleRefreshKpis() {
    setRefreshing(true);
    try {
      await api.post(`/institution-analytics/${id}/kpis/refresh`);
      await loadKpis();
      // Also force-reload current tab
      loadedTabs.current.delete(activeTab);
      await loadTab(activeTab, true);
      setToast({ message: "KPIs refreshed successfully", type: "success" });
    } catch (e) {
      setToast({ message: e?.response?.data?.error ?? "Refresh failed", type: "error" });
    } finally {
      setRefreshing(false);
    }
  }

  // ── Reload a specific tab (used by sub-components) ──────────────────────────

  async function reloadTab(tab) {
    loadedTabs.current.delete(tab);
    await loadTab(tab, true);
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F4F6FA]">
        <div className="max-w-7xl mx-auto px-6 py-10 space-y-8">
          <div className="h-8 w-64 bg-slate-200 rounded animate-pulse" />
          <div className="grid grid-cols-4 gap-4">
            {[...Array(8)].map((_, i) => <CardSkeleton key={i} />)}
          </div>
        </div>
      </div>
    );
  }

  if (kpiError) {
    return (
      <div className="min-h-screen bg-[#F4F6FA] flex items-center justify-center">
        <div className="bg-white border border-red-200 rounded-md p-8 max-w-md text-center">
          <AlertCircle className="mx-auto text-red-500 mb-3" size={32} />
          <h2 className="font-semibold text-slate-800 mb-1">Unable to Load Analytics</h2>
          <p className="text-sm text-slate-500">{kpiError}</p>
          <button
            onClick={() => { setKpiError(null); setLoading(true); loadKpis(); }}
            className="mt-4 px-4 py-2 text-sm font-semibold text-white rounded-lg"
            style={{ backgroundColor: "#0F2847" }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const isTabLoading = tabLoading[activeTab];

  const tabBar = (
    <div className="flex gap-0 overflow-x-auto">
      {TABS.map(tab => (
        <button
          key={tab.id}
          onClick={() => activateTab(tab.id)}
          className={`px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
            activeTab === tab.id
              ? "border-b-2 text-slate-900"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
          style={activeTab === tab.id ? { borderColor: "#0F2847", color: "#0F2847" } : {}}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );

  return (
    <AnalyticsLayout
      title="Research Intelligence Center"
      subtitle={`Institution ID: ${id}`}
      actions={
        <>
          <Link
            to={`/institution-hub/${id}`}
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 transition-colors"
          >
            <ChevronLeft size={15} /> Institution Hub
          </Link>
          <button
            onClick={handleRefreshKpis}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 text-sm font-semibold border border-slate-200 text-slate-700 hover:bg-slate-50 disabled:opacity-60 transition-colors"
          >
            <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Refreshing…" : "Refresh KPIs"}
          </button>
        </>
      }
      nav={tabBar}
    >
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
      {isTabLoading ? (
        <TabSkeleton />
      ) : (
        <>
          {activeTab === "executive" && <ExecutiveTab kpis={kpis} tabData={tabData} />}
          {activeTab === "performance" && <PerformanceTab tabData={tabData} />}
          {activeTab === "researchers" && <ResearchersTab tabData={tabData} />}
          {activeTab === "departments" && <DepartmentsTab tabData={tabData} />}
          {activeTab === "grants" && <GrantsTab tabData={tabData} />}
          {activeTab === "collaborations" && <CollaborationsTab tabData={tabData} />}
          {activeTab === "benchmarks" && <BenchmarksTab tabData={tabData} />}
          {activeTab === "forecasts" && (
            <ForecastsTab
              id={id}
              tabData={tabData}
              user={user}
              onReload={() => reloadTab("forecasts")}
            />
          )}
          {activeTab === "reports" && (
            <ReportsTab
              id={id}
              tabData={tabData}
              onReload={() => reloadTab("reports")}
            />
          )}
          {activeTab === "settings" && <SettingsTab id={id} />}
        </>
      )}
    </AnalyticsLayout>
  );
}
