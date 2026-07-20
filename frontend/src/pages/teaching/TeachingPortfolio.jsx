/* eslint-disable */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Award, Plus, Star, Edit2, Trash2 } from "lucide-react";
import api from "../../lib/api";
import { toast } from "sonner";
import { EmptyState } from "../../components/ds/EmptyState";
import { Spinner } from "../../components/ds/LoadingState";
import { Button } from "@/components/ds/Button";
import { Card } from "@/components/ds/Card";
import { Badge } from "@/components/ds/Badge";
import { Tag } from "@/components/ds/Tag";
import { Input } from "@/components/ds/Input";
import { Textarea } from "@/components/ds/Textarea";
import { FormSelect } from "@/components/ds/FormSelect";
import { Checkbox } from "@/components/ds/Form";
import { NAVY } from "@/lib/tokens";
import { ResearchLayout } from "@/layouts";

const SUBJECTS   = ["Mathematics","Economics","Management","Computer Science","Medicine","Engineering","Psychology","Education","Sciences","Humanities","Law","Business","Other"];
const ITEM_TYPES = ["lesson","course","assessment","achievement","award","reflection","resource","publication"];
const FILTER_TYPES = ["", ...ITEM_TYPES];

// Arbitrary hex per type via Badge's `color` escape hatch — the 8 item types
// don't map cleanly onto the 6 fixed semantic Badge variants (distinct blue/
// indigo/purple/amber/yellow/emerald/slate/red original palette).
const TYPE_BADGE_COLOR = {
  lesson:       "#1d4ed8",
  course:       "#4338ca",
  assessment:   "#7e22ce",
  achievement:  "#b45309",
  award:        "#a16207",
  reflection:   "#047857",
  resource:     "#475569",
  publication:  "#b91c1c",
};

const EMPTY_FORM = {
  title: "", item_type: "lesson", description: "", subject: "",
  audience: "", date: "", evidence_url: "", tags: [], featured: false,
};

function PortfolioCard({ item, onEdit, onDelete, onToggleFeatured }) {
  return (
    <Card padding="lg" className={item.featured ? "border-[#0F2847]" : ""}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge color={TYPE_BADGE_COLOR[item.item_type]} size="sm">
            {item.item_type}
          </Badge>
          {item.featured && (
            <Badge variant="warning" size="sm">
              <Star size={9} fill="currentColor" /> Featured
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <Button variant="ghost" size="icon" onClick={() => onToggleFeatured(item)} title={item.featured ? "Remove from featured" : "Feature this"}
            className={item.featured ? "text-amber-500" : "text-slate-300 hover:text-amber-400"}>
            <Star size={13} strokeWidth={1.5} fill={item.featured ? "currentColor" : "none"} />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => onEdit(item)} className="text-slate-400 hover:text-slate-700">
            <Edit2 size={12} strokeWidth={1.5} />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => onDelete(item)} className="text-slate-300 hover:text-red-400">
            <Trash2 size={12} strokeWidth={1.5} />
          </Button>
        </div>
      </div>
      <h3 className="font-serif text-lg text-slate-900 leading-snug mb-1">{item.title}</h3>
      {item.subject && <div className="text-xs text-slate-500 mb-2">{item.subject}{item.date ? ` · ${item.date}` : ""}</div>}
      {item.description && <p className="text-sm text-slate-700 leading-relaxed line-clamp-3">{item.description}</p>}
      {item.evidence_url && (
        <a href={item.evidence_url} target="_blank" rel="noopener noreferrer"
          className="mt-3 inline-block text-xs text-[#0F2847] border-b border-[#0F2847] hover:opacity-70">
          View evidence →
        </a>
      )}
      {(item.tags || []).length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {item.tags.map((t) => (
            <Tag key={t} size="sm">{t}</Tag>
          ))}
        </div>
      )}
    </Card>
  );
}

