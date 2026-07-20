import React, { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Menu, Bell, MessageSquare, Search } from "lucide-react";
import { useUnread } from "../../contexts/UnreadContext";
import { NAVY } from "@/lib/tokens";

// Route → page title, longest specific prefix first
const TITLE_MAP = [
  ["/discover",                    "Home"],
  ["/collaborations/new",          "New Collaboration"],
  ["/collaborations/my",           "My Collaborations"],
  ["/collaborations",              "Collaborations"],
  ["/network",                     "Network"],
  ["/academic-passport",           "Academic Passport"],
  ["/profile",                     "Profile"],
  ["/projects",                    "Projects"],
  ["/messages",                    "Messages"],
  ["/analytics",                   "Analytics"],
  ["/ai-usage",                    "AI Usage"],
  ["/marketplace",                 "Marketplace"],
  ["/expertise",                   "Expertise"],
  ["/invitations",                 "Invitations"],
  ["/institutions",                "Institutions"],
  ["/institution/analytics",       "Institution Analytics"],
  ["/institution/departments",     "Departments"],
  ["/units",                       "Research Unit"],
  ["/research-centers",            "Research Center"],
  ["/labs",                        "Laboratory"],
  ["/notifications",               "Inbox"],
  ["/meetings",                   "Meetings"],
  ["/settings",                    "Settings"],
  ["/journals",                    "Journals"],
  ["/conferences",                 "Conferences"],
  ["/funding",                     "Funding"],
  ["/grants",                      "Grants"],
  ["/workspaces",                  "Workspaces"],
  ["/manuscripts",                 "Manuscripts"],
  ["/reviews",                     "Reviews"],
  ["/manuscript-review",           "AI Manuscript Review"],
  ["/literature-review",           "Literature Review"],
  ["/ai/abstract",                 "Abstract Generator"],
  ["/ai/rewrite",                  "AI Rewriting"],
  ["/research-gap-finder",         "Research Gap Finder"],
  ["/research-design-advisor",     "Study Design Advisor"],
  ["/statistical-review",          "Statistical Review"],
  ["/citation-monitoring",         "Citation Monitoring"],
  ["/citations",                   "Citations"],
  ["/research-impact",             "Research Impact"],
  ["/collaboration-intelligence",  "Collaboration AI"],
  ["/collaboration-requests",      "Collaboration Requests"],
  ["/publication-hub",             "Publication Hub"],
  ["/repository",                  "Repository"],
  ["/teaching/lesson-planner",     "Lesson Planner"],
  ["/teaching/lessons",            "Lesson Plan"],
  ["/teaching/assessment-builder", "Assessment Builder"],
  ["/teaching/assessments",        "Assessment"],
  ["/teaching/portfolio",          "Teaching Portfolio"],
  ["/teaching/workspaces",         "Teaching Workspaces"],
  ["/teaching",                    "Teaching Hub"],
  ["/admin/users",                 "Admin · Users"],
  ["/admin/audit",                 "Admin · Audit"],
  ["/admin/security",              "Admin · Security"],
  ["/admin/email",                 "Admin · Email"],
  ["/admin/analytics",             "Admin · Analytics"],
  ["/admin/revenue",               "Admin · Revenue"],
  ["/admin/health",                "Admin · Health"],
  ["/admin",                       "Admin Dashboard"],
];

function getPageTitle(pathname) {
  for (const [prefix, label] of TITLE_MAP) {
    if (pathname === prefix || pathname.startsWith(prefix + "/")) return label;
  }
  return "SYNAPTIQ";
}

export default function MobileTopBar({ onOpenDrawer, onOpenSearch }) {
  const { pathname } = useLocation();
  const { total: msgUnread } = useUnread();
  const [notifCount, setNotifCount] = useState(0);

  // Increment badge on incoming WebSocket notifications
  useEffect(() => {
    const handler = () => setNotifCount((n) => n + 1);
    window.addEventListener("synaptiq:notification", handler);
    return () => window.removeEventListener("synaptiq:notification", handler);
  }, []);

  // Clear badge when user visits /notifications
  useEffect(() => {
    if (pathname === "/notifications") setNotifCount(0);
  }, [pathname]);

  const title = getPageTitle(pathname);

  return (
    <header
      className="fixed top-0 left-0 right-0 h-14 z-40 lg:hidden bg-white border-b border-[rgba(15,23,42,0.08)] flex items-center gap-2 px-3"
      role="banner"
    >
      <button
        onClick={onOpenDrawer}
        className="w-9 h-9 flex items-center justify-center text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors shrink-0"
        aria-label="Open navigation menu"
        aria-expanded={false}
        aria-controls="mobile-drawer"
      >
        <Menu size={18} strokeWidth={1.5} />
      </button>

      <span className="text-[13px] font-bold tracking-[0.06em] text-[#0F2847] shrink-0">SYNAPTIQ</span>

      <div className="flex-1 min-w-0 px-2">
        <span className="text-[11px] overline text-slate-500 truncate block">{title}</span>
      </div>

      <div className="flex items-center gap-0.5 shrink-0">
        <button
          onClick={onOpenSearch}
          className="w-9 h-9 flex items-center justify-center text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          aria-label="Search platform"
        >
          <Search size={15} strokeWidth={1.5} />
        </button>

        <Link
          to="/notifications"
          className="relative w-9 h-9 flex items-center justify-center text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          aria-label={`Inbox${notifCount > 0 ? `, ${notifCount} new` : ""}`}
        >
          <Bell size={15} strokeWidth={1.5} />
          {notifCount > 0 && (
            <span
              className="absolute top-1.5 right-1.5 min-w-[14px] h-3.5 bg-[#8A1538] text-white text-[9px] font-mono flex items-center justify-center px-0.5 leading-none rounded-badge"
              aria-hidden="true"
            >
              {notifCount > 9 ? "9+" : notifCount}
            </span>
          )}
        </Link>

        <Link
          to="/messages"
          className="relative w-9 h-9 flex items-center justify-center text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          aria-label={`Messages${msgUnread > 0 ? `, ${msgUnread} unread` : ""}`}
        >
          <MessageSquare size={15} strokeWidth={1.5} />
          {msgUnread > 0 && (
            <span
              className="absolute top-1.5 right-1.5 min-w-[14px] h-3.5 bg-[#0F2847] text-white text-[9px] font-mono flex items-center justify-center px-0.5 leading-none rounded-badge"
              aria-hidden="true"
            >
              {msgUnread > 99 ? "99+" : msgUnread}
            </span>
          )}
        </Link>
      </div>
    </header>
  );
}
