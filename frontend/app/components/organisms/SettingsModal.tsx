"use client";

import { useState, useEffect, useCallback } from "react";
import { apiUrl } from "@/app/lib/api";

type Props = { open: boolean; onClose: () => void };

type Config = {
  base_url: string;
  api_key: string;
  model_name: string;
};

export function SettingsModal({ open, onClose }: Props) {
  const [config, setConfig] = useState<Config>({
    base_url: "",
    api_key: "",
    model_name: "",
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  // Load config on open
  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError("");
    setSuccess(false);
    fetch(apiUrl("/api/config"))
      .then((r) => r.json())
      .then((data: Config) => {
        setConfig(data);
        setLoading(false);
      })
      .catch(() => {
        setError("Failed to load config");
        setLoading(false);
      });
  }, [open]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError("");
    setSuccess(false);
    try {
      const res = await fetch(apiUrl("/api/config"), {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base_url: config.base_url,
          api_key: config.api_key.startsWith("****") ? undefined : config.api_key,
          model_name: config.model_name,
        }),
      });
      if (res.ok) {
        setSuccess(true);
        setTimeout(() => {
          onClose();
          setSuccess(false);
        }, 600);
      } else {
        const data = await res.json();
        setError(data.detail || "Save failed");
      }
    } catch {
      setError("Network error");
    } finally {
      setSaving(false);
    }
  }, [config, onClose]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

      {/* Modal */}
      <div
        className="relative z-10 w-full max-w-sm rounded-xl border p-5 shadow-xl"
        style={{
          borderColor: "var(--glass-border)",
          backgroundColor: "rgba(30, 30, 40, 0.95)",
          backdropFilter: "blur(24px)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h2
            className="text-sm font-medium uppercase tracking-wider"
            style={{ color: "var(--color-on-surface)" }}
          >
            LLM Settings
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="cursor-pointer text-[color:var(--color-on-surface-muted)] transition-colors hover:text-[color:var(--color-on-surface)]"
            style={{ background: "none", border: "none", padding: 0, lineHeight: 1 }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: "18px" }}>
              close
            </span>
          </button>
        </div>

        {loading ? (
          <div className="py-6 text-center text-xs" style={{ color: "var(--color-on-surface-muted)" }}>
            Loading...
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <Field
              label="Base URL"
              value={config.base_url}
              onChange={(v) => setConfig((c) => ({ ...c, base_url: v }))}
            />
            <Field
              label="API Key"
              type="password"
              value={config.api_key}
              onChange={(v) => setConfig((c) => ({ ...c, api_key: v }))}
            />
            <Field
              label="Model Name"
              value={config.model_name}
              onChange={(v) => setConfig((c) => ({ ...c, model_name: v }))}
            />

            {error && (
              <p className="text-[11px]" style={{ color: "#f87171" }}>
                {error}
              </p>
            )}

            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="mt-1 w-full cursor-pointer rounded-full border px-3 py-1.5 text-[11px] font-medium uppercase tracking-wider transition-all duration-200 disabled:opacity-50"
              style={{
                borderColor: "rgba(129, 140, 248, 0.3)",
                backgroundColor: success
                  ? "rgba(52, 211, 153, 0.15)"
                  : "rgba(129, 140, 248, 0.1)",
                color: success ? "#34d399" : "var(--color-primary)",
              }}
            >
              {saving ? "SAVING..." : success ? "SAVED" : "SAVE"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({
  label,
  type = "text",
  value,
  onChange,
}: {
  label: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span
        className="text-[10px] font-medium uppercase tracking-wider"
        style={{ color: "var(--color-on-surface-muted)" }}
      >
        {label}
      </span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border px-3 py-1.5 text-sm outline-none transition-colors focus:border-[rgba(129,140,248,0.5)]"
        style={{
          borderColor: "var(--glass-border)",
          backgroundColor: "rgba(255,255,255,0.05)",
          color: "var(--color-on-surface)",
        }}
      />
    </label>
  );
}
