import React, { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { WARM } from "@/lib/tokens";
import {
  Users, FolderOpen, BookOpen, Calendar, Coins,
  GraduationCap, ClipboardCheck, Building2,
  ChevronDown, ChevronUp, RefreshCw, X, Check,
  AlertCircle, ExternalLink, Bookmark, MessageSquare,
  UserPlus, Filter,
} from "lucide-react";
import { AIWorkspaceLayout } from "@/layouts";



// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(val) {
  if (val == null) return "—";
  return val;
}

function formatDate(iso) {
  if (!iso) return "No deadline";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function deadlineStatus(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (isNaN(d)) return null;
  const now = new Date();
  const diff = d - now;
  if (diff < 0) return "closed";
  if (diff < 7 * 24 * 60 * 60 * 1000) return "closing_soon";
  return "open";
}

function ScoreBadge({ score }) {
  if (score == null) return null;
  const pct = Math.round(score);
  const color =
    pct >= 80 ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
    pct >= 60 ? "bg-blue-50 text-blue-700 border-blue-200" :
                "bg-slate-100 text-slate-600 border-slate-200";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 text-xs font-semibold border ${color}`}>
      {pct}% Match
    </span>
  );
}

function QuartileBadge({ quartile }) {
  if (!quartile) return null;
  const colors = {
    Q1: "bg-emerald-100 text-emerald-700 border-emerald-200",
    Q2: "bg-blue-100 text-blue-700 border-blue-200",
    Q3: "bg-amber-100 text-amber-700 border-amber-200",
    Q4: "bg-slate-100 text-slate-600 border-slate-200",
  };
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 text-xs font-semibold border ${colors[quartile] || colors.Q4}`}>
      {quartile}
    </span>
  );
}

