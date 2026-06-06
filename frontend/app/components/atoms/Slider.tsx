"use client";

type SliderProps = {
  value: number;
  onChange: (value: number) => void;
  className?: string;
};

export function Slider({ value, onChange, className }: SliderProps) {
  const safe = Math.min(1, Math.max(0, Number.isFinite(value) ? value : 0));

  return (
    <input
      type="range"
      min={0}
      max={1}
      step={0.001}
      value={safe}
      onChange={(e) => {
        const v = parseFloat(e.target.value);
        onChange(Number.isFinite(v) ? Math.min(1, Math.max(0, v)) : 0);
      }}
      className={[
        "h-2 w-full appearance-none cursor-pointer bg-transparent",
        "[&::-webkit-slider-runnable-track]:h-1 [&::-webkit-slider-runnable-track]:rounded-full",
        "[&::-webkit-slider-runnable-track]:bg-[rgba(255,255,255,0.08)]",
        "[&::-moz-range-track]:h-1 [&::-moz-range-track]:rounded-full [&::-moz-range-track]:border-0",
        "[&::-moz-range-track]:bg-[rgba(255,255,255,0.08)]",
        "[&::-webkit-slider-thumb]:-mt-[5px] [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:w-3.5",
        "[&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full",
        "[&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white/30",
        "[&::-webkit-slider-thumb]:bg-[#818cf8]",
        "[&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(129,140,248,0.5)]",
        "[&::-moz-range-thumb]:h-3.5 [&::-moz-range-thumb]:w-3.5 [&::-moz-range-thumb]:rounded-full",
        "[&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-white/30",
        "[&::-moz-range-thumb]:bg-[#818cf8]",
        "[&::-moz-range-thumb]:shadow-[0_0_10px_rgba(129,140,248,0.5)]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#818cf8] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0a0a1a]",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    />
  );
}
