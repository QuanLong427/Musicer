"use client";

export function Logo({
  className,
  onClick,
}: {
  className?: string;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={["flex items-center gap-2 cursor-pointer transition-opacity hover:opacity-80", className]
        .filter(Boolean)
        .join(" ")}
      aria-label="Settings"
    >
      <span
        className="material-symbols-outlined"
        style={{ fontSize: "22px", color: "var(--color-primary)" }}
      >
        settings
      </span>
    </button>
  );
}
