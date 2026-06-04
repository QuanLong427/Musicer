"use client";

type BadgeVariant = "primary" | "error" | "default";

type BadgeProps = {
  label: string;
  variant?: BadgeVariant;
  className?: string;
};

const variantStyles: Record<BadgeVariant, string> = {
  primary:
    "bg-[rgba(129,140,248,0.15)] text-[#a5b4fc] border border-[rgba(129,140,248,0.25)]",
  error:
    "bg-[rgba(251,113,133,0.15)] text-[#fda4af] border border-[rgba(251,113,133,0.25)]",
  default:
    "text-[color:var(--color-on-surface-muted)] bg-[rgba(255,255,255,0.06)] border border-[var(--glass-border)]",
};

export function Badge({ label, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center rounded-full px-2.5 py-0.5",
        "text-[11px] font-medium tracking-wide",
        variantStyles[variant],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {label}
    </span>
  );
}
