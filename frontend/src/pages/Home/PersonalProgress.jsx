/* eslint-disable */
import React from "react";
import ReputationWidget from "@/components/reputation/ReputationWidget";

/**
 * PersonalProgress — surfaces the existing reputation/badges system
 * (already built for Today.jsx and the Academic Passport) on the main
 * dashboard too, instead of building a second badges/achievements widget.
 * Renders nothing while loading or if the user has no reputation data yet
 * (ReputationWidget itself returns null in that case).
 */
export default function PersonalProgress() {
  return (
    <section aria-label="Personal Progress">
      <ReputationWidget />
    </section>
  );
}
