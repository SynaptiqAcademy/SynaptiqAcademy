/**
 * SavedSearchControls — embed inside Discovery pages (Journals/Conferences/Grants).
 *
 * Props:
 *   kind: "journal" | "conference" | "grant"
 *   query: current free-text query
 *   filters: current filter object (will be persisted as `filters`)
 *
 * Renders:
 *   - "Save search" button (opens modal to name + pick digest frequency)
 *   - "Saved searches" button (opens drawer to list / edit / delete / preview)
 */
import React, { useCallback, useEffect, useState } from "react";
import api from "../../lib/api";
import { toast } from "sonner";
import {
  Bookmark, X, Edit3, Trash2, Mail, Eye, Calendar, CalendarDays,
  ChevronRight, Loader2, BookmarkPlus,
} from "lucide-react";
import { Link } from "react-router-dom";
import { NAVY } from "@/lib/tokens";

const FREQ_LABEL = { off: "No digest", daily: "Daily digest", weekly: "Weekly digest" };

export default function SavedSearchControls({ kind, query, filters }) {
  const [showSave, setShowSave] = useState(false);
  const [showManage, setShowManage] = useState(false);
  const [name, setName] = useState("");
  const [freq, setFreq] = useState("off");
  const [busy, setBusy] = useState(false);
  const [count, setCount] = useState(null);

  const loadCount = useCallback(async () => {
    try {
      const { data } = await api.get("/searches");
      setCount((data || []).filter((s) => s.kind === kind).length);
    } catch (e) { /* ignore */ }
  }, [kind]);
  useEffect(() => { loadCount(); }, [loadCount]);

  const save = async () => {
    if (!name.trim()) { toast.error("Name required"); return; }
    setBusy(true);
    try {
      await api.post("/searches", {
        kind, name: name.trim(), query: query || "",
        filters: filters || {}, frequency: freq,
      });
      toast.success("Search saved");
      setShowSave(false); setName(""); setFreq("off");
      loadCount();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    } finally { setBusy(false); }
  };

  return (
    <>
      <button
        data-testid="discovery-save-search-btn"
        onClick={() => setShowSave(true)}
        className="inline-flex items-center gap-1.5 text-xs border border-slate-300 px-3 py-2 hover:border-[#0F2847] hover:text-[#0F2847]"
        title="Save this search"
      >
        <BookmarkPlus size={12} strokeWidth={1.5} />
        Save search
      </button>
      <button
        data-testid="discovery-manage-searches-btn"
        onClick={() => setShowManage(true)}
        className="inline-flex items-center gap-1.5 text-xs border border-slate-300 px-3 py-2 hover:border-[#0F2847] hover:text-[#0F2847]"
      >
        <Bookmark size={12} strokeWidth={1.5} />
        Saved searches{count != null && count > 0 ? ` · ${count}` : ""}
      </button>

      {showSave && (
        <SaveSearchModal
          kind={kind} query={query} filters={filters}
          name={name} setName={setName} freq={freq} setFreq={setFreq}
          onClose={() => setShowSave(false)}
          onSubmit={save} busy={busy}
        />
      )}
      {showManage && (
        <ManageSearchesDrawer
          kind={kind}
          onClose={() => setShowManage(false)}
          onMutated={loadCount}
        />
      )}
    </>
  );
}

