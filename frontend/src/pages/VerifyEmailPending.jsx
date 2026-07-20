/* eslint-disable */
/**
 * VerifyEmailPending — gate shown after registration when email verification is required.
 */
import React, { useState } from "react";
import { useLocation } from "react-router-dom";
import { Mail, CheckCircle2, RefreshCw } from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import {
  AuthLayout, AuthCard, AuthHeader, NAVY, T_MID, T_FAINT, BORDER,
} from "../components/auth/AuthShared";

export default function VerifyEmailPending() {
  const { logout } = useAuth();
  const location = useLocation();
  // Read the email from route state (set by Register.jsx), not from
  // AuthContext's `user` — registration with verification pending never
  // establishes a session, so `user` is correctly anonymous here.
  const email = location.state?.email || "";
  const [resending, setResending] = useState(false);
  const [resent,    setResent]    = useState(false);
  const [err,       setErr]       = useState("");

  async function resend() {
    setResending(true);
    setErr("");
    setResent(false);
    try {
      await api.post("/auth/resend-verification", { email });
      setResent(true);
    } catch (e) {
      const detail = e?.response?.data?.detail;
      setErr(typeof detail === "string" ? detail : "Could not send — please try again.");
    } finally {
      setResending(false);
    }
  }

  return (
    <AuthLayout>
      <AuthCard>
        <AuthHeader />

        <div style={{ textAlign: "center" }}>
          {/* Icon */}
          <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#EFF6FF", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 24px" }}>
            <Mail size={28} strokeWidth={1.5} style={{ color: NAVY }} />
          </div>

          <h2 style={{ fontFamily: "Georgia, serif", fontSize: "1.5rem", fontWeight: 700, color: "#0f172a", margin: "0 0 10px", letterSpacing: "-0.02em" }}>
            Check your inbox
          </h2>
          <p style={{ fontSize: "0.875rem", color: T_MID, lineHeight: 1.75, marginBottom: 28 }}>
            We sent a verification link to{" "}
            {email
              ? <strong style={{ color: "#0f172a" }}>{email}</strong>
              : "your email address"}
            . Click the link to activate your account.
          </p>

          {/* Resend */}
          {resent ? (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, color: "#059669", fontSize: "0.875rem", marginBottom: 20 }}>
              <CheckCircle2 size={16} strokeWidth={1.5} />
              Verification email resent — check your inbox.
            </div>
          ) : (
            <button
              onClick={resend}
              disabled={resending}
              style={{
                display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8,
                width: "100%", height: 52,
                background: resending ? "#94a3b8" : NAVY, color: "#fff",
                border: "none", borderRadius: 10,
                fontSize: "0.9rem", fontWeight: 600,
                cursor: resending ? "not-allowed" : "pointer",
                marginBottom: 12, transition: "opacity 150ms",
                fontFamily: "inherit",
              }}
              onMouseEnter={function(e) { if (!resending) e.currentTarget.style.opacity = "0.88"; }}
              onMouseLeave={function(e) { e.currentTarget.style.opacity = "1"; }}
            >
              <RefreshCw size={14} strokeWidth={1.5} style={{ animation: resending ? "auth-spin 1s linear infinite" : "none" }} />
              {resending ? "Sending…" : "Resend verification email"}
            </button>
          )}

          {err && (
            <p style={{ fontSize: "0.84rem", color: "#8A1538", marginBottom: 12 }}>{err}</p>
          )}

          {/* Sign out */}
          <div style={{ marginTop: 24, paddingTop: 20, borderTop: `1px solid ${BORDER}` }}>
            <p style={{ fontSize: "0.78rem", color: T_FAINT, margin: 0 }}>
              Wrong account?{" "}
              <button
                onClick={logout}
                style={{ color: NAVY, background: "none", border: "none", cursor: "pointer", fontSize: "0.78rem", fontWeight: 600, padding: 0, transition: "opacity 150ms" }}
                onMouseEnter={function(e) { e.currentTarget.style.opacity = "0.7"; }}
                onMouseLeave={function(e) { e.currentTarget.style.opacity = "1"; }}
              >
                Sign out
              </button>
            </p>
          </div>
        </div>
      </AuthCard>
    </AuthLayout>
  );
}
