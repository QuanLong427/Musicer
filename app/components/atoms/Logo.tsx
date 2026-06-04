export function Logo({ className }: { className?: string }) {
  return (
    <div className={["flex items-center gap-2", className].filter(Boolean).join(" ")}>
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden>
        <circle cx="12" cy="12" r="10" stroke="var(--color-primary)" strokeWidth="1.5" opacity="0.6" />
        <circle cx="12" cy="12" r="5" fill="var(--color-primary)" opacity="0.3" />
        <circle cx="12" cy="12" r="2.5" fill="var(--color-primary)" />
      </svg>
    </div>
  );
}
