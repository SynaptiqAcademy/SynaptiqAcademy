import React, { useEffect, useRef, useState } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import Link from "@tiptap/extension-link";
import {
  Bold, Italic, Strikethrough, Heading1, Heading2, Heading3,
  List, ListOrdered, Quote, Code, Link as LinkIcon, Undo2, Redo2,
} from "lucide-react";
import { BRD, TEXT_MUTED, TEXT_SECONDARY, NAVY, RADIUS_SM, WHITE } from "@/lib/tokens";
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

/**
 * WikiEditor — Tiptap-based rich text editor for wiki pages.
 *
 * Persists structured Tiptap JSON (not rendered HTML) via onSave, debounced
 * so typing doesn't fire a request per keystroke. Covers headings, bold/
 * italic/strike, bullet/ordered lists, blockquote, inline code + code
 * blocks, and links — the core StarterKit set actually installed. Tables,
 * checklists, images/embeds/PDF previews are NOT implemented yet (no
 * extension installed for them) — a real, disclosed gap, not silently
 * dropped.
 */
export default function WikiEditor({ content, onSave, editable = true, autosaveMs = 1500 }) {
  const [linkPromptOpen, setLinkPromptOpen] = useState(false);
  const saveTimer = useRef(null);
  const lastSavedRef = useRef(content);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: "Write something, or press '/' for a formatting hint…" }),
      Link.configure({ openOnClick: false, autolink: true }),
    ],
    content: content || "",
    editable,
    onUpdate: ({ editor }) => {
      if (!onSave) return;
      const json = editor.getJSON();
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(() => {
        lastSavedRef.current = json;
        onSave(json);
      }, autosaveMs);
    },
  });

  // Keep the editor in sync if `content` changes externally (e.g. version restore)
  useEffect(() => {
    if (editor && content && JSON.stringify(content) !== JSON.stringify(lastSavedRef.current)) {
      editor.commands.setContent(content, false);
      lastSavedRef.current = content;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content]);

  useEffect(() => () => { if (saveTimer.current) clearTimeout(saveTimer.current); }, []);

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
          className="flex items-center gap-1 flex-wrap"
          style={{ padding: "6px 8px", borderBottom: `1px solid ${BRD}` }}
        >
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
      )}
      <div style={{ padding: "16px 20px", minHeight: 240 }} className="sq-wiki-editor">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}
