import React, { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  ResponsiveContainer, LineChart, Line,
} from "recharts";
import { BookOpen, ClipboardCheck, FolderOpen, Users, Sparkles, Award, RefreshCw } from "lucide-react";
import api from "../../lib/api";
import { toast } from "sonner";
import { NAVY } from "@/lib/tokens";
import { SkeletonCard } from "@/components/ds/LoadingState";
import { AdministrationLayout } from "@/layouts";

function StatBox({ label, value, icon: Icon }) {
  return (
    <div className="border border-slate-200 bg-white p-5">
      <div className="flex items-start justify-between">
        <div>
          <div className="overline text-slate-500">{label}</div>
          <div className="font-serif text-3xl text-slate-900 mt-1">{value ?? "—"}</div>
        </div>
        {Icon && <Icon size={18} strokeWidth={1.5} className="text-slate-300 mt-1 shrink-0" />}
      </div>
    </div>
  );
}

function SectionTitle({ children }) {
  return <div className="overline mb-4">{children}</div>;
}

function DistChart({ data, color = "#0F2847", height = 180 }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center bg-slate-50 border border-dashed border-slate-200" style={{ height }}>
        <span className="text-xs text-slate-400">No data yet</span>
      </div>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 9, fill: "#94a3b8" }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 9, fill: "#94a3b8" }} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip contentStyle={{ border: "1px solid #e2e8f0", fontSize: 12, borderRadius: 0 }} />
        <Bar dataKey="count" fill={color} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function TrendChart({ data, color = "#0F2847", height = 160 }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center bg-slate-50 border border-dashed border-slate-200" style={{ height }}>
        <span className="text-xs text-slate-400">No activity yet</span>
      </div>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="date" tick={{ fontSize: 9, fill: "#94a3b8" }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 9, fill: "#94a3b8" }} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip contentStyle={{ border: "1px solid #e2e8f0", fontSize: 12, borderRadius: 0 }} />
        <Line type="monotone" dataKey="count" stroke={color} strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export default function AdminTeachingAnalytics() {
  const [data, setData]   = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const { data: d } = await api.get("/teaching-analytics/admin/overview");
      setData(d);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to load teaching analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <div className="p-6"><SkeletonCard rows={4} /></div>;
  if (!data)   return null;

  const totals = data.platform_totals || {};
  const last30 = data.last_30d || {};

  return (
    <AdministrationLayout
      title="Teaching Analytics"
      subtitle="Platform-wide teaching activity intelligence"
      actions={
        <button
          onClick={load}
          className="inline-flex items-center gap-1.5 text-sm border border-slate-300 px-4 py-2 text-slate-600 hover:border-[#0F2847] hover:text-[#0F2847]"
        >
          <RefreshCw size={13} strokeWidth={1.5} /> Refresh
        </button>
      }
    >

      {/* Platform totals */}
      <section>
        <SectionTitle>Platform totals</SectionTitle>
        <div className="grid sm:grid-cols-3 lg:grid-cols-4 gap-4">
          <StatBox label="Active Educators"  value={totals.active_educators}  icon={Users}        />
          <StatBox label="Lessons"           value={totals.lessons}           icon={BookOpen}     />
          <StatBox label="Assessments"       value={totals.assessments}       icon={ClipboardCheck} />
          <StatBox label="Workspaces"        value={totals.workspaces}        icon={FolderOpen}   />
          <StatBox label="Portfolio Items"   value={totals.portfolio_items}   icon={Award}        />
          <StatBox label="AI Messages"       value={totals.ai_messages}       icon={Sparkles}     />
        </div>
      </section>

      {/* Last 30 days */}
      <section>
        <SectionTitle>Last 30 days</SectionTitle>
        <div className="grid sm:grid-cols-3 gap-4">
          <StatBox label="Lessons Created"    value={last30.lessons}      icon={BookOpen}      />
          <StatBox label="Assessments Created" value={last30.assessments} icon={ClipboardCheck} />
          <StatBox label="AI Messages"        value={last30.ai_messages}  icon={Sparkles}      />
        </div>
      </section>

      {/* Workspace activity trend */}
      <section>
        <SectionTitle>Workspace activity (30d)</SectionTitle>
        <TrendChart data={data.workspace_activity_trend} />
      </section>

      {/* Subject + level + assessment type distribution */}
      <section className="grid sm:grid-cols-2 lg:grid-cols-3 gap-8">
        <div>
          <SectionTitle>Subject distribution</SectionTitle>
          <DistChart data={data.subject_distribution} height={200} />
        </div>
        <div>
          <SectionTitle>Level distribution</SectionTitle>
          <DistChart data={data.level_distribution} color="#10b981" height={200} />
        </div>
        <div>
          <SectionTitle>Assessment types</SectionTitle>
          <DistChart data={data.assessment_type_distribution} color="#94a3b8" height={200} />
        </div>
      </section>

      {/* Top educators */}
      <section>
        <SectionTitle>Most active educators (by lesson count)</SectionTitle>
        <div className="border border-slate-200 bg-white divide-y divide-slate-100">
          {(data.top_educators || []).length === 0 && (
            <div className="px-6 py-8 text-sm text-slate-400 text-center italic">No lesson data yet.</div>
          )}
          {(data.top_educators || []).map((u, i) => (
            <div key={i} className="px-5 py-4 flex items-center gap-4">
              <div className="text-xs text-slate-400 font-mono w-5 shrink-0">{i + 1}</div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-slate-900 truncate">{u.name}</div>
                <div className="text-xs text-slate-500 truncate">{u.institution || "—"}</div>
              </div>
              <div className="text-sm font-mono text-slate-700 shrink-0">{u.lessons} lessons</div>
            </div>
          ))}
        </div>
      </section>
    </AdministrationLayout>
  );
}
