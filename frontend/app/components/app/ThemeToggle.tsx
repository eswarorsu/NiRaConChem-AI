"use client";

import { MoonStars, Sun } from "@phosphor-icons/react";

export default function ThemeToggle({
  isDark,
  onToggle,
}: {
  isDark: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      aria-pressed={isDark}
      className="theme-toggle"
      onClick={onToggle}
      title={isDark ? "Light theme" : "Dark theme"}
      type="button"
    >
      <span className="theme-toggle-symbol theme-toggle-sun" aria-hidden="true">
        <Sun size={17} weight="duotone" />
      </span>
      <span className="theme-toggle-symbol theme-toggle-moon" aria-hidden="true">
        <MoonStars size={18} weight="duotone" />
      </span>
      <span className="theme-toggle-knob" aria-hidden="true" />
    </button>
  );
}
