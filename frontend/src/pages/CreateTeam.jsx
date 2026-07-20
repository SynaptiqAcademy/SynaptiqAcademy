/* eslint-disable */
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { DiscoveryLayout } from "@/layouts";
import api from "../lib/api";
import { toast } from "sonner";
import { TEAM_TYPES } from "./Teams";
import { NAVY, WARM, ACCENT } from "@/lib/tokens";
import {
  ArrowLeft, Plus, X, Users, Globe, Lock,
} from "lucide-react";

const BORDER = "#E4E8EF";

const DISCIPLINES = [
  "Artificial Intelligence", "Biology", "Chemistry", "Computer Science",
  "Economics", "Education", "Engineering", "Environmental Science",
  "Healthcare", "History", "Law", "Mathematics", "Medicine",
  "Neuroscience", "Physics", "Political Science", "Psychology",
  "Public Health", "Sociology", "Statistics", "Other",
];

const inputStyle = {
  width: "100%", padding: "9px 12px", border: `1px solid ${BORDER}`,
  fontSize: 13, color: "#374151", outline: "none", boxSizing: "border-box",
  background: "white",
};
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
    <DiscoveryLayout title="Create a Team" subtitle="Start a new research collaboration team.">

      {/* Back */}
      <button
        onClick={() => navigate("/teams")}
        style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", background: "none", border: "none", cursor: "pointer", padding: 0, marginBottom: 28 }}
      >
        <ArrowLeft size={12} strokeWidth={2} /> Back to Teams
      </button>

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
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setType(t.value)}
                  style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6, padding: "14px 8px", border: `2px solid ${active ? t.color : BORDER}`, background: active ? t.color + "10" : "white", cursor: "pointer", transition: "all 0.15s", textAlign: "center" }}
                >
                  <div style={{ width: 30, height: 30, background: t.color + (active ? "22" : "12"), display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Icon size={14} strokeWidth={1.5} style={{ color: t.color }} />
                  </div>
                  <span style={{ fontSize: 10, fontWeight: active ? 700 : 500, color: active ? t.color : "#64748B", lineHeight: 1.2 }}>{t.label}</span>
                </button>
              );
            })}
          </div>
        </section>

        {/* Basic info */}
        <section style={{ background: "white", border: `1px solid ${BORDER}`, padding: 24, marginBottom: 20 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", marginBottom: 20, paddingBottom: 14, borderBottom: `1px solid ${BORDER}`, letterSpacing: "-0.01em" }}>Team Details</div>

          <div style={{ marginBottom: 18 }}>
            <label style={labelStyle}>Team Name *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={`e.g. ${selectedType.label} on Machine Learning in Healthcare`}
              style={inputStyle}
              onFocus={(e) => e.currentTarget.style.borderColor = NAVY + "70"}
              onBlur={(e) => e.currentTarget.style.borderColor = BORDER}
              required
            />
          </div>

          <div style={{ marginBottom: 18 }}>
            <label style={labelStyle}>Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this team working on? What are the goals?"
              rows={4}
              style={{ ...inputStyle, resize: "vertical", lineHeight: 1.6 }}
              onFocus={(e) => e.currentTarget.style.borderColor = NAVY + "70"}
              onBlur={(e) => e.currentTarget.style.borderColor = BORDER}
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 18 }}>
            <div>
              <label style={labelStyle}>Research Discipline</label>
              <select
                value={discipline}
                onChange={(e) => setDiscipline(e.target.value)}
                style={{ ...inputStyle, cursor: "pointer" }}
                onFocus={(e) => e.currentTarget.style.borderColor = NAVY + "70"}
                onBlur={(e) => e.currentTarget.style.borderColor = BORDER}
              >
                <option value="">Select discipline</option>
                {DISCIPLINES.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Institution (optional)</label>
              <input
                value={institution}
                onChange={(e) => setInstitution(e.target.value)}
                placeholder="e.g. MIT, Oxford…"
                style={inputStyle}
                onFocus={(e) => e.currentTarget.style.borderColor = NAVY + "70"}
                onBlur={(e) => e.currentTarget.style.borderColor = BORDER}
              />
            </div>
          </div>

          {/* Keywords */}
          <div style={{ marginBottom: 18 }}>
            <label style={labelStyle}>Keywords</label>
            <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
              <input
                value={keywordInput}
                onChange={(e) => setKeywordInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addKeyword(); } }}
                placeholder="Add a keyword and press Enter"
                style={{ ...inputStyle, flex: 1 }}
                onFocus={(e) => e.currentTarget.style.borderColor = NAVY + "70"}
                onBlur={(e) => e.currentTarget.style.borderColor = BORDER}
              />
              <button type="button" onClick={addKeyword} style={{ padding: "9px 14px", background: WARM, border: `1px solid ${BORDER}`, color: NAVY, cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
                <Plus size={13} strokeWidth={2} />
              </button>
            </div>
            {keywords.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
                {keywords.map((kw) => (
                  <span key={kw} style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, background: WARM, border: `1px solid ${BORDER}`, padding: "3px 9px", color: "#374151" }}>
                    {kw}
                    <button type="button" onClick={() => setKeywords((prev) => prev.filter((k) => k !== kw))} style={{ background: "none", border: "none", cursor: "pointer", color: "#94A3B8", padding: 0, lineHeight: 1, display: "flex" }}>
                      <X size={10} strokeWidth={2} />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Settings */}
        <section style={{ background: "white", border: `1px solid ${BORDER}`, padding: 24, marginBottom: 28 }}>
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
                    <button
                      key={v.value}
                      type="button"
                      onClick={() => setVisibility(v.value)}
                      style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4, padding: "12px 8px", border: `2px solid ${active ? NAVY : BORDER}`, background: active ? WARM : "white", cursor: "pointer" }}
                    >
                      <Icon size={16} strokeWidth={1.5} style={{ color: active ? NAVY : "#94A3B8" }} />
                      <span style={{ fontSize: 12, fontWeight: active ? 700 : 500, color: active ? NAVY : "#64748B" }}>{v.label}</span>
                      <span style={{ fontSize: 10, color: "#94A3B8" }}>{v.sub}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <label style={labelStyle}>Max Members</label>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input
                  type="number"
                  min={2}
                  max={500}
                  value={maxMembers}
                  onChange={(e) => setMaxMembers(Number(e.target.value) || 10)}
                  style={{ ...inputStyle, width: 80 }}
                  onFocus={(e) => e.currentTarget.style.borderColor = NAVY + "70"}
                  onBlur={(e) => e.currentTarget.style.borderColor = BORDER}
                />
                <span style={{ fontSize: 12, color: "#94A3B8" }}>members</span>
              </div>
            </div>
          </div>
        </section>

        {/* Submit */}
        <div style={{ display: "flex", gap: 10 }}>
          <button
            type="submit"
            disabled={busy || !name.trim()}
            style={{ display: "inline-flex", alignItems: "center", gap: 8, background: busy || !name.trim() ? "#94A3B8" : NAVY, color: "white", border: "none", padding: "11px 28px", fontSize: 14, fontWeight: 700, cursor: busy || !name.trim() ? "not-allowed" : "pointer", letterSpacing: "-0.01em" }}
          >
            {busy ? "Creating…" : <>
              <div style={{ width: 18, height: 18, background: selectedType.color + "40", display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
                <TypeIcon size={10} strokeWidth={2} style={{ color: "white" }} />
              </div>
              Create Team
            </>}
          </button>
          <button type="button" onClick={() => navigate("/teams")} style={{ fontSize: 13, color: "#64748B", background: "white", border: `1px solid ${BORDER}`, padding: "11px 20px", cursor: "pointer" }}>
            Cancel
          </button>
        </div>

      </form>
    </DiscoveryLayout>
  );
}
