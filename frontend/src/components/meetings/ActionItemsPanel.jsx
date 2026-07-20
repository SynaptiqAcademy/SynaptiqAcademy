import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ListChecks } from "lucide-react";
import { Badge } from "@/components/ds/Badge";
import { Checkbox } from "@/components/ds/Form";
import { EmptyState } from "@/components/ds/EmptyState";
import { ErrorState } from "@/components/ds/ErrorState";
import { SkeletonTable } from "@/components/ds/LoadingState";
import { FilterBar } from "@/components/ds/SearchBar";
import { useMeetingActionItems, updateActionItem } from "@/hooks/useMeetings";
import { BRD, TEXT_PRIMARY, TEXT_MUTED, TEXT_SECONDARY } from "@/lib/tokens";

const PRIORITY_VARIANT = { high: "danger", medium: "warning", low: "neutral" };
const STATUS_FILTERS = [
  { label: "Open", value: "open" },
  { label: "In progress", value: "in_progress" },
  { label: "Done", value: "done" },
  { label: "All", value: "" },
];

function formatDue(iso) {
  if (!iso) return "No due date";
  const d = new Date(iso);
  const overdue = d < new Date() && d.toDateString() !== new Date().toDateString();
  return { text: d.toLocaleDateString("en-US", { month: "short", day: "numeric" }), overdue };
}

/**
 * ActionItemsPanel — standalone Action Items panel across all meetings.
 */
export function ActionItemsPanel() {
  const [status, setStatus] = useState("open");
  const { data: items, loading, error, reload, setData } = useMeetingActionItems(status ? { status } : {});

  const toggleDone = async (item) => {
    const nextStatus = item.status === "done" ? "open" : "done";
    setData((prev) => prev.map((i) => (i.id === item.id ? { ...i, status: nextStatus } : i)));
    try {
      await updateActionItem(item.id, { status: nextStatus });
    } catch {
      reload();
    }
  };

  return (
    <div>
      <FilterBar
        filters={STATUS_FILTERS.map((f) => ({ ...f, active: status === f.value }))}
        onFilter={setStatus}
      />

      <div style={{ marginTop: 16 }}>
        {loading && <SkeletonTable rows={4} />}
        {!loading && error && <ErrorState message="Could not load action items" onRetry={reload} />}
        {!loading && !error && (!items || items.length === 0) && (
          <EmptyState
            icon={<ListChecks />}
            title="No action items"
            description="Action items extracted or added from your meetings will show up here."
          />
        )}
        {!loading && !error && items && items.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 1, border: `1px solid ${BRD}`, borderRadius: 8, overflow: "hidden" }}>
            {items.map((item) => {
              const due = formatDue(item.due_date);
              return (
                <div
                  key={item.id}
                  style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 14px", background: "#fff", borderBottom: `1px solid ${BRD}` }}
                >
                  <Checkbox checked={item.status === "done"} onChange={() => toggleDone(item)} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 13, fontWeight: 500, color: TEXT_PRIMARY,
                      textDecoration: item.status === "done" ? "line-through" : "none",
                      opacity: item.status === "done" ? 0.55 : 1,
                    }}>
                      {item.title}
                    </div>
                    {item.meeting && (
                      <Link to={`/meetings/${item.meeting.id}`} style={{ fontSize: 11.5, color: TEXT_MUTED, textDecoration: "none" }}>
                        {item.meeting.title}
                      </Link>
                    )}
                  </div>
                  <Badge variant={PRIORITY_VARIANT[item.priority] || "neutral"} size="sm">{item.priority}</Badge>
                  <span style={{ fontSize: 11.5, color: due.overdue && item.status !== "done" ? "#DC2626" : TEXT_SECONDARY, minWidth: 70, textAlign: "right" }}>
                    {due.text}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default ActionItemsPanel;
