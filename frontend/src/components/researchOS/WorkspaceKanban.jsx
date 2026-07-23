import React, { useCallback, useEffect, useState, useMemo } from "react";
import api from "../../lib/api";
import { TID } from "../../lib/testIds";
import { toast } from "sonner";
import { Plus, GripVertical, User as UserIcon } from "lucide-react";
import { NAVY } from "@/lib/tokens";

const COLUMNS = [
  { key: "backlog", label: "Backlog", accent: "border-slate-300" },
  { key: "planned", label: "Planned", accent: "border-sky-300" },
  { key: "in_progress", label: "In progress", accent: "border-amber-300" },
  { key: "review", label: "Review", accent: "border-purple-300" },
  { key: "completed", label: "Completed", accent: "border-emerald-400" },
];

const PRIORITY_TONE = {
  high: "text-red-700 bg-red-50 border-red-200",
  medium: "text-amber-700 bg-amber-50 border-amber-200",
  low: "text-slate-600 bg-slate-50 border-slate-200",
};

export default function WorkspaceKanban({ wsId, canEdit }) {
  const [data, setData] = useState({ projects: [], tasks: [] });
  const [loading, setLoading] = useState(true);
  const [projectId, setProjectId] = useState("");
  const [composing, setComposing] = useState(null); // status column open for new-task input
  const [newTitle, setNewTitle] = useState("");
  const [draggingId, setDraggingId] = useState(null);
  const [dragOver, setDragOver] = useState(null);

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

  const byCol = useMemo(() => {
    const map = Object.fromEntries(COLUMNS.map((c) => [c.key, []]));
    for (const t of data.tasks || []) {
      const k = COLUMNS.find((c) => c.key === t.status) ? t.status : "backlog";
      map[k].push(t);
    }
    return map;
  }, [data]);

  const moveTask = async (task, newStatus) => {
    if (task.status === newStatus) return;
    // optimistic update
    setData((d) => ({ ...d, tasks: d.tasks.map((t) => t.id === task.id ? { ...t, status: newStatus } : t) }));
    try {
      await api.patch(`/projects/tasks/${task.id}`, { status: newStatus });
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

  if (loading) return <div className="text-sm text-slate-500 font-mono">Loading tasks…</div>;

  if ((data.projects || []).length === 0) {
    return (
      <div className="text-sm text-slate-500 py-12 text-center border border-dashed border-slate-300">
        No projects linked to this workspace. Tasks live inside projects — link or create a project first from the Projects page.
      </div>
    );
  }

  return (
    <div data-testid={TID.kanban} className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="text-sm text-slate-600">{(data.tasks || []).length} task{(data.tasks || []).length === 1 ? "" : "s"} across {(data.projects || []).length} project{(data.projects || []).length === 1 ? "" : "s"}.</div>
        <div className="flex items-center gap-2">
          <span className="overline">New task in</span>
          <select
            data-testid={TID.kanbanProjectPicker}
            value={projectId} onChange={(e) => setProjectId(e.target.value)}
            className="px-2 py-1 border border-slate-300 bg-white text-xs"
          >
            {(data.projects || []).map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3">
        {COLUMNS.map((col) => {
          const tasks = byCol[col.key] || [];
          const isDropping = dragOver === col.key;
          return (
            <div
              key={col.key}
              data-testid={TID.kanbanColumn(col.key)}
              onDragOver={(e) => { e.preventDefault(); setDragOver(col.key); }}
              onDragLeave={() => setDragOver(null)}
              onDrop={(e) => {
                e.preventDefault();
                const id = e.dataTransfer.getData("text/plain");
                const t = data.tasks.find((x) => x.id === id);
                if (t) moveTask(t, col.key);
                setDragOver(null); setDraggingId(null);
              }}
              className={`border-t-2 ${col.accent} bg-slate-50/60 transition-colors ${isDropping ? "bg-slate-100" : ""}`}
            >
              <div className="px-3 py-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="overline text-slate-700">{col.label}</div>
                  <span className="text-[10px] font-mono text-slate-500">{tasks.length}</span>
                </div>
                {canEdit && (
                  <button
                    data-testid={TID.kanbanAddBtn(col.key)}
                    onClick={() => { setComposing(col.key); setNewTitle(""); }}
                    className="text-slate-400 hover:text-[#0F2847] p-1"
                    title="Add task"
                  ><Plus size={14} strokeWidth={1.5} /></button>
                )}
              </div>
              <div className="px-2 pb-2 space-y-2 min-h-[120px]">
                {composing === col.key && (
                  <div className="border border-[#0F2847] bg-white p-2 space-y-2">
                    <input
                      data-testid={TID.kanbanNewTitle(col.key)}
                      autoFocus value={newTitle} onChange={(e) => setNewTitle(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") createTask(col.key); if (e.key === "Escape") setComposing(null); }}
                      placeholder="Task title…"
                      className="w-full px-2 py-1 border border-slate-300 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
                    />
                    <div className="flex gap-2">
                      <button data-testid={TID.kanbanNewSubmit(col.key)} onClick={() => createTask(col.key)} className="bg-[#0F2847] text-white px-3 py-1 text-xs hover:bg-slate-800">Create</button>
                      <button onClick={() => setComposing(null)} className="text-xs text-slate-500 hover:text-slate-900">Cancel</button>
                    </div>
                  </div>
                )}
                {tasks.map((t) => (
                  <div
                    key={t.id}
                    data-testid={TID.kanbanTask(t.id)}
                    draggable={canEdit}
                    onDragStart={(e) => { e.dataTransfer.setData("text/plain", t.id); setDraggingId(t.id); e.dataTransfer.effectAllowed = "move"; }}
                    onDragEnd={() => { setDraggingId(null); setDragOver(null); }}
                    className={`bg-white border border-slate-200 p-3 cursor-grab active:cursor-grabbing transition-opacity ${draggingId === t.id ? "opacity-50" : ""} hover:border-[#0F2847]`}
                  >
                    <div className="flex items-start gap-2">
                      {canEdit && <GripVertical size={12} strokeWidth={1.5} className="text-slate-300 mt-0.5 shrink-0" />}
                      <div className="min-w-0 flex-1">
                        <div className="text-sm text-slate-900 leading-snug">{t.title}</div>
                        <div className="mt-2 flex items-center gap-2 flex-wrap">
                          {t.priority && <span className={`text-[10px] font-mono px-1.5 py-0.5 border ${PRIORITY_TONE[t.priority] || PRIORITY_TONE.low}`}>{t.priority}</span>}
                          {t.project && <span className="text-[10px] font-mono text-slate-500 truncate max-w-[140px]">{t.project.title}</span>}
                          {t.due_date && <span className="text-[10px] font-mono text-slate-500">{t.due_date}</span>}
                        </div>
                        {t.assignee && (
                          <div className="mt-2 flex items-center gap-1.5">
                            {t.assignee.avatar_url
                              ? <img src={t.assignee.avatar_url} alt="" className="h-5 w-5 rounded-full object-cover" />
                              : <UserIcon size={12} strokeWidth={1.5} className="text-slate-400" />}
                            <span className="text-[11px] text-slate-600 truncate">{t.assignee.full_name}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {tasks.length === 0 && composing !== col.key && (
                  <div className="text-[11px] text-slate-400 text-center py-3 font-mono">Drop tasks here</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
