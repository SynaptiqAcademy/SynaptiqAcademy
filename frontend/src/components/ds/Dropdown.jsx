/* eslint-disable */
import React, { createContext, useContext, useState, useRef, useEffect } from "react";
import { BRD, TEXT_PRIMARY, TEXT_MUTED, WARM, WHITE, CRIMSON, RADIUS_LG, SHADOW_DROPDOWN, Z } from "@/lib/tokens";

const DropdownCtx = createContext(null);

// ── Dropdown ──────────────────────────────────────────────────────────────────
/**
 * Dropdown — popover menu anchored to a trigger element.
 *
 * Props:
 *   trigger  ReactElement   the button/element that opens the menu
 *   align    "left"|"right" default "left"
 *   width    number|string  default 180
 *   children DropdownItem / DropdownSeparator / DropdownLabel
 */
export function Dropdown({ trigger, children, align = "left", width = 180, style }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const menuRef = useRef(null);
  const triggerRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // Menu items get focus once the menu mounts, then arrow keys move a
  // roving focus among them per the ARIA APG menu-button pattern — without
  // this, keyboard/screen-reader users can open a menu but can't operate it.
  useEffect(() => {
    if (!open) return;
    const items = () => Array.from(menuRef.current?.querySelectorAll('[role="menuitem"]:not(:disabled)') || []);
    items()[0]?.focus();

    const keyHandler = (e) => {
      if (e.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
        return;
      }
      const list = items();
      if (!list.length) return;
      const idx = list.indexOf(document.activeElement);
      if (e.key === "ArrowDown") {
        e.preventDefault();
        list[(idx + 1) % list.length]?.focus();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        list[(idx - 1 + list.length) % list.length]?.focus();
      } else if (e.key === "Home") {
        e.preventDefault();
        list[0]?.focus();
      } else if (e.key === "End") {
        e.preventDefault();
        list[list.length - 1]?.focus();
      }
    };
    document.addEventListener("keydown", keyHandler);
    return () => document.removeEventListener("keydown", keyHandler);
  }, [open]);

  const close = () => setOpen(false);
  const toggle = (e) => { e.stopPropagation(); setOpen(o => !o); };

  return (
    <DropdownCtx.Provider value={{ close }}>
      <div ref={ref} style={{ position: "relative", display: "inline-block" }}>
        {React.isValidElement(trigger)
          ? React.cloneElement(trigger, {
              onClick: toggle,
              ref: (node) => {
                triggerRef.current = node;
                const { ref: origRef } = trigger;
                if (typeof origRef === "function") origRef(node);
                else if (origRef) origRef.current = node;
              },
              "aria-haspopup": "menu",
              "aria-expanded": open,
            })
          : trigger}

        {open && (
          <div
            ref={menuRef}
            role="menu"
            style={{
              position: "absolute",
              top: "calc(100% + 6px)",
              [align === "right" ? "right" : "left"]: 0,
              width,
              background: WHITE,
              border: `1px solid ${BRD}`,
              borderRadius: RADIUS_LG,
              boxShadow: SHADOW_DROPDOWN,
              zIndex: Z.dropdown,
              padding: "4px 0",
              animation: "sq-slide-up 120ms cubic-bezier(0.16,1,0.3,1)",
              ...style,
            }}
          >
            {children}
          </div>
        )}
      </div>
    </DropdownCtx.Provider>
  );
}

// ── DropdownItem ──────────────────────────────────────────────────────────────
/**
 * DropdownItem — single menu row.
 *
 * Props:
 *   children     label text
 *   icon         Lucide icon component
 *   onClick      fn   also closes the menu
 *   shortcut     string   shown on right (e.g. "⌘K")
 *   destructive  bool     red text
 *   disabled     bool
 */
export function DropdownItem({ children, icon: Icon, onClick, shortcut, destructive, disabled, style }) {
  const ctx = useContext(DropdownCtx);
  const [hov, setHov] = useState(false);
  const color = destructive ? CRIMSON : TEXT_PRIMARY;

  return (
    <button
      role="menuitem"
      onClick={() => { if (!disabled) { onClick?.(); ctx?.close(); } }}
      disabled={disabled}
      style={{
        display: "flex", alignItems: "center", gap: 8,
        width: "100%", padding: "7px 12px",
        border: "none",
        background: hov && !disabled ? WARM : "transparent",
        cursor: disabled ? "not-allowed" : "pointer",
        color: disabled ? TEXT_MUTED : color,
        fontSize: "0.875rem", fontWeight: 400,
        textAlign: "left",
        transition: "background 120ms",
        opacity: disabled ? 0.5 : 1,
        ...style,
      }}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
    >
      {Icon && <Icon size={14} style={{ flexShrink: 0, opacity: 0.7 }} />}
      <span style={{ flex: 1 }}>{children}</span>
      {shortcut && (
        <kbd style={{
          fontSize: "0.6875rem", color: TEXT_MUTED,
          fontFamily: "inherit", background: "none",
        }}>
          {shortcut}
        </kbd>
      )}
    </button>
  );
}

// ── DropdownSeparator ─────────────────────────────────────────────────────────

export function DropdownSeparator({ style }) {
  return <div style={{ height: 1, background: BRD, margin: "4px 0", ...style }} />;
}

// ── DropdownLabel ─────────────────────────────────────────────────────────────

export function DropdownLabel({ children, style }) {
  return (
    <div style={{
      padding: "5px 12px 4px",
      fontSize: "0.6875rem", fontWeight: 700,
      letterSpacing: "0.06em", textTransform: "uppercase",
      color: TEXT_MUTED,
      ...style,
    }}>
      {children}
    </div>
  );
}

// ── DropdownGroup ─────────────────────────────────────────────────────────────

export function DropdownGroup({ children, style }) {
  return <div style={{ padding: "0", ...style }}>{children}</div>;
}
