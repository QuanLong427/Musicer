"use client";

import { useDanmaku } from "@/app/context/DanmakuContext";

export function DanmakuToggle() {
  const { enabled, hasDanmaku, error, toggleDanmaku } = useDanmaku();

  const tooltip = error ?? (hasDanmaku ? undefined : "当前音频无弹幕");

  return (
    <div className="relative ml-auto">
      <button
        onClick={toggleDanmaku}
        disabled={!hasDanmaku && !error}
        title={tooltip}
        className="rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-30"
        style={{
          borderColor: error
            ? "rgba(251,113,133,0.3)"
            : enabled
              ? "rgba(129,140,248,0.3)"
              : "var(--glass-border)",
          color: error
            ? "var(--color-error)"
            : enabled
              ? "var(--color-primary)"
              : "var(--color-on-surface-muted)",
          backgroundColor: error
            ? "rgba(251,113,133,0.1)"
            : enabled
              ? "rgba(129,140,248,0.1)"
              : "rgba(255,255,255,0.04)",
          boxShadow: enabled && !error
            ? "0 0 12px rgba(129,140,248,0.2)"
            : "none",
        }}
      >
        DANMAKU
      </button>
    </div>
  );
}
