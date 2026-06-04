"use client";

import type { DanmakuItem } from "@/app/lib/bili";
import { useDanmaku } from "@/app/context/DanmakuContext";
import { usePlayer } from "@/app/context/PlayerContext";
import { useCallback, useEffect, useRef, useState } from "react";

const LOOKAHEAD = 0.3;
const DANMAKU_TTL = 14000;

type ActiveDanmaku = DanmakuItem & { spawnId: number; ring: number; offset: number };

let spawnIdCounter = 0;

export function DanmakuOverlay() {
  const { state } = usePlayer();
  const { enabled, currentDanmaku } = useDanmaku();

  const [active, setActive] = useState<ActiveDanmaku[]>([]);
  const lastProgressRef = useRef(0);
  const lastIndexRef = useRef(0);

  const progress = state.progress;

  const spawnDanmaku = useCallback(
    (item: DanmakuItem) => {
      const spawnId = ++spawnIdCounter;
      const ring = spawnId % 3;
      const offset = (spawnId * 47) % 360;
      setActive((prev) => [...prev, { ...item, spawnId, ring, offset }]);
      setTimeout(() => {
        setActive((prev) => prev.filter((d) => d.spawnId !== spawnId));
      }, DANMAKU_TTL + 500);
    },
    []
  );

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
        (d) => d.time >= progress - LOOKAHEAD
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
      className="pointer-events-none absolute inset-0 z-30 overflow-hidden flex items-center justify-center"
      aria-hidden
    >
      {/* Wireframe sphere */}
      <div
        className="absolute"
        style={{
          width: "280px",
          height: "280px",
          perspective: "800px",
        }}
      >
        <div
          style={{
            width: "100%",
            height: "100%",
            position: "relative",
            transformStyle: "preserve-3d",
            animation: "sphere-rotate 40s linear infinite",
          }}
        >
          {/* Equator ring */}
          <div
            className="absolute inset-0 rounded-full"
            style={{
              border: "1px solid rgba(124, 140, 248, 0.08)",
              transform: "rotateX(90deg)",
            }}
          />
          {/* Meridian ring 1 */}
          <div
            className="absolute inset-0 rounded-full"
            style={{
              border: "1px solid rgba(124, 140, 248, 0.06)",
              transform: "rotateY(0deg)",
            }}
          />
          {/* Meridian ring 2 */}
          <div
            className="absolute inset-0 rounded-full"
            style={{
              border: "1px solid rgba(124, 140, 248, 0.06)",
              transform: "rotateY(60deg)",
            }}
          />
          {/* Meridian ring 3 */}
          <div
            className="absolute inset-0 rounded-full"
            style={{
              border: "1px solid rgba(124, 140, 248, 0.06)",
              transform: "rotateY(120deg)",
            }}
          />
          {/* Latitude rings */}
          <div
            className="absolute rounded-full"
            style={{
              top: "25%",
              left: "12.5%",
              right: "12.5%",
              bottom: "25%",
              border: "1px solid rgba(124, 140, 248, 0.05)",
              transform: "rotateX(90deg)",
            }}
          />
          <div
            className="absolute rounded-full"
            style={{
              top: "37.5%",
              left: "2.5%",
              right: "2.5%",
              bottom: "37.5%",
              border: "1px solid rgba(124, 140, 248, 0.05)",
              transform: "rotateX(90deg)",
            }}
          />
        </div>
      </div>

      {/* Orbiting danmaku rings */}
      {[0, 1, 2].map((ringIdx) => (
        <div
          key={ringIdx}
          className="absolute"
          style={{
            width: "300px",
            height: "300px",
            perspective: "900px",
          }}
        >
          <div
            style={{
              width: "100%",
              height: "100%",
              position: "relative",
              transformStyle: "preserve-3d",
              animation: `sphere-rotate ${30 + ringIdx * 8}s linear infinite`,
              animationDirection: ringIdx === 1 ? "reverse" : "normal",
            }}
          >
            {active
              .filter((d) => d.ring === ringIdx)
              .map((d) => {
                const ringRadii = [140, 160, 180];
                const ringTilts = [15, -20, 5];
                const radius = ringRadii[ringIdx];
                const tiltX = ringTilts[ringIdx];

                return (
                  <span
                    key={d.spawnId}
                    className="absolute whitespace-nowrap text-xs font-medium"
                    style={{
                      top: "50%",
                      left: "50%",
                      transform: `rotateY(${d.offset}deg) rotateX(${tiltX}deg) translateZ(${radius}px)`,
                      transformStyle: "preserve-3d",
                      color: d.color || "rgba(232, 232, 240, 0.7)",
                      fontFamily: "var(--font-headline)",
                      textShadow: "0 0 8px rgba(0,0,0,0.6), 0 0 16px rgba(0,0,0,0.3)",
                      backfaceVisibility: "hidden",
                      animation: `fade-danmaku 0.8s ease-in forwards`,
                      animationDelay: "0.2s",
                      opacity: 0,
                      marginLeft: "-50%",
                      marginTop: "-0.5em",
                    }}
                  >
                    {d.content}
                  </span>
                );
              })}
          </div>
        </div>
      ))}

      <style>{`
        @keyframes sphere-rotate {
          from { transform: rotateY(0deg); }
          to   { transform: rotateY(360deg); }
        }
        @keyframes fade-danmaku {
          from { opacity: 0; }
          to   { opacity: 0.85; }
        }
      `}</style>
    </div>
  );
}
