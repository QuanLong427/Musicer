"use client";

import { apiUrl } from "@/app/lib/api";
import { useCallback, useEffect, useState } from "react";

interface WikiStatusData {
  initialized: boolean;
  total_songs?: number;
  total_artists?: number;
  total_genres?: number;
  total_albums?: number;
  total_topics?: number;
  last_ingested_at?: string;
}

export function WikiStatus() {
  const [status, setStatus] = useState<WikiStatusData | null>(null);
  const [initializing, setInitializing] = useState(false);

  const loadStatus = useCallback(async () => {
    try {
      const res = await fetch(apiUrl("/api/wiki/status"));
      if (res.ok) {
        setStatus(await res.json());
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const handleInit = async () => {
    setInitializing(true);
    try {
      const res = await fetch(apiUrl("/api/wiki/init"), { method: "POST" });
      if (res.ok) {
        await loadStatus();
      }
    } catch {
      // ignore
    }
    setInitializing(false);
  };

  if (!status) {
    return (
      <div className="text-[11px] opacity-50" style={{ color: "var(--color-on-surface-muted)" }}>
        Loading wiki status...
      </div>
    );
  }

  if (!status.initialized) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-[11px] opacity-60" style={{ color: "var(--color-on-surface-muted)" }}>
          Wiki not initialized
        </span>
        <button
          type="button"
          onClick={handleInit}
          disabled={initializing}
          className="rounded border px-2 py-0.5 text-[10px] font-medium transition-colors hover:bg-[rgba(129,140,248,0.15)]"
          style={{
            borderColor: "rgba(129,140,248,0.3)",
            color: "var(--color-primary)",
          }}
        >
          {initializing ? "Initializing..." : "Init Wiki"}
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-3 text-[10px]" style={{ color: "var(--color-on-surface-muted)" }}>
      <span className="opacity-60">Wiki:</span>
      <span>{status.total_songs ?? 0} songs</span>
      <span>{status.total_artists ?? 0} artists</span>
      <span>{status.total_genres ?? 0} genres</span>
      <span>{status.total_albums ?? 0} albums</span>
      {status.last_ingested_at && (
        <span className="opacity-40">last: {status.last_ingested_at}</span>
      )}
    </div>
  );
}
