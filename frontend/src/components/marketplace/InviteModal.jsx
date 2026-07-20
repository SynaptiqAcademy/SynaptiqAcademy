/**
 * InviteModal — invite a researcher to a collaboration / workspace / project /
 * manuscript / expertise request.
 */
import React, { useState } from "react";
import api from "../../lib/api";
import { toast } from "sonner";
import { X, Loader2, UserPlus } from "lucide-react";
import { userTypeLabel } from "../../lib/userTypes";
import { NAVY } from "@/lib/tokens";

const KINDS = [
  { value: "collaboration",              label: "Research Collaboration" },
  { value: "project",                    label: "Project Invitation" },
  { value: "workspace",                  label: "Workspace Invitation" },
  { value: "manuscript",                 label: "Manuscript Invitation" },
  { value: "grant_team",                 label: "Grant Team Invitation" },
  { value: "conference_team",            label: "Conference Team Invitation" },
  { value: "reviewer",                   label: "Reviewer Invitation" },
  { value: "mentorship",                 label: "Mentorship Invitation" },
  { value: "institutional_collaboration", label: "Institutional Collaboration" },
  { value: "expertise_request",          label: "Expertise Request" },
];

const ENTITY_KINDS = new Set(["workspace", "project", "manuscript", "expertise_request"]);

const DURATION_OPTIONS = [
  "", "Less than 1 month", "1–3 months", "3–6 months", "6–12 months", "More than 1 year", "Ongoing",
];

export default function InviteModal({ target, onClose, defaultKind = "collaboration", entityId }) {
  const [kind, setKind] = useState(defaultKind);
  const [eid, setEid] = useState(entityId || "");
  const [role, setRole] = useState("");
  const [message, setMessage] = useState("");
  const [contribution, setContribution] = useState("");
  const [duration, setDuration] = useState("");
  const [busy, setBusy] = useState(false);

  if (!target) return null;
  const u = target.user || target;

  const send = async () => {
    if (!message.trim()) { toast.error("Add a short message"); return; }
    setBusy(true);
    try {
      await api.post("/marketplace/invite", {
        target_user_id: u.id,
        kind,
        entity_id: ENTITY_KINDS.has(kind) ? (eid || null) : null,
        role: role || null,
        message: message.trim(),
        expected_contribution: contribution.trim() || null,
        estimated_duration: duration || null,
      });
      toast.success(`Invitation sent to ${u.full_name}`);
      onClose?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-[100] bg-slate-900/50 flex items-center justify-center px-4" onClick={onClose} data-testid="invite-modal">
      <div className="bg-white w-full max-w-lg border border-slate-200 max-h-[90vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="border-b border-slate-200 px-5 py-4 flex items-start justify-between shrink-0">
          <div>
            <div className="overline">Collaboration Invitation</div>
            <h3 className="font-serif text-xl text-slate-900 mt-0.5">Invite {u.full_name}</h3>
            <div className="text-xs text-slate-500 mt-0.5">
              {[userTypeLabel(u), u.institution].filter(Boolean).join(" · ")}
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-900"><X size={16} strokeWidth={1.5} /></button>
        </div>
        <div className="p-5 space-y-4 overflow-y-auto flex-1">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <div className="overline mb-2">Invitation type</div>
              <select
                data-testid="invite-kind"
                value={kind} onChange={(e) => setKind(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
              >
                {KINDS.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}
              </select>
            </div>
            <div>
              <div className="overline mb-2">Role / expertise needed</div>
              <input
                data-testid="invite-role"
                value={role} onChange={(e) => setRole(e.target.value)}
                placeholder="co-author, statistician, reviewer…"
                className="w-full px-3 py-2 border border-slate-300 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
              />
            </div>
          </div>
          {ENTITY_KINDS.has(kind) && (
            <div>
              <div className="overline mb-2">{kind === "expertise_request" ? "Request" : kind.charAt(0).toUpperCase() + kind.slice(1)} ID <span className="text-slate-400">(optional)</span></div>
              <input
                data-testid="invite-entity-id"
                value={eid} onChange={(e) => setEid(e.target.value)}
                placeholder={`Paste the ${kind} ID, or leave empty`}
                className="w-full px-3 py-2 border border-slate-300 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847] font-mono"
              />
            </div>
          )}
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <div className="overline mb-2">Expected contribution <span className="text-slate-400">(optional)</span></div>
              <input
                data-testid="invite-contribution"
                value={contribution} onChange={(e) => setContribution(e.target.value)}
                placeholder="Data analysis, writing, review…"
                className="w-full px-3 py-2 border border-slate-300 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
              />
            </div>
            <div>
              <div className="overline mb-2">Estimated duration</div>
              <select
                data-testid="invite-duration"
                value={duration} onChange={(e) => setDuration(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
              >
                {DURATION_OPTIONS.map((d) => <option key={d} value={d}>{d || "Not specified"}</option>)}
              </select>
            </div>
          </div>
          <div>
            <div className="overline mb-2">Personal message <span className="text-[#8A1538]">*</span></div>
            <textarea
              data-testid="invite-message"
              rows={4}
              value={message} onChange={(e) => setMessage(e.target.value)}
              placeholder="Explain the research context, why you're reaching out, and what collaboration could look like."
              className="w-full px-3 py-2 border border-slate-300 text-sm focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
            />
            <div className="text-[10px] text-slate-400 mt-1">Expires in 30 days if not accepted.</div>
          </div>
        </div>
        <div className="border-t border-slate-200 px-5 py-3 flex items-center justify-end gap-2 shrink-0">
          <button onClick={onClose} className="text-xs text-slate-600 hover:text-slate-900 px-3 py-2">Cancel</button>
          <button
            data-testid="invite-submit"
            disabled={busy || !message.trim()}
            onClick={send}
            className="text-xs bg-[#0F2847] text-white px-4 py-2 hover:bg-slate-800 disabled:opacity-50 inline-flex items-center gap-1.5"
          >
            {busy ? <Loader2 size={11} className="animate-spin" /> : <UserPlus size={11} strokeWidth={1.5} />}
            Send invitation
          </button>
        </div>
      </div>
    </div>
  );
}
