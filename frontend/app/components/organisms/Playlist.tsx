"use client";

import { Label } from "@/app/components/atoms/Label";
import type { Track } from "@/app/lib/types";
import { usePlayer } from "@/app/context/PlayerContext";
import { apiUrl } from "@/app/lib/api";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

function fmtSec(s: number): string {
  if (!Number.isFinite(s) || s <= 0) return "—";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

function useDurationMap(tracks: Track[]) {
  const [map, setMap] = useState<Record<string, number>>({});
  const pending = useRef(new Set<string>());

  useEffect(() => {
    for (const t of tracks) {
      if (map[t.id] != null || pending.current.has(t.id)) continue;
      pending.current.add(t.id);

      const audio = new Audio();
      audio.preload = "metadata";
      const id = t.id;
      audio.addEventListener(
        "loadedmetadata",
        () => {
          const dur = audio.duration;
          if (Number.isFinite(dur) && dur > 0) {
            setMap((prev) => ({ ...prev, [id]: dur }));
          }
          pending.current.delete(id);
          audio.src = "";
        },
        { once: true }
      );
      audio.addEventListener(
        "error",
        () => {
          pending.current.delete(id);
          audio.src = "";
        },
        { once: true }
      );
      audio.src = apiUrl(t.url);
    }
  }, [tracks, map]);

  return map;
}

export function Playlist() {
  const { state, playTrack, removeTrack } = usePlayer();
  const [filter, setFilter] = useState("");

  const allTracks = state.playlist;
  const durMap = useDurationMap(allTracks);

  const q = filter.trim().toLowerCase();
  const rows = useMemo(() => {
    if (!q.length) return allTracks;
    return allTracks.filter((t) => {
      const hay = `${t.title} ${t.author} ${t.filename}`.toLowerCase();
      return hay.includes(q);
    });
  }, [allTracks, q]);

  const onRowClick = useCallback(
    (track: Track) => {
      playTrack(track);
    },
    [playTrack]
  );

  return (
    <div
      className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border transition-all duration-200"
      style={{
        borderColor: "var(--glass-border)",
        backgroundColor: "rgba(255, 255, 255, 0.04)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
      }}
    >
      <div
        className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-[var(--glass-border)] px-3 py-2.5 md:px-4"
      >
        <div className="flex flex-wrap items-baseline gap-2">
          <Label size="md">QUEUE</Label>
          <span className="text-[11px] tabular-nums text-[color:var(--color-on-surface-muted)] opacity-70">
            [{rows.length}/{allTracks.length}]
          </span>
        </div>
      </div>

      <div className="shrink-0 px-3 py-2 md:px-4">
        <label className="sr-only" htmlFor="playlist-search">
          Filter queue
        </label>
        <input
          id="playlist-search"
          type="search"
          placeholder="Search queue…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          autoCapitalize="off"
          autoCorrect="off"
          spellCheck={false}
          className="w-full rounded-lg border border-[var(--glass-border)] bg-[rgba(255,255,255,0.04)] px-3 py-2 text-sm outline-none transition-all duration-200 placeholder:text-[color:var(--color-on-surface-muted)] focus:border-[rgba(129,140,248,0.3)] focus:bg-[rgba(255,255,255,0.06)]"
          style={{
            fontFamily: "var(--font-body)",
            color: "var(--color-on-surface)",
          }}
        />
      </div>

      {allTracks.length === 0 ? (
        <div className="flex flex-1 items-center justify-center px-4 py-6">
          <p className="text-center text-xs text-[color:var(--color-on-surface-muted)] opacity-60">
            Empty queue — use the chat to add songs
          </p>
        </div>
      ) : rows.length === 0 ? (
        <p className="px-3 py-4 text-sm text-[color:var(--color-on-surface-muted)] opacity-60 md:px-4">
          No matches found
        </p>
      ) : (
        <div className="min-h-0 flex-1 overflow-auto scrollbar-thin">
          <table className="w-full border-collapse text-left text-sm">
            <thead className="sticky top-0 z-[1]">
              <tr style={{ borderBottom: "1px solid var(--glass-border)" }}>
                <th className="w-10 px-2 py-2.5 text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-on-surface-muted)]">
                  #
                </th>
                <th className="px-2 py-2.5 text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-on-surface-muted)]">
                  TITLE
                </th>
                <th className="w-20 shrink-0 px-2 py-2.5 text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-on-surface-muted)]">
                  DUR
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t, idx) => {
                const active = state.current?.id === t.id;
                return (
                  <tr
                    key={t.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => onRowClick(t)}
                    onKeyDown={(e) => {
                      if (e.key !== "Enter" && e.key !== " ") return;
                      e.preventDefault();
                      onRowClick(t);
                    }}
                    className="group relative cursor-pointer transition-all duration-200 hover:bg-[rgba(255,255,255,0.04)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-primary)] focus-visible:ring-inset"
                    style={{
                      borderLeft: active ? "3px solid var(--color-primary)" : "3px solid transparent",
                      backgroundColor: active ? "rgba(129,140,248,0.06)" : undefined,
                    }}
                  >
                    <td className="w-10 shrink-0 px-2 py-2.5 tabular-nums text-[color:var(--color-on-surface-muted)]">
                      {idx + 1}
                    </td>
                    <td className="max-w-0 truncate px-2 py-2.5" style={{ color: active ? "var(--color-primary)" : "var(--color-on-surface)" }}>
                      {t.title}
                    </td>
                    <td className="w-20 shrink-0 px-2 py-2.5 text-right tabular-nums text-[color:var(--color-on-surface-muted)]">
                      {active && state.duration > 0 ? fmtSec(state.duration) : fmtSec(durMap[t.id])}
                    </td>
                    <td className="absolute right-0 top-0 bottom-0 flex items-center justify-center px-1 opacity-0 group-hover:opacity-100 transition-opacity"
                      style={{ backgroundColor: "rgba(10, 10, 26, 0.8)" }}
                    >
                      <button
                        type="button"
                        aria-label="移除"
                        onClick={(e) => {
                          e.stopPropagation();
                          removeTrack(t.id);
                        }}
                        className="group/rm relative flex h-7 w-7 items-center justify-center rounded-full border border-[var(--glass-border)] bg-transparent text-[color:var(--color-on-surface-muted)] transition-all duration-200 hover:border-[var(--color-error)] hover:text-[var(--color-error)] hover:bg-[rgba(251,113,133,0.1)]"
                      >
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                          <line x1="18" y1="6" x2="6" y2="18" />
                          <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                        <span
                          className="pointer-events-none absolute -top-8 right-0 z-10 whitespace-nowrap rounded-lg px-2 py-1 text-[10px] font-medium uppercase tracking-wider opacity-0 transition-opacity duration-200 group-hover/rm:opacity-100"
                          style={{
                            backgroundColor: "rgba(255, 255, 255, 0.1)",
                            backdropFilter: "blur(8px)",
                            WebkitBackdropFilter: "blur(8px)",
                            color: "var(--color-error)",
                            border: "1px solid rgba(251,113,133,0.2)",
                          }}
                        >
                          REMOVE
                        </span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
