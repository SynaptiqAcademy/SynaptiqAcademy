import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Users, ExternalLink } from "lucide-react";
import { AdministrationLayout } from "@/layouts";

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

  if (loading) return <div className="p-8 text-slate-500 text-sm">Loading…</div>;
  if (err) return <div className="p-8 text-red-600 text-sm">{err}</div>;

  return (
    <AdministrationLayout
      title="Public Research Profiles"
      subtitle={`All researcher public profiles — ${profiles.length} total`}
    >
      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search by name or institution…"
        className="w-full max-w-sm border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:border-slate-900"
      />

      <div className="bg-white border border-slate-200">
        {filtered.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">No profiles found</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase tracking-widest text-slate-400">
                <th className="px-4 py-2 text-left">Name</th>
                <th className="px-4 py-2 text-left">Institution</th>
                <th className="px-4 py-2 text-left">Research Areas</th>
                <th className="px-4 py-2 text-left">Slug</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr key={p.id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="px-4 py-2.5 font-medium text-slate-800">{p.full_name || "—"}</td>
                  <td className="px-4 py-2.5 text-slate-600">{p.institution || "—"}</td>
                  <td className="px-4 py-2.5 text-slate-500">
                    {(p.research_areas || []).slice(0, 2).join(", ") || "—"}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-slate-400">{p.slug || "—"}</td>
                  <td className="px-4 py-2.5">
                    {p.slug && (
                      <a href={`/researcher/${p.slug}`} target="_blank" rel="noopener noreferrer"
                        className="text-slate-400 hover:text-slate-700">
                        <ExternalLink size={12} />
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </AdministrationLayout>
  );
}
