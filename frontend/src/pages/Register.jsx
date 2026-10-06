/* eslint-disable */
import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import api, { getErrorMessage } from "../lib/api";
import { TID } from "../lib/testIds";
import { trackMarketingEvent as track } from "../lib/marketingAnalytics";
import {
  AuthLayout, AuthCard, AuthTitle, AuthInput, PasswordInput,
  AuthButton, AuthDivider, SocialButtons, useOauthProviders, ErrorBanner,
  AuthFooter, AuthLink, AuthCheckbox, PasswordStrength, Notice,
} from "../components/auth/AuthShared";

// Which field an existing validation message is about, so that field can be
// marked invalid and linked to the message for screen readers.
function fieldOf(err) {
  if (!err) return null;
  if (/full name/i.test(err)) return "name";
  if (/email/i.test(err)) return "email";
  if (/do not match/i.test(err)) return "confirm";
  if (/^Password must/i.test(err)) return "password";
  if (/18 or older/i.test(err)) return "agree";
  return null;
}

export default function Register() {
  useEffect(() => {
    document.title = "Start Free — Synaptiq";
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
  const [oauthBusy,   setOauthBusy]   = useState(""); // "orcid" | "google" while redirecting
  const [signupsOpen, setSignupsOpen] = useState(null);
  const submittingRef = useRef(false);
  const navigate = useNavigate();
  const providers = useOauthProviders();

  useEffect(() => {
    api.get("/auth/registration-status")
      .then((r) => setSignupsOpen(r.data?.open !== false))
      .catch(() => setSignupsOpen(null));
  }, []);

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
    setOauthBusy("google");
    try {
      const { data } = await api.get("/google/authorize?mode=signup&accepted_terms=true");
      if (data.authorization_url) window.location.href = data.authorization_url;
      else setOauthBusy("");
    } catch (e) {
      setOauthBusy("");
      setErr(getErrorMessage(e));
    }
  }

  async function handleOrcid() {
    if (needsAgreement()) return;
    setOauthBusy("orcid");
    try {
      const { data } = await api.get("/orcid/authorize?mode=signup&accepted_terms=true");
      if (data.authorization_url) window.location.href = data.authorization_url;
      else setOauthBusy("");
    } catch (e) {
      setOauthBusy("");
      setErr(getErrorMessage(e));
    }
  }

  const bad = fieldOf(err);
  const describe = (f) => (bad === f ? "register-error" : undefined);

  return (
    <AuthLayout>
      <AuthCard wide>
        <AuthTitle
          kicker="Start Free"
          title="Create your Academic Passport"
          subtitle="Your research identity, free to start. Research areas and ORCID come next, after you sign up."
        />

        {signupsOpen === false && (
          <div style={{ marginBottom: 22 }}>
            <Notice>
              New sign-ups are paused while billing is set up. If you already have an account,{" "}
              <Link to="/login" className="au-link">sign in</Link>.
            </Notice>
          </div>
        )}

        <form onSubmit={onSubmit} noValidate className="au-fields">
          <AuthInput
            label="Full name"
            value={fullName}
            onChange={function(e) { setFullName(e.target.value); }}
            placeholder="Dr Jane Doe"
            required
            autoComplete="name"
            testId={TID.registerName}
            invalid={bad === "name"}
            describedBy={describe("name")}
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
            invalid={bad === "email"}
            describedBy={describe("email")}
          />

          <div className="au-field">
            <PasswordInput
              label="Password"
              value={password}
              onChange={function(e) { setPassword(e.target.value); }}
              required
              testId={TID.registerPassword}
              autoComplete="new-password"
              invalid={bad === "password"}
              describedBy={["register-password-hint", describe("password")].filter(Boolean).join(" ")}
            />
            <p className="au-hint" id="register-password-hint">At least 8 characters, with a letter and a number.</p>
            <PasswordStrength password={password} />
          </div>

          <PasswordInput
            label="Confirm password"
            value={confirm}
            onChange={function(e) { setConfirm(e.target.value); }}
            required
            autoComplete="new-password"
            invalid={bad === "confirm"}
            describedBy={describe("confirm")}
          />

          <AuthCheckbox className="au-consent" checked={agreed} onChange={function(e) { setAgreed(e.target.checked); }}>
            I'm 18 or older and agree to the <Link to="/terms">Terms of Service</Link>.
            {" "}I've read the <Link to="/privacy">Privacy Policy</Link>.
          </AuthCheckbox>

          <ErrorBanner error={err} testId={TID.registerError} id="register-error" />

          <AuthButton loading={loading} testId={TID.registerSubmit} loadingLabel="Creating your account…">
            Create account
          </AuthButton>
        </form>

        {(providers.google || providers.orcid) && <AuthDivider />}
        <SocialButtons onGoogle={handleGoogle} onOrcid={handleOrcid} providers={providers} busy={oauthBusy} />

        <AuthFooter>
          Already have an account?{" "}
          <AuthLink to="/login" testId={TID.authToggleLink}>Sign In</AuthLink>
        </AuthFooter>
      </AuthCard>
    </AuthLayout>
  );
}
