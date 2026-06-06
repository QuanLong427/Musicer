"use client";

import type { DanmakuItem } from "@/app/lib/bili";
import { useDanmaku } from "@/app/context/DanmakuContext";
import { usePlayer } from "@/app/context/PlayerContext";
import { useCallback, useEffect, useRef, useState } from "react";

const LOOKAHEAD = 0.3;
const DANMAKU_TTL = 9000;
const DRIFT_STEPS = 8;
const BOUNDARY_LEFT = 8;
const BOUNDARY_RIGHT = 80;

type ActiveDanmaku = DanmakuItem & {
  spawnId: number;
  left: number;
  duration: number;
  delay: number;
  hasBorder: boolean;
  borderHue: number;
  keyframes: string;
};

let spawnIdCounter = 0;

function seededRandom(seed: number) {
  const x = Math.sin(seed * 9301 + 49297) * 233280;
  return x - Math.floor(x);
}

function clamp(val: number, min: number, max: number) {
  return Math.max(min, Math.min(max, val));
}

/**
 * 生成弹幕的漂移路径 keyframes CSS 字符串。
 * 弹幕从 startX 出发，每步水平漂移一定距离，
 * 碰到左右边界时弹回（钳制到边界内）。
 */
function generateDriftKeyframes(
  startX: number,
  driftSpeed: number,
  _duration: number,
): string {
  const frames: string[] = [];
  let x = startX;

  for (let i = 0; i <= DRIFT_STEPS; i++) {
    const pct = (i / DRIFT_STEPS) * 100;
    const yVh = -(i / DRIFT_STEPS) * 105;
    let opacity = "0.9";
    if (i === 0) opacity = "0";
    else if (i === 1) opacity = "0.9";
    else if (i >= DRIFT_STEPS - 1) opacity = "0";

    frames.push(
      `${pct.toFixed(1)}% { transform: translateX(${(x - startX).toFixed(1)}vw) translateY(${yVh.toFixed(1)}vh); opacity: ${opacity}; }`,
    );

    if (i < DRIFT_STEPS) {
      const stepDuration = _duration / DRIFT_STEPS;
      const drift = driftSpeed * stepDuration * 0.03;
      x = clamp(x + drift, BOUNDARY_LEFT, BOUNDARY_RIGHT);
    }
  }

  return `@keyframes dm-drift-${spawnIdCounter} { ${frames.join(" ")} }`;
}

export function DanmakuOverlay() {
  const { state } = usePlayer();
  const { enabled, currentDanmaku } = useDanmaku();

  const [active, setActive] = useState<ActiveDanmaku[]>([]);
  const lastProgressRef = useRef(0);
  const lastIndexRef = useRef(0);

  const progress = state.progress;

  const spawnDanmaku = useCallback((item: DanmakuItem) => {
    const id = ++spawnIdCounter;
    const r = seededRandom(id);
    const left = 10 + r * 70;
    const duration = 5 + seededRandom(id + 1) * 4;
    const delay = seededRandom(id + 2) * 0.5;
    const hasBorder = seededRandom(id + 3) > 0.5;
    const borderHue = Math.floor(seededRandom(id + 4) * 360);
    const driftSpeed = (seededRandom(id + 5) - 0.5) * 60;

    const keyframes = generateDriftKeyframes(left, driftSpeed, duration);

    setActive((prev) => [
      ...prev,
      { ...item, spawnId: id, left, duration, delay, hasBorder, borderHue, keyframes },
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
      spawnDanmaku(items[idx]!);
      idx++;
    }
    lastIndexRef.current = idx;
  }, [progress, enabled, currentDanmaku, spawnDanmaku]);

  if (!enabled || !currentDanmaku.length) return null;

  return (
    <div
      className="pointer-events-none absolute inset-0 z-30 overflow-hidden"
      aria-hidden
    >
      <style>{active.map((d) => d.keyframes).join("\n")}</style>
      {active.map((d) => (
        <span
          key={d.spawnId}
          className="absolute bottom-0 whitespace-nowrap rounded-full px-5 py-2.5 text-sm font-bold"
          style={{
            left: `${d.left}%`,
            animation: `dm-drift-${d.spawnId} ${d.duration}s linear ${d.delay}s forwards`,
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
