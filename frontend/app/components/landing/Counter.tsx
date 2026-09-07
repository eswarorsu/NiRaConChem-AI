"use client";

import { useEffect, useRef } from "react";
import { animate, useInView, useReducedMotion } from "motion/react";

/**
 * Counts up to a value the first time it scrolls into view.
 *
 * Driven by Motion's imperative `animate` writing straight to textContent, so
 * the count never triggers a React render per frame.
 */
export default function Counter({
  to,
  suffix = "",
  duration = 1.4,
}: {
  to: number;
  suffix?: string;
  duration?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.5 });
  const reduced = useReducedMotion();

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    if (reduced || !inView) {
      if (reduced) node.textContent = to.toLocaleString("en-US") + suffix;
      return;
    }

    const controls = animate(0, to, {
      duration,
      ease: [0.16, 0.84, 0.32, 1],
      onUpdate: (value) => {
        node.textContent = Math.round(value).toLocaleString("en-US") + suffix;
      },
    });

    return () => controls.stop();
  }, [inView, reduced, to, suffix, duration]);

  return (
    <span ref={ref}>
      0{suffix}
    </span>
  );
}
