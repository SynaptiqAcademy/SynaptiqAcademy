import React, { useState, useEffect, useCallback } from "react";
import { TrendingUp } from "lucide-react";
import { NAVY, ACCENT, EMERALD, TEXT_SECONDARY } from "@/lib/tokens";
import { InstitutionLayout } from "@/layouts";
import { Card, NavTabs, Tag, Callout, Spinner } from "@/components/ds";
import { fetchApi } from "@/lib/api";

const API = process.env.REACT_APP_API_URL || "";
const authH = () => ({ Authorization: `Bearer ${localStorage.getItem("token")}` });

// The dual-source (historical vs. forecast) bar chart with a dividing rule,
// per-bar hover tooltips, and a fading forecast-bar opacity ramp has no
// equivalent in ds/'s BarChart (single dataset, no divider/tooltip/opacity-ramp
// support) — left hand-rolled.
function ForecastPanel({ title, data, valueKey, color }) {
  if (!data) return null;
  const historical = data.historical || [];
  const forecasts  = data.forecasts  || [];
  const allValues  = [...historical.map(h => h[valueKey === "total" ? "total" : valueKey] ?? h.total ?? 0), ...forecasts.map(f => f[`projected_${valueKey === "total" ? "" : valueKey}`] ?? f.projected ?? f.projected_faculty ?? f.projected_approved ?? f.projected_citations ?? 0)];
  const maxVal = Math.max(...allValues, 1);

  const getValue = (item, isForecast) => {
    if (!isForecast) return item[valueKey] ?? item.total ?? item.count ?? item.citations ?? 0;
    return item[`projected_${valueKey}`] ?? item.projected ?? item.projected_faculty ?? item.projected_approved ?? item.projected_citations ?? 0;
  };

  return (
    <Card padding="lg">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: NAVY }}>{title}</h3>
        <span style={{ fontSize: 11, color: TEXT_SECONDARY }}>Trend slope: {data.trend_slope > 0 ? "+" : ""}{data.trend_slope}/yr</span>
      </div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 5, height: 80, marginBottom: 8 }}>
        {historical.slice(-6).map((h, i) => {
          const val = getValue(h, false);
          const barH = Math.max(4, (val / maxVal) * 80);
          return (
            <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 3 }}>
              <div title={`${h.year || h.date}: ${val}`} style={{ width: "100%", height: barH, background: `${NAVY}60`, borderRadius: "3px 3px 0 0" }} />
              <span style={{ fontSize: 9, color: TEXT_SECONDARY }}>{h.year || (h.date || "")?.slice(-4)}</span>
            </div>
          );
        })}
        <div style={{ width: 1, background: `${color}60`, height: 80, flexShrink: 0 }} />
        {forecasts.map((f, i) => {
          const val = getValue(f, true);
          const barH = Math.max(4, (val / maxVal) * 80);
          return (
            <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 3 }}>
              <div title={`${f.year}: ${val} (${f.confidence_pct}% confidence)`}
                style={{ width: "100%", height: barH, background: color, borderRadius: "3px 3px 0 0", opacity: 0.6 + i * 0.1 }} />
              <span style={{ fontSize: 9, color }}>{f.year}</span>
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", gap: 12 }}>
        <span style={{ fontSize: 11, color: TEXT_SECONDARY, display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 10, height: 10, background: `${NAVY}60`, borderRadius: 2, display: "inline-block" }} /> Historical
        </span>
        <span style={{ fontSize: 11, color, display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 10, height: 10, background: color, borderRadius: 2, display: "inline-block", opacity: 0.7 }} /> Forecast
        </span>
      </div>
      <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
        {forecasts.map((f, i) => {
          const val = getValue(f, true);
          return (
            <Tag key={i} color={color}>
              <span style={{ fontWeight: 700 }}>{f.year}: {val.toLocaleString()}</span>
              <span style={{ opacity: 0.75, marginLeft: 6 }}>({f.confidence_pct}%)</span>
            </Tag>
          );
        })}
      </div>
    </Card>
  );
}

