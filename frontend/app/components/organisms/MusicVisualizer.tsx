"use client";

import { useEffect, useRef } from "react";

export function MusicVisualizer() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    let cleanup: (() => void) | undefined;

    import("./MusicVisualizerCore").then(({ initVisualizer }) => {
      cleanup = initVisualizer(containerRef.current!);
    });

    return () => cleanup?.();
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        position: "fixed",
        inset: 0,
        width: "100%",
        height: "100%",
        zIndex: 0,
        pointerEvents: "none",
      }}
    />
  );
}
