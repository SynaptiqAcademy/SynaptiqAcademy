import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import { fetchApi } from "@/lib/api";
import { setPageSeo } from "../lib/seo";
import "../components/landing/landing.css";
import "./support.css";

/*
 * System status — live checks only (GET /api/status, /api/status/history).
 * No uptime percentages, response times or day-by-day bars: Synaptiq doesn't
 * record an uptime history, so none is shown.
 */
const CHECKS = [
  ["api", "Application", "Sign-in, pages and the API"],
  ["database", "Database", "Stored accounts, research and messages"],
  ["ai", "AI services", "Connections to the AI providers"],
  ["email", "Email delivery", "Account and notification emails"],
  ["cache", "Cache", "Speeds up repeated requests; the site works without it"],
];
const WORD = { operational: "Operational", degraded: "Degraded", outage: "Outage", maintenance: "Maintenance" };
const OVERALL = {
  operational: "All checked services are operational.",
  degraded: "Some services are degraded.",
  outage: "A service is unavailable.",
  maintenance: "Maintenance is in progress.",
};

export default function Status() {
  const [data, setData] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [checkedAt, setCheckedAt] = useState(null);

  useEffect(() => setPageSeo({
    title: "Status | Synaptiq",
    description: "Live checks of the services Synaptiq runs on, and any incidents or maintenance we have posted.",
    path: "/status",
  }), []);

  const load = useCallback(async () => {
    setLoading(true); setError(false);
    try {
      const [s, h] = await Promise.all([fetchApi("/api/status"), fetchApi("/api/status/history?days=90")]);
      if (s.ok) { setData(await s.json()); setCheckedAt(new Date()); } else { setError(true); }
      if (h.ok) { setIncidents((await h.json())?.incidents || []); }
    } catch { setError(true); } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const overall = error ? "outage" : data?.status || "operational";
  const components = data?.components || {};
  const maintenance = data?.maintenance;

  return (
    <MarketingLayout>
      <div className="lp sp">
        <header className="sp-head">
          <div className="lp-wrap">
            <div className="lp-mono sp-crumb"><b>Support</b><span aria-hidden="true"> / </span>Status</div>
            <h1 className="sp-title">System status</h1>
            <p className="sp-dek">Live checks of the services Synaptiq runs on. This page shows their state now; it doesn't keep an uptime history.</p>
          </div>
        </header>

        <div className="lp-wrap sp-body">
          <section aria-labelledby="sp-now" className="sp-section">
            <div className="sp-now">
              <h2 id="sp-now" className="sp-h2">{loading ? "Checking…" : error ? "We couldn't reach the status check." : OVERALL[overall]}</h2>
              <button type="button" className="sp-btn" onClick={load} disabled={loading}>Check again</button>
            </div>
            {checkedAt && <p className="lp-mono sp-meta">Checked {checkedAt.toLocaleString()}</p>}
            <ul className="sp-rows" aria-label="Service checks">
              {CHECKS.map(([key, name, what]) => {
                const st = error ? "outage" : components[key]?.status || (data ? "operational" : null);
                return (
                  <li key={key}>
                    <div><div className="sp-row-name">{name}</div><div className="sp-row-what">{what}</div></div>
                    <span className={`lp-mono sp-state sp-state-${st || "unknown"}`}>{st ? WORD[st] || st : "—"}</span>
                  </li>
                );
              })}
            </ul>
            <p className="sp-note">Online payments aren't open yet, so billing isn't listed.</p>
          </section>

          {maintenance?.active && (
            <section aria-labelledby="sp-maint" className="sp-section">
              <h2 id="sp-maint" className="sp-h2">Maintenance</h2>
              <p>{maintenance.message}</p>
            </section>
          )}

          <section aria-labelledby="sp-inc" className="sp-section">
            <h2 id="sp-inc" className="sp-h2">Incidents</h2>
            {incidents.length === 0 ? (
              <p>No incidents have been posted in the last 90 days.</p>
            ) : (
              <ul className="sp-rows">
                {incidents.map((inc) => (
                  <li key={inc.id || inc.title}>
                    <div>
                      <div className="sp-row-name">{inc.title}</div>
                      {inc.message && <div className="sp-row-what">{inc.message}</div>}
                    </div>
                    <span className="lp-mono sp-state">{inc.resolved_at ? "Resolved" : (inc.status || "Open")}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <p className="sp-next">Something not working for you? <Link to="/help-center">Help Center</Link> · <Link to="/contact?topic=support">Contact us</Link></p>
        </div>
      </div>
    </MarketingLayout>
  );
}
