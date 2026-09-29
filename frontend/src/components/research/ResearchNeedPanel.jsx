/**
 * P1 Phase 8C — Research Need Intelligence.
 *
 * "Describe what you're researching" -> AI (or deterministic) interpretation
 * -> editable structured Research Need -> "Expertise this research may
 * need" -> real Synaptiq collaborators, grouped into similar/complementary/
 * methods, with "Why this person" evidence and "Expertise still missing".
 *
 * Deliberately not a chat interface: one text box, one structured result,
 * editable before matching. Reuses ExpertResultCard from ResearchExperts.jsx
 * so a Research Need result looks identical to a basic-search result except
 * for the evidence block.
 */
import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { NAVY, TEXT_SECONDARY, TEXT_MUTED, BRD } from "@/lib/tokens";
import { Card, Button, EmptyState, LoadingOverlay } from "@/components/ds";
import { ExpertResultCard } from "@/pages/ResearchExperts";

const PLACEHOLDER =
  "e.g. How can AI improve quality management in public hospitals while protecting patient outcomes and supporting healthcare staff?";

function EditableChipList({ label, items, onChange }) {
  const [draft, setDraft] = useState("");
  const add = () => {
    const v = draft.trim();
    if (v && !items.includes(v)) onChange([...items, v]);
    setDraft("");
  };
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: TEXT_SECONDARY, marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.3 }}>{label}</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 6 }}>
        {items.map((it) => (
          <span key={it} style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12, padding: "3px 8px", background: `${NAVY}0F`, color: NAVY, border: `1px solid ${NAVY}25` }}>
            {it}
            <button type="button" onClick={() => onChange(items.filter((x) => x !== it))} aria-label={`Remove ${it}`}
              style={{ border: "none", background: "none", cursor: "pointer", color: NAVY, fontWeight: 700, padding: 0, lineHeight: 1 }}>×</button>
          </span>
        ))}
        {items.length === 0 && <span style={{ fontSize: 11.5, color: TEXT_MUTED, fontStyle: "italic" }}>None identified</span>}
      </div>
      <div style={{ display: "flex", gap: 6 }}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }}
          placeholder={`Add ${label.toLowerCase()}…`}
          style={{ flex: 1, fontSize: 12.5, padding: "5px 8px", border: `1px solid ${BRD}`, background: "#fff" }}
        />
        <Button type="button" size="sm" variant="ghost" onClick={add}>Add</Button>
      </div>
    </div>
  );
}

function ResultGroup({ title, description, people }) {
  if (!people || people.length === 0) return null;
  return (
    <div style={{ marginBottom: 22 }}>
      <div style={{ fontSize: 14, fontWeight: 700, color: NAVY, marginBottom: 2 }}>{title}</div>
      {description && <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 10 }}>{description}</div>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 12 }}>
        {people.map((p) => <ExpertResultCard key={p.id} person={p} />)}
      </div>
    </div>
  );
}