function SaveSearchModal({ kind, query, filters, name, setName, freq, setFreq, onClose, onSubmit, busy }) {
  return (
    <div className="fixed inset-0 z-[100] bg-slate-900/50 flex items-center justify-center px-4" onClick={onClose}>
      <div className="bg-white w-full max-w-md border border-slate-200" onClick={(e) => e.stopPropagation()} data-testid="save-search-modal">
        <div className="border-b border-slate-200 px-5 py-4 flex items-center justify-between">
          <div>
            <div className="overline">Discovery</div>
            <h3 className="font-serif text-xl text-slate-900">Save this {kind} search</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-900"><X size={16} strokeWidth={1.5} /></button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <div className="overline mb-2">Name</div>
            <input
              autoFocus
              data-testid="save-search-name"
              value={name} onChange={(e) => setName(e.target.value)}
              placeholder={`e.g. ${kind === 'journal' ? 'Q1 ML journals' : kind === 'conference' ? 'EU AI conferences' : 'NIH biomedical grants'}`}
              className="w-full px-3 py-2 border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0F2847] text-sm"
            />
          </div>
          <div className="bg-slate-50 border border-slate-200 px-3 py-2.5 text-xs">
            <div className="overline mb-1">Captured criteria</div>
            <div className="text-slate-700">
              {query ? <span className="font-mono">q: "{query}" </span> : <span className="text-slate-400">No keyword</span>}
            </div>
            <div className="text-slate-600 mt-1">
              {filters && Object.keys(filters).length > 0
                ? Object.entries(filters).map(([k, v]) => (
                  <span key={k} className="inline-block mr-2 font-mono">{k}: {String(v)}</span>
                ))
                : <span className="text-slate-400">No filters</span>}
            </div>
          </div>
          <div>
            <div className="overline mb-2">Email digest</div>
            <div className="grid grid-cols-3 gap-2">
              {["off", "daily", "weekly"].map((f) => (
                <button
                  key={f}
                  data-testid={`save-search-freq-${f}`}
                  onClick={() => setFreq(f)}
                  className={`text-xs border px-3 py-2 inline-flex items-center justify-center gap-1.5 ${freq === f ? "border-[#0F2847] bg-[#0F2847] text-white" : "border-slate-300 text-slate-600 hover:border-slate-400"}`}
                >
                  {f === "off" ? null : f === "daily" ? <Calendar size={11} strokeWidth={1.5} /> : <CalendarDays size={11} strokeWidth={1.5} />}
                  {FREQ_LABEL[f]}
                </button>
              ))}
            </div>
            <div className="text-[11px] text-slate-500 mt-2">
              We'll email you the newest items matching this search. You can change or stop anytime.
            </div>
          </div>
        </div>
        <div className="border-t border-slate-200 px-5 py-3 flex items-center justify-end gap-2">
          <button onClick={onClose} className="text-xs text-slate-600 hover:text-slate-900 px-3 py-2">Cancel</button>
          <button
            data-testid="save-search-submit"
            disabled={busy || !name.trim()}
            onClick={onSubmit}
            className="text-xs bg-[#0F2847] text-white px-4 py-2 hover:bg-slate-800 disabled:opacity-50 inline-flex items-center gap-1.5"
          >
            {busy && <Loader2 size={11} className="animate-spin" />} Save search
          </button>
        </div>
      </div>
    </div>
  );
}

function ManageSearchesDrawer({ kind, onClose, onMutated }) {
  const [items, setItems] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [previewing, setPreviewing] = useState(null);

  const load = async () => {
    try {
      const { data } = await api.get("/searches");
      setItems(data || []);
    } catch { setItems([]); }
  };
  useEffect(() => { load(); }, []);

  const update = async (s, patch) => {
    try {
      await api.patch(`/searches/${s.id}`, {
        kind: s.kind, name: patch.name ?? s.name, query: patch.query ?? s.query,
        filters: patch.filters ?? s.filters, frequency: patch.frequency ?? s.frequency,
      });
      toast.success("Updated");
      setEditingId(null); load(); onMutated?.();
    } catch (e) { toast.error("Failed"); }
  };

  const del = async (sid) => {
    if (!confirm("Delete this saved search?")) return;
    try { await api.delete(`/searches/${sid}`); load(); onMutated?.(); }
    catch (e) { toast.error("Failed"); }
  };

  const preview = async (s) => {
    setPreviewing({ search: s, loading: true, items: [] });
    try {
      const { data } = await api.post(`/searches/${s.id}/preview`);
      setPreviewing({ search: s, loading: false, items: data.items || [] });
    } catch (e) {
      setPreviewing({ search: s, loading: false, items: [], error: "Preview failed" });
    }
  };

  const filtered = (items || []).filter((s) => s.kind === kind);

  return (
    <div className="fixed inset-0 z-[100] flex" onClick={onClose} data-testid="saved-searches-drawer">
      <div className="absolute inset-0 bg-slate-900/40" />
      <div className="ml-auto relative w-full max-w-xl h-full bg-white border-l border-slate-200 flex flex-col shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="border-b border-slate-200 px-5 py-4 flex items-center justify-between">
          <div>
            <div className="overline">Saved {kind} searches</div>
            <h3 className="font-serif text-xl text-slate-900 mt-0.5">Your watchlist</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-900"><X size={16} strokeWidth={1.5} /></button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3 bg-slate-50/40">
          {items === null && <div className="text-sm text-slate-500 font-mono">Loading…</div>}
          {items && filtered.length === 0 && (
            <div className="text-center py-12 border border-dashed border-slate-300 text-sm text-slate-500">
              No saved {kind} searches yet. Save your current search to get digests when new matches arrive.
            </div>
          )}
          {filtered.map((s) => (
            <SavedSearchCard
              key={s.id}
              s={s}
              isEditing={editingId === s.id}
              onEdit={() => setEditingId(s.id)}
              onCancelEdit={() => setEditingId(null)}
              onUpdate={(patch) => update(s, patch)}
              onDelete={() => del(s.id)}
              onPreview={() => preview(s)}
            />
          ))}
        </div>
        {previewing && (
          <PreviewModal data={previewing} onClose={() => setPreviewing(null)} />
        )}
      </div>
    </div>
  );
}

