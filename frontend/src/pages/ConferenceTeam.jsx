import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { useAuth } from "../contexts/AuthContext";
import { Users, Plus, X, Layers, Check, Clock } from "lucide-react";
import { ResearchLayout } from "@/layouts";
import { Card } from "@/components/ds/Card";
import { Button } from "@/components/ds/Button";
import { Input } from "@/components/ds/Input";
import { Avatar } from "@/components/ds/Avatar";
import { Badge } from "@/components/ds/Badge";
import { SkeletonCard } from "@/components/ds/LoadingState";

export default function ConferenceTeam() {
  const { teamId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [team, setTeam] = useState(null);
  const [error, setError] = useState(null);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviting, setInviting] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/conference-teams/${teamId}`);
      setTeam(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Team not found.");
    }
  }, [teamId]);

  useEffect(() => { load(); }, [load]);

  const isLead = team && user && team.lead_user_id === user.id;

  const invite = async () => {
    if (!inviteEmail.trim()) return;
    setInviting(true);
    try {
      const { data: found } = await api.get(`/users/search?q=${encodeURIComponent(inviteEmail)}`).catch(() => ({ data: [] }));
      const target = Array.isArray(found) ? found[0] : null;
      if (!target) { toast.error("User not found."); return; }
      await api.post(`/conference-teams/${teamId}/invite`, { to_user_id: target.id, role: "co_author" });
      toast.success("Invitation sent.");
      setInviteEmail("");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not send invitation.");
    } finally {
      setInviting(false);
    }
  };

  const removeMember = async (uid) => {
    try {
      await api.delete(`/conference-teams/${teamId}/members/${uid}`);
      toast.success("Removed.");
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not remove member.");
    }
  };

  if (error) {
    return (
      <ResearchLayout title="Team not found">
        <div className="text-sm text-slate-500">
          {error} <Link to="/conferences" className="underline">Back to conferences</Link>
        </div>
      </ResearchLayout>
    );
  }
  if (!team) return <ResearchLayout title="Submission Team"><SkeletonCard rows={4} /></ResearchLayout>;

  return (
    <ResearchLayout
      title={team.title}
      subtitle={
        <span className="inline-flex items-center gap-2">
          Submission team <Badge variant={team.status === "forming" ? "warning" : "success"} size="sm">{team.status}</Badge>
        </span>
      }
      actions={
        <Button as={Link} to={`/conferences/${team.conference_id}`} variant="ghost" size="sm">
          ← Back to conference
        </Button>
      }
    >
      <div className="max-w-3xl space-y-6">
      {team.description && <p className="text-sm text-slate-600">{team.description}</p>}

      {team.workspace_id && (
        <Card padding="sm" className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-slate-700">
            <Layers size={14} strokeWidth={1.5} className="text-[#0F2847]" />
            Shared workspace ready — write and coordinate the submission here.
          </div>
          <Button as={Link} to={`/workspaces/${team.workspace_id}`} size="sm" variant="outline">
            Open Workspace
          </Button>
        </Card>
      )}

      <Card padding="sm">
        <div className="overline mb-3">Team members ({(team.members || []).length})</div>
        <div className="space-y-2">
          {(team.members || []).map((m) => (
            <div key={m.user_id} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-b-0">
              <div className="flex items-center gap-3">
                <Avatar url={m.avatar_url} name={m.user_name} size={32} />
                <div>
                  <div className="text-sm font-medium text-slate-900">{m.user_name || "Unknown"}</div>
                  <div className="text-xs text-slate-500">{m.role === "lead" ? "Lead" : "Co-Author"} · {m.institution}</div>
                </div>
              </div>
              {(isLead || m.user_id === user?.id) && m.role !== "lead" && (
                <Button onClick={() => removeMember(m.user_id)} variant="ghost" size="icon" aria-label="Remove member" className="!text-slate-400 hover:!text-rose-600">
                  <X size={13} strokeWidth={1.5} />
                </Button>
              )}
            </div>
          ))}
        </div>
      </Card>

      {isLead && (
        <Card padding="sm">
          <div className="overline mb-3">Invite a co-author</div>
          <div className="flex gap-2">
            <Input
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="Search by name or email"
              onKeyDown={(e) => e.key === "Enter" && invite()}
            />
            <Button onClick={invite} disabled={inviting} loading={inviting} size="sm">
              <Plus size={12} strokeWidth={2} />
              Invite
            </Button>
          </div>
        </Card>
      )}
      </div>
    </ResearchLayout>
  );
}
