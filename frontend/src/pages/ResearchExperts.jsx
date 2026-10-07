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
import { Search, X, Shield, CheckCircle2, Sparkles, SlidersHorizontal } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import api from "@/lib/api";
import { NAVY, TEXT_SECONDARY, TEXT_MUTED, BRD } from "@/lib/tokens";
import "./research-experts.css";
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
    <span style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 10.5, fontWeight: 600, color: "var(--sq-success-text)", background: "var(--sq-success-bg)", padding: "2px 7px", borderRadius: 4 }}>
      <Icon size={10} /> {label}
    </span>
  );
}

// Topic chips are information, not status: one neutral treatment.
function ChipRow({ items }) {
  if (!items || items.length === 0) return null;
  const visible = items.slice(0, 4);
  const rest = items.length - visible.length;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
      {visible.map((it) => (
        <span key={it} style={{ fontSize: 11, padding: "2px 8px", background: "var(--sq-surface-2)", color: TEXT_SECONDARY, border: `1px solid ${BRD}`, borderRadius: 4 }}>{it}</span>
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

// P1 Phase 8C/8D: a Research Need relevance result carries `explanation`
// (plain evidence text, no score — see services/research_need/relevance.py),
// `contribution` (conservative "what could they contribute" sentences),
// `relevance_labels` (a small deterministic vocabulary — a candidate may
// have more than one), and `evidence` (the full structured list, shown only
// on request — progressive disclosure per §11). Never a percentage: this is
// relevance to THIS research need, not researcher quality (§2/§20).
const LABEL_META = {
  directly_relevant: { text: "Directly relevant" },
  complementary_expertise: { text: "Complementary expertise" },
  methods_specialist: { text: "Methods specialist" },
  context_specialist: { text: "Context specialist" },
};

function WhyThisPerson({ explanation, contribution, relevanceLabels, evidence }) {
  const [expanded, setExpanded] = useState(false);
  if (!explanation) return null;
  return (
    <div style={{ borderTop: `1px solid ${BRD}`, marginTop: 10, paddingTop: 10 }}>
      {relevanceLabels?.length > 0 && (
        <div style={{ display: "flex", gap: 5, flexWrap: "wrap", marginBottom: 6 }}>
          {relevanceLabels.map((l) => {
            const meta = LABEL_META[l];
            if (!meta) return null;
            return (
              <span key={l} style={{ fontSize: 10.5, fontWeight: 600, padding: "2px 7px", color: NAVY, background: "var(--sq-navy-50)", border: "1px solid var(--sq-navy-100)", borderRadius: 4 }}>
                {meta.text}
              </span>
            );
          })}
        </div>
      )}
      <div style={{ fontSize: 11, fontWeight: 700, color: NAVY, marginBottom: 3, textTransform: "uppercase", letterSpacing: 0.3 }}>
        Why this person
      </div>
      <p style={{ margin: 0, fontSize: 11.5, color: TEXT_SECONDARY, lineHeight: 1.6 }}>{explanation}</p>

      {contribution?.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: NAVY, marginBottom: 2, textTransform: "uppercase", letterSpacing: 0.3 }}>
            Possible contribution
          </div>
          <ul style={{ margin: 0, paddingLeft: 16, fontSize: 11.5, color: TEXT_SECONDARY, lineHeight: 1.6 }}>
            {contribution.map((c) => <li key={c}>{c}</li>)}
          </ul>
        </div>
      )}

      {evidence?.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            style={{ fontSize: 11, fontWeight: 600, color: NAVY, background: "none", border: "none", padding: 0, cursor: "pointer", textDecoration: "underline" }}
          >
            {expanded ? "Hide relevance details" : "View relevance details"}
          </button>
          {expanded && (
            <ul style={{ margin: "6px 0 0", paddingLeft: 16, fontSize: 11, color: TEXT_SECONDARY, lineHeight: 1.7 }}>
              {evidence.map((e, i) => (
                <li key={i}>
                  <strong>{e.candidate_value}</strong> — {e.relationship === "direct" ? "direct overlap" : "complementary"} with "{e.need_value}"
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

// P1 Phase 8E — onInvite is optional so this card stays the one shared
// component for basic search (Phase 8B, no invite action), Research Need
// results (Phase 8C/8D), and anywhere else it's reused; only a caller that
// passes onInvite gets the button.
export function ExpertResultCard({ person, onInvite }) {
  const role = [person.academic_role, person.professional_role].filter(Boolean).join(" · ");
  return (
    <Card padding="lg">
      <Link to={`/profile/${person.id}`} style={{ textDecoration: "none", color: "inherit" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          <div style={{ width: 44, height: 44, borderRadius: "50%", background: `${NAVY}14`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, fontSize: 17, fontWeight: 800, color: NAVY, overflow: "hidden" }}>
            {person.profile_picture ? <img src={person.profile_picture} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : (person.name || "?")[0].toUpperCase()}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: 14.5, color: "var(--sq-text-primary)" }}>{person.name || "Researcher"}</div>
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
        <ChipRow items={person.research_areas} />
        <ChipRow items={person.professional_expertise} />
        <ChipRow items={person.methods} />
      </div>

      {person.explanation ? (
        <WhyThisPerson
          explanation={person.explanation}
          contribution={person.contribution}
          relevanceLabels={person.relevance_labels}
          evidence={person.evidence}
        />
      ) : (
        <CompatibilityBadge compatibility={person.compatibility} />
      )}

      {onInvite && (
        <div style={{ marginTop: 12, paddingTop: 10, borderTop: `1px solid ${BRD}` }}>
          <Button type="button" size="sm" variant="primary" onClick={() => onInvite(person)}>
            Invite to Collaborate
          </Button>
          {person.available_for_collaboration === false && (
            <div style={{ marginTop: 5, fontSize: 11, color: TEXT_MUTED, fontStyle: "italic" }}>
              This researcher has indicated they're not currently open to collaboration.
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

// Contextual identity guidance: one dismissible line, not a banner card.
function CompletenessHint({ profile }) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed || !profile) return null;
  const missing = [];
  if (!(profile.research_areas || []).length) missing.push("research areas");
  if (!(profile.methods || []).length) missing.push("methods");
  if (!(profile.professional_expertise || []).length) missing.push("professional expertise");
  if (!(profile.languages || []).length) missing.push("languages");
  if (!(profile.orcid?.orcid_id)) missing.push("ORCID");
  if (missing.length === 0) return null;
  return (
    <p className="rx-hint">
      Others find you through this same search. Adding {missing.slice(0, 3).join(", ")}{missing.length > 3 ? " and more" : ""} helps the right people find you.{" "}
      <Link to="/academic-passport" className="rx-hint-link">Edit Academic Passport</Link>
      <button type="button" className="rx-hint-x" onClick={() => setDismissed(true)} aria-label="Dismiss">
        <X size={13} />
      </button>
    </p>
  );
}

const FILTER_FIELDS = [
  { key: "institution", label: "Institution" },
  { key: "country", label: "Country" },
  { key: "discipline", label: "Research area or discipline" },
  { key: "professional_role", label: "Professional role" },
];
const FILTER_FLAGS = [
  { key: "available_for_collaboration", label: "Open to collaboration" },
  { key: "available_for_reviewing", label: "Open to peer review" },
  { key: "orcid_verified", label: "ORCID connected" },
  { key: "institution_verified", label: "Institution verified" },
];
const MODE_KEY = "sq:rx-mode";

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

  const [mode, setMode] = useState(() => {
    if (searchParams.get("q")) return "search";
    try { return localStorage.getItem(MODE_KEY) || "need"; } catch { return "need"; }
  });
  const chooseMode = (m) => { setMode(m); try { localStorage.setItem(MODE_KEY, m); } catch {} };
  const [filtersOpen, setFiltersOpen] = useState(false);
  const active = [
    ...FILTER_FIELDS.filter((f) => filters[f.key]).map((f) => ({ key: f.key, label: `${f.label}: ${filters[f.key]}`, clear: "" })),
    ...FILTER_FLAGS.filter((f) => filters[f.key]).map((f) => ({ key: f.key, label: f.label, clear: false })),
  ];

  return (
    <ResearchLayout title="Research & Experts" subtitle="Find the expertise a research question needs, or search members directly.">
      <CompletenessHint profile={me} />

      <div className="rx-modes" role="tablist" aria-label="How do you want to find people?">
        <button type="button" role="tab" id="rx-tab-need" aria-selected={mode === "need"} aria-controls="rx-panel-need" onClick={() => chooseMode("need")}>
          Describe a research need
        </button>
        <button type="button" role="tab" id="rx-tab-search" aria-selected={mode === "search"} aria-controls="rx-panel-search" onClick={() => chooseMode("search")}>
          Search members
        </button>
      </div>

      <div id="rx-panel-need" role="tabpanel" aria-labelledby="rx-tab-need" hidden={mode !== "need"}>
        <ResearchNeedPanel />
      </div>

      <div id="rx-panel-search" role="tabpanel" aria-labelledby="rx-tab-search" hidden={mode !== "search"}>
        <form onSubmit={(e) => { e.preventDefault(); runSearch(filters); }} className="rx-search">
          <Input
            value={filters.q}
            onChange={(e) => setFilter("q", e.target.value)}
            placeholder="Name, research area, method or professional expertise"
            aria-label="Search members"
            prefix={<Search size={15} />}
            wrapperClassName="flex-1"
          />
          <Button type="submit" variant="primary">Search</Button>
          <Button type="button" variant="secondary" aria-expanded={filtersOpen} aria-controls="rx-filters" onClick={() => setFiltersOpen((v) => !v)}>
            <SlidersHorizontal size={14} /> Filters{active.length ? ` · ${active.length}` : ""}
          </Button>
        </form>
        <p className="rx-free">Member search is free and never uses AI credits.</p>

        {filtersOpen && (
          <div id="rx-filters" className="rx-filters">
            <div className="rx-filter-grid">
              {FILTER_FIELDS.map(({ key, label }) => (
                <Input
                  key={key}
                  label={label}
                  size="sm"
                  value={filters[key]}
                  onChange={(e) => setFilter(key, e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); runSearch(setFilter(key, e.target.value)); } }}
                />
              ))}
            </div>
            <div className="rx-filter-flags">
              {FILTER_FLAGS.map(({ key, label }) => (
                <Checkbox key={key} label={label} checked={filters[key]} onChange={(e) => runSearch(setFilter(key, e.target.checked))} />
              ))}
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <Button type="button" variant="primary" size="sm" onClick={() => runSearch(filters)}>Apply filters</Button>
            </div>
          </div>
        )}

        {active.length > 0 && (
          <div className="rx-active" aria-label="Active filters">
            {active.map((a) => (
              <button key={a.key} type="button" className="rx-chip" onClick={() => runSearch(setFilter(a.key, a.clear))} aria-label={`Remove filter ${a.label}`}>
                {a.label} <X size={11} />
              </button>
            ))}
            <button type="button" className="rx-clear" onClick={() => { const next = { ...EMPTY_FILTERS, q: filters.q }; setFilters(next); runSearch(next); }}>
              Clear all
            </button>
          </div>
        )}

        {!loading && <div className="rx-count">{total} result{total === 1 ? "" : "s"}</div>}

        {loading ? (
          <LoadingOverlay text="Searching…" />
        ) : results.length === 0 ? (
          <EmptyState
            icon={<Search />}
            title="No members match this search."
            description="Try fewer filters or a broader term, or describe the research need instead."
            action={<Button size="sm" variant="secondary" onClick={() => chooseMode("need")}>Describe a research need</Button>}
          />
        ) : (
          <div className="rx-results">
            {results.map((p) => <ExpertResultCard key={p.id} person={p} />)}
          </div>
        )}

        {pages > 1 && (
          <div style={{ marginTop: 20 }}>
            <Pagination page={page} totalPages={pages} onPage={(p) => { setPage(p); search(filters, p); }} />
          </div>
        )}
      </div>
    </ResearchLayout>
  );
}
