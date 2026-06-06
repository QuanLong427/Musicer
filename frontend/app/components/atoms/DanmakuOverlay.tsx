"use client";

import type { DanmakuItem } from "@/app/lib/bili";
import { useDanmaku } from "@/app/context/DanmakuContext";
import { usePlayer } from "@/app/context/PlayerContext";
import { useCallback, useEffect, useRef, useState } from "react";

const LOOKAHEAD = 0.3;
const DANMAKU_TTL = 9000;
const DRIFT_STEPS = 12;
const SKIP_BEFORE = 1.0; // Skip danmaku before this time (e.g. opening "你好")

type ActiveDanmaku = DanmakuItem & {
  spawnId: number;
  status: "pending" | "active";
  initialX: number;
  textW: number;
  duration: number;
  delay: number;
  hasBorder: boolean;
  borderHue: number;
  keyframes: string;
};

let spawnIdCounter = 0;

function seededRandom(seed: number) {
  let h = seed | 0;
  h = (h ^ 61) ^ (h >>> 16);
  h = h + (h << 3);
  h = h ^ (h >>> 4);
  h = (h * 0x27d4eb2d) | 0;
  h = h ^ (h >>> 15);
  return (h >>> 0) / 4294967296;
}

/**
 * Generate drift keyframes. Clamps position to stay within boundaries.
 */
function generateDriftKeyframes(
  initialX: number,
  driftSpeed: number,
  duration: number,
  boundaryLeft: number,
  boundaryRight: number,
  spawnId: number,
): string {
  const frames: string[] = [];
  let x = initialX;
  const dir = driftSpeed >= 0 ? 1 : -1;
  const absSpeed = Math.abs(driftSpeed);

  for (let i = 0; i <= DRIFT_STEPS; i++) {
    const pct = (i / DRIFT_STEPS) * 100;
    const yVh = -(i / DRIFT_STEPS) * 105;
    let opacity = "0.9";
    if (i === 0) opacity = "0";
    else if (i === 1) opacity = "0.9";
    else if (i >= DRIFT_STEPS - 1) opacity = "0";

    // Clamp x to boundaries
    const clampedX = Math.max(boundaryLeft, Math.min(boundaryRight, x));

    frames.push(
      `${pct.toFixed(1)}% { transform: translateX(${clampedX.toFixed(1)}px) translateY(${yVh.toFixed(1)}vh); opacity: ${opacity}; }`,
    );

    if (i < DRIFT_STEPS) {
      const stepDur = duration / DRIFT_STEPS;
      const step = absSpeed * stepDur * 0.25;
      x = x + dir * step;
    }
  }

  return `@keyframes dm-drift-${spawnId} { ${frames.join(" ")} }`;
}

