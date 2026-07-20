import React from "react";
import { FileText, FolderOpen, Users, BookOpen, Trophy, Calendar } from "lucide-react";

const CATEGORY_CONFIG = {
  publishing:    { icon: FileText, color: "#6366F1", bg: "#EEF2FF", label: "Publishing" },
  research:      { icon: FolderOpen, color: "#3B82F6", bg: "#EFF6FF", label: "Research" },
  collaboration: { icon: Users, color: "#14B8A6", bg: "#F0FDFA", label: "Collaboration" },
  funding:       { icon: Trophy, color: "#F97316", bg: "#FFF7ED", label: "Funding" },
  teaching:      { icon: BookOpen, color: "#EC4899", bg: "#FDF2F8", label: "Teaching" },
  default:       { icon: Calendar, color: "#6B7280", bg: "#F9FAFB", label: "Other" },
};

function EventDot({ category }) {
  const cfg = CATEGORY_CONFIG[category] || CATEGORY_CONFIG.default;
  const Icon = cfg.icon;
  return (
    <div
      className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center"
      style={{ background: cfg.bg }}
    >
      <Icon size={11} color={cfg.color} />
    </div>
  );
}

function TimelineEvent({ event }) {
  return (
    <div className="flex gap-2.5 items-start">
      <EventDot category={event.category} />
      <div className="flex-1 min-w-0">
        <p className="text-[11px] font-medium text-slate-700 leading-snug truncate">{event.title}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-[9px] text-slate-400">{new Date(event.date).toLocaleDateString()}</span>
          {event.status && (
            <span className="text-[9px] px-1 py-0.5 rounded bg-slate-100 text-slate-500">{event.status}</span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function TwinTimeline({ timeline, loading }) {
  if (loading) {
    return <div className="text-center py-12 text-[11px] text-slate-400">Building timeline…</div>;
  }

  if (!timeline || !timeline.timeline?.length) {
    return (
      <div className="text-center py-12 text-[11px] text-slate-400">
        No timeline events yet. Start creating manuscripts, projects, or collaborations to build your research timeline.
      </div>
    );
  }

  const reversed = [...timeline.timeline].reverse();
  const cats = timeline.category_totals || {};

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(cats).map(([cat, count]) => {
          const cfg = CATEGORY_CONFIG[cat] || CATEGORY_CONFIG.default;
          const Icon = cfg.icon;
          return (
            <div key={cat} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg" style={{ background: cfg.bg }}>
              <Icon size={11} color={cfg.color} />
              <span className="text-[11px] font-medium" style={{ color: cfg.color }}>{count} {cfg.label}</span>
            </div>
          );
        })}
      </div>

      {/* Year groups */}
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-2.5 top-0 bottom-0 w-px bg-slate-200" />

        <div className="space-y-6 pl-8">
          {reversed.map((yearGroup, yi) => (
            <div key={yi}>
              <div className="relative -ml-8 mb-3">
                <div className="absolute -left-1.5 top-1 w-2.5 h-2.5 rounded-full bg-slate-300 border-2 border-white" />
                <span className="text-[12px] font-bold text-slate-600 ml-2">{yearGroup.year}</span>
                <span className="text-[10px] text-slate-400 ml-2">{yearGroup.event_count} events</span>
              </div>

              <div className="space-y-2.5">
                {(yearGroup.events || []).slice(0, 8).map((ev, i) => (
                  <TimelineEvent key={i} event={ev} />
                ))}
                {(yearGroup.events || []).length > 8 && (
                  <p className="text-[10px] text-slate-400">+{yearGroup.events.length - 8} more events</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="text-[10px] text-slate-400 text-center border-t border-slate-100 pt-3">
        {timeline.total_events} verified platform events
        {timeline.earliest_event && ` · since ${new Date(timeline.earliest_event).toLocaleDateString()}`}
      </div>
      <p className="text-[10px] text-slate-400 text-center">{timeline.policy_note}</p>
    </div>
  );
}
