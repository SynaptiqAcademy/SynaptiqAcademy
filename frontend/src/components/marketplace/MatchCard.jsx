/**
 * MatchCard — compact researcher card for marketplace results.
 *
 * Props:
 *   match: { user, score, components, shared_areas, shared_keywords, shared_skills,
 *            reputation, llm_score, explanation }
 *   onInvite(user), onView(user)
 */
import React from "react";
import { Link } from "react-router-dom";
import ReputationBadge from "./ReputationBadge";
import OrcidBadge from "../orcid/OrcidBadge";
import {
  Sparkles, MapPin, Building2, BookOpen, Briefcase, MessageSquare, UserPlus, ExternalLink,
} from "lucide-react";
import { userTypeLabel } from "../../lib/userTypes";
import { NAVY } from "@/lib/tokens";

const AVAIL_TONE = {
  available: "border-emerald-300 bg-emerald-50 text-emerald-800",
  selective: "border-amber-300 bg-amber-50 text-amber-800",
  not_available: "border-slate-200 bg-slate-50 text-slate-500",
};

export default function MatchCard({ match, onInvite, onMessage, compact = false }) {
  const u = match.user || {};
  const reranked = match.llm_score != null;
  const score = Math.round(reranked ? match.llm_score : match.score);
  const initials = (u.full_name || "").split(" ").map((s) => s[0]).filter(Boolean).slice(0, 2).join("").toUpperCase();

  return (
    <div className="border border-slate-200 bg-white p-5 hover:border-[#0F2847] transition-colors group" data-testid={`match-card-${u.id}`}>
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div className="w-12 h-12 shrink-0 bg-[#0F2847] text-white font-serif text-xl flex items-center justify-center">
          {u.avatar_url
            ? <img src={u.avatar_url} alt="" className="w-full h-full object-cover" />
            : initials || "?"}
        </div>

        <div className="flex-1 min-w-0">
          {/* Name + score */}
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <Link
                to={`/profile/${u.id}`}
                data-testid={`match-name-${u.id}`}
                className="font-serif text-lg text-slate-900 hover:text-[#0F2847] truncate block"
              >
                {u.full_name || "Researcher"}
                {u.orcid?.orcid_id && u.orcid?.verified_at && (
                  <span className="ml-2 align-middle"><OrcidBadge orcidId={u.orcid.orcid_id} testId={`orcid-${u.id}`} /></span>
                )}
              </Link>
              <div className="text-xs text-slate-500 mt-0.5 inline-flex items-center gap-2 flex-wrap">
                {userTypeLabel(u) && (
                  <span className="inline-flex items-center gap-1"><Briefcase size={10} strokeWidth={1.5} /> {userTypeLabel(u)}</span>
                )}
                {u.institution && (
                  <span className="inline-flex items-center gap-1"><Building2 size={10} strokeWidth={1.5} /> {u.institution}</span>
                )}
                {u.country && (
                  <span className="inline-flex items-center gap-1"><MapPin size={10} strokeWidth={1.5} /> {u.country}</span>
                )}
              </div>
            </div>
            <div className="shrink-0 text-right">
              <div className={`inline-flex flex-col items-end gap-1 ${reranked ? "" : ""}`}>
                <span className={`font-serif text-2xl ${reranked ? "text-amber-700" : "text-[#0F2847]"}`} data-testid={`match-score-${u.id}`}>
                  {score}
                  {reranked && <Sparkles size={11} strokeWidth={1.5} className="inline ml-1 -mt-1" />}
                </span>
                <span className="overline text-slate-500">{reranked ? "AI score" : "Match"}</span>
              </div>
            </div>
          </div>

          {/* Availability + reputation */}
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            {u.availability && (
              <span className={`overline border px-1.5 py-0.5 ${AVAIL_TONE[u.availability] || AVAIL_TONE.selective}`}>
                {u.availability.replace("_", " ")}
              </span>
            )}
            {match.reputation && <ReputationBadge reputation={match.reputation} compact testId={`rep-compact-${u.id}`} />}
            {match.collab_history_count > 0 && (
              <span className="overline border border-[#0F2847]/30 bg-[#0F2847]/5 text-[#0F2847] px-1.5 py-0.5">
                {match.collab_history_count} prior collab{match.collab_history_count > 1 ? "s" : ""}
              </span>
            )}
          </div>

          {/* Shared signals */}
          {!compact && (match.shared_areas?.length > 0 || match.shared_keywords?.length > 0) && (
            <div className="mt-3 text-xs">
              <div className="overline mb-1">Overlap</div>
              <div className="flex flex-wrap gap-1">
                {(match.shared_areas || []).slice(0, 4).map((a, i) => (
                  <span key={`a-${i}`} className="border border-[#0F2847]/30 bg-[#0F2847]/5 text-[#0F2847] px-2 py-0.5 text-[11px]">{a}</span>
                ))}
                {(match.shared_keywords || []).slice(0, 4).map((k, i) => (
                  <span key={`k-${i}`} className="border border-slate-200 bg-slate-50 text-slate-700 px-2 py-0.5 text-[11px]">{k}</span>
                ))}
              </div>
            </div>
          )}

          {/* AI explanation when reranked */}
          {match.explanation && (
            <div className="mt-3 bg-amber-50 border-l-2 border-amber-400 px-3 py-2 text-xs text-slate-800 font-serif italic">
              {match.explanation}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2 mt-3">
            <button
              data-testid={`match-invite-${u.id}`}
              onClick={() => onInvite?.(match)}
              className="inline-flex items-center gap-1.5 text-xs bg-[#0F2847] text-white px-3 py-1.5 hover:bg-slate-800"
            >
              <UserPlus size={11} strokeWidth={1.5} /> Invite
            </button>
            <button
              data-testid={`match-message-${u.id}`}
              onClick={() => onMessage?.(match)}
              className="inline-flex items-center gap-1.5 text-xs border border-slate-300 px-3 py-1.5 hover:border-[#0F2847] hover:text-[#0F2847]"
            >
              <MessageSquare size={11} strokeWidth={1.5} /> Message
            </button>
            <Link
              to={`/profile/${u.id}`}
              className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-[#0F2847] ml-auto"
            >
              View profile <ExternalLink size={10} strokeWidth={1.5} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
