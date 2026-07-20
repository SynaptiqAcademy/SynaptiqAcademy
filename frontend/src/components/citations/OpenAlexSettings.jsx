/**
 * OpenAlexSettings — manage OpenAlex author profile, sync citations, and view metrics.
 *
 * Data sources:
 *   GET  /api/orcid/status           → orcid connection state
 *   POST /api/reputation/sync-openalex → pull author metrics from OpenAlex
 *   POST /api/citations/sync          → refresh citation counts (all publications)
 *   GET  /api/citations/dashboard     → summary stats
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../../lib/api";
import { toast } from "sonner";
import { Card } from "@/components/ds/Card";
import { Section } from "@/components/ds/Section";
import { Button } from "@/components/ds/Button";
import { Badge } from "@/components/ds/Badge";
import { TYPE, NAVY, WARM, BRD, TEXT_MUTED, EMERALD, AMBER } from "@/lib/tokens";
import {
  RefreshCw, Loader2, ExternalLink, BarChart2, BookOpen,
  ChevronRight, AlertCircle, CheckCircle2, Database,
} from "lucide-react";

function MetricCell({ label, value, sub }) {
  return (
    <div style={{ background: WARM, border: `1px solid ${BRD}`, borderRadius: 10, padding: "12px 14px" }}>
      <div style={{ ...TYPE.label, marginBottom: 6 }}>{label}</div>
      <div style={{ ...TYPE.h3, fontFamily: "Georgia, serif" }}>{value ?? "—"}</div>
      {sub && <div style={{ ...TYPE.meta, marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

export default function OpenAlexSettings() {
  const [orcidStatus, setOrcidStatus]   = useState(null);
  const [dashboard, setDashboard]       = useState(null);
  const [openalex, setOpenalex]         = useState(null);
  const [syncingAuthor, setSyncingAuthor]       = useState(false);
  const [syncingCitations, setSyncingCitations] = useState(false);
  const [loading, setLoading]           = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [os, db] = await Promise.allSettled([
        api.get("/orcid/status"),
        api.get("/citations/dashboard", { silentGate: true }),
      ]);
      if (os.status === "fulfilled") setOrcidStatus(os.value.data);
      if (db.status === "fulfilled") setDashboard(db.value.data);
    } catch (_) {}
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const syncAuthor = async () => {
    setSyncingAuthor(true);
    try {
      const { data } = await api.post("/reputation/sync-openalex");
      setOpenalex(data.openalex);
      toast.success(`OpenAlex synced — h-index: ${data.openalex?.h_index ?? 0}, ${data.openalex?.citations?.toLocaleString() ?? 0} citations`);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "OpenAlex author sync failed");
    } finally { setSyncingAuthor(false); }
  };

  const syncCitations = async () => {
    setSyncingCitations(true);
    try {
      const { data } = await api.post("/citations/sync");
      toast.success(`Citation sync: ${data.synced} publications updated, +${data.new_citations} new citations`);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Citation sync failed");
    } finally { setSyncingCitations(false); }
  };

  const sum = dashboard?.summary || {};
  // After a manual "sync author profile" the fresh openalex metrics are stored in state;
  // otherwise fall back to the author object already embedded in the dashboard payload.
  const author = dashboard?.author || {};
  const oam = openalex || {
    openalex_id:  author.openalex_id,
    works_count:  sum.works_count,
    citations:    author.total_citations ?? sum.total_citations,
    h_index:      author.h_index ?? sum.h_index,
    i10_index:    author.i10_index ?? sum.i10_index,
  };

  return (
    <Card padding="xl" data-testid="openalex-settings">
      <Section gap="lg">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Database size={13} style={{ color: TEXT_MUTED }} />
              <span style={{ ...TYPE.label, color: NAVY }}>OpenAlex — Research Intelligence</span>
            </div>
            <h3 style={{ ...TYPE.h3, marginTop: 8 }}>Citation &amp; Impact Metrics</h3>
            <p style={{ ...TYPE.bodySm, marginTop: 4, maxWidth: 520 }}>
              Publication citations, h-index, and research impact sourced from{" "}
              <a href="https://openalex.org" target="_blank" rel="noreferrer" style={{ color: NAVY, display: "inline-flex", alignItems: "center", gap: 3 }}>
                OpenAlex <ExternalLink size={9} />
              </a>
              . Connect ORCID to auto-match your author profile.
            </p>
          </div>
          {!orcidStatus?.connected && (
            <Link to="/academic-passport" style={{ flexShrink: 0 }}>
              <Badge variant="warning"><AlertCircle size={10} /> Connect ORCID first</Badge>
            </Link>
          )}
        </div>

        {loading ? (
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: TEXT_MUTED }}>
            <Loader2 size={13} className="animate-spin" /> Loading…
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-3" data-testid="openalex-author-metrics">
            <MetricCell
              label="OpenAlex Author ID"
              value={oam.openalex_id
                ? <a href={`https://openalex.org/authors/${(oam.openalex_id || "").split("/").pop()}`}
                    target="_blank" rel="noreferrer"
                    style={{ fontFamily: "monospace", fontSize: 12, color: NAVY, display: "inline-flex", alignItems: "center", gap: 4 }}>
                    {(oam.openalex_id || "").split("/").pop()}
                    <ExternalLink size={10} />
                  </a>
                : <span style={{ color: TEXT_MUTED, fontSize: 14 }}>Not linked</span>}
            />
            <MetricCell
              label="Total Publications"
              value={(oam.works_count ?? "—")}
              sub={orcidStatus?.connected ? `ORCID: ${orcidStatus.publications_imported ?? 0} imported` : undefined}
            />
            <MetricCell
              label="Total Citations"
              value={(oam.citations ?? sum.total_citations ?? "—")?.toLocaleString?.() ?? "—"}
            />
            <MetricCell
              label="h-index"
              value={oam.h_index ?? sum.h_index ?? "—"}
              sub={oam.i10_index != null ? `i10-index: ${oam.i10_index}` : undefined}
            />
          </div>
        )}

        {sum.last_synced && (
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: TEXT_MUTED }}>
            <CheckCircle2 size={12} style={{ color: EMERALD }} />
            Last sync: {new Date(sum.last_synced).toLocaleString()}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <Button data-testid="openalex-sync-author-btn" onClick={syncAuthor} loading={syncingAuthor} variant="primary" size="md">
            {!syncingAuthor && <RefreshCw size={13} />} Sync author profile
          </Button>
          <Button data-testid="openalex-sync-citations-btn" onClick={syncCitations} loading={syncingCitations} variant="ghost" size="md">
            {!syncingCitations && <BarChart2 size={13} />} Sync citation counts
          </Button>
          <Link to="/citations" style={{ marginLeft: "auto" }}>
            <Button as="span" variant="ghost" size="md">
              <BookOpen size={13} /> Full analytics <ChevronRight size={13} />
            </Button>
          </Link>
        </div>

        {sum.works_count > 0 && (
          <div className="grid sm:grid-cols-3 gap-3" style={{ borderTop: `1px solid ${BRD}`, paddingTop: 16 }}>
            <div>
              <div style={TYPE.label}>Publications tracked</div>
              <div style={{ ...TYPE.h3, marginTop: 4 }}>{sum.works_count}</div>
            </div>
            {sum.this_month != null && (
              <div>
                <div style={TYPE.label}>New citations (30d)</div>
                <div style={{ ...TYPE.h3, marginTop: 4, color: EMERALD }}>+{sum.this_month}</div>
              </div>
            )}
            {sum.unread_alerts > 0 && (
              <div>
                <div style={TYPE.label}>Unread alerts</div>
                <div style={{ ...TYPE.h3, marginTop: 4, color: AMBER }}>{sum.unread_alerts}</div>
              </div>
            )}
          </div>
        )}
      </Section>
    </Card>
  );
}
