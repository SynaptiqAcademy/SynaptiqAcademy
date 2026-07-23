import React, { useCallback, useEffect, useRef, useState } from "react";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { Search, Coins } from "lucide-react";
import { Spinner } from "@/components/ds/LoadingState";
import { EmptyState } from "@/components/ds/EmptyState";
import { Card } from "@/components/ds/Card";
import { Button } from "@/components/ds/Button";
import { Input } from "@/components/ds/Input";
import { FormSelect } from "@/components/ds/FormSelect";
import { Tag, TagGroup } from "@/components/ds/Tag";
import { DiscoveryLayout } from "@/layouts";

const AREAS = ["Artificial Intelligence", "Healthcare", "Management", "Economics", "Education", "Public Health", "Cybersecurity", "Engineering", "Psychology"];

export default function Funding() {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [area, setArea] = useState("");
  const [agency, setAgency] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const params = {};
    if (q) params.q = q;
    if (area) params.research_area = area;
    if (agency) params.agency = agency;
    const { data } = await api.get("/funding", { params });
    setItems(data);
    setLoading(false);
  }, [q, area, agency]);

  // Only auto-fetch on mount; subsequent searches are user-triggered (Enter / Apply filters).
  const loadRef = useRef(load);
  useEffect(() => { loadRef.current = load; }, [load]);
  useEffect(() => { loadRef.current(); }, []);

  return (
    <DiscoveryLayout
      title="Funding"
      subtitle="A searchable database of funding opportunities — grants, fellowships, and programmes."
    >
      <div className="grid sm:grid-cols-4 gap-3">
        <Input
          data-testid={TID.fundingSearch}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && load()}
          placeholder="Search title, agency, description…"
          prefix={<Search size={14} strokeWidth={1.5} />}
          wrapperClassName="sm:col-span-2"
        />
        <FormSelect value={area} onChange={(e) => setArea(e.target.value)}>
          <option value="">All research areas</option>
          {AREAS.map((a) => <option key={a}>{a}</option>)}
        </FormSelect>
        <Input value={agency} onChange={(e) => setAgency(e.target.value)} placeholder="Agency…" />
      </div>
      <Button variant="link" size="sm" onClick={load}>Apply filters</Button>

      <div data-testid={TID.fundingList} className="space-y-4">
        {loading && <div className="py-4 flex justify-center"><Spinner size={16} /></div>}
        {!loading && items.length === 0 && (
          <EmptyState title="No funding opportunities match your filters." size="sm" />
        )}
        {items.map((g) => (
          <Card
            key={g.id}
            to={`/funding/${g.id}`}
            data-testid={TID.fundingCard(g.id)}
            padding="lg"
          >
            <div className="grid sm:grid-cols-12 gap-6">
              <div className="sm:col-span-8 min-w-0">
                <div className="overline text-[#0F2847]">{g.funding_type || "Grant"} · {g.agency}</div>
                <h3 className="font-serif text-2xl text-slate-900 mt-2 leading-snug">{g.title}</h3>
                <p className="text-sm text-slate-600 mt-3 line-clamp-2">{g.description || "Funding opportunity."}</p>
                <TagGroup gap={8} className="mt-4">
                  {(g.research_areas || []).slice(0, 4).map((a) => (
                    <Tag key={a} size="sm">{a}</Tag>
                  ))}
                </TagGroup>
              </div>
              <div className="sm:col-span-4 sm:border-l sm:border-slate-200 sm:pl-6 space-y-2 text-xs">
                <Row label="Amount" value={g.amount} icon={<Coins size={12} strokeWidth={1.5} />} />
                <Row label="Deadline" value={g.deadline} />
                <Row label="Duration" value={g.duration || "—"} />
              </div>
            </div>
          </Card>
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
