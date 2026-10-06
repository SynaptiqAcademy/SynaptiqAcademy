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

        <div className="au-success">
          {/* Icon */}
          <div className="au-success-mark">
            <Mail size={28} strokeWidth={1.5} style={{ color: NAVY }} />
          </div>

          <h1 className="au-title au-title-sm">
            Check your inbox
          </h1>
          <p className="au-sub au-gap">
            We sent a verification link to{" "}
            {email
              ? <strong>{email}</strong>
              : "your email address"}
            . Click the link to activate your account.
          </p>

          {/* Resend */}
          {resent ? (
            <div className="au-ok" role="status">
              <CheckCircle2 size={16} strokeWidth={1.5} />
              Verification email resent — check your inbox.
            </div>
          ) : (
            <button
              onClick={resend}
              disabled={resending}
              className="au-btn au-btn-primary"
              onMouseEnter={function(e) { if (!resending) e.currentTarget.style.opacity = "0.88"; }}
              onMouseLeave={function(e) { e.currentTarget.style.opacity = "1"; }}
            >
              <RefreshCw size={14} strokeWidth={1.5} style={{ animation: resending ? "auth-spin 1s linear infinite" : "none" }} />
              {resending ? "Sending…" : "Resend verification email"}
            </button>
          )}

          {err && (
            <div className="au-alert" role="alert" style={{ marginTop: 12 }}><span>{err}</span></div>
          )}

          {/* Sign out */}
          <div className="au-switch">
            <p style={{ margin: 0 }}>
              Wrong account?{" "}
              <button
                onClick={logout}
                className="au-link" style={{ background: "none", border: "none", padding: 0, cursor: "pointer", font: "inherit" }}
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