export function DanmakuOverlay() {
  const { state } = usePlayer();
  const { enabled, currentDanmaku } = useDanmaku();
  const containerRef = useRef<HTMLDivElement>(null);
  const containerWidthRef = useRef(600);

  const [active, setActive] = useState<ActiveDanmaku[]>([]);
  const lastProgressRef = useRef(0);
  const lastIndexRef = useRef(0);

  const progress = state.progress;

  // ResizeObserver: track container width
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    containerWidthRef.current = el.clientWidth;

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        containerWidthRef.current = entry.contentRect.width;
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Phase 2: Measure pending danmaku widths and activate them
  useEffect(() => {
    const pending = active.filter((d) => d.status === "pending");
    if (!pending.length) return;

    const w = containerWidthRef.current;

    const toActivate: ActiveDanmaku[] = [];

    for (const d of pending) {
      const el = containerRef.current?.querySelector(
        `[data-dm-id="${d.spawnId}"]`,
      ) as HTMLElement | null;
      if (!el) continue;

      // Measure actual rendered width (includes px-5 padding)
      const textW = el.getBoundingClientRect().width;

      // Center-based positioning: center ∈ [textW/2, containerWidth - textW/2]
      const halfW = textW / 2;
      const minCenter = halfW;
      const maxCenter = w - halfW;
      const center = minCenter + seededRandom(d.spawnId + 100) * Math.max(maxCenter - minCenter, 1);

      // leftEdge = center - textW/2
      const leftEdge = center - halfW;

      // Boundaries for drift: 弹幕左边缘 ∈ [0, containerWidth - textW - SAFETY]
      const SAFETY = 20;
      const bL = SAFETY;
      const bR = w - textW - SAFETY;

      const keyframes = generateDriftKeyframes(
        leftEdge,
        d.borderHue, // using as temp — will be overwritten
        d.duration,
        bL,
        bR,
        d.spawnId,
      );

      toActivate.push({
        ...d,
        status: "active",
        textW,
        initialX: leftEdge,
        keyframes: generateDriftKeyframes(
          leftEdge,
          (seededRandom(d.spawnId + 5) - 0.5) * 50,
          d.duration,
          bL,
          bR,
          d.spawnId,
        ),
      });
    }

    if (toActivate.length) {
      setActive((prev) =>
        prev.map((d) => {
          const activated = toActivate.find((a) => a.spawnId === d.spawnId);
          return activated ?? d;
        }),
      );
    }
  }, [active]);

  // Phase 1: Spawn danmaku as pending (measured later)
  const spawnDanmaku = useCallback((item: DanmakuItem) => {
    const id = ++spawnIdCounter;
    const duration = 5 + seededRandom(id + 1) * 4;
    const delay = seededRandom(id + 2) * 0.5;
    const hasBorder = seededRandom(id + 3) > 0.5;
    const borderHue = Math.floor(seededRandom(id + 4) * 360);

    setActive((prev) => [
      ...prev,
      {
        ...item,
        spawnId: id,
        status: "pending",
        initialX: 0,
        textW: 0,
        duration,
        delay,
        hasBorder,
        borderHue,
        keyframes: "",
      },
    ]);
    setTimeout(() => {
      setActive((prev) => prev.filter((d) => d.spawnId !== id));
    }, DANMAKU_TTL + 500);
  }, []);

  useEffect(() => {
    if (!enabled || !currentDanmaku.length) {
      setActive([]);
      lastIndexRef.current = 0;
      lastProgressRef.current = progress;
      return;
    }

    const delta = progress - lastProgressRef.current;
    const seeked = delta < -1 || delta > 3;
    lastProgressRef.current = progress;

    if (seeked) {
      setActive([]);
      lastIndexRef.current = 0;
      if (progress <= 0) return;
      const resumeIdx = currentDanmaku.findIndex(
        (d) => d.time >= progress - LOOKAHEAD,
      );
      lastIndexRef.current = Math.max(0, resumeIdx);
    }

    const target = progress + LOOKAHEAD;
    const items = currentDanmaku;
    let idx = lastIndexRef.current;
    while (idx < items.length && items[idx]!.time <= target) {
      if (items[idx]!.time >= SKIP_BEFORE) {
        spawnDanmaku(items[idx]!);
      }
      idx++;
    }
    lastIndexRef.current = idx;
  }, [progress, enabled, currentDanmaku, spawnDanmaku]);

  if (!enabled || !currentDanmaku.length) return null;

  // Only render active (measured) danmaku, pending ones are invisible
  const visible = active.filter((d) => d.status === "active");

  return (
    <div
      ref={containerRef}
      className="pointer-events-none absolute inset-0 z-30 overflow-hidden"
      aria-hidden
    >
      <style>{visible.map((d) => d.keyframes).join("\n")}</style>
      {active.map((d) => (
        <span
          key={d.spawnId}
          data-dm-id={d.spawnId}
          className="absolute bottom-0 left-0 whitespace-nowrap rounded-full px-5 py-2.5 text-sm font-bold"
          style={{
            animation:
              d.status === "active"
                ? `dm-drift-${d.spawnId} ${d.duration}s linear ${d.delay}s forwards`
                : undefined,
            opacity: 0,
            color: d.color || "var(--color-on-surface)",
            textShadow:
              "0 0 6px var(--color-primary), 1px 1px 3px rgba(0,0,0,0.8)",
            ...(d.hasBorder
              ? {
                  background: `hsla(${d.borderHue}, 100%, 20%, 0.25)`,
                  border: `1px solid hsla(${d.borderHue}, 100%, 60%, 0.5)`,
                  boxShadow: `0 0 12px hsla(${d.borderHue}, 100%, 60%, 0.3), inset 0 0 8px hsla(${d.borderHue}, 100%, 60%, 0.15)`,
                  backdropFilter: "blur(4px)",
                }
              : {}),
          }}
        >
          {d.content}
        </span>
      ))}
    </div>
  );
}
