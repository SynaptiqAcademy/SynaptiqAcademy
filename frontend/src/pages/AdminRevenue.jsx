/**
 * AdminRevenue — Super Admin revenue dashboard.
 *
 * Endpoint: GET /api/admin/revenue (super_admin only)
 * Layout uses the same editorial vocabulary as the rest of the platform.
 */
import React, { useEffect, useState } from "react";
import api from "../lib/api";
import { TrendingUp, Users, Zap, AlertTriangle } from "lucide-react";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";

export default function AdminRevenue() {
  const [data, setData] = useState(null);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    api.get("/admin/revenue")
      .then((r) => setData(r.data))
      .catch((e) => { if (e?.response?.status === 403) setDenied(true); });
  }, []);

  if (denied) return (
    <div className="p-12 max-w-2xl mx-auto" data-testid="admin-revenue-denied">
      <div className="overline">Restricted</div>
      <h1 className="font-serif text-3xl text-slate-900 mt-2">Super Admin only</h1>
      <p className="text-slate-700 mt-3">You don't have permission to view this page.</p>
    </div>
  );
  if (!data) return (
    <div className="p-12 max-w-7xl mx-auto" data-testid="admin-revenue-loading">
      <div className="overline">Loading</div>
      <h1 className="font-serif text-3xl text-slate-900 mt-2">Revenue dashboard</h1>
    </div>
  );

  const u = data.users, r = data.revenue, c = data.credits, ch = data.churn;
  return (
    <AdministrationLayout title="Revenue" subtitle="Live aggregates from the production database. No mocks." data-testid="admin-revenue">
      {/* KPI tiles */}
      <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Tile icon={<TrendingUp size={14}/>} label="MRR" value={`€${r.mrr_eur.toLocaleString()}`} sub={`ARR €${r.arr_eur.toLocaleString()}`} testId="kpi-mrr"/>
        <Tile icon={<Users    size={14}/>}   label="Active subscribers" value={u.active_subscribers} sub={`${u.total} total users`} testId="kpi-active-subs"/>
        <Tile icon={<Zap      size={14}/>}   label="Credits consumed (30d)" value={c.consumed_30d.toLocaleString()} sub={`${c.purchased_30d.toLocaleString()} purchased`} testId="kpi-credits"/>
        <Tile icon={<AlertTriangle size={14}/>} label="Churn (30d)" value={`${ch.churn_rate_pct}%`} sub={`${ch.churned_30d} subs cancelled`} testId="kpi-churn"/>
      </div>

      {/* Plan breakdown */}
      <section className="mt-10 border border-slate-200 bg-white p-6" data-testid="plan-breakdown">
        <div className="overline">Users by plan</div>
        <h2 className="font-serif text-2xl text-slate-900 mt-1">Plan distribution</h2>
        <div className="mt-5 grid grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
          {["free","researcher","pro_researcher","institution"].map((p) => (
            <div key={p} className="border border-slate-200 p-4" data-testid={`plan-tile-${p}`}>
              <div className="overline">{p.replace("_"," ")}</div>
              <div className="font-serif text-3xl text-slate-900 mt-1">{u[p] ?? 0}</div>
              <div className="text-xs text-slate-500 mt-1">{((u[p] ?? 0) / Math.max(u.total,1) * 100).toFixed(1)}%</div>
            </div>
          ))}
        </div>
      </section>

      {/* Weekly revenue trend */}
      <section className="mt-10 mb-12 border border-slate-200 bg-white p-6" data-testid="revenue-trend">
        <div className="overline">Last 12 weeks</div>
        <h2 className="font-serif text-2xl text-slate-900 mt-1">Revenue trend</h2>
        <div className="mt-5 flex items-end gap-2 h-40">
          {(data.revenue_trend_weekly || []).map((w) => {
            const max = Math.max(...(data.revenue_trend_weekly || []).map((x) => x.amount_eur), 1);
            const h = Math.max(4, (w.amount_eur / max) * 100);
            return (
              <div key={w.week_start} className="flex-1 flex flex-col items-center" title={`${w.week_start}: €${w.amount_eur}`}>
                <div className="w-full bg-[#0F2847]" style={{ height: `${h}%` }} />
                <div className="text-[10px] text-slate-400 mt-1 font-mono">{w.week_start.slice(5)}</div>
              </div>
            );
          })}
        </div>
        <div className="mt-3 text-xs text-slate-500">Includes invoice payments + credit pack purchases.</div>
      </section>
    </AdministrationLayout>
  );
}

function Tile({ icon, label, value, sub, testId }) {
  return (
    <div className="border border-slate-200 bg-white p-5" data-testid={testId}>
      <div className="flex items-center gap-2 text-slate-500 overline">
        {icon}<span>{label}</span>
      </div>
      <div className="font-serif text-3xl text-slate-900 mt-2">{value}</div>
      <div className="text-xs text-slate-500 mt-1">{sub}</div>
    </div>
  );
}
