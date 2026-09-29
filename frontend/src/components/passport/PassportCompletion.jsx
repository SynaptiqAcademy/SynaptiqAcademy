import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, ChevronDown, ChevronUp, ArrowRight } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { ProgressRing } from "@/components/ds/Progress";
import { NAVY, EMERALD, BRD, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED } from "@/lib/tokens";

/**
 * PassportCompletion — P1 Phase 7C4.1's "Build your Academic Passport"
 * guided experience, replacing the old scattered "35/100" rings +
 * "N steps remaining" caption repeated across the hero, right rail, and
 * Research tab. ONE canonical completion source
 * (services/profile_completion.py::compute_profile_completion(), read via
 * GET /users/me/profile-completion) drives everything here — no second
 * calculation.
 *
 * Groups are an honest relabeling of the real 11 canonical items
 * (avatar/biography/institution/keywords/methods/social/availability/
 * orcid_connected/publications/employment/education) into 4 categories a
 * user can scan — not invented categories the backend doesn't track.
 */
const GROUPS = [
  { title: "Identity", keys: ["avatar", "biography", "institution"] },
  { title: "Research Profile", keys: ["keywords", "methods", "availability"] },
  { title: "Academic Connections", keys: ["orcid_connected", "social"] },
  { title: "Research Record", keys: ["publications", "employment", "education"] },
];

// Items whose backend `action` points at a page ("/profile", "/settings")
// that either navigates away from the Passport unnecessarily (identity
// fields, which EditIdentityModal already edits in place) or no longer
// hosts the actual control at all ("/settings" — ORCID connect/sync moved
// into the Passport's own Research tab in P1 Phase 7C4.1, so it left behind
// a dead destination). These are handled directly instead of navigating
// (P1 Phase 7C4.3 §6/§2).
const IDENTITY_KEYS = new Set(["avatar", "biography", "institution", "keywords", "methods", "social", "availability"]);
const ORCID_DEPENDENT_KEYS = new Set(["publications", "employment", "education"]);

function CompletionItem({ item, onEditIdentity, onConnectOrcid, onSyncOrcid, orcidConnected, orcidConfigured = true }) {
  const navigate = useNavigate();
  const orcidKeyBlocked = !orcidConfigured && !orcidConnected &&
    (item.key === "orcid_connected" || ORCID_DEPENDENT_KEYS.has(item.key));
  const handleClick = () => {
    if (!item.action || orcidKeyBlocked) return;
    if (IDENTITY_KEYS.has(item.key)) return onEditIdentity?.();
    if (item.key === "orcid_connected") return onConnectOrcid?.();
    if (ORCID_DEPENDENT_KEYS.has(item.key)) return orcidConnected ? onSyncOrcid?.() : onConnectOrcid?.();
    navigate(item.action);
  };
  return (
    <button
      onClick={handleClick}
      disabled={item.earned || orcidKeyBlocked}
      title={orcidKeyBlocked ? "ORCID connect is pending admin setup" : undefined}
      style={{
        display: "flex", alignItems: "center", gap: 10, width: "100%", padding: "8px 4px",
        border: "none", background: "none", cursor: (item.earned || orcidKeyBlocked) ? "default" : "pointer", textAlign: "left",
        borderRadius: 6, opacity: (item.earned || orcidKeyBlocked) ? 0.7 : 1,
      }}
      onMouseEnter={(e) => { if (!item.earned && !orcidKeyBlocked) e.currentTarget.style.background = "#F8FAFC"; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
    >
      <span style={{
        width: 18, height: 18, borderRadius: "50%", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center",
        background: item.earned ? EMERALD : "transparent", border: item.earned ? "none" : `1.5px solid ${BRD}`,
      }}>
        {item.earned && <Check size={12} style={{ color: "#fff" }} />}
      </span>
      <span style={{ fontSize: 13, color: item.earned ? TEXT_SECONDARY : TEXT_PRIMARY, flex: 1, textDecoration: item.earned ? "line-through" : "none" }}>
        {item.label}
      </span>
      {!item.earned && item.action_label && (
        orcidKeyBlocked ? (
          <span style={{ fontSize: 11, color: TEXT_SECONDARY, fontStyle: "italic", flexShrink: 0 }}>Pending admin setup</span>
        ) : (
          <span style={{ fontSize: 11.5, fontWeight: 600, color: NAVY, flexShrink: 0, display: "flex", alignItems: "center", gap: 2 }}>
            {item.action_label} <ArrowRight size={11} />
          </span>
        )
      )}
    </button>
  );
}

export function PassportCompletion({ completion, onEditIdentity, onConnectOrcid, onSyncOrcid, orcidConnected, orcidConfigured = true }) {
  const [expanded, setExpanded] = useState(false);
  if (!completion) return null;

  const items = completion.items || [];
  const byKey = Object.fromEntries(items.map((i) => [i.key, i]));
  const pct = completion.percentage ?? 0;

  if (pct >= 100) {
    return (
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ width: 36, height: 36, borderRadius: "50%", background: EMERALD, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <Check size={18} style={{ color: "#fff" }} />
          </span>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: TEXT_PRIMARY }}>Academic Passport complete</div>
            <div style={{ fontSize: 12.5, color: TEXT_SECONDARY, marginTop: 2 }}>Every canonical Passport field is filled in.</div>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card padding="lg">
      <div style={{ display: "flex", alignItems: "center", gap: 16, cursor: "pointer" }} onClick={() => setExpanded((v) => !v)}>
        <ProgressRing value={pct} max={100} size="md" colorByValue />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: TEXT_PRIMARY }}>Build your Academic Passport</div>
          <div style={{ fontSize: 12.5, color: TEXT_SECONDARY, marginTop: 2 }}>
            {pct}% complete — {items.filter((i) => !i.earned).length} step{items.filter((i) => !i.earned).length === 1 ? "" : "s"} remaining
          </div>
        </div>
        <button
          aria-expanded={expanded}
          aria-label={expanded ? "Collapse Passport steps" : "Expand Passport steps"}
          style={{ background: "none", border: "none", cursor: "pointer", color: TEXT_MUTED, flexShrink: 0 }}
        >
          {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
      </div>

      {expanded && (
        <div style={{ marginTop: 18, paddingTop: 16, borderTop: `1px solid ${BRD}`, display: "flex", flexDirection: "column", gap: 16 }}>
          {GROUPS.map((group) => {
            const groupItems = group.keys.map((k) => byKey[k]).filter(Boolean);
            if (!groupItems.length) return null;
            return (
              <div key={group.title}>
                <div style={{ fontSize: 10.5, fontWeight: 700, color: TEXT_MUTED, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>
                  {group.title}
                </div>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  {groupItems.map((item) => (
                    <CompletionItem
                      key={item.key} item={item}
                      onEditIdentity={onEditIdentity} onConnectOrcid={onConnectOrcid}
                      onSyncOrcid={onSyncOrcid} orcidConnected={orcidConnected} orcidConfigured={orcidConfigured}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

export default PassportCompletion;
