/**
 * DeadlinesWidget — used by Workspace dashboard, Project dashboard, and the
 * top-level user dashboard. Calls /api/deadlines/mine (optionally scoped).
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../../lib/api";
import { Clock, AlertOctagon, AlertCircle, Calendar } from "lucide-react";

const URGENCY = {
  missed:    { tone: "border-red-300 bg-red-50 text-red-700",          icon: AlertOctagon, label: "Missed" },
  critical:  { tone: "border-amber-400 bg-amber-50 text-amber-800",    icon: AlertCircle,  label: "Critical" },
  due_soon:  { tone: "border-amber-200 bg-amber-50 text-amber-700",    icon: Clock,        label: "Due soon" },
  upcoming:  { tone: "border-slate-200 bg-slate-50 text-slate-600",    icon: Calendar,     label: "Upcoming" },
};

export default function DeadlinesWidget({ workspaceId, projectId, limit = 6, initialItems = null }) {
  const [items, setItems] = useState(initialItems || []);
  const [counts, setCounts] = useState({});
  const [loading, setLoading] = useState(!initialItems);

  useEffect(() => {
    if (initialItems) return;  // parent already supplied items
    const params = {};
    if (workspaceId) params.workspace_id = workspaceId;
    if (projectId) params.project_id = projectId;
    params.limit = limit;
    setLoading(true);
    api.get("/deadlines/mine", { params })
      .then(({ data }) => { setItems(data.items || []); setCounts(data.counts || {}); })
      .catch(() => { setItems([]); setCounts({}); })
      .finally(() => setLoading(false));
  }, [workspaceId, projectId, limit, initialItems]);

  return (
    <div className="border border-slate-200 bg-white p-5" data-testid="deadlines-widget">
      <div className="flex items-center justify-between mb-4">
        <div className="overline">Upcoming deadlines</div>
        {(counts.critical > 0 || counts.missed > 0) && (
          <span className="text-[10px] font-mono text-red-700">
            {counts.missed || 0} missed · {counts.critical || 0} critical
          </span>
        )}
      </div>
      {loading && <div className="text-xs text-slate-500 font-mono">Loading…</div>}
      {!loading && items.length === 0 && (
        <div className="text-sm text-slate-500">No deadlines yet. Add a target venue or save a grant to start tracking.</div>
      )}
      <ul className="space-y-3">
        {items.map((d, i) => {
          const u = URGENCY[d.urgency] || URGENCY.upcoming;
          const Icon = u.icon;
          return (
            <li key={i}>
              <Link to={d.link || "#"} className="block border-l-2 pl-3 py-1 hover:bg-slate-50 transition-colors" style={{ borderColor: d.urgency === "missed" ? "#dc2626" : d.urgency === "critical" ? "#f59e0b" : d.urgency === "due_soon" ? "#fbbf24" : "#cbd5e1" }}>
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm text-slate-900 truncate">{d.label}</div>
                    <div className="text-[10px] font-mono text-slate-500 mt-0.5 capitalize">{d.kind?.replace(/_/g, " ")}</div>
                  </div>
                  <div className={`overline border px-1.5 py-0.5 inline-flex items-center gap-1 shrink-0 ${u.tone}`}>
                    <Icon size={10} strokeWidth={1.5}/> {d.date || "TBD"}
                  </div>
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
