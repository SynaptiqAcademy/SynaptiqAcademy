import React, { useMemo, useState } from "react";
import { ChevronRight, ChevronDown, FileText, Plus, MoreHorizontal, Copy, Archive, Trash2 } from "lucide-react";
import { Dropdown, DropdownItem } from "@/components/ds/Dropdown";
import { NAVY, NAVY_06, TEXT_PRIMARY, TEXT_MUTED, RADIUS_SM } from "@/lib/tokens";
import { transition } from "@/lib/motion";

function TreeNode({ page, childrenOf, activeId, depth, onSelect, onAddChild, onDuplicate, onArchive, onDelete, expanded, toggleExpanded }) {
  const kids = childrenOf(page.id);
  const isOpen = expanded.has(page.id);
  const isActive = activeId === page.id;
  const [hov, setHov] = useState(false);

  return (
    <div>
      <div
        onMouseEnter={() => setHov(true)}
        onMouseLeave={() => setHov(false)}
        className="flex items-center gap-1 group"
        style={{
          paddingLeft: 8 + depth * 16,
          paddingRight: 6,
          height: 30,
          background: isActive ? NAVY_06 : "transparent",
          borderRadius: RADIUS_SM,
          cursor: "pointer",
        }}
      >
        <button
          onClick={() => toggleExpanded(page.id)}
          aria-label={isOpen ? "Collapse" : "Expand"}
          style={{ width: 16, height: 16, display: "flex", alignItems: "center", justifyContent: "center", background: "none", border: "none", cursor: "pointer", color: TEXT_MUTED, flexShrink: 0, visibility: kids.length ? "visible" : "hidden" }}
        >
          {isOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </button>
        <button
          onClick={() => onSelect(page)}
          style={{ display: "flex", alignItems: "center", gap: 6, flex: 1, minWidth: 0, background: "none", border: "none", cursor: "pointer", padding: "0 4px", textAlign: "left" }}
        >
          <span style={{ fontSize: 13, flexShrink: 0 }}>{page.icon || <FileText size={12} strokeWidth={1.75} style={{ color: TEXT_MUTED }} />}</span>
          <span style={{ fontSize: 13, color: isActive ? NAVY : TEXT_PRIMARY, fontWeight: isActive ? 600 : 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {page.title || "Untitled"}
          </span>
          {page.status === "archived" && <span style={{ fontSize: 10, color: TEXT_MUTED, flexShrink: 0 }}>(archived)</span>}
        </button>
        <div style={{ display: "flex", alignItems: "center", gap: 2, opacity: hov ? 1 : 0, transition: transition.hover }}>
          <button onClick={() => onAddChild(page.id)} aria-label={`New page under ${page.title}`} style={{ width: 20, height: 20, display: "flex", alignItems: "center", justifyContent: "center", background: "none", border: "none", cursor: "pointer", color: TEXT_MUTED }}>
            <Plus size={12} strokeWidth={1.75} />
          </button>
          <Dropdown
            align="right" width={150}
            trigger={
              <button aria-label={`More actions for ${page.title}`} style={{ width: 20, height: 20, display: "flex", alignItems: "center", justifyContent: "center", background: "none", border: "none", cursor: "pointer", color: TEXT_MUTED }}>
                <MoreHorizontal size={12} strokeWidth={1.75} />
              </button>
            }
          >
            <DropdownItem icon={Copy} onClick={() => onDuplicate(page)}>Duplicate</DropdownItem>
            <DropdownItem icon={Archive} onClick={() => onArchive(page)}>{page.status === "archived" ? "Unarchive" : "Archive"}</DropdownItem>
            <DropdownItem icon={Trash2} destructive onClick={() => onDelete(page)}>Delete</DropdownItem>
          </Dropdown>
        </div>
      </div>
      {isOpen && kids.map((k) => (
        <TreeNode
          key={k.id} page={k} childrenOf={childrenOf} activeId={activeId} depth={depth + 1}
          onSelect={onSelect} onAddChild={onAddChild} onDuplicate={onDuplicate} onArchive={onArchive} onDelete={onDelete}
          expanded={expanded} toggleExpanded={toggleExpanded}
        />
      ))}
    </div>
  );
}

/**
 * WikiPageTree — nested page navigation built from a flat list of
 * workspace_items (item_type=wiki_page) via their parent_id field.
 */
export default function WikiPageTree({ pages, activeId, onSelect, onAddChild, onDuplicate, onArchive, onDelete }) {
  const [expanded, setExpanded] = useState(() => new Set(pages.map((p) => p.id)));
  const toggleExpanded = (id) => setExpanded((prev) => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  const roots = useMemo(() => pages.filter((p) => !p.parent_id), [pages]);
  const childrenOf = (parentId) => pages.filter((p) => p.parent_id === parentId).sort((a, b) => (a.position || 0) - (b.position || 0));

  return (
    <div role="tree" aria-label="Wiki pages">
      {roots.length === 0 ? (
        <div style={{ fontSize: 12, color: TEXT_MUTED, padding: "8px 4px" }}>No pages yet.</div>
      ) : (
        roots.map((p) => (
          <TreeNode
            key={p.id} page={p} childrenOf={childrenOf} activeId={activeId} depth={0}
            onSelect={onSelect} onAddChild={onAddChild} onDuplicate={onDuplicate} onArchive={onArchive} onDelete={onDelete}
            expanded={expanded} toggleExpanded={toggleExpanded}
          />
        ))
      )}
    </div>
  );
}