function ItemForm({ initial, onSave, onCancel, saving }) {
  const [f, setF] = useState(initial || EMPTY_FORM);

  return (
    <form onSubmit={(e) => { e.preventDefault(); onSave(f); }} className="space-y-4">
      <div className="grid sm:grid-cols-2 gap-4">
        <Input
          label="Title *"
          required
          value={f.title}
          onChange={(e) => setF({ ...f, title: e.target.value })}
          placeholder="e.g. Introduction to Research Methods — 12-week course"
          wrapperClassName="sm:col-span-2"
        />
        <FormSelect
          label="Type"
          value={f.item_type}
          onChange={(e) => setF({ ...f, item_type: e.target.value })}
        >
          {ITEM_TYPES.map((t) => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
        </FormSelect>
        <FormSelect
          label="Subject"
          value={f.subject}
          onChange={(e) => setF({ ...f, subject: e.target.value })}
        >
          <option value="">Not specified</option>
          {SUBJECTS.map((s) => <option key={s}>{s}</option>)}
        </FormSelect>
        <Input
          label="Audience"
          value={f.audience}
          onChange={(e) => setF({ ...f, audience: e.target.value })}
          placeholder="e.g. Undergraduate students"
        />
        <Input
          label="Date"
          type="date"
          value={f.date}
          onChange={(e) => setF({ ...f, date: e.target.value })}
        />
        <Textarea
          label="Description"
          rows={3}
          value={f.description}
          onChange={(e) => setF({ ...f, description: e.target.value })}
          placeholder="Describe this portfolio item — what you did, what you achieved, what students learned."
          wrapperClassName="sm:col-span-2"
        />
        <Input
          label="Evidence URL"
          value={f.evidence_url}
          onChange={(e) => setF({ ...f, evidence_url: e.target.value })}
          placeholder="Link to syllabus, slides, recordings, or other evidence"
          wrapperClassName="sm:col-span-2"
        />
        <div className="sm:col-span-2">
          <Checkbox
            id="featured"
            checked={f.featured}
            onChange={(e) => setF({ ...f, featured: e.target.checked })}
            label="Feature this item at the top of your portfolio"
          />
        </div>
      </div>
      <div className="flex gap-3">
        <Button type="submit" loading={saving}>
          {saving ? "Saving…" : "Save item"}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  );
}

export default function TeachingPortfolio() {
  const [items, setItems]         = useState([]);
  const [loading, setLoading]     = useState(true);
  const [filterType, setFilterType] = useState("");
  const [showAdd, setShowAdd]     = useState(false);
  const [editItem, setEditItem]   = useState(null);
  const [saving, setSaving]       = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/teaching/portfolio", {
        params: filterType ? { item_type: filterType } : {},
      });
      setItems(data || []);
    } catch (_) {
      toast.error("Failed to load portfolio");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterType]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAdd = async (f) => {
    setSaving(true);
    try {
      await api.post("/teaching/portfolio", f);
      toast.success("Portfolio item added");
      setShowAdd(false);
      load();
    } catch (_) {
      toast.error("Failed to add item");
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = async (f) => {
    if (!editItem) return;
    setSaving(true);
    try {
      await api.patch(`/teaching/portfolio/${editItem.id}`, f);
      toast.success("Item updated");
      setEditItem(null);
      load();
    } catch (_) {
      toast.error("Failed to update item");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (item) => {
    if (!window.confirm("Remove this portfolio item?")) return;
    try {
      await api.delete(`/teaching/portfolio/${item.id}`);
      toast.success("Item removed");
      load();
    } catch (_) {
      toast.error("Failed to remove item");
    }
  };

  const handleToggleFeatured = async (item) => {
    try {
      await api.patch(`/teaching/portfolio/${item.id}`, { featured: !item.featured });
      load();
    } catch (_) {
      toast.error("Failed to update");
    }
  };

  const featured = items.filter((i) => i.featured);
  const rest     = items.filter((i) => !i.featured);

  return (
    <ResearchLayout
      title="Teaching Portfolio"
      subtitle="Document your teaching philosophy, course designs, achievements, and evidence of impact. Build a portfolio that speaks for itself."
      icon={Award}
      actions={
        <Button
          variant={showAdd ? "primary" : "outline"}
          onClick={() => { setShowAdd(!showAdd); setEditItem(null); }}
        >
          <Plus size={14} strokeWidth={1.5} /> Add item
        </Button>
      }
    >

      {/* Add form */}
      {showAdd && !editItem && (
        <Card variant="flush" padding="lg">
          <div className="overline mb-4">New portfolio item</div>
          <ItemForm onSave={handleAdd} onCancel={() => setShowAdd(false)} saving={saving} />
        </Card>
      )}

      {/* Edit form */}
      {editItem && (
        <Card variant="flush" padding="lg" className="border-[#0F2847]/20 bg-slate-50">
          <div className="overline mb-4">Edit portfolio item</div>
          <ItemForm initial={editItem} onSave={handleEdit} onCancel={() => setEditItem(null)} saving={saving} />
        </Card>
      )}

      {/* Filter */}
      <div className="flex items-center gap-4">
        <div className="overline">Portfolio items</div>
        <FormSelect
          size="sm"
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="!w-auto"
        >
          {FILTER_TYPES.map((t) => <option key={t} value={t}>{t || "All types"}</option>)}
        </FormSelect>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-slate-400 py-8">
          <Spinner size={14} /> Loading…
        </div>
      )}

      {!loading && items.length === 0 && (
        <EmptyState
          icon={<Award />}
          title="Your portfolio is empty"
          description="Add teaching evidence — courses designed, lessons delivered, assessments built, awards received, or reflections on your practice."
          action={
            <Button onClick={() => setShowAdd(true)}>
              Add first item
            </Button>
          }
        />
      )}

      {/* Featured items */}
      {featured.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Star size={12} strokeWidth={1.5} className="text-amber-500" fill="currentColor" />
            <div className="overline">Featured</div>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {featured.map((item) => (
              <PortfolioCard key={item.id} item={item}
                onEdit={(i) => { setEditItem(i); setShowAdd(false); }}
                onDelete={handleDelete}
                onToggleFeatured={handleToggleFeatured} />
            ))}
          </div>
        </div>
      )}

      {/* Rest */}
      {rest.length > 0 && (
        <div>
          {featured.length > 0 && <div className="overline mb-4">All items</div>}
          <div className="grid md:grid-cols-2 gap-4">
            {rest.map((item) => (
              <PortfolioCard key={item.id} item={item}
                onEdit={(i) => { setEditItem(i); setShowAdd(false); }}
                onDelete={handleDelete}
                onToggleFeatured={handleToggleFeatured} />
            ))}
          </div>
        </div>
      )}
    </ResearchLayout>
  );
}
