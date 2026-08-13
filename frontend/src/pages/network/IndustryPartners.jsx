import React, { useState, useEffect, useCallback, useRef } from "react";
import api from "@/lib/api";
import { Search, ArrowRight, Building2 } from "lucide-react";
import { NAVY, WARM, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
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

  const search = useCallback(async (pg) => {
    setLoading(true);
    try {
      const params = { page: pg, limit: 20, type: "industry" };
      if (q) params.q = q;
      const r = await api.get("/network/institutions", { params });
      setResults(r.data.results || []);
      setTotal(r.data.total || 0);
    } catch { setResults([]); } finally { setLoading(false); }
  }, [q]);

  const searchRef = useRef(search);
  useEffect(() => { searchRef.current = search; }, [search]);
  useEffect(() => { searchRef.current(1); }, []);

  const handleSearch = e => { e.preventDefault(); setPage(1); search(1); };

  return (
    <ResearchLayout
      title="Industry Partners"
      subtitle="Discover industry organisations for applied research, technology transfer, and co-funded projects."
      sidebar={<IndustryPartnersSidebar results={results} total={total} q={q} />}
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
    </ResearchLayout>
  );
}

// ── Right rail — real search results already loaded by this page ─────────────
function IndustryPartnersSidebar({ results, total, q }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Building2 size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Search Results</div>
        </div>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 28, fontWeight: 700, color: "#0f172a" }}>{total}</div>
        <p style={{ fontSize: 12, color: "#64748B", margin: "4px 0 0", lineHeight: 1.5 }}>
          {q ? `Industry partners matching "${q}".` : "Industry partners on the platform."}
        </p>
      </Card>

      {results.length > 0 && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <Search size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Top Matches</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {results.slice(0, 5).map((inst, i) => (
              <div key={i}>
                <div style={{ fontSize: 12.5, fontWeight: 600, color: "#0f172a", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{inst.name}</div>
                <div style={{ fontSize: 11, color: "#94A3B8" }}>{inst.country}</div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
