import React, { useRef } from "react";
import { Search, X } from "lucide-react";
import {
  NAVY, BRD, BRDH, WARM, WHITE, NAVY_08, NAVY_20, NAVY_40,
  TEXT_PRIMARY, TEXT_STRONG, TEXT_TERTIARY, TEXT_MUTED, RADIUS_MD, RADIUS_FULL,
} from "@/lib/tokens";

/**
 * SearchBar — unified search input.
 *
 * Props:
 *   value          string
 *   onChange       function(value: string)
 *   placeholder    string
 *   size           "sm" | "md" | "lg"
 *   onClear        function        — If provided, shows X button when value is non-empty
 *   onKeyDown      function
 *   autoFocus      bool
 *   className      string
 */
export function SearchBar({
  value = "",
  onChange,
  placeholder = "Search…",
  size = "md",
  onClear,
  onKeyDown,
  autoFocus,
  className = "",
  style = {},
}) {
  const inputRef = useRef(null);
  const heights = { sm: 30, md: 36, lg: 40 };
  const fontSizes = { sm: "0.78rem", md: "0.82rem", lg: "0.875rem" };
  const iconSizes = { sm: 13, md: 14, lg: 15 };
  const h = heights[size] || heights.md;
  const fs = fontSizes[size] || fontSizes.md;
  const is = iconSizes[size] || iconSizes.md;

  return (
    <div
      className={className}
      style={{
        position: "relative",
        display: "flex",
        alignItems: "center",
        ...style,
      }}
    >
      <Search
        size={is}
        style={{
          position: "absolute",
          left: size === "sm" ? 9 : 11,
          color: value ? TEXT_TERTIARY : TEXT_MUTED,
          pointerEvents: "none",
          transition: "color 150ms",
        }}
      />
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        autoFocus={autoFocus}
        style={{
          height: h,
          width: "100%",
          paddingLeft: size === "sm" ? 30 : 34,
          paddingRight: value && onClear ? 34 : 12,
          fontSize: fs,
          color: TEXT_PRIMARY,
          background: WHITE,
          border: `1px solid ${BRD}`,
          borderRadius: RADIUS_MD,
          outline: "none",
          transition: "border-color 150ms, box-shadow 150ms",
          fontFamily: "inherit",
        }}
        onFocus={(e) => {
          e.target.style.borderColor = NAVY_40;
          e.target.style.boxShadow = `0 0 0 3px ${NAVY_08}`;
        }}
        onBlur={(e) => {
          e.target.style.borderColor = BRD;
          e.target.style.boxShadow = "none";
        }}
      />
      {value && onClear && (
        <button
          onClick={() => { onClear(); inputRef.current?.focus(); }}
          style={{
            position: "absolute",
            right: 9,
            background: "none",
            border: "none",
            cursor: "pointer",
            color: TEXT_MUTED,
            padding: 2,
            display: "flex",
            alignItems: "center",
            transition: "color 150ms",
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = TEXT_STRONG; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = TEXT_MUTED; }}
          aria-label="Clear search"
        >
          <X size={12} />
        </button>
      )}
    </div>
  );
}

/**
 * FilterChip — small filter toggle pill.
 *
 * Props:
 *   label     string
 *   active    bool
 *   onClick   function
 *   count     number    — optional count badge
 */
export function FilterChip({ label, active, onClick, count }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        height: 28,
        padding: "0 10px",
        fontSize: "0.73rem",
        fontWeight: active ? 600 : 400,
        color: active ? NAVY : TEXT_TERTIARY,
        background: active ? NAVY_08 : WHITE,
        border: `1px solid ${active ? NAVY_20 : BRD}`,
        borderRadius: RADIUS_MD,
        cursor: "pointer",
        transition: "all 150ms",
        whiteSpace: "nowrap",
      }}
      onMouseEnter={(e) => {
        if (!active) {
          e.currentTarget.style.borderColor = BRDH;
          e.currentTarget.style.color = TEXT_STRONG;
        }
      }}
      onMouseLeave={(e) => {
        if (!active) {
          e.currentTarget.style.borderColor = BRD;
          e.currentTarget.style.color = TEXT_TERTIARY;
        }
      }}
    >
      {label}
      {count != null && (
        <span
          style={{
            fontSize: "0.65rem",
            fontWeight: 700,
            background: active ? NAVY : "#e2e8f0",
            color: active ? WHITE : TEXT_TERTIARY,
            borderRadius: RADIUS_FULL,
            padding: "0 5px",
            lineHeight: "18px",
          }}
        >
          {count}
        </span>
      )}
    </button>
  );
}

/**
 * FilterBar — search + filter chips row.
 *
 * Props:
 *   search       { value, onChange, placeholder }
 *   filters      [{ label, value, active, count }]
 *   onFilter     function(value)
 *   actions      ReactNode   — right-side actions
 */
export function FilterBar({ search, filters = [], onFilter, actions, className = "" }) {
  return (
    <div
      className={className}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        flexWrap: "wrap",
      }}
    >
      {search && (
        <SearchBar
          value={search.value}
          onChange={search.onChange}
          placeholder={search.placeholder || "Search…"}
          onClear={search.value ? () => search.onChange("") : undefined}
          style={{ width: search.width || 260, flexShrink: 0 }}
        />
      )}
      {filters.length > 0 && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {filters.map((f) => (
            <FilterChip
              key={f.value ?? f.label}
              label={f.label}
              active={f.active}
              count={f.count}
              onClick={() => onFilter?.(f.value ?? f.label)}
            />
          ))}
        </div>
      )}
      {actions && (
        <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
          {actions}
        </div>
      )}
    </div>
  );
}

export default SearchBar;
