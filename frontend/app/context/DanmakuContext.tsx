"use client";

import type { DanmakuItem } from "@/app/lib/bili";
import { usePlayer } from "@/app/context/PlayerContext";
import { apiUrl } from "@/app/lib/api";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

type DanmakuCtxValue = {
  enabled: boolean;
  hasDanmaku: boolean;
  currentDanmaku: DanmakuItem[];
  error: string | null;
  toggleDanmaku: () => void;
  fetchDanmaku: (bvid: string) => void;
  retryFetch: () => void;
};

const DanmakuContext = createContext<DanmakuCtxValue | null>(null);

export function DanmakuProvider({ children }: { children: ReactNode }) {
  const [enabled, setEnabled] = useState(true);
  const [danmakuMap, setDanmakuMap] = useState<
    Record<string, DanmakuItem[]>
  >({});
  const [error, setError] = useState<string | null>(null);

  const { state, trackRemoved, clearTrackRemoved } = usePlayer();
  const bvid = state.current?.bvid ?? null;
  const prevBvidRef = useRef<string | null>(null);
  const danmakuMapRef = useRef<Record<string, DanmakuItem[]>>({});
  const [activeDanmaku, setActiveDanmaku] = useState<DanmakuItem[]>([]);

  // Keep ref in sync with state
  useEffect(() => {
    danmakuMapRef.current = danmakuMap;
  }, [danmakuMap]);

  const toggleDanmaku = useCallback(() => {
    setEnabled((prev) => !prev);
  }, []);

  const fetchDanmaku = useCallback(
    (bvidToFetch: string) => {
      if (danmakuMap[bvidToFetch]) return;

      console.log("[Danmaku] Fetching for bvid:", bvidToFetch);
      fetch(apiUrl(`/api/bili/danmaku?bvid=${encodeURIComponent(bvidToFetch)}`))
        .then((res) => {
          console.log("[Danmaku] Response status:", res.status);
          return res.json();
        })
        .then((json: { danmaku?: DanmakuItem[] }) => {
          console.log("[Danmaku] Got danmaku count:", json.danmaku?.length ?? 0);
          if (json.danmaku?.length) {
            setDanmakuMap((prev) => ({
              ...prev,
              [bvidToFetch]: json.danmaku!,
            }));
          }
        })
        .catch((err) => {
          console.error("[Danmaku] Fetch error:", err);
          setError("弹幕获取失败");
        });
    },
    [danmakuMap]
  );

  // Auto-fetch danmaku when current track's bvid changes
  useEffect(() => {
    console.log("[Danmaku] bvid changed:", bvid, "trackRemoved:", trackRemoved);
    if (trackRemoved) {
      // Track was deleted — load new track's danmaku from cache (or empty)
      clearTrackRemoved();
      prevBvidRef.current = bvid;
      setActiveDanmaku(bvid ? danmakuMapRef.current[bvid] ?? [] : []);
      return;
    }
    // Normal bvid change — fetch and switch to new track's danmaku
    if (bvid !== prevBvidRef.current) {
      prevBvidRef.current = bvid;
      if (bvid) {
        setError(null);
        fetchDanmaku(bvid);
        // Set danmaku from cache if available
        setActiveDanmaku(danmakuMapRef.current[bvid] ?? []);
      } else {
        setActiveDanmaku([]);
      }
    }
  }, [bvid, fetchDanmaku, trackRemoved, clearTrackRemoved]);

  // Update active danmaku when fetch completes
  useEffect(() => {
    if (prevBvidRef.current && danmakuMap[prevBvidRef.current]) {
      setActiveDanmaku(danmakuMap[prevBvidRef.current]);
    }
  }, [danmakuMap]);

  const currentDanmaku = activeDanmaku;
  const hasDanmaku = currentDanmaku.length > 0;

  const retryFetch = useCallback(() => {
    if (!bvid) return;
    setError(null);
    // Remove from cache so fetchDanmaku won't skip it
    setDanmakuMap((prev) => {
      const next = { ...prev };
      delete next[bvid];
      return next;
    });
    // Re-fetch after cache is cleared
    fetchDanmaku(bvid);
  }, [bvid, fetchDanmaku]);

  const value = useMemo<DanmakuCtxValue>(
    () => ({
      enabled,
      hasDanmaku,
      currentDanmaku,
      error,
      toggleDanmaku,
      fetchDanmaku,
      retryFetch,
    }),
    [enabled, hasDanmaku, currentDanmaku, error, toggleDanmaku, fetchDanmaku, retryFetch]
  );

  return (
    <DanmakuContext.Provider value={value}>
      {children}
    </DanmakuContext.Provider>
  );
}

export function useDanmaku() {
  const v = useContext(DanmakuContext);
  if (!v) throw new Error("useDanmaku must be used within DanmakuProvider");
  return v;
}
