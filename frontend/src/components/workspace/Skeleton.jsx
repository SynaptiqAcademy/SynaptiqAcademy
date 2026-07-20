import React from "react";
import { BRD, WHITE, NAVY, RADIUS_BASE } from "@/lib/tokens";

// Re-export the DS primitives so pages can import everything from @/components/workspace
export {
  Skeleton,
} from "@/components/ds/Skeleton";
export {
  SkeletonLine as SkeletonText,
  SkeletonCard,
} from "@/components/ds/LoadingState";

/**
 * WorkspaceSkeleton — full-page loading state that mirrors the WorkspaceLayout
 * visual rhythm: header → summary card → content+sidebar grid.
 *
 * Drop in as the return value while data is loading:
 *   if (loading) return <WorkspaceSkeleton />;
 *
 * Props:
 *   hasSidebar bool   — render the right-column skeleton (default: true)
 *   rows       number — number of content card rows (default: 3)
 */
export function WorkspaceSkeleton({ hasSidebar = true, rows = 3 }) {
  return (
    <div style={{ display: "flex", flexDirection: "column" }}>

      {/* Header zone */}
      <div
        style={{
          margin: "-24px -24px 0",
          padding: "20px 24px 20px",
          background: WHITE,
          borderBottom: `1px solid ${BRD}`,
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 16,
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <Bone w={180} h={20} />
          <Bone w={280} h={13} opacity={0.6} />
        </div>
        <Bone w={96} h={32} radius={6} />
      </div>

      {/* Summary card */}
      <div style={{ marginTop: 20 }}>
        <div
          style={{
            background: WHITE,
            border: `1px solid ${BRD}`,
            borderLeft: `3px solid rgba(15,40,71,0.15)`,
            borderRadius: RADIUS_BASE,
            padding: "14px 18px",
            display: "flex",
            gap: 24,
          }}
          aria-hidden="true"
          className="sq-skeleton"
        >
          {[100, 80, 90, 70].map((w, i) => (
            <div key={i} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <Bone w={w} h={22} />
              <Bone w={w * 0.7} h={11} opacity={0.5} />
            </div>
          ))}
        </div>
      </div>

      {/* Content grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: hasSidebar ? "minmax(0,1fr) 288px" : "minmax(0,1fr)",
          gap: "0 28px",
          marginTop: 24,
          alignItems: "start",
        }}
      >
        {/* Main column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Section header */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <Bone w={120} h={13} />
            {Array.from({ length: rows }).map((_, i) => (
              <ContentCardBone key={i} />
            ))}
          </div>
        </div>

        {/* Sidebar column */}
        {hasSidebar && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <SidebarCardBone h={110} />
            <SidebarCardBone h={90} />
            <SidebarCardBone h={130} />
          </div>
        )}
      </div>
    </div>
  );
}

// ── Internal shimmer bones ─────────────────────────────────────────────────

function Bone({ w, h = 14, radius = 4, opacity = 1 }) {
  return (
    <span
      className="sq-skeleton"
      aria-hidden="true"
      style={{
        display: "block",
        width: w,
        height: h,
        borderRadius: radius,
        opacity,
        flexShrink: 0,
      }}
    />
  );
}

function ContentCardBone() {
  return (
    <div
      style={{
        background: WHITE,
        border: `1px solid ${BRD}`,
        borderRadius: RADIUS_BASE,
        padding: "14px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
      aria-hidden="true"
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <Bone w={28} h={28} radius={6} />
        <div style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1 }}>
          <Bone w="60%" h={13} />
          <Bone w="40%" h={10} opacity={0.6} />
        </div>
        <Bone w={60} h={22} radius={4} opacity={0.5} />
      </div>
      <Bone w="100%" h={10} opacity={0.5} />
      <Bone w="80%" h={10} opacity={0.4} />
    </div>
  );
}

function SidebarCardBone({ h }) {
  return (
    <div
      style={{
        background: WHITE,
        border: `1px solid ${BRD}`,
        borderRadius: RADIUS_BASE,
        overflow: "hidden",
        height: h,
      }}
      aria-hidden="true"
      className="sq-skeleton"
    />
  );
}

export default WorkspaceSkeleton;
