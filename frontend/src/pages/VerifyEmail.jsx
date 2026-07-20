/* eslint-disable */
/**
 * VerifyEmail — handles /verify-email?token=... deep link.
 */
import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, AlertTriangle, Loader2, Mail, ArrowRight } from "lucide-react";
import api from "../lib/api";
import {
  AuthLayout, AuthCard, AuthHeader, AuthButton, NAVY, T_MID, T_FAINT, BORDER,
} from "../components/auth/AuthShared";

export default function VerifyEmail() {
  const [params]   = useSearchParams();
  const token      = params.get("token");
  const [state,    setState]    = useState("verifying"); // verifying | success | already | error
  const [errorMsg, setErrorMsg] = useState("");
  const [resending,setResending]= useState(false);
  const [resentTo, setResentTo] = useState("");

  useEffect(function() {
    if (!token) { setState("error"); setErrorMsg("No verification token provided."); return; }
    (async function() {
      try {
        const { data } = await api.post("/auth/verify-email", { token });
        setState(data.already_verified ? "already" : "success");
      } catch (e) {
        setState("error");
        setErrorMsg(e?.response?.data?.detail || "Verification failed.");
      }
    })();
  }, [token]);

  async function resend() {
    const email = window.prompt("Enter your account email to resend verification:");
    if (!email) return;
    setResending(true);
    try {
      await api.post("/auth/resend-verification", { email });
      setResentTo(email);
    } catch (_) {}
    finally { setResending(false); }
  }

  const PrimaryLink = function({ to, children, testId }) {
    return (
      <Link
        to={to}
        data-testid={testId}
        style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8, width: "100%", height: 52, background: NAVY, color: "#fff", textDecoration: "none", borderRadius: 10, fontSize: "0.9rem", fontWeight: 600, letterSpacing: "-0.01em" }}
      >
        {children} <ArrowRight size={14} />
      </Link>
    );
  };

  return (
    <AuthLayout>
      <AuthCard>
        <AuthHeader />

        <div data-testid="verify-email-card">

          {/* ── Loading ── */}
          {state === "verifying" && (
            <div data-testid="verify-loading" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16, padding: "16px 0" }}>
              <Loader2 size={32} strokeWidth={1.5} style={{ color: NAVY, animation: "auth-spin 1s linear infinite" }} />
              <p style={{ fontSize: "0.9rem", color: T_MID, margin: 0 }}>Verifying your email…</p>
            </div>
          )}

          {/* ── Success ── */}
          {state === "success" && (
            <div data-testid="verify-success" style={{ textAlign: "center" }}>
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#ECFDF5", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 24px" }}>
                <CheckCircle2 size={28} strokeWidth={1.5} style={{ color: "#059669" }} />
              </div>
              <h2 style={{ fontFamily: "Georgia, serif", fontSize: "1.5rem", fontWeight: 700, color: "#0f172a", margin: "0 0 10px", letterSpacing: "-0.02em" }}>
                Email verified
              </h2>
              <p style={{ fontSize: "0.875rem", color: T_MID, lineHeight: 1.7, marginBottom: 28 }}>
                Your account is now active. Welcome to Synaptiq.
              </p>
              <PrimaryLink to="/login" testId="verify-go-login">Continue to Synaptiq</PrimaryLink>
            </div>
          )}

          {/* ── Already verified ── */}
          {state === "already" && (
            <div data-testid="verify-already" style={{ textAlign: "center" }}>
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#ECFDF5", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 24px" }}>
                <CheckCircle2 size={28} strokeWidth={1.5} style={{ color: "#059669" }} />
              </div>
              <h2 style={{ fontFamily: "Georgia, serif", fontSize: "1.5rem", fontWeight: 700, color: "#0f172a", margin: "0 0 10px", letterSpacing: "-0.02em" }}>
                Already verified
              </h2>
              <p style={{ fontSize: "0.875rem", color: T_MID, lineHeight: 1.7, marginBottom: 28 }}>
                This email has already been confirmed. You can sign in now.
              </p>
              <PrimaryLink to="/login">Go to Sign In</PrimaryLink>
            </div>
          )}

          {/* ── Error ── */}
          {state === "error" && (
            <div data-testid="verify-error" style={{ textAlign: "center" }}>
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#FFFBEB", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 24px" }}>
                <AlertTriangle size={28} strokeWidth={1.5} style={{ color: "#D97706" }} />
              </div>
              <h2 style={{ fontFamily: "Georgia, serif", fontSize: "1.5rem", fontWeight: 700, color: "#0f172a", margin: "0 0 10px", letterSpacing: "-0.02em" }}>
                Verification failed
              </h2>
              <p style={{ fontSize: "0.875rem", color: T_MID, lineHeight: 1.7, marginBottom: 24 }}>
                {errorMsg}
              </p>
              <button
                onClick={resend}
                disabled={resending}
                data-testid="verify-resend-btn"
                style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8, width: "100%", height: 52, background: NAVY, color: "#fff", border: "none", borderRadius: 10, fontSize: "0.9rem", fontWeight: 600, cursor: resending ? "not-allowed" : "pointer", marginBottom: 12 }}
              >
                {resending && <Loader2 size={14} strokeWidth={2} style={{ animation: "auth-spin 1s linear infinite" }} />}
                {resending ? "Sending…" : "Resend verification email"}
              </button>
              {resentTo && (
                <p data-testid="verify-resend-toast" style={{ fontSize: "0.78rem", color: T_FAINT, margin: "0 0 12px" }}>
                  If an account exists for <span style={{ fontFamily: "monospace" }}>{resentTo}</span>, a new link has been sent.
                </p>
              )}
              <Link to="/login" style={{ fontSize: "0.84rem", color: NAVY, textDecoration: "none", fontWeight: 500 }}>
                Back to Sign In
              </Link>
            </div>
          )}

        </div>
      </AuthCard>
    </AuthLayout>
  );
}
