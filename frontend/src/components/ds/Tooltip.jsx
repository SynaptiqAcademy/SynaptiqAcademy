/* eslint-disable */
import React, { useState, useRef, useCallback } from "react";
import { WHITE, Z, RADIUS_SM } from "@/lib/tokens";

// ── Tooltip ───────────────────────────────────────────────────────────────────
/**
 * Tooltip — hover tooltip anchored to a single child element.
 * Rendered via a fixed-position div relative to the viewport.
 *
 * Props:
 *   content    string | ReactNode   tooltip text
 *   placement  "top"|"bottom"|"left"|"right"   default "top"
 *   delay      number   show delay in ms, default 400
 *   children   ReactElement   must be exactly one child
 */
export function Tooltip({ content, children, placement = "top", delay = 400 }) {
  const [visible, setVisible] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });
  const timer = useRef(null);
  const triggerRef = useRef(null);

  const show = useCallback(() => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      const el = triggerRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const GAP = 8;
      let top, left;

      if (placement === "top") {
        top  = r.top - GAP;
        left = r.left + r.width / 2;
      } else if (placement === "bottom") {
        top  = r.bottom + GAP;
        left = r.left + r.width / 2;
      } else if (placement === "left") {
        top  = r.top + r.height / 2;
        left = r.left - GAP;
      } else {
        top  = r.top + r.height / 2;
        left = r.right + GAP;
      }

      setCoords({ top, left });
      setVisible(true);
    }, delay);
  }, [placement, delay]);

  const hide = useCallback(() => {
    clearTimeout(timer.current);
    setVisible(false);
  }, []);

  const TRANSFORMS = {
    top:    "translate(-50%, -100%)",
    bottom: "translate(-50%, 0%)",
    left:   "translate(-100%, -50%)",
    right:  "translate(0%, -50%)",
  };

  const child = React.Children.only(children);

  return (
    <>
      {React.cloneElement(child, {
        ref: (node) => {
          triggerRef.current = node;
          // Forward existing ref if present
          const { ref } = child;
          if (typeof ref === "function") ref(node);
          else if (ref) ref.current = node;
        },
        onMouseEnter: (e) => { show(); child.props.onMouseEnter?.(e); },
        onMouseLeave: (e) => { hide(); child.props.onMouseLeave?.(e); },
        onFocus:      (e) => { show(); child.props.onFocus?.(e); },
        onBlur:       (e) => { hide(); child.props.onBlur?.(e); },
      })}

      {visible && content && (
        <div
          role="tooltip"
          style={{
            position: "fixed",
            top: coords.top,
            left: coords.left,
            transform: TRANSFORMS[placement] ?? TRANSFORMS.top,
            background: "#1e293b",
            color: WHITE,
            fontSize: "0.75rem",
            fontWeight: 500,
            lineHeight: 1.45,
            padding: "5px 9px",
            borderRadius: RADIUS_SM,
            boxShadow: "0 4px 12px rgba(0,0,0,0.2)",
            pointerEvents: "none",
            whiteSpace: "nowrap",
            zIndex: Z.tooltip,
            maxWidth: 240,
            animation: "sq-fade-in 100ms ease",
          }}
        >
          {content}
        </div>
      )}
    </>
  );
}
