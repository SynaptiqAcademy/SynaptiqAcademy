import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { Avatar } from "@/components/ds/Avatar";
import { NAVY } from "@/lib/tokens";
import { NavTabs } from "@/components/ds/NavTabs";
import EmptyState from "@/components/ds/EmptyState";
import { FolderOpen } from "lucide-react";
import { ResearchLayout } from "@/layouts";

export default function MyCollaborations() {
  const [data, setData] = useState({ active: [], completed: [], pending: [] });
  const [tab, setTab] = useState("active");

  useEffect(() => {
    api.get("/collaborations/mine").then((r) => setData(r.data)).catch(() => {});
  }, []);

  const list = data[tab] || [];

  return (
    <ResearchLayout
      title="My Collaborations"
      subtitle="Track your active, pending, and completed research collaborations."
    >

      <NavTabs
        tabs={[
          { id: "active",    label: "Active",    count: data.active.length },
          { id: "pending",   label: "Pending",   count: data.pending.length },
          { id: "completed", label: "Completed", count: data.completed.length },
        ]}
        active={tab}
        onChange={setTab}
        variant="underline"
      />

      <div className="space-y-4">
        {list.length === 0 && (
          <EmptyState icon={<FolderOpen />} title="Nothing here yet" size="md" dashed={true} />
        )}
        {list.map((c) => (
          <Link
            to={`/collaborations/${c.id}`}
            key={c.id}
            className="block border border-slate-200 bg-white p-6 hover:border-[#0F2847]"
          >
            <div className="flex items-start gap-6">
              <div className="flex-1 min-w-0">
                <div className="overline text-[#0F2847]">{c.collab_type}</div>
                <h3 className="font-serif text-2xl text-slate-900 mt-1">{c.title}</h3>
                <p className="text-sm text-slate-600 mt-2 line-clamp-2">{c.description}</p>
              </div>
              <div className="text-right text-xs">
                <div className="font-mono text-slate-500">{c.research_area}</div>
                {c.application_status && (
                  <div className="mt-1 inline-block px-2 py-0.5 bg-amber-50 text-amber-700">Application: {c.application_status}</div>
                )}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </ResearchLayout>
  );
}
