"use client";

import Image from "next/image";

import type { MarketProduct } from "../../lib/types";

export default function MarketResults({
  products,
  isProjectQuery,
}: {
  products: MarketProduct[];
  isProjectQuery: boolean;
}) {
  return (
    <div className="market-results" aria-label="Market result products">
      <p className="market-summary">
        {isProjectQuery
          ? "Ranked against the project conditions resolved from this conversation."
          : "Describe a project condition for tighter matching."}
      </p>
      <div className="market-grid">
        {products.map((product) => (
          <a className="market-card" href={product.url} key={product.url} rel="noreferrer" target="_blank">
            <span className="market-image">
              <Image
                alt={product.name}
                height={180}
                loading="lazy"
                sizes="(max-width: 700px) 45vw, 220px"
                src={product.localImage || product.imageUrl || "/icons/brand-mark.png"}
                width={240}
              />
            </span>
            <span className="market-card-body">
              <span className="market-brand">{product.company}</span>
              <strong>{product.name}</strong>
              <span>{product.category}</span>
              {product.description ? <p>{product.description}</p> : null}
              {product.price ? <em>{product.price}</em> : null}
            </span>
          </a>
        ))}
      </div>
    </div>
  );
}