export default function ForecastCenter() {
  const [pubF, setPubF] = useState(null);
  const [grantF, setGrantF] = useState(null);
  const [facF, setFacF] = useState(null);
  const [citF, setCitF] = useState(null);
  const [loading, setLoading] = useState(true);
  const [horizon, setHorizon] = useState(3);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [pr, gr, fr, cr] = await Promise.all([
        fetchApi(`${API}/api/iip/forecasts/publications?horizon=${horizon}`, { headers: authH() }),
        fetchApi(`${API}/api/iip/forecasts/grants?horizon=${horizon}`, { headers: authH() }),
        fetchApi(`${API}/api/iip/forecasts/faculty?horizon=${horizon}`, { headers: authH() }),
        fetchApi(`${API}/api/iip/forecasts/citations?horizon=${horizon}`, { headers: authH() }),
      ]);
      if (pr.ok) setPubF(await pr.json());
      if (gr.ok) setGrantF(await gr.json());
      if (fr.ok) setFacF(await fr.json());
      if (cr.ok) setCitF(await cr.json());
    } catch (_) {}
    setLoading(false);
  }, [horizon]);

  useEffect(() => { load(); }, [load]);

  return (
    <InstitutionLayout
      title="Forecast Center"
      subtitle="Linear trend extrapolation from historical institutional data"
      actions={
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ fontSize: 13, color: TEXT_SECONDARY }}>Horizon:</span>
          <NavTabs
            variant="segment"
            size="sm"
            active={horizon}
            onChange={setHorizon}
            tabs={[1, 2, 3, 5].map(h => ({ id: h, label: `${h}yr` }))}
          />
        </div>
      }
      sidebar={!loading ? <ForecastCenterSidebar pubF={pubF} grantF={grantF} facF={facF} citF={citF} /> : undefined}
    >
      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: 40 }}>
          <Spinner size={32} color={ACCENT} />
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <ForecastPanel title="Publication Forecast" data={pubF} valueKey="total" color={EMERALD} />
          <ForecastPanel title="Grant Approvals Forecast" data={grantF} valueKey="approved" color="#8b5cf6" />
          <ForecastPanel title="Faculty Growth Forecast" data={facF} valueKey="faculty" color="#0ea5e9" />
          <ForecastPanel title="Citation Growth Forecast" data={citF} valueKey="citations" color="#f59e0b" />
        </div>
      )}

      <Callout variant="neutral" style={{ marginTop: 16 }}>
        Forecasts are based on historical trends using linear regression. Confidence decreases with forecast horizon.
        These projections are indicative and should inform — not replace — expert strategic judgement.
      </Callout>
    </InstitutionLayout>
  );
}

// ── Right rail — next-year forecast values already fetched by this page ───────
function forecastValue(item, valueKey) {
  return item[`projected_${valueKey}`] ?? item.projected ?? item.projected_faculty ?? item.projected_approved ?? item.projected_citations ?? 0;
}

function ForecastCenterSidebar({ pubF, grantF, facF, citF }) {
  const rows = [
    { label: "Publications",     data: pubF,   key: "total",     color: EMERALD },
    { label: "Grant Approvals",  data: grantF, key: "approved",  color: "#8b5cf6" },
    { label: "Faculty",          data: facF,   key: "faculty",   color: "#0ea5e9" },
    { label: "Citations",        data: citF,   key: "citations", color: "#f59e0b" },
  ].filter(r => r.data?.forecasts?.length > 0);

  if (rows.length === 0) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
          <TrendingUp size={13} style={{ color: NAVY }} />
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>Next-Year Outlook</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {rows.map((r) => {
            const f = r.data.forecasts[0];
            const val = forecastValue(f, r.key);
            return (
              <div key={r.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <span style={{ fontSize: 12.5, color: "#374151" }}>{r.label}</span>
                <span style={{ fontSize: 12.5, fontWeight: 700, color: r.color }}>
                  {val.toLocaleString()} <span style={{ fontSize: 10, fontWeight: 400, color: "#94A3B8" }}>({f.confidence_pct}%)</span>
                </span>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
