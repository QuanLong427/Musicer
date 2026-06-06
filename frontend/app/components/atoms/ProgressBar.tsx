"use client";

type ProgressBarProps = {
  value: number;
  className?: string;
};

export function ProgressBar({ value, className }: ProgressBarProps) {
  const clamped = Math.min(1, Math.max(0, Number.isFinite(value) ? value : 0));
  const pct = clamped * 100;

  return (
    <div
      className={[
        "relative h-1 w-full overflow-visible rounded-full",
        "bg-[rgba(255,255,255,0.08)]",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      role="progressbar"
      aria-valuenow={Math.round(clamped * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="pointer-events-none absolute left-0 top-0 h-full rounded-full bg-gradient-to-r from-[#6366f1] to-[#818cf8]"
        style={{ width: `${pct}%` }}
      />
      <div
        className="pointer-events-none absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#818cf8] border-2 border-white/30"
        style={{
          left: `${pct}%`,
          boxShadow: "0 0 12px rgba(129, 140, 248, 0.5)",
        }}
      />
    </div>
  );
}
