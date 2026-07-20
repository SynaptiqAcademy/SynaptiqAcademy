import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { Search, Coins } from "lucide-react";
import { NAVY } from "@/lib/tokens";
import { Spinner } from "@/components/ds/LoadingState";
import { DiscoveryLayout } from "@/layouts";

const AREAS = ["Artificial Intelligence", "Healthcare", "Management", "Economics", "Education", "Public Health", "Cybersecurity", "Engineering", "Psychology"];

export default function Funding() {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [area, setArea] = useState("");
  const [agency, setAgency] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const params = {};
    if (q) params.q = q;
    if (area) params.research_area = area;
    if (agency) params.agency = agency;
    const { data } = await api.get("/funding", { params });
    setItems(data);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  return (
    <DiscoveryLayout
      title="Funding"
      subtitle="A searchable database of funding opportunities — grants, fellowships, and programmes."
    >
      <div className="grid sm:grid-cols-4 gap-3">
        <div className="relative sm:col-span-2">
          <Search size={14} strokeWidth={1.5} className="absolute left-3 top-3 text-slate-400" />
          <input
            data-testid={TID.fundingSearch}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load()}
            placeholder="Search title, agency, description…"
            className="w-full pl-9 pr-3 py-2 border border-slate-300 focus:outline-none focus:ring-1 focus:ring-[#0F2847]"
          />
        </div>
        <select value={area} onChange={(e) => setArea(e.target.value)} className="px-3 py-2 border border-slate-300 bg-white">
          <option value="">All research areas</option>
          {AREAS.map((a) => <option key={a}>{a}</option>)}
        </select>
        <input value={agency} onChange={(e) => setAgency(e.target.value)} placeholder="Agency…" className="px-3 py-2 border border-slate-300 bg-white" />
      </div>
      <button onClick={load} className="text-sm text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">Apply filters</button>

      <div data-testid={TID.fundingList} className="space-y-4">
        {loading && <div className="py-4 flex justify-center"><Spinner size={16} /></div>}
        {!loading && items.length === 0 && (
          <div className="text-sm text-slate-500 py-12 text-center border border-dashed border-slate-300">No funding opportunities match your filters.</div>
        )}
        {items.map((g) => (
          <Link
            key={g.id}
            to={`/funding/${g.id}`}
            data-testid={TID.fundingCard(g.id)}
            className="block border border-slate-200 bg-white p-6 hover:border-[#0F2847] transition-colors"
          >
            <div className="grid sm:grid-cols-12 gap-6">
              <div className="sm:col-span-8 min-w-0">
                <div className="overline text-[#0F2847]">{g.funding_type || "Grant"} · {g.agency}</div>
                <h3 className="font-serif text-2xl text-slate-900 mt-2 leading-snug">{g.title}</h3>
                <p className="text-sm text-slate-600 mt-3 line-clamp-2">{g.description || "Funding opportunity."}</p>
                <div className="flex flex-wrap gap-2 mt-4">
                  {(g.research_areas || []).slice(0, 4).map((a) => (
                    <span key={a} className="text-xs px-2 py-0.5 bg-slate-100 text-slate-700">{a}</span>
                  ))}
                </div>
              </div>
              <div className="sm:col-span-4 sm:border-l sm:border-slate-200 sm:pl-6 space-y-2 text-xs">
                <Row label="Amount" value={g.amount} icon={<Coins size={12} strokeWidth={1.5} />} />
                <Row label="Deadline" value={g.deadline} />
                <Row label="Duration" value={g.duration || "—"} />
              </div>
            </div>
          </Link>
        ))}
      </div>
    </DiscoveryLayout>
  );
}

function Row({ label, value, icon }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-slate-500 uppercase tracking-widest text-[10px] flex items-center gap-1">{icon}{label}</span>
      <span className="text-slate-900 text-right truncate">{value || "—"}</span>
    </div>
  );
}
