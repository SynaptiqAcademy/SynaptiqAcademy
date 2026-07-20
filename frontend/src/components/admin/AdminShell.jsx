import React, { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar, TopNav, ContentFrame } from "@/components/ds";
import AdminCommandPalette from "./AdminCommandPalette";
import { AdminRealtimeProvider } from "@/contexts/AdminRealtimeContext";
import { trackAdminPageVisit } from "@/hooks/useAdminRecentPages";

export default function AdminShell() {
  const [searchOpen, setSearchOpen] = useState(false);
  const { pathname } = useLocation();

  useEffect(() => { trackAdminPageVisit(pathname); }, [pathname]);

  useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen((p) => !p);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <AdminRealtimeProvider>
      <div className="flex h-screen bg-[#F1F5F9] overflow-hidden">
        <Sidebar variant="admin" />
        <div className="flex-1 flex flex-col overflow-hidden">
          <TopNav variant="admin" onOpenSearch={() => setSearchOpen(true)} />
          <main className="flex-1 overflow-y-auto">
            <ContentFrame variant="admin">
              <Outlet />
            </ContentFrame>
          </main>
        </div>
      </div>
      <AdminCommandPalette open={searchOpen} onClose={() => setSearchOpen(false)} />
    </AdminRealtimeProvider>
  );
}
