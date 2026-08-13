import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import api from "@/lib/api";
import { Search, X, Shield, Users } from "lucide-react";
import { NAVY, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Badge, Button, Input, FormSelect, EmptyState, LoadingOverlay, Pagination } from "@/components/ds";

const CAREER_STAGES = ["student", "postdoc", "early_career", "mid_career", "senior", "professor"];
const STAGE_COLOR = { student: "#06b6d4", postdoc: "#8b5cf6", early_career: ACCENT, mid_career: EMERALD, senior: "#f97316", professor: NAVY };

function PersonCard({ person }) {
  const stage = person.career_stage || "researcher";
  const color = STAGE_COLOR[stage] || NAVY;
  return (
    <Card padding="md">
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
        <div style={{ width: 44, height: 44, borderRadius: "50%", background: `${color}20`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, fontSize: 18, fontWeight: 800, color }}>
          {(person.name || "?")[0].toUpperCase()}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 14, color: NAVY }}>{person.name || "Researcher"}</div>
          <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{person.institution || ""}{person.country ? ` · ${person.country}` : ""}</div>
          {person.career_stage && (
            <Badge color={color} size="sm" style={{ marginTop: 4 }}>
              {stage.replace("_", " ")}
            </Badge>
          )}
        </div>
        {person.trust_score > 0 && (
          <div style={{ display: "flex", alignItems: "center", gap: 3, fontSize: 11, color: EMERALD, fontWeight: 700 }}>
            <Shield size={11} />
            {Math.round(person.trust_score)}
          </div>
        )}
      </div>
      {person.research_interests && (
        <Card.Footer style={{ fontSize: 12, color: TEXT_SECONDARY, lineHeight: 1.5 }}>
          <span style={{ fontWeight: 600, color: NAVY }}>Interests: </span>{String(person.research_interests).slice(0, 120)}
          {String(person.research_interests).length > 120 ? "…" : ""}
        </Card.Footer>
      )}
    </Card>
  );
}

export default function PeopleDiscovery() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);

  const [filters, setFilters] = useState({
    q: searchParams.get("q") || "",
    institution: "",
    country: "",
    career_stage: "",
    discipline: "",
  });

  const search = useCallback(async (f, pg) => {
    setLoading(true);
    try {
      const params = { page: pg, limit: 20, ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)) };
      const r = await api.get("/network/people", { params });
      setResults(r.data.results || []);
      setTotal(r.data.total || 0);
      setPages(r.data.pages || 1);
    } catch (e) {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const initialSearchStateRef = useRef({ filters, page });
  useEffect(() => {
    const { filters: f0, page: p0 } = initialSearchStateRef.current;
    search(f0, p0);
  }, [search]);

  const handleSearch = e => {
    e.preventDefault();
    setPage(1);
    search(filters, 1);
  };

  const clearFilter = key => {
    const f = { ...filters, [key]: "" };
    setFilters(f);
    setPage(1);
    search(f, 1);
  };

  return (
    <ResearchLayout title="Find Researchers" sidebar={<PeopleDiscoverySidebar results={results} total={total} />}>
      {/* Search bar */}
      <form onSubmit={handleSearch} style={{ display: "flex", gap: 10, marginBottom: 16 }}>
        <Input
          value={filters.q}
          onChange={e => setFilters(f => ({ ...f, q: e.target.value }))}
          placeholder="Search name, interests, expertise…"
          prefix={<Search size={15} />}
          wrapperClassName="flex-1"
        />
        <Button type="submit" variant="primary">
          Search
        </Button>
      </form>
      {/* Filters */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        {[
          { key: "institution", placeholder: "Institution" },
          { key: "country", placeholder: "Country" },
          { key: "discipline", placeholder: "Discipline" },
        ].map(({ key, placeholder }) => (
          <div key={key} style={{ position: "relative" }}>
            <Input
              value={filters[key]}
              onChange={e => setFilters(f => ({ ...f, [key]: e.target.value }))}
              onKeyDown={e => { if (e.key === "Enter") { setPage(1); search({ ...filters, [key]: e.target.value }, 1); } }}
              placeholder={placeholder}
              size="sm"
              style={{ paddingRight: filters[key] ? 30 : undefined }}
            />
            {filters[key] && (
              <Button
                size="icon"
                variant="ghost"
                onClick={() => clearFilter(key)}
                aria-label={`Clear ${placeholder}`}
                style={{
                  position: "absolute",
                  right: 8,
                  top: "50%",
                  transform: "translateY(-50%)",
                  padding: 0
                }}>
                <X size={13} color={TEXT_SECONDARY} />
              </Button>
            )}
          </div>
        ))}
        <FormSelect
          value={filters.career_stage}
          onChange={e => { const f = { ...filters, career_stage: e.target.value }; setFilters(f); setPage(1); search(f, 1); }}
          size="sm"
        >
          <option value="">Any career stage</option>
          {CAREER_STAGES.map(s => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
        </FormSelect>
      </div>
      {/* Results */}
      {loading ? (
        <LoadingOverlay text="Searching…" />
      ) : results.length === 0 ? (
        <EmptyState title="No researchers found." description="Try adjusting your filters." />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 12 }}>
          {results.map((p, i) => <PersonCard key={p.id || i} person={p} />)}
        </div>
      )}
      {/* Pagination */}
      {pages > 1 && (
        <div style={{ marginTop: 20 }}>
          <Pagination
            page={page}
            totalPages={pages}
            onPage={(p) => { setPage(p); search(filters, p); }}
          />
        </div>
      )}
    </ResearchLayout>
  );
}

// ── Right rail — real search results already loaded by this page ─────────────
function PeopleDiscoverySidebar({ results, total }) {
  const stageCounts = results.reduce((acc, p) => {
    const s = p.career_stage || "unspecified";
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {});
  const stageEntries = Object.entries(stageCounts).sort((a, b) => b[1] - a[1]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <Users size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Researchers Found</div>
        </div>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 28, fontWeight: 700, color: "#0f172a" }}>{total}</div>
        <p style={{ fontSize: 12, color: "#64748B", margin: "4px 0 0", lineHeight: 1.5 }}>
          Matching your current search and filters.
        </p>
      </Card>

      {stageEntries.length > 0 && (
        <Card padding="lg">
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", marginBottom: 8 }}>Career Stage Mix</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {stageEntries.map(([stage, count]) => (
              <div key={stage} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#374151" }}>
                <span style={{ textTransform: "capitalize" }}>{stage.replace("_", " ")}</span>
                <span style={{ fontWeight: 700, color: NAVY }}>{count}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
