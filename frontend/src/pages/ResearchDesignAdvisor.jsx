import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FlaskConical, Lock, RotateCcw, Clock, ChevronDown, ChevronUp,
  AlertTriangle, CheckCircle2, XCircle, Target, Layers,
  BarChart2, Users, Database, Shield, BookOpen, Lightbulb,
  ListChecks, ClipboardList, TrendingUp,
} from "lucide-react";
import api from "../lib/api";
import { TID } from "../lib/testIds";
import { NAVY, WARM } from "@/lib/tokens";
import { ErrorState } from "@/components/ds/ErrorState";
import { ResearchLayout } from "@/layouts";
import { AI_NAV_ITEMS } from "@/lib/navItems";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Tag as DsTag } from "@/components/ds/Tag";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { InlineError } from "@/components/ds/Alert";



// ─────────────────────── shared primitives ───────────────────────────────────

function SectionHeader({ icon: Icon, label, color = "#0F2847" }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Icon size={15} strokeWidth={1.5} style={{ color }} />
      <div className="overline" style={{ color }}>{label}</div>
    </div>
  );
}

function Tag({ children, className = "" }) {
  return <DsTag size="sm" className={className}>{children}</DsTag>;
}

function BulletList({ items }) {
  if (!items?.length) return null;
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex gap-2.5 text-sm text-slate-700 leading-relaxed">
          <span className="mt-2 w-1 h-1 rounded-full bg-slate-400 shrink-0" />
          <span>{typeof item === "string" ? item : JSON.stringify(item)}</span>
        </li>
      ))}
    </ul>
  );
}

function LabelValue({ label, value }) {
  if (!value && value !== 0) return null;
  return (
    <div>
      <div className="text-xs text-slate-500 overline mb-0.5">{label}</div>
      <div className="text-sm text-slate-700 leading-relaxed">{String(value)}</div>
    </div>
  );
}

