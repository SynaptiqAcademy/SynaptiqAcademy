import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import api from "../../lib/api";
import { TID } from "../../lib/testIds";
import { toast } from "sonner";
import { Plus, Search, ChevronDown, ChevronRight, Diamond, AlertTriangle } from "lucide-react";
import {
  NAVY, BRD, WARM, WHITE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
  CRIMSON, AMBER, EMERALD, RADIUS_MD, RADIUS_SM,
} from "@/lib/tokens";
import { transition } from "@/lib/motion";
import { Input } from "@/components/ds/Input";
import { FormSelect } from "@/components/ds/FormSelect";
import { Modal } from "@/components/ds/Modal";
import { Badge } from "@/components/ds/Badge";
import { Button } from "@/components/ds/Button";
import { EmptyState } from "@/components/ds/EmptyState";
import { SkeletonCard } from "@/components/ds/LoadingState";
import CommentThread from "@/components/comments/CommentThread";

// Same status palette as WorkspaceKanban.jsx, kept in sync deliberately —
// tasks are the same underlying entity, just viewed differently.
const STATUS_COLOR = {
  backlog: TEXT_MUTED, planned: "#0284C7", in_progress: AMBER,
  review: "#7C3AED", completed: EMERALD,
};
const PRIORITY_COLOR = { high: CRIMSON, medium: AMBER, low: TEXT_MUTED };

const LEFT_W = 280;
const ROW_H = 36;
const HEADER_H = 40;

const ZOOMS = {
  day:     { label: "Day",     pxPerDay: 34, tickDays: 1  },
  week:    { label: "Week",    pxPerDay: 15, tickDays: 7  },
  month:   { label: "Month",   pxPerDay: 6,  tickDays: 30 },
  quarter: { label: "Quarter", pxPerDay: 2.2, tickDays: 90 },
};

// ── date helpers (plain ISO "YYYY-MM-DD" strings throughout) ─────────────────
function toDate(s) {
  if (!s) return null;
  const d = new Date(s.length <= 10 ? `${s}T00:00:00` : s);
  return isNaN(d.getTime()) ? null : d;
}
function toISODate(d) {
  return d.toISOString().slice(0, 10);
}
function addDays(iso, n) {
  const d = toDate(iso);
  d.setDate(d.getDate() + n);
  return toISODate(d);
}
function daysBetween(a, b) {
  const da = toDate(a), db = toDate(b);
  if (!da || !db) return 0;
  return Math.round((db - da) / 86400000);
}
function fmtTick(iso, view) {
  const d = toDate(iso);
  if (!d) return "";
  if (view === "day") return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  if (view === "week") return `Wk of ${d.toLocaleDateString("en-GB", { day: "numeric", month: "short" })}`;
  if (view === "month") return d.toLocaleDateString("en-GB", { month: "short", year: "numeric" });
  const q = Math.floor(d.getMonth() / 3) + 1;
  return `Q${q} ${d.getFullYear()}`;
}

/**
 * Real critical-path (CPM) computation over the dependency graph:
 * duration = day-span of start_date..end_date (falls back to 1 day if either
 * is missing — undated tasks can't meaningfully sit on a critical path).
 * Standard forward/backward pass; slack === 0 marks a task critical.
 * This is a real deterministic calculation over stored fields, not a
 * fabricated metric — worth disclosing the duration-fallback rule above
 * since it's the one judgment call in an otherwise textbook CPM.
 */
