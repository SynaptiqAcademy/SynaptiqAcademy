/**
 * OrcidSettings — connect / disconnect / sync / view publications.
 *
 * Renders gracefully when ORCID is not configured: shows the "configure" notice
 * but the panel still appears. Once configured + connected, surfaces ORCID iD,
 * sync history, and a "Sync now" action.
 */
import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../../lib/api";
import { toast } from "sonner";
import OrcidBadge from "./OrcidBadge";
import { Card } from "@/components/ds/Card";
import { Section } from "@/components/ds/Section";
import { Button } from "@/components/ds/Button";
import { Badge } from "@/components/ds/Badge";
import { TYPE, NAVY, WARM, BRD, TEXT_MUTED, TEXT_SECONDARY, EMERALD } from "@/lib/tokens";
import {
  CheckCircle2, RefreshCw, Loader2, Link as LinkIcon, Unplug, Sparkles, AlertCircle, Clock,
} from "lucide-react";

function StatTile({ label, testId, children, sub }) {
  return (
    <div
      data-testid={testId}
      style={{ background: WARM, border: `1px solid ${BRD}`, borderRadius: 10, padding: "12px 14px" }}
    >
      <div style={{ ...TYPE.label, marginBottom: 6 }}>{label}</div>
      {children}
      {sub && <div style={{ ...TYPE.meta, marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

const ORCID_ERROR_MESSAGES = {
  cancelled: "You cancelled the ORCID sign-in.",
  already_linked_to_other_account: "This ORCID iD is already linked to a different SYNAPTIQ account.",
};

export default function OrcidSettings() {
  const [config, setConfig] = useState(null);
  const [status, setStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    const orcidError = searchParams.get("orcid_error");
    const orcidConnected = searchParams.get("orcid") === "connected";
    if (orcidError) {
      toast.error(ORCID_ERROR_MESSAGES[orcidError] || "ORCID sign-in failed. Please try again.");
      setSearchParams((p) => { p.delete("orcid_error"); return p; }, { replace: true });
    } else if (orcidConnected) {
      toast.success("ORCID connected");
      setSearchParams((p) => { p.delete("orcid"); return p; }, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const load = async () => {
    try {
      const [c, s, h] = await Promise.all([
        api.get("/orcid/config"),
        api.get("/orcid/status"),
        api.get("/orcid/sync-history"),
      ]);
      setConfig(c.data); setStatus(s.data); setHistory(h.data || []);
    } catch (e) {}
  };
  useEffect(() => { load(); }, []);

  const connect = async () => {
    try {
      const { data } = await api.get("/orcid/authorize?mode=link");
      window.location.href = data.authorization_url;
    } catch (e) { toast.error(e?.response?.data?.detail || "ORCID is not configured"); }
  };

  const disconnect = async () => {
    if (!confirm("Disconnect ORCID? Imported publications will be retained.")) return;
    try {
      await api.post("/orcid/disconnect");
      toast.success("ORCID disconnected");
      load();
    } catch (e) { toast.error("Failed"); }
  };

  const sync = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/orcid/sync");
      toast.success(`Sync ok: +${data.publications_imported} new, ~${data.publications_updated} updated`);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Sync failed"); }
    finally { setBusy(false); }
  };

  const enrich = async () => {
    setEnriching(true);
    try {
      const { data } = await api.post("/orcid/enrich-openalex");
      toast.success(`OpenAlex enrichment: ${data.enriched} updated`);
      load();
    } catch (e) { toast.error("Failed"); }
    finally { setEnriching(false); }
  };

  if (!config || !status) {
    return (
      <Card padding="xl" data-testid="orcid-settings">
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: TEXT_MUTED }}>
          <Loader2 size={13} className="animate-spin" /> Loading…
        </div>
      </Card>
    );
  }

  return (
    <Card padding="xl" data-testid="orcid-settings">
      <Section
        gap="lg"
        action={!config.configured && (
          <span data-testid="orcid-not-configured">
            <Badge variant="warning"><AlertCircle size={10} /> Admin setup pending</Badge>
          </span>
        )}
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <svg width={16} height={16} viewBox="0 0 256 256" aria-hidden style={{ flexShrink: 0 }}>
                <circle cx="128" cy="128" r="128" fill="#A6CE39" />
                <g fill="#FFF"><path d="M86.3 186.2H70.9V79.1h15.4v107.1zM78.6 64.6c-4.9 0-9-4.1-9-9 0-5 4.1-9 9-9 5 0 9 4 9 9 0 4.9-4 9-9 9zM108.9 79.1h41.6c39.6 0 57 28.3 57 53.6 0 27.5-21.5 53.6-56.8 53.6h-41.8V79.1zm15.4 93.3h24.5c34.9 0 42.9-26.5 42.9-39.7 0-21.5-13.7-39.7-43.7-39.7h-23.7v79.4z" /></g>
              </svg>
              <span style={{ ...TYPE.label, color: NAVY }}>ORCID — Academic Identity</span>
              <Badge variant="neutral" size="sm">{config.environment}</Badge>
            </div>
            <h3 style={{ ...TYPE.h3, marginTop: 8 }}>
              {status.connected ? "Connected" : "Connect your ORCID iD"}
            </h3>
            <p style={{ ...TYPE.bodySm, marginTop: 4, maxWidth: 520 }}>
              Verify your identity, auto-import publications, and unlock the ORCID Verified badge across the platform.
            </p>
          </div>
        </div>

        <div className="grid sm:grid-cols-3 gap-3" data-testid="orcid-status-block">
          <StatTile label="ORCID iD" testId="orcid-id-value">
            {status.orcid_id ? (
              <OrcidBadge orcidId={status.orcid_id} size="md" showId testId="orcid-id-badge" />
            ) : <span style={{ ...TYPE.body, color: TEXT_MUTED }}>—</span>}
          </StatTile>
          <StatTile
            label="Verification"
            sub={status.verified_at ? new Date(status.verified_at).toLocaleDateString() : undefined}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 6, ...TYPE.h4 }}>
              {status.verified ? (
                <><CheckCircle2 size={14} style={{ color: EMERALD }} /> Verified</>
              ) : <span style={{ color: TEXT_SECONDARY, fontWeight: 600 }}>Not verified</span>}
            </div>
          </StatTile>
          <StatTile
            label="Publications imported"
            sub={`Last sync: ${status.last_sync_at ? new Date(status.last_sync_at).toLocaleString() : "never"}`}
          >
            <div data-testid="orcid-pub-count" style={TYPE.numberLg}>{status.publications_imported}</div>
          </StatTile>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {!status.connected ? (
            <button
              data-testid="orcid-connect-btn"
              onClick={connect}
              disabled={!config.configured}
              aria-disabled={!config.configured}
              className="inline-flex items-center justify-center gap-2 font-medium rounded-btn h-9 px-4 text-[13px] text-white transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ background: EMERALD }}
              onMouseEnter={(e) => { if (config.configured) e.currentTarget.style.background = "#047857"; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = EMERALD; }}
            >
              <LinkIcon size={13} /> Connect with ORCID
            </button>
          ) : (
            <>
              <Button data-testid="orcid-sync-btn" onClick={sync} loading={busy} variant="primary" size="md">
                {!busy && <RefreshCw size={13} />} Sync now
              </Button>
              <Button data-testid="orcid-enrich-btn" onClick={enrich} loading={enriching} variant="ghost" size="sm">
                {!enriching && <Sparkles size={12} />} Enrich via OpenAlex
              </Button>
              <Button data-testid="orcid-disconnect-btn" onClick={disconnect} variant="ghost" size="sm" className="ml-auto !text-[#8A1538] !border-[rgba(138,21,56,0.25)] hover:!bg-[rgba(138,21,56,0.06)]">
                <Unplug size={12} /> Disconnect
              </Button>
            </>
          )}
          {!config.configured && status.connected === false && (
            <span style={{ ...TYPE.caption }}>Admin needs to add ORCID_CLIENT_ID + ORCID_CLIENT_SECRET to backend env.</span>
          )}
        </div>

        {history.length > 0 && (
          <div data-testid="orcid-sync-history">
            <div style={{ ...TYPE.label, marginBottom: 8, display: "flex", alignItems: "center", gap: 5 }}>
              <Clock size={11} /> Sync history
            </div>
            <div style={{ border: `1px solid ${BRD}`, borderRadius: 10, overflow: "hidden", maxHeight: 240, overflowY: "auto" }}>
              {history.slice().reverse().map((h, i) => (
                <div
                  key={i}
                  data-testid={`orcid-history-row-${i}`}
                  className="flex-wrap"
                  style={{
                    display: "flex", alignItems: "center", gap: 12, padding: "10px 14px", fontSize: 12,
                    borderTop: i > 0 ? `1px solid ${BRD}` : "none", background: i % 2 ? WARM : "transparent",
                  }}
                >
                  <span style={{ color: TEXT_MUTED, fontVariantNumeric: "tabular-nums", flexShrink: 0 }}>
                    {new Date(h.finished_at).toLocaleString()}
                  </span>
                  <Badge variant="neutral" size="sm">{h.trigger}</Badge>
                  <span style={{ color: "#0f172a" }}>
                    +{h.publications_imported} new · ~{h.publications_updated} updated · ↔ {h.publications_linked} linked
                  </span>
                  {h.errors?.length > 0 && <Badge variant="danger" size="sm">{h.errors.length} errors</Badge>}
                  {h.ok && <CheckCircle2 size={13} style={{ color: EMERALD, marginLeft: "auto", flexShrink: 0 }} />}
                </div>
              ))}
            </div>
          </div>
        )}
      </Section>
    </Card>
  );
}
