import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { ExternalLink } from "lucide-react";
import { AdministrationLayout } from "@/layouts";
import { SearchBar, DataTable, LoadingOverlay, ErrorState } from "@/components/ds";

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
