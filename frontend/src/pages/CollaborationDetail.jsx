import React, { useCallback, useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { useAuth } from "../contexts/AuthContext";
import { Avatar } from "@/components/ds/Avatar";
import { toast } from "sonner";
import { userTypeLabel } from "../lib/userTypes";
import { NAVY } from "@/lib/tokens";
import { Spinner } from "@/components/ds/LoadingState";
import EmptyState from "@/components/ds/EmptyState";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Tag } from "@/components/ds/Tag";
import { Button } from "@/components/ds/Button";
import { Textarea } from "@/components/ds/Textarea";
import { Users } from "lucide-react";
import { ResearchLayout } from "@/layouts";

export default function CollaborationDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [collab, setCollab] = useState(null);
  const [message, setMessage] = useState("");
  const [applications, setApplications] = useState([]);
  const [applying, setApplying] = useState(false);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/collaborations/${id}`);
      setCollab(data);
      if (data.creator_id === user.id) {
        const apps = await api.get(`/collaborations/${id}/applications`);
        setApplications(apps.data);
      }
    } catch (e) {
      toast.error("Failed to load collaboration");
    }
  }, [id, user]);
  useEffect(() => { load(); }, [load]);

  const apply = async () => {
    if (!message.trim()) { toast.error("Add a short pitch message"); return; }
    setApplying(true);
    try {
      await api.post(`/collaborations/${id}/apply`, { message });
      toast.success("Application sent");
      setMessage("");
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to apply");
    } finally {
      setApplying(false);
    }
  };

  const decide = async (appId, decision) => {
    try {
      await api.post(`/collaborations/applications/${appId}/decide`, { decision });
      toast.success(`Application ${decision}`);
      load();
    } catch (e) { toast.error("Failed"); }
  };

  if (!collab) return <ResearchLayout title="Collaboration"><div className="flex items-center gap-2 p-8 text-sm text-slate-500"><Spinner size={14} /> Loading…</div></ResearchLayout>;

  const isOwner = collab.creator_id === user.id;

  return (
    <ResearchLayout title={collab.title} subtitle={collab.collab_type}>
    <div className="grid lg:grid-cols-12 gap-10">
      <div className="lg:col-span-8 space-y-8">
        <Link to="/collaborations" className="text-sm text-slate-500 hover:text-slate-900">← All collaborations</Link>

        <article className="prose prose-slate max-w-none">
          <p className="text-lg text-slate-700 leading-relaxed whitespace-pre-line">{collab.description}</p>
        </article>

        <section className="border-t border-slate-200 pt-8">
          <h2 className="overline mb-4">Skills needed</h2>
          <div className="flex flex-wrap gap-2">
            {(collab.skills_needed || []).map((s) => (
              <Tag key={s}>{s}</Tag>
            ))}
          </div>
        </section>

        {!isOwner && (
          <Card padding="lg" className="mt-6">
            <h2 className="font-serif text-2xl text-slate-900 mb-3">Apply to join</h2>
            <p className="text-sm text-slate-600 mb-4">Write a short pitch: what you bring, your relevant experience, your availability.</p>
            <Textarea
              data-testid={TID.collabApplyMessage}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={4}
              placeholder="I can contribute the survival analysis layer (R, lme4) and have run a 1,800-patient study on a similar dataset…"
            />
            <div className="mt-3 flex gap-3">
              <Button
                data-testid={TID.collabApplySubmit}
                onClick={apply}
                disabled={applying}
                loading={applying}
              >
                Submit application
              </Button>
              <Button
                variant="ghost"
                data-testid={TID.collabApplyBtn}
                onClick={() => navigate(`/messages/${collab.creator_id}`)}
              >
                Message creator
              </Button>
            </div>
          </Card>
        )}

        {isOwner && (
          <Card padding="lg">
            <h2 className="font-serif text-2xl text-slate-900 mb-2">Applications</h2>
            <p className="text-sm text-slate-600 mb-4">{applications.length} application{applications.length === 1 ? "" : "s"}</p>
            <div className="space-y-4">
              {applications.length === 0 && (
                <EmptyState icon={<Users />} title="No applications yet" size="sm" />
              )}
              {applications.map((a) => (
                <Card key={a.id} padding="md">
                  <div className="flex items-start gap-3">
                    <Avatar url={a.applicant?.avatar_url} name={a.applicant?.full_name} size={40} />
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold text-slate-900">{a.applicant?.full_name}</div>
                      <div className="text-xs text-slate-500">{userTypeLabel(a.applicant)} · {a.applicant?.institution}</div>
                      <p className="text-sm text-slate-700 mt-2">{a.message}</p>
                    </div>
                    <div className="flex flex-col gap-2">
                      {a.status === "pending" ? (
                        <>
                          <Button size="sm" onClick={() => decide(a.id, "accepted")}>Accept</Button>
                          <Button variant="ghost" size="sm" onClick={() => decide(a.id, "rejected")}>Reject</Button>
                        </>
                      ) : (
                        <Badge variant={a.status === "accepted" ? "success" : "neutral"} size="sm">{a.status}</Badge>
                      )}
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </Card>
        )}
      </div>

      <aside className="lg:col-span-4 space-y-6">
        <Card padding="lg">
          <div className="overline mb-3">Created by</div>
          <Link to={`/profile/${collab.creator?.id}`} className="flex items-center gap-3">
            <Avatar url={collab.creator?.avatar_url} name={collab.creator?.full_name} size={48} />
            <div>
              <div className="font-semibold text-slate-900">{collab.creator?.full_name}</div>
              <div className="text-xs text-slate-500">{collab.creator?.institution}</div>
            </div>
          </Link>
        </Card>
        <Card padding="lg" className="space-y-3">
          <Detail label="Research area" value={collab.research_area} />
          <Detail label="Team size" value={collab.team_size} />
          <Detail label="Duration" value={collab.duration} />
          <Detail label="Publication goal" value={collab.publication_goal || "—"} />
          <Detail label="Funding status" value={collab.funding_status || "—"} />
          <Detail label="Applications" value={collab.applications_count || 0} />
        </Card>
        {collab.project_id && (
          <Button as={Link} to={`/projects/${collab.project_id}`} variant="outline" className="w-full">
            Open project workspace →
          </Button>
        )}
        <Button
          data-testid={TID.openChatBtn}
          onClick={() => navigate("/messages", { state: { openContext: { type: "collaboration", id: collab.id } } })}
          className="w-full"
        >
          Open collaboration chat →
        </Button>
      </aside>
    </div>
    </ResearchLayout>
  );
}

function Detail({ label, value }) {
  return (
    <div className="flex items-baseline justify-between gap-3 text-sm">
      <span className="overline">{label}</span>
      <span className="text-slate-900 text-right truncate">{value}</span>
    </div>
  );
}
