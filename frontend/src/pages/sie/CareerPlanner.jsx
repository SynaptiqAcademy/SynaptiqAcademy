import React, { useState, useEffect, useCallback } from "react";
import { ChevronRight, CheckCircle } from "lucide-react";
import { NAVY, WARM, BRD, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { AIWorkspaceLayout } from "@/layouts";
import { SIE_NAV_ITEMS } from "@/lib/navItems";
import { Card, Badge, Input, FormSelect, Button, NavTabs, Spinner, H4 } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

const POSITIONS = [
  "phd_student","postdoc","research_associate","assistant_professor",
  "associate_professor","full_professor","research_scientist","senior_researcher",
  "principal_investigator","industry_researcher","other",
];

function ReadinessBar({ req }) {
  const color = req.met ? EMERALD : req.pct >= 60 ? "#f59e0b" : ACCENT;
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 12, color: NAVY, fontWeight: 500 }}>{req.label}</span>
        <span style={{ fontSize: 12, fontWeight: 700, color }}>{req.pct}%</span>
      </div>
      <div style={{ height: 6, background: `${NAVY}15`, borderRadius: 3 }}>
        <div style={{ width: `${req.pct}%`, height: "100%", background: color, borderRadius: 3, transition: "width 0.3s" }} />
      </div>
      {req.threshold > 0 && <div style={{ fontSize: 11, color: TEXT_SECONDARY, marginTop: 2 }}>{req.current}/{req.threshold} {req.met ? "✓" : ""}</div>}
    </div>
  );
}

export default function CareerPlanner() {
  const [profile, setProfile] = useState(null);
  const [readiness, setReadiness] = useState(null);
  const [roadmap, setRoadmap] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [tab, setTab] = useState("readiness");
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [pr, rr, rm] = await Promise.all([
        fetch(`${API}/api/sie/career/profile`, { headers: authH() }),
        fetch(`${API}/api/sie/career/readiness`, { headers: authH() }),
        fetch(`${API}/api/sie/career/roadmap`, { headers: authH() }),
      ]);
      if (pr.ok) { const d = await pr.json(); setProfile(d); setForm(d); }
      if (rr.ok) setReadiness(await rr.json());
      if (rm.ok) setRoadmap(await rm.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setSaving(true);
    try {
      const r = await fetch(`${API}/api/sie/career/profile`, {
        method: "PUT", headers: { ...authH(), "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (r.ok) { setProfile(await r.json()); setEditing(false); load(); }
    } catch (_) {}
    setSaving(false);
  };

  if (loading) return (
    <div style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Spinner size={32} color={ACCENT} />
    </div>
  );

  const readinessScore = readiness?.readiness_score ?? 0;
  const readyColor = readinessScore >= 75 ? EMERALD : readinessScore >= 50 ? "#f59e0b" : ACCENT;

  return (
    <AIWorkspaceLayout
      title="Career Planner"
      subtitle="AI-powered academic career planning and progression tracker."
      navItems={SIE_NAV_ITEMS}
    >

      {editing && (
        <Card padding="xl" style={{ marginBottom: 20 }}>
          <H4 style={{ marginBottom: 16 }}>Career Profile</H4>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
            {[
              { label: "Current Position", key: "current_position", type: "select", options: POSITIONS },
              { label: "Target Position", key: "target_position", type: "select", options: POSITIONS },
              { label: "Institution", key: "institution", type: "text" },
              { label: "Department", key: "department", type: "text" },
              { label: "Years in Position", key: "years_in_position", type: "number" },
              { label: "Target Timeline (years)", key: "target_timeline_years", type: "number" },
              { label: "PhD Students Supervised", key: "phd_students_supervised", type: "number" },
              { label: "Teaching Courses", key: "teaching_courses", type: "number" },
            ].map(({ label, key, type, options }) => (
              <div key={key}>
                {type === "select" ? (
                  <FormSelect
                    label={label}
                    value={form[key] || ""}
                    onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  >
                    {options.map(o => <option key={o} value={o}>{o.replace(/_/g, " ")}</option>)}
                  </FormSelect>
                ) : (
                  <Input
                    label={label}
                    type={type}
                    value={form[key] || ""}
                    onChange={e => setForm(f => ({ ...f, [key]: type === "number" ? Number(e.target.value) : e.target.value }))}
                  />
                )}
              </div>
            ))}
          </div>
          <Button onClick={save} loading={saving} disabled={saving}>
            {saving ? "Saving…" : "Save Profile"}
          </Button>
        </Card>
      )}

      <div style={{ marginBottom: 16 }}>
        <NavTabs
          variant="pill"
          tabs={[
            { id: "readiness", label: "Promotion Readiness" },
            { id: "roadmap", label: "Career Roadmap" },
          ]}
          active={tab}
          onChange={setTab}
        />
      </div>

      {tab === "readiness" && readiness && (
        <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 20 }}>
          <Card padding="lg" style={{ textAlign: "center" }}>
            <div style={{ fontSize: 48, fontWeight: 900, color: readyColor }}>{readinessScore}</div>
            <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginBottom: 8 }}>Readiness Score</div>
            {readiness.ready_for_promotion && (
              <Badge variant="success" style={{ justifyContent: "center", width: "100%" }}>
                <CheckCircle size={13} style={{ marginRight: 4 }} /> Ready
              </Badge>
            )}
            <div style={{ marginTop: 12, fontSize: 12, color: TEXT_SECONDARY }}>
              {readiness.current_position?.replace(/_/g, " ")} → {readiness.next_position?.replace(/_/g, " ")}
            </div>
          </Card>
          <Card padding="lg">
            <H4 style={{ marginBottom: 14 }}>Promotion Requirements</H4>
            {(readiness.requirements || []).map((req, i) => <ReadinessBar key={i} req={req} />)}
          </Card>
        </div>
      )}

      {tab === "roadmap" && roadmap && (
        <Card padding="lg">
          <H4 style={{ marginBottom: 16 }}>
            Career Path: {roadmap.current_position?.replace(/_/g, " ")} → {roadmap.target_position?.replace(/_/g, " ")} ({roadmap.timeline_years} years)
          </H4>
          <div style={{ display: "flex", gap: 0, flexWrap: "wrap" }}>
            {(roadmap.path || []).map((step, i) => (
              <React.Fragment key={i}>
                {/* Path step tile: kept hand-rolled — Card's fixed white
                    background can't reproduce the WARM/accent-tinted step
                    tiles that distinguish the current step from future ones */}
                <div style={{ background: i === 0 ? `${ACCENT}15` : WARM, border: `1px solid ${i === 0 ? ACCENT : BRD}`, borderRadius: 10, padding: "12px 14px", minWidth: 160 }}>
                  <div style={{ fontSize: 12, fontWeight: 800, color: i === 0 ? ACCENT : NAVY, marginBottom: 4 }}>{step.label}</div>
                  <div style={{ fontSize: 11, color: TEXT_SECONDARY, marginBottom: 6 }}>~{step.estimated_years}yr{i === 0 ? " (now)" : ""}</div>
                  {(step.key_requirements || []).map((r, j) => (
                    <div key={j} style={{ fontSize: 11, color: "#334155", marginBottom: 2 }}>• {r}</div>
                  ))}
                </div>
                {i < roadmap.path.length - 1 && (
                  <div style={{ display: "flex", alignItems: "center", padding: "0 4px" }}>
                    <ChevronRight size={16} color={TEXT_SECONDARY} />
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        </Card>
      )}
    </AIWorkspaceLayout>
  );
}
