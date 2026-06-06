"use client";

type Props = {
  volume: number;
  onChange: (value: number) => void;
};

export function VolumeControl({ volume, onChange }: Props) {
  const v = Number.isFinite(volume) ? volume : 0;
  const pct = Math.round(v * 100);

  const onInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(Number(e.target.value));
  };

  return (
    <div className="flex min-w-[140px] max-w-[220px] items-center gap-3">
      <span className="shrink-0 text-[color:var(--color-on-surface-muted)]" aria-hidden>
        {v <= 0.001 ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
            <line x1="23" y1="9" x2="17" y2="15" />
            <line x1="17" y1="9" x2="23" y2="15" />
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07" style={{ opacity: v >= 0.35 ? 1 : 0.3 }} />
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14" style={{ opacity: v >= 0.7 ? 1 : 0.3 }} />
          </svg>
        )}
      </span>
      <label className="sr-only" htmlFor="volume-slider">
        Volume
      </label>
      <div className="relative flex flex-1 items-center" style={{ height: "20px" }}>
        <div
          className="pointer-events-none absolute left-0 right-0 overflow-hidden rounded-full"
          style={{
            height: "4px",
            backgroundColor: "rgba(255, 255, 255, 0.08)",
          }}
        >
          <div
            className="h-full rounded-full transition-[width] duration-100"
            style={{
              width: `${pct}%`,
              background: "linear-gradient(to right, #6366f1, #818cf8)",
              boxShadow: "0 0 8px rgba(129, 140, 248, 0.3)",
            }}
          />
        </div>
        <input
          id="volume-slider"
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={v}
          onChange={onInput}
          className={[
            "relative z-[1] w-full cursor-pointer appearance-none bg-transparent",
            "[&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:w-3.5",
            "[&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white/30",
            "[&::-webkit-slider-thumb]:bg-[#818cf8]",
            "[&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(129,140,248,0.5)]",
            "[&::-webkit-slider-runnable-track]:bg-transparent [&::-webkit-slider-runnable-track]:h-3.5",
            "[&::-moz-range-thumb]:h-3.5 [&::-moz-range-thumb]:w-3.5 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-white/30",
            "[&::-moz-range-thumb]:bg-[#818cf8]",
            "[&::-moz-range-thumb]:shadow-[0_0_10px_rgba(129,140,248,0.5)]",
            "[&::-moz-range-track]:bg-transparent [&::-moz-range-track]:h-3.5 [&::-moz-range-track]:border-0",
            "focus-visible:outline-none",
          ].join(" ")}
          style={{ height: "20px" }}
        />
      </div>
    </div>
  );
}
