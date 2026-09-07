/**
 * Route-level loading state. App Router streams this in while the page's
 * server work resolves, so the first paint is the brand rather than a blank
 * document. Deliberately quiet — it is on screen for a few hundred milliseconds.
 */
export default function Loading() {
  return (
    <div className="route-state" role="status" aria-live="polite">
      <span className="route-state-mark" aria-hidden="true" />
      <p className="route-state-title">NiRaConChem AI</p>
      <p className="route-state-body">Loading the workspace…</p>
    </div>
  );
}
