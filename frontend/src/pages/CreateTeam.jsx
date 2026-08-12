/* eslint-disable */
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ResearchLayout } from "@/layouts";
import api from "../lib/api";
import { toast } from "sonner";
import { TEAM_TYPES } from "./Teams";
import { NAVY, WARM, ACCENT } from "@/lib/tokens";
import {
  ArrowLeft, Plus, X, Users, Globe, Lock,
} from "lucide-react";
import { Card } from "@/components/ds/Card";
import { Tag } from "@/components/ds/Tag";
import { Button } from "@/components/ds/Button";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";

const BORDER = "#E4E8EF";

const DISCIPLINES = [
  "Artificial Intelligence", "Biology", "Chemistry", "Computer Science",
  "Economics", "Education", "Engineering", "Environmental Science",
  "Healthcare", "History", "Law", "Mathematics", "Medicine",
  "Neuroscience", "Physics", "Political Science", "Psychology",
  "Public Health", "Sociology", "Statistics", "Other",
];

const labelStyle = {
  display: "block", fontSize: 11, fontWeight: 700, letterSpacing: "0.07em",
  textTransform: "uppercase", color: "#64748B", marginBottom: 6,
};

export default function CreateTeam() {
  const navigate = useNavigate();

  const [name, setName]               = useState("");
  const [type, setType]               = useState("research_paper");
  const [description, setDescription] = useState("");
  const [discipline, setDiscipline]   = useState("");
  const [visibility, setVisibility]   = useState("public");
  const [maxMembers, setMaxMembers]   = useState(10);
  const [keywordInput, setKeywordInput] = useState("");
  const [keywords, setKeywords]       = useState([]);
  const [institution, setInstitution] = useState("");
  const [busy, setBusy]               = useState(false);

  const addKeyword = () => {
    const kw = keywordInput.trim();
    if (kw && !keywords.includes(kw) && keywords.length < 12) {
      setKeywords((prev) => [...prev, kw]);
      setKeywordInput("");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) { toast.error("Team name is required"); return; }
    setBusy(true);
    try {
      const { data } = await api.post("/network/groups", {
        name: name.trim(),
        type,
        description: description.trim(),
        discipline,
        keywords,
        visibility,
        max_members: maxMembers,
        institution: institution.trim(),
      });
      toast.success("Team created");
      const id = data._id || data.id;
      navigate(`/teams/${id}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to create team");
    } finally {
      setBusy(false);
    }
  };

  const selectedType = TEAM_TYPES.find((t) => t.value === type) || TEAM_TYPES[1];
  const TypeIcon = selectedType.icon;

  return (
    <ResearchLayout title="Create a Team" subtitle="Start a new research collaboration team.">

      {/* Back */}
      <Button variant="link" size="sm" onClick={() => navigate("/teams")} className="mb-7">
        <ArrowLeft size={12} strokeWidth={2} /> Back to Teams
      </Button>

      <form onSubmit={handleSubmit}>

        {/* Team type picker */}
        <section style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", marginBottom: 4, letterSpacing: "-0.01em" }}>Team Type</div>
          <div style={{ fontSize: 12, color: "#94A3B8", marginBottom: 16 }}>Choose the purpose of your team. This determines what features are highlighted.</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
            {TEAM_TYPES.filter((t) => t.value !== "").map((t) => {
              const active = type === t.value;
              const Icon = t.icon;
              return (
                <Card
                  key={t.value}
                  padding="sm"
                  onClick={() => setType(t.value)}
                  style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6, border: `2px solid ${active ? t.color : BORDER}`, background: active ? t.color + "10" : "white", textAlign: "center" }}
                >
                  <div style={{ width: 30, height: 30, background: t.color + (active ? "22" : "12"), display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Icon size={14} strokeWidth={1.5} style={{ color: t.color }} />
                  </div>
                  <span style={{ fontSize: 10, fontWeight: active ? 700 : 500, color: active ? t.color : "#64748B", lineHeight: 1.2 }}>{t.label}</span>
                </Card>
              );
            })}
          </div>
        </section>

        {/* Basic info */}
        <Card padding="lg" className="mb-5">
          <div style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", marginBottom: 20, paddingBottom: 14, borderBottom: `1px solid ${BORDER}`, letterSpacing: "-0.01em" }}>Team Details</div>

          <div style={{ marginBottom: 18 }}>
            <Input
              label="Team Name *"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={`e.g. ${selectedType.label} on Machine Learning in Healthcare`}
              required
            />
          </div>

          <div style={{ marginBottom: 18 }}>
            <Textarea
              label="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this team working on? What are the goals?"
              rows={4}
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 18 }}>
            <FormSelect
              label="Research Discipline"
              value={discipline}
              onChange={(e) => setDiscipline(e.target.value)}
            >
              <option value="">Select discipline</option>
              {DISCIPLINES.map((d) => <option key={d} value={d}>{d}</option>)}
            </FormSelect>
            <Input
              label="Institution (optional)"
              value={institution}
              onChange={(e) => setInstitution(e.target.value)}
              placeholder="e.g. MIT, Oxford…"
            />
          </div>

          {/* Keywords */}
          <div style={{ marginBottom: 18 }}>
            <label style={labelStyle}>Keywords</label>
            <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
              <Input
                wrapperClassName="flex-1"
                value={keywordInput}
                onChange={(e) => setKeywordInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addKeyword(); } }}
                placeholder="Add a keyword and press Enter"
              />
              <Button type="button" variant="subtle" onClick={addKeyword} aria-label="Add keyword">
                <Plus size={13} strokeWidth={2} />
              </Button>
            </div>
            {keywords.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                {keywords.map((kw) => (
                  <Tag key={kw} onRemove={() => setKeywords((prev) => prev.filter((k) => k !== kw))}>
                    {kw}
                  </Tag>
                ))}
              </div>
            )}
          </div>
        </Card>

        {/* Settings */}
        <Card padding="lg" className="mb-7">
          <div style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", marginBottom: 20, paddingBottom: 14, borderBottom: `1px solid ${BORDER}`, letterSpacing: "-0.01em" }}>Settings</div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <label style={labelStyle}>Visibility</label>
              <div style={{ display: "flex", gap: 8 }}>
                {[
                  { value: "public",  label: "Public",  icon: Globe,   sub: "Anyone can join" },
                  { value: "private", label: "Private", icon: Lock,    sub: "Invite only" },
                ].map((v) => {
                  const active = visibility === v.value;
                  const Icon = v.icon;
                  return (
                    <Card
                      key={v.value}
                      padding="sm"
                      onClick={() => setVisibility(v.value)}
                      style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4, border: `2px solid ${active ? NAVY : BORDER}`, background: active ? WARM : "white" }}
                    >
                      <Icon size={16} strokeWidth={1.5} style={{ color: active ? NAVY : "#94A3B8" }} />
                      <span style={{ fontSize: 12, fontWeight: active ? 700 : 500, color: active ? NAVY : "#64748B" }}>{v.label}</span>
                      <span style={{ fontSize: 10, color: "#94A3B8" }}>{v.sub}</span>
                    </Card>
                  );
                })}
              </div>
            </div>

            <div>
              <label style={labelStyle}>Max Members</label>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Input
                  type="number"
                  min={2}
                  max={500}
                  value={maxMembers}
                  onChange={(e) => setMaxMembers(Number(e.target.value) || 10)}
                  className="w-20"
                />
                <span style={{ fontSize: 12, color: "#94A3B8" }}>members</span>
              </div>
            </div>
          </div>
        </Card>

        {/* Submit */}
        <div style={{ display: "flex", gap: 10 }}>
          <Button
            type="submit"
            disabled={busy || !name.trim()}
            loading={busy}
          >
            <div style={{ width: 18, height: 18, background: selectedType.color + "40", display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
              <TypeIcon size={10} strokeWidth={2} style={{ color: "white" }} />
            </div>
            Create Team
          </Button>
          <Button type="button" variant="ghost" onClick={() => navigate("/teams")}>
            Cancel
          </Button>
        </div>

      </form>
    </ResearchLayout>
  );
}
