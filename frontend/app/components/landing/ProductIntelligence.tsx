"use client";

import { useState } from "react";
import { motion } from "motion/react";
import { FileText } from "@phosphor-icons/react";
import { CATALOG_PRODUCTS } from "./catalog.data";
import { inView, riseIn, stagger } from "../../lib/motion";

/** "shore_d_hardness" -> "Shore D hardness" */
function humanise(key: string) {
  return key
    .split("_")
    .map((word, index) => {
      if (word.length <= 2) return word.toUpperCase();
      return index === 0 ? word.charAt(0).toUpperCase() + word.slice(1) : word;
    })
    .join(" ");
}

function titleCase(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export default function ProductIntelligence() {
  const [activeIndex, setActiveIndex] = useState(0);
  const product = CATALOG_PRODUCTS[activeIndex];

  return (
    <section className="nrc-section" id="product">
      <div className="nrc-wrap">
        <motion.div variants={stagger()} {...inView}>
          <motion.h2 className="nrc-h2" variants={riseIn}>
            Every recommendation is backed by a <span className="nrc-grad">record</span>.
          </motion.h2>
          <motion.p className="nrc-lede" variants={riseIn}>
            Live entries from the index, carrying the values printed on the
            manufacturer&rsquo;s own datasheet.
          </motion.p>
        </motion.div>

        <motion.div className="nrc-console" variants={riseIn} {...inView}>
          <div className="nrc-console-bar">
            <span>Product index</span>
            <strong>
              {activeIndex + 1} / {CATALOG_PRODUCTS.length} shown
            </strong>
            <span className="nrc-pulse" aria-hidden="true" />
          </div>

          <div className="nrc-console-body">
            <div className="nrc-console-list" role="tablist" aria-label="Indexed products">
              {CATALOG_PRODUCTS.map((entry, index) => (
                <button
                  aria-controls="nrc-product-detail"
                  aria-selected={index === activeIndex}
                  className={`nrc-console-item${index === activeIndex ? " is-active" : ""}`}
                  key={entry.name}
                  onClick={() => setActiveIndex(index)}
                  role="tab"
                  type="button"
                >
                  <strong>{entry.name}</strong>
                  <span>{entry.category}</span>
                </button>
              ))}
            </div>

            <div className="nrc-console-detail" id="nrc-product-detail" role="tabpanel">
              <div className="nrc-console-title">
                <div>
                  <h3>{product.name}</h3>
                  <p>
                    {product.manufacturer} · {product.country} · {product.systemType}
                  </p>
                </div>
              </div>

              <dl className="nrc-spec">
                <div>
                  <dt>Application</dt>
                  <dd>{titleCase(product.category)}</dd>
                </div>
                <div>
                  <dt>Application areas</dt>
                  <dd>{product.applicationAreas.map(titleCase).join(", ")}</dd>
                </div>
                <div>
                  <dt>Climate fit</dt>
                  <dd>{product.climateStrengths.map(titleCase).join(", ")}</dd>
                </div>
                {Object.entries(product.performance).map(([key, value]) => (
                  <div key={key}>
                    <dt>{humanise(key)}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>

              <p className="nrc-lede" style={{ marginTop: 0, fontSize: 14 }}>
                {product.tagline ? <strong>{product.tagline}. </strong> : null}
                {product.description}
              </p>

              <p className="nrc-source">
                <FileText size={15} weight="duotone" />
                Source: {product.documents.join(", ") || "Manufacturer documentation"}
                {product.datasheetUrl ? (
                  <>
                    {" · "}
                    <a href={product.datasheetUrl} rel="noreferrer noopener" target="_blank">
                      Open datasheet
                    </a>
                  </>
                ) : null}
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
