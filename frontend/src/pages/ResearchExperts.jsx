/**
 * Research & Experts — P1 Phase 8B, the consolidated primary discovery
 * experience (replacing the two previously-duplicate "Researchers" nav
 * entries — see navigation.js). Evolved from network/PeopleDiscovery.jsx's
 * structure (its backend, GET /network/people → discovery_engine.
 * search_people(), was already the correct privacy-safe canonical
 * retrieval layer — see Phase 8A audit) rather than Researchers.jsx (whose
 * Explorer hit a different endpoint). Old /researchers and /network/people
 * both still resolve here; App.js redirects the latter for compatibility.
 *
 * career_stage/verification_level/trust_score filters from the old page
 * are gone — Phase 8A confirmed none of the three is ever set on a real
 * user document, so they never matched anything (§5).
 *
 * Basic discovery costs zero AI credits — GET /network/people never calls
 * consume_credits(); the compatibility score it returns per result comes
 * from the canonical deterministic engine, called directly (§1/§15).
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Search, X, Shield, CheckCircle2, Sparkles } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import api from "@/lib/api";
import { NAVY, EMERALD, TEXT_SECONDARY, TEXT_MUTED, BRD } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import { Card, Badge, Button, Input, EmptyState, LoadingOverlay, Pagination, Checkbox } from "@/components/ds";
import ResearchNeedPanel from "@/components/research/ResearchNeedPanel";

const PAGE_SIZE = 20;

const EMPTY_FILTERS = {
  q: "", institution: "", country: "", discipline: "", professional_role: "",
  available_for_collaboration: false, available_for_reviewing: false,
  orcid_verified: false, institution_verified: false,
};

function VerifiedBadge({ icon: Icon, label }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 10.5, fontWeight: 700, color: EMERALD, background: "#ECFDF5", padding: "2px 7px", borderRadius: 100 }}>
      <Icon size={10} /> {label}
    </span>
  );
}

function ChipRow({ items, color = NAVY, bg }) {
  if (!items || items.length === 0) return null;
  const visible = items.slice(0, 4);
  const rest = items.length - visible.length;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
      {visible.map((it) => (
        <span key={it} style={{ fontSize: 11, padding: "2px 8px", background: bg || `${color}12`, color, border: `1px solid ${color}30` }}>{it}</span>
      ))}
      {rest > 0 && <span style={{ fontSize: 11, color: TEXT_MUTED }}>+{rest} more</span>}
    </div>
  );
}

function CompatibilityBadge({ compatibility }) {
  if (compatibility === undefined) return null;
  if (compatibility === null) {
    return <div style={{ fontSize: 11, color: TEXT_MUTED, fontStyle: "italic" }}>Limited profile information</div>;
  }
  const { score, shared_keywords, complementary_skills, explanation } = compatibility;
  return (
    <div style={{ borderTop: `1px solid ${BRD}`, marginTop: 10, paddingTop: 10 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12.5, fontWeight: 700, color: NAVY, marginBottom: 4 }}>
        <Sparkles size={12} /> Research compatibility · {score}%
      </div>
      {(shared_keywords?.length > 0 || complementary_skills?.length > 0) ? (
        <ul style={{ margin: 0, paddingLeft: 16, fontSize: 11.5, color: TEXT_SECONDARY, lineHeight: 1.7 }}>
          {shared_keywords?.slice(0, 3).map((k) => <li key={`s-${k}`}>Shared: {k}</li>)}
          {complementary_skills?.slice(0, 2).map((k) => <li key={`c-${k}`}>Complementary: {k}</li>)}
        </ul>
      ) : (
        explanation && <p style={{ margin: 0, fontSize: 11.5, color: TEXT_SECONDARY, lineHeight: 1.6 }}>{explanation}</p>
      )}
    </div>
  );
}

// P1 Phase 8C: a Research Need relevance result carries `explanation` (plain
// evidence text, no score — see services/research_need/relevance.py) instead
// of `compatibility` (the Phase 8B canonical-engine score). Same card, two
// possible evidence blocks, so both search paths reuse one component.
function WhyThisPerson({ explanation }) {
  if (!explanation) return null;
  return (
    <div style={{ borderTop: `1px solid ${BRD}`, marginTop: 10, paddingTop: 10 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: NAVY, marginBottom: 3, textTransform: "uppercase", letterSpacing: 0.3 }}>
        Why this person
      </div>
      <p style={{ margin: 0, fontSize: 11.5, color: TEXT_SECONDARY, lineHeight: 1.6 }}>{explanation}</p>
    </div>
  );
}

export function ExpertResultCard({ person }) {
  const role = [person.academic_role, person.professional_role].filter(Boolean).join(" · ");
  return (
    <Card padding="lg">
      <Link to={`/profile/${person.id}`} style={{ textDecoration: "none", color: "inherit" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          <div style={{ width: 44, height: 44, borderRadius: "50%", background: `${NAVY}14`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, fontSize: 17, fontWeight: 800, color: NAVY, overflow: "hidden" }}>
            {person.profile_picture ? <img src={person.profile_picture} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : (person.name || "?")[0].toUpperCase()}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 700, fontSize: 14.5, color: NAVY }}>{person.name || "Researcher"}</div>
            {role && <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 1 }}>{role}</div>}
            <div style={{ fontSize: 11.5, color: TEXT_MUTED, marginTop: 1 }}>
              {[person.institution, person.country].filter(Boolean).join(" · ")}
            </div>
            <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
              {person.orcid_verified && <VerifiedBadge icon={CheckCircle2} label="ORCID" />}
              {person.institution_verified && <VerifiedBadge icon={Shield} label="Institution" />}
              {person.available_for_collaboration && <Badge size="sm">Open to collaboration</Badge>}
              {person.available_for_reviewing && <Badge size="sm">Open to peer review</Badge>}
            </div>
          </div>
        </div>
      </Link>

      <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
        <ChipRow items={person.research_areas} color="#0891B2" />
        <ChipRow items={person.professional_expertise} color="#0F766E" />
        <ChipRow items={person.methods} color={NAVY} bg="#F8FAFC" />
      </div>

      {person.explanation ? <WhyThisPerson explanation={person.explanation} /> : <CompatibilityBadge compatibility={person.compatibility} />}
    </Card>
  );
}

function CompletenessBanner({ profile }) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed || !profile) return null;
  const missing = [];
  if (!(profile.research_areas || []).length) missing.push("research areas");
  if (!(profile.methods || []).length) missing.push("methods");
  if (!(profile.professional_expertise || []).length) missing.push("professional expertise");
  if (!(profile.languages || []).length) missing.push("languages");
  if (!(profile.orcid?.orcid_id)) missing.push("ORCID connection");
  if (missing.length === 0) return null;
  return (
    <Card padding="md" style={{ marginBottom: 16, border: `1px solid ${NAVY}25`, background: "#F8FAFC" }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 10 }}>
        <div style={{ fontSize: 12.5, color: TEXT_SECONDARY, lineHeight: 1.6 }}>
          <strong style={{ color: NAVY }}>Other researchers find you through this same search.</strong>{" "}
          Add {missing.slice(0, 3).join(", ")}{missing.length > 3 ? ", and more" : ""} on your Academic Passport so relevant collaborators can find you.
        </div>
        <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
          <Link to="/academic-passport"><Button as="span" size="sm">Edit identity</Button></Link>
          <Button size="sm" variant="ghost" onClick={() => setDismissed(true)}>Dismiss</Button>
        </div>
      </div>
    </Card>
  );
}

export default function ResearchExperts() {
  const { user: me } = useAuth();
  const [searchParams] = useSearchParams();
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ ...EMPTY_FILTERS, q: searchParams.get("q") || "" });

  const search = useCallback(async (f, pg) => {
    setLoading(true);
    try {
      const params = { page: pg, limit: PAGE_SIZE };
      Object.entries(f).forEach(([k, v]) => {
        if (v === "" || v === false || v === null || v === undefined) return;
        params[k === "discipline" ? "discipline" : k] = v;
      });
      const r = await api.get("/network/people", { params });
      setResults(r.data.results || []);
      setTotal(r.data.total || 0);
      setPages(r.data.pages || 1);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const initialRef = useRef({ filters, page });
  useEffect(() => {
    const { filters: f0, page: p0 } = initialRef.current;
    search(f0, p0);
  }, [search]);

  const runSearch = (nextFilters) => {
    setPage(1);
    search(nextFilters, 1);
  };

  const setFilter = (key, value) => {
    const next = { ...filters, [key]: value };
    setFilters(next);
    return next;
  };

  return (
    <ResearchLayout title="Research & Experts" subtitle="Find researchers and interdisciplinary experts across Synaptiq">
      <CompletenessBanner profile={me} />

      <ResearchNeedPanel />

      <form
        onSubmit={(e) => { e.preventDefault(); runSearch(filters); }}
        style={{ display: "flex", gap: 10, marginBottom: 12 }}
      >
        <Input
          value={filters.q}
          onChange={(e) => setFilter("q", e.target.value)}
          placeholder="Search name, research area, methods, professional expertise…"
          prefix={<Search size={15} />}
          wrapperClassName="flex-1"
        />
        <Button type="submit" variant="primary">Search</Button>
      </form>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
        {[
          { key: "institution", placeholder: "Institution" },
          { key: "country", placeholder: "Country" },
          { key: "discipline", placeholder: "Research area or discipline" },
          { key: "professional_role", placeholder: "Professional role" },
        ].map(({ key, placeholder }) => (
          <div key={key} style={{ position: "relative" }}>
            <Input
              value={filters[key]}
              onChange={(e) => setFilter(key, e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") runSearch(setFilter(key, e.target.value)); }}
              placeholder={placeholder}
              size="sm"
              style={{ paddingRight: filters[key] ? 30 : undefined }}
            />
            {filters[key] && (
              <Button size="icon" variant="ghost" onClick={() => runSearch(setFilter(key, ""))} aria-label={`Clear ${placeholder}`}
                style={{ position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)", padding: 0 }}>
                <X size={13} color={TEXT_SECONDARY} />
              </Button>
            )}
          </div>
        ))}
      </div>

      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 18, fontSize: 12.5 }}>
        {[
          { key: "available_for_collaboration", label: "Open to collaboration" },
          { key: "available_for_reviewing", label: "Open to peer review" },
          { key: "orcid_verified", label: "ORCID connected" },
          { key: "institution_verified", label: "Institution verified" },
        ].map(({ key, label }) => (
          <Checkbox key={key} label={label} checked={filters[key]} onChange={(e) => runSearch(setFilter(key, e.target.checked))} />
        ))}
      </div>

      {!loading && <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 12 }}>{total} result{total === 1 ? "" : "s"}</div>}

      {loading ? (
        <LoadingOverlay text="Searching…" />
      ) : results.length === 0 ? (
        <EmptyState title="No researchers or experts found." description="Try broadening your search or filters." />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 12 }}>
          {results.map((p) => <ExpertResultCard key={p.id} person={p} />)}
        </div>
      )}

      {pages > 1 && (
        <div style={{ marginTop: 20 }}>
          <Pagination page={page} totalPages={pages} onPage={(p) => { setPage(p); search(filters, p); }} />
        </div>
      )}
    </ResearchLayout>
  );
}
