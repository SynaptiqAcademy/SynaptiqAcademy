import React, { useState, useEffect } from "react";
import axios from "axios";
import { Search, ArrowRight } from "lucide-react";
import { NAVY, WARM, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { DiscoveryLayout } from "@/layouts";
import { Card, Button, Input, EmptyState, LoadingOverlay } from "@/components/ds";

const TIPS = [
  { title: "Technology Transfer", desc: "Explore IP licensing and spin-off opportunities with industry R&D divisions." },
  { title: "Contract Research", desc: "Partner with companies as contract research provider for applied projects." },
  { title: "Co-funded Projects", desc: "Apply for industry-academia joint funding through national innovation schemes." },
  { title: "Advisory Roles", desc: "Offer scientific advisory capacity to startups and established companies." },
  { title: "Guest Researchers", desc: "Host industry researchers for knowledge exchange and joint publications." },
];

export default function IndustryPartners() {
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);

  const search = async (pg) => {
    setLoading(true);
    try {
      const params = { page: pg, limit: 20, type: "industry" };
      if (q) params.q = q;
      const r = await axios.get("/api/network/institutions", { params });
      setResults(r.data.results || []);
      setTotal(r.data.total || 0);
    } catch { setResults([]); } finally { setLoading(false); }
  };

  useEffect(() => { search(1); }, []);

  const handleSearch = e => { e.preventDefault(); setPage(1); search(1); };

  return (
    <DiscoveryLayout
      title="Industry Partners"
      subtitle="Discover industry organisations for applied research, technology transfer, and co-funded projects."
    >

      {/* Search */}
      <form onSubmit={handleSearch} style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        <Input
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="Search industry organisations…"
          prefix={<Search size={14} />}
          wrapperClassName="flex-1"
        />
        <Button type="submit" variant="primary">Search</Button>
      </form>

      {loading ? (
        <LoadingOverlay text="Searching…" />
      ) : results.length === 0 ? (
        <div style={{ marginBottom: 20 }}>
          <EmptyState title="No industry partners found in this search." description="You can also post a collaboration opportunity to reach industry partners." />
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 12, marginBottom: 20 }}>
          {results.map((inst, i) => (
            <Card key={i} padding="md">
              <div style={{ fontWeight: 700, fontSize: 13, color: NAVY }}>{inst.name}</div>
              <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{inst.country}</div>
              {inst.research_focus && <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 4 }}>{String(inst.research_focus).slice(0, 80)}</div>}
            </Card>
          ))}
        </div>
      )}

      {/* Tips */}
      <Card padding="lg">
        <h3 style={{ margin: "0 0 14px", fontSize: 14, fontWeight: 700, color: NAVY }}>Academia-Industry Collaboration Pathways</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {TIPS.map((tip, i) => (
            <div key={i} style={{ background: WARM, borderRadius: 10, padding: "12px 16px" }}>
              <div style={{ fontWeight: 700, fontSize: 13, color: NAVY }}>{tip.title}</div>
              <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 2 }}>{tip.desc}</div>
            </div>
          ))}
        </div>
        <Button variant="primary" onClick={() => window.location.href = "/network/collaborations"} style={{ marginTop: 16 }}>
          Post Collaboration Opportunity <ArrowRight size={13} />
        </Button>
      </Card>
    </DiscoveryLayout>
  );
}
