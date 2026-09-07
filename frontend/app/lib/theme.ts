"use client";

import { useEffect, useSyncExternalStore } from "react";

/**
 * Theme as an external store rather than component state.
 *
 * The previous implementation initialised `isDarkTheme` to false and then read
 * localStorage inside an effect. That is a setState-in-effect: React renders the
 * light theme, commits it, then immediately re-renders dark — a visible flash for
 * anyone who had chosen dark, plus a cascading render on every mount.
 *
 * useSyncExternalStore reads the real value during the first client render and
 * returns a stable server snapshot for SSR, so there is no flash and no cascade.
 */

const STORAGE_KEY = "niraconchem-theme";

export type Theme = "light" | "dark";

let cached: Theme | null = null;
const listeners = new Set<() => void>();

function read(): Theme {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "dark" ? "dark" : "light";
  } catch {
    // Private browsing and blocked site data both throw on access.
    return "light";
  }
}

function getSnapshot(): Theme {
  if (cached === null) cached = read();
  return cached;
}

function getServerSnapshot(): Theme {
  return "light";
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  // Keep tabs in step: another tab writing the key updates this one.
  const onStorage = (event: StorageEvent) => {
    if (event.key === STORAGE_KEY) {
      cached = read();
      listeners.forEach((notify) => notify());
    }
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

export function setTheme(next: Theme) {
  cached = next;
  try {
    window.localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // Preference simply is not persisted; the session still switches.
  }
  listeners.forEach((notify) => notify());
}

export function useTheme(): Theme {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

/**
 * Reflects the theme onto the document.
 *
 * `data-theme` is what the token layer reads; the two legacy classes are kept
 * until the last `.dark-theme` component override in globals.css has been
 * migrated onto tokens.
 */
export function useApplyTheme(isDark: boolean) {
  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = isDark ? "ink" : "light";
    root.classList.toggle("theme-dark-body", isDark);
    document.body.classList.toggle("theme-dark-body", isDark);
  }, [isDark]);
}
