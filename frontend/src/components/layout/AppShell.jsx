import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { Sidebar, TopNav, ContentFrame } from "@/components/ds";
import MobileTopBar from "./MobileTopBar";
import MobileDrawer from "./MobileDrawer";
import MobileBottomNav from "./MobileBottomNav";
import MobileSearch from "./MobileSearch";
import CommandPalette from "./CommandPalette";
import { trackPageVisit } from "../../hooks/useRecentPages";
import { recordVisit } from "../../hooks/useUserMemory";
import ProactivePanel from "../proactive/ProactivePanel";
import { loadPrefs } from "../../hooks/usePreferences";
import { applyPreferenceEffects } from "../../lib/applyPreferenceEffects";

export default function AppShell({ children }) {
  const [drawerOpen,  setDrawerOpen]  = useState(false);
  const [searchOpen,  setSearchOpen]  = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { pathname } = useLocation();

  // Apply the stored Application Preferences' real, working effects (reduced
  // motion, focus indicators, font size, high contrast) on every app boot —
  // not just when the Settings page happens to be open.
  useEffect(() => {
    applyPreferenceEffects(loadPrefs());
  }, []);

  // Close mobile overlays on route change
  useEffect(() => {
    setDrawerOpen(false);
    setSearchOpen(false);
  }, [pathname]);

  // Track recently visited pages (label lookup) + behavior memory (frequency)
  useEffect(() => {
    trackPageVisit(pathname);
    recordVisit(pathname);
  }, [pathname]);

  // Global keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      // ⌘K / Ctrl+K — toggle command palette
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setPaletteOpen((p) => !p);
        return;
      }

      // / — open command palette (only when focus is not inside a text field)
      if (
        e.key === "/" &&
        !paletteOpen &&
        document.activeElement?.tagName !== "INPUT" &&
        document.activeElement?.tagName !== "TEXTAREA" &&
        !document.activeElement?.isContentEditable
      ) {
        e.preventDefault();
        setPaletteOpen(true);
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [paletteOpen]);

  return (
    <div className="min-h-screen flex" style={{ background: "#FAFAFA" }}>
      {/* Desktop sidebar — lg+ only */}
      <Sidebar />

      {/* Mobile top bar — below lg */}
      <MobileTopBar
        onOpenDrawer={() => setDrawerOpen(true)}
        onOpenSearch={() => setSearchOpen(true)}
      />

      {/* Mobile slide-over drawer */}
      <MobileDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />

      {/* Mobile global search overlay */}
      <MobileSearch
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
      />

      {/* Desktop content column */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Desktop top bar — lg+ only, in normal flow */}
        <TopNav onOpenPalette={() => setPaletteOpen(true)} />

        {/* Main content
            pt-14: offset fixed mobile top bar (no effect on lg since TopBar is in-flow)
            pb-20/md:pb-6: offset fixed mobile bottom nav */}
        <main className="flex-1 pt-14 lg:pt-0 pb-20 md:pb-0">
          <ContentFrame variant="app">
            {children}
          </ContentFrame>
        </main>
      </div>

      {/* Mobile bottom navigation — below md */}
      <MobileBottomNav onOpenDrawer={() => setDrawerOpen(true)} />

      {/* Global command palette — available everywhere via ⌘K or / */}
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
      />

      {/* Proactive AI panel — floating, always accessible, never a modal */}
      <ProactivePanel />
    </div>
  );
}