function ExpandCard({ title, subtitle, badge, badgeColor, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const Chev = open ? ChevronUp : ChevronDown;
  return (
    <Card padding="none">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-start justify-between gap-4 px-5 py-4 text-left hover:bg-slate-50 transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="font-serif text-base text-slate-900 leading-snug">{title}</div>
          {subtitle && <div className="text-sm text-slate-500 mt-0.5 leading-snug">{subtitle}</div>}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {badge && (
            <Badge color={badgeColor || "#64748b"} size="sm" className="font-mono">
              {badge}
            </Badge>
          )}
          <Chev size={15} strokeWidth={1.5} className="text-slate-400" />
        </div>
      </button>
      {open && (
        <div className="border-t border-slate-100 px-5 pb-5 pt-4">
          {children}
        </div>
      )}
    </Card>
  );
}

// ─────────────────────── score bar ───────────────────────────────────────────

function ScoreBar({ label, score }) {
  const color = score >= 8 ? "#16a34a" : score >= 6 ? "#d97706" : "#dc2626";
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-500">{label}</span>
        <span className="text-xs font-mono text-slate-600">{score}/10</span>
      </div>
      <div className="h-1.5 bg-slate-100">
        <div className="h-full transition-all" style={{ width: `${score * 10}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

// ─────────────────────── publication score ring ───────────────────────────────

function ScoreRing({ score }) {
  const r = 36;
  const circ = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score));
  const offset = circ * (1 - pct / 100);
  const color = pct >= 80 ? "#16a34a" : pct >= 60 ? "#d97706" : pct >= 40 ? "#ea580c" : "#dc2626";
  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={88} height={88} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={44} cy={44} r={r} fill="none" stroke="#e2e8f0" strokeWidth={6} />
        <circle cx={44} cy={44} r={r} fill="none" stroke={color} strokeWidth={6}
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="butt" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-serif text-xl text-slate-900">{score}</span>
        <span className="text-[9px] text-slate-500 -mt-0.5">/ 100</span>
      </div>
    </div>
  );
}

// ─────────────────────── design type badge ───────────────────────────────────

function DesignBadge({ type }) {
  const map = {
    qualitative:   { color: "#7c3aed", label: "Qualitative" },
    quantitative:  { color: "#2563eb", label: "Quantitative" },
    mixed_methods: { color: "#0F2847", label: "Mixed Methods" },
  };
  const cfg = map[type?.toLowerCase()] || { color: "#64748b", label: type || "Unknown" };
  return (
    <Badge color={cfg.color} className="font-mono">
      {cfg.label}
    </Badge>
  );
}

function PriorityIcon({ level }) {
  if (level === "high") return <XCircle size={14} className="text-red-500 shrink-0 mt-0.5" />;
  if (level === "medium") return <AlertTriangle size={14} className="text-amber-500 shrink-0 mt-0.5" />;
  return <CheckCircle2 size={14} className="text-slate-400 shrink-0 mt-0.5" />;
}

// ─────────────────────── gate view ───────────────────────────────────────────

function GateView() {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="w-14 h-14 border-2 border-slate-900 flex items-center justify-center mx-auto">
          <Lock size={22} strokeWidth={1.5} />
        </div>
        <div>
          <h1 className="font-serif text-2xl text-slate-900 mb-2">Pro Researcher Required</h1>
          <p className="text-slate-600 text-sm leading-relaxed">
            AI Research Design Advisor requires a Pro Researcher or Institution plan.
            Transform any research idea into a defensible, publishable study design.
          </p>
        </div>
        <Card padding="md" className="text-left space-y-2">
          <div className="text-xs overline text-slate-500 mb-3">Included in this advisory</div>
          {[
            "Methodology recommendation with justification",
            "Research framework & theoretical structure",
            "Hypothesis development (H1–H4)",
            "Full variables, sampling & data collection plan",
            "Threats to validity & ethical considerations",
            "Publication readiness score (0–100)",
            "Prioritised improvement plan",
          ].map((f) => (
            <div key={f} className="flex items-center gap-2 text-sm text-slate-700">
              <CheckCircle2 size={13} className="text-[#0F2847] shrink-0" />
              {f}
            </div>
          ))}
        </Card>
        <Button as={Link} to="/pricing" variant="primary" size="lg" className="w-full">
          Upgrade to Pro Researcher
        </Button>
        <p className="text-xs text-slate-500">10 credits per advisory · Refunded if advisory fails</p>
      </div>
    </div>
  );
}

// ─────────────────────── input form view ─────────────────────────────────────

function InputView({ onResult }) {
  const [topic, setTopic] = useState("");
  const [question, setQuestion] = useState("");
  const [objective, setObjective] = useState("");
  const [showOptional, setShowOptional] = useState(false);
  const [discipline, setDiscipline] = useState("");
  const [journalType, setJournalType] = useState("");
  const [methodology, setMethodology] = useState("");
  const [population, setPopulation] = useState("");
  const [sampleSize, setSampleSize] = useState("");
  const [dataSources, setDataSources] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const isGated = error?.status === 402;

  const submit = async (e) => {
    e.preventDefault();
    if (!topic.trim() || !question.trim() || !objective.trim()) {
      setError({ message: "Topic, research question, and research objective are required." });
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const body = {
        topic: topic.trim(),
        research_question: question.trim(),
        research_objective: objective.trim(),
        ...(discipline && { discipline }),
        ...(journalType && { target_journal_type: journalType }),
        ...(methodology && { preferred_methodology: methodology }),
        ...(population && { target_population: population }),
        ...(sampleSize && { expected_sample_size: sampleSize }),
        ...(dataSources && { available_data_sources: dataSources }),
      };
      const { data } = await api.post("/research-design-advisor", body, { timeout: 180000 });
      onResult(data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 402) {
        setError({ status: 402, message: detail?.message || "Plan upgrade required." });
      } else {
        setError({ message: detail?.message || detail || "Advisory failed. Please try again." });
      }
    } finally {
      setLoading(false);
    }
  };

  if (isGated) return <GateView />;

  return (
    <div>
      <div className="max-w-2xl mx-auto">
        {/* header */}
        <div className="mb-8">
          <p className="text-xs text-slate-500">Pro Researcher · 10 credits per advisory</p>
        </div>

        {/* form */}
        <form onSubmit={submit} data-testid={TID.researchDesignForm} className="space-y-5">
          {/* topic */}
          <Input
            label="Research Topic *"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Digital health interventions for Type 2 diabetes self-management"
            maxLength={300}
            data-testid={TID.researchDesignTopic}
          />

          {/* research question */}
          <Textarea
            label="Research Question *"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. To what extent do smartphone-based self-monitoring apps improve glycaemic control in adults with Type 2 diabetes compared to standard care over 12 months?"
            rows={3}
            resize={false}
            maxLength={1000}
            data-testid={TID.researchDesignQuestion}
          />

          {/* research objective */}
          <Textarea
            label="Research Objective *"
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            placeholder="e.g. To evaluate the effectiveness of a smartphone-based self-monitoring intervention on HbA1c levels, medication adherence, and quality of life in adults with Type 2 diabetes over a 12-month period."
            rows={3}
            resize={false}
            maxLength={1000}
            data-testid={TID.researchDesignObjective}
          />

          {/* optional section toggle */}
          <button
            type="button"
            onClick={() => setShowOptional((v) => !v)}
            className="flex items-center gap-2 text-sm text-slate-500 hover:text-[#0F2847] transition-colors"
          >
            {showOptional ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {showOptional ? "Hide" : "Show"} optional refinements
          </button>

          {showOptional && (
            <Card padding="lg" className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="Discipline"
                  value={discipline}
                  onChange={(e) => setDiscipline(e.target.value)}
                  placeholder="e.g. Public Health"
                  maxLength={100}
                />
                <Input
                  label="Target Journal Type"
                  value={journalType}
                  onChange={(e) => setJournalType(e.target.value)}
                  placeholder="e.g. High-impact clinical"
                  maxLength={200}
                />
              </div>
              <Input
                label="Preferred Methodology"
                value={methodology}
                onChange={(e) => setMethodology(e.target.value)}
                placeholder="e.g. RCT, mixed methods, systematic review"
                maxLength={200}
              />
              <Input
                label="Target Population"
                value={population}
                onChange={(e) => setPopulation(e.target.value)}
                placeholder="e.g. Adults aged 40–70 with diagnosed Type 2 diabetes"
                maxLength={300}
              />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="Expected Sample Size"
                  value={sampleSize}
                  onChange={(e) => setSampleSize(e.target.value)}
                  placeholder="e.g. 200 participants"
                  maxLength={100}
                />
                <Input
                  label="Available Data Sources"
                  value={dataSources}
                  onChange={(e) => setDataSources(e.target.value)}
                  placeholder="e.g. Hospital EHR, patient surveys"
                  maxLength={500}
                />
              </div>
            </Card>
          )}

          {error && !isGated && (
            <ErrorState message={error.message} type="generic" />
          )}

          <Button
            type="submit"
            disabled={loading}
            loading={loading}
            data-testid={TID.researchDesignSubmitBtn}
            variant="primary"
            size="lg"
            className="w-full"
          >
            {loading ? "Designing your study… (up to 3 min)" : "Design My Study — 10 Credits"}
          </Button>
        </form>
      </div>
    </div>
  );
}

// ─────────────────────── result view ─────────────────────────────────────────

function VariableTable({ items, columns }) {
  if (!items?.length) return <p className="text-sm text-slate-400">None identified.</p>;
  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <Card key={i} padding="md" variant="ghost" className="!bg-slate-50 border border-slate-100 space-y-2">
          {columns.map(([key, label]) => item[key] ? (
            <LabelValue key={key} label={label} value={item[key]} />
          ) : null)}
        </Card>
      ))}
    </div>
  );
}

function ValiditySection({ threats, label, color }) {
  if (!threats?.length) return null;
  return (
    <div>
      <div className="text-xs overline mb-2" style={{ color }}>{label}</div>
      <div className="space-y-3">
        {threats.map((t, i) => (
          <Card key={i} padding="md" variant="ghost" className="!bg-slate-50 border border-slate-100 space-y-2">
            <div className="font-medium text-sm text-slate-900">{t.threat}</div>
            <LabelValue label="Risk" value={t.description} />
            <LabelValue label="Mitigation" value={t.mitigation} />
          </Card>
        ))}
      </div>
    </div>
  );
}

function ImprovementList({ items, level }) {
  const configs = {
    high:   { color: "#dc2626", bg: "bg-red-50",   border: "border-red-100",   label: "High Priority" },
    medium: { color: "#d97706", bg: "bg-amber-50", border: "border-amber-100", label: "Medium Priority" },
    low:    { color: "#64748b", bg: "bg-slate-50",  border: "border-slate-100", label: "Low Priority" },
  };
  const cfg = configs[level];
  if (!items?.length) return null;
  return (
    <div>
      <div className="text-xs overline mb-2" style={{ color: cfg.color }}>{cfg.label}</div>
      <div className="space-y-2">
        {items.map((item, i) => (
          <Card key={i} padding="md" variant="ghost" className={`${cfg.border} ${cfg.bg} space-y-1.5`}>
            <div className="flex items-start gap-2">
              <PriorityIcon level={level} />
              <div className="font-medium text-sm text-slate-900">{item.action}</div>
            </div>
            {item.reason && (
              <p className="text-xs text-slate-500 leading-relaxed ml-5">{item.reason}</p>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

function ResultView({ data, onReset }) {
  const r = data.review_json || {};
  const design = r.research_design_recommendation || {};
  const framework = r.research_framework || {};
  const objAssess = r.research_objectives_assessment || {};
  const hypoSection = r.hypothesis_development || {};
  const variables = r.variables || {};
  const sampling = r.sampling_strategy || {};
  const dataCol = r.data_collection_strategy || {};
  const analysis = r.data_analysis_plan || {};
  const validity = r.threats_to_validity || {};
  const ethics = r.ethical_considerations || {};
  const pubReady = r.publication_readiness || {};
  const improvement = r.improvement_plan || {};

  const potColor = (pubReady.score >= 80) ? "#16a34a" : (pubReady.score >= 60) ? "#d97706" : "#dc2626";

  return (
    <div data-testid={TID.researchDesignResult}>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* meta bar */}
        <div className="flex items-center justify-between gap-4 pb-6 border-b border-slate-200 flex-wrap">
          <div className="min-w-0">
            <div className="text-sm font-semibold text-slate-900 truncate">{data.topic}</div>
            <p className="text-xs text-slate-500 mt-0.5 truncate">{data.research_question}</p>
          </div>
          <Button onClick={onReset} variant="outline" size="sm" className="shrink-0">
            <RotateCcw size={13} />
            New Advisory
          </Button>
        </div>


        {/* design recommendation + publication score */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card padding="xl" className="md:col-span-2 space-y-4">
            <SectionHeader icon={Target} label="Research Design Recommendation" />
            <div className="flex flex-wrap gap-2">
              <DesignBadge type={design.recommended_design} />
              {design.design_type && (
                <Badge variant="outline" size="sm" className="font-mono">
                  {design.design_type}
                </Badge>
              )}
            </div>
            {design.justification && (
              <p className="text-sm text-slate-700 leading-relaxed">{design.justification}</p>
            )}
            {design.alternative_considered && (
              <Card padding="sm" variant="ghost" className="!bg-slate-50 border border-slate-100">
                <div className="text-xs overline text-slate-500 mb-1">Alternative Considered</div>
                <p className="text-sm text-slate-600">{design.alternative_considered}</p>
              </Card>
            )}
            {design.feasibility_note && (
              <Card padding="sm" variant="ghost" className="!bg-amber-50 border border-amber-100">
                <div className="text-xs overline text-amber-700 mb-1">Feasibility Note</div>
                <p className="text-sm text-amber-800">{design.feasibility_note}</p>
              </Card>
            )}
          </Card>

          {/* publication readiness */}
          <Card padding="xl" className="flex flex-col items-center justify-center text-center gap-3">
            <div className="overline text-slate-500">Publication Readiness</div>
            <ScoreRing score={pubReady.score || 0} />
            {pubReady.recommended_target_journals && (
              <p className="text-xs text-slate-500 leading-snug">{pubReady.recommended_target_journals}</p>
            )}
          </Card>
        </div>

        {/* objectives assessment */}
        <Card padding="xl">
          <SectionHeader icon={ClipboardList} label="Research Objectives Assessment" color="#2563eb" />
          <div className="grid grid-cols-3 gap-4 mb-5">
            <ScoreBar label="Clarity" score={objAssess.clarity_score || 0} />
            <ScoreBar label="Measurability" score={objAssess.measurability_score || 0} />
            <ScoreBar label="Alignment" score={objAssess.alignment_score || 0} />
          </div>
          <div className="space-y-3">
            {objAssess.overall_assessment && (
              <p className="text-sm text-slate-700 leading-relaxed">{objAssess.overall_assessment}</p>
            )}
            {objAssess.refined_objective && (
              <Card padding="md" variant="ghost" className="!bg-slate-50 border border-[#0F2847]">
                <div className="text-xs overline text-[#0F2847] mb-1">Refined Objective</div>
                <p className="text-sm text-slate-700 leading-relaxed italic">{objAssess.refined_objective}</p>
              </Card>
            )}
          </div>
        </Card>

        {/* research framework */}
        <Card padding="xl">
          <SectionHeader icon={Layers} label="Research Framework" color="#7c3aed" />
          <div className="space-y-4">
            <LabelValue label="Conceptual Model" value={framework.conceptual_model} />
            <LabelValue label="Theoretical Structure" value={framework.theoretical_structure} />
            {framework.framework_rationale && (
              <LabelValue label="Framework Rationale" value={framework.framework_rationale} />
            )}
            {framework.key_constructs?.length > 0 && (
              <div>
                <div className="text-xs overline text-slate-500 mb-2">Key Constructs</div>
                <div className="space-y-2">
                  {framework.key_constructs.map((c, i) => (
                    <Card key={i} padding="sm" variant="ghost" className="!bg-slate-50 border border-slate-100 flex gap-3">
                      <Badge variant="outline" size="sm" className="font-mono shrink-0 h-fit capitalize">
                        {c.role}
                      </Badge>
                      <div>
                        <div className="text-sm font-medium text-slate-900">{c.construct}</div>
                        {c.definition && <div className="text-xs text-slate-500 mt-0.5">{c.definition}</div>}
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>

        {/* hypotheses */}
        <Card padding="xl">
          <SectionHeader icon={Lightbulb} label="Hypothesis Development" color="#16a34a" />
          {hypoSection.hypotheses_appropriate === false ? (
            <Card padding="md" variant="ghost" className="!bg-amber-50 border border-amber-100">
              <div className="text-xs overline text-amber-700 mb-1">Hypotheses Not Applicable</div>
              <p className="text-sm text-amber-800">{hypoSection.hypotheses_not_appropriate_reason}</p>
            </Card>
          ) : (
            <div className="space-y-3">
              {(hypoSection.hypotheses || []).map((h, i) => (
                <ExpandCard
                  key={i}
                  title={`${h.id}: ${h.statement}`}
                  badge={h.test_type}
                  defaultOpen={i === 0}
                >
                  <div className="space-y-3">
                    <LabelValue label="Null Hypothesis" value={h.null_hypothesis} />
                    <LabelValue label="Rationale" value={h.rationale} />
                    <LabelValue label="Statistical Test" value={h.test_type} />
                  </div>
                </ExpandCard>
              ))}
            </div>
          )}
        </Card>

        {/* variables */}
        <Card padding="xl">
          <SectionHeader icon={Database} label="Variables" color="#0F2847" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="text-xs overline text-[#0F2847] mb-2">Independent Variables</div>
              <VariableTable items={variables.independent_variables}
                columns={[["variable","Variable"],["operationalisation","Operationalisation"],["measurement_level","Measurement Level"]]} />
            </div>
            <div>
              <div className="text-xs overline text-[#2563eb] mb-2">Dependent Variables</div>
              <VariableTable items={variables.dependent_variables}
                columns={[["variable","Variable"],["operationalisation","Operationalisation"],["measurement_level","Measurement Level"]]} />
            </div>
          </div>
          {(variables.moderators?.length > 0 || variables.mediators?.length > 0 || variables.control_variables?.length > 0) && (
            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-6">
              {variables.moderators?.length > 0 && (
                <div>
                  <div className="text-xs overline text-slate-500 mb-2">Moderators</div>
                  <VariableTable items={variables.moderators}
                    columns={[["variable","Variable"],["rationale","Rationale"]]} />
                </div>
              )}
              {variables.mediators?.length > 0 && (
                <div>
                  <div className="text-xs overline text-slate-500 mb-2">Mediators</div>
                  <VariableTable items={variables.mediators}
                    columns={[["variable","Variable"],["rationale","Rationale"]]} />
                </div>
              )}
              {variables.control_variables?.length > 0 && (
                <div>
                  <div className="text-xs overline text-slate-500 mb-2">Control Variables</div>
                  <VariableTable items={variables.control_variables}
                    columns={[["variable","Variable"],["rationale","Rationale"]]} />
                </div>
              )}
            </div>
          )}
        </Card>

        {/* sampling */}
        <Card padding="xl">
          <SectionHeader icon={Users} label="Sampling Strategy" color="#7c3aed" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <LabelValue label="Target Population" value={sampling.target_population} />
              <LabelValue label="Sampling Method" value={sampling.sampling_method} />
              <LabelValue label="Justification" value={sampling.sampling_method_justification} />
              <LabelValue label="Recommended Sample Size" value={sampling.recommended_sample_size} />
              <LabelValue label="Sample Size Rationale" value={sampling.sample_size_rationale} />
              <LabelValue label="Recruitment Strategy" value={sampling.recruitment_strategy} />
            </div>
            <div className="space-y-4">
              {sampling.inclusion_criteria?.length > 0 && (
                <div>
                  <div className="text-xs overline text-[#16a34a] mb-2">Inclusion Criteria</div>
                  <BulletList items={sampling.inclusion_criteria} />
                </div>
              )}
              {sampling.exclusion_criteria?.length > 0 && (
                <div>
                  <div className="text-xs overline text-[#dc2626] mb-2">Exclusion Criteria</div>
                  <BulletList items={sampling.exclusion_criteria} />
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* data collection */}
        <Card padding="xl">
          <SectionHeader icon={ClipboardList} label="Data Collection Strategy" color="#2563eb" />
          <div className="space-y-4">
            <LabelValue label="Primary Method" value={dataCol.primary_method} />
            <LabelValue label="Justification" value={dataCol.primary_method_justification} />
            {dataCol.secondary_methods?.length > 0 && (
              <LabelValue label="Secondary Methods" value={dataCol.secondary_methods.join(", ")} />
            )}
            <LabelValue label="Estimated Timeline" value={dataCol.timeline_estimate} />
            {dataCol.instruments?.length > 0 && (
              <div>
                <div className="text-xs overline text-slate-500 mb-2">Instruments</div>
                <div className="space-y-3">
                  {dataCol.instruments.map((inst, i) => (
                    <Card key={i} padding="md" variant="ghost" className="!bg-slate-50 border border-slate-100 space-y-2">
                      <div className="font-medium text-sm text-slate-900">{inst.instrument}</div>
                      <LabelValue label="Purpose" value={inst.purpose} />
                      <LabelValue label="Validation" value={inst.validation_note} />
                      <LabelValue label="Duration" value={inst.estimated_duration} />
                    </Card>
                  ))}
                </div>
              </div>
            )}
            {dataCol.data_quality_measures?.length > 0 && (
              <div>
                <div className="text-xs overline text-slate-500 mb-2">Data Quality Measures</div>
                <BulletList items={dataCol.data_quality_measures} />
              </div>
            )}
          </div>
        </Card>

        {/* analysis plan */}
        <Card padding="xl">
          <SectionHeader icon={BarChart2} label="Data Analysis Plan" color="#0F2847" />
          <div className="space-y-4">
            <LabelValue label="Primary Analysis Method" value={analysis.primary_analysis_method} />
            <LabelValue label="Justification" value={analysis.primary_method_justification} />
            <LabelValue label="Software" value={analysis.software_recommendation} />
            <LabelValue label="Reporting Standards" value={analysis.reporting_standards} />
            {analysis.secondary_analyses?.length > 0 && (
              <LabelValue label="Secondary Analyses" value={analysis.secondary_analyses.join(", ")} />
            )}
            {analysis.analysis_steps?.length > 0 && (
              <div>
                <div className="text-xs overline text-slate-500 mb-2">Analysis Steps</div>
                <ol className="space-y-2">
                  {analysis.analysis_steps.map((step, i) => (
                    <li key={i} className="flex gap-3 text-sm text-slate-700">
                      <span className="font-mono text-[#0F2847] shrink-0 w-5">{step.step}.</span>
                      <span>{step.description}</span>
                    </li>
                  ))}
                </ol>
              </div>
            )}
            {analysis.statistical_assumptions?.length > 0 && (
              <div>
                <div className="text-xs overline text-slate-500 mb-2">Statistical Assumptions</div>
                <BulletList items={analysis.statistical_assumptions} />
              </div>
            )}
          </div>
        </Card>

        {/* validity threats */}
        <Card padding="xl">
          <SectionHeader icon={Shield} label="Threats to Validity" color="#dc2626" />
          <div className="space-y-6">
            <ValiditySection threats={validity.internal_validity} label="Internal Validity" color="#dc2626" />
            <ValiditySection threats={validity.external_validity} label="External Validity" color="#d97706" />
            <ValiditySection threats={validity.construct_validity} label="Construct Validity" color="#7c3aed" />
          </div>
        </Card>

        {/* ethics */}
        <Card padding="xl">
          <SectionHeader icon={BookOpen} label="Ethical Considerations" color="#16a34a" />
          <div className="space-y-4">
            {ethics.irb_required != null && (
              <Badge variant={ethics.irb_required ? "danger" : "outline"} className="font-mono">
                {ethics.irb_required ? <XCircle size={12} /> : <CheckCircle2 size={12} />}
                IRB / Ethics approval {ethics.irb_required ? "required" : "may not be required — verify locally"}
              </Badge>
            )}
            <LabelValue label="Consent Approach" value={ethics.consent_approach} />
            <LabelValue label="Data Privacy" value={ethics.data_privacy} />
            <LabelValue label="Vulnerable Populations" value={ethics.vulnerable_populations} />
            {ethics.key_ethical_risks?.length > 0 && (
              <div>
                <div className="text-xs overline text-slate-500 mb-2">Key Ethical Risks</div>
                <div className="space-y-2">
                  {ethics.key_ethical_risks.map((risk, i) => (
                    <Card key={i} padding="sm" variant="ghost" className="!bg-slate-50 border border-slate-100 space-y-1">
                      <div className="text-sm font-medium text-slate-900">{risk.risk}</div>
                      {risk.mitigation && <p className="text-xs text-slate-500">{risk.mitigation}</p>}
                    </Card>
                  ))}
                </div>
              </div>
            )}
            {ethics.additional_considerations && (
              <LabelValue label="Additional Considerations" value={ethics.additional_considerations} />
            )}
          </div>
        </Card>

        {/* publication readiness detail */}
        <Card padding="xl">
          <SectionHeader icon={TrendingUp} label="Publication Readiness Assessment" color={potColor} />
          <div className="space-y-4">
            {pubReady.assessment && (
              <p className="text-sm text-slate-700 leading-relaxed">{pubReady.assessment}</p>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {pubReady.strongest_elements?.length > 0 && (
                <div>
                  <div className="text-xs overline text-[#16a34a] mb-2">Strongest Elements</div>
                  <BulletList items={pubReady.strongest_elements} />
                </div>
              )}
              {pubReady.weakest_elements?.length > 0 && (
                <div>
                  <div className="text-xs overline text-[#dc2626] mb-2">Weakest Elements</div>
                  <BulletList items={pubReady.weakest_elements} />
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* improvement plan */}
        <Card padding="xl">
          <SectionHeader icon={ListChecks} label="Research Design Improvement Plan" color="#0F2847" />
          <div className="space-y-6">
            <ImprovementList items={improvement.high_priority} level="high" />
            <ImprovementList items={improvement.medium_priority} level="medium" />
            <ImprovementList items={improvement.low_priority} level="low" />
          </div>
        </Card>

        {/* footer */}
        <Card padding="none" className="px-6 py-4 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-3">
            <Clock size={11} />
            <span>Analysed {new Date(data.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}</span>
            {data.credits_used != null && <span>· {data.credits_used} credits used</span>}
          </div>
          <div className="flex items-center gap-1.5 text-amber-600">
            <AlertTriangle size={11} />
            <span>Consult your institution's IRB before commencing data collection</span>
          </div>
        </Card>
      </div>
    </div>

  );
}

// ─────────────────────── history item ────────────────────────────────────────

function HistoryItem({ item, onSelect }) {
  return (
    <Card
      onClick={() => onSelect(item.id)}
      data-testid={TID.researchDesignHistoryItem(item.id)}
      padding="md"
      className="w-full text-left space-y-2"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="font-serif text-sm text-slate-900 line-clamp-1">{item.topic}</div>
        {item.publication_score != null && (
          <Badge variant="outline" size="sm" className="shrink-0 font-mono">
            {item.publication_score}/100
          </Badge>
        )}
      </div>
      <p className="text-xs text-slate-500 line-clamp-2">{item.research_question}</p>
      <div className="flex items-center gap-1.5 text-xs text-slate-400">
        <Clock size={10} />
        {new Date(item.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
      </div>
    </Card>
  );
}

// ─────────────────────── main page ───────────────────────────────────────────

export default function ResearchDesignAdvisor() {
  const [view, setView] = useState("input");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    api.get("/research-design-advisor/history")
      .then((r) => setHistory(r.data))
      .catch(() => {})
      .finally(() => setLoadingHistory(false));
  }, []);

  const handleResult = (data) => {
    setResult(data);
    setView("result");
    setHistory((h) => [{ ...data, review_json: undefined }, ...h]);
  };

  const handleHistorySelect = async (id) => {
    try {
      const { data } = await api.get(`/research-design-advisor/${id}`);
      setResult(data);
      setView("result");
    } catch {}
  };

  const handleReset = () => {
    setResult(null);
    setView("input");
  };

  if (view === "result" && result) {
    return (
      <ResearchLayout
        navItems={AI_NAV_ITEMS}
        title="Research Design Advisor"
        subtitle="AI-powered guidance on research methodology, design, and study planning."
      >
      <div style={{ display: "flex", flex: 1, minHeight: 0, overflow: "hidden" }}>
        <div className="flex-1 overflow-y-auto">
          <ResultView data={result} onReset={handleReset} />
        </div>
        {history.length > 1 && (
          <aside className="hidden xl:flex flex-col w-72 border-l border-slate-200 bg-white overflow-y-auto">
            <div className="px-4 py-4 border-b border-slate-100">
              <div className="overline text-slate-500">Past Advisories</div>
            </div>
            <div className="p-3 space-y-2">
              {history.map((item) => (
                <HistoryItem key={item.id} item={item} onSelect={handleHistorySelect} />
              ))}
            </div>
          </aside>
        )}
      </div>
      </ResearchLayout>
    );
  }

  return (
    <ResearchLayout
      navItems={AI_NAV_ITEMS}
      title="Research Design Advisor"
      subtitle="AI-powered guidance on research methodology, design, and study planning."
    >
    <div style={{ display: "flex", flex: 1, minHeight: 0, overflow: "hidden" }}>
      <div className="flex-1 overflow-y-auto">
        <InputView onResult={handleResult} />
      </div>
      {!loadingHistory && history.length > 0 && (
        <aside className="hidden xl:flex flex-col w-72 border-l border-slate-200 bg-white overflow-y-auto">
          <div className="px-4 py-4 border-b border-slate-100">
            <div className="overline text-slate-500">Past Advisories</div>
          </div>
          <div className="p-3 space-y-2">
            {history.map((item) => (
              <HistoryItem key={item.id} item={item} onSelect={handleHistorySelect} />
            ))}
          </div>
        </aside>
      )}
    </div>
    </ResearchLayout>

  );
}
