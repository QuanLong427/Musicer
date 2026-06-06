"use client";

import { useMode, type AppMode } from "@/app/context/ModeContext";

const MODES: { key: AppMode; label: string }[] = [
  { key: "local", label: "LOCAL" },
  { key: "cloud", label: "CLOUD" },
];

export function ModeSwitch() {
  const { mode, setMode } = useMode();

  return (
    <div
      className="flex overflow-hidden rounded-full border"
      style={{
        borderColor: "var(--glass-border)",
        backgroundColor: "rgba(255, 255, 255, 0.04)",
      }}
    >
      {MODES.map(({ key, label }) => {
        const active = mode === key;
        return (
          <button
            key={key}
            onClick={() => setMode(key)}
            className="px-4 py-1.5 text-[11px] font-medium uppercase tracking-wider transition-all duration-200"
            style={{
              backgroundColor: active
                ? "rgba(129, 140, 248, 0.2)"
                : "transparent",
              color: active
                ? "var(--color-primary)"
                : "var(--color-on-surface-muted)",
            }}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
