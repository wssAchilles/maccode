import { animate } from "animejs";
import { useEffect, useRef } from "react";
import type { ReactNode } from "react";

import { prefersReducedMotion } from "../../hooks/useAnimeScope";

interface MetricTileProps {
  alert?: boolean;
  detail?: ReactNode;
  label: string;
  value: ReactNode;
  tone?: "neutral" | "green" | "blue" | "cyan" | "amber" | "red";
}

export function MetricTile({ alert = false, detail, label, value, tone = "neutral" }: MetricTileProps) {
  const tileRef = useRef<HTMLElement | null>(null);
  const valueRef = useRef<HTMLElement | null>(null);
  const hasMountedRef = useRef(false);

  useEffect(() => {
    if (!tileRef.current || prefersReducedMotion()) {
      return;
    }
    if (!hasMountedRef.current) {
      hasMountedRef.current = true;
      return;
    }

    animate(tileRef.current, {
      opacity: [0.84, 1],
      y: [3, 0],
      duration: 260,
      ease: "out(3)"
    });
    if (valueRef.current) {
      animate(valueRef.current, {
        scale: [1, 1.045, 1],
        duration: 320,
        ease: "out(3)"
      });
    }
  }, [alert, detail, tone, value]);

  return (
    <section className={`metric-tile ${tone}${alert ? " alert" : ""}`} ref={tileRef}>
      <span>{label}</span>
      <strong ref={valueRef}>{value}</strong>
      {detail && <small>{detail}</small>}
    </section>
  );
}
