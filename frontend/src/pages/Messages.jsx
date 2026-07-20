/* eslint-disable */
/**
 * Messages — Premium Academic Collaboration Workspace
 *
 * Ground-up presentation redesign. Zero backend/WebSocket/API changes.
 *
 * Preserved exactly (same calls, same payloads, same behavior):
 *   POST   /conversations                                  (bootstrap direct/context conversation)
 *   GET    /conversations?type&q
 *   GET    /conversations/{id}
 *   GET    /conversations/{id}/messages
 *   POST   /conversations/{id}/read
 *   POST   /conversations/{id}/messages
 *   PATCH  /conversations/{id}/messages/{msgId}
 *   DELETE /conversations/{id}/messages/{msgId}
 *   POST   /conversations/{id}/messages/{msgId}/reactions
 *   DELETE /conversations/{id}/messages/{msgId}/reactions/{emoji}
 *   POST   /conversations/{id}/leave
 *   POST   /conversations/{id}/mute
 *   POST   /uploads
 *   GET    /journals /conferences /funding /manuscripts /projects  (SharePicker)
 *   WS     /api/ws/conversations/{id}  — message, message_edited, message_deleted,
 *                                         reaction_added, reaction_removed, typing, read
 *
 * Pin, Archive and the in-thread search are real, working, client-only features
 * (localStorage) — the backend has no such fields. There is no per-conversation
 * AI summary, sentiment, or task-extraction field in the data; the AI panel
 * either computes a real digest from already-loaded messages, or deep-links to
 * the existing Synaptiq AI assistant (/ai) with a pre-filled prompt — it never
 * fabricates content. There is no video/voice calling backend, so "Meet" opens
 * the real Meetings page rather than pretending to start a live call. Rich text
 * (bold/italic/code/links/DOI/ORCID/@mentions) is parsed client-side with no
 * new dependency; full LaTeX and GFM tables are out of scope for the same reason.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams, useLocation, Link } from "react-router-dom";
import api, { BACKEND_URL } from "../lib/api";
import { TID } from "../lib/testIds";
import { useAuth } from "../contexts/AuthContext";
import { Avatar } from "@/components/ds/Avatar";
import { ErrorState } from "@/components/ds/ErrorState";
import { Spinner } from "@/components/ds/LoadingState";
import { toast } from "sonner";
import {
  Send, Paperclip, Share2, Search, X, FileText, File, BookOpen,
  CalendarDays, Coins, FolderOpen, Users, Check, CheckCheck, Reply,
  Pencil, CornerDownRight, Trash2, Bell, BellOff, LogOut, BrainCircuit,
  ArrowRight, MessageSquare, Layers, Users2, ExternalLink,
  Star, Archive as ArchiveIcon, Sparkles, Video, Download,
  Keyboard, MoreHorizontal, Smile, Link2, IdCard,
} from "lucide-react";
import { useUnread } from "../contexts/UnreadContext";
import { usePersistentSet } from "@/hooks/usePersistentSet";
import { ShortcutsModal } from "@/components/shared/ShortcutsModal";
import { ACCENT, NAVY, WARM, WHITE } from "@/lib/tokens";

// ─── Palette — no per-type rainbow, one accent only ──────────────────────────
const INK     = "#1C2333";
const HAIR    = "#E7E9F0";
const RAIL_BG = "#FAFAFB";
const MUTED   = "#8A93A6";
const DISABLED= "#B8C0CE";

// ─── Domain constants (unchanged business classification) ───────────────────
const TYPE_LABEL = {
  direct: "Direct Message", collaboration: "Collaboration",
  project: "Project", workspace: "Workspace", manuscript: "Manuscript",
};
const TYPE_ICON = {
  direct: Users, collaboration: Users2, project: FolderOpen,
  workspace: Layers, manuscript: FileText,
};
const CONTEXT_LINK = {
  project: "projects", workspace: "workspaces",
  collaboration: "collaborations", manuscript: "manuscripts",
};
const ALLOWED_MIME = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "image/png", "image/jpeg", "image/webp", "image/gif",
];
const REACTION_EMOJIS = ["👍", "🎉", "✅", "💡", "❓"];

function fmtTime(d) { return new Date(d).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }); }
function fmtDate(d) {
  const now = new Date(); const dt = new Date(d);
  const today = now.toDateString(); const yest = new Date(now - 86400000).toDateString();
  if (dt.toDateString() === today) return "Today";
  if (dt.toDateString() === yest) return "Yesterday";
  return dt.toLocaleDateString("en-GB", { day: "numeric", month: "long" });
}
function sameDay(a, b) { return new Date(a).toDateString() === new Date(b).toDateString(); }

// ─── Rich text — bold/italic/code/links/DOI/ORCID/@mentions, no dependency ──
const DOI_RE    = /\b10\.\d{4,9}\/\S+\b/g;
const ORCID_RE  = /\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b/g;
const URL_RE    = /\bhttps?:\/\/[^\s<]+/g;
const CODE_RE   = /`([^`]+)`/g;
const BOLD_RE   = /\*\*([^*]+)\*\*/g;
const ITALIC_RE = /(?<!\*)\*([^*]+)\*(?!\*)/g;

