import React from "react";
import { useLocation } from "react-router-dom";
import { Home, Search, Users, FolderOpen, Building2, Sparkles } from "lucide-react";
import { ErrorPage } from "@/components/ds/ErrorPage";

const QUICK_LINKS = [
  { to: "/",            label: "Dashboard",     icon: Home       },
  { to: "/search",      label: "Search",        icon: Search     },
  { to: "/researchers", label: "Researchers",   icon: Users      },
  { to: "/projects",    label: "Projects",      icon: FolderOpen },
  { to: "/institution-hub", label: "Institutions", icon: Building2 },
  { to: "/ai-suite",    label: "AI Suite",      icon: Sparkles   },
];

export default function NotFound() {
  const { pathname } = useLocation();

  return (
    <ErrorPage
      code="404"
      title="This page doesn't exist"
      description={
        <>
          <p style={{ margin: "0 0 4px" }}>
            The path <code style={{ fontSize: "0.75em", background: "#e2e8f0", padding: "1px 4px", fontFamily: "monospace" }}>{pathname}</code> was not found.
          </p>
          <p style={{ margin: 0 }}>It may have been moved, renamed, or you may have followed an old link.</p>
        </>
      }
      quickLinks={QUICK_LINKS}
    />
  );
}
