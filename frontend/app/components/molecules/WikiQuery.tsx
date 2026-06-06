"use client";

import { apiUrl } from "@/app/lib/api";
import { useState } from "react";

interface WikiResult {
  title: string;
  path: string;
  snippet: string;
  score: number;
}

export function WikiQuery() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<WikiResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const res = await fetch(apiUrl(`/api/wiki/query?q=${encodeURIComponent(query.trim())}`));
      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
        setIsOpen(true);
      }
    } catch {
      // ignore
    }
    setSearching(false);
  };

  return (
    <div className="relative">
      <div className="flex items-center gap-1">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Search wiki..."
          className="w-24 rounded border px-2 py-0.5 text-[10px]"
          style={{
            backgroundColor: "transparent",
            borderColor: "var(--glass-border)",
            color: "var(--color-on-surface)",
          }}
        />
        <button
          type="button"
          onClick={handleSearch}
          disabled={searching}
          className="text-[10px] opacity-60 transition-opacity hover:opacity-100"
          style={{ color: "var(--color-primary)" }}
        >
          {searching ? "..." : "Go"}
        </button>
      </div>

      {isOpen && results.length > 0 && (
        <div
          className="absolute top-full right-0 z-50 mt-1 max-h-60 w-64 overflow-y-auto rounded-lg border py-1"
          style={{
            backgroundColor: "var(--color-surface)",
            borderColor: "var(--glass-border)",
          }}
        >
          {results.map((r) => (
            <div
              key={r.path}
              className="border-b px-3 py-2 last:border-b-0"
              style={{ borderColor: "var(--glass-border)" }}
            >
              <div className="text-[11px] font-medium" style={{ color: "var(--color-primary)" }}>
                {r.title}
              </div>
              {r.snippet && (
                <div className="mt-0.5 text-[10px] opacity-60 line-clamp-2" style={{ color: "var(--color-on-surface-muted)" }}>
                  {r.snippet}
                </div>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="w-full px-3 py-1 text-center text-[10px] opacity-40 hover:opacity-80"
            style={{ color: "var(--color-on-surface-muted)" }}
          >
            Close
          </button>
        </div>
      )}

      {isOpen && results.length === 0 && (
        <div
          className="absolute top-full right-0 z-50 mt-1 w-48 rounded-lg border px-3 py-2 text-center text-[10px]"
          style={{
            backgroundColor: "var(--color-surface)",
            borderColor: "var(--glass-border)",
            color: "var(--color-on-surface-muted)",
          }}
        >
          No results found
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="mt-1 block w-full opacity-40 hover:opacity-80"
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
}