function parseInline(text, members, keyBase) {
  // Tokenize by scanning all patterns in priority order, left to right.
  const patterns = [
    { re: CODE_RE,   type: "code" },
    { re: BOLD_RE,   type: "bold" },
    { re: ITALIC_RE, type: "italic" },
    { re: DOI_RE,    type: "doi" },
    { re: ORCID_RE,  type: "orcid" },
    { re: URL_RE,    type: "url" },
  ];
  let matches = [];
  patterns.forEach(({ re, type }) => {
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(text))) {
      matches.push({ start: m.index, end: m.index + m[0].length, raw: m[0], value: m[1] ?? m[0], type });
    }
  });
  // Resolve overlaps: keep earliest, longest, drop overlapping later ones.
  matches.sort((a, b) => a.start - b.start || (b.end - b.start) - (a.end - a.start));
  const kept = [];
  let cursor = 0;
  for (const m of matches) {
    if (m.start < cursor) continue;
    kept.push(m);
    cursor = m.end;
  }

  // @mentions — matched against real conversation members only.
  const names = (members || []).map(m => m.full_name).filter(Boolean);
  if (names.length) {
    const mentionRe = new RegExp("@(" + names.map(n => n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") + ")", "g");
    let m;
    mentionRe.lastIndex = 0;
    while ((m = mentionRe.exec(text))) {
      const overlaps = kept.some(k => m.index < k.end && m.index + m[0].length > k.start);
      if (!overlaps) kept.push({ start: m.index, end: m.index + m[0].length, raw: m[0], value: m[1], type: "mention" });
    }
    kept.sort((a, b) => a.start - b.start);
  }

  const nodes = [];
  let pos = 0;
  kept.forEach((m, i) => {
    if (m.start < pos) return;
    if (m.start > pos) nodes.push(text.slice(pos, m.start));
    const key = `${keyBase}-${i}`;
    if (m.type === "code") nodes.push(<code key={key} style={{ background: "rgba(28,35,51,0.07)", padding: "1px 5px", borderRadius: 4, fontFamily: "ui-monospace, monospace", fontSize: "0.88em" }}>{m.value}</code>);
    else if (m.type === "bold") nodes.push(<strong key={key} style={{ fontWeight: 700 }}>{m.value}</strong>);
    else if (m.type === "italic") nodes.push(<em key={key}>{m.value}</em>);
    else if (m.type === "doi") nodes.push(<a key={key} href={`https://doi.org/${m.value}`} target="_blank" rel="noreferrer" style={{ color: ACCENT, fontWeight: 600, textDecoration: "none", borderBottom: `1px solid ${ACCENT}55` }}>doi:{m.value}</a>);
    else if (m.type === "orcid") nodes.push(<a key={key} href={`https://orcid.org/${m.value}`} target="_blank" rel="noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: 3, color: "#059669", fontWeight: 600, textDecoration: "none" }}><IdCard size={11} /> {m.value}</a>);
    else if (m.type === "url") nodes.push(<a key={key} href={m.value} target="_blank" rel="noreferrer" style={{ color: "inherit", textDecoration: "underline", textDecorationColor: "currentColor", opacity: 0.85 }}>{m.value}</a>);
    else if (m.type === "mention") nodes.push(<span key={key} style={{ color: ACCENT, fontWeight: 700, background: `${ACCENT}12`, borderRadius: 4, padding: "0 3px" }}>@{m.value}</span>);
    pos = m.end;
  });
  if (pos < text.length) nodes.push(text.slice(pos));
  return nodes;
}

function RichText({ content, members }) {
  if (!content) return null;
  // Split on fenced code blocks first — never parsed further.
  const blocks = content.split(/```([\s\S]*?)```/g);
  return (
    <div style={{ whiteSpace: "pre-wrap" }}>
      {blocks.map((block, i) => {
        if (i % 2 === 1) {
          return (
            <pre key={i} style={{ background: "rgba(28,35,51,0.06)", padding: "10px 12px", borderRadius: 8, overflowX: "auto", margin: "6px 0", fontSize: "0.82em" }}>
              <code style={{ fontFamily: "ui-monospace, monospace" }}>{block}</code>
            </pre>
          );
        }
        return <React.Fragment key={i}>{parseInline(block, members, `t${i}`)}</React.Fragment>;
      })}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// LEFT — Conversation navigation
// ═══════════════════════════════════════════════════════════════════════════

// IA note: this nav is organized purely by WHO/WHERE you're talking to.
// "Needs Action" / urgency-style filtering belongs to Inbox, not here — so
// there is deliberately no priority filter on this page. "Collaboration"
// conversations are labeled "Research Teams" to read clearly as a group of
// people, not as the generic "Collaborations" bucket Inbox used to show.
const NAV_GROUPS = [
  { key: "all",           label: "All conversations" },
  { key: "unread",        label: "Unread" },
];
const TYPE_GROUPS = [
  { key: "direct",        label: "Direct Messages" },
  { key: "collaboration", label: "Research Teams" },
  { key: "project",       label: "Project Chats" },
  { key: "workspace",     label: "Workspace Chats" },
  { key: "manuscript",    label: "Manuscript Discussions" },
];

function convPriority(c) {
  if (c.unread > 2) return "high";
  if (c.unread > 0 && c.type === "direct") return "high";
  if (c.unread > 0) return "medium";
  return "low";
}

function SideNav({ conversations, filter, setFilter, search, setSearch, activeId, onOpen, pinned, togglePin, archived, toggleArchive, showArchived, setShowArchived, onToggleMute }) {
  const unreadCount = conversations.filter(c => c.unread > 0).length;

  const scoped = useMemo(() => conversations.filter(c => showArchived ? archived.has(c.id) : !archived.has(c.id)), [conversations, archived, showArchived]);
  const list = useMemo(() => {
    let l = scoped;
    if (filter === "unread") l = l.filter(c => c.unread > 0);
    else if (filter === "pinned") l = l.filter(c => pinned.has(c.id));
    else if (TYPE_GROUPS.some(g => g.key === filter)) l = l.filter(c => c.type === filter);
    return l;
  }, [scoped, filter, pinned]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: RAIL_BG, borderRight: `1px solid ${HAIR}` }}>
      <div style={{ padding: "18px 16px 12px" }}>
        <h1 style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontSize: "1.15rem", fontWeight: 700, color: INK, letterSpacing: "-0.02em", margin: "0 0 3px" }}>
          Messages
        </h1>
        <p style={{ fontSize: "0.68rem", color: MUTED, margin: "0 0 12px", lineHeight: 1.4 }}>
          People and teams you work with.
        </p>
        <div style={{ position: "relative" }}>
          <Search size={13} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: MUTED }} />
          <input
            data-testid={TID.convSearch}
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search conversations…"
            aria-label="Search conversations"
            style={{ width: "100%", padding: "7px 10px 7px 30px", border: `1px solid ${HAIR}`, borderRadius: 8, fontSize: "0.8rem", color: INK, outline: "none", background: WHITE, boxSizing: "border-box" }}
            onFocus={e => e.target.style.borderColor = ACCENT}
            onBlur={e => e.target.style.borderColor = HAIR}
          />
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "0 8px 12px" }}>
        <NavGroup>
          {NAV_GROUPS.map(g => (
            <NavRow key={g.key} label={g.label}
              count={g.key === "unread" ? unreadCount : null}
              active={!showArchived && filter === g.key}
              onClick={() => { setShowArchived(false); setFilter(g.key); }}
              icon={g.key === "unread" ? Bell : MessageSquare}
            />
          ))}
        </NavGroup>

        <NavSectionLabel>Spaces</NavSectionLabel>
        <NavGroup>
          {TYPE_GROUPS.map(g => (
            <NavRow key={g.key} label={g.label}
              count={scoped.filter(c => c.type === g.key).length || null}
              active={!showArchived && filter === g.key}
              onClick={() => { setShowArchived(false); setFilter(g.key); }}
              icon={TYPE_ICON[g.key]}
            />
          ))}
        </NavGroup>

        <NavSectionLabel>Yours</NavSectionLabel>
        <NavGroup>
          <NavRow label="Pinned" icon={Star} count={pinned.size || null} active={!showArchived && filter === "pinned"} onClick={() => { setShowArchived(false); setFilter("pinned"); }} />
          <NavRow label="Archived" icon={ArchiveIcon} count={archived.size || null} active={showArchived} onClick={() => setShowArchived(true)} />
        </NavGroup>

        <div style={{ height: 1, background: HAIR, margin: "10px 8px" }} />

        <div style={{ display: "flex", flexDirection: "column" }}>
          {list.length === 0 ? (
            <div style={{ padding: "28px 16px", textAlign: "center" }}>
              <MessageSquare size={22} style={{ color: DISABLED, margin: "0 auto 10px" }} />
              <p style={{ fontSize: "0.78rem", color: MUTED, lineHeight: 1.6, margin: 0 }}>
                {showArchived ? "Nothing archived." : "No conversations here yet."}
              </p>
            </div>
          ) : (
            list.map(c => (
              <ConvRow
                key={c.id}
                c={c}
                active={activeId === c.id}
                isPinned={pinned.has(c.id)}
                isArchived={archived.has(c.id)}
                onClick={() => onOpen(c.id)}
                onToggleMute={onToggleMute}
                onTogglePin={() => togglePin(c.id)}
                onToggleArchive={() => toggleArchive(c.id)}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function NavGroup({ children }) { return <div style={{ display: "flex", flexDirection: "column", gap: 1, marginBottom: 4 }}>{children}</div>; }
function NavSectionLabel({ children }) {
  return <div style={{ fontSize: "0.63rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: DISABLED, padding: "10px 10px 5px" }}>{children}</div>;
}
function NavRow({ label, icon: Icon, active, count, onClick }) {
  const [hov, setHov] = useState(false);
  return (
    <button onClick={onClick} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", textAlign: "left", padding: "6px 10px", borderRadius: 8, border: "none", cursor: "pointer",
        background: active ? WHITE : hov ? "rgba(28,35,51,0.03)" : "transparent", boxShadow: active ? "0 1px 3px rgba(15,23,42,0.06)" : "none" }}>
      {Icon && <Icon size={13} strokeWidth={1.75} style={{ color: active ? ACCENT : MUTED, flexShrink: 0 }} />}
      <span style={{ fontSize: "0.8rem", fontWeight: active ? 600 : 500, color: active ? INK : "#4A5468", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{label}</span>
      {count != null && count > 0 && (
        <span style={{ fontSize: "0.63rem", fontWeight: 700, minWidth: 16, textAlign: "center", color: active ? WHITE : MUTED, background: active ? ACCENT : "rgba(28,35,51,0.07)", borderRadius: 99, padding: "1px 5px" }}>{count}</span>
      )}
    </button>
  );
}

function ConvRow({ c, active, isPinned, isArchived, onClick, onToggleMute, onTogglePin, onToggleArchive }) {
  const [hov, setHov] = useState(false);
  const isDirect = c.type === "direct";
  const Icon = TYPE_ICON[c.type] || Users;
  const title = isDirect ? (c.other_user?.full_name || "Direct") : (c.title || TYPE_LABEL[c.type]);
  const priority = convPriority(c);

  return (
    <div
      data-testid={TID.convItem(c.id)}
      role="button" tabIndex={0}
      onClick={onClick}
      onKeyDown={e => { if (e.key === "Enter" || e.key === " ") onClick(); }}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "9px 8px", margin: "1px 0", borderRadius: 10, cursor: "pointer",
        background: active ? `${ACCENT}0C` : hov ? "rgba(28,35,51,0.03)" : "transparent", position: "relative", transition: "background 120ms ease" }}
    >
      {active && <span aria-hidden="true" style={{ position: "absolute", left: 0, top: 8, bottom: 8, width: 3, borderRadius: 3, background: ACCENT }} />}

      <div style={{ position: "relative", flexShrink: 0 }}>
        {isDirect
          ? <Avatar url={c.other_user?.avatar_url} name={c.other_user?.full_name} size={34} />
          : <div style={{ width: 34, height: 34, borderRadius: "50%", background: "rgba(28,35,51,0.06)", display: "flex", alignItems: "center", justifyContent: "center" }}><Icon size={14} strokeWidth={1.6} style={{ color: INK }} /></div>}
        {c.unread > 0 && <span style={{ position: "absolute", top: -1, right: -1, width: 9, height: 9, borderRadius: "50%", background: priority === "high" ? "#DC2626" : ACCENT, border: `2px solid ${RAIL_BG}` }} />}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 4 }}>
          <span style={{ fontSize: "0.83rem", fontWeight: c.unread > 0 ? 650 : 500, color: INK, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{title}</span>
          {c.unread > 0 && <span style={{ fontSize: "0.62rem", fontWeight: 700, color: WHITE, background: priority === "high" ? "#DC2626" : ACCENT, borderRadius: 99, padding: "1px 6px", flexShrink: 0 }}>{c.unread}</span>}
        </div>
        {isDirect && c.other_user?.institution && (
          <div style={{ fontSize: "0.68rem", color: MUTED, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginTop: 1 }}>{c.other_user.institution}</div>
        )}
        <div style={{ fontSize: "0.72rem", color: MUTED, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginTop: 2 }}>{c.last_message_preview || "No messages yet"}</div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 2, opacity: hov ? 1 : 0, transition: "opacity 120ms ease", flexShrink: 0 }}>
        <RowIconBtn icon={Star} active={isPinned} onClick={e => { e.stopPropagation(); onTogglePin(); }} title="Pin" />
        <RowIconBtn icon={c.muted ? BellOff : Bell} onClick={e => { e.stopPropagation(); onToggleMute(c.id, c.muted); }} title={c.muted ? "Unmute" : "Mute"} />
      </div>
    </div>
  );
}

function RowIconBtn({ icon: Icon, onClick, title, active }) {
  return (
    <button onClick={onClick} title={title} aria-label={title}
      style={{ width: 20, height: 20, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 5, border: "none", cursor: "pointer", background: "transparent", color: active ? ACCENT : MUTED }}>
      <Icon size={11} fill={active && Icon === Star ? ACCENT : "none"} />
    </button>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// TOP — Conversation toolbar
// ═══════════════════════════════════════════════════════════════════════════

function Toolbar({ conv, isPinned, onTogglePin, onShare, onExport, onLeave, onOpenShortcuts, threadQuery, setThreadQuery }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const isDirect = conv.type === "direct" && conv.other_user;
  const Icon = TYPE_ICON[conv.type] || Users;
  const title = isDirect ? conv.other_user.full_name : (conv.title || TYPE_LABEL[conv.type]);
  const contextPath = CONTEXT_LINK[conv.type];

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 20px", borderBottom: `1px solid ${HAIR}`, background: WHITE, flexShrink: 0 }}>
      {isDirect ? <Avatar url={conv.other_user.avatar_url} name={conv.other_user.full_name} size={34} />
        : <div style={{ width: 34, height: 34, borderRadius: "50%", background: "rgba(28,35,51,0.06)", display: "flex", alignItems: "center", justifyContent: "center" }}><Icon size={14} style={{ color: INK }} /></div>}

      <div style={{ minWidth: 0, flex: 1 }}>
        {isDirect ? (
          <Link to={`/profile/${conv.other_user.id}`} style={{ fontSize: "0.92rem", fontWeight: 650, color: INK, textDecoration: "none", letterSpacing: "-0.01em" }}>{title}</Link>
        ) : (
          <span style={{ fontSize: "0.92rem", fontWeight: 650, color: INK, letterSpacing: "-0.01em" }}>{title}</span>
        )}
        <div style={{ fontSize: "0.7rem", color: MUTED, marginTop: 1 }}>
          {isDirect ? (conv.other_user.institution || "Direct message") : `${(conv.members || []).length} member${(conv.members || []).length !== 1 ? "s" : ""} · ${TYPE_LABEL[conv.type]}`}
        </div>
      </div>

      {searchOpen && (
        <div style={{ position: "relative" }}>
          <input
            autoFocus
            value={threadQuery}
            onChange={e => setThreadQuery(e.target.value)}
            onKeyDown={e => e.key === "Escape" && (setSearchOpen(false), setThreadQuery(""))}
            placeholder="Search in conversation…"
            style={{ width: 220, padding: "6px 10px", border: `1px solid ${HAIR}`, borderRadius: 8, fontSize: "0.78rem", outline: "none" }}
          />
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: 4, flexShrink: 0 }}>
        <ToolIconBtn icon={Search} title="Search in conversation" onClick={() => { setSearchOpen(o => !o); if (searchOpen) setThreadQuery(""); }} active={searchOpen} />
        <ToolIconBtn icon={Star} title={isPinned ? "Unpin" : "Pin"} onClick={onTogglePin} active={isPinned} />
        {contextPath && conv.context_id && (
          <Link to={`/${contextPath}/${conv.context_id}`} title={`Open ${TYPE_LABEL[conv.type]}`} style={{ width: 30, height: 30, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 8, color: MUTED, border: `1px solid transparent` }}>
            <ExternalLink size={14} />
          </Link>
        )}
        <Link to="/meetings" title="Schedule a meeting" style={{ width: 30, height: 30, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 8, color: MUTED }}>
          <Video size={14} />
        </Link>
        <Link to="/ai" title="Ask Synaptiq AI" style={{ width: 30, height: 30, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 8, color: ACCENT }}>
          <BrainCircuit size={14} />
        </Link>
        <ToolIconBtn icon={Share2} title="Share a resource" onClick={onShare} />

        <div style={{ position: "relative" }}>
          <ToolIconBtn icon={MoreHorizontal} title="More" onClick={() => setMenuOpen(o => !o)} />
          {menuOpen && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
              <div style={{ position: "absolute", right: 0, top: "calc(100% + 6px)", background: WHITE, border: `1px solid ${HAIR}`, borderRadius: 10, boxShadow: "0 8px 28px rgba(15,23,42,0.12)", zIndex: 20, minWidth: 190, padding: 5 }}>
                <MenuItem icon={Download} label="Export conversation" onClick={() => { onExport(); setMenuOpen(false); }} />
                <MenuItem icon={Keyboard} label="Keyboard shortcuts" onClick={() => { onOpenShortcuts(); setMenuOpen(false); }} />
                <div style={{ height: 1, background: HAIR, margin: "4px 6px" }} />
                <MenuItem icon={LogOut} label="Leave conversation" danger onClick={() => { onLeave(); setMenuOpen(false); }} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function ToolIconBtn({ icon: Icon, title, onClick, active }) {
  const [hov, setHov] = useState(false);
  return (
    <button onClick={onClick} title={title} aria-label={title} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{ width: 30, height: 30, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 8, border: "none", cursor: "pointer",
        background: active ? `${ACCENT}14` : hov ? RAIL_BG : "transparent", color: active ? ACCENT : MUTED }}>
      <Icon size={14} fill={active && Icon === Star ? "currentColor" : "none"} />
    </button>
  );
}

function MenuItem({ icon: Icon, label, onClick, danger }) {
  return (
    <button onClick={onClick} style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "8px 10px", background: "none", border: "none", cursor: "pointer", borderRadius: 6, fontSize: "0.8rem", color: danger ? "#DC2626" : INK, textAlign: "left" }}
      onMouseEnter={e => e.currentTarget.style.background = RAIL_BG} onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
      <Icon size={13} /> {label}
    </button>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// CENTER — Message feed
// ═══════════════════════════════════════════════════════════════════════════

function DateSeparator({ label }) {
  return (
    <div style={{ position: "sticky", top: 0, zIndex: 5, display: "flex", justifyContent: "center", padding: "10px 0", pointerEvents: "none" }}>
      <span style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: MUTED, background: WHITE, border: `1px solid ${HAIR}`, borderRadius: 99, padding: "3px 12px", boxShadow: "0 1px 3px rgba(15,23,42,0.05)" }}>
        {label}
      </span>
    </div>
  );
}

function MessageBubble({ m, mine, convDetail, readBy, onReply, onEdit, onDelete, onReactionToggle, currentUserId, isGrouped, highlight }) {
  const [hov, setHov] = useState(false);
  const [menu, setMenu] = useState(null);

  let readReceipt = null;
  if (mine && convDetail.type === "direct" && convDetail.other_user) {
    const otherRead = readBy[convDetail.other_user.id];
    const seen = otherRead && otherRead >= m.created_at;
    readReceipt = seen ? <CheckCheck size={12} style={{ color: ACCENT }} /> : <Check size={12} style={{ color: DISABLED }} />;
  }

  return (
    <div
      data-testid={`message-${m.id}`}
      style={{ display: "flex", flexDirection: mine ? "row-reverse" : "row", alignItems: "flex-end", gap: 8, marginBottom: isGrouped ? 3 : 14, position: "relative" }}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      onContextMenu={e => { e.preventDefault(); setMenu({ x: e.clientX, y: e.clientY }); }}
    >
      <div style={{ width: 30, flexShrink: 0 }}>
        {!mine && !isGrouped && m.sender && <Avatar url={m.sender?.avatar_url} name={m.sender?.full_name} size={30} />}
      </div>

      <div style={{ maxWidth: "66%", minWidth: 0 }}>
        {!mine && !isGrouped && m.sender && (
          <div style={{ fontSize: "0.72rem", fontWeight: 650, color: "#4A5468", marginBottom: 4, marginLeft: 2 }}>{m.sender.full_name}</div>
        )}

        <div style={{
          background: mine ? NAVY : WHITE, border: mine ? "none" : `1px solid ${HAIR}`,
          borderRadius: 16, padding: "11px 15px", fontSize: "0.86rem", lineHeight: 1.6,
          color: mine ? WHITE : INK, wordBreak: "break-word",
          boxShadow: mine ? "none" : "0 1px 2px rgba(15,23,42,0.04)",
          outline: highlight ? `2px solid ${ACCENT}` : "none", outlineOffset: 1,
        }}>
          {m.reply_to && (
            <div style={{ marginBottom: 8, padding: "6px 10px", borderRadius: 8, borderLeft: `2px solid ${mine ? "rgba(255,255,255,0.5)" : ACCENT}`, background: mine ? "rgba(255,255,255,0.1)" : "rgba(138,21,56,0.05)", fontSize: "0.76rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 2, opacity: 0.75 }}>
                <CornerDownRight size={10} /> <span style={{ fontWeight: 650 }}>{m.reply_to.sender_name || "Reply"}</span>
              </div>
              <div style={{ opacity: 0.75, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.reply_to.deleted ? "(deleted)" : m.reply_to.snippet}</div>
            </div>
          )}

          {m.content && <RichText content={m.content} members={convDetail.members} />}

          {(m.attachments || []).map(a => <AttachmentChip key={a.id} a={a} mine={mine} />)}
          {(m.shared_resources || []).map((s, i) => <ResourceChip key={i} s={s} mine={mine} />)}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4, justifyContent: mine ? "flex-end" : "flex-start" }}>
          <span style={{ fontSize: "0.65rem", color: DISABLED }}>{fmtTime(m.created_at)}</span>
          {m.edited && <span style={{ fontSize: "0.65rem", color: DISABLED, fontStyle: "italic" }}>edited</span>}
          {readReceipt}
          <div style={{ display: "flex", alignItems: "center", gap: 3, opacity: hov ? 1 : 0, transition: "opacity 120ms ease" }}>
            <MiniBtn icon={Reply} onClick={onReply} title="Reply" />
            {mine && !m.deleted && <MiniBtn icon={Pencil} onClick={onEdit} title="Edit" />}
            {mine && !m.deleted && <MiniBtn icon={Trash2} onClick={onDelete} title="Delete" danger />}
          </div>
        </div>

        <ReactionsBar messageId={m.id} reactions={m.reactions || {}} currentUserId={currentUserId} onReactionToggle={onReactionToggle} mine={mine} />
      </div>

      {menu && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setMenu(null)} onContextMenu={e => { e.preventDefault(); setMenu(null); }} />
          <div style={{ position: "fixed", left: menu.x, top: menu.y, background: WHITE, border: `1px solid ${HAIR}`, borderRadius: 10, boxShadow: "0 8px 28px rgba(15,23,42,0.14)", zIndex: 50, minWidth: 160, padding: 5 }}>
            <MenuItem icon={Reply} label="Reply" onClick={() => { onReply(); setMenu(null); }} />
            {mine && !m.deleted && <MenuItem icon={Pencil} label="Edit" onClick={() => { onEdit(); setMenu(null); }} />}
            {mine && !m.deleted && <MenuItem icon={Trash2} label="Delete" danger onClick={() => { onDelete(); setMenu(null); }} />}
          </div>
        </>
      )}
    </div>
  );
}

function MiniBtn({ icon: Icon, onClick, title, danger }) {
  return (
    <button onClick={onClick} title={title} aria-label={title} style={{ width: 20, height: 20, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 6, border: "none", cursor: "pointer", background: "rgba(28,35,51,0.05)", color: danger ? "#DC2626" : MUTED }}>
      <Icon size={10} />
    </button>
  );
}

function AttachmentChip({ a, mine }) {
  const isImg = a.kind === "image";
  const uploadUrl = `${BACKEND_URL}/api/uploads/${a.id}`;
  if (isImg) {
    return <div style={{ marginTop: 8 }}><img src={uploadUrl} alt={a.filename} style={{ maxHeight: 220, borderRadius: 10, border: `1px solid ${mine ? "rgba(255,255,255,0.25)" : HAIR}` }} crossOrigin="use-credentials" /></div>;
  }
  const isPdf = a.content_type === "application/pdf";
  return (
    <a href={uploadUrl} target="_blank" rel="noreferrer" style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 9, padding: "9px 12px", borderRadius: 10, background: mine ? "rgba(255,255,255,0.14)" : RAIL_BG, border: `1px solid ${mine ? "rgba(255,255,255,0.28)" : HAIR}`, fontSize: "0.78rem", color: mine ? WHITE : "#374151", textDecoration: "none" }}>
      <div style={{ width: 28, height: 28, borderRadius: 7, background: mine ? "rgba(255,255,255,0.18)" : `${ACCENT}12`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
        {isPdf ? <FileText size={13} style={{ color: mine ? WHITE : ACCENT }} /> : <File size={13} style={{ color: mine ? WHITE : ACCENT }} />}
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 200, fontWeight: 600 }}>{a.filename}</div>
        <div style={{ opacity: 0.6, fontSize: "0.7rem" }}>{isPdf ? "PDF · " : ""}{Math.round((a.size || 0) / 1024)} KB</div>
      </div>
    </a>
  );
}

