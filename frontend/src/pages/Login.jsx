/* eslint-disable */
import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate, useLocation, Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import api, { getErrorMessage } from "../lib/api";
import { TID } from "../lib/testIds";
import {
  AuthLayout, AuthCard, AuthTitle, AuthInput, PasswordInput,
  AuthButton, AuthDivider, SocialButtons, useOauthProviders, ErrorBanner, AuthFooter, AuthLink,
  AuthCheckbox,
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
  const [oauthBusy, setOauthBusy] = useState(""); // "orcid" | "google" while redirecting
  const submittingRef = useRef(false);
  const navigate  = useNavigate();
  const location  = useLocation();
  const providers = useOauthProviders();
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
    setOauthBusy("google");
    try {
      const { data } = await api.get("/google/authorize?mode=login");
      if (data.authorization_url) window.location.href = data.authorization_url;
      else setOauthBusy("");
    } catch (e) {
      setOauthBusy("");
      setErr(getErrorMessage(e));
    }
  }

  async function handleOrcid() {
    setOauthBusy("orcid");
    try {
      const { data } = await api.get("/orcid/authorize?mode=login");
      if (data.authorization_url) window.location.href = data.authorization_url;
      else setOauthBusy("");
    } catch (e) {
      setOauthBusy("");
      setErr(getErrorMessage(e));
    }
  }

  if (mfaToken) {
    return (
      <AuthLayout>
        <AuthCard>
          <AuthTitle
            kicker="Two-step verification"
            title="Enter your code"
            subtitle="Open your authenticator app and enter the 6-digit code for Synaptiq."
          />

          <form onSubmit={onMfaSubmit} noValidate className="au-fields">
            <AuthInput
              label="Authentication code"
              type="text"
              inputMode="numeric"
              value={mfaCode}
              onChange={function(e) { setMfaCode(e.target.value.replace(/[^0-9a-zA-Z]/g, "")); }}
              placeholder="123456"
              required
              autoComplete="one-time-code"
              testId="mfa-code-input"
              invalid={!!err}
              describedBy={err ? "mfa-error" : undefined}
            />

            <AuthCheckbox checked={trustDevice} onChange={function(e) { setTrustDevice(e.target.checked); }}>
              Trust this device for 30 days
            </AuthCheckbox>

            <ErrorBanner error={err} testId="mfa-error" id="mfa-error" />

            <AuthButton loading={loading} testId="mfa-verify-submit" loadingLabel="Verifying…">
              Verify and sign in
            </AuthButton>
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
        <AuthTitle
          kicker="Sign in"
          title="Welcome back"
          subtitle="Continue your research with Synaptiq."
        />

        <form onSubmit={onSubmit} noValidate className="au-fields">
          <AuthInput
            label="Email"
            type="email"
            value={email}
            onChange={function(e) { setEmail(e.target.value); }}
            placeholder="you@university.edu"
            required
            autoComplete="email"
            testId={TID.loginEmail}
            invalid={!!err}
            describedBy={err ? "login-error" : undefined}
          />

          <PasswordInput
            label="Password"
            value={password}
            onChange={function(e) { setPassword(e.target.value); }}
            required
            testId={TID.loginPassword}
            autoComplete="current-password"
            invalid={!!err}
            describedBy={err ? "login-error" : undefined}
          />

          <div className="au-row">
            <AuthCheckbox checked={remember} onChange={function(e) { setRemember(e.target.checked); }}>
              Remember me
            </AuthCheckbox>
            <Link to="/forgot-password" data-testid={TID.loginForgotLink} className="au-quiet">
              Forgot password?
            </Link>
          </div>

          <ErrorBanner error={err} testId={TID.loginError} id="login-error" />

          <AuthButton loading={loading} testId={TID.loginSubmit} loadingLabel="Signing in…">
            Sign In
          </AuthButton>
        </form>

        {(providers.google || providers.orcid) && <AuthDivider />}
        <SocialButtons onGoogle={handleGoogle} onOrcid={handleOrcid} providers={providers} busy={oauthBusy} />

        <AuthFooter>
          New to Synaptiq?{" "}
          <AuthLink to="/register" testId={TID.authToggleLink}>Start Free</AuthLink>
        </AuthFooter>
      </AuthCard>
    </AuthLayout>
  );
}
