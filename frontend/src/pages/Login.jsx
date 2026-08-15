/* eslint-disable */
import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate, useLocation, Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import api, { getErrorMessage } from "../lib/api";
import { TID } from "../lib/testIds";
import {
  AuthLayout, AuthCard, AuthHeader, AuthTitle, AuthInput, PasswordInput,
  AuthButton, AuthDivider, SocialButtons, ErrorBanner, AuthFooter, AuthLink,
  AuthCheckbox, NAVY, T_MID, T_FAINT, BORDER,
} from "../components/auth/AuthShared";

export default function Login() {
  useEffect(() => {
    document.title = "Sign In — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  const { login, mfaVerify, user } = useAuth();
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [err,      setErr]      = useState("");
  const [loading,  setLoading]  = useState(false);
  const submittingRef = useRef(false);
  const navigate  = useNavigate();
  const location  = useLocation();

  // MFA challenge state — set either after a password login on an MFA-enabled
  // account, or from ?mfa_token= on redirect back from the Google OAuth flow
  // (routers/google_auth.py issues the same pending token instead of cookies
  // when the account has MFA enabled, so both login paths funnel through the
  // same code-entry step here rather than silently skipping it).
  const [mfaToken,   setMfaToken]   = useState(null);
  const [mfaCode,    setMfaCode]    = useState("");
  const [trustDevice, setTrustDevice] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const token = params.get("mfa_token");
    if (token) {
      setMfaToken(token);
      navigate(location.pathname, { replace: true }); // scrub the token from the URL bar
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (user) {
    if (user.is_super_admin) return <Navigate to="/admin" replace />;
    if (!user.onboarded)    return <Navigate to="/onboarding" replace />;
    return <Navigate to={location.state?.from?.pathname || "/discover"} replace />;
  }

  async function onSubmit(e) {
    e.preventDefault();
    // Guard against double-submit from rapid double-clicks: setLoading(true)
    // below doesn't disable the button until React re-renders, so a second
    // click landing before that paint would otherwise fire a second request.
    if (submittingRef.current) return;
    setErr("");
    // See Register.jsx — native `required` silently blocks the submit event
    // before this handler runs when a field is empty, so it never got a
    // chance to give feedback for that case. `noValidate` below hands it back.
    if (!email.trim())  { setErr("Please enter your email address."); return; }
    if (!password)      { setErr("Please enter your password."); return; }
    submittingRef.current = true;
    setLoading(true);
    try {
      const data = await login(email, password, remember);
      if (data?.mfa_required) { setMfaToken(data.mfa_token); return; }
      if (data?.is_super_admin)  navigate("/admin",      { replace: true });
      else if (!data?.onboarded) navigate("/onboarding", { replace: true });
      else navigate(location.state?.from?.pathname || "/discover", { replace: true });
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
      submittingRef.current = false;
    }
  }

  async function onMfaSubmit(e) {
    e.preventDefault();
    if (submittingRef.current) return;
    setErr("");
    if (!mfaCode.trim()) { setErr("Enter the 6-digit code from your authenticator app."); return; }
    submittingRef.current = true;
    setLoading(true);
    try {
      const data = await mfaVerify(mfaToken, mfaCode.trim(), trustDevice);
      if (data?.is_super_admin)  navigate("/admin",      { replace: true });
      else if (!data?.onboarded) navigate("/onboarding", { replace: true });
      else navigate(location.state?.from?.pathname || "/discover", { replace: true });
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
      submittingRef.current = false;
    }
  }

  async function handleGoogle() {
    try {
      const { data } = await api.get("/google/authorize?mode=login");
      if (data.authorization_url) window.location.href = data.authorization_url;
    } catch (e) {
      setErr(getErrorMessage(e));
    }
  }

  async function handleOrcid() {
    try {
      const { data } = await api.get("/orcid/authorize?mode=login");
      if (data.authorization_url) window.location.href = data.authorization_url;
    } catch (e) {
      setErr(getErrorMessage(e));
    }
  }

  if (mfaToken) {
    return (
      <AuthLayout>
        <AuthCard>
          <AuthHeader />

          <AuthTitle
            title="Two-factor authentication"
            subtitle="Enter the 6-digit code from your authenticator app."
          />

          <form onSubmit={onMfaSubmit} noValidate style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <AuthInput
              label="Authentication code"
              type="text"
              value={mfaCode}
              onChange={function(e) { setMfaCode(e.target.value.replace(/[^0-9a-zA-Z]/g, "")); }}
              placeholder="123456"
              required
              autoComplete="one-time-code"
              testId="mfa-code-input"
            />

            <AuthCheckbox checked={trustDevice} onChange={function(e) { setTrustDevice(e.target.checked); }}>
              <span>Trust this device for 30 days</span>
            </AuthCheckbox>

            <ErrorBanner error={err} testId="mfa-error" />

            <div style={{ marginTop: 4 }}>
              <AuthButton loading={loading} testId="mfa-verify-submit">
                Verify &amp; Sign In
              </AuthButton>
            </div>
          </form>

          <AuthFooter>
            <AuthLink
              to="#"
              onClick={(e) => { e.preventDefault(); setMfaToken(null); setMfaCode(""); setErr(""); }}
            >
              Back to sign in
            </AuthLink>
          </AuthFooter>
        </AuthCard>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <AuthCard>
        <AuthHeader />

        <AuthTitle
          title="Welcome back"
          subtitle="Continue your research journey with Synaptiq."
        />

        <form onSubmit={onSubmit} noValidate style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <AuthInput
            label="Email"
            type="email"
            value={email}
            onChange={function(e) { setEmail(e.target.value); }}
            placeholder="you@university.edu"
            required
            autoComplete="email"
            testId={TID.loginEmail}
          />

          <PasswordInput
            label="Password"
            value={password}
            onChange={function(e) { setPassword(e.target.value); }}
            required
            testId={TID.loginPassword}
            autoComplete="current-password"
          />

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "8px 16px", marginTop: -4 }}>
            <AuthCheckbox checked={remember} onChange={function(e) { setRemember(e.target.checked); }}>
              <span style={{ whiteSpace: "nowrap" }}>Remember me</span>
            </AuthCheckbox>
            <Link
              to="/forgot-password"
              data-testid={TID.loginForgotLink}
              style={{ fontSize: "0.8rem", fontWeight: 500, color: T_FAINT, textDecoration: "none", transition: "color 120ms", flexShrink: 0 }}
              onMouseEnter={function(e) { e.currentTarget.style.color = NAVY; }}
              onMouseLeave={function(e) { e.currentTarget.style.color = T_FAINT; }}
            >
              Forgot password?
            </Link>
          </div>

          <ErrorBanner error={err} testId={TID.loginError} />

          <div style={{ marginTop: 4 }}>
            <AuthButton loading={loading} testId={TID.loginSubmit}>
              Sign In
            </AuthButton>
          </div>
        </form>

        <AuthDivider />
        <SocialButtons onGoogle={handleGoogle} onOrcid={handleOrcid} />

        <AuthFooter>
          Don&rsquo;t have an account?{" "}
          <AuthLink to="/register" testId={TID.authToggleLink}>Get Started</AuthLink>
        </AuthFooter>
      </AuthCard>
    </AuthLayout>
  );
}