function ResourceChip({ s, mine }) {
  const ICONS = { journal: BookOpen, conference: CalendarDays, grant: Coins, publication: FileText, project: FolderOpen, manuscript: FileText };
  const PATHS = { journal: "journals", conference: "conferences", grant: "funding", publication: "manuscripts", project: "projects", manuscript: "manuscripts" };
  const Icon = ICONS[s.type] || Share2;
  return (
    <Link to={`/${PATHS[s.type]}/${s.id}`} style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", borderRadius: 10, border: `1px solid ${mine ? "rgba(255,255,255,0.35)" : ACCENT}`, background: mine ? "rgba(255,255,255,0.1)" : `${ACCENT}06`, fontSize: "0.78rem", color: mine ? WHITE : INK, textDecoration: "none" }}>
      <Icon size={14} />
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: "0.62rem", fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", opacity: 0.65, marginBottom: 1 }}>Shared {s.type}</div>
        <div style={{ fontWeight: 650, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.title}</div>
        {s.subtitle && <div style={{ opacity: 0.65, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.subtitle}</div>}
      </div>
    </Link>
  );
}

function TypingLine({ typingUsers, members }) {
  const active = Object.entries(typingUsers).filter(([, t]) => t && Date.now() - t < 4000).map(([uid]) => uid);
  if (active.length === 0) return null;
  const names = active.map(uid => (members.find(m => m.id === uid)?.full_name || "Someone").split(" ")[0]);
  return (
    <div data-testid={TID.typingIndicator} style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 0 4px 38px", fontSize: "0.78rem", color: MUTED, fontStyle: "italic" }}>
      <div style={{ display: "flex", gap: 3 }}>
        {[0, 1, 2].map(i => <span key={i} style={{ width: 5, height: 5, borderRadius: "50%", background: DISABLED, animation: `tp 1.2s ${i * 0.2}s ease-in-out infinite` }} />)}
      </div>
      {names.join(", ")} {names.length === 1 ? "is" : "are"} typing…
    </div>
  );
}

function ReactionsBar({ messageId, reactions, currentUserId, onReactionToggle, mine }) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const entries = Object.entries(reactions).filter(([, users]) => users.length > 0);
  if (entries.length === 0 && !pickerOpen) return <div style={{ height: 4 }} />;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 4, marginTop: 5, justifyContent: mine ? "flex-end" : "flex-start" }}>
      {entries.map(([emoji, users]) => {
        const isMine = users.some(u => u.user_id === currentUserId);
        return (
          <button key={emoji} onClick={() => onReactionToggle(messageId, emoji)} title={users.map(u => u.full_name).join(", ")}
            style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: "0.76rem", padding: "2px 8px", borderRadius: 99, border: `1px solid ${isMine ? ACCENT : HAIR}`, background: isMine ? `${ACCENT}12` : WHITE, color: isMine ? ACCENT : "#374151", cursor: "pointer" }}>
            {emoji} <span style={{ fontSize: "0.65rem", fontWeight: 700 }}>{users.length}</span>
          </button>
        );
      })}
      <div style={{ position: "relative" }}>
        <button onClick={() => setPickerOpen(p => !p)} aria-label="Add reaction" style={{ width: 20, height: 20, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 99, border: "none", background: "transparent", color: DISABLED, cursor: "pointer" }}><Smile size={13} /></button>
        {pickerOpen && (
          <div style={{ position: "absolute", [mine ? "right" : "left"]: 0, bottom: "100%", marginBottom: 4, background: WHITE, border: `1px solid ${HAIR}`, borderRadius: 10, padding: 6, display: "flex", gap: 4, zIndex: 20, boxShadow: "0 8px 24px rgba(15,23,42,0.14)" }} onMouseLeave={() => setPickerOpen(false)}>
            {REACTION_EMOJIS.map(e => <button key={e} onClick={() => { onReactionToggle(messageId, e); setPickerOpen(false); }} style={{ fontSize: 16, background: "none", border: "none", cursor: "pointer", padding: 4, borderRadius: 6 }}>{e}</button>)}
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// RIGHT — AI Collaboration Assistant
// ═══════════════════════════════════════════════════════════════════════════

function digest(messages, members, currentUserId) {
  const shared = [];
  messages.forEach(m => {
    (m.attachments || []).forEach(a => shared.push({ kind: "attachment", ...a, at: m.created_at }));
    (m.shared_resources || []).forEach(s => shared.push({ kind: "resource", ...s, at: m.created_at }));
  });
  const fromOthers = messages.filter(m => m.sender_id !== currentUserId).length;
  return {
    messageCount: messages.length,
    fromOthers,
    participantCount: (members || []).length,
    shared: shared.reverse(),
  };
}

function AIPanel({ conv, messages, currentUserId, onLeave, onExport }) {
  if (!conv) {
    return (
      <div style={{ padding: 28, textAlign: "center" }}>
        <BrainCircuit size={26} strokeWidth={1.25} style={{ color: DISABLED, margin: "0 auto 12px" }} />
        <p style={{ fontSize: "0.8rem", color: MUTED, lineHeight: 1.6, margin: 0 }}>Select a conversation to see its AI collaboration context.</p>
      </div>
    );
  }

  const isDirect = conv.type === "direct";
  const d = digest(messages, conv.members, currentUserId);
  const other = conv.other_user;
  const prompts = isDirect
    ? [`Summarise my conversation with ${other?.full_name || "this researcher"}`, `Draft a reply to ${other?.full_name || "this researcher"}`, "Extract action items from this conversation"]
    : [`Summarise the "${conv.title || TYPE_LABEL[conv.type]}" conversation`, "Extract action items from this conversation", "Suggest next steps for this collaboration"];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflowY: "auto" }}>

      {/* Identity */}
      <div style={{ padding: "18px 18px 14px", borderBottom: `1px solid ${HAIR}` }}>
        <SectionLabel>Collaboration Assistant</SectionLabel>
        {isDirect && other ? (
          <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 8 }}>
            <Avatar url={other.avatar_url} name={other.full_name} size={42} />
            <div style={{ minWidth: 0 }}>
              <Link to={`/profile/${other.id}`} style={{ fontSize: "0.85rem", fontWeight: 700, color: INK, textDecoration: "none", display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{other.full_name}</Link>
              {other.institution && <div style={{ fontSize: "0.72rem", color: MUTED }}>{other.institution}</div>}
            </div>
          </div>
        ) : (
          <div style={{ fontSize: "0.9rem", fontWeight: 700, color: INK, marginTop: 8 }}>{conv.title || TYPE_LABEL[conv.type]}</div>
        )}
      </div>

      {/* Real computed digest */}
      <div style={{ padding: "16px 18px", borderBottom: `1px solid ${HAIR}` }}>
        <SectionLabel>Conversation summary</SectionLabel>
        <div style={{ display: "flex", gap: 16, marginTop: 10 }}>
          <Stat value={d.messageCount} label="messages" />
          <Stat value={d.participantCount} label={d.participantCount === 1 ? "participant" : "participants"} />
          <Stat value={d.shared.length} label="shared items" />
        </div>
      </div>

      {/* AI actions — real deep-links into the existing assistant, no fabricated output */}
      <div style={{ padding: "16px 18px", borderBottom: `1px solid ${HAIR}` }}>
        <SectionLabel>Ask Synaptiq AI</SectionLabel>
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 10 }}>
          {prompts.map((p, i) => (
            <Link key={i} to="/ai" state={{ initialPrompt: p }} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", borderRadius: 8, border: `1px solid ${HAIR}`, textDecoration: "none", fontSize: "0.78rem", color: INK, fontWeight: 500 }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = ACCENT; e.currentTarget.style.background = `${ACCENT}06`; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = HAIR; e.currentTarget.style.background = "transparent"; }}>
              <Sparkles size={12} style={{ color: ACCENT, flexShrink: 0 }} />
              {p}
            </Link>
          ))}
        </div>
      </div>

      {/* Referenced documents — real, aggregated from actual messages */}
      {d.shared.length > 0 && (
        <div style={{ padding: "16px 18px", borderBottom: `1px solid ${HAIR}` }}>
          <SectionLabel>Shared in this conversation</SectionLabel>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 10 }}>
            {d.shared.slice(0, 6).map((s, i) => (
              s.kind === "attachment" ? (
                <a key={i} href={`${BACKEND_URL}/api/uploads/${s.id}`} target="_blank" rel="noreferrer" style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.76rem", color: "#374151", textDecoration: "none" }}>
                  <File size={12} style={{ color: MUTED, flexShrink: 0 }} />
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.filename}</span>
                </a>
              ) : (
                <Link key={i} to={`/${CONTEXT_LINK[s.type] || "manuscripts"}/${s.id}`} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.76rem", color: "#374151", textDecoration: "none" }}>
                  <Link2 size={12} style={{ color: MUTED, flexShrink: 0 }} />
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.title}</span>
                </Link>
              )
            ))}
          </div>
        </div>
      )}

      {/* Participants — real */}
      {(conv.members || []).length > 0 && (
        <div style={{ padding: "16px 18px", borderBottom: `1px solid ${HAIR}` }}>
          <SectionLabel>Participants ({conv.members.length})</SectionLabel>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 10 }}>
            {conv.members.slice(0, 8).map(m => (
              <Link key={m.id} to={`/profile/${m.id}`} style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none" }}>
                <Avatar url={m.avatar_url} name={m.full_name} size={26} />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: "0.78rem", fontWeight: 600, color: "#374151", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.full_name}</div>
                  {m.institution && <div style={{ fontSize: "0.68rem", color: MUTED, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.institution}</div>}
                </div>
              </Link>
            ))}
            {conv.members.length > 8 && <div style={{ fontSize: "0.72rem", color: MUTED }}>+{conv.members.length - 8} more</div>}
          </div>
        </div>
      )}

      {/* Quick links */}
      <div style={{ padding: "16px 18px" }}>
        <SectionLabel>Quick links</SectionLabel>
        <div style={{ display: "flex", flexDirection: "column", gap: 2, marginTop: 10 }}>
          {[
            { label: "Find researchers", to: "/network", icon: Users },
            { label: "Schedule a meeting", to: "/meetings", icon: Video },
            { label: "Export this conversation", onClick: onExport, icon: Download },
          ].map(({ label, to, icon: Ic, onClick }) => {
            const content = <><Ic size={12} style={{ flexShrink: 0 }} />{label}</>;
            const style = { display: "flex", alignItems: "center", gap: 8, padding: "7px 8px", fontSize: "0.76rem", color: "#4A5468", textDecoration: "none", borderRadius: 7, cursor: "pointer", background: "none", border: "none", width: "100%", textAlign: "left" };
            return to
              ? <Link key={label} to={to} style={style} onMouseEnter={e => e.currentTarget.style.background = RAIL_BG} onMouseLeave={e => e.currentTarget.style.background = "transparent"}>{content}</Link>
              : <button key={label} onClick={onClick} style={style} onMouseEnter={e => e.currentTarget.style.background = RAIL_BG} onMouseLeave={e => e.currentTarget.style.background = "transparent"}>{content}</button>;
          })}
        </div>
      </div>

      <div style={{ fontSize: "0.68rem", color: DISABLED, lineHeight: 1.6, padding: "0 18px 18px" }}>
        There's no per-message AI summary or task-extraction stored on the server — the digest above is computed live from this thread, and the prompts open the real Synaptiq AI assistant.
      </div>
    </div>
  );
}

