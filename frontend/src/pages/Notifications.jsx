/* eslint-disable */
/**
 * Inbox — Notification Center
 *
 * IA note: Inbox and Messages previously shared overlapping navigation
 * (Collaborations/Projects/Workspaces appeared as filters on both pages)
 * and this page surfaced raw "New message" notification stubs — content
 * that duplicated the actual conversation, which lives in Messages. Fixed:
 *
 *   - Notifications of type "message" are excluded from this feed entirely.
 *     A new message is signaled by the Messages page and its own unread
 *     badges, never by a chat preview sitting in the Notification Center.
 *   - The left nav is organized by NOTIFICATION KIND (what happened), not
 *     by conversation context (who/where) — Messages owns that axis.
 *   - "Mentions" stays, since a mention is an alert about being called out,
 *     not a conversation itself; clicking it deep-links into Messages.
 *
 * Ground-up presentation redesign. Zero backend changes.
 *
 * APIs preserved exactly (same calls, same payloads, same behavior):
 *   GET    /notifications
 *   POST   /notifications/{id}/read
 *   POST   /notifications/read-all
 *   DELETE /notifications/{id}
 *   DELETE /notifications          (clear read)
 *
 * Pin, Archive and Labels are real, working features implemented entirely
 * client-side (localStorage) since the backend has no such fields; nothing
 * here is decorative. There is no per-item AI summary, sentiment, or
 * detected-deadline field in the data — none is fabricated. The
 * intelligence panel surfaces only what is genuinely derivable from the
 * real payload (type, priority, body, link, and aggregate counts).
 */
import React, { useEffect, useMemo, useState, useRef, useCallback } from "react";
import { Button } from "@/components/ds";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { ErrorState } from "@/components/ds/ErrorState";
import { usePersistentSet } from "@/hooks/usePersistentSet";
import { ShortcutsModal } from "@/components/shared/ShortcutsModal";
import {
  ACCENT, NAVY, NAVY2, WARM, BRDX, WHITE,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_DISABLED,
  SHADOW_CARD, SHADOW_CARD_HOVER,
  EMERALD, AMBER, CRIMSON,
  RADIUS_LG, RADIUS_MD, RADIUS_FULL,
} from "@/lib/tokens";
import {
  Inbox as InboxIcon, Circle, Zap, AtSign, MessageSquare, Users2,
  FolderOpen, Layers, BookMarked, Coins, BrainCircuit, Activity,
  Star, Archive as ArchiveIcon, Tag, Bell, UserCheck, Briefcase, BookOpen,
  Search, X, CheckCheck, Settings, ArrowUpDown, Keyboard,
  ChevronRight, ExternalLink, Check, Plus, Sparkles,
} from "lucide-react";

// ─── Neutral palette — no per-type rainbow, one accent only ──────────────────

const INK      = "#1C2333";                 // charcoal — primary UI ink
const NAV_BG   = WHITE;
const RAIL_BG  = "#FAFAFB";
const HAIR     = BRDX;

// ─── Notification type → icon + label (business classification, unchanged) ──

const KIND_CONFIG = {
  message:              { icon: MessageSquare, label: "Message" },
  mention:              { icon: AtSign,        label: "Mention" },
  invitation:           { icon: Users2,        label: "Invitation" },
  workspace_invitation: { icon: Layers,        label: "Workspace" },
  collaboration:        { icon: Users2,        label: "Collaboration" },
  application:          { icon: Users2,        label: "Application" },
  workspace:            { icon: Layers,        label: "Workspace" },
  workspace_created:    { icon: Layers,        label: "Workspace" },
  project:              { icon: FolderOpen,    label: "Project" },
  manuscript:           { icon: BookMarked,    label: "Manuscript" },
  grant:                { icon: Coins,         label: "Grant" },
  funding:              { icon: Coins,         label: "Funding" },
  citation:             { icon: BookMarked,    label: "Citation" },
  publication:          { icon: BookMarked,    label: "Publication" },
  reputation:           { icon: Star,          label: "Reputation" },
  ai:                   { icon: BrainCircuit,  label: "AI" },
  security:             { icon: Bell,          label: "Security" },
  system:               { icon: Activity,      label: "System" },
  review:               { icon: BookMarked,    label: "Review" },
  teaching:             { icon: Users2,        label: "Teaching" },
  research:             { icon: FolderOpen,    label: "Research" },
  conference:           { icon: BookMarked,    label: "Conference" },
  journal:              { icon: BookMarked,    label: "Journal" },
  analytics:            { icon: Activity,      label: "Analytics" },
};
const DEFAULT_KIND = { icon: Bell, label: "Notification" };

function kindConfig(type) {
  if (!type) return DEFAULT_KIND;
  const t = type.toLowerCase();
  if (KIND_CONFIG[t]) return KIND_CONFIG[t];
  for (const k of Object.keys(KIND_CONFIG)) {
    if (t.includes(k)) return KIND_CONFIG[k];
  }
  return DEFAULT_KIND;
}

// ─── Priority (unchanged heuristic, exposed to users as "AI Priority") ───────

const HIGH_TYPES = ["security", "invitation", "workspace_invitation", "application"];
const MED_TYPES  = ["collaboration", "message", "mention", "manuscript", "grant", "review", "workspace"];

function getPriority(type) {
  if (!type) return "low";
  const t = type.toLowerCase();
  if (HIGH_TYPES.some(k => t.includes(k))) return "high";
  if (MED_TYPES.some(k => t.includes(k))) return "medium";
  return "low";
}

// ─── Time helpers (unchanged) ────────────────────────────────────────────────

