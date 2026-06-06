"use client";

type GlowDotColor = "primary" | "error";

type GlowDotProps = {
  color?: GlowDotColor;
  size?: number;
  className?: string;
};

const colorGlow: Record<GlowDotColor, { dot: string; shadow: string }> = {
  primary: {
    dot: "bg-[#818cf8]",
    shadow: "0 0 12px rgba(129, 140, 248, 0.5)",
  },
  error: {
    dot: "bg-[#fb7185]",
    shadow: "0 0 12px rgba(251, 113, 133, 0.5)",
  },
};

export function GlowDot({ color = "primary", size = 8, className }: GlowDotProps) {
  const { dot, shadow } = colorGlow[color];

  return (
    <span
      role="presentation"
      className={["inline-block shrink-0 rounded-full animate-glow-pulse", dot, className].filter(Boolean).join(" ")}
      style={{
        width: size,
        height: size,
        boxShadow: shadow,
      }}
    />
  );
}