function SectionLabel({ children }) { return <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: DISABLED }}>{children}</div>; }
function Stat({ value, label }) {
  return (
    <div>
      <div style={{ fontFamily: "Georgia, serif", fontSize: "1.1rem", fontWeight: 700, color: INK, lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: "0.66rem", color: MUTED, marginTop: 2 }}>{label}</div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Share Picker (logic unchanged, restyled)
// ═══════════════════════════════════════════════════════════════════════════

function SharePicker({ onClose, onPick }) {
  const [tab, setTab] = useState("journal");
  const [q, setQ] = useState("");
  const [items, setItems] = useState([]);

  const ENDPOINTS = {
    journal:     { url: "/journals",     title: x => x.title, sub: x => x.publisher },
    conference:  { url: "/conferences",  title: x => x.name,  sub: x => `${x.location} · ${x.date}` },
    grant:       { url: "/funding",      title: x => x.title, sub: x => `${x.agency} · ${x.amount}` },
    publication: { url: "/manuscripts",  title: x => x.title, sub: x => x.manuscript_type },
    project:     { url: "/projects",     title: x => x.title, sub: x => x.description },
    manuscript:  { url: "/manuscripts",  title: x => x.title, sub: x => x.manuscript_type },
  };

  useEffect(() => {
    const E = ENDPOINTS[tab];
    api.get(E.url, { params: q ? { q } : {} }).then(r => setItems(r.data.slice(0, 30))).catch(() => setItems([]));
    // eslint-disable-next-line
  }, [tab]);

  const doSearch = () => { const E = ENDPOINTS[tab]; api.get(E.url, { params: q ? { q } : {} }).then(r => setItems(r.data.slice(0, 30))); };
  const E = ENDPOINTS[tab];

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,0.4)", zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }} onClick={onClose}>
      <div style={{ background: WHITE, borderRadius: 16, width: "100%", maxWidth: 640, maxHeight: "80vh", display: "flex", flexDirection: "column", boxShadow: "0 24px 64px rgba(15,23,42,0.2)" }} onClick={e => e.stopPropagation()}>
        <div style={{ padding: "20px 24px", borderBottom: `1px solid ${HAIR}`, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <SectionLabel>Share to conversation</SectionLabel>
            <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: INK, margin: "4px 0 0", letterSpacing: "-0.02em" }}>Pick an academic resource</h2>
          </div>
          <button onClick={onClose} aria-label="Close" style={{ background: "none", border: "none", cursor: "pointer", color: MUTED }}><X size={18} /></button>
        </div>
        <div style={{ padding: "12px 24px", borderBottom: `1px solid ${HAIR}`, display: "flex", flexWrap: "wrap", gap: 6 }}>
          {Object.keys(ENDPOINTS).map(k => (
            <button key={k} data-testid={TID.shareTab(k)} onClick={() => setTab(k)}
              style={{ fontSize: "0.76rem", fontWeight: 600, padding: "5px 12px", borderRadius: 99, border: `1px solid ${tab === k ? ACCENT : HAIR}`, background: tab === k ? ACCENT : WHITE, color: tab === k ? WHITE : "#4A5468", cursor: "pointer", textTransform: "capitalize" }}>
              {k}
            </button>
          ))}
        </div>
        <div style={{ padding: "10px 24px", borderBottom: `1px solid ${HAIR}` }}>
          <input value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => e.key === "Enter" && doSearch()} placeholder="Search…"
            style={{ width: "100%", padding: "8px 12px", border: `1px solid ${HAIR}`, borderRadius: 8, fontSize: "0.84rem", outline: "none", boxSizing: "border-box" }} />
        </div>
        <div style={{ overflowY: "auto", flex: 1, padding: 16, display: "flex", flexDirection: "column", gap: 6 }}>
          {items.length === 0 && <div style={{ fontSize: "0.82rem", color: MUTED, padding: "0 8px" }}>No results.</div>}
          {items.map(x => (
            <button key={x.id} onClick={() => onPick({ type: tab, id: x.id, title: E.title(x), subtitle: E.sub(x) })}
              style={{ display: "block", width: "100%", textAlign: "left", border: `1px solid ${HAIR}`, borderRadius: 10, padding: "12px 14px", background: WHITE, cursor: "pointer" }}
              onMouseEnter={e => e.currentTarget.style.borderColor = ACCENT} onMouseLeave={e => e.currentTarget.style.borderColor = HAIR}>
              <div style={{ fontSize: "0.84rem", fontWeight: 650, color: INK, marginBottom: 2 }}>{E.title(x)}</div>
              <div style={{ fontSize: "0.74rem", color: MUTED }}>{E.sub(x)}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

const MESSAGES_SHORTCUT_ROWS = [
  ["Enter", "Send message"], ["Shift + Enter", "New line"], ["Esc", "Close search / cancel reply"],
];

// ═══════════════════════════════════════════════════════════════════════════
// Empty states
// ═══════════════════════════════════════════════════════════════════════════

function NoConversationsState() {
  return (
    <div style={{ padding: "60px 24px", textAlign: "center" }}>
      <svg width="60" height="60" viewBox="0 0 60 60" fill="none" style={{ margin: "0 auto 16px" }}>
        <circle cx="30" cy="30" r="26" stroke="#E7E9F0" strokeWidth="1" />
        <path d="M18 24c0-2 1.5-3.5 3.5-3.5h17c2 0 3.5 1.5 3.5 3.5v9c0 2-1.5 3.5-3.5 3.5H26l-6 5v-5h-.5c-2 0-3.5-1.5-3.5-3.5z" stroke="#DADEE5" strokeWidth="1.4" fill="none" strokeLinejoin="round" />
      </svg>
      <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: INK, margin: "0 0 6px" }}>No conversations yet</h3>
      <p style={{ fontSize: "0.8rem", color: MUTED, lineHeight: 1.6, margin: "0 auto 16px", maxWidth: 240 }}>
        Message a researcher from Network, or start a project to unlock collaboration chats.
      </p>
      <Link to="/network" style={{ display: "inline-flex", alignItems: "center", gap: 6, background: NAVY, color: WHITE, borderRadius: 8, padding: "8px 16px", fontSize: "0.78rem", fontWeight: 600, textDecoration: "none" }}>
        Browse researchers <ArrowRight size={12} />
      </Link>
    </div>
  );
}

function NoActiveConversation() {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 48, textAlign: "center" }}>
      <div style={{ width: 60, height: 60, borderRadius: "50%", background: RAIL_BG, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 20 }}>
        <MessageSquare size={24} strokeWidth={1.25} style={{ color: DISABLED }} />
      </div>
      <h3 style={{ fontSize: "1.05rem", fontWeight: 700, color: INK, margin: "0 0 8px", letterSpacing: "-0.015em" }}>Select a conversation</h3>
      <p style={{ fontSize: "0.84rem", color: MUTED, lineHeight: 1.6, margin: "0 auto 20px", maxWidth: 300 }}>
        Choose a thread on the left, or find a researcher in <Link to="/network" style={{ color: ACCENT }}>Network</Link> to start a new one.
      </p>
      <Link to="/network" style={{ display: "inline-flex", alignItems: "center", gap: 6, border: `1px solid ${HAIR}`, borderRadius: 8, padding: "8px 16px", fontSize: "0.8rem", fontWeight: 600, color: INK, textDecoration: "none" }}>
        Browse researchers <ArrowRight size={12} />
      </Link>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Composer
// ═══════════════════════════════════════════════════════════════════════════

function Composer({
  input, onInputChange, onSend, sending, editingMessage, onCancelEdit,
  replyingTo, onCancelReply, pendingAttachments, onRemoveAttachment,
  pendingShare, onRemoveShare, fileInputRef, onUploadClick, onFileChange,
  onKeyDown, textareaRef, placeholder, dragOver, onDrop, onDragOver, onDragLeave,
}) {
  return (
    <div
      style={{ borderTop: `1px solid ${HAIR}`, padding: "12px 20px 14px", background: WHITE, flexShrink: 0, position: "relative" }}
      onDrop={onDrop} onDragOver={onDragOver} onDragLeave={onDragLeave}
    >
      {dragOver && (
        <div style={{ position: "absolute", inset: 8, border: `2px dashed ${ACCENT}`, borderRadius: 12, background: `${ACCENT}08`, display: "flex", alignItems: "center", justifyContent: "center", zIndex: 5, pointerEvents: "none" }}>
          <span style={{ fontSize: "0.82rem", fontWeight: 600, color: ACCENT }}>Drop to attach</span>
        </div>
      )}

      {replyingTo && (
        <div style={{ display: "flex", alignItems: "flex-start", gap: 8, borderLeft: `2px solid ${ACCENT}`, borderRadius: 8, paddingLeft: 10, paddingTop: 5, paddingBottom: 5, marginBottom: 8, background: `${ACCENT}06` }}>
          <Reply size={12} style={{ color: ACCENT, marginTop: 2, flexShrink: 0 }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: "0.68rem", fontWeight: 700, color: ACCENT, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>Replying to {replyingTo.sender_name}</div>
            <div style={{ fontSize: "0.78rem", color: "#4A5468", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{replyingTo.snippet}</div>
          </div>
          <button onClick={onCancelReply} aria-label="Cancel reply" style={{ background: "none", border: "none", cursor: "pointer", color: MUTED }}><X size={13} /></button>
        </div>
      )}

      {editingMessage && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, borderLeft: "2px solid #D97706", borderRadius: 8, paddingLeft: 10, paddingTop: 5, paddingBottom: 5, marginBottom: 8, background: "#FFFBEB" }}>
          <Pencil size={12} style={{ color: "#D97706", flexShrink: 0 }} />
          <div style={{ flex: 1, fontSize: "0.76rem", fontWeight: 650, color: "#92400E" }}>Editing message</div>
          <button onClick={onCancelEdit} aria-label="Cancel edit" style={{ background: "none", border: "none", cursor: "pointer", color: MUTED }}><X size={13} /></button>
        </div>
      )}

      {pendingAttachments.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
          {pendingAttachments.map(a => (
            <div key={a.id} style={{ display: "flex", alignItems: "center", gap: 6, border: `1px solid ${HAIR}`, borderRadius: 8, padding: "4px 10px", fontSize: "0.76rem" }}>
              <FileText size={12} style={{ color: ACCENT }} />
              <span style={{ maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{a.filename}</span>
              <button onClick={() => onRemoveAttachment(a.id)} aria-label={`Remove attachment ${a.name || ""}`.trim()} style={{ background: "none", border: "none", cursor: "pointer", color: MUTED }}><X size={12} /></button>
            </div>
          ))}
        </div>
      )}

      {pendingShare && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, border: `1px solid ${ACCENT}`, borderRadius: 8, padding: "6px 12px", marginBottom: 8, fontSize: "0.78rem" }}>
          <Share2 size={13} style={{ color: ACCENT }} />
          <span style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: MUTED }}>{pendingShare.type}</span>
          <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: INK, fontWeight: 600 }}>{pendingShare.title}</span>
          <button onClick={onRemoveShare} aria-label="Remove shared item" style={{ background: "none", border: "none", cursor: "pointer", color: MUTED }}><X size={13} /></button>
        </div>
      )}

      <div style={{ display: "flex", alignItems: "flex-end", gap: 8 }}>
        <div style={{ display: "flex", gap: 3 }}>
          <button data-testid={TID.attachBtn} onClick={onUploadClick} title="Attach file" style={composerIconStyle}><Paperclip size={15} /></button>
          <input ref={fileInputRef} type="file" accept={ALLOWED_MIME.join(",")} style={{ display: "none" }} onChange={onFileChange} />
        </div>
        <div style={{ flex: 1, position: "relative" }}>
          <textarea
            ref={textareaRef}
            data-testid={TID.messageInput}
            value={input}
            onChange={onInputChange}
            onKeyDown={onKeyDown}
            placeholder={placeholder}
            aria-label="Message"
            rows={1}
            style={{ width: "100%", padding: "10px 14px", border: `1px solid ${HAIR}`, borderRadius: 12, fontSize: "0.86rem", color: "#374151", outline: "none", resize: "none", overflow: "hidden", minHeight: 42, maxHeight: 160, lineHeight: 1.5, fontFamily: "inherit", boxSizing: "border-box" }}
            onFocus={e => e.currentTarget.style.borderColor = ACCENT}
            onBlur={e => e.currentTarget.style.borderColor = HAIR}
          />
        </div>
        <button data-testid={TID.messageSendBtn} onClick={onSend} disabled={sending}
          style={{ display: "flex", alignItems: "center", gap: 6, background: NAVY, color: WHITE, border: "none", borderRadius: 12, padding: "10px 18px", fontSize: "0.86rem", fontWeight: 650, cursor: sending ? "not-allowed" : "pointer", opacity: sending ? 0.6 : 1, flexShrink: 0 }}>
          <Send size={14} />
          {editingMessage ? "Save" : "Send"}
        </button>
      </div>
      <div style={{ fontSize: "0.66rem", color: DISABLED, marginTop: 5, paddingLeft: 2 }}>Enter to send · Shift+Enter for new line · drag files to attach</div>
    </div>
  );
}

