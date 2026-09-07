"use client";

import { useEffect, useState } from "react";

import type { BeforeInstallPromptEvent } from "../lib/types";

/**
 * Captures the browser's install prompt so it can be offered somewhere the page
 * chooses rather than wherever the browser would have put it.
 *
 * Note: this never fires while public/sw.js is the current service worker —
 * that worker unregisters itself on activate, and Chrome requires a live worker
 * with a fetch handler before it will offer installation.
 */
export function useInstallPrompt() {
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    function onBeforeInstallPrompt(event: Event) {
      event.preventDefault();
      setInstallPrompt(event as BeforeInstallPromptEvent);
    }
    window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
  }, []);

  async function install() {
    if (!installPrompt) return;
    await installPrompt.prompt();
    const choice = await installPrompt.userChoice;
    if (choice.outcome !== "dismissed") setInstallPrompt(null);
  }

  return { canInstall: Boolean(installPrompt), install };
}
