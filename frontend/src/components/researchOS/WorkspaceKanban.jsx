import React, { useCallback, useEffect, useState, useMemo, useRef } from "react";
import api from "../../lib/api";
import { TID } from "../../lib/testIds";
import { toast } from "sonner";
import { Plus, GripVertical, User as UserIcon, Search, ChevronDown, ChevronRight, MoreHorizontal, X } from "lucide-react";
import {
  NAVY, BRD, BRDH, WARM, WHITE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
  CRIMSON, AMBER, EMERALD, RADIUS_MD, RADIUS_SM,
} from "@/lib/tokens";
import { transition, transform } from "@/lib/motion";
import { Input } from "@/components/ds/Input";
import { FormSelect } from "@/components/ds/FormSelect";
import { Modal } from "@/components/ds/Modal";
import { Dropdown, DropdownItem } from "@/components/ds/Dropdown";
import { Badge } from "@/components/ds/Badge";
import { Button } from "@/components/ds/Button";
import { EmptyState } from "@/components/ds/EmptyState";
import { SkeletonCard } from "@/components/ds/LoadingState";
import CommentThread from "@/components/comments/CommentThread";

const COLUMNS = [
  { key: "backlog", label: "Backlog", accent: TEXT_MUTED },
  { key: "planned", label: "Planned", accent: "#0284C7" },
  { key: "in_progress", label: "In progress", accent: AMBER },
  { key: "review", label: "Review", accent: "#7C3AED" },
  { key: "completed", label: "Completed", accent: EMERALD },
];

const PRIORITY_COLOR = { high: CRIMSON, medium: AMBER, low: TEXT_MUTED };
const PRIORITIES = ["low", "medium", "high"];

// ── localStorage helpers — per-workspace view prefs (collapse, WIP limits) ────
function loadPrefs(wsId) {
  try { return JSON.parse(localStorage.getItem(`sq_kanban_prefs_${wsId}`) || "{}"); }
  catch { return {}; }
}
function savePrefs(wsId, prefs) {
  try { localStorage.setItem(`sq_kanban_prefs_${wsId}`, JSON.stringify(prefs)); } catch {}
}

// ── Auto-scroll the page while dragging near the viewport edges ──────────────
function useAutoScroll(active) {
  useEffect(() => {
    if (!active) return;
    let raf;
    const onDrag = (e) => {
      const margin = 80, speed = 16;
      if (e.clientY < margin) window.scrollBy(0, -speed);
      else if (window.innerHeight - e.clientY < margin) window.scrollBy(0, speed);
    };
    document.addEventListener("dragover", onDrag);
    return () => { document.removeEventListener("dragover", onDrag); cancelAnimationFrame(raf); };
  }, [active]);
}

function TaskCard({ task, canEdit, onDragStart, onDragEnd, dragging, onOpen, onMove }) {
  const [hov, setHov] = useState(false);
  return (
    <div
      data-testid={TID.kanbanTask(task.id)}
      role="listitem"
      aria-label={`${task.title}, ${task.priority || "no"} priority${task.assignee ? `, assigned to ${task.assignee.full_name}` : ""}`}
      tabIndex={0}
      draggable={canEdit}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      onClick={() => onOpen(task)}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpen(task); } }}
      style={{
        background: WHITE,
        border: `1px solid ${hov ? BRDH : BRD}`,
        borderRadius: RADIUS_MD,
        padding: "12px 12px",
        cursor: canEdit ? "grab" : "pointer",
        opacity: dragging ? 0.4 : 1,
        transform: hov ? transform.liftSm : transform.none,
        transition: transition.hoverCard,
        boxShadow: hov ? "0 6px 16px -10px rgba(15,23,42,0.2)" : "none",
      }}
    >
      <div className="flex items-start gap-2">
        {canEdit && <GripVertical size={12} strokeWidth={1.5} style={{ color: TEXT_MUTED, marginTop: 2, flexShrink: 0 }} aria-hidden="true" />}
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ fontSize: 13, color: TEXT_PRIMARY, lineHeight: 1.4 }}>{task.title}</div>
          <div className="flex items-center gap-2 flex-wrap" style={{ marginTop: 8 }}>
            {task.priority && (
              <Badge color={PRIORITY_COLOR[task.priority] || PRIORITY_COLOR.low} size="sm">{task.priority}</Badge>
            )}
            {task.project && (
              <span style={{ fontSize: 10, color: TEXT_MUTED, fontFamily: "monospace", maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {task.project.title}
              </span>
            )}
            {task.due_date && (
              <span style={{ fontSize: 10, color: TEXT_MUTED, fontFamily: "monospace" }}>{task.due_date}</span>
            )}
          </div>
          {task.assignee && (
            <div className="flex items-center gap-1.5" style={{ marginTop: 8 }}>
              {task.assignee.avatar_url
                ? <img src={task.assignee.avatar_url} alt="" style={{ height: 18, width: 18, borderRadius: "50%", objectFit: "cover" }} />
                : <UserIcon size={12} strokeWidth={1.5} style={{ color: TEXT_MUTED }} />}
              <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>{task.assignee.full_name}</span>
            </div>
          )}
        </div>

        {canEdit && (
          <div onClick={(e) => e.stopPropagation()}>
            <Dropdown
              align="right"
              width={170}
              trigger={
                <button
                  aria-label={`More actions for ${task.title}`}
                  style={{
                    width: 22, height: 22, display: "flex", alignItems: "center", justifyContent: "center",
                    border: "none", background: "transparent", cursor: "pointer", color: TEXT_MUTED,
                    borderRadius: RADIUS_SM, flexShrink: 0, opacity: hov ? 1 : 0, transition: transition.hover,
                  }}
                >
                  <MoreHorizontal size={14} strokeWidth={1.75} />
                </button>
              }
            >
              <div style={{ padding: "5px 12px 4px", fontSize: "0.6875rem", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: TEXT_MUTED }}>
                Move to
              </div>
              {COLUMNS.filter((c) => c.key !== task.status).map((c) => (
                <DropdownItem key={c.key} onClick={() => onMove(task, c.key)}>{c.label}</DropdownItem>
              ))}
            </Dropdown>
          </div>
        )}
      </div>
    </div>
  );
}

