/* eslint-disable */
import React, { useState, useEffect, useRef } from "react";
import { Link, useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import api, { getErrorMessage } from "../lib/api";
import { TID } from "../lib/testIds";
import {
  AuthLayout, AuthCard, AuthHeader, AuthTitle, AuthInput, PasswordInput,
  AuthSelect, AuthButton, AuthDivider, SocialButtons, ErrorBanner,
  AuthFooter, AuthLink, AuthCheckbox, PasswordStrength, TermsNote,
  NAVY, T_MID, T_FAINT, BORDER,
} from "../components/auth/AuthShared";

const ROLES = [
  { value: "student",     label: "Student"                   },
  { value: "master",      label: "Master Student"            },
  { value: "phd",         label: "PhD Candidate"             },
  { value: "researcher",  label: "Researcher"                },
  { value: "professor",   label: "Professor"                 },
  { value: "admin",       label: "Institution Administrator" },
];

export default function Register() {
  useEffect(() => {
    document.title = "Get Started — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  const { register, user } = useAuth();
  const [fullName,    setFullName]    = useState("");
  const [institution, setInstitution] = useState("");
  const [email,       setEmail]       = useState("");
  const [password,    setPassword]    = useState("");
  const [confirm,     setConfirm]     = useState("");
  const [role,        setRole]        = useState("");
  const [agreed,      setAgreed]      = useState(false);
  const [err,         setErr]         = useState("");
  const [loading,     setLoading]     = useState(false);
  const submittingRef = useRef(false);
  const navigate = useNavigate();

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
    if (!agreed) { setErr("Please accept the Terms and Privacy Policy to continue."); return; }
    if (submittingRef.current) return;
    submittingRef.current = true;
    setLoading(true);
    try {
      const data = await register(fullName, email, password);
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

  async function handleGoogle() {
    try {
      const { data } = await api.get("/google/authorize?mode=signup");
      if (data.authorization_url) window.location.href = data.authorization_url;
    } catch (e) {
      setErr(getErrorMessage(e));
    }
  }

  async function handleOrcid() {
    try {
      const { data } = await api.get("/orcid/authorize?mode=signup");
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
          {/* Row: Full Name + Institution */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
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
              label="Institution"
              value={institution}
              onChange={function(e) { setInstitution(e.target.value); }}
              placeholder="University or organisation"
              autoComplete="organization"
            />
          </div>

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

          <AuthSelect
            label="Academic Role"
            value={role}
            onChange={function(e) { setRole(e.target.value); }}
          >
            <option value="" disabled>Select your role</option>
            {ROLES.map(function(r) {
              return <option key={r.value} value={r.value}>{r.label}</option>;
            })}
          </AuthSelect>

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
            I agree to the{" "}
            <Link to="/terms"   style={{ color: NAVY, fontWeight: 600, textDecoration: "none" }}>Terms of Service</Link>
            {" "}and{" "}
            <Link to="/privacy" style={{ color: NAVY, fontWeight: 600, textDecoration: "none" }}>Privacy Policy</Link>
          </AuthCheckbox>

          <ErrorBanner error={err} testId={TID.registerError} />

          <div style={{ marginTop: 4 }}>
            <AuthButton loading={loading} testId={TID.registerSubmit}>
              Create Account
            </AuthButton>
          </div>
        </form>

        <AuthDivider />
        <SocialButtons onGoogle={handleGoogle} onOrcid={handleOrcid} />

        <AuthFooter>
          Already have an account?{" "}
          <AuthLink to="/login" testId={TID.authToggleLink}>Sign In</AuthLink>
        </AuthFooter>
      </AuthCard>
    </AuthLayout>
  );
}
