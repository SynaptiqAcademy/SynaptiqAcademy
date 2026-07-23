import React, { useCallback, useEffect, useRef, useState } from "react";
import api from "../lib/api";
import { Link } from "react-router-dom";
import { TID } from "../lib/testIds";
import { toast } from "sonner";
import { BRD, BRDH, NAVY, WARM } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";
import {
  Archive, Plus, FileText, Database, FileCheck2, BookOpen,
  ExternalLink, Search, X, ChevronRight, ArrowRight,
  Layers, ClipboardCheck, Coins, FolderOpen, Tag,
  File, Image, Code, Microscope,
} from "lucide-react";
import { EmptyState } from "@/components/ds/EmptyState";
import { SkeletonCard } from "@/components/ds/LoadingState";
import { SearchBar, FilterChip } from "@/components/ds/SearchBar";

// ─── Brand tokens ─────────────────────────────────────────────────────────────
const EMRL  = "#059669";

// ─── Asset type system ────────────────────────────────────────────────────────
const TYPES = [
  { key: "Document",   label: "Document",   icon: FileText,   color: NAVY,      bg: "rgba(15,40,71,0.07)"  },
  { key: "Dataset",    label: "Dataset",    icon: Database,   color: "#059669", bg: "rgba(5,150,105,0.07)" },
  { key: "Template",   label: "Template",   icon: FileCheck2, color: "#7C3AED", bg: "rgba(124,58,237,0.07)"},
  { key: "Literature", label: "Literature", icon: BookOpen,   color: "#B45309", bg: "rgba(180,83,9,0.07)"  },
];

const getType = (key) => TYPES.find((t) => t.key === key) || TYPES[0];