export default function ResearchNeedPanel() {
  const [query, setQuery] = useState("");
  const [cost, setCost] = useState(null);
  const [interpreting, setInterpreting] = useState(false);
  const [need, setNeed] = useState(null);
  const [source, setSource] = useState(null); // "ai" | "fallback"
  const [matching, setMatching] = useState(false);
  const [matchResult, setMatchResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/research-need/cost").then((r) => setCost(r.data.cost)).catch(() => setCost(null));
  }, []);

  const runInterpret = async (useAi) => {
    if (!query.trim()) return;
    setError("");
    setInterpreting(true);
    setMatchResult(null);
    try {
      const r = await api.post("/research-need/interpret", { query, use_ai: useAi });
      setNeed(r.data.need);
      setSource(r.data.source);
    } catch (e) {
      setError(e?.response?.data?.detail || "Could not interpret this research question. Please try again.");
    } finally {
      setInterpreting(false);
    }
  };

  const runMatch = async () => {
    if (!need) return;
    setMatching(true);
    setError("");
    try {
      const r = await api.post("/research-need/match", { need });
      setMatchResult(r.data);
    } catch (e) {
      setError(e?.response?.data?.detail || "Could not find relevant collaborators. Please try again.");
    } finally {
      setMatching(false);
    }
  };

  const updateNeed = (field, value) => setNeed((n) => ({ ...n, [field]: value }));

  return (
    <Card padding="lg" style={{ marginBottom: 24, border: `1px solid ${NAVY}20` }}>
      <div style={{ fontSize: 16, fontWeight: 700, color: NAVY, marginBottom: 2 }}>Describe what you're researching</div>
      <p style={{ fontSize: 12.5, color: TEXT_SECONDARY, marginTop: 0, marginBottom: 12, lineHeight: 1.6 }}>
        Describe a research question, project idea, or problem. Synaptiq will identify the expertise you may need and help you find relevant collaborators.
      </p>

      <textarea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={PLACEHOLDER}
        rows={4}
        style={{ width: "100%", fontSize: 13.5, padding: 10, border: `1px solid ${BRD}`, fontFamily: "inherit", resize: "vertical", marginBottom: 10 }}
      />

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        <Button
          type="button"
          variant="primary"
          disabled={!query.trim() || interpreting}
          onClick={() => runInterpret(true)}
        >
          {interpreting ? "Interpreting…" : `Find expertise${cost ? ` · uses AI (${cost} credits)` : ""}`}
        </Button>
        <Button
          type="button"
          variant="ghost"
          disabled={!query.trim() || interpreting}
          onClick={() => runInterpret(false)}
        >
          Skip AI — basic term matching (free)
        </Button>
      </div>

      {error && <div style={{ marginTop: 10, fontSize: 12.5, color: "#B91C1C" }}>{error}</div>}

      {interpreting && <div style={{ marginTop: 16 }}><LoadingOverlay text="Interpreting your research question…" /></div>}

      {need && !interpreting && (
        <div style={{ marginTop: 20, borderTop: `1px solid ${BRD}`, paddingTop: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
            <div style={{ fontSize: 13.5, fontWeight: 700, color: NAVY }}>Research need</div>
            <div style={{ fontSize: 11, color: TEXT_MUTED }}>
              {source === "ai" ? "AI-interpreted — edit anything below before matching" : "Basic term matching — edit anything below before matching"}
            </div>
          </div>
          {need.concise_problem_statement && (
            <p style={{ fontSize: 12.5, color: TEXT_SECONDARY, marginTop: 4, marginBottom: 14, lineHeight: 1.6 }}>{need.concise_problem_statement}</p>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
            <EditableChipList label="Core expertise" items={need.required_expertise} onChange={(v) => updateNeed("required_expertise", v)} />
            <EditableChipList label="Complementary expertise" items={need.complementary_expertise} onChange={(v) => updateNeed("complementary_expertise", v)} />
            <EditableChipList label="Methods" items={need.useful_methods} onChange={(v) => updateNeed("useful_methods", v)} />
            <EditableChipList label="Keywords" items={need.research_keywords} onChange={(v) => updateNeed("research_keywords", v)} />
          </div>

          <Button type="button" variant="primary" onClick={runMatch} disabled={matching} style={{ marginTop: 6 }}>
            {matching ? "Searching…" : "Find relevant collaborators"}
          </Button>
        </div>
      )}

      {matching && <div style={{ marginTop: 20 }}><LoadingOverlay text="Finding relevant Synaptiq collaborators…" /></div>}

      {matchResult && !matching && (
        <div style={{ marginTop: 24, borderTop: `1px solid ${BRD}`, paddingTop: 18 }}>
          {(matchResult.similar.length + matchResult.complementary.length + matchResult.methods_specialists.length) === 0 ? (
            <EmptyState
              title="No discoverable Synaptiq member currently matches this expertise."
              description="This doesn't mean no one relevant exists — it means the network doesn't yet have a discoverable match. Try refining the research need above, or check back as more researchers join."
            />
          ) : (
            <>
              <ResultGroup title="Best aligned" description="Working directly in the same research area." people={matchResult.similar} />
              <ResultGroup title="Complementary expertise" description="Expertise that fills a different part of this research problem." people={matchResult.complementary} />
              <ResultGroup title="Methods specialists" description="Relevant methods or tools, though not the same core topic." people={matchResult.methods_specialists} />
            </>
          )}

          {matchResult.missing_expertise?.length > 0 && (
            <div style={{ marginTop: 8, padding: 14, background: "#FFFBEB", border: "1px solid #FDE68A" }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#92400E", marginBottom: 4 }}>Expertise still missing</div>
              <p style={{ fontSize: 12, color: "#92400E", margin: 0, lineHeight: 1.6 }}>
                No discoverable Synaptiq member currently matches: {matchResult.missing_expertise.join(", ")}.
              </p>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
