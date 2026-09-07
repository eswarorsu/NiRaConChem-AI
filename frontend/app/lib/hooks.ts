"use client";

import { useCallback, useEffect, useState } from "react";
import { useSyncExternalStore } from "react";

/* ---------------------------------------------------------------------------
   Media queries
   ---------------------------------------------------------------------------
   Read through useSyncExternalStore rather than useState + useEffect. The
   effect version renders once with a guessed value, commits, then re-renders
   with the real one — a cascading render on every mount, and a visible jump
   when the guess drives layout (particle counts, network density, 3D on/off).
------------------------------------------------------------------------------ */

function useMediaQuery(query: string, serverValue = false): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const mql = window.matchMedia(query);
      mql.addEventListener("change", onChange);
      return () => mql.removeEventListener("change", onChange);
    },
    [query],
  );

  const getSnapshot = useCallback(() => window.matchMedia(query).matches, [query]);

  return useSyncExternalStore(subscribe, getSnapshot, () => serverValue);
}

/** True once the user has asked the OS to reduce motion. Live, not sampled. */
export function usePrefersReducedMotion(): boolean {
  return useMediaQuery("(prefers-reduced-motion: reduce)");
}

export type ViewportClass = "mobile" | "tablet" | "desktop";

/**
 * Coarse device class used to scale visual cost: particle counts, network
 * density, and whether the WebGL hero runs at full complexity.
 */
export function useViewportClass(): ViewportClass {
  const isMobile = useMediaQuery("(max-width: 699px)");
  const isTablet = useMediaQuery("(max-width: 1099px)");
  if (isMobile) return "mobile";
  if (isTablet) return "tablet";
  return "desktop";
}

/* ---------------------------------------------------------------------------
   Reveal on scroll
------------------------------------------------------------------------------ */

type RevealOptions = {
  threshold?: number;
  rootMargin?: string;
};

/**
 * Reveals an element the first time it enters the viewport, and never again.
 *
 * Returns a **callback ref**, not a ref object: React 19 lets a ref callback
 * return its own cleanup, so the observer is created and torn down with the
 * node itself. No ref object survives between renders, which also means the
 * element can remount (a responsive layout swap, a Fast Refresh) without
 * leaking an observer.
 *
 * Reduced motion resolves to "revealed" immediately — the content is never
 * withheld, only the movement is.
 */
export function useReveal<T extends HTMLElement = HTMLDivElement>({
  threshold = 0.18,
  rootMargin = "0px 0px -8% 0px",
}: RevealOptions = {}) {
  const reducedMotion = usePrefersReducedMotion();
  const [seen, setSeen] = useState(false);

  const ref = useCallback(
    (node: T | null) => {
      if (!node || typeof IntersectionObserver === "undefined") return;

      const observer = new IntersectionObserver(
        (entries) => {
          if (entries.some((entry) => entry.isIntersecting)) {
            setSeen(true);
            observer.disconnect();
          }
        },
        { threshold, rootMargin },
      );

      observer.observe(node);
      return () => observer.disconnect();
    },
    [threshold, rootMargin],
  );

  return [ref, seen || reducedMotion] as const;
}

/* ---------------------------------------------------------------------------
   Stepped sequences (the engine pipeline, the recommendation demo)
------------------------------------------------------------------------------ */

/**
 * Advances through `steps` while `active`, looping. Runs only while the section
 * is on screen, so nothing animates in a tab the user cannot see, and collapses
 * to the finished state under reduced motion.
 */
export function useSequence(active: boolean, steps: number, intervalMs: number): number {
  const reducedMotion = usePrefersReducedMotion();
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!active || steps <= 0 || reducedMotion) return;

    const timer = window.setInterval(() => {
      setIndex((current) => (current >= steps ? 0 : current + 1));
    }, intervalMs);

    return () => window.clearInterval(timer);
  }, [active, steps, intervalMs, reducedMotion]);

  if (!active) return -1;
  if (reducedMotion) return steps;
  return index;
}