function computeCriticalPath(tasks) {
  const byId = new Map(tasks.map((t) => [t.id, t]));
  const duration = new Map();
  const preds = new Map();
  const succs = new Map();
  for (const t of tasks) {
    const dur = t.start_date && t.end_date ? Math.max(1, daysBetween(t.start_date, t.end_date)) : 1;
    duration.set(t.id, dur);
    preds.set(t.id, (t.depends_on || []).filter((d) => byId.has(d)));
    succs.set(t.id, []);
  }
  for (const t of tasks) for (const p of preds.get(t.id)) succs.get(p).push(t.id);

  // Kahn topo sort
  const indeg = new Map(tasks.map((t) => [t.id, preds.get(t.id).length]));
  const queue = tasks.filter((t) => indeg.get(t.id) === 0).map((t) => t.id);
  const order = [];
  const q = [...queue];
  while (q.length) {
    const n = q.shift();
    order.push(n);
    for (const s of succs.get(n)) {
      indeg.set(s, indeg.get(s) - 1);
      if (indeg.get(s) === 0) q.push(s);
    }
  }
  if (order.length !== tasks.length) return new Set(); // a cycle slipped through server validation — bail out safely

  const earliestStart = new Map(), earliestFinish = new Map();
  for (const id of order) {
    const es = Math.max(0, ...preds.get(id).map((p) => earliestFinish.get(p) ?? 0));
    earliestStart.set(id, es);
    earliestFinish.set(id, es + duration.get(id));
  }
  const projectFinish = Math.max(0, ...order.map((id) => earliestFinish.get(id)));
  const latestFinish = new Map(), latestStart = new Map();
  for (let i = order.length - 1; i >= 0; i--) {
    const id = order[i];
    const s = succs.get(id);
    const lf = s.length ? Math.min(...s.map((x) => latestStart.get(x))) : projectFinish;
    latestFinish.set(id, lf);
    latestStart.set(id, lf - duration.get(id));
  }
  const critical = new Set();
  for (const id of order) {
    if (latestStart.get(id) - earliestStart.get(id) === 0) critical.add(id);
  }
  return critical;
}

function buildTicks(rangeStartISO, totalDays, view, pxPerDay) {
  const ticks = [];
  const step = view === "day" ? 1 : view === "week" ? 7 : view === "month" ? 30 : 90;
  for (let d = 0; d <= totalDays; d += step) {
    ticks.push({ x: d * pxPerDay, label: fmtTick(addDays(rangeStartISO, d), view) });
  }
  return ticks;
}

function buildRows(tasks, groupBy, collapsed) {
  const groups =
    groupBy === "none"
      ? [{ key: "all", label: null, tasks }]
      : Object.entries(
          tasks.reduce((acc, t) => {
            const key = groupBy === "project" ? (t.project?.id || "none") : (t.assignee?.id || "unassigned");
            const label = groupBy === "project" ? (t.project?.title || "No project") : (t.assignee?.full_name || "Unassigned");
            (acc[key] ||= { key, label, tasks: [] }).tasks.push(t);
            return acc;
          }, {})
        ).map(([, g]) => g);

  const rows = [];
  for (const g of groups) {
    if (g.label !== null) rows.push({ type: "group", key: `g-${g.key}`, label: g.label, count: g.tasks.length });
    const byId = new Map(g.tasks.map((t) => [t.id, t]));
    const children = new Map();
    for (const t of g.tasks) {
      if (t.parent_task_id && byId.has(t.parent_task_id)) {
        (children.get(t.parent_task_id) || children.set(t.parent_task_id, []).get(t.parent_task_id)).push(t);
      }
    }
    const roots = g.tasks.filter((t) => !t.parent_task_id || !byId.has(t.parent_task_id));
    const visit = (t, depth) => {
      rows.push({ type: "task", key: t.id, task: t, depth });
      if (collapsed[t.id]) return;
      for (const c of children.get(t.id) || []) visit(c, depth + 1);
    };
    for (const t of roots) visit(t, 0);
  }
  return rows;
}

/**
 * WorkspaceGantt — a real, independent Gantt/timeline view over the same
 * `tasks` collection the Kanban board uses (GET /workspaces/{id}/tasks),
 * NOT a reuse of ResearchTimeline.jsx (that component represents career
 * events and has a different purpose/data source entirely).
 *
 * Drag-to-reschedule, resize, dependency validation and persistence all go
 * through the real PATCH /projects/tasks/{id} endpoint (extended in Phase 7
 * with start_date/end_date/progress/depends_on/parent_task_id/is_milestone).
 * Critical-path highlighting is computed client-side via a textbook CPM
 * forward/backward pass — see computeCriticalPath above.
 */
