import React, { useEffect, useRef, useState } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import Link from "@tiptap/extension-link";
import Collaboration from "@tiptap/extension-collaboration";
import CollaborationCursor from "@tiptap/extension-collaboration-cursor";
import {
  Bold, Italic, Strikethrough, Heading1, Heading2, Heading3,
  List, ListOrdered, Quote, Code, Link as LinkIcon, Undo2, Redo2,
  Wifi, WifiOff, Loader2,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useWikiCollab } from "@/hooks/useWikiCollab";
import { BRD, TEXT_MUTED, TEXT_SECONDARY, NAVY, RADIUS_SM, WHITE, EMERALD, AMBER } from "@/lib/tokens";
import { transition } from "@/lib/motion";

function ToolbarButton({ active, onClick, disabled, label, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      aria-pressed={!!active}
      title={label}
      style={{
        width: 28, height: 28, display: "flex", alignItems: "center", justifyContent: "center",
        border: "none", borderRadius: RADIUS_SM, cursor: disabled ? "default" : "pointer",
        background: active ? "rgba(15,40,71,0.1)" : "transparent",
        color: disabled ? TEXT_MUTED : active ? NAVY : TEXT_SECONDARY,
        opacity: disabled ? 0.4 : 1,
        transition: transition.hover,
      }}
    >
      {children}
    </button>
  );
}

function PresenceBadge({ status }) {
  const map = {
    connected: { icon: Wifi, color: EMERALD, label: "Live" },
    connecting: { icon: Loader2, color: AMBER, label: "Connecting…" },
    offline: { icon: WifiOff, color: TEXT_MUTED, label: "Editing locally — will sync when reconnected" },
  };
  const { icon: Icon, color, label } = map[status] || map.offline;
  return (
    <span title={label} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color }}>
      <Icon size={11} strokeWidth={2} className={status === "connecting" ? "animate-spin" : undefined} />
      {status === "connected" ? "Live" : status === "connecting" ? "Connecting…" : "Offline"}
    </span>
  );
}

/**
 * WikiEditor — Tiptap rich text editor for wiki pages, with real-time
 * collaborative editing via Yjs when `pageId` is provided (see
 * useWikiCollab). Content is persisted as structured Tiptap JSON through
 * `onSave`, debounced so typing doesn't fire a request per keystroke.
 *
 * If the collab WebSocket can't connect, the editor stays fully editable —
 * edits keep saving through the normal autosave path, they just won't be
 * seen live by other editors until the connection recovers. A strict
 * read-only fallback would block legitimate solo editing during a network
 * blip, which seemed like the wrong trade-off for a wiki page.
 *
 * Covers headings, bold/italic/strike, bullet/ordered lists, blockquote,
 * inline code + code blocks, and links — the core StarterKit set actually
 * installed. Tables, checklists, images/embeds/PDF previews are not
 * implemented yet (no extension installed for them) — a disclosed gap.
 */
