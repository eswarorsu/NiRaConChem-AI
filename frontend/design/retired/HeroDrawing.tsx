"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { usePrefersReducedMotion, useViewportClass } from "../../lib/hooks";

/**
 * An axonometric section through a waterproofed roof build-up.
 *
 * This replaced a WebGL particle mesh. The mesh was decorative, generic — a
 * node-and-edge plexus is the most reproduced graphic in AI marketing — and it
 * cost three.js and react-three-fiber in the bundle to say nothing about the
 * product. A drawn section says what the product is *for*: the layers a
 * construction chemical decision is actually made about.
 *
 * Pure SVG, so it is resolution independent, themable from the token layer, and
 * free. The build-up shown is standard construction practice, not a
 * manufacturer's system: no product is named and no performance is claimed.
 */

type Layer = {
  id: string;
  label: string;
  note: string;
  thickness: number;
  accent?: boolean;
};

const LAYERS: Layer[] = [
  { id: "slab", label: "Structural slab", note: "Substrate", thickness: 26 },
  { id: "primer", label: "Primer", note: "Adhesion", thickness: 5 },
  {
    id: "membrane",
    label: "Waterproofing membrane",
    note: "The decision",
    thickness: 11,
    accent: true,
  },
  { id: "protection", label: "Protection layer", note: "Separation", thickness: 8 },
  { id: "screed", label: "Screed to falls", note: "Drainage", thickness: 18 },
  { id: "finish", label: "Finish", note: "Exposure", thickness: 7 },
];

/** 2:1 axonometric. u and v run along the plan axes, h is height. */
function iso(u: number, v: number, h: number) {
  return { x: (u - v) * 0.866, y: (u + v) * 0.5 - h };
}

function poly(points: { x: number; y: number }[]) {
  return points.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
}

const U = 190;
const V = 130;

function slabFaces(h0: number, h1: number) {
  const top = [iso(0, 0, h1), iso(U, 0, h1), iso(U, V, h1), iso(0, V, h1)];
  const left = [iso(0, V, h1), iso(U, V, h1), iso(U, V, h0), iso(0, V, h0)];
  const right = [iso(U, 0, h1), iso(U, V, h1), iso(U, V, h0), iso(U, 0, h0)];
  return { top: poly(top), left: poly(left), right: poly(right) };
}

export default function HeroDrawing() {
  const reducedMotion = usePrefersReducedMotion();
  const viewport = useViewportClass();
  const [drawn, setDrawn] = useState(false);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const frame = useRef(0);

  useEffect(() => {
    const timer = window.setTimeout(() => setDrawn(true), 120);
    return () => window.clearTimeout(timer);
  }, []);

  // A few degrees of parallax — present, but under the threshold of notice.
  useEffect(() => {
    if (reducedMotion || viewport === "mobile") return;
    function onMove(event: PointerEvent) {
      cancelAnimationFrame(frame.current);
      frame.current = requestAnimationFrame(() => {
        setTilt({
          x: (event.clientX / window.innerWidth - 0.5) * 14,
          y: (event.clientY / window.innerHeight - 0.5) * 10,
        });
      });
    }
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      cancelAnimationFrame(frame.current);
    };
  }, [reducedMotion, viewport]);

  // Stack the layers from the slab upwards. Written as a fold rather than a
  // running counter: mutating a variable while rendering is not safe under
  // concurrent React, which may abandon and restart a render.
  const stack = useMemo(
    () =>
      LAYERS.reduce<(Layer & { h0: number; h1: number; faces: ReturnType<typeof slabFaces> })[]>(
        (built, layer) => {
          const h0 = built.length ? built[built.length - 1].h1 : 0;
          const h1 = h0 + layer.thickness;
          return [...built, { ...layer, h0, h1, faces: slabFaces(h0, h1) }];
        },
        [],
      ),
    [],
  );

  const labelX = U * 0.866 + 26;

  return (
    <div
      className={`nrc-drawing${drawn ? " is-drawn" : ""}`}
      style={{ "--tilt-x": `${tilt.x}px`, "--tilt-y": `${tilt.y}px` } as React.CSSProperties}
    >
      <svg
        viewBox="-190 -190 560 400"
        role="img"
        aria-label="Axonometric section through a roof build-up: structural slab, primer, waterproofing membrane, protection layer, screed to falls and finish."
        preserveAspectRatio="xMidYMid meet"
      >
        <g className="nrc-drawing-stack">
          {stack.map((layer, index) => (
            <g
              className={`nrc-drawing-layer${layer.accent ? " is-accent" : ""}`}
              key={layer.id}
              style={{ "--i": index } as React.CSSProperties}
            >
              <polygon className="nrc-face nrc-face--left" points={layer.faces.left} />
              <polygon className="nrc-face nrc-face--right" points={layer.faces.right} />
              <polygon className="nrc-face nrc-face--top" points={layer.faces.top} />
            </g>
          ))}
        </g>

        <g className="nrc-drawing-notes">
          {/* Labels are ordered by where each layer actually sits in the
              section — top of the build-up at the top of the list — so the
              leaders run parallel instead of crossing each other. */}
          {[...stack]
            .map((layer) => ({ layer, anchor: iso(U, V * 0.5, (layer.h0 + layer.h1) / 2) }))
            .sort((a, b) => a.anchor.y - b.anchor.y)
            .map(({ layer, anchor }, index) => {
            const y = -104 + index * 36;
            return (
              <g
                className={`nrc-drawing-note${layer.accent ? " is-accent" : ""}`}
                key={layer.id}
                style={{ "--i": index } as React.CSSProperties}
              >
                <path
                  className="nrc-leader"
                  d={`M ${anchor.x.toFixed(1)} ${anchor.y.toFixed(1)} L ${(labelX - 14).toFixed(1)} ${y} L ${labelX} ${y}`}
                />
                <circle className="nrc-leader-dot" cx={anchor.x} cy={anchor.y} r="2.4" />
                <text x={labelX + 8} y={y - 3}>
                  {layer.label}
                </text>
                <text className="nrc-drawing-note-sub" x={labelX + 8} y={y + 11}>
                  {layer.note}
                </text>
              </g>
            );
            })}
        </g>
      </svg>
    </div>
  );
}