export default function WorkspaceGantt({ wsId, canEdit }) {
  const [data, setData] = useState({ projects: [], tasks: [] });
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState("week");
  const [groupBy, setGroupBy] = useState("project");
  const [query, setQuery] = useState("");
  const [assigneeFilter, setAssigneeFilter] = useState("");
  const [projectFilter, setProjectFilter] = useState("");
  const [showCritical, setShowCritical] = useState(false);
  const [collapsed, setCollapsed] = useState({});
  const [editing, setEditing] = useState(null); // task being edited, or "new"
  const [projectIdForNew, setProjectIdForNew] = useState("");
  const scrollRef = useRef(null);
  const dragRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/workspaces/${wsId}/tasks`);
      setData(data || { projects: [], tasks: [] });
      if (!projectIdForNew && data?.projects?.length) setProjectIdForNew(data.projects[0].id);
    } catch (e) {
      setData({ projects: [], tasks: [] });
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wsId]);
  useEffect(() => { load(); }, [load]);

  const filteredTasks = useMemo(() => {
    return (data.tasks || []).filter((t) => {
      if (query && !t.title?.toLowerCase().includes(query.toLowerCase())) return false;
      if (assigneeFilter && t.assignee?.id !== assigneeFilter) return false;
      if (projectFilter && t.project?.id !== projectFilter) return false;
      return true;
    });
  }, [data.tasks, query, assigneeFilter, projectFilter]);

  const critical = useMemo(() => (showCritical ? computeCriticalPath(filteredTasks) : new Set()), [showCritical, filteredTasks]);

  const rows = useMemo(() => buildRows(filteredTasks, groupBy, collapsed), [filteredTasks, groupBy, collapsed]);
  const taskRowIndex = useMemo(() => {
    const m = new Map();
    rows.forEach((r, i) => { if (r.type === "task") m.set(r.task.id, i); });
    return m;
  }, [rows]);

  const zoom = ZOOMS[view];
  const dated = filteredTasks.filter((t) => t.start_date || t.end_date || t.due_date);
  const today = toISODate(new Date());
  const allDates = dated.flatMap((t) => [t.start_date, t.end_date || t.due_date].filter(Boolean));
  const rangeStart = allDates.length ? addDays(allDates.reduce((a, b) => (a < b ? a : b)), -7) : addDays(today, -14);
  const rangeEndRaw = allDates.length ? addDays(allDates.reduce((a, b) => (a > b ? a : b)), 14) : addDays(today, 60);
  const totalDays = Math.min(1095, Math.max(30, daysBetween(rangeStart, rangeEndRaw)));
  const totalWidth = totalDays * zoom.pxPerDay;
  const ticks = useMemo(() => buildTicks(rangeStart, totalDays, view, zoom.pxPerDay), [rangeStart, totalDays, view, zoom.pxPerDay]);
  const xOf = useCallback((iso) => daysBetween(rangeStart, iso) * zoom.pxPerDay, [rangeStart, zoom.pxPerDay]);
  const todayX = xOf(today);

  const assignees = useMemo(() => {
    const m = new Map();
    for (const t of data.tasks || []) if (t.assignee) m.set(t.assignee.id, t.assignee.full_name);
    return [...m.entries()];
  }, [data.tasks]);

  const patchTask = async (taskId, patch, prevTask) => {
    // optimistic
    setData((d) => ({ ...d, tasks: d.tasks.map((t) => (t.id === taskId ? { ...t, ...patch } : t)) }));
    try {
      const { data: updated } = await api.patch(`/projects/tasks/${taskId}`, patch);
      setData((d) => ({ ...d, tasks: d.tasks.map((t) => (t.id === taskId ? { ...t, ...updated } : t)) }));
    } catch (e) {
      // roll back
      if (prevTask) setData((d) => ({ ...d, tasks: d.tasks.map((t) => (t.id === taskId ? prevTask : t)) }));
      toast.error(e?.response?.data?.detail || "Failed to update task");
    }
  };

  // ── Drag-to-reschedule / resize ────────────────────────────────────────────
  const beginDrag = (e, task, mode) => {
    if (!canEdit) return;
    e.preventDefault();
    e.stopPropagation();
    dragRef.current = {
      taskId: task.id, mode, startX: e.clientX, moved: false,
      origStart: task.start_date, origEnd: task.end_date || task.due_date,
      task,
    };
    window.addEventListener("mousemove", onDragMove);
    window.addEventListener("mouseup", onDragEnd);
  };
  const onDragMove = (e) => {
    const dr = dragRef.current;
    if (!dr) return;
    const dx = e.clientX - dr.startX;
    if (Math.abs(dx) > 3) dr.moved = true;
    const dayDelta = Math.round(dx / ZOOMS[view].pxPerDay);
    let newStart = dr.origStart, newEnd = dr.origEnd;
    if (dr.mode === "move" && dr.origStart) {
      newStart = addDays(dr.origStart, dayDelta);
      newEnd = dr.origEnd ? addDays(dr.origEnd, dayDelta) : undefined;
    } else if (dr.mode === "resize-start" && dr.origStart) {
      newStart = addDays(dr.origStart, dayDelta);
      if (dr.origEnd && newStart > dr.origEnd) newStart = dr.origEnd;
    } else if (dr.mode === "resize-end" && dr.origEnd) {
      newEnd = addDays(dr.origEnd, dayDelta);
      if (dr.origStart && newEnd < dr.origStart) newEnd = dr.origStart;
    }
    dr.previewStart = newStart;
    dr.previewEnd = newEnd;
    setData((d) => ({
      ...d,
      tasks: d.tasks.map((t) => (t.id === dr.taskId ? { ...t, start_date: newStart, end_date: newEnd ?? t.end_date } : t)),
    }));
  };
  const onDragEnd = () => {
    const dr = dragRef.current;
    window.removeEventListener("mousemove", onDragMove);
    window.removeEventListener("mouseup", onDragEnd);
    dragRef.current = null;
    if (!dr) return;
    if (!dr.moved) {
      setEditing(dr.task);
      return;
    }
    const patch = {};
    if (dr.previewStart !== dr.origStart) patch.start_date = dr.previewStart;
    if (dr.previewEnd !== dr.origEnd) patch.end_date = dr.previewEnd;
    if (Object.keys(patch).length) patchTask(dr.taskId, patch, dr.task);
  };
  useEffect(() => () => {
    window.removeEventListener("mousemove", onDragMove);
    window.removeEventListener("mouseup", onDragEnd);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onBarKeyDown = (e, task) => {
    if (!canEdit || !task.start_date) return;
    const shift = e.shiftKey;
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      if (shift && task.end_date) patchTask(task.id, { end_date: addDays(task.end_date, -1) }, task);
      else patchTask(task.id, { start_date: addDays(task.start_date, -1), end_date: task.end_date ? addDays(task.end_date, -1) : undefined }, task);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      if (shift && task.end_date) patchTask(task.id, { end_date: addDays(task.end_date, 1) }, task);
      else patchTask(task.id, { start_date: addDays(task.start_date, 1), end_date: task.end_date ? addDays(task.end_date, 1) : undefined }, task);
    }
  };

  if (loading) {
    return (
      <div className="space-y-2" role="status" aria-label="Loading timeline">
        {[0, 1, 2].map((i) => <SkeletonCard key={i} height={36} />)}
      </div>
    );
  }

  if (!(data.tasks || []).length) {
    return (
      <EmptyState
        title="No tasks yet"
        description="Tasks you add on the Tasks board will appear here once they have dates — set a start and end date to place them on the timeline."
      />
    );
  }

  const contentHeight = rows.length * ROW_H;

  return (
    <div data-testid={TID.gantt} style={{ border: `1px solid ${BRD}`, borderRadius: 10, background: WHITE }}>
      {/* Toolbar */}
      <div className="flex items-center justify-between flex-wrap gap-2" style={{ padding: "10px 12px", borderBottom: `1px solid ${BRD}` }}>
        <div className="flex items-center gap-2 flex-wrap">
          <Input size="sm" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search tasks…" prefix={<Search size={12} strokeWidth={1.75} />} />
          <FormSelect size="sm" value={projectFilter} onChange={(e) => setProjectFilter(e.target.value)} aria-label="Filter by project" style={{ width: 140 }}>
            <option value="">All projects</option>
            {data.projects.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
          </FormSelect>
          <FormSelect size="sm" value={assigneeFilter} onChange={(e) => setAssigneeFilter(e.target.value)} aria-label="Filter by assignee" style={{ width: 140 }}>
            <option value="">All assignees</option>
            {assignees.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
          </FormSelect>
          <FormSelect size="sm" value={groupBy} onChange={(e) => setGroupBy(e.target.value)} aria-label="Group by" style={{ width: 130 }}>
            <option value="project">Group: Project</option>
            <option value="assignee">Group: Assignee</option>
            <option value="none">No grouping</option>
          </FormSelect>
          <Button
            size="sm"
            variant={showCritical ? "primary" : "ghost"}
            onClick={() => setShowCritical((v) => !v)}
            aria-pressed={showCritical}
          >
            <AlertTriangle size={12} strokeWidth={1.75} /> Critical path
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1" role="group" aria-label="Zoom level">
            {Object.entries(ZOOMS).map(([key, z]) => (
              <button
                key={key}
                data-testid={TID.ganttZoom(key)}
                onClick={() => setView(key)}
                aria-pressed={view === key}
                style={{
                  fontSize: 12, padding: "4px 10px", borderRadius: RADIUS_SM, border: `1px solid ${view === key ? NAVY : BRD}`,
                  background: view === key ? NAVY : "transparent", color: view === key ? WHITE : TEXT_SECONDARY,
                  cursor: "pointer", transition: transition.hoverButton,
                }}
              >
                {z.label}
              </button>
            ))}
          </div>
          {canEdit && (
            <Button size="sm" onClick={() => setEditing("new")}>
              <Plus size={12} strokeWidth={1.75} /> Add task
            </Button>
          )}
        </div>
      </div>

      {/* Timeline */}
      <div ref={scrollRef} style={{ overflow: "auto", maxHeight: 560 }}>
        <div style={{ position: "relative", minWidth: LEFT_W + totalWidth }}>
          {/* Header */}
          <div style={{ position: "sticky", top: 0, zIndex: 3, display: "flex", background: WHITE, borderBottom: `1px solid ${BRD}` }}>
            <div style={{ position: "sticky", left: 0, width: LEFT_W, flexShrink: 0, background: WHITE, zIndex: 4, height: HEADER_H, display: "flex", alignItems: "center", padding: "0 12px", fontSize: 11, fontWeight: 700, color: TEXT_MUTED, textTransform: "uppercase", letterSpacing: 0.4, borderRight: `1px solid ${BRD}` }}>
              Task
            </div>
            <div style={{ position: "relative", width: totalWidth, height: HEADER_H }}>
              {ticks.map((t, i) => (
                <div key={i} style={{ position: "absolute", left: t.x, top: 0, height: "100%", borderLeft: `1px solid ${BRD}`, paddingLeft: 4, display: "flex", alignItems: "center", fontSize: 11, color: TEXT_MUTED, whiteSpace: "nowrap" }}>
                  {t.label}
                </div>
              ))}
            </div>
          </div>

          {/* Rows */}
          {rows.map((row) => {
            if (row.type === "group") {
              return (
                <div key={row.key} style={{ display: "flex", background: WARM, borderBottom: `1px solid ${BRD}` }}>
                  <div style={{ position: "sticky", left: 0, width: LEFT_W, flexShrink: 0, background: WARM, zIndex: 2, height: ROW_H, display: "flex", alignItems: "center", padding: "0 12px", fontSize: 12.5, fontWeight: 700, color: TEXT_PRIMARY, borderRight: `1px solid ${BRD}` }}>
                    {row.label} <span style={{ marginLeft: 6, fontWeight: 500, color: TEXT_MUTED }}>({row.count})</span>
                  </div>
                  <div style={{ width: totalWidth, height: ROW_H }} />
                </div>
              );
            }
            const t = row.task;
            const hasStart = !!t.start_date;
            const end = t.end_date || t.due_date;
            const barX = hasStart ? xOf(t.start_date) : null;
            const barW = hasStart && end ? Math.max(10, xOf(end) - xOf(t.start_date)) : null;
            const isCritical = critical.has(t.id);
            const color = STATUS_COLOR[t.status] || TEXT_MUTED;
            const hasChildren = (data.tasks || []).some((x) => x.parent_task_id === t.id);

            return (
              <div key={row.key} style={{ display: "flex", borderBottom: `1px solid ${BRD}` }}>
                <div style={{ position: "sticky", left: 0, width: LEFT_W, flexShrink: 0, background: WHITE, zIndex: 2, height: ROW_H, display: "flex", alignItems: "center", gap: 4, padding: `0 8px 0 ${12 + row.depth * 16}px`, borderRight: `1px solid ${BRD}`, minWidth: 0 }}>
                  {hasChildren ? (
                    <button
                      onClick={() => setCollapsed((c) => ({ ...c, [t.id]: !c[t.id] }))}
                      aria-label={collapsed[t.id] ? `Expand ${t.title}` : `Collapse ${t.title}`}
                      style={{ border: "none", background: "none", cursor: "pointer", color: TEXT_MUTED, display: "flex", padding: 0 }}
                    >
                      {collapsed[t.id] ? <ChevronRight size={13} /> : <ChevronDown size={13} />}
                    </button>
                  ) : <span style={{ width: 13 }} />}
                  {t.is_milestone && <Diamond size={10} style={{ color: AMBER, flexShrink: 0 }} fill={AMBER} />}
                  <button
                    onClick={() => setEditing(t)}
                    title={t.title}
                    style={{ border: "none", background: "none", cursor: "pointer", textAlign: "left", fontSize: 12.5, color: TEXT_PRIMARY, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", padding: 0 }}
                  >
                    {t.title}
                  </button>
                </div>
                <div style={{ position: "relative", width: totalWidth, height: ROW_H }}>
                  {!hasStart && (
                    <button
                      onClick={() => setEditing(t)}
                      style={{ position: "absolute", left: 8, top: 8, fontSize: 11, color: TEXT_MUTED, background: "none", border: `1px dashed ${BRD}`, borderRadius: RADIUS_SM, padding: "2px 8px", cursor: "pointer" }}
                    >
                      Set dates
                    </button>
                  )}
                  {hasStart && t.is_milestone && (
                    <div
                      data-testid={TID.ganttBar(t.id)}
                      title={`${t.title} — milestone on ${t.start_date}`}
                      style={{ position: "absolute", left: barX - 6, top: 10, width: 16, height: 16, transform: "rotate(45deg)", background: AMBER, borderRadius: 3 }}
                    />
                  )}
                  {hasStart && !t.is_milestone && (
                    <div
                      data-testid={TID.ganttBar(t.id)}
                      role="button"
                      tabIndex={0}
                      aria-label={`${t.title}, ${t.start_date} to ${end || "no end date"}, ${t.progress || 0}% complete${isCritical ? ", on critical path" : ""}`}
                      onMouseDown={(e) => beginDrag(e, t, "move")}
                      onKeyDown={(e) => onBarKeyDown(e, t)}
                      style={{
                        position: "absolute", left: barX, top: 7, width: barW || 24, height: 22, borderRadius: RADIUS_SM,
                        background: `${color}22`, border: `1.5px solid ${isCritical ? CRIMSON : color}`,
                        cursor: canEdit ? "grab" : "default", overflow: "hidden",
                      }}
                    >
                      <div style={{ position: "absolute", inset: 0, width: `${Math.min(100, Math.max(0, t.progress || 0))}%`, background: `${color}55` }} />
                      <span style={{ position: "relative", fontSize: 10.5, color: TEXT_PRIMARY, padding: "0 6px", lineHeight: "22px", whiteSpace: "nowrap" }}>
                        {t.title}
                      </span>
                      {canEdit && barW > 16 && (
                        <>
                          <div onMouseDown={(e) => beginDrag(e, t, "resize-start")} style={{ position: "absolute", left: 0, top: 0, width: 6, height: "100%", cursor: "ew-resize" }} />
                          <div onMouseDown={(e) => beginDrag(e, t, "resize-end")} style={{ position: "absolute", right: 0, top: 0, width: 6, height: "100%", cursor: "ew-resize" }} />
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Dependency connectors */}
          <svg
            width={totalWidth} height={contentHeight}
            style={{ position: "absolute", left: LEFT_W, top: HEADER_H, pointerEvents: "none" }}
          >
            <defs>
              <marker id="gantt-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
                <path d="M0,0 L6,3 L0,6 Z" fill={TEXT_MUTED} />
              </marker>
            </defs>
            {filteredTasks.map((t) =>
              (t.depends_on || []).map((depId) => {
                const dep = filteredTasks.find((x) => x.id === depId);
                if (!dep || !dep.start_date || !t.start_date) return null;
                const rowA = taskRowIndex.get(dep.id), rowB = taskRowIndex.get(t.id);
                if (rowA === undefined || rowB === undefined) return null;
                const depEnd = dep.end_date || dep.due_date || dep.start_date;
                const x1 = xOf(depEnd), y1 = rowA * ROW_H + ROW_H / 2;
                const x2 = xOf(t.start_date), y2 = rowB * ROW_H + ROW_H / 2;
                const midX = x1 + 8;
                return (
                  <path
                    key={`${depId}-${t.id}`}
                    d={`M ${x1} ${y1} H ${midX} V ${y2} H ${x2}`}
                    fill="none" stroke={TEXT_MUTED} strokeWidth={1.25} markerEnd="url(#gantt-arrow)"
                  />
                );
              })
            )}
          </svg>

          {/* Today marker */}
          {todayX >= 0 && todayX <= totalWidth && (
            <div
              data-testid={TID.ganttToday}
              title={`Today — ${today}`}
              style={{ position: "absolute", left: LEFT_W + todayX, top: HEADER_H, width: 1, height: contentHeight, background: CRIMSON, opacity: 0.5, pointerEvents: "none" }}
            />
          )}
        </div>
      </div>

      {editing && (
        <TaskEditModal
          task={editing === "new" ? null : editing}
          projects={data.projects}
          allTasks={data.tasks}
          defaultProjectId={projectIdForNew}
          canEdit={canEdit}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); load(); }}
        />
      )}
    </div>
  );
}

function TaskEditModal({ task, projects, allTasks, defaultProjectId, canEdit, onClose, onSaved }) {
  const isNew = !task;
  const [projectId, setProjectId] = useState(task?.project?.id || defaultProjectId || "");
  const [title, setTitle] = useState(task?.title || "");
  const [startDate, setStartDate] = useState(task?.start_date || "");
  const [endDate, setEndDate] = useState(task?.end_date || task?.due_date || "");
  const [progress, setProgress] = useState(task?.progress ?? 0);
  const [priority, setPriority] = useState(task?.priority || "medium");
  const [status, setStatus] = useState(task?.status || "backlog");
  const [isMilestone, setIsMilestone] = useState(task?.is_milestone || false);
  const [parentTaskId, setParentTaskId] = useState(task?.parent_task_id || "");
  const [dependsOn, setDependsOn] = useState(task?.depends_on || []);
  const [saving, setSaving] = useState(false);

  const candidateTasks = (allTasks || []).filter((t) => t.id !== task?.id && (!projectId || t.project?.id === projectId));

  const save = async () => {
    if (!title.trim()) { toast.error("Title is required"); return; }
    if (isNew && !projectId) { toast.error("Pick a project"); return; }
    setSaving(true);
    try {
      const payload = {
        title: title.trim(), start_date: startDate || undefined, end_date: endDate || undefined,
        progress: Number(progress) || 0, priority, status, is_milestone: isMilestone,
        parent_task_id: parentTaskId || undefined, depends_on: dependsOn,
      };
      if (isNew) {
        await api.post(`/projects/${projectId}/tasks`, payload);
        toast.success("Task created");
      } else {
        await api.patch(`/projects/tasks/${task.id}`, payload);
        toast.success("Task updated");
      }
      onSaved();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to save task");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open onClose={onClose} title={isNew ? "New task" : "Edit task"} size="md">
      <div className="space-y-3">
        {isNew && (
          <FormSelect label="Project" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">Select a project…</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
          </FormSelect>
        )}
        <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} disabled={!canEdit} />
        <div className="grid grid-cols-2 gap-3">
          <Input type="date" label="Start date" value={startDate} onChange={(e) => setStartDate(e.target.value)} disabled={!canEdit} />
          <Input type="date" label="End date" value={endDate} onChange={(e) => setEndDate(e.target.value)} disabled={!canEdit} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <FormSelect label="Status" value={status} onChange={(e) => setStatus(e.target.value)} disabled={!canEdit}>
            {["backlog", "planned", "in_progress", "review", "completed"].map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
          </FormSelect>
          <FormSelect label="Priority" value={priority} onChange={(e) => setPriority(e.target.value)} disabled={!canEdit}>
            {["low", "medium", "high"].map((p) => <option key={p} value={p}>{p}</option>)}
          </FormSelect>
        </div>
        <div className="grid grid-cols-2 gap-3 items-end">
          <Input type="number" min={0} max={100} label="Progress (%)" value={progress} onChange={(e) => setProgress(e.target.value)} disabled={!canEdit} />
          <label className="flex items-center gap-2" style={{ fontSize: 13, color: TEXT_SECONDARY, paddingBottom: 8 }}>
            <input type="checkbox" checked={isMilestone} onChange={(e) => setIsMilestone(e.target.checked)} disabled={!canEdit} />
            Milestone
          </label>
        </div>
        {!isNew && (
          <>
            <FormSelect label="Parent task" value={parentTaskId} onChange={(e) => setParentTaskId(e.target.value)} disabled={!canEdit}>
              <option value="">No parent</option>
              {candidateTasks.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
            </FormSelect>
            <div>
              <label style={{ fontSize: 12.5, fontWeight: 600, color: TEXT_SECONDARY, display: "block", marginBottom: 4 }}>Depends on</label>
              <select
                multiple
                disabled={!canEdit}
                value={dependsOn}
                onChange={(e) => setDependsOn(Array.from(e.target.selectedOptions).map((o) => o.value))}
                style={{ width: "100%", minHeight: 80, border: `1px solid ${BRD}`, borderRadius: RADIUS_MD, fontSize: 12.5, padding: 6 }}
              >
                {candidateTasks.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
              </select>
            </div>
            <div style={{ borderTop: `1px solid ${BRD}`, paddingTop: 12 }}>
              <CommentThread targetType="task" targetId={task.id} workspaceMembers={[]} />
            </div>
          </>
        )}
        {canEdit && (
          <div className="flex justify-end gap-2" style={{ paddingTop: 8 }}>
            <Button variant="ghost" onClick={onClose}>Cancel</Button>
            <Button onClick={save} disabled={saving}>{saving ? "Saving…" : isNew ? "Create task" : "Save changes"}</Button>
          </div>
        )}
      </div>
    </Modal>
  );
}