export default function WikiEditor({ pageId, content, onSave, onTypingChange, editable = true, autosaveMs = 1500 }) {
  const { user } = useAuth();
  const { ydoc, awareness, status } = useWikiCollab(pageId, user);
  const saveTimer = useRef(null);
  const typingTimer = useRef(null);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({ history: false }), // Yjs owns undo/redo history in collab mode
      Placeholder.configure({ placeholder: "Write something, or press '/' for a formatting hint…" }),
      Link.configure({ openOnClick: false, autolink: true }),
      Collaboration.configure({ document: ydoc }),
      CollaborationCursor.configure({
        provider: { awareness },
        user: { name: user?.full_name || "Someone", color: awareness.getLocalState()?.user?.color || NAVY },
      }),
    ],
    editable,
    onUpdate: ({ editor }) => {
      if (onTypingChange) {
        onTypingChange(true);
        if (typingTimer.current) clearTimeout(typingTimer.current);
        typingTimer.current = setTimeout(() => onTypingChange(false), 2000);
      }
      if (!onSave) return;
      const json = editor.getJSON();
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(() => onSave(json), autosaveMs);
    },
  }, [ydoc]);

  // First-load seed: if the shared doc is empty and we have persisted
  // content, load it into the editor once so it merges into the Y.Doc.
  useEffect(() => {
    if (!editor) return;
    const fragment = ydoc.getXmlFragment("default");
    if (fragment.length === 0 && content) {
      editor.commands.setContent(content, false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editor]);

  useEffect(() => () => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
    if (typingTimer.current) clearTimeout(typingTimer.current);
  }, []);

  if (!editor) return null;

  const setLink = () => {
    const url = window.prompt("Link URL");
    if (url === null) return;
    if (url === "") { editor.chain().focus().unsetLink().run(); return; }
    editor.chain().focus().setLink({ href: url }).run();
  };

  return (
    <div style={{ border: `1px solid ${BRD}`, borderRadius: 10, background: WHITE }}>
      {editable && (
        <div
          role="toolbar"
          aria-label="Formatting"
          className="flex items-center justify-between flex-wrap gap-1"
          style={{ padding: "6px 8px", borderBottom: `1px solid ${BRD}` }}
        >
          <div className="flex items-center gap-1 flex-wrap">
            <ToolbarButton label="Undo" onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()}><Undo2 size={14} strokeWidth={1.75} /></ToolbarButton>
            <ToolbarButton label="Redo" onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()}><Redo2 size={14} strokeWidth={1.75} /></ToolbarButton>
            <span style={{ width: 1, height: 18, background: BRD, margin: "0 4px" }} aria-hidden="true" />
            <ToolbarButton label="Heading 1" active={editor.isActive("heading", { level: 1 })} onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}><Heading1 size={14} strokeWidth={1.75} /></ToolbarButton>
            <ToolbarButton label="Heading 2" active={editor.isActive("heading", { level: 2 })} onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}><Heading2 size={14} strokeWidth={1.75} /></ToolbarButton>
            <ToolbarButton label="Heading 3" active={editor.isActive("heading", { level: 3 })} onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}><Heading3 size={14} strokeWidth={1.75} /></ToolbarButton>
            <span style={{ width: 1, height: 18, background: BRD, margin: "0 4px" }} aria-hidden="true" />
            <ToolbarButton label="Bold" active={editor.isActive("bold")} onClick={() => editor.chain().focus().toggleBold().run()}><Bold size={14} strokeWidth={1.75} /></ToolbarButton>
            <ToolbarButton label="Italic" active={editor.isActive("italic")} onClick={() => editor.chain().focus().toggleItalic().run()}><Italic size={14} strokeWidth={1.75} /></ToolbarButton>
            <ToolbarButton label="Strikethrough" active={editor.isActive("strike")} onClick={() => editor.chain().focus().toggleStrike().run()}><Strikethrough size={14} strokeWidth={1.75} /></ToolbarButton>
            <ToolbarButton label="Inline code" active={editor.isActive("code")} onClick={() => editor.chain().focus().toggleCode().run()}><Code size={14} strokeWidth={1.75} /></ToolbarButton>
            <ToolbarButton label="Link" active={editor.isActive("link")} onClick={setLink}><LinkIcon size={14} strokeWidth={1.75} /></ToolbarButton>
            <span style={{ width: 1, height: 18, background: BRD, margin: "0 4px" }} aria-hidden="true" />
            <ToolbarButton label="Bullet list" active={editor.isActive("bulletList")} onClick={() => editor.chain().focus().toggleBulletList().run()}><List size={14} strokeWidth={1.75} /></ToolbarButton>
            <ToolbarButton label="Numbered list" active={editor.isActive("orderedList")} onClick={() => editor.chain().focus().toggleOrderedList().run()}><ListOrdered size={14} strokeWidth={1.75} /></ToolbarButton>
            <ToolbarButton label="Quote" active={editor.isActive("blockquote")} onClick={() => editor.chain().focus().toggleBlockquote().run()}><Quote size={14} strokeWidth={1.75} /></ToolbarButton>
          </div>
          {pageId && <PresenceBadge status={status} />}
        </div>
      )}
      <div style={{ padding: "16px 20px", minHeight: 240 }} className="sq-wiki-editor">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}
