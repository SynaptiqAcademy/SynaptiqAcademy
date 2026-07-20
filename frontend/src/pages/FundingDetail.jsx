import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { Bookmark, BookmarkCheck } from "lucide-react";
import { toast } from "sonner";
import { NAVY } from "@/lib/tokens";
import { SkeletonCard } from "@/components/ds/LoadingState";

export default function FundingDetail() {
  const { id } = useParams();
  const [g, setG] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.get(`/funding/${id}`).then((r) => setG(r.data)).catch(() => {});
    api.get("/auth/me").then((r) => setSaved((r.data.saved_funding_ids || []).includes(id))).catch(() => {});
  }, [id]);

  const toggleSave = async () => {
    try {
      if (saved) { await api.post(`/grants/${id}/unsave`); toast.success("Removed from saved"); setSaved(false); }
      else { await api.post(`/grants/${id}/save`); toast.success("Saved to your grants"); setSaved(true); }
    } catch (e) { toast.error("Failed"); }
  };

  if (!g) return <div className="p-6"><SkeletonCard rows={4} /></div>;

  return (
    <div className="grid lg:grid-cols-12 gap-10">
      <div className="lg:col-span-8 space-y-8">
        <Link to="/funding" className="text-sm text-slate-500 hover:text-slate-900">← All funding</Link>
        <header>
          <div className="overline text-[#0F2847]">{g.funding_type || "Grant"} · {g.agency}</div>
          <h1 className="font-serif text-5xl text-slate-900 mt-3 leading-tight">{g.title}</h1>
        </header>

        <p className="text-lg text-slate-700 leading-relaxed">{g.description || "Funding opportunity."}</p>

        <section className="border-t border-slate-200 pt-8">
          <h2 className="overline mb-4">Eligibility</h2>
          <p className="text-slate-700 leading-relaxed">{g.eligibility || "Refer to agency call for eligibility criteria."}</p>
        </section>

        <section className="border-t border-slate-200 pt-8">
          <h2 className="overline mb-4">Research areas</h2>
          <div className="flex flex-wrap gap-2">
            {(g.research_areas || []).map((a) => (
              <span key={a} className="text-sm px-3 py-1 border border-slate-300 text-slate-700">{a}</span>
            ))}
            {(g.research_areas || []).length === 0 && <div className="text-slate-500 text-sm">—</div>}
          </div>
        </section>
      </div>

      <aside className="lg:col-span-4 space-y-6">
        <div className="border border-slate-200 bg-white p-6 space-y-3 text-sm">
          <Detail label="Funding amount" value={g.amount} />
          <Detail label="Deadline" value={g.deadline} />
          <Detail label="Duration" value={g.duration || "—"} />
          <Detail label="Type" value={g.funding_type || "Grant"} />
          <Detail label="Agency" value={g.agency} />
        </div>
        <button
          data-testid={TID.fundingSaveBtn}
          onClick={toggleSave}
          className={`w-full inline-flex items-center justify-center gap-2 py-3 text-sm transition-colors ${saved ? "bg-[#0F2847] text-white hover:bg-slate-800" : "border border-[#0F2847] text-[#0F2847] hover:bg-[#0F2847] hover:text-white"}`}
        >
          {saved ? <><BookmarkCheck size={14} strokeWidth={1.5} /> Saved</> : <><Bookmark size={14} strokeWidth={1.5} /> Save to grants</>}
        </button>
      </aside>
    </div>
  );
}

function Detail({ label, value }) {
  return (
    <div className="flex items-baseline justify-between">
      <span className="overline">{label}</span>
      <span className="text-slate-900 text-right">{value || "—"}</span>
    </div>
  );
}
