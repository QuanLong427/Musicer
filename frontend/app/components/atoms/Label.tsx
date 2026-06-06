"use client";

import type { ReactNode } from "react";

type LabelSize = "sm" | "md";

type LabelProps = {
  children: ReactNode;
  size?: LabelSize;
  className?: string;
};

const sizeStyles: Record<LabelSize, string> = {
  sm: "text-[11px] font-medium tracking-wide",
  md: "text-[12px] font-semibold tracking-wide",
};

export function Label({ children, size = "sm", className }: LabelProps) {
  return (
    <span
      className={[
        "inline uppercase text-[color:var(--color-on-surface-muted)]",
        sizeStyles[size],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </span>
  );
}
