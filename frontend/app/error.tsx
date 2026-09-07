"use client";

import { useEffect } from "react";

/**
 * Route error boundary. Without this, an exception anywhere in the client tree
 * replaces the whole application with Next's default error screen — in
 * production, a blank page. This keeps the user inside the product and gives
 * them a way out.
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surfaced here rather than swallowed, so the digest is reachable from the
    // browser console when a user reports a problem.
    console.error("[niraconchem] route error", error);
  }, [error]);

  return (
    <div className="route-state">
      <span className="route-state-mark" aria-hidden="true" />
      <p className="route-state-code">Error</p>
      <h1 className="route-state-title">Something went wrong.</h1>
      <p className="route-state-body">
        The page hit an unexpected error. Trying again usually clears it — the
        recommendation service may simply have been unreachable.
      </p>
      <button className="route-state-action" onClick={reset} type="button">
        Try again
      </button>
      {error.digest ? <p className="route-state-digest">Reference: {error.digest}</p> : null}
    </div>
  );
}