const composerIconStyle = { width: 38, height: 38, display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 10, color: MUTED, border: `1px solid ${HAIR}`, background: WHITE, cursor: "pointer" };

// ═══════════════════════════════════════════════════════════════════════════
// Main
// ═══════════════════════════════════════════════════════════════════════════

export default function Messages() {
  const { conversationId, otherId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [conversations, setConversations] = useState([]);
  const [convListLoading, setConvListLoading] = useState(true);
  const [convListError, setConvListError]     = useState(false);
  const [filter, setFilter]               = useState("all");
  const [search, setSearch]               = useState("");
  const [activeId, setActiveId]           = useState(conversationId || null);
  const [convDetail, setConvDetail]       = useState(null);
  const [messages, setMessages]           = useState([]);
  const [input, setInput]                 = useState("");
  const [sending, setSending]             = useState(false);
  const [pendingAttachments, setPendingAttachments] = useState([]);
  const [pendingShare, setPendingShare]   = useState(null);
  const [shareOpen, setShareOpen]         = useState(false);
  const [replyingTo, setReplyingTo]       = useState(null);
  const [editingMessage, setEditingMessage] = useState(null);
  const [typingUsers, setTypingUsers]     = useState({});
  const [readBy, setReadBy]               = useState({});
  const [showArchived, setShowArchived]   = useState(false);
  const [threadQuery, setThreadQuery]     = useState("");
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [dragOver, setDragOver]           = useState(false);

  const [pinnedConvs,   togglePinConv]    = usePersistentSet("sq_msg_pinned_v1");
  const [archivedConvs, toggleArchiveConv] = usePersistentSet("sq_msg_archived_v1");

  const bottomRef = useRef(null);
  const wsRef = useRef(null);
  const fileInputRef = useRef(null);
  const typingTimeoutRef = useRef(null);
  const textareaRef = useRef(null);
  const { markConvRead, refresh: refreshUnread } = useUnread();

  // Bootstrap from direct-message deep link
  useEffect(() => {
    if (otherId && !conversationId) {
      api.post("/conversations", { type: "direct", other_user_id: otherId })
        .then(r => navigate(`/messages/c/${r.data.id}`, { replace: true }))
        .catch(() => toast.error("Couldn't open conversation"));
    }
  }, [otherId, conversationId, navigate]);

  // Open conversation from location state
  useEffect(() => {
    const intent = location.state?.openContext;
    if (intent?.type && intent?.id) {
      api.post("/conversations", { type: intent.type, context_id: intent.id })
        .then(r => navigate(`/messages/c/${r.data.id}`, { replace: true, state: {} }))
        .catch(() => toast.error("Couldn't open conversation"));
    }
  }, [location.state, navigate]);

  const loadConversations = useCallback(async () => {
    const params = {};
    if (filter !== "all" && !["unread", "priority", "pinned"].includes(filter)) params.type = filter;
    if (search) params.q = search;
    try {
      const { data } = await api.get("/conversations", { params });
      setConversations(data);
      setConvListError(false);
    } catch {
      setConvListError(true);
    } finally {
      setConvListLoading(false);
    }
  }, [filter, search]);

  useEffect(() => { loadConversations(); }, [loadConversations]);
  useEffect(() => { setActiveId(conversationId || null); }, [conversationId]);

  // Kept as a ref so the WebSocket effect below (keyed only on activeId/user)
  // can call the latest loadConversations without reconnecting the socket
  // every time `filter`/`search` change loadConversations's identity.
  const loadConversationsRef = useRef(loadConversations);
  useEffect(() => { loadConversationsRef.current = loadConversations; }, [loadConversations]);

  useEffect(() => {
    if (!activeId) { setConvDetail(null); setMessages([]); return; }
    let alive = true;
    (async () => {
      try {
        const [d, m] = await Promise.all([
          api.get(`/conversations/${activeId}`),
          api.get(`/conversations/${activeId}/messages`),
        ]);
        if (!alive) return;
        setConvDetail(d.data);
        setMessages(m.data);
        api.post(`/conversations/${activeId}/read`).catch(() => {});
        markConvRead(activeId);
        setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
      } catch { toast.error("Couldn't load conversation"); }
    })();
    return () => { alive = false; };
  }, [activeId]);

  // WebSocket — exponential backoff reconnect (unchanged)
  useEffect(() => {
    if (!activeId) return;
    let alive = true;
    let retryDelay = 1000;
    let retryTimer = null;

    const connect = () => {
      if (!alive) return;
      const wsUrl = BACKEND_URL.replace(/^http/, "ws") + `/api/ws/conversations/${activeId}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onopen = () => { retryDelay = 1000; };
      ws.onmessage = (ev) => {
        try {
          const evt = JSON.parse(ev.data);
          if (evt.type === "message") {
            setMessages(prev => prev.some(m => m.id === evt.message.id) ? prev : [...prev, evt.message]);
            if (evt.message.sender_id !== user.id) {
              api.post(`/conversations/${activeId}/read`).catch(() => {});
              loadConversationsRef.current();
            }
            setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
          } else if (evt.type === "message_edited") {
            setMessages(prev => prev.map(m => m.id === evt.message.id ? evt.message : m));
          } else if (evt.type === "message_deleted") {
            setMessages(prev => prev.filter(m => m.id !== evt.message_id));
          } else if (evt.type === "reaction_added") {
            setMessages(prev => prev.map(m => {
              if (m.id !== evt.message_id) return m;
              const reactions = { ...(m.reactions || {}) };
              if (!reactions[evt.emoji]) reactions[evt.emoji] = [];
              if (!reactions[evt.emoji].some(r => r.user_id === evt.user_id)) reactions[evt.emoji] = [...reactions[evt.emoji], { user_id: evt.user_id, full_name: evt.full_name }];
              return { ...m, reactions };
            }));
          } else if (evt.type === "reaction_removed") {
            setMessages(prev => prev.map(m => {
              if (m.id !== evt.message_id) return m;
              const reactions = { ...(m.reactions || {}) };
              if (reactions[evt.emoji]) reactions[evt.emoji] = reactions[evt.emoji].filter(r => r.user_id !== evt.user_id);
              return { ...m, reactions };
            }));
          } else if (evt.type === "typing") {
            if (evt.user_id === user.id) return;
            setTypingUsers(prev => ({ ...prev, [evt.user_id]: evt.typing ? Date.now() : 0 }));
            if (evt.typing) {
              setTimeout(() => setTypingUsers(prev => {
                if (!prev[evt.user_id]) return prev;
                if (Date.now() - prev[evt.user_id] > 4000) return { ...prev, [evt.user_id]: 0 };
                return prev;
              }), 4500);
            }
          } else if (evt.type === "read") {
            setReadBy(prev => ({ ...prev, [evt.user_id]: evt.at }));
          }
        } catch {}
      };
      ws.onerror = () => {};
      ws.onclose = () => {
        if (!alive) return;
        retryTimer = setTimeout(() => { retryDelay = Math.min(retryDelay * 2, 30000); connect(); }, retryDelay);
      };
    };

    connect();
    return () => {
      alive = false;
      if (retryTimer) clearTimeout(retryTimer);
      try { wsRef.current?.close(); } catch {}
    };
  }, [activeId, user?.id]);

  const onTyping = () => {
    if (!wsRef.current || wsRef.current.readyState !== 1) return;
    wsRef.current.send(JSON.stringify({ type: "typing", typing: true }));
    if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
    typingTimeoutRef.current = setTimeout(() => {
      try { wsRef.current.send(JSON.stringify({ type: "typing", typing: false })); } catch {}
    }, 2500);
  };

  const send = async () => {
    if (!activeId) return;
    const content = input.trim();
    if (editingMessage) {
      if (!content) return;
      setSending(true);
      try {
        await api.patch(`/conversations/${activeId}/messages/${editingMessage.id}`, { content });
        setInput(""); setEditingMessage(null);
        if (textareaRef.current) textareaRef.current.style.height = "auto";
      } catch (e) { toast.error(e.response?.data?.detail || "Edit failed"); }
      finally { setSending(false); }
      return;
    }
    if (!content && pendingAttachments.length === 0 && !pendingShare) return;
    setSending(true);
    try {
      const body = {
        content,
        attachment_ids: pendingAttachments.map(a => a.id),
        shared_resources: pendingShare ? [pendingShare] : [],
        reply_to_id: replyingTo ? replyingTo.id : "",
      };
      await api.post(`/conversations/${activeId}/messages`, body);
      setInput(""); setPendingAttachments([]); setPendingShare(null); setReplyingTo(null);
      if (textareaRef.current) textareaRef.current.style.height = "auto";
      loadConversations();
      refreshUnread();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed to send"); }
    finally { setSending(false); }
  };

  const startEdit = (m) => { setEditingMessage({ id: m.id, content: m.content }); setInput(m.content); setReplyingTo(null); };
  const cancelEdit = () => { setEditingMessage(null); setInput(""); if (textareaRef.current) textareaRef.current.style.height = "auto"; };
  const startReply = (m) => { setReplyingTo({ id: m.id, snippet: (m.content || "📎 Attachment").slice(0, 140), sender_name: m.sender?.full_name || "" }); setEditingMessage(null); };

  const deleteMessage = async (msgId) => {
    if (!window.confirm("Delete this message?")) return;
    try {
      await api.delete(`/conversations/${activeId}/messages/${msgId}`);
      setMessages(prev => prev.filter(m => m.id !== msgId));
    } catch (e) { toast.error(e.response?.data?.detail || "Failed to delete"); }
  };

  const toggleReaction = async (msgId, emoji) => {
    const msg = messages.find(m => m.id === msgId);
    if (!msg) return;
    const isMine = ((msg.reactions || {})[emoji] || []).some(r => r.user_id === user.id);
    try {
      if (isMine) await api.delete(`/conversations/${activeId}/messages/${msgId}/reactions/${encodeURIComponent(emoji)}`);
      else await api.post(`/conversations/${activeId}/messages/${msgId}/reactions`, { emoji });
    } catch { toast.error("Reaction failed"); }
  };

  const leaveConversation = async (convId) => {
    if (!window.confirm("Leave this conversation? You won't receive new messages.")) return;
    try {
      await api.post(`/conversations/${convId}/leave`);
      navigate("/messages");
      loadConversations();
    } catch (e) { toast.error(e.response?.data?.detail || "Failed to leave conversation"); }
  };

  const toggleMute = async (convId) => {
    try {
      const { data } = await api.post(`/conversations/${convId}/mute`);
      setConversations(prev => prev.map(c => c.id === convId ? { ...c, muted: data.muted } : c));
    } catch { toast.error("Failed to toggle mute"); }
  };

  const uploadFile = async (f) => {
    if (!ALLOWED_MIME.includes(f.type)) { toast.error("File type not allowed"); return; }
    if (f.size > 25 * 1024 * 1024) { toast.error("File too large (25 MB max)"); return; }
    const form = new FormData();
    form.append("file", f);
    try {
      const { data } = await api.post("/uploads", form, { headers: { "Content-Type": "multipart/form-data" } });
      setPendingAttachments(prev => [...prev, data]);
      toast.success("Attached");
    } catch (err) { toast.error(err.response?.data?.detail || "Upload failed"); }
  };

  const onUploadClick = () => fileInputRef.current?.click();
  const onFileChange = async (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (f) await uploadFile(f);
  };

  // Drag & drop upload — real, client-side convenience wrapping the same upload call
  const onDrop = (e) => {
    e.preventDefault(); setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f && activeId) uploadFile(f);
  };
  const onDragOver = (e) => { e.preventDefault(); if (activeId) setDragOver(true); };
  const onDragLeave = () => setDragOver(false);

  const handleInputChange = (e) => {
    setInput(e.target.value);
    onTyping();
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
  };

  const handleComposerKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
    else if (e.key === "Escape") { if (replyingTo) setReplyingTo(null); else if (editingMessage) cancelEdit(); }
  };

  // Export — real, fully client-side transcript of already-loaded messages
  const exportConversation = () => {
    if (!convDetail) return;
    const title = convDetail.type === "direct" ? convDetail.other_user?.full_name : (convDetail.title || TYPE_LABEL[convDetail.type]);
    const lines = [`# ${title}`, ""];
    messages.forEach(m => {
      lines.push(`**${m.sender?.full_name || "Unknown"}** — ${new Date(m.created_at).toLocaleString()}`);
      if (m.content) lines.push(m.content);
      (m.attachments || []).forEach(a => lines.push(`[attachment: ${a.filename}]`));
      (m.shared_resources || []).forEach(s => lines.push(`[shared ${s.type}: ${s.title}]`));
      lines.push("");
    });
    const blob = new Blob([lines.join("\n")], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${(title || "conversation").replace(/\s+/g, "-").toLowerCase()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const groupedMessages = useMemo(() => messages.map((m, i) => {
    const prev = messages[i - 1];
    const isGrouped = prev && prev.sender_id === m.sender_id && sameDay(prev.created_at, m.created_at) && (new Date(m.created_at) - new Date(prev.created_at) < 120000);
    return { ...m, isGrouped };
  }), [messages]);

  const visibleMessages = useMemo(() => (
    threadQuery
      ? groupedMessages.filter(m => (m.content || "").toLowerCase().includes(threadQuery.toLowerCase()))
      : groupedMessages
  ), [groupedMessages, threadQuery]);

  const placeholders = ["Discuss your manuscript…", "Share research updates…", "Coordinate collaboration tasks…", "Ask about methodology…"];
  const placeholder = placeholders[Math.floor(Date.now() / 86400000) % placeholders.length];

  return (
    <>
      <style>{`
        @keyframes tp{0%,80%,100%{transform:scale(0.6);opacity:0.4}40%{transform:scale(1);opacity:1}}
        .msg-scroll::-webkit-scrollbar{width:5px}
        .msg-scroll::-webkit-scrollbar-track{background:transparent}
        .msg-scroll::-webkit-scrollbar-thumb{background:#E2E8F0;border-radius:99px}
      `}</style>

      <div style={{ margin: "-24px -24px 0", display: "grid", gridTemplateColumns: "260px 1fr 320px", background: WHITE, height: "calc(100vh - 56px)" }}>

        {/* LEFT */}
        <SideNav
          conversations={conversations} filter={filter} setFilter={setFilter}
          search={search} setSearch={setSearch} activeId={activeId}
          onOpen={id => navigate(`/messages/c/${id}`)}
          pinned={pinnedConvs} togglePin={togglePinConv}
          archived={archivedConvs} toggleArchive={toggleArchiveConv}
          showArchived={showArchived} setShowArchived={setShowArchived}
          onToggleMute={toggleMute}
        />

        {/* CENTER */}
        <div style={{ display: "flex", flexDirection: "column", overflow: "hidden", borderRight: `1px solid ${HAIR}`, position: "relative" }}>
          {convListLoading && !activeId && (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Spinner size={22} />
            </div>
          )}
          {!convListLoading && convListError && conversations.length === 0 && !activeId && (
            <ErrorState message="Could not load your conversations." onRetry={loadConversations} />
          )}
          {!convListLoading && !convListError && conversations.length === 0 && !activeId && <NoConversationsState />}
          {conversations.length > 0 && !activeId && <NoActiveConversation />}

          {activeId && convDetail && (
            <>
              <Toolbar
                conv={convDetail}
                isPinned={pinnedConvs.has(activeId)}
                onTogglePin={() => togglePinConv(activeId)}
                onShare={() => setShareOpen(true)}
                onExport={exportConversation}
                onLeave={() => leaveConversation(activeId)}
                onOpenShortcuts={() => setShortcutsOpen(true)}
                threadQuery={threadQuery} setThreadQuery={setThreadQuery}
              />

              <div data-testid={TID.messageList} className="msg-scroll" style={{ flex: 1, overflowY: "auto", padding: "16px 22px 8px" }}>
                {visibleMessages.length === 0 && (
                  <div style={{ textAlign: "center", color: DISABLED, fontSize: "0.8rem", padding: "40px 0" }}>
                    {threadQuery ? "No messages match your search." : "No messages yet. Start the conversation."}
                  </div>
                )}
                {visibleMessages.map((m, i) => {
                  const prev = visibleMessages[i - 1];
                  const showDate = !prev || !sameDay(prev.created_at, m.created_at);
                  return (
                    <React.Fragment key={m.id}>
                      {showDate && <DateSeparator label={fmtDate(m.created_at)} />}
                      <MessageBubble
                        m={m} mine={m.sender_id === user.id} convDetail={convDetail} readBy={readBy}
                        onReply={() => startReply(m)} onEdit={() => startEdit(m)} onDelete={() => deleteMessage(m.id)}
                        onReactionToggle={toggleReaction} currentUserId={user.id} isGrouped={m.isGrouped}
                        highlight={!!threadQuery}
                      />
                    </React.Fragment>
                  );
                })}
                <TypingLine typingUsers={typingUsers} members={convDetail.members || []} />
                <div ref={bottomRef} />
              </div>

              <Composer
                input={input} onInputChange={handleInputChange} onSend={send} sending={sending}
                editingMessage={editingMessage} onCancelEdit={cancelEdit}
                replyingTo={replyingTo} onCancelReply={() => setReplyingTo(null)}
                pendingAttachments={pendingAttachments} onRemoveAttachment={id => setPendingAttachments(pendingAttachments.filter(x => x.id !== id))}
                pendingShare={pendingShare} onRemoveShare={() => setPendingShare(null)}
                fileInputRef={fileInputRef} onUploadClick={onUploadClick} onFileChange={onFileChange}
                onKeyDown={handleComposerKeyDown} textareaRef={textareaRef} placeholder={placeholder}
                dragOver={dragOver} onDrop={onDrop} onDragOver={onDragOver} onDragLeave={onDragLeave}
              />
            </>
          )}
        </div>

        {/* RIGHT */}
        <div className="msg-scroll" style={{ overflowY: "auto", background: RAIL_BG }}>
          <AIPanel conv={convDetail} messages={messages} currentUserId={user.id} onLeave={() => activeId && leaveConversation(activeId)} onExport={exportConversation} />
        </div>
      </div>

      {shareOpen && <SharePicker onClose={() => setShareOpen(false)} onPick={r => { setPendingShare(r); setShareOpen(false); }} />}
      {shortcutsOpen && <ShortcutsModal onClose={() => setShortcutsOpen(false)} rows={MESSAGES_SHORTCUT_ROWS} />}
    </>
  );
}
