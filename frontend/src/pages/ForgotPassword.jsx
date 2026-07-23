/* eslint-disable */
import React, { useState, useRef } from "react";
import { Link } from "react-router-dom";
import api, { getErrorMessage } from "../lib/api";
import { TID } from "../lib/testIds";
import {
  AuthLayout, AuthCard, AuthHeader, AuthTitle, AuthInput,
  AuthButton, BackLink, ErrorBanner, NAVY, T_MID, T_FAINT, BORDER,
} from "../components/auth/AuthShared";
import { CheckCircle2, Mail } from "lucide-react";

export default function ForgotPassword() {
  const [email,     setEmail]     = useState("");
  const [sent,      setSent]      = useState(false);
  const [debugLink, setDebugLink] = useState("");
  const [loading,   setLoading]   = useState(false);
  const [err,       setErr]       = useState("");
  const submittingRef = useRef(false);

  async function submit(e) {
    e.preventDefault();
    setErr("");
    // Native `required` silently blocks the submit event before this
    // handler runs when the field is empty (see Login.jsx/Register.jsx) —
    // `noValidate` on the form hands it back to this explicit check.
    if (!email.trim()) { setErr("Please enter your email address."); return; }
    if (submittingRef.current) return;
    submittingRef.current = true;
    setLoading(true);
    try {
      const { data } = await api.post("/auth/forgot-password", { email });
      setSent(true);
      if (data.debug_reset_token) {
        setDebugLink(`${window.location.origin}/reset-password?token=${data.debug_reset_token}`);
      }
    } catch (e) {
      // Previously silently swallowed — the user would see the button stop
      // loading with no indication the request failed, and could be left
      // waiting indefinitely for a reset email that was never sent.
      setErr(getErrorMessage(e) || "Something went wrong. Please try again.");
    }
    finally {
      setLoading(false);
      submittingRef.current = false;
    }
  }

  return (
    <AuthLayout>
      <AuthCard>
        <AuthHeader />
        <BackLink to="/login" label="Back to Sign In" />

        {!sent ? (
          <>
            <AuthTitle
              title="Reset your password"
              subtitle="Enter your email and we'll send you a secure reset link."
            />

            <form onSubmit={submit} noValidate style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <AuthInput
                label="Email address"
                type="email"
                value={email}
                onChange={function(e) { setEmail(e.target.value); }}
                placeholder="you@university.edu"
                required
                autoComplete="email"
                testId={TID.forgotEmail}
              />
              <ErrorBanner error={err} testId={TID.forgotError} />
              <div style={{ marginTop: 4 }}>
                <AuthButton loading={loading} disabled={sent} testId={TID.forgotSubmit}>
                  Send Reset Link
                </AuthButton>
              </div>
            </form>
          </>
        ) : (
          // Success state
          <div style={{ textAlign: "center" }} data-testid={TID.forgotSent}>
            <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#EFF6FF", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 24px" }}>
              <Mail size={28} strokeWidth={1.5} style={{ color: NAVY }} />
            </div>
            <h2 style={{ fontFamily: "Georgia, serif", fontSize: "1.5rem", fontWeight: 700, color: "#0f172a", margin: "0 0 10px", letterSpacing: "-0.02em" }}>
              Check your inbox
            </h2>
            <p style={{ fontSize: "0.875rem", color: T_MID, lineHeight: 1.7, marginBottom: 28 }}>
              We've sent password reset instructions to <strong style={{ color: "#0f172a" }}>{email}</strong>. Check your spam folder if it doesn't arrive within a few minutes.
            </p>

            {debugLink && (
              <div style={{ marginBottom: 20, padding: "10px 14px", background: "#F8FAFC", border: `1px solid ${BORDER}`, borderRadius: 9, fontSize: "0.75rem", color: T_FAINT }}>
                <span style={{ fontFamily: "monospace", textTransform: "uppercase", fontSize: 10, letterSpacing: "0.1em" }}>Dev</span>
                {" — "}
                <Link to={debugLink.replace(window.location.origin, "")} style={{ color: NAVY, fontWeight: 500 }}>Use this reset link</Link>
              </div>
            )}

            <Link
              to="/login"
              style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "100%", height: 52, background: NAVY, color: "#fff", textDecoration: "none", borderRadius: 10, fontSize: "0.9rem", fontWeight: 600, letterSpacing: "-0.01em" }}
            >
              Back to Sign In
            </Link>
          </div>
        )}
      </AuthCard>
    </AuthLayout>
  );
}