function timeAgo(iso) {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60)     return "just now";
  if (diff < 3600)   return `${Math.floor(diff / 60)}m`;
  if (diff < 86400)  return `${Math.floor(diff / 3600)}h`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d`;
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function fullDate(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-GB", {
    weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit",
  });
}

function groupByDate(items) {
  const now = new Date();
  const todayStr     = now.toDateString();
  const yesterdayStr = new Date(now - 86400000).toDateString();
  const weekAgo      = now.getTime() - 7 * 86400000;
  const groups = { today: [], yesterday: [], week: [], older: [] };
  for (const n of items) {
    const d = new Date(n.created_at);
    const ds = d.toDateString();
    if (ds === todayStr)     groups.today.push(n);
    else if (ds === yesterdayStr) groups.yesterday.push(n);
    else if (d.getTime() >= weekAgo) groups.week.push(n);
    else groups.older.push(n);
  }
  return groups;
}

// ─── Filters — organized by NOTIFICATION KIND, never by conversation ────────
// context (that axis — direct/team/project/workspace — belongs to Messages).

const NAV_ITEMS = [
  { key: "all",           label: "All",         icon: InboxIcon },
  { key: "unread",        label: "Unread",      icon: Circle },
  { key: "priority",      label: "Needs Action",icon: Zap },
];

// Each category's match() runs against the real `type` field — this is the
// same substring classification the page always used, just consolidated
// into fewer, clearer buckets so it no longer echoes Messages' taxonomy.
const CATEGORY_ITEMS = [
  { key: "approvals",   label: "Approvals & Invitations",    icon: UserCheck,
    match: t => ["invitation", "application", "collaboration"].some(k => t.includes(k)) },
  { key: "mention",     label: "Mentions",                   icon: AtSign,
    match: t => t.includes("mention") },
  { key: "workspace",   label: "Workspace & Project Updates",icon: Briefcase,
    match: t => ["workspace", "project"].some(k => t.includes(k)) },
  { key: "review",      label: "Reviewer Feedback",          icon: BookOpen,
    match: t => t.includes("review") },
  { key: "publishing",  label: "Publishing Updates",         icon: BookMarked,
    match: t => ["manuscript", "journal", "publication", "citation", "conference"].some(k => t.includes(k)) },
  { key: "funding",     label: "Funding Alerts",             icon: Coins,
    match: t => ["grant", "funding"].some(k => t.includes(k)) },
  { key: "ai",          label: "AI Alerts",                  icon: BrainCircuit,
    match: t => t === "ai" || t.includes("ai_") },
  { key: "system",      label: "System Notifications",       icon: Activity,
    match: t => ["system", "security"].some(k => t.includes(k)) },
];

function matchesFilter(n, key, ctx) {
  const t = (n.type || "").toLowerCase();
  if (key === "all")      return true;
  if (key === "unread")   return !n.read;
  if (key === "priority") return !n.read && getPriority(n.type) === "high";
  if (key === "pinned")   return ctx.pinned.has(n.id);
  if (key.startsWith("label:")) return ctx.labels[n.id] === key.slice(6);
  const cat = CATEGORY_ITEMS.find(c => c.key === key);
  if (cat) return cat.match(t);
  return t.includes(key);
}

// Chat-thread activity is Messages' territory, never shown here.
function isConversationStub(n) {
  return (n.type || "").toLowerCase() === "message";
}

function matchesSearch(n, q) {
  if (!q) return true;
  const lq = q.toLowerCase();
  return [n.title, n.body, n.type].some(s => (s || "").toLowerCase().includes(lq));
}

// ─── Inline action builder (unchanged) ───────────────────────────────────────

function getActions(n) {
  const t = (n.type || "").toLowerCase();
  const hasLink = n.link && n.link !== "#";
  const actions = [];

  if (t.includes("invitation") || t.includes("application")) {
    actions.push({ label: "Accept",  variant: "accept", to: n.link });
    // "Dismiss" (not "Decline"): this only marks the notification read —
    // there's no reliable per-type request id on the notification payload
    // to call a real accept/decline endpoint against, so the label must
    // match what actually happens rather than implying a response was sent.
    actions.push({ label: "Dismiss", variant: "decline" });
  } else if (t.includes("message") || t.includes("mention")) {
    if (hasLink) actions.push({ label: "Reply", variant: "primary", to: n.link });
  } else if (hasLink) {
    const label = t.includes("manuscript") ? "View manuscript" :
                  t.includes("workspace") ? "Open workspace" :
                  t.includes("review") ? "Review" :
                  t.includes("grant") ? "View grant" :
                  t.includes("ai") ? "View results" :
                  "Open";
    actions.push({ label, variant: "link", to: n.link });
  }

  return actions;
}

// ─── Smart digest (unchanged logic, relocated into the intelligence panel) ──

function buildSummaryBullets(items) {
  const unread = items.filter(n => !n.read);
  if (!unread.length) return [];
  const bullets = [];

  const collabs = unread.filter(n => (n.type || "").toLowerCase().includes("invitation") || (n.type || "").toLowerCase().includes("collaboration"));
  if (collabs.length) bullets.push(`${collabs.length} collaboration ${collabs.length === 1 ? "request" : "requests"} awaiting your response`);

  const manuscripts = unread.filter(n => {
    const t = (n.type || "").toLowerCase();
    return t.includes("manuscript") || t.includes("review") || t.includes("publication");
  });
  if (manuscripts.length) bullets.push(`${manuscripts.length} manuscript ${manuscripts.length === 1 ? "update" : "updates"} available`);

  const citations = unread.filter(n => {
    const t = (n.type || "").toLowerCase();
    return t.includes("citation") || (n.title || "").toLowerCase().includes("citation");
  });
  if (citations.length) bullets.push(`${citations.length} new citation${citations.length > 1 ? "s" : ""} detected`);

  const grants = unread.filter(n => {
    const t = (n.type || "").toLowerCase();
    return t.includes("grant") || t.includes("funding") || (n.title || "").toLowerCase().includes("deadline");
  });
  if (grants.length) bullets.push(`${grants.length} grant notification${grants.length > 1 ? "s" : ""} requiring attention`);

  const aiItems = unread.filter(n => (n.type || "").toLowerCase() === "ai");
  if (aiItems.length) bullets.push(`${aiItems.length} AI task${aiItems.length > 1 ? "s" : ""} completed`);

  // "message"-type items never reach this function (filtered out before Inbox
  // sees them), so this only ever counts mentions — worded accordingly.
  const mentions = unread.filter(n => (n.type || "").toLowerCase().includes("mention"));
  if (mentions.length) bullets.push(`${mentions.length} mention${mentions.length > 1 ? "s" : ""} to review`);

  if (!bullets.length) bullets.push(`${unread.length} unread notification${unread.length > 1 ? "s" : ""}`);

  return bullets.slice(0, 6);
}

// ─── Client-only persistence — real, working, zero backend surface ──────────

function useLocalLabels(key) {
  const [map, setMap] = useState(() => {
    try { return JSON.parse(localStorage.getItem(key) || "{}"); } catch { return {}; }
  });
  const setLabel = useCallback((id, label) => {
    setMap(prev => {
      const next = { ...prev };
      if (!label) delete next[id]; else next[id] = label;
      try { localStorage.setItem(key, JSON.stringify(next)); } catch {}
      return next;
    });
  }, [key]);
  return [map, setLabel];
}

const LABEL_PALETTE = [ACCENT, NAVY, EMERALD, "#7C3AED", "#0891B2"];
function labelColor(name) {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return LABEL_PALETTE[h % LABEL_PALETTE.length];
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function Notifications() {
  const navigate   = useNavigate();
  const [items,   setItems]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [filter,  setFilter]  = useState("all");
  const [q,       setQ]       = useState("");
  const [sortBy,  setSortBy]  = useState("newest"); // newest | priority
  const [selectedId, setSelectedId] = useState(null);
  const [mobilePanelOpen, setMobilePanelOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const searchRef = useRef(null);
  const listRef = useRef(null);

  const [pinned,   togglePinned]   = usePersistentSet("sq_inbox_pinned_v1");
  const [archived, toggleArchived] = usePersistentSet("sq_inbox_archived_v1");
  const [labels,   setLabel]       = useLocalLabels("sq_inbox_labels_v1");

  const load = async () => {
    setLoading(true);
    setLoadError(false);
    try {
      const { data } = await api.get("/notifications");
      setItems(data || []);
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  // ── API actions (unchanged) ─────────────────────────────────────────────
  const markAll = async () => {
    try {
      await api.post("/notifications/read-all");
      setItems(prev => prev.map(n => ({ ...n, read: true })));
    } catch {
      toast.error("Could not mark all as read. Please try again.");
    }
  };

  const markOne = async id => {
    try {
      await api.post(`/notifications/${id}/read`);
      setItems(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    } catch {
      toast.error("Could not mark as read. Please try again.");
    }
  };

  const deleteOne = async id => {
    try {
      await api.delete(`/notifications/${id}`);
      setItems(prev => prev.filter(n => n.id !== id));
      if (selectedId === id) setSelectedId(null);
    } catch {
      toast.error("Could not delete this notification. Please try again.");
    }
  };

  const deleteRead = async () => {
    try {
      await api.delete("/notifications");
      setItems(prev => prev.filter(n => !n.read));
    } catch {
      toast.error("Could not clear read notifications. Please try again.");
    }
  };

  // ── Derived ─────────────────────────────────────────────────────────────
  // Conversation-stub notifications ("New message") never surface here —
  // that content belongs to Messages. They still exist in `items` (so
  // mark-all-read / delete-read behave exactly as before), just excluded
  // from everything the user sees or counts in this Notification Center.
  const visibleItems = useMemo(() => items.filter(n => !isConversationStub(n)), [items]);

  const unreadCount   = visibleItems.filter(n => !n.read).length;
  const priorityCount = visibleItems.filter(n => !n.read && getPriority(n.type) === "high").length;
  const hasRead       = visibleItems.some(n => n.read);
  const knownLabels   = useMemo(() => [...new Set(Object.values(labels))].sort(), [labels]);

  const ctx = { pinned, labels };

  const scoped = useMemo(() => {
    const base = filter === "pinned" ? visibleItems.filter(n => pinned.has(n.id)) : visibleItems;
    return base.filter(n => showArchived ? archived.has(n.id) : !archived.has(n.id));
  }, [visibleItems, filter, pinned, archived, showArchived]);

  const filtered = useMemo(() => {
    let list = scoped.filter(n => matchesFilter(n, filter, ctx) && matchesSearch(n, q));
    if (sortBy === "priority") {
      const rank = { high: 0, medium: 1, low: 2 };
      list = [...list].sort((a, b) => {
        if (a.read !== b.read) return a.read ? 1 : -1;
        return rank[getPriority(a.type)] - rank[getPriority(b.type)];
      });
    }
    return list;
  }, [scoped, filter, q, sortBy, ctx]);

  const groups  = useMemo(() => groupByDate(filtered), [filtered]);
  const flatOrdered = useMemo(() => [...groups.today, ...groups.yesterday, ...groups.week, ...groups.older], [groups]);
  const bullets = useMemo(() => buildSummaryBullets(visibleItems), [visibleItems]);
  const selected = useMemo(() => visibleItems.find(n => n.id === selectedId) || null, [visibleItems, selectedId]);

  const relatedCount = useMemo(() => {
    if (!selected) return 0;
    return visibleItems.filter(n => n.id !== selected.id && kindConfig(n.type).label === kindConfig(selected.type).label && !archived.has(n.id)).length;
  }, [visibleItems, selected, archived]);

  // ── Keyboard model ──────────────────────────────────────────────────────
  useEffect(() => {
    function isTyping() {
      const el = document.activeElement;
      return el?.tagName === "INPUT" || el?.tagName === "TEXTAREA" || el?.isContentEditable;
    }
    function onKey(e) {
      if (isTyping()) return;
      const idx = flatOrdered.findIndex(n => n.id === selectedId);

      if (e.key === "ArrowDown" || e.key === "j") {
        e.preventDefault();
        const next = flatOrdered[Math.min(flatOrdered.length - 1, idx + 1)];
        if (next) { setSelectedId(next.id); setMobilePanelOpen(false); }
      } else if (e.key === "ArrowUp" || e.key === "k") {
        e.preventDefault();
        const prev = flatOrdered[Math.max(0, idx - 1)];
        if (prev) { setSelectedId(prev.id); setMobilePanelOpen(false); }
      } else if (e.key === "Enter") {
        if (selected) {
          if (!selected.read) markOne(selected.id);
          if (selected.link && selected.link !== "#") navigate(selected.link);
        }
      } else if (e.key === "e") {
        if (selected) toggleArchived(selected.id);
      } else if (e.key === "p") {
        if (selected) togglePinned(selected.id);
      } else if (e.key === "u") {
        if (selected && !selected.read) markOne(selected.id);
      } else if (e.key === "?") {
        setShortcutsOpen(o => !o);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [flatOrdered, selectedId, selected, navigate, toggleArchived, togglePinned]);

  function selectItem(id) {
    setSelectedId(id);
    setMobilePanelOpen(true);
  }

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div
      className="flex flex-col lg:flex-row"
      style={{ margin: "-24px -24px 0", minHeight: "calc(100vh - 56px)", background: NAV_BG }}
    >
      {/* ══════════════ LEFT — smart navigation ══════════════ */}
      <SideNav
        filter={filter} setFilter={f => { setFilter(f); setSelectedId(null); }}
        unreadCount={unreadCount} priorityCount={priorityCount}
        pinnedCount={pinned.size} archivedCount={archived.size}
        knownLabels={knownLabels}
        showArchived={showArchived} setShowArchived={setShowArchived}
      />
      {/* ══════════════ CENTER + RIGHT ══════════════ */}
      <div className="flex-1 min-w-0 flex flex-col">

        {/* ── TOP — premium toolbar ── */}
        <Toolbar
          q={q} setQ={setQ} searchRef={searchRef}
          sortBy={sortBy} setSortBy={setSortBy}
          unreadCount={unreadCount} hasRead={hasRead}
          onMarkAll={markAll} onClearRead={deleteRead}
          onShortcuts={() => setShortcutsOpen(true)}
          resultCount={filtered.length}
        />

        <div className="flex-1 min-w-0 flex overflow-hidden">
          {/* ── CENTER — the feed ── */}
          <div className="flex-1 min-w-0 overflow-y-auto" ref={listRef} data-testid={TID.notificationsList}>
            {loading && <FeedSkeleton />}

            {!loading && loadError && filtered.length === 0 && (
              <ErrorState message="Could not load your notifications." onRetry={load} />
            )}

            {!loading && !loadError && filtered.length === 0 && (
              <FeedEmptyState
                hasFilter={filter !== "all" || !!q || showArchived}
                showArchived={showArchived}
                onClear={() => { setFilter("all"); setQ(""); setShowArchived(false); }}
              />
            )}

            {!loading && filtered.length > 0 && (
              <div className="max-w-[760px]">
                <FeedGroup label="Today"             items={groups.today}     {...rowProps()} />
                <FeedGroup label="Yesterday"         items={groups.yesterday} {...rowProps()} />
                <FeedGroup label="Earlier this week" items={groups.week}      {...rowProps()} />
                <FeedGroup label="Older"             items={groups.older}     {...rowProps()} />
              </div>
            )}
          </div>

          {/* ── RIGHT — intelligence panel (desktop) ── */}
          <div className="hidden xl:block" style={{ width: 360, flexShrink: 0, borderLeft: `1px solid ${HAIR}` }}>
            <IntelligencePanel
              selected={selected}
              bullets={bullets}
              unreadCount={unreadCount}
              priorityCount={priorityCount}
              relatedCount={relatedCount}
              isPinned={selected ? pinned.has(selected.id) : false}
              isArchived={selected ? archived.has(selected.id) : false}
              label={selected ? labels[selected.id] : null}
              knownLabels={knownLabels}
              onTogglePin={() => selected && togglePinned(selected.id)}
              onToggleArchive={() => selected && toggleArchived(selected.id)}
              onSetLabel={(l) => selected && setLabel(selected.id, l)}
              onRead={() => selected && !selected.read && markOne(selected.id)}
              onViewPriority={() => setFilter("priority")}
              onDelete={() => selected && deleteOne(selected.id)}
            />
          </div>
        </div>
      </div>
      {/* ── RIGHT panel as a mobile/tablet slide-over ── */}
      {mobilePanelOpen && selected && (
        <div className="xl:hidden fixed inset-0 z-50 flex justify-end" style={{ background: "rgba(15,23,42,0.35)" }} onClick={() => setMobilePanelOpen(false)}>
          <div
            className="h-full w-full sm:w-[420px] overflow-y-auto"
            style={{ background: WHITE, boxShadow: "-16px 0 48px rgba(15,23,42,0.14)" }}
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: `1px solid ${HAIR}` }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: TEXT_PRIMARY }}>Details</span>
              <Button
                size="icon"
                variant="ghost"
                onClick={() => setMobilePanelOpen(false)}
                aria-label="Close details"
                style={{
                  color: TEXT_MUTED
                }}>
                <X size={18} />
              </Button>
            </div>
            <IntelligencePanel
              selected={selected}
              bullets={bullets}
              unreadCount={unreadCount}
              priorityCount={priorityCount}
              relatedCount={relatedCount}
              isPinned={selected ? pinned.has(selected.id) : false}
              isArchived={selected ? archived.has(selected.id) : false}
              label={selected ? labels[selected.id] : null}
              knownLabels={knownLabels}
              onTogglePin={() => selected && togglePinned(selected.id)}
              onToggleArchive={() => selected && toggleArchived(selected.id)}
              onSetLabel={(l) => selected && setLabel(selected.id, l)}
              onRead={() => selected && !selected.read && markOne(selected.id)}
              onViewPriority={() => { setFilter("priority"); setMobilePanelOpen(false); }}
              onDelete={() => selected && deleteOne(selected.id)}
            />
          </div>
        </div>
      )}
      {shortcutsOpen && <ShortcutsModal onClose={() => setShortcutsOpen(false)} rows={INBOX_SHORTCUT_ROWS} />}
    </div>
  );

  function rowProps() {
    return {
      selectedId, onSelect: selectItem, onRead: markOne, onDelete: deleteOne,
      pinned, onTogglePin: togglePinned, archived, onToggleArchive: toggleArchived,
      labels,
    };
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// LEFT — Smart navigation
// ═══════════════════════════════════════════════════════════════════════════

function SideNav({ filter, setFilter, unreadCount, priorityCount, pinnedCount, archivedCount, knownLabels, showArchived, setShowArchived }) {
  return (
    <>
      {/* Desktop rail */}
      <aside
        className="hidden lg:flex flex-col"
        style={{ width: 228, flexShrink: 0, background: RAIL_BG, borderRight: `1px solid ${HAIR}`, padding: "20px 12px" }}
      >
        <div className="px-2 mb-5">
          <h1 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "1.15rem", fontWeight: 700, color: INK, letterSpacing: "-0.02em", margin: "0 0 3px" }}>
            Inbox
          </h1>
          <p style={{ fontSize: "0.68rem", color: TEXT_MUTED, margin: 0, lineHeight: 1.4 }}>
            Things that need your attention.
          </p>
        </div>

        <NavGroup>
          {NAV_ITEMS.map(item => (
            <NavRow
              key={item.key}
              label={item.label}
              icon={item.icon}
              active={!showArchived && filter === item.key}
              count={item.key === "unread" ? unreadCount : item.key === "priority" ? priorityCount : null}
              onClick={() => { setShowArchived(false); setFilter(item.key); }}
            />
          ))}
        </NavGroup>

        <div style={{ height: 1, background: HAIR, margin: "14px 8px" }} />

        <NavSectionLabel>Categories</NavSectionLabel>
        <NavGroup>
          {CATEGORY_ITEMS.map(item => (
            <NavRow
              key={item.key}
              label={item.label}
              icon={item.icon}
              active={!showArchived && filter === item.key}
              onClick={() => { setShowArchived(false); setFilter(item.key); }}
            />
          ))}
        </NavGroup>

        <div style={{ height: 1, background: HAIR, margin: "14px 8px" }} />

        <NavSectionLabel>Yours</NavSectionLabel>
        <NavGroup>
          <NavRow
            label="Pinned" icon={Star}
            active={!showArchived && filter === "pinned"}
            count={pinnedCount || null}
            onClick={() => { setShowArchived(false); setFilter("pinned"); }}
          />
          <NavRow
            label="Archive" icon={ArchiveIcon}
            active={showArchived}
            count={archivedCount || null}
            onClick={() => setShowArchived(true)}
          />
        </NavGroup>

        {knownLabels.length > 0 && (
          <>
            <div style={{ height: 1, background: HAIR, margin: "14px 8px" }} />
            <NavSectionLabel>Labels</NavSectionLabel>
            <NavGroup>
              {knownLabels.map(l => (
                <NavRow
                  key={l}
                  label={l}
                  dotColor={labelColor(l)}
                  active={!showArchived && filter === `label:${l}`}
                  onClick={() => { setShowArchived(false); setFilter(`label:${l}`); }}
                />
              ))}
            </NavGroup>
          </>
        )}
      </aside>

      {/* Compact horizontal rail — below lg */}
      <div
        className="flex lg:hidden gap-1.5 overflow-x-auto px-4 py-2.5"
        style={{ borderBottom: `1px solid ${HAIR}`, background: RAIL_BG, scrollbarWidth: "none" }}
      >
        {[...NAV_ITEMS, ...CATEGORY_ITEMS].map(item => (
          <CompactPill
            key={item.key}
            label={item.label}
            active={!showArchived && filter === item.key}
            count={item.key === "unread" ? unreadCount : item.key === "priority" ? priorityCount : null}
            onClick={() => { setShowArchived(false); setFilter(item.key); }}
          />
        ))}
        <CompactPill label="Pinned" active={!showArchived && filter === "pinned"} onClick={() => { setShowArchived(false); setFilter("pinned"); }} />
        <CompactPill label="Archive" active={showArchived} onClick={() => setShowArchived(true)} />
      </div>
    </>
  );
}

function NavGroup({ children }) {
  return <div className="flex flex-col gap-0.5">{children}</div>;
}

function NavSectionLabel({ children }) {
  return (
    <div style={{ fontSize: "0.63rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: TEXT_DISABLED, padding: "0 10px 6px" }}>
      {children}
    </div>
  );
}

function NavRow({ label, icon: Icon, dotColor, active, count, onClick }) {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: "flex", alignItems: "center", gap: 9,
        width: "100%", textAlign: "left",
        padding: "7px 10px", borderRadius: RADIUS_MD,
        border: "none", cursor: "pointer",
        background: active ? WHITE : hov ? "rgba(15,23,42,0.03)" : "transparent",
        boxShadow: active ? SHADOW_CARD : "none",
        transition: "background 120ms ease",
      }}
    >
      {Icon ? (
        <Icon size={14} strokeWidth={1.75} style={{ color: active ? ACCENT : TEXT_MUTED, flexShrink: 0 }} />
      ) : (
        <span style={{ width: 7, height: 7, borderRadius: "50%", background: dotColor || TEXT_MUTED, flexShrink: 0 }} />
      )}
      <span style={{ fontSize: "0.82rem", fontWeight: active ? 600 : 500, color: active ? INK : TEXT_SECONDARY, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {label}
      </span>
      {count != null && count > 0 && (
        <span style={{
          fontSize: "0.65rem", fontWeight: 700, minWidth: 17, textAlign: "center",
          color: active ? WHITE : TEXT_MUTED, background: active ? ACCENT : "rgba(15,23,42,0.06)",
          borderRadius: RADIUS_FULL, padding: "1px 5px",
        }}>
          {count}
        </span>
      )}
    </button>
  );
}

function CompactPill({ label, active, count, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        flexShrink: 0, whiteSpace: "nowrap",
        display: "inline-flex", alignItems: "center", gap: 5,
        padding: "6px 12px", borderRadius: RADIUS_FULL,
        border: `1px solid ${active ? ACCENT : HAIR}`,
        background: active ? ACCENT : WHITE,
        color: active ? WHITE : TEXT_SECONDARY,
        fontSize: "0.78rem", fontWeight: active ? 600 : 500,
        cursor: "pointer",
      }}
    >
      {label}
      {count != null && count > 0 && (
        <span style={{ fontSize: "0.62rem", fontWeight: 700, opacity: 0.85 }}>{count}</span>
      )}
    </button>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// TOP — Premium toolbar
// ═══════════════════════════════════════════════════════════════════════════

function Toolbar({ q, setQ, searchRef, sortBy, setSortBy, unreadCount, hasRead, onMarkAll, onClearRead, onShortcuts, resultCount }) {
  const [sortOpen, setSortOpen] = useState(false);

  return (
    <div
      className="flex items-center gap-3 px-5 py-3"
      style={{ borderBottom: `1px solid ${HAIR}`, background: WHITE }}
    >
      <div style={{ position: "relative", flex: 1, maxWidth: 420 }}>
        <Search size={14} style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: TEXT_MUTED }} />
        <input
          ref={searchRef}
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="Search your inbox…"
          aria-label="Search notifications"
          style={{
            width: "100%", padding: "8px 12px 8px 32px",
            border: `1px solid ${HAIR}`, borderRadius: RADIUS_MD,
            background: RAIL_BG, fontSize: "0.82rem", color: TEXT_PRIMARY,
            outline: "none",
          }}
          onFocus={e => e.target.style.borderColor = ACCENT}
          onBlur={e => e.target.style.borderColor = HAIR}
        />
        {q && (
          <Button
            size="icon"
            variant="ghost"
            onClick={() => setQ("")}
            aria-label="Clear search"
            style={{
              position: "absolute",
              right: 8,
              top: "50%",
              transform: "translateY(-50%)",
              color: TEXT_MUTED
            }}>
            <X size={13} />
          </Button>
        )}
      </div>
      <span style={{ fontSize: "0.72rem", color: TEXT_DISABLED, flexShrink: 0 }}>
        {resultCount} {resultCount === 1 ? "item" : "items"}
      </span>
      <div className="flex-1" />
      {/* Sort */}
      <div style={{ position: "relative" }}>
        <ToolbarBtn icon={ArrowUpDown} label={sortBy === "priority" ? "Priority" : "Newest"} onClick={() => setSortOpen(o => !o)} />
        {sortOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setSortOpen(false)} />
            <div style={{ position: "absolute", right: 0, top: "calc(100% + 6px)", background: WHITE, border: `1px solid ${HAIR}`, borderRadius: RADIUS_MD, boxShadow: SHADOW_CARD_HOVER, zIndex: 20, minWidth: 140, padding: 4 }}>
              {[{ k: "newest", l: "Newest first" }, { k: "priority", l: "Priority first" }].map(o => (
                <button
                  key={o.k}
                  onClick={() => { setSortBy(o.k); setSortOpen(false); }}
                  style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", padding: "7px 10px", background: "none", border: "none", cursor: "pointer", fontSize: "0.78rem", color: TEXT_PRIMARY, borderRadius: RADIUS_MD }}
                  onMouseEnter={e => e.currentTarget.style.background = RAIL_BG}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                >
                  {o.l}
                  {sortBy === o.k && <Check size={12} style={{ color: ACCENT }} />}
                </button>
              ))}
            </div>
          </>
        )}
      </div>
      {unreadCount > 0 && (
        <ToolbarBtn icon={CheckCheck} label="Mark all read" onClick={onMarkAll} />
      )}
      {hasRead && (
        <ToolbarBtn icon={X} label="Clear read" onClick={onClearRead} />
      )}
      <ToolbarBtn icon={Keyboard} onClick={onShortcuts} title="Keyboard shortcuts" />
      <Link to="/settings" aria-label="Settings" style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 30, height: 30, borderRadius: RADIUS_MD, color: TEXT_MUTED, border: `1px solid ${HAIR}` }}>
        <Settings size={13} />
      </Link>
    </div>
  );
}

function ToolbarBtn({ icon: Icon, label, onClick, title }) {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={onClick}
      title={title || label}
      aria-label={title || label}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: "inline-flex", alignItems: "center", gap: 6,
        padding: label ? "7px 11px" : "7px",
        borderRadius: RADIUS_MD, border: `1px solid ${hov ? "rgba(15,23,42,0.16)" : HAIR}`,
        background: hov ? RAIL_BG : WHITE, cursor: "pointer",
        fontSize: "0.76rem", fontWeight: 500, color: TEXT_SECONDARY,
        whiteSpace: "nowrap", flexShrink: 0,
      }}
    >
      <Icon size={13} strokeWidth={1.75} />
      {label}
    </button>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// CENTER — Feed
// ═══════════════════════════════════════════════════════════════════════════

function FeedGroup({ label, items, ...rowProps }) {
  if (!items?.length) return null;
  return (
    <div>
      <div style={{ padding: "16px 24px 8px", fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: TEXT_DISABLED }}>
        {label}
      </div>
      {items.map(n => <FeedCard key={n.id} n={n} {...rowProps} />)}
    </div>
  );
}

function FeedCard({ n, selectedId, onSelect, onRead, onDelete, pinned, onTogglePin, archived, onToggleArchive }) {
  const [hov, setHov] = useState(false);
  const cfg = kindConfig(n.type);
  const Icon = cfg.icon;
  const priority = getPriority(n.type);
  const active = selectedId === n.id;
  const isPinned = pinned.has(n.id);
  const isArchived = archived.has(n.id);

  return (
    <div
      role="listitem"
      tabIndex={0}
      onClick={() => onSelect(n.id)}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(n.id); } }}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: "flex", alignItems: "flex-start", gap: 13,
        padding: "14px 24px", margin: "0 12px", borderRadius: RADIUS_LG,
        cursor: "pointer", position: "relative",
        background: active ? "rgba(138,21,56,0.045)" : hov ? RAIL_BG : "transparent",
        transition: "background 120ms ease",
      }}
    >
      {active && (
        <span aria-hidden="true" style={{ position: "absolute", left: 0, top: 10, bottom: 10, width: 3, borderRadius: 3, background: ACCENT }} />
      )}

      {/* Icon avatar */}
      <div style={{ position: "relative", flexShrink: 0, marginTop: 1 }}>
        <div style={{
          width: 36, height: 36, borderRadius: "50%",
          background: n.read ? "#F1F3F6" : "rgba(28,35,51,0.06)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Icon size={15} strokeWidth={1.6} style={{ color: n.read ? TEXT_DISABLED : INK }} />
        </div>
        {!n.read && (
          <span style={{
            position: "absolute", top: -1, right: -1, width: 9, height: 9, borderRadius: "50%",
            background: priority === "high" ? CRIMSON : ACCENT, border: `2px solid ${WHITE}`,
          }} aria-label="Unread" />
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="flex items-start justify-between gap-3">
          <p style={{
            fontSize: "0.9rem", fontWeight: n.read ? 400 : 650,
            color: n.read ? TEXT_SECONDARY : INK, lineHeight: 1.4,
            letterSpacing: "-0.005em", margin: 0, flex: 1, minWidth: 0,
          }}>
            {n.title}
          </p>
          <span style={{ fontSize: "0.68rem", color: TEXT_DISABLED, flexShrink: 0, marginTop: 2 }}>
            {timeAgo(n.created_at)}
          </span>
        </div>

        {n.body && (
          <p style={{
            fontSize: "0.78rem", color: TEXT_MUTED, lineHeight: 1.55, margin: "3px 0 0",
            display: "-webkit-box", WebkitLineClamp: 1, WebkitBoxOrient: "vertical", overflow: "hidden",
          }}>
            {n.body}
          </p>
        )}

        <div className="flex items-center gap-2 mt-1.5">
          <span style={{ fontSize: "0.65rem", fontWeight: 600, color: TEXT_MUTED }}>{cfg.label}</span>
          {priority === "high" && !n.read && (
            <span style={{ fontSize: "0.65rem", fontWeight: 700, color: CRIMSON }}>· Needs attention</span>
          )}
        </div>
      </div>

      {/* Hover actions */}
      <div style={{ display: "flex", gap: 2, flexShrink: 0, opacity: hov ? 1 : 0, transition: "opacity 120ms ease" }}>
        <RowIconBtn icon={Star} active={isPinned} onClick={e => { e.stopPropagation(); onTogglePin(n.id); }} title="Pin" />
        <RowIconBtn icon={ArchiveIcon} active={isArchived} onClick={e => { e.stopPropagation(); onToggleArchive(n.id); }} title={isArchived ? "Unarchive" : "Archive"} />
        {!n.read && <RowIconBtn icon={Check} onClick={e => { e.stopPropagation(); onRead(n.id); }} title="Mark read" />}
        <RowIconBtn icon={X} onClick={e => { e.stopPropagation(); onDelete(n.id); }} title="Dismiss" />
      </div>
    </div>
  );
}

function RowIconBtn({ icon: Icon, onClick, title, active }) {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={onClick} title={title} aria-label={title}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        width: 24, height: 24, display: "flex", alignItems: "center", justifyContent: "center",
        borderRadius: RADIUS_MD, border: "none", cursor: "pointer",
        background: hov ? WHITE : "transparent",
        boxShadow: hov ? SHADOW_CARD : "none",
        color: active ? ACCENT : hov ? TEXT_PRIMARY : TEXT_MUTED,
      }}
    >
      <Icon size={12} strokeWidth={2} fill={active && Icon === Star ? ACCENT : "none"} />
    </button>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// RIGHT — Intelligence panel
// ═══════════════════════════════════════════════════════════════════════════

function IntelligencePanel({
  selected, bullets, unreadCount, priorityCount, relatedCount,
  isPinned, isArchived, label, knownLabels,
  onTogglePin, onToggleArchive, onSetLabel, onRead, onViewPriority, onDelete,
}) {
  const [labelInput, setLabelInput] = useState("");

  if (!selected) {
    return (
      <div className="p-6 flex flex-col gap-6">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={13} style={{ color: ACCENT }} />
            <span style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: TEXT_MUTED }}>
              Today's digest
            </span>
          </div>
          {bullets.length === 0 ? (
            <p style={{ fontSize: "0.82rem", color: TEXT_MUTED, lineHeight: 1.6 }}>
              You're all caught up. Select any item to see its full context here.
            </p>
          ) : (
            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
              {bullets.map((b, i) => (
                <li key={i} style={{ display: "flex", gap: 8, fontSize: "0.82rem", color: TEXT_SECONDARY, lineHeight: 1.5 }}>
                  <span style={{ width: 4, height: 4, borderRadius: "50%", background: TEXT_DISABLED, marginTop: 7, flexShrink: 0 }} />
                  {b}
                </li>
              ))}
            </ul>
          )}
          {priorityCount > 0 && (
            <button
              onClick={onViewPriority}
              style={{ marginTop: 14, display: "inline-flex", alignItems: "center", gap: 5, background: "none", border: "none", padding: 0, fontSize: "0.78rem", fontWeight: 600, color: ACCENT, cursor: "pointer" }}
            >
              View {priorityCount} priority item{priorityCount > 1 ? "s" : ""} <ChevronRight size={12} />
            </button>
          )}
        </div>

        <div style={{ borderTop: `1px solid ${HAIR}`, paddingTop: 16 }}>
          <Link to="/ai" style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.82rem", fontWeight: 600, color: INK, textDecoration: "none" }}>
            <BrainCircuit size={14} style={{ color: ACCENT }} />
            Ask Synaptiq AI about your activity
            <ChevronRight size={12} style={{ marginLeft: "auto", color: TEXT_MUTED }} />
          </Link>
        </div>
      </div>
    );
  }

  const cfg = kindConfig(selected.type);
  const Icon = cfg.icon;
  const priority = getPriority(selected.type);
  const actions = getActions(selected);

  return (
    <div className="flex flex-col h-full">
      <div className="p-6 flex flex-col gap-5 overflow-y-auto">

        {/* Identity */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div style={{ width: 30, height: 30, borderRadius: "50%", background: "rgba(28,35,51,0.06)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Icon size={14} style={{ color: INK }} />
            </div>
            <span style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: TEXT_MUTED }}>
              {cfg.label}
            </span>
            {priority === "high" && (
              <span style={{ fontSize: "0.65rem", fontWeight: 700, color: CRIMSON, marginLeft: "auto" }}>Needs attention</span>
            )}
          </div>
          <h2 style={{ fontSize: "1.05rem", fontWeight: 650, color: INK, lineHeight: 1.35, margin: "0 0 6px", letterSpacing: "-0.01em" }}>
            {selected.title}
          </h2>
          <span style={{ fontSize: "0.72rem", color: TEXT_DISABLED }}>{fullDate(selected.created_at)}</span>
        </div>

        {selected.body && (
          <p style={{ fontSize: "0.85rem", color: TEXT_SECONDARY, lineHeight: 1.65, margin: 0, paddingBottom: 16, borderBottom: `1px solid ${HAIR}` }}>
            {selected.body}
          </p>
        )}

        {/* Actions */}
        {actions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {actions.map(a => (
              <IntelActionBtn key={a.label} action={a} onRead={onRead} />
            ))}
          </div>
        )}

        {/* Quick controls */}
        <div className="flex items-center gap-2 pb-4" style={{ borderBottom: `1px solid ${HAIR}` }}>
          <PanelToggle icon={Star} active={isPinned} label={isPinned ? "Pinned" : "Pin"} onClick={onTogglePin} />
          <PanelToggle icon={ArchiveIcon} active={isArchived} label={isArchived ? "Archived" : "Archive"} onClick={onToggleArchive} />
          <button onClick={onDelete} style={{ marginLeft: "auto", fontSize: "0.75rem", color: TEXT_MUTED, background: "none", border: "none", cursor: "pointer" }}>
            Dismiss
          </button>
        </div>

        {/* Related activity — real, computed */}
        {relatedCount > 0 && (
          <div>
            <SectionHeading>Related activity</SectionHeading>
            <p style={{ fontSize: "0.8rem", color: TEXT_SECONDARY, margin: 0 }}>
              {relatedCount} other {cfg.label.toLowerCase()} {relatedCount === 1 ? "item" : "items"} in your inbox.
            </p>
          </div>
        )}

        {/* Label */}
        <div>
          <SectionHeading>Label</SectionHeading>
          {label ? (
            <div className="flex items-center gap-2">
              <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: "0.76rem", fontWeight: 600, color: labelColor(label), background: `${labelColor(label)}14`, padding: "3px 9px", borderRadius: RADIUS_FULL }}>
                <Tag size={10} /> {label}
              </span>
              <button onClick={() => onSetLabel(null)} style={{ background: "none", border: "none", cursor: "pointer", color: TEXT_MUTED, fontSize: "0.7rem" }}>Remove</button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <input
                value={labelInput}
                onChange={e => setLabelInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && labelInput.trim()) { onSetLabel(labelInput.trim()); setLabelInput(""); } }}
                placeholder="Add a label…"
                style={{ flex: 1, fontSize: "0.78rem", padding: "6px 9px", border: `1px solid ${HAIR}`, borderRadius: RADIUS_MD, outline: "none" }}
              />
              {labelInput.trim() && (
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => { onSetLabel(labelInput.trim()); setLabelInput(""); }}
                  aria-label="Add label"
                  style={{
                    color: ACCENT
                  }}>
                  <Plus size={15} />
                </Button>
              )}
            </div>
          )}
          {!label && knownLabels.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {knownLabels.map(l => (
                <button key={l} onClick={() => onSetLabel(l)} style={{ fontSize: "0.7rem", color: labelColor(l), background: `${labelColor(l)}14`, border: "none", borderRadius: RADIUS_FULL, padding: "2px 8px", cursor: "pointer" }}>
                  {l}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Honest note on what isn't shown */}
        <div style={{ fontSize: "0.7rem", color: TEXT_DISABLED, lineHeight: 1.6, paddingTop: 4 }}>
          This item carries no attachments, linked workspace, or citation data from the server —
          only what's shown above is real.
        </div>
      </div>
    </div>
  );
}

function SectionHeading({ children }) {
  return (
    <div style={{ fontSize: "0.66rem", fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: TEXT_DISABLED, marginBottom: 8 }}>
      {children}
    </div>
  );
}

function PanelToggle({ icon: Icon, active, label, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "inline-flex", alignItems: "center", gap: 5,
        padding: "5px 10px", borderRadius: RADIUS_FULL,
        border: `1px solid ${active ? ACCENT : HAIR}`,
        background: active ? "rgba(138,21,56,0.06)" : WHITE,
        color: active ? ACCENT : TEXT_SECONDARY,
        fontSize: "0.74rem", fontWeight: 600, cursor: "pointer",
      }}
    >
      <Icon size={11} fill={active && Icon === Star ? "currentColor" : "none"} />
      {label}
    </button>
  );
}

function IntelActionBtn({ action, onRead }) {
  const isAccept  = action.variant === "accept";
  const isDecline = action.variant === "decline";
  const style = {
    display: "inline-flex", alignItems: "center", gap: 5,
    fontSize: "0.78rem", fontWeight: 600, cursor: "pointer",
    textDecoration: "none", padding: "7px 14px", borderRadius: RADIUS_MD,
    border: `1px solid ${isAccept ? EMERALD : isDecline ? HAIR : ACCENT}`,
    background: isAccept ? "#F0FDF4" : isDecline ? "transparent" : ACCENT,
    color: isAccept ? EMERALD : isDecline ? TEXT_MUTED : WHITE,
  };
  if (action.to) {
    return <Link to={action.to} onClick={onRead} style={style}>{action.label}</Link>;
  }
  return <button style={style} onClick={onRead}>{action.label}</button>;
}

// ═══════════════════════════════════════════════════════════════════════════
// Shortcuts modal
// ═══════════════════════════════════════════════════════════════════════════

const INBOX_SHORTCUT_ROWS = [
  ["j / ↓", "Next item"],
  ["k / ↑", "Previous item"],
  ["Enter", "Open selected"],
  ["e", "Archive / unarchive"],
  ["p", "Pin / unpin"],
  ["u", "Mark as read"],
  ["?", "Toggle this panel"],
];

// ═══════════════════════════════════════════════════════════════════════════
// Skeleton + empty state
// ═══════════════════════════════════════════════════════════════════════════

function FeedSkeleton() {
  return (
    <div className="max-w-[760px]" style={{ animation: "sk-p 1.5s ease-in-out infinite" }}>
      <style>{`@keyframes sk-p{0%,100%{opacity:1}50%{opacity:.4}}`}</style>
      {[1, 2, 3, 4, 5, 6].map(i => (
        <div key={i} style={{ display: "flex", gap: 13, padding: "14px 24px" }}>
          <div style={{ width: 36, height: 36, borderRadius: "50%", background: "#EEF0F3", flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div style={{ background: "#EEF0F3", height: 13, width: `${50 + (i % 3) * 12}%`, marginBottom: 8, borderRadius: 3 }} />
            <div style={{ background: "#EEF0F3", height: 11, width: `${30 + (i % 4) * 8}%`, borderRadius: 3 }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function FeedEmptyState({ hasFilter, showArchived, onClear }) {
  return (
    <div className="flex flex-col items-center text-center" style={{ padding: "88px 24px" }}>
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none" aria-hidden="true">
        <circle cx="32" cy="32" r="28" stroke="#E7E9EE" strokeWidth="1" />
        <circle cx="32" cy="32" r="17" stroke="#E7E9EE" strokeWidth="1" />
        <circle cx="32" cy="32" r="4" fill="#DADEE5" />
        {showArchived ? (
          <path d="M20 26h24v4H20zM22 30h20l-2 12H24z" stroke="#DADEE5" strokeWidth="1.4" fill="none" strokeLinejoin="round" />
        ) : (
          <path d="M20 40l8-16 8 10 4-6 4 12" stroke="#DADEE5" strokeWidth="1.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        )}
      </svg>
      <h2 style={{ fontSize: "1rem", fontWeight: 650, color: INK, letterSpacing: "-0.015em", margin: "20px 0 6px" }}>
        {showArchived ? "Nothing archived" : hasFilter ? "No matches here" : "You're all caught up"}
      </h2>
      <p style={{ fontSize: "0.82rem", color: TEXT_MUTED, lineHeight: 1.6, maxWidth: 320, margin: "0 0 20px" }}>
        {showArchived
          ? "Items you archive will be tucked away here, out of your main inbox."
          : hasFilter
          ? "Try a different filter, or clear your search to see everything."
          : "New activity — collaborations, manuscript updates, citations, and AI results — will land here."}
      </p>
      {hasFilter && (
        <button
          onClick={onClear}
          style={{ background: NAVY, color: WHITE, border: "none", padding: "8px 18px", borderRadius: RADIUS_MD, fontSize: "0.78rem", fontWeight: 600, cursor: "pointer" }}
        >
          Clear filters
        </button>
      )}
    </div>
  );
}
