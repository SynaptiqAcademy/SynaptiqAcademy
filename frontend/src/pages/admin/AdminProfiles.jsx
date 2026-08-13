import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { ExternalLink, Building2, Tags } from "lucide-react";
import { NAVY } from "@/lib/tokens";
import { AdministrationLayout } from "@/layouts";
import { SearchBar, DataTable, LoadingOverlay, ErrorState, Card } from "@/components/ds";

export default function AdminProfiles() {
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.get("/public-profiles/directory?limit=50")
      .then((r) => setProfiles(r.data?.profiles || []))
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load profiles"))
      .finally(() => setLoading(false));
  }, []);

  const filtered = profiles.filter((p) =>
    !search || p.full_name?.toLowerCase().includes(search.toLowerCase()) ||
    p.institution?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) return <LoadingOverlay text="Loading…" />;
  if (err) return <div className="p-8"><ErrorState message={err} /></div>;

  const columns = [
    { key: "full_name", label: "Name", render: (v) => <span className="font-medium text-slate-800">{v || "—"}</span> },
    { key: "institution", label: "Institution", render: (v) => v || "—" },
    {
      key: "research_areas",
      label: "Research Areas",
      render: (v) => (v || []).slice(0, 2).join(", ") || "—",
    },
    { key: "slug", label: "Slug", render: (v) => <span className="font-mono text-xs">{v || "—"}</span> },
    {
      key: "_link",
      label: "",
      align: "right",
      render: (_, p) =>
        p.slug ? (
          <a
            href={`/researcher/${p.slug}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-400 hover:text-slate-700"
          >
            <ExternalLink size={12} />
          </a>
        ) : null,
    },
  ];

  return (
    <AdministrationLayout
      title="Public Research Profiles"
      subtitle={`All researcher public profiles — ${profiles.length} total`}
      sidebar={profiles.length > 0 ? <ProfilesSidebar profiles={profiles} /> : undefined}
    >
      <div className="flex flex-col gap-4">
        <SearchBar
          value={search}
          onChange={setSearch}
          placeholder="Search by name or institution…"
          onClear={() => setSearch("")}
          className="max-w-sm"
        />

        <DataTable columns={columns} rows={filtered} />
      </div>
    </AdministrationLayout>
  );
}

// ── Right rail — computed from the profiles already fetched above ─────────────
function ProfilesSidebar({ profiles }) {
  const topN = (counts, n) => Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, n);

  const institutionCounts = profiles.reduce((acc, p) => {
    if (p.institution) acc[p.institution] = (acc[p.institution] || 0) + 1;
    return acc;
  }, {});
  const areaCounts = profiles.reduce((acc, p) => {
    (p.research_areas || []).forEach((a) => { acc[a] = (acc[a] || 0) + 1; });
    return acc;
  }, {});

  const topInstitutions = topN(institutionCounts, 5);
  const topAreas = topN(areaCounts, 5);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {topInstitutions.length > 0 && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <Building2 size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Top Institutions</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {topInstitutions.map(([name, count]) => (
              <div key={name} style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <span style={{ fontSize: 12, color: "#374151", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{name}</span>
                <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a", flexShrink: 0 }}>{count}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {topAreas.length > 0 && (
        <Card padding="lg">
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <Tags size={13} style={{ color: NAVY }} />
            <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Top Research Areas</div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {topAreas.map(([area, count]) => (
              <div key={area} style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <span style={{ fontSize: 12, color: "#374151", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{area}</span>
                <span style={{ fontSize: 12, fontWeight: 700, color: "#0f172a", flexShrink: 0 }}>{count}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
