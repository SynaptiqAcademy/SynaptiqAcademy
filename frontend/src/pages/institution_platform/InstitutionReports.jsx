import React, { useState, useEffect, useCallback } from "react";
import { FileText, Download, RefreshCw } from "lucide-react";
import { NAVY, WARM, ACCENT, EMERALD, WHITE, TEXT_SECONDARY } from "@/lib/tokens";
import { AnalyticsLayout } from "@/layouts";
import { Card, Button, Alert, DataTable, Badge } from "@/components/ds";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

const REPORT_COLUMNS = [
  {
    key: "report_type", label: "Report Type",
    render: (v) => <span style={{ color: NAVY, fontWeight: 600, textTransform: "capitalize" }}>{v?.replace(/_/g, " ")}</span>,
  },
  { key: "health_score", label: "Health Score", render: (v) => <span style={{ fontWeight: 800, color: NAVY }}>{v?.toFixed(1) ?? "—"}</span> },
  {
    key: "grade", label: "Grade",
    render: (v) => <Badge color={v === "A" || v === "A+" ? EMERALD : ACCENT}>{v}</Badge>,
  },
  {
    key: "risk_count", label: "Risks",
    render: (v, row) => (
      <span style={{ color: row.critical_count > 0 ? "#dc2626" : TEXT_SECONDARY, fontWeight: row.critical_count > 0 ? 700 : 400 }}>
        {v ?? 0} ({row.critical_count ?? 0} critical)
      </span>
    ),
  },
  {
    key: "generated_at", label: "Generated",
    render: (v) => <span style={{ color: TEXT_SECONDARY, fontSize: 11 }}>{v ? new Date(v).toLocaleString() : "—"}</span>,
  },
];

export default function InstitutionReports() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [success, setSuccess] = useState("");

  const loadReports = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/iip/reports/list`, { headers: authH() });
      if (r.ok) setReports(await r.json());
    } catch (_) {}
    setLoading(false);
  }, []);

  useEffect(() => { loadReports(); }, [loadReports]);

  const generate = async () => {
    setGenerating(true);
    setSuccess("");
    try {
      const r = await fetch(`${API}/api/iip/reports/generate`, {
        method: "POST", headers: { ...authH(), "Content-Type": "application/json" },
        body: JSON.stringify({ report_type: "executive_summary" }),
      });
      if (r.ok) {
        setSuccess("Report generated successfully.");
        loadReports();
      }
    } catch (_) {}
    setGenerating(false);
  };

  const download = async (fmt) => {
    setDownloading(true);
    try {
      const r = await fetch(`${API}/api/iip/reports/download/${fmt}`, { headers: authH() });
      if (r.ok) {
        const blob = await r.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `institution_report.${fmt}`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (_) {}
    setDownloading(false);
  };

  return (
    <AnalyticsLayout
      title="Institution Reports"
      subtitle="Generate and download executive intelligence reports"
      icon={FileText}
      actions={
        <Button variant="primary" onClick={generate} disabled={generating} loading={generating}>
          {!generating && <RefreshCw size={14} />} Generate Report
        </Button>
      }
    >

      {success && (
        <Alert variant="success" style={{ marginBottom: 16 }}>
          {success}
        </Alert>
      )}

      {/* Download options — per-format colored double-border cards with a
          format-specific hover tint have no clean Card/Button variant match
          (Card's `accent` only draws a left border, not a full colored
          border; Button's variants don't take an arbitrary per-instance
          color) — left hand-rolled. */}
      <Card padding="lg" className="mb-5">
        <h3 style={{ margin: "0 0 14px", fontSize: 14, fontWeight: 700, color: NAVY }}>Download Current Report</h3>
        <p style={{ margin: "0 0 16px", fontSize: 13, color: TEXT_SECONDARY }}>
          Generate a real-time executive intelligence report in your preferred format. The report includes health score, faculty metrics, publications, grants, risks, and benchmarks.
        </p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {[
            { fmt: "csv", label: "CSV Export", color: EMERALD, desc: "Structured data for Excel" },
            { fmt: "json", label: "JSON Export", color: "#8b5cf6", desc: "Machine-readable full report" },
          ].map(({ fmt, label, color, desc }) => (
            <button key={fmt} onClick={() => download(fmt)} disabled={downloading} style={{
              background: WHITE, border: `2px solid ${color}`, borderRadius: 10, padding: "12px 20px",
              cursor: downloading ? "not-allowed" : "pointer", textAlign: "left",
              opacity: downloading ? 0.7 : 1, transition: "background 0.1s",
            }}
              onMouseOver={e => e.currentTarget.style.background = `${color}10`}
              onMouseOut={e => e.currentTarget.style.background = WHITE}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <Download size={16} color={color} />
                <span style={{ fontWeight: 700, color, fontSize: 14 }}>{label}</span>
              </div>
              <div style={{ fontSize: 12, color: TEXT_SECONDARY }}>{desc}</div>
            </button>
          ))}
        </div>
      </Card>

      {/* Report history — DataTable owns its own bordered chrome, so the
          tinted header strip sits directly above it rather than nested in a
          second Card. */}
      <div>
        <div style={{ padding: "14px 20px", background: WARM, borderRadius: "10px 10px 0 0" }}>
          <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: NAVY }}>Report History ({reports.length})</h3>
        </div>
        <DataTable
          columns={REPORT_COLUMNS}
          rows={reports}
          loading={loading}
          emptyNode={
            <div style={{ padding: 32, textAlign: "center", color: TEXT_SECONDARY, fontSize: 13 }}>
              No reports generated yet. Click "Generate Report" to create your first executive report.
            </div>
          }
        />
      </div>
    </AnalyticsLayout>
  );
}
