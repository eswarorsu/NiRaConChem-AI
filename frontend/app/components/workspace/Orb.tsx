/** NiRa's mark in the workspace: a slowly turning ring of warm light. Pure CSS
 *  (see .ws-orb in workspace.css) and still under reduced motion. */
export default function Orb({ size = "lg" }: { size?: "sm" | "lg" }) {
  return (
    <span aria-hidden="true" className={`ws-orb ws-orb-${size}`}>
      <span className="ws-orb-ring" />
      <span className="ws-orb-ring ws-orb-ring-2" />
      <span className="ws-orb-core" />
    </span>
  );
}
