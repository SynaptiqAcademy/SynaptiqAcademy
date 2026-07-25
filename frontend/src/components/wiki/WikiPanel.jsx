import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Search, History, MessageSquare, Clock, X } from "lucide-react";
import api from "@/lib/api";
import WikiPageTree from "./WikiPageTree";
import WikiEditor from "./WikiEditor";
import CommentThread from "@/components/comments/CommentThread";
import { Input } from "@/components/ds/Input";
import { Button } from "@/components/ds/Button";
import { Drawer } from "@/components/ds/Drawer";
import { EmptyState } from "@/components/ds/EmptyState";
import { BRD, TEXT_PRIMARY, TEXT_MUTED, TEXT_SECONDARY, NAVY, RADIUS_MD } from "@/lib/tokens";

function fmtDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

/**
 * WikiPanel — the workspace's Knowledge Wiki: nested pages, Tiptap rich
 * editor with autosave, draft/published state, version history + restore,
 * search, and comments — everything persisted through the real
 * /api/workspaces/{id}/items + /api/wiki/* endpoints, nothing local-only.
 */
export default function WikiPanel({ workspaceId, members = [] }) {
  const [pages, setPages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeId, setActiveId] = useState(null);
  const [saveState, setSaveState] = useState("idle"); // idle | saving | saved
  const [historyOpen, setHistoryOpen] = useState(false);
  const [versions, setVersions] = useState([]);
  const [commentsOpen, setCommentsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/workspaces/${workspaceId}/items`, { params: { item_type: "wiki_page" } });
      setPages(data || []);
      if (!activeId && data?.length) setActiveId(data[0].id);
    } catch (e) {
      setPages([]);
    } finally { setLoading(false); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId]);
  useEffect(() => { load(); }, [load]);

  const active = pages.find((p) => p.id === activeId) || null;

  const createPage = async (parentId = null) => {
    try {
      const { data } = await api.post(`/workspaces/${workspaceId}/items`, {
        item_type: "wiki_page", title: "Untitled", parent_id: parentId, content: null, status: "draft",
      });
      setPages((prev) => [...prev, data]);
      setActiveId(data.id);
    } catch (e) { toast.error("Failed to create page"); }
  };

  const saveContent = async (content) => {
    if (!active) return;
    setSaveState("saving");
    try {
      const { data } = await api.patch(`/items/${active.id}`, { content });
      setPages((prev) => prev.map((p) => p.id === active.id ? data : p));
      setSaveState("saved");
      setTimeout(() => setSaveState("idle"), 1500);
    } catch (e) {
      setSaveState("idle");
      toast.error("Failed to save — reload and try again");
    }
  };

  const renameActive = async (title) => {
    setPages((prev) => prev.map((p) => p.id === active.id ? { ...p, title } : p));
    try {
      await api.patch(`/items/${active.id}`, { title });
    } catch (e) { toast.error("Failed to rename"); }
  };

  const togglePublish = async () => {
    const nextStatus = active.status === "published" ? "draft" : "published";
    try {
      const { data } = await api.patch(`/items/${active.id}`, { status: nextStatus });
      setPages((prev) => prev.map((p) => p.id === active.id ? data : p));
    } catch (e) { toast.error("Failed to update status"); }
  };

  const duplicatePage = async (page) => {
    try {
      const { data } = await api.post(`/wiki/pages/${page.id}/duplicate`);
      setPages((prev) => [...prev, data]);
      toast.success("Page duplicated");
    } catch (e) { toast.error("Failed to duplicate"); }
  };

  const archivePage = async (page) => {
    const nextStatus = page.status === "archived" ? "draft" : "archived";
    try {
      const { data } = await api.patch(`/items/${page.id}`, { status: nextStatus });
      setPages((prev) => prev.map((p) => p.id === page.id ? data : p));
    } catch (e) { toast.error("Failed to update page"); }
  };

  const deletePage = async (page) => {
    if (!window.confirm(`Delete "${page.title}"? This can be restored by a workspace admin.`)) return;
    try {
      await api.delete(`/items/${page.id}`);
      setPages((prev) => prev.filter((p) => p.id !== page.id));
      if (activeId === page.id) setActiveId(null);
    } catch (e) { toast.error("Failed to delete page"); }
  };

  const openHistory = async () => {
    if (!active) return;
    setHistoryOpen(true);
    try {
      const { data } = await api.get(`/wiki/pages/${active.id}/versions`);
      setVersions(data || []);
    } catch (e) { setVersions([]); }
  };

  const restoreVersion = async (versionId) => {
    try {
      const { data } = await api.post(`/wiki/pages/${active.id}/versions/${versionId}/restore`);
      setPages((prev) => prev.map((p) => p.id === active.id ? data : p));
      setHistoryOpen(false);
      toast.success("Version restored");
    } catch (e) { toast.error("Failed to restore version"); }
  };

  const runSearch = async (q) => {
    setQuery(q);
    if (!q.trim()) { setSearchResults(null); return; }
    try {
      const { data } = await api.get(`/workspaces/${workspaceId}/wiki/search`, { params: { q } });
      setSearchResults(data || []);
    } catch (e) { setSearchResults([]); }
  };

  if (loading) {
    return <div style={{ fontSize: 13, color: TEXT_MUTED }} role="status">Loading wiki…</div>;
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[240px_minmax(0,1fr)] gap-6" style={{ minHeight: 480 }}>
      {/* Page tree sidebar */}
      <div>
        <div className="flex items-center gap-2" style={{ marginBottom: 10 }}>
          <Input
            size="sm"
            value={query}
            onChange={(e) => runSearch(e.target.value)}
            placeholder="Search wiki…"
            prefix={<Search size={12} strokeWidth={1.75} />}
            wrapperClassName="flex-1"
          />
          <Button size="sm" variant="ghost" onClick={() => createPage(null)} aria-label="New page"><Plus size={13} strokeWidth={1.75} /></Button>
        </div>
        {searchResults ? (
          <div>
            <div style={{ fontSize: 11, color: TEXT_MUTED, marginBottom: 6 }}>{searchResults.length} result{searchResults.length === 1 ? "" : "s"}</div>
            {searchResults.map((r) => (
              <button
                key={r.id}
                onClick={() => { setActiveId(r.id); setQuery(""); setSearchResults(null); }}
                style={{ display: "block", width: "100%", textAlign: "left", padding: "6px 8px", background: "none", border: "none", cursor: "pointer", borderRadius: 6 }}
              >
                <div style={{ fontSize: 13, color: TEXT_PRIMARY, fontWeight: 600 }}>{r.title}</div>
                {r._snippet && <div style={{ fontSize: 11, color: TEXT_MUTED }}>{r._snippet}</div>}
              </button>
            ))}
          </div>
        ) : (
          <WikiPageTree
            pages={pages}
            activeId={activeId}
            onSelect={(p) => setActiveId(p.id)}
            onAddChild={createPage}
            onDuplicate={duplicatePage}
            onArchive={archivePage}
            onDelete={deletePage}
          />
        )}
      </div>

      {/* Editor */}
      <div style={{ minWidth: 0 }}>
        {!active ? (
          <EmptyState
            title="No page selected"
            description="Create a page to start writing your workspace's knowledge base."
            action={<Button size="sm" onClick={() => createPage(null)}><Plus size={12} strokeWidth={1.75} /> New page</Button>}
          />
        ) : (
          <div>
            <div className="flex items-center justify-between flex-wrap gap-2" style={{ marginBottom: 12 }}>
              <input
                value={active.title}
                onChange={(e) => renameActive(e.target.value)}
                aria-label="Page title"
                style={{
                  fontSize: 22, fontWeight: 700, color: TEXT_PRIMARY, border: "none", outline: "none",
                  background: "transparent", flex: 1, minWidth: 200,
                }}
              />
              <div className="flex items-center gap-2">
                <span style={{ fontSize: 11, color: TEXT_MUTED, minWidth: 50 }}>
                  {saveState === "saving" ? "Saving…" : saveState === "saved" ? "Saved" : ""}
                </span>
                <Button size="sm" variant="ghost" onClick={openHistory}><History size={12} strokeWidth={1.75} /> History</Button>
                <Button size="sm" variant="ghost" onClick={() => setCommentsOpen(true)}><MessageSquare size={12} strokeWidth={1.75} /> Comments</Button>
                <Button size="sm" variant={active.status === "published" ? "outline" : "primary"} onClick={togglePublish}>
                  {active.status === "published" ? "Unpublish" : "Publish"}
                </Button>
              </div>
            </div>

            <WikiEditor key={active.id} pageId={active.id} content={active.content} onSave={saveContent} />
          </div>
        )}
      </div>

      {/* Version history drawer */}
      <Drawer open={historyOpen} onClose={() => setHistoryOpen(false)} title="Version history" width={380}>
        {versions.length === 0 ? (
          <div style={{ fontSize: 13, color: TEXT_MUTED }}>No earlier versions yet — versions are saved automatically each time you edit.</div>
        ) : (
          versions.map((v) => (
            <div key={v.id} style={{ padding: "10px 0", borderBottom: `1px solid ${BRD}` }} className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Clock size={12} style={{ color: TEXT_MUTED }} />
                <span style={{ fontSize: 12.5, color: TEXT_SECONDARY }}>{fmtDate(v.created_at)}</span>
              </div>
              <Button size="sm" variant="ghost" onClick={() => restoreVersion(v.id)}>Restore</Button>
            </div>
          ))
        )}
      </Drawer>

      {/* Comments drawer */}
      <Drawer open={commentsOpen} onClose={() => setCommentsOpen(false)} title="Comments" width={380}>
        {active && <CommentThread targetType="workspace_item" targetId={active.id} workspaceMembers={members} />}
      </Drawer>
    </div>
  );
}
