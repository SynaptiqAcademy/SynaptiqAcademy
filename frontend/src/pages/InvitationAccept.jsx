/* eslint-disable */
/**
 * InvitationAccept — standalone auth-flow page for accepting a collaboration invite via link.
 * Route: /invite?token=...
 */
import React, { useEffect, useState, useRef } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { CheckCircle2, X, Loader2, Users, FolderOpen, Building2, Mail, User } from "lucide-react";
import api from "../lib/api";
import {
  AuthLayout, AuthCard, AuthHeader, AuthButton, NAVY, T_MID, T_FAINT, BORDER,
} from "../components/auth/AuthShared";

const KIND_LABELS = {
  collaboration:               "Research Collaboration",
  project:                     "Project Invitation",
  workspace:                   "Workspace Invitation",
  manuscript:                  "Manuscript Invitation",
  expertise_request:           "Expertise Request",
  grant_team:                  "Grant Team",
  conference_team:             "Conference Team",
  reviewer:                    "Reviewer",
  mentorship:                  "Mentorship",
  institutional_collaboration: "Institutional Collaboration",
};

const KIND_ICONS = {
  collaboration: Users,
  project:       FolderOpen,
  workspace:     FolderOpen,
  manuscript:    FolderOpen,
  grant_team:    Building2,
};

