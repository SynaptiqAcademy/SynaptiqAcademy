import React, { useState, useEffect, useCallback, useRef } from "react";
import api from "@/lib/api";
import { Search, FolderKanban } from "lucide-react";
import { NAVY, TEXT_SECONDARY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Badge, Button, Input, EmptyState, LoadingOverlay, Pagination } from "@/components/ds";

function ProjectCard({ project }) {
  return (
    <Card padding="md">
      <div style={{ fontWeight: 700, fontSize: 14, color: NAVY, marginBottom: 4 }}>{project.title || "Project"}</div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
        {project.status && <Badge variant="success" size="sm">{project.status}</Badge>}
        {project.discipline && <Badge variant="neutral" size="sm">{project.discipline}</Badge>}
        {project.methodology && <Badge variant="neutral" size="sm">{project.methodology}</Badge>}
      </div>
      {project.description && <div style={{ fontSize: 12, color: TEXT_SECONDARY, lineHeight: 1.5 }}>{String(project.description).slice(0, 120)}{String(project.description).length > 120 ? "…" : ""}</div>}
    </Card>
  );
}

export default function ProjectsDiscovery() {
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ q: "", discipline: "", methodology: "" });

  const search = useCallback(async (f, pg) => {
    setLoading(true);
    try {
      const params = { page: pg, limit: 20, ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)) };
      const r = await api.get("/network/projects", { params });
      setResults(r.data.results || []);
      setTotal(r.data.total || 0);
      setPages(r.data.pages || 1);
    } catch { setResults([]); } finally { setLoading(false); }
  }, []);

  const initialFiltersRef = useRef(filters);
  useEffect(() => { search(initialFiltersRef.current, 1); }, [search]);

  const handleSearch = e => { e.preventDefault(); setPage(1); search(filters, 1); };

  return (
    <ResearchLayout title="Research Projects" sidebar={<ProjectsDiscoverySidebar results={results} total={total} />}>

      <form onSubmit={handleSearch} style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <Input
          value={filters.q}
          onChange={e => setFilters(f => ({ ...f, q: e.target.value }))}
          placeholder="Search projects…"
          prefix={<Search size={14} />}
          style={{ minWidth: 200 }}
          wrapperClassName="flex-1"
        />
        <Input
          value={filters.discipline}
          onChange={e => setFilters(f => ({ ...f, discipline: e.target.value }))}
          placeholder="Discipline"
          style={{ width: 140 }}
        />
        <Input
          value={filters.methodology}
          onChange={e => setFilters(f => ({ ...f, methodology: e.target.value }))}
          placeholder="Methodology"
          style={{ width: 140 }}
        />
        <Button type="submit" variant="primary">Search</Button>
      </form>

      {loading ? (
        <LoadingOverlay text="Searching…" />
      ) : results.length === 0 ? (
        <EmptyState title="No active projects found." description="Projects created by researchers on the platform will appear here." />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 12 }}>
          {results.map((p, i) => <ProjectCard key={p.id || i} project={p} />)}
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
    </ResearchLayout>
  );
}

// ── Right rail — real search results already loaded by this page ─────────────
function ProjectsDiscoverySidebar({ results, total }) {
  const statusCounts = results.reduce((acc, p) => {
    const s = p.status || "unspecified";
    acc[s] = (acc[s] || 0) + 1;
    return acc;
  }, {});
  const statusEntries = Object.entries(statusCounts).sort((a, b) => b[1] - a[1]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <FolderKanban size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Projects Found</div>
        </div>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 28, fontWeight: 700, color: "#0f172a" }}>{total}</div>
        <p style={{ fontSize: 12, color: "#64748B", margin: "4px 0 0", lineHeight: 1.5 }}>
          Matching your current search and filters.
        </p>
      </Card>

      {statusEntries.length > 0 && (
        <Card padding="lg">
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a", marginBottom: 8 }}>By Status</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {statusEntries.map(([status, count]) => (
              <div key={status} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#374151" }}>
                <span style={{ textTransform: "capitalize" }}>{status.replace("_", " ")}</span>
                <span style={{ fontWeight: 700, color: NAVY }}>{count}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