export default function WorkspaceKanban({ wsId, canEdit }) {
  const [data, setData] = useState({ projects: [], tasks: [] });
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [projectId, setProjectId] = useState("");
  const [composing, setComposing] = useState(null);
  const [newTitle, setNewTitle] = useState("");
  const [draggingId, setDraggingId] = useState(null);
  const [dragOver, setDragOver] = useState(null);
  const [query, setQuery] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [assigneeFilter, setAssigneeFilter] = useState("");
  const [editingTask, setEditingTask] = useState(null);
  const [editDraft, setEditDraft] = useState(null);
  const [saving, setSaving] = useState(false);

  const prefs = useRef(loadPrefs(wsId));
  const [collapsed, setCollapsed] = useState(() => prefs.current.collapsed || {});
  const [wipLimits, setWipLimits] = useState(() => prefs.current.wipLimits || {});

  useAutoScroll(draggingId != null);

  useEffect(() => { savePrefs(wsId, { collapsed, wipLimits }); }, [wsId, collapsed, wipLimits]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/workspaces/${wsId}/tasks`);
      setData(data || { projects: [], tasks: [] });
      if (data?.projects?.length) setProjectId((prev) => prev || data.projects[0].id);
    } catch (e) {
      setData({ projects: [], tasks: [] });
    } finally { setLoading(false); }
  }, [wsId]);
  useEffect(() => { load(); }, [wsId, load]);

  // Real workspace members — used to populate the assignee picker with
  // people who can actually be assigned, not just whoever already has a task.
  useEffect(() => {
    api.get(`/workspaces/${wsId}`).then((r) => setMembers(r.data?.members_info || [])).catch(() => {});
  }, [wsId]);

  const assigneeOptions = useMemo(() => {
    const map = new Map();
    members.forEach((m) => map.set(m.id, m));
    (data.tasks || []).forEach((t) => { if (t.assignee) map.set(t.assignee.id, t.assignee); });
    return Array.from(map.values());
  }, [members, data.tasks]);

  const filteredTasks = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (data.tasks || []).filter((t) => {
      if (q && !t.title?.toLowerCase().includes(q)) return false;
      if (priorityFilter && t.priority !== priorityFilter) return false;
      if (assigneeFilter && t.assignee?.id !== assigneeFilter) return false;
      return true;
    });
  }, [data.tasks, query, priorityFilter, assigneeFilter]);

  const byCol = useMemo(() => {
    const map = Object.fromEntries(COLUMNS.map((c) => [c.key, []]));
    for (const t of filteredTasks) {
      const k = COLUMNS.find((c) => c.key === t.status) ? t.status : "backlog";
      map[k].push(t);
    }
    return map;
  }, [filteredTasks]);

  const moveTask = async (task, newStatus, { silent = false } = {}) => {
    if (task.status === newStatus) return;
    const prevStatus = task.status;
    setData((d) => ({ ...d, tasks: d.tasks.map((t) => t.id === task.id ? { ...t, status: newStatus } : t) }));
    try {
      await api.patch(`/projects/tasks/${task.id}`, { status: newStatus });
      if (!silent) {
        toast.success(`Moved to ${COLUMNS.find((c) => c.key === newStatus)?.label}`, {
          action: { label: "Undo", onClick: () => moveTask({ ...task, status: newStatus }, prevStatus, { silent: true }) },
        });
      }
    } catch (e) {
      toast.error("Failed to move task");
      load();
    }
  };

  const createTask = async (status) => {
    if (!newTitle.trim()) return;
    if (!projectId) { toast.error("Pick a project first"); return; }
    try {
      await api.post(`/projects/${projectId}/tasks`, { title: newTitle, status, priority: "medium" });
      setNewTitle(""); setComposing(null);
      load();
    } catch (e) { toast.error("Failed to create"); }
  };

  const openEdit = (task) => {
    if (!canEdit) return;
    setEditingTask(task);
    setEditDraft({ title: task.title, priority: task.priority || "medium", due_date: task.due_date || "", assignee_id: task.assignee?.id || "" });
  };

  const saveEdit = async () => {
    if (!editingTask || !editDraft.title.trim()) return;
    setSaving(true);
    try {
      await api.patch(`/projects/tasks/${editingTask.id}`, {
        title: editDraft.title.trim(),
        priority: editDraft.priority,
        due_date: editDraft.due_date || null,
        assignee_id: editDraft.assignee_id || null,
      });
      setEditingTask(null);
      load();
      toast.success("Task updated");
    } catch (e) {
      toast.error("Failed to update task");
    } finally { setSaving(false); }
  };

  const toggleCollapse = (key) => setCollapsed((c) => ({ ...c, [key]: !c[key] }));

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3" role="status" aria-label="Loading tasks">
        {COLUMNS.map((c) => <SkeletonCard key={c.key} rows={2} />)}
      </div>
    );
  }

  if ((data.projects || []).length === 0) {
    return (
      <EmptyState
        title="No projects linked to this workspace"
        description="Tasks live inside projects — link or create a project first from the Projects page."
        size="md"
        dashed
      />
    );
  }

  const activeFilterCount = [query, priorityFilter, assigneeFilter].filter(Boolean).length;

  return (
    <div data-testid={TID.kanban} className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div style={{ fontSize: 13, color: TEXT_SECONDARY }}>
          {filteredTasks.length} of {(data.tasks || []).length} task{(data.tasks || []).length === 1 ? "" : "s"} across {(data.projects || []).length} project{(data.projects || []).length === 1 ? "" : "s"}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Input
            size="sm"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search tasks…"
            prefix={<Search size={12} strokeWidth={1.75} />}
            wrapperClassName="w-auto"
            style={{ width: 160 }}
            aria-label="Search tasks"
          />
          <FormSelect size="sm" value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} aria-label="Filter by priority" style={{ width: 120 }}>
            <option value="">All priorities</option>
            {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
          </FormSelect>
          {assigneeOptions.length > 0 && (
            <FormSelect size="sm" value={assigneeFilter} onChange={(e) => setAssigneeFilter(e.target.value)} aria-label="Filter by assignee" style={{ width: 140 }}>
              <option value="">All assignees</option>
              {assigneeOptions.map((a) => <option key={a.id} value={a.id}>{a.full_name}</option>)}
            </FormSelect>
          )}
          {activeFilterCount > 0 && (
            <button
              onClick={() => { setQuery(""); setPriorityFilter(""); setAssigneeFilter(""); }}
              style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: TEXT_MUTED, background: "none", border: "none", cursor: "pointer" }}
            >
              <X size={11} strokeWidth={2} /> Clear
            </button>
          )}
          <span style={{ width: 1, height: 20, background: BRD }} aria-hidden="true" />
          <span className="overline" style={{ fontSize: 11, color: TEXT_MUTED }}>New task in</span>
          <FormSelect size="sm" data-testid={TID.kanbanProjectPicker} value={projectId} onChange={(e) => setProjectId(e.target.value)} style={{ width: 150 }}>
            {(data.projects || []).map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
          </FormSelect>
        </div>
      </div>

      {/* Board */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3">
        {COLUMNS.map((col) => {
          const tasks = byCol[col.key] || [];
          const isDropping = dragOver === col.key;
          const isCollapsed = !!collapsed[col.key];
          const wip = wipLimits[col.key];
          const overWip = wip && tasks.length > wip;

          return (
            <div
              key={col.key}
              data-testid={TID.kanbanColumn(col.key)}
              onDragOver={(e) => { e.preventDefault(); setDragOver(col.key); }}
              onDragLeave={() => setDragOver(null)}
              onDrop={(e) => {
                e.preventDefault();
                const idDropped = e.dataTransfer.getData("text/plain");
                const t = data.tasks.find((x) => x.id === idDropped);
                if (t) moveTask(t, col.key);
                setDragOver(null); setDraggingId(null);
              }}
              style={{
                borderTop: `2px solid ${col.accent}`,
                background: isDropping ? "rgba(15,40,71,0.04)" : WARM,
                borderRadius: `0 0 ${RADIUS_MD} ${RADIUS_MD}`,
                transition: transition.hoverBase,
              }}
            >
              <div className="flex items-center justify-between" style={{ padding: "10px 12px" }}>
                <button
                  onClick={() => toggleCollapse(col.key)}
                  aria-expanded={!isCollapsed}
                  style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "none", cursor: "pointer", padding: 0 }}
                >
                  {isCollapsed ? <ChevronRight size={12} style={{ color: TEXT_MUTED }} /> : <ChevronDown size={12} style={{ color: TEXT_MUTED }} />}
                  <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: TEXT_SECONDARY }}>{col.label}</span>
                  <span style={{ fontSize: 10, fontFamily: "monospace", color: overWip ? CRIMSON : TEXT_MUTED, fontWeight: overWip ? 700 : 400 }}>
                    {tasks.length}{wip ? ` / ${wip}` : ""}
                  </span>
                </button>
                {canEdit && !isCollapsed && (
                  <button
                    data-testid={TID.kanbanAddBtn(col.key)}
                    onClick={() => { setComposing(col.key); setNewTitle(""); }}
                    aria-label={`Add task to ${col.label}`}
                    style={{ color: TEXT_MUTED, background: "none", border: "none", cursor: "pointer", padding: 2 }}
                  ><Plus size={14} strokeWidth={1.5} /></button>
                )}
              </div>

              {!isCollapsed && (
                <div role="list" aria-label={`${col.label} tasks`} className="space-y-2" style={{ padding: "0 8px 8px", minHeight: 120 }}>
                  {overWip && (
                    <div style={{ fontSize: 10, color: CRIMSON, fontWeight: 600, padding: "2px 4px" }}>
                      Over WIP limit ({tasks.length}/{wip})
                    </div>
                  )}
                  {composing === col.key && (
                    <div style={{ border: `1px solid ${NAVY}`, background: WHITE, padding: 8, borderRadius: RADIUS_MD }} className="space-y-2">
                      <input
                        data-testid={TID.kanbanNewTitle(col.key)}
                        autoFocus value={newTitle} onChange={(e) => setNewTitle(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter") createTask(col.key); if (e.key === "Escape") setComposing(null); }}
                        placeholder="Task title…"
                        style={{ width: "100%", padding: "4px 6px", border: `1px solid ${BRD}`, fontSize: 13, borderRadius: RADIUS_SM, outline: "none" }}
                      />
                      <div className="flex gap-2">
                        <Button size="sm" data-testid={TID.kanbanNewSubmit(col.key)} onClick={() => createTask(col.key)}>Create</Button>
                        <Button size="sm" variant="ghost" onClick={() => setComposing(null)}>Cancel</Button>
                      </div>
                    </div>
                  )}
                  {tasks.map((t) => (
                    <TaskCard
                      key={t.id}
                      task={t}
                      canEdit={canEdit}
                      dragging={draggingId === t.id}
                      onDragStart={(e) => { e.dataTransfer.setData("text/plain", t.id); setDraggingId(t.id); e.dataTransfer.effectAllowed = "move"; }}
                      onDragEnd={() => { setDraggingId(null); setDragOver(null); }}
                      onOpen={openEdit}
                      onMove={moveTask}
                    />
                  ))}
                  {tasks.length === 0 && composing !== col.key && (
                    <div style={{ fontSize: 11, color: TEXT_MUTED, textAlign: "center", padding: "12px 0", fontFamily: "monospace" }}>
                      Drop tasks here
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Inline edit modal */}
      <Modal
        open={!!editingTask}
        onClose={() => setEditingTask(null)}
        title="Edit task"
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setEditingTask(null)} disabled={saving}>Cancel</Button>
            <Button onClick={saveEdit} loading={saving}>Save</Button>
          </>
        }
      >
        {editDraft && (
          <div className="space-y-4">
            <Input label="Title" value={editDraft.title} onChange={(e) => setEditDraft((d) => ({ ...d, title: e.target.value }))} />
            <FormSelect label="Priority" value={editDraft.priority} onChange={(e) => setEditDraft((d) => ({ ...d, priority: e.target.value }))}>
              {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
            </FormSelect>
            <Input label="Due date" type="date" value={editDraft.due_date} onChange={(e) => setEditDraft((d) => ({ ...d, due_date: e.target.value }))} />
            <FormSelect label="Assignee" value={editDraft.assignee_id} onChange={(e) => setEditDraft((d) => ({ ...d, assignee_id: e.target.value }))}>
              <option value="">Unassigned</option>
              {assigneeOptions.map((a) => <option key={a.id} value={a.id}>{a.full_name}</option>)}
            </FormSelect>
            <div style={{ borderTop: `1px solid ${BRD}`, paddingTop: 16, marginTop: 4 }}>
              <CommentThread targetType="task" targetId={editingTask.id} workspaceMembers={members} />
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
