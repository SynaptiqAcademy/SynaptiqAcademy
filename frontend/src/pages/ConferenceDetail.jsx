import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../lib/api";
import { toast } from "sonner";
import { ExternalLink, CalendarDays, MapPin, Clock, Bookmark, BookmarkCheck, Users } from "lucide-react";
import { NAVY } from "@/lib/tokens";
import { SkeletonCard } from "@/components/ds/LoadingState";
import { Button } from "@/components/ds/Button";
import { ResearchLayout } from "@/layouts";

function dateRow(label, value) {
  if (!value) return null;
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-100 last:border-b-0">
      <span className="text-sm text-slate-600">{label}</span>
      <span className="font-mono text-sm text-slate-900">{value}</span>
    </div>
  );
}

export default function ConferenceDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [c, setC] = useState(null);
  const [myTeam, setMyTeam] = useState(undefined); // undefined = loading, null = none
  const [formingTeam, setFormingTeam] = useState(false);

  useEffect(() => { api.get(`/conferences/${id}`).then((r) => setC(r.data)).catch(() => setC({error: true})); }, [id]);
  useEffect(() => {
    api.get("/conference-teams/mine")
      .then((r) => setMyTeam((r.data?.teams || []).find((t) => t.conference_id === id) || null))
      .catch(() => setMyTeam(null));
  }, [id]);

  const formTeam = async () => {
    setFormingTeam(true);
    try {
      const res = await api.post("/conference-teams", { conference_id: id, title: c?.name });
      navigate(`/conference-teams/${res.data.id}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not form a team.");
    } finally {
      setFormingTeam(false);
    }
  };

  if (!c) return <ResearchLayout title="Conference"><SkeletonCard rows={4} /></ResearchLayout>;
  if (c.error) return (
    <ResearchLayout title="Conference not found">
      <div className="text-sm text-slate-500">Conference not found. <Link to="/conferences" className="underline">Back</Link></div>
    </ResearchLayout>
  );

  const state = c.deadline_state || "unknown";
  const STATE_TONE = {
    open: "border-emerald-300 bg-emerald-50 text-emerald-700",
    closing_soon: "border-amber-300 bg-amber-50 text-amber-700",
    closed: "border-slate-300 bg-slate-50 text-slate-600",
    unknown: "border-slate-300 bg-slate-50 text-slate-600",
  };

  return (
    <ResearchLayout title={c.name} subtitle={c.organizer ? `Organized by ${c.organizer}` : undefined}>
      <div className="space-y-8">
        <Link to="/conferences" className="text-sm text-slate-500 hover:text-slate-900">← All conferences</Link>

        {/* Meta bar */}
        <div className="flex items-center gap-2 flex-wrap pb-6 border-b border-slate-200">
          <CalendarDays size={16} strokeWidth={1.5} className="text-[#0F2847]" />
          {c.acronym && (
            <div className="overline border border-[#0F2847]/20 bg-[#0F2847]/5 text-[#0F2847] px-2 py-0.5">
              {c.acronym} {c.year || ""}
            </div>
          )}
          {c.rank && (
            <div className="overline border border-purple-200 bg-purple-50 text-purple-700 px-2 py-0.5">CORE {c.rank}</div>
          )}
          <div className={`overline border px-2 py-0.5 ${STATE_TONE[state]}`}>
            {state === "closing_soon" ? "Closing soon" : state}
          </div>
        </div>

      <div className="grid lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8 space-y-8">
          <section>
            <h2 className="overline mb-3">Research areas</h2>
            <div className="flex flex-wrap gap-2">
              {(c.research_areas || []).map((s, i) => (
                <span key={i} className="text-sm px-3 py-1 border border-slate-300 text-slate-700">{s}</span>
              ))}
            </div>
          </section>

          {c.topics && c.topics.length > 0 && (
            <section className="border-t border-slate-200 pt-6">
              <h2 className="overline mb-3">Topics</h2>
              <div className="flex flex-wrap gap-2">
                {c.topics.map((t, i) => (
                  <span key={i} className="text-xs font-mono px-2 py-1 bg-slate-100 text-slate-700">{t}</span>
                ))}
              </div>
            </section>
          )}

          {(c.location || c.format) && (
            <section className="border-t border-slate-200 pt-6 text-sm">
              {c.location && (
                <div className="inline-flex items-center gap-2 text-slate-700">
                  <MapPin size={14} strokeWidth={1.5} className="text-[#0F2847]" /> {c.location}
                </div>
              )}
              {c.format && (
                <span className="ml-4 overline border border-slate-300 px-2 py-0.5">{c.format}</span>
              )}
            </section>
          )}

          {(c.cfp_url || c.website) && (
            <section className="border-t border-slate-200 pt-6 flex flex-wrap gap-4">
              {c.website && (
                <a href={c.website} target="_blank" rel="noreferrer"
                   className="inline-flex items-center gap-2 text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">
                  Conference website <ExternalLink size={14} strokeWidth={1.5} />
                </a>
              )}
              {c.cfp_url && c.cfp_url !== c.website && (
                <a href={c.cfp_url} target="_blank" rel="noreferrer"
                   className="inline-flex items-center gap-2 text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">
                  Call for papers <ExternalLink size={14} strokeWidth={1.5} />
                </a>
              )}
            </section>
          )}
        </div>

        <aside className="lg:col-span-4 space-y-6">
          <div className="border border-slate-200 bg-white p-6">
            <div className="overline mb-4 flex items-center gap-2">
              <Users size={13} strokeWidth={1.5} className="text-[#0F2847]" />
              Submission team
            </div>
            {myTeam === undefined ? (
              <div className="text-sm text-slate-400">Loading…</div>
            ) : myTeam ? (
              <Button as={Link} to={`/conference-teams/${myTeam.id}`} size="sm" variant="outline" className="w-full justify-center">
                View my team
              </Button>
            ) : (
              <>
                <p className="text-xs text-slate-500 mb-3">
                  Form a co-author team for this submission — opens a shared workspace to write and coordinate in.
                </p>
                <Button onClick={formTeam} disabled={formingTeam} loading={formingTeam} size="sm" className="w-full justify-center">
                  Form a team
                </Button>
              </>
            )}
          </div>
          <div className="border border-slate-200 bg-white p-6">
            <div className="overline mb-4">Key dates (UTC)</div>
            {dateRow("Submission deadline", c.submission_deadline)}
            {dateRow("Notification", c.notification_date)}
            {dateRow("Camera ready", c.camera_ready_date)}
            {dateRow("Conference starts", c.start_date)}
            {dateRow("Conference ends", c.end_date)}
            {!c.submission_deadline && !c.start_date && (
              <div className="text-sm text-slate-500">Dates not published yet.</div>
            )}
          </div>
          <div className="text-[11px] text-slate-500">
            Data: {c.source === "wikicfp" ? "WikiCFP" : (c.source || "—")}
          </div>
        </aside>
      </div>
      </div>
    </ResearchLayout>
  );
}
