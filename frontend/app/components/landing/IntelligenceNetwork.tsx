"use client";

import { useMemo } from "react";
import { motion } from "motion/react";

import { useReveal, useSequence, useViewportClass } from "../../lib/hooks";
import { inView, riseIn, stagger } from "../../lib/motion";

const NODES = [
  "Products",
  "Applications",
  "Substrates",
  "Technical data",
  "Environmental conditions",
  "Project requirements",
  "Manufacturers",
];

const LAYOUTS = {
  desktop: { w: 1000, h: 560, rx: 296, ry: 186, core: 84, node: 8, font: 11.5 },
  tablet: { w: 900, h: 560, rx: 258, ry: 182, core: 78, node: 8, font: 12 },
  mobile: { w: 620, h: 780, rx: 176, ry: 286, core: 72, node: 7.5, font: 13 },
} as const;

export default function IntelligenceNetwork() {
  const [stageRef, stageIn] = useReveal<HTMLDivElement>({ threshold: 0.2 });
  const viewport = useViewportClass();
  const layout = LAYOUTS[viewport];
  const hot = useSequence(stageIn, NODES.length - 1, 1400);

  const points = useMemo(() => {
    const cx = layout.w / 2;
    const cy = layout.h / 2;
    return NODES.map((label, index) => {
      // Start at the top and walk clockwise so the diagram reads like a dial.
      const angle = (index / NODES.length) * Math.PI * 2 - Math.PI / 2;
      const x = cx + Math.cos(angle) * layout.rx;
      const y = cy + Math.sin(angle) * layout.ry;
      const cos = Math.cos(angle);
      const anchor: "middle" | "start" | "end" =
        Math.abs(cos) < 0.25 ? "middle" : cos > 0 ? "start" : "end";
      const dx = anchor === "middle" ? 0 : cos > 0 ? 18 : -18;
      const dy = Math.abs(cos) < 0.25 ? (Math.sin(angle) > 0 ? 26 : -20) : 4;
      return { label, x, y, cx, cy, anchor, dx, dy };
    });
  }, [layout]);

  return (
    <section className="nrc-section" id="network">
      <div className="nrc-wrap">
        <motion.div variants={stagger()} {...inView}>
          <motion.h2 className="nrc-h2 nrc-h2--wide" variants={riseIn}>
            Fragmented knowledge, connected into <span className="nrc-grad">one decision</span>.
          </motion.h2>
        </motion.div>

        <motion.div className="nrc-network" ref={stageRef} variants={riseIn} {...inView}>
          <svg
            role="img"
            aria-label="NiRaConChem AI at the centre of a network connecting products, applications, substrates, technical data, environmental conditions, project requirements and manufacturers."
            viewBox={`0 0 ${layout.w} ${layout.h}`}
            preserveAspectRatio="xMidYMid meet"
          >
            <ellipse
              className="nrc-net-ring"
              cx={layout.w / 2}
              cy={layout.h / 2}
              rx={layout.rx}
              ry={layout.ry}
            />
            <ellipse
              className="nrc-net-ring"
              cx={layout.w / 2}
              cy={layout.h / 2}
              rx={layout.rx * 0.55}
              ry={layout.ry * 0.55}
            />

            {points.map((point, index) => (
              <g key={`edge-${point.label}`}>
                <line
                  className="nrc-net-edge"
                  x1={point.cx}
                  y1={point.cy}
                  x2={point.x}
                  y2={point.y}
                />
                <line
                  className="nrc-net-pulse"
                  x1={point.x}
                  y1={point.y}
                  x2={point.cx}
                  y2={point.cy}
                  style={{ animationDelay: `${index * 0.55}s` }}
                />
              </g>
            ))}

            {points.map((point, index) => (
              <g
                className={`nrc-net-node${index === hot ? " is-hot" : ""}`}
                key={point.label}
              >
                <circle cx={point.x} cy={point.y} r={layout.node} strokeWidth={1.2} />
                <text
                  x={point.x + point.dx}
                  y={point.y + point.dy}
                  textAnchor={point.anchor}
                  fontSize={layout.font}
                >
                  {point.label}
                </text>
              </g>
            ))}

            <g className="nrc-net-node nrc-net-core is-hot">
              <ellipse
                cx={layout.w / 2}
                cy={layout.h / 2}
                rx={layout.rx * 0.28}
                ry={layout.ry * 0.28}
                strokeWidth={1.4}
              />
              <text
                x={layout.w / 2}
                y={layout.h / 2}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={layout.font - 1}
              >
                NiRaConChem AI
              </text>
            </g>
          </svg>
          <p className="nrc-net-legend">Retrieval graph</p>
        </motion.div>
      </div>
    </section>
  );
}
