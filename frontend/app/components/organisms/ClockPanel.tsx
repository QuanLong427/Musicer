"use client";

import { GlowDot } from "@/app/components/atoms/GlowDot";
import { Label } from "@/app/components/atoms/Label";
import { useClock } from "@/app/hooks/useClock";

export function ClockPanel() {
  const { time, day, date } = useClock();
  const [hours, minutes] = time.split(":");

  return (
    <div
      className="relative overflow-hidden rounded-xl border p-5 transition-all duration-200"
      style={{
        borderColor: "var(--glass-border)",
        backgroundColor: "rgba(255, 255, 255, 0.025)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
      }}
    >
      {/* Subtle scan line */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(124,140,248,0.015) 2px, rgba(124,140,248,0.015) 3px)",
        }}
      />

      <div className="relative z-10 flex flex-col gap-5">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <GlowDot color="error" />
          <Label size="sm">LIVE</Label>
          <Label size="sm" className="text-[color:var(--color-cta)]">
            STREAMING
          </Label>
        </div>

        <div className="text-center">
          <div
            aria-live="polite"
            className="block tracking-tight"
            style={{
              fontFamily: "var(--font-headline)",
              fontSize: "52px",
              fontWeight: 700,
              lineHeight: "1.05",
              background: "linear-gradient(135deg, #7c8cf8 0%, #b0a0f0 50%, #7c8cf8 100%)",
              backgroundSize: "200% 100%",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
              animation: "gradient-shift 8s ease infinite",
              filter: "drop-shadow(0 0 20px rgba(124,140,248,0.2))",
            }}
          >
            {hours}
            <span style={{ opacity: 0.5 }}>:</span>
            {minutes}
          </div>
          <div className="mt-3 flex flex-wrap items-baseline justify-center gap-x-4 gap-y-2 md:justify-start">
            <span className="text-sm font-medium uppercase tracking-[0.2em] text-[color:var(--color-on-surface)]">
              {day}
            </span>
            <span className="text-sm text-[color:var(--color-on-surface-muted)]">
              {date}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
