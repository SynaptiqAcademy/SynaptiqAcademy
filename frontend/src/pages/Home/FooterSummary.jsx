/* eslint-disable */
import React from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, RefreshCw } from "lucide-react";

export default function FooterSummary({ billing }) {
  const credits  = billing?.credits;
  const planName = billing?.plan?.name || null;
  const balance  = credits?.monthly_balance ?? credits?.balance ?? null;
  const syncTime = new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });

  const labelStyle = { fontSize: "0.68rem", fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)" };
  const valueStyle = { fontSize: "0.75rem", fontWeight: 600, color: "rgba(255,255,255,0.85)", textDecoration: "none" };

  return (
    <div className="flex flex-wrap items-center gap-x-7 gap-y-2">
      {planName && (
        <div className="flex items-center gap-2">
          <span style={labelStyle}>Plan</span>
          <Link to="/settings/billing" style={valueStyle}>{planName}</Link>
        </div>
      )}

      {balance != null && (
        <div className="flex items-center gap-2">
          <span style={labelStyle}>Credits</span>
          <Link to="/ai-credits" style={valueStyle}>{balance.toLocaleString()} remaining</Link>
        </div>
      )}

      <Link to="/status" className="flex items-center gap-1.5" style={{ textDecoration: "none" }}>
        <CheckCircle2 size={11} style={{ color: "#34D399" }} />
        <span style={{ fontSize: "0.72rem", fontWeight: 600, color: "#34D399" }}>System status</span>
      </Link>

      <div className="flex items-center gap-1.5" style={{ marginLeft: "auto" }}>
        <RefreshCw size={9} style={{ color: "rgba(255,255,255,0.35)" }} />
        <span style={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.4)" }}>Last sync {syncTime}</span>
      </div>
    </div>
  );
}
