import React, { useState } from "react";
import { toast } from "sonner";
import { BookOpen, Search, RefreshCw, Loader2, ChevronDown, ExternalLink } from "lucide-react";
import { Card } from "@/components/ds/Card";
import { Section } from "@/components/ds/Section";
import { Button } from "@/components/ds/Button";
import { EmptyState } from "@/components/ds/EmptyState";
import { SkeletonCard } from "@/components/ds/LoadingState";
import { NAVY, BRD, WARM, TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY } from "@/lib/tokens";
import api from "@/lib/api";

const PUB_TYPE_LABELS = {
  "journal-article": "Journal Article", "conference-paper": "Conference Paper",
  "book-chapter": "Book Chapter", "book": "Book", "preprint": "Preprint",
  "thesis": "Thesis", "review": "Review",
};

function PublicationRow({ pub }) {
  const [expanded, setExpanded] = useState(false);
  const typeLabel = PUB_TYPE_LABELS[pub.type] || pub.type || "Publication";
  const isRecent = pub.year >= 2020;

  return (
    <div
      onClick={() => setExpanded((v) => !v)}
      style={{
        display: "flex", gap: 14, padding: "14px 16px", cursor: "pointer",
        border: `1px solid ${BRD}`, borderLeft: `3px solid ${isRecent ? "#0891B2" : BRD}`,
      }}
    >
      <div style={{ flexShrink: 0, minWidth: 46, textAlign: "center" }}>
        {pub.year && (
          <div style={{ fontSize: 13, fontWeight: 700, fontFamily: "monospace", color: isRecent ? "#0891B2" : TEXT_MUTED }}>{pub.year}</div>
        )}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: TEXT_PRIMARY, lineHeight: 1.45, marginBottom: 4 }}>{pub.title}</div>
        {(pub.authors || []).length > 0 && (
          <div style={{ fontSize: 11, color: TEXT_MUTED, marginBottom: 4 }}>
            {pub.authors.slice(0, 5).join(", ")}{pub.authors.length > 5 ? ` +${pub.authors.length - 5}` : ""}
          </div>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          {pub.journal && <span style={{ fontSize: 11, color: TEXT_SECONDARY, fontStyle: "italic" }}>{pub.journal}</span>}
          <span style={{ fontSize: 10, padding: "1px 6px", background: "#EFF6FF", color: NAVY, fontWeight: 600 }}>{typeLabel}</span>
        </div>
        {expanded && pub.abstract && (
          <p style={{ fontSize: 12, color: TEXT_SECONDARY, lineHeight: 1.65, margin: "8px 0 0", borderTop: `1px solid ${BRD}`, paddingTop: 8 }}>{pub.abstract}</p>
        )}
      </div>
      <div style={{ flexShrink: 0, textAlign: "right", display: "flex", flexDirection: "column", gap: 4, alignItems: "flex-end" }}>
        {pub.citations > 0 && <div style={{ fontSize: 13, fontWeight: 700, fontFamily: "monospace" }}>{pub.citations}<span style={{ fontSize: 10, fontWeight: 400, color: TEXT_MUTED, marginLeft: 3 }}>cites</span></div>}
        {pub.doi && (
          <a href={`https://doi.org/${pub.doi}`} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()} style={{ display: "inline-flex", alignItems: "center", gap: 3, fontSize: 10, color: "#0891B2", fontWeight: 600, textDecoration: "none" }}>
            DOI <ExternalLink size={9} />
          </a>
        )}
        <ChevronDown size={12} style={{ color: "#CBD5E1", transform: expanded ? "rotate(180deg)" : "none", transition: "transform 150ms" }} />
      </div>
    </div>
  );
}

/**
 * PublicationsPanel — searchable publications list + ORCID sync.
 * Merges Profile.jsx's PublicationsSection + PublicationCard.
 */
export function PublicationsPanel({ pubs, loading, query, onQuery, onRefresh }) {
  const [syncing, setSyncing] = useState(false);

  const importOrcid = async () => {
    setSyncing(true);
    try {
      const { data } = await api.post("/orcid/sync");
      const imported = data.publications_imported ?? data.imported ?? 0;
      toast.success(`ORCID synced — ${imported} publications imported`);
      onRefresh();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "ORCID sync failed");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <Card padding="xl">
      <Section
        title="Publications"
        action={
          <Button size="sm" variant="ghost" onClick={importOrcid} disabled={syncing}>
            {syncing ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />} Sync ORCID
          </Button>
        }
      >
        <div style={{ position: "relative", marginBottom: 14 }}>
          <Search size={12} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: TEXT_MUTED }} />
          <input
            type="search"
            value={query}
            onChange={(e) => onQuery(e.target.value)}
            placeholder="Search publications by title, journal, keyword…"
            style={{ width: "100%", padding: "8px 12px 8px 30px", border: `1px solid ${BRD}`, fontSize: 12, outline: "none", boxSizing: "border-box" }}
          />
        </div>

        {loading && <SkeletonCard rows={3} />}
        {!loading && (!pubs || pubs.results.length === 0) && (
          <EmptyState
            icon={<BookOpen />}
            title={query ? "No publications match your search" : "No publications on record"}
            description={!query ? "Sync ORCID to automatically import your publications." : undefined}
          />
        )}
        {!loading && pubs && pubs.results.length > 0 && (
          <>
            {pubs.total > pubs.results.length && (
              <div style={{ fontSize: 11, color: TEXT_MUTED, marginBottom: 10 }}>Showing {pubs.results.length} of {pubs.total}</div>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {pubs.results.map((pub) => <PublicationRow key={pub.id} pub={pub} />)}
            </div>
          </>
        )}
      </Section>
    </Card>
  );
}

export default PublicationsPanel;
