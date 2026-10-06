/* eslint-disable */
import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import api, { getErrorMessage } from "../lib/api";
import { TID } from "../lib/testIds";
import { trackMarketingEvent as track } from "../lib/marketingAnalytics";
import {
  AuthLayout, AuthCard, AuthHeader, AuthTitle, AuthInput, PasswordInput,
  AuthButton, AuthDivider, SocialButtons, useOauthProviders, ErrorBanner,
  AuthFooter, AuthLink, AuthCheckbox, PasswordStrength, TermsNote,
  NAVY, T_MID, T_FAINT, BORDER,
} from "../components/auth/AuthShared";

export default function Register() {
  useEffect(() => {
    document.title = "Get Started — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  const { register, user } = useAuth();
  const [fullName,    setFullName]    = useState("");
  const [email,       setEmail]       = useState("");
  const [password,    setPassword]    = useState("");
  const [confirm,     setConfirm]     = useState("");
  const [agreed,      setAgreed]      = useState(false);
  const [err,         setErr]         = useState("");
  const [loading,     setLoading]     = useState(false);
  const submittingRef = useRef(false);
  const navigate = useNavigate();
  const providers = useOauthProviders();

  // Returned here by an OAuth callback that couldn't create an account.
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const code = q.get("orcid_error") || q.get("google_error");
    if (code === "terms_required") setErr("To create an account, first confirm you're 18 or older and accept the Terms of Service below, then continue.");
    else if (code === "registration_closed") setErr("Sign-ups are closed at the moment, so a new account can't be created.");
  }, []);
  if (user) {
    if (user.is_super_admin) return <Navigate to="/admin" replace />;
    if (!user.onboarded)    return <Navigate to="/onboarding" replace />;
    return <Navigate to="/discover" replace />;
  }

  async function onSubmit(e) {
    e.preventDefault();
    setErr("");
    // The native `required` attribute on these fields silently blocks the
    // browser's submit event before React ever sees it when a field is
    // empty — this handler then never runs, so the app's own styled error
    // banner (used for every other validation case below) never appears.
    // `noValidate` on the <form> hands all of that back to this function so
    // every validation failure gets the same visible, consistent feedback.
    if (!fullName.trim()) { setErr("Please enter your full name."); return; }
    if (!email.trim()) { setErr("Please enter your email address."); return; }
    if (password.length < 8) { setErr("Password must be at least 8 characters."); return; }
    if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      setErr("Password must contain at least one letter and one digit.");
      return;
    }
    if (password !== confirm) { setErr("Passwords do not match."); return; }
    if (!agreed) { setErr("Please confirm you are 18 or older and accept the Terms of Service to continue."); return; }
    if (submittingRef.current) return;
    submittingRef.current = true;
    setLoading(true);
    track("signup_started");
    try {
      const data = await register(fullName, email, password);
      track("signup_completed");
      if (data?.is_super_admin) navigate("/admin", { replace: true });
      else if (data?.email_verified === false) navigate("/verify-email-pending", { replace: true, state: { email: data?.email || email } });
      else navigate("/onboarding", { replace: true });
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
      submittingRef.current = false;
    }
  }

  // Every way of creating an account requires the same 18+ and Terms
  // confirmation; the server refuses a new OAuth account without it.
  function needsAgreement() {
    if (agreed) return false;
    setErr("Please confirm you are 18 or older and accept the Terms of Service to continue.");
    return true;
  }

  async function handleGoogle() {
    if (needsAgreement()) return;
    try {
      const { data } = await api.get("/google/authorize?mode=signup&accepted_terms=true");
      if (data.authorization_url) window.location.href = data.authorization_url;
    } catch (e) {
      setErr(getErrorMessage(e));
    }
  }

  async function handleOrcid() {
    if (needsAgreement()) return;
    try {
      const { data } = await api.get("/orcid/authorize?mode=signup&accepted_terms=true");
      if (data.authorization_url) window.location.href = data.authorization_url;
    } catch (e) {
      setErr(getErrorMessage(e));
    }
  }

  return (
    <AuthLayout>
      <AuthCard wide>
        <AuthHeader />

        <AuthTitle
          title="Create your Synaptiq account"
          subtitle="Join researchers, universities and research teams from around the world."
        />

        <form onSubmit={onSubmit} noValidate style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <AuthInput
            label="Full Name"
            value={fullName}
            onChange={function(e) { setFullName(e.target.value); }}
            placeholder="Dr. Jane Doe"
            required
            autoComplete="name"
            testId={TID.registerName}
          />

          <AuthInput
            label="Email"
            type="email"
            value={email}
            onChange={function(e) { setEmail(e.target.value); }}
            placeholder="you@university.edu"
            required
            autoComplete="email"
            testId={TID.registerEmail}
          />

          {/* Password + strength */}
          <div>
            <PasswordInput
              label="Password"
              value={password}
              onChange={function(e) { setPassword(e.target.value); }}
              required
              testId={TID.registerPassword}
              autoComplete="new-password"
            />
            <PasswordStrength password={password} />
          </div>

          <PasswordInput
            label="Confirm Password"
            value={confirm}
            onChange={function(e) { setConfirm(e.target.value); }}
            required
            autoComplete="new-password"
          />

          <AuthCheckbox checked={agreed} onChange={function(e) { setAgreed(e.target.checked); }}>
            {/* One inline run, so the sentence wraps as text rather than as flex columns. */}
            <span>
              I'm 18 or older and agree to the{" "}
              <Link to="/terms"   style={{ color: NAVY, fontWeight: 600, textDecoration: "none" }}>Terms of Service</Link>.
              {" "}I've read the{" "}
              <Link to="/privacy" style={{ color: NAVY, fontWeight: 600, textDecoration: "none" }}>Privacy Policy</Link>.
            </span>
          </AuthCheckbox>

          <ErrorBanner error={err} testId={TID.registerError} />

          <div style={{ marginTop: 4 }}>
            <AuthButton loading={loading} testId={TID.registerSubmit}>
              Create Account
            </AuthButton>
          </div>
        </form>

        {(providers.google || providers.orcid) && <AuthDivider />}
        <SocialButtons onGoogle={handleGoogle} onOrcid={handleOrcid} providers={providers} />

        <AuthFooter>
          Already have an account?{" "}
          <AuthLink to="/login" testId={TID.authToggleLink}>Sign In</AuthLink>
        </AuthFooter>
      </AuthCard>
    </AuthLayout>
  );
}
