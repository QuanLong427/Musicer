"use client";

const SPECTRUM_KF = `@keyframes sp-bounce{0%,100%{transform:scaleY(0.35)}50%{transform:scaleY(1)}}`;

type Props = {
  active: boolean;
  muted: boolean;
};

export function SpectrumBars({ active, muted }: Props) {
  const barCount = 4;

  return (
    <>
      <style>{SPECTRUM_KF}</style>
      <span
        className="inline-flex items-end gap-[3px]"
        style={{
          height: "20px",
          opacity: muted ? 0.4 : 1,
        }}
        aria-hidden
      >
        {Array.from({ length: barCount }).map((_, i) => {
          const durations = ["0.48s", "0.62s", "0.55s", "0.72s"];
          const delays = ["0s", "0.18s", "0.08s", "0.32s"];

          return (
            <span
              key={i}
              className="inline-block w-[3px] rounded-full"
              style={{
                height: "100%",
                backgroundColor: muted
                  ? "var(--color-on-surface-muted)"
                  : "var(--color-primary)",
                boxShadow: muted ? "none" : "0 0 8px rgba(129,140,248,0.4)",
                animationName: "sp-bounce",
                animationDuration: durations[i] ?? "0.55s",
                animationDelay: delays[i] ?? "0s",
                animationIterationCount: "infinite",
                animationTimingFunction: "ease-in-out",
                animationPlayState: active && !muted ? "running" : "paused",
                transformOrigin: "bottom",
              }}
            />
          );
        })}
      </span>
    </>
  );
}