function SavedSearchCard({ s, isEditing, onEdit, onCancelEdit, onUpdate, onDelete, onPreview }) {
  const [name, setName] = useState(s.name);
  const [freq, setFreq] = useState(s.frequency);

  useEffect(() => { setName(s.name); setFreq(s.frequency); }, [s.id, s.name, s.frequency]);

  return (
    <div className="border border-slate-200 bg-white p-4" data-testid={`saved-search-${s.id}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          {isEditing ? (
            <input
              value={name} onChange={(e) => setName(e.target.value)}
              className="w-full px-2 py-1 border border-slate-300 text-sm"
              autoFocus
            />
          ) : (
            <div className="font-serif text-lg text-slate-900">{s.name}</div>
          )}
          <div className="text-xs text-slate-500 mt-1 font-mono">
            {s.query ? `"${s.query}"` : "No keyword"}
            {s.filters && Object.keys(s.filters).length > 0 && (
              <span className="ml-2">· {Object.entries(s.filters).map(([k, v]) => `${k}=${v}`).join(", ")}</span>
            )}
          </div>
        </div>
        <span className={`overline px-2 py-0.5 border shrink-0 ${
          s.frequency === "daily" ? "border-emerald-300 bg-emerald-50 text-emerald-700"
          : s.frequency === "weekly" ? "border-[#0F2847]/30 bg-[#0F2847]/5 text-[#0F2847]"
          : "border-slate-200 bg-slate-50 text-slate-500"
        }`}>
          {FREQ_LABEL[s.frequency]}
        </span>
      </div>

      {isEditing && (
        <div className="mt-3 space-y-2">
          <div className="grid grid-cols-3 gap-2">
            {["off", "daily", "weekly"].map((f) => (
              <button
                key={f}
                onClick={() => setFreq(f)}
                className={`text-[11px] border px-2 py-1.5 ${freq === f ? "border-[#0F2847] bg-[#0F2847] text-white" : "border-slate-300 text-slate-600"}`}
              >
                {FREQ_LABEL[f]}
              </button>
            ))}
          </div>
          <div className="flex items-center justify-end gap-2">
            <button onClick={onCancelEdit} className="text-xs text-slate-600 px-2 py-1">Cancel</button>
            <button
              data-testid={`saved-search-save-${s.id}`}
              onClick={() => onUpdate({ name: name.trim() || s.name, frequency: freq })}
              className="text-xs bg-[#0F2847] text-white px-3 py-1.5 hover:bg-slate-800"
            >
              Update
            </button>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between mt-3 text-[10px] font-mono text-slate-400">
        <span>
          {s.last_sent_at ? `Last digest: ${new Date(s.last_sent_at).toLocaleDateString()}` : "No digest sent yet"}
        </span>
        {!isEditing && (
          <div className="flex items-center gap-2 text-slate-500">
            <button
              data-testid={`saved-search-preview-${s.id}`}
              onClick={onPreview}
              className="hover:text-[#0F2847] inline-flex items-center gap-1"
              title="Preview current matches"
            >
              <Eye size={11} strokeWidth={1.5} /> Preview
            </button>
            <button onClick={onEdit} className="hover:text-[#0F2847] inline-flex items-center gap-1">
              <Edit3 size={11} strokeWidth={1.5} /> Edit
            </button>
            <button
              data-testid={`saved-search-delete-${s.id}`}
              onClick={onDelete} className="hover:text-red-600 inline-flex items-center gap-1"
            >
              <Trash2 size={11} strokeWidth={1.5} /> Delete
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function PreviewModal({ data, onClose }) {
  const { search, loading, items, error } = data;
  return (
    <div data-testid="saved-search-preview-modal" className="absolute inset-0 z-10 bg-slate-900/40 flex items-center justify-center px-4" onClick={onClose}>
      <div className="bg-white w-full max-w-lg max-h-[80vh] border border-slate-200 flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="border-b border-slate-200 px-5 py-3 flex items-center justify-between">
          <div>
            <div className="overline">Preview · {search.kind}</div>
            <div className="font-serif text-lg text-slate-900">{search.name}</div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-900"><X size={14} strokeWidth={1.5} /></button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-2 bg-slate-50/40">
          {loading && <div className="text-sm text-slate-500 font-mono">Loading…</div>}
          {error && <div className="text-sm text-red-600">{error}</div>}
          {!loading && items.length === 0 && !error && <div className="text-sm text-slate-500">No matches right now.</div>}
          {items.map((it) => {
            const path = search.kind === "journal" ? `/journals/${it.id}` : search.kind === "conference" ? `/conferences/${it.id}` : `/grants/${it.id}`;
            return (
              <Link key={it.id} to={path} className="block border border-slate-200 bg-white p-3 hover:border-[#0F2847]">
                <div className="font-serif text-sm text-slate-900 line-clamp-2">{it.title}</div>
                <div className="text-[11px] text-slate-500 mt-1 font-mono">{it.subtitle}</div>
                {it.deadline && <div className="text-[10px] font-mono text-amber-700 mt-1">Deadline: {it.deadline}</div>}
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
