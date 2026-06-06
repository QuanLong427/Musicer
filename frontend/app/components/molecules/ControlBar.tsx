"use client";

type Props = {
  playing: boolean;
  onPrev: () => void;
  onToggle: () => void | Promise<void>;
  onNext: () => void;
  onStop: () => void;
};

const btn =
  "group relative inline-flex h-10 w-10 items-center justify-center rounded-full bg-[rgba(255,255,255,0.06)] border border-[var(--glass-border)] text-[var(--color-on-surface-muted)] transition-all duration-200 cursor-pointer " +
  "outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-0 " +
  "hover:bg-[rgba(129,140,248,0.15)] hover:border-[rgba(129,140,248,0.3)] hover:text-[var(--color-primary)]";

const btnPrimary =
  "group relative inline-flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-primary)] border-0 text-white transition-all duration-200 cursor-pointer " +
  "outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-surface)] " +
  "hover:bg-[var(--color-primary-soft)] hover:shadow-[0_0_20px_rgba(129,140,248,0.4)]";

function Tooltip({ label }: { label: string }) {
  return (
    <span
      className="pointer-events-none absolute -bottom-9 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-lg px-2.5 py-1 text-[10px] font-medium uppercase tracking-wider opacity-0 transition-opacity duration-200 group-hover:opacity-100"
      style={{
        backgroundColor: "rgba(255, 255, 255, 0.12)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        color: "var(--color-on-surface)",
        border: "1px solid var(--glass-border)",
      }}
    >
      {label}
    </span>
  );
}

export function ControlBar({ playing, onPrev, onToggle, onNext, onStop }: Props) {
  return (
    <div className="flex items-center gap-2.5">
      <button type="button" aria-label="上一首" onClick={onPrev} className={btn}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="19 20 9 12 19 4 19 20" />
          <line x1="5" y1="19" x2="5" y2="5" />
        </svg>
        <Tooltip label="PREV" />
      </button>

      <button type="button" aria-label={playing ? "暂停" : "播放"} onClick={() => void onToggle()} className={btnPrimary}>
        {playing ? (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="4" width="4" height="16" rx="1" />
            <rect x="14" y="4" width="4" height="16" rx="1" />
          </svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
        )}
        <Tooltip label={playing ? "PAUSE" : "PLAY"} />
      </button>

      <button type="button" aria-label="下一首" onClick={onNext} className={btn}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="5 4 15 12 5 20 5 4" />
          <line x1="19" y1="5" x2="19" y2="19" />
        </svg>
        <Tooltip label="NEXT" />
      </button>

      <button type="button" aria-label="停止" onClick={onStop} className={btn}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
          <rect x="6" y="6" width="12" height="12" rx="2" />
        </svg>
        <Tooltip label="STOP" />
      </button>
    </div>
  );
}
