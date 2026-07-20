import React from "react";
import { Search, Grid3X3, List, SlidersHorizontal, ChevronDown } from "lucide-react";
import {
  NAVY,
  BRD,
  WHITE,
  WARM,
  RADIUS_BASE,
  TEXT_SECONDARY,
  TEXT_MUTED,
} from "@/lib/tokens";

/**
 * PageToolbar — unified filter / search / view-toggle strip.
 *
 * Two usage modes:
 *
 * 1. Structured (default):
 *    <PageToolbar
 *      search={q} onSearch={setQ}
 *      left={<FilterButton ... />}
 *      right={<ViewToggle ... />}
 *      count={42} label="manuscripts"
 *    />
 *
 * 2. Custom (children override everything):
 *    <PageToolbar>
 *      <MyFilterChip />
 *      <MySort />
 *    </PageToolbar>
 */
export function PageToolbar({
  // Structured mode
  search,
  onSearch,
  left,
  right,
  count,
  label = "results",
  // Custom mode
  children,
}) {
  if (children) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        {children}
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 8,
        flexWrap: "wrap",
        width: "100%",
      }}
    >
      {/* Left: search + filter controls */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        {onSearch != null && (
          <SearchInput value={search || ""} onChange={onSearch} />
        )}
        {left}
      </div>

      {/* Right: count + sort/view controls */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {count != null && (
          <span
            style={{
              fontSize: "0.72rem",
              color: TEXT_MUTED,
              whiteSpace: "nowrap",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {count.toLocaleString()} {label}
          </span>
        )}
        {right}
      </div>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────

/**
 * SearchInput — styled search input with icon.
 */
export function SearchInput({ value = "", onChange, placeholder = "Search…", width = 200 }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        background: WARM,
        border: `1px solid ${BRD}`,
        borderRadius: RADIUS_BASE,
        padding: "5px 10px",
        minWidth: width,
        transition: "border-color 150ms ease",
      }}
      onFocusCapture={(e) => {
        e.currentTarget.style.borderColor = NAVY;
      }}
      onBlurCapture={(e) => {
        e.currentTarget.style.borderColor = BRD;
      }}
    >
      <Search size={12} style={{ color: TEXT_MUTED, flexShrink: 0 }} />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        placeholder={placeholder}
        style={{
          border: "none",
          outline: "none",
          background: "transparent",
          fontSize: "0.78rem",
          color: "#374151",
          flex: 1,
          minWidth: 0,
        }}
      />
    </div>
  );
}

/**
 * ViewToggle — grid / list switcher.
 */
export function ViewToggle({ view = "grid", onChange }) {
  const Btn = ({ v, Icon }) => (
    <button
      onClick={() => onChange?.(v)}
      aria-pressed={view === v}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: 28,
        height: 28,
        border: "none",
        cursor: "pointer",
        background: view === v ? NAVY : "transparent",
        color: view === v ? WHITE : TEXT_MUTED,
        borderRadius: 4,
        transition: "background 120ms ease, color 120ms ease",
      }}
    >
      <Icon size={12} />
    </button>
  );

  return (
    <div
      style={{
        display: "flex",
        border: `1px solid ${BRD}`,
        borderRadius: RADIUS_BASE,
        overflow: "hidden",
        background: WHITE,
      }}
    >
      <Btn v="grid" Icon={Grid3X3} />
      <Btn v="list" Icon={List} />
    </div>
  );
}

/**
 * FilterButton — a toggle-able filter chip.
 */
export function FilterButton({ label, active = false, onClick, count }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        padding: "4px 10px",
        height: 30,
        borderRadius: RADIUS_BASE,
        border: `1px solid ${active ? NAVY : BRD}`,
        background: active ? "rgba(15,40,71,0.07)" : WHITE,
        color: active ? NAVY : TEXT_SECONDARY,
        fontSize: "0.75rem",
        fontWeight: active ? 600 : 400,
        cursor: "pointer",
        whiteSpace: "nowrap",
        transition: "all 120ms ease",
      }}
      onMouseEnter={(e) => {
        if (!active) e.currentTarget.style.borderColor = "#94a3b8";
      }}
      onMouseLeave={(e) => {
        if (!active) e.currentTarget.style.borderColor = BRD;
      }}
    >
      <SlidersHorizontal size={11} />
      {label}
      {count != null && count > 0 && (
        <span
          style={{
            background: NAVY,
            color: WHITE,
            borderRadius: 999,
            padding: "1px 5px",
            fontSize: "0.63rem",
            fontWeight: 700,
            lineHeight: 1.5,
          }}
        >
          {count}
        </span>
      )}
    </button>
  );
}

/**
 * SortSelect — lightweight sort dropdown.
 */
export function SortSelect({ value, onChange, options = [] }) {
  return (
    <div style={{ position: "relative", display: "inline-flex", alignItems: "center" }}>
      <select
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        style={{
          appearance: "none",
          WebkitAppearance: "none",
          padding: "4px 26px 4px 10px",
          height: 30,
          borderRadius: RADIUS_BASE,
          border: `1px solid ${BRD}`,
          background: WHITE,
          color: TEXT_SECONDARY,
          fontSize: "0.75rem",
          cursor: "pointer",
          outline: "none",
        }}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown
        size={10}
        style={{
          position: "absolute",
          right: 8,
          top: "50%",
          transform: "translateY(-50%)",
          color: TEXT_MUTED,
          pointerEvents: "none",
        }}
      />
    </div>
  );
}

/**
 * TabFilter — horizontal pill-style tab group.
 */
export function TabFilter({ tabs = [], active, onChange }) {
  return (
    <div
      style={{
        display: "flex",
        gap: 2,
        background: WARM,
        border: `1px solid ${BRD}`,
        borderRadius: RADIUS_BASE,
        padding: 2,
      }}
    >
      {tabs.map((tab) => (
        <button
          key={tab.value}
          onClick={() => onChange?.(tab.value)}
          style={{
            padding: "3px 10px",
            borderRadius: 4,
            border: "none",
            fontSize: "0.72rem",
            fontWeight: active === tab.value ? 600 : 400,
            color: active === tab.value ? NAVY : TEXT_MUTED,
            background: active === tab.value ? WHITE : "transparent",
            cursor: "pointer",
            whiteSpace: "nowrap",
            boxShadow: active === tab.value ? "0 1px 2px rgba(15,23,42,0.08)" : "none",
            transition: "all 120ms ease",
          }}
        >
          {tab.label}
          {tab.count != null && (
            <span
              style={{
                marginLeft: 5,
                fontSize: "0.63rem",
                color: active === tab.value ? "#64748b" : TEXT_MUTED,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

export default PageToolbar;