// ─── Lifecycle nav ────────────────────────────────────────────────────────────
function LifecycleNav({ current }) {
  const steps = [
    { to: "/manuscripts",        label: "Writing"      },
    { to: "/reviews",            label: "Peer Review"  },
    { to: "/publication-hub",    label: "Publishing"   },
    { to: "/repository",         label: "Archive"      },
    { to: "/grant-applications", label: "Applications" },
  ];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
      {steps.map((s, i) => {
        const isCur = s.to === current;
        return (
          <React.Fragment key={s.to}>
            {i > 0 && <ChevronRight size={10} strokeWidth={1.5} style={{ color: "#CBD5E1", flexShrink: 0 }} />}
            <Link
              to={s.to}
              style={{
                fontSize: 11, fontWeight: isCur ? 700 : 400,
                color: isCur ? NAVY : "#94A3B8",
                padding: "3px 7px",
                background: isCur ? "rgba(15,40,71,0.07)" : "transparent",
                borderRadius: 3, textDecoration: "none", whiteSpace: "nowrap",
              }}
            >
              {s.label}
            </Link>
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─── Asset card ───────────────────────────────────────────────────────────────
function AssetCard({ item }) {
  const [hov, setHov] = useState(false);
  const type = getType(item.type);

  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: "#fff",
        border: `1px solid ${hov ? BRDH : BRD}`,
        padding: "20px",
        display: "flex", flexDirection: "column",
        boxShadow: hov ? "0 4px 20px rgba(15,23,42,0.09)" : "none",
        transition: "border-color 150ms, box-shadow 150ms",
        height: "100%", boxSizing: "border-box",
      }}
    >
      {/* Type icon + type badge */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
        <div style={{ width: 36, height: 36, background: type.bg, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
          <type.icon size={16} strokeWidth={1.5} style={{ color: type.color }} />
        </div>
        <span style={{
          fontSize: 9, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase",
          color: type.color, background: type.bg, border: `1px solid ${type.color}20`,
          padding: "2px 7px",
        }}>
          {item.type}
        </span>
      </div>

      {/* Title */}
      <h3 style={{ fontSize: 14, fontWeight: 600, color: hov ? NAVY : "#0F172A", margin: "0 0 6px", lineHeight: 1.4, transition: "color 150ms" }}>
        {item.title}
      </h3>

      {/* Description */}
      {item.description && (
        <p style={{ fontSize: 12, color: "#64748B", margin: "0 0 10px", lineHeight: 1.6, flex: 1, display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
          {item.description}
        </p>
      )}

      {/* Tags */}
      {(item.tags || []).length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 12 }}>
          {item.tags.map((t) => (
            <span key={t} style={{ fontSize: 9, fontFamily: "monospace", background: WARM, border: `1px solid ${BRD}`, padding: "2px 6px", color: "#64748B" }}>
              {t}
            </span>
          ))}
        </div>
      )}

      {/* Footer */}
      <div style={{ marginTop: "auto", paddingTop: 12, borderTop: `1px solid ${BRD}`, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div style={{ fontSize: 10, fontFamily: "monospace", color: "#94A3B8" }}>{item.owner_name || "—"}</div>
          {item.created_at && (
            <div style={{ fontSize: 9, fontFamily: "monospace", color: "#CBD5E1" }}>
              {new Date(item.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
            </div>
          )}
        </div>
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 600, color: NAVY, textDecoration: "none" }}
          >
            Open <ExternalLink size={10} strokeWidth={1.5} />
          </a>
        )}
      </div>
    </div>
  );
}

// ─── Add item form ────────────────────────────────────────────────────────────
function AddItemForm({ onCreated, onCancel }) {
  const [form, setForm] = useState({ title: "", type: "Document", description: "", url: "", tags: "" });
  const [busy, setBusy] = useState(false);
  const titleRef = useRef(null);
  useEffect(() => { titleRef.current?.focus(); }, []);

  const create = async () => {
    if (!form.title.trim()) return;
    setBusy(true);
    try {
      await api.post("/repository", {
        title: form.title, type: form.type,
        description: form.description, url: form.url,
        tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
      });
      toast.success("Item added to repository");
      onCreated();
    } catch { toast.error("Failed to add item"); }
    finally { setBusy(false); }
  };

  const inp = {
    width: "100%", boxSizing: "border-box",
    padding: "9px 12px", border: `1px solid ${BRD}`,
    fontSize: 13, color: "#0F172A", background: "#fff",
    outline: "none", fontFamily: "inherit",
  };

  return (
    <div style={{ background: "#fff", border: `1px solid ${BRD}`, padding: "24px 28px", maxWidth: 640, marginBottom: 28 }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94A3B8", marginBottom: 16 }}>
        Add to Repository
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <input
          ref={titleRef}
          data-testid={TID.repositoryNewTitle}
          placeholder="Title *"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          onKeyDown={(e) => e.key === "Enter" && create()}
          style={inp}
        />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} style={{ ...inp }}>
            {TYPES.map((t) => <option key={t.key}>{t.key}</option>)}
          </select>
          <input
            placeholder="URL (optional)"
            value={form.url}
            onChange={(e) => setForm({ ...form, url: e.target.value })}
            style={inp}
          />
        </div>
        <input
          placeholder="Tags (comma-separated)"
          value={form.tags}
          onChange={(e) => setForm({ ...form, tags: e.target.value })}
          style={inp}
        />
        <textarea
          placeholder="Description"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          rows={3}
          style={{ ...inp, resize: "vertical", lineHeight: 1.6 }}
        />
      </div>
      <div style={{ marginTop: 18, display: "flex", gap: 10 }}>
        <button
          data-testid={TID.repositoryNewSubmit}
          onClick={create}
          disabled={busy || !form.title.trim()}
          style={{
            background: busy || !form.title.trim() ? "#94A3B8" : NAVY,
            color: "#fff", border: "none", padding: "9px 20px",
            fontSize: 13, fontWeight: 600,
            cursor: busy || !form.title.trim() ? "not-allowed" : "pointer",
          }}
        >
          {busy ? "Adding…" : "Add to repository"}
        </button>
        <button
          onClick={onCancel}
          style={{ background: "transparent", color: "#64748B", border: `1px solid ${BRD}`, padding: "9px 16px", fontSize: 13, cursor: "pointer" }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ─── Type stats row ───────────────────────────────────────────────────────────
function TypeStats({ items }) {
  if (!items.length) return null;
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 28 }}>
      {TYPES.map(({ key, label, icon: Icon, color, bg }) => {
        const count = items.filter((i) => i.type === key).length;
        return (
          <div key={key} style={{ background: "#fff", border: `1px solid ${BRD}`, padding: "14px 18px", display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 32, height: 32, background: bg, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <Icon size={14} strokeWidth={1.5} style={{ color }} />
            </div>
            <div>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#0F172A", fontFamily: "Georgia, serif", lineHeight: 1 }}>{count}</div>
              <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", color: "#94A3B8", marginTop: 2 }}>{label}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function Repository() {
  const [items, setItems] = useState(null);
  const [filter, setFilter] = useState("");
  const [q, setQ]           = useState("");
  const [showNew, setShowNew] = useState(false);

  const load = useCallback(async () => {
    try {
      const params = {};
      if (filter) params.item_type = filter;
      if (q)      params.q = q;
      const { data } = await api.get("/repository", { params });
      setItems(data || []);
    } catch { setItems([]); }
  }, [filter, q]);

  // Refetch automatically on filter change; `q` (free-text search) is applied
  // only when the user explicitly triggers search(), not on every keystroke.
  const loadRef = useRef(load);
  useEffect(() => { loadRef.current = load; }, [load]);
  useEffect(() => { loadRef.current(); }, [filter]);

  const search = () => load();

  const repoActions = (
    <div style={{ display: "flex", gap: 8 }}>
      <Link to="/manuscripts" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", textDecoration: "none", padding: "8px 14px", border: `1px solid ${BRD}`, background: "#fff" }}>
        <FileText size={12} strokeWidth={1.5} /> Manuscripts
      </Link>
      <button
        data-testid={TID.repositoryCreateBtn}
        onClick={() => setShowNew(!showNew)}
        style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 600, color: "#fff", background: NAVY, border: "none", padding: "8px 16px", cursor: "pointer" }}
      >
        <Plus size={13} strokeWidth={1.5} /> Add Item
      </button>
    </div>
  );

  return (
    <ResearchLayout
      title="Repository"
      subtitle="Your shared archive of documents, datasets, templates, and literature. Everything your research team needs in one searchable place."
      nav={<LifecycleNav current="/repository" />}
      actions={repoActions}
    >
      <div data-testid={TID.repository} style={{ paddingBottom: 64 }}>
        {/* Type stats (only when loaded and non-empty) */}
        {items && items.length > 0 && !filter && !q && <TypeStats items={items} />}

        {/* Add form */}
        {showNew && (
          <AddItemForm
            onCreated={() => { setShowNew(false); load(); }}
            onCancel={() => setShowNew(false)}
          />
        )}

        {/* Search + filter bar */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 24, flexWrap: "wrap" }}>
          <div style={{ flex: "0 0 280px" }}>
            <SearchBar
              data-testid={TID.repositorySearch}
              value={q}
              onChange={setQ}
              placeholder="Search the repository…"
              onClear={() => { setQ(""); load(); }}
              size="sm"
            />
          </div>
          <button
            onClick={search}
            style={{ padding: "8px 14px", fontSize: 12, fontWeight: 600, color: NAVY, background: "#fff", border: `1px solid ${BRD}`, cursor: "pointer", fontFamily: "inherit" }}
          >
            Search
          </button>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <FilterChip
              label="All"
              active={!filter}
              onClick={() => setFilter("")}
            />
            {TYPES.map(({ key }) => (
              <FilterChip
                key={key}
                label={key}
                active={filter === key}
                onClick={() => setFilter(filter === key ? "" : key)}
              />
            ))}
          </div>
        </div>

        {/* Grid */}
        {items === null ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
            {[1,2,3,4,5,6].map((i) => (
              <SkeletonCard key={i} rows={3} />
            ))}
          </div>
        ) : items.length === 0 ? (
          filter || q ? (
            <EmptyState
              icon={<Search />}
              title="No items match your search"
              action={
                <button onClick={() => { setFilter(""); setQ(""); }} style={{ fontSize: 12, color: NAVY, background: "none", border: "none", cursor: "pointer", textDecoration: "underline" }}>
                  Clear filters
                </button>
              }
              size="sm"
            />
          ) : (
            <EmptyState
              icon={<Archive />}
              title="Your repository is empty"
              description="Store documents, datasets, templates, and literature in one searchable archive shared across your team."
              action={
                <button
                  data-testid={TID.repositoryCreateBtn}
                  onClick={() => setShowNew(true)}
                  style={{ display: "inline-flex", alignItems: "center", gap: 8, background: NAVY, color: "#fff", border: "none", padding: "10px 20px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
                >
                  <Plus size={14} strokeWidth={1.5} /> Add your first item
                </button>
              }
              size="lg"
              dashed={false}
            />
          )
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 16 }}>
            {items.map((it) => <AssetCard key={it.id} item={it} />)}
          </div>
        )}

        {/* Lifecycle footer */}
        {items !== null && items.length > 0 && (
          <div style={{ marginTop: 48, paddingTop: 24, borderTop: `1px solid ${BRD}`, display: "flex", gap: 16, flexWrap: "wrap" }}>
            {[
              { to: "/manuscripts",        label: "Manuscripts",      icon: FileText },
              { to: "/publication-hub",    label: "Publication Hub",  icon: Layers },
              { to: "/reviews",            label: "Peer Reviews",     icon: ClipboardCheck },
              { to: "/grant-applications", label: "Applications",     icon: Coins },
            ].map(({ to, label, icon: Icon }) => (
              <Link key={to} to={to} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#64748B", textDecoration: "none" }}>
                <Icon size={12} strokeWidth={1.5} /> {label}
                <ArrowRight size={10} strokeWidth={1.5} />
              </Link>
            ))}
          </div>
        )}
      </div>
    </ResearchLayout>
  );
}
