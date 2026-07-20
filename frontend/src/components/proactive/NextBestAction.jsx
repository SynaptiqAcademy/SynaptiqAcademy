/**
 * NextBestAction — single highest-priority recommendation for the current page (Phase XXX).
 *
 * Placed on key pages (Today, Discover, Manuscripts, Grants, etc.) to surface
 * one actionable recommendation without overwhelming the user.
 *
 * Props:
 *   page   string  — current pathname, used for context filtering
 */

import React, { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ChevronRight, X, Sparkles } from "lucide-react";
import { getNextAction, dismissRec, acceptRec } from "../../services/proactiveEngine";
import { NAVY } from "@/lib/tokens";

const CAT_COLOR = {
  writing:       "#1D4ED8",
  publishing:    "#7C3AED",
  research:      "#0F2847",
  collaboration: "#047857",
  funding:       "#B45309",
  teaching:      "#0891B2",
  institution:   "#6D28D9",
  career:        "#DC2626",
  productivity:  "#475569",
};

export default function NextBestAction({ page }) {
  const { pathname } = useLocation();
  const target = page || pathname;

  const [action,    setAction]   = useState(null);
  const [dismissed, setDismissed] = useState(false);
  const [loaded,    setLoaded]   = useState(false);

  useEffect(() => {
    setDismissed(false);
    setLoaded(false);
    getNextAction(target).then(data => {
      setAction(data?.action || null);
      setLoaded(true);
    });
  }, [target]);

  if (!loaded || dismissed || !action) return null;

  const color = CAT_COLOR[action.category] || NAVY;

  const handleDismiss = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDismissed(true);
    await dismissRec(action.id);
  };

  const handleAccept = async () => {
    await acceptRec(action.id);
  };

  return (
    <div
      className="flex items-center gap-3 px-4 py-2.5 border mb-5 group"
      style={{ borderColor: color + "30", background: color + "06" }}
    >
      <Sparkles size={11} strokeWidth={1.5} style={{ color, flexShrink: 0 }} />
      <div className="flex-1 min-w-0">
        <span className="text-[12px] text-slate-700 font-medium">{action.title}</span>
        {action.description && (
          <span className="text-[11px] text-slate-400 ml-2 hidden sm:inline">{action.description}</span>
        )}
      </div>
      {action.action && (
        <Link
          to={action.action.route}
          onClick={handleAccept}
          className="flex items-center gap-1 text-[11px] font-semibold shrink-0 transition-colors no-underline"
          style={{ color }}
        >
          {action.action.label}
          <ChevronRight size={9} strokeWidth={2.5} />
        </Link>
      )}
      <button
        onClick={handleDismiss}
        className="text-slate-300 hover:text-slate-500 transition-colors p-0.5 shrink-0 opacity-0 group-hover:opacity-100"
        aria-label="Dismiss"
      >
        <X size={11} strokeWidth={1.5} />
      </button>
    </div>
  );
}
