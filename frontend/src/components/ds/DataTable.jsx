import React, { useState } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import { NAVY, BRD, BRD_SOFT, WARM, WHITE, NAVY_04, TEXT_MUTED, TEXT_STRONG, RADIUS_MD } from "@/lib/tokens";

/**
 * DataTable — standardized data table component.
 *
 * Props:
 *   columns   [{ key, label, width?, align?, sortable?, render? }]
 *   rows      array of objects
 *   onSort    function({ key, dir: "asc"|"desc" })
 *   sortKey   string
 *   sortDir   "asc" | "desc"
 *   loading   bool
 *   emptyNode ReactNode   — empty state override
 *   onRowClick function(row)
 *   stickyHeader bool
 *   className string
 *   selectable   bool          — renders a checkbox column when true
 *   selectedIds  Set|array     — ids currently selected (matched against row.id ?? row._id)
 *   onSelectRow  function(row, checked)
 *   onSelectAll  function(checked)
 */
export function DataTable({
  columns = [],
  rows = [],
  onSort,
  sortKey,
  sortDir = "asc",
  loading = false,
  emptyNode,
  onRowClick,
  stickyHeader = false,
  className = "",
  selectable = false,
  selectedIds,
  onSelectRow,
  onSelectAll,
}) {
  const [hoveredRow, setHoveredRow] = useState(null);
  const selectedSet = selectedIds instanceof Set ? selectedIds : new Set(selectedIds || []);

  function handleSort(col) {
    if (!col.sortable || !onSort) return;
    onSort({
      key: col.key,
      dir: sortKey === col.key && sortDir === "asc" ? "desc" : "asc",
    });
  }

  const allSelected = selectable && rows.length > 0 && rows.every((r) => selectedSet.has(r.id ?? r._id));

  return (
    <div
      className={className}
      style={{
        border: `1px solid ${BRD}`,
        borderRadius: RADIUS_MD,
        overflow: "hidden",
        background: WHITE,
      }}
    >
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
          <thead>
            <tr style={{ background: WARM }}>
              {selectable && (
                <th style={{
                  padding: "10px 14px", width: 36,
                  borderBottom: `1px solid ${BRD}`,
                  position: stickyHeader ? "sticky" : undefined,
                  top: stickyHeader ? 0 : undefined,
                  background: WARM,
                }}>
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={(e) => onSelectAll?.(e.target.checked)}
                    aria-label="Select all rows"
                  />
                </th>
              )}
              {columns.map((col) => {
                const sorted = sortKey === col.key;
                return (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col)}
                    style={{
                      padding: "10px 14px",
                      textAlign: col.align || "left",
                      fontSize: "0.67rem",
                      fontWeight: 700,
                      letterSpacing: "0.09em",
                      textTransform: "uppercase",
                      color: sorted ? NAVY : TEXT_MUTED,
                      borderBottom: `1px solid ${BRD}`,
                      whiteSpace: "nowrap",
                      cursor: col.sortable ? "pointer" : "default",
                      userSelect: "none",
                      width: col.width || undefined,
                      position: stickyHeader ? "sticky" : undefined,
                      top: stickyHeader ? 0 : undefined,
                      background: WARM,
                      transition: "color 150ms",
                    }}
                  >
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                      {col.label}
                      {col.sortable && (
                        <span style={{ display: "inline-flex", flexDirection: "column", gap: 1, opacity: sorted ? 1 : 0.3 }}>
                          <ChevronUp
                            size={9}
                            style={{ color: sorted && sortDir === "asc" ? NAVY : TEXT_MUTED }}
                          />
                          <ChevronDown
                            size={9}
                            style={{ color: sorted && sortDir === "desc" ? NAVY : TEXT_MUTED, marginTop: -5 }}
                          />
                        </span>
                      )}
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={columns.length} style={{ padding: "32px 16px", textAlign: "center", color: TEXT_MUTED, fontSize: "0.8rem" }}>
                  Loading…
                </td>
              </tr>
            )}
            {!loading && rows.length === 0 && (
              <tr>
                <td colSpan={columns.length} style={{ padding: 0 }}>
                  {emptyNode || (
                    <div style={{ padding: "40px 24px", textAlign: "center", color: TEXT_MUTED, fontSize: "0.8rem" }}>
                      No data found.
                    </div>
                  )}
                </td>
              </tr>
            )}
            {!loading && rows.map((row, ri) => {
              const isHovered = hoveredRow === ri && !!onRowClick;
              const rowId = row.id ?? row._id ?? ri;
              const isSelected = selectable && selectedSet.has(rowId);
              return (
                <tr
                  key={rowId}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  onMouseEnter={() => setHoveredRow(ri)}
                  onMouseLeave={() => setHoveredRow(null)}
                  style={{
                    borderBottom: ri < rows.length - 1 ? `1px solid ${BRD_SOFT}` : "none",
                    background: isSelected ? NAVY_04 : isHovered ? WARM : WHITE,
                    cursor: onRowClick ? "pointer" : "default",
                    transition: "background 100ms",
                  }}
                >
                  {selectable && (
                    <td
                      style={{ padding: "10px 14px", verticalAlign: "middle" }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => onSelectRow?.(row, e.target.checked)}
                        aria-label="Select row"
                      />
                    </td>
                  )}
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      style={{
                        padding: "10px 14px",
                        textAlign: col.align || "left",
                        color: TEXT_STRONG,
                        whiteSpace: col.wrap ? undefined : "nowrap",
                        maxWidth: col.maxWidth || undefined,
                        overflow: col.maxWidth ? "hidden" : undefined,
                        textOverflow: col.maxWidth ? "ellipsis" : undefined,
                        verticalAlign: "middle",
                      }}
                    >
                      {col.render ? col.render(row[col.key], row) : row[col.key] ?? "—"}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/**
 * Pagination — standard page navigation.
 */
export function Pagination({ page, totalPages, onPage, className = "" }) {
  if (totalPages <= 1) return null;
  const pages = [];
  const maxVisible = 7;

  if (totalPages <= maxVisible) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (page > 3) pages.push("…");
    for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i++) pages.push(i);
    if (page < totalPages - 2) pages.push("…");
    pages.push(totalPages);
  }

  const btnStyle = (isActive) => ({
    minWidth: 32,
    height: 32,
    padding: "0 8px",
    fontSize: "0.78rem",
    fontWeight: isActive ? 700 : 400,
    color: isActive ? WHITE : TEXT_STRONG,
    background: isActive ? NAVY : WHITE,
    border: `1px solid ${isActive ? NAVY : BRD}`,
    borderRadius: RADIUS_MD,
    cursor: "pointer",
    transition: "all 150ms",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
  });

  return (
    <div
      className={className}
      style={{ display: "flex", alignItems: "center", gap: 4, justifyContent: "center" }}
    >
      <button
        onClick={() => onPage(page - 1)}
        disabled={page <= 1}
        style={{ ...btnStyle(false), opacity: page <= 1 ? 0.4 : 1 }}
      >
        ‹
      </button>
      {pages.map((p, i) =>
        p === "…" ? (
          <span key={`ellipsis-${i}`} style={{ padding: "0 4px", color: TEXT_MUTED }}>…</span>
        ) : (
          <button key={p} onClick={() => onPage(p)} style={btnStyle(p === page)}>
            {p}
          </button>
        )
      )}
      <button
        onClick={() => onPage(page + 1)}
        disabled={page >= totalPages}
        style={{ ...btnStyle(false), opacity: page >= totalPages ? 0.4 : 1 }}
      >
        ›
      </button>
    </div>
  );
}

export default DataTable;