export default function InvitationAccept() {
  const [params]   = useSearchParams();
  const navigate   = useNavigate();
  const token      = params.get("token") || "";

  const [state,    setState]   = useState("loading"); // loading | ready | accepting | declined | done | error
  const [inv,      setInv]     = useState(null);
  const [err,      setErr]     = useState("");
  const actionRef = useRef(false);

  useEffect(function() {
    if (!token) { setState("error"); setErr("Invalid or missing invitation link."); return; }
    (async function() {
      try {
        const { data } = await api.get(`/marketplace/invitations/preview?token=${token}`);
        setInv(data);
        setState("ready");
      } catch (e) {
        setState("error");
        setErr(e?.response?.data?.detail || "This invitation link is invalid or has expired.");
      }
    })();
  }, [token]);

  async function accept() {
    if (actionRef.current) return;
    actionRef.current = true;
    setState("accepting");
    try {
      await api.post(`/marketplace/invitations/accept?token=${token}`);
      setState("done");
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to accept invitation.");
      setState("error");
    } finally {
      actionRef.current = false;
    }
  }

  async function decline() {
    if (actionRef.current) return;
    actionRef.current = true;
    setState("declined");
    try {
      await api.post(`/marketplace/invitations/decline?token=${token}`);
    } catch (_) {
    } finally {
      actionRef.current = false;
    }
  }

  const IconComponent = inv ? (KIND_ICONS[inv.kind] || Users) : Users;

  return (
    <AuthLayout>
      <AuthCard>
        <AuthHeader tagline="Invitation" />

        {/* Loading */}
        {state === "loading" && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16, padding: "16px 0" }}>
            <Loader2 size={32} strokeWidth={1.5} style={{ color: NAVY, animation: "auth-spin 1s linear infinite" }} />
            <p style={{ fontSize: "0.9rem", color: T_MID, margin: 0 }}>Loading invitation…</p>
          </div>
        )}

        {/* Ready — show invitation details */}
        {(state === "ready" || state === "accepting") && inv && (
          <div>
            {/* Kind badge */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 24 }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: "#EFF6FF", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <IconComponent size={18} strokeWidth={1.5} style={{ color: NAVY }} />
              </div>
              <div>
                <div style={{ fontSize: "0.62rem", fontWeight: 700, color: T_FAINT, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                  {KIND_LABELS[inv.kind] || inv.kind?.replace(/_/g, " ") || "Invitation"}
                </div>
                <div style={{ fontFamily: "Georgia, serif", fontSize: "1.4rem", fontWeight: 700, color: "#0f172a", letterSpacing: "-0.02em", lineHeight: 1.2 }}>
                  You've been invited
                </div>
              </div>
            </div>

            {/* Detail rows */}
            <div style={{ border: `1px solid ${BORDER}`, borderRadius: 10, overflow: "hidden", marginBottom: 24 }}>
              {[
                inv.workspace_name    && { icon: FolderOpen,  label: "Workspace",    value: inv.workspace_name    },
                inv.institution_name  && { icon: Building2,   label: "Institution",  value: inv.institution_name  },
                inv.project_name      && { icon: FolderOpen,  label: "Project",      value: inv.project_name      },
                inv.inviter_name      && { icon: User,        label: "Invited by",   value: inv.inviter_name      },
                inv.role              && { icon: Users,        label: "Your role",    value: inv.role              },
              ].filter(Boolean).map(function(row, i, arr) {
                const Icon = row.icon;
                return (
                  <div
                    key={row.label}
                    style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", borderBottom: i < arr.length - 1 ? `1px solid ${BORDER}` : "none" }}
                  >
                    <Icon size={14} strokeWidth={1.5} style={{ color: T_FAINT, flexShrink: 0 }} />
                    <span style={{ fontSize: "0.78rem", color: T_FAINT, width: 90, flexShrink: 0 }}>{row.label}</span>
                    <span style={{ fontSize: "0.875rem", color: "#0f172a", fontWeight: 500 }}>{row.value}</span>
                  </div>
                );
              })}
              {inv.message && (
                <div style={{ padding: "12px 16px", borderTop: `1px solid ${BORDER}`, background: "#FAFAFA" }}>
                  <div style={{ fontSize: "0.62rem", fontWeight: 700, color: T_FAINT, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>Message</div>
                  <p style={{ fontSize: "0.84rem", color: "#475569", fontStyle: "italic", margin: 0, lineHeight: 1.65 }}>"{inv.message}"</p>
                </div>
              )}
            </div>

            {/* Actions */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <AuthButton loading={state === "accepting"} onClick={accept}>
                Accept Invitation
              </AuthButton>
              <button
                type="button"
                onClick={decline}
                disabled={state === "accepting"}
                style={{ width: "100%", height: 48, background: "#fff", border: `1.5px solid ${BORDER}`, borderRadius: 10, fontSize: "0.875rem", fontWeight: 500, color: T_MID, cursor: "pointer", transition: "border-color 150ms", fontFamily: "inherit" }}
                onMouseEnter={function(e) { e.currentTarget.style.borderColor = "#94a3b8"; }}
                onMouseLeave={function(e) { e.currentTarget.style.borderColor = BORDER; }}
              >
                Decline
              </button>
            </div>
          </div>
        )}

        {/* Accepted */}
        {state === "done" && (
          <div style={{ textAlign: "center" }}>
            <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#ECFDF5", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 24px" }}>
              <CheckCircle2 size={28} strokeWidth={1.5} style={{ color: "#059669" }} />
            </div>
            <h2 style={{ fontFamily: "Georgia, serif", fontSize: "1.5rem", fontWeight: 700, color: "#0f172a", margin: "0 0 10px", letterSpacing: "-0.02em" }}>
              Invitation accepted
            </h2>
            <p style={{ fontSize: "0.875rem", color: T_MID, lineHeight: 1.7, marginBottom: 28 }}>
              You've successfully joined. Head to the app to get started.
            </p>
            <Link to="/discover" style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "100%", height: 52, background: NAVY, color: "#fff", textDecoration: "none", borderRadius: 10, fontSize: "0.9rem", fontWeight: 600 }}>
              Continue to Synaptiq
            </Link>
          </div>
        )}

        {/* Declined */}
        {state === "declined" && (
          <div style={{ textAlign: "center" }}>
            <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#F8FAFC", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 24px" }}>
              <X size={28} strokeWidth={1.5} style={{ color: T_FAINT }} />
            </div>
            <h2 style={{ fontFamily: "Georgia, serif", fontSize: "1.5rem", fontWeight: 700, color: "#0f172a", margin: "0 0 10px", letterSpacing: "-0.02em" }}>
              Invitation declined
            </h2>
            <p style={{ fontSize: "0.875rem", color: T_MID, lineHeight: 1.7, marginBottom: 28 }}>
              The invitation has been declined. You can always start a new collaboration from the platform.
            </p>
            <Link to="/login" style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "100%", height: 52, background: "#fff", border: `1.5px solid ${BORDER}`, color: "#0f172a", textDecoration: "none", borderRadius: 10, fontSize: "0.9rem", fontWeight: 500 }}>
              Go to Sign In
            </Link>
          </div>
        )}

        {/* Error */}
        {state === "error" && (
          <div style={{ textAlign: "center" }}>
            <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#FFFBEB", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 24px" }}>
              <Mail size={28} strokeWidth={1.5} style={{ color: "#D97706" }} />
            </div>
            <h2 style={{ fontFamily: "Georgia, serif", fontSize: "1.5rem", fontWeight: 700, color: "#0f172a", margin: "0 0 10px", letterSpacing: "-0.02em" }}>
              Link unavailable
            </h2>
            <p style={{ fontSize: "0.875rem", color: T_MID, lineHeight: 1.7, marginBottom: 28 }}>
              {err}
            </p>
            <Link to="/login" style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "100%", height: 52, background: NAVY, color: "#fff", textDecoration: "none", borderRadius: 10, fontSize: "0.9rem", fontWeight: 600 }}>
              Go to Sign In
            </Link>
          </div>
        )}

      </AuthCard>
    </AuthLayout>
  );
}
