import Link from "next/link";

export const metadata = {
  title: "Page not found · NiRaConChem AI",
};

export default function NotFound() {
  return (
    <div className="route-state">
      <span className="route-state-mark" aria-hidden="true" />
      <p className="route-state-code">404</p>
      <h1 className="route-state-title">This page doesn&rsquo;t exist.</h1>
      <p className="route-state-body">
        The link may be out of date. Everything lives on one page — start from there.
      </p>
      <Link className="route-state-action" href="/">
        Back to NiRaConChem AI
      </Link>
    </div>
  );
}
