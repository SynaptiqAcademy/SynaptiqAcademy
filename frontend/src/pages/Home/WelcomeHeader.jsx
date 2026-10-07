/* eslint-disable */
import React from "react";

function getGreeting() {
  const h = new Date().getHours();
  if (h < 5)  return "Good evening";
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function formatDate() {
  return new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
}

/**
 * WelcomeHeader — the Home page header, in the shared product-header
 * language (eyebrow, serif title, one line). Plan, credits, notifications
 * and settings live in the app shell; they are not repeated here.
 */
export default function WelcomeHeader({ user }) {
  const firstName = user?.first_name || user?.full_name?.split(" ")[0] || "there";
  return (
    <header className="hm-head">
      <p className="pl-eyebrow">{formatDate()}</p>
      <h1 className="pl-hero-title">{getGreeting()}, {firstName}.</h1>
    </header>
  );
}
