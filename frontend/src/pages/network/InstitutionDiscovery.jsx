import React, { useState, useEffect } from "react";
import axios from "axios";
import { Building2, Search } from "lucide-react";
import { NAVY, ACCENT, TEXT_SECONDARY } from "@/lib/tokens";
import { DiscoveryLayout } from "@/layouts";
import { Card, Button, Input, FormSelect, EmptyState, LoadingOverlay, Pagination } from "@/components/ds";

function InstCard({ inst }) {
  return (
    <Card padding="md">
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
        <div style={{ width: 44, height: 44, borderRadius: 10, background: `${ACCENT}15`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
          <Building2 size={22} color={ACCENT} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14, color: NAVY }}>{inst.name || "Institution"}</div>
          <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{inst.country || ""}  {inst.type ? `· ${inst.type}` : ""}</div>
          {inst.research_focus && (
            <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 6, lineHeight: 1.5 }}>
              {String(inst.research_focus).slice(0, 100)}{String(inst.research_focus).length > 100 ? "…" : ""}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

export default function InstitutionDiscovery() {
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ q: "", country: "", type: "" });

  const search = async (f, pg) => {
    setLoading(true);
    try {
      const params = { page: pg, limit: 20, ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)) };
      const r = await axios.get("/api/network/institutions", { params });
      setResults(r.data.results || []);
      setTotal(r.data.total || 0);
      setPages(r.data.pages || 1);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { search(filters, 1); }, []);

  const handleSearch = e => { e.preventDefault(); setPage(1); search(filters, 1); };

  return (
    <DiscoveryLayout title="Find Institutions">

      <form onSubmit={handleSearch} style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <Input
          value={filters.q}
          onChange={e => setFilters(f => ({ ...f, q: e.target.value }))}
          placeholder="Search institutions, research focus…"
          prefix={<Search size={15} />}
          style={{ minWidth: 200 }}
          wrapperClassName="flex-1"
        />
        <Input
          value={filters.country}
          onChange={e => setFilters(f => ({ ...f, country: e.target.value }))}
          placeholder="Country"
          style={{ width: 140 }}
        />
        <FormSelect
          value={filters.type}
          onChange={e => { const f = { ...filters, type: e.target.value }; setFilters(f); setPage(1); search(f, 1); }}
        >
          <option value="">Any type</option>
          {["university", "research_center", "government", "industry", "hospital", "ngo"].map(t => (
            <option key={t} value={t}>{t.replace("_", " ")}</option>
          ))}
        </FormSelect>
        <Button type="submit" variant="primary">
          Search
        </Button>
      </form>

      {loading ? (
        <LoadingOverlay text="Searching…" />
      ) : results.length === 0 ? (
        <EmptyState title="No institutions found." description="Try a different search." />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 12 }}>
          {results.map((inst, i) => <InstCard key={inst.id || i} inst={inst} />)}
        </div>
      )}

      {pages > 1 && (
        <div style={{ marginTop: 20 }}>
          <Pagination
            page={page}
            totalPages={pages}
            onPage={(p) => { setPage(p); search(filters, p); }}
          />
        </div>
      )}
    </DiscoveryLayout>
  );
}
