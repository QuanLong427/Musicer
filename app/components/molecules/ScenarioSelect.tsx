"use client";

import { useState } from "react";
import { apiUrl } from "@/app/lib/api";

interface ScenarioSelectProps {
  value: string;
  onChange: (scenario: string) => void;
}

export function ScenarioSelect({ value, onChange }: ScenarioSelectProps) {
  const [scenarios, setScenarios] = useState<string[]>([]);
  const [isAdding, setIsAdding] = useState(false);
  const [newName, setNewName] = useState("");
  const [isOpen, setIsOpen] = useState(false);

  const loadScenarios = async () => {
    try {
      const res = await fetch(apiUrl("/api/scenarios"));
      if (res.ok) {
        const data = await res.json();
        setScenarios(data.scenarios || []);
      }
    } catch {
      // 加载失败使用默认值
      setScenarios(["默认", "编程", "跑步", "睡觉", "驾驶"]);
    }
  };

  const handleAdd = async () => {
    if (!newName.trim()) return;
    try {
      const res = await fetch(apiUrl("/api/scenarios"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName.trim() }),
      });
      if (res.ok) {
        const data = await res.json();
        setScenarios(data.scenarios || []);
        onChange(newName.trim());
        setNewName("");
        setIsAdding(false);
      }
    } catch {
      // 添加失败
    }
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => {
          setIsOpen(!isOpen);
          if (!isOpen) loadScenarios();
        }}
        className="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase tracking-wider transition-all duration-200 hover:bg-[rgba(129,140,248,0.15)]"
        style={{
          borderColor: "rgba(129,140,248,0.3)",
          color: "var(--color-primary)",
        }}
      >
        <span className="opacity-60">场景:</span>
        <span>{value}</span>
        <span className="opacity-40">{isOpen ? "▴" : "▾"}</span>
      </button>

      {isOpen && (
        <div
          className="absolute top-full left-0 z-50 mt-1 min-w-[120px] rounded-lg border py-1"
          style={{
            backgroundColor: "var(--color-surface)",
            borderColor: "var(--glass-border)",
          }}
        >
          {scenarios.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => {
                onChange(s);
                setIsOpen(false);
              }}
              className="block w-full px-3 py-1.5 text-left text-[11px] transition-colors hover:bg-[rgba(129,140,248,0.1)]"
              style={{
                color: s === value ? "var(--color-primary)" : "var(--color-on-surface)",
              }}
            >
              {s}
            </button>
          ))}

          <div className="border-t px-2 py-1" style={{ borderColor: "var(--glass-border)" }}>
            {isAdding ? (
              <div className="flex gap-1">
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAdd()}
                  placeholder="场景名称"
                  className="flex-1 rounded border px-1.5 py-0.5 text-[11px]"
                  style={{
                    backgroundColor: "transparent",
                    borderColor: "var(--glass-border)",
                    color: "var(--color-on-surface)",
                  }}
                  autoFocus
                />
                <button
                  type="button"
                  onClick={handleAdd}
                  className="text-[10px] font-medium"
                  style={{ color: "var(--color-primary)" }}
                >
                  添加
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setIsAdding(true)}
                className="w-full text-left text-[11px] opacity-60 transition-opacity hover:opacity-100"
                style={{ color: "var(--color-on-surface-muted)" }}
              >
                + 添加场景
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