function StatusBadge({ label, color }) {
  const palette = {
    green:  "bg-emerald-50 text-emerald-700 border-emerald-200",
    blue:   "bg-blue-50 text-blue-700 border-blue-200",
    amber:  "bg-amber-50 text-amber-700 border-amber-200",
    red:    "bg-red-50 text-red-700 border-red-200",
    slate:  "bg-slate-100 text-slate-600 border-slate-200",
  };
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 text-xs border ${palette[color] || palette.slate}`}>
      {label}
    </span>
  );
}

function Chip({ label }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 text-xs bg-slate-100 text-slate-700">
      {label}
    </span>
  );
}

function ChipList({ items = [], max = 4 }) {
  const shown = items.slice(0, max);
  const rest = items.length - max;
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {shown.map((s) => <Chip key={s} label={s} />)}
      {rest > 0 && <Chip label={`+${rest} more`} />}
    </div>
  );
}

function Avatar({ url, name, size = 40 }) {
  const initials = (name || "??").split(" ").map((n) => n[0]).slice(0, 2).join("").toUpperCase();
  return (
    <div
      className="bg-slate-200 text-slate-700 flex items-center justify-center font-semibold flex-shrink-0 overflow-hidden"
      style={{ width: size, height: size, fontSize: size / 3 }}
    >
      {url ? <img src={url} alt="" className="w-full h-full object-cover" /> : initials}
    </div>
  );
}

function ExplanationToggle({ bullets = [] }) {
  const [open, setOpen] = useState(false);
  if (!bullets || bullets.length === 0) return null;
  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-xs text-slate-500 hover:text-[#0F2847] transition-colors"
      >
        Why recommended?
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
      {open && (
        <ul className="mt-2 space-y-1">
          {bullets.map((b, i) => (
            <li key={i} className="text-xs text-slate-600 flex items-start gap-1.5">
              <span className="text-[#0F2847] mt-0.5 flex-shrink-0">•</span>
              {b}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Skeleton card ─────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="border border-slate-200 bg-white p-5 animate-pulse">
      <div className="flex gap-3 mb-4">
        <div className="w-10 h-10 bg-slate-200 rounded-sm flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-slate-200 rounded w-2/3" />
          <div className="h-3 bg-slate-200 rounded w-1/2" />
        </div>
      </div>
      <div className="flex gap-2 mb-3">
        <div className="h-5 bg-slate-200 rounded w-16" />
        <div className="h-5 bg-slate-200 rounded w-20" />
        <div className="h-5 bg-slate-200 rounded w-14" />
      </div>
      <div className="h-3 bg-slate-200 rounded w-full mb-2" />
      <div className="h-3 bg-slate-200 rounded w-4/5" />
    </div>
  );
}

function EmptyState({ message }) {
  return (
    <div className="border border-dashed border-slate-300 bg-slate-50 p-10 text-center">
      <AlertCircle size={32} strokeWidth={1.5} className="text-slate-300 mx-auto mb-3" />
      <p className="text-slate-500 text-sm max-w-sm mx-auto">{message}</p>
      <Link to="/academic-passport" className="mt-4 inline-flex items-center gap-1.5 text-xs text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">
        Complete your profile <ExternalLink size={10} />
      </Link>
    </div>
  );
}

function ErrorCard({ message, onRetry }) {
  return (
    <div className="border border-red-200 bg-red-50 p-6 text-center">
      <AlertCircle size={24} strokeWidth={1.5} className="text-red-400 mx-auto mb-2" />
      <p className="text-red-700 text-sm mb-3">{message || "Failed to load recommendations."}</p>
      <button
        onClick={onRetry}
        className="text-xs border border-red-300 text-red-700 px-3 py-1.5 hover:bg-red-100 transition-colors"
      >
        Retry
      </button>
    </div>
  );
}

// ── Dismiss overlay ───────────────────────────────────────────────────────────

function useDismissedSet() {
  const [dismissed, setDismissed] = useState(new Set());
  const timers = useRef({});

  const dismiss = useCallback((id, onFinalRemove) => {
    setDismissed((prev) => new Set([...prev, `${id}:pending`]));
    timers.current[id] = setTimeout(() => {
      setDismissed((prev) => {
        const next = new Set(prev);
        next.delete(`${id}:pending`);
        next.add(`${id}:done`);
        return next;
      });
      onFinalRemove(id);
    }, 5000);
  }, []);

  const undo = useCallback((id) => {
    clearTimeout(timers.current[id]);
    setDismissed((prev) => {
      const next = new Set(prev);
      next.delete(`${id}:pending`);
      return next;
    });
  }, []);

  const isDismissedPending = (id) => dismissed.has(`${id}:pending`);

  return { isDismissedPending, dismiss, undo };
}

// ── Feedback poster ───────────────────────────────────────────────────────────

async function postFeedback({ rec_type, rec_id, action }) {
  try {
    await api.post("/recommendations/feedback", { recommendation_type: rec_type, target_id: rec_id, action });
  } catch (_) {
    // silent — don't break UI on feedback errors
  }
}

// ── Card action buttons ───────────────────────────────────────────────────────

function ActionBtn({ onClick, icon: Icon, label, variant = "secondary" }) {
  const base = "inline-flex items-center gap-1.5 px-3 py-1.5 text-xs transition-colors";
  const styles = {
    primary: "bg-[#0F2847] text-white hover:bg-slate-800",
    secondary: "border border-slate-300 text-slate-700 hover:border-[#0F2847] hover:text-[#0F2847]",
    danger: "border border-red-200 text-red-600 hover:bg-red-50",
  };
  return (
    <button onClick={onClick} className={`${base} ${styles[variant] || styles.secondary}`}>
      {Icon && <Icon size={12} strokeWidth={1.5} />}
      {label}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ── CARD COMPONENTS ───────────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────────────

function ResearcherCard({ item, onDismiss, onClickAction }) {
  const { isDismissedPending, dismiss, undo } = useDismissedSet();
  const pending = isDismissedPending(item.id);

  if (pending) {
    return (
      <div className="border border-slate-200 bg-slate-50 p-5 flex items-center justify-between">
        <span className="text-sm text-slate-400 italic">Recommendation dismissed</span>
        <button onClick={() => undo(item.id)} className="text-xs text-[#0F2847] hover:underline">
          Undo
        </button>
      </div>
    );
  }

  const explanation = item.explanation_bullets || item.explanation || [];
  const bullets = Array.isArray(explanation)
    ? explanation
    : typeof explanation === "object"
    ? Object.values(explanation).filter(Boolean)
    : [];

  return (
    <div className="border border-slate-200 bg-white p-5 hover:border-slate-300 transition-colors">
      <div className="flex items-start gap-3">
        <Avatar url={item.avatar_url} name={item.full_name} size={40} />
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-slate-900 truncate">{fmt(item.full_name)}</div>
          <div className="text-xs text-slate-500 truncate mt-0.5">
            {[item.role, item.institution, item.country].filter(Boolean).join(" · ")}
          </div>
          <ChipList items={item.research_areas || item.interests || []} max={4} />
          <div className="flex items-center gap-2 mt-2">
            <ScoreBadge score={item.score} />
          </div>
          <ExplanationToggle bullets={bullets} />
        </div>
      </div>
      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-100">
        <ActionBtn
          label="Connect"
          icon={UserPlus}
          variant="primary"
          onClick={() => onClickAction(item.id, "clicked")}
        />
        <ActionBtn
          label="View Profile"
          icon={ExternalLink}
          onClick={() => onClickAction(item.id, "clicked")}
        />
        <ActionBtn
          label="Dismiss"
          icon={X}
          variant="danger"
          onClick={() => {
            dismiss(item.id, onDismiss);
            onClickAction(item.id, "dismissed");
          }}
        />
      </div>
    </div>
  );
}

function ProjectCard({ item, onDismiss, onClickAction }) {
  const { isDismissedPending, dismiss, undo } = useDismissedSet();
  const pending = isDismissedPending(item.id);

  if (pending) {
    return (
      <div className="border border-slate-200 bg-slate-50 p-5 flex items-center justify-between">
        <span className="text-sm text-slate-400 italic">Recommendation dismissed</span>
        <button onClick={() => undo(item.id)} className="text-xs text-[#0F2847] hover:underline">Undo</button>
      </div>
    );
  }

  const bullets = item.explanation_bullets || [];
  const statusColor = item.status === "open" ? "green" : item.status === "completed" ? "slate" : "blue";

  return (
    <div className="border border-slate-200 bg-white p-5 hover:border-slate-300 transition-colors">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="font-semibold text-slate-900">{fmt(item.title)}</div>
        <ScoreBadge score={item.score} />
      </div>
      <div className="flex items-center gap-2 flex-wrap text-xs text-slate-500 mb-1">
        <span>{fmt(item.owner_name)}</span>
        {item.status && <StatusBadge label={item.status} color={statusColor} />}
        {item.member_count != null && <span>{item.member_count} members</span>}
      </div>
      <ChipList items={item.research_areas || []} max={4} />
      {item.description && (
        <p className="text-xs text-slate-600 mt-2 line-clamp-2 leading-relaxed">{item.description}</p>
      )}
      <ExplanationToggle bullets={bullets} />
      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-100">
        <ActionBtn label="View Project" icon={ExternalLink} variant="primary" onClick={() => onClickAction(item.id, "clicked")} />
        <ActionBtn label="Request to Join" icon={UserPlus} onClick={() => onClickAction(item.id, "clicked")} />
        <ActionBtn label="Dismiss" icon={X} variant="danger" onClick={() => { dismiss(item.id, onDismiss); onClickAction(item.id, "dismissed"); }} />
      </div>
    </div>
  );
}

function JournalCard({ item, onDismiss, onClickAction }) {
  const { isDismissedPending, dismiss, undo } = useDismissedSet();
  const pending = isDismissedPending(item.id);

  if (pending) {
    return (
      <div className="border border-slate-200 bg-slate-50 p-5 flex items-center justify-between">
        <span className="text-sm text-slate-400 italic">Recommendation dismissed</span>
        <button onClick={() => undo(item.id)} className="text-xs text-[#0F2847] hover:underline">Undo</button>
      </div>
    );
  }

  const bullets = item.explanation_bullets || [];
  const acceptColor = item.acceptance_rate === "High" ? "green" : item.acceptance_rate === "Low" ? "red" : "slate";

  return (
    <div className="border border-slate-200 bg-white p-5 hover:border-slate-300 transition-colors">
      <div className="font-semibold text-slate-900 mb-1">{fmt(item.title || item.name)}</div>
      <div className="flex items-center gap-2 flex-wrap text-xs text-slate-500 mb-1">
        <span>{fmt(item.publisher)}</span>
        <QuartileBadge quartile={item.quartile} />
        {item.open_access && <StatusBadge label="Open Access" color="green" />}
      </div>
      <ChipList items={item.subjects || item.research_areas || []} max={3} />
      <div className="flex items-center gap-2 mt-2">
        <ScoreBadge score={item.score} />
        {item.acceptance_rate && (
          <StatusBadge label={`Acceptance: ${item.acceptance_rate}`} color={acceptColor} />
        )}
      </div>
      <ExplanationToggle bullets={bullets} />
      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-100">
        <ActionBtn label="View Journal" icon={ExternalLink} variant="primary" onClick={() => onClickAction(item.id, "clicked")} />
        <ActionBtn label="Bookmark" icon={Bookmark} onClick={() => onClickAction(item.id, "bookmarked")} />
        <ActionBtn label="Dismiss" icon={X} variant="danger" onClick={() => { dismiss(item.id, onDismiss); onClickAction(item.id, "dismissed"); }} />
      </div>
    </div>
  );
}

function ConferenceCard({ item, onDismiss, onClickAction }) {
  const { isDismissedPending, dismiss, undo } = useDismissedSet();
  const pending = isDismissedPending(item.id);

  if (pending) {
    return (
      <div className="border border-slate-200 bg-slate-50 p-5 flex items-center justify-between">
        <span className="text-sm text-slate-400 italic">Recommendation dismissed</span>
        <button onClick={() => undo(item.id)} className="text-xs text-[#0F2847] hover:underline">Undo</button>
      </div>
    );
  }

  const bullets = item.explanation_bullets || [];
  const status = deadlineStatus(item.deadline);
  const statusConfig = {
    open:         { label: "Open", color: "green" },
    closing_soon: { label: "Closing Soon", color: "amber" },
    closed:       { label: "Closed", color: "red" },
  };
  const sc = statusConfig[status] || {};
  const topicColor = item.topic_fit === "Strong" ? "green" : item.topic_fit === "Moderate" ? "amber" : "blue";

  return (
    <div className="border border-slate-200 bg-white p-5 hover:border-slate-300 transition-colors">
      <div className="flex items-start justify-between gap-3 mb-1">
        <div className="font-semibold text-slate-900">{fmt(item.name || item.title)}</div>
        {item.rank && <StatusBadge label={item.rank} color="blue" />}
      </div>
      <div className="flex items-center gap-2 flex-wrap text-xs text-slate-500 mb-1">
        <span>{fmt(item.country)}</span>
        {item.format && <StatusBadge label={item.format} color="slate" />}
      </div>
      <ChipList items={item.research_areas || []} max={4} />
      <div className="flex items-center gap-2 mt-2 flex-wrap">
        <span className="text-xs text-slate-600">Deadline: {formatDate(item.deadline)}</span>
        {status && <StatusBadge label={sc.label} color={sc.color} />}
      </div>
      <div className="flex items-center gap-2 mt-1">
        <ScoreBadge score={item.score} />
        {item.topic_fit && <StatusBadge label={`Topic Fit: ${item.topic_fit}`} color={topicColor} />}
      </div>
      <ExplanationToggle bullets={bullets} />
      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-100">
        <ActionBtn label="View Conference" icon={ExternalLink} variant="primary" onClick={() => onClickAction(item.id, "clicked")} />
        <ActionBtn label="Bookmark" icon={Bookmark} onClick={() => onClickAction(item.id, "bookmarked")} />
        <ActionBtn label="Dismiss" icon={X} variant="danger" onClick={() => { dismiss(item.id, onDismiss); onClickAction(item.id, "dismissed"); }} />
      </div>
    </div>
  );
}

function GrantCard({ item, onDismiss, onClickAction }) {
  const { isDismissedPending, dismiss, undo } = useDismissedSet();
  const pending = isDismissedPending(item.id);

  if (pending) {
    return (
      <div className="border border-slate-200 bg-slate-50 p-5 flex items-center justify-between">
        <span className="text-sm text-slate-400 italic">Recommendation dismissed</span>
        <button onClick={() => undo(item.id)} className="text-xs text-[#0F2847] hover:underline">Undo</button>
      </div>
    );
  }

  const bullets = item.explanation_bullets || [];
  const hasAmount = item.amount_min != null || item.amount_max != null;
  const amountStr = hasAmount
    ? `€${(item.amount_min || 0).toLocaleString()} – €${(item.amount_max || 0).toLocaleString()}`
    : item.amount
    ? item.amount
    : null;
  const eligPct = item.eligibility_score != null ? Math.round(item.eligibility_score) : null;

  return (
    <div className="border border-slate-200 bg-white p-5 hover:border-slate-300 transition-colors">
      <div className="font-semibold text-slate-900 mb-1">{fmt(item.title)}</div>
      <div className="text-xs font-medium text-slate-700 mb-1">{fmt(item.sponsor || item.funder)}</div>
      {item.career_stages && item.career_stages.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {item.career_stages.map((s) => <StatusBadge key={s} label={s} color="blue" />)}
        </div>
      )}
      {amountStr && (
        <div className="text-xs text-slate-600 mb-1">Amount: <span className="font-medium">{amountStr}</span></div>
      )}
      <div className="text-xs text-slate-600 mb-2">Deadline: <span className="font-medium">{formatDate(item.deadline)}</span></div>
      <div className="flex items-center gap-2">
        <ScoreBadge score={item.score} />
        {eligPct != null && (
          <StatusBadge label={`Eligibility: ${eligPct}%`} color={eligPct >= 70 ? "green" : eligPct >= 40 ? "amber" : "red"} />
        )}
      </div>
      <ExplanationToggle bullets={bullets} />
      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-100">
        <ActionBtn label="View Grant" icon={ExternalLink} variant="primary" onClick={() => onClickAction(item.id, "clicked")} />
        <ActionBtn label="Apply Now" icon={Check} onClick={() => onClickAction(item.id, "clicked")} />
        <ActionBtn label="Dismiss" icon={X} variant="danger" onClick={() => { dismiss(item.id, onDismiss); onClickAction(item.id, "dismissed"); }} />
      </div>
    </div>
  );
}

function MentorCard({ item, onDismiss, onClickAction }) {
  const { isDismissedPending, dismiss, undo } = useDismissedSet();
  const pending = isDismissedPending(item.id);

  if (pending) {
    return (
      <div className="border border-slate-200 bg-slate-50 p-5 flex items-center justify-between">
        <span className="text-sm text-slate-400 italic">Recommendation dismissed</span>
        <button onClick={() => undo(item.id)} className="text-xs text-[#0F2847] hover:underline">Undo</button>
      </div>
    );
  }

  const bullets = item.explanation_bullets || [];

  return (
    <div className="border border-slate-200 bg-white p-5 hover:border-slate-300 transition-colors">
      <div className="flex items-start gap-3">
        <Avatar url={item.avatar_url} name={item.full_name} size={40} />
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-slate-900 truncate">{fmt(item.full_name)}</div>
          <div className="text-xs text-slate-500 truncate mt-0.5">
            {[item.role, item.institution].filter(Boolean).join(" · ")}
          </div>
          <ChipList items={item.research_areas || item.interests || []} max={3} />
          <div className="flex items-center gap-2 mt-2">
            <ScoreBadge score={item.score} />
            {item.publication_count != null && (
              <span className="text-xs text-slate-500">Publications: {item.publication_count}</span>
            )}
          </div>
          {item.mentorship_areas && item.mentorship_areas.length > 0 && (
            <div className="mt-2">
              <div className="text-xs text-slate-500 mb-1">Mentorship areas:</div>
              <div className="text-xs text-slate-700">{item.mentorship_areas.join(", ")}</div>
            </div>
          )}
          <ExplanationToggle bullets={bullets} />
        </div>
      </div>
      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-100">
        <ActionBtn label="View Profile" icon={ExternalLink} variant="primary" onClick={() => onClickAction(item.id, "clicked")} />
        <ActionBtn label="Send Message" icon={MessageSquare} onClick={() => onClickAction(item.id, "clicked")} />
        <ActionBtn label="Dismiss" icon={X} variant="danger" onClick={() => { dismiss(item.id, onDismiss); onClickAction(item.id, "dismissed"); }} />
      </div>
    </div>
  );
}

function ReviewerCard({ item, onClickAction }) {
  const bullets = item.explanation_bullets || [];

  return (
    <div className="border border-slate-200 bg-white p-5 hover:border-slate-300 transition-colors">
      <div className="flex items-start gap-3">
        <Avatar url={item.avatar_url} name={item.full_name} size={40} />
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-slate-900 truncate">{fmt(item.full_name)}</div>
          <div className="text-xs text-slate-500 truncate mt-0.5">
            {[item.role, item.institution].filter(Boolean).join(" · ")}
          </div>
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <ScoreBadge score={item.score} />
            {item.no_coi !== false && (
              <StatusBadge label="No COI" color="green" />
            )}
          </div>
          {item.expertise && item.expertise.length > 0 && (
            <div className="mt-2 text-xs text-slate-600">
              Expertise: {item.expertise.slice(0, 3).join(", ")}
            </div>
          )}
          <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
            {item.publication_count != null && <span>Publications: {item.publication_count}</span>}
            {item.review_count != null && <span>Reviews: {item.review_count}</span>}
          </div>
          <ExplanationToggle bullets={bullets} />
        </div>
      </div>
      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-100">
        <ActionBtn label="Invite as Reviewer" icon={UserPlus} variant="primary" onClick={() => onClickAction(item.id, "clicked")} />
        <ActionBtn label="View Profile" icon={ExternalLink} onClick={() => onClickAction(item.id, "clicked")} />
      </div>
    </div>
  );
}

function InstitutionCard({ item, onClickAction }) {
  return (
    <div className="border border-slate-200 bg-white p-5 hover:border-slate-300 transition-colors">
      <div className="flex items-start gap-3 mb-2">
        <div className="w-10 h-10 bg-[#0F2847] text-white flex items-center justify-center flex-shrink-0">
          <Building2 size={18} strokeWidth={1.5} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-slate-900">{fmt(item.name)}</div>
          <div className="text-xs text-slate-500 mt-0.5">
            {[item.country, item.researcher_count != null ? `${item.researcher_count} researchers in your field` : null].filter(Boolean).join(" · ")}
          </div>
        </div>
      </div>
      <ChipList items={item.top_areas || item.research_areas || []} max={4} />
      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-100">
        <ActionBtn label="View Researchers" icon={Users} variant="primary" onClick={() => onClickAction(item.name, "clicked")} />
        <ActionBtn label="Connect with Institution" icon={Building2} onClick={() => onClickAction(item.name, "clicked")} />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ── TABS CONFIG ───────────────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────────────

const TABS = [
  {
    id: "researchers",
    label: "Researchers For You",
    icon: Users,
    endpoint: "/recommendations/researchers",
    dataKey: "recommendations",
    emptyMsg: "No researcher recommendations yet. Complete your profile to get personalized matches.",
  },
  {
    id: "projects",
    label: "Projects For You",
    icon: FolderOpen,
    endpoint: "/recommendations/projects",
    dataKey: "recommendations",
    emptyMsg: "No project recommendations yet. Add your research areas to see relevant projects.",
  },
  {
    id: "journals",
    label: "Journals For You",
    icon: BookOpen,
    endpoint: "/recommendations/journals",
    dataKey: "recommendations",
    emptyMsg: "No journal recommendations yet. Add publications to your profile for better matches.",
  },
  {
    id: "conferences",
    label: "Conferences For You",
    icon: Calendar,
    endpoint: "/recommendations/conferences",
    dataKey: "recommendations",
    emptyMsg: "No conference recommendations yet. Update your research interests to see relevant events.",
  },
  {
    id: "grants",
    label: "Grants For You",
    icon: Coins,
    endpoint: "/recommendations/grants",
    dataKey: "recommendations",
    emptyMsg: "No grant recommendations yet. Complete your career stage and research areas for funding matches.",
  },
  {
    id: "mentors",
    label: "Mentors For You",
    icon: GraduationCap,
    endpoint: "/recommendations/mentors",
    dataKey: "recommendations",
    emptyMsg: "No mentor recommendations yet. Tell us about your research goals to find the right mentors.",
  },
  {
    id: "reviewers",
    label: "Reviewers For You",
    icon: ClipboardCheck,
    endpoint: "/recommendations/reviewers",
    dataKey: "recommendations",
    emptyMsg: "No reviewer recommendations. You need an active manuscript or project to get reviewer suggestions.",
  },
  {
    id: "institutions",
    label: "Institutions For You",
    icon: Building2,
    endpoint: "/recommendations/researchers",
    dataKey: "recommendations",
    emptyMsg: "No institution recommendations yet. Complete your profile to find relevant academic institutions.",
    isInstitutionView: true,
  },
];

// ── Filter bar ────────────────────────────────────────────────────────────────

const RESEARCH_AREAS = [
  "", "Computer Science", "Medicine", "Physics", "Chemistry",
  "Biology", "Mathematics", "Engineering", "Social Sciences",
  "Economics", "Law", "Education", "Environmental Science",
  "Psychology", "Neuroscience", "Data Science", "AI & Machine Learning",
];

const COUNTRIES = [
  "", "US", "UK", "DE", "FR", "CA", "AU", "JP", "CN", "IN",
  "BR", "IT", "ES", "NL", "SE", "CH", "SG", "KR", "ZA", "RO",
];

const ROLES = [
  "", "PhD Student", "Postdoc", "Assistant Professor",
  "Associate Professor", "Full Professor", "Research Scientist", "Industry Researcher",
];

function SelectFilter({ label, value, onChange, options }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="text-xs border border-slate-300 bg-white text-slate-700 px-2 py-1.5 hover:border-slate-400 focus:outline-none focus:border-[#0F2847] transition-colors"
    >
      <option value="">{label}</option>
      {options.filter(Boolean).map((o) => (
        <option key={o} value={o}>{o}</option>
      ))}
    </select>
  );
}

function FilterBar({ tabId, filters, onChange, manuscripts }) {
  const set = (key) => (val) => onChange({ ...filters, [key]: val });

  if (tabId === "researchers") {
    return (
      <div className="flex items-center gap-2 flex-wrap">
        <Filter size={13} strokeWidth={1.5} className="text-slate-400" />
        <SelectFilter label="All Countries" value={filters.country || ""} onChange={set("country")} options={COUNTRIES} />
        <SelectFilter label="All Research Areas" value={filters.area || ""} onChange={set("area")} options={RESEARCH_AREAS} />
        <SelectFilter label="All Roles" value={filters.role || ""} onChange={set("role")} options={ROLES} />
      </div>
    );
  }
  if (tabId === "projects" || tabId === "conferences" || tabId === "grants" || tabId === "mentors") {
    return (
      <div className="flex items-center gap-2 flex-wrap">
        <Filter size={13} strokeWidth={1.5} className="text-slate-400" />
        <SelectFilter label="All Research Areas" value={filters.area || ""} onChange={set("area")} options={RESEARCH_AREAS} />
        {tabId === "conferences" && (
          <SelectFilter label="Deadline" value={filters.deadline_status || ""} onChange={set("deadline_status")} options={["open"]} />
        )}
      </div>
    );
  }
  if (tabId === "journals") {
    return (
      <div className="flex items-center gap-2 flex-wrap">
        <Filter size={13} strokeWidth={1.5} className="text-slate-400" />
        <label className="flex items-center gap-1.5 text-xs text-slate-600 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.open_access || false}
            onChange={(e) => onChange({ ...filters, open_access: e.target.checked })}
            className="rounded"
          />
          Open Access only
        </label>
        <SelectFilter label="All Quartiles" value={filters.quartile || ""} onChange={set("quartile")} options={["Q1", "Q2", "Q3", "Q4"]} />
      </div>
    );
  }
  if (tabId === "reviewers") {
    if (!manuscripts || manuscripts.length === 0) {
      return (
        <div className="text-xs text-slate-500 italic">
          Upload a manuscript to get reviewer suggestions tailored to your work.
        </div>
      );
    }
    return (
      <div className="flex items-center gap-2 flex-wrap">
        <Filter size={13} strokeWidth={1.5} className="text-slate-400" />
        <SelectFilter
          label="All Manuscripts"
          value={filters.manuscript_id || ""}
          onChange={set("manuscript_id")}
          options={manuscripts.map((m) => m.id || m.title)}
        />
      </div>
    );
  }
  return null;
}

// ── Client-side filter applier ────────────────────────────────────────────────

function applyFilters(items, tabId, filters) {
  if (!filters) return items;
  return items.filter((item) => {
    if (tabId === "researchers" || tabId === "mentors") {
      if (filters.country && item.country !== filters.country) return false;
      if (filters.area) {
        const areas = item.research_areas || item.interests || [];
        if (!areas.some((a) => a.toLowerCase().includes(filters.area.toLowerCase()))) return false;
      }
      if (filters.role && item.role !== filters.role) return false;
    }
    if (tabId === "journals") {
      if (filters.open_access && !item.open_access) return false;
      if (filters.quartile && item.quartile !== filters.quartile) return false;
    }
    if (tabId === "projects" || tabId === "conferences" || tabId === "grants") {
      if (filters.area) {
        const areas = item.research_areas || [];
        if (!areas.some((a) => a.toLowerCase().includes(filters.area.toLowerCase()))) return false;
      }
      if (tabId === "conferences" && filters.deadline_status === "open") {
        const s = deadlineStatus(item.deadline);
        if (s === "closed") return false;
      }
    }
    return true;
  });
}

// ── Group researchers by institution ─────────────────────────────────────────

function groupByInstitution(researchers) {
  const map = {};
  for (const r of researchers) {
    const inst = r.institution || "Unknown Institution";
    if (!map[inst]) {
      map[inst] = {
        name: inst,
        country: r.country || "",
        researcher_count: 0,
        top_areas: [],
        _area_set: new Set(),
      };
    }
    map[inst].researcher_count += 1;
    (r.research_areas || r.interests || []).forEach((a) => {
      if (!map[inst]._area_set.has(a)) {
        map[inst]._area_set.add(a);
        map[inst].top_areas.push(a);
      }
    });
  }
  return Object.values(map).sort((a, b) => b.researcher_count - a.researcher_count);
}

// ─────────────────────────────────────────────────────────────────────────────
// ── MAIN PAGE ─────────────────────────────────────────────────────────────────
// ─────────────────────────────────────────────────────────────────────────────

export default function Recommendations() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState(TABS[0]);
  const [dataByTab, setDataByTab] = useState({});
  const [loadingByTab, setLoadingByTab] = useState({});
  const [errorByTab, setErrorByTab] = useState({});
  const [filters, setFilters] = useState({});
  const [manuscripts, setManuscripts] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshDisabled, setRefreshDisabled] = useState(false);
  const refreshTimerRef = useRef(null);

  // Fetch manuscripts for reviewer tab
  useEffect(() => {
    api.get("/manuscripts").then((r) => {
      setManuscripts(Array.isArray(r.data) ? r.data : r.data?.manuscripts || []);
    }).catch(() => setManuscripts([]));
  }, []);

  const fetchTab = useCallback(async (tab, forceRefresh = false) => {
    const tid = tab.id;
    setLoadingByTab((prev) => ({ ...prev, [tid]: true }));
    setErrorByTab((prev) => ({ ...prev, [tid]: null }));
    try {
      const params = {};
      if (forceRefresh) params.force_refresh = true;
      const res = await api.get(tab.endpoint, { params });
      const raw = res.data;
      const items = raw[tab.dataKey] || raw.data || raw || [];
      setDataByTab((prev) => ({ ...prev, [tid]: Array.isArray(items) ? items : [] }));
    } catch (err) {
      const msg = err?.response?.data?.detail || "Failed to load recommendations.";
      setErrorByTab((prev) => ({ ...prev, [tid]: typeof msg === "string" ? msg : "Failed to load." }));
    } finally {
      setLoadingByTab((prev) => ({ ...prev, [tid]: false }));
    }
  }, []);

  // Fetch active tab on mount + tab switch
  useEffect(() => {
    if (!dataByTab[activeTab.id] && !loadingByTab[activeTab.id]) {
      fetchTab(activeTab);
    }
  }, [activeTab, dataByTab, loadingByTab, fetchTab]);

  // Cleanup refresh timer on unmount
  useEffect(() => {
    return () => { if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current); };
  }, []);

  const handleRefresh = async () => {
    if (refreshDisabled) return;
    setRefreshing(true);
    setRefreshDisabled(true);
    await fetchTab(activeTab, true);
    setRefreshing(false);
    refreshTimerRef.current = setTimeout(() => setRefreshDisabled(false), 30000);
  };

  const handleDismiss = useCallback(async (itemId, tabId) => {
    await postFeedback({ rec_type: tabId, rec_id: String(itemId), action: "dismissed" });
    setDataByTab((prev) => ({
      ...prev,
      [tabId]: (prev[tabId] || []).filter((item) => String(item.id) !== String(itemId)),
    }));
  }, []);

  const handleClickAction = useCallback(async (itemId, tabId, action) => {
    await postFeedback({ rec_type: tabId, rec_id: String(itemId), action });
  }, []);

  const rawItems = dataByTab[activeTab.id] || [];
  const filteredItems = applyFilters(rawItems, activeTab.id, filters);
  const institutionItems = activeTab.isInstitutionView ? groupByInstitution(rawItems) : [];
  const displayItems = activeTab.isInstitutionView ? institutionItems : filteredItems;

  const isLoading = loadingByTab[activeTab.id];
  const error = errorByTab[activeTab.id];

  return (
    <AIWorkspaceLayout>
    <div className="bg-[#F4F6FA]" style={{ margin: "-24px" }}>
      {/* ── Sticky header ─────────────────────────────────── */}
      <header className="sticky top-0 z-30 border-b border-slate-200 px-6 pt-3 pb-4" style={{ background: "#F4F6FA" }}>
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4 mt-3">
          <div>
            <div className="overline text-[#0F2847]">AI-Powered</div>
            <h1 className="font-serif text-2xl text-slate-900 leading-tight">Academic Recommendations</h1>
            <p className="text-xs text-slate-500 mt-0.5">Personalized for your research profile</p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshDisabled}
            className="inline-flex items-center gap-2 border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:border-[#0F2847] hover:text-[#0F2847] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw size={14} strokeWidth={1.5} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Refreshing…" : refreshDisabled ? "Refresh (wait 30s)" : "Refresh Recommendations"}
          </button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto flex gap-0">
        {/* ── Left sidebar tabs ──────────────────────────────── */}
        <aside className="w-64 shrink-0 border-r border-slate-200 bg-white min-h-[calc(100vh-73px)] sticky top-[73px]">
          <nav className="py-4">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = tab.id === activeTab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => { setActiveTab(tab); setFilters({}); }}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-sm text-left transition-colors ${
                    isActive
                      ? "bg-[#0F2847] text-white"
                      : "text-slate-700 hover:bg-slate-50 hover:text-[#0F2847]"
                  }`}
                >
                  <Icon size={16} strokeWidth={1.5} className="flex-shrink-0" />
                  <span className="leading-tight">{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </aside>

        {/* ── Main content area ──────────────────────────────── */}
        <main className="flex-1 min-w-0 p-6">
          {/* Sub-header with filter bar */}
          <div className="flex items-center justify-between gap-4 mb-5 pb-4 border-b border-slate-200">
            <div>
              <h2 className="font-serif text-xl text-slate-900">{activeTab.label}</h2>
              {!isLoading && !error && (
                <div className="text-xs text-slate-500 mt-0.5">
                  {displayItems.length} recommendation{displayItems.length !== 1 ? "s" : ""}
                </div>
              )}
            </div>
            <div className="flex-shrink-0">
              <FilterBar
                tabId={activeTab.id}
                filters={filters}
                onChange={setFilters}
                manuscripts={manuscripts}
              />
            </div>
          </div>

          {/* Content */}
          {isLoading ? (
            <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
            </div>
          ) : error ? (
            <ErrorCard message={error} onRetry={() => fetchTab(activeTab)} />
          ) : displayItems.length === 0 ? (
            <EmptyState message={activeTab.emptyMsg} />
          ) : (
            <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {activeTab.id === "researchers" && displayItems.map((item) => (
                <ResearcherCard
                  key={item.id}
                  item={item}
                  onDismiss={(id) => handleDismiss(id, activeTab.id)}
                  onClickAction={(id, action) => handleClickAction(id, activeTab.id, action)}
                />
              ))}
              {activeTab.id === "projects" && displayItems.map((item) => (
                <ProjectCard
                  key={item.id}
                  item={item}
                  onDismiss={(id) => handleDismiss(id, activeTab.id)}
                  onClickAction={(id, action) => handleClickAction(id, activeTab.id, action)}
                />
              ))}
              {activeTab.id === "journals" && displayItems.map((item) => (
                <JournalCard
                  key={item.id || item.title}
                  item={item}
                  onDismiss={(id) => handleDismiss(id, activeTab.id)}
                  onClickAction={(id, action) => handleClickAction(id, activeTab.id, action)}
                />
              ))}
              {activeTab.id === "conferences" && displayItems.map((item) => (
                <ConferenceCard
                  key={item.id}
                  item={item}
                  onDismiss={(id) => handleDismiss(id, activeTab.id)}
                  onClickAction={(id, action) => handleClickAction(id, activeTab.id, action)}
                />
              ))}
              {activeTab.id === "grants" && displayItems.map((item) => (
                <GrantCard
                  key={item.id}
                  item={item}
                  onDismiss={(id) => handleDismiss(id, activeTab.id)}
                  onClickAction={(id, action) => handleClickAction(id, activeTab.id, action)}
                />
              ))}
              {activeTab.id === "mentors" && displayItems.map((item) => (
                <MentorCard
                  key={item.id}
                  item={item}
                  onDismiss={(id) => handleDismiss(id, activeTab.id)}
                  onClickAction={(id, action) => handleClickAction(id, activeTab.id, action)}
                />
              ))}
              {activeTab.id === "reviewers" && displayItems.map((item) => (
                <ReviewerCard
                  key={item.id}
                  item={item}
                  onClickAction={(id, action) => handleClickAction(id, activeTab.id, action)}
                />
              ))}
              {activeTab.id === "institutions" && displayItems.map((item, i) => (
                <InstitutionCard
                  key={item.name || i}
                  item={item}
                  onClickAction={(id, action) => handleClickAction(id, activeTab.id, action)}
                />
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
    </AIWorkspaceLayout>
  );
}
